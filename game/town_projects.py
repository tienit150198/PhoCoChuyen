"""🏗️ Công trình của phố: the street's own buildings, paid for by its players (story mode).

Owner 16/10: "bổ sung công trình của phố góp tiền và có bảng tài trợ, có mục tiêu nhé. Thời gian xây dựng là 2 ngày hay
bao lâu đó … có cả map cũ và mới nhé". The richest players hold 13–48 million xu; this turns that money into something
the whole town sees. A pure sink: nothing here pays xu, speeds up work or changes an income. Catalogue:
game/town_projects_content.py (built in order, ids never renamed).

* One project raises money at a time (status 'funding'). jr_town_give {project, amount, anon?, confirm}: at least
  C.MIN_GIFT xu and at most C.MAX_GIFT at once (a wallet history row of every build stays within ±10 M), from the wallet then the bank account (lux._take: never a loan, never with a wallet in debt; wallet
  kind 'life', which every build knows). The reducer pays; command_commit, in the save's own transaction
  (game/storage.py), locks the project row (FOR UPDATE) and refuses the whole command (nothing paid) when the project
  is not raising money any more or the amount is more than what is left of the goal: two players closing the goal at
  once never overshoot, the second one is told what is left. The `town_gifts` row id is '<pid>:<n>' (n moves with the
  save), so it is written once.
* The goal reached: status 'building' for C.BUILD_SECS (48 real hours), then 'done': on both town maps for good, with
  its plaque (bia tài trợ). The next project of the catalogue then opens by itself. advance() does both, idempotently
  and under an advisory lock, lazily from GET /api/town and from the server's housekeeping (every 30 s): no cron
  needed, any number of processes.
* Completion: every sponsor gets a `live_effects` row of kind 'town' (game/live_effects.py pays it into the save on the
  next load, once): titles granted for good into game/spend.py's block like game/lux.py's (the 1st: the project's
  own title, the top 3: t_ct_vang, 4–10: t_ct_bac, everyone: the 🧱 badge t_ct_gach). An older build never pays a
  kind it does not know: the row waits. The street's ticker, a line on Cả phố and the fireworks NOTIFY of
  live/fireworks.py (a 'dai_tiec' show without a giver, the wish "Khánh thành …") announce it.
* Boards (GET /api/town, cached a few seconds): each project's top sponsors, total and sponsor count, the all-time board,
  mine; GET /api/town/board?p=<id>&page=<n> pages a project's whole list.

State `s['journey']['town']` (absent until the first contribution; journey.validate allows extra keys, so older builds
keep it untouched), see initial():
    v      VERSION
    n      contributions made                 sum   xu given
    by     {project id: xu given}             ids a newer build wrote are kept by shape
    last   {n, p (project), a (xu), anon, at (unix s)} the last contribution, for command_commit
Tables: town_projects, town_gifts (game/pg_schema.py, SCHEMA_VERSION 52).
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time

from . import bank as bk
from . import town_projects_content as C

VERSION = 1
KEY = 'town'
KIND = 'life'                     # wallet history kind (journey.HISTORY_KINDS of every build)
FX = 'town'                       # live_effects kind
BLOCK_KEYS = frozenset({'v', 'n', 'sum', 'by', 'last'})
LAST_KEYS = frozenset({'n', 'p', 'a', 'anon', 'at'})
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
COMMANDS = ('jr_town_give',)
BIG = 10**12
BY_MAX = 32
LOCK = 17852                      # pg_advisory_xact_lock(LOCK, 1): openings and completions
PAGE = 50                         # sponsors a page of the full list
PROJECT = {p['id']: p for p in C.PROJECTS}
ORDER = [p['id'] for p in C.PROJECTS]
TITLE_IDS = frozenset([p['title'] for p in C.PROJECTS] + [C.GOLD, C.SILVER, C.BRICK])
GUEST_NAME = 'Một người hàng xóm'
ANON_NAME = 'Một người hàng xóm giấu tên'


def now() -> float:
    return time.time()


def _core():
    from . import engine
    return engine


def _lux():
    from . import lux
    return lux


def fmt(n: int) -> str:
    return bk._fmt(n)


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _id(v) -> bool:
    return isinstance(v, str) and ID_RE.fullmatch(v) is not None


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- the save block
def initial() -> dict:
    return dict(v=VERSION, n=0, sum=0, by={}, last=None)


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
    return x is None or (isinstance(x, dict) and set(x) == LAST_KEYS and _int(x['n'], 1, 10**9) and _id(x['p'])
                         and _int(x['a'], 1, BIG) and type(x['anon']) is bool and _int(x['at'], 0, 2**34))


def _by_ok(d) -> bool:
    return isinstance(d, dict) and len(d) <= BY_MAX and all(_id(k) and _int(v, 1) for k, v in d.items())


def validate(s: dict) -> None:
    """``s['journey']['town']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    b = get(s)
    bad = 'Dữ liệu công trình trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get(KEY) is None, bad, 'invalid_save')
        return
    e.need(set(b) == BLOCK_KEYS and b['v'] == VERSION and _int(b['n'], 0, 10**9) and _int(b['sum']) and _by_ok(b['by'])
           and _last_ok(b['last']) and (b['last'] is None or b['last']['n'] == b['n']), bad, 'invalid_save')


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense. Absent stays
    absent."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    if not isinstance(b, dict):
        j[KEY] = initial()
        return
    out = initial()
    out['n'] = b['n'] if _int(b.get('n'), 0, 10**9) else 0
    out['sum'] = b['sum'] if _int(b.get('sum')) else 0
    by = b.get('by') if isinstance(b.get('by'), dict) else {}
    out['by'] = {k: v for k, v in list(by.items())[:BY_MAX] if _id(k) and _int(v, 1)}
    last = b.get('last')
    if isinstance(last, dict) and set(last) >= LAST_KEYS:
        last = {k: last[k] for k in LAST_KEYS}
    out['last'] = last if _last_ok(last) and last and last['n'] == out['n'] else None
    if out != b:
        j[KEY] = out


