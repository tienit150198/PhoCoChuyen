"""🛡️ Bang chiến pet: team against team (owner 19/10, verbatim: "pet thì mỗi bang đến giờ sẽ chọn các pet ra đánh với nhau,
đánh 5v5 và ngẫu nhiên ấy, mỗi người chọn 1 pet xong đánh nhau thôi. sắp xếp thứ tự đánh nhau, ai thắng nhiều thì vào
vòng trong, kiểu vậy á").

Teams are generic: (team_kind, team_id). A kind is a TeamProvider registered here (`register`): a Bang is kind 'bang',
plugged in by the bang module (its own tables), so this file does not depend on it. Without a provider nobody has a
team and the war simply has no entrants.

The weekly war (start(): Saturday WAR_HOUR, outside the 17:30–20:00 peak; PET_WAR_DOW / PET_WAR_HOUR / PET_WAR_MIN):
* Until LOCK_MIN minutes before the start, each member of a team may field exactly one pet (`war_pick`; again to
  change it, `war_unpick` to leave the slot). A team fields at most SIZE (5), first come first in; the provider may
  refuse a member (`can_pick`). Every jr_pet_* command refreshes the fielded pet's snapshot (on_pet_commit).
* At the lock (server.py housekeeping, or the first page that looks after it) the war is played at once, on the
  server, exactly once (an advisory lock and the pet_war row): the teams with at least one pet fielded enter a single-
  elimination bracket (seeded by the teams' rating across weeks, byes to the best seeds), round r starting at
  start + (r − 1)·GAP. In a match the two lineups are shuffled from the match's seed (the order of Trận 1…5 is shown)
  and paired: five 1-vs-1 duels (game/pet_battle.py). More duel wins advances ("ai thắng nhiều thì vào vòng trong");
  a missing pet loses its duel (both missing: nobody wins it); a tie goes to the HP left, then the better seed.
* Everybody sees the same: results are fixed at the lock, but a match is shown only from its start, its duels one
  by one (DUEL_SECS each, `war_match`), the bracket's score once the match is over.
* The team ladder: pet_team_ladder (the week: wins, losses, the round reached, points) and pet_team_rating (Elo across
  weeks). Titles (game/lb_titles.py board 'pet_war'): the champion's fighters 🏆 Bang vô địch đấu pet, the runner-up's
  🥈 Á quân bang chiến pet, for a week. Nothing else: no xu.
* 🏋️ A team's training ground (the bang's "Sân luyện pet") is read from the provider (`facility`, key TRAINING_KEY):
  its level adds TRAINING_PCT % (at most TRAINING_MAX) to its fighters' stats in this war only.

API for other modules (the Bang agent): register(kind, provider), team_match(a, b, key), standings(db, t), ladder(db,
kind, week), team_rating(db, kind, id), training_bonus(db, kind, id).
"""
from __future__ import annotations

import hashlib
import os

from . import pet_arena as A
from . import pet_battle as B

SIZE = 5
LOCK_MIN = 10
GAP = 300                  # seconds between the starts of two rounds
DUEL_SECS = 30             # each duel of a match is shown this long after the one before
LOCK_KEY = 17825
TRAINING_KEY = 'san_luyen_pet'
TRAINING_PCT, TRAINING_MAX = 1, 5
K_TEAM = 32
PTS_WIN, PTS_CHAMP = 3, 5


def _env_int(name: str, default: int, lo: int, hi: int) -> int:
    try:
        v = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return v if lo <= v <= hi else default


def start_of(t: float) -> float:
    """The start of the war of the Vietnam week of `t` (Sunday 20:00 by default: owner 21/10 "bang chiến diễn ra chủ nhật hằng tuần, 8h tối")."""
    from .wedding_live import week_start
    return (week_start(t) + _env_int('PET_WAR_DOW', 6, 0, 6) * 86400 + _env_int('PET_WAR_HOUR', 20, 0, 23) * 3600
            + _env_int('PET_WAR_MIN', 0, 0, 59) * 60)


def lock_of(t: float) -> float:
    return start_of(t) - LOCK_MIN * 60


