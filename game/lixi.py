"""🧧 Lì xì: phát và giật lì xì (owner 16/10: "cho phép người ta phát lì xì và giật lì xì, tiền ngẫu nhiên, phát ở trên
màn hình hoặc chat gì đó nhé … check kĩ nhé, có cả map cũ và mới nhé"). The richest players hold tens of millions of xu;
this is something to spend them on that everyone online enjoys. Story mode.

* 🧧 Phát (jr_lixi_give {total, n, wish?, text?, confirm}): TOTAL_MIN → TOTAL_MAX xu in N_MIN → N_MAX envelopes, each
  at least ENV_MIN xu, with a wish from WISHES (or a short line of one's own, through the chat's cleaner and mask:
  live/filters.py). Paid from the wallet, then the bank account (never a loan, never with a wallet in debt; wallet rows
  of kind 'life', bank log rows: no closed list grows). command_commit (game/storage.py, the save's own transaction)
  writes the `lixi_packets` row: a refusal there (no account, GAP seconds since the giver's last packet, DAY_MAX packets
  this Vietnam day, OPEN_MAX packets open on the street) rolls the whole command back, so nothing is paid. On commit a
  NOTIFY op 'lixi' that the live service (live/lixi.py) sends to every open page: envelopes fall over the screen (both
  interfaces) and a card sits in Cả phố (public/js/v4/lixi.js, lixi-cards.js) for HOURS or until the last envelope.
  A big packet (NEWS_FROM xu) also gets a line on the street's ticker.
* ✋ Giật (POST /api/lixi/grab {id}): first come, first served, one envelope per player per packet, never the giver's
  own. Under the packet's row lock (FOR UPDATE) the amount is drawn then (WeChat's "twice the mean of what is left":
  uniform in [ENV_MIN, min(2 × left_xu / left_n, left_xu − ENV_MIN × (left_n − 1))]; the last envelope takes the rest),
  so the envelopes always add up to the total exactly and none is under ENV_MIN. The grab row, the packet's new
  remainder and a `live_effects` row of kind 'lixi' (id lixi:<packet>:<pid>) are one transaction; game/live_effects.py
  pays that row into the grabber's wallet once (its request id and the save's own list of paid rows), at once (the
  route calls on_load) or at the next load. Two taps on the last envelope: the second waits for the lock and finds it
  empty. A second tap on the same packet answers the first amount again.
* 🛡️ Not a pipe between one's own accounts: a grabber needs a registered account ACCOUNT_DAYS old and a save at life day
  LIFE_DAYS (game/quay_hire.py's rules), must not have blocked or be blocked by the giver (`blocks` by pid,
  `marriage_blocks` by sid), opens at most GRAB_DAY envelopes and GRAB_DAY_XU xu a Vietnam day (an envelope is cut to
  what is left of that and the cut part stays with the giver), PAIR_DAY packets of the same giver a day, and one
  envelope per network address per packet (ONE_PER_IP; a hash of the address, never the address).
* ⏳ 24 h: an envelope nobody took goes back to the giver (sweep, housekeeping every 30 s and on the page: under the row
  lock, only from 'open', the refund row 'lixi:<packet>:back' is written once whatever the workers). The same happens at
  once when the last envelope was cut by a grabber's cap.
* 📜 GET /api/lixi: the last HOURS of packets (cached ~2 s), mine (what I grabbed), my caps today; ?id= one packet with
  "ai giật được bao nhiêu" (🏆 Hên nhất once it is finished). GET /api/admin/lixi: the operator's list.

No key in any save: only wallet rows (kind 'life'), bank log rows and the paid-row hashes game/live_effects.py already
keeps. An older build (2.4.27 →) loads every save this writes; it leaves 'lixi' rows pending (they wait for this build)
and refuses jr_lixi_give as an unknown action. Tables: lixi_packets, lixi_grabs (game/pg_schema.py, SCHEMA_VERSION 51).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time

from . import bank as bk
from . import marriage as mr
from . import quay_hire as qh

TOTAL_MIN, TOTAL_MAX = 10_000, 10_000_000
N_MIN, N_MAX = 1, 100
ENV_MIN = 100                 # xu an envelope holds at least
HOURS = 24                    # a packet waits this long, then what is left goes back to the giver
GAP = 60                      # seconds between two packets of one giver
DAY_MAX = 10                  # packets a giver sends a Vietnam day
OPEN_MAX = 40                 # packets open at once on the whole street
ACCOUNT_DAYS = qh.ACCOUNT_DAYS   # a grabber's account is this many real days old (3)
LIFE_DAYS = qh.LIFE_DAYS         # a grabber's save has lived this many days (10)
GRAB_DAY = 20                 # envelopes a player opens a Vietnam day
GRAB_DAY_XU = 300_000         # xu a player gets from envelopes a Vietnam day
PAIR_DAY = 3                  # packets of one giver a player opens a Vietnam day
ONE_PER_IP = os.environ.get('LIXI_ONE_PER_IP', '1') != '0'   # one envelope per network address per packet
NEWS_FROM = 500_000           # a packet from this total gets a line on the ticker
TEXT_MAX = 40                 # a giver's own line
KIND = 'life'                 # wallet history kind (journey.HISTORY_KINDS): every build knows it
FX = 'lixi'                   # live_effects kind (game/live_effects.py PAYS)
LIST_MAX = 30                 # packets GET /api/lixi lists
DAY = 86400
GONE = 'Một người chơi'
COMMANDS = ('jr_lixi_give',)
STATUSES = ('open', 'done', 'expired', 'gone')
WISHES = (
    ('an_khang', 'An khang thịnh vượng'),
    ('van_su', 'Vạn sự như ý'),
    ('phat_tai', 'Phát tài phát lộc'),
    ('suc_khoe', 'Sức khỏe dồi dào'),
    ('hoc_hanh', 'Học hành tấn tới'),
    ('cong_viec', 'Công việc hanh thông'),
    ('tinh_duyen', 'Tình duyên phơi phới'),
    ('lay_hen', 'Lấy hên nha cả phố!'),
)
WISH = dict(WISHES)
PK_RE = re.compile(r'lx[0-9a-f]{14}')
PID_RE = re.compile(r'[0-9a-f]{16}')


class LixiError(mr.MarriageError):
    """A refusal shown as is (server.py answers it like Hôn nhân's)."""


def need(cond, message: str, code: str = 'lixi_error', status: int = 400):
    if not cond:
        raise LixiError(message, code, status)


def now() -> float:
    return time.time()


def vn_day(t: float | None = None) -> str:
    return time.strftime('%Y-%m-%d', time.gmtime((now() if t is None else t) + 7 * 3600))


def fmt(n: int) -> str:
    return bk._fmt(n)


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def valid_pk(v) -> bool:
    return isinstance(v, str) and PK_RE.fullmatch(v) is not None


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


# ---------------------------------------------------------------- the split
def split(left_xu: int, left_n: int, rng=None) -> int:
    """One envelope out of `left_xu` xu still in `left_n` envelopes (left_xu ≥ ENV_MIN × left_n): the last takes the
    rest; otherwise uniform in [ENV_MIN, min(2 × mean, what leaves ENV_MIN for every other envelope)]."""
    left_xu, left_n = int(left_xu), int(left_n)
    if left_n <= 1:
        return left_xu
    hi = min(2 * left_xu // left_n, left_xu - ENV_MIN * (left_n - 1))
    hi = max(ENV_MIN, hi)
    r = rng or secrets.SystemRandom()
    return r.randint(ENV_MIN, hi)


# ---------------------------------------------------------------- the giver's command (reducer)
def clean_line(text) -> tuple[str, str]:
    """A giver's own line: (what players see, the original when the mask changed it, else ''). '' when none."""
    if text in (None, ''):
        return '', ''
    from live import filters
    e = _core()
    e.need(isinstance(text, str), 'Lời chúc không hợp lệ.')
    out = filters.clean(text, TEXT_MAX, 1)
    e.need(out is not None, f'Lời chúc dài tối đa {TEXT_MAX} ký tự thôi nhé.', 'bad_text')
    masked = filters.mask(out)
    return masked, (out if masked != out else '')


def _have(s: dict) -> int:
    j = s['journey']
    b = bk.get(s)
    return max(0, j['wallet']) + (b['balance'] if b else 0)


def ready_why(s: dict, amount: int) -> str:
    j = s['journey']
    if j['wallet'] < 0:
        return f'Ví đang nợ {fmt(-j["wallet"])} xu. Trả nợ trước nhé.'
    short = amount - _have(s)
    return f'Còn thiếu {fmt(short)} xu.' if short > 0 else ''


def _take(s: dict, amount: int, label: str) -> str:
    """`amount` from the wallet first, then the bank account (checked by the caller). Where it came from."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, KIND, label[:120])
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label[:120], -rest)
    if rest and cash:
        return f'{fmt(cash)} xu tiền mặt và {fmt(rest)} xu từ tài khoản'
    return f'{fmt(amount)} xu từ tài khoản' if rest else f'{fmt(amount)} xu tiền mặt'


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need_ = e.need
    j = s['journey']
    need_(j.get('story'), 'Lì xì chỉ có trong hành trình.', 'locked')
    need_(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need_(isinstance(p, dict) and set(p) <= {'total', 'n', 'wish', 'text', 'confirm'} and {'total', 'n'} <= set(p), 'Thông tin không hợp lệ.')
    total, n = p['total'], p['n']
    need_(type(total) is int and TOTAL_MIN <= total <= TOTAL_MAX, f'Tổng lì xì từ {fmt(TOTAL_MIN)} đến {fmt(TOTAL_MAX)} xu nhé.', 'bad_total')
    need_(type(n) is int and N_MIN <= n <= N_MAX, f'Chia từ {N_MIN} đến {N_MAX} bao nhé.', 'bad_count')
    need_(total >= n * ENV_MIN, f'Mỗi bao ít nhất {ENV_MIN} xu: {n} bao cần từ {fmt(n * ENV_MIN)} xu.', 'bad_split')
    wish = p.get('wish') or ''
    need_(isinstance(wish, str) and (wish == '' or wish in WISH), 'Chọn lời chúc nhé.', 'bad_wish')
    text, raw = clean_line(p.get('text'))
    need_(p.get('confirm') is True, f'Xác nhận phát {fmt(total)} xu lì xì.')
    why = ready_why(s, total)
    need_(not why, why, 'not_enough')
    how = _take(s, total, f'🧧 Phát lì xì · {n} bao')
    return dict(message=f'🧧 Đã phát {n} bao lì xì, tổng {fmt(total)} xu ({how}). Cả phố đang giật!',
                lixi=dict(total=total, n=n, wish=wish, text=text, raw=raw))


def apply_fx(s: dict, p: dict, amount: int) -> str:
    """A 'lixi' live_effects row paid into the save (game/live_effects.py apply): what='grab' an envelope grabbed,
    what='back' what nobody took, back to the giver. Into the wallet (kind 'life')."""
    e = _core()
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    what = data.get('what')
    e.need(what in ('grab', 'back') and valid_pk(data.get('pk')), 'Dữ liệu lì xì không hợp lệ.')
    j = s['journey']
    if what == 'back':
        _jr()._wallet(j, amount, KIND, '🧧 Lì xì chưa ai giật, trả lại')
        return f'🧧 {fmt(amount)} xu lì xì chưa ai giật đã về ví.'
    name = data.get('name') if isinstance(data.get('name'), str) else ''
    name = name.strip()[:24] or GONE
    _jr()._wallet(j, amount, KIND, f'🧧 Lì xì của {name}'[:120])
    return f'🧧 +{fmt(amount)} xu lì xì của {name}!'


# ---------------------------------------------------------------- database: the packet (the save's own transaction)
def _display(db, sid: str) -> str:
    from .auction import display
    name = display(db, sid, False)
    from . import auction_content as AC
    return GONE if name in (AC.GONE, '') else name


def _notify(db, event: dict) -> None:
    from . import live_chat
    live_chat.notify(db, event)


def wish_text(wish: str, text: str) -> str:
    return (text or WISH.get(wish or '', '') or '')[:TEXT_MAX + 8]


def command_commit(db, sid: str, action: str, after: dict, result) -> None:
    """jr_lixi_give in the save's transaction (game/storage.py). A GameError here rolls the whole command back (nothing
    is paid): no account, too soon after the last packet, the day's packets, the street full of open packets."""
    if action not in COMMANDS:
        return
    r = (result or {}).get('lixi') if isinstance(result, dict) else None
    if not isinstance(r, dict):
        return
    e = _core()
    t = now()
    acc = db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()
    e.need(acc is not None, 'Tạo tài khoản để phát lì xì nhé (cả phố cần biết ai lì xì).', 'account_required')
    db.execute('SELECT pg_advisory_xact_lock(17826, 1)')
    day = vn_day(t)
    last = db.execute('SELECT MAX(at) AS at FROM lixi_packets WHERE sid=?', (sid,)).fetchone()
    wait = int(GAP - (t - float(last['at']))) if last and last['at'] is not None else 0
    e.need(wait <= 0, f'Vừa phát xong. Đợi {max(1, wait)} giây nữa nhé.', 'busy')
    mine = db.execute('SELECT COUNT(*) AS n FROM lixi_packets WHERE sid=? AND day=?', (sid, day)).fetchone()
    e.need(int(mine['n']) < DAY_MAX, f'Hôm nay bạn đã phát {DAY_MAX} lần lì xì rồi. Mai phát tiếp nhé!', 'limit')
    busy = db.execute("SELECT COUNT(*) AS n FROM lixi_packets WHERE status='open' AND expires>?", (t,)).fetchone()
    e.need(int(busy['n']) < OPEN_MAX, 'Phố đang nhiều lì xì quá. Đợi mọi người giật bớt rồi phát nhé!', 'busy')
    total, n = int(r['total']), int(r['n'])
    pk = 'lx' + secrets.token_hex(7)
    name = _display(db, sid)
    pid = pid_of(sid)
    db.execute('INSERT INTO lixi_packets(id, sid, pid, name, total, n, left_n, left_xu, wish, text, raw, status, day, at, expires, back, seq) '
               "VALUES(?,?,?,?,?,?,?,?,?,?,?,'open',?,?,?,0,0)",
               (pk, sid, pid, name, total, n, n, total, r.get('wish') or '', r.get('text') or '', r.get('raw') or '', day, t,
                t + HOURS * 3600))
    wish = wish_text(r.get('wish') or '', r.get('text') or '')
    if total >= NEWS_FROM:
        mr._post_news(db, 'lixi', f'lixi:{pk}', f'🧧 {name} phát {n} bao lì xì {fmt(total)} xu cho cả phố!', '', '')
    _VIEW.clear()
    _notify(db, dict(op='lixi', id=pk, pid=pid, name=name, n=n, left=n, total=total, wish=wish, at=round(t, 1),
                     exp=round(t + HOURS * 3600, 1)))


# ---------------------------------------------------------------- database: a grab
def _old_enough(db, sid: str, t: float) -> bool:
    r = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    if not r:
        return False
    return str(r['created_at']) <= time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - ACCOUNT_DAYS * DAY))