# ---------------------------------------------------------------- the command
def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Góp xây công trình chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'project', 'amount', 'anon', 'confirm'} and {'project', 'amount'} <= set(p),
         'Thông tin không hợp lệ.')
    pr = PROJECT.get(p['project']) if isinstance(p['project'], str) else None
    need(pr is not None, 'Chọn một công trình nhé.')
    amount = p['amount']
    need(type(amount) is int and C.MIN_GIFT <= amount, f'Góp từ {fmt(C.MIN_GIFT)} xu trở lên nhé.')
    need(amount <= min(C.MAX_GIFT, pr['goal']), f'Mỗi lần góp tối đa {fmt(min(C.MAX_GIFT, pr["goal"]))} xu nhé.')
    # Goals are whole thousands: whole-thousand gifts always leave a remainder someone can give (never 1–999 xu).
    need(amount % C.MIN_GIFT == 0, f'Góp theo bội số {fmt(C.MIN_GIFT)} xu nhé.')
    anon = p.get('anon', False)
    need(type(anon) is bool, 'Thông tin không hợp lệ.')
    need(p.get('confirm') is True, f'Xác nhận góp {fmt(amount)} xu xây {pr["name"]}.')
    lx = _lux()
    why = lx.ready_why(s, amount)
    need(not why, why, 'not_enough')
    how = lx._take(s, amount, f'🏗️ Góp xây {pr["name"]}')
    b = _ensure(s)
    b['n'] += 1
    b['sum'] = min(BIG, b['sum'] + amount)
    if pr['id'] in b['by'] or len(b['by']) < BY_MAX:
        b['by'][pr['id']] = min(BIG, b['by'].get(pr['id'], 0) + amount)
    b['last'] = dict(n=b['n'], p=pr['id'], a=amount, anon=anon, at=int(now()))
    return dict(message=f'{pr["emoji"]} Bạn góp {fmt(amount)} xu xây {pr["name"]} ({how}). Cả phố cảm ơn bạn!',
                town=dict(project=pr['id'], amount=amount))


