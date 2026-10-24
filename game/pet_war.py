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
* 👑 The team's leaders may choose the lineup instead (owner: "bang chủ được quyền chọn danh sách thú để xuất
  chiến nhé"; the provider's `can_lead`: a bang's Trưởng lão and up, as for the ⚔️ Thách đấu roster). `war_team` lists
  the members with their pets (each member's save read only, the strongest first: the suggestion), `war_lineup` saves
  1…SIZE member + pet pairs (one pet a member, the member's own pet at home or in the kennel, `can_pick` and the
  provider's island rule as for `war_pick`): it replaces the team's picks of the week, under the same team lock, with
  the same snapshots (they follow the pets until the lock; a pet gone meanwhile fights as its last snapshot, as a
  member's own pick does). A marker row in pet_war_picks (sid LEAD + kind|id, no pet, never a member: every reader
  skips it, an older build too since no team owns that sid) says the lineup is the leaders' own: members can no longer
  pick or leave it themselves (`lead_set`) until a leader hands it back (`war_lineup_off`, the picks kept). The team
  gets a line in its log and chat group naming the members picked. No table or column added.
* 🛡️ The team's card (owner: "có nơi nào đó cho mọi người ở bang thấy sự kiện bang chiến cuối tuần đi"; `team_card`,
  the bang page's home tab): when, the lock, the phase (pick / locked / live / done / cancelled), the lineup as it
  stands (who fields which pet, who chose it), what this member may do, the team's matches once known and its result.
  An hour before the lock (REMIND_SECS) the housekeeping reminds every team that can play (`remind_due`, the
  provider's `remind`: once a team a week, its own log row being the marker).
* At the lock (server.py housekeeping, or the first page that looks after it) the war is played at once, on the
  server, exactly once (an advisory lock and the pet_war row): the teams with at least one pet fielded enter a single-
  elimination bracket (seeded by the teams' rating across weeks, byes to the best seeds), round r starting at
  start + (r − 1)·GAP. In a match the two lineups are shuffled from the match's seed (the order of Trận 1…5 is shown)
  and paired: five 1-vs-1 duels (game/pet_battle.py). More duel wins advances ("ai thắng nhiều thì vào vòng trong");
  a missing pet loses its duel (both missing: nobody wins it); a tie goes to the HP left, then the better seed.
* 🥉 Tranh hạng 3 (owner 25/10): with two real semi-finals (4 teams or more) their losers play once more, at the same
  time as the final, by the same rules. Stored as one more pet_war_matches row, rd = rounds + 1, slot 0 (data.third;
  pet_war.rounds stays the bracket's rounds, no schema change). Its winner gets PTS_WIN like any win (no champion
  bonus), both teams' Elo moves, `best` stays the semi-final; pet_war.data names third_team / fourth_team (third:
  the fighters' sids). With 3 teams one semi-final is a bye: its real semi-final's loser is third, no match.
  An older build (2.6.7) reading the row: its bracket draws only the rounds 1…rounds (war.rounds), so the row is not
  drawn there; its team card lists it as "Vòng <rounds + 1>" with the score; its ladder orders the two by points then
  rating (no third/fourth flag); its titles ignore ranks 11…15. Nothing crashes.
* Everybody sees the same: results are fixed at the lock, but a match is shown only from its start, its duels one
  by one (DUEL_SECS each, `war_match`), the bracket's score once the match is over.
* The team ladder: pet_team_ladder (the week: wins, losses, the round reached, points) and pet_team_rating (Elo across
  weeks). Titles (game/lb_titles.py board 'pet_war'): the champion's fighters 🏆 Bang vô địch đấu pet, the runner-up's
  🥈 Á quân bang chiến pet, the third's 🥉 Hạng ba bang chiến pet (ranks 11…15), for a week. 🏆 Thưởng top tuần
  (lb_titles WEEKLY_REWARD) pays the champion's and the runner-up's fighters only: no xu for the third.
* 🏋️ A team's training ground (the bang's "Sân luyện pet") is read from the provider (`facility`, key TRAINING_KEY):
  its level adds TRAINING_PCT % (at most TRAINING_MAX) to its fighters' stats in this war only.

API for other modules (the Bang agent): register(kind, provider), team_match(a, b, key), standings(db, t), ladder(db,
kind, week), team_rating(db, kind, id), training_bonus(db, kind, id), lead_of(db, week, kind, id).
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
LEAD = '~lead|'            # the sid of the marker row of a lineup chosen by the team's leaders (never a save's sid)
PETS_SHOWN = 8             # a member's strongest pets the lineup editor lists (and the one fielded now)
REMIND_SECS = 3600         # the reminder goes this long before the lock
REMIND_BATCH = 200         # teams reminded a housekeeping tick (the rest the next tick, 30 s later)


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

    # 👑 the leaders' lineup (none by default: every member picks their own)
    lead_who = 'Đội trưởng'

    def can_lead(self, db, team_id: str, sid: str) -> bool:
        """May this member choose the team's lineup?"""
        return False

    def role_of(self, db, team_id: str, sid: str) -> str:
        """The member's title as the lineup's notices name it ('Bang chủ')."""
        return ''

    def roster(self, db, team_id: str) -> list:
        """The members now: [{sid, pid, name, role}] (pid: the id the page shows, never a sid)."""
        return []

    def lock_team(self, db, team_id: str) -> None:
        """Take the team's own row lock first (its module's lock order), before the war's team lock."""

    def announce(self, db, team_id: str, sid: str, text: str, t: float) -> None:
        """A line for the team (its log, its chat group)."""

    def remind(self, db, text: str, t: float, since: float, limit: int) -> tuple:
        """The war's reminder to at most `limit` teams that can play and were not reminded since `since`: (sent, more left)."""
        return 0, False


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
    if op == 'war_team':
        return team_view(store, token)
    if op in ('war_lineup', 'war_lineup_off'):
        return set_lineup(store, token, data, op == 'war_lineup_off')
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
        lead = lead_of(db, week, kind, tid)
        if lead:   # 👑 the leaders chose the lineup: theirs wins until they hand it back
            A.need(False, f'👑 {lead["role"]} đã chọn đội hình bang chiến tuần này, bạn không tự đổi được. Nhờ {lead["role"]} đổi giúp nhé.',
                   'lead_set', 409)
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
        if r['sid'].startswith(LEAD):
            continue
        now_team = team_of(db, r['sid'])
        if now_team and (now_team[0], now_team[1]) == (kind, tid):
            out.append(r['sid'])
    return out


# ---------------------------------------------------------------- 👑 the leaders' lineup
def _lead_sid(kind: str, tid: str) -> str:
    return f'{LEAD}{kind}|{tid}'


def lead_of(db, week: str, kind: str, tid: str) -> dict | None:
    """{role, by (the leader's pid), at} when the team's leaders chose the week's lineup, else None."""
    r = db.execute('SELECT snap, at FROM pet_war_picks WHERE week=? AND sid=?', (week, _lead_sid(kind, tid))).fetchone()
    if not r:
        return None
    d = A._j(r['snap'], {})
    return dict(role=str(d.get('role') or 'Đội trưởng')[:24], by=str(d.get('by') or ''), at=float(r['at']))


def _states(store, db, sids: list) -> dict:
    """{sid: save} of these players, read only (parsed, migrated in memory when an older shape: never written)."""
    from . import archive as ar
    from .engine import migrate_state, needs_migration
    out = {}
    if not sids:
        return out
    for r in db.execute('SELECT sid, state FROM sessions WHERE sid = ANY(?)', (list(sids),)).fetchall():
        try:
            s = store.parse_state(r['state'], r['sid'])
            if needs_migration(s):
                with ar.collect():
                    s = migrate_state(s, owned=True)
        except Exception:  # noqa: BLE001 - one unreadable save never breaks the editor: that member shows no pet
            continue
        out[r['sid']] = s
    return out


def _leader(db, sid: str) -> tuple:
    """(kind, team id, team name, provider) of the player's team when they may choose its lineup."""
    team = team_of(db, sid)
    A.need(team, 'Vào một bang để cùng ra trận nhé.', 'no_team', 409)
    kind, tid, tname, _ = team
    prov = _providers()[kind]
    A.need(prov.can_lead(db, tid, sid), f'Chọn đội hình cần {prov.lead_who}.', 'role', 403)
    return kind, tid, tname, prov


def _eligible(db, prov, tid: str, m: dict, s) -> str:
    """'' when member `m` may fight for the team with one of the pets of save `s`, else why not."""
    if not prov.can_pick(db, tid, m['sid']):
        return 'Chưa được ra trận tuần này'
    if not s or not A._story(s).get('story'):
        return 'Chưa vào hành trình'
    if not A.candidates(s):
        return 'Chưa có bé'
    return ''


def team_view(store, token) -> dict:
    """👑 The lineup editor: every member with their pets (the strongest first, each with its rank and power), who is
    fielded now, and whether the lineup is the leaders' already."""
    from . import pet_tiers as px
    sid, display = A._who(store, token)
    A.need(display, 'Tạo tài khoản để vào đấu trường nhé.', 'account_required', 403)
    t = A.now()
    week, start, lock = _week_open(t)
    with store.connect() as db:
        kind, tid, tname, prov = _leader(db, sid)
        members = prov.roster(db, tid)
        states = _states(store, db, [m['sid'] for m in members])
        picked = {r['sid']: r['pet'] for r in db.execute('SELECT sid, pet FROM pet_war_picks WHERE week=? AND team_kind=? AND team_id=?',
                                                         (week, kind, tid)).fetchall() if not r['sid'].startswith(LEAD)}
        lead = lead_of(db, week, kind, tid)
        why = {m['sid']: _eligible(db, prov, tid, m, states.get(m['sid'])) for m in members}
    rows, picks = [], []
    for m in members:
        s = states.get(m['sid'])
        pets = []
        if s and not why[m['sid']]:
            ranked = sorted(A.candidates(s), key=lambda p: -px.power(s, p))
            shown = ranked[:PETS_SHOWN]
            now_pet = next((p for p in ranked if p['id'] == picked.get(m['sid'])), None)
            if now_pet and now_pet not in shown:
                shown.append(now_pet)
            pets = [A.pet_view(A.fighter(s, p)) | dict(id=p['id']) for p in shown]
        cur = picked.get(m['sid'])
        if cur and any(p['id'] == cur for p in pets):
            picks.append(dict(pid=m['pid'], pet=cur))
        rows.append(dict(pid=m['pid'], name=m['name'], role=m['role'], me=m['sid'] == sid, ok=not why[m['sid']] and bool(pets),
                         why=why[m['sid']], pets=pets, best=pets[0]['id'] if pets else '', pw=pets[0].get('pw', 0) if pets else 0))
    rows.sort(key=lambda r: (not r['ok'], -int(r['pw'] or 0), r['name']))
    return dict(ok=True, week=week, start=start, lock=lock, now=t, open=t < lock, size=SIZE, team=dict(kind=kind, id=tid, name=tname),
                members=rows, picks=picks, lead=dict(role=lead['role'], at=lead['at']) if lead else None)


def set_lineup(store, token, data, off: bool = False) -> dict:
    """👑 `war_lineup` {picks: [{pid, pet}]} (1…SIZE, one pet a member, in their order): the team's lineup for this
    week's war, replacing every pick of the team; `war_lineup_off`: members pick their own again (picks kept)."""
    sid, display = A._who(store, token)
    A.need(display, 'Tạo tài khoản để vào đấu trường nhé.', 'account_required', 403)
    want = [] if off else data.get('picks')
    if not off:
        A.need(isinstance(want, list) and 1 <= len(want) <= SIZE, f'Chọn từ 1 tới {SIZE} bé nhé.', 'bad_picks')
        A.need(all(isinstance(x, dict) and isinstance(x.get('pid'), str) and 0 < len(x['pid']) <= 40 and isinstance(x.get('pet'), str)
                   and 0 < len(x['pet']) <= 60 for x in want), 'Đội hình không hợp lệ.', 'bad_picks')
        A.need(len({x['pid'] for x in want}) == len(want), 'Mỗi người chỉ ra trận 1 bé thôi.', 'twice')
    t = A.now()
    week, start, lock = _week_open(t)
    A.need(t < lock, 'Đã khóa đội hình bang chiến tuần này. Tuần sau chọn sớm nhé!', 'locked', 409)

    def run(db):
        team = team_of(db, sid)
        A.need(team, 'Vào một bang để cùng ra trận nhé.', 'no_team', 409)
        _providers()[team[0]].lock_team(db, team[1])          # the team's own row first (its lock order), then the war's
        db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (LOCK_KEY, f'{week}|{team[0]}|{team[1]}'))
        kind, tid, tname, prov = _leader(db, sid)
        A.need((kind, tid) == tuple(team[:2]), 'Bạn vừa đổi bang. Mở lại nhé.', 'retry', 409)
        who = (prov.role_of(db, tid, sid) or prov.lead_who)[:24]
        roster = prov.roster(db, tid)
        me = next((m for m in roster if m['sid'] == sid), None)
        if off:
            n = db.execute('DELETE FROM pet_war_picks WHERE week=? AND sid=?', (week, _lead_sid(kind, tid))).rowcount
            A.need(n, 'Mọi người đang tự chọn bé rồi.', 'none', 409)
            prov.announce(db, tid, sid, f'🛡️ {who} {display[:24]} để mọi người tự chọn bé ra Bang chiến pet tuần này.', t)
            return dict(ok=True, message='Đã để mọi người tự chọn bé ra trận.')
        members = {m['pid']: m for m in roster}
        chosen = []
        for x in want:
            A.need(x['pid'] in members, 'Có người vừa rời bang. Mở lại nhé.', 'not_member', 409)
            chosen.append((members[x['pid']], x['pet']))
        states = _states(store, db, [m['sid'] for m, _ in chosen])
        rows = []
        for m, pid in chosen:
            s = states.get(m['sid'])
            why = _eligible(db, prov, tid, m, s)
            A.need(not why, f'{m["name"]}: {why}.', 'not_allowed', 403)
            pet = next((p for p in A.candidates(s) if p['id'] == pid), None)
            A.need(pet, f'Bé này không phải của {m["name"]}, hoặc không ở nhà hay trại nuôi.', 'not_owned', 409)
            rows.append((m, pet, A.fighter(s, pet)))
        db.execute('DELETE FROM pet_war_picks WHERE week=? AND team_kind=? AND team_id=?', (week, kind, tid))
        db.execute('INSERT INTO pet_war_picks(week, sid, team_kind, team_id, name, pet, snap, at) VALUES(?,?,?,?,?,?,?,?) '
                   'ON CONFLICT (week, sid) DO UPDATE SET snap=EXCLUDED.snap, at=EXCLUDED.at',
                   (week, _lead_sid(kind, tid), kind, tid, '', '', A._dump(dict(lead=1, role=who, by=me['pid'] if me else '')), t))
        for i, (m, pet, f) in enumerate(rows):
            db.execute('INSERT INTO pet_war_picks(week, sid, team_kind, team_id, name, pet, snap, at) VALUES(?,?,?,?,?,?,?,?) '
                       'ON CONFLICT (week, sid) DO UPDATE SET team_kind=EXCLUDED.team_kind, team_id=EXCLUDED.team_id, name=EXCLUDED.name, '
                       'pet=EXCLUDED.pet, snap=EXCLUDED.snap, at=EXCLUDED.at',
                       (week, m['sid'], kind, tid, m['name'][:24], pet['id'], A._dump(f), t + (i + 1) / 1000))
        names = ', '.join(f'{m["name"]} ({pet["n"]})' for m, pet, _ in rows)
        prov.announce(db, tid, sid, f'🛡️ {who} {display[:24]} chọn đội hình Bang chiến pet tuần này: {names}.', t)
        return dict(ok=True, message=f'👑 Đã chọn đội hình {len(rows)}/{SIZE} bé cho {tname}!')
    return store.transaction(run)


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


def _play_match(db, week: str, rd: int, slot: int, a: dict, b: dict, at: float, third: bool = False) -> tuple:
    """Play one team match of the bracket (a tie: the better seed) and store it: (w 0 | 1, winner, loser)."""
    key = f'w{week}-{rd}-{slot}'
    res = team_match(a, b, key)
    w = res['w'] if res['w'] != 2 else (0 if a['seed'] < b['seed'] else 1)
    duels = [dict(i=d['i'], w=d['w'], seed=key, a=dict(sid=d['a']['sid'], name=d['a']['name'], f=d['a']['f']) if d['a'] else None,
                  b=dict(sid=d['b']['sid'], name=d['b']['name'], f=d['b']['f']) if d['b'] else None) for d in res['duels']]
    data = dict(duels=duels, tb=[a['tb'], b['tb']], hp=res['hp'], tie=res['w'] == 2,
                engine=B.engine_of(*([d['f']] for dd in duels for d in (dd['a'], dd['b']) if d)))
    if third:
        data['third'] = True
    db.execute('INSERT INTO pet_war_matches(week, rd, slot, a_kind, a_id, a_name, b_kind, b_id, b_name, win, wa, wb, start, data) '
               'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (week, rd, slot, a['kind'], a['id'], a['name'], b['kind'], b['id'], b['name'], w, res['wa'], res['wb'], at, A._dump(data)))
    return (w, a, b) if w == 0 else (w, b, a)


def play(db, week: str, t: float) -> bool:
    """Lock the lineups of `week` and play its whole bracket, once."""
    db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (LOCK_KEY, week))
    if db.execute('SELECT 1 FROM pet_war WHERE week=?', (week,)).fetchone():
        return False
    start = start_of(t)
    teams = {}
    for r in db.execute('SELECT * FROM pet_war_picks WHERE week=? ORDER BY at, sid', (week,)).fetchall():
        if r['sid'].startswith(LEAD):      # 👑 the leaders' marker: not a fighter
            continue
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
    semi_lost = []                                          # 🥉 the losers of the real semi-finals (round rounds − 1)
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
            w, win, lose = _play_match(db, week, rd, slot, a, b, at)
            nxt.append(win)
            played.append((rd, a, b, w))
            for tm, me in ((a, w == 0), (b, w == 1)):
                tm['w'] = tm.get('w', 0) + me
                tm['l'] = tm.get('l', 0) + (not me)
                tm['best'] = rd
            if rd == rounds:
                champ, second = win, lose
            elif rd == rounds - 1:
                semi_lost.append(lose)
        alive = nxt
    if champ is None:   # cannot happen with ≥ 2 entrants (byes are all in round 1), kept safe
        champ = alive[0]
    # 🥉 Tranh hạng 3 (owner 25/10): the two semi-final losers play once more, at the final's start (rd = rounds + 1,
    # slot 0; same rules and tie-breaks). Their `best` stays the semi-final: only the win and the loss count. With one
    # real semi-final (3 teams: the other was a bye) its loser is third without a match.
    third = fourth = None
    if len(semi_lost) == 2:
        a, b = semi_lost
        w, third, fourth = _play_match(db, week, rounds + 1, 0, a, b, start + (rounds - 1) * GAP, third=True)
        played.append((rounds + 1, a, b, w))
        for tm, me in ((a, w == 0), (b, w == 1)):
            tm['w'] = tm.get('w', 0) + me
            tm['l'] = tm.get('l', 0) + (not me)
    elif len(semi_lost) == 1:
        third = semi_lost[0]
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
                third=[m['sid'] for m in third['members']] if third else [],
                third_team=dict(kind=third['kind'], id=third['id'], name=third['name']) if third else None,
                fourth_team=dict(kind=fourth['kind'], id=fourth['id'], name=fourth['name']) if fourth else None,
                third_match=fourth is not None,
                end=start + (rounds - 1) * GAP + SIZE * DUEL_SECS)      # the final and the 🥉 match start together
    db.execute("INSERT INTO pet_war(week, status, start, n, rounds, champ_kind, champ_id, champ_name, data, at) VALUES(?, 'done', ?, ?, ?, ?, ?, ?, ?, ?)",
               (week, start, len(entrants), rounds, champ['kind'], champ['id'], champ['name'][:40], A._dump(data), t))
    return True


def end_of(row) -> float:
    data = A._j(row['data'], {})
    return float(data.get('end') or row['start'])


def standings(db, t: float) -> list:
    """[(board, rank, sid, score)]: the fighters of the champion of the latest war over by `t` (ranks 1…5), of the
    runner-up (6…10) and 🥉 of the third (11…15) (game/lb_titles.py board 'pet_war')."""
    for row in db.execute("SELECT * FROM pet_war WHERE status='done' ORDER BY week DESC LIMIT 2").fetchall():
        if end_of(row) > t:
            continue
        data = A._j(row['data'], {})
        out = [('pet_war', i + 1, s, 2) for i, s in enumerate((data.get('champ') or [])[:SIZE])]
        out += [('pet_war', SIZE + i + 1, s, 1) for i, s in enumerate((data.get('second') or [])[:SIZE])]
        out += [('pet_war', 2 * SIZE + i + 1, s, 0) for i, s in enumerate((data.get('third') or [])[:SIZE])]
        return out
    return []


def ladder(db, kind: str | None = None, week: str | None = None, t: float | None = None, n: int = 20) -> list:
    """The team ladder of a war over (the latest by default): [{rank, kind, id, name, w, l, best, pts, rating, champ,
    place}] (place 3 / 4: 🥉 the 3rd-place match's winner comes before its loser, whatever their points)."""
    t = A.now() if t is None else t
    if week is None:
        rows = db.execute("SELECT * FROM pet_war WHERE status='done' ORDER BY week DESC LIMIT 2").fetchall()
        row = next((r for r in rows if end_of(r) <= t), None)
        if not row:
            return []
        week = row['week']
    else:
        row = db.execute('SELECT * FROM pet_war WHERE week=?', (week,)).fetchone()
    data = A._j(row['data'], {}) if row else {}
    q = 'SELECT * FROM pet_team_ladder WHERE week=?' + (' AND team_kind=?' if kind else '') + ' ORDER BY champ DESC, best DESC, pts DESC, rating DESC, name LIMIT ?'
    rows = db.execute(q, (week, kind, max(n, 4)) if kind else (week, max(n, 4))).fetchall()
    out = [dict(kind=r['team_kind'], id=r['team_id'], name=r['name'], w=r['w'], l=r['l'], best=r['best'], pts=r['pts'],
                rating=r['rating'], champ=bool(r['champ']), place=_place(data, r['team_kind'], r['team_id'])) for r in rows]
    # same champ and round reached: third before fourth (a stable sort keeps the SQL order otherwise)
    out.sort(key=lambda x: (not x['champ'], -int(x['best'] or 0), {3: 0, 4: 1}.get(x['place'], 0)))
    return [dict(x, rank=i + 1) for i, x in enumerate(out[:n])]


def team_rating(db, kind: str, tid: str) -> dict | None:
    r = db.execute('SELECT * FROM pet_team_rating WHERE team_kind=? AND team_id=?', (kind, tid)).fetchone()
    return dict(rating=r['rating'], wars=r['wars'], titles=r['titles']) if r else None


# ---------------------------------------------------------------- views
ROUND_NAMES = {1: 'Chung kết', 2: 'Bán kết', 3: 'Tứ kết'}
THIRD_NAME = 'Tranh hạng 3'


def is_third(rd: int, rounds: int) -> bool:
    """🥉 The 3rd-place match is stored as round rounds + 1 (slot 0), after the last round of the bracket."""
    return rounds >= 2 and rd == rounds + 1


def round_name(rd: int, rounds: int) -> str:
    if is_third(rd, rounds):
        return THIRD_NAME
    return ROUND_NAMES.get(rounds - rd + 1) or f'Vòng {rd}'


def _place(data: dict, kind: str, tid: str) -> int:
    """🥉 3 or 4 when the team finished third / fourth of a war (pet_war.data, from 2.6.7.1), else 0."""
    for n, k in ((3, 'third_team'), (4, 'fourth_team')):
        x = data.get(k)
        if isinstance(x, dict) and (x.get('kind'), x.get('id')) == (kind, tid):
            return n
    return 0


def _clock(t: float) -> str:
    """'20:00' in Vietnam time."""
    import datetime
    d = datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=7)))
    return f'{d.hour:02d}:{d.minute:02d}'