def _blocked(db, sid: str, other: str) -> bool:
    if not other:
        return False
    a, b = pid_of(sid), pid_of(other)
    if db.execute('SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?)', (a, b, b, a)).fetchone():
        return True
    return mr._blocked(db, sid, other)


def ip_tag(ip: str) -> str:
    """A short keyed hash of the network address (never the address itself)."""
    if not isinstance(ip, str) or not ip or ip == '?':
        return ''
    salt = os.environ.get('LIXI_IP_SALT') or 'mnl-lixi'
    return hashlib.sha256(f'{salt}|{ip}'.encode()).hexdigest()[:16]


def _back(db, p: dict, amount: int, t: float) -> None:
    """What nobody took goes back to the giver, once (a deterministic row id)."""
    if amount <= 0 or not p['sid']:
        return
    data = dict(pk=p['id'], what='back', src='lixi')
    db.execute('INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
               (f'lixi:{p["id"]}:back', p['sid'], FX, int(amount), json.dumps(data, ensure_ascii=False), 'pending', t))
    db.execute('UPDATE lixi_packets SET back=? WHERE id=?', (int(amount), p['id']))


def grab(store, token: str, d: dict, state: dict | None, ip: str = '', rng=None) -> dict:
    """POST /api/lixi/grab {id}: one envelope of the packet. {amount, again, message, id}. The xu travel in a
    live_effects row (the caller pays it at once with live_effects.on_load)."""
    need(isinstance(d, dict) and valid_pk(d.get('id')), 'Bao lì xì không hợp lệ.', 'bad_lixi')
    pk = d['id']
    sid, display = mr.whoami(store, token)
    need(sid, 'Tải lại trang để bắt đầu phiên chơi.', 'session_missing', 401)
    need(display, 'Tạo tài khoản để giật lì xì nhé.', 'account_required', 403)
    j = (state or {}).get('journey') if isinstance((state or {}).get('journey'), dict) else {}
    need(j.get('story'), 'Lì xì chỉ có trong hành trình.', 'not_story', 403)
    need(int(j.get('life_day') or 0) >= LIFE_DAYS, f'Giật lì xì mở từ ngày sống {LIFE_DAYS}.', 'too_new', 403)
    t = now()
    day = vn_day(t)
    tag = ip_tag(ip) if ONE_PER_IP else ''

    def run(db):
        row = db.execute('SELECT * FROM lixi_packets WHERE id=? FOR UPDATE', (pk,)).fetchone()
        need(row is not None, 'Không thấy bao lì xì này.', 'not_found', 404)
        p = dict(row)
        mine = db.execute('SELECT amount FROM lixi_grabs WHERE packet=? AND sid=?', (pk, sid)).fetchone()
        if mine:   # a second tap, another tab: the same envelope again
            return dict(amount=int(mine['amount']), again=True, name=p['name'])
        need(p['sid'] != sid, 'Lì xì của bạn mà, để cả phố giật nhé 😄', 'own', 409)
        need(p['status'] == 'open' and p['expires'] > t and p['left_n'] > 0, 'Hết bao rồi! Lần sau nhanh tay hơn nhé.', 'empty', 409)
        need(_old_enough(db, sid, t), f'Tài khoản cần đủ {ACCOUNT_DAYS} ngày mới giật được lì xì.', 'too_new', 403)
        need(not _blocked(db, sid, p['sid']), 'Bạn không giật được bao này.', 'blocked', 403)
        if tag:
            need(not db.execute('SELECT 1 FROM lixi_grabs WHERE packet=? AND ip=?', (pk, tag)).fetchone(),
                 'Mạng này vừa có người giật bao này rồi.', 'same_ip', 409)
        today = db.execute('SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS xu FROM lixi_grabs WHERE sid=? AND day=?', (sid, day)).fetchone()
        need(int(today['n']) < GRAB_DAY, f'Hôm nay bạn giật đủ {GRAB_DAY} bao rồi. Mai giật tiếp nhé!', 'limit', 409)
        room = GRAB_DAY_XU - int(today['xu'])
        need(room >= ENV_MIN, f'Hôm nay bạn nhận đủ {fmt(GRAB_DAY_XU)} xu lì xì rồi. Mai giật tiếp nhé!', 'limit', 409)
        pair = db.execute('SELECT COUNT(*) AS n FROM lixi_grabs WHERE sid=? AND giver=? AND day=?', (sid, p['sid'], day)).fetchone()
        need(int(pair['n']) < PAIR_DAY, f'Hôm nay bạn đã giật {PAIR_DAY} bao của người này rồi.', 'limit', 409)
        amount = min(split(p['left_xu'], p['left_n'], rng), room)
        left_n, left_xu = int(p['left_n']) - 1, int(p['left_xu']) - amount
        status = 'open' if left_n > 0 else 'done'
        db.execute('INSERT INTO lixi_grabs(packet, sid, pid, name, giver, amount, day, ip, at) VALUES(?,?,?,?,?,?,?,?,?)',
                   (pk, sid, pid_of(sid), display[:24], p['sid'], amount, day, tag, t))
        need(db.execute('UPDATE lixi_packets SET left_n=?, left_xu=?, status=?, done_at=?, seq=seq+1 WHERE id=? AND seq=?',
                        (left_n, left_xu, status, t if status != 'open' else None, pk, p['seq'])).rowcount == 1,
             'Bao vừa thay đổi, thử lại nhé.', 'busy', 409)
        data = dict(pk=pk, what='grab', name=p['name'][:24], src='lixi')
        db.execute('INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,?,?)',
                   (f'lixi:{pk}:{pid_of(sid)}', sid, FX, amount, json.dumps(data, ensure_ascii=False), 'pending', t))
        if status != 'open':
            _back(db, p, left_xu, t)   # the last envelope was cut by a cap: the rest goes home
        _notify(db, dict(op='lixi_upd', id=pk, left=left_n, done=status != 'open'))
        return dict(amount=amount, again=False, name=p['name'])
    out = store.transaction(run)
    _VIEW.clear()
    who = out['name'] or GONE
    msg = (f'🧧 Bạn đã giật bao này rồi: {fmt(out["amount"])} xu.' if out['again'] else
           f'🧧 Bạn giật được {fmt(out["amount"])} xu từ lì xì của {who}!')
    return dict(ok=True, id=pk, amount=out['amount'], again=out['again'], message=msg)


