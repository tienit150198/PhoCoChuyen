"""⚔️ Bang tags (game/bang.py): the bang a player is in, its emoji, colour and the player's role, beside the name.

Read from the game's tables (bang_members ⨝ bangs, never from a frame) and sent as an optional `bg` = {n, e, c, r, k?, b?}
(name, emoji, colour id, role id, 👑 Bang mạnh nhất tuần, 🎖️ badge worn): on chat messages (live and pages), on walkers
of the 2.5D map (live/town.py) and of the old street (live/street.py), on their cards. An older client ignores `bg`.

* Cheap: a bounded LRU of CACHE players, each entry kept TTL seconds; one primary-key-indexed query per 500 missing
  players; nothing on a movement frame (the walker keeps its tag from town_in / walk_in).
* The game server announces changes with NOTIFY {op: 'bang', pids?, ch?, add?, rm?, invite?, bang?}: the players'
  entries are dropped and walkers on screen get their new tag (a `mv` with `bg` on the map, a `bg` diff on the street);
  `ch` is the bang's chat group (a chat_channels row of kind 'group', owner 'bang'): its cached members are read again,
  `add` get the chat in their list, `rm` lose it. {op: 'bang_crown'}: the week's winner moved, every tag is read again.
* The tables come with SCHEMA_VERSION 57. Until they exist every lookup answers {} and they are looked for again every
  RETRY seconds, so this service and the game server roll out in any order.
"""
from __future__ import annotations

import datetime
import time

from game import bang_content as C

from .db import Error as DbError, log
from .limits import LRU
from .protocol import Feature

CACHE = 20000
TTL = 300.0
RETRY = 300.0
CROWN_TTL = 300.0
VN = datetime.timezone(datetime.timedelta(hours=7))


def prev_week(t: float) -> str:
    d = datetime.datetime.fromtimestamp(t, VN).date()
    d -= datetime.timedelta(days=d.weekday() + 1)
    y, w, _ = d.isocalendar()
    return f'{y}-W{w:02d}'


def frame(row: dict, crown: str | None) -> dict:
    out = dict(n=str(row['name'])[:24], e=row['emoji'] if row['emoji'] in C.EMOJIS else '⚔️',
               c=row['color'] if row['color'] in C.COLORS else 'do', r=row['role'] if row['role'] in C.ROLES else 'tv')
    if crown and row['id'] == crown:
        out['k'] = 1
    if int(row.get('wear') or 0) & C.WEAR_BITS['huy']:
        out['b'] = 1
    if int(row.get('wear') or 0) & C.WEAR_BITS['ao']:
        out['u'] = 1   # 👕 the bang uniform is worn: the map draws the top in its colour, not the green town uniform
    return out


class Bangs:
    def __init__(self, app):
        self.app = app
        self.rows = LRU(CACHE)        # pid -> (fetched monotonic, tag | None)
        self.off_until = 0.0
        self.crown = (0.0, None)      # (fetched monotonic, bang id holding 👑 this week)

    def forget(self, pid: str) -> None:
        self.rows.pop(pid, None)

    def clear(self) -> None:
        self.rows = LRU(CACHE)
        self.crown = (0.0, None)

    async def _crown(self, mono: float) -> str | None:
        if mono - self.crown[0] < CROWN_TTL:
            return self.crown[1]
        try:
            r = await self.app.db.fetchrow('SELECT bang FROM bang_week_win WHERE week=?', (prev_week(time.time()),))
        except DbError:
            r = None
        self.crown = (mono, r['bang'] if r else None)
        return self.crown[1]

    async def of(self, pids) -> dict:
        """{pid: tag} for these players ({} for none)."""
        mono = time.monotonic()
        ids = [p for p in dict.fromkeys(pids) if isinstance(p, str) and p]
        out, miss = {}, []
        for pid in ids:
            hit = self.rows.get(pid)
            if hit is not None and mono - hit[0] < TTL:
                if hit[1]:
                    out[pid] = hit[1]
            else:
                miss.append(pid)
        if not miss or mono < self.off_until or self.app.db is None:
            return out
        crown = await self._crown(mono)
        for i in range(0, len(miss), 500):
            part = miss[i:i + 500]
            try:
                got = {r['pid']: dict(r) for r in await self.app.db.fetch(
                    'SELECT m.pid, m.role, m.wear, b.id, b.name, b.emoji, b.color FROM bang_members m JOIN bangs b ON b.id=m.bang '
                    f"WHERE m.pid IN ({','.join('?' * len(part))}) AND m.status='in' AND b.status='active' AND b.hidden=0", part)}
            except DbError as e:   # a database from before SCHEMA_VERSION 57: nobody is in a bang yet
                log('bangs:', type(e).__name__)
                self.off_until = mono + RETRY
                return out
            for pid in part:
                row = got.get(pid)
                tag = frame(row, crown) if row else None
                self.rows.put(pid, (mono, tag))
                if tag:
                    out[pid] = tag
        return out

    async def one(self, pid: str) -> dict | None:
        return (await self.of([pid])).get(pid)


