"""Frames and features.

A frame is a JSON object `{t: <type>, ...}` of at most 4 KB (bigger ones close the socket). Each type has one
handler, registered by a Feature:

    class StreetFeature(Feature):          # phase 2 (live/street.py), switch LIVE_STREET
        name, flag = 'street', 'street'

        @on('move', rate=(4, 1.0))         # at most 4 per second per player, else error {code: 'slow'}
        async def move(self, conn, f):
            ...
            return {'t': 'moved', ...}     # a reply to this socket (or None)

A handler raises LiveError(code, message, **extra) for a refusal: the client gets
`{t: 'error', code, msg, ref: <the frame's cid or type>, ...extra}`. A frame for a feature whose switch is off
gets code 'off'. Hooks a feature may define: start() (once, before serving), on_hello(conn) (before the
welcome), welcome(conn) -> dict (merged into the welcome frame), on_close(conn), on_gone(player) (last socket
gone, after the grace), tick(now) (every second), on_notify(event) (admin events from the game server).
"""
from __future__ import annotations

import time

from game import jail as JL

from .db import Error as DbError, log

TYPE_MAX = 24
# 🚔 Trại tạm giữ (game/jail.py, owner 09/10 "chỉ được ở tù, nhắn tin, làm công ích"): a jailed player's frames other
# than the chat's (and leaving a room) are refused. The answer is cached per player for JAIL_TTL seconds (a shorter
# JAIL_TTL_IN while jailed, so a bail or the last day opens the rooms soon); a miss costs one primary-key read of the
# tiny jail_marks table (no row: free; the save itself is read only for a marked player, at most once per
# JL.MARK_CHECK_S, to drop a mark an older server left behind).
JAIL_TTL, JAIL_TTL_IN = 20.0, 8.0


class LiveError(Exception):
    def __init__(self, code: str, msg: str = '', **extra):
        super().__init__(msg or code)
        self.code, self.msg, self.extra = code, msg, extra


def on(kind: str, rate: tuple | None = None):
    """Mark a Feature method as the handler of frames of type `kind`; rate = (count, seconds) per player."""
    def deco(fn):
        fn._live = (kind, rate)
        return fn
    return deco


class Feature:
    name = 'core'
    flag: str | None = None      # 'chat' | 'street' | 'dating' | 'wedding' | 'fair' | None (always on)

    def __init__(self, app):
        self.app, self.hub, self.cfg = app, app.hub, app.cfg

    @property
    def db(self):
        return self.app.db

    def enabled(self) -> bool:
        return self.flag is None or bool(self.cfg.flags().get(self.flag))

    def handlers(self):
        for attr in dir(type(self)):
            fn = getattr(type(self), attr, None)
            spec = getattr(fn, '_live', None)
            if spec:
                yield spec[0], spec[1], getattr(self, attr)

    async def start(self): ...
    async def on_hello(self, conn): ...
    def welcome(self, conn) -> dict: return {}
    async def on_close(self, conn): ...
    def on_gone(self, player): ...
    async def tick(self, now: float): ...
    async def on_notify(self, event: dict): ...


class Core(Feature):
    """Always on: keep-alive."""

    @on('ping')
    async def ping(self, conn, f):
        return dict(t='pong', at=round(time.time(), 3))


class Dispatcher:
    def __init__(self, features):
        self.features = list(features)
        self.table: dict = {}
        for feat in self.features:
            for kind, rate, fn in feat.handlers():
                if kind in self.table:
                    raise RuntimeError(f'frame type {kind!r} has two handlers ({self.table[kind][0].name}, {feat.name})')
                self.table[kind] = (feat, rate, fn)

    async def dispatch(self, conn, f: dict) -> None:
        hub = conn.player and self.features[0].hub
        kind = f.get('t')
        ref = f.get('cid') if isinstance(f.get('cid'), (str, int)) and len(str(f.get('cid'))) <= 40 else kind
        entry = self.table.get(kind) if isinstance(kind, str) and len(kind) <= TYPE_MAX else None
        try:
            if entry is None:
                raise LiveError('unknown', 'Không hiểu yêu cầu này.')
            feat, rate, fn = entry
            if not feat.enabled():
                raise LiveError('off', 'Tính năng này đang tắt.')
            if conn.player and not JL.frame_open(feat.name, kind) and await self.jailed(feat, conn.player):
                raise LiveError('jailed', JL.JAILED)
            if rate:
                w = hub.rate(conn.player, kind, rate[0], rate[1])
                if not w.hit():
                    raise LiveError('slow', 'Chậm lại một chút nhé.', wait=round(w.wait(), 1))
            out = await fn(conn, f)
            if out:
                hub.send(conn, out)
        except LiveError as e:
            hub.send(conn, dict(t='error', code=e.code, msg=e.msg, ref=ref, **e.extra))
        except DbError as e:  # busy or restarting database: an answer, not a dropped socket
            log('db', kind, type(e).__name__)
            hub.send(conn, dict(t='error', code='busy', msg='Máy chủ đang bận, thử lại sau giây lát.', ref=ref))
        except Exception as e:  # noqa: BLE001 - a bug in one handler never drops the socket
            log('handler', kind, type(e).__name__, str(e)[:200])
            hub.send(conn, dict(t='error', code='internal', msg='Có lỗi, thử lại sau nhé.', ref=ref))

    async def jailed(self, feat, player) -> bool:
        """In the trại tạm giữ now (game/jail.py active), cached per player (JAIL_TTL)."""
        if JL.off() or not getattr(player, 'sid', None):
            return False
        t = time.monotonic()
        hit = player.ext.get('jail')
        if hit and hit[0] > t:
            return hit[1]
        db, now = feat.app.db, JL.now()
        row = await db.fetchrow(JL.MARK_GET, (player.sid,))
        u = float(row['until']) if row else None
        seen = player.ext.setdefault('jail_seen', {})
        inside = JL.mark_answer(u, seen, now)
        if inside is None:   # marked: the save confirms it (rare: only jailed players, at most once per MARK_CHECK_S)
            inside = JL.from_save(await db.fetchrow(JL.MARK_SAVE, (player.sid,)), now)
            if not inside:
                await db.execute(JL.MARK_STALE, (player.sid, u))
            JL.mark_note(seen, u, now, inside)
        player.ext['jail'] = (t + (JAIL_TTL_IN if inside else JAIL_TTL), inside)
        return inside
