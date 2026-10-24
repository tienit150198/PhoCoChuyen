"""🎣 The fishing boards, the species records and the town ticker line (game/fishing.py catches).

Owner 24/10: "🐋 Cá lớn nhất: each player's single heaviest fish … all-time and weekly, per species the holder (kỷ lục
loài) shown in Sổ cá; 📖 Bộ sưu tập cá: players ranked by species collected, tie-break by rarer species first, then who
got there first", each with weekly titles, frames and rewards like the other boards (game/lb_titles.py).

Tables (SCHEMA_VERSION 93, game/pg_schema.py), written in the save's own transaction by a jr_fish_land that keeps a fish:
* fish_best (sid, week): the heaviest fish of a player, week 'all' (all time) and 'YYYY-Www' (that Vietnam week).
* fish_dex (sid): species caught, the counts per rarity and a sort key `k` (species, then 🔴 … ⚪ counts), `at` when `n`
  last moved (who got there first).
* fish_rec (sp): each species' heaviest catch in town and who holds it.
Names follow the boards' privacy (game/leaderboard.py _VISIBLE); a hidden player still sees his own place.
Boards: 'fish_big' (this week's heaviest: titles, frozen with the week), 'fish_all' (all time, no titles), 'fish_dex'
(the collection: titles taken from the standings each day, like 🪽 Cánh).
"""
from __future__ import annotations

import json
import threading
import time

from . import fishing_content as C

BIG, ALL, DEX = 'fish_big', 'fish_all', 'fish_dex'
BOARDS = (BIG, ALL, DEX)
CACHE_SECONDS = 30.0
TOP_READ = 50
BITS = 5                      # per rarity count in the sort key (a tier holds < 32 species)


def now() -> float:
    return time.time()


def _week(t: float) -> str:
    from .wedding_live import vn_week
    return vn_week(t)


# ---------------------------------------------------------------- the collection's key
def dex_row(s: dict) -> dict | None:
    """{n, rc (counts per rarity), k} of the species a save has caught, or None for none."""
    d = (s.get('journey') or {}).get('fish') if isinstance(s, dict) else None
    dex = d.get('dex') if isinstance(d, dict) else None
    if not isinstance(dex, dict):
        return None
    rc = [0] * C.NR
    for sp, v in dex.items():
        x = C.SPECIES.get(sp)
        if x and isinstance(v, list) and v and type(v[0]) is int and v[0] > 0:
            rc[x['r']] += 1
    n = sum(rc)
    if not n:
        return None
    return dict(n=n, rc=rc, k=key_of(n, rc))


def key_of(n: int, rc: list) -> int:
    """Species first, then the rarest counts (🔴 Cổ đại, 🟡 …, ⚪)."""
    k = n
    for r in range(C.NR - 1, -1, -1):
        k = (k << BITS) | min(rc[r], 2**BITS - 1)
    return k


_BEST = ('INSERT INTO fish_best(sid, week, sp, g, r, at) VALUES(?,?,?,?,?,?) ON CONFLICT (sid, week) DO UPDATE SET '
         'sp=EXCLUDED.sp, g=EXCLUDED.g, r=EXCLUDED.r, at=EXCLUDED.at WHERE fish_best.g < EXCLUDED.g')
_REC = ('INSERT INTO fish_rec(sp, sid, g, at) VALUES(?,?,?,?) ON CONFLICT (sp) DO UPDATE SET sid=EXCLUDED.sid, g=EXCLUDED.g, '
        'at=EXCLUDED.at WHERE fish_rec.g < EXCLUDED.g')
_DEX = ('INSERT INTO fish_dex(sid, n, k, rc, at) VALUES(?,?,?,?,?) ON CONFLICT (sid) DO UPDATE SET '
        'at=CASE WHEN fish_dex.n<>EXCLUDED.n THEN EXCLUDED.at ELSE fish_dex.at END, n=EXCLUDED.n, k=EXCLUDED.k, rc=EXCLUDED.rc '
        'WHERE (fish_dex.n, fish_dex.k) IS DISTINCT FROM (EXCLUDED.n, EXCLUDED.k)')


NEWS_GAP_S = 600          # 2.6.5: better rods land 🔴 Cổ đại often (≈2.7 an hour on Cần Long Vương): at most one fish line on
NEWS_SELF_S = 3600        # the town ticker every 10 minutes, and one a player an hour, so weddings and the rest still show


def _news_room(db, sid: str) -> bool:
    """Room on the ticker for a fish line (the newest rows by primary key, never a scan)."""
    t, mine = now(), f'fish:{sid[:16]}:'
    for row in db.execute('SELECT kind, ref, at FROM news ORDER BY id DESC LIMIT 200').fetchall():
        if row['kind'] != 'fish':
            continue
        if t - row['at'] < NEWS_GAP_S:
            return False
        if str(row['ref']).startswith(mine) and t - row['at'] < NEWS_SELF_S:
            return False
    return True


