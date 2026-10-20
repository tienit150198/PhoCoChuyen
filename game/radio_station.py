"""📻 Đài phát thanh Sóng Mây for players (owner 21/10 "làm hết đi"): a radio player sells airtime on the town ticker.

Two services in 🛎️ Phố dịch vụ (game/service_market.py: ordering, negotiation, escrow, the 95/5 split, refunds, anti-laundering):
* 📢 quang_cao: a short ad line for the buyer's shop (anyone with a workplace or a quầy), on the ticker for AD_MINUTES.
* 🎵 tang_bai: a song from the station's library with a message for someone dear, read by a DJ (the radio player past probation),
  on the ticker for SONG_MINUTES.
Default price: the NPC base (BASE) × 3, the provider's ×1–×10 or 🤝 thương lượng; 95 % to the DJ's wallet, 5 % burned.

The flow: the buyer writes the line in the order's note (moderated at once, before any money moves: note_check); the DJ opens
📻 Đơn lên sóng at the station (public/js/v4/radio.js, GET /api/radio/desk), reads the line, picks the background music or the
song and taps 🔴 Lên sóng (POST /api/radio/air): the order is taken if it was not, then delivered (service_market.deliver) with
{pick, ok}: the deliver hook below moderates again, checks the caps and writes the line into radio_lines in the same transaction
that marks the work done; 'auto' confirm: the DJ is paid there and then. A delivery without the DJ's reading (the generic
"Xong việc" button) is refused and the order stays open.

Moderation (public text on everybody's screen): live/filters.py clean (one line, no control or invisible characters), at most
TEXT_MAX characters, at least TEXT_MIN; refused when the chat mask would change it (links, e-mails, @handles, contact ids, phone or
bank numbers, heavy words) or when it holds a word of social.BANNED. Nothing is masked into the ticker: a refused line never airs.

Bounds (so the ticker is never a wall of ads): at most LIVE_MAX lines on air at once in the whole town (both services), at most
BUYER_DAY lines a buyer a Vietnam day (orders still open count too), at most DJ_DAY lines a DJ a Vietnam day. The DB request is
serialised by an advisory lock so two DJs cannot both take the last slot. The ticker (marriage.news → `radio`) reads the live lines
once per CACHE_S per store (one small dict, at most CACHE_STORES entries); an older page ignores the key.

Taking a line down: its buyer, its DJ or an admin (GET/POST /api/admin/radio) hides it; nothing is refunded (it aired), nothing
is deleted. A deleted account's lines are hidden (forget).

🛑 MNL_RADIO_OFF=1: no new orders, no deliveries, nothing on the ticker; open orders wait (the buyer may cancel for a full refund,
or the market refunds them after their hours). The career itself (game/careers/radio.py) keeps working.

Table (game/pg_schema.py SCHEMA_VERSION 70): radio_lines. No save key.
"""
from __future__ import annotations

import os
import re
import secrets
import threading
import time

from . import marriage as mr

CAREER = 'radio'
AD, SONG = 'quang_cao', 'tang_bai'
KINDS = (AD, SONG)
BASE = {AD: 500, SONG: 200}           # NPC price of one airing, xu (the market asks × 3 by default)
AD_MINUTES, SONG_MINUTES = 60, 30     # how long a line stays on the ticker
MINUTES = {AD: AD_MINUTES, SONG: SONG_MINUTES}
TEXT_MIN, TEXT_MAX = 6, 120           # the buyer's words
LINE_MAX = 200                        # the whole ticker line (the news text limit)
LIVE_MAX = 4                          # lines on air at once, whole town
BUYER_DAY = 2                         # lines a buyer may put on air a Vietnam day (open orders count)
DJ_DAY = 12                           # lines one DJ airs a Vietnam day
REPLAY_S = 480                        # a device replays a live line at most this often (public/js/v4/ticker.js)
CACHE_S = 10.0
CACHE_STORES = 4
MINE_MAX = 20
ADMIN_MAX = 100
BEDS = [('vui', 'Nhạc nền vui tươi'), ('em', 'Nhạc nền êm dịu'), ('ron', 'Nhạc nền rộn ràng'), ('none', 'Không nhạc nền, đọc rõ từng chữ')]
OPEN = ('talk', 'held', 'working', 'delivered', 'ready')
ID_RX = re.compile(r'rl_[0-9a-f]{20}')


