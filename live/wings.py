"""🪽 Cánh (game/wings.py, owner 22/10 "cho cánh đẹp tí, có cả mode cũ và mode mới đều hiển thị được nhé"): the wing a
walker wears, drawn on their character on the old street (live/street.py) and on the 2.5D map (live/town.py).

Read from the game's table (wing_worn: the save writes it with every jr_pet_wing_* command, never a frame) and sent as an
optional `wg` = {k: style, r: tier 0 D … 7 Huyền thoại} beside the walker's look, only for a style this build knows. The
client draws it (public/js/v4/look.js paintWings); an older client ignores `wg`.

* Cheap, like live/charms.py: a bounded LRU of CACHE players, each entry kept TTL seconds, one indexed query per 500
  missing players, nothing on a movement frame.
* The game server announces a change with NOTIFY {op: 'wing', pids}: those entries are dropped and their walkers on screen
  get the new `wg` (a `mv` with `wg` on the map, a `wg` event on the street; null: none worn). 🪽 A flyer whose wings
  came off lands; a new tier flies at its own speed (`fl` in the `mv` on the map, an `rd` on the street).
* The table comes with SCHEMA_VERSION 90. Until it exists every lookup answers {} and it is looked for again every RETRY
  seconds, so this service and the game server roll out in any order.
"""
from __future__ import annotations

import time

from game.wings_content import INDEX, TOP

from .db import Error as DbError, log
from .limits import LRU
from .protocol import Feature

CACHE = 20000
TTL = 300.0
RETRY = 300.0


def frame(k, r) -> dict | None:
    """{k, r} of a row, or None for a style this build lacks or an odd tier."""
    if k in INDEX and type(r) is int and 0 <= r <= TOP:
        return dict(k=k, r=r)
    return None


class Wings:
    def __init__(self, app):
        self.app = app
        self.rows = LRU(CACHE)        # pid -> (fetched monotonic, wg | None)
        self.off_until = 0.0

    def forget(self, pid: str) -> None:
        self.rows.pop(pid, None)

    async def of(self, players) -> dict:
        """{pid: wg} for these players (Player objects: pid and sid); nobody wearing wings is left out."""
        mono = time.monotonic()
        out, miss = {}, {}
        for p in players:
            pid, sid = getattr(p, 'pid', None), getattr(p, 'sid', None)
            if not (isinstance(pid, str) and pid and isinstance(sid, str) and sid) or pid in out or pid in miss:
                continue
            hit = self.rows.get(pid)
            if hit is not None and mono - hit[0] < TTL:
                if hit[1]:
                    out[pid] = hit[1]
            else:
                miss[pid] = sid
        if not miss or mono < self.off_until or self.app.db is None:
            return out
        items = list(miss.items())
        for i in range(0, len(items), 500):
            part = items[i:i + 500]
            sids = [s for _, s in part]
            try:
                rows = await self.app.db.fetch(f"SELECT sid, k, r FROM wing_worn WHERE sid IN ({','.join('?' * len(sids))})", sids)
            except DbError as e:   # a database from before SCHEMA_VERSION 90: nobody wears wings yet
                log('wings:', type(e).__name__)
                self.off_until = mono + RETRY
                return out
            got = {r['sid']: frame(r['k'], int(r['r'])) for r in rows}
            for pid, sid in part:
                wg = got.get(sid)
                self.rows.put(pid, (mono, wg))
                if wg:
                    out[pid] = wg
        return out

    async def one(self, player) -> dict | None:
        return (await self.of([player])).get(player.pid)


def of_app(app) -> Wings:
    w = getattr(app, '_wings', None)
    if w is None:
        w = app._wings = Wings(app)
    return w


class WingFeature(Feature):
    """No frames of its own: NOTIFY {op: 'wing', pids} from the game server keeps the walkers' wings current."""
    name = 'wing'

    async def on_notify(self, e: dict):
        if e.get('op') != 'wing':
            return
        pids = {p for p in (e.get('pids') or [])[:20] if isinstance(p, str) and len(p) == 16}
        if not pids:
            return
        cache = of_app(self.app)
        for pid in pids:
            cache.forget(pid)
        town, street = self.app.by_name.get('town'), self.app.by_name.get('street')
        walkers = []
        if town is not None:
            from .town import PREFIX
            from .scale_sites import SITE_PREFIX
            for room in self.hub.rooms_with_prefix(PREFIX) + self.hub.rooms_with_prefix(SITE_PREFIX):
                walkers += [('town', room, w) for w in room.data.get('people', {}).values() if w.pid in pids]
        if street is not None:
            for room in street.rooms():
                walkers += [('street', room, w) for w in room.data.get('people', {}).values() if w.pid in pids]
        if not walkers:
            return
        worn = await cache.of(w.player for _, _, w in walkers)
        now = time.time()
        for kind, room, w in walkers:
            wg = worn.get(w.pid)
            if getattr(w, 'wg', None) == wg:
                continue
            w.wg = wg
            fl = getattr(w, 'fl', None)
            land = fl is not None and (wg['r'] if wg else None) != fl   # 🪽 wings off: landed; a new tier: its speed
            if kind == 'town':
                if land:
                    w.fl = wg['r'] if wg else None
                    if w.fl is None and 'site_key' not in room.data:
                        from .town import land as down
                        down(w)   # 🪽 over a roof, a tree or the water: on the nearest open ground
                ev = dict(k='mv', pid=w.pid, x=w.x, y=w.y, direction=w.direction, wg=wg)
                if land:
                    ev['fl'] = w.fl
                town._queue(room, w.pid, ev)
            else:
                street._queue(room, w.pid, dict(k='wg', pid=w.pid, wg=wg))
                if land:
                    street._set_fly(room, w, wg['r'] if wg else None, now)
