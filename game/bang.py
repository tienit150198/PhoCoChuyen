"""⚔️ Bang: player guilds (owner design 19/10). Numbers and names: game/bang_content.py.

What a player does
* 🏯 Lập bang (the command jr_bang_found {name, emoji, color, motto, open, confirm}): an account at least
  C.FOUND_ACCOUNT_DAYS real days old, a chức danh (a promotion step ≥ 1 in some career, game/promotion.py), and
  C.FOUND_FEE xu, a pure sink (the wallet then the bank, never a loan; wallet rows ≤ 10 M; kind 'life'). The name passes
  the display-name rules of players (game/accounts.py clean_display, game/social.py) and is unique on a key that ignores
  case, diacritics, spaces and punctuation. The reducer pays; command_commit, in the save's own transaction, checks the
  account, the name (under an advisory lock on its key) and writes the bang, its leader, its chat group: a refusal
  there rolls the whole command back, nothing paid.
* 🚪 Vào bang thoải mái (POST /api/bang/<op>, database only, no save): join an open bang at once, ask a closed one, or
  accept an invitation; one bang at a time, no cooldown: joining another bang leaves the current one (a Bang chủ hands
  over or disbands first), a soft anti-churn cap of C.SWITCH_DAY_MAX bangs joined (or founded) a Vietnam day. Members
  cap: the Đại sảnh (C.HALL_CAP, 10 → 30), counted under the bang row's lock.
* 🚪 Cách nhận người (owner 20/10; POST /api/bang/rules, Phó bang and up; bangs.rules, SCHEMA_VERSION 60): 🚫 Đóng
  (no join, no request; an officer's invitation still lets a player in, open requests may still be approved), 🔒 Cần
  duyệt, 🚪 Tự động duyệt (in at once when the requirements hold, else refused with the reason); optional requirements,
  all applying: a career from a title of its real ladder (game/promotion.py), a title step in any career, the account's
  age. Checked on the server from the player's real save (parsed before the transaction, only for a bang with
  requirements) on join, request, invitation and approval; members already in stay when they change.
* 💰 Quỹ bang: deposits only (the command jr_bang_give {bang, amount, confirm}: from C.GIVE_MIN, whole thousands, no
  maximum but what the player has, wallet then bank: owner 21/10 "quỹ bang cho k giới hạn", "góp 1 lần không giới hạn";
  the wallet's part in Sổ ví rows of at most ROW_MAX), written with the save (ledger row 'g:<pid>:<nonce>', the nonce in
  journey.bang.last.r: never reused after reset_all or an imported older save; a clash refuses the whole command) under
  the bang row's lock. No cap on the fund (only C.FUND_MAX, a technical ceiling). Nothing pays out of it: it only buys
  facility levels and the bang's island; disbanding burns it (a 'burn' row, `burned`). There is no withdraw, transfer or
  refund path anywhere (tests/test_bang.py checks the source).
* 🏝️ Đảo bang (owner 21/10, SCHEMA_VERSION 62: bangs.isle…): bought (cấp 1, C.ISLE_BUY) then upgraded (cấp 2…5 at the
  private islands' prices, real-time builds) from the fund by Phó bang and up (POST /api/bang/isle {to, confirm}:
  idempotent by `to`, under the bang row's lock). has_island() gates what is played there: a visit (game/
  bang_island_source.py), the pet arena (game/pet_arena.py) and the Bang chiến pet (game/bang_pets.py can_pick).
  Joining, the fund, check-in, builds, the shop, chat and the Giờ vàng work without it (a bang saves up to buy it).
  Facilities' higher levels wait for higher island levels (C.isle_needed). Bangs from before 21/10 hold cấp 1 (the
  column's default, 'grant').
* ⭐ Điểm cống hiến, per member per bang: 1 per 1.000 xu given (+ the Kho bang's bonus; at most C.GIVE_PTS_DAY a day
  from gifts, every bang together), 📅 Điểm danh once a day,
  work days closed (end_day, a few a day): C.ACTIVITY_DAY_MAX a day from activity, one ledger id per player and day so
  hopping between bangs earns nothing more. Spent only in the 🛍️ Cửa hàng bang (never xu).
* 🎖️ Danh hiệu: Bang chủ (1), Phó bang (2), Trưởng lão (3), Tinh anh (5), Thành viên; the leader appoints and may hand
  over; leaving drops the title at once. The live service shows the tag and role beside the name (live/bangs.py: the
  2.5D map, the old street, chat, cards); the game's profile page reads tag_of().
* 🏗️ Công trình bang (facilities, many levels each, real-time builds paid from the fund by Phó bang and up).
* ⏰ Giờ vàng của bang (Đền vàng): windows the leader (or a Phó bang) sets at least an hour ahead. During one, members'
  staff orders and counter sales take ×2 (C.GOLDEN_MULT) like the town's Giờ vàng: the larger of the two, never both
  (ads' private ×1,5 stays on top as before). A window counts for a member who joined the bang at least
  C.GOLDEN_SENIORITY (24 h) before it started, and only until they leave (membership spans, bang_stints), so hopping
  between bangs earns nothing and offline catch-up books the same as polling. No query per order: before each command
  (never under its lock) the storage layer refreshes a small shared snapshot of the windows on now (once a minute, one
  thread a process) and, every half hour, the player's own windows that already ended (prepare); the command binds
  this save's (bind).
* 👑 Bang mạnh nhất tuần (owner 21/10, final: "đừng để cống hiến bang tính điểm nhé, hãy tính điểm của pets, công trình
  và cấp bang làm điểm nhé"): three parts (standings, weights in game/bang_content.py), heaviest first: 🐾 Pets (the
  week's pet war once its matches were shown, its ⚔️ Thách đấu bang, and 💪 Chiến lực: the strongest pet power of each
  current member, pet_power), 🏗️ Công trình (facility levels but the hall), ⭐ Cấp bang (the Đại sảnh's level, + the
  island's when that branch gives one); the sum × the Tượng bang's bonus. Điểm cống hiến never counts (the shop only). The winner, frozen after the week
  (its chiến lực as it is then), gives its members the title for the next week (shown in the tag; leaving drops it).
  No money prize.

State in the save: only s['journey']['bang'] = {v, n, sum, last: {n, k, a, at, r?}} (absent until the first paid command;
journey.validate of every build allows extra keys): the paid commands' counter and the last one's nonce (`r`, optional).
Old rows go to archive tables (run_housekeeping, SCHEMA_VERSION 59), never deleted. 🛑 MNL_BANG_OFF: off(). Everything else is in the
database (game/pg_schema.py SCHEMA_VERSION 57), visible to everyone.
"""
from __future__ import annotations

import contextvars
import datetime
import hashlib
import json
import math
import os
import re
import secrets
import threading
import time
import unicodedata

from . import bang_content as C
from . import marriage as mr

VERSION = 1
KEY = 'bang'
KIND = 'life'                    # wallet history kind every build knows
COMMANDS = ('jr_bang_found', 'jr_bang_give')
BLOCK_KEYS = frozenset({'v', 'n', 'sum', 'last'})
LAST_KEYS = frozenset({'n', 'k', 'a', 'at'})
LAST_OPT = frozenset({'r'})       # the paid command's nonce (review fix 19/10): optional, a block without it stays valid
NONCE_RE = re.compile(r'[0-9a-f]{16}')
ROW_MAX = 10_000_000             # a wallet history row (every build validates ±10 M)
BIG = 10**12
ID_RE = re.compile(r'b[0-9a-f]{10}')
PID_RE = re.compile(r'[0-9a-f]{16}')
RID_RE = re.compile(r'[A-Za-z0-9\-]{8,64}')
CODE_RE = re.compile(r'PCC-[0-9A-Z]{6}')
LOCK = 17862                     # pg_advisory_xact_lock(LOCK, …): a name key, the week's freeze
VN = datetime.timezone(datetime.timedelta(hours=7))
SEARCH_MAX = 30
LOG_SHOWN = 20
GONE = 'Một người chơi'


class BangError(mr.MarriageError):
    """A refusal of a database operation, shown as is (answered like Hôn nhân's)."""


def need(ok, message: str, code: str = 'bang_error', status: int = 400):
    if not ok:
        raise BangError(message, code, status)


def now() -> float:
    return time.time()


OFF_TEXT = 'Bang đang tạm nghỉ để bảo trì. Quay lại sau nhé!'


