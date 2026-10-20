"""💐 Thiệp 20/10 (owner 16/10): a page of its own (/2010) where a player writes a card for someone and shares its link.

Owner: "1 event riêng, xong mọi người bấm vào đó rồi ghi chú gì đó gửi tặng người khác. và có share link được. Người khác
mà vào k cần chơi game vẫn đọc được, nam gửi tặng nữ hoặc nữ tặng nam, xong làm gì đó cute nữa. có vài theme để người ta
thiết kế. làm 1 cái / riêng đi ... Xong các bạn tham gia chương trình này sẽ tặng 100k."

Pages (server.py, rendered from public/2010.html; no save is read or created):
- GET /2010: the writer (signed-in accounts), my cards, and the event's words; after the window: "đã khép lại".
- GET /2010/c/<id>: one card for anyone, no game and no sign-in (an envelope that opens, petals, ❤ thả tim). og:title /
  og:description / og:image (a static PNG per theme: public/icons/2010/og-<theme>.png) are rendered on the server so a
  link shared on Facebook / Zalo / Messenger previews well. The card's words are never in the preview (a surprise).
API: GET /api/2010/me (who writes, the reward, my cards, the CSRF for this same-origin page), GET /api/2010/card?id=,
POST /api/2010/cards {op: create | delete | claim} (session + CSRF), POST /api/2010/heart {id, n} and /api/2010/report
{id, reason} (anyone: same-site checks, rate limits per address). Admin: GET/POST /api/admin/2010 (reported first,
hide / show; the reward log with the account, its life day and how many rewards share its network address).
Words: the chat's cleaner and mask (live/filters.py, like game/chua_wish.py): no control or invisible characters,
phones / links / contacts / heavy words masked; the original kept for admins only (`raw`). The page escapes all of it.
Id: 12 url-safe characters from secrets (72 bits): a card is found by its link only, never listed for others.

🎁 Reward (REWARD_COINS once per account, never per card): the first card written while the window is open by a
registered account (not a guest) whose character has lived MIN_LIFE_DAY days (journey.life_day) queues one system gift
(game/system_gift.py, id ev2010-u<uid>, paid into the wallet at the next game load, with its "Quà" card). The
ev2010_rewards row (uid primary key, sid unique) and the gift row are written in the card's own transaction: two tabs,
retries or many cards never pay twice. A card written before day MIN_LIFE_DAY can be claimed later ({op: 'claim'}) while
the window is open. Clone rings (owner 10/2026): REWARDS_PER_IP rewards at most per network address (a hash, never the
address), every reward logged for the admin.
Window (Vietnam time): writing and the reward until WRITE_UNTIL (21/10/2026 23:59:59), reading until READ_UNTIL (~60
days more). MNL_2010_OFF=1 stops new cards (reading stays). Limits: PER_DAY cards an account, a Vietnam day; per-minute
budgets in server.py.
Tables (game/pg_schema.py, SCHEMA_VERSION 46): new ones only (ev2010_cards, ev2010_reports, ev2010_rewards), no save key,
no FK: an older build never sees them. Account deletion empties the player's cards (the reward log stays: money paid).
"""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import re
import secrets
import time