def write_dex(db, sid: str, s: dict, at: float) -> None:
    row = dex_row(s)
    if row:
        db.execute(_DEX, (sid, row['n'], row['k'], json.dumps(row['rc'], separators=(',', ':')), at))


def on_catch(db, sid: str, after: dict, catch: dict, result: dict) -> None:
    """A kept fish (game/fishing.py command_commit): the player's best of all time and of the week, the species record,
    the collection row, and a 🔴 Cổ đại line on the ticker. A beaten town record shows on the catch card."""
    t = float(catch.get('at') or now())
    sp, g, r = catch['s'], int(catch['g']), int(catch['r'])
    for week in ('all', _week(t)):
        db.execute(_BEST, (sid, week, sp, g, r, t))
    if db.execute(_REC, (sp, sid, g, t)).rowcount == 1:
        catch['rec'] = True
        result.setdefault('effects', []).append('🏆 Kỷ lục loài của cả phố!')
    write_dex(db, sid, after, t)
    clear_cache()
    if r >= C.NEWS_MIN and _news_room(db, sid):
        from . import forge_news, lux, marriage
        from .fishing import fmt_kg
        who = lux._display(db, sid, forge_news.hidden(after))
        info = C.SPECIES[sp]
        text = f'🎣 {who} vừa câu được {C.RARITIES[r]["emoji"]} {info["name"]} {fmt_kg(g)} ở {C.SPOTS[catch["spot"]]["name"]}! Cả phố trầm trồ!'
        if marriage._post_news(db, 'fish', f'fish:{sid[:16]}:{catch["i"]}', text, '', ''):
            catch['news'] = True


def forget(db, sid: str) -> None:
    for table in ('fish_best', 'fish_dex'):
        db.execute(f'DELETE FROM {table} WHERE sid=?', (sid,))
    db.execute('DELETE FROM fish_rec WHERE sid=?', (sid,))


# ---------------------------------------------------------------- reading
_SEL_BEST = ('SELECT b.sid, b.sp, b.g, b.r, b.at, a.display, p.name AS gname, a.uid IS NOT NULL AS acct '
             'FROM fish_best b LEFT JOIN accounts a ON a.sid=b.sid LEFT JOIN leaderboard_players p ON p.sid=b.sid ')
_ORD_BEST = 'ORDER BY b.g DESC, b.at, b.sid'
_SEL_DEX = ('SELECT b.sid, b.n, b.k, b.rc, b.at, a.display, p.name AS gname, a.uid IS NOT NULL AS acct '
            'FROM fish_dex b LEFT JOIN accounts a ON a.sid=b.sid LEFT JOIN leaderboard_players p ON p.sid=b.sid ')
_ORD_DEX = 'ORDER BY b.k DESC, b.at, b.sid'


def _ranked(db, board: str, n: int, week: str | None = None) -> list:
    from .leaderboard import _VISIBLE
    if board == DEX:
        return db.execute(_SEL_DEX + f'WHERE {_VISIBLE} {_ORD_DEX} LIMIT ?', (n,)).fetchall()
    return db.execute(_SEL_BEST + f'WHERE b.week=? AND {_VISIBLE} {_ORD_BEST} LIMIT ?', (week or 'all', n)).fetchall()


def standings(db, board: str, t: float, n: int) -> list:
    """[(board, rank, sid, score)] (game/lb_titles.py): 🐋 the week of `t` (grams), 📖 the collection now (species)."""
    if board == BIG:
        return [(BIG, i + 1, r['sid'], int(r['g'])) for i, r in enumerate(_ranked(db, BIG, n, _week(t)))]
    return [(DEX, i + 1, r['sid'], int(r['n'])) for i, r in enumerate(_ranked(db, DEX, n))]


def _counts(raw) -> list:
    try:
        v = json.loads(raw or '[]')
    except (TypeError, ValueError):
        v = []
    v = [x if type(x) is int and x > 0 else 0 for x in v][:C.NR] if isinstance(v, list) else []
    return v + [0] * (C.NR - len(v))


def _row(board: str, r) -> dict:
    guest = not r['acct']
    out = dict(name=r['gname'] if guest else r['display'], guest=guest)
    if board == DEX:
        out.update(score=int(r['n']), rc=_counts(r['rc']))
    else:
        out.update(score=int(r['g']), sp=r['sp'], r=int(r['r']), at=float(r['at']))
    return out


_cache: dict = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _board(store, board: str, week: str) -> tuple[list, int]:
    key = (id(store), board, week)
    mono = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and mono - hit[0] < CACHE_SECONDS:
            return hit[1], hit[2]
    from .leaderboard import _VISIBLE
    with store.connect() as db:
        rows = _ranked(db, board, TOP_READ, week)
        if board == DEX:
            total = db.execute('SELECT COUNT(*) FROM fish_dex b LEFT JOIN accounts a ON a.sid=b.sid '
                               f'LEFT JOIN leaderboard_players p ON p.sid=b.sid WHERE {_VISIBLE}').fetchone()[0]
        else:
            total = db.execute('SELECT COUNT(*) FROM fish_best b LEFT JOIN accounts a ON a.sid=b.sid '
                               f'LEFT JOIN leaderboard_players p ON p.sid=b.sid WHERE b.week=? AND {_VISIBLE}', (week,)).fetchone()[0]
    out = [(r['sid'], _row(board, r)) for r in rows]
    with _lock:
        if len(_cache) > 16:
            _cache.clear()
        _cache[key] = (mono, out, int(total))
    return out, int(total)