# ---------------------------------------------------------------- teams (providers)
class TeamProvider:
    """What a team kind tells the war. Override what applies; every method takes the open db (any transaction)."""
    kind = ''
    label = 'Đội'

    def team_of(self, db, sid: str):
        """(team_id, team name) of the player's team, or None."""
        return None

    def name(self, db, team_id: str) -> str:
        return str(team_id)

    def can_pick(self, db, team_id: str, sid: str) -> bool:
        """May this member field a pet (e.g. only members who joined before the week)?"""
        return True

    def facility(self, db, team_id: str, key: str) -> int:
        """The level of a team facility (TRAINING_KEY: the training ground), 0 without one."""
        return 0


PROVIDERS: dict = {}


def register(kind: str, provider: TeamProvider) -> None:
    """Plug a team kind in (the bang module: register('bang', BangTeams()))."""
    provider.kind = kind
    PROVIDERS[kind] = provider


def unregister(kind: str) -> None:
    PROVIDERS.pop(kind, None)


class DemoTeams(TeamProvider):
    """MNL_PET_WAR_DEMO=1 (local and staging only, never production): every arena player belongs to one of six demo
    teams by a hash of their save id, so the war can be played and looked at before the bangs exist."""
    label = 'Đội'
    NAMES = ('Đội Mây', 'Đội Gió', 'Đội Mưa', 'Đội Nắng', 'Đội Sao', 'Đội Trăng')

    def team_of(self, db, sid):
        i = int(hashlib.sha256(('demo-team|' + sid).encode()).hexdigest()[:8], 16) % len(self.NAMES)
        return f't{i}', self.NAMES[i]

    def name(self, db, team_id):
        try:
            return self.NAMES[int(team_id[1:])]
        except (ValueError, IndexError):
            return team_id


def _providers() -> dict:
    if os.environ.get('MNL_PET_WAR_DEMO') == '1' and 'demo' not in PROVIDERS:
        register('demo', DemoTeams())
    return PROVIDERS


def team_of(db, sid: str):
    """(kind, team_id, name, provider label) of the player's team, or None."""
    for kind, p in _providers().items():
        try:
            got = p.team_of(db, sid)
        except Exception:  # noqa: BLE001 - a provider's fault never breaks the arena
            got = None
        if got:
            return kind, str(got[0]), str(got[1])[:40], p.label
    return None


def training_bonus(db, kind: str, team_id: str) -> int:
    """% added to a team's fighters in a war: TRAINING_PCT a level of its training ground, at most TRAINING_MAX."""
    p = _providers().get(kind)
    if not p:
        return 0
    try:
        lv = int(p.facility(db, team_id, TRAINING_KEY) or 0)
    except Exception:  # noqa: BLE001
        lv = 0
    return max(0, min(TRAINING_MAX, lv * TRAINING_PCT))


# ---------------------------------------------------------------- one team match (the generic API)
def team_match(team_a: dict, team_b: dict, key: str, size: int = SIZE) -> dict:
    """Team against team: {kind, id, name, members: [{sid, name, f: fighter}], tb: training %} each. The members of
    each are shuffled from the seed of `key` (the order of the duels), then paired one by one: `size` 1-vs-1 duels.
    Returns {w: 0 | 1 | 2, wa, wb, hp: [a, b] (HP shares left, the tie-break), duels: [{i, a, b, w, sc}]} where a/b are
    the members ({sid, name, f}) or None (nobody fielded: that duel is lost; both missing, nobody wins it)."""
    rng = B.Rng(B.seed_of(key, 'order'))
    la = rng.shuffle(list(team_a.get('members') or [])[:size])
    lb = rng.shuffle(list(team_b.get('members') or [])[:size])
    duels, wa, wb, ha, hb = [], 0, 0, 0, 0
    for i in range(size):
        ma = la[i] if i < len(la) else None
        mb = lb[i] if i < len(lb) else None
        d = dict(i=i, a=ma, b=mb)
        if ma and mb:
            fa, fb = dict(ma['f'], tb=team_a.get('tb') or 0), dict(mb['f'], tb=team_b.get('tb') or 0)
            res = B.battle([fa], [fb], B.seed_of(key, f'duel{i}'))
            d.update(w=res['w'], sc=res['sc'])
        else:
            d.update(w=0 if ma else 1 if mb else 2, sc=[1000 if ma else 0, 1000 if mb else 0])
        wa += d['w'] == 0
        wb += d['w'] == 1
        ha += d['sc'][0]
        hb += d['sc'][1]
        duels.append(d)
    w = 0 if wa > wb else 1 if wb > wa else 0 if ha > hb else 1 if hb > ha else 2
    return dict(w=w, wa=wa, wb=wb, hp=[ha, hb], duels=duels)


