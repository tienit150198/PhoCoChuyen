"""⚔️ Thách đấu bang: bang against bang with pets, any day (owner 21/10: "đấu trường pets chỉ mở cho các bang hội đánh
nhau thôi, thêm hoạt động đó vào cho các bang hội nhé", and earlier "các bạn trong bang xếp nhau mà chơi").

* 🐾 Đội hình bang (a standing roster, bang_chal_roster): each member registers one pet (`tc_reg`, again to change it,
  `tc_unreg` to leave); Trưởng lão and up arrange the order (`tc_order`): the first SIZE (5) ready entries start, the
  rest are substitutes who step in when a starter left the bang or their pet is no longer at home or in the kennel
  (`ok` 0). The pet's battle snapshot follows the pet: every jr_pet_* command refreshes it (on_pet_commit, the save's
  own transaction, like the weekly war's pick). This roster is separate from the weekly war's lineup (pet_war_picks:
  first come, five a bang, reset each week) so arranging one never changes the other.
* ⚔️ A challenge (bang_chal): a Trưởng lão or higher of bang A challenges bang B (`tc_send`, from the list `tc_find`
  with each bang's power, Elo and record). B's Trưởng lão or higher accepts or declines within WINDOW (30 minutes;
  `tc_answer`), A may take it back while open (`tc_cancel`); unanswered it expires. A bang may take challenges
  automatically (mode 'auto', set by Phó bang and up with `tc_set`; 'off': no challenges). On accept the server plays
  the match at once (game/pet_war.py team_match, the pairing shuffled from the challenge id: Trận 1→5, more duel wins
  win, a missing pet loses its duel; the 🐾 Sân luyện pet adds +1 %/level, at most 5 %, as in the war), once: the row
  goes open → done under its lock, behind both bang rows. Both bangs get a line in their chat group and their log;
  anyone can watch the replay (`tc_match`: the same duels from the stored snapshots and the id's seed).
* 🏆 Rewards, no xu ever: the bang's challenge Elo and record (bang_chal_team, K; separate from the weekly war's
  pet_team_rating so its seeding is unchanged) and a few điểm cống hiến for the winning fighters (PTS_WIN, a draw
  PTS_DRAW both sides; at most PTS_DAY_N times a member a Vietnam day: ids per person per day, so hopping between bangs
  earns nothing more; nothing for beating a bang that fielded fewer than MIN_FIELD pets), and the 👑 Bang mạnh nhất
  tuần's 🐾 Pets points (owner 21/10 "hãy tính điểm của pets, công trình và cấp bang làm điểm"):
  C.CHAL_WIN a win, C.CHAL_DRAW each on a draw (sa, sb; nothing against a bang that fielded fewer than MIN_FIELD), at
  most C.CHAL_WEEK_MAX a bang a week (chal_scores; game/bang.py standings).
* Limits (a Vietnam day): SEND_DAY challenges sent and PLAY_DAY matches played a bang, OPEN_IN open challenges waiting
  for a bang at once, PAIR_DAY between the same two bangs; both bangs need MIN_FIELD ready pets to send; hidden or
  disbanded bangs are never listed nor challenged (their open challenges are cancelled).

Lock order (game/bang.py's): the bang rows in id order, then the member rows, then bang_chal / bang_chal_team rows.
Request ids: `tc_send` carries `rid` (unique per sending bang: a retry answers the same challenge). Nothing here
writes a save. Tables: bang_chal_roster, bang_chal_team, bang_chal (game/pg_schema.py SCHEMA_VERSION 61).
🛑 MNL_BANG_CHAL_OFF=1 (or MNL_BANG_OFF / MNL_PET_ARENA_OFF): every op is refused gracefully, nothing changes.
"""
from __future__ import annotations

import os
import re
import secrets
import threading
import time

from . import bang as BG
from . import bang_content as BC
from . import pet_arena as A
from . import pet_battle as B
from . import pet_war as PW

SIZE = PW.SIZE              # five duels a match
MIN_FIELD = 3               # ready pets a bang needs to send (and to take) a challenge
WINDOW = 30 * 60            # an open challenge waits this long for an answer
SEND_DAY = 5                # challenges a bang sends a Vietnam day
PLAY_DAY = 5                # matches a bang plays a Vietnam day (sent or received)
OPEN_IN = 5                 # open challenges waiting for one bang at once
PAIR_DAY = 2                # matches (open or played) between the same two bangs a day
K = 24                      # the challenge Elo's K (both sides)
PTS_WIN, PTS_DRAW = 10, 5             # điểm cống hiến for each fighter of the winning bang (a draw: both)
PTS_DAY_N = 3                         # times a member earns them a Vietnam day (≤ 30 points)
OFFICER = BC.APPROVE_FROM             # 3: Trưởng lão and up send, answer, cancel and arrange the roster
MODE_FROM = BC.RULES_FROM             # 4: Phó bang and up choose how the bang takes challenges
MODES = {'ask': 'Hỏi trước', 'auto': 'Tự nhận', 'off': 'Không nhận'}
RECENT = 10
TOWN = 8
FIND_MAX = 30
ID_RE = re.compile(r't[0-9a-f]{16}')
GONE = 'Một người chơi'
NO_BANG = A.NO_BANG
OFF_TEXT = 'Thách đấu bang đang tạm nghỉ để bảo trì. Quay lại sau nhé!'
OPS = ('tc', 'tc_find', 'tc_match', 'tc_reg', 'tc_unreg', 'tc_order', 'tc_send', 'tc_answer', 'tc_cancel', 'tc_set')
LIGHT = frozenset(op for op in OPS if op != 'tc_reg')     # every op but registering a pet reads no save
need = A.need


def off() -> bool:
    return os.environ.get('MNL_BANG_CHAL_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on') or BG.off()


def now() -> float:
    return A.now()


def _j(text, default):
    return A._j(text, default)


def _rows(db, sql, args=()) -> list:
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def _row(db, sql, args=()) -> dict | None:
    r = db.execute(sql, args).fetchone()
    return dict(r) if r else None


def _label(bang: dict) -> str:
    return f"{bang['emoji']} {bang['name']}".strip()[:40]


def _mine(db, sid: str) -> dict | None:
    """My membership of an active, shown bang: {bang, role, name, emoji} or None."""
    if not sid:
        return None
    from . import bang_pets
    r = bang_pets._member(db, sid)
    return dict(r) if r else None