WRITE_UNTIL = 1792601999      # 21/10/2026 23:59:59 (VN): writing and the reward close
READ_UNTIL = 1792947599       # 25/10/2026 23:59:59 (VN): owner 20/10 "thiệp giữ tới ngày 25/10 sẽ mất, công bố ra nhé"
# 📣 Owner 20/10 "ai ok thì công bố ngẫu nhiên rồi chúc mừng có xxx thiệp đã gửi tới": the season's numbers and a few
# senders picked at random among the cards kept (offensive ones and clone accounts left out), written once at the
# close (scratchpad ev2010 audit) so every page and the ticker say the same thing until READ_UNTIL.
RECAP_FROM = 1792515600       # 21/10/2026 00:00 (VN): the season closed (owner 20/10 "tối nay 0h thì chốt")
RECAP = dict(cards=922, people=723, names=('Chery', 'Cá Voi', 'Phanh', 'Mây', 'Ngoan', 'Changggg', 'Nguyệt Miêu', 'Cam'))
REWARD_COINS = 100_000        # owner 16/10: "tham gia chương trình này sẽ tặng 100k", once per account
MIN_LIFE_DAY = 3              # the character's life day (journey.life_day) a reward needs (fresh clone accounts)
NEED_ACCOUNT = True           # writing needs a registered account too (a guest is asked to sign in / register)
REWARDS_PER_IP = 5            # rewards per network address over the whole event (0: no cap); refused ones still send
PER_DAY = 20                  # cards an account writes a Vietnam day
HIDE_AFTER = 3                # reports from different readers that hide a card until an admin looks
TO_MAX, FROM_MAX = 30, 30     # names (one line)
TEXT_MIN, TEXT_MAX, TEXT_LINES = 4, 400, 10
STICKERS_MAX = 6
HEARTS_MAX = 20               # ❤ a request may add (the page batches taps); server.py caps requests per address
MINE_MAX = 40                 # my cards listed on the page
GIFT_TITLE = 'Quà thiệp 20/10 💐'
GIFT_TEXT = 'Cảm ơn bạn đã gửi thiệp 20/10. Phố tặng bạn 100.000 xu, chúc bạn một mùa thương thật ấm! 💐'
SITE = 'Phố Có Chuyện'
VN = datetime.timezone(datetime.timedelta(hours=7))
# id: name. The look lives in public/css/event2010.css (data-theme) and the art in public/js/event2010.js.
THEMES = {   # owner 16/10: "làm nhiều theme cute vào nhé"; one og:image each (scripts/build_2010_og.py)
    'hoa_hong': 'Hoa hồng', 'tulip': 'Tulip pastel', 'cuc_hoa_mi': 'Cúc họa mi', 'huong_duong': 'Hướng dương',
    'sen': 'Sen hồng', 'ao_dai': 'Áo dài xưa', 'anh_dao': 'Anh đào', 'gau_meo': 'Gấu & mèo', 'tra_sua': 'Trà sữa',
    'bong_bong': 'Bóng bay tim', 'dem_sao': 'Đêm sao', 'thu_tay': 'Thư tay', 'polaroid': 'Polaroid',
}
DIRECTIONS = ('nam_nu', 'nu_nam', 'khac')   # "Nam gửi nữ", "Nữ gửi nam", "Gửi ai cũng được": wording and decor only
STICKERS = ('🌹', '🌷', '💐', '🌸', '🌻', '💌', '💖', '💕', '🫶', '🧸', '🐱', '🐰', '🎀', '⭐', '🌙', '✨', '🦋', '🍰', '☕', '🎁')
REASONS = ('spam', 'rude', 'private', 'scam', 'other')
STATUSES = ('live', 'hidden', 'removed', 'down')   # down: the sender deleted it (its words are gone)
ID_RX = re.compile(r'[A-Za-z0-9_-]{12}')
GIFT_PREFIX = 'ev2010-u'


