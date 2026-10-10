"""One server-authorized, 48-hour promotion for three virtual-xu luck stalls.

Activation is an immutable mnl_meta row. Deploying/restarting a worker never starts
or extends it. Each eligible command reads that row through fair.loc_prepare;
the reducer checks its own server time before drawing. No player-supplied data
can activate it. Saved journey metadata is only for the public hint after reload.

Winning means a positive-net main game outcome: scratch event wins use prizes
above a refund; loto still requires correct, timely Kinh. Existing police, fees,
and skill/honest-dice/fixed-odds games retain their rules.
"""
from __future__ import annotations

import contextvars

KEY = 'fair_golden_days_20261011'
DISPLAY_KEY = 'fair_golden_days'
DURATION = 48 * 60 * 60
WIN_P = .70                    # server only; never include in public/status data
GAMES = ('xd', 'lt', 'xs')
ACTIONS = ('fair_xd', 'fair_loto_buy', 'fair_xs')
TITLE = '2 ngày vàng, tăng tỷ lệ thắng cược Chợ Đen'
_starts = contextvars.ContextVar('fair_golden_days_start', default=None)


def _start(value) -> int | None:
    try:
        start = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return start if 0 < start < 4102444800 - DURATION else None


def _read(db) -> int | None:
    row = db.execute('SELECT value FROM mnl_meta WHERE key=?', (KEY,)).fetchone()
    return _start(row[0]) if row else None


def _now(db) -> int:
    return int(db.execute('SELECT EXTRACT(EPOCH FROM statement_timestamp())').fetchone()[0])


def status(db, *, at: float | None = None) -> dict:
    """Administrative status; no draw probabilities or player information."""
    start = _read(db)
    t = _now(db) if at is None else at
    return dict(id=KEY, title=TITLE, active=start is not None and start <= t < start + DURATION,
                starts=start, ends=start + DURATION if start is not None else None)


def activate(db, *, at: int | None = None) -> dict:
    """Insert once inside the caller's transaction. Retrying never renews an event.

    Production callers omit at and use the database clock; at is for controlled
    tests. Concurrent activators share the row chosen by the first committed insert.
    """
    start = _now(db) if at is None else at
    if type(start) is not int or _start(start) is None:
        raise ValueError('Invalid golden-days start')
    row = db.execute('INSERT INTO mnl_meta (key, value) VALUES (?, ?) '
                     'ON CONFLICT (key) DO NOTHING RETURNING value', (KEY, str(start))).fetchone()
    result = status(db, at=start)
    if result['starts'] is None:
        raise ValueError('Existing golden-days activation is invalid; refusing to replace it')
    return dict(result, created=row is not None)


def clear() -> None:
    _starts.set(None)


def prepare(db, action: str) -> None:
    """Reset every command, including unrelated commands and missing/invalid rows.

    No worker cache: activation is seen on the next eligible command everywhere.
    A failed read leaves the old context cleared and fails the command normally.
    """
    clear()
    if action in ACTIONS:
        _starts.set(_read(db))


def active(game: str, t: float) -> bool:
    start = _starts.get()
    return game in GAMES and start is not None and start <= t < start + DURATION


def mark_display(j: dict) -> None:
    """Only the server's prepared window is saved. It never authorizes a draw."""
    start = _starts.get()
    if start is not None:
        j[DISPLAY_KEY] = dict(id=KEY, starts=start)


def public(j: dict, t: float) -> dict | None:
    """A previously played event's label/end survive reload, with no odds fields."""
    marker = j.get(DISPLAY_KEY)
    if not isinstance(marker, dict) or marker.get('id') != KEY or type(marker.get('starts')) is not int:
        return None
    start = _start(marker['starts'])
    if start is None or not start <= t < start + DURATION:
        return None
    return dict(title=TITLE, starts=start, ends=start + DURATION, games=list(GAMES))
