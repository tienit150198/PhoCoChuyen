"""🎃 Lễ hội Ma Phố: the Halloween season of 2026 (owner 20/10: "tính toán luôn cả halloween nhé, coi có gì triển khai được
dịp halloween thì lên plan chạy luôn, chạy trước 5 ngày của halloween nhé, event gì đó đặc biệt"). The plan for the owner:
docs/HALLOWEEN_2026.md. The words and the shop: game/halloween_content.py.

When (server time, Vietnam days)
* START (Mon 26/10 00:00) → END (Sun 01/11 00:00): candy (🍬 kẹo) is earned. NIGHT (Sat 31/10 19:00) → END: 🎭 Đêm hội hóa
  trang, every candy earned ×NIGHT_MULT and the giant pumpkin. Until SHOP_UNTIL (Mon 02/11 00:00): the candy shop and the
  board stay open (grace). Nothing shows before START or after SHOP_UNTIL. MNL_HALLOWEEN_OFF=1: nothing shows, nothing is
  earned or exchanged, the season's close waits (candy already earned and rewards already granted stay).

Candy (a registered account; the table hw_players, never the save)
* ✅ Điểm danh: CHECKIN a Vietnam day (+ the day's bonus), from the start card or the sheet.
* 🎃 Săn bí ngô: PUMPKINS places of the town hide a pumpkin each day (a hash of the day). The sheet gives a riddle per
  pumpkin and CHOICES places: one try each (right: PUMP candy, wrong: it rolls away for the day). In the 2.5D town, tapping a
  place that hides one finds it without the riddle (POST walk {place}).
* 🍬 Cho kẹo hay bị ghẹo: knock on another player's door (a participant, a friend, a username or a player code), once a
  host a day, KNOCKS_DAY a day; TRICK_PCT % of knocks are a trick (TRICK candy) else a treat (TREAT); the host gets HOST
  for each of their first HOSTED_DAY knocks a day. Anti-clone: the visitor's account is KNOCK_AGE_DAYS old, KNOCK_IPS
  visitor accounts a network a day, blocked players never meet.
* 🎭 Bí ngô khổng lồ: GIANT once, on the night.
🎁 Đổi kẹo: 🎨 Phong cách cosmetics, a pet piece and three bags of xu (100k, 200k, 500k), each once an account; a bag
needs an account SWAP_AGE_DAYS old and a character of life day SWAP_LIFE_DAY (no network cap: owner 21/10). The candy leaves hw_players and a
live_effects row of kind FX is written in the same transaction; game/live_effects.py pays it into the save at once (an
older build leaves it pending). 🏆 Bảng kẹo: candy earned (never spent); at END the housekeeping grants the top TOP once.

Tables (game/pg_schema.py SCHEMA_VERSION 80; 76–79 belong to other branches): hw_players, hw_log. No save key.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import secrets
import threading
import time

from . import halloween_content as C
from . import marriage as mr

VN = datetime.timezone(datetime.timedelta(hours=7))
START = 1792947600        # 26/10/2026 00:00 (VN)
END = 1793466000          # 01/11/2026 00:00 (VN): earning closes (31/10 23:59:59 is the last second)
SHOP_UNTIL = 1793552400   # 02/11/2026 00:00 (VN): the shop and the board stay open one more day
NIGHT = 1793448000        # 31/10/2026 19:00 (VN): 🎭 Đêm hội hóa trang
FX = 'hween'              # live_effects kind (game/live_effects.py)
CHECKIN = 10
PUMP = 5
TREAT, TRICK, HOST = 4, 1, 2
KNOCKS_DAY = 10
HOSTED_DAY = 15
KNOCK_AGE_DAYS = 1
KNOCK_IPS = 3
GIANT = 30
NIGHT_MULT = 2
SWAP_AGE_DAYS = 3
SWAP_LIFE_DAY = 3
TOP = 10
DOORS = 12
LIST_MAX = 20
BOARD_TTL = 20.0
USER_RX = re.compile(r'@?([a-z0-9_.]{3,24})')


class HalloweenError(mr.MarriageError):
    """A refusal shown as is (the server answers a MarriageError with its status and code)."""


def need(cond, message: str, code: str = 'hween_error', status: int = 400):
    if not cond:
        raise HalloweenError(message, code, status)


def now() -> float:
    return time.time()


def off() -> bool:
    return os.environ.get('MNL_HALLOWEEN_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def phase(t: float | None = None) -> str:
    """'off' | 'before' | 'open' (candy earned) | 'grace' (the shop and the board only) | 'over'."""
    t = now() if t is None else t
    if off():
        return 'off'
    return 'before' if t < START else 'open' if t < END else 'grace' if t < SHOP_UNTIL else 'over'


def vn_day(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%Y-%m-%d')


def day_of(t: float) -> dict | None:
    """The season's day at t: {date, n (1…6), icon, title, line, bonus}, None outside the six days."""
    d = vn_day(t)
    x = C.DAYS.get(d)
    return dict(x, date=d, n=sorted(C.DAYS).index(d) + 1) if x else None