class RadioError(mr.MarriageError):
    """A refusal shown as is (the server answers a MarriageError with its status and code)."""


def need(cond, message: str, code: str = 'radio_error', status: int = 400):
    if not cond:
        raise RadioError(message, code, status)


def off() -> bool:
    return os.environ.get('MNL_RADIO_OFF', '').strip() in ('1', 'true', 'yes', 'on')


def now() -> float:
    return time.time()


def today(t: float | None = None) -> str:
    from .wedding_live import vn_day
    return vn_day(now() if t is None else t)


def songs() -> list:
    """The station's library that may air (game/careers/radio_content.py SONGS): [(id, title, artist)]."""
    from .careers.radio_content import SONGS
    return [(s[0], s[1], s[2]) for s in SONGS if s[6]]


def _song(pick: str):
    return next((s for s in songs() if s[0] == pick), None)


def picks(kind: str) -> list:
    return [dict(id=k, label=v) for k, v in BEDS] if kind == AD else [dict(id=s[0], label=f'{s[1]} · {s[2]}') for s in songs()]


# ---------------------------------------------------------------- moderation
def moderate(text) -> tuple[str, str]:
    """(the line as it will air, '') or ('', why it cannot air). Never masks: a line that needs a mask is refused."""
    from live import filters
    from . import social
    if not isinstance(text, str) or not text.strip():
        return '', 'Viết lời lên sóng vào ô lời nhắn nhé.'
    out = filters.clean(text, TEXT_MAX, 1)
    if out is None:
        long = filters.clean(text, TEXT_MAX * 4, 1)
        return '', (f'Lời lên sóng dài tối đa {TEXT_MAX} ký tự thôi nhé.' if long and len(long) > TEXT_MAX else 'Viết lời lên sóng vào ô lời nhắn nhé.')
    if len(out) < TEXT_MIN:
        return '', f'Lời lên sóng cần ít nhất {TEXT_MIN} ký tự.'
    if '•••' in out or filters.mask(out) != out:
        return '', 'Lời lên sóng không được có đường link, số điện thoại, tài khoản liên hệ hay từ tục.'
    for word in social.BANNED:
        if re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)', out, re.I):
            return '', 'Lời lên sóng không được có từ tục hay lời xúc phạm.'
    return out, ''


def note_check(note) -> str:
    """service_market spec hook, before any money moves: '' or why this note cannot air."""
    if off():
        return 'Đài Sóng Mây đang tạm nghỉ nhận đơn lên sóng.'
    return moderate(note)[1]


# ---------------------------------------------------------------- the caps
def _lock(db) -> None:
    db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('radio-live',))


def live_count(db, t: float) -> int:
    return int(db.execute('SELECT COUNT(*) AS n FROM radio_lines WHERE hidden=0 AND end_at>? AND start_at<=?', (t, t)).fetchone()['n'] or 0)


def buyer_today(db, buyer: str, t: float) -> int:
    """Lines this buyer aired today plus their radio orders still open (both kinds): the BUYER_DAY cap."""
    aired = db.execute('SELECT COUNT(*) AS n FROM radio_lines WHERE buyer=? AND day=?', (buyer, today(t))).fetchone()['n']
    marks = ','.join('?' * len(OPEN))
    waiting = db.execute(f"SELECT COUNT(*) AS n FROM svc_orders WHERE buyer=? AND career=? AND kind='svc' AND status IN ({marks})",
                         (buyer, CAREER, *OPEN)).fetchone()['n']
    return int(aired or 0) + int(waiting or 0)


def dj_today(db, dj: str, t: float) -> int:
    return int(db.execute('SELECT COUNT(*) AS n FROM radio_lines WHERE provider=? AND day=?', (dj, today(t))).fetchone()['n'] or 0)


