"""Helpers for the live service tests: a real game database (SQLite, or PostgreSQL with TEST_DATABASE_URL),
the live service on a free port, and WebSocket clients. Skipped when the `websockets` library is missing
(production vendors it into shared/pyvendor; locally: pip install websockets)."""
import asyncio
import secrets
import tempfile
import time
import unittest
from pathlib import Path

try:
    import websockets
    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosed, InvalidStatus
    HAVE_WS = True
except ImportError:
    HAVE_WS = False

from game import admin_stats, friends, push, social
from game.storage import Store

ORIGIN = 'http://test.local'
needs_ws = unittest.skipUnless(HAVE_WS, 'needs the websockets library (pip install websockets)')


class Client:
    def __init__(self, ws):
        self.ws = ws
        self.frames = []
        self.cond = asyncio.Condition()
        self.closed = None
        self.task = asyncio.ensure_future(self._read())

    async def _read(self):
        from live import jsonx
        try:
            async for raw in self.ws:
                async with self.cond:
                    self.frames.append(jsonx.loads(raw))
                    self.cond.notify_all()
        except ConnectionClosed:
            pass
        finally:
            self.closed = (self.ws.close_code, self.ws.close_reason)
            async with self.cond:
                self.cond.notify_all()

    async def send(self, **frame):
        from live import jsonx
        await self.ws.send(jsonx.dumps(frame).decode())

    async def expect(self, t, timeout=3.0, **match):
        """The first received frame of type t (and fields equal to `match`), removed from the inbox."""
        def find():
            for i, f in enumerate(self.frames):
                if f.get('t') == t and all(f.get(k) == v for k, v in match.items()):
                    return self.frames.pop(i)
            return None
        deadline = time.monotonic() + timeout
        async with self.cond:
            while True:
                f = find()
                if f is not None:
                    return f
                left = deadline - time.monotonic()
                if left <= 0 or self.closed:
                    raise AssertionError(f'no {t} {match} frame; got {[x.get("t") for x in self.frames]} closed={self.closed}')
                try:
                    await asyncio.wait_for(self.cond.wait(), left)
                except asyncio.TimeoutError:
                    pass

    async def nothing(self, t, wait=0.3, **match):
        await asyncio.sleep(wait)
        hits = [f for f in self.frames if f.get('t') == t and all(f.get(k) == v for k, v in match.items())]
        assert not hits, f'unexpected {t}: {hits}'

    async def call(self, t, reply, timeout=3.0, **frame):
        await self.send(t=t, **frame)
        return await self.expect(reply, timeout)

    async def wait_closed(self, timeout=3.0):
        await asyncio.wait_for(asyncio.shield(self.task), timeout)
        return self.closed

    async def close(self):
        await self.ws.close()
        try:
            await asyncio.wait_for(self.task, 2)
        except asyncio.TimeoutError:
            self.task.cancel()


@needs_ws
class LiveCase(unittest.IsolatedAsyncioTestCase):
    """A game database with players, and the live service on a free port (chat on)."""
    cfg_extra: dict = {}

    async def asyncSetUp(self):
        from live.app import App
        from live.config import Config
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.sqlite3')
        social.ensure(self.store)
        push.ensure(self.store)
        admin_stats.ensure(self.store)
        pg = self.store.pg
        self.cfg = Config(port=0, chat=True, origins=frozenset({ORIGIN}), db_path=None if pg else self.store.path,
                          db_url=pg.url if pg else None, db_schema=pg.schema if pg else None, presence_grace=0.3, **self.cfg_extra)
        self.app = App(self.cfg)
        await self.app.start()
        self.port = self.app.port()
        self.clients = []

    async def asyncTearDown(self):
        for c in self.clients:
            if c.closed is None:
                await c.close()
        await self.app.stop()
        self.store.close_pool()
        self.tmp.cleanup()

    # ---- players ------------------------------------------------------------------------------------------
    def guest(self, name='Mây Bếp', old=True):
        """A guest save with a character name (leaderboard_players, as the game keeps it). Returns (token, sid)."""
        token, _, _ = self.store.session(None)
        sid = self.store.key(token)
        with self.store.connect() as db:
            if name:
                db.execute('INSERT INTO leaderboard_players(sid, name, updated) VALUES(?, ?, ?)', (sid, name, time.time()))
            if old:
                db.execute('INSERT INTO stat_births(sid, day) VALUES(?, ?) ON CONFLICT(sid) DO UPDATE SET day=excluded.day', (sid, '2026-01-01'))
        return token, sid

    def account(self, display='Hoa Gió', old=True):
        """A registered player signed in on this device (a `logins` row). Returns (token, sid)."""
        token, sid = self.guest(name=None, old=old)
        login = secrets.token_hex(32)
        with self.store.connect() as db:
            db.execute('INSERT INTO accounts(username, display, pw, sid) VALUES(?, ?, ?, ?)',
                       ('u' + secrets.token_hex(6), display, 'x', sid))
            db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?, ?, ?)', (self.store.digest(login), sid, 'c'))
        return login, sid

    def befriend(self, a_sid, b_sid):
        self.store.transaction(lambda db: friends._befriend(db, a_sid, b_sid, None))

    @staticmethod
    def pid(sid):
        return social.pid_of(sid)

    async def connect(self, token, origin=ORIGIN, hello=True, resume=None):
        headers = {'Cookie': f'mnl_session={token}'} if token else {}
        ws = await connect(f'ws://127.0.0.1:{self.port}/live', origin=origin, additional_headers=headers, open_timeout=5)
        c = Client(ws)
        self.clients.append(c)
        if hello:
            await c.send(t='hello', v=1, **({'resume': resume} if resume else {}))
            c.welcome = await c.expect('welcome')
        return c