def night(t: float) -> bool:
    return NIGHT <= t < END


def mult(t: float) -> int:
    return NIGHT_MULT if night(t) else 1


def bonus(kind: str, t: float) -> int:
    d = C.DAYS.get(vn_day(t))
    b = d and d.get('bonus')
    return int(b[1]) if b and b[0] == kind else 0


def _h(*parts) -> int:
    return int(hashlib.sha256('\x1f'.join(str(p) for p in parts).encode()).hexdigest()[:12], 16)


def _hs(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _salt() -> str:
    return (os.environ.get('MNL_HALLOWEEN_SALT') or 'mnl-hween-2026').strip()


def ip_tag(ip: str) -> str:
    """A network as the log keeps it: grouped, never stored."""
    return hashlib.sha256(('hween:' + str(ip or '')).encode()).hexdigest()[:16]


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


# ---------------------------------------------------------------- the bootstrap hint and the ticker
def hint(t: float | None = None) -> dict | None:
    """/api/bootstrap `ui.hween` and /api/news `hween`: the season's status while it shows (open or grace), else None."""
    t = now() if t is None else t
    p = phase(t)
    if p not in ('open', 'grace'):
        return None
    d = day_of(t) if p == 'open' else None
    return dict(state=p, starts=START, ends=END, until=SHOP_UNTIL, night=NIGHT, now=int(t),
                day=d['n'] if d else 0, title=d['title'] if d else '', icon=d['icon'] if d else '🎃')


def news_line(t: float | None = None) -> dict | None:
    """The ticker's line while candy is earned (public/js/v4/ticker.js plays an `event` once per key on a device): one a
    day, one more when the night begins."""
    t = now() if t is None else t
    if phase(t) != 'open':
        return None
    d = day_of(t)
    if not d:
        return None
    if night(t):
        return dict(text='🎭 Đêm hội hóa trang bắt đầu! Từ giờ tới nửa đêm mọi viên kẹo nhân đôi, bí ngô khổng lồ đang chờ ở '
                         'công viên. Khu phố → 🎃 Lễ hội Ma Phố.', key=f'hween:{d["date"]}:night')
    return dict(text=f'{d["icon"]} Lễ hội Ma Phố · {d["title"]}: {d["line"]} Khu phố → 🎃 Lễ hội Ma Phố.', key=f'hween:{d["date"]}')


# ---------------------------------------------------------------- 🎃 pumpkins
def spots(day: str) -> list:
    """The day's hidden pumpkins: [{i, key, riddle, choices}] (the same for everyone; `key` never leaves the server)."""
    keys = [p[0] for p in C.PLACES]
    picks = sorted(keys, key=lambda k: _h(_salt(), day, k))[:C.PUMPKINS]
    out = []
    for i, k in enumerate(picks):
        riddle = C.PLACE[k][2][_h(_salt(), day, k, 'r') % len(C.PLACE[k][2])]
        decoys = sorted((x for x in keys if x != k), key=lambda x: _h(_salt(), day, k, x))[:C.CHOICES - 1]
        choices = sorted([k] + decoys, key=lambda x: _h(_salt(), day, i, x, 'c'))
        out.append(dict(i=i, key=k, riddle=riddle, choices=choices))
    return out


# ---------------------------------------------------------------- the ledger
def _lock(db, *names: str) -> None:
    for n in sorted(set(names)):
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('hween:' + n,))


def _earn(db, sid: str, key: str, kind: str, n: int, day: str, t: float, other: str = '', ip: str = '') -> bool:
    """One candy move, once per key: the log row, then the player's candy and earned. False: the key was used already."""
    from . import social
    if not db.execute('INSERT INTO hw_log(id, sid, kind, n, day, other, ip, at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                      (key, sid, kind, n, day, other, ip, t)).rowcount:
        return False
    if n > 0:
        db.execute('INSERT INTO hw_players(sid, pid, candy, earned, last_at, created) VALUES(?,?,?,?,?,?) ON CONFLICT(sid) DO UPDATE '
                   'SET candy=hw_players.candy+EXCLUDED.candy, earned=hw_players.earned+EXCLUDED.earned, last_at=EXCLUDED.last_at',
                   (sid, social.pid_of(sid), n, n, t, t))
    else:
        _join(db, sid, t)
    return True


def _join(db, sid: str, t: float) -> None:
    from . import social
    db.execute('INSERT INTO hw_players(sid, pid, candy, earned, last_at, created) VALUES(?,?,0,0,0,?) ON CONFLICT DO NOTHING',
               (sid, social.pid_of(sid), t))


def _me(db, sid: str) -> dict:
    r = db.execute('SELECT candy, earned, last_at FROM hw_players WHERE sid=?', (sid,)).fetchone()
    return dict(candy=int(r['candy']), earned=int(r['earned']), last_at=float(r['last_at'])) if r else dict(candy=0, earned=0, last_at=0.0)


def _account(db, sid: str):
    return db.execute('SELECT uid, username, display, created_at FROM accounts WHERE sid=?', (sid,)).fetchone()


def _old_enough(created_at, days: int, t: float) -> bool:
    """accounts.created_at is UTC text 'YYYY-MM-DD HH:MM:SS' (pg_schema.NOW_TEXT)."""
    cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - days * 86400))
    return bool(created_at) and str(created_at) <= cut