def _has_place(db, sid: str) -> bool:
    return bool(db.execute('SELECT 1 FROM work_visit_places WHERE owner=? LIMIT 1', (sid,)).fetchone())


def _check(kind):
    def check(db, buyer, state):
        if off():
            return 'Đài Sóng Mây đang tạm nghỉ nhận đơn lên sóng.'
        if kind == AD and not _has_place(db, buyer):
            return 'Quảng cáo dành cho người có tiệm, quầy hoặc chỗ làm. Vào làm một nghề trước nhé.'
        if buyer_today(db, buyer, now()) >= BUYER_DAY:
            return f'Mỗi ngày bạn gửi lên sóng tối đa {BUYER_DAY} lượt (kể cả đơn đang chờ). Mai gửi tiếp nhé.'
        return ''
    return check


def _can(kind):
    def can(state):
        c = (state.get('careers') or {}).get(CAREER)
        if not (isinstance(c, dict) and c.get('started')):
            return 'Bạn cần làm ở Đài phát thanh Sóng Mây trước đã.'
        if kind == SONG and not ((c.get('ext') or {}).get('data') or {}).get('promoted'):
            return 'Gửi bài hát tặng cần DJ: làm phát thanh viên hết thử việc trước đã.'
        return ''
    return can


# ---------------------------------------------------------------- the deliver hook (inside the market's transaction)
def _name(db, sid: str) -> str:
    from . import work_visits
    return str(work_visits._person(db, sid).get('name') or 'Một người chơi')[:40]


def _shop(db, sid: str) -> str:
    """The buyer's shop name: their most recently updated place, else their display name."""
    import json
    r = db.execute('SELECT data FROM work_visit_places WHERE owner=? ORDER BY updated_at DESC LIMIT 1', (sid,)).fetchone()
    try:
        name = (json.loads(r['data']) if r and r['data'] else {}).get('name')
    except (TypeError, ValueError):
        name = None
    return str(name or _name(db, sid))[:40]


def line_text(kind: str, who: str, dj: str, text: str, pick: str) -> str:
    if kind == AD:
        out = f'📢 {who}: {text} · 📻 Sóng Mây'
    else:
        s = _song(pick)
        out = f'🎵 {who} gửi tặng bài “{s[1] if s else "Sóng Mây"}” qua DJ {dj}: “{text}”'
    return out[:LINE_MAX]


def _deliver(kind):
    def deliver(db, provider, buyer, order):
        from .service_market import ServiceError
        if off():
            raise ServiceError('Đài Sóng Mây đang tạm nghỉ lên sóng.', 'radio_off', 409)
        got = order.get('input') if isinstance(order.get('input'), dict) else None
        if not got or got.get('ok') is not True:
            raise ServiceError('Mở 📻 Đơn lên sóng ở Đài Sóng Mây để duyệt lời và lên sóng đơn này.', 'radio_desk', 409)
        pick = got.get('pick')
        ids = [p['id'] for p in picks(kind)]
        if pick not in ids:
            raise ServiceError('Chọn nhạc nền hoặc bài hát trước khi lên sóng nhé.', 'radio_pick')
        text, why = moderate(order.get('note'))
        if why:
            raise ServiceError(why + ' Từ chối đơn để hoàn tiền cho khách nhé.', 'radio_text')
        t = now()
        _lock(db)
        old = db.execute('SELECT * FROM radio_lines WHERE order_id=?', (order['id'],)).fetchone()
        if old:
            return dict(line=old['text'], slot=_slot(old['start_at'], old['end_at']))
        if live_count(db, t) >= LIVE_MAX:
            raise ServiceError(f'Bảng tin cả phố đang đủ {LIVE_MAX} dòng. Chờ ít phút có dòng hết giờ rồi lên sóng nhé.', 'radio_full', 409)
        if dj_today(db, provider, t) >= DJ_DAY:
            raise ServiceError(f'Hôm nay bạn đã lên sóng {DJ_DAY} lượt rồi. Mai lên tiếp nhé.', 'radio_dj_day', 409)
        aired = int(db.execute('SELECT COUNT(*) AS n FROM radio_lines WHERE buyer=? AND day=?', (buyer, today(t))).fetchone()['n'] or 0)
        if aired >= BUYER_DAY:
            raise ServiceError(f'Hôm nay khách này đã có {BUYER_DAY} lượt lên sóng. Mai lên sóng tiếp nhé.', 'radio_buyer_day', 409)
        who = _shop(db, buyer) if kind == AD else _name(db, buyer)
        line = line_text(kind, who, _name(db, provider), text, pick)
        end = t + MINUTES[kind] * 60
        db.execute('INSERT INTO radio_lines(id,order_id,kind,buyer,provider,text,note,pick,day,start_at,end_at,created_at) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(order_id) DO NOTHING',
                   ('rl_' + secrets.token_hex(10), order['id'], kind, buyer, provider, line, text, pick, today(t), t, end, t))
        stale()
        return dict(line=line, slot=_slot(t, end))
    return deliver