def apply_fx(s: dict, p: dict, amount: int) -> str:
    """A 'town' live_effects row paid into the save (game/live_effects.py apply): a finished project's titles."""
    e = _core()
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    pr = PROJECT.get(data.get('project')) if isinstance(data.get('project'), str) else None
    titles, rank = data.get('titles'), data.get('rank')
    e.need(pr is not None and isinstance(titles, list) and 0 < len(titles) <= 4 and all(t in TITLE_IDS for t in titles)
           and _int(rank, 1, 10**7), 'Dữ liệu công trình không hợp lệ.')
    from . import spend as sp
    from . import spend_content as SC
    new = []
    for tid in titles:
        b = sp.get(s)
        if b and b['own'].get(tid, 0) >= SC.PERMANENT:
            continue
        b = sp._ensure(s)
        if len(b['own']) >= sp.OWN_MAX and tid not in b['own']:
            continue
        b['own'][tid] = SC.PERMANENT
        new.append(SC.TITLE_TEXT[tid])
    msg = f'{pr["emoji"]} {pr["name"]} đã khánh thành! Bạn đứng thứ {rank} trên bia tài trợ.'
    return msg + (' 🏷️ Danh hiệu mới: ' + ', '.join(new) + ' (đeo ở Phong cách).' if new else '')


def public(s: dict) -> dict | None:
    b = get(s)
    return dict(n=b['n'], sum=b['sum'], by={k: v for k, v in b['by'].items() if k in PROJECT}) if b else None


def catalogue() -> dict:
    return dict(projects=[dict(p) for p in C.PROJECTS], build=C.BUILD_SECS, min=C.MIN_GIFT, max=C.MAX_GIFT, presets=list(C.PRESETS))


# ---------------------------------------------------------------- database
def _display(db, sid: str, anon: bool) -> str:
    if anon:
        return ANON_NAME
    r = db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()
    return str(r['display'])[:24] if r and r['display'] else GUEST_NAME


def _news(db, ref: str, text: str) -> None:
    from . import marriage
    marriage._post_news(db, 'town', ref, text, '', '')


def command_commit(db, sid: str, action: str, after: dict) -> None:
    """Called by the storage layer for jr_town_* commands, in the save's transaction (game/storage.py). A GameError here
    rolls the whole command back: nothing is paid."""
    if action not in COMMANDS:
        return
    e = _core()
    b = get(after)
    x = b['last'] if b else None
    if not x:
        return
    pr = PROJECT.get(x['p'])
    e.need(pr is not None, 'Chọn một công trình nhé.')
    row = db.execute('SELECT id, goal, raised, status FROM town_projects WHERE id=? FOR UPDATE', (pr['id'],)).fetchone()
    e.need(row is not None and row['status'] == 'funding',
           f'{pr["name"]} đang không nhận góp nữa. Mở lại bảng công trình xem nhé.', 'closed')
    left = int(row['goal']) - int(row['raised'])
    e.need(x['a'] <= left, f'{pr["name"]} chỉ còn thiếu {fmt(left)} xu. Góp {fmt(left)} xu thôi nhé.', 'over')
    rid = f'{pid_of(sid)}:{x["n"]}'
    t = now()
    if not db.execute('INSERT INTO town_gifts(id, sid, project, amount, anon, at) VALUES(?,?,?,?,?,?) ON CONFLICT DO NOTHING '
                      'RETURNING id', (rid, sid, pr['id'], x['a'], 1 if x['anon'] else 0, float(x['at']))).fetchone():
        return   # written already (cannot happen: n moves with the save)
    who = _display(db, sid, x['anon'])
    if x['a'] == left:
        db.execute("UPDATE town_projects SET raised=goal, status='building', funded_at=?, ready_at=? WHERE id=?",
                   (t, t + C.BUILD_SECS, pr['id']))
        _news(db, f'town:goal:{pr["id"]}', f'{pr["emoji"]} Đủ {fmt(int(row["goal"]))} xu xây {pr["name"]}! {who} góp phần cuối. '
              f'Công trình khởi công, 2 ngày nữa khánh thành.')
    else:
        db.execute('UPDATE town_projects SET raised=raised+? WHERE id=?', (x['a'], pr['id']))
        if x['a'] >= C.NEWS_FROM:
            _news(db, f'town:{rid}', f'{pr["emoji"]} {who} góp {fmt(x["a"])} xu xây {pr["name"]}!')
    _VIEW.clear()