def _people(db, sids) -> dict:
    from . import service_market as sm
    return sm._people(db, [s for s in sids if s])


def _blocks(db, sid: str) -> tuple:
    from . import town_fair
    return town_fair._blocks(db, sid)


def _blocked(blocks: tuple, other: str) -> bool:
    from . import social
    return other in blocks[0] or social.pid_of(other) in blocks[1]


# ---------------------------------------------------------------- the board
_board_cache: dict = {}
_board_lock = threading.Lock()


def clear_cache() -> None:
    with _board_lock:
        _board_cache.clear()


def _top(db, n: int) -> list:
    return [dict(r) for r in db.execute('SELECT h.sid, h.earned, h.last_at FROM hw_players h JOIN accounts a ON a.sid=h.sid '
                                        'WHERE h.earned>0 ORDER BY h.earned DESC, h.last_at, h.sid LIMIT ?', (n,)).fetchall()]


def board(store, t: float | None = None) -> list:
    """🏆 The top LIST_MAX by candy earned (ties: who got there first), cached BOARD_TTL seconds."""
    t = now() if t is None else t
    key = str(getattr(store, 'path', id(store)))
    with _board_lock:
        hit = _board_cache.get(key)
        if hit and 0 <= t - hit[0] < BOARD_TTL:
            return hit[1]
    with store.connect() as db:
        rows = _top(db, LIST_MAX)
        who = _people(db, [r['sid'] for r in rows])
    out = [dict(rank=i, earned=int(r['earned']), who=who.get(r['sid']), sid=r['sid']) for i, r in enumerate(rows, 1)]
    with _board_lock:
        _board_cache[key] = (t, out)
        while len(_board_cache) > 8:
            _board_cache.pop(next(iter(_board_cache)))
    return out


def _rank(db, me: dict) -> int:
    if me['earned'] <= 0:
        return 0
    r = db.execute('SELECT COUNT(*) AS n FROM hw_players WHERE earned>? OR (earned=? AND last_at<?)',
                   (me['earned'], me['earned'], me['last_at'])).fetchone()
    return int(r['n']) + 1


def top_items(rank: int) -> tuple:
    for lo, hi, items in C.TOP_ITEMS:
        if lo <= rank <= hi:
            return items
    return ()


# ---------------------------------------------------------------- the sheet
def _style_name(item_id: str) -> str:
    from . import spend_content as SC
    it = SC.STYLE_ITEMS.get(item_id)
    return f'{it["emoji"]} {it["name"]}' if it else item_id


def _key(sid: str, it: dict) -> str:
    """The hw_log id of an exchange, once an account and item ('swap:' a xu bag, 'buy:' the rest)."""
    return f'{"swap" if it["kind"] == "xu" else "buy"}:{sid}:{it["id"]}'


def _bag_coins(log_id: str) -> int:
    it = C.SHOP_ITEM.get(log_id.rsplit(':', 1)[-1])
    return it['coins'] if it and it['kind'] == 'xu' else 0


