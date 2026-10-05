"""Hôn nhân: two registered players marry each other.

Flow: buy a ring (tiệm nhẫn) → propose with a preset message to a "mã người chơi"
(PCC-XXXXXX) → the partner accepts or declines → the engaged couple plans the
wedding (venue, tables × menu, ceremonies, extras, date, who pays how much) → one
proposes the plan, the other confirms and both deposits are taken → when the day
comes the neighbours attend, give tiền mừng, and the money is shared by the same
ratio → married, with a server-wide news line on the ticker if both allowed it.

Where things live
* Cross-account state is in PostgreSQL (tables in game/pg_schema.py): marriage_people
  (public code, "nhận lời cầu hôn", cached life day and guest pool, cooldown,
  last notice), marriage_rings, proposals, couples, marriage_bonds (PRIMARY KEY
  sid: one spouse at a time, even with two acceptances at once), weddings (plan,
  server quote, status, result), marriage_effects, marriage_blocks, news.
* A player's save changes only through `marriage_effects`: rows with a fixed id
  (e.g. ``dep:12:a``) applied by `_mutate` in the SAME transaction that writes
  the save and marks the row applied, under the save's revision guard. So an
  effect is applied once, whatever the retries, devices or processes. The ids
  applied last are also kept in the save (``s['marriage']['applied']``).
* Money moves through the journey wallet (journey._wallet, history kind 'life'),
  like the other personal-money modules. Ring and deposit need the money; the
  balance on the wedding day is paid from the tiền mừng first and any shortfall
  from each wallet by the split, which may then go into debt (the same "Ví đang
  nợ" as unpaid rent) - the wedding never silently shrinks or moves.
* The save carries a small display block ``s['marriage']`` (spouse, sticker
  "Đã về chung một nhà", optional couple id/side), exposed by public_state and checked by validate_save.
* Proposals go only to friends (game/friends.py: exact-username search, requests, blocks).
  After the wedding, game/couple.py adds the joint fund, transfers, help requests, IOUs,
  daily moments and anniversaries; its tables are in game/pg_schema.py. Rings carry a metal and
  a stone colour (NULL = the tier's own), re-coloured at "tiệm kim hoàn" (ring_recolor).

Races: accepting two proposals at once → the second bond insert fails; a divorce
while a wedding is pending → the wedding is cancelled (the deposit is not
refunded, like a real đặt cọc) and the resolution's status guard sees it;
resolution is decided once in the DB (status 'confirmed' → 'done') and then
applied to each save; confirmation takes both deposits in one transaction.
"""
from __future__ import annotations

import datetime
import json
import random
import re
import secrets
import threading
import time

from . import archive as ar
from . import db as dbm
from . import retention as rt
from . import wedding_content as W
from .engine import GameError, migrate_state, validate_state, public_state

VERSION = 1
KIND = 'life'                       # journey wallet history kind (journey.HISTORY_KINDS)
APPLIED_KEPT = 60
CODE_CHARS = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'   # no 0/O, 1/I/L
CODE_LEN = 6
CODE_RX = re.compile(rf'PCC-[{CODE_CHARS}]{{{CODE_LEN}}}')
RINGS_MAX = 5
NEWS_WINDOW = 48 * 3600             # news older than this is never sent
NEWS_FIRST = 24 * 3600              # a first poll (since=0) gets only the last day
NEWS_CACHE_S = 10
CARD_TIER = 3                       # "Người quen" and closer are named on the result card
DAY = 86400
SPOUSE_KEYS = {'name', 'status', 'since', 'wed', 'date'}
SPOUSE_LINK = {'couple', 'side'}      # optional: which couple row (joint fund, bank card)
STORE = None                        # the Store, set by bind() (game/bank.py helpers in game/couple.py)


# Created by Store.__init__ (game/storage.py). Money never lives here: only what two saves
# share, and the effects waiting to be applied to each save.


def _xu(n) -> str:
    """1240 -> '1.240' (money in player messages)."""
    return f'{int(n):,}'.replace(',', '.')


def now() -> float:
    return time.time()