def seed_order(n: int) -> list:
    """Bracket positions of seeds 1…n (a power of two): 1 meets n, the best two only in the final."""
    order = [1]
    while len(order) < n:
        m = len(order) * 2 + 1
        order = [x for s in order for x in (s, m - s)]
    return order


# ---------------------------------------------------------------- picks
def _week_open(t: float) -> tuple:
    """(week, start, lock) of the war players can field pets for now: this week's until its lock, else none."""
    week = A.vn_week(t)
    return week, start_of(t), lock_of(t)


def act(store, token, op, data, state, ip=''):
    if op == 'war':
        return view(store, token)
    if op == 'war_match':
        return match_view(store, token, data)
    A.need(op in ('war_pick', 'war_unpick'), 'Thao tác không hợp lệ.', 'unknown', 404)
    sid, display = A._who(store, token)
    A._gate(state, display)
    t = A.now()
    week, start, lock = _week_open(t)
    A.need(t < lock, 'Đã khóa đội hình bang chiến tuần này. Tuần sau chọn sớm nhé!', 'locked', 409)

    def run(db):
        team = team_of(db, sid)
        A.need(team, 'Vào một bang để cùng ra trận nhé.', 'no_team', 409)
        kind, tid, tname, _ = team
        db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (LOCK_KEY, f'{week}|{kind}|{tid}'))
        if op == 'war_unpick':
            db.execute('DELETE FROM pet_war_picks WHERE week=? AND sid=?', (week, sid))
            return dict(ok=True, message='Đã rút bé khỏi đội hình.')
        pid = data.get('pet')
        A.need(isinstance(pid, str), 'Chọn một bé nhé.', 'bad_pet')
        pet = next((p for p in A.candidates(state) if p['id'] == pid), None)
        A.need(pet, 'Bé này không ở nhà hay trại nuôi.', 'not_owned', 409)
        prov = _providers()[kind]
        A.need(prov.can_pick(db, tid, sid), 'Bạn chưa được ra trận cho bang tuần này.', 'not_allowed', 403)
        n = len(current_picks(db, week, kind, tid, exclude=sid))   # only members still in the team count (leavers' picks never block)
        A.need(n < SIZE, f'Đội đã đủ {SIZE} bé rồi.', 'full', 409)
        f = A.fighter(state, pet)
        db.execute('INSERT INTO pet_war_picks(week, sid, team_kind, team_id, name, pet, snap, at) VALUES(?,?,?,?,?,?,?,?) '
                   'ON CONFLICT (week, sid) DO UPDATE SET team_kind=EXCLUDED.team_kind, team_id=EXCLUDED.team_id, name=EXCLUDED.name, '
                   'pet=EXCLUDED.pet, snap=EXCLUDED.snap', (week, sid, kind, tid, display[:24], pid, A._dump(f), t))
        return dict(ok=True, message=f'🛡️ {pet["n"]} sẽ ra trận cho {tname}!')
    return store.transaction(run)


def current_picks(db, week: str, kind: str, tid: str, exclude: str = '') -> list:
    """The team's picks of `week` (oldest first) whose player is still in that team now (a pick of someone who left, was
    kicked or whose team is hidden does not count: the provider's team_of decides, as at the lock)."""
    rows = db.execute('SELECT sid FROM pet_war_picks WHERE week=? AND team_kind=? AND team_id=? AND sid<>? ORDER BY at, sid',
                      (week, kind, tid, exclude)).fetchall()
    out = []
    for r in rows:
        now_team = team_of(db, r['sid'])
        if now_team and (now_team[0], now_team[1]) == (kind, tid):
            out.append(r['sid'])
    return out