def view(store, token: str, t: float | None = None) -> dict:
    """GET /api/halloween: everything the sheet shows for this player (a guest gets the season and a sign-in prompt)."""
    t = now() if t is None else t
    p = phase(t)
    base = dict(state=p, now=int(t), starts=START, ends=END, until=SHOP_UNTIL, night=NIGHT, night_on=night(t),
                day=day_of(t) if p == 'open' else None, grace_line=C.GRACE_LINE,
                rules=dict(checkin=CHECKIN, pump=PUMP, treat=TREAT, trick=TRICK, host=HOST, knocks=KNOCKS_DAY, hosted=HOSTED_DAY,
                           giant=GIANT, mult=NIGHT_MULT, swap_bags=list(C.XU_BAGS), swap_age=SWAP_AGE_DAYS,
                           swap_life=SWAP_LIFE_DAY, knock_age=KNOCK_AGE_DAYS, trick_pct=C.TRICK_PCT, top=TOP, pumpkins=C.PUMPKINS))
    if p not in ('open', 'grace'):
        return base
    sid = store.key(token)
    top = board(store, t)
    base['board'] = [dict(rank=r['rank'], earned=r['earned'], who=r['who'], me=r['sid'] == sid) for r in top[:TOP]]
    with store.connect() as db:
        acct = _account(db, sid)
        if not acct:
            return dict(base, account=False)
        me = _me(db, sid)
        day = vn_day(t)
        rows = [dict(r) for r in db.execute('SELECT id, kind, n, other, at FROM hw_log WHERE sid=? AND day=?', (sid, day)).fetchall()]
        visitors = [dict(r) for r in db.execute("SELECT sid, n, at FROM hw_log WHERE other=? AND day=? AND kind='knock' ORDER BY at DESC LIMIT ?",
                                                (sid, day, LIST_MAX)).fetchall()]
        bought = {r['id'] for r in db.execute("SELECT id FROM hw_log WHERE sid=? AND kind IN ('buy','swap')", (sid,)).fetchall()}
        giant = bool(db.execute('SELECT 1 FROM hw_log WHERE id=?', (f'giant:{sid}',)).fetchone())
        doors = _doors(db, sid, {r['other'] for r in rows if r['kind'] == 'knock'}, t) if p == 'open' else []
        rank = _rank(db, me)
        people = _people(db, [r['other'] for r in rows if r['kind'] == 'knock'] + [v['sid'] for v in visitors])
        old = _old_enough(acct['created_at'], KNOCK_AGE_DAYS, t)
    tried = {int(r['id'].rsplit(':', 1)[1]): r for r in rows if r['kind'] in ('pump', 'miss')}
    pumpkins = []
    if p == 'open':
        for sp in spots(day):
            r = tried.get(sp['i'])
            x = dict(i=sp['i'], riddle=sp['riddle'], choices=[dict(id=k, name=C.PLACE[k][1]) for k in sp['choices']],
                     status='open' if not r else 'found' if r['kind'] == 'pump' else 'missed')
            if r:
                x.update(place=C.PLACE[sp['key']][1], n=int(r['n']))
            pumpkins.append(x)
    mine = [dict(who=people.get(r['other']), n=int(r['n']), trick=r['n'] < TREAT, at=int(r['at']))
            for r in sorted((r for r in rows if r['kind'] == 'knock'), key=lambda r: -r['at'])]
    knocked = {r['other'] for r in rows if r['kind'] == 'knock'}
    hosted = [r for r in rows if r['kind'] == 'host']
    shop = []
    for it in C.SHOP:
        owned = _key(sid, it) in bought
        left = 1 - int(owned)
        shop.append(dict({k: v for k, v in it.items() if k in ('id', 'cost', 'kind', 'emoji', 'name', 'line', 'coins')}, owned=owned, left=left,
                         short=max(0, it['cost'] - me['candy'])))
    checkin = next((r for r in rows if r['kind'] == 'checkin'), None)
    return dict(base, account=True, me=dict(candy=me['candy'], earned=me['earned'], rank=rank),
                checkin=dict(done=bool(checkin), n=int(checkin['n']) if checkin else (CHECKIN + bonus('checkin', t)) * mult(t)),
                pumpkins=pumpkins, giant=dict(on=night(t), done=giant, n=GIANT),
                knock=dict(left=max(0, KNOCKS_DAY - len(mine)), max=KNOCKS_DAY, old=old, doors=doors, mine=mine[:LIST_MAX],
                           hosted=sum(1 for r in hosted if r['n'] > 0), host_max=HOSTED_DAY,
                           visitors=[dict(who=people.get(v['sid']), back=v['sid'] in knocked, at=int(v['at'])) for v in visitors]),
                shop=shop)


def _doors(db, sid: str, knocked: set, t: float) -> list:
    """Doors to knock on: friends first, then players of the season seen most recently; never mine, never one knocked today,
    never someone blocked either way; accounts only."""
    from . import social
    friends = [r['friend'] for r in db.execute('SELECT friend FROM friends WHERE sid=? LIMIT 40', (sid,)).fetchall()]
    recent = [r['sid'] for r in db.execute('SELECT sid FROM hw_players WHERE sid<>? ORDER BY last_at DESC LIMIT 60', (sid,)).fetchall()]
    blocks = _blocks(db, sid)
    pool, seen = [], set()
    for s in friends + recent:
        if s in seen or s == sid or s in knocked or _blocked(blocks, s):
            continue
        seen.add(s)
        pool.append(s)
    if pool:
        marks = ','.join('?' * len(pool))
        have = {r['sid'] for r in db.execute(f'SELECT sid FROM accounts WHERE sid IN ({marks})', tuple(pool)).fetchall()}
        pool = [s for s in pool if s in have][:DOORS]
    who = _people(db, pool)
    fr = set(friends)
    return [dict(who.get(s) or {}, pid=social.pid_of(s), friend=s in fr) for s in pool]