NO_ISLAND = 'Bang cần mua Đảo bang để thách đấu.'


def has_island(db, bid: str) -> bool:
    """🏝️ Owner 21/10 "phải có mua đảo bang thì mới chơi được": a bang plays only once it owns its Đảo bang
    (game/bang.py has_island: bangs.isle ≥ 1, bought from the fund or granted to the bangs from before 21/10)."""
    return bool(BG.has_island(db, bid))


def _rank(role: str) -> int:
    return BC.ROLES.get(role, BC.ROLES['tv'])[3]


def _role_name(rank_from: int) -> str:
    return BC.ROLES[next(k for k in BC.ROLE_ORDER if BC.ROLES[k][3] == rank_from)][0]


def _who(store, token) -> tuple:
    sid, display = A._who(store, token)
    need(display, 'Tạo tài khoản để vào đấu trường nhé.', 'account_required', 403)
    return sid, display


# ---------------------------------------------------------------- the roster
def _roster(db, bid: str) -> list:
    """The bang's roster in its order, members still in that bang only (a leaver's row stays, unused)."""
    return _rows(db, "SELECT r.sid, r.pid, r.name, r.pet, r.snap, r.pw, r.ok, r.pos, r.at, m.role FROM bang_chal_roster r "
                     "JOIN bang_members m ON m.bang=r.bang AND m.sid=r.sid AND m.status='in' WHERE r.bang=? ORDER BY r.pos, r.at, r.sid",
                 (bid,))


def _fighter(r: dict) -> dict | None:
    return B.clean(_j(r['snap'], {})) if r.get('ok') else None


def starters(rows: list) -> list:
    """The first SIZE ready entries: (row, fighter)."""
    out = []
    for r in rows:
        f = _fighter(r)
        if f:
            out.append((r, f))
            if len(out) >= SIZE:
                break
    return out


def power_of(rows: list) -> int:
    return sum(int(f.get('pw') or 0) for _, f in starters(rows))


def on_pet_commit(db, sid: str, after: dict) -> None:
    """A jr_pet_* command (the save's own transaction): the registered pet's snapshot follows it; a pet no longer at
    home or in the kennel is not ready (`ok` 0) until it is back. One indexed read for everyone else, no write when
    nothing changed."""
    rows = _rows(db, 'SELECT bang, pet, snap, ok FROM bang_chal_roster WHERE sid=?', (sid,))
    if not rows:
        return
    have = {p['id']: p for p in A.candidates(after)}
    for r in rows:
        pet = have.get(r['pet'])
        if pet:
            f = A.fighter(after, pet)
            snap = A._dump(f)
            if snap != r['snap'] or not r['ok']:
                db.execute('UPDATE bang_chal_roster SET snap=?, pw=?, ok=1 WHERE bang=? AND sid=?', (snap, int(f['pw']), r['bang'], sid))
        elif r['ok']:
            db.execute('UPDATE bang_chal_roster SET ok=0 WHERE bang=? AND sid=?', (r['bang'], sid))


def forget(db, sid: str) -> None:
    """A player erased their data: their roster rows go; challenges keep the bangs' names, never the player."""
    db.execute('DELETE FROM bang_chal_roster WHERE sid=?', (sid,))
    db.execute("UPDATE bang_chal SET by_sid='' WHERE by_sid=?", (sid,))
    db.execute("UPDATE bang_chal SET ans_sid='' WHERE ans_sid=?", (sid,))


# ---------------------------------------------------------------- the team rows
def _team(db, bid: str) -> dict:
    r = _row(db, 'SELECT * FROM bang_chal_team WHERE bang=?', (bid,))
    out = dict(bang=bid, rating=A.START, w=0, l=0, d=0, mode='ask')
    if r:
        out.update(rating=int(r['rating']), w=int(r['w']), l=int(r['l']), d=int(r['d']), mode=r['mode'] if r['mode'] in MODES else 'ask')
    return out


def _team_put(db, bid: str, t: float, **cols) -> None:
    keys = sorted(cols)
    db.execute(f'INSERT INTO bang_chal_team(bang, {", ".join(keys)}, at) VALUES(?, {", ".join("?" * len(keys))}, ?) '
               f'ON CONFLICT (bang) DO UPDATE SET {", ".join(f"{k}=EXCLUDED.{k}" for k in keys)}, at=EXCLUDED.at',
               (bid, *[cols[k] for k in keys], t))


# ---------------------------------------------------------------- counters (a Vietnam day)
def _sent(db, bid: str, day: str) -> int:
    return int(db.execute('SELECT COUNT(*) AS n FROM bang_chal WHERE a=? AND day=?', (bid, day)).fetchone()['n'])


def _played(db, bid: str, day: str) -> int:
    return int(db.execute("SELECT COUNT(*) AS n FROM bang_chal WHERE status='done' AND done_day=? AND (a=? OR b=?)",
                          (day, bid, bid)).fetchone()['n'])


def _open_in(db, bid: str, t: float) -> int:
    return int(db.execute("SELECT COUNT(*) AS n FROM bang_chal WHERE b=? AND status='open' AND expires>?", (bid, t)).fetchone()['n'])


def _pair(db, x: str, y: str, day: str) -> int:
    return int(db.execute("SELECT COUNT(*) AS n FROM bang_chal WHERE day=? AND status IN ('open','done') AND ((a=? AND b=?) OR (a=? AND b=?))",
                          (day, x, y, y, x)).fetchone()['n'])


def _expire(db, t: float, bids=()) -> int:
    """Open challenges past their window become 'expired' (of these bangs, or any: the housekeeping)."""
    if bids:
        marks = ','.join('?' * len(bids))
        return db.execute(f"UPDATE bang_chal SET status='expired', answered=expires WHERE status='open' AND expires<=? "
                          f'AND (a IN ({marks}) OR b IN ({marks}))', (t, *bids, *bids)).rowcount
    return db.execute("UPDATE bang_chal SET status='expired', answered=expires WHERE id IN (SELECT id FROM bang_chal WHERE status='open' "
                      'AND expires<=? ORDER BY expires LIMIT 500 FOR UPDATE SKIP LOCKED)', (t,)).rowcount


