"""🌧️ Danh hiệu độc nhất: an honour the admin gives to one player by name, that nobody else can get, buy, win or copy.

The owner (24/10): "cho mnt2410 cái khung mưa rơi đi, xong rồi cái danh hiệu Cuồng Vũ Tán Tiên. làm độc nhất nhé".

How it is held
* EXCLUSIVE below maps an honour id (`ex_<name>`) to the one account it belongs to (accounts.username, lower case,
  unique, never renamed) and what it shows: a title (emoji + name) and the frame that goes with it. The account is
  looked up by its username in the accounts table (its sid, cached HOLDERS_SECONDS), and only an account made before
  `before` (UTC, accounts.created_at) counts: a username freed by a deleted account and taken again gets nothing.
* Nothing is written into a save: it cannot be traded, imported, copied or restored from a backup into another save.
  Granting another one is a new row here and a release; taking one back is removing its row (ids are never reused).
* The frame is chosen like any other (Hành trình → Danh hiệu → Khung: journey.hf_pick = the id, game/journey.py
  HF_PICK_RE allows `ex_…`): `check_pick` refuses the choice to anybody else inside the command's transaction
  (game/storage.py), and live/honours.py only ever puts an id in `tt` for its holder, so a save that carries the id
  anyway (an edited import) shows nothing.

Where it shows: `tt` beside the name (live/honours.py: chat, cards, walkers, the fishing lake; first of all, before the
auction titles), the street's name tag (live/street.py title_of), the town's name tag (live/town.py `tt`), the boards'
rows (`ex` on a row, game/leaderboard.py and the other boards), Phố nghề (game/social.py `rank`), the player's own
card and frame chooser (GET /api/bootstrap `ex_titles`). The client's copy of the table: public/js/v4/exclusive.js
(tests/test_exclusive.py compares them).
"""
from __future__ import annotations

import threading
import time

PREFIX = 'ex_'
LABEL = 'Độc nhất'
EXCLUSIVE = {
    # 24/10 (owner): Mưa (mnt2410) — the title "Cuồng Vũ Tán Tiên" and the frame "Mưa rơi", one of a kind.
    'ex_cuong_vu': dict(username='mnt2410', before='2026-10-25', emoji='🌧️', name='Cuồng Vũ Tán Tiên', frame='Mưa rơi'),
}
HOLDERS_SECONDS = 300.0         # how long a process trusts its copy of the holders (an account's sid never changes)


def ids_sql() -> tuple:
    """(sql, args) reading the accounts the table names (used here and by the live service)."""
    names = sorted({x['username'] for x in EXCLUSIVE.values()})
    return f"SELECT sid, username, created_at FROM accounts WHERE username IN ({','.join('?' * len(names))})", names


def from_rows(rows) -> dict:
    """{sid: [ids]} from rows of ids_sql(): each id to the account with its username made before its date."""
    out: dict = {}
    by_name = {}
    for r in rows or ():
        by_name[str(r['username']).lower()] = r
    for xid, x in EXCLUSIVE.items():
        r = by_name.get(x['username'])
        if r is None or not r['sid'] or not str(r['created_at'] or '') or str(r['created_at']) >= x['before']:
            continue
        out.setdefault(r['sid'], []).append(xid)
    return out


def title(xid: str) -> dict | None:
    """{id, emoji, name, text, frame, label} of an exclusive honour, or None."""
    x = EXCLUSIVE.get(xid) if isinstance(xid, str) else None
    if x is None:
        return None
    return dict(id=xid, emoji=x['emoji'], name=x['name'], text=f"{x['emoji']} {x['name']}", frame=x['frame'], label=LABEL)


def text_of(tt) -> str | None:
    """The title text of the first exclusive honour among `tt` ids (the street's name tag), or None."""
    for xid in tt or ():
        t = title(xid)
        if t:
            return t['text']
    return None


# ---------------------------------------------------------------- reading (cached per process)
_cache: dict = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _key(store) -> str:
    return str(getattr(store, 'path', None) or id(store))


def holders(store) -> dict:
    """{sid: [ids]}: who holds which exclusive honour (empty when the table names nobody or the read fails)."""
    if not EXCLUSIVE:
        return {}
    t, key = time.monotonic(), _key(store)
    with _lock:
        hit = _cache.get(key)
        if hit and t - hit[0] < HOLDERS_SECONDS:
            return hit[1]
    sql, args = ids_sql()
    try:
        with store.connect() as db:
            out = from_rows(db.execute(sql, args).fetchall())
    except Exception:  # noqa: BLE001 - a page never fails because of this
        return {}
    with _lock:
        if len(_cache) > 32:
            _cache.clear()
        _cache[key] = (t, out)
    return out


def held(store, sid: str | None) -> list:
    """[{id, emoji, name, text, frame, label}] this save holds (empty for nobody)."""
    if not sid:
        return []
    return [t for t in map(title, holders(store).get(sid, ())) if t]


def holds(db, sid: str | None, xid: str) -> bool:
    """Inside a transaction: does this save hold `xid` (read now, no cache)."""
    if not sid or xid not in EXCLUSIVE:
        return False
    sql, args = ids_sql()
    return xid in from_rows(db.execute(sql, args).fetchall()).get(sid, ())


def mark(row: dict, sid: str | None, ex: dict) -> dict:
    """A board's row with `ex` {id, emoji, name} when its player holds an exclusive honour (`ex`: holders())."""
    got = ex.get(sid) if sid else None
    t = title(got[0]) if got else None
    if t:
        row['ex'] = dict(id=t['id'], emoji=t['emoji'], name=t['name'])
    return row


def check_pick(db, sid: str, state: dict) -> None:
    """jr_frame (game/storage.py, in the command's transaction): an exclusive frame is worn by its holder only. A
    GameError rolls the command back."""
    j = state.get('journey') if isinstance(state, dict) else None
    v = j.get('hf_pick') if isinstance(j, dict) else None
    if isinstance(v, str) and v.startswith(PREFIX):
        from .engine import need
        need(holds(db, sid, v), 'Khung này là độc nhất, chỉ người được tặng mới đeo được.', 'not_yours')