def view(store, board: str, limit: int, token: str | None = None) -> dict:
    """GET /api/leaderboard?board=fish_big|fish_all|fish_dex: the top `limit`, the viewer's own place (also when hidden)
    and the weekly titles (not for all time)."""
    from . import lb_titles as lbt
    from .leaderboard import _privacy, _viewer, _VISIBLE
    lbt.ensure(store)
    week = _week(now()) if board == BIG else 'all'
    top, total = _board(store, board, week)
    sid = _viewer(store, token)
    holders = lbt.holders(store) if board != ALL else {}
    rows = []
    for i, (row_sid, r) in enumerate(top[:limit]):
        row = dict(r, rank=i + 1, me=row_sid == sid)
        mine = [h for h in holders.get(row_sid, ()) if h['board'] == board]
        if mine:
            row['title'] = dict(emoji=mine[0]['emoji'], name=mine[0]['name'])
        rows.append(row)
    me = None
    if sid:
        with store.connect() as db:
            me = _privacy(db, sid)
            if board == DEX:
                own = db.execute(_SEL_DEX + 'WHERE b.sid=?', (sid,)).fetchone()
                if own:
                    ahead = db.execute('SELECT COUNT(*) FROM fish_dex b LEFT JOIN accounts a ON a.sid=b.sid LEFT JOIN leaderboard_players p '
                                       f'ON p.sid=b.sid WHERE {_VISIBLE} AND b.sid<>? AND (b.k>? OR b.k=? AND (b.at<? OR b.at=? AND b.sid<?))',
                                       (sid, own['k'], own['k'], own['at'], own['at'], sid)).fetchone()[0]
            else:
                own = db.execute(_SEL_BEST + 'WHERE b.week=? AND b.sid=?', (week, sid)).fetchone()
                if own:
                    ahead = db.execute('SELECT COUNT(*) FROM fish_best b LEFT JOIN accounts a ON a.sid=b.sid LEFT JOIN leaderboard_players p '
                                       f'ON p.sid=b.sid WHERE b.week=? AND {_VISIBLE} AND b.sid<>? AND (b.g>? OR b.g=? AND (b.at<? OR b.at=? AND b.sid<?))',
                                       (week, sid, own['g'], own['g'], own['at'], own['at'], sid)).fetchone()[0]
            if own:
                r = _row(board, own)
                r.pop('name', None)
                r.pop('guest', None)
                me.update(r, rank=1 + int(ahead))
            else:
                me['rank'] = None
        me.pop('show', None)
        me['titles'] = [dict(emoji=h['emoji'], name=h['name'], board=h['board'], label=h['label']) for h in holders.get(sid, ())]
    weekly = None
    if board != ALL:
        try:
            weekly = lbt.board_view(store, board, sid)
        except Exception:  # noqa: BLE001 - the board still shows without its weekly block
            weekly = None
    return dict(board=board, total=total, rows=rows, me=me, weekly=weekly, week=week)


def records(store, token: str | None = None) -> dict:
    """GET /api/fish/records: each species' town record {sp: {g, name, me}} (Sổ cá) and the top 3 of each board (the
    📖 Bảng bộ sưu tập stand at the lake)."""
    from .leaderboard import _viewer, GUEST_DEFAULT
    sid = _viewer(store, token)
    key = (id(store), 'rec')
    mono = time.monotonic()
    with _lock:
        hit = _cache.get(key)
    if hit and mono - hit[0] < CACHE_SECONDS:
        rows = hit[1]
    else:
        with store.connect() as db:
            rows = [dict(r) for r in db.execute(
                'SELECT f.sp, f.g, f.sid, a.display, p.name AS gname, p.show, a.uid IS NOT NULL AS acct FROM fish_rec f '
                'LEFT JOIN accounts a ON a.sid=f.sid LEFT JOIN leaderboard_players p ON p.sid=f.sid').fetchall()]
        with _lock:
            _cache[key] = (mono, rows)
    out = {}
    for r in rows:
        if r['sp'] not in C.SPECIES:
            continue
        account = bool(r['acct'])
        name = r['display'] if account else r['gname']
        show = r['show'] if r['show'] is not None else (1 if account else GUEST_DEFAULT)
        out[r['sp']] = dict(g=int(r['g']), name=name if name and (show or r['sid'] == sid) else 'Một người chơi', me=r['sid'] == sid)
    tops = {}
    for board in BOARDS:
        week = _week(now()) if board == BIG else 'all'
        top, _ = _board(store, board, week)
        tops[board] = [dict(rank=i + 1, me=s == sid, **r) for i, (s, r) in enumerate(top[:3])]
    return dict(records=out, tops=tops)