# ---------------------------------------------------------------- actions
def _actor(db, store, token: str) -> tuple:
    sid = store.key(token)
    acct = _account(db, sid)
    need(acct, 'Đăng nhập tài khoản để chơi Lễ hội Ma Phố nhé.', 'login_required', 401)
    return sid, dict(acct)


def _open(t: float) -> None:
    p = phase(t)
    need(p != 'off', 'Lễ hội Ma Phố đang tạm nghỉ.', 'hween_off', 503)
    need(p != 'before', 'Lễ hội Ma Phố mở từ 0 giờ ngày 26/10 nhé 🎃', 'hween_soon', 409)
    need(p == 'open', 'Lễ hội Ma Phố đã khép lại. Kẹo còn trong túi đổi quà đến hết 01/11 nhé.', 'hween_over', 409)


def _checkin(store, token, data, ip, t):
    need(not data, 'Thông tin không hợp lệ.')
    _open(t)

    def run(db):
        sid, _ = _actor(db, store, token)
        _lock(db, sid)
        day = vn_day(t)
        n = (CHECKIN + bonus('checkin', t)) * mult(t)
        need(_earn(db, sid, f'checkin:{day}:{sid}', 'checkin', n, day, t), 'Hôm nay bạn đã nhận kẹo điểm danh rồi. Mai ghé tiếp nhé 🎃', 'done', 409)
        return dict(message=f'🍬 +{n} kẹo điểm danh! Đi săn bí ngô và gõ cửa xin kẹo thôi.', n=n)
    return store.transaction(run)


def _pumpkin(db, sid: str, i: int, place: str, day: str, t: float, walked: bool) -> dict:
    sp = spots(day)[i]
    right = place == sp['key']
    n = (PUMP + bonus('pump', t)) * mult(t) if right else 0
    if not _earn(db, sid, f'pump:{day}:{sid}:{i}', 'pump' if right else 'miss', n, day, t):
        return dict(found=False, already=True, message='Quả bí ngô này bạn đã tìm rồi.')
    name = C.PLACE[sp['key']][1]
    if right:
        how = 'Bạn đi ngang' if walked else 'Đúng rồi!'
        return dict(found=True, n=n, message=f'🎃 {how} Bí ngô nấp ở {name}. +{n} kẹo.')
    return dict(found=False, n=0, message=f'💨 Bí ngô không ở {C.PLACE[place][1]}… nó lăn mất rồi (nó nấp ở {name}). Quả khác vẫn còn nhé!')


def _guess(store, token, data, ip, t):
    need(set(data) == {'spot', 'place'}, 'Thông tin không hợp lệ.')
    _open(t)
    i, place = data.get('spot'), data.get('place')
    need(type(i) is int and 0 <= i < C.PUMPKINS, 'Không có quả bí ngô này.')
    day = vn_day(t)
    need(isinstance(place, str) and place in spots(day)[i]['choices'], 'Chọn một nơi trong danh sách nhé.')

    def run(db):
        sid, _ = _actor(db, store, token)
        _lock(db, sid)
        out = _pumpkin(db, sid, i, place, day, t, False)
        need(not out.get('already'), out['message'], 'done', 409)
        return out
    return store.transaction(run)


def _walk(store, token, data, ip, t):
    """The 2.5D town: the player reached a place (its signpost 'place:<id>'). Finds that place's pumpkin when it hides one
    today and it was not tried yet; anything else answers found: false (nothing written)."""
    need(set(data) == {'place'} and isinstance(data.get('place'), str) and len(data['place']) <= 40, 'Thông tin không hợp lệ.')
    if phase(t) != 'open':
        return dict(found=False)
    day = vn_day(t)
    hit = next((sp for sp in spots(day) if sp['key'] == data['place']), None)
    if not hit:
        return dict(found=False)

    def run(db):
        sid, _ = _actor(db, store, token)
        _lock(db, sid)
        out = _pumpkin(db, sid, hit['i'], hit['key'], day, t, True)
        return dict(found=False) if out.get('already') else out
    return store.transaction(run)


def _giant(store, token, data, ip, t):
    need(not data, 'Thông tin không hợp lệ.')
    _open(t)
    need(night(t), 'Bí ngô khổng lồ chỉ hiện ra trong Đêm hội hóa trang (31/10 từ 19:00).', 'not_night', 409)

    def run(db):
        sid, _ = _actor(db, store, token)
        _lock(db, sid)
        need(_earn(db, sid, f'giant:{sid}', 'giant', GIANT, vn_day(t), t), 'Bạn đã gõ bí ngô khổng lồ rồi 🎃', 'done', 409)
        return dict(message=f'🎃 Bí ngô khổng lồ nứt ra, kẹo tuôn như suối! +{GIANT} kẹo.', n=GIANT)
    return store.transaction(run)