def on_pet_commit(db, sid: str, after: dict) -> None:
    """The fielded pet's snapshot follows the pet until the lineups lock (game/pet_arena.py on_pet_commit)."""
    t = A.now()
    if t >= lock_of(t):
        return
    week = A.vn_week(t)
    r = db.execute('SELECT pet, snap FROM pet_war_picks WHERE week=? AND sid=?', (week, sid)).fetchone()
    if not r:
        return
    pet = next((p for p in A.candidates(after) if p['id'] == r['pet']), None)
    if pet:
        snap = A._dump(A.fighter(after, pet))
        if snap != r['snap']:   # nothing changed (most jr_pet_* commands): no write
            db.execute('UPDATE pet_war_picks SET snap=? WHERE week=? AND sid=?', (snap, week, sid))


# ---------------------------------------------------------------- the war
def run_due(store, t: float | None = None) -> bool:
    t = A.now() if t is None else t
    if t < lock_of(t):
        return False
    week = A.vn_week(t)
    with store.connect() as db:
        if db.execute('SELECT 1 FROM pet_war WHERE week=?', (week,)).fetchone():
            return False
    return bool(store.transaction(lambda db: play(db, week, t)))


def _team_rating(db, kind: str, tid: str) -> int:
    r = db.execute('SELECT rating FROM pet_team_rating WHERE team_kind=? AND team_id=?', (kind, tid)).fetchone()
    return int(r['rating']) if r else A.START