def of_app(app) -> Bangs:
    b = getattr(app, '_bangs', None)
    if b is None:
        b = app._bangs = Bangs(app)
    return b


def put(f: dict, tag) -> dict:
    """The frame with `bg` set (a copy when it changes; buffered frames are never mutated)."""
    if f.get('bg') == (tag or None):
        return f
    f = dict(f)
    if tag:
        f['bg'] = tag
    else:
        f.pop('bg', None)
    return f


async def with_bangs(app, frames: list, key: str = 'pid') -> list:
    if not frames:
        return frames
    bx = await of_app(app).of(f.get(key) for f in frames)
    return [put(f, bx.get(f.get(key))) for f in frames]


class BangFeature(Feature):
    """No frames of its own: NOTIFY from the game server keeps tags and the bang chat groups current."""
    name = 'bang'

    async def on_notify(self, e: dict):
        op = e.get('op')
        if op == 'bang_crown':
            of_app(self.app).clear()
            await self._retag(None)
            return
        if op != 'bang':
            return
        tags = of_app(self.app)
        pids = [p for p in (e.get('pids') or []) if isinstance(p, str) and len(p) == 16]
        if e.get('bang'):   # the bang itself changed (an admin rename / hide, the emoji or colour): every member's tag
            tags.rows = LRU(CACHE)
            await self._retag(None)
        elif pids:
            for pid in pids:
                tags.forget(pid)
            await self._retag(set(pids))
        for pid in pids:   # my own bang changed (joined, kicked, a role, an item worn): my page reads it again
            self.hub.send_many([c for c in self.hub.conns_of(pid) if c.ready], dict(t='bang_me'))
        ch = e.get('ch')
        chat = self.app.chat
        if chat is not None and isinstance(ch, str) and ch.startswith('g:') and len(ch) <= 16:
            chat.chans.pop(ch, None)
            chat.reply_epoch += 1
            for pid in [p for p in (e.get('rm') or []) if isinstance(p, str)]:
                self.hub.send_many(self.hub.conns_of(pid), dict(t='unchan', ch=ch))
            add = [p for p in (e.get('add') or []) if isinstance(p, str)]
            if add or e.get('bang'):
                try:
                    c = await chat.chan(ch)
                except DbError as x:
                    log('bang chat:', type(x).__name__)
                    c = None
                if c is not None:
                    chat._push_chan(c)
        inv = e.get('invite')
        if isinstance(inv, str) and len(inv) == 16:
            self.hub.send_many([c for c in self.hub.conns_of(inv) if c.ready],
                               dict(t='bang_invite', name=str(e.get('name') or '')[:24], e=str(e.get('emoji') or '⚔️')[:4]))

    async def _retag(self, only: set | None) -> None:
        """Walkers on screen take their new tag: the map (live/town.py) and the street (live/street.py)."""
        town = self.app.by_name.get('town')
        street = self.app.by_name.get('street')
        walkers = []
        if town is not None:
            from .town import PREFIX
            from .scale_sites import SITE_PREFIX
            for room in self.hub.rooms_with_prefix(PREFIX) + self.hub.rooms_with_prefix(SITE_PREFIX):
                for w in room.data.get('people', {}).values():
                    if only is None or w.pid in only:
                        walkers.append(('town', room, w))
        if street is not None:
            for room in street.rooms():
                for w in room.data.get('people', {}).values():
                    if only is None or w.pid in only:
                        walkers.append(('street', room, w))
        if not walkers:
            return
        tags = await of_app(self.app).of(w.pid for _, _, w in walkers)
        for kind, room, w in walkers:
            tag = tags.get(w.pid)
            if getattr(w, 'bg', None) == tag:
                continue
            w.bg = tag
            if kind == 'town':
                town._queue(room, w.pid, dict(k='mv', pid=w.pid, x=w.x, y=w.y, direction=w.direction, bg=tag))
            else:
                street._queue(room, w.pid, dict(k='bg', pid=w.pid, bg=tag))