def team_card(db, kind: str, tid: str, sid: str, t: float | None = None) -> dict:
    """🛡️ The week's war for a team's page (the bang sheet's home tab), every member the same but for their buttons:
    {start, lock, end, now, phase, size, slots: [{name, me, pet}], lead: {role} | None, n, mine, can_lead, can_pick,
    matches: [{rd, round, vs, state, start, won, score, third}], third: the team plays 🥉 Tranh hạng 3 (once its pairing
    is shown), result: {champ, second, third, place, round, w, l, pts} | None, entered}.
    A few indexed reads: the team's picks (one query), its members, the war row, its matches and ladder row once played."""
    t = A.now() if t is None else t
    week, start, lock = _week_open(t)
    prov = _providers().get(kind)
    roster = {m['sid']: m for m in (prov.roster(db, tid) if prov else [])}
    rows = db.execute('SELECT sid, name, pet, snap FROM pet_war_picks WHERE week=? AND team_kind=? AND team_id=? ORDER BY at, sid',
                      (week, kind, tid)).fetchall()
    lead, picks = None, []
    for r in rows:
        if r['sid'].startswith(LEAD):
            d = A._j(r['snap'], {})
            lead = dict(role=str(d.get('role') or (prov.lead_who if prov else ''))[:24])
        elif t >= lock or r['sid'] in roster:     # before the lock only members still in the team count (as play does at it)
            f = B.clean(A._j(r['snap'], {}))
            if f:
                picks.append(dict(name=(roster.get(r['sid']) or {}).get('name') or r['name'], me=r['sid'] == sid, pet=A.pet_view(f)))
    picks = picks[:SIZE]
    war = db.execute('SELECT * FROM pet_war WHERE week=?', (week,)).fetchone()
    end = end_of(war) if war and war['status'] == 'done' else start + SIZE * DUEL_SECS
    if t < lock:
        phase = 'pick'
    elif war and war['status'] != 'done':
        phase = 'cancelled'
    elif not war or t < start:
        phase = 'locked'
    else:
        phase = 'live' if t < end else 'done'
    try:
        can_lead = bool(prov and prov.can_lead(db, tid, sid))
        can_pick = bool(prov and prov.can_pick(db, tid, sid))
    except Exception:  # noqa: BLE001 - a provider's fault never breaks the page
        can_lead = can_pick = False
    out = dict(week=week, start=start, lock=lock, end=end, now=t, phase=phase, size=SIZE, slots=picks, n=len(picks), lead=lead,
               mine=any(p['me'] for p in picks), can_lead=can_lead and phase == 'pick', can_pick=can_pick and phase == 'pick' and not lead,
               matches=[], result=None, entered=False, third=False)
    if not war or war['status'] != 'done':
        return out
    rounds = int(war['rounds'] or 0)
    data = A._j(war['data'], {})
    for m in db.execute('SELECT rd, slot, a_kind, a_id, a_name, b_kind, b_id, b_name, win, wa, wb, start FROM pet_war_matches WHERE week=? '
                        'AND ((a_kind=? AND a_id=?) OR (b_kind=? AND b_id=?)) ORDER BY rd', (week, kind, tid, kind, tid)).fetchall():
        if m['start'] > t and not (m['rd'] == 1 or t >= m['start'] - GAP + SIZE * DUEL_SECS):
            continue                                      # a later round's pairing is shown once the round before is over
        side = 0 if (m['a_kind'], m['a_id']) == (kind, tid) else 1
        bye = not m['b_name']
        state = 'wait' if m['start'] > t else 'live' if m['start'] + SIZE * DUEL_SECS > t and not bye else 'done'
        third = is_third(m['rd'], rounds)
        one = dict(rd=m['rd'], slot=m['slot'], round=round_name(m['rd'], rounds), vs='' if bye else (m['b_name'] if side == 0 else m['a_name']),
                   bye=bye, state=state, start=m['start'], third=third)
        out['third'] = out['third'] or third
        if state == 'done' and not bye:
            one.update(won=m['win'] == side, score=[m['wa'], m['wb']] if side == 0 else [m['wb'], m['wa']])
        out['matches'].append(one)
    out['entered'] = bool(out['matches'])
    if phase == 'done':
        lad = db.execute('SELECT * FROM pet_team_ladder WHERE week=? AND team_kind=? AND team_id=?', (week, kind, tid)).fetchone()
        if lad:
            champ = bool(lad['champ'])
            second = not champ and int(lad['best']) == rounds
            place = 1 if champ else 2 if second else _place(data, kind, tid)
            out['result'] = dict(champ=champ, second=second, third=place == 3, place=place,
                                 round=round_name(min(int(lad['best']) or 1, rounds), rounds) if rounds else '',
                                 w=int(lad['w']), l=int(lad['l']), pts=int(lad['pts']), champ_name=war['champ_name'])
        else:
            out['result'] = dict(champ=False, second=False, third=False, place=0, round='', w=0, l=0, pts=0, champ_name=war['champ_name'], out=True)
    return out