def play(db, week: str, t: float) -> bool:
    """Lock the lineups of `week` and play its whole bracket, once."""
    db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (LOCK_KEY, week))
    if db.execute('SELECT 1 FROM pet_war WHERE week=?', (week,)).fetchone():
        return False
    start = start_of(t)
    teams = {}
    for r in db.execute('SELECT * FROM pet_war_picks WHERE week=? ORDER BY at, sid', (week,)).fetchall():
        key = (r['team_kind'], r['team_id'])
        now_team = team_of(db, r['sid'])
        if not now_team or (now_team[0], now_team[1]) != key:   # left the team since: their pick does not count
            continue
        f = B.clean(A._j(r['snap'], {}))
        if not f:
            continue
        tm = teams.setdefault(key, dict(kind=key[0], id=key[1], name=now_team[2], members=[]))
        if len(tm['members']) < SIZE:
            tm['members'].append(dict(sid=r['sid'], name=r['name'], f=f))
    for tm in teams.values():
        tm['tb'] = training_bonus(db, tm['kind'], tm['id'])
        tm['rating'] = _team_rating(db, tm['kind'], tm['id'])
    entrants = sorted(teams.values(), key=lambda x: (-x['rating'], x['name'], x['kind'], x['id']))
    if len(entrants) < 2:
        db.execute("INSERT INTO pet_war(week, status, start, n, rounds, at) VALUES(?, 'cancelled', ?, ?, 0, ?)", (week, start, len(entrants), t))
        return True
    size = 2
    while size < len(entrants):
        size *= 2
    seeds = {i + 1: tm for i, tm in enumerate(entrants)}
    for i, tm in seeds.items():
        tm['seed'] = i
    alive = [seeds.get(s) for s in seed_order(size)]       # None: a bye
    rounds = size.bit_length() - 1
    played = []
    champ = second = None
    for rd in range(1, rounds + 1):
        nxt = []
        at = start + (rd - 1) * GAP
        for slot in range(len(alive) // 2):
            a, b = alive[2 * slot], alive[2 * slot + 1]
            if a is None or b is None:
                win = a or b
                nxt.append(win)
                if win:
                    db.execute('INSERT INTO pet_war_matches(week, rd, slot, a_kind, a_id, a_name, win, start, data) VALUES(?,?,?,?,?,?,0,?,?)',
                               (week, rd, slot, win['kind'], win['id'], win['name'], at, A._dump(dict(bye=True))))
                continue
            key = f'w{week}-{rd}-{slot}'
            res = team_match(a, b, key)
            w = res['w'] if res['w'] != 2 else (0 if a['seed'] < b['seed'] else 1)
            win, lose = (a, b) if w == 0 else (b, a)
            nxt.append(win)
            duels = [dict(i=d['i'], w=d['w'], seed=key, a=dict(sid=d['a']['sid'], name=d['a']['name'], f=d['a']['f']) if d['a'] else None,
                          b=dict(sid=d['b']['sid'], name=d['b']['name'], f=d['b']['f']) if d['b'] else None) for d in res['duels']]
            db.execute('INSERT INTO pet_war_matches(week, rd, slot, a_kind, a_id, a_name, b_kind, b_id, b_name, win, wa, wb, start, data) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (week, rd, slot, a['kind'], a['id'], a['name'], b['kind'], b['id'], b['name'], w, res['wa'], res['wb'], at,
                        A._dump(dict(duels=duels, tb=[a['tb'], b['tb']], hp=res['hp'], tie=res['w'] == 2, engine=B.ENGINE))))
            played.append((rd, a, b, w))
            for tm, me in ((a, w == 0), (b, w == 1)):
                tm['w'] = tm.get('w', 0) + me
                tm['l'] = tm.get('l', 0) + (not me)
                tm['best'] = rd
            if rd == rounds:
                champ, second = win, lose
        alive = nxt
    if champ is None:   # cannot happen with ≥ 2 entrants (byes are all in round 1), kept safe
        champ = alive[0]
    # team ratings and the week's ladder (written now; the views show them once the war is over)
    for rd, a, b, w in played:
        da = A.elo(a['rating'], b['rating'], 1.0 if w == 0 else 0.0, K_TEAM)
        db_ = A.elo(b['rating'], a['rating'], 1.0 if w == 1 else 0.0, K_TEAM)
        a['rating'] += da
        b['rating'] += db_
    for tm in entrants:
        is_champ = tm is champ
        pts = PTS_WIN * tm.get('w', 0) + (PTS_CHAMP if is_champ else 0)
        best = rounds + 1 if is_champ else tm.get('best', 0)
        db.execute('INSERT INTO pet_team_ladder(week, team_kind, team_id, name, rating, w, l, best, pts, champ, at) VALUES(?,?,?,?,?,?,?,?,?,?,?) '
                   'ON CONFLICT (week, team_kind, team_id) DO UPDATE SET name=EXCLUDED.name, rating=EXCLUDED.rating, w=EXCLUDED.w, l=EXCLUDED.l, '
                   'best=EXCLUDED.best, pts=EXCLUDED.pts, champ=EXCLUDED.champ, at=EXCLUDED.at',
                   (week, tm['kind'], tm['id'], tm['name'][:40], tm['rating'], tm.get('w', 0), tm.get('l', 0), best, pts, 1 if is_champ else 0, t))
        db.execute('INSERT INTO pet_team_rating(team_kind, team_id, name, rating, wars, titles, at) VALUES(?,?,?,?,1,?,?) '
                   'ON CONFLICT (team_kind, team_id) DO UPDATE SET name=EXCLUDED.name, rating=EXCLUDED.rating, wars=pet_team_rating.wars+1, '
                   'titles=pet_team_rating.titles+EXCLUDED.titles, at=EXCLUDED.at',
                   (tm['kind'], tm['id'], tm['name'][:40], tm['rating'], 1 if is_champ else 0, t))
    data = dict(size=size, teams=[dict(seed=tm['seed'], kind=tm['kind'], id=tm['id'], name=tm['name'], n=len(tm['members']), tb=tm['tb'])
                                  for tm in entrants],
                champ=[m['sid'] for m in champ['members']], second=[m['sid'] for m in second['members']] if second else [],
                second_team=dict(kind=second['kind'], id=second['id'], name=second['name']) if second else None,
                end=start + (rounds - 1) * GAP + SIZE * DUEL_SECS)
    db.execute("INSERT INTO pet_war(week, status, start, n, rounds, champ_kind, champ_id, champ_name, data, at) VALUES(?, 'done', ?, ?, ?, ?, ?, ?, ?, ?)",
               (week, start, len(entrants), rounds, champ['kind'], champ['id'], champ['name'][:40], A._dump(data), t))
    return True


def end_of(row) -> float:
    data = A._j(row['data'], {})
    return float(data.get('end') or row['start'])