class MarriageError(Exception):
    def __init__(self, message: str, code: str = 'marriage_error', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(cond, message: str, code: str = 'marriage_error', status: int = 400):
    if not cond:
        raise MarriageError(message, code, status)


class _Retry(Exception):
    """A save moved under us (revision guard) or an effect was applied elsewhere."""


# ---------------------------------------------------------------- the save's display block
def blank() -> dict:
    return dict(v=VERSION, applied=[], spouse=None, sticker=False, weddings=0)


def validate_save(s: dict) -> None:
    """``s['marriage']`` (absent in older saves). Raises GameError like validate_state."""
    from .engine import need as eneed, integer
    m = s.get('marriage')
    if m is None:
        return
    eneed(isinstance(m, dict) and set(m) == set(blank()) and m.get('v') == VERSION, 'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
    eneed(isinstance(m['applied'], list) and len(m['applied']) <= APPLIED_KEPT
          and all(isinstance(x, str) and 1 <= len(x) <= 64 for x in m['applied']), 'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
    eneed(type(m['sticker']) is bool, 'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
    integer(m['weddings'], 0, 1000)
    sp = m['spouse']
    if sp is not None:
        eneed(isinstance(sp, dict) and SPOUSE_KEYS <= set(sp) <= SPOUSE_KEYS | SPOUSE_LINK and sp.get('status') in ('engaged', 'married'),
              'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
        eneed(set(sp) & SPOUSE_LINK in (set(), SPOUSE_LINK), 'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
        if 'couple' in sp:
            eneed(type(sp['couple']) is int and 1 <= sp['couple'] <= 10 ** 12 and sp['side'] in ('a', 'b'), 'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
        eneed(isinstance(sp['name'], str) and 1 <= len(sp['name']) <= 24, 'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
        integer(sp['since'], 1, 10 ** 6)
        eneed(sp['wed'] is None or (type(sp['wed']) is int and 1 <= sp['wed'] <= 10 ** 6), 'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')
        eneed(sp['date'] is None or (isinstance(sp['date'], str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', sp['date'])),
              'Dữ liệu hôn nhân không hợp lệ.', 'invalid_save')


def _box(s: dict) -> dict:
    """The block, repaired to a clean one when a hand-edited backup broke it."""
    try:
        validate_save(s)
        if isinstance(s.get('marriage'), dict):
            return s['marriage']
    except GameError:
        pass
    s['marriage'] = blank()
    return s['marriage']


def _jr():
    from . import journey
    return journey


def _life_day(s: dict) -> int:
    try:
        return max(1, int((s.get('journey') or {}).get('life_day') or 1))
    except (TypeError, ValueError):
        return 1


def _apply_effect(s: dict, e: dict) -> bool:
    """One effect row onto a save (False: this save already had it)."""
    m = _box(s)
    if e['id'] in m['applied']:
        return False
    if e['kind'] == 'wallet':
        amount = int(e['amount'])
        if amount:
            _jr()._wallet(s['journey'], amount, KIND, str(e['label'])[:120])
    elif e['kind'] == 'status':
        data = json.loads(e['data'] or '{}')
        what = data.get('set')
        link = (dict(couple=data['couple'], side=data['side'])
                if type(data.get('couple')) is int and data['couple'] >= 1 and data.get('side') in ('a', 'b') else {})
        if what == 'engaged':
            m['spouse'] = dict(name=str(data.get('name') or 'Người ấy')[:24], status='engaged', since=_life_day(s), wed=None, date=None, **link)
        elif what == 'married':
            sp = m['spouse'] if isinstance(m['spouse'], dict) else None
            m['spouse'] = dict(name=str(data.get('name') or (sp or {}).get('name') or 'Người ấy')[:24], status='married',
                               since=(sp or {}).get('since') or _life_day(s), wed=_life_day(s), date=data.get('date'),
                               **(link or {k: sp[k] for k in SPOUSE_LINK if sp and k in sp}))
            m['sticker'] = True
            m['weddings'] = min(1000, m['weddings'] + 1)
        elif what == 'link':
            if isinstance(m['spouse'], dict) and link:
                m['spouse'].update(link)
        elif what is None:
            m['spouse'] = None
            m['sticker'] = False
            from . import housing
            housing.leave_shared(s)
    elif e['kind'] == 'home':  # 🏠 the spouse's home (game/housing.py): moving in, or a home sold
        from . import housing
        data = json.loads(e['data'] or '{}')
        # Old pending auto-move effects cannot bypass the new explicit invitation.
        # Already shared saves are retained; only sold-home removals still use the inbox.
        if data.get('set') == 'out':
            housing.apply_effect(s, data)
    elif e['kind'] == 'bag':  # a small gift from the spouse, into the closeness gift bag
        item = json.loads(e['data'] or '{}').get('item')
        st = (s.get('journey') or {}).get('closeness')
        try:
            from .closeness_content import RECEIVED
            from .closeness import BAG_MAX
        except Exception:  # noqa: BLE001
            RECEIVED, BAG_MAX = {}, 0
        if item in RECEIVED and isinstance(st, dict) and isinstance(st.get('bag'), dict):
            st['bag'][item] = min(BAG_MAX, int(st['bag'].get(item, 0)) + 1)
    m['applied'] = (m['applied'] + [e['id']])[-APPLIED_KEPT:]
    return True


def _can_spend(s: dict, amount: int, how=None) -> bool:
    """Enough funds in the selected personal payment source (game/bank.py)."""
    from . import bank
    return bank.can_pay(s, amount, how if how in ('cash', 'card', 'account') else 'auto', no_joint=True)


def _spend(s: dict, e: dict, how=None) -> bool:
    """BANK.PAY: a purchase (a negative 'wallet' effect) follows this save's cash, account or card choice.
    Never the joint fund: this runs inside the store transaction."""
    from . import bank
    m, amount = _box(s), -int(e['amount'])
    how = how if how in ('cash', 'card', 'account') else 'auto'
    if e['id'] in m['applied'] or amount <= 0:
        return _apply_effect(s, e)
    selected = bank._method(s, amount, how, no_joint=True)
    account_only = how == 'account' or (how == 'auto' and (bank.get(s) or {}).get('pref') == 'account')
    if selected not in ('card', 'account') and not account_only:
        return _apply_effect(s, e)
    try:
        bank.pay(s, amount, str(e['label']), method=selected or 'account', kind=KIND, no_joint=True)
    except GameError as x:
        raise MarriageError(x.message, x.code, 400) from None
    (bank.get(s) or {}).pop('ting', None)   # the payment sound belongs to journey commands
    m['applied'] = (m['applied'] + [e['id']])[-APPLIED_KEPT:]
    return True


def _effect(eid: str, sid: str, kind: str, amount: int = 0, label: str = '', data: dict | None = None, due: float = 0.0) -> dict:
    return dict(id=eid[:64], sid=sid, kind=kind, amount=int(amount), label=label[:120], data=json.dumps(data or {}, ensure_ascii=False), due=due)


def _insert_effects(db, effects: list, status: str = 'pending') -> None:
    t = now()
    for e in effects:
        db.execute('INSERT INTO marriage_effects(id,sid,kind,amount,label,data,status,due,at,applied_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (e['id'], e['sid'], e['kind'], e['amount'], e['label'], e['data'], status, e['due'], t, t if status == 'applied' else None))


# ---------------------------------------------------------------- writing saves
def _read_state(store, sid: str):
    """(state, revision, text) of a save, migrated in memory; None when the save is gone."""
    with store.connect() as db:
        row = db.execute('SELECT revision,state FROM sessions WHERE sid=?', (sid,)).fetchone()
    if not row:
        return None
    state = migrate_state(store.parse_state(row['state'], sid), owned=True)
    return state, row['revision']


def _mutate(store, fns: dict, db_ops=None) -> dict:
    """Change one or more saves and the marriage tables atomically.

    fns: {sid: fn(state)} run on a fresh copy of each save (they may raise MarriageError);
    every save is fully validated, then all are written in ONE transaction under their
    revision guards, together with db_ops(db). A save that moved meanwhile raises _Retry
    (nothing written); the caller decides whether to compute again."""
    from .storage import serialize, _write_archive, _archive_rows
    prepared = {}
    with store.connect() as db:
        rows = {sid: db.execute('SELECT revision,state FROM sessions WHERE sid=?', (sid,)).fetchone() for sid in fns}
    for sid, fn in fns.items():
        row = rows[sid]
        need(row, 'Không tìm thấy tiến trình của người chơi này.', 'session_missing', 404)
        with ar.collect() as box:
            state = store.parse_state(row['state'], sid)
            before = dict(state['careers']) if isinstance(state.get('careers'), dict) else {}
            state = migrate_state(state, owned=True)
            fn(state)
            validate_state(state)
            validate_save(state)
        prepared[sid] = (row['revision'], serialize(state, None, True), _archive_rows(box, before, state, ''), state)

    def write(db):
        # Sorted: two couples' writes lock their saves in the same order (no PostgreSQL deadlock).
        for sid, (rev, text, cut, _) in sorted(prepared.items()):
            if db.execute('UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=? AND revision=?',
                          (text, rev + 1, sid, rev)).rowcount != 1:
                raise _Retry()
            _write_archive(db, sid, cut)
        from . import rentals
        for sid, (_, _, _, state) in sorted(prepared.items()):
            original = store.parse_state(rows[sid]['state'], sid)
            rentals.command_commit(db, sid, original, state, 'shared_mutation')
        return db_ops(db) if db_ops else None
    out = store.transaction(write)
    return dict(db=out, states={sid: (p[3], p[0] + 1) for sid, p in prepared.items()})


def _mutate_retry(store, fns: dict, db_ops=None, tries: int = 5) -> dict:
    for _ in range(tries):
        try:
            return _mutate(store, fns, db_ops)
        except _Retry:
            time.sleep(.01)
    raise MarriageError('Tiến trình đang thay đổi liên tục. Thử lại sau một chút nhé.', 'busy', 409)


def settle(store, sid: str) -> tuple | None:
    """Apply this save's pending effects (the inbox). Returns (state, revision) when it changed."""
    for _ in range(5):
        t = now()
        with store.connect() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM marriage_effects WHERE sid=? AND status='pending' AND due<=? ORDER BY at,id LIMIT 30",
                                                (sid, t))]
        if not rows:
            return None
        ids = [r['id'] for r in rows]

        def fn(s, rows=rows):
            for r in rows:
                _apply_effect(s, r)

        def db_ops(db, ids=ids, t=t):
            marks = ','.join('?' * len(ids))
            if db.execute(f"UPDATE marriage_effects SET status='applied',applied_at=? WHERE status='pending' AND id IN ({marks})",
                          (t, *ids)).rowcount != len(ids):
                raise _Retry()
        try:
            out = _mutate(store, {sid: fn}, db_ops)
        except _Retry:
            time.sleep(.01)
            continue
        return out['states'][sid]
    return None


# ---------------------------------------------------------------- people, codes, names
def _row(db, sql: str, args=()) -> dict | None:
    r = db.execute(sql, args).fetchone()
    return dict(r) if r else None


def _rows(db, sql: str, args=()) -> list:
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def _display(db, sid: str) -> str:
    r = db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()
    return _clean_name(r['display']) if r else 'Một người chơi'


def _clean_name(name) -> str:
    text = re.sub(r'[\x00-\x1f\x7f<>&"`]', '', str(name or '')).strip()
    return text[:24] or 'Một người chơi'


def whoami(store, token: str | None) -> tuple:
    """(sid, display) of a signed-in account, (sid, None) for a guest, (None, None) without a session."""
    if not token:
        return None, None
    sid, login = store.resolve(token)
    if not login:
        return sid, None
    with store.connect() as db:
        r = db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()
    return (sid, _clean_name(r['display'])) if r else (sid, None)


def _new_code() -> str:
    return 'PCC-' + ''.join(secrets.choice(CODE_CHARS) for _ in range(CODE_LEN))


def ensure_person(store, sid: str) -> dict:
    with store.connect() as db:
        p = _row(db, 'SELECT * FROM marriage_people WHERE sid=?', (sid,))
    if p:
        return p
    for _ in range(8):
        t = now()
        try:
            def add(db, code=_new_code(), t=t):
                db.execute('INSERT INTO marriage_people(sid,code,created,updated) VALUES(?,?,?,?) ON CONFLICT DO NOTHING', (sid, code, t, t))
            store.transaction(add)
        except dbm.IntegrityError:  # the code was taken: draw another
            continue
        with store.connect() as db:
            p = _row(db, 'SELECT * FROM marriage_people WHERE sid=?', (sid,))
        if p:
            return p
    raise MarriageError('Chưa tạo được mã người chơi. Thử lại nhé.', 'busy', 503)


def ensure_person_db(db, sid: str) -> None:
    """The same inside a transaction (friends: someone found by username gets a code)."""
    for _ in range(8):
        if db.execute('SELECT 1 FROM marriage_people WHERE sid=?', (sid,)).fetchone():
            return
        t = now()
        db.execute('INSERT INTO marriage_people(sid,code,created,updated) VALUES(?,?,?,?) ON CONFLICT DO NOTHING', (sid, _new_code(), t, t))


def bind(store) -> None:
    """Store.__init__ calls this: joint_account / joint_spend (game/couple.py) need the database
    while game/bank.py computes a save, and get only the save."""
    global STORE
    STORE = store


def clean_code(value) -> str:
    need(isinstance(value, str) and len(value) <= 20, 'Mã người chơi không hợp lệ.', 'bad_code')
    code = re.sub(r'[\s\-_.]', '', value.upper())
    if code.startswith('PCC'):
        code = code[3:]
    code = 'PCC-' + code
    need(CODE_RX.fullmatch(code), 'Mã người chơi có dạng PCC-XXXXXX (6 ký tự sau dấu gạch).', 'bad_code')
    return code


def _notice(db, sid: str, text: str) -> None:
    db.execute('UPDATE marriage_people SET notice=?,notice_at=? WHERE sid=?', (text[:200], now(), sid))


def _bond(db, sid: str) -> dict | None:
    return _row(db, 'SELECT c.* FROM marriage_bonds b JOIN couples c ON c.id=b.couple WHERE b.sid=?', (sid,))


def _side(couple: dict, sid: str) -> str:
    return 'a' if couple['a'] == sid else 'b'


def _other(couple: dict, sid: str) -> str:
    return couple['b'] if couple['a'] == sid else couple['a']


def _blocked(db, x: str, y: str) -> bool:
    return bool(db.execute('SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?)', (x, y, y, x)).fetchone())


def _split(amount: int, pct_a: int) -> tuple[int, int]:
    a = (amount * pct_a + 50) // 100
    return a, amount - a


def _ceil_pct(amount: int, pct: int) -> int:
    return -(-amount * pct // 100)


# ---------------------------------------------------------------- closeness and the guest pool
def _cl():
    """game/closeness.py ("Điểm thân quen") when it is there, else None."""
    try:
        from . import closeness as cl
    except Exception:  # noqa: BLE001 - absent or broken: the fallback below
        return None
    return cl if callable(getattr(cl, 'closeness', None)) and callable(getattr(cl, 'tier', None)) else None


def _tier(close: int) -> int:
    return 5 if close >= 80 else 4 if close >= 60 else 3 if close >= 40 else 2 if close >= 20 else 1


def neighbour(s: dict, who: str) -> dict:
    """How close this person is to the player: close 0–100, tier 1–5 (5 = "Như người nhà") and,
    from closeness.wedding(), the chance in % they come to a wedding (None: use the formula in
    _odds). THE one place that decides it: closeness.py when present; otherwise the neighbour
    bonds (tình làng nghĩa xóm, journey life) and the relationships built at work."""
    cl = _cl()
    if cl:
        try:
            close = max(0, min(100, int(cl.closeness(s, who))))
            t = int(cl.tier(s, who))
            attend = None
            if callable(getattr(cl, 'wedding', None)):
                attend = max(0, min(100, int(cl.wedding(s, who)['attend'])))
            return dict(close=close, tier=max(1, min(5, t)), attend=attend)
        except Exception:  # noqa: BLE001 - a bad save for that module: fall back
            pass
    bonds = (((s.get('journey') or {}).get('life') or {}).get('bonds') or {})
    if type(bonds.get(who)) is int:
        close = bonds[who]
    else:
        close = 0
        for c in (s.get('careers') or {}).values():
            v = ((c or {}).get('relationships') or {}).get(who) if isinstance(c, dict) else None
            if type(v) is int:
                close = max(close, v)
    close = max(0, min(100, close))
    return dict(close=close, tier=_tier(close), attend=None)


def closeness_of(s: dict, who: str) -> int:
    return neighbour(s, who)['close']


def pool_of(s: dict) -> dict:
    """The people who might come to this player's wedding, and how many people know them at all
    (the circle). Small enough to cache in marriage_people.pool (the partner may be offline)."""
    from .content import NPC_INDEX, CAREER_META
    from .life_content import GOSSIPS
    jr, cl = _jr(), _cl()
    people = {}
    for who, p in jr.CAST.items():
        people[who] = dict(id=who, name=p['name'], emoji=p['emoji'], role=p['role'], cast=True)
    for who, p in GOSSIPS.items():
        people[who] = dict(id=who, name=p['name'], emoji=p['emoji'], role=p['role'], cast=False)
    served = places = 0
    met = []
    for cid, c in (s.get('careers') or {}).items():
        if not isinstance(c, dict):
            continue
        n = int(((c.get('metrics') or {}).get('served')) or 0)
        served += n
        places += n > 0
        met += [(who, cid) for who, v in (c.get('relationships') or {}).items() if type(v) is int and v > 0]
    if cl and callable(getattr(cl, 'known', None)):
        try:
            met = [(who, (NPC_INDEX.get(who) or {}).get('career_id')) for who in cl.known(s)]
        except Exception:  # noqa: BLE001
            pass
    for who, cid in met:
        home = cl.home(who) if cl and callable(getattr(cl, 'home', None)) else who
        if home and home not in people and home in NPC_INDEX:
            npc = NPC_INDEX[home]
            people[home] = dict(id=home, name=str(npc.get('display_name') or home)[:32], emoji='🙂',
                                role=str(npc.get('role') or CAREER_META.get(cid, {}).get('place') or '')[:40], cast=False)
    rows = []
    for who, g in people.items():
        n = neighbour(s, who)
        if not g['cast'] and who not in GOSSIPS and n['close'] <= 0:
            continue
        rows.append(dict(g, **n))
    rows.sort(key=lambda g: (-g['close'], g['id']))
    rows = rows[:30]
    life = ((s.get('journey') or {}).get('life') or {})
    bonds = [v for v in (life.get('bonds') or {}).values() if type(v) is int]
    warmth = sum(bonds) // len(bonds) if bonds else 50
    trusts = []
    for c in (s.get('careers') or {}).values():
        box = ((c or {}).get('ext') or {}).get('incidents') if isinstance(c, dict) else None
        if isinstance(box, dict) and type(box.get('trust')) is int and c.get('started'):
            trusts.append(box['trust'])
    street = (warmth + (sum(trusts) // len(trusts) if trusts else 50)) // 2
    circle = 60 + 15 * places + min(150, served // 4) + len(rows)
    return dict(named=rows, circle=circle, street=street)


def _merge_pools(pa: dict | None, pb: dict | None) -> dict:
    """The couple's guests: a neighbour both spouses know counts once, at the higher closeness."""
    pa, pb = pa or {}, pb or {}
    named = {}
    for g in (pa.get('named') or []) + (pb.get('named') or []):
        if not isinstance(g, dict) or not isinstance(g.get('id'), str):
            continue
        cur = named.get(g['id'])
        if not cur or int(g.get('close', 0)) > int(cur.get('close', 0)):
            named[g['id']] = g
    rows = sorted(named.values(), key=lambda g: (-int(g.get('close', 0)), g['id']))
    circles = [int(p.get('circle', 0)) for p in (pa, pb) if p.get('circle')]
    streets = [int(p.get('street', 50)) for p in (pa, pb) if p.get('circle')]
    return dict(named=rows, circle=sum(circles) if circles else 150, street=sum(streets) // len(streets) if streets else 50)


# ---------------------------------------------------------------- plan, prices, forecast
def table_price(venue: str, menu: str) -> int:
    return (W.MENU_INDEX[menu]['price'] * W.VENUE_INDEX[venue]['menu_pct'] + 50) // 100


def clean_plan(p) -> dict:
    need(isinstance(p, dict), 'Kế hoạch cưới không hợp lệ.', 'bad_plan')
    venue = p.get('venue')
    need(venue in W.VENUE_INDEX, 'Chọn nơi tổ chức nhé.', 'bad_plan')
    v = W.VENUE_INDEX[venue]
    tables = p.get('tables')
    need(type(tables) is int and W.TABLES_MIN <= tables <= v['max_tables'],
         f'{v["name"]} nhận từ {W.TABLES_MIN} đến {v["max_tables"]} bàn.', 'bad_plan')
    menu = p.get('menu')
    need(menu in W.MENU_INDEX, 'Chọn thực đơn nhé.', 'bad_plan')
    cer = p.get('ceremonies') or {}
    need(isinstance(cer, dict) and set(cer) <= set(W.CEREMONY_INDEX), 'Nghi lễ không hợp lệ.', 'bad_plan')
    ceremonies = {}
    for cid in W.CEREMONY_INDEX:
        val = cer.get(cid, 0 if cid == 'an_hoi' else False)
        if cid == 'an_hoi':
            need(val in (0,) + W.AN_HOI_TRAYS and type(val) is int, 'Số mâm tráp ăn hỏi là 5, 7 hoặc 9.', 'bad_plan')
        else:
            need(type(val) is bool, 'Nghi lễ không hợp lệ.', 'bad_plan')
        ceremonies[cid] = val
    extras = p.get('extras') or []
    need(isinstance(extras, list) and len(extras) == len(set(extras)) and all(x in W.EXTRA_INDEX for x in extras),
         'Dịch vụ thêm không hợp lệ.', 'bad_plan')
    days = p.get('days', W.DAYS_DEFAULT)
    need(type(days) is int and W.DAYS_MIN <= days <= W.DAYS_MAX, f'Ngày cưới cách từ {W.DAYS_MIN} đến {W.DAYS_MAX} ngày sống.', 'bad_plan')
    out = dict(venue=venue, tables=tables, menu=menu, ceremonies=ceremonies, extras=[x['id'] for x in W.EXTRAS if x['id'] in extras], days=days)
    at = p.get('at')   # 💍 a real date and time (game/wedding_live.py); its window is checked when sent and confirmed
    if at is not None:
        need(type(at) in (int, float) and 1.6e9 < at < 4e9, 'Giờ cưới không hợp lệ.', 'bad_plan')
        out['at'] = int(at) // 60 * 60
    return out


def mood_points(plan: dict) -> int:
    pts = W.VENUE_INDEX[plan['venue']]['mood']
    for cid, val in plan['ceremonies'].items():
        if cid == 'an_hoi':
            pts += next((m for n, _, m in W.CEREMONY_INDEX['an_hoi']['options'] if n == val), 0)
        elif val:
            pts += W.CEREMONY_INDEX[cid]['mood']
    return pts + sum(W.EXTRA_INDEX[x]['mood'] for x in plan['extras'])


def mood_of(points: int) -> dict:
    low, emoji, label = next(m for m in W.MOODS if points >= m[0])
    return dict(points=points, emoji=emoji, label=label)


def costs(plan: dict) -> dict:
    """The breakdown: sections with lines and subtotals, total, deposit and balance."""
    v, m = W.VENUE_INDEX[plan['venue']], W.MENU_INDEX[plan['menu']]
    seats, tp = plan['tables'] * W.TABLE_SEATS, table_price(plan['venue'], plan['menu'])
    sections = [
        dict(id='venue', name='Địa điểm', lines=[dict(label=f'{v["emoji"]} {v["name"]} · phí địa điểm', amount=v['fee'])]),
        dict(id='reception', name='Tiệc', lines=[dict(label=f'{plan["tables"]} bàn × {tp} xu · thực đơn {m["name"].lower()}', amount=plan['tables'] * tp)]),
    ]
    cer = []
    for c in W.CEREMONIES:
        val = plan['ceremonies'].get(c['id'])
        if c['id'] == 'an_hoi':
            if val:
                price = next(pr for n, pr, _ in c['options'] if n == val)
                cer.append(dict(label=f'{c["name"]} · tráp {val} mâm', amount=price))
        elif val:
            cer.append(dict(label=c['name'], amount=c['price']))
    sections.append(dict(id='ceremony', name='Nghi lễ', lines=cer))
    ext = []
    for x in W.EXTRAS:
        if x['id'] in plan['extras']:
            if x.get('per10'):
                ext.append(dict(label=f'{x["emoji"]} {x["name"]} · {seats} khách', amount=x['per10'] * plan['tables']))
            else:
                ext.append(dict(label=f'{x["emoji"]} {x["name"]}', amount=x['price']))
    sections.append(dict(id='extras', name='Dịch vụ thêm', lines=ext))
    for sec in sections:
        sec['subtotal'] = sum(line['amount'] for line in sec['lines'])
    total = sum(sec['subtotal'] for sec in sections)
    deposit = _ceil_pct(total, W.DEPOSIT_PCT)
    return dict(sections=sections, total=total, deposit=deposit, balance=total - deposit, seats=seats, table_price=tp)


def _adj(plan: dict) -> float:
    """Tiền mừng shift (percent): a rich menu and a joyful party make guests a little more generous."""
    return (W.MENU_INDEX[plan['menu']]['gift_pct'] - 100) + min(mood_points(plan), 15) * 0.8


def _shift_mean(dist, adj: float) -> float:
    amounts = [a for a, _ in dist]
    total = sum(w for _, w in dist)
    q = min(1.0, abs(adj) / 100)
    out = 0.0
    for i, (a, w) in enumerate(dist):
        j = min(len(amounts) - 1, i + 1) if adj > 0 else max(0, i - 1)
        out += w / total * ((1 - q) * a + q * amounts[j])
    return out


def _pick(rng: random.Random, dist, adj: float) -> int:
    amounts = [a for a, _ in dist]
    total = sum(w for _, w in dist)
    r, i = rng.random() * total, 0
    for i, (_, w) in enumerate(dist):
        r -= w
        if r < 0:
            break
    if rng.random() < min(1.0, abs(adj) / 100):
        i = min(len(amounts) - 1, i + 1) if adj > 0 else max(0, i - 1)
    return amounts[i]


def _odds(plan: dict, pool: dict) -> dict:
    v = W.VENUE_INDEX[plan['venue']]
    cards = next((x.get('attend', 0) for x in W.EXTRAS if x['id'] == 'cards'), 0) if 'cards' in plan['extras'] else 0
    bonus = v['near'] + cards + min(mood_points(plan), 15) * 0.5
    seats = plan['tables'] * W.TABLE_SEATS
    named = [g for g in (pool.get('named') or [])][:seats]
    near = min(seats, max(int(pool.get('circle', 150)), len(named)))
    return dict(seats=seats, named=named, near=near, bonus=bonus,
                p_near=max(45.0, min(96.0, W.NEAR_ATTEND + (int(pool.get('street', 50)) - 50) * .3 + bonus)),
                p_named=lambda g: _p_named(g, bonus),
                rich=.30 if plan['venue'] == 'center' else .20)


def _p_named(g: dict, bonus: float) -> float:
    """Chance (%) that a named guest comes: closeness.wedding() by tier when present, else from
    the closeness score; a good party, thiệp mời and a home wedding bring a few more."""
    if type(g.get('attend')) is int:
        return max(5.0, min(98.0, g['attend'] + bonus * .5))
    return max(20.0, min(98.0, 35 + .6 * int(g.get('close', 0)) + bonus))


def forecast(plan: dict, pool: dict) -> dict:
    """Expected guests and tiền mừng (a band, not a promise)."""
    o, adj = _odds(plan, pool), _adj(plan)
    anon_mean = _shift_mean(W.VENUE_INDEX[plan['venue']]['gifts'], adj)
    g_named = sum(o['p_named'](g) / 100 for g in o['named'])
    m_named = sum(o['p_named'](g) / 100 * _shift_mean(W.TIER_GIFTS[max(1, min(5, int(g.get('tier', 1))))], adj)
                  for g in o['named'])
    anon = max(0, o['near'] - len(o['named'])) * o['p_near'] / 100 + (o['seats'] - o['near']) * W.FAR_ATTEND / 100
    rich = o['rich'] * (sum(r['amount'] for r in W.RICH) / len(W.RICH) - anon_mean)
    guests = min(o['seats'], g_named + anon)
    gifts = m_named + anon * anon_mean + rich
    return dict(guests=[max(0, round(guests * .93)), min(o['seats'], round(guests * 1.07))], expected_guests=round(guests),
                gifts=[round(gifts * .87), round(gifts * 1.13)], expected_gifts=round(gifts))


def quote(plan: dict, pool: dict | None = None, split_a: int = 50) -> dict:
    plan = clean_plan(plan)
    out = costs(plan)
    pool = pool or dict(named=[], circle=150, street=50)
    fc = forecast(plan, pool)
    dep = _split(out['deposit'], split_a)
    bal = _split(out['balance'], split_a)
    out.update(plan=plan, mood=mood_of(mood_points(plan)), forecast=fc, split_a=split_a,
               shares=dict(a=dict(deposit=dep[0], balance=bal[0]), b=dict(deposit=dep[1], balance=bal[1])),
               profit=[fc['gifts'][0] - out['total'], fc['gifts'][1] - out['total']])
    return out


# ---------------------------------------------------------------- the wedding day
def roll(seed: str, plan: dict, pool: dict, names: tuple = ('', '')) -> dict:
    """Who came and what they gave: seeded, so any retry or either spouse gets the same day."""
    rng = random.Random(seed)
    plan = clean_plan(plan)
    o, adj = _odds(plan, pool), _adj(plan)
    v = W.VENUE_INDEX[plan['venue']]
    came = []
    for g in o['named']:
        close = int(g.get('close', 0))
        if rng.random() * 100 < o['p_named'](g):
            tier = max(1, min(5, int(g.get('tier', 1))))
            came.append(dict(id=g['id'], name=str(g.get('name', ''))[:32], emoji=str(g.get('emoji', '🙂'))[:8], tier=tier,
                             tier_name=W.TIER_NAMES[tier], close=close, amount=_pick(rng, W.TIER_GIFTS[tier], adj), cast=bool(g.get('cast'))))
    anon = sum(rng.random() * 100 < o['p_near'] for _ in range(max(0, o['near'] - len(o['named']))))
    anon += sum(rng.random() * 100 < W.FAR_ATTEND for _ in range(o['seats'] - o['near']))
    highlights, late = [], []
    if anon and rng.random() < o['rich']:
        r = rng.choice(W.RICH)
        anon -= 1
        highlights.append(dict(kind='rich', name=r['name'], emoji=r['emoji'], amount=r['amount'], line=r['line']))
    if anon and rng.random() < .6:
        j = rng.choice(W.JOKES)
        anon -= 1
        highlights.append(dict(kind='joke', name=j['name'], emoji=j['emoji'], amount=j['amount'], line=j['line']))
    forgot = [f for f in W.FORGOT if f['who'] not in {g['id'] for g in came}]
    if anon and forgot and rng.random() < .5:
        f = rng.choice(forgot)
        anon -= 1
        highlights.append(dict(kind='forgot', name=f['name'], emoji=f['emoji'], amount=0, line=f['line']))
        late.append(dict(name=f['name'], amount=f['later']))
    weights = [30, 25, 20, 15, 10]
    groups = {g['id']: dict(id=g['id'], name=g['name'], emoji=g['emoji'], count=0, total=0) for g in W.GROUPS}
    ids = [g['id'] for g in W.GROUPS]
    for _ in range(anon):
        gid = rng.choices(ids, weights)[0]
        groups[gid]['count'] += 1
        groups[gid]['total'] += _pick(rng, v['gifts'], adj)
    guests = len(came) + anon + sum(1 for h in highlights)
    gifts = sum(g['amount'] for g in came) + sum(g['total'] for g in groups.values()) + sum(h['amount'] for h in highlights)
    # Speeches: the MC, then the closest neighbours who came (their own words), a gossip line.
    a, b = names
    speeches = []
    if 'mc' in plan['extras']:
        speeches.append(W.SPEECHES['mc'].format(a=a, b=b))
    for g in sorted(came, key=lambda g: (-g['close'], g['id'])):
        if len(speeches) >= 3:
            break
        if g['id'] in W.SPEECHES:
            speeches.append(W.SPEECHES[g['id']])
    if len(speeches) < 2:
        friend = next((g for g in came if not g['cast'] and g['id'] not in W.SPEECHES), None)
        speeches.append(W.SPEECHES['friend'].format(g=friend['name']) if friend else W.SPEECHES['plain'])
    # The result card lists the neighbours you know (Người quen and closer) who came, closest first.
    close = sorted((g for g in came if g['tier'] >= CARD_TIER), key=lambda g: (-g['tier'], -g['close'], -g['amount'], g['name']))
    guests = min(guests, o['seats'])
    return dict(guests=guests, seats=o['seats'], empty=o['seats'] - guests, named=len(came),
                close=[dict(name=g['name'], emoji=g['emoji'], tier=g['tier'], tier_name=g['tier_name'], amount=g['amount']) for g in close[:12]],
                groups=[g for g in groups.values() if g['count']], highlights=highlights[:6], late=late, late_total=sum(x['amount'] for x in late),
                gifts=gifts, speeches=speeches[:4], gossip=rng.choice(W.GOSSIP), mood=mood_of(mood_points(plan)))


# ---------------------------------------------------------------- news (the ticker)
_NEWS = {}                          # database path -> (fetched at, rows): every poll of every player reads this
_NEWS_LOCK = threading.Lock()


def _news_stale() -> None:
    with _NEWS_LOCK:
        _NEWS.clear()


def _post_news(db, kind: str, ref: str, text: str, a: str, b: str) -> bool:
    n = db.execute('INSERT INTO news(kind,ref,text,a,b,at) VALUES(?,?,?,?,?,?) ON CONFLICT DO NOTHING', (kind, ref, text[:200], a, b, now())).rowcount
    if n:
        _news_stale()
    return bool(n)


def _recent_news(store) -> list:
    t, key = now(), str(store.path)
    with _NEWS_LOCK:
        hit = _NEWS.get(key)
        if hit and 0 <= t - hit[0] < NEWS_CACHE_S:
            return hit[1]
    with store.connect() as db:
        rows = _rows(db, 'SELECT id,kind,text,at FROM news WHERE at>? ORDER BY id DESC LIMIT 20', (t - NEWS_WINDOW,))
    with _NEWS_LOCK:
        _NEWS[key] = (t, rows)
    return rows


def news(store, since, token: str | None = None) -> dict:
    """GET /api/news?since=<id>: recent weddings for the ticker (+ my marriage alerts when signed in)."""
    try:
        since = max(0, int(since or 0))
    except (TypeError, ValueError):
        since = 0
    rows = _recent_news(store)
    last = rows[0]['id'] if rows else 0
    t = now()
    if since > last:  # a database that started over: start over too
        since = 0
    if since:
        items = [r for r in rows if r['id'] > since][:5]
    else:
        items = [r for r in rows if r['at'] > t - NEWS_FIRST][:3]
    out = dict(items=[dict(id=r['id'], kind=r['kind'], text=r['text'], at=int(r['at'])) for r in reversed(items)], last=last)
    me = None
    if token:
        try:
            sid, display = whoami(store, token)
            if display:
                me = alerts(store, sid)
        except Exception:  # noqa: BLE001 - the ticker never fails for this
            me = None
    out['me'] = me
    return out


def alerts(store, sid: str) -> dict | None:
    with store.connect() as db:
        r = _row(db, """SELECT (SELECT COUNT(*) FROM proposals WHERE to_sid=? AND status='pending' AND at>?) AS incoming,
                               (SELECT notice FROM marriage_people WHERE sid=?) AS notice,
                               (SELECT notice_at FROM marriage_people WHERE sid=?) AS notice_at,
                               (SELECT couple FROM marriage_bonds WHERE sid=?) AS couple""", (sid, now() - W.PROPOSAL_DAYS * DAY, sid, sid, sid))
        if not r:
            return None
        n = int(r['incoming'] or 0) + (1 if r['notice'] else 0)
        from . import couple as cp
        friends = int(db.execute("SELECT COUNT(*) FROM friend_requests WHERE to_sid=? AND status='pending'", (sid,)).fetchone()[0])
        from .bank_xfer import waiting   # 💸 a friend's transfer waits: the client asks to receive it (game/bank_xfer.py)
        xfer = waiting(db, sid)
        n += cp.alerts(db, sid, r['couple'])
        n += int(db.execute("SELECT COUNT(*) FROM family_requests WHERE to_sid=? AND status='pending'",(sid,)).fetchone()[0])
        target = None
        if r['couple']:
            c = _row(db, 'SELECT * FROM couples WHERE id=?', (r['couple'],))
            w = _row(db, 'SELECT * FROM weddings WHERE couple=? ORDER BY id DESC LIMIT 1', (r['couple'],))
            if c and w:
                side = _side(c, sid)
                if w['status'] == 'proposed' and w['planner'] != sid:
                    n += 1
                if w['status'] == 'confirmed':
                    target = w['target_' + side]
                if w['status'] == 'done' and not w['seen_' + side]:
                    n += 1
    return dict(alerts=n, friends=friends, notice=r['notice'], notice_at=int(r['notice_at'] or 0), target=target, xfer=xfer)


# ---------------------------------------------------------------- loading a save: due weddings and the inbox
def on_load(store, token: str, state: dict | None) -> bool:
    """Bootstrap and GET /api/marriage: resolve a wedding whose day has come and apply this
    save's pending effects. True when the save changed. Cheap for everyone else (one query)."""
    sid, display = whoami(store, token)
    if not sid:
        return False
    return _on_load_sid(store, sid, state)


def _on_load_sid(store, sid: str, state: dict | None) -> bool:
    t = now()
    with store.connect() as db:
        r = db.execute("""SELECT (SELECT couple FROM marriage_bonds WHERE sid=?) AS couple,
                                 EXISTS(SELECT 1 FROM marriage_effects WHERE sid=? AND status='pending' AND due<=?) AS pending""",
                       (sid, sid, t)).fetchone()
    changed = False
    if r['couple']:
        day = _life_day(state) if state else None
        if day is not None:
            store.transaction(lambda db: db.execute('UPDATE marriage_people SET life_day=? WHERE sid=? AND (life_day IS NULL OR life_day<>?)', (day, sid, day)), 250)
        changed = _resolve_if_due(store, sid, day) or changed
    pending = r['pending']
    if state:  # anniversaries, card holds, old saves' couple link: they only add effects to the inbox
        from . import couple as cp
        with store.connect() as db:
            c = _bond(db, sid) if r['couple'] else None
        cp.on_load(store, sid, state, c)
        with store.connect() as db:
            pending = db.execute("SELECT 1 FROM marriage_effects WHERE sid=? AND status='pending' AND due<=? LIMIT 1", (sid, now())).fetchone()
    if pending or changed:
        changed = bool(settle(store, sid)) or changed
    return changed


def _resolve_if_due(store, sid: str, day: int | None) -> bool:
    with store.connect() as db:
        c = _bond(db, sid)
        if not c or c['status'] != 'engaged':
            return False
        w = _row(db, "SELECT * FROM weddings WHERE couple=? AND status='confirmed' ORDER BY id DESC LIMIT 1", (c['id'],))
        if not w:
            return False
        side, other = _side(c, sid), _other(c, sid)
        p = _row(db, 'SELECT life_day FROM marriage_people WHERE sid=?', (other,))
    mine = day if day is not None else 0
    theirs = int((p or {}).get('life_day') or 0)
    due = (mine >= int(w['target_' + side] or 10 ** 9) or theirs >= int(w['target_' + ('b' if side == 'a' else 'a')] or 10 ** 9)
           or (w['due_at'] is not None and now() >= float(w['due_at'])))
    if not due:
        return False
    return resolve(store, c['id'], w['id'])


def resolve(store, couple_id: int, wedding_id: int) -> bool:
    """The wedding day: decided once in the database, then applied to each save (the inbox)."""
    with store.connect() as db:
        c = _row(db, 'SELECT * FROM couples WHERE id=?', (couple_id,))
        w = _row(db, "SELECT * FROM weddings WHERE id=? AND status='confirmed'", (wedding_id,))
        if not c or not w or c['status'] != 'engaged':
            return False
        name_a, name_b = _display(db, c['a']), _display(db, c['b'])
    pools, days = {}, {}
    for side in ('a', 'b'):
        got = None
        try:
            got = _read_state(store, c[side])
        except Exception:  # noqa: BLE001 - an unreadable save still gets its wedding (default guests)
            got = None
        pools[side] = pool_of(got[0]) if got else None
        days[side] = _life_day(got[0]) if got else None
    plan = json.loads(w['plan'])
    q = json.loads(w['quote'])
    res = roll(f'wedding|{w["id"]}|{c["id"]}|{int(c["since"])}', plan, _merge_pools(pools['a'], pools['b']), (name_a, name_b))
    total, balance, pct = int(q['total']), int(q['balance']), int(w['split_a'])
    g = _split(res['gifts'], pct)
    bal = _split(balance, pct)
    late = _split(res['late_total'], pct)
    date = datetime.datetime.fromtimestamp(now(), datetime.timezone.utc).strftime('%Y-%m-%d')
    res.update(total=total, deposit=int(q['deposit']), balance=balance, profit=res['gifts'] + res['late_total'] - total,
               venue=W.VENUE_INDEX[plan['venue']]['name'], venue_emoji=W.VENUE_INDEX[plan['venue']]['emoji'], tables=plan['tables'],
               menu=W.MENU_INDEX[plan['menu']]['name'], names=dict(a=name_a, b=name_b), date=date, days=days, split_a=pct,
               shares=dict(a=dict(deposit=int(w['deposit_a']), gift=g[0], balance=bal[0], late=late[0], net=g[0] + late[0] - bal[0] - int(w['deposit_a'])),
                           b=dict(deposit=int(w['deposit_b']), gift=g[1], balance=bal[1], late=late[1], net=g[1] + late[1] - bal[1] - int(w['deposit_b']))))
    later = now() + 12 * 3600
    effects = []
    for i, side in enumerate(('a', 'b')):
        sid, partner = c[side], name_b if side == 'a' else name_a
        effects.append(_effect(f'gift:{w["id"]}:{side}', sid, 'wallet', g[i], 'Tiền mừng cưới (phần của bạn)'))
        # BANK.PAY: wedding balance stays a cash effect (applied later through the inbox; may push the wallet
        # into debt, which the bank's auto-sweep then covers from the account the next morning)
        effects.append(_effect(f'bal:{w["id"]}:{side}', sid, 'wallet', -bal[i], 'Trả nốt tiệc cưới (phần của bạn)'))
        effects.append(_effect(f'wed:{w["id"]}:{side}', sid, 'status', data=dict(set='married', name=partner, date=date, couple=c['id'], side=side)))
        if late[i]:
            who = res['late'][0]['name'] if res['late'] else 'Khách'
            effects.append(_effect(f'late:{w["id"]}:{side}', sid, 'wallet', late[i], f'{who} gửi bù phong bì cưới', due=later))

    def decide(db):
        if db.execute("UPDATE weddings SET status='done',result=?,done_at=? WHERE id=? AND status='confirmed'",
                      (json.dumps(res, ensure_ascii=False), now(), w['id'])).rowcount != 1:
            return False
        db.execute("UPDATE couples SET status='married',married_at=? WHERE id=? AND status='engaged'", (now(), c['id']))
        for side in ('a', 'b'):   # Giữ chân (game/retention.py): first marriage of each save
            rt.mark(db, c[side], 'married')
        _insert_effects(db, effects)
        if w['announce_a'] and w['announce_b']:
            _post_news(db, 'wedding', f'wedding:{w["id"]}', W.NEWS_TEXT.format(a=name_a, b=name_b, tables=plan['tables'], venue=res['venue']),
                       c['a'], c['b'])
        for side in ('a', 'b'):
            _notice(db, c[side], f'🎊 Đám cưới của {name_a} và {name_b} đã diễn ra: {res["guests"]} khách, tiền mừng {_xu(res["gifts"])} xu. Mở mục Hôn nhân để xem thiệp kỷ niệm!')
        return True
    if not store.transaction(decide):
        return False
    for side in ('a', 'b'):
        try:
            settle(store, c[side])
        except Exception:  # noqa: BLE001 - pending effects wait for that save's next load
            pass
    return True


# ---------------------------------------------------------------- views
def catalog() -> dict:
    return dict(
        rings=[dict(r, metal=W.RING_COLORS[r['id']][0], stone=W.RING_COLORS[r['id']][1], stones=bool(W.RING_COLORS[r['id']][1])) for r in W.RINGS],
        metals=W.METALS, stones=W.STONES, recolor_fee=W.RECOLOR_FEE, messages=W.MESSAGES,
        venues=[dict({k: v[k] for k in ('id', 'emoji', 'name', 'fee', 'max_tables', 'menu_pct', 'desc')},
                     table_price={m['id']: table_price(v['id'], m['id']) for m in W.MENUS}) for v in W.VENUES],
        menus=[{k: m[k] for k in ('id', 'name', 'price', 'dishes')} for m in W.MENUS],
        ceremonies=[dict({k: c[k] for k in ('id', 'name', 'desc')}, price=c.get('price'),
                         options=[dict(trays=n, price=p) for n, p, _ in c.get('options', ())]) for c in W.CEREMONIES],
        extras=[{k: x.get(k) for k in ('id', 'emoji', 'name', 'price', 'per10', 'desc')} for x in W.EXTRAS],
        deposit_pct=W.DEPOSIT_PCT, seats=W.TABLE_SEATS, tables=[W.TABLES_MIN, W.TABLES_MAX],
        days=[W.DAYS_MIN, W.DAYS_MAX, W.DAYS_DEFAULT], tiers=W.TIER_NAMES, sticker=W.STICKER,
        limits=dict(proposals_per_day=W.PROPOSALS_PER_DAY, decline_days=0, decline_hours=W.DECLINE_HOURS, remarry_days=0, remarry_hours=W.REMARRY_HOURS,
                    proposal_days=W.PROPOSAL_DAYS, rings_max=RINGS_MAX))


def ring_colors(tier: str, metal=None, stone=None) -> tuple:
    """(metal, stone) of a ring, the tier's own colours for anything unset or unknown."""
    dm, ds = W.RING_COLORS.get(tier, ('bac', None))
    metal = metal if metal in W.METAL_INDEX else dm
    stone = (stone if stone in W.STONE_INDEX else ds) if ds else None
    return metal, stone


def clean_colors(tier: str, d: dict) -> tuple:
    dm, ds = W.RING_COLORS[tier]
    metal, stone = d.get('metal', dm), d.get('stone', ds)
    need(metal in W.METAL_INDEX, 'Màu kim loại không hợp lệ.', 'bad_color')
    if ds:
        need(stone in W.STONE_INDEX, 'Màu đá không hợp lệ.', 'bad_color')
    else:
        need(stone is None, 'Mẫu nhẫn này không có đá.', 'bad_color')
    return metal, stone


def color_extra(tier: str, metal: str, stone) -> int:
    dm, ds = W.RING_COLORS[tier]
    extra = max(0, W.METAL_INDEX[metal]['extra'] - W.METAL_INDEX[dm]['extra'])
    if ds and stone:
        extra += max(0, W.STONE_INDEX[stone]['extra'] - W.STONE_INDEX[ds]['extra'])
    return extra


def _ring_view(r: dict) -> dict:
    spec = W.RING_INDEX.get(r['tier'], W.RINGS[0])
    metal, stone = ring_colors(r['tier'], r.get('metal'), r.get('stone'))
    m, st = W.METAL_INDEX[metal], W.STONE_INDEX.get(stone)
    return dict(id=r['id'], tier=r['tier'], name=spec['name'], emoji=spec['emoji'], tone=spec['tone'], price=r['price'], status=r['status'],
                sell_price=r['price'] * 80 // 100 if r['status'] == 'owned' else 0,
                metal=metal, stone=stone, metal_name=m['name'], stone_name=st['name'] if st else None,
                colors=dict(metal=m['hex'], metal_dark=m['dark'], stone=st['hex'] if st else None, stone_dark=st['dark'] if st else None))


def _expire(store, sid: str) -> None:
    """Unanswered proposals (mine, or to me) lapse after a week; their rings come back."""
    cut = now() - W.PROPOSAL_DAYS * DAY

    def run(db):
        old = _rows(db, "SELECT id,ring FROM proposals WHERE status='pending' AND at<? AND (from_sid=? OR to_sid=?)", (cut, sid, sid))
        for p in old:
            if db.execute("UPDATE proposals SET status='expired',decided=? WHERE id=? AND status='pending'", (now(), p['id'])).rowcount:
                db.execute("UPDATE marriage_rings SET status='owned' WHERE id=? AND status='proposed'", (p['ring'],))
    with store.connect() as db:
        if not db.execute("SELECT 1 FROM proposals WHERE status='pending' AND at<? AND (from_sid=? OR to_sid=?) LIMIT 1", (cut, sid, sid)).fetchone():
            return
    store.transaction(run)


def _wedding_view(db, c: dict, w: dict, sid: str, day: int) -> dict:
    side = _side(c, sid)
    other = 'b' if side == 'a' else 'a'
    q = json.loads(w['quote'])
    pct_mine = int(w['split_a']) if side == 'a' else 100 - int(w['split_a'])
    out = dict(id=w['id'], status=w['status'], version=w['version'], mine=w['planner'] == sid, plan=json.loads(w['plan']), quote=q,
               split_mine=pct_mine, announce_mine=bool(w['announce_' + side]), announce_partner=bool(w['announce_' + other]),
               days=w['days'], deposit_mine=int(w['deposit_' + side]), deposit_partner=int(w['deposit_' + other]),
               share_mine=q['shares'][side], share_partner=q['shares'][other], created=int(w['created']))
    if w['status'] == 'confirmed':
        target = int(w['target_' + side] or 0)
        p = _row(db, 'SELECT life_day FROM marriage_people WHERE sid=?', (c[other],))
        left_theirs = int(w['target_' + other] or 0) - int((p or {}).get('life_day') or 0)
        out.update(target=target, left=max(0, min(target - day, left_theirs)), left_mine=max(0, target - day),
                   due_at=int(w['due_at'] or 0), hours_left=max(0, int(((w['due_at'] or 0) - now()) // 3600)))
        at = out['plan'].get('at')
        if at:   # 💍 booked at a real date and time: no life-day countdown (game/wedding_live.py)
            from . import wedding_live as wl
            out.update(at=int(at), at_label=wl.fmt_at(at), left=max(0, wl.days_between(now(), at)), left_mine=max(0, wl.days_between(now(), at)))
    if w['status'] == 'done' and w['result']:
        out['result'] = json.loads(w['result'])
        out['side'] = side
        out['seen'] = bool(w['seen_' + side])
    return out


def view(store, token: str, state: dict | None, with_catalog: bool = False) -> dict:
    """GET /api/marriage: everything the Hôn nhân sheet shows, for this player only."""
    sid, display = whoami(store, token)
    out = dict(guest=display is None)
    if with_catalog:
        out['catalog'] = catalog()
    if not sid or display is None:
        return out
    person = ensure_person(store, sid)
    from . import friends as fr
    fr.ensure_codes(store, sid)
    changed = _on_load_sid(store, sid, state)
    if changed:
        got = store.read(token)
        state = got[0]
        out.update(state=public_state(state), revision=got[1])
    _expire(store, sid)
    day = _life_day(state) if state else 1
    pool = json.dumps(pool_of(state), ensure_ascii=False) if state else None
    t = now()
    if pool and (person.get('pool') != pool or person.get('life_day') != day):
        # The guest list the partner's wedding day will use even when this player is offline.
        store.transaction(lambda db: db.execute('UPDATE marriage_people SET pool=?,life_day=?,updated=? WHERE sid=?', (pool, day, t, sid)), 250)
    with store.connect() as db:
        person = _row(db, 'SELECT * FROM marriage_people WHERE sid=?', (sid,))
        today = _rows(db, 'SELECT id FROM proposals WHERE from_sid=? AND at>?', (sid, t - DAY))
        rings = [_ring_view(r) for r in _rows(db, "SELECT * FROM marriage_rings WHERE sid=? AND status IN ('owned','proposed') ORDER BY at", (sid,))]
        incoming = []
        for p in _rows(db, "SELECT * FROM proposals WHERE to_sid=? AND status='pending' ORDER BY id DESC LIMIT 10", (sid,)):
            ring = _row(db, 'SELECT * FROM marriage_rings WHERE id=?', (p['ring'],))
            fp = _row(db, 'SELECT code FROM marriage_people WHERE sid=?', (p['from_sid'],))
            incoming.append(dict(id=p['id'], name=_display(db, p['from_sid']), code=(fp or {}).get('code'), ring=_ring_view(ring) if ring else None,
                                 message=W.MESSAGE_INDEX.get(p['message'], W.MESSAGES[0])['text'], at=int(p['at']),
                                 expires=int(p['at'] + W.PROPOSAL_DAYS * DAY)))
        outgoing = []
        for p in _rows(db, "SELECT * FROM proposals WHERE from_sid=? AND (status='pending' OR (status IN ('declined','accepted') AND decided>?)) ORDER BY id DESC LIMIT 10",
                       (sid, t - 3 * DAY)):
            ring = _row(db, 'SELECT * FROM marriage_rings WHERE id=?', (p['ring'],))
            tp = _row(db, 'SELECT code FROM marriage_people WHERE sid=?', (p['to_sid'],))
            outgoing.append(dict(id=p['id'], name=_display(db, p['to_sid']), code=(tp or {}).get('code'), status=p['status'],
                                 ring=_ring_view(ring) if ring else None, message=W.MESSAGE_INDEX.get(p['message'], W.MESSAGES[0])['text'], at=int(p['at'])))
        blocks = []
        for b in _rows(db, 'SELECT target FROM marriage_blocks WHERE sid=? ORDER BY at DESC LIMIT 30', (sid,)):
            tp = _row(db, 'SELECT code FROM marriage_people WHERE sid=?', (b['target'],))
            if tp:
                blocks.append(dict(name=_display(db, b['target']), code=tp['code']))
        couple = wedding = last = None
        c = _bond(db, sid)
        if c:
            other = _other(c, sid)
            op = _row(db, 'SELECT code FROM marriage_people WHERE sid=?', (other,))
            cring = _row(db, 'SELECT * FROM marriage_rings WHERE id=?', (c['ring'],)) if c['ring'] else None
            couple = dict(id=c['id'], status=c['status'], partner=dict(name=_display(db, other), code=(op or {}).get('code')),
                          ring=_ring_view(cring) if cring else None,
                          since=int(c['since']), married_at=int(c['married_at']) if c['married_at'] else None,
                          days_together=max(0, int((t - c['since']) // DAY)))
            from . import wedding_live as wl
            couple['wed_label'] = wl.label_of(db, c)   # 💍 "Cưới ngày 04/10/2026 · 20:30" (booked, or the legacy date)
            couple['party'] = wl.party_view(db, c, t)   # 🎉 the 10-minute live party: choose its time, invite, watch it go
            w = _row(db, "SELECT * FROM weddings WHERE couple=? AND status IN ('proposed','rejected','confirmed','done') ORDER BY id DESC LIMIT 1", (c['id'],))
            if w:
                wedding = _wedding_view(db, c, w, sid, day)
        else:
            w = _row(db, "SELECT w.* FROM weddings w JOIN couples c ON c.id=w.couple WHERE (c.a=? OR c.b=?) AND w.status='done' ORDER BY w.id DESC LIMIT 1", (sid, sid))
            if w:
                c0 = _row(db, 'SELECT * FROM couples WHERE id=?', (w['couple'],))
                last = dict(status=c0['status'], date=json.loads(w['result']).get('date')) if c0 else None
        from . import friends as fr, couple as cp, family as fam
        friends = fr.view(db, sid)
        home = cp.view(db, sid, c)
        family = fam.view(db, sid, c, state or {})
        bag = (((state or {}).get('journey') or {}).get('closeness') or {}).get('bag')
        home['bag'] = {k: int(n) for k, n in bag.items() if k in home['gifts'] and type(n) is int and n > 0} if isinstance(bag, dict) else {}
    j = (state or {}).get('journey') or {}
    out.update(me=dict(code=person['code'], name=display, accept=bool(person['accept']), wallet=int(j.get('wallet', 0)), life_day=day,
                       cooldown=int(person['remarry_after']) if person['remarry_after'] > t else 0,
                       proposals_left=max(0, W.PROPOSALS_PER_DAY - len(today)), notice=person['notice'], notice_at=int(person['notice_at'] or 0),
                       sticker=bool(((state or {}).get('marriage') or {}).get('sticker'))),
               rings=rings, incoming=incoming, outgoing=outgoing, blocks=blocks, couple=couple, wedding=wedding, last=last,
               friends=friends, home=home, family=family)
    return out


# ---------------------------------------------------------------- actions
def _require(store, token: str) -> tuple:
    sid, display = whoami(store, token)
    need(sid, 'Tải lại trang để bắt đầu phiên chơi.', 'session_missing', 401)
    need(display, 'Tạo tài khoản để kết hôn nhé.', 'account_required', 403)
    ensure_person(store, sid)
    return sid, display


def _rid(d: dict) -> str:
    rid = d.get('rid')
    if isinstance(rid, str) and re.fullmatch(r'[A-Za-z0-9\-]{8,64}', rid):
        return rid
    return secrets.token_hex(8)


def act(store, token: str, op: str, d: dict) -> dict:
    """POST /api/marriage/<op>. Returns {message, changed}."""
    need(isinstance(d, dict), 'Dữ liệu không hợp lệ.')
    if op == 'quote':
        sid, _ = whoami(store, token)
        pool, pct = None, 50
        if sid:
            with store.connect() as db:
                c = _bond(db, sid)
                if c:
                    pa = _row(db, 'SELECT pool FROM marriage_people WHERE sid=?', (c['a'],))
                    pb = _row(db, 'SELECT pool FROM marriage_people WHERE sid=?', (c['b'],))
                    pool = _merge_pools(json.loads((pa or {}).get('pool') or '{}'), json.loads((pb or {}).get('pool') or '{}'))
                    mine = d.get('mine', 50)
                    need(type(mine) is int and 0 <= mine <= 100, 'Tỉ lệ góp không hợp lệ.', 'bad_plan')
                    pct = mine if _side(c, sid) == 'a' else 100 - mine
        return dict(message='', quote=quote(d.get('plan'), pool, pct), quiet=True)
    sid, display = _require(store, token)
    handler = ACTIONS.get(op) or _more_actions().get(op)
    need(handler, 'Không có thao tác này.', 'not_found', 404)
    return handler(store, sid, display, d)


def _more_actions() -> dict:
    from . import friends as fr, couple as cp, family as fam
    return {**fr.ACTIONS, **cp.ACTIONS, **fam.ACTIONS}


def _ring_buy(store, sid: str, display: str, d: dict) -> dict:
    tier = d.get('tier')
    need(tier in W.RING_INDEX, 'Mẫu nhẫn không hợp lệ.', 'bad_ring')
    metal, stone = clean_colors(tier, d)
    spec = dict(W.RING_INDEX[tier])
    spec['price'] += color_extra(tier, metal, stone)
    ring_id = 'r' + secrets.token_hex(6)
    eid = f'ring:{sid[:16]}:{_rid(d)}'
    with store.connect() as db:
        if db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (eid,)).fetchone():
            return dict(message='Nhẫn này bạn đã mua rồi.', changed=False)
        owned = db.execute("SELECT COUNT(*) FROM marriage_rings WHERE sid=? AND status IN ('owned','proposed')", (sid,)).fetchone()[0]
    need(owned < RINGS_MAX, f'Bạn đang giữ {RINGS_MAX} chiếc nhẫn rồi. Cất bớt ý định lại nhé!', 'too_many_rings')
    # BANK.PAY: ring purchase: cash or the credit card (_spend)
    eff = _effect(eid, sid, 'wallet', -spec['price'], f'Mua {spec["name"]}')

    def fn(s):
        need(_can_spend(s, spec['price'], d.get('pay')), f'Ví chưa đủ {spec["price"]} xu để mua {spec["name"].lower()}. Rút tiền lời từ nơi làm việc về ví trước nhé.',
             'not_enough', 400)
        _spend(s, eff, d.get('pay'))

    def ops(db):
        db.execute('INSERT INTO marriage_rings(id,sid,tier,price,status,at,metal,stone) VALUES(?,?,?,?,?,?,?,?)',
                   (ring_id, sid, tier, spec['price'], 'owned', now(), metal, stone))
        _insert_effects(db, [eff], 'applied')
    try:
        _mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:
        return dict(message='Nhẫn này bạn đã mua rồi.', changed=False)
    return dict(message=f'Đã mua {spec["name"].lower()} ({spec["price"]} xu). Giờ chỉ còn thiếu một lời cầu hôn.', changed=True)


def _ring_sell(store, sid: str, display: str, d: dict) -> dict:
    """Sell only a spare owned ring; wallet and guarded receipt commit together."""
    ring_id = d.get('ring')
    need(isinstance(ring_id, str) and 1 <= len(ring_id) <= 20, 'Chọn một chiếc nhẫn trong hộp.', 'bad_ring')
    eid = 'ring-sell:' + ring_id
    with store.connect() as db:
        r = _row(db, 'SELECT * FROM marriage_rings WHERE id=? AND sid=?', (ring_id, sid))
        need(r, 'Không tìm thấy chiếc nhẫn này trong hộp của bạn.', 'bad_ring', 404)
        if r['status'] == 'sold':
            return dict(message='Chiếc nhẫn này đã được bán, tiền đã về ví.', changed=False)
        need(r['status'] == 'owned', 'Chỉ bán được nhẫn dư trong hộp. Nhẫn đang cầu hôn hoặc nhẫn của hai bạn được giữ lại.', 'bad_ring', 409)
    amount = r['price'] * 80 // 100
    eff = _effect(eid, sid, 'wallet', amount, 'Bán nhẫn dư tại tiệm kim hoàn')

    def ops(db):
        need(db.execute("UPDATE marriage_rings SET status='sold' WHERE id=? AND sid=? AND status='owned'", (ring_id, sid)).rowcount == 1,
             'Chiếc nhẫn vừa thay đổi. Mở lại hộp nhẫn nhé.', 'bad_ring', 409)
        _insert_effects(db, [eff], 'applied')
    _mutate_retry(store, {sid: lambda s: _apply_effect(s, eff)}, ops)
    return dict(message=f'Đã bán nhẫn dư, {amount} xu vào ví (80% giá mua nhẫn).', changed=True)


def _ring_recolor(store, sid: str, display: str, d: dict) -> dict:
    """Tiệm kim hoàn: re-colour a ring in your box, or the ring the two of you wear."""
    ring_id = d.get('ring')
    need(isinstance(ring_id, str) and len(ring_id) <= 20, 'Chọn một chiếc nhẫn nhé.', 'bad_ring')
    eid = f'recolor:{ring_id}:{_rid(d)}'
    with store.connect() as db:
        if db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (eid[:64],)).fetchone():
            return dict(message='Nhẫn đã đổi màu rồi.', changed=False)
        r = _row(db, 'SELECT * FROM marriage_rings WHERE id=?', (ring_id,))
        c = _bond(db, sid)
        mine = bool(r and ((r['sid'] == sid and r['status'] == 'owned') or (c and c['ring'] == ring_id and r['status'] == 'given')))
    need(r and (mine or (r['sid'] == sid and r['status'] == 'proposed')), 'Không tìm thấy chiếc nhẫn này.', 'bad_ring', 404)
    need(mine, 'Chiếc nhẫn đang nằm trong một lời cầu hôn, chờ trả lời đã nhé.', 'bad_ring', 409)
    metal, stone = clean_colors(r['tier'], d)
    now_metal, now_stone = ring_colors(r['tier'], r['metal'], r['stone'])
    need((metal, stone) != (now_metal, now_stone), 'Nhẫn đang đúng màu này rồi.', 'same_color')
    fee = W.RECOLOR_FEE + max(0, color_extra(r['tier'], metal, stone) - color_extra(r['tier'], now_metal, now_stone))
    name = W.RING_INDEX[r['tier']]['name']
    # BANK.PAY: jeweller fee: cash or the credit card (_spend)
    eff = _effect(eid, sid, 'wallet', -fee, f'Tiệm kim hoàn: đổi màu {name.lower()}')

    def fn(s):
        need(_can_spend(s, fee, d.get('pay')), f'Ví chưa đủ {fee} xu để đổi màu nhẫn.', 'not_enough')
        _spend(s, eff, d.get('pay'))

    def ops(db):
        need(db.execute("UPDATE marriage_rings SET metal=?,stone=? WHERE id=? AND status IN ('owned','given')", (metal, stone, ring_id)).rowcount == 1,
             'Chiếc nhẫn vừa thay đổi. Xem lại nhé.', 'bad_ring', 409)
        _insert_effects(db, [eff], 'applied')
        if c and c['ring'] == ring_id:
            _notice(db, _other(c, sid), f'💍 {display} vừa mang nhẫn cưới ra tiệm kim hoàn: giờ là {W.METAL_INDEX[metal]["name"].lower()}'
                    + (f', đá {W.STONE_INDEX[stone]["name"].lower()}.' if stone else '.'))
    try:
        _mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:
        return dict(message='Nhẫn đã đổi màu rồi.', changed=False)
    return dict(message=f'Tiệm kim hoàn đã làm xong ({fee} xu): {W.METAL_INDEX[metal]["name"].lower()}'
                + (f', {W.STONE_INDEX[stone]["name"].lower()}.' if stone else '.'), changed=True)


def _find(db, code: str) -> dict | None:
    return _row(db, 'SELECT p.* FROM marriage_people p JOIN accounts a ON a.sid=p.sid WHERE p.code=?', (code,))


def _can_propose(db, sid: str, target: dict | None) -> str | None:
    """Why this proposal cannot go out (None: it can). Same words whatever the hidden reason."""
    t = now()
    if not target:
        return 'Không tìm thấy người chơi có mã này.'
    if target['sid'] == sid:
        return 'Đây là mã của chính bạn.'
    me = _row(db, 'SELECT * FROM marriage_people WHERE sid=?', (sid,))
    if me and me['remarry_after'] > t:
        return f'Bạn vừa khép lại một cuộc hôn nhân. Cho lòng nghỉ {W.REMARRY_HOURS} tiếng rồi hẵng tính tiếp nhé.'
    if _bond(db, sid):
        return 'Bạn đang có đôi rồi.'
    if _blocked(db, sid, target['sid']):
        return 'Không gửi được lời cầu hôn tới người này.'
    if not db.execute('SELECT 1 FROM friends WHERE sid=? AND friend=?', (sid, target['sid'])).fetchone():
        return 'Chỉ cầu hôn được bạn bè. Kết bạn trước nhé (mục 👥 Bạn bè).'
    if not target['accept']:
        return 'Người này đang tắt nhận lời cầu hôn.'
    if _bond(db, target['sid']) or target['remarry_after'] > t:
        return 'Người này hiện chưa nhận lời cầu hôn.'
    if db.execute("SELECT 1 FROM proposals WHERE from_sid=? AND to_sid=? AND status='pending'", (sid, target['sid'])).fetchone():
        return 'Bạn đã gửi lời cầu hôn tới người này rồi, chờ hồi âm nhé.'
    if db.execute("SELECT 1 FROM proposals WHERE from_sid=? AND to_sid=? AND status='declined' AND decided>?",
                  (sid, target['sid'], t - W.DECLINE_HOURS * 3600)).fetchone():
        return f'Người ấy vừa từ chối. Cho nhau {W.DECLINE_HOURS} tiếng để nghĩ thêm nhé.'
    if db.execute('SELECT COUNT(*) FROM proposals WHERE from_sid=? AND at>?', (sid, t - DAY)).fetchone()[0] >= W.PROPOSALS_PER_DAY:
        return f'Mỗi ngày chỉ gửi được {W.PROPOSALS_PER_DAY} lời cầu hôn. Mai thử lại nhé.'
    return None


def _lookup(store, sid: str, display: str, d: dict) -> dict:
    code = clean_code(d.get('code'))
    with store.connect() as db:
        target = _find(db, code)
        why = _can_propose(db, sid, target)
        name = _display(db, target['sid']) if target and target['sid'] != sid and not _blocked(db, sid, target['sid']) else None
    return dict(message='', found=dict(code=code, name=name, can=why is None, why=why))


def _propose(store, sid: str, display: str, d: dict) -> dict:
    code = clean_code(d.get('code'))
    msg = d.get('message')
    need(msg in W.MESSAGE_INDEX, 'Chọn một lời cầu hôn soạn sẵn nhé.', 'bad_message')
    announce = d.get('announce', True)
    need(type(announce) is bool, 'Lựa chọn không hợp lệ.')
    ring_id = d.get('ring')
    need(isinstance(ring_id, str) and len(ring_id) <= 20, 'Chọn một chiếc nhẫn nhé.', 'bad_ring')
    _expire(store, sid)

    def run(db):
        target = _find(db, code)
        why = _can_propose(db, sid, target)
        need(why is None, why or '', 'cannot_propose', 409)
        need(db.execute("UPDATE marriage_rings SET status='proposed' WHERE id=? AND sid=? AND status='owned'", (ring_id, sid)).rowcount == 1,
             'Chiếc nhẫn này không còn trong hộp của bạn.', 'bad_ring')
        db.execute('INSERT INTO proposals(from_sid,to_sid,ring,message,announce,status,at) VALUES(?,?,?,?,?,?,?)',
                   (sid, target['sid'], ring_id, msg, int(announce), 'pending', now()))
        _notice(db, target['sid'], f'💍 {display} vừa gửi lời cầu hôn tới bạn. Mở mục Hôn nhân để trả lời nhé.')
        return _display(db, target['sid'])
    name = store.transaction(run)
    return dict(message=f'Đã gửi lời cầu hôn tới {name}. Chờ người ấy trả lời nhé!', changed=False)


def _respond(store, sid: str, display: str, d: dict) -> dict:
    pid = d.get('id')
    need(type(pid) is int, 'Lời cầu hôn không hợp lệ.')
    answer = d.get('answer')
    need(answer in ('accept', 'decline'), 'Trả lời không hợp lệ.')
    announce = d.get('announce', True)
    need(type(announce) is bool, 'Lựa chọn không hợp lệ.')
    t = now()
    with store.connect() as db:
        p = _row(db, "SELECT * FROM proposals WHERE id=? AND to_sid=?", (pid, sid))
    need(p and p['status'] == 'pending' and p['at'] > t - W.PROPOSAL_DAYS * DAY, 'Lời cầu hôn này không còn chờ trả lời.', 'gone', 409)
    if answer == 'decline':
        def run(db):
            need(db.execute("UPDATE proposals SET status='declined',decided=? WHERE id=? AND status='pending'", (now(), pid)).rowcount == 1,
                 'Lời cầu hôn này không còn chờ trả lời.', 'gone', 409)
            db.execute("UPDATE marriage_rings SET status='owned' WHERE id=? AND status='proposed'", (p['ring'],))
            _notice(db, p['from_sid'], f'{display} chưa nhận lời cầu hôn lần này. Chiếc nhẫn vẫn nằm trong hộp của bạn.')
        store.transaction(run)
        return dict(message='Đã từ chối nhẹ nhàng. Chiếc nhẫn vẫn là của người gửi.', changed=False)
    other = p['from_sid']

    def run(db):
        need(db.execute("UPDATE proposals SET status='accepted',decided=? WHERE id=? AND status='pending'", (now(), pid)).rowcount == 1,
             'Lời cầu hôn này không còn chờ trả lời.', 'gone', 409)
        for who in (sid, other):
            pp = _row(db, 'SELECT remarry_after FROM marriage_people WHERE sid=?', (who,))
            need(not pp or pp['remarry_after'] <= now(), f'Một trong hai bạn vừa khép lại một cuộc hôn nhân, chờ thêm {W.REMARRY_HOURS} tiếng nhé.', 'cooldown', 409)
        need(not _blocked(db, sid, other), 'Không nhận lời được.', 'blocked', 409)
        sql, args = "INSERT INTO couples(a,b,ring,status,since) VALUES(?,?,?,'engaged',?)", (other, sid, p['ring'], now())
        cid = db.execute(sql + ' RETURNING id', args).fetchone()[0]
        try:
            db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', (other, cid))
            db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', (sid, cid))
        except dbm.IntegrityError:
            raise MarriageError('Một trong hai bạn vừa nhận lời người khác rồi.', 'taken', 409) from None
        for who in (other, sid):   # Giữ chân (game/retention.py): first engagement of each save
            rt.mark(db, who, 'engaged')
        db.execute("UPDATE marriage_rings SET status='given' WHERE id=?", (p['ring'],))
        # Every other proposal from or to either of us ends here; their rings go back to the box.
        for q in _rows(db, "SELECT id,ring FROM proposals WHERE status='pending' AND (from_sid IN (?,?) OR to_sid IN (?,?))", (sid, other, sid, other)):
            db.execute("UPDATE proposals SET status='cancelled',decided=? WHERE id=?", (now(), q['id']))
            db.execute("UPDATE marriage_rings SET status='owned' WHERE id=? AND status='proposed'", (q['ring'],))
        name_other = _display(db, other)
        _insert_effects(db, [_effect(f'eng:{cid}:a', other, 'status', data=dict(set='engaged', name=display, couple=cid, side='a')),
                             _effect(f'eng:{cid}:b', sid, 'status', data=dict(set='engaged', name=name_other, couple=cid, side='b'))])
        if p['announce'] and announce:
            _post_news(db, 'engaged', f'engaged:{cid}', W.NEWS_ENGAGED.format(a=name_other, b=display), other, sid)
        _notice(db, other, f'💞 {display} đã nhận lời cầu hôn của bạn! Hai bạn cùng lên kế hoạch cưới nhé.')
        return name_other
    name_other = store.transaction(run)
    for who in (sid, other):
        try:
            settle(store, who)
        except Exception:  # noqa: BLE001
            pass
    return dict(message=f'💞 Bạn và {name_other} đã đính hôn! Cùng lên kế hoạch cưới nhé.', changed=True)


def _cancel(store, sid: str, display: str, d: dict) -> dict:
    pid = d.get('id')
    need(type(pid) is int, 'Lời cầu hôn không hợp lệ.')

    def run(db):
        p = _row(db, "SELECT * FROM proposals WHERE id=? AND from_sid=?", (pid, sid))
        need(p and db.execute("UPDATE proposals SET status='cancelled',decided=? WHERE id=? AND status='pending'", (now(), pid)).rowcount == 1,
             'Lời cầu hôn này không còn chờ trả lời.', 'gone', 409)
        db.execute("UPDATE marriage_rings SET status='owned' WHERE id=? AND status='proposed'", (p['ring'],))
    store.transaction(run)
    return dict(message='Đã rút lại lời cầu hôn. Chiếc nhẫn về lại hộp của bạn.', changed=False)


def _target_sid(db, sid: str, d: dict) -> str:
    if type(d.get('id')) is int:
        p = _row(db, 'SELECT from_sid FROM proposals WHERE id=? AND to_sid=?', (d['id'], sid))
        need(p, 'Không tìm thấy người này.', 'not_found', 404)
        return p['from_sid']
    target = _find(db, clean_code(d.get('code')))
    need(target and target['sid'] != sid, 'Không tìm thấy người này.', 'not_found', 404)
    return target['sid']


def _block(store, sid: str, display: str, d: dict) -> dict:
    def run(db):
        other = _target_sid(db, sid, d)
        from . import home_guests
        home_guests.lock_pair(db,sid,other)
        db.execute('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?) ON CONFLICT DO NOTHING', (sid, other, now()))
        home_guests.invalidate(db,sid)
        for q in _rows(db, "SELECT id,ring FROM proposals WHERE status='pending' AND ((from_sid=? AND to_sid=?) OR (from_sid=? AND to_sid=?))",
                       (sid, other, other, sid)):
            db.execute("UPDATE proposals SET status='cancelled',decided=? WHERE id=?", (now(), q['id']))
            db.execute("UPDATE marriage_rings SET status='owned' WHERE id=? AND status='proposed'", (q['ring'],))
    store.transaction(run)
    return dict(message='Đã chặn. Người này không gửi lời cầu hôn cho bạn được nữa.', changed=False)


def _unblock(store, sid: str, display: str, d: dict) -> dict:
    def run(db):
        other = _target_sid(db, sid, d)
        db.execute('DELETE FROM marriage_blocks WHERE sid=? AND target=?', (sid, other))
    store.transaction(run)
    return dict(message='Đã bỏ chặn.', changed=False)


def _settings(store, sid: str, display: str, d: dict) -> dict:
    accept = d.get('accept')
    need(type(accept) is bool, 'Thiết lập không hợp lệ.')
    store.transaction(lambda db: db.execute('UPDATE marriage_people SET accept=?,updated=? WHERE sid=?', (int(accept), now(), sid)))
    return dict(message='Đã bật nhận lời cầu hôn.' if accept else 'Đã tắt nhận lời cầu hôn. Không ai gửi lời mới cho bạn được.', changed=False)


def _couple_pool(db, c: dict) -> dict:
    pa = _row(db, 'SELECT pool FROM marriage_people WHERE sid=?', (c['a'],))
    pb = _row(db, 'SELECT pool FROM marriage_people WHERE sid=?', (c['b'],))
    return _merge_pools(json.loads((pa or {}).get('pool') or '{}'), json.loads((pb or {}).get('pool') or '{}'))


def _plan(store, sid: str, display: str, d: dict) -> dict:
    plan = clean_plan(d.get('plan'))
    if 'at' in plan:   # 💍 1 hour to 14 days ahead (game/wedding_live.py)
        from . import wedding_live as wl
        wl.clean_at(plan['at'])
    mine = d.get('mine', 50)
    need(type(mine) is int and 0 <= mine <= 100, 'Tỉ lệ góp là từ 0 đến 100%.', 'bad_plan')
    announce = d.get('announce', True)
    need(type(announce) is bool, 'Lựa chọn không hợp lệ.')

    def run(db):
        c = _bond(db, sid)
        need(c and c['status'] == 'engaged', 'Chỉ cặp đã đính hôn mới lên kế hoạch cưới.', 'not_engaged', 409)
        need(not db.execute("SELECT 1 FROM weddings WHERE couple=? AND status IN ('confirmed','done')", (c['id'],)).fetchone(),
             'Kế hoạch cưới đã chốt rồi.', 'locked', 409)
        side = _side(c, sid)
        pct_a = mine if side == 'a' else 100 - mine
        q = quote(plan, _couple_pool(db, c), pct_a)
        cur = _row(db, "SELECT * FROM weddings WHERE couple=? AND status IN ('proposed','rejected') ORDER BY id DESC LIMIT 1", (c['id'],))
        ann = dict(announce_a=int(announce) if side == 'a' else (cur or {}).get('announce_a', 1),
                   announce_b=int(announce) if side == 'b' else (cur or {}).get('announce_b', 1))
        if cur:
            db.execute("UPDATE weddings SET status='proposed',version=version+1,planner=?,plan=?,quote=?,split_a=?,announce_a=?,announce_b=?,days=?,created=? WHERE id=?",
                       (sid, json.dumps(plan), json.dumps(q, ensure_ascii=False), pct_a, ann['announce_a'], ann['announce_b'], plan['days'], now(), cur['id']))
        else:
            db.execute("INSERT INTO weddings(couple,status,planner,plan,quote,split_a,announce_a,announce_b,days,created) VALUES(?,'proposed',?,?,?,?,?,?,?,?)",
                       (c['id'], sid, json.dumps(plan), json.dumps(q, ensure_ascii=False), pct_a, ann['announce_a'], ann['announce_b'], plan['days'], now()))
        partner = _other(c, sid)
        _notice(db, partner, f'📋 {display} vừa gửi kế hoạch cưới: {plan["tables"]} bàn, tổng {_xu(q["total"])} xu. Mở mục Hôn nhân để xem và xác nhận.')
        return _display(db, partner)
    name = store.transaction(run)
    return dict(message=f'Đã gửi kế hoạch cho {name}. Khi {name} xác nhận, tiền cọc mới được trừ.', changed=False)


def _withdraw(store, sid: str, display: str, d: dict) -> dict:
    def run(db):
        c = _bond(db, sid)
        need(c, 'Bạn chưa đính hôn.', 'not_engaged', 409)
        need(db.execute("UPDATE weddings SET status='withdrawn' WHERE couple=? AND planner=? AND status IN ('proposed','rejected')", (c['id'], sid)).rowcount,
             'Không có kế hoạch nào đang chờ.', 'gone', 409)
    store.transaction(run)
    return dict(message='Đã rút lại kế hoạch cưới.', changed=False)


def _reject(store, sid: str, display: str, d: dict) -> dict:
    wid = d.get('id')
    need(type(wid) is int, 'Kế hoạch không hợp lệ.')

    def run(db):
        c = _bond(db, sid)
        need(c, 'Bạn chưa đính hôn.', 'not_engaged', 409)
        w = _row(db, "SELECT * FROM weddings WHERE id=? AND couple=? AND status='proposed' AND planner<>?", (wid, c['id'], sid))
        need(w, 'Kế hoạch này không còn chờ bạn xác nhận.', 'gone', 409)
        db.execute("UPDATE weddings SET status='rejected' WHERE id=?", (wid,))
        _notice(db, w['planner'], f'{display} muốn bàn lại kế hoạch cưới. Sửa rồi gửi lại nhé.')
    store.transaction(run)
    return dict(message='Đã báo muốn bàn lại. Bạn có thể tự sửa kế hoạch rồi gửi lại.', changed=False)


def _confirm(store, sid: str, display: str, d: dict) -> dict:
    wid, version = d.get('id'), d.get('version')
    need(type(wid) is int and type(version) is int, 'Kế hoạch không hợp lệ.')
    announce = d.get('announce', True)
    need(type(announce) is bool, 'Lựa chọn không hợp lệ.')
    with store.connect() as db:
        c = _bond(db, sid)
        need(c and c['status'] == 'engaged', 'Bạn chưa đính hôn.', 'not_engaged', 409)
        w = _row(db, "SELECT * FROM weddings WHERE id=? AND couple=? AND status='proposed'", (wid, c['id']))
        need(w, 'Kế hoạch này không còn chờ xác nhận.', 'gone', 409)
        need(w['planner'] != sid, 'Người còn lại cần xác nhận kế hoạch này.', 'not_yours', 409)
        need(w['version'] == version, 'Kế hoạch vừa được sửa. Xem lại bản mới rồi xác nhận nhé.', 'plan_changed', 409)
        names = dict(a=_display(db, c['a']), b=_display(db, c['b']))
    q = json.loads(w['quote'])
    dep = dict(zip(('a', 'b'), _split(int(q['deposit']), int(w['split_a']))))
    side = _side(c, sid)
    days = int(w['days'])
    targets = {}
    at = json.loads(w['plan']).get('at')   # 💍 a real date and time: the ceremony resolves then, the live party is booked
    if at is not None:
        from . import wedding_live as wl
        need(at >= now() + wl.CONFIRM_MIN, 'Giờ cưới đã sát quá rồi. Sửa lại giờ trong kế hoạch rồi gửi nhau nhé.', 'too_late', 409)

    def pay(who):
        def fn(s):
            targets[who] = _life_day(s) + days
            if dep[who]:
                need(_can_spend(s, dep[who], d.get('pay') if who == side else None),
                     (f'Ví của bạn chưa đủ {dep[who]} xu tiền cọc.' if who == side else f'Ví của {names[who]} chưa đủ {dep[who]} xu tiền cọc. Nhờ {names[who]} rút thêm tiền về ví rồi xác nhận lại nhé.'),
                     'not_enough', 400)
            _spend(s, eff[who], d.get('pay') if who == side else None)
        return fn
    # BANK.PAY: wedding deposit, both spouses in one transaction; each side cash or their own card (_spend)
    eff = {who: _effect(f'dep:{wid}:{who}', c[who], 'wallet', -dep[who], 'Đặt cọc tiệc cưới (phần của bạn)') for who in ('a', 'b')}

    def ops(db):
        ta, tb, due = (targets['a'], targets['b'], now() + days * DAY) if at is None else (None, None, float(at))
        if db.execute("UPDATE weddings SET status='confirmed',confirmed_at=?,target_a=?,target_b=?,due_at=?,deposit_a=?,deposit_b=?,announce_"
                      + side + "=? WHERE id=? AND status='proposed' AND version=?",
                      (now(), ta, tb, due, dep['a'], dep['b'], int(announce), wid, version)).rowcount != 1:
            raise MarriageError('Kế hoạch vừa thay đổi. Xem lại rồi xác nhận nhé.', 'plan_changed', 409)
        _insert_effects(db, [eff['a'], eff['b']], 'applied')
        if at is not None:
            wl.book(db, c, wid, float(at))
            _notice(db, w['planner'], f'✅ {display} đã xác nhận kế hoạch cưới. Tiền cọc đã đặt. Hẹn cả phố lúc {wl.fmt_at(at)}! 💍')
            other = 'b' if side == 'a' else 'a'
            if announce and int(w['announce_' + other] or 0):   # both agreed to tell the phố: the date and time go out server-wide
                venue = W.VENUE_INDEX.get(json.loads(w['plan']).get('venue'), {}).get('name', 'tiệc cưới')
                _post_news(db, 'booked', f'booked:{wid}', W.NEWS_BOOKED.format(a=names['a'], b=names['b'], at=wl.fmt_at(at), venue=venue),
                           c['a'], c['b'])
        else:
            _notice(db, w['planner'], f'✅ {display} đã xác nhận kế hoạch cưới. Tiền cọc đã đặt, còn {days} ngày nữa là tới ngày vui!')
    try:
        _mutate_retry(store, {c['a']: pay('a'), c['b']: pay('b')}, ops)
    except dbm.IntegrityError:
        raise MarriageError('Kế hoạch này đã được xác nhận rồi.', 'gone', 409) from None
    mine = targets.get(side)
    when_ = f'Ngày cưới của bạn: Ngày {mine} (còn {days} ngày).' if mine else f'Còn {days} ngày nữa là tới ngày cưới!'
    if at is not None:
        when_ = f'Cưới lúc {wl.fmt_at(at)}: cả phố được mời dự 💍'
    return dict(message=f'Đã chốt kế hoạch và đặt cọc {q["deposit"]} xu (phần của bạn {dep[side]} xu). {when_}',
                changed=True)


def _divorce(store, sid: str, display: str, d: dict) -> dict:
    with store.connect() as db:
        c = _bond(db, sid)
    need(c, 'Bạn đang không có đôi.', 'not_engaged', 409)
    word = 'LY HON' if c['status'] == 'married' else 'HUY'
    need(isinstance(d.get('confirm'), str) and d['confirm'].strip().upper() == word, f'Gõ {word} để xác nhận.', 'confirm')
    other = _other(c, sid)

    def run(db):
        if db.execute("UPDATE couples SET status=?,ended=?,ended_by=? WHERE id=? AND status IN ('engaged','married')",
                      ('divorced' if c['status'] == 'married' else 'broken', now(), sid, c['id'])).rowcount != 1:
            return None
        db.execute('DELETE FROM marriage_bonds WHERE couple=?', (c['id'],))
        db.execute("UPDATE weddings SET status='cancelled' WHERE couple=? AND status IN ('proposed','rejected','confirmed')", (c['id'],))
        from . import wedding_live as wl
        wl.cancel_party(db, c['id'])   # 💍 a booked live party is off too
        until = now() + W.REMARRY_HOURS * 3600
        db.execute('UPDATE marriage_people SET remarry_after=? WHERE sid IN (?,?)', (until, sid, other))
        from . import couple as cp, family as fam  # the joint fund and child custody are settled atomically
        fam.end(db, c)
        _insert_effects(db, [_effect(f'end:{c["id"]}:a', c['a'], 'status', data=dict(set=None)),
                             _effect(f'end:{c["id"]}:b', c['b'], 'status', data=dict(set=None))] + cp.on_end(db, c, sid))
        _notice(db, other, ('💔 ' + display + (' đã ly hôn.' if c['status'] == 'married' else ' đã hủy hôn ước.')
                            + f' Cả hai cần {W.REMARRY_HOURS} tiếng trước khi tính chuyện mới.'))
        return True
    if not store.transaction(run):
        raise MarriageError('Chuyện này đã khép lại rồi.', 'gone', 409)
    for who in (sid, other):
        try:
            settle(store, who)
        except Exception:  # noqa: BLE001
            pass
    return dict(message=('Đã ly hôn.' if c['status'] == 'married' else 'Đã hủy hôn ước.') + f' Cả hai cần {W.REMARRY_HOURS} tiếng trước khi tính chuyện mới.',
                changed=True)


def _seen(store, sid: str, display: str, d: dict) -> dict:
    def run(db):
        db.execute('UPDATE marriage_people SET notice=NULL,notice_at=NULL WHERE sid=?', (sid,))
        if type(d.get('wedding')) is int:
            w = _row(db, "SELECT w.id,c.a FROM weddings w JOIN couples c ON c.id=w.couple WHERE w.id=? AND (c.a=? OR c.b=?)", (d['wedding'], sid, sid))
            if w:
                db.execute(f"UPDATE weddings SET seen_{'a' if w['a'] == sid else 'b'}=1 WHERE id=?", (w['id'],))
    store.transaction(run)
    return dict(message='', changed=False)


def _party(store, sid: str, display: str, d: dict) -> dict:
    """🎉 "Tổ chức tiệc cưới" (game/wedding_live.py book_party): pick or move the live party's date and time, free."""
    from . import wedding_live as wl

    def run(db):
        c = _bond(db, sid)
        need(c, 'Bạn đang không có đôi.', 'not_engaged', 409)
        got = wl.book_party(db, c, sid, d.get('at'))
        _notice(db, _other(c, sid), f'🎉 {display} đã hẹn tiệc cưới của hai bạn lúc {wl.fmt_at(got["at"])}. Mời bạn bè tới chung vui nhé!')
        return got
    got = store.transaction(run)
    return dict(message=f'Đã hẹn tiệc cưới lúc {wl.fmt_at(got["at"])}. Bấm “Mời khách” để báo bạn bè và cả phố nhé 💌', changed=False)


def _party_invite(store, sid: str, display: str, d: dict) -> dict:
    """💌 "Mời khách" (free, once per party): friends of both get an inbox line and a push, the phố a news line."""
    from . import wedding_live as wl

    def run(db):
        c = _bond(db, sid)
        need(c, 'Bạn đang không có đôi.', 'not_engaged', 409)
        return wl.invite(db, c, dict(a=_display(db, c['a']), b=_display(db, c['b'])))
    n = store.transaction(run)
    if not n:
        return dict(message='Đã gửi lời mời cả phố. Bạn bè sẽ được nhắc lại trước giờ tiệc 30 phút 💌', changed=False)
    return dict(message=f'Đã mời {n} người bạn và cả phố. Miễn phí, không mất xu nào 💌', changed=False)


def _envelope(store, sid: str, display: str, d: dict) -> dict:
    """🧧 A guest's red envelope for the couple at a live party (game/wedding_live.py envelope)."""
    from . import wedding_live as wl
    return wl.envelope(store, sid, display, d)


def _wed_gift(store, sid: str, display: str, d: dict) -> dict:
    """🎁 The admin's 500 xu for the weddings, once per save (game/wedding_live.py wed_gift)."""
    from . import wedding_live as wl
    return wl.wed_gift(store, sid, display, d)


ACTIONS = dict(ring_buy=_ring_buy, ring_sell=_ring_sell, ring_recolor=_ring_recolor, lookup=_lookup, propose=_propose, respond=_respond, cancel=_cancel, block=_block, unblock=_unblock,
               settings=_settings, plan=_plan, withdraw=_withdraw, reject=_reject, confirm=_confirm, divorce=_divorce, seen=_seen,
               party=_party, party_invite=_party_invite, envelope=_envelope, wed_gift=_wed_gift)


# ---------------------------------------------------------------- privacy
def forget(store, token: str) -> None:
    """Account deletion ("Xóa dữ liệu"): end any engagement/marriage, drop proposals, rings,
    blocks, the code and the news lines that named this player."""
    sid = store.key(token)

    def run(db):
        c = _bond(db, sid)
        if c:
            other = _other(c, sid)
            db.execute("UPDATE couples SET status='ended',ended=?,ended_by=? WHERE id=?", (now(), 'deleted', c['id']))
            db.execute('DELETE FROM marriage_bonds WHERE couple=?', (c['id'],))
            db.execute("UPDATE weddings SET status='cancelled' WHERE couple=? AND status IN ('proposed','rejected','confirmed')", (c['id'],))
            from . import couple as cp, family as fam  # the one who stays keeps the joint fund and child
            fam.end(db, c, deleted=sid)
            _insert_effects(db, [_effect(f'end:{c["id"]}:{_side(c, other)}', other, 'status', data=dict(set=None))] + cp.on_end(db, c, None, deleted=sid))
            _notice(db, other, 'Người ấy đã xóa tài khoản. Chuyện hai bạn khép lại ở đây.')
        for q in _rows(db, "SELECT id,ring,from_sid FROM proposals WHERE status='pending' AND to_sid=?", (sid,)):
            db.execute("UPDATE marriage_rings SET status='owned' WHERE id=? AND status='proposed'", (q['ring'],))
        db.execute('DELETE FROM proposals WHERE from_sid=? OR to_sid=?', (sid, sid))
        db.execute('DELETE FROM marriage_rings WHERE sid=?', (sid,))
        db.execute('DELETE FROM marriage_blocks WHERE sid=? OR target=?', (sid, sid))
        from . import friends as fr, couple as cp
        fr.forget(db, sid)
        cp.forget(db, sid)
        from . import family as fam
        fam.forget(db, sid)
        db.execute('DELETE FROM marriage_effects WHERE sid=?', (sid,))
        db.execute('DELETE FROM marriage_people WHERE sid=?', (sid,))
        if db.execute('DELETE FROM news WHERE a=? OR b=?', (sid, sid)).rowcount:
            _news_stale()
    store.transaction(run)
