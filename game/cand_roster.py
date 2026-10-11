"""👮 Công an phường Mây across players (owner spec 11/10): the roster of every player on the CAND ladder, one row per
save, kept by the save's own command transaction (command_commit, like jail_marks). It answers:

* the seats (org_content.SEATS: Phó Giám đốc CATP ≤ 5 players, Giám đốc CATP ≤ 1): a post with a cap is appointed only
  while fewer players hold it (org.close / org.answer read full(); command_commit checks again under the row lock);
* the commanders' lists (game/cand_ops.py): who is on the force, who carries a grave fault (sev) a commander may expel
  for.

A seat holder who has not played for SEEN_DAYS real days no longer counts (the seat is free for the next appointment;
the holder keeps the post). Not in the save: an older build never sees the table.
"""
from __future__ import annotations

import threading
import time

from . import org as ORG
from . import org_content as OC

CAREER = 'police'
ORG_ID = 'cand'
SEEN_DAYS = 14
TOUCH_S = 6 * 3600        # a seat holder's row is refreshed at most this often
CACHE_S = 60              # the seat counts a worker keeps for the screens
DECIDE = ('pm_answer', 'end_day')   # the actions that may appoint: their counts are read fresh

_lock = threading.Lock()
_cache: dict = dict(at=0.0, n={})
_touched: dict = {}


def now() -> float:
    return time.time()


def info(state) -> dict | None:
    """(post, grade, sev, out) of a save on the CAND ladder now, else None."""
    if not isinstance(state, dict):
        return None
    c = (state.get('careers') or {}).get(CAREER)
    rec = (((state.get('journey') or {}).get('promo') or {}).get(CAREER)) if isinstance(state.get('journey'), dict) else None
    if not isinstance(c, dict) or not isinstance(rec, dict):
        return None
    x = ORG.active(CAREER, c, rec)
    if not x or x.get('org') != ORG_ID:
        return None
    e = rec.get('cx') if isinstance(rec.get('cx'), dict) else {}
    sev = max((int(r.get('t') or 0) for r in e.get('sev') or ()), default=0)
    code = next((r.get('c') for r in reversed(e.get('sev') or ()) if int(r.get('t') or 0) == sev), '') if sev else ''
    return dict(post=x['p'], grade=OC.ORGS[ORG_ID]['grades'][x['g']]['id'], sev=sev, code=code or '')


def _counts(db) -> dict:
    cut = now() - SEEN_DAYS * 86400
    rows = db.execute('SELECT post, COUNT(*) AS n FROM cand_roster WHERE seen>=? GROUP BY post', (cut,)).fetchall()
    return {r['post']: int(r['n']) for r in rows}


def prepare(db, action: str) -> None:
    """Before a command: the seat counts (fresh for an action that may appoint, else at most CACHE_S old)."""
    t = now()
    if action not in DECIDE and t - _cache['at'] < CACHE_S:
        return
    try:
        n = _counts(db)
    except Exception:  # noqa: BLE001 - no table yet (an older schema, tests without it): no caps known
        return
    with _lock:
        _cache.update(at=t, n=n)


def holders(post: str) -> int:
    return int(_cache['n'].get(post, 0))


def full(post: str) -> bool:
    cap = OC.SEATS.get(post)
    return cap is not None and holders(post) >= cap


def command_commit(db, sid: str, before, after, action: str = '') -> None:
    """The roster row follows the save, in its transaction. A new appointment to a capped post is checked again here:
    two appointments at once never pass the cap together."""
    commit_info(db, sid, info(before), after)


def commit_info(db, sid: str, a: dict | None, after) -> None:
    """command_commit with the save before already read (info(before)): marriage._mutate keeps only that."""
    b = info(after)
    if b is None:
        if a is not None:
            db.execute('DELETE FROM cand_roster WHERE sid=?', (sid,))
            _touched.pop(sid, None)
        return
    t = now()
    if a == b and t - _touched.get(sid, 0) < TOUCH_S:
        return
    name = str((after or {}).get('name') or '')[:40]
    db.execute('INSERT INTO cand_roster(sid,name,post,grade,seen,sev,sev_code) VALUES(?,?,?,?,?,?,?) '
               'ON CONFLICT(sid) DO UPDATE SET name=excluded.name,post=excluded.post,grade=excluded.grade,seen=excluded.seen,'
               'sev=excluded.sev,sev_code=excluded.sev_code', (sid, name, b['post'], b['grade'], t, b['sev'], b['code']))
    _touched[sid] = t
    if len(_touched) > 5000:
        _touched.clear()
    cap = OC.SEATS.get(b['post'])
    if cap is not None and (a is None or a['post'] != b['post']):
        n = db.execute('SELECT COUNT(*) AS n FROM cand_roster WHERE post=? AND seen>=?', (b['post'], t - SEEN_DAYS * 86400)).fetchone()['n']
        if int(n) > cap:
            from .engine import GameError
            raise GameError(f'Ghế {ORG._post(OC.ORGS[ORG_ID], b["post"])["short"]} vừa đủ {cap} người. Thử lại sau nhé.', 'seat_taken')


def roster(db, limit: int = 60) -> list[dict]:
    """The force, highest post first (the commanders' list)."""
    cut = now() - SEEN_DAYS * 86400
    rows = db.execute('SELECT sid,name,post,grade,seen,sev,sev_code FROM cand_roster WHERE seen>=? ORDER BY seen DESC LIMIT ?',
                      (cut, max(1, min(200, limit)))).fetchall()
    o = OC.ORGS[ORG_ID]
    order = {p['id']: i for i, p in enumerate(o['posts'])}
    out = [dict(r) for r in rows]
    out.sort(key=lambda r: (-order.get(r['post'], 0), r['name']))
    return out


def forget(db, sid: str) -> None:
    db.execute('DELETE FROM cand_roster WHERE sid=?', (sid,))