def standings(db, t: float) -> list:
    """[(board, rank, sid, score)]: the fighters of the champion of the latest war over by `t` (ranks 1…5) and of the
    runner-up (6…10) (game/lb_titles.py board 'pet_war')."""
    for row in db.execute("SELECT * FROM pet_war WHERE status='done' ORDER BY week DESC LIMIT 2").fetchall():
        if end_of(row) > t:
            continue
        data = A._j(row['data'], {})
        out = [('pet_war', i + 1, s, 2) for i, s in enumerate((data.get('champ') or [])[:SIZE])]
        out += [('pet_war', SIZE + i + 1, s, 1) for i, s in enumerate((data.get('second') or [])[:SIZE])]
        return out
    return []


def ladder(db, kind: str | None = None, week: str | None = None, t: float | None = None, n: int = 20) -> list:
    """The team ladder of a war over (the latest by default): [{rank, kind, id, name, w, l, best, pts, rating, champ}]."""
    t = A.now() if t is None else t
    if week is None:
        rows = db.execute("SELECT * FROM pet_war WHERE status='done' ORDER BY week DESC LIMIT 2").fetchall()
        row = next((r for r in rows if end_of(r) <= t), None)
        if not row:
            return []
        week = row['week']
    q = 'SELECT * FROM pet_team_ladder WHERE week=?' + (' AND team_kind=?' if kind else '') + ' ORDER BY champ DESC, best DESC, pts DESC, rating DESC, name LIMIT ?'
    rows = db.execute(q, (week, kind, n) if kind else (week, n)).fetchall()
    return [dict(rank=i + 1, kind=r['team_kind'], id=r['team_id'], name=r['name'], w=r['w'], l=r['l'], best=r['best'], pts=r['pts'],
                 rating=r['rating'], champ=bool(r['champ'])) for i, r in enumerate(rows)]


def team_rating(db, kind: str, tid: str) -> dict | None:
    r = db.execute('SELECT * FROM pet_team_rating WHERE team_kind=? AND team_id=?', (kind, tid)).fetchone()
    return dict(rating=r['rating'], wars=r['wars'], titles=r['titles']) if r else None


# ---------------------------------------------------------------- views
ROUND_NAMES = {1: 'Chung kết', 2: 'Bán kết', 3: 'Tứ kết'}


def round_name(rd: int, rounds: int) -> str:
    return ROUND_NAMES.get(rounds - rd + 1) or f'Vòng {rd}'


def summary(store, sid: str, t: float) -> dict:
    """The arena home's card: when the war is, your team and your pick."""
    week, start, lock = _week_open(t)
    with store.connect() as db:
        team = team_of(db, sid)
        pick = db.execute('SELECT pet, snap FROM pet_war_picks WHERE week=? AND sid=?', (week, sid)).fetchone()
        n = len(current_picks(db, week, team[0], team[1])) if team else 0
        done = db.execute('SELECT * FROM pet_war WHERE week=?', (week,)).fetchone()
    phase = 'pick' if t < lock else 'none' if not done or done['status'] != 'done' else 'live' if t < end_of(done) else 'done'
    return dict(week=week, start=start, lock=lock, phase=phase, team=dict(kind=team[0], id=team[1], name=team[2], label=team[3]) if team else None,
                pick=A.pet_view(A._j(pick['snap'], {})) | dict(id=pick['pet']) if pick else None, n=n, size=SIZE)