def off() -> bool:
    """🛑 MNL_BANG_OFF=1 (ops' kill switch, default unset: on): the ⚔️ Bang entry hides (content `off`), new actions
    are refused gracefully (the paid commands, POST /api/bang/<op>, the pages). Nothing in the database or the saves
    changes: builds finish on time, Giờ vàng windows already set still count, tags stay, the pet war still runs."""
    return os.environ.get('MNL_BANG_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _core():
    from . import engine
    return engine


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def vn_day(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%Y-%m-%d')


def vn_week(t: float) -> str:
    y, w, _ = datetime.datetime.fromtimestamp(t, VN).isocalendar()
    return f'{y}-W{w:02d}'


def week_start(t: float) -> float:
    d = datetime.datetime.fromtimestamp(t, VN).date()
    d -= datetime.timedelta(days=d.weekday())
    return datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp()


def prev_week(t: float) -> str:
    return vn_week(week_start(t) - 3600)


def week_end(week: str) -> float:
    """The end (epoch s) of a Vietnam ISO week 'YYYY-Www'."""
    y, w = week.split('-W')
    d = datetime.date.fromisocalendar(int(y), int(w), 1) + datetime.timedelta(days=7)
    return datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp()


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


# ---------------------------------------------------------------- names
def name_key(name: str) -> str:
    """The uniqueness key: lower case, no diacritics (đ → d), letters and digits only ("Rồng Đỏ" = "rong do" = "RONGDO")."""
    t = unicodedata.normalize('NFD', str(name).lower()).replace('đ', 'd')
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r'[^0-9a-z]+', '', t)


def clean_name(value) -> str | None:
    """(name) through the players' display-name rules, or raises GameError with the reason."""
    from . import social
    from .accounts import offensive_name
    e = _core()
    try:
        name = social.clean(value, C.NAME_MAX, C.NAME_MIN, 'Tên bang', keep=social.NAME_JOINER)
    except social.SocialError as x:
        raise e.GameError(x.message, 'bad_name') from None
    problem = social.name_problem(name) if name else social.NAME_RULE
    e.need(not problem, (problem or '').replace('Tên ', 'Tên bang ', 1), 'bad_name')
    e.need('•' not in name and not offensive_name(name), 'Chọn một cái tên bang thân thiện hơn nhé.', 'bad_name')
    e.need(len(name_key(name)) >= C.NAME_MIN, f'Tên bang cần ít nhất {C.NAME_MIN} chữ hoặc số.', 'bad_name')
    return name


def clean_motto(value) -> str:
    from . import social
    e = _core()
    if value in (None, ''):
        return ''
    try:
        text = social.clean(value, C.MOTTO_MAX, 0, 'Khẩu hiệu').replace('\n', ' ')
    except social.SocialError as x:
        raise e.GameError(x.message, 'bad_motto') from None
    from live import filters
    return filters.mask(text)[:C.MOTTO_MAX].strip()


def has_title(s: dict) -> bool:
    """A chức danh (a promotion step ≥ 1) in at least one career."""
    from . import promotion
    for career, c in (s.get('careers') or {}).items():
        try:
            if isinstance(c, dict) and promotion.rank(s, c, career) >= 1:
                return True
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return False


# ---------------------------------------------------------------- 🚪 join rules (owner 20/10)
_LADDER: dict = {}


def ladder() -> list:
    """[{id, name, titles}] of every playable career and its real promotion ladder (game/promotion.py: the titles of
    steps 1…top), for the requirement picker (GET /api/bang?careers=1)."""
    if not _LADDER:
        from . import promotion
        from .admin_stats import career_names
        from .content import CAREERS
        names = career_names()
        _LADDER['list'] = [dict(id=c, name=names.get(c, c), titles=[title_name(c, n) for n in range(1, promotion.top(c) + 1)])
                           for c in CAREERS]
        _LADDER['by'] = {x['id']: x for x in _LADDER['list']}
    return _LADDER['list']


def title_name(career: str, n: int) -> str:
    """The title of step n of a career's ladder, as a player of no stated gender sees it."""
    from . import promotion
    return promotion.title({'journey': {}}, {}, career, n)


def rules_of(row: dict) -> dict:
    """{mode, career, rank, any, days} of a bang row: its `rules` (SCHEMA_VERSION 60; '{}' or missing: the mode
    from `open`, no requirement). Anything unknown or out of range reads as no requirement."""
    try:
        r = json.loads(row.get('rules') or '{}')
    except (TypeError, ValueError):
        r = {}
    r = r if isinstance(r, dict) else {}
    mode = r.get('mode') if r.get('mode') in C.JOIN_MODES else ('auto' if row.get('open') else 'ask')
    ladder()
    career = r.get('career') if isinstance(r.get('career'), str) and r.get('career') in _LADDER['by'] else ''
    top = len(_LADDER['by'][career]['titles']) if career else 0
    rank = r.get('rank') if career and _int(r.get('rank'), 1, top) else 0
    return dict(mode=mode, career=career if rank else '', rank=rank,
                any=r.get('any') if _int(r.get('any'), 1, C.REQ_RANK_MAX) else 0,
                days=r.get('days') if _int(r.get('days'), 1, C.REQ_DAYS_MAX) else 0)


def has_reqs(rules: dict) -> bool:
    return bool(rules['rank'] or rules['any'] or rules['days'])


def req_lines(rules: dict) -> list:
    """The requirements in words (the bang's card in Tìm bang, its page, a refusal)."""
    out = []
    if rules['rank']:
        x = _LADDER['by'][rules['career']]
        out.append(f'{x["name"]} từ {x["titles"][rules["rank"] - 1]} (bậc {rules["rank"]})')
    if rules['any']:
        out.append(f'Chức danh bậc {rules["any"]} trở lên ở một nghề bất kỳ')
    if rules['days']:
        out.append(f'Tài khoản từ {rules["days"]} ngày')
    return out


def _age_days(created_at) -> int:
    try:
        born = datetime.datetime.strptime(str(created_at)[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp()
    except ValueError:
        return 0
    return max(0, int((time.time() - born) // 86400))


def profile_of(db, sid: str) -> dict:
    """{ranks: {career: promotion step}, days: account age} of a player, from their real save (parsed once: called
    before the operation's transaction, never under a bang row's lock) and their account."""
    from . import promotion
    acc = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    try:
        st = json.loads(row['state']) if row and row['state'] else {}
    except (TypeError, ValueError):
        st = {}
    ranks = {}
    for career, c in ((st.get('careers') if isinstance(st, dict) else None) or {}).items():
        try:
            n = promotion.rank(st, c, career) if isinstance(c, dict) else 0
        except (KeyError, TypeError, ValueError, AttributeError):
            n = 0
        if n >= 1:
            ranks[career] = n
    return dict(ranks=ranks, days=_age_days(acc['created_at']) if acc else 0)


def req_problem(rules: dict, prof: dict | None, who: str = 'Bạn') -> str | None:
    """Why `prof` does not meet the bang's requirements (None: it does, or there are none)."""
    if not has_reqs(rules):
        return None
    if prof is None:
        return 'Bang vừa đổi yêu cầu. Thử lại nhé.'
    miss = []
    if rules['rank'] and prof['ranks'].get(rules['career'], 0) < rules['rank']:
        miss.append(req_lines(dict(rules, any=0, days=0))[0])
    if rules['any'] and max(prof['ranks'].values(), default=0) < rules['any']:
        miss.append(f'chức danh bậc {rules["any"]} trở lên ở một nghề')
    if rules['days'] and prof['days'] < rules['days']:
        miss.append(f'tài khoản từ {rules["days"]} ngày (mới {prof["days"]} ngày)')
    return f'{who} chưa đủ yêu cầu của bang: cần ' + '; '.join(miss) + '.' if miss else None


# ---------------------------------------------------------------- the save block
def initial() -> dict:
    return dict(v=VERSION, n=0, sum=0, last=None)


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def _last_ok(x) -> bool:
    return x is None or (isinstance(x, dict) and LAST_KEYS <= set(x) <= LAST_KEYS | LAST_OPT and _int(x['n'], 1, 10**9)
                         and x['k'] in ('found', 'give') and _int(x['a'], 1, BIG) and _int(x['at'], 0, 2**34)
                         and ('r' not in x or (isinstance(x['r'], str) and NONCE_RE.fullmatch(x['r']) is not None)))


def validate(s: dict) -> None:
    """``s['journey']['bang']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    b = get(s)
    bad = 'Dữ liệu bang trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get(KEY) is None, bad, 'invalid_save')
        return
    e.need(set(b) == BLOCK_KEYS and b['v'] == VERSION and _int(b['n'], 0, 10**9) and _int(b['sum']) and _last_ok(b['last'])
           and (b['last'] is None or b['last']['n'] == b['n']), bad, 'invalid_save')


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    if not isinstance(b, dict):
        j[KEY] = initial()
        return
    out = initial()
    out['n'] = b['n'] if _int(b.get('n'), 0, 10**9) else 0
    out['sum'] = b['sum'] if _int(b.get('sum')) else 0
    last = b.get('last')
    if isinstance(last, dict) and set(last) >= LAST_KEYS:
        last = {k: last[k] for k in LAST_KEYS | LAST_OPT if k in last}
    out['last'] = last if _last_ok(last) and last and last['n'] == out['n'] else None
    if out != b:
        j[KEY] = out


def _take(s: dict, amount: int, label: str) -> str:
    """`amount` from the wallet first (rows of at most ROW_MAX), then the bank account (the caller checked it is there)."""
    from . import bank as bk
    from . import journey as jr
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    left = cash
    while left > 0:
        part = min(left, ROW_MAX)
        jr._wallet(j, -part, KIND, label[:120])
        left -= part
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label[:120], -rest)
    if rest and cash:
        return f'{fmt(cash)} xu tiền mặt và {fmt(rest)} xu từ tài khoản'
    return f'{fmt(amount)} xu từ tài khoản' if rest else f'{fmt(amount)} xu tiền mặt'


def _ready_why(s: dict, amount: int) -> str:
    from . import lux
    return lux.ready_why(s, amount)


# ---------------------------------------------------------------- the two paid commands
def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need_ = e.need
    j = s['journey']
    need_(j.get('story'), 'Bang chỉ có trong hành trình.', 'locked')
    need_(not off(), OFF_TEXT, 'off')
    need_(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need_(isinstance(p, dict), 'Thông tin không hợp lệ.')
    t = int(now())
    if name == 'jr_bang_found':
        need_(set(p) <= {'name', 'emoji', 'color', 'motto', 'open', 'confirm'} and 'name' in p, 'Thông tin không hợp lệ.')
        bname = clean_name(p['name'])
        emoji = p.get('emoji', C.EMOJIS[0])
        need_(emoji in C.EMOJIS, 'Chọn một biểu tượng trong danh sách nhé.', 'bad_emoji')
        color = p.get('color', 'do')
        need_(isinstance(color, str) and color in C.COLORS, 'Chọn một màu trong bảng màu nhé.', 'bad_color')
        motto = clean_motto(p.get('motto', ''))
        is_open = p.get('open', True)
        need_(type(is_open) is bool, 'Thông tin không hợp lệ.')
        # owner 21/10: "ai cũng lập được, đủ 14 ngày và có 5M xu là lập được, k cần chức danh ở nghề" (has_title kept for reuse)
        need_(p.get('confirm') is True, f'Xác nhận trả {fmt(C.FOUND_FEE)} xu để lập bang {bname}.')
        why = _ready_why(s, C.FOUND_FEE)
        need_(not why, why, 'not_enough')
        how = _take(s, C.FOUND_FEE, f'⚔️ Lập bang {bname}')
        b = _ensure(s)
        b['n'] += 1
        b['sum'] = min(BIG, b['sum'] + C.FOUND_FEE)
        b['last'] = dict(n=b['n'], k='found', a=C.FOUND_FEE, at=t, r=secrets.token_hex(8))
        return dict(message=f'{emoji} Bang {bname} ra đời! Bạn là Bang chủ ({how}).',
                    bang=dict(k='found', n=b['n'], r=b['last']['r'], name=bname, emoji=emoji, color=color, motto=motto, open=is_open))
    need_(set(p) <= {'bang', 'amount', 'confirm'} and {'bang', 'amount'} <= set(p), 'Thông tin không hợp lệ.')
    bid = p['bang']
    need_(isinstance(bid, str) and ID_RE.fullmatch(bid), 'Chọn bang của bạn nhé.')
    amount = p['amount']
    need_(type(amount) is int and C.GIVE_MIN <= amount, f'Góp từ {fmt(C.GIVE_MIN)} xu trở lên nhé.')
    need_(amount <= C.GIVE_MAX, 'Số xu góp không hợp lệ.')   # a technical ceiling only (21/10: no cap but what you have)
    need_(amount % C.GIVE_MIN == 0, f'Góp theo bội số {fmt(C.GIVE_MIN)} xu nhé.')
    need_(p.get('confirm') is True, f'Xác nhận góp {fmt(amount)} xu vào quỹ bang (không rút lại được).')
    why = _ready_why(s, amount)
    need_(not why, why, 'not_enough')
    how = _take(s, amount, '⚔️ Góp quỹ bang')
    b = _ensure(s)
    b['n'] += 1
    b['sum'] = min(BIG, b['sum'] + amount)
    # 🔑 the ledger id comes from a nonce, never from n alone: n starts again after reset_all or an imported older save
    b['last'] = dict(n=b['n'], k='give', a=amount, at=t, r=secrets.token_hex(8))
    return dict(message=f'💰 Bạn góp {fmt(amount)} xu vào quỹ bang ({how}).', bang=dict(k='give', n=b['n'], bang=bid, a=amount, r=b['last']['r']))


# ---------------------------------------------------------------- database helpers
def _rows(db, sql: str, args=()) -> list:
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def _row(db, sql: str, args=()) -> dict | None:
    r = db.execute(sql, args).fetchone()
    return dict(r) if r else None


def _display(db, sid: str) -> str:
    r = db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()
    return str(r['display'])[:24] if r and r['display'] else GONE


def _lock(db, *ids) -> dict:
    """The bang rows, locked in id order (the one lock order of this module), as {id: row}."""
    out = {}
    for bid in sorted({i for i in ids if i}):
        r = _row(db, 'SELECT * FROM bangs WHERE id=? FOR UPDATE', (bid,))
        if r:
            out[bid] = r
    return out


def _mine(db, sid: str, lock: bool = False) -> dict | None:
    """My membership row now ('in'), or None."""
    return _row(db, "SELECT * FROM bang_members WHERE sid=? AND status='in'" + (' FOR UPDATE' if lock else ''), (sid,))


def _rank(role: str) -> int:
    return C.ROLES.get(role, C.ROLES['tv'])[3]


def _count(db, bid: str) -> int:
    return int(db.execute("SELECT COUNT(*) AS n FROM bang_members WHERE bang=? AND status='in'", (bid,)).fetchone()['n'])


def _seats(db, bid: str, role: str) -> int:
    return int(db.execute("SELECT COUNT(*) AS n FROM bang_members WHERE bang=? AND status='in' AND role=?", (bid, role)).fetchone()['n'])


def _log(db, bid: str, sid: str, kind: str, text: str, t: float) -> None:
    db.execute('INSERT INTO bang_log(bang, sid, kind, text, at) VALUES(?,?,?,?,?)', (bid, sid, kind, text[:200], t))


def _bump(db, bid: str) -> None:
    db.execute('UPDATE bangs SET seq=seq+1 WHERE id=?', (bid,))
    _VIEW.clear()


def _notify(db, **event) -> None:
    """Tell the live service (live/bangs.py): name tags of these pids, chat group membership."""
    from . import live_chat
    live_chat.notify(db, dict(op='bang', **event))


def _isle(db, why: str, bid: str, sid: str = '') -> None:
    """⚔️ Đảo bang (live/bang_island.py on_notify): re-check this player now (join, left, kicked, role, guest), repaint
    the island (view: a facility, the name, the colours) or close it (disband). Delivered on commit; an older live
    service ignores the op."""
    from . import live_chat
    live_chat.notify(db, dict(op='bang_island', why=why, bang=bid, **(dict(sid=sid) if sid else {})))


def finish_builds(db, bid: str, t: float) -> list:
    """Builds whose time is up become their level (guarded by target: idempotent, any number of processes); the
    island's upgrade too (finish_isle, first: the bang row before the facility rows, the module's lock order)."""
    finish_isle(db, bid, t)
    done = _rows(db, 'UPDATE bang_facilities SET level=target, target=NULL WHERE bang=? AND target IS NOT NULL AND ready_at<=? '
                 'RETURNING fac, level', (bid, t))
    for r in done:
        f = C.FACILITIES.get(r['fac'])
        if f:
            _log(db, bid, '', 'built', f'{f["emoji"]} {f["name"]} lên cấp {r["level"]}: {C.perk(r["fac"], int(r["level"]))}.', t)
    if done:
        _bump(db, bid)
        _isle(db, 'view', bid)
    return done


def builds_due(db, bid: str, t: float) -> bool:
    return (db.execute('SELECT 1 FROM bang_facilities WHERE bang=? AND target IS NOT NULL AND ready_at<=? LIMIT 1', (bid, t)).fetchone() is not None
            or db.execute('SELECT 1 FROM bangs WHERE id=? AND isle_to IS NOT NULL AND isle_ready<=?', (bid, t)).fetchone() is not None)


# ---------------------------------------------------------------- 🏝️ Đảo bang (owner 21/10, SCHEMA_VERSION 62)
def island_of(row: dict, t: float) -> dict:
    """{level, to, ready, started, how} of a bang row's island now: an upgrade whose time is up counts as done (read only:
    finish_isle writes it). level 0: not bought."""
    lv = int(row.get('isle') or 0)
    to, ready = row.get('isle_to'), row.get('isle_ready')
    if to is not None and ready is not None and float(ready) <= t:
        lv, to = max(lv, int(to)), None
    return dict(level=max(0, min(C.ISLE_MAX, lv)), to=int(to) if to is not None else None,
                ready=float(ready) if to is not None and ready is not None else None,
                started=float(row['isle_started']) if to is not None and row.get('isle_started') is not None else None,
                how=str(row.get('isle_how') or ''))


def has_island(db, bang_id: str) -> bool:
    """🏝️ Does this (active) bang hold its island: cấp ≥ 1, bought, or granted to the bangs from before 21/10. One
    primary-key read. The gate of everything played there (owner 21/10 "phải có mua đảo bang thì mới chơi được"): a
    visit, the pet arena, the Bang chiến pet; other branches call it too (keep the name and the signature)."""
    r = db.execute("SELECT isle FROM bangs WHERE id=? AND status='active'", (bang_id,)).fetchone()
    return bool(r) and int(r['isle'] or 0) >= 1


def finish_isle(db, bid: str, t: float) -> bool:
    """The island's upgrade whose time is up becomes its level (guarded by isle_to: idempotent, any process)."""
    r = _row(db, 'UPDATE bangs SET isle=isle_to, isle_to=NULL, isle_ready=NULL WHERE id=? AND isle_to IS NOT NULL AND isle_ready<=? '
                 'RETURNING isle', (bid, t))
    if not r:
        return False
    lv = int(r['isle'])
    _log(db, bid, '', 'built', f'🏝️ Đảo bang lên cấp {lv}: {C.ISLE_ZONES[lv - 1]}, {C.isle_cap(lv)} người cùng lúc.', t)
    _bump(db, bid)
    _isle(db, 'view', bid)
    return True


def isle_card(row: dict, t: float) -> dict:
    """The island for the bang's page: level, cap, what each level added, the upgrade being built, the next one."""
    cur = island_of(row, t)
    lv = cur['level']
    out = dict(level=lv, max=C.ISLE_MAX, cap=C.isle_cap(lv), how=cur['how'], zones=list(C.ISLE_ZONES[:lv]))
    if cur['to']:
        out.update(to=cur['to'], ready=cur['ready'], started=cur['started'] or t)
    if lv < C.ISLE_MAX:
        xu, secs = C.isle_cost(lv + 1)
        out.update(next=lv + 1, cost=xu, secs=secs, next_cap=C.isle_cap(lv + 1), next_zone=C.ISLE_ZONES[lv])
    return out


def levels(db, bid: str) -> dict:
    out = {f: 0 for f in C.FACILITIES}
    for r in _rows(db, 'SELECT fac, level FROM bang_facilities WHERE bang=?', (bid,)):
        if r['fac'] in out:
            out[r['fac']] = int(r['level'])
    out[C.HALL] = max(1, out[C.HALL])
    return out


def cap_of(lv: dict) -> int:
    return C.HALL_CAP[min(len(C.HALL_CAP) - 1, max(1, lv[C.HALL]))]


def fund_cap(lv: dict) -> int:
    """21/10: the fund has no cap (an older page still reads `fund_cap`: the technical ceiling)."""
    return C.FUND_MAX


def _chat_add(db, ch: str, sid: str, t: float) -> None:
    if ch:
        db.execute("INSERT INTO chat_members(channel, pid, sid, role, joined) VALUES(?, ?, ?, 'member', ?) ON CONFLICT(channel, pid) DO NOTHING",
                   (ch, pid_of(sid), sid, t))


def _chat_drop(db, ch: str, sid: str) -> None:
    if ch:
        db.execute('DELETE FROM chat_members WHERE channel=? AND pid=?', (ch, pid_of(sid)))


def _leave(db, sid: str, bang: dict, t: float, why: str) -> None:
    """Out of `bang` (its row locked by the caller): the title goes at once, points and items stay with that bang."""
    db.execute("UPDATE bang_members SET status='out', role='tv', left_at=?, why=? WHERE bang=? AND sid=? AND status='in'",
               (t, why, bang['id'], sid))
    db.execute('UPDATE bang_stints SET left_at=?, why=? WHERE bang=? AND sid=? AND left_at IS NULL', (t, why, bang['id'], sid))
    _chat_drop(db, bang['channel'], sid)
    word = {'leave': 'rời bang', 'switch': 'sang bang khác', 'kick': 'được mời ra khỏi bang', 'gone': 'rời phố'}.get(why, 'rời bang')
    _log(db, bang['id'], sid, 'leave', f'{_display(db, sid)} {word}.', t)
    _bump(db, bang['id'])
    _notify(db, pids=[pid_of(sid)], ch=bang['channel'], rm=[pid_of(sid)])
    _isle(db, 'kicked' if why == 'kick' else 'left', bang['id'], sid)
    _war_unpick(db, bang['id'], [sid], t)
    _noted_leave(sid, bang['id'], t)   # the bang's Giờ vàng stops counting for them now (no snapshot reset)


def day_start(t: float) -> float:
    d = datetime.datetime.fromtimestamp(t, VN).date()
    return datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp()


def joins_today(db, sid: str, t: float) -> int:
    """Bangs this player joined (or founded) this Vietnam day: one bang_stints row each (index bang_stints_sid)."""
    return int(db.execute('SELECT COUNT(*) AS n FROM bang_stints WHERE sid=? AND joined>=?', (sid, day_start(t))).fetchone()['n'])


def _switch_need(db, sid: str, t: float, how: str = 'join') -> None:
    """Joining stays free (owner 19/10), with a soft anti-churn cap: C.SWITCH_DAY_MAX bangs a Vietnam day."""
    if joins_today(db, sid, t) < C.SWITCH_DAY_MAX:
        return
    if how == 'approve':
        need(False, f'Hôm nay người này đã vào {C.SWITCH_DAY_MAX} bang rồi. Mai duyệt lại nhé.', 'switch_cap')
    need(False, f'Hôm nay bạn đã vào {C.SWITCH_DAY_MAX} bang rồi. Mai hãy đổi bang tiếp nhé (vào bang vẫn miễn phí).', 'switch_cap')


def _war_unpick(db, bid: str, sids: list, t: float) -> None:
    """🛡️ Their pet leaves the bang's lineup for this week's war while it is still open (game/pet_war.py: a pick
    counts only for a current member, the lineup's five slots free again)."""
    if not sids:
        return
    from . import pet_war
    if t >= pet_war.lock_of(t):
        return
    db.execute("DELETE FROM pet_war_picks WHERE week=? AND team_kind='bang' AND team_id=? AND sid = ANY(?)",
               (pet_war.A.vn_week(t), bid, list(sids)))


def _join(db, sid: str, bang: dict, t: float, locked: dict, how: str = 'join') -> None:
    """Into `bang` (the caller locked it, and the current bang if any): leaves the current one first."""
    mine = _mine(db, sid, lock=True)
    if mine and mine['bang'] == bang['id']:
        return
    need(bang['status'] == 'active' and not bang['hidden'], 'Bang này không còn nhận người.', 'closed')
    if mine:
        need(mine['role'] != 'chu', 'Bạn đang là Bang chủ: trao lại chức hoặc giải tán bang cũ trước nhé.', 'leader')
        old = locked.get(mine['bang'])
        need(old is not None, 'Thử lại nhé.', 'retry')
    _switch_need(db, sid, t, how)
    if mine:
        _leave(db, sid, old, t, 'switch')
    finish_builds(db, bang['id'], t)
    cap = cap_of(levels(db, bang['id']))
    need(_count(db, bang['id']) < cap, f'Bang {bang["name"]} đã đủ {cap} người.', 'full')
    db.execute("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?, ?, ?, 'in', 'tv', ?) "
               "ON CONFLICT(bang, sid) DO UPDATE SET status='in', role='tv', joined=excluded.joined, left_at=NULL, why=''",
               (bang['id'], sid, pid_of(sid), t))
    db.execute('INSERT INTO bang_stints(bang, sid, joined) VALUES(?,?,?)', (bang['id'], sid, t))
    db.execute("UPDATE bang_asks SET status='done', answered=? WHERE bang=? AND sid=? AND status='open'", (t, bang['id'], sid))
    _chat_add(db, bang['channel'], sid, t)
    _log(db, bang['id'], sid, 'join', f'{_display(db, sid)} vào bang.', t)
    _bump(db, bang['id'])
    _notify(db, pids=[pid_of(sid)], ch=bang['channel'], add=[pid_of(sid)])
    _isle(db, 'join', bang['id'], sid)


# ---------------------------------------------------------------- the paid commands, in the save's transaction
def command_commit(db, sid: str, action: str, after: dict, result) -> None:
    """Called by the storage layer for jr_bang_* commands, in the save's transaction (game/storage.py). A GameError
    here rolls the whole command back: nothing is paid."""
    if action not in COMMANDS:
        return
    e = _core()
    b = get(after)
    x = b['last'] if b else None
    info = (result or {}).get('bang') if isinstance(result, dict) else None
    if not x or not isinstance(info, dict) or info.get('n') != x['n'] or info.get('k') != x['k'] or info.get('r') != x.get('r'):
        return
    t = now()
    pid = pid_of(sid)
    if x['k'] == 'found':
        _found_commit(db, sid, pid, x, info, t)
    else:
        _give_commit(db, sid, pid, x, info, t)


def _found_commit(db, sid, pid, x, info, t) -> None:
    e = _core()
    from .bank_xfer import _old_enough
    e.need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone() is not None,
           'Cần đăng nhập tài khoản mới lập được bang.', 'account')
    e.need(_old_enough(db, sid, C.FOUND_ACCOUNT_DAYS), f'Tài khoản cần đủ {C.FOUND_ACCOUNT_DAYS} ngày (đời thực) mới lập được bang.', 'too_new')
    key = name_key(info['name'])
    db.execute(f'SELECT pg_advisory_xact_lock({LOCK}, hashtext(?))', (key,))   # two foundings of one name: one waits
    e.need(not db.execute("SELECT 1 FROM bangs WHERE key=? AND status='active'", (key,)).fetchone(),
           'Tên bang này đã có. Thử một tên khác nhé.', 'name_taken')
    mine = _mine(db, sid)
    locked = _lock(db, mine['bang']) if mine else {}
    e.need(joins_today(db, sid, t) < C.SWITCH_DAY_MAX, f'Hôm nay bạn đã vào {C.SWITCH_DAY_MAX} bang rồi. Mai hãy lập bang nhé.', 'switch_cap')
    if mine:
        e.need(mine['role'] != 'chu', 'Bạn đang là Bang chủ: trao lại chức hoặc giải tán bang cũ trước nhé.', 'leader')
        _leave(db, sid, locked[mine['bang']], t, 'switch')
    bid = 'b' + secrets.token_hex(5)
    ch = 'g:' + secrets.token_hex(5)
    # 🏝️ isle 0: a bang founded from 21/10 buys its island (the column's default 1 is the grant of the older bangs)
    db.execute("INSERT INTO bangs(id, name, key, emoji, color, motto, open, leader, created, created_by, channel, isle, isle_how) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?,0,'')",
               (bid, info['name'], key, info['emoji'], info['color'], info['motto'], 1 if info['open'] else 0, sid, t, sid, ch))
    db.execute("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?, ?, ?, 'in', 'chu', ?)", (bid, sid, pid, t))
    db.execute('INSERT INTO bang_stints(bang, sid, joined) VALUES(?,?,?)', (bid, sid, t))
    db.execute("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, ?, 1)", (bid, C.HALL))
    db.execute("INSERT INTO chat_channels(id, kind, title, owner_pid, created) VALUES(?, 'group', ?, 'bang', ?)",
               (ch, f'{info["emoji"]} {info["name"]}'[:40], t))
    _chat_add(db, ch, sid, t)
    who = _display(db, sid)
    _log(db, bid, sid, 'found', f'{who} lập bang (phí {fmt(x["a"])} xu).', t)
    mr._post_news(db, 'bang', f'bang:new:{bid}', f'⚔️ {who} vừa lập bang {info["emoji"]} {info["name"]}! Vào bang ở mục ⚔️ Bang nhé.', '', '')
    _notify(db, pids=[pid], ch=ch, add=[pid])
    _VIEW.clear()


def give_ref(pid: str, x: dict) -> str:
    """The deposit's ledger id: 'g:<pid>:<nonce>' (a block from before the nonce: 'g:<pid>:<n>', as it was)."""
    return f'g:{pid}:{x["r"]}' if x.get('r') else f'g:{pid}:{x["n"]}'


def _give_commit(db, sid, pid, x, info, t) -> None:
    e = _core()
    bid = info.get('bang')
    rows = _lock(db, bid)
    bang = rows.get(bid)
    e.need(bang is not None and bang['status'] == 'active', 'Bang này không còn nữa.', 'closed')
    me = _row(db, "SELECT * FROM bang_members WHERE bang=? AND sid=? AND status='in' FOR UPDATE", (bid, sid))
    e.need(me is not None, f'Bạn không còn ở bang {bang["name"]}. Mở lại mục ⚔️ Bang xem nhé.', 'not_member')
    finish_builds(db, bid, t)
    lv = levels(db, bid)
    # 21/10: no cap on the fund (C.FUND_MAX is a bigint's safety margin, never reached)
    e.need(int(bang['fund']) + x['a'] <= C.FUND_MAX, 'Quỹ bang đã quá lớn. Thử lại sau nhé.', 'fund_full')
    ref = give_ref(pid, x)
    bal = int(bang['fund']) + x['a']
    # A row with this id already there (cannot happen with a nonce): refuse, so the whole command rolls back and the
    # wallet is never debited without its deposit (review fix 19/10: an old `n` after reset_all / an older import).
    e.need(db.execute("INSERT INTO bang_fund(id, bang, sid, kind, amount, balance, at) VALUES(?,?,?,'give',?,?,?) ON CONFLICT DO NOTHING "
                      'RETURNING id', (ref, bid, sid, x['a'], bal, t)).fetchone() is not None,
           'Khoản góp này trùng mã với một khoản trước. Thử lại nhé.', 'retry')
    db.execute('UPDATE bangs SET fund=?, given=given+? WHERE id=?', (bal, x['a'], bid))
    pts = x['a'] // C.XU_PER_POINT * (100 + C.KHO_BONUS * lv['kho']) // 100
    if pts > 0:   # at most C.GIVE_PTS_DAY a Vietnam day from gifts, every bang together (the save row is locked: one at a time)
        today = int(db.execute("SELECT COALESCE(SUM(pts), 0) AS p FROM bang_points WHERE sid=? AND day=? AND kind='give'",
                               (sid, vn_day(t))).fetchone()['p'])
        pts = max(0, min(pts, C.GIVE_PTS_DAY - today))
    if pts > 0:
        db.execute('INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                   (ref, bid, sid, 'give', pts, vn_week(t), vn_day(t), t))
    db.execute("UPDATE bang_members SET points=points+?, earned=earned+?, given=given+? WHERE bang=? AND sid=?", (pts, pts, x['a'], bid, sid))
    if x['a'] >= 1_000_000:
        _log(db, bid, sid, 'give', f'{_display(db, sid)} góp {fmt(x["a"])} xu (+{fmt(pts)} điểm).', t)
    _bump(db, bid)


def work_commit(db, sid: str) -> None:
    """A work day closed (end_day, in the save's transaction): a few activity points a day for a member. Never raises
    for a player outside any bang (one indexed lookup)."""
    me = _row(db, "SELECT bang, pid FROM bang_members WHERE sid=? AND status='in' FOR UPDATE", (sid,))
    if not me:
        return
    t = now()
    day = vn_day(t)
    n = int(db.execute("SELECT COUNT(*) AS n FROM bang_points WHERE sid=? AND day=? AND kind='work'", (sid, day)).fetchone()['n'])
    if n >= C.WORK_DAYS:
        return
    _earn(db, me['bang'], sid, f'w:{me["pid"]}:{day}:{n + 1}', 'work', C.WORK_POINTS, t)


def _earn(db, bid: str, sid: str, ref: str, kind: str, pts: int, t: float) -> bool:
    if not db.execute('INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING '
                      'RETURNING id', (ref, bid, sid, kind, pts, vn_week(t), vn_day(t), t)).fetchone():
        return False
    db.execute('UPDATE bang_members SET points=points+?, earned=earned+? WHERE bang=? AND sid=?', (pts, pts, bid, sid))
    return True


# ---------------------------------------------------------------- ⏰ Giờ vàng của bang
GH_REFRESH = 60.0
GH_AHEAD = 3600.0                # windows starting within the next hour (set ≥ 1 h ahead: none is missed by a refresh)
GH_MARGIN = 3 * 3600.0           # windows that ended in the last 3 h stay in the shared snapshot
GH_WIN_MAX = 2000                # windows in the shared snapshot at most (newest first)
GH_STINT_MAX = 30_000            # membership spans in it at most (only those of the snapshot's bangs that can count)
GH_COLD_TTL = 1800.0             # a player's own older windows (offline catch-up) are read again after this (< GH_MARGIN − 1 h)
GH_COLD_MAX = 4096               # players whose older windows are kept (least recently used out first)
GH_GONE_MAX = 10_000
INF = float('inf')
# The shared snapshot (per process): {at, wins: {bang: ((gid, start, ends, name), …)}, stints: {sid: ((bang, joined,
# left_at | INF), …)}}. `gone`: this process's own leaves since (sid -> (bang, t, when noted)), applied on top until the
# next refresh has them. `_COLD`: sid -> (read at, ((gid, start, until, name), …)): the player's windows that had already
# ended when read (never changed again: a window cannot be cancelled once started, a later leave is after its end).
_GH: dict = dict(at=0.0, wins={}, stints={}, gone={})
_GH_LOCK = threading.Lock()      # guards the dicts' swaps
_GH_LOAD = threading.Lock()      # single flight: one thread a process reads the snapshot, the others use the one they have
_COLD: dict = {}
_CUR: contextvars.ContextVar = contextvars.ContextVar('bang_gh', default=())


def gh_reset() -> None:
    """Forget every snapshot (tests; an operator's repair)."""
    with _GH_LOCK:
        _GH.update(at=0.0, wins={}, stints={}, gone={})
        _COLD.clear()


def _load_hot(db, t: float) -> None:
    rows = db.execute("SELECT g.id AS id, g.bang AS bang, g.start AS start, g.ends AS ends, b.name AS name FROM bang_gh g "
                      "JOIN bangs b ON b.id=g.bang WHERE g.status='set' AND g.ends>=? AND g.start<=? ORDER BY g.start DESC LIMIT ?",
                      (t - GH_MARGIN, t + GH_AHEAD, GH_WIN_MAX)).fetchall()
    wins: dict = {}
    for r in rows:
        wins.setdefault(r['bang'], []).append((int(r['id']), float(r['start']), float(r['ends']), str(r['name'])))
    stints: dict = {}
    if wins:
        starts = [w[1] for v in wins.values() for w in v]
        for r in db.execute('SELECT bang, sid, joined, left_at FROM bang_stints WHERE bang = ANY(?) AND joined<=? '
                            'AND (left_at IS NULL OR left_at>?) ORDER BY joined DESC LIMIT ?',
                            (list(wins), max(starts) - C.GOLDEN_SENIORITY, min(starts), GH_STINT_MAX)).fetchall():
            stints.setdefault(r['sid'], []).append((r['bang'], float(r['joined']), INF if r['left_at'] is None else float(r['left_at'])))
    with _GH_LOCK:
        gone = {k: v for k, v in _GH['gone'].items() if v[2] >= t - GH_REFRESH}   # older ones: in this read already
        _GH.update(at=t, wins={k: tuple(v) for k, v in wins.items()}, stints={k: tuple(v) for k, v in stints.items()}, gone=gone)


def _load_cold(db, sid: str, t: float) -> None:
    rows = db.execute("SELECT g.id AS id, g.start AS start, g.ends AS ends, b.name AS name, s.left_at AS left_at FROM bang_stints s "
                      "JOIN bang_gh g ON g.bang=s.bang JOIN bangs b ON b.id=g.bang WHERE s.sid=? AND (s.left_at IS NULL OR s.left_at>?) "
                      "AND g.status='set' AND g.ends>? AND g.ends<=? AND g.start>=s.joined+? AND (s.left_at IS NULL OR g.start<s.left_at) "
                      'ORDER BY g.start DESC LIMIT 64', (sid, t - C.GOLDEN_LOOKBACK, t - C.GOLDEN_LOOKBACK, t, C.GOLDEN_SENIORITY)).fetchall()
    got = tuple((int(r['id']), float(r['start']), min(float(r['ends']), INF if r['left_at'] is None else float(r['left_at'])), str(r['name']))
                for r in rows)
    with _GH_LOCK:
        _COLD.pop(sid, None)
        _COLD[sid] = (t, got)
        while len(_COLD) > GH_COLD_MAX:
            _COLD.pop(next(iter(_COLD)))


def prepare(db, t: float | None = None, sid: str | None = None) -> None:
    """Before a command (game/storage.py, on the snapshot's connection, never inside the command's locked transaction):
    the shared snapshot of the windows on now (read at most once a minute per process, by one thread: the others go on
    with the one they have), and, for `sid`, the player's own windows that already ended (offline catch-up within
    C.GOLDEN_LOOKBACK: read again every GH_COLD_TTL). Never raises (a database without the tables: no windows)."""
    t = now() if t is None else t
    if t - _GH['at'] >= GH_REFRESH or _GH['at'] > t + GH_REFRESH:
        first = _GH['at'] == 0.0
        if _GH_LOAD.acquire(blocking=first):          # the very first read: wait for it; afterwards never wait
            try:
                if t - _GH['at'] >= GH_REFRESH or _GH['at'] > t + GH_REFRESH:
                    _load_hot(db, t)
            except Exception:  # noqa: BLE001 - an older schema: nobody has a window
                with _GH_LOCK:
                    _GH.update(at=t, wins={}, stints={})
            finally:
                _GH_LOAD.release()
    if sid:
        hit = _COLD.get(sid)
        if hit is None or t - hit[0] >= GH_COLD_TTL or hit[0] > t:
            try:
                _load_cold(db, sid, t)
            except Exception:  # noqa: BLE001
                with _GH_LOCK:
                    _COLD[sid] = (t, ())


def _hot_of(sid: str) -> list:
    """(gid, start, until, name, ends) of the shared snapshot's windows that count for `sid`: a window of a bang they
    joined at least C.GOLDEN_SENIORITY before it starts, until it ends or they left (whichever is first)."""
    wins, mine, gone = _GH['wins'], _GH['stints'].get(sid, ()), _GH['gone'].get(sid)
    out = []
    for bid, joined, left in mine:
        if gone and gone[0] == bid and gone[1] < left:
            left = gone[1]
        for gid, a, b, name in wins.get(bid, ()):
            if joined <= a - C.GOLDEN_SENIORITY and a < left:
                out.append((gid, a, min(b, left), name, b))
    return out


def windows(sid: str) -> tuple:
    """((start, until, bang name), …) of every window that counts for this player (the snapshot and their older ones)."""
    seen, out = set(), []
    for gid, a, u, name, *_ in list(_hot_of(sid)) + list((_COLD.get(sid) or (0, ()))[1]):
        if gid not in seen and u > a:
            seen.add(gid)
            out.append((a, u, name))
    out.sort()
    return tuple(out)


def _noted_leave(sid: str, bid: str, t: float) -> None:
    """A leave this process wrote: the shared snapshot stops counting the player's windows of that bang from `t` at
    once (other processes: at their next refresh, within GH_REFRESH)."""
    with _GH_LOCK:
        if len(_GH['gone']) >= GH_GONE_MAX:
            _GH['gone'] = {}
        _GH['gone'] = dict(_GH['gone'], **{sid: (bid, t, now())})


def _noted_cancel(bid: str, gid: int | None = None, after: float = 0.0) -> None:
    """Windows of one bang cancelled (one, or every one starting after `after`: a disband): out of this process's
    snapshot now (a window already on stays: what was booked before the members left still counts)."""
    with _GH_LOCK:
        cur = _GH['wins'].get(bid)
        if cur:
            keep = tuple(w for w in cur if (w[0] != gid if gid is not None else w[1] <= after))
            _GH['wins'] = dict(_GH['wins'], **{bid: keep})


def bind(sid: str):
    """The command computing this save books this player's windows (storage._compute). Returns the token to reset."""
    return _CUR.set(windows(sid))


def unbind(token) -> None:
    _CUR.reset(token)


def gold_mult(t: float) -> int:
    """×2 (hundredths) at time t inside one of the bound save's bang windows (while still a member), else 100."""
    for a, b, _ in _CUR.get():
        if a <= t < b:
            return C.GOLDEN_MULT
    return 100


def gold_now(store, sid: str, t: float | None = None) -> dict | None:
    """{name, ends, minutes} of my bang window on now (the ticker), from the minute's snapshot."""
    t = now() if t is None else t
    if t - _GH['at'] >= GH_REFRESH:
        with store.connect() as db:
            prepare(db, t)
    for gid, a, until, name, ends in _hot_of(sid):
        if a <= t < until:
            return dict(name=name, ends=ends, minutes=int(round((ends - a) / 60)))
    return None


def news_line(g: dict) -> str:
    return f"⏰ Giờ vàng của bang {g['name']}: lãi tiệm và quầy ×2 trong {g['minutes']} phút!"


def _gh_rules(lv: dict) -> tuple[int, int]:
    return C.GOLDEN[min(len(C.GOLDEN) - 1, lv['den_vang'])]


# ---------------------------------------------------------------- 👑 Bang mạnh nhất tuần
_VIEW: dict = {}
_VIEW_LOCK = threading.Lock()
VIEW_SECS = 15.0


def _cached(key, fn):
    with _VIEW_LOCK:
        hit = _VIEW.get(key)
        if hit and time.monotonic() - hit[0] < VIEW_SECS:
            return hit[1]
    out = fn()
    with _VIEW_LOCK:
        if len(_VIEW) > 64:
            _VIEW.clear()
        _VIEW[key] = (time.monotonic(), out)
    return out


EARN_KINDS = ('give', 'checkin', 'work', 'chal')   # 🙌 Cống hiến: điểm cống hiến members earn (never what they spend)


def war_scores(db, week: str, t: float | None = None) -> dict:
    """{bang id: points} from that week's 🛡️ Bang chiến pet (game/pet_war.py: its day and hour are pet_war's), once it is
    over by `t` (its results are fixed at the lock but shown only as the matches play: never sooner here either): the
    team ladder's points (a win PTS_WIN, the champion PTS_CHAMP more) × C.PET_WAR_SCORE."""
    from . import pet_war
    t = now() if t is None else t
    war = _row(db, "SELECT * FROM pet_war WHERE week=? AND status='done'", (week,))
    if not war or pet_war.end_of(war) > t:
        return {}
    return {r['team_id']: int(r['pts']) * C.PET_WAR_SCORE
            for r in _rows(db, "SELECT team_id, pts FROM pet_team_ladder WHERE week=? AND team_kind='bang' AND pts>0", (week,))}


def power(db, bids=None) -> dict:
    """💪 Chiến lực {bang id: power} now: the sum of the strongest pet power of each current member (the top C.POWER_TOP
    members), from pet_power (game/pet_arena.py power_commit: refreshed by every jr_pet_* command and arena visit) or
    the member's pet on the Thách đấu roster when higher. A member who left counts no more at once. One query, no save."""
    rows = _rows(db, "SELECT m.bang AS bang, GREATEST(COALESCE(p.pw, 0), COALESCE(r.pw, 0)) AS pw FROM bang_members m "
                     "LEFT JOIN pet_power p ON p.sid=m.sid LEFT JOIN bang_chal_roster r ON r.bang=m.bang AND r.sid=m.sid AND r.ok=1 "
                     "WHERE m.status='in'" + (' AND m.bang = ANY(?)' if bids is not None else ''), (list(bids),) if bids is not None else ())
    by: dict = {}
    for r in rows:
        by.setdefault(r['bang'], []).append(int(r['pw'] or 0))
    return {b: sum(sorted(v, reverse=True)[:C.POWER_TOP]) for b, v in by.items()}


ISLE_COLS = 'isle, isle_to, isle_ready, isle_started, isle_how'


def _isle_level(row: dict | None, t: float) -> int:
    """⭐ The bang's 🏝️ Đảo bang level for Cấp bang (owner 21/10: pets, công trình and cấp bang only), from its bangs row
    (bangs.isle, an upgrade whose time is up counting as done: island_of); 0 when not bought."""
    return island_of(row, t)['level'] if row else 0


def _part(bid: str, war: int, chal: int, pw: int, fac: dict, isle: int = 0) -> dict:
    """One bang's three parts (game/bang_content.py: the weights) and its score: 🐾 pets, 🏗️ công trình, ⭐ cấp bang."""
    pets = war + chal + pw // C.POWER_DIV
    levels = sum(v for k, v in fac.items() if k in C.FACILITIES and k != C.HALL)
    build = C.FAC_SCORE * levels
    hall = max(1, int(fac.get(C.HALL, 1) or 1))
    level = C.LEVEL_SCORE * (hall + isle)
    tuong = fac.get('tuong', 0)
    return dict(bang=bid, score=(pets + build + level) * (100 + C.TUONG_BONUS * tuong) // 100, pets=pets, war=war, chal=chal,
                power=pw, build=build, levels=levels, level=level, hall=hall, island=isle, tuong=C.TUONG_BONUS * tuong)


def standings(db, week: str, t: float | None = None) -> list:
    """👑 Bang mạnh nhất tuần (owner 21/10: "đừng để cống hiến bang tính điểm nhé, hãy tính điểm của pets, công trình và cấp
    bang làm điểm nhé"): the active, shown bangs founded before the week's end, best first, each with its three parts,
    heaviest first: 🐾 Pets (the week's pet war once shown + its ⚔️ Thách đấu + 💪 chiến lực), 🏗️ Công trình (facility
    levels but the hall), ⭐ Cấp bang (the Đại sảnh's level, + the island's); the sum × the Tượng bang's bonus. Điểm cống
    hiến never counts. Ties: more pets points, then the older bang."""
    from . import bang_challenge
    war = war_scores(db, week, t)
    chal = bang_challenge.chal_scores(db, week)
    fac: dict = {}
    for r in _rows(db, 'SELECT f.bang AS bang, f.fac AS fac, f.level AS level FROM bang_facilities f JOIN bangs b ON b.id=f.bang '
                       "WHERE b.status='active' AND b.hidden=0"):
        fac.setdefault(r['bang'], {})[r['fac']] = int(r['level'])
    t = now() if t is None else t
    live = {r['id']: r for r in _rows(db, f"SELECT id, created, {ISLE_COLS} FROM bangs WHERE status='active' AND hidden=0 AND created<?",
                                      (week_end(week),))}   # a bang founded after that week is not in it
    pw = power(db, list(live)) if live else {}
    out = [dict(_part(b, war.get(b, 0), chal.get(b, 0), pw.get(b, 0), fac.get(b, {}), _isle_level(r, t)), created=float(r['created']))
           for b, r in live.items()]
    out.sort(key=lambda x: (-x['score'], -x['pets'], x['created'], x['bang']))
    return out


def week_of(db, bid: str, week: str, t: float | None = None) -> dict:
    """One bang's three parts this week (its page: a few small indexed queries)."""
    from . import bang_challenge
    fac = {x['fac']: int(x['level']) for x in _rows(db, 'SELECT fac, level FROM bang_facilities WHERE bang=?', (bid,))}
    t = now() if t is None else t
    return _part(bid, war_scores(db, week, t).get(bid, 0), bang_challenge.chal_scores(db, week).get(bid, 0),
                 power(db, [bid]).get(bid, 0), fac, _isle_level(_row(db, f'SELECT {ISLE_COLS} FROM bangs WHERE id=?', (bid,)), t))


def scores(db, week: str) -> list:
    """[(bang id, score)] of standings, best first (the weekly freeze, the lists)."""
    return [(x['bang'], x['score']) for x in standings(db, week)]


def freeze(db, t: float) -> dict | None:
    """Last week's winner, written once (any process): its members wear the title this week."""
    week = prev_week(t)
    r = _row(db, 'SELECT * FROM bang_week_win WHERE week=?', (week,))
    if r:
        return r
    db.execute(f'SELECT pg_advisory_xact_lock({LOCK}, hashtext(?))', ('week:' + week,))
    r = _row(db, 'SELECT * FROM bang_week_win WHERE week=?', (week,))
    if r:
        return r
    best = next(((b, s) for b, s in scores(db, week) if s > 0), None)
    if not best:
        return None
    db.execute('INSERT INTO bang_week_win(week, bang, score, at) VALUES(?,?,?,?) ON CONFLICT DO NOTHING', (week, best[0], best[1], t))
    name = _row(db, 'SELECT name, emoji FROM bangs WHERE id=?', (best[0],))
    if name:
        mr._post_news(db, 'bang', f'bang:week:{week}', f'👑 Bang mạnh nhất tuần: {name["emoji"]} {name["name"]} ({fmt(best[1])} điểm)!', '', '')
    from . import live_chat
    live_chat.notify(db, dict(op='bang_crown'))
    return _row(db, 'SELECT * FROM bang_week_win WHERE week=?', (week,))


def crown(store, t: float | None = None) -> str | None:
    """The bang holding 👑 this week (last week's winner), cached."""
    t = now() if t is None else t

    def run():
        try:
            with store.connect() as db:   # frozen already (every day of the week but its first minutes): a read only
                r = _row(db, 'SELECT * FROM bang_week_win WHERE week=?', (prev_week(t),))
            return r or store.transaction(lambda db: freeze(db, t))
        except Exception:  # noqa: BLE001 - the page never fails for this
            return None
    r = _cached(('crown', prev_week(t)), run)
    return r['bang'] if r else None


# ---------------------------------------------------------------- views
def color(cid: str) -> dict:
    c = C.COLORS.get(cid) or C.COLORS['do']
    return dict(id=cid if cid in C.COLORS else 'do', name=c[0], hex=c[1], ink=c[2], wear=c[3], paint=c[4])


def tag(row: dict, role: str = '', crowned: bool = False, wear: int = 0) -> dict:
    """The small public tag beside a name: {n, e, c (colour id), r (role), k (👑), b (badge worn)}."""
    out = dict(id=row['id'], n=row['name'], e=row['emoji'], c=row['color'] if row['color'] in C.COLORS else 'do', r=role or 'tv')
    if crowned:
        out['k'] = 1
    if wear & C.WEAR_BITS['huy']:
        out['b'] = 1
    if wear & C.WEAR_BITS['ao']:
        out['u'] = 1
    return out


def tag_of(store, db, sid: str) -> dict | None:
    """A player's bang tag now (the game's profile page)."""
    try:
        r = _row(db, "SELECT b.id, b.name, b.emoji, b.color, b.hidden, m.role, m.wear FROM bang_members m JOIN bangs b ON b.id=m.bang "
                     "WHERE m.sid=? AND m.status='in' AND b.status='active'", (sid,))
    except Exception:  # noqa: BLE001 - an older schema
        return None
    if not r or r['hidden']:
        return None
    return tag(r, r['role'], crown(store) == r['id'], int(r['wear']))


def catalogue() -> dict:
    return dict(fee=C.FOUND_FEE, account_days=C.FOUND_ACCOUNT_DAYS, name=[C.NAME_MIN, C.NAME_MAX], motto=C.MOTTO_MAX,
                emojis=list(C.EMOJIS), colors=[color(k) for k in C.COLORS],
                roles={k: dict(name=v[0], short=v[1], seats=v[2], rank=v[3]) for k, v in C.ROLES.items()},
                give=dict(min=C.GIVE_MIN, max=C.GIVE_MAX, presets=list(C.GIVE_PRESETS), per_point=C.XU_PER_POINT, day_pts=C.GIVE_PTS_DAY),
                isle=dict(max=C.ISLE_MAX, prices=list(C.ISLE_PRICES), hours=list(C.ISLE_HOURS), caps=list(C.ISLE_CAP[1:]),
                          zones=list(C.ISLE_ZONES), gate=list(C.ISLE_GATE)),
                points=dict(checkin=C.CHECKIN_POINTS, work=C.WORK_POINTS, work_days=C.WORK_DAYS, day_max=C.ACTIVITY_DAY_MAX),
                facilities=[dict(id=f, name=C.FACILITIES[f]['name'], emoji=C.FACILITIES[f]['emoji'], blurb=C.FACILITIES[f]['blurb'],
                                 max=C.max_level(f)) for f in C.FAC_ORDER],
                items=[dict(id=i, name=C.ITEMS[i][0], emoji=C.ITEMS[i][1], price=C.ITEMS[i][2], needs=C.ITEMS[i][3], kind=C.ITEMS[i][4])
                       for i in C.ITEM_ORDER],
                uniforms=[dict(id=u, name=C.UNIFORMS[u][0], top=C.UNIFORMS[u][1], level=C.UNIFORMS[u][2]) for u in C.UNIFORM_ORDER],
                golden=dict(mult=C.GOLDEN_MULT, ahead=C.GOLDEN_AHEAD_MIN, max_ahead=C.GOLDEN_AHEAD_MAX, step=C.GOLDEN_STEP),
                title=C.WEEK_TITLE)


def _price(item: str, lv: dict) -> int:
    base = C.ITEMS[item][2]
    if item in C.SEWN:
        base = base * (100 - C.XUONG_OFF * lv['xuong_may']) // 100
    return max(1, base)


def _unlocked(item: str, lv: dict) -> bool:
    n = C.ITEMS[item][3]
    return n is None or lv.get(n[0], 0) >= n[1]


PARTS = ('pets', 'build', 'level', 'power', 'war', 'chal', 'levels', 'hall', 'island', 'tuong')


def _card(r: dict, n: int, cap: int, score: int = 0, rank: int = 0, part: dict | None = None) -> dict:
    rules = rules_of(r)
    return dict(id=r['id'], name=r['name'], emoji=r['emoji'], color=r['color'], motto=r['motto'], open=rules['mode'] == 'auto',
                mode=rules['mode'], req=req_lines(rules), n=n, cap=cap, score=score, rank=rank, isle=island_of(r, now())['level'],
                **{k: int((part or {}).get(k) or 0) for k in PARTS})


def search(store, sid: str | None, q: str = '') -> list:
    """Active, shown bangs, the week's strongest first (a name filter folds case and diacritics)."""
    t = now()
    key = name_key(q or '')[:20]

    def run():
        with store.connect() as db:
            rows = _rows(db, "SELECT * FROM bangs WHERE status='active' AND hidden=0")
            counts = {r['bang']: int(r['n']) for r in _rows(db, "SELECT bang, COUNT(*) AS n FROM bang_members WHERE status='in' GROUP BY bang")}
            halls = {r['bang']: int(r['level']) for r in _rows(db, 'SELECT bang, level FROM bang_facilities WHERE fac=?', (C.HALL,))}
            sc = standings(db, vn_week(t))
        order = {x['bang']: (i + 1, x) for i, x in enumerate(sc)}
        out = []
        for r in rows:
            rank, x = order.get(r['id'], (len(order) + 1, dict(score=0)))
            out.append(_card(r, counts.get(r['id'], 0), C.HALL_CAP[min(5, max(1, halls.get(r['id'], 1)))], x['score'], rank, x))
        out.sort(key=lambda c: (c['rank'], c['name']))
        return out
    cards = _cached(('search', vn_week(t)), run)
    if key:
        cards = [c for c in cards if key in name_key(c['name'])]
    return cards[:SEARCH_MAX]


def board(store, t: float | None = None) -> dict:
    t = now() if t is None else t

    def run():
        with store.connect() as db:
            sc = standings(db, vn_week(t))[:C.BOARD_TOP]
            names = {r['id']: r for r in _rows(db, "SELECT id, name, emoji, color FROM bangs WHERE status='active'")}
        return [dict(rank=i + 1, id=x['bang'], name=names[x['bang']]['name'], emoji=names[x['bang']]['emoji'], color=names[x['bang']]['color'],
                     score=x['score'], **{k: x[k] for k in PARTS})
                for i, x in enumerate(sc) if x['bang'] in names]
    top = _cached(('board', vn_week(t)), run)
    holder = crown(store, t)
    return dict(week=vn_week(t), ends=week_start(t) + 7 * 86400, top=top, crown=holder,
                weights=dict(war=C.PET_WAR_SCORE, chal=C.CHAL_WIN, power_div=C.POWER_DIV, fac=C.FAC_SCORE, level=C.LEVEL_SCORE, tuong=C.TUONG_BONUS))


def _seen(updated_at) -> float | None:
    """A member's last activity (the save's last write, UTC text), to the quarter hour (members see 'hôm nay', '3 ngày')."""
    try:
        at = datetime.datetime.strptime(str(updated_at)[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp()
    except ValueError:
        return None
    return float(int(at // 900) * 900)


def _members(db, bid: str, t: float) -> list:
    week = vn_week(t)
    wk = {r['sid']: int(r['p']) for r in _rows(db, "SELECT sid, SUM(pts) AS p FROM bang_points WHERE bang=? AND week=? AND pts>0 "
                                                  "AND kind IN ('give','checkin','work','chal') GROUP BY sid", (bid, week))}
    rows = _rows(db, "SELECT m.sid, m.pid, m.role, m.joined, m.points, m.earned, m.given, a.display, s.updated_at AS seen FROM bang_members m "
                     "LEFT JOIN accounts a ON a.sid=m.sid LEFT JOIN sessions s ON s.sid=m.sid WHERE m.bang=? AND m.status='in'", (bid,))
    out = [dict(pid=r['pid'], name=str(r['display'])[:24] if r['display'] else GONE, role=r['role'], joined=float(r['joined']),
                earned=int(r['earned']), given=int(r['given']), week=wk.get(r['sid'], 0), last=_seen(r['seen'])) for r in rows]
    out.sort(key=lambda m: (-_rank(m['role']), -m['week'], m['joined']))
    return out


def _facilities(db, bid: str, t: float) -> list:
    rows = {r['fac']: r for r in _rows(db, 'SELECT * FROM bang_facilities WHERE bang=?', (bid,))}
    lv = levels(db, bid)
    out = []
    for f in C.FAC_ORDER:
        r = rows.get(f)
        level = lv[f]
        top = C.max_level(f)
        nxt = level + 1 if level < top else None
        d = dict(id=f, level=level, max=top, perk=C.perk(f, level))
        if r and r['target'] is not None:
            d.update(building=int(r['target']), ready=float(r['ready_at']), started=float(r['started']))
        if nxt:
            xu, secs = C.cost(f, nxt)
            d.update(next=nxt, cost=xu, secs=secs, hall=C.hall_needed(f, nxt), isle=C.isle_needed(f, nxt), next_perk=C.perk(f, nxt))
        out.append(d)
    return out


def _gh_list(db, bid: str, t: float) -> list:
    return [dict(id=int(r['id']), start=float(r['start']), ends=float(r['ends'])) for r in _rows(
        db, "SELECT id, start, ends FROM bang_gh WHERE bang=? AND status='set' AND ends>? ORDER BY start LIMIT 20", (bid, t))]


def _items_of(db, sid: str) -> list:
    rows = _rows(db, 'SELECT i.bang, i.item, i.n, b.name, b.emoji, b.color FROM bang_items i JOIN bangs b ON b.id=i.bang '
                     'WHERE i.sid=? ORDER BY i.at', (sid,))
    return [dict(bang=r['bang'], item=r['item'], n=int(r['n']), bang_name=r['name'], bang_emoji=r['emoji'], bang_color=r['color'])
            for r in rows if r['item'] in C.ITEMS]


def page(store, sid: str, bid: str | None = None) -> dict:
    """A bang's page for me: everything when I am a member, its public card otherwise."""
    t = now()
    with store.connect() as db:
        mine = _mine(db, sid) if sid else None
        bid = bid or (mine['bang'] if mine else None)
        if not bid:
            return {}
        r = _row(db, 'SELECT * FROM bangs WHERE id=?', (bid,))
        need(r is not None and (r['status'] == 'active' and not r['hidden'] or (mine and mine['bang'] == bid)), 'Không tìm thấy bang này.', 'not_found', 404)
        due = r['status'] == 'active' and builds_due(db, bid, t)
    if due:   # a write transaction only when a build's time is up (a page read otherwise writes nothing); the bang row first
        store.transaction(lambda db: (_lock(db, bid), finish_builds(db, bid, t)))
    with store.connect() as db:
        if due:
            r = _row(db, 'SELECT * FROM bangs WHERE id=?', (bid,)) or r
        lv = levels(db, bid)
        n, cap = _count(db, bid), cap_of(lv)
        wk = week_of(db, bid, vn_week(t), t)
        out = dict(bang=_card(r, n, cap, wk['score'], 0, wk),
                   member=bool(mine and mine['bang'] == bid), leader_name=_display(db, r['leader']),
                   levels=lv, color=color(r['color']), created=float(r['created']), status=r['status'], isle=isle_card(r, t))
        if not out['member']:
            ask = _row(db, "SELECT kind FROM bang_asks WHERE bang=? AND sid=? AND status='open'", (bid, sid)) if sid else None
            out.update(asked=bool(ask and ask['kind'] == 'ask'), invited=bool(ask and ask['kind'] == 'invite'),
                       members=_members(db, bid, t)[:10])
            return out
        me = _row(db, 'SELECT * FROM bang_members WHERE bang=? AND sid=?', (bid, sid))
        owned = {x['item']: x['n'] for x in _items_of(db, sid) if x['bang'] == bid}
        day = vn_day(t)
        act = int(db.execute("SELECT COALESCE(SUM(pts), 0) AS p FROM bang_points WHERE sid=? AND day=? AND kind IN ('checkin','work')",
                             (sid, day)).fetchone()['p'])
        checked = db.execute("SELECT 1 FROM bang_points WHERE id=?", (f'c:{pid_of(sid)}:{day}',)).fetchone() is not None
        out.update(
            me=dict(pid=pid_of(sid), role=me['role'], points=int(me['points']), earned=int(me['earned']), given=int(me['given']), wear=int(me['wear']),
                    uniform=me['uniform'], checkin=checked, today=act, today_max=C.ACTIVITY_DAY_MAX),
            fund=int(r['fund']), fund_cap=fund_cap(lv), given=int(r['given']), spent=int(r['spent']), channel=r['channel'],
            members=_members(db, bid, t), facilities=_facilities(db, bid, t),
            shop=[dict(id=i, price=_price(i, lv), unlocked=_unlocked(i, lv), owned=owned.get(i, 0)) for i in C.ITEM_ORDER],
            golden=dict(list=_gh_list(db, bid, t), per_week=_gh_rules(lv)[0], minutes=_gh_rules(lv)[1]),
            rules=rules_of(r), chal=_chal_card(db, bid, sid, me['role'], t),
            log=[dict(text=x['text'], at=float(x['at']), kind=x['kind']) for x in _rows(
                db, 'SELECT text, at, kind FROM bang_log WHERE bang=? ORDER BY id DESC LIMIT ?', (bid, LOG_SHOWN))],
            slots=C.build_slots(lv[C.HALL]), phao_at=float(r['phao_at']))
        if _rank(me['role']) >= C.APPROVE_FROM:
            out['asks'] = [dict(pid=pid_of(x['sid']), name=str(x['display'])[:24] if x['display'] else GONE, at=float(x['at'])) for x in _rows(
                db, "SELECT k.sid, k.at, a.display FROM bang_asks k LEFT JOIN accounts a ON a.sid=k.sid WHERE k.bang=? AND k.kind='ask' "
                    "AND k.status='open' ORDER BY k.at LIMIT 50", (bid,))]
    out['crowned'] = crown(store, t) == bid
    return out


def _chal_card(db, bid: str, sid: str, role: str, t: float) -> dict | None:
    """⚔️ Thách đấu bang's card on the home tab (game/bang_challenge.py card)."""
    from . import bang_challenge
    if bang_challenge.off():
        return None
    return bang_challenge.card(db, bid, sid, role, t)


def me_view(store, token) -> dict:
    """GET /api/bang/me: my membership (the client's tag, uniform, flag, boat paint), invitations, my items."""
    sid, display = mr.whoami(store, token)
    t = now()
    out = dict(now=t, account=bool(display), catalogue=catalogue())
    if off():
        return dict(out, off=True, message=OFF_TEXT)
    if not sid:
        return out
    with store.connect() as db:
        try:
            mine = _row(db, "SELECT m.*, b.name, b.emoji, b.color, b.channel, b.hidden, b.isle, b.isle_to, b.isle_ready, b.isle_started, "
                            "b.isle_how FROM bang_members m JOIN bangs b ON b.id=m.bang WHERE m.sid=? AND m.status='in'", (sid,))
        except Exception:  # noqa: BLE001 - an older schema: no bangs yet
            return out
        out['invites'] = [dict(bang=x['bang'], name=x['name'], emoji=x['emoji'], color=x['color'], by=str(x['display'] or GONE)[:24])
                          for x in _rows(db, "SELECT k.bang, b.name, b.emoji, b.color, a.display FROM bang_asks k JOIN bangs b ON b.id=k.bang "
                                             "LEFT JOIN accounts a ON a.sid=k.by_sid WHERE k.sid=? AND k.kind='invite' AND k.status='open' "
                                             "AND b.status='active' AND b.hidden=0 ORDER BY k.at DESC LIMIT 20", (sid,))]
        out['items'] = _items_of(db, sid)
        if mine:
            lv = levels(db, mine['bang'])
            out['mine'] = dict(bang=mine['bang'], pid=pid_of(sid), name=mine['name'], emoji=mine['emoji'], color=color(mine['color']), role=mine['role'],
                               wear=int(mine['wear']), uniform=mine['uniform'] if mine['uniform'] in C.UNIFORMS else 'polo',
                               points=int(mine['points']), channel=mine['channel'], pet=lv['san_pet'], isle=island_of(mine, t)['level'],
                               uniforms=[u for u in C.UNIFORM_ORDER if C.UNIFORMS[u][2] <= lv['xuong_may']])
            if _rank(mine['role']) >= C.APPROVE_FROM and not mine['hidden']:   # ⚔️ challenges waiting for an answer (the menu's badge)
                from . import bang_challenge
                out['mine']['tc_in'] = bang_challenge.incoming_count(db, mine['bang'], t)
    if mine:
        g = gold_now(store, sid, t)
        out['mine']['golden'] = g
        out['mine']['crowned'] = crown(store, t) == mine['bang']
    return out


def member_perks(store, sid: str) -> dict | None:
    """For other systems: {bang, role, pet (Sân luyện pet level)} of a member, or None. The pet war reads the bang through
    game/bang_pets.py (its TeamProvider), not this."""
    with store.connect() as db:
        m = _mine(db, sid)
        if not m:
            return None
        lv = levels(db, m['bang'])
    return dict(bang=m['bang'], role=m['role'], pet=lv['san_pet'], hall=lv[C.HALL])


def get_view(store, token, query: dict) -> dict:
    """GET /api/bang?q= (search), ?id= (a bang's page), ?board=1, else me + my bang's page."""
    need(not off(), OFF_TEXT, 'off', 503)
    sid, _ = mr.whoami(store, token)
    q = query or {}
    if q.get('board'):
        return board(store)
    if 'q' in q or q.get('list'):
        return dict(list=search(store, sid, str(q.get('q') or '')[:30]), board=board(store))
    bid = q.get('id')
    if bid:
        need(isinstance(bid, str) and ID_RE.fullmatch(bid), 'Không tìm thấy bang này.', 'not_found', 404)
        return page(store, sid, bid)
    if q.get('friends'):
        return dict(friends=_friends(store, sid))
    if q.get('careers'):   # 🚪 the requirement picker: careers and their real promotion ladders
        return dict(careers=ladder(), modes=dict(C.JOIN_MODES), days_max=C.REQ_DAYS_MAX)
    if q.get('found'):
        return dict(found=found_check(store, token))
    out = me_view(store, token)
    if out.get('mine'):
        out['page'] = page(store, sid)
    else:
        out['list'] = search(store, sid)
    out['board'] = board(store)
    return out


def found_check(store, token) -> dict:
    """The Lập bang checklist (GET /api/bang?found=1, read only when the form opens: it parses the save once)."""
    sid, display = mr.whoami(store, token)
    out = dict(account=bool(display), days=C.FOUND_ACCOUNT_DAYS, days_ok=False, title=False, title_name='', money=0, fee=C.FOUND_FEE)
    if not sid:
        return out
    from .bank_xfer import _old_enough
    with store.connect() as db:
        out['days_ok'] = bool(display) and _old_enough(db, sid, C.FOUND_ACCOUNT_DAYS)
        r = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    if r:
        try:
            born = datetime.datetime.strptime(str(r['created_at'])[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp()
            out['age'] = max(0, int((time.time() - born) // 86400))
        except ValueError:
            pass
    s = store.read(token)[0]
    out['title'] = has_title(s)
    if out['title']:
        from . import promotion
        best = max(((promotion.rank(s, c, k), k) for k, c in (s.get('careers') or {}).items() if isinstance(c, dict)), default=(0, ''))
        if best[0] >= 1:
            out['title_name'] = promotion.title(s, s['careers'][best[1]], best[1], best[0])
    from . import bank as bk
    j = s['journey']
    b = bk.get(s)
    out['money'] = (max(0, j['wallet']) + (b['balance'] if b else 0)) if j['wallet'] >= 0 else 0
    return out


def _friends(store, sid: str | None) -> list:
    if not sid:
        return []
    with store.connect() as db:
        rows = _rows(db, "SELECT f.friend AS sid, a.display, p.code, (SELECT m.bang FROM bang_members m WHERE m.sid=f.friend AND m.status='in') AS bang "
                         'FROM friends f JOIN accounts a ON a.sid=f.friend LEFT JOIN marriage_people p ON p.sid=f.friend '
                         'WHERE f.sid=? ORDER BY f.since DESC LIMIT 100', (sid,))
    return [dict(code=r['code'], name=str(r['display'])[:24], bang=r['bang'] or '') for r in rows if r['code']]


# ---------------------------------------------------------------- database operations (POST /api/bang/<op>)
def _actor(store, token) -> str:
    sid, display = mr.whoami(store, token)
    need(sid and display, 'Đăng nhập tài khoản để vào bang nhé.', 'login_required', 401)
    return sid


def _need_member(db, sid: str, locked_bang: str | None = None) -> dict:
    me = _mine(db, sid, lock=True)
    need(me is not None, 'Bạn chưa ở bang nào.', 'not_member')
    need(locked_bang is None or me['bang'] == locked_bang, 'Bạn không ở bang này.', 'not_member')
    return me


def _op_join(db, sid, data, t):
    bid = data.get('bang')
    need(isinstance(bid, str) and ID_RE.fullmatch(bid), 'Chọn một bang nhé.')
    mine = _mine(db, sid)
    locked = _lock(db, bid, mine['bang'] if mine else None)
    bang = locked.get(bid)
    need(bang is not None and bang['status'] == 'active' and not bang['hidden'], 'Không tìm thấy bang này.', 'not_found', 404)
    if mine and mine['bang'] == bid:
        return dict(message=f'Bạn đã ở bang {bang["name"]} rồi.')
    rules = rules_of(bang)
    invite = _row(db, "SELECT 1 FROM bang_asks WHERE bang=? AND sid=? AND kind='invite' AND status='open'", (bid, sid))
    # 🚫 closed: nobody joins or asks (an invitation still opens the door); the requirements hold for everyone
    need(invite or rules['mode'] != 'closed', f'Bang {bang["name"]} đang đóng, không nhận thêm người.', 'closed_bang')
    problem = req_problem(rules, data.get('_who'))
    need(not problem, problem, 'requirements')
    if rules['mode'] == 'auto' or invite:
        _join(db, sid, bang, t, locked)
        return dict(message=f'{bang["emoji"]} Chào mừng bạn vào bang {bang["name"]}!', joined=bid)
    db.execute("INSERT INTO bang_asks(bang, sid, kind, by_sid, status, at) VALUES(?, ?, 'ask', ?, 'open', ?) "
               "ON CONFLICT(bang, sid, kind) DO UPDATE SET status='open', at=excluded.at, answered=NULL", (bid, sid, sid, t))
    _bump(db, bid)
    return dict(message=f'Đã xin vào bang {bang["name"]}. Chờ bang duyệt nhé.', asked=bid)


def _op_cancel(db, sid, data, t):
    bid = data.get('bang')
    need(isinstance(bid, str) and ID_RE.fullmatch(bid), 'Chọn một bang nhé.')
    n = db.execute("UPDATE bang_asks SET status='cancelled', answered=? WHERE bang=? AND sid=? AND kind='ask' AND status='open'", (t, bid, sid)).rowcount
    need(n, 'Không có đơn xin vào nào để hủy.', 'none')
    return dict(message='Đã hủy đơn xin vào bang.')


def _op_accept(db, sid, data, t):
    bid = data.get('bang')
    need(isinstance(bid, str) and ID_RE.fullmatch(bid), 'Chọn một bang nhé.')
    need(_row(db, "SELECT 1 FROM bang_asks WHERE bang=? AND sid=? AND kind='invite' AND status='open'", (bid, sid)),
         'Lời mời này không còn nữa.', 'gone')
    mine = _mine(db, sid)
    locked = _lock(db, bid, mine['bang'] if mine else None)
    bang = locked.get(bid)
    need(bang is not None and bang['status'] == 'active' and not bang['hidden'], 'Bang này không còn nữa.', 'gone')
    problem = req_problem(rules_of(bang), data.get('_who'))   # an invitation opens a closed bang, not its requirements
    need(not problem, problem, 'requirements')
    _join(db, sid, bang, t, locked)
    return dict(message=f'{bang["emoji"]} Chào mừng bạn vào bang {bang["name"]}!', joined=bid)


def _op_decline(db, sid, data, t):
    bid = data.get('bang')
    need(isinstance(bid, str) and ID_RE.fullmatch(bid), 'Chọn một bang nhé.')
    db.execute("UPDATE bang_asks SET status='declined', answered=? WHERE bang=? AND sid=? AND kind='invite' AND status='open'", (t, bid, sid))
    _isle(db, 'guest', bid, sid)            # no longer a guest of that island
    return dict(message='Đã từ chối lời mời.')


def _op_leave(db, sid, data, t):
    me = _mine(db, sid)
    need(me is not None, 'Bạn chưa ở bang nào.', 'not_member')
    bang = _lock(db, me['bang'])[me['bang']]
    me = _need_member(db, sid, bang['id'])
    need(me['role'] != 'chu', 'Bang chủ cần trao lại chức trước khi rời (hoặc giải tán bang).', 'leader')
    need(data.get('confirm') is True, f'Xác nhận rời bang {bang["name"]}.')
    _leave(db, sid, bang, t, 'leave')
    return dict(message=f'Bạn đã rời bang {bang["name"]}. Điểm và đồ bang vẫn giữ nếu quay lại.')


def _role_need(me: dict, rank_from: int) -> None:
    need(_rank(me['role']) >= rank_from, f'Việc này cần {C.ROLES[next(k for k in C.ROLE_ORDER if C.ROLES[k][3] == rank_from)][0]} trở lên.', 'role')


def _officer(db, sid, rank_from: int) -> tuple[dict, dict]:
    """(my locked bang row, my member row) when my role is at least rank_from."""
    me = _mine(db, sid)
    need(me is not None, 'Bạn chưa ở bang nào.', 'not_member')
    bang = _lock(db, me['bang'])[me['bang']]
    me = _need_member(db, sid, bang['id'])
    _role_need(me, rank_from)
    return bang, me


def _target(db, bid: str, pid) -> dict:
    need(isinstance(pid, str) and PID_RE.fullmatch(pid), 'Chọn một người nhé.')
    m = _row(db, "SELECT * FROM bang_members WHERE bang=? AND pid=? AND status='in' FOR UPDATE", (bid, pid))
    need(m is not None, 'Người này không ở trong bang.', 'not_member')
    return m


def _op_invite(db, sid, data, t):
    bang, me = _officer(db, sid, C.APPROVE_FROM)
    code = data.get('code')
    need(isinstance(code, str) and CODE_RE.fullmatch(code.strip().upper()), 'Nhập mã người chơi dạng PCC-XXXXXX nhé.')
    p = _row(db, 'SELECT p.sid FROM marriage_people p JOIN accounts a ON a.sid=p.sid WHERE p.code=?', (code.strip().upper(),))
    need(p is not None, 'Không tìm thấy người chơi có mã này.', 'not_found')
    other = p['sid']
    need(other != sid, 'Đây là mã của chính bạn mà.')
    need(not _row(db, "SELECT 1 FROM bang_members WHERE bang=? AND sid=? AND status='in'", (bang['id'], other)), 'Người này đã ở trong bang.')
    blocked = _row(db, 'SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?)', (sid, other, other, sid))
    need(not blocked, 'Không mời được người này.', 'blocked')
    db.execute("INSERT INTO bang_asks(bang, sid, kind, by_sid, status, at) VALUES(?, ?, 'invite', ?, 'open', ?) "
               "ON CONFLICT(bang, sid, kind) DO UPDATE SET status='open', by_sid=excluded.by_sid, at=excluded.at, answered=NULL",
               (bang['id'], other, sid, t))
    _log(db, bang['id'], sid, 'invite', f'{_display(db, sid)} mời {_display(db, other)}.', t)
    _bump(db, bang['id'])
    _notify(db, invite=pid_of(other), name=bang['name'], emoji=bang['emoji'])
    _isle(db, 'guest', bang['id'], other)   # an open invitation: a guest of the island
    return dict(message=f'Đã gửi lời mời tới {_display(db, other)}.')


def _op_approve(db, sid, data, t):
    pid = data.get('pid')
    need(isinstance(pid, str) and PID_RE.fullmatch(pid), 'Chọn một người nhé.')
    me = _mine(db, sid)
    need(me is not None, 'Bạn chưa ở bang nào.', 'not_member')
    rows = _rows(db, "SELECT sid FROM bang_asks WHERE bang=? AND kind='ask' AND status='open'", (me['bang'],))
    other = next((r['sid'] for r in rows if pid_of(r['sid']) == pid), None)
    need(other is not None, 'Đơn này không còn nữa.', 'gone')
    theirs = _mine(db, other) if data.get('ok') is not False else None
    # Both bang ids read first, then locked together in id order (review fix 19/10: locking mine, then theirs, could
    # deadlock with them moving bang, which locks the two in id order too).
    locked = _lock(db, me['bang'], theirs['bang'] if theirs else None)
    bang = locked.get(me['bang'])
    need(bang is not None, 'Thử lại nhé.', 'retry')
    me = _need_member(db, sid, bang['id'])
    _role_need(me, C.APPROVE_FROM)
    need(_row(db, "SELECT 1 FROM bang_asks WHERE bang=? AND sid=? AND kind='ask' AND status='open'", (bang['id'], other)),
         'Đơn này không còn nữa.', 'gone')
    if data.get('ok') is False:
        db.execute("UPDATE bang_asks SET status='declined', answered=? WHERE bang=? AND sid=? AND kind='ask'", (t, bang['id'], other))
        _bump(db, bang['id'])
        return dict(message='Đã từ chối đơn.')
    now_theirs = _mine(db, other)
    need((now_theirs['bang'] if now_theirs else None) == (theirs['bang'] if theirs else None),
         'Người này vừa đổi bang. Thử lại nhé.', 'retry')
    who = data.get('_who')
    problem = req_problem(rules_of(bang), who[1] if who and who[0] == other else None, 'Người này')
    need(not problem, problem, 'requirements')
    _join(db, other, bang, t, locked, how='approve')
    return dict(message=f'Đã nhận {_display(db, other)} vào bang.')


def _op_kick(db, sid, data, t):
    bang, me = _officer(db, sid, C.KICK_FROM)
    m = _target(db, bang['id'], data.get('pid'))
    need(m['sid'] != sid, 'Muốn rời bang thì bấm Rời bang nhé.')
    need(_rank(m['role']) < _rank(me['role']), 'Không mời được người cùng hoặc cao chức hơn ra khỏi bang.', 'role')
    need(data.get('confirm') is True, 'Xác nhận mời người này ra khỏi bang.')
    _leave(db, m['sid'], bang, t, 'kick')
    return dict(message='Đã mời ra khỏi bang.')


def _op_role(db, sid, data, t):
    bang, me = _officer(db, sid, 5)
    m = _target(db, bang['id'], data.get('pid'))
    role = data.get('role')
    need(role in C.APPOINT or role == 'chu', 'Chọn một danh hiệu nhé.')
    need(m['sid'] != sid, 'Đây là bạn mà.')
    if role == 'chu':   # 🔁 hand over: the old leader becomes Phó bang (a free seat) or Thành viên
        need(data.get('confirm') is True, f'Xác nhận trao chức Bang chủ cho {_display(db, m["sid"])}.')
        pho = _seats(db, bang['id'], 'pho') - (1 if m['role'] == 'pho' else 0)
        mine = 'pho' if pho < C.ROLES['pho'][2] else 'tv'
        db.execute("UPDATE bang_members SET role='chu' WHERE bang=? AND sid=?", (bang['id'], m['sid']))
        db.execute('UPDATE bang_members SET role=? WHERE bang=? AND sid=?', (mine, bang['id'], sid))
        db.execute('UPDATE bangs SET leader=? WHERE id=?', (m['sid'], bang['id']))
        _log(db, bang['id'], sid, 'role', f'{_display(db, sid)} trao chức Bang chủ cho {_display(db, m["sid"])}.', t)
        _bump(db, bang['id'])
        _notify(db, pids=[pid_of(sid), m['pid']])
        _isle(db, 'role', bang['id'], sid)
        _isle(db, 'role', bang['id'], m['sid'])
        return dict(message=f'{_display(db, m["sid"])} là Bang chủ mới.')
    if m['role'] == role:
        return dict(message='Không có gì thay đổi.')
    seats = C.ROLES[role][2]
    need(seats is None or _seats(db, bang['id'], role) < seats, f'{C.ROLES[role][0]} đã đủ {seats} người.', 'seats')
    db.execute('UPDATE bang_members SET role=? WHERE bang=? AND sid=?', (role, bang['id'], m['sid']))
    _log(db, bang['id'], sid, 'role', f'{_display(db, m["sid"])} thành {C.ROLES[role][0]}.', t)
    _bump(db, bang['id'])
    _notify(db, pids=[m['pid']])
    _isle(db, 'role', bang['id'], m['sid'])
    return dict(message=f'Đã phong {C.ROLES[role][0]}.')


def _op_set(db, sid, data, t):
    bang, me = _officer(db, sid, C.SETTINGS_FROM)
    changes = []
    if 'open' in data:   # an older page's switch: tự động duyệt / cần duyệt, the requirements kept
        need(type(data['open']) is bool, 'Thông tin không hợp lệ.')
        _write_rules(db, bang, dict(rules_of(bang), mode='auto' if data['open'] else 'ask'))
        changes.append('tự động duyệt' if data['open'] else 'vào bang cần duyệt')
    if 'motto' in data:
        from .engine import GameError
        try:
            motto = clean_motto(data['motto'])
        except GameError as x:
            raise BangError(x.message, 'bad_motto') from None
        db.execute('UPDATE bangs SET motto=? WHERE id=?', (motto, bang['id']))
        changes.append('khẩu hiệu mới')
    if 'emoji' in data:
        need(data['emoji'] in C.EMOJIS, 'Chọn một biểu tượng trong danh sách nhé.')
        db.execute('UPDATE bangs SET emoji=? WHERE id=?', (data['emoji'], bang['id']))
        changes.append('biểu tượng mới')
    if 'color' in data:
        need(isinstance(data['color'], str) and data['color'] in C.COLORS, 'Chọn một màu trong bảng màu nhé.')
        db.execute('UPDATE bangs SET color=? WHERE id=?', (data['color'], bang['id']))
        changes.append('màu mới')
    need(changes, 'Không có gì thay đổi.')
    if 'emoji' in data:
        db.execute('UPDATE chat_channels SET title=? WHERE id=?', (f'{data["emoji"]} {bang["name"]}'[:40], bang['channel']))
    _log(db, bang['id'], sid, 'set', 'Bang chủ đổi: ' + ', '.join(changes) + '.', t)
    _bump(db, bang['id'])
    pids = [x['pid'] for x in _rows(db, "SELECT pid FROM bang_members WHERE bang=? AND status='in'", (bang['id'],))]
    _notify(db, bang=bang['id'], ch=bang['channel'], pids=pids)   # the live service re-tags these members only
    _isle(db, 'view', bang['id'])
    return dict(message='Đã lưu.')


def _write_rules(db, bang: dict, rules: dict) -> None:
    """Store the rules (only what is set) and keep `open` in step (1: tự động duyệt) for code that reads it."""
    keep = {k: v for k, v in rules.items() if v and k != 'mode'}
    if not keep.get('rank'):
        keep.pop('career', None)
    db.execute('UPDATE bangs SET rules=?, open=? WHERE id=?',
               (json.dumps(dict(mode=rules['mode'], **keep), sort_keys=True), 1 if rules['mode'] == 'auto' else 0, bang['id']))


def _op_rules(db, sid, data, t):
    """🚪 The join mode and the requirements (Phó bang and up, owner 20/10). Members already in are never removed when
    the requirements change. {mode?, career?, rank?, any?, days?}: what is left out stays; 0 / '' clears one."""
    bang, me = _officer(db, sid, C.RULES_FROM)
    need(set(data) <= {'mode', 'career', 'rank', 'any', 'days'} and data, 'Thông tin không hợp lệ.')
    cur = rules_of(bang)
    new = dict(cur)
    if 'mode' in data:
        need(data['mode'] in C.JOIN_MODES, 'Chọn cách nhận người nhé.')
        new['mode'] = data['mode']
    if 'career' in data or 'rank' in data:
        career, rank = data.get('career', cur['career']), data.get('rank', cur['rank'])
        if not career or not rank:
            new.update(career='', rank=0)
        else:
            ladder()
            x = _LADDER['by'].get(career) if isinstance(career, str) else None
            need(x is not None, 'Chọn một nghề trong danh sách nhé.')
            need(type(rank) is int and 1 <= rank <= len(x['titles']), f'Chọn một chức danh của nghề {x["name"]} nhé.')
            new.update(career=career, rank=rank)
    if 'any' in data:
        need(type(data['any']) is int and 0 <= data['any'] <= C.REQ_RANK_MAX, f'Bậc chức danh từ 0 đến {C.REQ_RANK_MAX} nhé.')
        new['any'] = data['any']
    if 'days' in data:
        need(type(data['days']) is int and 0 <= data['days'] <= C.REQ_DAYS_MAX, f'Tuổi tài khoản từ 0 đến {C.REQ_DAYS_MAX} ngày nhé.')
        new['days'] = data['days']
    if new == cur:
        return dict(message='Không có gì thay đổi.')
    _write_rules(db, bang, new)
    reqs = req_lines(new)
    text = f'{C.JOIN_MODES[new["mode"]]}' + (f'; yêu cầu: {", ".join(reqs)}' if reqs else '; không yêu cầu gì')
    _log(db, bang['id'], sid, 'set', f'{_display(db, sid)} đổi cách nhận người: {text}.', t)
    _bump(db, bang['id'])
    return dict(message=f'Đã lưu: {text}.', rules=rules_of(dict(bang, rules=json.dumps(new), open=1 if new['mode'] == 'auto' else 0)))


def _op_disband(db, sid, data, t):
    bang, me = _officer(db, sid, 5)
    need(data.get('confirm') is True and data.get('name') == bang['name'],
         f'Gõ đúng tên bang "{bang["name"]}" để giải tán. Quỹ {fmt(bang["fund"])} xu sẽ mất, không trả lại ai.', 'confirm')
    _disband(db, bang, sid, t, 'Bang chủ giải tán bang.')
    return dict(message=f'Bang {bang["name"]} đã giải tán. Quỹ không trả lại (đã đốt).')


def _disband(db, bang: dict, sid: str, t: float, text: str) -> None:
    """The bang ends (its row locked): every member out, the fund burned (a ledger row), every row kept."""
    members = _rows(db, "SELECT sid, pid FROM bang_members WHERE bang=? AND status='in'", (bang['id'],))
    fund = int(bang['fund'])
    if fund > 0:
        db.execute("INSERT INTO bang_fund(id, bang, sid, kind, amount, balance, note, at) VALUES(?,?,?,'burn',?,0,?,?) ON CONFLICT DO NOTHING",
                   (f'x:{bang["id"]}', bang['id'], sid, -fund, 'giải tán', t))
    db.execute("UPDATE bangs SET status='disbanded', ended=?, burned=burned+fund, fund=0 WHERE id=?", (t, bang['id']))
    db.execute("UPDATE bang_members SET status='out', role='tv', left_at=?, why='disband' WHERE bang=? AND status='in'", (t, bang['id']))
    db.execute("UPDATE bang_stints SET left_at=?, why='disband' WHERE bang=? AND left_at IS NULL", (t, bang['id']))
    db.execute("UPDATE bang_asks SET status='cancelled', answered=? WHERE bang=? AND status='open'", (t, bang['id']))
    db.execute("UPDATE bang_gh SET status='cancelled' WHERE bang=? AND status='set' AND start>?", (bang['id'], t))
    from . import bang_challenge
    bang_challenge.cancel_open(db, bang['id'], t)   # ⚔️ its open challenges, both ways
    if bang['channel']:
        db.execute('DELETE FROM chat_members WHERE channel=?', (bang['channel'],))
    _log(db, bang['id'], sid, 'disband', text, t)
    _bump(db, bang['id'])
    _notify(db, pids=[m['pid'] for m in members], ch=bang['channel'], rm=[m['pid'] for m in members])
    _isle(db, 'disband', bang['id'])
    _war_unpick(db, bang['id'], [m['sid'] for m in members], t)
    for m in members:
        _noted_leave(m['sid'], bang['id'], t)
    _noted_cancel(bang['id'], after=t)


def _op_checkin(db, sid, data, t):
    me = _mine(db, sid)
    need(me is not None, 'Vào một bang để điểm danh nhé.', 'not_member')
    bang = _lock(db, me['bang']).get(me['bang'])      # the bang row first, then mine (the one lock order: kick, disband)
    need(bang is not None, 'Vào một bang để điểm danh nhé.', 'not_member')
    me = _need_member(db, sid, bang['id'])
    day = vn_day(t)
    ok = _earn(db, me['bang'], sid, f'c:{me["pid"]}:{day}', 'checkin', C.CHECKIN_POINTS, t)
    need(ok, 'Hôm nay bạn điểm danh rồi. Mai quay lại nhé!', 'done')
    _bump(db, me['bang'])
    return dict(message=f'📅 Điểm danh xong: +{C.CHECKIN_POINTS} điểm cống hiến.')


def _op_build(db, sid, data, t):
    bang, me = _officer(db, sid, C.BUILD_FROM)
    fac = data.get('fac')
    need(isinstance(fac, str) and fac in C.FACILITIES, 'Chọn một công trình nhé.')
    finish_builds(db, bang['id'], t)
    lv = levels(db, bang['id'])
    rows = {r['fac']: r for r in _rows(db, 'SELECT * FROM bang_facilities WHERE bang=? FOR UPDATE', (bang['id'],))}
    f = C.FACILITIES[fac]
    cur = rows.get(fac)
    need(not (cur and cur['target'] is not None), f'{f["name"]} đang xây rồi.', 'building')
    level = lv[fac]
    need(level < C.max_level(fac), f'{f["name"]} đã ở cấp cao nhất.', 'max')
    nxt = level + 1
    hall = C.hall_needed(fac, nxt)
    need(lv[C.HALL] >= hall, f'Cần {C.FACILITIES[C.HALL]["name"]} cấp {hall} trước.', 'hall')
    isle = C.isle_needed(fac, nxt)   # 🏝️ 21/10: the higher levels wait for the island (levels already built stay)
    need(island_of(bang, t)['level'] >= isle, f'Cần 🏝️ Đảo bang cấp {isle} trước.', 'island')
    busy = sum(1 for r in rows.values() if r['target'] is not None)
    slots = C.build_slots(lv[C.HALL])
    need(busy < slots, f'Bang đang xây {busy} công trình (tối đa {slots} cùng lúc).', 'slots')
    xu, secs = C.cost(fac, nxt)
    fund = int(bang['fund'])
    need(fund >= xu, f'Quỹ bang còn thiếu {fmt(xu - fund)} xu.', 'not_enough')
    need(data.get('confirm') is True, f'Xác nhận dùng {fmt(xu)} xu quỹ bang xây {f["name"]} cấp {nxt}.')
    bal = fund - xu
    db.execute("INSERT INTO bang_fund(id, bang, sid, kind, amount, balance, note, at) VALUES(?,?,?,'build',?,?,?,?)",
               (f'b:{bang["id"]}:{fac}:{nxt}', bang['id'], sid, -xu, bal, f'{fac} {nxt}', t))
    db.execute('UPDATE bangs SET fund=?, spent=spent+? WHERE id=?', (bal, xu, bang['id']))
    db.execute('INSERT INTO bang_facilities(bang, fac, level, target, started, ready_at, paid) VALUES(?,?,?,?,?,?,?) '
               'ON CONFLICT(bang, fac) DO UPDATE SET target=excluded.target, started=excluded.started, ready_at=excluded.ready_at, '
               'paid=bang_facilities.paid+excluded.paid', (bang['id'], fac, level, nxt, t, t + secs, xu))
    _log(db, bang['id'], sid, 'build', f'{_display(db, sid)} cho xây {f["emoji"]} {f["name"]} cấp {nxt} ({fmt(xu)} xu).', t)
    _bump(db, bang['id'])
    _isle(db, 'view', bang['id'])
    hours = secs // 3600
    return dict(message=f'{f["emoji"]} Bắt đầu xây {f["name"]} cấp {nxt}: {hours} giờ nữa xong.')


def _op_isle(db, sid, data, t):
    """🏝️ Buy the island (to=1) or upgrade it one level (to=level+1), Phó bang and up, from the fund only, under the bang
    row's lock: two officers at once wait for each other, the second sees the first's purchase. Idempotent by `to`: a
    level held, or the upgrade to it already being built, answers again=True and pays nothing."""
    bang, me = _officer(db, sid, C.BUILD_FROM)
    to = data.get('to')
    need(type(to) is int and 1 <= to <= C.ISLE_MAX, 'Chọn cấp đảo nhé.')
    finish_builds(db, bang['id'], t)
    bang = _row(db, 'SELECT * FROM bangs WHERE id=?', (bang['id'],))     # locked by _officer; finish_isle may have moved it
    cur = island_of(bang, t)
    if cur['level'] >= to:
        return dict(message='Bang đã có đảo rồi.' if to == 1 else f'Đảo bang đã ở cấp {cur["level"]} rồi.', again=True)
    if cur['to'] == to:
        return dict(message=f'Đảo đang được mở rộng lên cấp {to} rồi.', again=True)
    need(cur['to'] is None, f'Đảo đang mở rộng lên cấp {cur["to"]}: xong rồi mới nâng tiếp nhé.', 'building')
    need(to == cur['level'] + 1, f'Nâng lần lượt nhé: tiếp theo là cấp {cur["level"] + 1}.', 'order')
    xu, secs = C.isle_cost(to)
    fund = int(bang['fund'])
    need(fund >= xu, f'Quỹ bang còn thiếu {fmt(xu - fund)} xu.', 'not_enough')
    what = 'mua Đảo bang' if to == 1 else f'nâng Đảo bang lên cấp {to}'
    need(data.get('confirm') is True, f'Xác nhận dùng {fmt(xu)} xu quỹ bang để {what}.')
    bal = fund - xu
    bid = bang['id']
    db.execute("INSERT INTO bang_fund(id, bang, sid, kind, amount, balance, note, at) VALUES(?,?,?,'build',?,?,?,?)",
               (f'i:{bid}:{to}', bid, sid, -xu, bal, f'isle {to}', t))
    if secs:
        db.execute('UPDATE bangs SET fund=?, spent=spent+?, isle_to=?, isle_started=?, isle_ready=?, isle_paid=isle_paid+? WHERE id=?',
                   (bal, xu, to, t, t + secs, xu, bid))
    else:
        db.execute("UPDATE bangs SET fund=?, spent=spent+?, isle=?, isle_to=NULL, isle_ready=NULL, isle_started=?, isle_paid=isle_paid+?, "
                   "isle_how=CASE WHEN ?=1 THEN 'buy' ELSE isle_how END WHERE id=?", (bal, xu, to, t, xu, to, bid))
    who = _display(db, sid)
    if to == 1:
        _log(db, bid, sid, 'build', f'🏝️ {who} mua Đảo bang ({fmt(xu)} xu quỹ): cả bang ra đảo chơi được rồi!', t)
    else:
        _log(db, bid, sid, 'build', f'🏝️ {who} cho mở rộng Đảo bang lên cấp {to} ({fmt(xu)} xu quỹ).', t)
    _bump(db, bid)
    _isle(db, 'view', bid)
    if to == 1:
        return dict(message='🏝️ Bang đã có đảo! Bấm 🏯 Đảo bang để cả bang ra chơi.', isle=to)
    return dict(message=f'🏗️ Bắt đầu mở rộng Đảo bang lên cấp {to}: {secs // 3600} giờ nữa xong.', isle=to)


def _op_buy(db, sid, data, t):
    item = data.get('item')
    need(isinstance(item, str) and item in C.ITEMS, 'Chọn một món nhé.')
    rid = data.get('rid')
    need(isinstance(rid, str) and RID_RE.fullmatch(rid), 'Thiếu mã thao tác. Tải lại trang nhé.')
    me = _mine(db, sid, lock=True)
    need(me is not None, 'Vào một bang để mua đồ bang nhé.', 'not_member')
    bid = me['bang']
    ref = f'buy:{me["pid"]}:{rid}'
    if db.execute('SELECT 1 FROM bang_points WHERE id=?', (ref,)).fetchone():
        return dict(message='Đã mua rồi.', again=True)
    lv = levels(db, bid)
    name, emoji, _, needs, kind = C.ITEMS[item]
    if not _unlocked(item, lv):
        need(False, f'Cần {C.FACILITIES[needs[0]]["name"]} cấp {needs[1]} mới mở {name}.', 'locked')
    have = _row(db, 'SELECT n FROM bang_items WHERE bang=? AND sid=? AND item=? FOR UPDATE', (bid, sid, item))
    if kind == 'wear':
        need(not have or int(have['n']) < 1, f'Bạn đã có {name} của bang này.', 'owned')
    else:
        need(not have or int(have['n']) < C.PHAO_MAX, f'Giữ tối đa {C.PHAO_MAX} {name}.', 'full')
    price = _price(item, lv)
    need(int(me['points']) >= price, f'Còn thiếu {fmt(price - int(me["points"]))} điểm cống hiến.', 'not_enough')
    db.execute('INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,?,?,?,?,?)',
               (ref, bid, sid, 'buy', -price, vn_week(t), vn_day(t), t))
    db.execute('UPDATE bang_members SET points=points-? WHERE bang=? AND sid=?', (price, bid, sid))
    db.execute('INSERT INTO bang_items(bang, sid, item, n, at) VALUES(?,?,?,1,?) ON CONFLICT(bang, sid, item) DO UPDATE SET n=bang_items.n+1',
               (bid, sid, item, t))
    if kind == 'wear':   # worn at once (one tap to take it off)
        db.execute('UPDATE bang_members SET wear=wear|? WHERE bang=? AND sid=?', (C.WEAR_BITS[item], bid, sid))
        _notify(db, pids=[me['pid']])
    return dict(message=f'{emoji} Đã đổi {fmt(price)} điểm lấy {name}.', item=item)


def _op_wear(db, sid, data, t):
    item = data.get('item')
    need(item in C.WEAR_BITS, 'Chọn một món nhé.')
    on = data.get('on')
    need(type(on) is bool, 'Thông tin không hợp lệ.')
    me = _mine(db, sid, lock=True)
    need(me is not None, 'Đồ bang chỉ dùng được khi đang ở bang của nó.', 'not_member')
    bid = me['bang']
    have = _row(db, 'SELECT n FROM bang_items WHERE bang=? AND sid=? AND item=?', (bid, sid, item))
    need(have and int(have['n']) > 0, 'Món này chỉ dùng được ở bang bạn mua nó.', 'not_owned')
    bit = C.WEAR_BITS[item]
    style = data.get('style')
    if style is not None:
        need(item == 'ao' and style in C.UNIFORMS, 'Chọn một kiểu đồng phục nhé.')
        lv = levels(db, bid)
        need(C.UNIFORMS[style][2] <= lv['xuong_may'], f'Cần Xưởng may cấp {C.UNIFORMS[style][2]} cho kiểu này.', 'locked')
        db.execute('UPDATE bang_members SET uniform=? WHERE bang=? AND sid=?', (style, bid, sid))
    db.execute('UPDATE bang_members SET wear=? WHERE bang=? AND sid=?',
               ((int(me['wear']) | bit) if on else (int(me['wear']) & ~bit), bid, sid))
    _notify(db, pids=[me['pid']])
    return dict(message='Đã mặc.' if on and item == 'ao' else 'Đã bật.' if on else 'Đã cất.')


def _op_fire(db, sid, data, t):
    rid = data.get('rid')
    need(isinstance(rid, str) and RID_RE.fullmatch(rid), 'Thiếu mã thao tác. Tải lại trang nhé.')
    me = _mine(db, sid)
    need(me is not None, 'Pháo hoa bang chỉ bắn được khi đang ở bang của nó.', 'not_member')
    bang = _lock(db, me['bang'])[me['bang']]
    me = _need_member(db, sid, bang['id'])
    have = _row(db, "SELECT n FROM bang_items WHERE bang=? AND sid=? AND item='phao' FOR UPDATE", (bang['id'], sid))
    need(have and int(have['n']) > 0, 'Hết pháo hoa bang. Đổi điểm ở Cửa hàng bang nhé.', 'none')
    wait = float(bang['phao_at']) + C.PHAO_GAP - t
    need(wait <= 0, f'Bang vừa bắn pháo hoa. Chờ {math.ceil(wait / 60)} phút nữa nhé.', 'soon')
    db.execute("UPDATE bang_items SET n=n-1 WHERE bang=? AND sid=? AND item='phao'", (bang['id'], sid))
    db.execute('UPDATE bangs SET phao_at=? WHERE id=?', (t, bang['id']))
    _log(db, bang['id'], sid, 'fire', f'{_display(db, sid)} bắn pháo hoa bang.', t)
    from . import live_chat
    fid = f'{hashlib.sha256(("bang:" + bang["id"]).encode()).hexdigest()[:16]}:{int(t)}'
    wish = (bang['motto'] or f'Bang {bang["name"]} chào cả phố!')[:40]
    live_chat.notify(db, dict(op='fireworks', id=fid, pid=me['pid'], size='lon', name=f'{bang["emoji"]} {bang["name"]}'[:24], wish=wish, at=float(t)))
    mr._post_news(db, 'bang', f'bang:fw:{bang["id"]}:{int(t)}', f'🎆 Bang {bang["emoji"]} {bang["name"]} bắn pháo hoa chào cả phố!', '', '')
    return dict(message='🎆 Pháo hoa bang đã bay lên trời phố!')


def _op_gh_set(db, sid, data, t):
    bang, me = _officer(db, sid, C.BUILD_FROM)
    finish_builds(db, bang['id'], t)
    lv = levels(db, bang['id'])
    per_week, minutes = _gh_rules(lv)
    need(per_week > 0, 'Xây Đền vàng để có Giờ vàng của bang nhé.', 'locked')
    start = data.get('start')
    need(type(start) is int and start % C.GOLDEN_STEP == 0, 'Chọn giờ bắt đầu theo mốc 5 phút nhé.')
    need(start >= t + C.GOLDEN_AHEAD_MIN, 'Đặt Giờ vàng trước ít nhất 1 tiếng nhé.', 'too_soon')
    need(start <= t + C.GOLDEN_AHEAD_MAX, 'Chỉ đặt trước tối đa 7 ngày nhé.', 'too_far')
    ends = start + minutes * 60
    rows = _rows(db, "SELECT start, ends FROM bang_gh WHERE bang=? AND status='set' AND ends>? FOR UPDATE", (bang['id'], start - 8 * 86400))
    day, week = vn_day(start), vn_week(start)
    need(not any(vn_day(float(r['start'])) == day for r in rows), 'Mỗi ngày bang chỉ có một Giờ vàng.', 'day')
    n = sum(1 for r in rows if vn_week(float(r['start'])) == week)
    need(n < per_week, f'Tuần đó bang đã đặt đủ {per_week} lần Giờ vàng (Đền vàng cấp {lv["den_vang"]}).', 'week')
    db.execute("INSERT INTO bang_gh(bang, start, ends, by_sid, status, at) VALUES(?,?,?,?,'set',?)", (bang['id'], float(start), float(ends), sid, t))
    hhmm = datetime.datetime.fromtimestamp(start, VN).strftime('%H:%M %d/%m')
    _log(db, bang['id'], sid, 'golden', f'⏰ {_display(db, sid)} đặt Giờ vàng {hhmm} ({minutes} phút).', t)
    _bump(db, bang['id'])   # no snapshot reset: set ≥ 1 h ahead, the next minute's read (GH_AHEAD) has it before it starts
    return dict(message=f'⏰ Đã đặt Giờ vàng của bang lúc {hhmm}, {minutes} phút: lãi tiệm và quầy ×2.')


def _op_gh_cancel(db, sid, data, t):
    bang, me = _officer(db, sid, C.BUILD_FROM)
    gid = data.get('id')
    need(type(gid) is int, 'Chọn một Giờ vàng nhé.')
    r = _row(db, "SELECT start FROM bang_gh WHERE id=? AND bang=? AND status='set' FOR UPDATE", (gid, bang['id']))
    need(r is not None, 'Không tìm thấy Giờ vàng này.', 'gone')
    need(float(r['start']) > t, 'Giờ vàng đã bắt đầu thì không đổi được nữa.', 'started')
    need(float(r['start']) - t > C.GOLDEN_CANCEL_FREEZE, f'Còn chưa tới {C.GOLDEN_CANCEL_FREEZE // 60} phút là Giờ vàng bắt đầu: không hủy được nữa.', 'started')
    db.execute("UPDATE bang_gh SET status='cancelled' WHERE id=?", (gid,))
    _log(db, bang['id'], sid, 'golden', f'{_display(db, sid)} hủy một Giờ vàng.', t)
    _bump(db, bang['id'])
    _noted_cancel(bang['id'], gid)   # only this bang's window, in this process; the others' next read (≤ 1 min, before the freeze)
    return dict(message='Đã hủy Giờ vàng đó.')


OPS = dict(join=_op_join, cancel=_op_cancel, accept=_op_accept, decline=_op_decline, leave=_op_leave, invite=_op_invite,
           approve=_op_approve, kick=_op_kick, role=_op_role, set=_op_set, disband=_op_disband, checkin=_op_checkin,
           build=_op_build, buy=_op_buy, isle=_op_isle, wear=_op_wear, fire=_op_fire, gh_set=_op_gh_set, gh_cancel=_op_gh_cancel, rules=_op_rules)


def _pre_profile(store, sid: str, op: str, data: dict) -> None:
    """🚪 The joining player's ranks and account age (data['_who']), read before the operation's transaction (a save is
    parsed only when the bang has requirements): join / accept → mine, approve → (the applicant's sid, theirs)."""
    with store.connect() as db:
        if op == 'approve':
            me = _mine(db, sid)
            pid = data.get('pid')
            if not me or data.get('ok') is False or not isinstance(pid, str):
                return
            bang = _row(db, 'SELECT * FROM bangs WHERE id=?', (me['bang'],))
            if not bang or not has_reqs(rules_of(bang)):
                return
            other = next((r['sid'] for r in _rows(db, "SELECT sid FROM bang_asks WHERE bang=? AND kind='ask' AND status='open'", (me['bang'],))
                          if pid_of(r['sid']) == pid), None)
            if other:
                data['_who'] = (other, profile_of(db, other))
            return
        bid = data.get('bang')
        bang = _row(db, 'SELECT * FROM bangs WHERE id=?', (bid,)) if isinstance(bid, str) and ID_RE.fullmatch(bid) else None
        if bang and has_reqs(rules_of(bang)):
            data['_who'] = profile_of(db, sid)


def post(store, token, op: str, data) -> dict:
    """POST /api/bang/<op>: one transaction (the bang rows locked in id order, then member rows)."""
    need(not off(), OFF_TEXT, 'off', 503)
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Yêu cầu không hợp lệ.')
    need(op in OPS, 'Không tìm thấy mục này.', 'not_found', 404)
    data = {k: v for k, v in data.items() if not (isinstance(k, str) and k.startswith('_'))}   # '_who' is ours, never the page's
    if op in ('join', 'accept', 'approve'):
        _pre_profile(store, sid, op, data)
    out = store.transaction(lambda db: OPS[op](db, sid, data, now()))
    _VIEW.clear()
    return dict(done=out or {}, **get_view(store, token, {}))


# ---------------------------------------------------------------- the operator (admin)
def admin_view(store, q: str = '') -> dict:
    key = name_key(q or '')
    with store.connect() as db:
        rows = _rows(db, 'SELECT b.*, a.display AS leader_name, a.username AS leader_user, '
                         "(SELECT COUNT(*) FROM bang_members m WHERE m.bang=b.id AND m.status='in') AS n "
                         'FROM bangs b LEFT JOIN accounts a ON a.sid=b.leader ORDER BY b.created DESC LIMIT 500')
    out = [dict(id=r['id'], name=r['name'], emoji=r['emoji'], color=r['color'], motto=r['motto'], status=r['status'], hidden=bool(r['hidden']),
                n=int(r['n']), fund=int(r['fund']), given=int(r['given']), spent=int(r['spent']), burned=int(r['burned']),
                leader=str(r['leader_name'] or GONE), user=str(r['leader_user'] or ''), created=float(r['created']), note=r['admin_note'])
           for r in rows if not key or key in name_key(r['name'])]
    return dict(bangs=out[:200])


def admin_act(store, admin: str, data) -> dict:
    """{op: 'hide' | 'show' | 'rename', id, name?}: never a hard delete; a hidden bang leaves the lists and its tag goes."""
    need(isinstance(data, dict), 'Yêu cầu không hợp lệ.')
    op, bid = data.get('op'), data.get('id')
    need(op in ('hide', 'show', 'rename'), 'Thao tác không hợp lệ.')
    need(isinstance(bid, str) and ID_RE.fullmatch(bid), 'Không tìm thấy bang này.')
    t = now()

    def run(db):
        bang = _lock(db, bid).get(bid)
        need(bang is not None, 'Không tìm thấy bang này.', 'not_found', 404)
        who = str(admin or 'admin')[:40]
        if op == 'rename':
            from .engine import GameError
            try:
                name = clean_name(data.get('name'))
            except GameError as x:
                raise BangError(x.message, 'bad_name') from None
            key = name_key(name)
            if bang['status'] == 'active':
                need(not db.execute("SELECT 1 FROM bangs WHERE key=? AND status='active' AND id<>?", (key, bid)).fetchone(),
                     'Tên này đã có bang dùng.', 'name_taken')
            db.execute('UPDATE bangs SET name=?, key=?, admin_note=? WHERE id=?', (name, key, f'đổi tên bởi {who} (cũ: {bang["name"]})'[:200], bid))
            if bang['channel']:
                db.execute('UPDATE chat_channels SET title=? WHERE id=?', (f'{bang["emoji"]} {name}'[:40], bang['channel']))
            _log(db, bid, '', 'admin', f'Quản trị đổi tên bang thành {name}.', t)
        else:
            db.execute('UPDATE bangs SET hidden=?, admin_note=? WHERE id=?', (1 if op == 'hide' else 0, f'{op} bởi {who}'[:200], bid))
            _log(db, bid, '', 'admin', 'Quản trị ẩn bang.' if op == 'hide' else 'Quản trị hiện lại bang.', t)
        _bump(db, bid)
        members = _rows(db, "SELECT sid, pid FROM bang_members WHERE bang=? AND status='in'", (bid,))
        if op == 'hide':   # a hidden bang fields nobody in the pet war: its lineup's slots free (the picks go)
            _war_unpick(db, bid, [r['sid'] for r in members], t)
            from . import bang_challenge
            bang_challenge.cancel_open(db, bid, t)   # ⚔️ nor in a challenge
        pids = [r['pid'] for r in members]
        _notify(db, pids=pids, bang=bid, ch=bang['channel'])
        _isle(db, 'view', bid)
    store.transaction(run)
    _VIEW.clear()
    return dict(ok=True, **admin_view(store))


def forget(db, sid: str) -> None:
    """A player erased their data (storage.delete, the save's row locked): out of their bang (a leader hands over to the
    highest, oldest member, or the bang ends when they were alone); what they gave stays in the ledgers, as anonymous."""
    try:
        mine = _mine(db, sid)
    except Exception:  # noqa: BLE001 - an older schema
        return
    t = now()
    if mine:
        bang = _lock(db, mine['bang']).get(mine['bang'])
        if bang:
            if mine['role'] == 'chu':
                rest = _rows(db, "SELECT sid, role, joined FROM bang_members WHERE bang=? AND status='in' AND sid<>?", (bang['id'], sid))
                if rest:
                    nxt = sorted(rest, key=lambda r: (-_rank(r['role']), float(r['joined'])))[0]
                    db.execute("UPDATE bang_members SET role='chu' WHERE bang=? AND sid=?", (bang['id'], nxt['sid']))
                    db.execute('UPDATE bangs SET leader=? WHERE id=?', (nxt['sid'], bang['id']))
                    _leave(db, sid, bang, t, 'gone')
                else:
                    _disband(db, bang, sid, t, 'Bang chủ rời phố, bang giải tán.')
            else:
                _leave(db, sid, bang, t, 'gone')
    for table in ('bang_fund', 'bang_points', 'bang_log', 'bang_points_old', 'bang_log_old'):
        db.execute(f"UPDATE {table} SET sid='' WHERE sid=?", (sid,))
    db.execute("UPDATE bang_asks SET status='cancelled' WHERE sid=? AND status='open'", (sid,))


# ---------------------------------------------------------------- 🗄️ housekeeping (server.py, one process, every 30 s)
KEEP_LOG_DAYS = 30              # bang_log rows older than this go to bang_log_old (each bang's newest LOG_SHOWN stay)
KEEP_POINTS_DAYS = 35           # bang_points older than five weeks (the ranking reads this week and the last)
KEEP_STINTS_DAYS = 30           # closed membership spans older than this (Giờ vàng reads 14 days back, the cap today)
ARCHIVE_EVERY = 600.0
ARCHIVE_BATCH = 500
ARCHIVE_ROUNDS = 4
_ARCH = dict(at=0.0)


def archive_old(store, t: float | None = None) -> dict:
    """Moves rows past their keep into the archive tables (SCHEMA_VERSION 59), a few small batches a call, each its own
    transaction (game/archive.py move_rows: copied, then removed; never dropped). {table: rows moved}."""
    from . import archive as ar
    t = now() if t is None else t
    out = dict(bang_log=0, bang_points=0, bang_stints=0)

    def log_batch(db):
        # a quiet bang's page still shows its newest LOG_SHOWN lines: only rows with that many newer ones in their bang
        rows = _rows(db, 'SELECT l.id FROM bang_log l WHERE l.at<? AND (SELECT x.id FROM bang_log x WHERE x.bang=l.bang AND x.id>l.id '
                         'ORDER BY x.id OFFSET ? LIMIT 1) IS NOT NULL ORDER BY l.at LIMIT ? FOR UPDATE SKIP LOCKED',
                     (t - KEEP_LOG_DAYS * 86400, LOG_SHOWN - 1, ARCHIVE_BATCH))
        return ar.move_rows(db, 'bang_log', 'bang_log_old', [int(r['id']) for r in rows], t), len(rows)

    def points_batch(db):
        rows = _rows(db, 'SELECT id FROM bang_points WHERE at<? ORDER BY at LIMIT ? FOR UPDATE SKIP LOCKED',
                     (t - KEEP_POINTS_DAYS * 86400, ARCHIVE_BATCH))
        return ar.move_rows(db, 'bang_points', 'bang_points_old', [r['id'] for r in rows], t), len(rows)

    def stints_batch(db):
        rows = _rows(db, 'SELECT id FROM bang_stints WHERE left_at IS NOT NULL AND left_at<? ORDER BY left_at LIMIT ? FOR UPDATE SKIP LOCKED',
                     (t - KEEP_STINTS_DAYS * 86400, ARCHIVE_BATCH))
        return ar.move_rows(db, 'bang_stints', 'bang_stints_old', [int(r['id']) for r in rows], t), len(rows)

    for table, fn in (('bang_log', log_batch), ('bang_points', points_batch), ('bang_stints', stints_batch)):
        for _ in range(ARCHIVE_ROUNDS):
            moved, seen = store.transaction(fn)
            out[table] += moved
            if seen < ARCHIVE_BATCH or not moved:
                break
    return out


def run_housekeeping(store) -> None:
    """server.py housekeeping: archive_old every ARCHIVE_EVERY seconds, never in the peak hours. Never raises."""
    import sys
    from . import archive as ar
    t = now()
    if t - _ARCH['at'] < ARCHIVE_EVERY or ar.peak(t):
        return
    _ARCH['at'] = t
    try:
        n = archive_old(store, t)
        if any(n.values()):
            sys.stderr.write(f'[bang] archived {n}\n')
    except Exception as e:  # noqa: BLE001 - housekeeping must never take the server down (an older schema: no archive tables)
        sys.stderr.write(f'[bang] archive: {type(e).__name__}\n')