class EventError(Exception):
    def __init__(self, message: str, code: str = 'bad_card', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(ok, message: str, code: str = 'bad_card', status: int = 400) -> None:
    if not ok:
        raise EventError(message, code, status)


def now() -> float:
    return time.time()


def vn_day(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%Y-%m-%d')


def write_until() -> int:
    raw = (os.environ.get('MNL_2010_UNTIL') or '').strip()   # the operator may stretch the window without a release
    return int(raw) if raw.isdigit() else WRITE_UNTIL


def writing_open(t: float | None = None) -> bool:
    return (now() if t is None else t) <= write_until() and os.environ.get('MNL_2010_OFF', '').strip() in ('', '0')


def reading_open(t: float | None = None) -> bool:
    return (now() if t is None else t) <= max(READ_UNTIL, write_until())


def news_line(t: float | None = None) -> dict | None:
    """The ticker's line while writing is open (game/marriage.py news → `event`; public/js/v4/ticker.js plays it once a
    day on a device): {text, key}. The key is the VN day, so a new day's line plays again."""
    t = now() if t is None else t
    if not writing_open(t):
        line = recap_line(t)
        return dict(text=line, key='ev2010:recap:' + vn_day(t)) if line else None
    day = vn_day(t)
    text = ('💐 Hôm nay 20/10! Gửi một tấm thiệp cho người phụ nữ bạn thương: Tiện ích → Thiệp 20/10.' if day.endswith('-10-20') else
            '💐 Thiệp 20/10 mở đến hết hôm nay: tấm đầu tiên vẫn được Phố tặng 100.000 xu. Tiện ích → Thiệp 20/10.' if vn_day(write_until()) == day else
            '💐 Phố đang mùa thiệp 20/10: viết vài dòng tặng người thương, tấm đầu tiên được Phố tặng 100.000 xu. Tiện ích → Thiệp 20/10.')
    return dict(text=text, key='ev2010:' + day)


def recap_line(t: float | None = None) -> str | None:
    """After the close, until READ_UNTIL: how many cards went out, a few senders, when the cards go away."""
    t = now() if t is None else t
    if writing_open(t) or not RECAP_FROM <= t <= READ_UNTIL or not RECAP['cards']:
        return None
    n = lambda x: f'{int(x):,}'.replace(',', '.')
    names = list(RECAP['names'])
    who = f'Chúc mừng {", ".join(names)} cùng {n(max(0, RECAP["people"] - len(names)))} bạn khác. ' if names else ''
    return (f'💐 Mùa thiệp 20/10 đã khép lại: {n(RECAP["cards"])} tấm thiệp đã được gửi tới những người thương! ' + who +
            'Thiệp mở được tới hết 25/10, sau đó sẽ được cất đi.')


def ip_tag(ip: str) -> str:
    """A network address as the reward log keeps it: grouped, never stored."""
    return hashlib.sha256(('ev2010:' + str(ip or '')).encode()).hexdigest()[:16]


def valid_id(cid) -> bool:
    return isinstance(cid, str) and bool(ID_RX.fullmatch(cid))


# ---------------------------------------------------------------- the words
def _clean(text, most: int, lines: int, empty: str, long: str) -> tuple[str, str | None]:
    """(what readers see, the original when the mask changed it)."""
    from live import filters
    need(isinstance(text, str), empty)
    out = filters.clean(text, most, lines)
    if out is None:
        stripped = filters.clean(text, most * 4, lines) or ''
        need(len(stripped) <= most, long)
        need(False, empty)
    masked = filters.mask(out)
    return masked, (out if masked != out else None)


def parse(d: dict, default_from: str) -> dict:
    """The card of POST /api/2010/cards {op: 'create', theme, direction, to, from?, text, stickers?}."""
    need(isinstance(d, dict) and set(d) <= {'op', 'theme', 'direction', 'to', 'from', 'text', 'stickers'}, 'Thiệp chưa đúng, tải lại trang nhé.')
    theme, direction = d.get('theme'), d.get('direction', 'nam_nu')
    need(isinstance(theme, str) and theme in THEMES, 'Chọn một mẫu thiệp nhé.')
    need(isinstance(direction, str) and direction in DIRECTIONS, 'Chọn kiểu thiệp nhé.')
    to, to_raw = _clean(d.get('to'), TO_MAX, 1, 'Viết tên người nhận nhé.', f'Tên người nhận dài tối đa {TO_MAX} ký tự thôi.')
    sender = d.get('from')
    if not (isinstance(sender, str) and sender.strip()):
        sender = default_from or 'Một người thương'
    sender, from_raw = _clean(sender, FROM_MAX, 1, 'Viết tên của bạn nhé.', f'Tên ký dài tối đa {FROM_MAX} ký tự thôi.')
    text, text_raw = _clean(d.get('text'), TEXT_MAX, TEXT_LINES, 'Viết vài lời gửi người ấy nhé.', f'Lời nhắn dài tối đa {TEXT_MAX} ký tự thôi.')
    need(len(text) >= TEXT_MIN, f'Viết ít nhất {TEXT_MIN} ký tự nhé.')
    stickers = d.get('stickers', [])
    need(isinstance(stickers, list) and len(stickers) <= STICKERS_MAX and all(isinstance(s, str) and s in STICKERS for s in stickers)
         and len(set(stickers)) == len(stickers), f'Chọn tối đa {STICKERS_MAX} hình dán nhé.')
    raw = None
    if to_raw or from_raw or text_raw:   # admins see what was written before the mask
        raw = json.dumps(dict(to=to_raw or to, sender=from_raw or sender, text=text_raw or text), ensure_ascii=False)
    return dict(theme=theme, direction=direction, to=to, sender=sender, text=text, stickers=stickers, raw=raw)


# ---------------------------------------------------------------- who is writing
def _who(store, db, token: str | None) -> dict | None:
    """The save behind this cookie: {sid, account (uid, username, display) | None, state}. None: no game here."""
    if not isinstance(token, str) or len(token) != 64:
        return None
    sid, login = store._resolve(db, store.digest(token))
    if sid.startswith('revoked:'):
        return None
    row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    if row is None:
        return None
    acct = db.execute('SELECT uid, username, display FROM accounts WHERE sid=?', (sid,)).fetchone() if login else None
    return dict(sid=sid, account=dict(acct) if acct else None, state=store.parse_state(row['state'], sid))


def _life(state: dict) -> tuple[bool, int]:
    j = (state or {}).get('journey') or {}
    try:
        return bool(j.get('story')), int(j.get('life_day') or 0)
    except (TypeError, ValueError):
        return False, 0


def _default_from(who: dict) -> str:
    name = ' '.join(str((who.get('state') or {}).get('name') or '').split())
    if not name or name == 'Mây':   # the unnamed default (game/pg_schema.py repair_character_names)
        name = (who.get('account') or {}).get('display') or ''
    return name[:FROM_MAX]


def _paid(db, who: dict):
    a = who.get('account')
    return db.execute('SELECT uid, gift, at FROM ev2010_rewards WHERE sid=? OR uid=?',
                      (who['sid'], a['uid'] if a else -1)).fetchone()


def _reward_state(db, who: dict | None, ip: str, t: float, has_card: bool) -> dict:
    """What the page says about the 100.000 xu: paid | write | ready | days | account | ip | closed."""
    out = dict(coins=REWARD_COINS, min_life_day=MIN_LIFE_DAY)
    if who is None or not who.get('account'):
        return dict(out, state='account')
    row = _paid(db, who)
    if row:
        g = db.execute('SELECT status FROM system_gifts WHERE id=?', (row['gift'],)).fetchone()
        return dict(out, state='paid', pending=bool(g and g['status'] == 'pending'))
    if not writing_open(t):
        return dict(out, state='closed')
    story, day = _life(who['state'])
    if not story or day < MIN_LIFE_DAY:
        return dict(out, state='days', need=max(1, MIN_LIFE_DAY - day))
    if REWARDS_PER_IP and db.execute('SELECT count(*) FROM ev2010_rewards WHERE ip=?', (ip_tag(ip),)).fetchone()[0] >= REWARDS_PER_IP:
        return dict(out, state='ip')
    return dict(out, state='ready' if has_card else 'write')


def _grant(db, who: dict, ip: str, card: str, t: float) -> dict:
    """Inside the card's transaction: the reward row, then the system gift (game/system_gift.py: paid at the next load)."""
    st = _reward_state(db, who, ip, t, True)
    if st['state'] != 'ready':
        return st
    a, (_, day) = who['account'], _life(who['state'])
    tag = ip_tag(ip)
    db.execute('SELECT pg_advisory_xact_lock(7620, hashtext(?))', ('ev2010-ip:' + tag,))   # REWARDS_PER_IP holds under races
    if REWARDS_PER_IP and db.execute('SELECT count(*) FROM ev2010_rewards WHERE ip=?', (tag,)).fetchone()[0] >= REWARDS_PER_IP:
        return dict(st, state='ip')
    gid = f'{GIFT_PREFIX}{int(a["uid"])}'
    if not db.execute('INSERT INTO ev2010_rewards(uid, sid, username, card, gift, coins, life_day, ip, at) VALUES(?,?,?,?,?,?,?,?,?) '
                      'ON CONFLICT DO NOTHING', (int(a['uid']), who['sid'], a['username'], card, gid, REWARD_COINS, day, tag, t)).rowcount:
        return dict(st, state='paid', pending=True)
    db.execute("INSERT INTO system_gifts(id, sid, coins, title, text, status, created, granted_by) VALUES(?,?,?,?,?,'pending',?,?) "
               'ON CONFLICT (id) DO NOTHING', (gid, who['sid'], REWARD_COINS, GIFT_TITLE, GIFT_TEXT, t, 'event2010'))
    return dict(st, state='paid', pending=True, granted=True)


# ---------------------------------------------------------------- views
_COLS = 'id, theme, direction, to_name, from_name, text, stickers, hearts, status, at'


def view(r) -> dict:
    """A card as anyone sees it (never the sid, the account or the original words)."""
    try:
        stickers = [s for s in json.loads(r['stickers'] or '[]') if s in STICKERS][:STICKERS_MAX]
    except (TypeError, ValueError):
        stickers = []
    return dict(id=r['id'], theme=r['theme'], direction=r['direction'], to=r['to_name'], sender=r['from_name'], text=r['text'],
                stickers=stickers, hearts=int(r['hearts']), at=int(r['at']))


def _mine(db, sid: str) -> list:
    rows = db.execute(f"SELECT {_COLS} FROM ev2010_cards WHERE sid=? AND status<>'down' ORDER BY at DESC LIMIT ?", (sid, MINE_MAX)).fetchall()
    return [dict(view(r), status=r['status']) for r in rows]


def me(store, token: str | None, ip: str) -> dict:
    """GET /api/2010/me: what the writer needs. The CSRF is this device's own (the page is same-origin; a GET from
    another site cannot read the answer), like /api/bootstrap gives it to the game page."""
    t = now()
    base = dict(open=writing_open(t), until=write_until(), read_until=READ_UNTIL, now=int(t), per_day=PER_DAY, recap=recap_line(t),
                themes=list(THEMES), stickers=list(STICKERS), stickers_max=STICKERS_MAX,
                limits=dict(to=TO_MAX, sender=FROM_MAX, text=TEXT_MAX, text_min=TEXT_MIN))
    with store.connect() as db:
        who = _who(store, db, token)
        if who is None:
            return dict(base, signed=False, reward=_reward_state(db, None, ip, t, False), mine=[])
        mine = _mine(db, who['sid'])
        used = db.execute('SELECT count(*) FROM ev2010_cards WHERE sid=? AND day=?', (who['sid'], vn_day(t))).fetchone()[0]
        reward = _reward_state(db, who, ip, t, bool(mine))
    story, day = _life(who['state'])
    a = who['account']
    return dict(base, signed=bool(a), guest=not a, can_write=bool(a) or not NEED_ACCOUNT,
                account=dict(username=a['username'], display=a['display']) if a else None,
                name=_default_from(who), life_day=day, story=story, left=max(0, PER_DAY - int(used)),
                reward=reward, csrf=store.csrf(token), mine=mine)


def card(store, token: str | None, cid) -> dict:
    """GET /api/2010/card?id=: one live card (+ mine when this device wrote it)."""
    need(valid_id(cid), 'Không tìm thấy thiệp này.', 'not_found', 404)
    need(reading_open(), 'Mùa thiệp 20/10 đã qua, thiệp này đã cất đi rồi.', 'expired', 410)
    with store.connect() as db:
        r = db.execute(f'SELECT {_COLS}, sid FROM ev2010_cards WHERE id=?', (cid,)).fetchone()
        need(r is not None and r['status'] == 'live', 'Thiệp này không còn mở được nữa.', 'not_found', 404)
        who = _who(store, db, token) if token else None
    return dict(card=view(r), mine=bool(who and who['sid'] == r['sid']))


# ---------------------------------------------------------------- writing, deleting, claiming
def act(store, token: str, d: dict, ip: str) -> dict:
    """POST /api/2010/cards {op: create | delete | claim, ...}."""
    need(isinstance(d, dict) and d.get('op') in ('create', 'delete', 'claim'), 'Thao tác không hợp lệ.')
    op, t = d['op'], now()
    if op == 'delete':
        cid = d.get('id')
        need(set(d) == {'op', 'id'} and valid_id(cid), 'Không tìm thấy thiệp này.', 'not_found', 404)

        def drop(db):
            who = _who(store, db, token)
            need(who is not None, 'Tải lại trang để vào phiên chơi nhé.', 'session_missing', 401)
            # the words go; the row stays (today's count, the reward log's card id)
            n = db.execute("UPDATE ev2010_cards SET status='down', text='', raw=NULL, to_name='', from_name='', stickers='[]' "
                           "WHERE id=? AND sid=? AND status<>'down'", (cid, who['sid'])).rowcount
            need(n == 1, 'Thiệp này không phải của bạn hoặc đã xóa rồi.', 'not_found', 404)
            db.execute('DELETE FROM ev2010_reports WHERE card=?', (cid,))
            return dict(ok=True, message='Đã xóa thiệp. Link cũ sẽ không mở được nữa.')
        return store.transaction(drop)
    need(writing_open(t), 'Mùa viết thiệp 20/10 đã khép lại. Thiệp đã gửi vẫn mở được bằng link nhé 💐', 'closed', 403)
    if op == 'claim':
        need(set(d) == {'op'}, 'Thao tác không hợp lệ.')

        def claim(db):
            who = _who(store, db, token)
            need(who is not None, 'Tải lại trang để vào phiên chơi nhé.', 'session_missing', 401)
            db.execute('SELECT pg_advisory_xact_lock(7620, hashtext(?))', ('ev2010:' + who['sid'],))
            first = db.execute("SELECT id FROM ev2010_cards WHERE sid=? AND status<>'down' ORDER BY at LIMIT 1", (who['sid'],)).fetchone()
            need(first is not None, 'Gửi một tấm thiệp trước đã nhé 💌', 'no_card', 409)
            return dict(reward=_grant(db, who, ip, first['id'], t))
        return store.transaction(claim)
    with store.connect() as db:
        who = _who(store, db, token)
    need(who is not None, 'Tải lại trang để vào phiên chơi nhé.', 'session_missing', 401)
    need(who['account'] or not NEED_ACCOUNT, 'Đăng nhập tài khoản trong phố để viết thiệp nhé.', 'need_account', 403)
    c = parse(d, _default_from(who))

    def write(db):
        db.execute('SELECT pg_advisory_xact_lock(7620, hashtext(?))', ('ev2010:' + who['sid'],))   # PER_DAY holds under races
        day = vn_day(t)
        used = db.execute('SELECT count(*) FROM ev2010_cards WHERE sid=? AND day=?', (who['sid'], day)).fetchone()[0]
        need(used < PER_DAY, f'Hôm nay bạn đã gửi {PER_DAY} tấm thiệp rồi. Mai viết tiếp nhé 🌙', 'card_limit', 429)
        for _ in range(4):
            cid = secrets.token_urlsafe(9)
            if db.execute('INSERT INTO ev2010_cards(id, sid, uid, theme, direction, to_name, from_name, text, raw, stickers, at, day) '
                          'VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (id) DO NOTHING',
                          (cid, who['sid'], int(who['account']['uid']) if who['account'] else None, c['theme'], c['direction'], c['to'],
                           c['sender'], c['text'], c['raw'], json.dumps(c['stickers'], ensure_ascii=False), t, day)).rowcount:
                break
        else:
            need(False, 'Chưa gửi được, thử lại nhé.', 'retry', 503)
        r = db.execute(f'SELECT {_COLS} FROM ev2010_cards WHERE id=?', (cid,)).fetchone()
        return dict(card=view(r), path=f'/2010/c/{cid}', left=max(0, PER_DAY - int(used) - 1), reward=_grant(db, who, ip, cid, t))
    return store.transaction(write)


# ---------------------------------------------------------------- readers: ❤ and ⚑ (no game, no sign-in)
def heart(store, cid, n) -> dict:
    """POST /api/2010/heart {id, n}: n taps (1..HEARTS_MAX) the page gathered. Per-address budgets: server.py."""
    need(valid_id(cid), 'Không tìm thấy thiệp này.', 'not_found', 404)
    need(type(n) is int and 1 <= n <= HEARTS_MAX, 'Thả tim chậm lại chút nhé.')
    need(reading_open(), 'Mùa thiệp 20/10 đã qua.', 'expired', 410)
    row = store.transaction(lambda db: db.execute("UPDATE ev2010_cards SET hearts=hearts+? WHERE id=? AND status='live' RETURNING hearts",
                                                  (n, cid)).fetchone())
    need(row is not None, 'Thiệp này không còn mở được nữa.', 'not_found', 404)
    return dict(hearts=int(row['hearts']))


def report(store, token: str | None, cid, reason, ip: str) -> dict:
    """POST /api/2010/report {id, reason}: once per reader (their save, else their address); HIDE_AFTER hide it."""
    need(valid_id(cid), 'Không tìm thấy thiệp này.', 'not_found', 404)
    reason = reason if reason is not None else 'other'
    need(reason in REASONS, 'Lý do không hợp lệ.')
    t = now()

    def run(db):
        who = _who(store, db, token) if token else None
        c = db.execute('SELECT sid, status FROM ev2010_cards WHERE id=? FOR UPDATE', (cid,)).fetchone()
        need(c is not None and c['status'] == 'live', 'Thiệp này không còn mở được nữa.', 'not_found', 404)
        need(not (who and who['sid'] == c['sid']), 'Đây là thiệp của bạn mà 🙂 Muốn gỡ thì bấm Xóa thiệp nhé.', 'own')
        by = 's:' + hashlib.sha256(who['sid'].encode()).hexdigest()[:16] if who else 'ip:' + ip_tag(ip)
        if db.execute('INSERT INTO ev2010_reports(card, reporter, reason, at) VALUES(?,?,?,?) ON CONFLICT DO NOTHING', (cid, by, reason, t)).rowcount:
            db.execute("UPDATE ev2010_cards SET reports=reports+1, status=CASE WHEN reports+1>=? AND status='live' THEN 'hidden' "
                       'ELSE status END WHERE id=?', (HIDE_AFTER, cid))
        return dict(ok=True, message='Cảm ơn bạn đã báo. Ban quản lý phố sẽ xem thiệp này.')
    return store.transaction(run)


# ---------------------------------------------------------------- the page (server-side: preview tags + the card)
def _json(data) -> str:
    """JSON safe inside <script type="application/json"> (never executed; no </script> can close it)."""
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def page_data(store, cid: str | None) -> tuple[int, dict]:
    """(HTTP status, what public/2010.html embeds): the home, one card, or why a card does not open."""
    t = now()
    base = dict(open=writing_open(t), until=write_until(), read_until=READ_UNTIL, now=int(t), coins=REWARD_COINS, min_life_day=MIN_LIFE_DAY,
                recap=recap_line(t))
    if cid is None:
        return 200, dict(base, mode='home')
    if not valid_id(cid):
        return 404, dict(base, mode='gone', why='missing')
    if not reading_open(t):
        return 410, dict(base, mode='gone', why='expired')
    with store.connect() as db:
        r = db.execute(f'SELECT {_COLS} FROM ev2010_cards WHERE id=?', (cid,)).fetchone()
    if r is None or r['status'] == 'down':
        return 404, dict(base, mode='gone', why='missing')
    if r['status'] != 'live':
        return 404, dict(base, mode='gone', why='hidden')
    return 200, dict(base, mode='card', card=view(r))


def head_tags(data: dict, origin: str) -> str:
    """<title>, description, robots and Open Graph tags (escaped) for the page's preview on Facebook / Zalo."""
    e = lambda s: html.escape(str(s), quote=True)
    c = data.get('card')
    if c:
        title = f'💌 {c["sender"]} gửi {c["to"]} một tấm thiệp 20/10'
        desc = 'Có một lá thư đang chờ bạn mở. Chạm để đọc lời chúc 20/10 nhé 💐'
        image, url = f'/icons/2010/og-{c["theme"]}.png', f'/2010/c/{c["id"]}'
    else:
        title = 'Thiệp 20/10 · Gửi lời thương' if data.get('mode') == 'home' else 'Thiệp 20/10'
        desc = 'Viết một tấm thiệp 20/10 thật xinh, gửi link cho người thương. Người nhận không cần chơi game vẫn mở được 💐'
        image, url = '/icons/2010/og-hoa_hong.png', '/2010'
    tags = [f'<title>{e(title)} · {SITE}</title>', f'<meta name="description" content="{e(desc)}">',
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE}">',
            f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">',
            f'<meta property="og:url" content="{e(origin + url)}"><meta property="og:locale" content="vi_VN">',
            f'<meta property="og:image" content="{e(origin + image)}"><meta property="og:image:width" content="1200">'
            f'<meta property="og:image:height" content="630"><meta property="og:image:alt" content="{e(title)}">',
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}">'
            f'<meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(origin + image)}">']
    if data.get('mode') != 'home':
        tags.append('<meta name="robots" content="noindex,nofollow">')
    return '\n  '.join(tags)