def view(store, token) -> dict:
    """The war page: phase, your team's lineup, the bracket (each match from its start), the champion, the ladder."""
    sid = store.resolve(token)[0] if isinstance(token, str) else None
    t = A.now()
    week, start, lock = _week_open(t)
    with store.connect() as db:
        team = team_of(db, sid) if sid else None
        war = db.execute('SELECT * FROM pet_war WHERE week=?', (week,)).fetchone()
        picks = []
        if team:
            still = set(current_picks(db, week, team[0], team[1]))
            picks = [dict(r) for r in db.execute('SELECT sid, name, pet, snap FROM pet_war_picks WHERE week=? AND team_kind=? AND team_id=? ORDER BY at, sid',
                                                 (week, team[0], team[1])).fetchall() if r['sid'] in still]
        matches = [dict(r) for r in db.execute('SELECT week, rd, slot, a_name, b_name, a_kind, a_id, b_kind, b_id, win, wa, wb, start, data '
                                               'FROM pet_war_matches WHERE week=? ORDER BY rd, slot', (week,)).fetchall()] if war else []
        board = ladder(db, t=t)
        last = db.execute("SELECT * FROM pet_war WHERE status='done' AND week<? ORDER BY week DESC LIMIT 1", (week,)).fetchone()
    phase = 'pick' if t < lock else 'wait' if not war else 'cancelled' if war['status'] != 'done' else 'live' if t < end_of(war) else 'done'
    bracket = []
    for m in matches:
        if m['start'] > t:
            state = 'wait'
        elif m['start'] + SIZE * DUEL_SECS > t and m['b_name']:
            state = 'live'
        else:
            state = 'done'
        bye = not m['b_name']
        # who plays a later round is known once the round before is over (never shown sooner)
        known = m['rd'] == 1 or t >= m['start'] - GAP + SIZE * DUEL_SECS
        mine = bool(team) and known and ((m['a_kind'], m['a_id']) == team[:2] or (m['b_kind'], m['b_id']) == team[:2])
        bracket.append(dict(rd=m['rd'], slot=m['slot'], a=m['a_name'] if known else '', b=(m['b_name'] or '') if known else '', bye=bye and known,
                            start=m['start'], state=state, mine=mine,
                            **(dict(win=m['win'], wa=m['wa'], wb=m['wb']) if state == 'done' else {})))
    rounds = war['rounds'] if war else 0
    out = dict(ok=True, week=week, start=start, lock=lock, now=t, phase=phase, size=SIZE, duel_secs=DUEL_SECS, gap=GAP,
               team=dict(kind=team[0], id=team[1], name=team[2], label=team[3]) if team else None,
               picks=[dict(name=p['name'], me=p['sid'] == sid, pet=A.pet_view(A._j(p['snap'], {}))) for p in picks],
               rounds=[dict(rd=r, name=round_name(r, rounds)) for r in range(1, rounds + 1)], bracket=bracket,
               champ=war['champ_name'] if war and phase == 'done' else None, ladder=board,
               last=dict(week=last['week'], champ=last['champ_name']) if last else None, kinds=sorted(_providers()))
    return out


def match_view(store, token, data) -> dict:
    """One match of the war, once it has started: the five duels in their order, each with its log."""
    rd, slot = data.get('rd'), data.get('slot')
    A.need(type(rd) is int and type(slot) is int and 1 <= rd <= 12 and 0 <= slot < 4096, 'Không thấy trận này.', 'not_found', 404)
    week = data.get('week') if isinstance(data.get('week'), str) and len(data['week']) <= 10 else A.vn_week(A.now())
    with store.connect() as db:
        m = db.execute('SELECT * FROM pet_war_matches WHERE week=? AND rd=? AND slot=?', (week, rd, slot)).fetchone()
    A.need(m, 'Không thấy trận này.', 'not_found', 404)
    t = A.now()
    A.need(m['start'] <= t, 'Trận này chưa tới giờ.', 'not_yet', 409)
    d = A._j(m['data'], {})
    duels = []
    shown = int((t - m['start']) // DUEL_SECS) + 1        # duels revealed so far (all once the match is over)
    for x in d.get('duels') or []:
        if x['i'] >= shown:
            break
        side = lambda s: dict(name=s['name'], pets=[A.pet_view(s['f'])]) if s else dict(name='Vắng mặt', pets=[])
        one = dict(i=x['i'], w=x['w'], sides=[side(x.get('a')), side(x.get('b'))])
        if x.get('a') and x.get('b') and d.get('engine') == B.ENGINE:
            tb = d.get('tb') or [0, 0]
            res = B.battle([dict(x['a']['f'], tb=tb[0])], [dict(x['b']['f'], tb=tb[1])], B.seed_of(x['seed'], f'duel{x["i"]}'))
            one.update(ev=res['ev'], hp=res['hp'], max=res['max'])
        duels.append(one)
    over = t >= m['start'] + SIZE * DUEL_SECS
    return dict(ok=True, week=week, rd=rd, slot=slot, a=m['a_name'], b=m['b_name'], start=m['start'], duel_secs=DUEL_SECS, duels=duels,
                total=len(d.get('duels') or []), over=over, **(dict(win=m['win'], wa=m['wa'], wb=m['wb']) if over else {}))