def _sponsors(db, project: str | None, limit: int | None = None, offset: int = 0) -> list:
    """(sid, name, xu) by xu given, the earliest first on a tie. A player is named when any of their gifts was; an
    erased one (sid '') stays anonymous."""
    where, args = ('WHERE g.project=?', [project]) if project else ('', [])
    tail = ''
    if limit is not None:
        tail, args = ' LIMIT ? OFFSET ?', args + [int(limit), int(offset)]
    rows = db.execute('SELECT g.sid AS sid, MIN(g.anon) AS anon, SUM(g.amount) AS xu, MIN(g.at) AS first, MAX(a.display) AS display '
                      f'FROM town_gifts g LEFT JOIN accounts a ON a.sid=g.sid AND g.sid<>\'\' {where} '
                      f'GROUP BY g.sid ORDER BY xu DESC, first ASC, g.sid{tail}', tuple(args)).fetchall()
    return [dict(sid=r['sid'], name=_name(r), xu=int(r['xu'])) for r in rows]


def _name(r) -> str:
    if r['anon'] or not r['sid']:
        return ANON_NAME
    return str(r['display'])[:24] if r['display'] else GUEST_NAME


def titles_for(rank: int, project: str) -> list:
    out = [PROJECT[project]['title']] if rank == 1 else []
    if rank <= C.TOP_TITLES:
        out.append(C.GOLD)
    elif rank <= C.TOP_SILVER:
        out.append(C.SILVER)
    return out + [C.BRICK]


def _fx_id(project: str, sid: str) -> str:
    return f'town:{project}:{hashlib.sha256(sid.encode()).hexdigest()[:16]}'


def _complete(db, r: dict, t: float) -> None:
    """A project finished (its row just moved to 'done', once): titles to every sponsor, the ticker, Cả phố, fireworks."""
    pr = PROJECT.get(r['id'])
    if not pr:
        return
    ranked = _sponsors(db, pr['id'])
    for i, x in enumerate(ranked, 1):
        if not x['sid']:
            continue   # erased players: their gifts stay on the plaque, there is no save to give a title to
        data = dict(project=pr['id'], rank=i, xu=x['xu'], titles=titles_for(i, pr['id']))
        db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) "
                   'ON CONFLICT DO NOTHING', (_fx_id(pr['id'], x['sid']), x['sid'], FX, 1, json.dumps(data), t))
    top = ranked[0]['name'] if ranked else ''
    text = f'{pr["emoji"]} {pr["name"]} khánh thành!' + (f' Cảm ơn {len(ranked)} nhà tài trợ, đứng đầu là {top}.' if ranked else '')
    _news(db, f'town:done:{pr["id"]}', text)
    from . import live_chat
    c = db.execute("INSERT INTO chat_messages(channel, pid, name, av, text, at, adm) VALUES('town', 'admin', ?, '🏗️', ?, ?, 1) "
                   'RETURNING id', ('🏗️ Công trình phố', (text + ' Ra xem bia tài trợ nhé 🎉')[:300], t)).fetchone()
    if c:
        live_chat.notify(db, dict(op='unhide', id=int(c['id'])))
    fid = f'{hashlib.sha256(("town:" + pr["id"]).encode()).hexdigest()[:16]}:{int(r["seq"])}'
    live_chat.notify(db, dict(op='fireworks', id=fid, pid='', size='dai_tiec', name='', wish=f'Khánh thành {pr["name"]}!'[:40],
                              at=float(t)))


