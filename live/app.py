"""The live service: one asyncio process, one WebSocket per open tab at /live.

Handshake (process_request): the path, the Origin (LIVE_ORIGINS; a cross-site page cannot open a socket
with the player's cookie), the caps (LIVE_MAX_CONN, LIVE_PER_IP, 60 handshakes per IP per minute) and the
`mnl_session` cookie (live/auth.py). Then the client sends `hello {v, resume}` within 10 s and gets
`welcome {flags, me, friends, chans, ...}`; after that every frame goes to the dispatcher (live/protocol.py).

Bounded: frames ≤ 4 KB (bigger close the socket, 1009), 8 frames/s per socket (burst 30, more closes it,
1008), no frame for 70 s closes it (the client pings every 25 s), a socket that does not read its frames
(256 KB unsent) is cut off.

Restart (SIGTERM, a deploy): every socket is closed with 1012; clients reconnect with jitter and back-off and
resume from the last message id they hold. GET /live/health (from nginx's host only: nginx exposes `= /live`)
answers JSON counters.
"""
from __future__ import annotations

import asyncio
import os
import signal
import time

from . import PROTOCOL, honours, jsonx
from .auth import identify, token_from
from .booth import BoothFeature
from .chat import ChatFeature
from .dating import DatingFeature
from .fair import FairFeature
from .config import Config, from_env
from .db import Error as DbError, log, open_db, wait_for_tables
from .hub import Conn, Hub
from .home import HomeFeature
from .market import MarketFeature
from .work_visits import WorkVisitsFeature
from .limits import LRU, Keyed
from .protocol import Core, Dispatcher
from .street import StreetFeature
from .wedding import WeddingFeature
from .town import TownFeature
from .karaoke import KaraokeFeature
from .auction import AuctionFeature
from .fireworks import FireworksFeature

try:
    import websockets
    from websockets.asyncio.server import serve
    from websockets.exceptions import ConnectionClosed
except ImportError:  # pragma: no cover
    websockets = None

# Phase 2 adds live.street.StreetFeature, phase 3 live.dating.DatingFeature (one line each).
FEATURES = [ChatFeature, StreetFeature, DatingFeature, WeddingFeature, FairFeature, BoothFeature, HomeFeature, WorkVisitsFeature, MarketFeature, TownFeature, KaraokeFeature, AuctionFeature, FireworksFeature]
HELLO_SECS = 10.0
NOTIFY_CHANNEL = 'mnl_live'


