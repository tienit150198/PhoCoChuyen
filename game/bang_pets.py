"""⚔️ Bang × 🛡️ Bang chiến pet: the bang tables as the pet war's team kind 'bang' (game/pet_war.py TeamProvider).

* team_of: the player's bang now: a membership row 'in' of a bang that is active and not hidden by an operator (a hidden
  or disbanded bang fields nobody; its picks drop out at the lock, game/pet_war.py play re-reads every pick's team).
* name: '<emoji> <name>' of the bang (what the bracket, the ladder and the titles show).
* can_pick: any member fields their own pet ("mỗi người chọn 1 pet", owner 19/10): one pet a member, the first
  pet_war.SIZE members to pick fill the five slots (pet_war counts them under its team lock). No officer step. 🏝️ Only
  while the bang holds its island (owner 21/10 "phải có mua đảo bang thì mới chơi được": game/bang.py has_island): a
  bang without one fields nobody (its members still see the war; team_of stays, so their page names their bang). An
  island is never taken back, so a pick made stays valid until the lock.
* facility(TRAINING_KEY): the level of the bang's 🐾 Sân luyện pet ('san_pet'), counting a build whose time is up even if
  nobody opened the bang page since (read only: finish_builds writes it later). pet_war turns it into +1 %/level of the
  fighters' stats in the war, at most pet_war.TRAINING_MAX.

Registered once on import (server.py imports this module); a fault here never breaks the arena (pet_war catches it).
"""
from __future__ import annotations

from . import bang as BG
from . import pet_war as PW

KIND = 'bang'
FAC = 'san_pet'            # game/bang_content.py FACILITIES key of 🐾 Sân luyện pet


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