def fallback(data: dict) -> str:
    """The card in plain HTML (escaped) for a reader without JavaScript; the page script replaces it."""
    e = lambda s: html.escape(str(s), quote=True)
    c = data.get('card')
    if c:
        body = '<br>'.join(e(line) for line in c['text'].split('\n'))
        return f'<article class="ev-plain"><p>Gửi <b>{e(c["to"])}</b>,</p><p>{body}</p><p>— {e(c["sender"])}</p></article>'
    if data.get('mode') == 'gone':
        return '<p class="ev-plain">Thiệp này không còn mở được nữa.</p>'
    return '<p class="ev-plain">Bật JavaScript để viết thiệp 20/10 nhé.</p>'


def render(template: str, data: dict, origin: str) -> str:
    """public/2010.html with its three markers filled."""
    return (template.replace('<!--ev:head-->', head_tags(data, origin), 1)
            .replace('<!--ev:plain-->', fallback(data), 1)
            .replace('<!--ev:data-->', f'<script type="application/json" id="ev-data">{_json(data)}</script>', 1))


# ---------------------------------------------------------------- admins, privacy
def admin_view(store) -> dict:
    """GET /api/admin/2010: cards reported and not looked at first, then the newest; the reward log (newest first) with
    the account's age and how many rewards share its network address (a clone ring shows up as a group)."""
    with store.connect() as db:
        q = ('SELECT c.id, c.theme, c.direction, c.to_name, c.from_name, c.text, c.raw, c.hearts, c.reports, c.status, c.at, '
             'c.reviewed_at, c.by_admin, a.username FROM ev2010_cards c LEFT JOIN accounts a ON a.sid=c.sid ')
        rows = db.execute(f"({q} WHERE c.reports>0 AND c.reviewed_at IS NULL AND c.status<>'down' ORDER BY c.at DESC LIMIT 100) UNION ALL "
                          f"({q} WHERE NOT (c.reports>0 AND c.reviewed_at IS NULL) AND c.status<>'down' ORDER BY c.at DESC LIMIT 80)").fetchall()
        reasons = {}
        ids = [r['id'] for r in rows if r['reports']]
        if ids:
            for x in db.execute('SELECT card, reason, count(*) AS n FROM ev2010_reports WHERE card=ANY(?) GROUP BY card, reason', (ids,)):
                reasons.setdefault(x['card'], {})[x['reason']] = int(x['n'])
        rewards = db.execute('SELECT r.uid, r.username, r.card, r.gift, r.coins, r.life_day, r.ip, r.at, a.created_at, g.status AS gift_status, '
                             '(SELECT count(*) FROM ev2010_rewards x WHERE x.ip=r.ip) AS same_ip FROM ev2010_rewards r '
                             'LEFT JOIN accounts a ON a.uid=r.uid LEFT JOIN system_gifts g ON g.id=r.gift ORDER BY r.at DESC LIMIT 300').fetchall()
        total = db.execute("SELECT count(*) AS n, count(DISTINCT sid) AS people, COALESCE(sum(hearts), 0) AS hearts FROM ev2010_cards "
                           "WHERE status<>'down'").fetchone()
        paid = db.execute('SELECT count(*) AS n, COALESCE(sum(coins), 0) AS coins FROM ev2010_rewards').fetchone()
    return dict(open=writing_open(), until=write_until(), read_until=READ_UNTIL, coins=REWARD_COINS, min_life_day=MIN_LIFE_DAY,
                per_ip=REWARDS_PER_IP, per_day=PER_DAY,
                totals=dict(cards=int(total['n']), people=int(total['people']), hearts=int(total['hearts']),
                            rewards=int(paid['n']), coins=int(paid['coins'])),
                items=[dict(id=r['id'], theme=r['theme'], theme_name=THEMES.get(r['theme'], r['theme']), direction=r['direction'],
                            to=r['to_name'], sender=r['from_name'], text=r['text'], raw=r['raw'], hearts=int(r['hearts']),
                            reports=int(r['reports']), reasons=reasons.get(r['id'], {}), status=r['status'], at=float(r['at']),
                            username=r['username'] or '', reviewed=r['reviewed_at'] is not None, by=r['by_admin'] or '') for r in rows],
                rewards=[dict(uid=int(r['uid']), username=r['username'] or '', card=r['card'], coins=int(r['coins']),
                              life_day=int(r['life_day']), ip=r['ip'], same_ip=int(r['same_ip']), at=float(r['at']),
                              account_created=r['created_at'] or '', gift=r['gift_status'] or 'gone') for r in rewards])


def admin_act(store, admin: str, d: dict) -> dict:
    """POST /api/admin/2010 {act: hide | show, id}: hide = 'removed' (the link stops opening); show = live again
    (a card its sender deleted stays deleted)."""
    cid = d.get('id') if isinstance(d, dict) else None
    need(isinstance(d, dict) and set(d) == {'act', 'id'} and d.get('act') in ('hide', 'show') and valid_id(cid), 'Thao tác không hợp lệ.', 'bad_admin')
    status = 'removed' if d['act'] == 'hide' else 'live'
    n = store.transaction(lambda db: db.execute("UPDATE ev2010_cards SET status=?, reviewed_at=?, by_admin=? WHERE id=? AND status<>'down'",
                                                (status, now(), str(admin)[:40], cid)).rowcount)
    return dict(ok=True, changed=bool(n), status=status)


def forget(store, token: str) -> None:
    """Account deletion ("XOA"): this player's cards and the reports on them. The reward log stays (money paid)."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM ev2010_reports WHERE card IN (SELECT id FROM ev2010_cards WHERE sid=?)', (sid,))
        db.execute('DELETE FROM ev2010_cards WHERE sid=?', (sid,))
    store.transaction(run)
