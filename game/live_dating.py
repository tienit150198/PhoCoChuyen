"""💕 Dates of the live service (live/dating.py), the game server's side: the PostgreSQL tables in
game/pg_schema.py, the bond "Đang tìm hiểu 💕" shown on a friend's card (game/friends.py), and the cleanup when a
player deletes their data.

* `live_dates`: one row per café date (pids a < b and their saves, start, end, how it ended, cards in common, right
  orders). The live service reads the last 24 h at start-up: the same two players are not matched again within a day.
* `date_bonds`: two saves (sids, a < b) that both tapped ❤️ at the end of a date. Couples "đang tìm hiểu" may later
  use the ring and proposal flow of game/marriage.py like any two friends; nothing there changes.
The game server never writes these rows (the live service does); it only reads the bond and forgets a player."""
from __future__ import annotations



def bonded(db, sid: str, other: str) -> bool:
    """These two saves are "đang tìm hiểu" (both ❤️ at the end of a date)."""
    a, b = sorted((sid, other))
    try:
        return bool(db.execute('SELECT 1 FROM date_bonds WHERE a=? AND b=?', (a, b)).fetchone())
    except Exception:  # noqa: BLE001 - a database from before the dating tables
        return False


def forget(store, token: str) -> None:
    """A player deletes their data ("XOA"): their bonds and their dates go with it."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM date_bonds WHERE a=? OR b=?', (sid, sid))
        db.execute('DELETE FROM live_dates WHERE a_sid=? OR b_sid=?', (sid, sid))
    store.transaction(run)