# ---------------------------------------------------------------- the 24 h sweep (housekeeping, idempotent)
def expire_one(store, pk: str, t: float | None = None) -> int | None:
    """Close one packet whose time is up: the xu returned (0 when it was empty), None when there was nothing to do.
    Safe from any worker any number of times."""
    t = now() if t is None else t

    def run(db):
        row = db.execute('SELECT * FROM lixi_packets WHERE id=? FOR UPDATE', (pk,)).fetchone()
        if not row or row['status'] != 'open' or row['expires'] > t:
            return None
        p = dict(row)
        db.execute("UPDATE lixi_packets SET status='expired', done_at=?, seq=seq+1 WHERE id=? AND status='open'", (t, pk))
        _back(db, p, int(p['left_xu']), t)
        _notify(db, dict(op='lixi_upd', id=pk, left=int(p['left_n']), done=True))
        return int(p['left_xu']) if p['sid'] else 0
    out = store.transaction(run)
    if out is not None:
        _VIEW.clear()
    return out


SWEEP_EVERY = 30.0
_swept = [0.0]


def sweep(store, t: float | None = None, limit: int = 50, force: bool = False) -> int:
    """Expire every packet past its time (at most `limit`). The number closed."""
    t = now() if t is None else t
    if not force and time.monotonic() - _swept[0] < SWEEP_EVERY:
        return 0
    _swept[0] = time.monotonic()
    with store.connect() as db:
        ids = [r['id'] for r in db.execute("SELECT id FROM lixi_packets WHERE status='open' AND expires<=? ORDER BY expires LIMIT ?",
                                           (t, limit)).fetchall()]
    return sum(1 for pk in ids if expire_one(store, pk, t) is not None)


