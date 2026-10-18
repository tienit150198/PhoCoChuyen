"""🐾 Thú cưng on the main Bảng xếp hạng (owner 19/10: "bảng xếp hạng bên ngoài thêm bảng xếp hạng 'Thú cưng' nữa nhé,
thêm khung này kia thật đẹp vào nhé").

Each player's best pet by 💪 lực chiến: the pet_board rows with week POWER ('LC'), written in the save's own
transaction by game/pets.py _power_row (pts = power, acc = {r, top, x, lg, a}). Names follow the boards' privacy
(game/leaderboard.py _VISIBLE), unlike the pets sheet's own 🏆 board. Its weekly titles (top 1 / 2–3 / 4–10,
game/lb_titles.py BOARD_TITLES['pets']) are taken once a day like the other boards, from the same standings.

Nothing is stored here and the `leaderboard` table is not touched (no new formula, no rebuild): one indexed read of
the top rows (pet_board_week) per process every CACHE_SECONDS.
"""
from __future__ import annotations

import json
import threading
import time

PETS = 'pets'
POWER = 'LC'                # game/pets.py POWER
CACHE_SECONDS = 30.0
TOP_READ = 50               # rows read for the board (its LIMIT is at most game/leaderboard.py LIMIT)

_SELECT = ('SELECT b.sid, b.pts, b.name AS pn, b.breed, b.coat, b.acc, b.at, a.display, p.name AS gname, a.uid IS NOT NULL AS acct '
           'FROM pet_board b LEFT JOIN accounts a ON a.sid=b.sid LEFT JOIN leaderboard_players p ON p.sid=b.sid ')


def _ranked(db, n: int) -> list:
    from .leaderboard import _VISIBLE
    return db.execute(_SELECT + f'WHERE b.week=? AND {_VISIBLE} ORDER BY b.pts DESC, b.at, b.sid LIMIT ?', (POWER, n)).fetchall()


def standings(db, n: int) -> list:
    """[(board, rank, sid, power)] of the top `n` now (game/lb_titles.py)."""
    return [(PETS, i + 1, r['sid'], int(r['pts'])) for i, r in enumerate(_ranked(db, n))]


def _pet(r) -> dict:
    """The pet part of a row: name, breed, coat, rank, coat effect, legendary, accessories (checked like game/pets.py _rows)."""
    from . import pet_tiers as px
    from . import pets_content as C
    from . import pet_wardrobe
    try:
        raw = json.loads(r['acc'] or '{}')
    except (TypeError, ValueError):
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    rk = raw.get('r')
    br = C.BREEDS.get(r['breed']) or {}
    look = pet_wardrobe.row_look(raw)   # 👗 what it wears (wings, ranks, cute aura, set) and a 🌟 kept-breed legendary
    kept = look.pop('lg')
    return dict(pn=str(r['pn'] or '')[:C.NAME_MAX], b=r['breed'] if br else '', c=int(r['coat'] or 0),
                r=rk if type(rk) is int and 0 <= rk <= px.TOP else 0, x=raw.get('x') if raw.get('x') in px.FX_IDS else '',
                lg=br.get('fuse') == 'legend' or kept, kind=br.get('kind') or '', **look)


_cache: dict = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _board(store) -> tuple[list, int]:
    """([(sid, power, public row)], visible total), cached CACHE_SECONDS per process."""
    key = id(store)
    mono = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and mono - hit[0] < CACHE_SECONDS:
            return hit[1], hit[2]
    from .leaderboard import _VISIBLE
    with store.connect() as db:
        rows = _ranked(db, TOP_READ)
        total = int(db.execute('SELECT COUNT(*) FROM pet_board b LEFT JOIN accounts a ON a.sid=b.sid '
                               f'LEFT JOIN leaderboard_players p ON p.sid=b.sid WHERE b.week=? AND {_VISIBLE}', (POWER,)).fetchone()[0])
    out = []
    for r in rows:
        guest = not r['acct']
        out.append((r['sid'], int(r['pts']), dict(name=r['gname'] if guest else r['display'], guest=guest, score=int(r['pts']), **_pet(r))))
    with _lock:
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = (mono, out, total)
    return out, total


def view(store, limit: int, token: str | None = None) -> dict:
    """GET /api/leaderboard?board=pets: like game/leaderboard.py view(): the top `limit`, the viewer's own place
    (also when hidden) and the weekly titles."""
    from . import lb_titles as lbt
    from .leaderboard import _privacy, _viewer, _VISIBLE
    lbt.ensure(store)
    board, total = _board(store)
    sid = _viewer(store, token)
    holders = lbt.holders(store)
    rows = []
    for i, (row_sid, _, r) in enumerate(board[:limit]):
        row = dict(r, rank=i + 1, me=row_sid == sid)
        mine = [h for h in holders.get(row_sid, ()) if h['board'] == PETS]
        if mine:
            row['title'] = dict(emoji=mine[0]['emoji'], name=mine[0]['name'])
        rows.append(row)
    me = None
    if sid:
        with store.connect() as db:
            me = _privacy(db, sid)
            own = db.execute(_SELECT + 'WHERE b.week=? AND b.sid=?', (POWER, sid)).fetchone()
            if own:
                ahead = db.execute('SELECT COUNT(*) FROM pet_board b LEFT JOIN accounts a ON a.sid=b.sid '
                                   f'LEFT JOIN leaderboard_players p ON p.sid=b.sid WHERE b.week=? AND {_VISIBLE} AND b.sid<>? '
                                   'AND (b.pts>? OR b.pts=? AND (b.at<? OR b.at=? AND b.sid<?))',
                                   (POWER, sid, own['pts'], own['pts'], own['at'], own['at'], sid)).fetchone()[0]
                me.update(score=int(own['pts']), rank=1 + int(ahead), **_pet(own))
            else:
                me['rank'] = None
        me.pop('show', None)
        me['titles'] = [dict(emoji=h['emoji'], name=h['name'], board=h['board'], label=h['label']) for h in holders.get(sid, ())]
    try:
        weekly = lbt.board_view(store, PETS, sid)
    except Exception:  # noqa: BLE001 - the board still shows without its weekly block
        weekly = None
    return dict(board=PETS, total=total, rows=rows, me=me, weekly=weekly)