def _slot(a: float, b: float) -> str:
    from .wedding_live import vn
    return f'Lên sóng {vn(a).strftime("%H:%M")}–{vn(b).strftime("%H:%M")}'


SPECS = {
    AD: dict(name='Quảng cáo tiệm trên sóng', icon='📢', base=BASE[AD], unit='lượt',
             desc=f'Một dòng quảng cáo chạy trên bảng tin cả phố {AD_MINUTES} phút', duration=AD_MINUTES, work_hours=24,
             note_hint=f'Lời quảng cáo, tối đa {TEXT_MAX} ký tự, không link hay số điện thoại'),
    SONG: dict(name='Gửi bài hát tặng người thương', icon='🎵', base=BASE[SONG], unit='lượt',
               desc=f'DJ mở một bài và đọc lời nhắn của bạn trên bảng tin cả phố {SONG_MINUTES} phút', duration=SONG_MINUTES, work_hours=24,
               note_hint='Gửi ai, lời nhắn gì, muốn bài kiểu nào'),
}
_installed = [False]


def install() -> bool:
    """Register both services with the market (server start, and the first use in any process). True when registered."""
    from . import service_market as sm
    for kind, spec in SPECS.items():
        sm.register(CAREER, kind, dict(spec, deliver=_deliver(kind), check=_check(kind), can_provide=_can(kind), note_check=note_check,
                                       requires=dict(story=True)))
    _installed[0] = True
    return True


def _ensure() -> None:
    if not _installed[0]:
        install()


# ---------------------------------------------------------------- the ticker (marriage.news → `radio`)
_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()


def stale() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def ticker(store) -> list:
    """The lines on air now, oldest first, at most LIVE_MAX: [{id, text, until, replay}]. Cached CACHE_S per store."""
    if off():
        return []
    t, key = now(), str(getattr(store, 'path', ''))
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and 0 <= t - hit[0] < CACHE_S:
            return [dict(x) for x in hit[1] if x['until'] > t]
    try:
        with store.connect() as db:
            rows = db.execute('SELECT id, text, end_at FROM radio_lines WHERE hidden=0 AND end_at>? AND start_at<=? '
                              'ORDER BY start_at, id LIMIT ?', (t, t, LIVE_MAX)).fetchall()
        out = [dict(id=r['id'], text=str(r['text'])[:LINE_MAX], until=int(r['end_at']), replay=REPLAY_S) for r in rows]
    except Exception:  # noqa: BLE001 - a database before SCHEMA_VERSION 70, a hiccup: the ticker never fails for this
        out = []
    with _CACHE_LOCK:
        if len(_CACHE) >= CACHE_STORES and key not in _CACHE:
            _CACHE.clear()
        _CACHE[key] = (t, out)
    return [dict(x) for x in out]


# ---------------------------------------------------------------- HTTP: /api/radio/<sub>
def _actor(store, token) -> str:
    sid = store.key(token)
    with store.connect() as db:
        need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone(), 'Đăng nhập để dùng Đài Sóng Mây.', 'login_required', 401)
    return sid