def _target(db, to: str, me: str) -> str | None:
    """A host by pid (a door of the list, a visitor to knock back), username or player code."""
    from . import social
    from . import work_visits
    if re.fullmatch(r'[0-9a-f]{16}', to):
        r = db.execute('SELECT sid FROM hw_players WHERE pid=? LIMIT 1', (to,)).fetchone()
        if r:
            return r['sid']
        for f in db.execute('SELECT friend FROM friends WHERE sid=? LIMIT 200', (me,)).fetchall():
            if social.pid_of(f['friend']) == to:
                return f['friend']
        return work_visits._resolve(db, to)
    m = USER_RX.fullmatch(to.strip().lower())
    if m:
        r = db.execute('SELECT sid FROM accounts WHERE username=?', (m.group(1),)).fetchone()
        if r:
            return r['sid']
    return work_visits._resolve(db, to.strip())


def _knock(store, token, data, ip, t):
    need(set(data) == {'to'} and isinstance(data.get('to'), str) and 0 < len(data['to'].strip()) <= 40, 'Gõ cửa nhà ai nè?')
    _open(t)
    day, tag = vn_day(t), ip_tag(ip)

    def run(db):
        sid, acct = _actor(db, store, token)
        need(_old_enough(acct['created_at'], KNOCK_AGE_DAYS, t), 'Tài khoản cần đủ 1 ngày tuổi mới đi xin kẹo được. Mai quay lại nhé!',
             'too_new', 403)
        host = _target(db, data['to'], sid)
        need(host and _account(db, host), 'Không tìm thấy nhà này. Kiểm tra lại tên đăng nhập nhé.', 'not_found', 404)
        need(host != sid, 'Đây là nhà bạn mà 😄 Đi gõ cửa hàng xóm nhé!', 'own_door')
        need(not _blocked(_blocks(db, sid), host), 'Không tìm thấy nhà này.', 'not_found', 404)
        _lock(db, sid, host, 'ip:' + tag)
        used = int(db.execute("SELECT COUNT(*) AS n FROM hw_log WHERE sid=? AND day=? AND kind='knock'", (sid, day)).fetchone()['n'])
        need(used < KNOCKS_DAY, f'Hôm nay bạn đã gõ đủ {KNOCKS_DAY} nhà rồi. Mai đi tiếp nhé 🌙', 'knock_limit', 429)
        if not used:
            others = int(db.execute("SELECT COUNT(DISTINCT sid) AS n FROM hw_log WHERE ip=? AND day=? AND kind='knock' AND sid<>?",
                                    (tag, day, sid)).fetchone()['n'])
            need(others < KNOCK_IPS, 'Mạng này đã có nhiều tài khoản đi xin kẹo hôm nay rồi.', 'knock_ip', 429)
        m = mult(t)
        trick = secrets.randbelow(100) < C.TRICK_PCT
        n = (TRICK if trick else TREAT + bonus('treat', t)) * m
        need(_earn(db, sid, f'knock:{day}:{sid}:{host}', 'knock', n, day, t, other=host, ip=tag),
             'Hôm nay bạn đã gõ cửa nhà này rồi. Mai quay lại nhé!', 'done', 409)
        hosted = int(db.execute("SELECT COUNT(*) AS n FROM hw_log WHERE sid=? AND day=? AND kind='host' AND n>0", (host, day)).fetchone()['n'])
        tip = (HOST + bonus('host', t)) * m if hosted < HOSTED_DAY else 0
        _earn(db, host, f'host:{day}:{sid}:{host}', 'host', tip, day, t, other=sid)
        name = (_people(db, [host]).get(host) or {}).get('name') or 'Hàng xóm'
        lines = C.TRICKS if trick else C.TREATS
        line = lines[secrets.randbelow(len(lines))].format(host=name)
        return dict(message=f'{line}. +{n} kẹo.', n=n, trick=trick, host=name, tip=tip)
    return store.transaction(run)