def run_housekeeping(store) -> None:
    """server.py maintenance (every 30 s, one process). Never raises."""
    import sys
    try:
        n = sweep(store, force=True)
        if n:
            sys.stderr.write(f'[lixi] expired {n}\n')
    except Exception as e:  # noqa: BLE001 - housekeeping never takes the server down
        sys.stderr.write(f'[lixi] housekeeping: {type(e).__name__}\n')


# ---------------------------------------------------------------- the page (GET /api/lixi)
VIEW_SECS = 2.0
_VIEW: dict = {}           # 'v' -> (monotonic, rows): one entry, bounded
_VIEW_LOCK = threading.Lock()


def _card(r) -> dict:
    return dict(id=r['id'], pid=r['pid'], name=r['name'] or GONE, n=int(r['n']), left=int(r['left_n']), total=int(r['total']),
                wish=wish_text(r['wish'], r['text']), status=r['status'], at=float(r['at']), exp=float(r['expires']))


def _rows(store) -> list:
    with _VIEW_LOCK:
        hit = _VIEW.get('v')
        if hit and time.monotonic() - hit[0] < VIEW_SECS:
            return hit[1]
    with store.connect() as db:
        rows = [_card(r) for r in db.execute('SELECT * FROM lixi_packets WHERE at>? ORDER BY at DESC LIMIT ?',
                                             (now() - HOURS * 3600, LIST_MAX)).fetchall()]
    with _VIEW_LOCK:
        _VIEW.clear()
        _VIEW['v'] = (time.monotonic(), rows)
    return rows