def chal_scores(db, week: str) -> dict:
    """{bang id: the week's 🐾 Pets points from challenges, at most C.CHAL_WEEK_MAX} (game/bang.py standings)."""
    out: dict = {}
    for r in _rows(db, "SELECT a, b, sa, sb FROM bang_chal WHERE week=? AND status='done' AND (sa>0 OR sb>0)", (week,)):
        out[r['a']] = out.get(r['a'], 0) + int(r['sa'])
        out[r['b']] = out.get(r['b'], 0) + int(r['sb'])
    return {k: min(v, BC.CHAL_WEEK_MAX) for k, v in out.items() if v > 0}


def run_due(store, t: float | None = None) -> int:
    """server.py housekeeping (every 30 s): open challenges past their window expire (a page also treats them so)."""
    t = now() if t is None else t
    return store.transaction(lambda db: _expire(db, t))


# ---------------------------------------------------------------- notices
def _say(db, bang: dict, text: str, t: float) -> None:
    """A line in the bang's chat group (an admin-style row the live chat delivers to its members) and its log."""
    BG._log(db, bang['id'], '', 'chal', text, t)
    ch = bang.get('channel')
    if not ch:
        return
    from . import live_chat
    c = db.execute("INSERT INTO chat_messages(channel, pid, name, av, text, at, adm) VALUES(?, 'admin', ?, '⚔️', ?, ?, 1) RETURNING id",
                   (ch, '⚔️ Thách đấu bang', text[:300], t)).fetchone()
    if c:
        live_chat.notify(db, dict(op='unhide', id=int(c['id'])))


def _officers(db, bid: str) -> list:
    return [r['pid'] for r in _rows(db, "SELECT pid, role FROM bang_members WHERE bang=? AND status='in'", (bid,)) if _rank(r['role']) >= OFFICER]


def _members_pids(db, bid: str) -> list:
    return [r['pid'] for r in _rows(db, "SELECT pid FROM bang_members WHERE bang=? AND status='in'", (bid,))]


def cancel_open(db, bid: str, t: float) -> int:
    """A bang disbanded or hidden (game/bang.py, its row locked): its open challenges are cancelled."""
    return db.execute("UPDATE bang_chal SET status='cancelled', answered=? WHERE status='open' AND (a=? OR b=?)", (t, bid, bid)).rowcount


# ---------------------------------------------------------------- the ops' shared steps
def _me_locked(db, sid: str, bids: tuple, mine: str, rank_from: int) -> tuple:
    """Both bang rows locked in id order, then my member row: (locked {id: row}, my member row) when I am still in
    `mine` with at least `rank_from`."""
    locked = BG._lock(db, *bids)
    m = _row(db, "SELECT * FROM bang_members WHERE sid=? AND status='in' FOR UPDATE", (sid,))
    need(m is not None and m['bang'] == mine, 'Bạn vừa đổi bang. Mở lại nhé.', 'not_member', 409)
    bang = locked.get(mine)
    need(bang is not None and bang['status'] == 'active' and not bang['hidden'], NO_BANG, 'no_bang', 403)
    if _rank(m['role']) < rank_from:
        need(False, f'Việc này cần {_role_name(rank_from)} trở lên.', 'role', 403)
    return locked, m


def _open_ok(ch: dict, t: float) -> bool:
    return ch['status'] == 'open' and float(ch['expires']) > t


def _resolve(db, ch: dict, locked: dict, t: float, ans_sid: str, auto: bool) -> dict:
    """Play the challenge now, once (the caller holds both bang rows and the challenge row): the five duels, the Elo,
    the week's points, the fighters' điểm cống hiến, the notices. Returns the done row."""
    teams = []
    for bid in (ch['a'], ch['b']):
        rows = _roster(db, bid)
        members = [dict(sid=r['sid'], pid=r['pid'], name=r['name'] or GONE, f=f) for r, f in starters(rows)]
        teams.append(dict(kind='bang', id=bid, name=_label(locked[bid]), members=members, tb=PW.training_bonus(db, 'bang', bid)))
    res = PW.team_match(teams[0], teams[1], ch['id'])
    w = res['w']
    ta, tb = _team(db, ch['a']), _team(db, ch['b'])
    score = 1.0 if w == 0 else 0.0 if w == 1 else 0.5
    da, dbb = A.elo(ta['rating'], tb['rating'], score, K), A.elo(tb['rating'], ta['rating'], 1.0 - score, K)
    fair = [len(tm['members']) >= MIN_FIELD for tm in teams]     # beating a team of one or two earns nothing
    pts = {'win': BC.CHAL_WIN, 'draw': BC.CHAL_DRAW, 'loss': 0}
    res_of = lambda side: 'draw' if w == 2 else 'win' if w == side else 'loss'   # noqa: E731
    sa = pts[res_of(0)] if fair[1] else 0
    sb = pts[res_of(1)] if fair[0] else 0
    day, week = A.vn_day(t), A.vn_week(t)
    duels = [dict(i=d['i'], w=d['w'], a=dict(pid=d['a']['pid'], name=d['a']['name'], f=d['a']['f']) if d['a'] else None,
                  b=dict(pid=d['b']['pid'], name=d['b']['name'], f=d['b']['f']) if d['b'] else None) for d in res['duels']]
    data = dict(duels=duels, tb=[teams[0]['tb'], teams[1]['tb']], hp=res['hp'], tie=w == 2, n=[len(teams[0]['members']), len(teams[1]['members'])])
    n = db.execute("UPDATE bang_chal SET status='done', answered=?, ans_sid=?, auto=?, win=?, wa=?, wb=?, ra=?, rb=?, da=?, db=?, sa=?, sb=?, "
                   "week=?, done_day=?, engine=?, data=? WHERE id=? AND status='open'",
                   (t, ans_sid, 1 if auto else 0, w, res['wa'], res['wb'], ta['rating'], tb['rating'], da, dbb, sa, sb, week, day,
                    B.engine_of(*([d['f']] for dd in duels for d in (dd['a'], dd['b']) if d)),
                    A._dump(data), ch['id'])).rowcount
    need(n == 1, 'Trận này vừa được trả lời. Mở lại nhé.', 'retry', 409)      # exactly once (the row is locked: cannot happen)
    for side, tm, d in ((0, ta, da), (1, tb, dbb)):
        won, draw = w == side, w == 2
        _team_put(db, tm['bang'], t, rating=tm['rating'] + d, w=tm['w'] + (1 if won else 0), l=tm['l'] + (0 if won or draw else 1),
                  d=tm['d'] + (1 if draw else 0), mode=tm['mode'])
    for side, tm in enumerate(teams):
        if (w == side or w == 2) and fair[1 - side]:
            for m in tm['members']:
                _earn(db, tm['id'], m['sid'], m['pid'], PTS_DRAW if w == 2 else PTS_WIN, t)
    an, bn = teams[0]['name'], teams[1]['name']
    score_line = f'{an} {res["wa"]}–{res["wb"]} {bn}'
    for side, bid in enumerate((ch['a'], ch['b'])):
        other = bn if side == 0 else an
        mine = (res['wa'], res['wb']) if side == 0 else (res['wb'], res['wa'])
        head = '🤝 Hòa' if w == 2 else '🏆 Thắng' if w == side else '💪 Thua'
        got = sa if side == 0 else sb
        extra = f' (+{got} điểm 🐾 xếp hạng tuần, mỗi bé ra sân +{PTS_DRAW if w == 2 else PTS_WIN} điểm cống hiến)' if got else ''
        _say(db, locked[bid], f'⚔️ Thách đấu: {head} {other} {mine[0]}–{mine[1]}{extra}. Xem lại ở ⚔️ Bang › Thách đấu.', t)
        BG._bump(db, bid)
    BG._notify(db, pids=_members_pids(db, ch['a']) + _members_pids(db, ch['b']))
    out = _row(db, 'SELECT * FROM bang_chal WHERE id=?', (ch['id'],))
    out['line'] = score_line
    return out


