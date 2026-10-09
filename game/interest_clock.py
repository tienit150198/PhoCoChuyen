"""⏱️ Interest days run on real time (owner 09/10): 1 real hour = 1 interest day.

Ending in-game days is free and fast (an empty day takes seconds), while the bank's year is 60 life days, so
interest paid per life day could be farmed: one save ended 2,549 empty days in 42 hours and its 3-year terms
renewed into ~146M xu. From now on a save earns interest on at most as many life days as real hours allow:

* an allowance (a token bucket) refilled with RATE interest days per real hour, banked up to CAP (about a week of
  hours away: an honest player who comes back and plays a long evening is never short);
* each new life day (journey.life_day moving on) takes one token; a day without a token still passes (bills, loans,
  cards, the rest of the morning run as before) but pays NO interest on the bank's savings (demand pot, term
  deposits: those days are taken out of the term's interest) nor on the invest savings book (invest.py);
* Mây Coin is a market price, not interest: untouched.

Rollback safety: the bank's and the invest's own day cursors still advance every day exactly as before, so an older
build loading a save from this one has nothing to catch up. The allowance lives in an OPTIONAL journey key (KEY):
journey.validate of every build accepts extra keys (`set(initial()) <= set(j)`), and a save without it simply starts
a full bucket.

KEY {v, s, d, t, at, x, w, n, a}:
  s   the life day the allowance began for this save (days before it were paid by the old rules: the audit
      script, scripts/bank_audit_reclaim.py, looks only at those);
  d   the last life day the allowance decided (a day n <= d is decided once and for all);
  t   whole interest days left in the bucket (0..CAP); at: epoch second the next refill counts from;
  x   [[lo, hi], ...] life days (mornings) lo..hi that earned no interest, oldest first (the last KEEP_DAYS);
  w, n, a  the day-skip alert: real-time window start, life days ended in it, alert written for it.

The alert: a save that ends more than ALERT_DAYS life days within one real day writes one line to the server log
("[day-skip] ..."), once per window.
"""
from __future__ import annotations

import sys
import time

KEY = 'iclock'
VERSION = 1
RATE_SECONDS = 3600      # one interest day per real hour
CAP = 168                # banked at most: a week of hours
KEEP_DAYS = 400          # forfeited ranges kept (the bank's catch-up limit; the longest term is 180 days)
RANGES_MAX = 400
ALERT_DAYS = 150         # life days ended within one real day before the log line
ALERT_WINDOW = 86400


def now() -> float:
    return time.time()


def _valid(c) -> bool:
    return (isinstance(c, dict) and c.get('v') == VERSION and set(c) == {'v', 's', 'd', 't', 'at', 'x', 'w', 'n', 'a'}
            and all(type(c[k]) is int for k in ('s', 'd', 't', 'at', 'w', 'n')) and type(c['a']) is bool
            and isinstance(c['x'], list) and all(isinstance(r, list) and len(r) == 2 and all(type(v) is int for v in r) for r in c['x']))


def _fresh(day: int, t: int) -> dict:
    return dict(v=VERSION, s=int(day), d=int(day), t=CAP, at=t, x=[], w=t, n=0, a=False)


def get(s: dict) -> dict | None:
    """The allowance block when the save has a valid one (read only)."""
    j = s.get('journey') if isinstance(s, dict) else None
    c = j.get(KEY) if isinstance(j, dict) else None
    return c if _valid(c) else None


def _refill(c: dict, t: int) -> None:
    if t <= c['at']:
        return
    hours = (t - c['at']) // RATE_SECONDS
    c['t'] = min(CAP, c['t'] + hours)
    c['at'] = t if c['t'] >= CAP else c['at'] + hours * RATE_SECONDS


def _forfeit(c: dict, n: int) -> None:
    if c['x'] and c['x'][-1][1] == n - 1:
        c['x'][-1][1] = n
    else:
        c['x'].append([n, n])


def _alert(s: dict, c: dict, days: int, t: int) -> None:
    if t - c['w'] >= ALERT_WINDOW or t < c['w']:
        c.update(w=t, n=0, a=False)
    c['n'] = min(10**6, c['n'] + days)
    if c['n'] > ALERT_DAYS and not c['a']:
        c['a'] = True
        j = s['journey']
        b = j.get('bank') if isinstance(j.get('bank'), dict) else {}
        try:
            sys.stderr.write(f"[day-skip] name={str(s.get('name') or '-')[:24]!r} seed={j.get('seed')} acct={b.get('no', '-')} "
                             f"life_day={j.get('life_day')} days_in_real_day={c['n']} since={int(c['w'])}\n")
        except Exception:   # noqa: BLE001 - a log line never fails a command
            pass


def sync(s: dict) -> dict | None:
    """Decide the life days up to journey.life_day (idempotent: each day once). Call before paying a day's interest."""
    j = s.get('journey')
    if not isinstance(j, dict) or type(j.get('life_day')) is not int:
        return None
    day = j['life_day']
    t = int(now())
    c = j.get(KEY)
    if not _valid(c):
        c = j[KEY] = _fresh(day, t)
        return c
    if day < c['d']:   # a save reset to an earlier day: start deciding from there
        c['d'] = day
        c['s'] = min(c['s'], day)
        c['x'] = [r for r in c['x'] if r[1] < day]
        return c
    if day == c['d']:
        return c
    _refill(c, t)
    new = day - c['d']
    for n in range(c['d'] + 1, day + 1):
        if c['t'] > 0:
            c['t'] -= 1
        else:
            _forfeit(c, n)
    c['d'] = day
    c['x'] = [r for r in c['x'] if r[1] > day - KEEP_DAYS][-RANGES_MAX:]
    _alert(s, c, new, t)
    return c


def paid(s: dict, n: int) -> bool:
    """Life day (morning) n earns interest."""
    c = get(s)
    if not c:
        return True
    return not any(lo <= n <= hi for lo, hi in c['x'])


def forfeited(s: dict, lo: int, hi: int) -> int:
    """How many life days (mornings) in lo < n <= hi earned no interest."""
    c = get(s)
    if not c or hi <= lo:
        return 0
    return sum(max(0, min(hi, b) - max(lo + 1, a) + 1) for a, b in c['x'])


def validate(s: dict) -> None:
    """The optional block: absent, or well formed."""
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    from . import engine as e
    c = j[KEY]
    e.need(_valid(c), 'Dữ liệu ngày tính lãi không hợp lệ.', 'invalid_save')
    e.integer(c['s'], 1, 10**6)
    e.integer(c['d'], 1, 10**6)
    e.integer(c['t'], 0, CAP)
    e.integer(c['at'], 0, 2**40)
    e.integer(c['w'], 0, 2**40)
    e.integer(c['n'], 0, 10**6)
    e.need(len(c['x']) <= RANGES_MAX and all(1 <= a <= b <= 10**6 for a, b in c['x']), 'Dữ liệu ngày tính lãi không hợp lệ.', 'invalid_save')