def _hidden(db, sid: str) -> set:
    """Pids hidden from this player (blocked either way, by chat or by Hôn nhân)."""
    me = pid_of(sid)
    out = {r['p'] for r in db.execute('SELECT target AS p FROM blocks WHERE pid=? UNION SELECT pid AS p FROM blocks WHERE target=?',
                                      (me, me)).fetchall()}
    for r in db.execute('SELECT target AS s FROM marriage_blocks WHERE sid=? UNION SELECT sid AS s FROM marriage_blocks WHERE target=?',
                        (sid, sid)).fetchall():
        out.add(pid_of(r['s']))
    return out


def _public(card: dict, me: str, hidden: set, got: dict) -> dict:
    out = {k: v for k, v in card.items() if k != 'pid'}
    if card['pid'] == me:
        out['own'] = True
    if card['pid'] in hidden:
        out.update(name='', wish='', no=True)
    if card['id'] in got:
        out['got'] = got[card['id']]
    if out['status'] == 'open' and out['exp'] <= now():
        out['status'] = 'expired'
    return out


def view(store, token: str | None, pk: str | None = None) -> dict:
    """The last HOURS of packets (newest first) and mine; with pk, that packet and who got how much."""
    try:
        sweep(store)
    except Exception:  # noqa: BLE001 - a page never fails because of the housekeeping
        pass
    rows = _rows(store)
    sid = store.key(token) if isinstance(token, str) and 16 <= len(token) <= 128 else None
    out = dict(now=now(), caps=dict(day=GRAB_DAY, xu=GRAB_DAY_XU, pair=PAIR_DAY))
    me, hidden, got = '', set(), {}
    if sid:
        me = pid_of(sid)
        with store.connect() as db:
            hidden = _hidden(db, sid)
            ids = [x['id'] for x in rows] + ([pk] if valid_pk(pk) else [])
            if ids:
                got = {r['packet']: int(r['amount']) for r in db.execute(
                    'SELECT packet, amount FROM lixi_grabs WHERE sid=? AND packet IN (%s)' % ','.join('?' * len(ids)), [sid] + ids).fetchall()}
            today = db.execute('SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS xu FROM lixi_grabs WHERE sid=? AND day=?',
                               (sid, vn_day())).fetchone()
            acct = db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone() is not None
            old = _old_enough(db, sid, now())
        why = '' if acct and old else ('Cần tài khoản đã đăng ký' if not acct else f'Cần tài khoản đủ {ACCOUNT_DAYS} ngày')
        out['me'] = dict(n=int(today['n']), xu=int(today['xu']), can=not why, why=why)
    out['packets'] = [_public(x, me, hidden, got) for x in rows]
    if valid_pk(pk):
        out['packet'] = detail(store, pk, me, hidden, got)
    return out