def _earn(db, bid: str, sid: str, pid: str, pts: int, t: float) -> bool:
    """A fighter's điểm cống hiến, at most PTS_DAY_N times a Vietnam day (ids per person per day: changing bang earns
    nothing more). The member row is updated by game/bang.py _earn (behind the bang rows: the one lock order)."""
    day = A.vn_day(t)
    n = int(db.execute("SELECT COUNT(*) AS n FROM bang_points WHERE sid=? AND day=? AND kind='chal'", (sid, day)).fetchone()['n'])
    if n >= PTS_DAY_N:
        return False
    return BG._earn(db, bid, sid, f'tc:{pid}:{day}:{n + 1}', 'chal', pts, t)


# ---------------------------------------------------------------- the ops
def register(store, token, data, state) -> dict:
    """🐾 Put one of my pets on my bang's roster (or change it): a new entry goes to the end of the order."""
    sid, display = _who(store, token)
    A._gate(state, display)
    pid_ = data.get('pet')
    need(isinstance(pid_, str), 'Chọn một bé nhé.', 'bad_pet')
    pet = next((p for p in A.candidates(state) if p['id'] == pid_), None)
    need(pet, 'Bé này không ở nhà hay trại nuôi.', 'not_owned', 409)
    f = A.fighter(state, pet)
    t = now()

    def run(db):
        me = _mine(db, sid)
        need(me, NO_BANG, 'no_bang', 403)
        locked, m = _me_locked(db, sid, (me['bang'],), me['bang'], 0)
        bid = me['bang']
        cur = _row(db, 'SELECT pos FROM bang_chal_roster WHERE bang=? AND sid=? FOR UPDATE', (bid, sid))
        pos = int(cur['pos']) if cur else int(db.execute('SELECT COALESCE(MAX(pos), 0) AS p FROM bang_chal_roster WHERE bang=?', (bid,)).fetchone()['p']) + 1
        db.execute('INSERT INTO bang_chal_roster(bang, sid, pid, name, pet, snap, pw, ok, pos, at) VALUES(?,?,?,?,?,?,?,1,?,?) '
                   'ON CONFLICT (bang, sid) DO UPDATE SET pid=EXCLUDED.pid, name=EXCLUDED.name, pet=EXCLUDED.pet, snap=EXCLUDED.snap, '
                   'pw=EXCLUDED.pw, ok=1', (bid, sid, m['pid'], display[:24], pid_, A._dump(f), int(f['pw']), pos, t))
        A.power_commit(db, sid, state)      # 💪 the bang ranking's Chiến lực, fresh
        BG._bump(db, bid)
        return _label(locked[bid])
    name = store.transaction(run)
    return dict(ok=True, message=f'🐾 {pet["n"]} vào đội hình thách đấu của {name}!')


def unregister(store, token, data) -> dict:
    sid, _ = _who(store, token)

    def run(db):
        me = _mine(db, sid)
        need(me, NO_BANG, 'no_bang', 403)
        _me_locked(db, sid, (me['bang'],), me['bang'], 0)
        n = db.execute('DELETE FROM bang_chal_roster WHERE bang=? AND sid=?', (me['bang'], sid)).rowcount
        need(n, 'Bạn chưa ghi danh bé nào.', 'none', 409)
        BG._bump(db, me['bang'])
    store.transaction(run)
    return dict(ok=True, message='Đã rút bé khỏi đội hình thách đấu.')


def order(store, token, data) -> dict:
    """✏️ Trưởng lão and up arrange the roster: `order` is a list of members' pids (the first SIZE ready ones start);
    entries left out keep their order after the listed ones."""
    sid, _ = _who(store, token)
    pids = data.get('order')
    need(isinstance(pids, list) and len(pids) <= 60 and all(isinstance(p, str) and BG.PID_RE.fullmatch(p) for p in pids)
         and len(set(pids)) == len(pids), 'Thứ tự không hợp lệ.', 'bad_order')

    def run(db):
        me = _mine(db, sid)
        need(me, NO_BANG, 'no_bang', 403)
        bid = me['bang']
        _me_locked(db, sid, (bid,), bid, OFFICER)
        rows = _rows(db, 'SELECT sid, pid, pos FROM bang_chal_roster WHERE bang=? ORDER BY pos, at, sid FOR UPDATE', (bid,))
        by = {r['pid']: r for r in rows}
        first = [by[p] for p in pids if p in by]
        listed = set(pids)
        rest = [r for r in rows if r['pid'] not in listed]
        for i, r in enumerate(first + rest):
            if int(r['pos']) != i + 1:
                db.execute('UPDATE bang_chal_roster SET pos=? WHERE bang=? AND sid=?', (i + 1, bid, r['sid']))
        BG._bump(db, bid)
    store.transaction(run)
    return dict(ok=True, message='✏️ Đã xếp lại đội hình.')