_REMIND: dict = {}


def remind_due(store, t: float | None = None) -> int:
    """⏰ server.py housekeeping (every 30 s): from REMIND_SECS before the lock until the lock, a line in each team's log
    and chat group ("Bang chiến 20:00 tối nay, đội hình chốt lúc 19:50"), once a team a week (the provider keeps the
    marker: a bang's own log row), REMIND_BATCH teams a tick, under the week's reminder lock (exactly once with two
    processes). Nothing outside that hour."""
    t = A.now() if t is None else t
    start, lock = start_of(t), lock_of(t)
    if not lock - REMIND_SECS <= t < lock:
        return 0
    week = A.vn_week(t)
    if _REMIND.get('done') == week:
        return 0
    text = f'🛡️ Bang chiến {_clock(start)} tối nay, đội hình chốt lúc {_clock(lock)}. Ghi danh bé ở ⚔️ Bang › 🛡️ Bang chiến tuần nhé!'

    def run(db):
        db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (LOCK_KEY, f'remind|{week}'))
        sent, more = 0, False
        for prov in list(_providers().values()):
            n, left = prov.remind(db, text, t, lock - REMIND_SECS, REMIND_BATCH - sent)
            sent += n
            more = more or left
        return sent, more
    sent, more = store.transaction(run)
    if not more:
        _REMIND['done'] = week
    return sent


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
        picks, lead, can_lead = [], None, False
        if team:
            lead = lead_of(db, week, team[0], team[1])
            prov = _providers().get(team[0])
            try:
                can_lead = bool(prov and prov.can_lead(db, team[1], sid))
            except Exception:  # noqa: BLE001 - a provider's fault never breaks the page
                can_lead = False
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
    for b in bracket:
        b['third'] = is_third(b['rd'], rounds)
    names = [dict(rd=r, name=round_name(r, rounds)) for r in range(1, rounds + 1)]
    if any(b['third'] for b in bracket):                  # 🥉 its own column after the final (same start)
        names.append(dict(rd=rounds + 1, name=THIRD_NAME, third=True))
    wdata = A._j(war['data'], {}) if war and phase == 'done' else {}
    out = dict(ok=True, week=week, start=start, lock=lock, now=t, phase=phase, size=SIZE, duel_secs=DUEL_SECS, gap=GAP,
               team=dict(kind=team[0], id=team[1], name=team[2], label=team[3]) if team else None,
               picks=[dict(name=p['name'], me=p['sid'] == sid, pet=A.pet_view(A._j(p['snap'], {}))) for p in picks],
               rounds=names, bracket=bracket,
               champ=war['champ_name'] if war and phase == 'done' else None, ladder=board,
               third=(wdata.get('third_team') or {}).get('name') or None,
               last=dict(week=last['week'], champ=last['champ_name']) if last else None, kinds=sorted(_providers()),
               lead=dict(role=lead['role'], at=lead['at']) if lead else None, can_lead=can_lead)
    return out


