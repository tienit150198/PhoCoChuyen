"""🎙️ Phòng hát: mic trực tiếp (owner 07/10; switch LIVE_KARAOKE_MIC, off by default).

In the public karaoke rooms (live/karaoke.py) the singer on stage may turn on a live mic, and everyone in the room
hears them through a self-hosted SFU (LiveKit, live/sfu.py, deploy/livekit). Listeners cannot speak. Nothing is
recorded anywhere. This module holds the rules both servers share, and the one thing stored for it:

* The birth year (an optional field of the account, asked the first time someone turns the mic on): the table
  `account_birth` (sid, year, at), SCHEMA_VERSION 30. A separate table, not a column of `accounts` and not a save key,
  so a rollback to 1.9.13 never sees it. It is set once (a player cannot retry with another year after a refusal); the
  admin can clear it. Deleted with the player's data (forget).
* The age rule: MIN_AGE (16). Only a year is asked, so a player counts as the youngest they can be this Vietnam year
  (year of birth + 1 + MIN_AGE <= this year): someone born in 2010 opens the mic from 2027.
* MIC_SECS: a mic session ends by itself after 6 minutes (and always when the song ends, is skipped, voted off or
  cut by an admin). MIC_REPORTS distinct reports of the singer while the mic is on cut it for the rest of the song.
* MIC_ACCOUNT_DAYS: accounts this old may sing live (a fresh account made to dodge a ban cannot).
"""
from __future__ import annotations

import os
import time

from .karaoke import KaraError, need, now

MIN_AGE = 16
YEAR_MIN = 1920
MIC_SECS = 360                   # the mic turns itself off this long after it was first turned on for a song
MIC_REPORTS = 3                  # distinct reports of the live singer that cut the mic for the rest of the song
MIC_ACCOUNT_DAYS = 1
LISTEN_TTL = 60                  # a listener's token must be used this soon (a new one per join)
DAY = 86400


def enabled() -> bool:
    """The game server's view of the switch (server.py headers, the birth-year route)."""
    return os.environ.get('LIVE_KARAOKE_MIC', '0').strip().lower() in ('1', 'true', 'yes', 'on')


def vn_year(t: float | None = None) -> int:
    return time.gmtime((now() if t is None else t) + 7 * 3600).tm_year


def age_ok(year, t: float | None = None) -> bool:
    """True when a player born in `year` is MIN_AGE or older even if their birthday is still to come this year."""
    return type(year) is int and YEAR_MIN <= year and vn_year(t) - year - 1 >= MIN_AGE


def account_old_enough(created_at, t: float | None = None) -> bool:
    """accounts.created_at is text 'YYYY-MM-DD HH:MM:SS' (UTC)."""
    cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime((now() if t is None else t) - MIC_ACCOUNT_DAYS * DAY))
    return bool(created_at) and str(created_at) <= cut


def birth_of(store, sid: str) -> int | None:
    with store.connect() as db:
        r = db.execute('SELECT year FROM account_birth WHERE sid=?', (sid,)).fetchone()
    return int(r['year']) if r else None


def birth(store, token: str, d: dict) -> dict:
    """POST /api/karaoke/birth {year}: the account's birth year, once. Returns {ok, year, mic, fixed}: `mic` says
    whether this account may sing live; `fixed` that a year was already stored (it does not change)."""
    from .karaoke import _who
    need(enabled(), 'Mic trực tiếp chưa mở.', 'off', 404)
    sid, _ = _who(store, token)
    year = d.get('year')
    need(type(year) is int and YEAR_MIN <= year <= vn_year(), 'Chọn năm sinh của bạn nhé.', 'bad_year')
    t = now()

    def run(db):
        db.execute('INSERT INTO account_birth(sid, year, at) VALUES(?, ?, ?) ON CONFLICT(sid) DO NOTHING', (sid, year, t))
    store.transaction(run)
    got = birth_of(store, sid)
    if got is None:
        raise KaraError('Chưa lưu được, thử lại nhé.', 'busy', 503)
    return dict(ok=True, year=got, mic=age_ok(got), fixed=got != year)


def forget(store, token: str) -> None:
    """A player deletes their data: their birth year goes with it."""
    sid = store.key(token)
    with store.connect() as db:
        db.execute('DELETE FROM account_birth WHERE sid=?', (sid,))