def _line_view(db, r: dict, me: str, t: float) -> dict:
    role = 'buyer' if r['buyer'] == me else 'dj' if r['provider'] == me else ''
    return dict(id=r['id'], kind=r['kind'], text=r['text'], live=bool(not r['hidden'] and r['start_at'] <= t < r['end_at']),
                hidden=bool(r['hidden']), hidden_by=r['hidden_by'], start=int(r['start_at']), until=int(r['end_at']),
                slot=_slot(r['start_at'], r['end_at']), role=role, can_hide=bool(role) and not r['hidden'] and r['end_at'] > t)


def desk(store, sid: str) -> dict:
    """The DJ's sheet: radio orders waiting (with the moderation preview), what is on air, today's caps, my own lines."""
    from . import service_market as sm
    _ensure()
    t = now()
    sm.settle_for(store, sid)
    with store.connect() as db:
        orders = []
        for o in sm.open_orders(db, sid, CAREER):
            if o['service'] not in KINDS:
                continue
            text, why = moderate(o['note'])
            orders.append(dict(id=o['id'], kind=o['service'], status=o['status'], price=o['price'], note=o['note'], text=text, why=why,
                               who=_name(db, o['buyer']), picks=picks(o['service']), minutes=MINUTES[o['service']],
                               preview=line_text(o['service'], _shop(db, o['buyer']) if o['service'] == AD else _name(db, o['buyer']),
                                                 _name(db, sid), text, picks(o['service'])[0]['id']) if text else ''))
        live = [_line_view(db, dict(r), sid, t) for r in db.execute(
            'SELECT * FROM radio_lines WHERE hidden=0 AND end_at>? AND start_at<=? ORDER BY start_at, id LIMIT ?', (t, t, LIVE_MAX)).fetchall()]
        mine = [_line_view(db, dict(r), sid, t) for r in db.execute(
            'SELECT * FROM radio_lines WHERE buyer=? OR provider=? ORDER BY created_at DESC, id LIMIT ?', (sid, sid, MINE_MAX)).fetchall()]
        caps = dict(live=live_count(db, t), live_max=LIVE_MAX, dj=dj_today(db, sid, t), dj_max=DJ_DAY, buyer=buyer_today(db, sid, t),
                    buyer_max=BUYER_DAY, minutes={AD: AD_MINUTES, SONG: SONG_MINUTES}, text_max=TEXT_MAX)
    return dict(off=off(), orders=orders, live=live, mine=mine, caps=caps, base=BASE)


def get(store, token, state, sub: str, query: dict) -> dict:
    sid = _actor(store, token)
    if sub == 'desk':
        return desk(store, sid)
    if sub == 'mine':
        t = now()
        with store.connect() as db:
            rows = db.execute('SELECT * FROM radio_lines WHERE buyer=? OR provider=? ORDER BY created_at DESC, id LIMIT ?', (sid, sid, MINE_MAX)).fetchall()
            return dict(off=off(), mine=[_line_view(db, dict(r), sid, t) for r in rows])
    raise RadioError('Không có mục này.', 'not_found', 404)


def air(store, token, sid: str, data: dict, ip: str = '') -> dict:
    """🔴 Lên sóng: take the order if it is still waiting, then deliver it with the DJ's pick (the deliver hook airs it)."""
    from . import service_market as sm
    _ensure()
    need(not off(), 'Đài Sóng Mây đang tạm nghỉ lên sóng.', 'radio_off', 409)
    need(set(data) <= {'order', 'pick', 'ok'}, 'Thông tin lên sóng không hợp lệ.')
    oid = data.get('order')
    need(isinstance(oid, str) and sm.ID_RX.fullmatch(oid), 'Không tìm thấy đơn.', 'not_found', 404)
    need(data.get('ok') is True, 'Đọc kỹ lời lên sóng rồi đánh dấu đã duyệt nhé.', 'radio_ok')
    with store.connect() as db:
        o = sm.order_of(db, oid)
    need(o and o['provider'] == sid and o['career'] == CAREER and o['service'] in KINDS, 'Không tìm thấy đơn.', 'not_found', 404)
    need(data.get('pick') in [p['id'] for p in picks(o['service'])], 'Chọn nhạc nền hoặc bài hát trước khi lên sóng nhé.', 'radio_pick')
    if o['status'] == 'held':
        sm.post(store, token, None, 'take', {'order': oid}, ip=ip)
    view = sm.deliver(store, sid, oid, dict(pick=data['pick'], ok=True))
    stale()
    aired = view['status'] in ('ready', 'done')
    return dict(order=view, changed=aired, message=('🔴 Đã lên sóng! Dòng chữ đang chạy trên bảng tin cả phố.' if aired else 'Đơn chưa lên sóng được.'))