def _open(db, pid: str, t: float) -> bool:
    pr = PROJECT[pid]
    n = db.execute("INSERT INTO town_projects(id, seq, goal, raised, status, opened_at) VALUES(?,?,?,0,'funding',?) "
                   'ON CONFLICT DO NOTHING', (pid, ORDER.index(pid) + 1, pr['goal'], t)).rowcount
    if n:
        _news(db, f'town:open:{pid}', f'🏗️ Phố góp tiền xây {pr["emoji"]} {pr["name"]}: mục tiêu {fmt(pr["goal"])} xu. Góp ở Công trình của phố nhé!')
    return bool(n)


def _due(rows: list, t: float) -> bool:
    if any(r['status'] == 'building' and r['ready_at'] is not None and float(r['ready_at']) <= t for r in rows):
        return True
    if any(r['status'] in ('funding', 'building') for r in rows):
        return False
    have = {r['id'] for r in rows}
    return any(p not in have for p in ORDER)


def _advance(db, t: float) -> list:
    db.execute(f'SELECT pg_advisory_xact_lock({LOCK}, 1)')
    rows = [dict(r) for r in db.execute('SELECT id, seq, status, ready_at FROM town_projects ORDER BY seq').fetchall()]
    done = []
    for r in rows:
        if r['status'] == 'building' and r['ready_at'] is not None and float(r['ready_at']) <= t:
            if db.execute("UPDATE town_projects SET status='done', done_at=ready_at WHERE id=? AND status='building'", (r['id'],)).rowcount == 1:
                r['status'] = 'done'
                _complete(db, r, t)
                done.append(('done', r['id']))
    if not any(r['status'] in ('funding', 'building') for r in rows):
        have = {r['id'] for r in rows}
        nxt = next((p for p in ORDER if p not in have), None)
        if nxt and _open(db, nxt, t):
            done.append(('open', nxt))
    return done


def advance(store, t: float | None = None) -> list:
    """Finish what is built, open the next project: idempotent, any number of processes (an advisory lock and guarded
    status changes). One cheap read when nothing is due."""
    t = now() if t is None else t
    with store.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT id, status, ready_at FROM town_projects').fetchall()]
    if not _due(rows, t):
        return []
    out = store.transaction(lambda db: _advance(db, t))
    if out:
        _VIEW.clear()
    return out


def run_housekeeping(store) -> None:
    """server.py maintenance (every 30 s, one process). Never raises."""
    import sys
    try:
        for what, pid in advance(store):
            sys.stderr.write(f'[town] {pid}: {what}\n')
    except Exception as e:  # noqa: BLE001 - housekeeping never takes the server down
        sys.stderr.write(f'[town] housekeeping: {type(e).__name__}\n')


# ---------------------------------------------------------------- the page (GET /api/town)
VIEW_SECS = 5.0
TOP = 10
_VIEW: dict = {}           # 'v' -> (monotonic, rows): one entry, bounded
_LOCK = threading.Lock()


def _rows(store) -> dict:
    with _LOCK:
        hit = _VIEW.get('v')
        if hit and time.monotonic() - hit[0] < VIEW_SECS:
            return hit[1]
    try:
        advance(store)
    except Exception:  # noqa: BLE001 - the page never fails for this: housekeeping tries again
        pass
    with store.connect() as db:
        rows = {r['id']: dict(r) for r in db.execute('SELECT * FROM town_projects').fetchall()}
        people = {r['project']: int(r['n']) for r in db.execute(
            "SELECT project, COUNT(DISTINCT sid) AS n FROM town_gifts GROUP BY project").fetchall()}
        tops = {pid: _sponsors(db, pid, TOP) for pid in rows}
        all_top = _sponsors(db, None, TOP)
        tot = db.execute("SELECT COALESCE(SUM(amount), 0) AS xu, COUNT(DISTINCT sid) AS n FROM town_gifts").fetchone()
    out = dict(rows=rows, people=people, tops=tops, all=all_top, xu=int(tot['xu']), n=int(tot['n']))
    with _LOCK:
        _VIEW.clear()
        _VIEW['v'] = (time.monotonic(), out)
    return out