def set_mode(store, token, data) -> dict:
    sid, _ = _who(store, token)
    mode = data.get('mode')
    need(mode in MODES, 'Chọn cách nhận thách đấu nhé.', 'bad_mode')
    t = now()

    def run(db):
        me = _mine(db, sid)
        need(me, NO_BANG, 'no_bang', 403)
        bid = me['bang']
        locked, _ = _me_locked(db, sid, (bid,), bid, MODE_FROM)
        tm = _team(db, bid)
        if tm['mode'] == mode:
            return False
        _team_put(db, bid, t, mode=mode)
        BG._log(db, bid, sid, 'chal', f'{BG._display(db, sid)} đổi nhận thách đấu: {MODES[mode]}.', t)
        BG._bump(db, bid)
        return True
    changed = store.transaction(run)
    return dict(ok=True, message=f'Đã lưu: {MODES[mode]}.' if changed else 'Không có gì thay đổi.')


def send(store, token, data) -> dict:
    """⚔️ Challenge another bang (Trưởng lão and up). An 'auto' bang takes it at once: the match is played now."""
    sid, display = _who(store, token)
    target, rid = data.get('bang'), data.get('rid')
    need(isinstance(target, str) and BG.ID_RE.fullmatch(target), 'Chọn một bang nhé.', 'bad_bang')
    need(isinstance(rid, str) and BG.RID_RE.fullmatch(rid), 'Thiếu mã thao tác. Tải lại trang nhé.', 'bad_rid')
    t = now()
    day = A.vn_day(t)

    def run(db):
        me = _mine(db, sid)
        need(me, NO_BANG, 'no_bang', 403)
        a = me['bang']
        need(target != a, 'Không tự thách đấu bang mình được nhé.', 'self')
        locked, _ = _me_locked(db, sid, (a, target), a, OFFICER)
        again = _row(db, 'SELECT * FROM bang_chal WHERE a=? AND rid=?', (a, rid))
        if again:   # the same request again (a retry): its answer, nothing new
            return again, True
        other = locked.get(target)
        need(other is not None and other['status'] == 'active' and not other['hidden'], 'Không tìm thấy bang này.', 'not_found', 404)
        _expire(db, t, (a, target))
        need(has_island(db, a), NO_ISLAND, 'no_island', 409)
        need(has_island(db, target), f'{_label(other)} chưa mua Đảo bang, chưa thách đấu được.', 'their_island', 409)
        tb = _team(db, target)
        need(tb['mode'] != 'off', f'{_label(other)} đang không nhận thách đấu.', 'closed', 409)
        need(len(starters(_roster(db, a))) >= MIN_FIELD, f'Bang mình cần ít nhất {MIN_FIELD} bé trong đội hình thách đấu đã nhé.', 'roster', 409)
        need(len(starters(_roster(db, target))) >= MIN_FIELD, f'{_label(other)} chưa đủ {MIN_FIELD} bé trong đội hình.', 'their_roster', 409)
        need(_sent(db, a, day) < SEND_DAY, f'Hôm nay bang đã gửi {SEND_DAY} lời thách đấu rồi. Mai gửi tiếp nhé!', 'send_limit', 409)
        need(_played(db, a, day) < PLAY_DAY, f'Hôm nay bang đã đấu {PLAY_DAY} trận rồi. Mai đấu tiếp nhé!', 'play_limit', 409)
        need(_played(db, target, day) < PLAY_DAY, f'Hôm nay {_label(other)} đã đấu đủ {PLAY_DAY} trận.', 'their_limit', 409)
        need(_pair(db, a, target, day) < PAIR_DAY, f'Hai bang đã đấu {PAIR_DAY} trận hôm nay rồi.', 'pair_limit', 409)
        need(not _row(db, "SELECT 1 FROM bang_chal WHERE status='open' AND expires>? AND ((a=? AND b=?) OR (a=? AND b=?))", (t, a, target, target, a)),
             'Hai bang đang có một lời thách đấu chờ trả lời.', 'pending', 409)
        need(_open_in(db, target, t) < OPEN_IN, f'{_label(other)} đang có nhiều lời thách đấu chờ. Thử lại sau nhé.', 'busy', 409)
        cid = 't' + secrets.token_hex(8)
        db.execute("INSERT INTO bang_chal(id, a, b, a_name, b_name, by_sid, rid, status, day, at, expires) VALUES(?,?,?,?,?,?,?,'open',?,?,?)",
                   (cid, a, target, _label(locked[a]), _label(other), sid, rid, day, t, t + WINDOW))
        ch = _row(db, 'SELECT * FROM bang_chal WHERE id=? FOR UPDATE', (cid,))
        BG._log(db, a, sid, 'chal', f'⚔️ {display[:24]} thách đấu {_label(other)}.', t)
        if tb['mode'] == 'auto':
            return _resolve(db, ch, locked, t, '', True), False
        _say(db, other, f'⚔️ {_label(locked[a])} thách đấu bang mình! Trưởng lão trở lên nhận lời trong {WINDOW // 60} phút: ⚔️ Bang › Thách đấu.', t)
        BG._bump(db, a)
        BG._bump(db, target)
        BG._notify(db, pids=_officers(db, target))
        return ch, False
    ch, again = store.transaction(run)
    return _answer_of(ch, again, 0)


def _answer_of(ch: dict, again: bool, side: int) -> dict:
    out = dict(ok=True, chal=_brief(ch, side), again=again)
    if ch['status'] == 'done':
        out['match'] = ch['id']
        w = int(ch['win'])
        head = '🤝 Hòa' if w == 2 else '🏆 Thắng' if w == side else '💪 Thua'
        mine, theirs = (ch['wa'], ch['wb']) if side == 0 else (ch['wb'], ch['wa'])
        vs = ch['b_name'] if side == 0 else ch['a_name']
        out['message'] = f'{head} {vs} {mine}–{theirs}! Xem trận nhé.'
    elif ch['status'] == 'open':
        out['message'] = f'⚔️ Đã gửi lời thách đấu tới {ch["b_name"]}. Chờ bang đó nhận lời trong {WINDOW // 60} phút nhé.'
    else:
        out['message'] = {'declined': 'Lời thách đấu đã bị từ chối.', 'cancelled': 'Lời thách đấu đã hủy.', 'expired': 'Lời thách đấu đã hết hạn.'}.get(ch['status'], '')
    return out