def _buy(store, token, data, ip, t):
    need(set(data) == {'item'} and isinstance(data.get('item'), str), 'Thông tin không hợp lệ.')
    p = phase(t)
    need(p != 'off', 'Lễ hội Ma Phố đang tạm nghỉ.', 'hween_off', 503)
    need(p in ('open', 'grace'), 'Quầy đổi kẹo chưa mở hoặc đã đóng.', 'hween_over', 409)
    it = C.SHOP_ITEM.get(data['item'])
    need(it, 'Không có món này.', 'not_found', 404)
    tag = ip_tag(ip)
    life = None
    if it['kind'] == 'xu':
        loaded = mr._read_state(store, store.key(token))
        j = (loaded[0].get('journey') or {}) if loaded else {}
        life = int(j.get('life_day') or 0) if j.get('story') else 0

    def run(db):
        sid, acct = _actor(db, store, token)
        _lock(db, sid)
        me = _me(db, sid)
        payload = dict(why='buy', item=it['id'])
        key = _key(sid, it)
        need(not db.execute('SELECT 1 FROM hw_log WHERE id=?', (key,)).fetchone(), 'Bạn đã đổi món này rồi.', 'owned', 409)
        if it['kind'] == 'xu':
            need(_old_enough(acct['created_at'], SWAP_AGE_DAYS, t), f'Đổi xu cần tài khoản từ {SWAP_AGE_DAYS} ngày tuổi. Đổi quà khác trước nhé!',
                 'too_new', 403)
            need((life or 0) >= SWAP_LIFE_DAY, f'Đổi xu cần nhân vật từ ngày sống thứ {SWAP_LIFE_DAY}.', 'too_new', 403)
            kind = 'swap'
            payload['coins'] = it['coins']
            amount = it['coins']
        else:
            kind = 'buy'
            if it['kind'] == 'style':
                payload['items'] = [it['id']]
            else:
                payload['pet'] = it['piece']
            amount = 1
        need(me['candy'] >= it['cost'], f'Bạn có {me["candy"]} kẹo, món này cần {it["cost"]} kẹo.', 'not_enough', 409)
        need(db.execute('UPDATE hw_players SET candy=candy-? WHERE sid=? AND candy>=?', (it['cost'], sid, it['cost'])).rowcount == 1,
             'Chưa đủ kẹo.', 'not_enough', 409)
        db.execute('INSERT INTO hw_log(id, sid, kind, n, day, other, ip, at) VALUES(?,?,?,?,?,?,?,?)',
                   (key, sid, kind, -it['cost'], vn_day(t), '', tag if kind == 'swap' else '', t))
        db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?)",
                   (f'{FX}:{key.split(":")[0]}:{_hs(key)}', sid, FX, amount, json.dumps(payload, ensure_ascii=False), t))
        what = f'{fmt(it["coins"])} xu vào ví' if it['kind'] == 'xu' else it['name']
        return dict(message=f'{it["emoji"]} Đổi {it["cost"]} kẹo: {what}!', item=it['id'], candy=me['candy'] - it['cost'])
    return store.transaction(run)   # server.py pays the row at once (live_effects.on_load), else the next load does


ACTIONS = dict(checkin=_checkin, guess=_guess, walk=_walk, giant=_giant, knock=_knock, buy=_buy)


def post(store, token: str, op: str, data, ip: str = '') -> dict:
    """POST /api/halloween/<op>: the action's answer and the sheet again (walk: only the answer)."""
    need(isinstance(data, dict), 'Thông tin không hợp lệ.')
    fn = ACTIONS.get(op)
    need(fn, 'Không có thao tác này.', 'not_found', 404)
    t = now()
    out = fn(store, token, data, ip, t)
    if op in ('knock', 'buy', 'giant', 'checkin'):
        clear_cache()
    if op == 'walk':
        return out
    return dict(out, view=view(store, token, t))


# ---------------------------------------------------------------- the reward into the save (game/live_effects.py apply)
def apply_fx(s: dict, p: dict, amount: int) -> str:
    """A 'hween' live_effects row: 🎨 Phong cách items kept for good, a pet wardrobe piece (rank D), or a bag of xu."""
    from . import engine as e
    from . import journey as jr
    from . import spend as sp
    from . import spend_content as SC
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    items, pet, coins = data.get('items') or [], data.get('pet'), data.get('coins') or 0
    e.need(isinstance(items, list) and len(items) <= 4 and all(isinstance(x, str) and x in C.STYLE_IDS and x in SC.STYLE_ITEMS for x in items)
           and (pet is None or pet in C.PET_PIECES) and type(coins) is int and 0 <= coins <= max(C.XU_BAGS) and (not coins or coins == amount)
           and (items or pet or coins), 'Dữ liệu lễ hội không hợp lệ.')
    new = []
    for item in items:
        b = sp.get(s)
        if b and b['own'].get(item, 0) >= SC.PERMANENT:
            continue
        b = sp._ensure(s)
        if len(b['own']) >= sp.OWN_MAX and item not in b['own']:
            continue
        b['own'][item] = SC.PERMANENT
        new.append(_style_name(item))
    if pet:
        from . import pet_wardrobe as pw
        from . import pet_wardrobe_content as W
        x = pw._ensure(s)
        e.need(len(x['it']) < pw.ITEM_MAX, f'Tủ đồ thú cưng đã đủ {pw.ITEM_MAX} món: ghép bớt rồi quà Halloween sẽ vào.', 'limit')
        pw._new(x, pet, 0)
        new.append(f'{W.ITEM[pet]["emoji"]} {W.ITEM[pet]["name"]} (tủ đồ thú cưng)')
    if coins:
        j = s['journey']
        e.need(j['wallet'] + coins <= 10**9, 'Ví đã đầy, quà Halloween chưa vào được.', 'wallet_full')
        jr._wallet(j, coins, 'life', '🎃 Lễ hội Ma Phố · đổi kẹo')
        new.append(f'+{fmt(coins)} xu vào ví')
    head = '🎃 Lễ hội Ma Phố'
    if data.get('why') == 'top':
        head += f': hạng {int(data.get("rank") or 0)} Bảng kẹo với {int(data.get("earned") or 0)} kẹo!'
    return head + (' Mới: ' + ', '.join(new) + '.' if new else ' Bạn đã có món này rồi.')


