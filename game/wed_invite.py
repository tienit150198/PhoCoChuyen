"""💌 Thiệp mời cưới cả phố: a couple's own words on a card every player on the server sees once.

Owner 08/10: "cho thêm tính năng thông báo cưới toàn server, mọi người sẽ nhập nội dung đó xong mời cưới (hiển thị
popup như của "Có gì mới" ấy, mà hiển thị cho toàn server 1 lần). xong mất 10k cho mỗi lần mời."

Who sends: a story-mode account that is engaged or married (game/marriage.py `couples`, the same bond the Hôn nhân
sheet shows). When the couple has a live party booked (game/wedding_live.py party_view 'booked' or 'live') the card
is tied to it: it shows the party's time (read again at every delivery, so a moved party shows its new time) and an
"Đi dự / Xem lịch cưới" button, and it is only delivered until the party ends. Otherwise it is a plain "Thông báo
cưới", delivered for PLAIN_SECS. A stranger without a partner never can.

Paying: PRICE xu through the Hôn nhân purchase path (marriage._can_spend / _spend: the wallet first, or the bank
account / card the player picks in the payment sheet, never the joint fund). The debit is a marriage_effects row
`wedinv:<sid16>:<rid>` written in the same transaction as the card, so a resent request (same rid) is never paid
twice. A refused send (limits, no partner, not enough money) pays nothing.

Limits: one card per sender a day (SEND_GAP), one per sender and party (a plain one: once per sender and couple),
Text: it goes through the chat's own cleaner and mask (live/filters.py): no control or invisible characters,
phone numbers / links / heavy words masked; the original is kept for admins only (`raw`).

Delivery, once per save, no mass write: the cards live in `wed_invites` (an increasing id). Each viewer has at most one
row in `wed_invite_seen` (sid, upto, day, n, cheer_upto), written only when a card is shown: `upto` is the last card
shown, so a card is never shown twice and a newer one is found with one indexed query. A viewer gets at most
PER_DAY cards a Vietnam day (the rest wait for the next day while they are still valid). The couple themselves never
get their own card, and nobody who blocked the sender or the partner (or was blocked by them; `marriage_blocks` by
sid, chat `blocks` by pid) ever sees it.
* online players: a NOTIFY 'wedinvite' on commit; the live service (live/wedinvite.py) tells every open page, which
  asks GET /api/wedinvite a moment later (an older page ignores the frame);
* everyone else: the page asks GET /api/wedinvite after loading (an older server answers 404: the page stays quiet).
"Chúc mừng 🎉" adds one to the card's `cheers` (once per viewer and card); the couple sees the count in the sheet.

Admins (ADMIN_USERS): GET/POST /api/admin/wedinvite lists the last cards and deletes one (no refund). Kill switch:
MNL_WED_INVITE_OFF=1 stops sending and showing at once.

Tables (game/pg_schema.py, SCHEMA_VERSION 32): new ones only, no save key: a rollback never sees them.
"""
from __future__ import annotations

import datetime
import os
import time

from . import db as dbm

PRICE = 10_000                  # xu a card (owner 08/10: "mất 10k cho mỗi lần mời")
TEXT_MIN, TEXT_MAX, TEXT_LINES = 10, 200, 4
SEND_GAP = 86400                # one card per sender a day
PLAIN_SECS = 48 * 3600          # a card without a party is delivered for 2 days
PARTY_HOLD = 15 * 86400         # upper bound of a party card's row (the party itself decides: delivered until it ends)
PER_DAY = 3                     # cards a viewer is shown a Vietnam day at most (the rest wait)
BATCH = 3                       # cards one GET hands out
LIVE_CACHE = 15.0               # seconds the "any card live at all?" answer is kept (most loads: none, no query)
VN = datetime.timezone(datetime.timedelta(hours=7))
PRESETS = (
    'Trân trọng kính mời cả phố tới chung vui trong ngày trọng đại của hai đứa mình 💕',
    'Tụi mình cưới rồi nè! Cảm ơn cả phố đã luôn ở bên, ghé chung vui với tụi mình nha 🥰',
    'Sau bao ngày thương nhau, tụi mình về chung một nhà. Mong được cả phố chúc phúc 💍',
    'Có cỗ, có nhạc, có múa lân! Cả phố nhớ ghé ăn cưới tụi mình nha 🎉',
)
_live = [0.0, None]             # [checked at, the newest live card id or 0]


def off() -> bool:
    return os.environ.get('MNL_WED_INVITE_OFF', '').strip() not in ('', '0')


def now() -> float:
    return time.time()