def detail(store, pk: str, me: str = '', hidden: set = frozenset(), got: dict | None = None) -> dict | None:
    """One packet and every envelope taken: [{name, amount, at, best?, me?}] in order; 🏆 Hên nhất once it is finished."""
    with store.connect() as db:
        r = db.execute('SELECT * FROM lixi_packets WHERE id=?', (pk,)).fetchone()
        if not r:
            return None
        grabs = [dict(g) for g in db.execute('SELECT pid, name, amount, at FROM lixi_grabs WHERE packet=? ORDER BY at, pid', (pk,)).fetchall()]
    card = _public(_card(r), me, hidden, got or {})
    best = None
    if card['status'] != 'open' and grabs:
        best = max(grabs, key=lambda g: (int(g['amount']), -float(g['at'])))
    card['grabs'] = [dict(name='' if g['pid'] in hidden else (g['name'] or GONE), amount=int(g['amount']), at=float(g['at']),
                          **({'best': True} if g is best else {}), **({'me': True} if me and g['pid'] == me else {})) for g in grabs]
    card['taken'] = sum(int(g['amount']) for g in grabs)
    card['back'] = int(r['back'])
    return card


def catalogue() -> dict:
    """Static rules for the client (bootstrap content, cached)."""
    return dict(min=TOTAL_MIN, max=TOTAL_MAX, n_min=N_MIN, n_max=N_MAX, env_min=ENV_MIN, hours=HOURS, gap=GAP, day_max=DAY_MAX,
                life_days=LIFE_DAYS, account_days=ACCOUNT_DAYS, grab_day=GRAB_DAY, grab_day_xu=GRAB_DAY_XU, pair_day=PAIR_DAY,
                text_max=TEXT_MAX, wishes=[dict(id=k, text=v) for k, v in WISHES])