def answer(store, token, data) -> dict:
    """✅ / ✕ an open challenge to my bang (Trưởng lão and up). Accepting plays it now; a second officer's accept (or
    a retry) finds it played and answers with the same match."""
    sid, display = _who(store, token)
    cid, ok = data.get('id'), data.get('ok')
    need(isinstance(cid, str) and ID_RE.fullmatch(cid), 'Không thấy lời thách đấu này.', 'not_found', 404)
    need(type(ok) is bool, 'Nhận hay từ chối?', 'bad')
    t = now()
    day = A.vn_day(t)

    def run(db):
        ch = _row(db, 'SELECT * FROM bang_chal WHERE id=?', (cid,))
        need(ch, 'Không thấy lời thách đấu này.', 'not_found', 404)
        me = _mine(db, sid)
        need(me and me['bang'] == ch['b'], 'Chỉ bang được thách đấu mới trả lời được.', 'not_yours', 403)
        locked, _ = _me_locked(db, sid, (ch['a'], ch['b']), ch['b'], OFFICER)
        ch = _row(db, 'SELECT * FROM bang_chal WHERE id=? FOR UPDATE', (cid,))
        if ch['status'] == 'done' and ok:
            return ch, True
        need(_open_ok(ch, t), {'done': 'Trận này đã đấu rồi.', 'declined': 'Lời thách đấu này đã bị từ chối.', 'cancelled': 'Bang kia đã hủy lời thách đấu.'}
             .get(ch['status'], 'Lời thách đấu đã hết hạn.'), 'gone', 409)
        a = locked.get(ch['a'])
        if not ok:
            db.execute("UPDATE bang_chal SET status='declined', answered=?, ans_sid=? WHERE id=?", (t, sid, cid))
            if a:
                BG._log(db, a['id'], '', 'chal', f'{_label(locked[ch["b"]])} từ chối lời thách đấu.', t)
                BG._bump(db, a['id'])
            BG._bump(db, ch['b'])
            return _row(db, 'SELECT * FROM bang_chal WHERE id=?', (cid,)), False
        need(a is not None and a['status'] == 'active' and not a['hidden'], 'Bang thách đấu không còn nữa.', 'gone', 409)
        need(has_island(db, ch['b']), NO_ISLAND, 'no_island', 409)
        need(has_island(db, ch['a']), f'{ch["a_name"]} chưa có Đảo bang, chưa đấu được.', 'their_island', 409)
        need(len(starters(_roster(db, ch['b']))) >= MIN_FIELD, f'Bang mình cần ít nhất {MIN_FIELD} bé trong đội hình thách đấu đã nhé.', 'roster', 409)
        need(_played(db, ch['b'], day) < PLAY_DAY, f'Hôm nay bang đã đấu {PLAY_DAY} trận rồi. Mai đấu tiếp nhé!', 'play_limit', 409)
        need(_played(db, ch['a'], day) < PLAY_DAY, f'Hôm nay {ch["a_name"]} đã đấu đủ {PLAY_DAY} trận.', 'their_limit', 409)
        return _resolve(db, ch, locked, t, sid, False), False
    ch, again = store.transaction(run)
    out = _answer_of(ch, again, 1)
    if ch['status'] == 'declined':
        out['message'] = 'Đã từ chối lời thách đấu.'
    return out


def cancel(store, token, data) -> dict:
    """↩️ Take back my bang's open challenge (Trưởng lão and up)."""
    sid, _ = _who(store, token)
    cid = data.get('id')
    need(isinstance(cid, str) and ID_RE.fullmatch(cid), 'Không thấy lời thách đấu này.', 'not_found', 404)
    t = now()

    def run(db):
        ch = _row(db, 'SELECT * FROM bang_chal WHERE id=?', (cid,))
        need(ch, 'Không thấy lời thách đấu này.', 'not_found', 404)
        me = _mine(db, sid)
        need(me and me['bang'] == ch['a'], 'Chỉ bang gửi mới hủy được.', 'not_yours', 403)
        _me_locked(db, sid, (ch['a'], ch['b']), ch['a'], OFFICER)
        ch = _row(db, 'SELECT * FROM bang_chal WHERE id=? FOR UPDATE', (cid,))
        need(_open_ok(ch, t), 'Trận này đã đấu rồi.' if ch['status'] == 'done' else 'Lời thách đấu này không còn chờ nữa.', 'gone', 409)
        db.execute("UPDATE bang_chal SET status='cancelled', answered=? WHERE id=?", (t, cid))
        BG._bump(db, ch['a'])
        BG._bump(db, ch['b'])
    store.transaction(run)
    return dict(ok=True, message='Đã hủy lời thách đấu.')


# ---------------------------------------------------------------- views
def _brief(ch: dict, side: int | None = None) -> dict:
    """A challenge for a list, from `side`'s point of view (0: the challenger, 1: the challenged, None: watching)."""
    out = dict(id=ch['id'], a=ch['a_name'], b=ch['b_name'], status=ch['status'], at=float(ch['at']), expires=float(ch['expires']))
    if ch['status'] == 'done':
        out.update(win=int(ch['win']), wa=int(ch['wa']), wb=int(ch['wb']), auto=bool(ch['auto']))
        if side in (0, 1):
            w = int(ch['win'])
            out.update(res='draw' if w == 2 else 'win' if w == side else 'loss', d=int(ch['da'] if side == 0 else ch['db']),
                       s=int(ch['sa'] if side == 0 else ch['sb']))
    if side in (0, 1):
        out['vs'] = ch['b_name'] if side == 0 else ch['a_name']
        out['mine'] = side
    return out


_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()
CACHE_SECS = 15.0


def _cached(key, fn):
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECS:
            return hit[1]
    out = fn()
    with _CACHE_LOCK:
        if len(_CACHE) > 16:
            _CACHE.clear()
        _CACHE[key] = (time.monotonic(), out)
    return out


