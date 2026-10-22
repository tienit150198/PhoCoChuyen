"""🤝 Phụ kiện đôi (game/friend_charms.py, owner 22/10, góp ý #484): the pairs a walker wears, drawn on their character.

Read from the game's table (friend_charms, never from a frame) and sent as an optional `pr` = {kind: count} on walkers of the
2.5D map (live/town.py) and of the old street (live/street.py): only the kinds this build knows and how many of each are worn,
never who they are shared with. The client draws them (public/js/v4/look.js paintPairs); an older client ignores `pr`.

* Cheap: a bounded LRU of CACHE players, each entry kept TTL seconds; one indexed query per 500 missing players; nothing on a
  movement frame (the walker keeps its pairs from town_in / walk_in).
* The game server announces a change with NOTIFY {op: 'charm', pids}: those entries are dropped and their walkers on screen
  get the new `pr` (a `mv` with `pr` on the map, a `pr` event on the street; null: none worn).
* The table comes with SCHEMA_VERSION 86. Until it exists every lookup answers {} and it is looked for again every RETRY
  seconds, so this service and the game server roll out in any order.
"""
from __future__ import annotations

import time

from game.friend_charms_content import ORDER

from .db import Error as DbError, log
from .limits import LRU
from .protocol import Feature

CACHE = 20000
TTL = 300.0
RETRY = 300.0
COUNT_MAX = 99


def frame(kinds) -> dict | None:
    """{kind: count} in catalogue order from the kinds of the rows worn (unknown kinds left out), or None."""
    out = {}
    for k in kinds:
        if k in ORDER:
            out[k] = min(COUNT_MAX, out.get(k, 0) + 1)
    return {k: out[k] for k in ORDER if k in out} or None


class Charms:
    def __init__(self, app):
        self.app = app
        self.rows = LRU(CACHE)        # pid -> (fetched monotonic, pr | None)
        self.off_until = 0.0

    def forget(self, pid: str) -> None:
        self.rows.pop(pid, None)

    async def of(self, players) -> dict:
        """{pid: pr} for these players (Player objects: pid and sid); nobody wearing a pair is left out."""
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
            marks = ','.join('?' * len(sids))
            try:
                rows = await self.app.db.fetch(
                    f"SELECT a, b, wear_a, wear_b, kind FROM friend_charms WHERE status='paired' AND "
                    f'((a IN ({marks}) AND wear_a=1) OR (b IN ({marks}) AND wear_b=1))', sids + sids)
            except DbError as e:   # a database from before SCHEMA_VERSION 86: nobody wears a pair yet
                log('charms:', type(e).__name__)
                self.off_until = mono + RETRY
                return out
            worn = {}
            for r in rows:
                if r['wear_a']:
                    worn.setdefault(r['a'], []).append(r['kind'])
                if r['wear_b']:
                    worn.setdefault(r['b'], []).append(r['kind'])
            for pid, sid in part:
                pr = frame(worn.get(sid, ()))
                self.rows.put(pid, (mono, pr))
                if pr:
                    out[pid] = pr
        return out

    async def one(self, player) -> dict | None:
        return (await self.of([player])).get(player.pid)


def of_app(app) -> Charms:
    c = getattr(app, '_charms', None)
    if c is None:
        c = app._charms = Charms(app)
    return c


class CharmFeature(Feature):
    """No frames of its own: NOTIFY {op: 'charm', pids} from the game server keeps the walkers' pairs current."""
    name = 'charm'

    async def on_notify(self, e: dict):
        if e.get('op') != 'charm':
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
        for kind, room, w in walkers:
            pr = worn.get(w.pid)
            if getattr(w, 'pr', None) == pr:
                continue
            w.pr = pr
            if kind == 'town':
                town._queue(room, w.pid, dict(k='mv', pid=w.pid, x=w.x, y=w.y, direction=w.direction, pr=pr))
            else:
                street._queue(room, w.pid, dict(k='pr', pid=w.pid, pr=pr))