def vn_day(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%Y-%m-%d')


def _mr():
    from . import marriage
    return marriage


def _pid(sid: str) -> str:
    from .social import pid_of
    return pid_of(sid)


def clean_text(text) -> tuple[str, str | None]:
    """(what players see, the original when the mask changed it). Raises MarriageError when it is not 10–200 chars."""
    from live import filters
    mr = _mr()
    mr.need(isinstance(text, str), 'Viết vài lời mời cả phố nhé.', 'bad_text')
    out = filters.clean(text, TEXT_MAX, TEXT_LINES)
    if out is None:
        stripped = filters.clean(text, TEXT_MAX * 4, TEXT_LINES) or ''
        mr.need(len(stripped) <= TEXT_MAX, f'Lời mời dài tối đa {TEXT_MAX} ký tự thôi nhé.', 'bad_text')
        mr.need(False, 'Viết vài lời mời cả phố nhé.', 'bad_text')
    mr.need(len(out) >= TEXT_MIN, f'Viết ít nhất {TEXT_MIN} ký tự nhé.', 'bad_text')
    masked = filters.mask(out)
    return masked, (out if masked != out else None)


def _invalidate() -> None:
    _live[0], _live[1] = 0.0, None


def _any_live(db, t: float) -> bool:
    """Is any card still deliverable? Kept LIVE_CACHE seconds: the common answer (none) costs no query."""
    if _live[1] is not None and t - _live[0] < LIVE_CACHE:
        return _live[1] > 0
    r = db.execute("SELECT MAX(id) AS id FROM wed_invites WHERE status='live' AND until>?", (t,)).fetchone()
    _live[0], _live[1] = t, int(r['id'] or 0) if r else 0
    return _live[1] > 0


# ---------------------------------------------------------------- the sender's side
def _party(db, c: dict, t: float) -> dict | None:
    """The couple's live party a card can be tied to: booked or open now (not done)."""
    from . import wedding_live as wl
    v = wl.party_view(db, c, t)
    return v if v and v.get('state') in ('booked', 'live') else None


def _check(db, sid: str, c: dict | None, t: float) -> tuple[dict | None, str]:
    """(the party or None, why not: '' when this sender may send now)."""
    if off():
        return None, 'Thiệp mời cả phố đang tạm nghỉ, quay lại sau nhé.'
    if not c or c.get('status') not in ('engaged', 'married'):
        return None, 'Thiệp mời cưới dành cho các cặp đã đính hôn hoặc kết hôn 💍'
    p = _party(db, c, t)
    if p:
        if db.execute('SELECT 1 FROM wed_invites WHERE sid=? AND wedding=?', (sid, p['id'])).fetchone():
            return p, 'Bạn đã gửi thiệp mời cho tiệc này rồi 💌'
    elif db.execute('SELECT 1 FROM wed_invites WHERE sid=? AND couple=? AND wedding IS NULL', (sid, c['id'])).fetchone():
        return p, 'Bạn đã gửi thông báo cưới cho cả phố rồi. Hẹn giờ tổ chức tiệc để gửi thiệp mời mọi người tới dự nhé 🎉'
    last = db.execute('SELECT at FROM wed_invites WHERE sid=? ORDER BY id DESC LIMIT 1', (sid,)).fetchone()
    if last and float(last['at']) > t - SEND_GAP:
        h = max(1, int((float(last['at']) + SEND_GAP - t + 3599) // 3600))
        return p, f'Mỗi ngày gửi một thiệp thôi nhé. Khoảng {h} giờ nữa là gửi được.'
    return p, ''


def _sent_view(r) -> dict:
    return dict(id=int(r['id']), at=int(r['at']), text=r['text'], cheers=int(r['cheers']), status=r['status'],
                party=r['wedding'] is not None)


def me(store, token: str) -> dict:
    """GET /api/wedinvite/me: what the compose sheet needs."""
    mr = _mr()
    sid, display = mr.whoami(store, token)
    out = dict(price=PRICE, min=TEXT_MIN, max=TEXT_MAX, presets=list(PRESETS), per_day=PER_DAY, off=off())
    if not sid or display is None:
        return dict(out, can=False, why='Tạo tài khoản để gửi thiệp mời cưới nhé.')
    state = store.read(token)[0]
    t = now()
    with store.connect() as db:
        c = mr._bond(db, sid)
        p, why = _check(db, sid, c, t)
        if not why and not (state.get('journey') or {}).get('story'):
            why = 'Thiệp mời cưới chỉ có trong hành trình.'
        last = db.execute('SELECT * FROM wed_invites WHERE sid=? ORDER BY id DESC LIMIT 1', (sid,)).fetchone()
        names = dict(a=mr._display(db, c['a']), b=mr._display(db, c['b'])) if c else None
    if names and c and c['b'] == sid:      # my name first
        names = dict(a=names['b'], b=names['a'])
    return dict(out, can=not why, why=why, names=names, status=(c or {}).get('status'),
                party=dict(id=p['id'], at=p['at'], at_label=p['at_label'], state=p['state']) if p else None,
                sent=_sent_view(last) if last else None)


def send(store, token: str, d: dict) -> dict:
    """POST /api/wedinvite/send {text, rid, pay}: pay PRICE and send the card to the whole server."""
    mr = _mr()
    mr.need(isinstance(d, dict), 'Dữ liệu không hợp lệ.')
    sid, display = mr._require(store, token)
    mr.need(not off(), 'Thiệp mời cả phố đang tạm nghỉ, quay lại sau nhé.', 'wedinv_off', 503)
    text, raw = clean_text(d.get('text'))
    rid = mr._rid(d)[:24]
    eid = f'wedinv:{sid[:16]}:{rid}'
    pay = d.get('pay')
    with store.connect() as db:
        if db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (eid,)).fetchone():
            return dict(message='Thiệp này đã gửi rồi 💌', changed=False, again=True)
        c = mr._bond(db, sid)
        _, why = _check(db, sid, c, now())
        mr.need(not why, why, 'wedinv_refused', 409)
    eff = mr._effect(eid, sid, 'wallet', -PRICE, '💌 Thiệp mời cưới cả phố')

    def fn(s):
        mr.need((s.get('journey') or {}).get('story'), 'Thiệp mời cưới chỉ có trong hành trình.', 'not_story')
        if eff['id'] in mr._box(s)['applied']:
            return
        mr.need(mr._can_spend(s, PRICE, pay), f'Chưa đủ {mr._xu(PRICE)} xu để gửi thiệp. Gom thêm chút rồi gửi nhé 💪', 'not_enough')
        mr._spend(s, eff, pay)

    def ops(db):
        t = now()
        c2 = mr._bond(db, sid)
        p, why = _check(db, sid, c2, t)      # again, in the transaction that pays (a double tap, a divorce meanwhile)
        mr.need(not why, why, 'wedinv_refused', 409)
        partner = mr._other(c2, sid)
        names = dict(a=mr._display(db, sid), b=mr._display(db, partner))
        mr._insert_effects(db, [eff], 'applied')
        until = t + (PARTY_HOLD if p else PLAIN_SECS)
        r = db.execute('INSERT INTO wed_invites(rid, sid, partner, pid, ppid, couple, wedding, name_a, name_b, text, raw, at, until, status, cheers) '
                       "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'live',0) RETURNING id",
                       (eid, sid, partner, _pid(sid), _pid(partner), c2['id'], p['id'] if p else None, names['a'], names['b'],
                        text, raw, t, until)).fetchone()
        mr._notice(db, partner, f'💌 {names["a"]} vừa gửi thiệp mời cưới của hai bạn tới cả phố!')
        from . import live_chat
        live_chat.notify(db, dict(op='wedinvite', id=int(r['id']), pids=[_pid(sid), _pid(partner)]))
        return int(r['id'])
    try:
        mr._mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:   # the same rid twice (a double tap), or this party's card from another tab
        with store.connect() as db:
            if db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (eid,)).fetchone():
                return dict(message='Thiệp này đã gửi rồi 💌', changed=False, again=True)
        mr.need(False, 'Bạn đã gửi thiệp mời cho tiệc này rồi 💌', 'wedinv_refused', 409)
    _invalidate()
    return dict(message='💌 Đã gửi thiệp! Cả phố sẽ thấy thiệp của hai bạn khi vào game.', changed=True)


# ---------------------------------------------------------------- the viewers' side
_DUE = ("SELECT i.id, i.wedding, i.name_a, i.name_b, i.text, i.at, p.at AS party_at FROM wed_invites i "
        'JOIN couples c ON c.id=i.couple LEFT JOIN wedding_parties p ON p.wedding=i.wedding '
        "WHERE i.status='live' AND i.id>? AND i.until>? AND i.sid<>? AND i.partner<>? AND c.status IN ('engaged','married') "
        "AND (i.wedding IS NULL OR (p.status='booked' AND p.at+?>?)) "
        'AND NOT EXISTS (SELECT 1 FROM marriage_blocks b WHERE (b.sid=? AND b.target IN (i.sid, i.partner)) OR (b.target=? AND b.sid IN (i.sid, i.partner))) '
        'AND NOT EXISTS (SELECT 1 FROM blocks k WHERE (k.pid=? AND k.target IN (i.pid, i.ppid)) OR (k.target=? AND k.pid IN (i.pid, i.ppid))) '
        'ORDER BY i.id LIMIT ?')


def _card(r) -> dict:
    from . import wedding_live as wl
    out = dict(id=int(r['id']), a=r['name_a'], b=r['name_b'], text=r['text'], at=int(r['at']))
    if r['wedding'] is not None and r['party_at'] is not None:
        pa = float(r['party_at'])
        out['party'] = dict(id=int(r['wedding']), at=int(pa), at_label=wl.fmt_at(pa), end=int(pa + wl.PARTY_SECS))
    return out


def due(store, sid: str, t: float | None = None) -> list:
    """GET /api/wedinvite: the cards this player has not been shown yet, oldest first, within today's PER_DAY."""
    from . import wedding_live as wl
    if off() or not sid:
        return []
    t = now() if t is None else t
    with store.connect() as db:
        if not _any_live(db, t):
            return []
        s = db.execute('SELECT upto, day, n FROM wed_invite_seen WHERE sid=?', (sid,)).fetchone()
        upto = int(s['upto']) if s else 0
        left = PER_DAY - (int(s['n']) if s and s['day'] == vn_day(t) else 0)
        if left <= 0:
            return []
        pid = _pid(sid)
        rows = db.execute(_DUE, (upto, t, sid, sid, wl.PARTY_SECS, t, sid, sid, pid, pid, min(left, BATCH))).fetchall()
    return [_card(r) for r in rows]


def seen(store, sid: str, d: dict) -> dict:
    """POST /api/wedinvite/seen {id, cheer?}: the card was shown (never again, counts for today); cheer: "Chúc mừng 🎉"
    once per viewer and card (an earlier card cannot be cheered after a later one was shown and cheered)."""
    mr = _mr()
    cid, cheer = d.get('id'), d.get('cheer', False)
    mr.need(type(cid) is int and 1 <= cid <= 10 ** 12 and type(cheer) is bool, 'Thiệp không hợp lệ.', 'bad_card')
    t = now()

    def run(db):
        mr.need(db.execute('SELECT 1 FROM wed_invites WHERE id=?', (cid,)).fetchone(), 'Thiệp không còn nữa.', 'gone', 404)
        shown = db.execute('INSERT INTO wed_invite_seen(sid, upto, day, n, cheer_upto) VALUES(?,?,?,1,0) ON CONFLICT(sid) DO UPDATE '
                           'SET upto=excluded.upto, n=CASE WHEN wed_invite_seen.day=excluded.day THEN wed_invite_seen.n+1 ELSE 1 END, '
                           'day=excluded.day WHERE wed_invite_seen.upto<excluded.upto', (sid, cid, vn_day(t))).rowcount == 1
        cheered = False
        if cheer and db.execute('UPDATE wed_invite_seen SET cheer_upto=? WHERE sid=? AND upto>=? AND cheer_upto<?',
                                (cid, sid, cid, cid)).rowcount == 1:
            cheered = db.execute("UPDATE wed_invites SET cheers=cheers+1 WHERE id=? AND status='live'", (cid,)).rowcount == 1
        return dict(ok=True, shown=shown, cheered=cheered)
    return store.transaction(run)


# ---------------------------------------------------------------- admins, privacy
def admin_view(store) -> dict:
    """GET /api/admin/wedinvite: the last 50 cards (the original text when the mask changed it)."""
    with store.connect() as db:
        rows = db.execute('SELECT i.*, a.username FROM wed_invites i LEFT JOIN accounts a ON a.sid=i.sid ORDER BY i.id DESC LIMIT 50').fetchall()
    return dict(off=off(), price=PRICE, items=[dict(id=int(r['id']), at=float(r['at']), until=float(r['until']), a=r['name_a'], b=r['name_b'],
                                                    username=r['username'] or '', text=r['text'], raw=r['raw'], status=r['status'],
                                                    cheers=int(r['cheers']), party=r['wedding'] is not None, by=r['by_admin'] or '')
                                               for r in rows])


def admin_act(store, admin: str, d: dict) -> dict:
    """POST /api/admin/wedinvite {act: 'delete', id}: the card is never shown again (the sender is not refunded)."""
    mr = _mr()
    cid = d.get('id')
    mr.need(d.get('act') == 'delete' and type(cid) is int and cid >= 1, 'Thao tác không hợp lệ.', 'bad_admin')
    n = store.transaction(lambda db: db.execute("UPDATE wed_invites SET status='deleted', by_admin=?, deleted_at=? WHERE id=? AND status='live'",
                                                (str(admin)[:40], now(), cid)).rowcount)
    _invalidate()
    return dict(ok=True, deleted=bool(n))


def forget(store, token: str) -> None:
    """Account deletion ("XOA"): this player's cards and their seen row."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM wed_invites WHERE sid=?', (sid,))
        db.execute('DELETE FROM wed_invite_seen WHERE sid=?', (sid,))
    store.transaction(run)
    _invalidate()
