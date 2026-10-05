"""PostgreSQL access for the live service.

psycopg async connections use a pool of at most LIVE_PG_POOL (default 8), plus one
LISTEN connection for admin events. SQL uses ? placeholders; transaction callbacks
run on one checked-out connection. Every short statement has a five-second timeout.
"""
from __future__ import annotations

import asyncio
import sys

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError as exc:  # pragma: no cover - deployment dependency guard
    raise SystemExit('[live] PostgreSQL requires psycopg; install the project dependencies') from exc

from game.db import validate_url

Error = (psycopg.Error,)


def to_pg(sql: str) -> str:
    return sql.replace('%', '%%').replace('?', '%s')


def log(*parts) -> None:
    print('[live]', *parts, file=sys.stderr, flush=True)


class _Ops:
    """fetch / fetchrow / fetchval / execute over `_run(sql, args, mode)`."""
    async def fetch(self, sql: str, args=()) -> list[dict]:
        return await self._run(sql, args, 'all')

    async def fetchrow(self, sql: str, args=()) -> dict | None:
        return await self._run(sql, args, 'one')

    async def fetchval(self, sql: str, args=()):
        row = await self._run(sql, args, 'one')
        return None if row is None else next(iter(row.values()))

    async def execute(self, sql: str, args=()) -> int:
        return await self._run(sql, args, 'count')


# ---------------------------------------------------------------- PostgreSQL
class _PgTx(_Ops):
    def __init__(self, conn):
        self.conn = conn

    async def _run(self, sql, args, mode):
        cur = await self.conn.execute(to_pg(sql), args)
        return await _result(cur, mode)


async def _result(cur, mode):
    if mode == 'count':
        return cur.rowcount
    if cur.description is None:
        return [] if mode == 'all' else None
    return await (cur.fetchall() if mode == 'all' else cur.fetchone())


class PgDB(_Ops):
    dialect = 'pg'

    def __init__(self, url: str, schema: str | None = None, size: int = 8, app: str = 'mnl-live'):
        self.url, self.schema, self.size, self.app = validate_url(url), schema, size, app
        self.idle: list = []
        self.open = 0
        self.sem = asyncio.Semaphore(size)
        self.listener = None
        self.closed = False

    async def _connect(self):
        conn = await psycopg.AsyncConnection.connect(self.url, autocommit=True, row_factory=dict_row, application_name=self.app)
        settings = dict(statement_timeout='5000', lock_timeout='3000', idle_in_transaction_session_timeout='15000')
        if self.schema:
            settings['search_path'] = self.schema
        await conn.execute('SELECT ' + ', '.join('set_config(%s, %s, false)' for _ in settings), [x for k, v in settings.items() for x in (k, v)])
        return conn

    async def _take(self):
        await self.sem.acquire()
        try:
            while self.idle:
                conn = self.idle.pop()
                if not conn.closed and not getattr(conn, 'broken', False):
                    return conn
                self.open -= 1
            conn = await self._connect()
            self.open += 1
            return conn
        except BaseException:
            self.sem.release()
            raise

    def _give(self, conn) -> None:
        """Back to the pool only when libpq says it is idle (no transaction, nothing running); else closed."""
        if not conn.closed and not getattr(conn, 'broken', False) and conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE:
            self.idle.append(conn)
        else:
            self.open -= 1
            asyncio.ensure_future(_close(conn))
        self.sem.release()

    async def _run(self, sql, args, mode):
        conn = await self._take()
        try:
            cur = await conn.execute(to_pg(sql), args)
            return await _result(cur, mode)
        finally:
            self._give(conn)

    async def transaction(self, fn):
        conn = await self._take()
        try:
            async with conn.transaction():
                return await fn(_PgTx(conn))
        finally:
            self._give(conn)

    async def listen(self, channel: str, on_event, on_reconnect=None) -> None:
        """Run forever: LISTEN `channel`, call on_event(payload) for each NOTIFY; after a lost connection,
        reconnect (1 s, 2 s, ... 30 s) and call on_reconnect() (events may have been missed)."""
        delay, first = 1.0, True
        while not self.closed:
            try:
                conn = await psycopg.AsyncConnection.connect(self.url, autocommit=True, application_name=self.app + '-listen')
                self.listener = conn
                await conn.execute(f'LISTEN {channel}')
                if not first and on_reconnect:
                    await on_reconnect()
                first, delay = False, 1.0
                async for n in conn.notifies():
                    try:
                        await on_event(n.payload)
                    except Exception as e:  # noqa: BLE001 - one bad event never stops the listener
                        log('notify handler:', type(e).__name__, e)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                if self.closed:
                    return
                log('listen lost:', type(e).__name__)
            finally:
                if self.listener is not None:
                    await _close(self.listener)
                    self.listener = None
            await asyncio.sleep(delay)
            delay = min(30.0, delay * 2)

    async def close(self) -> None:
        self.closed = True
        while self.idle:
            await _close(self.idle.pop())
        if self.listener is not None:
            await _close(self.listener)


async def _close(conn) -> None:
    try:
        await conn.close()
    except Exception:  # noqa: BLE001
        pass


async def open_db(cfg) -> PgDB:
    db = PgDB(validate_url(cfg.db_url), cfg.db_schema, cfg.pool_max)
    try:
        await db.fetchval('SELECT 1')
    except BaseException:
        await db.close()
        raise
    return db


async def wait_for_tables(db, names=('chat_messages', 'chat_channels', 'chat_members', 'chat_mutes', 'chat_prefs', 'chat_pins', 'chat_reacts',
                                     'chat_faces')) -> None:
    """The game server creates the tables (SCHEMA_VERSION 12: chat_faces; 11: chat_reacts, chat_messages.raw; 10: chat_pins,
    chat_messages.adm). Until a release that has them has started, wait."""
    said = False
    while True:
        try:
            for n in names:
                await db.fetchval(f'SELECT 1 FROM {n} LIMIT 1')
            return
        except Error:
            if not said:
                log('waiting for the chat tables (start the game server of this release first)')
                said = True
            await asyncio.sleep(10)