# ---------------------------------------------------------------- admin (GET /api/admin/lixi)
def admin_view(store) -> dict:
    """The last 60 packets with the giver's username and the takers, and today's biggest takers."""
    with store.connect() as db:
        rows = db.execute('SELECT p.*, a.username AS username FROM lixi_packets p LEFT JOIN accounts a ON a.sid=p.sid '
                          'ORDER BY p.at DESC LIMIT 60').fetchall()
        tops = db.execute('SELECT g.sid AS sid, MAX(g.name) AS name, MAX(a.username) AS username, COUNT(*) AS n, SUM(g.amount) AS xu '
                          'FROM lixi_grabs g LEFT JOIN accounts a ON a.sid=g.sid WHERE g.day=? GROUP BY g.sid ORDER BY xu DESC LIMIT 20',
                          (vn_day(),)).fetchall()
        tot = db.execute('SELECT COALESCE(SUM(total), 0) AS xu, COUNT(*) AS n FROM lixi_packets WHERE day=?', (vn_day(),)).fetchone()
    return dict(packets=[dict(_card(r), username=r['username'] or '', raw=r['raw'] or '', back=int(r['back'])) for r in rows],
                takers=[dict(name=r['name'] or GONE, username=r['username'] or '', n=int(r['n']), xu=int(r['xu'])) for r in tops],
                today=dict(xu=int(tot['xu']), n=int(tot['n'])))


# ---------------------------------------------------------------- account deletion
def forget(store, token: str) -> None:
    """A player erased their data: their open packets close (what is left went with the save), their name leaves every
    row (the amounts stay, so a packet still adds up)."""
    sid = store.key(token)
    gone = 'x' + pid_of(sid)[:15]
    t = now()

    def run(db):
        db.execute("UPDATE lixi_packets SET status='gone', done_at=?, seq=seq+1 WHERE sid=? AND status='open'", (t, sid))
        db.execute("UPDATE lixi_packets SET sid='', name=?, raw='' WHERE sid=?", (GONE, sid))
        db.execute("UPDATE lixi_grabs SET sid=?, name=?, ip='' WHERE sid=?", (gone, GONE, sid))
        db.execute("UPDATE lixi_grabs SET giver='' WHERE giver=?", (sid,))
    store.transaction(run)
    _VIEW.clear()