def _bangs(store, t: float) -> dict:
    """{bang id: card} of every active, shown bang: name, emoji, colour, members, Elo and record, mode, power and ready
    pets of its roster, matches played today and open challenges waiting for it (cached CACHE_SECS)."""
    day = A.vn_day(t)

    def run():
        with store.connect() as db:
            bangs = _rows(db, "SELECT id, name, emoji, color FROM bangs WHERE status='active' AND hidden=0")
            counts = {r['bang']: int(r['n']) for r in _rows(db, "SELECT bang, COUNT(*) AS n FROM bang_members WHERE status='in' GROUP BY bang")}
            teams = {r['bang']: r for r in _rows(db, 'SELECT * FROM bang_chal_team')}
            ready: dict = {}
            for r in _rows(db, "SELECT r.bang, r.pw FROM bang_chal_roster r JOIN bang_members m ON m.bang=r.bang AND m.sid=r.sid AND m.status='in' "
                               'WHERE r.ok=1 AND r.pw>0 ORDER BY r.bang, r.pos, r.at, r.sid'):
                ready.setdefault(r['bang'], []).append(int(r['pw']))
            played: dict = {}
            for r in _rows(db, "SELECT a, b FROM bang_chal WHERE status='done' AND done_day=?", (day,)):
                played[r['a']] = played.get(r['a'], 0) + 1
                played[r['b']] = played.get(r['b'], 0) + 1
            waiting = {r['b']: int(r['n']) for r in _rows(db, "SELECT b, COUNT(*) AS n FROM bang_chal WHERE status='open' AND expires>? GROUP BY b", (t,))}
            isle = {b['id']: has_island(db, b['id']) for b in bangs}
        out = {}
        for b in bangs:
            tm = teams.get(b['id']) or {}
            pws = ready.get(b['id'], [])
            out[b['id']] = dict(id=b['id'], name=b['name'], emoji=b['emoji'], color=b['color'], n=counts.get(b['id'], 0),
                                rating=int(tm.get('rating') or A.START), w=int(tm.get('w') or 0), l=int(tm.get('l') or 0), d=int(tm.get('d') or 0),
                                mode=tm.get('mode') if tm.get('mode') in MODES else 'ask', power=sum(pws[:SIZE]), ready=min(len(pws), SIZE),
                                played=played.get(b['id'], 0), waiting=waiting.get(b['id'], 0), island=isle[b['id']])
        return out
    return _cached(('bangs', day, int(t // CACHE_SECS)), run)


def find(store, token, data) -> dict:
    """The bangs my bang may challenge, the nearest in power first, each with why not (when not)."""
    sid, _ = _who(store, token)
    q = BG.name_key(str(data.get('q') or '')[:30])
    t = now()
    day = A.vn_day(t)
    cards = _bangs(store, t)
    with store.connect() as db:
        me = _mine(db, sid)
        need(me, NO_BANG, 'no_bang', 403)
        bid = me['bang']
        pair: dict = {}
        pending = set()
        for r in _rows(db, "SELECT a, b, status, expires FROM bang_chal WHERE (a=? OR b=?) AND (day=? OR status='open')", (bid, bid, day)):
            o = r['b'] if r['a'] == bid else r['a']
            if r['status'] == 'open' and float(r['expires']) > t:
                pending.add(o)
            if r['status'] in ('open', 'done'):
                pair[o] = pair.get(o, 0) + 1
        mine = cards.get(bid) or dict(power=power_of(_roster(db, bid)), ready=0, played=0)
    out = []
    for c in cards.values():
        if c['id'] == bid or (q and q not in BG.name_key(c['name'])):
            continue
        why = ('Chưa có Đảo bang' if not c['island'] else 'Không nhận thách đấu' if c['mode'] == 'off' else 'Đang chờ trả lời' if c['id'] in pending else
               f'Chưa đủ {MIN_FIELD} bé' if c['ready'] < MIN_FIELD else 'Đã đấu đủ hôm nay' if c['played'] >= PLAY_DAY else
               f'Đã gặp {PAIR_DAY} lần hôm nay' if pair.get(c['id'], 0) >= PAIR_DAY else 'Đang bận' if c['waiting'] >= OPEN_IN else '')
        out.append(dict(c, why=why, auto=c['mode'] == 'auto'))
    out.sort(key=lambda c: (bool(c['why']), abs(c['power'] - mine['power']), -c['rating'], c['name']))
    return dict(ok=True, list=out[:FIND_MAX], power=mine['power'])


def _team_card(db, bid: str) -> dict:
    tm = _team(db, bid)
    rows = _roster(db, bid)
    return dict(rating=tm['rating'], w=tm['w'], l=tm['l'], d=tm['d'], mode=tm['mode'], power=power_of(rows), ready=len(starters(rows)))


def view(store, token, data=None) -> dict:
    """The 🛡️ › ⚔️ Thách đấu section: my bang's roster (in its order, starters marked), how it takes challenges, its
    record, open challenges both ways, recent results; and the town's latest matches (anyone may watch)."""
    sid = store.resolve(token)[0] if isinstance(token, str) else None
    t = now()
    day = A.vn_day(t)
    with store.connect() as db:
        town = [_brief(r) for r in _rows(db, "SELECT * FROM bang_chal WHERE status='done' ORDER BY answered DESC LIMIT ?", (TOWN,))]
        me = _mine(db, sid) if sid else None
        out = dict(ok=True, rules=rules(), modes=dict(MODES), town=town, now=t, mine=None)
        if not me:
            return out
        bid = me['bang']
        rows = _roster(db, bid)
        start = {r['sid'] for r, _ in starters(rows)}
        tm = _team(db, bid)
        incoming = _rows(db, "SELECT * FROM bang_chal WHERE b=? AND status='open' AND expires>? ORDER BY at", (bid, t))
        outgoing = _rows(db, "SELECT * FROM bang_chal WHERE a=? AND status='open' AND expires>? ORDER BY at", (bid, t))
        recent = _rows(db, "SELECT * FROM bang_chal WHERE (a=? OR b=?) AND status<>'open' ORDER BY COALESCE(answered, at) DESC LIMIT ?",
                       (bid, bid, RECENT))
        foes = {c['a']: _team_card(db, c['a']) for c in incoming}
        counts = dict(sent=_sent(db, bid, day), played=_played(db, bid, day))
        mine_row = _row(db, 'SELECT pet, ok FROM bang_chal_roster WHERE bang=? AND sid=?', (bid, sid))
    roster = []
    for i, r in enumerate(rows):
        f = _fighter(r)
        roster.append(dict(pid=r['pid'], name=r['name'] or GONE, me=r['sid'] == sid, n=i + 1, start=r['sid'] in start, ok=bool(f),
                           pet=A.pet_view(f) if f else None))
    out['mine'] = dict(bang=bid, name=_label(me), role=me['role'], officer=_rank(me['role']) >= OFFICER, boss=_rank(me['role']) >= MODE_FROM,
                       rating=tm['rating'], w=tm['w'], l=tm['l'], d=tm['d'], mode=tm['mode'], power=sum(int(f.get('pw') or 0) for _, f in starters(rows)),
                       ready=len(start), today=dict(counts, send_max=SEND_DAY, play_max=PLAY_DAY),
                       pet=mine_row['pet'] if mine_row else '', pet_ok=bool(mine_row and mine_row['ok']))
    out['roster'] = roster
    out['incoming'] = [dict(_brief(c, 1), foe=foes.get(c['a'])) for c in incoming]
    out['outgoing'] = [_brief(c, 0) for c in outgoing]
    out['recent'] = [_brief(c, 0 if c['a'] == bid else 1) for c in recent]
    return out


def card(db, bid: str, sid: str, role: str, t: float | None = None) -> dict:
    """The ⚔️ Thách đấu card of the Bang sheet (game/bang.py page): record, open challenges to answer, the last results."""
    t = now() if t is None else t
    tm = _team(db, bid)
    rows = _roster(db, bid)
    incoming = _rows(db, "SELECT * FROM bang_chal WHERE b=? AND status='open' AND expires>? ORDER BY at LIMIT 5", (bid, t))
    out_n = int(db.execute("SELECT COUNT(*) AS n FROM bang_chal WHERE a=? AND status='open' AND expires>?", (bid, t)).fetchone()['n'])
    recent = _rows(db, "SELECT * FROM bang_chal WHERE (a=? OR b=?) AND status='done' ORDER BY answered DESC LIMIT 3", (bid, bid))
    day = A.vn_day(t)
    return dict(rating=tm['rating'], w=tm['w'], l=tm['l'], d=tm['d'], mode=tm['mode'], roster=len(rows), ready=len(starters(rows)),
                size=SIZE, min=MIN_FIELD, mine=any(r['sid'] == sid for r in rows), officer=_rank(role) >= OFFICER,
                incoming=[_brief(c, 1) for c in incoming], outgoing=out_n,
                recent=[_brief(c, 0 if c['a'] == bid else 1) for c in recent], played=_played(db, bid, day), play_max=PLAY_DAY)


def incoming_count(db, bid: str, t: float | None = None) -> int:
    t = now() if t is None else t
    return _open_in(db, bid, t)


def match_view(store, token, data) -> dict:
    """One played challenge: its five duels in order, each with its log (the same fight from the stored snapshots)."""
    cid = data.get('id')
    need(isinstance(cid, str) and ID_RE.fullmatch(cid), 'Không thấy trận này.', 'not_found', 404)
    sid = store.resolve(token)[0] if isinstance(token, str) else None
    with store.connect() as db:
        ch = _row(db, 'SELECT * FROM bang_chal WHERE id=?', (cid,))
        me = _mine(db, sid) if sid else None
    need(ch and ch['status'] == 'done', 'Không thấy trận này.', 'not_found', 404)
    d = _j(ch['data'], {})
    tb = d.get('tb') or [0, 0]
    my_pid = BG.pid_of(sid) if sid else ''
    duels = []
    for x in d.get('duels') or []:
        def side(s):
            return dict(name=s['name'], me=s.get('pid') == my_pid, pets=[A.pet_view(s['f'])]) if s else dict(name='Vắng mặt', pets=[])
        one = dict(i=x['i'], w=x['w'], sides=[side(x.get('a')), side(x.get('b'))])
        if x.get('a') and x.get('b') and int(ch['engine']) in B.REPLAYS:   # 🪽 2: a fighter wore wings
            res = B.battle([dict(x['a']['f'], tb=tb[0])], [dict(x['b']['f'], tb=tb[1])], B.seed_of(ch['id'], f'duel{x["i"]}'))
            one.update(ev=res['ev'], hp=res['hp'], max=res['max'])
        duels.append(one)
    side_ = 0 if me and me['bang'] == ch['a'] else 1 if me and me['bang'] == ch['b'] else None
    return dict(ok=True, id=cid, a=ch['a_name'], b=ch['b_name'], win=int(ch['win']), wa=int(ch['wa']), wb=int(ch['wb']), at=float(ch['answered'] or ch['at']),
                duels=duels, total=len(duels), tb=tb, me=side_, da=int(ch['da']), db=int(ch['db']), sa=int(ch['sa']), sb=int(ch['sb']))


def rules() -> dict:
    return dict(size=SIZE, min=MIN_FIELD, window=WINDOW, send_day=SEND_DAY, play_day=PLAY_DAY, pair_day=PAIR_DAY, open_in=OPEN_IN,
                pts_win=PTS_WIN, pts_draw=PTS_DRAW, score_win=BC.CHAL_WIN, score_draw=BC.CHAL_DRAW, score_week=BC.CHAL_WEEK_MAX, pts_day=PTS_WIN * PTS_DAY_N, training=PW.TRAINING_MAX)


def act(store, token, op: str, data: dict, state, ip: str = '') -> dict:
    """/api/arena/tc* (game/pet_arena.py act routes them here)."""
    need(not off(), OFF_TEXT, 'off', 503)
    need(op in OPS, 'Thao tác không hợp lệ.', 'unknown', 404)
    if op == 'tc':
        return view(store, token, data)
    if op == 'tc_match':
        return match_view(store, token, data)
    if op == 'tc_find':
        return find(store, token, data)
    if op == 'tc_reg':
        return register(store, token, data, state)
    if op == 'tc_unreg':
        return unregister(store, token, data)
    if op == 'tc_order':
        return order(store, token, data)
    if op == 'tc_set':
        return set_mode(store, token, data)
    if op == 'tc_send':
        return send(store, token, data)
    if op == 'tc_answer':
        return answer(store, token, data)
    return cancel(store, token, data)
