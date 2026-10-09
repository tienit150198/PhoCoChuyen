"""🕶️ The police's eye on the skill stalls (owner 09/10: "phóng dao, ô ăn quan thì chơi hệ kĩ năng", "bắt nếu cảm thấy
có cheat hoặc spam"). 🗡️ Phóng dao and 🪨 Ô ăn quan are not in the Chợ đen's arrest roll (game/fair.py _police): a
player who plays them for real never meets the police there. They are arrested only when this conservative detector
sees what no hand on a phone does (a miss is better than arresting an honest player):

* Phóng dao, throws sent ahead (KN_AHEAD_MS): a throw's last knife claims a moment of the level more than KN_AHEAD_MS
  later than the server has seen pass since it started the level. The stall's own page measures its throws on a
  level clock that starts when the board arrives, so it is always behind the server's (by the network, at most
  ~1 s ahead with the whole-second `now` of the state it aligns on); only a script that computes its throws from
  the board's schedule and sends them before they happen gets there. KN_AHEAD_FLAGS such throws within
  KN_AHEAD_WINDOW_MS: caught. (Throws more than fair_knife.SLACK ahead are refused as before.)
* Phóng dao, runs in a burst (KN_SPAM_RUNS runs started within KN_SPAM_MS): far past a hand that aims its knives.
* Ô ăn quan, moves too fast (OAQ_FAST_MOVES moves within OAQ_FAST_WINDOW_MS, each within OAQ_FAST_MS of its game's
  previous command): the stall's page plays every sowing out (fast mode and reduced motion too) and a move takes two
  taps (a cell, then a way) after it, so a person's moves come seconds, at the very least well over half a second,
  apart: not one of them is that fast.
* Ô ăn quan, games in a burst (OAQ_SPAM_GAMES games started within OAQ_SPAM_MS).

Counters are fixed windows ([start ms, count]: the count of events since the window's first one; a burst is caught
only when all of it falls within one window, never more often than a sliding window would). Only the server's own
clock and inputs it already receives are used. Nothing about the thresholds reaches the client; the arrest message
says what the police saw in words.

Save: journey['fair_watch'] (optional; an older server's journey keeps unknown blocks, its fair validator never sees
it): {ks: [at, n] knife runs started, ka: [at, n] knife throws sent ahead, os: [at, n] ô ăn quan games started,
ol: the last ô ăn quan command (ms), of: [at, n] ô ăn quan moves that came too fast}, every key optional.
"""
from __future__ import annotations

KEY = 'fair_watch'
KN_AHEAD_MS = 2500             # a throw claiming more than this beyond the server's elapsed level time is sent ahead
KN_AHEAD_FLAGS = 2             # ... this many such throws
KN_AHEAD_WINDOW_MS = 3_600_000  # ... within an hour
KN_SPAM_RUNS = 100             # Phóng dao runs started (3 s a run for 5 minutes on end)
KN_SPAM_MS = 300_000           # ... within 5 minutes
OAQ_FAST_MS = 350              # an ô ăn quan move this soon after the game's previous command is too fast
OAQ_FAST_MOVES = 8             # ... this many
OAQ_FAST_WINDOW_MS = 600_000   # ... within 10 minutes (a game can be short)
OAQ_SPAM_GAMES = 120           # ô ăn quan games started
OAQ_SPAM_MS = 600_000          # ... within 10 minutes
WINDOWS = ('ks', 'ka', 'os', 'of')
KEYS = WINDOWS + ('ol',)
COUNT_MAX = 10**6
MS_MAX = 10**14


def _w(j: dict) -> dict:
    w = j.get(KEY)
    if not isinstance(w, dict):
        w = j[KEY] = {}
    return w


def _tick(w: dict, k: str, ms: int, window: int) -> int:
    """One more event in the window `k`: a new window when the last one is over (or the clock went back); returns the
    events in the window, this one included."""
    c = w.get(k)
    if not c or ms < c[0] or ms - c[0] >= window:
        c = w[k] = [ms, 0]
    c[1] = min(COUNT_MAX, c[1] + 1)
    return c[1]


def kn_start(j: dict, ms: int) -> bool:
    """A Phóng dao run starts now: True when it makes a burst (spam)."""
    return _tick(_w(j), 'ks', ms, KN_SPAM_MS) >= KN_SPAM_RUNS


def kn_throw(j: dict, ms: int, ahead: int) -> bool:
    """A Phóng dao throw whose last knife claims `ahead` ms past the server's elapsed level time: True when the throws
    sent ahead are enough to call it a script."""
    if ahead <= KN_AHEAD_MS:
        return False
    return _tick(_w(j), 'ka', ms, KN_AHEAD_WINDOW_MS) >= KN_AHEAD_FLAGS


def oaq_start(j: dict, ms: int) -> bool:
    """An ô ăn quan game starts now: True when it makes a burst (spam). The game's move clock starts."""
    w = _w(j)
    w['ol'] = ms
    return _tick(w, 'os', ms, OAQ_SPAM_MS) >= OAQ_SPAM_GAMES


def oaq_move(j: dict, ms: int) -> bool:
    """A move of the game being played arrives now: True when too many moves came too fast. A game started before
    this build (no clock yet) only starts counting from its next move."""
    w = _w(j)
    last = w.get('ol')
    w['ol'] = ms
    if last is None or not 0 <= ms - last < OAQ_FAST_MS:
        return False
    return _tick(w, 'of', ms, OAQ_FAST_WINDOW_MS) >= OAQ_FAST_MOVES


def clear(j: dict, *keys: str) -> None:
    """After an arrest: the windows it came from start afresh."""
    w = _w(j)
    for k in keys:
        w.pop(k, None)


def validate(j: dict) -> None:
    if KEY not in j:
        return
    from .engine import need, integer
    bad = 'Dữ liệu chợ đen không hợp lệ.'
    w = j[KEY]
    need(isinstance(w, dict) and set(w) <= set(KEYS), bad, 'invalid_save')
    for k in WINDOWS:
        if k in w:
            c = w[k]
            need(isinstance(c, list) and len(c) == 2, bad, 'invalid_save')
            integer(c[0], 0, MS_MAX)
            integer(c[1], 0, COUNT_MAX)
    if 'ol' in w:
        integer(w['ol'], 0, MS_MAX)