class App:
    def __init__(self, cfg: Config, db=None):
        self.cfg, self.db = cfg, db
        self.hub = Hub(cfg)
        self.features = [Core(self)] + [cls(self) for cls in FEATURES]
        self.by_name = {f.name: f for f in self.features}
        self.chat = self.by_name.get('chat')
        self.dispatcher = Dispatcher(self.features)
        self.handshakes = Keyed(cfg.handshakes_per_ip, 60)
        self.seen = LRU(50000)          # pid -> first time this process saw them (age when nothing else says)
        self.server = None
        self.stopping = False
        self.started = time.time()
        self.bg: list = []

    def first_seen(self, pid: str) -> float:
        t = self.seen.get(pid)
        return t if t is not None else self.seen.put(pid, time.time())

    # ---- handshake ------------------------------------------------------------------------------------------
    def client_ip(self, connection, request) -> str:
        if self.cfg.trust_proxy:
            ip = (request.headers.get('X-Real-IP') or '').strip() or (request.headers.get('X-Forwarded-For') or '').split(',')[-1].strip()
            if ip:
                return ip[:64]
        addr = connection.remote_address
        return str(addr[0]) if addr else '?'

    async def process_request(self, connection, request):
        path = request.path.split('?', 1)[0]
        if path == self.cfg.path + '/health':
            return self._health(connection)
        if path != self.cfg.path:
            return connection.respond(404, 'Not found\n')
        if request.headers.get('Origin', '').rstrip('/') not in self.cfg.origins:
            return connection.respond(403, 'Origin not allowed\n')
        if self.stopping:
            return connection.respond(503, 'Restarting\n')
        ip = self.client_ip(connection, request)
        if len(self.hub.conns) >= self.cfg.max_conn:
            return connection.respond(503, 'Full\n')
        if self.hub.by_ip.get(ip, 0) >= self.cfg.per_ip or not self.handshakes.hit(ip):
            return connection.respond(429, 'Too many connections\n')
        try:
            ident = await identify(self.db, token_from(request.headers.get('Cookie')))
        except DbError as e:
            log('auth db:', type(e).__name__)
            return connection.respond(503, 'Busy\n')
        if ident is None:
            return connection.respond(401, 'No session\n')
        connection.live = (ident, ip)
        return None

    def _health(self, connection):
        r = connection.respond(200, jsonx.dumps(dict(ok=True, up=round(time.time() - self.started), flags=self.cfg.flags(), **self.hub.stats())).decode())
        del r.headers['Content-Type']
        r.headers['Content-Type'] = 'application/json'
        return r

    # ---- one socket -------------------------------------------------------------------------------------------
    async def handler(self, ws):
        ident, ip = ws.live
        hub = self.hub
        p = hub.player(ident)
        if len(p.conns) >= self.cfg.per_player:   # a new tab wins over the oldest one
            oldest = min(p.conns, key=lambda c: c.id)
            oldest.closing = True
            asyncio.ensure_future(oldest.ws.close(4002, 'other tab'))
        conn = Conn(ws, p, ip, self.cfg)
        hub.add(conn)
        try:
            try:
                raw = await asyncio.wait_for(ws.recv(), HELLO_SECS)
                hello = jsonx.loads(raw)
            except (asyncio.TimeoutError, ValueError, TypeError):
                await self.kick(conn, 1008, 'hello')
                return
            if not isinstance(hello, dict) or hello.get('t') != 'hello':
                await self.kick(conn, 1008, 'hello')
                return
            if not self.cfg.any_on():
                hub.send(conn, dict(t='welcome', v=PROTOCOL, flags=self.cfg.flags(), at=round(time.time(), 3)))
                await self.kick(conn, 4001, 'off')
                return
            conn.ext['fc'] = hello.get('fc')   # 🙂 the face this client wears now (live/faces.py; older clients send none)
            try:
                for feat in self.features:
                    if feat.enabled():
                        await feat.on_hello(conn)
            except DbError as e:
                log('hello db:', type(e).__name__)
                await self.kick(conn, 1013, 'busy')
                return
            welcome = dict(t='welcome', v=PROTOCOL, flags=self.cfg.flags(), at=round(time.time(), 3))
            for feat in self.features:
                if feat.enabled():
                    welcome.update(feat.welcome(conn))
            conn.ready = True
            hub.send(conn, welcome)
            hub.came_online(p)
            if self.chat and self.chat.enabled():
                await self.chat.resume(conn, hello.get('resume'))
            async for raw in ws:
                conn.last = time.monotonic()
                if conn.closing:
                    continue   # closing: drain what is queued so the client's close frame gets read
                if not conn.bucket.take():
                    self.kick_soon(conn, 1008, 'too fast')
                    continue
                try:
                    f = jsonx.loads(raw)
                except (ValueError, TypeError):
                    self.kick_soon(conn, 1007, 'json')
                    continue
                if not isinstance(f, dict):
                    self.kick_soon(conn, 1007, 'frame')
                    continue
                await self.dispatcher.dispatch(conn, f)
        except ConnectionClosed:
            pass
        finally:
            last = hub.remove(conn)
            for feat in self.features:
                try:
                    await feat.on_close(conn)
                except Exception as e:  # noqa: BLE001
                    log('on_close', feat.name, type(e).__name__)
            if last:
                hub.went_offline(p, on_gone=self._gone)

    def kick_soon(self, conn, code: int, reason: str) -> None:
        """Close a socket that broke a rule. The caller keeps reading (and dropping) its frames: a client that
        flooded us has its close frame queued behind them."""
        conn.closing = True
        asyncio.ensure_future(conn.ws.close(code, reason))

    async def kick(self, conn, code: int, reason: str) -> None:
        self.kick_soon(conn, code, reason)
        try:
            async for _ in conn.ws:
                pass
        except ConnectionClosed:
            pass

    def _gone(self, player) -> None:
        for feat in self.features:
            try:
                feat.on_gone(player)
            except Exception as e:  # noqa: BLE001
                log('on_gone', feat.name, type(e).__name__)

    # ---- admin events ---------------------------------------------------------------------------------------
    async def on_notify(self, payload: str) -> None:
        try:
            event = jsonx.loads(payload)
        except ValueError:
            return
        if isinstance(event, dict):
            honours.on_notify(self, event)   # 🏅 a title granted, the weekly holders moved (live/honours.py)
            for feat in self.features:
                await feat.on_notify(event)

    async def on_reconnect(self) -> None:
        honours.of_app(self).clear()   # 🏅 announcements may have been missed while LISTEN was down
        if self.chat:
            await self.chat.reconcile()

    # ---- background ---------------------------------------------------------------------------------------
    async def ticker(self) -> None:
        n = 0
        while True:
            await asyncio.sleep(1)
            n += 1
            now = time.time()
            for feat in self.features:
                if feat.enabled():
                    try:
                        await feat.tick(now)
                    except Exception as e:  # noqa: BLE001
                        log('tick', feat.name, type(e).__name__, e)
            if n % 5 == 0:
                cut = time.monotonic() - self.cfg.idle_secs
                for c in [c for c in self.hub.conns if c.last < cut and not c.closing]:
                    c.closing = True
                    asyncio.ensure_future(c.ws.close(4000, 'idle'))
            if n % 300 == 0:
                log('stats', jsonx.dumps(self.hub.stats()).decode())

    # ---- run ----------------------------------------------------------------------------------------------
    async def start(self) -> None:
        if websockets is None:
            raise SystemExit('[live] the websockets library is missing (scripts/vendor_websockets.sh)')
        if self.db is None:
            self.db = await open_db(self.cfg)
        await wait_for_tables(self.db)
        for feat in self.features:
            await feat.start()
        self.server = await serve(self.handler, self.cfg.host, self.cfg.port, process_request=self.process_request,
                                  compression=None, max_size=self.cfg.max_frame, max_queue=8, ping_interval=None,
                                  open_timeout=10, close_timeout=5, server_header=None)
        self.bg = [asyncio.ensure_future(self.ticker()),
                   asyncio.ensure_future(self.db.listen(NOTIFY_CHANNEL, self.on_notify, self.on_reconnect))]
        log(f'listening on {self.cfg.host}:{self.port()} (flags {self.cfg.flags()}, db {self.db.dialect}, pid {os.getpid()})')

    def port(self) -> int:
        try:
            return next(iter(self.server.sockets)).getsockname()[1]
        except (StopIteration, AttributeError):
            return self.cfg.port

    async def stop(self, code: int = 1012) -> None:
        """Close every socket with `code` (1012: restart, clients come back) and stop."""
        self.stopping = True
        closing = []
        for c in list(self.hub.conns):
            c.closing = True
            closing.append(asyncio.ensure_future(c.ws.close(code, 'restart')))
        if closing:
            await asyncio.wait(closing, timeout=4)
        if self.server is not None:
            self.server.close(close_connections=True)
            try:
                await asyncio.wait_for(self.server.wait_closed(), 5)
            except asyncio.TimeoutError:
                pass
        for t in self.bg:
            t.cancel()
        if self.bg:
            # LISTEN must unregister its socket reader before the database closes.
            await asyncio.gather(*self.bg, return_exceptions=True)
        if self.db is not None:
            await self.db.close()

    async def run(self) -> None:
        await self.start()
        done = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, done.set)
            except (NotImplementedError, RuntimeError):
                pass
        await done.wait()
        log('stopping: closing sockets with 1012 (clients reconnect)')
        await self.stop()


def main(argv=None) -> None:
    cfg = from_env(argv)
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(App(cfg).run())
