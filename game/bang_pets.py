"""⚔️ Bang × 🛡️ Bang chiến pet: the bang tables as the pet war's team kind 'bang' (game/pet_war.py TeamProvider).

* team_of: the player's bang now: a membership row 'in' of a bang that is active and not hidden by an operator (a hidden
  or disbanded bang fields nobody; its picks drop out at the lock, game/pet_war.py play re-reads every pick's team).
* name: '<emoji> <name>' of the bang (what the bracket, the ladder and the titles show).
* can_pick: any member fields their own pet ("mỗi người chọn 1 pet", owner 19/10): one pet a member, the first
  pet_war.SIZE members to pick fill the five slots (pet_war counts them under its team lock) unless the officers chose
  the lineup (can_lead below). 🏝️ Only while the bang holds its island (owner 21/10 "phải có mua đảo bang thì mới chơi
  được": game/bang.py has_island): a bang without one fields nobody (its members still see the war; team_of stays, so their page names their bang). An
  island is never taken back, so a pick made stays valid until the lock.
* 👑 can_lead (owner: "bang chủ được quyền chọn danh sách thú để xuất chiến nhé"): Trưởng lão and up (LEAD_FROM, the
  same officers who arrange the ⚔️ Thách đấu roster, game/bang_challenge.py OFFICER) choose the war's lineup from the
  members (roster: pid, display name, title); lock_team takes the bang row first (game/bang.py's lock order: the bang
  row, then the war's team lock and its pick rows, as a member leaving does); announce writes the line in the bang's
  log ('war') and its chat group (🛡️ Bang chiến pet), and bumps the bang so its pages refresh.
* facility(TRAINING_KEY): the level of the bang's 🐾 Sân luyện pet ('san_pet'), counting a build whose time is up even if
  nobody opened the bang page since (read only: finish_builds writes it later). pet_war turns it into +1 %/level of the
  fighters' stats in the war, at most pet_war.TRAINING_MAX.

Registered once on import (server.py imports this module); a fault here never breaks the arena (pet_war catches it).
"""
from __future__ import annotations

from . import bang as BG
from . import bang_content as BC
from . import pet_war as PW

KIND = 'bang'
FAC = 'san_pet'            # game/bang_content.py FACILITIES key of 🐾 Sân luyện pet
LEAD_FROM = BC.APPROVE_FROM   # 3: Trưởng lão and up choose the war's lineup (game/bang_challenge.py OFFICER)


def _member(db, sid: str):
    return db.execute("SELECT m.bang AS bang, m.role AS role, b.name AS name, b.emoji AS emoji FROM bang_members m "
                      "JOIN bangs b ON b.id=m.bang WHERE m.sid=? AND m.status='in' AND b.status='active' AND b.hidden=0",
                      (sid,)).fetchone()


def _label(r) -> str:
    return f"{r['emoji']} {r['name']}".strip()[:40]


class BangTeams(PW.TeamProvider):
    label = 'Bang'

    def team_of(self, db, sid: str):
        if not sid:
            return None
        r = _member(db, sid)
        return (str(r['bang']), _label(r)) if r else None

    def name(self, db, team_id: str) -> str:
        r = db.execute('SELECT name, emoji FROM bangs WHERE id=?', (team_id,)).fetchone()
        return _label(r) if r else str(team_id)

    def can_pick(self, db, team_id: str, sid: str) -> bool:
        r = _member(db, sid)
        return bool(r) and str(r['bang']) == str(team_id) and BG.has_island(db, str(team_id))

    lead_who = 'Trưởng lão trở lên'

    def _role(self, db, team_id: str, sid: str):
        r = _member(db, sid)
        return r['role'] if r and str(r['bang']) == str(team_id) else None

    def can_lead(self, db, team_id: str, sid: str) -> bool:
        role = self._role(db, team_id, sid)
        return role is not None and BC.ROLES.get(role, BC.ROLES['tv'])[3] >= LEAD_FROM

    def role_of(self, db, team_id: str, sid: str) -> str:
        role = self._role(db, team_id, sid)
        return BC.ROLES.get(role, BC.ROLES['tv'])[0] if role else ''

    def roster(self, db, team_id: str) -> list:
        rows = db.execute("SELECT m.sid, m.pid, m.role, a.display FROM bang_members m LEFT JOIN accounts a ON a.sid=m.sid "
                          "WHERE m.bang=? AND m.status='in' ORDER BY m.joined, m.sid", (team_id,)).fetchall()
        return [dict(sid=r['sid'], pid=r['pid'], name=(str(r['display'])[:24] if r['display'] else BG.GONE),
                     role=BC.ROLES.get(r['role'], BC.ROLES['tv'])[0]) for r in rows]

    def lock_team(self, db, team_id: str) -> None:
        BG._lock(db, team_id)

    def announce(self, db, team_id: str, sid: str, text: str, t: float) -> None:
        BG._log(db, team_id, sid, 'war', text, t)
        r = db.execute('SELECT channel FROM bangs WHERE id=?', (team_id,)).fetchone()
        if r and r['channel']:
            from . import live_chat
            c = db.execute("INSERT INTO chat_messages(channel, pid, name, av, text, at, adm) VALUES(?, 'admin', ?, '🛡️', ?, ?, 1) RETURNING id",
                           (r['channel'], '🛡️ Bang chiến pet', text[:300], t)).fetchone()
            if c:
                live_chat.notify(db, dict(op='unhide', id=int(c['id'])))
        BG._bump(db, team_id)

    def facility(self, db, team_id: str, key: str) -> int:
        if key != PW.TRAINING_KEY:
            return 0
        r = db.execute('SELECT level, target, ready_at FROM bang_facilities WHERE bang=? AND fac=?', (team_id, FAC)).fetchone()
        if not r:
            return 0
        lv = int(r['level'] or 0)
        if r['target'] is not None and r['ready_at'] is not None and float(r['ready_at']) <= BG.now():
            lv = max(lv, int(r['target']))
        return lv


PROVIDER = BangTeams()


def install() -> None:
    """(Re-)register the provider (tests that unregister 'bang' call this to put it back)."""
    PW.register(KIND, PROVIDER)


install()
