"""🐾 Đấu trường pet (owner 19/10: "thêm thi đua nữa nhé, kết hợp với pet ra tranh đấu với bang nữa").

Players' pets fight (game/pet_battle.py, server-authoritative): a lineup of 1–3 pets (home or the 🏠 kennel) against
another player's, a relay (front pets fight, the next steps in). POST /api/arena/<op> (server.py), never a save write:
* ⚔️ Đấu xếp hạng (`fight`): a random opponent of a similar rating (Elo, START), from the players who set a lineup and
  were around in the last ACTIVE_DAYS. Their lineup is a snapshot (`snap`: refreshed by every jr_pet_* command in the
  save's own transaction, on_pet_commit), so an opponent never needs to be online. The attacker's rating moves by
  K_ATT, the defender's by K_DEF. Nobody near: a practice fight against 🐾 Bé nhà Mây of the same strength (`spar`,
  unrated).
* 🤝 Đấu với bạn (`friend`): a friend's lineup, unrated (no farming between friends, nothing to farm).
* 🎯 Thử thách (`npc`): three NPC lineups a day (Dễ / Vừa / Khó, NPC_X of the player's own strength, seeded by the
  day); the first win of each a day is a ⭐ in the week's season.
* 🏆 Mùa tuần: the ladder of the Vietnam ISO week (pet_arena_season), each player starting the week from their
  rating pulled halfway back to START; titles (game/lb_titles.py board 'arena': 🏆 Vua đấu trường tuần …) for those
  with MIN_GAMES ranked battles against MIN_OPP different opponents. Rewards are titles and stars only: no xu, ever.
* 🏟️ Giải tuần (game/pet_cup.py) and 🛡️ Bang chiến pet (game/pet_war.py) share the fighters and the engine.

Anti-farm (the exploit rings of 09/10 farmed between alt accounts; game/dog_bark.py's rules): ranked needs an
account at least ACCOUNT_DAYS old; never two players of one network (`ip`, a keyed hash of the last address each
used: the defender's and the attacker's); the same two players at most PAIR_DAY ranked battles a Vietnam day (either
side attacking) and never one of the attacker's last RECENT opponents again; RANK_DAY ranked fights a day.
Friendly and practice fights move no rating. Pets are never harmed: no command here writes a save.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time

from . import pet_battle as B
from . import pets_content as C

START = 1000
FLOOR = 100
K_ATT, K_DEF = 32, 16
LINEUP_MAX = 3
RANK_DAY = 20            # ranked (and spar) fights a Vietnam day
FRIEND_DAY = 20
NPC_DAY = 12             # practice tries a day
PAIR_DAY = 2             # ranked battles between the same two players a day
RECENT = 3               # never one of the attacker's last RECENT opponents again
ACCOUNT_DAYS = 1
ACTIVE_DAYS = 14
MIN_GAMES, MIN_OPP = 5, 3
WINDOWS = (120, 250, 450, 10**6)    # rating distance tried, nearest first
NPC_X = (85, 100, 118)              # % of the player's own strength: Dễ, Vừa, Khó
NPC_NAMES = ('Dễ', 'Vừa', 'Khó')
NPC_OWNER = '🐾 Bé nhà Mây'
RECENT_LIST = 12
LIGHT = frozenset({'replay', 'ladder', 'cup_board', 'war', 'war_match', 'war_team', 'war_lineup', 'war_lineup_off', 'tc', 'tc_find', 'tc_match', 'tc_unreg', 'tc_order', 'tc_send',
                   'tc_answer', 'tc_cancel', 'tc_set'})   # server.py: these read no save (⚔️ Thách đấu: game/bang_challenge.py LIGHT)
DAY = 86400


class ArenaError(Exception):
    def __init__(self, message: str, code: str = 'arena', status: int = 400):
        super().__init__(message)
        self.code, self.status = code, status


def need(ok, message: str, code: str = 'arena', status: int = 400) -> None:
    if not ok:
        raise ArenaError(message, code, status)


def now() -> float:
    return time.time()


def vn_day(t: float) -> str:
    from .wedding_live import vn_day as d
    return d(t)


def vn_week(t: float) -> str:
    from .wedding_live import vn_week as w
    return w(t)


def ip_tag(ip: str) -> str:
    """A short keyed hash of the network address (never the address itself)."""
    if not isinstance(ip, str) or not ip or ip == '?':
        return ''
    salt = os.environ.get('PET_ARENA_IP_SALT') or os.environ.get('LIXI_IP_SALT') or 'mnl-pet-arena'
    return hashlib.sha256(f'{salt}|{ip}'.encode()).hexdigest()[:16]


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def _j(text, default):
    try:
        v = json.loads(text) if isinstance(text, str) and text else default
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


# ---------------------------------------------------------------- fighters from a save (read only)
def fighter(s: dict, p: dict) -> dict:
    """The battle snapshot of pet `p` of save `s`: its look (what the boards draw) and its five stats."""
    from . import pet_tiers as px
    from . import pet_wardrobe as pw
    rec = px.rec_of(s, p)
    st = px.stats(s, p, rec)
    br = C.BREEDS.get(p['b']) or {}
    legend = px.is_legend(p, s)
    f = dict(id=p['id'], n=str(p['n'])[:24], b=p['b'], c=p['c'], r=rec['r'], k=br.get('kind') or 'dog',
             e=B.element_of(p['b']), s=st, pw=sum(st))
    if rec['fx']:
        f['x'] = rec['fx']
    if legend and br.get('fuse') != 'legend':
        f['lg'] = True          # 🌟 a legendary that kept its breed (pet-art fxRef)
    if legend or br.get('fuse') == 'myth':
        f['L'] = 1              # 🌟 Thần uy
    f.update(pw.walk_look(s, p))
    return f                    # 🪽 the worn wing is in the stats already (pet_tiers.stats, 2.5.7): no `wg`, so ENGINE 1 replays it


def candidates(s: dict) -> list:
    """The pets that may fight: at home and in the kennel (not at the grandparents'), of a breed this build knows."""
    from . import pet_tiers as px
    from . import pets
    b = pets.get(s)
    x = px.get(s)
    rows = (b['list'] if b else []) + (x['ken'] if x else [])
    return [p for p in rows if p.get('b') in C.BREEDS]


def lineup_snap(s: dict, ids: list) -> list:
    by = {p['id']: p for p in candidates(s)}
    return [fighter(s, by[i]) for i in ids if i in by][:LINEUP_MAX]


def default_lineup(s: dict) -> list:
    """The strongest pets first (a player who never chose)."""
    from . import pet_tiers as px
    rows = sorted(candidates(s), key=lambda p: -px.power(s, p))
    return [p['id'] for p in rows[:LINEUP_MAX]]


# ---------------------------------------------------------------- the player's row
def _story(state) -> dict:
    j = (state or {}).get('journey') if isinstance((state or {}).get('journey'), dict) else {}
    return j


def _who(store, token: str) -> tuple:
    from . import marriage as mr
    sid, display = mr.whoami(store, token)
    need(sid, 'Tải lại trang để bắt đầu phiên chơi.', 'session_missing', 401)
    return sid, display


def _row(db, sid: str, lock: bool = False):
    r = db.execute('SELECT * FROM pet_arena WHERE sid=?' + (' FOR UPDATE' if lock else ''), (sid,)).fetchone()
    return dict(r) if r else None


def _write_row(db, sid: str, name: str, ids: list, snap: list, tag: str, t: float) -> None:
    pw = sum(int(f.get('pw') or 0) for f in snap)
    db.execute('INSERT INTO pet_arena(sid, pid, name, lineup, snap, size, pw, rating, best, games, wins, ip, npc, at, last) '
               "VALUES(?,?,?,?,?,?,?,?,?,0,0,?,'{}',?,0) ON CONFLICT (sid) DO UPDATE SET name=EXCLUDED.name, lineup=EXCLUDED.lineup, "
               'snap=EXCLUDED.snap, size=EXCLUDED.size, pw=EXCLUDED.pw, ip=CASE WHEN EXCLUDED.ip<>\'\' THEN EXCLUDED.ip ELSE pet_arena.ip END, at=EXCLUDED.at',
               (sid, pid_of(sid), name[:24], _dump(ids), _dump(snap), len(snap), pw, START, START, tag, t))


def _sync(db, sid: str, state: dict, display: str, tag: str, t: float, ids=None) -> dict:
    """The row with a fresh snapshot of the lineup from the save (made with the strongest pets the first time)."""
    row = _row(db, sid)
    if ids is None:
        ids = _j(row['lineup'], []) if row else []
        have = {p['id'] for p in candidates(state)}
        ids = [i for i in ids if i in have] or default_lineup(state)
    snap = lineup_snap(state, ids)
    _write_row(db, sid, display or (row['name'] if row else '') or 'Người chơi', [f['id'] for f in snap], snap, tag, t)
    return _row(db, sid)


def best_power(s: dict) -> int:
    """💪 The power (pet_tiers.power: the five stats) of the player's strongest pet at home or in the kennel, 0 without one."""
    from . import pet_tiers as px
    return max((px.power(s, p) for p in candidates(s)), default=0)


def power_commit(db, sid: str, s: dict) -> None:
    """💪 pet_power (SCHEMA_VERSION 61): the player's strongest pet power, the bang ranking's Chiến lực (game/bang.py
    standings: summed over a bang's members, never a save parsed per request). One primary-key read, a write only
    when it changed."""
    pw = best_power(s)
    r = db.execute('SELECT pw FROM pet_power WHERE sid=?', (sid,)).fetchone()
    if (int(r['pw']) if r else 0) == pw:
        return
    db.execute('INSERT INTO pet_power(sid, pw, at) VALUES(?,?,?) ON CONFLICT (sid) DO UPDATE SET pw=EXCLUDED.pw, at=EXCLUDED.at', (sid, pw, now()))


def on_pet_commit(db, sid: str, after: dict) -> None:
    """A jr_pet_* command (game/pets.py command_commit, the save's own transaction): the lineup's snapshot follows the
    pets (a fusion, training, gear). Nothing for a player who never opened the arena. 💪 Their strongest pet's power
    (pet_power) follows too, for everyone."""
    power_commit(db, sid, after)
    row = db.execute('SELECT lineup, snap FROM pet_arena WHERE sid=?', (sid,)).fetchone()
    if row:
        ids = _j(row['lineup'], [])
        have = {p['id'] for p in candidates(after)}
        ids = [i for i in ids if i in have] or default_lineup(after)
        snap = lineup_snap(after, ids)
        lineup, text = _dump([f['id'] for f in snap]), _dump(snap)
        if (lineup, text) != (row['lineup'], row['snap']):   # nothing changed (a feed, a walk): no write, no row lock
            db.execute('UPDATE pet_arena SET lineup=?, snap=?, size=?, pw=? WHERE sid=?',
                       (lineup, text, len(snap), sum(f['pw'] for f in snap), sid))
    from . import pet_war
    pet_war.on_pet_commit(db, sid, after)
    from . import bang_challenge
    bang_challenge.on_pet_commit(db, sid, after)   # ⚔️ the pet on the bang's Thách đấu roster follows too


def forget(db, sid: str) -> None:
    """A player erased their data (game/storage.py delete): their arena rows go; past matches keep the names shown."""
    db.execute('DELETE FROM pet_arena WHERE sid=?', (sid,))
    db.execute('DELETE FROM pet_arena_season WHERE sid=?', (sid,))
    db.execute('DELETE FROM pet_power WHERE sid=?', (sid,))
    db.execute('DELETE FROM pet_cup_entries WHERE sid=? AND week NOT IN (SELECT week FROM pet_cup)', (sid,))
    db.execute('DELETE FROM pet_war_picks WHERE sid=? AND week NOT IN (SELECT week FROM pet_war)', (sid,))
    from . import bang_challenge
    bang_challenge.forget(db, sid)   # ⚔️ their Thách đấu roster rows (played challenges keep the bangs' names only)


# ---------------------------------------------------------------- ratings
def expected(ra: int, rb: int) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def elo(ra: int, rb: int, score: float, k: int) -> int:
    """The change of a's rating (score 1 win, 0.5 draw, 0 loss), never below FLOOR."""
    d = round(k * (score - expected(ra, rb)))
    return max(FLOOR - ra, d)


def season_rating(db, week: str, sid: str, rating: int) -> int:
    """The rating a player starts this week's season from (halfway back to START), the row made."""
    r = db.execute('SELECT rating FROM pet_arena_season WHERE week=? AND sid=?', (week, sid)).fetchone()
    if r:
        return int(r['rating'])
    start = START + (rating - START) // 2
    db.execute('INSERT INTO pet_arena_season(week, sid, rating, at) VALUES(?,?,?,?) ON CONFLICT DO NOTHING', (week, sid, start, now()))
    return start


def season_peek(db, week: str, sid: str, rating: int) -> int:
    """season_rating without writing (the matchmaking read)."""
    r = db.execute('SELECT rating FROM pet_arena_season WHERE week=? AND sid=?', (week, sid)).fetchone()
    return int(r['rating']) if r else START + (rating - START) // 2


def met_today(db, a: str, b: str, day: str) -> int:
    return int(db.execute("SELECT COUNT(*) FROM pet_arena_matches WHERE kind='rank' AND day=? AND ((a=? AND b=?) OR (a=? AND b=?))",
                          (day, a, b, b, a)).fetchone()[0])


def _season_add(db, week: str, sid: str, rating: int, res: int, opp: str, t: float) -> None:
    """res 0 win, 1 loss, 2 draw; `opp` counted once among the distinct opponents of the week."""
    new_opp = not db.execute("SELECT 1 FROM pet_arena_matches WHERE week=? AND kind='rank' AND ((a=? AND b=?) OR (a=? AND b=?)) LIMIT 1",
                             (week, sid, opp, opp, sid)).fetchone()
    col = ('w', 'l', 'd')[res]
    db.execute(f'UPDATE pet_arena_season SET rating=?, {col}={col}+1, opp=opp+?, at=? WHERE week=? AND sid=?',
               (rating, 1 if new_opp else 0, t, week, sid))


# ---------------------------------------------------------------- matches
def new_id(prefix: str) -> str:
    return prefix + secrets.token_hex(8)


def _payload(row: dict, viewer: str | None = None) -> dict:
    """What the page needs to animate a stored match: both sides (names, pets with their battle numbers) and the log
    played again from its seed (the same fight). `me` 0/1: the viewer's side, None when watching."""
    data = _j(row['data'], {})
    a, b = data.get('a') or [], data.get('b') or []
    out = dict(id=row['id'], kind=row['kind'], at=row['at'], w=row['win'], da=row['da'], db=row['db'], ra=row['ra'], rb=row['rb'],
               rd=row.get('rd') or 0,
               sides=[dict(name=row['a_name'] or 'Người chơi', pets=[pet_view(f) for f in a]),
                      dict(name=row['b_name'] or NPC_OWNER, pets=[pet_view(f) for f in b])],
               me=0 if viewer and row['a'] == viewer else 1 if viewer and row['b'] == viewer else None)
    if row['engine'] in B.REPLAYS:   # 🪽 WING_ENGINE: a fighter wore wings (2.5.3 shows the stored result only)
        res = B.battle(a, b, B.seed_of(row['id']))
        out.update(ev=res['ev'], hp=res['hp'], max=res['max'])
    return out


def pet_view(f: dict) -> dict:
    """A fighter for the page: its look, rank, element, skill, passive and battle numbers (never an id of a save)."""
    look = {k: f[k] for k in ('n', 'b', 'c', 'r', 'x', 'lg', 'a', 'ar', 'o', 'st', 'k', 'e', 'pw') if k in f}
    look.update(B.preview(f))
    return look


def _summary(row: dict, viewer: str) -> dict:
    mine = 0 if row['a'] == viewer else 1
    other = row['b_name'] if mine == 0 else row['a_name']
    won = row['win'] == mine
    return dict(id=row['id'], kind=row['kind'], at=row['at'], vs=other or NPC_OWNER, res='win' if won else 'draw' if row['win'] == 2 else 'loss',
                d=row['da'] if mine == 0 else row['db'], attack=mine == 0)


def record(db, kind: str, mid: str, a: dict, b: dict, a_snap: list, b_snap: list, res: dict, t: float, ra=0, rb=0, da=0, dbb=0, rd=0) -> dict:
    """Store one match (the replay data: both snapshots, the seed is the id)."""
    row = dict(id=mid, kind=kind, day=vn_day(t), week=vn_week(t), a=a.get('sid') or '', b=b.get('sid') or '', a_name=(a.get('name') or '')[:24],
               b_name=(b.get('name') or '')[:24], win=res['w'], ra=ra, rb=rb, da=da, db=dbb, rd=rd, engine=B.engine_of(a_snap, b_snap),
               data=_dump(dict(a=a_snap, b=b_snap)), at=t)
    db.execute('INSERT INTO pet_arena_matches(id, kind, day, week, a, b, a_name, b_name, win, ra, rb, da, db, rd, engine, data, at) '
               'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', tuple(row[k] for k in ('id', 'kind', 'day', 'week', 'a', 'b', 'a_name', 'b_name', 'win', 'ra', 'rb', 'da', 'db', 'rd', 'engine', 'data', 'at')))
    return row


def _count(db, sid: str, day: str, kinds: tuple) -> int:
    marks = ','.join('?' * len(kinds))
    return int(db.execute(f'SELECT COUNT(*) FROM pet_arena_matches WHERE a=? AND day=? AND kind IN ({marks})', (sid, day, *kinds)).fetchone()[0])


# ---------------------------------------------------------------- 🐾 Bé nhà Mây (practice lineups)
def npc_lineup(seed: int, like: list, pct: int, n: int | None = None) -> list:
    """An NPC lineup of the strength of `like` (pct %), its breeds and names from the seed: never a player's pet."""
    rng = B.Rng(seed)
    like = [f for f in (B.clean(x) for x in like) if f] or [dict(s=[20] * 5, r=0)]
    n = n or len(like)
    pool = [b for b in C.SHOP]
    out = []
    for i in range(n):
        base = like[min(i, len(like) - 1)]
        bid = pool[rng.below(len(pool))]
        br = C.BREEDS[bid]
        s = [max(1, (v * pct // 100) + rng.below(9) - 4) for v in base['s']]
        out.append(dict(n=C.SHELTER_NAMES[rng.below(len(C.SHELTER_NAMES))], b=bid, c=rng.below(len(br['coats'])),
                        r=int(base.get('r') or 0), k=br['kind'], e=B.element_of(bid), s=s, pw=sum(s), npc=1))
    return out


def npc_today(sid: str, day: str, like: list) -> list:
    """Today's three thử thách lineups for this player."""
    return [npc_lineup(B.seed_of(f'npc|{day}|{sid}|{i}'), like, NPC_X[i]) for i in range(len(NPC_X))]


# ---------------------------------------------------------------- the ops
BANG_ONLY = True   # owner 21/10: "đấu trường pets ẩn đi, chỉ dành cho bang thôi … bên ngoài k chơi được"
NO_BANG = 'Đấu trường chỉ dành cho thành viên bang. Vào một bang để cùng đồng đội ra trận nhé!'


def bang_of(db, sid: str):
    """The player's current bang id (active, not hidden) or None."""
    from . import bang_pets
    r = bang_pets._member(db, sid)
    return str(r['bang']) if r else None


NO_ISLAND = 'Bang chưa có 🏝️ Đảo bang. Bang chủ hoặc Phó bang mua đảo bằng quỹ bang (mục ⚔️ Bang) để cả bang ra trận nhé!'


def island_lock(db, sid: str, bang_id: str) -> dict | None:
    """🏝️ owner 21/10 "phải có mua đảo bang thì mới chơi được": None when the bang holds its island, else what the
    locked page shows (officer: the player may buy it; cost: cấp 1's price)."""
    from . import bang as BG
    from . import bang_content as BC
    if BG.has_island(db, bang_id):
        return None
    r = db.execute("SELECT role FROM bang_members WHERE sid=? AND bang=? AND status='in'", (sid, bang_id)).fetchone()
    officer = bool(r) and BC.ROLES.get(r['role'], BC.ROLES['tv'])[3] >= BC.BUILD_FROM
    return dict(officer=officer, cost=BC.isle_cost(1)[0])


def need_bang(store, sid: str, island: bool = False) -> str:
    with store.connect() as db:
        b = bang_of(db, sid)
        need(b or not BANG_ONLY, NO_BANG, 'no_bang', 403)
        if b and island:
            need(island_lock(db, sid, b) is None, NO_ISLAND, 'no_island', 403)
    return b


def _gate(state, display, ranked: bool = False) -> dict:
    j = _story(state)
    need(display, 'Tạo tài khoản để vào đấu trường nhé.', 'account_required', 403)
    need(j.get('story'), 'Đấu trường chỉ có trong hành trình.', 'not_story', 403)
    need(candidates(state), 'Nuôi một bé đã nhé: nhận nuôi ở 🐾 Thú cưng.', 'no_pet', 409)
    return j


def view(store, token, state, ip='') -> dict:
    sid, display = _who(store, token)
    j = _story(state)
    out = dict(rules=rules(), elements=B.catalogue()['elements'])
    if not display or not j.get('story'):
        out['locked'] = 'account' if not display else 'story'
        return out
    t = now()
    day, week = vn_day(t), vn_week(t)
    mine = candidates(state)
    if not mine:
        out['locked'] = 'pet'
        return out
    if BANG_ONLY:
        with store.connect() as db:
            b = bang_of(db, sid)
            if not b:
                out['locked'] = 'bang'
                return out
            lock = island_lock(db, sid, b)   # 🏝️ 21/10: a bang plays here once it holds its island
            if lock:
                out.update(locked='island', island=lock)
                return out

    def run(db):
        row = _sync(db, sid, state, display, ip_tag(ip), t)
        power_commit(db, sid, state)   # 💪 the bang ranking's Chiến lực, fresh from this visit
        rating = season_rating(db, week, sid, int(row['rating']))
        season = dict(db.execute('SELECT * FROM pet_arena_season WHERE week=? AND sid=?', (week, sid)).fetchone())
        recent = [dict(r) for r in db.execute('SELECT * FROM pet_arena_matches WHERE (a=? OR b=?) AND kind IN (\'rank\',\'friend\',\'npc\',\'spar\',\'cup\') '
                                              'ORDER BY at DESC LIMIT ?', (sid, sid, RECENT_LIST)).fetchall()]
        counts = dict(rank=_count(db, sid, day, ('rank', 'spar')), friend=_count(db, sid, day, ('friend',)), npc=_count(db, sid, day, ('npc',)))
        return row, rating, season, recent, counts
    row, rating, season, recent, counts = store.transaction(run)
    snap = _j(row['snap'], [])
    npc = _j(row['npc'], {})
    won = npc.get('won') if npc.get('d') == day and isinstance(npc.get('won'), list) else []
    from . import pet_tiers as px
    out.update(
        me=dict(name=row['name'], rating=rating, best=int(row['best']), games=int(row['games']), wins=int(row['wins']),
                season=dict(week=week, w=season['w'], l=season['l'], d=season['d'], opp=season['opp'], stars=season['stars'],
                            ok=season['w'] + season['l'] + season['d'] >= MIN_GAMES and season['opp'] >= MIN_OPP)),
        lineup=[f['id'] for f in snap], team=[pet_view(f) for f in snap], pw=sum(f['pw'] for f in snap),
        pets=[dict(pet_view(fighter(state, p)), id=p['id'], at='home' if p in (state['journey'].get('pets') or {}).get('list', []) else 'ken')
              for p in sorted(mine, key=lambda p: -px.power(state, p))],
        today=dict(counts, rank_max=RANK_DAY, friend_max=FRIEND_DAY, npc_max=NPC_DAY),
        npc=[dict(stage=i, name=NPC_NAMES[i], won=i in won, pw=sum(f['pw'] for f in lineup), pets=[pet_view(f) for f in lineup])
             for i, lineup in enumerate(npc_today(sid, day, snap))],
        recent=[_summary(r, sid) for r in recent])
    from . import pet_cup, pet_war
    out['cup'] = pet_cup.summary(store, sid, t)
    out['war'] = pet_war.summary(store, sid, t)
    return out


def set_lineup(store, token, state, data, ip='') -> dict:
    sid, display = _who(store, token)
    _gate(state, display)
    ids = data.get('pets')
    need(isinstance(ids, list) and 1 <= len(ids) <= LINEUP_MAX and all(isinstance(i, str) for i in ids) and len(set(ids)) == len(ids),
         f'Chọn 1 đến {LINEUP_MAX} bé nhé.', 'bad_lineup')
    have = {p['id'] for p in candidates(state)}
    need(all(i in have for i in ids), 'Bé này không ở nhà hay trại nuôi.', 'not_owned', 409)
    t = now()
    store.transaction(lambda db: _sync(db, sid, state, display, ip_tag(ip), t, ids))
    return dict(ok=True, message='🐾 Đã xếp đội: ' + ', '.join(p['n'] for i in ids for p in candidates(state) if p['id'] == i) + '.')


def _opponent(db, sid: str, rating: int, size: int, tag: str, day: str, t: float, bang=None):
    """A ranked opponent: a similar rating (WINDOWS), never the same network, a blocked player, one met PAIR_DAY times
    today or one of the last RECENT; the same lineup size first. None: nobody fits."""
    from . import lixi
    last = [r['b'] for r in db.execute("SELECT b FROM pet_arena_matches WHERE a=? AND kind='rank' ORDER BY at DESC LIMIT ?", (sid, RECENT)).fetchall()]
    met = {}
    for r in db.execute("SELECT a, b FROM pet_arena_matches WHERE kind='rank' AND day=? AND (a=? OR b=?)", (day, sid, sid)).fetchall():
        o = r['b'] if r['a'] == sid else r['a']
        met[o] = met.get(o, 0) + 1
    if bang:   # 21/10: only the player's bang mates
        rows = db.execute("SELECT p.sid, p.rating, p.size, p.ip, p.pw FROM pet_arena p JOIN bang_members m ON m.sid=p.sid AND m.status='in' "
                          'WHERE m.bang=? AND p.sid<>? AND p.size>0 AND p.at>? ORDER BY abs(p.rating-?) LIMIT 60',
                          (bang, sid, t - ACTIVE_DAYS * DAY, rating)).fetchall()
    else:
        rows = db.execute('SELECT sid, rating, size, ip, pw FROM pet_arena WHERE sid<>? AND size>0 AND at>? ORDER BY abs(rating-?) LIMIT 60',
                          (sid, t - ACTIVE_DAYS * DAY, rating)).fetchall()
    for w in WINDOWS:
        ok = [r for r in rows if abs(int(r['rating']) - rating) <= w and r['sid'] not in last and met.get(r['sid'], 0) < PAIR_DAY
              and not (tag and r['ip'] == tag)]
        if not ok:
            continue
        ok.sort(key=lambda r: (int(r['size']) != size, abs(int(r['rating']) - rating)))
        pool = ok[:6]
        rng = B.Rng(B.seed_of(f'pick|{sid}|{t}'))
        for r in rng.shuffle(pool):
            if not lixi._blocked(db, sid, r['sid']):
                return dict(r)
    return None


def _old_enough(db, sid: str, t: float) -> bool:
    from .wedding_live import account_cut
    r = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    return bool(r) and str(r['created_at']) <= account_cut(t, ACCOUNT_DAYS)


def fight(store, token, state, data, ip='') -> dict:
    """⚔️ A ranked battle against a random opponent of a similar rating (or a spar with Bé nhà Mây)."""
    sid, display = _who(store, token)
    _gate(state, display, True)
    t = now()
    day, week, tag = vn_day(t), vn_week(t), ip_tag(ip)

    store.transaction(lambda db: _sync(db, sid, state, display, tag, t))   # the lineup's snapshot, fresh from the save

    def run(db):
        # Lock order: the pet_arena rows by sid before any write (two players attacking each other never deadlock).
        need(_old_enough(db, sid, t), f'Tài khoản cần đủ {ACCOUNT_DAYS} ngày mới đấu xếp hạng được. Thử thách và đấu với bạn thì chơi ngay nhé.', 'too_new', 403)
        me = _row(db, sid)
        mine = _j(me['snap'], []) if me else []
        need(mine, 'Xếp đội trước đã nhé.', 'no_lineup', 409)
        bang = bang_of(db, sid)
        need(bang or not BANG_ONLY, NO_BANG, 'no_bang', 403)
        opp = _opponent(db, sid, season_peek(db, week, sid, int(me['rating'])), len(mine), tag, day, t, bang)
        for x in sorted({sid, opp['sid']} if opp else {sid}):
            db.execute('SELECT 1 FROM pet_arena WHERE sid=? FOR UPDATE', (x,))
        need(_count(db, sid, day, ('rank', 'spar')) < RANK_DAY, f'Hôm nay đã đấu {RANK_DAY} trận xếp hạng rồi. Mai đấu tiếp nhé!', 'limit', 409)
        if not opp:   # nobody near: a practice fight, unrated
            theirs = npc_lineup(B.seed_of(f'spar|{sid}|{t}'), mine, 100)
            mid = new_id('s')
            res = B.battle(mine, theirs, B.seed_of(mid))
            return record(db, 'spar', mid, dict(sid=sid, name=display), dict(name=NPC_OWNER), mine, theirs, res, t)
        need(met_today(db, sid, opp['sid'], day) < PAIR_DAY, 'Hai bạn đã đấu đủ hôm nay. Thử lại để gặp người khác nhé.', 'pair_limit', 409)
        me, other = _row(db, sid), _row(db, opp['sid'])
        mine, theirs = _j(me['snap'], []), _j(other['snap'], [])
        ra = season_rating(db, week, sid, int(me['rating']))
        rb = season_rating(db, week, other['sid'], int(other['rating']))
        mid = new_id('r')
        res = B.battle(mine, theirs, B.seed_of(mid))
        score = 1.0 if res['w'] == 0 else 0.5 if res['w'] == 2 else 0.0
        da, dbb = elo(ra, rb, score, K_ATT), elo(rb, ra, 1.0 - score, K_DEF)
        # the season's distinct opponents are counted before this match is stored
        _season_add(db, week, sid, ra + da, (0, 1, 2)[res['w']], other['sid'], t)
        _season_add(db, week, other['sid'], rb + dbb, (1, 0, 2)[res['w']], sid, t)
        row = record(db, 'rank', mid, dict(sid=sid, name=display), dict(sid=other['sid'], name=other['name']), mine, theirs, res, t, ra, rb, da, dbb)
        for who, r0, d, won in ((sid, ra, da, res['w'] == 0), (other['sid'], rb, dbb, res['w'] == 1)):
            db.execute('UPDATE pet_arena SET rating=?, best=GREATEST(best, ?), games=games+1, wins=wins+?, last=? WHERE sid=?',
                       (r0 + d, r0 + d, 1 if won else 0, t, who))
        return row
    row = store.transaction(run)
    out = _payload(row, sid)
    out['message'] = _result_line(out)
    return dict(ok=True, match=out)


def _result_line(m: dict) -> str:
    me = m.get('me')
    if m['kind'] == 'spar':
        head = 'Chưa có đối thủ hợp, bé đấu tập với Bé nhà Mây (không tính điểm).'
        return head
    if me is None:
        return ''
    if m['w'] == 2:
        res = '🤝 Hòa!'
    else:
        res = '🎉 Thắng!' if m['w'] == me else '💪 Thua rồi, lần sau nhé!'
    d = m['da'] if me == 0 else m['db']
    return res + (f' Điểm {d:+d}.' if m['kind'] == 'rank' else '')


def friend(store, token, state, data, ip='') -> dict:
    """🤝 A friendly battle against a friend's lineup (unrated)."""
    sid, display = _who(store, token)
    _gate(state, display)
    pid = data.get('pid')
    need(isinstance(pid, str) and 8 <= len(pid) <= 32, 'Chọn một người bạn nhé.', 'bad_friend')
    t = now()
    day = vn_day(t)

    def run(db):
        me = _sync(db, sid, state, display, ip_tag(ip), t)
        db.execute('SELECT 1 FROM pet_arena WHERE sid=? FOR UPDATE', (sid,))
        need(_count(db, sid, day, ('friend',)) < FRIEND_DAY, f'Hôm nay đã đấu {FRIEND_DAY} trận với bạn rồi.', 'limit', 409)
        other = db.execute('SELECT * FROM pet_arena WHERE pid=? AND size>0', (pid,)).fetchone()
        need(other and other['sid'] != sid, 'Bạn ấy chưa xếp đội ở đấu trường.', 'not_found', 404)
        if BANG_ONLY:   # 21/10: a friendly is between bang mates
            mine_b = bang_of(db, sid)
            need(mine_b, NO_BANG, 'no_bang', 403)
            need(bang_of(db, other['sid']) == mine_b, 'Chỉ đấu giao hữu với đồng đội cùng bang nhé.', 'not_mate', 403)
        else:
            from . import friends
            need(friends.are_friends(db, sid, other['sid']), 'Chỉ đấu giao hữu với bạn bè nhé.', 'not_friend', 403)
        mine, theirs = _j(me['snap'], []), _j(other['snap'], [])
        mid = new_id('f')
        res = B.battle(mine, theirs, B.seed_of(mid))
        return record(db, 'friend', mid, dict(sid=sid, name=display), dict(sid=other['sid'], name=other['name']), mine, theirs, res, t)
    row = store.transaction(run)
    out = _payload(row, sid)
    out['message'] = _result_line(out) + ' (giao hữu)'
    return dict(ok=True, match=out)


def npc(store, token, state, data, ip='') -> dict:
    """🎯 Thử thách: today's NPC lineup `stage`; the first win of each stage a day is a ⭐ of the week."""
    sid, display = _who(store, token)
    _gate(state, display)
    stage = data.get('stage')
    need(type(stage) is int and 0 <= stage < len(NPC_X), 'Chọn một thử thách nhé.', 'bad_stage')
    t = now()
    day, week = vn_day(t), vn_week(t)

    def run(db):
        me = _sync(db, sid, state, display, ip_tag(ip), t)
        db.execute('SELECT 1 FROM pet_arena WHERE sid=? FOR UPDATE', (sid,))
        need(_count(db, sid, day, ('npc',)) < NPC_DAY, f'Hôm nay đã thử {NPC_DAY} lần rồi. Mai thử tiếp nhé!', 'limit', 409)
        mine = _j(me['snap'], [])
        theirs = npc_today(sid, day, mine)[stage]
        mid = new_id('n')
        res = B.battle(mine, theirs, B.seed_of(mid))
        row = record(db, 'npc', mid, dict(sid=sid, name=display), dict(name=f'{NPC_OWNER} · {NPC_NAMES[stage]}'), mine, theirs, res, t)
        prog = _j(me['npc'], {})
        won = prog.get('won') if prog.get('d') == day and isinstance(prog.get('won'), list) else []
        star = res['w'] == 0 and stage not in won
        if star:
            won = sorted(set(won) | {stage})
            season_rating(db, week, sid, int(me['rating']))
            db.execute('UPDATE pet_arena_season SET stars=stars+1, at=? WHERE week=? AND sid=?', (t, week, sid))
        db.execute('UPDATE pet_arena SET npc=? WHERE sid=?', (_dump(dict(d=day, won=won)), sid))
        return row, star
    row, star = store.transaction(run)
    out = _payload(row, sid)
    out['message'] = ('🎉 Qua thử thách ' + NPC_NAMES[stage] + '! +1 ⭐' if star else
                      '🎉 Thắng!' if row['win'] == 0 else '🤝 Hòa!' if row['win'] == 2 else '💪 Chưa qua, luyện thêm rồi thử lại nhé!')
    out['star'] = star
    return dict(ok=True, match=out)


def replay(store, token, data) -> dict:
    mid = data.get('id')
    need(isinstance(mid, str) and 4 <= len(mid) <= 40, 'Không thấy trận này.', 'not_found', 404)
    sid = None
    if isinstance(token, str):
        sid, _ = store.resolve(token)
    with store.connect() as db:
        row = db.execute('SELECT * FROM pet_arena_matches WHERE id=?', (mid,)).fetchone()
        if not row:   # 🗄️ an old match moved to the archive (archive_matches): still a replay
            try:
                row = db.execute('SELECT * FROM pet_arena_matches_old WHERE id=?', (mid,)).fetchone()
            except Exception:  # noqa: BLE001 - a database before SCHEMA_VERSION 59
                row = None
    need(row, 'Không thấy trận này.', 'not_found', 404)
    return dict(ok=True, match=_payload(dict(row), sid))


def _names(db, sids: list) -> dict:
    """{sid: the name the boards show} (game/leaderboard.py privacy: hidden → 'Một người chơi')."""
    from .leaderboard import _VISIBLE
    if not sids:
        return {}
    marks = ','.join('?' * len(sids))
    rows = db.execute(f'SELECT a.sid AS sid, a.display AS display, ({_VISIBLE}) AS vis FROM accounts a LEFT JOIN leaderboard_players p '
                      f'ON p.sid=a.sid WHERE a.sid IN ({marks})', sids).fetchall()
    return {r['sid']: (str(r['display'])[:24] if r['vis'] and r['display'] else 'Một người chơi') for r in rows}


def ladder(store, token, data=None) -> dict:
    """🏆 The week's ladder: the players with MIN_GAMES ranked battles against MIN_OPP opponents, best rating first."""
    t = now()
    week = vn_week(t)
    sid = store.resolve(token)[0] if isinstance(token, str) else None
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(_LADDER + ' LIMIT 50', (week, MIN_GAMES, MIN_OPP)).fetchall()]
        names = _names(db, [r['sid'] for r in rows] + ([sid] if sid else []))
        mine = db.execute('SELECT * FROM pet_arena_season WHERE week=? AND sid=?', (week, sid)).fetchone() if sid else None
    from . import lb_titles as lbt
    lbt.ensure(store)
    try:
        weekly = lbt.board_view(store, lbt.ARENA, sid)
    except Exception:  # noqa: BLE001 - the ladder shows without its titles block
        weekly = None
    top = [dict(rank=i + 1, name=names.get(r['sid'], 'Một người chơi'), rating=r['rating'], w=r['w'], l=r['l'], d=r['d'], stars=r['stars'],
                me=r['sid'] == sid) for i, r in enumerate(rows)]
    me = None
    if mine:
        me = dict(rating=mine['rating'], w=mine['w'], l=mine['l'], d=mine['d'], opp=mine['opp'], stars=mine['stars'],
                  rank=next((x['rank'] for x in top if x['me']), None), need=max(0, MIN_GAMES - mine['w'] - mine['l'] - mine['d']),
                  need_opp=max(0, MIN_OPP - mine['opp']))
    return dict(ok=True, week=week, top=top, me=me, weekly=weekly, min_games=MIN_GAMES, min_opp=MIN_OPP)


_LADDER = ('SELECT s.sid, s.rating, s.w, s.l, s.d, s.stars, s.at FROM pet_arena_season s '
           'WHERE s.week=? AND s.w+s.l+s.d>=? AND s.opp>=? ORDER BY s.rating DESC, s.w DESC, s.at, s.sid')


def standings(db, t: float, n: int) -> list:
    """[(board, rank, sid, rating)] of the week of `t` (game/lb_titles.py: the boards' privacy, like the others)."""
    from .leaderboard import _VISIBLE
    rows = db.execute('SELECT s.sid, s.rating FROM pet_arena_season s LEFT JOIN accounts a ON a.sid=s.sid '
                      'LEFT JOIN leaderboard_players p ON p.sid=s.sid '
                      f'WHERE s.week=? AND s.w+s.l+s.d>=? AND s.opp>=? AND {_VISIBLE} ORDER BY s.rating DESC, s.w DESC, s.at, s.sid LIMIT ?',
                      (vn_week(t), MIN_GAMES, MIN_OPP, n)).fetchall()
    return [('arena', i + 1, r['sid'], int(r['rating'])) for i, r in enumerate(rows)]


def friends_list(store, token) -> dict:
    """The friends who set a lineup (pid, name, rating, power)."""
    sid, display = _who(store, token)
    with store.connect() as db:
        if BANG_ONLY:   # 21/10: the bang mates who set a lineup
            b = bang_of(db, sid)
            rows = [] if not b else db.execute("SELECT p.pid, p.name, p.rating, p.pw, p.size FROM bang_members m JOIN pet_arena p ON p.sid=m.sid "
                                               "WHERE m.bang=? AND m.status='in' AND m.sid<>? AND p.size>0 ORDER BY p.name LIMIT 100", (b, sid)).fetchall()
        else:
            rows = db.execute('SELECT p.pid, p.name, p.rating, p.pw, p.size FROM friends f JOIN pet_arena p ON p.sid=f.friend '
                              'WHERE f.sid=? AND p.size>0 ORDER BY p.name LIMIT 100', (sid,)).fetchall()
    return dict(ok=True, friends=[dict(pid=r['pid'], name=r['name'], rating=r['rating'], pw=r['pw'], size=r['size']) for r in rows])


def rules() -> dict:
    return dict(lineup=LINEUP_MAX, rank_day=RANK_DAY, friend_day=FRIEND_DAY, npc_day=NPC_DAY, pair_day=PAIR_DAY, min_games=MIN_GAMES,
                min_opp=MIN_OPP, account_days=ACCOUNT_DAYS, npc=list(NPC_NAMES))


OPS = ('view', 'lineup', 'fight', 'friend', 'friends', 'npc', 'replay', 'ladder', 'cup_join', 'cup_leave', 'cup_board',
       'war', 'war_pick', 'war_unpick', 'war_match', 'war_team', 'war_lineup', 'war_lineup_off',   # 👑 the leaders' lineup (game/pet_war.py)
       # ⚔️ Thách đấu bang (game/bang_challenge.py, owner 21/10): view, find, replay, roster, order, send, answer, cancel, mode
       'tc', 'tc_find', 'tc_match', 'tc_reg', 'tc_unreg', 'tc_order', 'tc_send', 'tc_answer', 'tc_cancel', 'tc_set')


OFF_TEXT = 'Đấu trường pet đang tạm nghỉ để bảo trì. Quay lại sau nhé!'


def off() -> bool:
    """🛑 MNL_PET_ARENA_OFF=1 (ops' kill switch, default unset: on): the 🐾 Đấu trường pet entry hides (content `off`) and
    every /api/arena/<op> is refused gracefully. Nothing changes in any save (the arena never writes one); the weekly
    cup and the bang war still play at their time (housekeeping), lineup snapshots still follow the pets."""
    return os.environ.get('MNL_PET_ARENA_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def act(store, token, op: str, data: dict, state, ip: str = '') -> dict:
    """POST /api/arena/<op> (server.py). ArenaError → the caller's error answer."""
    need(not off(), OFF_TEXT, 'off', 503)
    need(op in OPS, 'Thao tác không hợp lệ.', 'unknown', 404)
    need(isinstance(data, dict), 'Thông tin không hợp lệ.', 'bad')
    if op == 'view':
        return view(store, token, state, ip)
    # 21/10 owner: "chỉ mở cho các bang hội đánh nhau thôi": no 1v1 ranked or friendly fights while BANG_ONLY
    need(not (BANG_ONLY and op in ('fight', 'friend', 'friends')), 'Đấu trường giờ dành cho bang đánh với bang: vào 🛡️ Bang chiến nhé.', 'bang_only', 409)
    if BANG_ONLY and (op in ('lineup', 'npc') or (op.startswith('cup_') and op != 'cup_board')):
        # 21/10: only bang members play, once their bang holds its 🏝️ island; the weekly cup (open to the whole town) is
        # closed while BANG_ONLY
        need(not op.startswith('cup_'), 'Giải tuần đang đóng: đấu trường giờ chỉ dành cho bang.', 'cup_closed', 409)
        need_bang(store, _who(store, token)[0], island=True)
    if op in ('war_pick', 'war_team', 'war_lineup'):   # 🏝️ a bang member's pick or a leader's lineup: the island first (game/bang_pets.py can_pick refuses too; other teams: pet_war)
        with store.connect() as db:
            sid = _who(store, token)[0]
            b = bang_of(db, sid) if sid else None
            need(not b or island_lock(db, sid, b) is None, NO_ISLAND, 'no_island', 403)
    if op == 'lineup':
        return set_lineup(store, token, state, data, ip)
    if op == 'fight':
        return fight(store, token, state, data, ip)
    if op == 'friend':
        return friend(store, token, state, data, ip)
    if op == 'friends':
        return friends_list(store, token)
    if op == 'npc':
        return npc(store, token, state, data, ip)
    if op == 'replay':
        return replay(store, token, data)
    if op == 'ladder':
        return ladder(store, token, data)
    if op.startswith('tc'):
        from . import bang_challenge
        return bang_challenge.act(store, token, op, data, state, ip)
    from . import pet_cup, pet_war
    if op.startswith('cup_'):
        return pet_cup.act(store, token, op, data, state, ip)
    return pet_war.act(store, token, op, data, state, ip)


KEEP_MATCH_DAYS = 30           # pet_arena_matches older than this go to pet_arena_matches_old (a replay still finds them)
ARCHIVE_EVERY = 600.0
ARCHIVE_BATCH = 500
ARCHIVE_ROUNDS = 4
_ARCH = dict(at=0.0)


def archive_matches(store, t: float | None = None) -> int:
    """Matches older than KEEP_MATCH_DAYS into pet_arena_matches_old (SCHEMA_VERSION 59), a few batches of
    ARCHIVE_BATCH, each its own transaction (copied, then removed: game/archive.py move_rows). Recent matches, the
    day's and the week's counts (met_today, the season's opponents, the cup's rounds) stay where they are read."""
    from . import archive as ar
    t = now() if t is None else t
    moved = 0
    for _ in range(ARCHIVE_ROUNDS):
        def batch(db):
            ids = [r['id'] for r in db.execute('SELECT id FROM pet_arena_matches WHERE at<? ORDER BY at LIMIT ? FOR UPDATE SKIP LOCKED',
                                               (t - KEEP_MATCH_DAYS * DAY, ARCHIVE_BATCH)).fetchall()]
            return ar.move_rows(db, 'pet_arena_matches', 'pet_arena_matches_old', ids, t)
        n = store.transaction(batch)
        moved += n
        if n < ARCHIVE_BATCH:
            break
    return moved


def run_housekeeping(store) -> None:
    """server.py housekeeping (every 30 s, one process): the weekly cup and the bang war when their time comes; old
    matches into the archive every ARCHIVE_EVERY seconds outside the peak hours."""
    import sys
    from . import archive as ar
    from . import pet_cup, pet_war
    t = now()
    if t - _ARCH['at'] >= ARCHIVE_EVERY and not ar.peak(t):
        _ARCH['at'] = t
        try:
            n = archive_matches(store, t)
            if n:
                sys.stderr.write(f'[pet_arena] archived {n} matches\n')
        except Exception as e:  # noqa: BLE001 - an older schema: no archive table yet
            sys.stderr.write(f'[pet_arena] archive: {type(e).__name__}\n')
    from . import bang_challenge
    for name, fn in (('cup', pet_cup.run_due), ('war', pet_war.run_due), ('chal', bang_challenge.run_due),
                     ('war_remind', pet_war.remind_due)):   # ⏰ the war's reminder, the hour before the lock
        try:
            fn(store)
        except Exception as e:  # noqa: BLE001 - housekeeping must never take the server down
            sys.stderr.write(f'[pet_arena] {name}: {type(e).__name__}: {e}\n')