# ---------------------------------------------------------------- the season's close (housekeeping)
_swept = [0.0]
_closed = [False]


def run_housekeeping(store, every: float = 60.0) -> int:
    """About once a minute after END: the top TOP of the board get their titles (live_effects rows) and the ticker its line,
    exactly once (the 'final:2026' log row is written in the same transaction, under an advisory lock)."""
    t = now()
    if _closed[0] or t - _swept[0] < every:
        return 0
    _swept[0] = t
    if off() or t < END:
        return 0

    def run(db):
        _lock(db, 'final')
        if not db.execute("INSERT INTO hw_log(id, sid, kind, n, day, other, ip, at) VALUES('final:2026','','final',0,?,'','',?) "
                          'ON CONFLICT DO NOTHING', (vn_day(t), t)).rowcount:
            return -1
        rows = _top(db, TOP)
        for rank, r in enumerate(rows, 1):
            items = top_items(rank)
            if not items:
                continue
            payload = dict(why='top', rank=rank, earned=int(r['earned']), items=list(items))
            db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT DO NOTHING",
                       (f'{FX}:top:{_hs(r["sid"])}', r['sid'], FX, 1, json.dumps(payload, ensure_ascii=False), t))
        if rows:
            name = (_people(db, [rows[0]['sid']]).get(rows[0]['sid']) or {}).get('name') or 'một người chơi'
            mr._post_news(db, 'hween', 'hween:final:2026', f'🏆 Lễ hội Ma Phố khép lại! Vua Kẹo Halloween là {name} với {rows[0]["earned"]} kẹo. '
                          f'Top {TOP} đã nhận danh hiệu, kẹo còn lại đổi quà đến hết 01/11 nhé 🎃', '', '')
        return len(rows)
    n = store.transaction(run)
    _closed[0] = True
    clear_cache()
    return max(0, n)


# ---------------------------------------------------------------- admin, privacy
def admin_view(store) -> dict:
    """GET /api/admin/halloween: the season's numbers, the board with each account's age, the xu swaps with how many accounts
    share a network (a clone ring shows up as a group)."""
    t = now()
    with store.connect() as db:
        tot = db.execute('SELECT COUNT(*) AS players, COALESCE(SUM(earned),0) AS earned, COALESCE(SUM(candy),0) AS candy FROM hw_players '
                         'WHERE earned>0').fetchone()
        kinds = {r['kind']: dict(n=int(r['n']), candy=int(r['candy'])) for r in db.execute(
            'SELECT kind, COUNT(*) AS n, COALESCE(SUM(n),0) AS candy FROM hw_log GROUP BY kind').fetchall()}
        top = db.execute('SELECT h.sid, h.earned, h.candy, a.username, a.created_at FROM hw_players h LEFT JOIN accounts a ON a.sid=h.sid '
                         'WHERE h.earned>0 ORDER BY h.earned DESC, h.last_at LIMIT 30').fetchall()
        xu = sum(_bag_coins(r['id']) for r in db.execute("SELECT id FROM hw_log WHERE kind='swap'").fetchall())
        swaps = db.execute("SELECT l.sid, l.ip, l.at, a.username, a.created_at, (SELECT COUNT(DISTINCT x.sid) FROM hw_log x WHERE x.kind='swap' "
                           "AND x.ip=l.ip) AS same_ip FROM hw_log l LEFT JOIN accounts a ON a.sid=l.sid WHERE l.kind='swap' "
                           'ORDER BY l.at DESC LIMIT 200').fetchall()
    return dict(state=phase(t), off=off(), starts=START, ends=END, until=SHOP_UNTIL, night=NIGHT,
                totals=dict(players=int(tot['players']), earned=int(tot['earned']), candy=int(tot['candy']),
                            swaps=kinds.get('swap', {}).get('n', 0), xu=xu),
                kinds=kinds,
                top=[dict(rank=i, username=r['username'] or '', earned=int(r['earned']), candy=int(r['candy']), created=r['created_at'] or '')
                     for i, r in enumerate(top, 1)],
                swaps=[dict(username=r['username'] or '', created=r['created_at'] or '', ip=r['ip'], same_ip=int(r['same_ip']), at=float(r['at']))
                       for r in swaps])


def forget(store, token: str) -> None:
    """Account deletion ("XOA"): this player's candy and log rows go with it (rewards already paid stay in no save)."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM hw_log WHERE sid=?', (sid,))
        db.execute('DELETE FROM hw_players WHERE sid=?', (sid,))
    store.transaction(run)
    clear_cache()