def match_view(store, token, data) -> dict:
    """One match of the war, once it has started: the five duels in their order, each with its log."""
    rd, slot = data.get('rd'), data.get('slot')
    A.need(type(rd) is int and type(slot) is int and 1 <= rd <= 12 and 0 <= slot < 4096, 'Không thấy trận này.', 'not_found', 404)
    week = data.get('week') if isinstance(data.get('week'), str) and len(data['week']) <= 10 else A.vn_week(A.now())
    with store.connect() as db:
        m = db.execute('SELECT * FROM pet_war_matches WHERE week=? AND rd=? AND slot=?', (week, rd, slot)).fetchone()
        war = db.execute('SELECT rounds FROM pet_war WHERE week=?', (week,)).fetchone() if m else None
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
        if x.get('a') and x.get('b') and d.get('engine') in B.REPLAYS:   # 🪽 2: a fighter wore wings
            tb = d.get('tb') or [0, 0]
            res = B.battle([dict(x['a']['f'], tb=tb[0])], [dict(x['b']['f'], tb=tb[1])], B.seed_of(x['seed'], f'duel{x["i"]}'))
            one.update(ev=res['ev'], hp=res['hp'], max=res['max'])
        duels.append(one)
    over = t >= m['start'] + SIZE * DUEL_SECS
    rounds = int(war['rounds'] or 0) if war else 0
    return dict(ok=True, week=week, rd=rd, slot=slot, a=m['a_name'], b=m['b_name'], start=m['start'], duel_secs=DUEL_SECS, duels=duels,
                round=round_name(rd, rounds) if rounds else '', third=is_third(rd, rounds),
                total=len(d.get('duels') or []), over=over, **(dict(win=m['win'], wa=m['wa'], wb=m['wb']) if over else {}))
