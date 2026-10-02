"""The live service's database: PostgreSQL in production (psycopg 3 async connections, a small pool of at
most `LIVE_PG_POOL` = 8, plus one connection that LISTENs for admin events), SQLite for dev and tests (one
connection in one worker thread). The SQL is written once with `?` placeholders and runs on both.

Rules for the SQL in live/: no `?` or `%` inside string literals (the PostgreSQL translation is a plain
replace), `COUNT(*)` and integer columns only (SUM of bigint would come back as Decimal on PostgreSQL),
`COALESCE` for NULL ordering. Every statement is short; a statement timeout of 5 s guards PostgreSQL.

    db = await open_db(cfg)
    rows = await db.fetch('SELECT ... WHERE pid=?', (pid,))         # [dict]
    row = await db.fetchrow(...); n = await db.fetchval(...); count = await db.execute(...)
    await db.transaction(fn)    # fn(tx) is an async function using the same methods on one connection
    await db.listen('mnl_live', on_event, on_reconnect)              # PostgreSQL only
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # SQLite-only dev machines
    psycopg = None

Error = (sqlite3.Error,) + ((psycopg.Error,) if psycopg else ())


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
        if psycopg is None:
            raise SystemExit('[live] DATABASE_URL is set but psycopg is not installed')
        self.url, self.schema, self.size, self.app = url, schema, size, app
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


# ---------------------------------------------------------------- SQLite (dev, tests)
class _SqTx(_Ops):
    def __init__(self, db):
        self.db = db

    async def _run(self, sql, args, mode):
        return await self.db._call(sql, args, mode)


class SqliteDB(_Ops):
    """One connection, one worker thread; an asyncio lock keeps a transaction's statements together."""
    dialect = 'sqlite'

    def __init__(self, path: str):
        self.path = path
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='live-sqlite')
        self.lock = asyncio.Lock()
        self.conn = None
        self.closed = False

    def _open(self):
        if self.conn is None:
            c = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA busy_timeout=10000')
            self.conn = c
        return self.conn

    def _do(self, sql, args, mode):
        cur = self._open().execute(sql, args)
        if mode == 'count':
            return cur.rowcount
        if mode == 'all':
            return [dict(r) for r in cur.fetchall()]
        r = cur.fetchone()
        # RETURNING: finish the statement so its change is applied
        cur.fetchall()
        return dict(r) if r is not None else None

    async def _call(self, sql, args, mode):
        return await asyncio.get_running_loop().run_in_executor(self.pool, self._do, sql, tuple(args), mode)

    async def _run(self, sql, args, mode):
        async with self.lock:
            return await self._call(sql, args, mode)

    async def transaction(self, fn):
        async with self.lock:
            await self._call('BEGIN IMMEDIATE', (), 'count')
            try:
                out = await fn(_SqTx(self))
            except BaseException:
                await self._call('ROLLBACK', (), 'count')
                raise
            await self._call('COMMIT', (), 'count')
            return out

    async def listen(self, channel, on_event, on_reconnect=None) -> None:
        return None  # no NOTIFY on SQLite: admin decisions apply after a restart

    async def close(self) -> None:
        self.closed = True
        if self.conn is not None:
            conn, self.conn = self.conn, None
            await asyncio.get_running_loop().run_in_executor(self.pool, conn.close)
        self.pool.shutdown(wait=False)


async def open_db(cfg) -> PgDB | SqliteDB:
    if cfg.db_url:
        db = PgDB(cfg.db_url, cfg.db_schema, cfg.pool_max)
    else:
        if not cfg.db_path or not os.path.exists(cfg.db_path):
            raise SystemExit(f'[live] no database: set DATABASE_URL or --db <game sqlite file> ({cfg.db_path} not found)')
        db = SqliteDB(cfg.db_path)
    await db.fetchval('SELECT 1')
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