def _status(r: dict | None, t: float) -> str:
    if not r:
        return 'soon'
    if r['status'] == 'building' and r['ready_at'] is not None and float(r['ready_at']) <= t:
        return 'done'
    return str(r['status'])


def _top(rows: list, sid: str | None) -> list:
    return [dict(name=x['name'], xu=x['xu'], me=bool(sid) and x['sid'] == sid) for x in rows]


def _sid(store, token) -> str | None:
    return store.key(token) if isinstance(token, str) and 16 <= len(token) <= 128 else None


def view(store, token: str | None) -> dict:
    """Every project (soon / funding / building / done) with its goal, raised, sponsors and top 10, the all-time board,
    and mine."""
    t = now()
    v = _rows(store)
    sid = _sid(store, token)
    projects, current = [], ''
    for p in C.PROJECTS:
        r = v['rows'].get(p['id'])
        st = _status(r, t)
        if st in ('funding', 'building') and not current:
            current = p['id']
        f = lambda k: float(r[k]) if r and r.get(k) is not None else 0.0
        done_at = f('done_at') or (f('ready_at') if st == 'done' else 0.0)
        projects.append(dict(id=p['id'], emoji=p['emoji'], name=p['name'], blurb=p['blurb'], goal=int(r['goal']) if r else p['goal'],
                             raised=int(r['raised']) if r else 0, people=v['people'].get(p['id'], 0), status=st,
                             opened=f('opened_at'), funded=f('funded_at'), ready=f('ready_at'), done=done_at,
                             top=_top(v['tops'].get(p['id'], []), sid)))
    mine = dict(xu=0, by={})
    if sid:
        with store.connect() as db:
            mine['by'] = {r['project']: int(r['xu']) for r in db.execute(
                'SELECT project, SUM(amount) AS xu FROM town_gifts WHERE sid=? GROUP BY project', (sid,)).fetchall()}
        mine['xu'] = sum(mine['by'].values())
    return dict(now=t, build=C.BUILD_SECS, min=C.MIN_GIFT, max=C.MAX_GIFT, presets=list(C.PRESETS), projects=projects, current=current,
                all=_top(v['all'], sid), xu=v['xu'], people=v['n'], mine=mine)


def board(store, token: str | None, project, page) -> dict:
    """GET /api/town/board?p=<id>&page=<n>: a project's whole list of sponsors, PAGE a page."""
    e = _core()
    e.need(isinstance(project, str) and project in PROJECT, 'Chọn một công trình nhé.')
    try:
        page = max(0, min(10**4, int(page or 0)))
    except (TypeError, ValueError):
        page = 0
    sid = _sid(store, token)
    with store.connect() as db:
        rows = _sponsors(db, project, PAGE + 1, page * PAGE)
        tot = db.execute('SELECT COALESCE(SUM(amount), 0) AS xu, COUNT(DISTINCT sid) AS n FROM town_gifts WHERE project=?',
                         (project,)).fetchone()
    more = len(rows) > PAGE
    return dict(project=project, page=page, more=more, xu=int(tot['xu']), people=int(tot['n']),
                rows=[dict(rank=page * PAGE + i + 1, **x) for i, x in enumerate(_top(rows[:PAGE], sid))])


def admin_view(store) -> dict:
    """The operator's look (admin page): every project's row and totals."""
    v = view(store, None)
    return dict(projects=[{k: p[k] for k in ('id', 'emoji', 'name', 'goal', 'raised', 'people', 'status', 'opened', 'funded', 'ready', 'done')}
                          for p in v['projects']], xu=v['xu'], people=v['people'], current=v['current'])


def forget(db, sid: str) -> None:
    """A player erased their data: what they gave stays on the plaques, as anonymous."""
    db.execute("UPDATE town_gifts SET sid='', anon=1 WHERE sid=?", (sid,))
    _VIEW.clear()