def hide(store, sid: str, data: dict, by: str = '') -> dict:
    """Take a line off the ticker: its buyer, its DJ (by=''), or an admin (by='admin'). Never refunded, never deleted."""
    need(set(data) <= {'line', 'op', 'note'}, 'Thông tin không hợp lệ.')
    lid = data.get('line')
    need(isinstance(lid, str) and ID_RX.fullmatch(lid), 'Không tìm thấy dòng này.', 'not_found', 404)
    show = by == 'admin' and data.get('op') == 'show'

    def run(db):
        r = db.execute('SELECT * FROM radio_lines WHERE id=? FOR UPDATE', (lid,)).fetchone()
        need(r, 'Không tìm thấy dòng này.', 'not_found', 404)
        who = 'admin' if by == 'admin' else 'buyer' if r['buyer'] == sid else 'dj' if r['provider'] == sid else ''
        need(who, 'Không tìm thấy dòng này.', 'not_found', 404)
        if show:
            db.execute("UPDATE radio_lines SET hidden=0, hidden_by='', hidden_at=NULL WHERE id=?", (lid,))
        elif not r['hidden']:
            db.execute('UPDATE radio_lines SET hidden=1, hidden_by=?, hidden_at=? WHERE id=?', (who, now(), lid))
        return True
    store.transaction(run)
    stale()
    return dict(changed=True, message='Đã hiện lại dòng này.' if show else 'Đã gỡ dòng này khỏi bảng tin.')


def post(store, token, state, sub: str, data: dict, ip: str = '') -> dict:
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Dữ liệu không hợp lệ.')
    if sub == 'air':
        return air(store, token, sid, data, ip)
    if sub == 'hide':
        return hide(store, sid, data)
    raise RadioError('Thao tác không hợp lệ.', 'unknown_action')


# ---------------------------------------------------------------- admin, account deletion
def admin_view(store) -> dict:
    t = now()
    with store.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM radio_lines ORDER BY created_at DESC, id LIMIT ?', (ADMIN_MAX,)).fetchall()]
        out = []
        for r in rows:
            v = _line_view(db, r, '', t)
            v.update(buyer=_name(db, r['buyer']), dj=_name(db, r['provider']), note=r['note'], order=r['order_id'])
            out.append(v)
        totals = dict(lines=int(db.execute('SELECT COUNT(*) AS n FROM radio_lines').fetchone()['n'] or 0), live=live_count(db, t))
    return dict(off=off(), lines=out, totals=totals, caps=dict(live_max=LIVE_MAX, buyer_day=BUYER_DAY, dj_day=DJ_DAY))


def admin_act(store, admin: str, data: dict) -> dict:
    need(isinstance(data, dict) and data.get('op') in ('hide', 'show'), 'Thao tác không hợp lệ.')
    return hide(store, admin, data, by='admin')


def forget(store, token: str) -> None:
    """A deleted account: its lines leave the ticker (hidden, kept)."""
    sid = store.key(token)
    try:
        store.transaction(lambda db: db.execute("UPDATE radio_lines SET hidden=1, hidden_by='gone', hidden_at=? WHERE hidden=0 AND (buyer=? OR provider=?)",
                                                (now(), sid, sid)))
    except Exception:  # noqa: BLE001 - a database before SCHEMA_VERSION 70
        pass
    stale()
