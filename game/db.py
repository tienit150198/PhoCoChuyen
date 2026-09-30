"""Database backends: SQLite (default, exactly as before) or PostgreSQL.

DATABASE_URL=postgresql://user@host:port/db switches the game to PostgreSQL (the
password comes from the URL, ~/.pgpass or PGPASSWORD; never log the URL). Without it
the game uses the SQLite file given by --db / GAME_DB, unchanged.

On PostgreSQL the game code keeps its SQLite-style SQL; PgConnection translates it:
* `?` placeholders -> `%s` (never inside string literals), a literal `%` -> `%%`;
* INSERT OR IGNORE -> INSERT ... ON CONFLICT DO NOTHING;
* CURRENT_TIMESTAMP and datetime('now', X) -> the same TEXT SQLite produces,
  'YYYY-MM-DD HH:MM:SS' in UTC (the columns stay text, see game/pg_schema.py);
* BEGIN IMMEDIATE -> BEGIN; PRAGMA -> nothing.
SQL that has no faithful translation (rowid, sqlite_master, JSON1, date()) is written
per dialect at its call site (see is_pg()). Rows are read by name AND by index, like
sqlite3.Row; SUM() of integers comes back as int, as in SQLite.

Transactions follow Python's sqlite3 rules: the psycopg connection is in autocommit
mode, a data change (INSERT/UPDATE/DELETE) opens a transaction, commit()/rollback()
or leaving `with store.connect() as db:` ends it. A SELECT outside a transaction runs
on its own and leaves nothing open: rows are fetched completely by execute(), there is
never a server-side cursor. A connection goes back to the pool only when libpq reports
it idle (no transaction, nothing in progress); otherwise it is rolled back or closed.

Pool (per Store, per process): PG_POOL idle connections are kept (default 6), at most
PG_POOL_MAX are open at once (default 12; a thread waits up to PG_POOL_WAIT_MS for one).
Connections are opened lazily in the process that uses them: never shared across fork()
(server.py closes the pool before forking workers). Per connection:
statement_timeout=PG_STATEMENT_TIMEOUT_MS (10 s), lock_timeout=PG_LOCK_TIMEOUT_MS (5 s),
idle_in_transaction_session_timeout=PG_IDLE_TX_TIMEOUT_MS (30 s); optional
PG_SYNCHRONOUS_COMMIT (e.g. off, see docs/POSTGRES.md).
Dead connections (PostgreSQL restarted, a backend terminated): an idle connection older than
PG_POOL_CHECK_MS (5000) is pinged before it is handed out, and if the FIRST statement of a
checkout fails because the connection is gone, it is retried once on a fresh connection
(nothing ran on the dead one; there is never a retry after a statement succeeded).

Tests: TEST_DATABASE_URL (and no DATABASE_URL) runs the test suite on PostgreSQL. Each
database path gets its own schema t_<run>_<hash of the path>, created on first use and
dropped when its directory is gone or when the test run ends. Never set it in production.
"""
from __future__ import annotations
import atexit
import functools
import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time

try:
    import psycopg
    from psycopg import pq
    from psycopg.adapt import Loader
except ImportError:  # SQLite-only installs do not need psycopg
    psycopg = None

Error = (sqlite3.Error,) + ((psycopg.Error,) if psycopg else ())
IntegrityError = (sqlite3.IntegrityError,) + ((psycopg.IntegrityError,) if psycopg else ())
OperationalError = (sqlite3.OperationalError,) + ((psycopg.OperationalError,) if psycopg else ())
# bad client data the database refuses (e.g. a NUL in a text value on PostgreSQL): a 400, not a 500
DataError = (sqlite3.DataError,) + ((psycopg.DataError,) if psycopg else ())

NOW_TEXT = "to_char(statement_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"
FMT = '%Y-%m-%d %H:%M:%S'


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, '') or default)
    except ValueError:
        return default


def utc_text(offset_seconds: float = 0.0) -> str:
    """Now (+ offset) as SQLite's CURRENT_TIMESTAMP text: 'YYYY-MM-DD HH:MM:SS', UTC."""
    return time.strftime(FMT, time.gmtime(time.time() + offset_seconds))


# ---------------------------------------------------------------- backend choice
def database_url() -> str | None:
    """The PostgreSQL URL, or None for SQLite. A DATABASE_URL that is set but is not a
    postgresql:// URL stops the process: silently running on the (frozen) SQLite file
    after the cut-over would serve old saves."""
    url = (os.environ.get('DATABASE_URL') or '').strip()
    if url.startswith(('postgresql://', 'postgres://')):
        return url
    if url:
        raise SystemExit('[db] DATABASE_URL is set but is not a postgresql:// URL: refusing to start '
                         '(unset it to run on SQLite)')
    test = (os.environ.get('TEST_DATABASE_URL') or '').strip()
    return test if test.startswith(('postgresql://', 'postgres://')) else None


def test_mode() -> bool:
    return not (os.environ.get('DATABASE_URL') or '').strip() and database_url() is not None


def is_pg(db) -> bool:
    return getattr(db, 'dialect', 'sqlite') == 'pg'


def for_update(db, of: str = '') -> str:
    """' FOR UPDATE' (row lock until commit) on PostgreSQL, '' on SQLite (BEGIN IMMEDIATE locks all)."""
    return (' FOR UPDATE' + (' OF ' + of if of else '')) if is_pg(db) else ''


# ---------------------------------------------------------------- SQL translation
_TOKENS = re.compile(r"('(?:[^']|'')*')|(\"(?:[^\"]|\"\")*\")|(\?\d*)|(%)")
_DATETIME = re.compile(r"datetime\(\s*'now'\s*(?:,\s*('(?:[^']|'')*'|\?)\s*)?\)", re.I)
_OR_IGNORE = re.compile(r'^\s*INSERT\s+OR\s+IGNORE\s+INTO\b', re.I)
_OR_REPLACE = re.compile(r'^\s*(INSERT\s+OR\s+REPLACE|REPLACE)\s+INTO\b', re.I)
_FIRST = re.compile(r'^\s*(\w+)(?:\s+(\w+))?')
_KINDS = dict(SELECT='select', WITH='select', VALUES='select', SHOW='select', INSERT='dml', UPDATE='dml', DELETE='dml',
              CREATE='ddl', DROP='ddl', ALTER='ddl', DO='ddl', BEGIN='begin', COMMIT='commit', END='commit',
              ROLLBACK='rollback', PRAGMA='pragma', SET='set')


def _datetime(m) -> str:
    arg = m.group(1)
    if arg is None:
        return NOW_TEXT
    return f"to_char((statement_timestamp() AT TIME ZONE 'UTC') + CAST({arg} AS interval), 'YYYY-MM-DD HH24:MI:SS')"


@functools.lru_cache(maxsize=1024)
def translate(sql: str, params: bool = True) -> tuple[str, str]:
    """(PostgreSQL SQL, kind) of a SQLite-dialect statement. kind: select, dml, ddl,
    begin, commit, rollback, pragma, set. `params`: placeholders will be bound (psycopg
    then needs `%` doubled)."""
    m = _FIRST.match(sql)
    kind = _KINDS.get(m.group(1).upper(), 'select') if m else 'select'
    if kind in ('begin', 'commit', 'rollback', 'pragma'):
        return '', kind
    if _OR_REPLACE.match(sql):
        raise NotImplementedError('INSERT OR REPLACE: write an explicit ON CONFLICT ... DO UPDATE')
    ignore = bool(_OR_IGNORE.match(sql))
    if ignore:
        sql = _OR_IGNORE.sub('INSERT INTO', sql, count=1)
    out = []
    pos = 0
    for tok in _TOKENS.finditer(sql):
        head = sql[pos:tok.start()]
        head = re.sub(r'\bCURRENT_TIMESTAMP\b', NOW_TEXT, head, flags=re.I)
        out.append(head)
        lit, ident, mark, pct = tok.groups()
        if lit is not None:
            out.append(lit.replace('%', '%%') if params else lit)
        elif ident is not None:
            out.append(ident)
        elif mark is not None:
            if len(mark) > 1:
                raise NotImplementedError('numbered ?NNN placeholders: pass the value again instead')
            out.append('%s')
        else:
            out.append('%%' if params else '%')
        pos = tok.end()
    out.append(re.sub(r'\bCURRENT_TIMESTAMP\b', NOW_TEXT, sql[pos:], flags=re.I))
    text = ''.join(out)
    # datetime('now', X): X is a literal or a %s placeholder, both kept as they are.
    text = re.sub(r"datetime\(\s*'now'\s*(?:,\s*('(?:[^']|'')*'|%s)\s*)?\)", _datetime, text, flags=re.I)
    if ignore:
        text = text.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    return text, kind


# ---------------------------------------------------------------- rows and cursors
@functools.lru_cache(maxsize=512)
def _row_class(names: tuple):
    index = {n: i for i, n in enumerate(names)}

    class Row(tuple):
        """sqlite3.Row look-alike: r[0], r['name'], keys(), dict(r)."""
        __slots__ = ()
        _index = index
        _names = names

        def __getitem__(self, key):
            if isinstance(key, str):
                return tuple.__getitem__(self, self._index[key])
            return tuple.__getitem__(self, key)

        def keys(self):
            return list(self._names)

    return Row


def _row_factory(cursor):
    desc = cursor.description
    if not desc:
        return tuple
    cls = _row_class(tuple(d.name for d in desc))
    return cls


class Cursor:
    """The complete result of one statement (already fetched: nothing stays open)."""
    __slots__ = ('_rows', '_i', 'rowcount', 'description', 'lastrowid')

    def __init__(self, rows=(), rowcount=-1, description=None):
        self._rows = rows
        self._i = 0
        self.rowcount = rowcount
        self.description = description
        self.lastrowid = None

    def fetchone(self):
        if self._i >= len(self._rows):
            return None
        self._i += 1
        return self._rows[self._i - 1]

    def fetchall(self):
        rest = self._rows[self._i:]
        self._i = len(self._rows)
        return list(rest)

    def fetchmany(self, size=1):
        rest = self._rows[self._i:self._i + size]
        self._i += len(rest)
        return list(rest)

    def __iter__(self):
        while self._i < len(self._rows):
            self._i += 1
            yield self._rows[self._i - 1]

    def close(self):
        self._rows = ()


if psycopg is not None:
    class _NumericLoader(Loader):
        """numeric -> int when whole (SUM of integers, like SQLite), else float."""
        def load(self, data):
            s = bytes(data).decode()
            try:
                return int(s)
            except ValueError:
                return float(s)

    IDLE = pq.TransactionStatus.IDLE
    INERROR = pq.TransactionStatus.INERROR
    INTRANS = pq.TransactionStatus.INTRANS

    class PoolTimeout(psycopg.OperationalError):
        pass
else:  # pragma: no cover
    class PoolTimeout(Exception):
        pass


class PgConnection:
    """A pooled psycopg connection that speaks the game's SQLite-style SQL (see module doc)."""
    dialect = 'pg'

    def __init__(self, raw, pool):
        self.raw = raw
        self._pool = pool
        self._closed = False
        self._used = False  # a statement has succeeded on this checkout: never retry after that

    # ---- transactions
    @property
    def in_transaction(self) -> bool:
        return self.raw.info.transaction_status != IDLE

    def begin(self) -> None:
        if self.raw.info.transaction_status == IDLE:
            self._first(lambda: self.raw.execute('BEGIN'))

    def _first(self, fn):
        """Run fn; if it is the first statement of this checkout and the pooled connection
        turns out to be dead (PostgreSQL restarted, backend terminated), retry it ONCE on a
        fresh connection. Safe: nothing ran on the dead one, and after the first success (or
        inside a transaction) there is no retry, so a write is never repeated."""
        if self._used or self.raw.info.transaction_status != IDLE:
            return fn()
        try:
            out = fn()
        except (psycopg.OperationalError, psycopg.InterfaceError) as e:
            if not _connection_lost(self.raw, e):
                raise
            self._fresh()
            out = fn()
        self._used = True
        return out

    def _fresh(self) -> None:
        """Swap the dead connection for a new one (the pool's open count stays the same)."""
        try:
            self.raw.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.raw = self._pool._open()
        except BaseException:
            self._closed = True  # the slot is given back here, not again in close()
            self._pool._forget()
            raise

    def commit(self) -> None:
        st = self.raw.info.transaction_status
        if st == IDLE:
            return
        if st == INERROR:
            self.raw.execute('ROLLBACK')
            raise psycopg.OperationalError('commit of a failed transaction: rolled back')
        self.raw.execute('COMMIT')

    def rollback(self) -> None:
        if self.raw.info.transaction_status != IDLE:
            self.raw.execute('ROLLBACK')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.commit()
            else:
                try:
                    self.rollback()
                except Exception:  # noqa: BLE001 - the original error matters more
                    pass
        finally:
            self.close()
        return False

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._pool.give(self.raw)

    # ---- statements
    def execute(self, sql: str, params=()):
        """SQLite-dialect SQL (see translate)."""
        q, kind = translate(sql, bool(params))
        return self._run(q, kind, params)

    def pg(self, sql: str, params=()):
        """Native PostgreSQL SQL (%s / %(name)s placeholders), same transaction rules."""
        m = _FIRST.match(sql)
        kind = _KINDS.get(m.group(1).upper(), 'select') if m else 'select'
        return self._run(sql, kind, params)

    def _run(self, q: str, kind: str, params):
        if kind == 'pragma':
            return Cursor()
        if kind == 'begin':
            self.begin()
            return Cursor()
        if kind == 'commit':
            self.commit()
            return Cursor()
        if kind == 'rollback':
            self.rollback()
            return Cursor()
        if kind == 'dml':
            self.begin()

        def run():
            cur = self.raw.cursor()
            try:
                cur.execute(q, params if params else None)
                rows = cur.fetchall() if cur.description is not None else ()
                return Cursor(rows, cur.rowcount, cur.description)
            finally:
                cur.close()
        if kind == 'select':  # outside a transaction a SELECT may be retried (see _first)
            return self._first(run)
        out = run()
        self._used = True
        return out

    def executemany(self, sql: str, seq) -> Cursor:
        """One SQLite-dialect statement for each parameter tuple (a data change: opens a transaction)."""
        q, kind = translate(sql, True)
        if kind == 'dml':
            self.begin()
        cur = self.raw.cursor()
        try:
            cur.executemany(q, list(seq))
            self._used = True
            return Cursor((), cur.rowcount, None)
        finally:
            cur.close()

    def executescript(self, script: str) -> None:
        """Several statements, no parameters (PostgreSQL DDL)."""
        self.raw.execute(script)
        self._used = True

    def set_local(self, name: str, value: str) -> None:
        """SET LOCAL for the current transaction (opened if needed)."""
        self.begin()
        self.raw.execute('SELECT set_config(%s, %s, true)', (name, str(value)))


def _connection_lost(raw, e) -> bool:
    """The server side is gone (not a statement error such as a timeout or a constraint)."""
    state = getattr(e, 'sqlstate', None) or ''
    return raw.closed or getattr(raw, 'broken', False) or state.startswith(('08', '57P'))


def _alive(raw) -> bool:
    try:
        raw.execute('SELECT 1')
        return raw.info.transaction_status == IDLE
    except Exception:  # noqa: BLE001
        return False


_ORPHANS: list = []  # connections inherited across fork(): never used, never closed in the child


class PgPool:
    """Connections of one Store in one process (see the module doc)."""

    def __init__(self, url: str, schema: str | None = None):
        if psycopg is None:
            raise RuntimeError('DATABASE_URL is set but psycopg (python3-psycopg) is not installed')
        self.url = url
        self.schema = schema
        self.keep = max(0, _env_int('PG_POOL', 6))
        self.cap = max(1, _env_int('PG_POOL_MAX', 12), self.keep)
        self.wait = max(0.1, _env_int('PG_POOL_WAIT_MS', 10000) / 1000)
        # an idle connection older than this is pinged before use (a PostgreSQL restart kills them all)
        self.check = max(0, _env_int('PG_POOL_CHECK_MS', 5000)) / 1000
        self.settings = dict(statement_timeout=str(_env_int('PG_STATEMENT_TIMEOUT_MS', 10000)),
                             lock_timeout=str(_env_int('PG_LOCK_TIMEOUT_MS', 5000)),
                             idle_in_transaction_session_timeout=str(_env_int('PG_IDLE_TX_TIMEOUT_MS', 30000)))
        sync = (os.environ.get('PG_SYNCHRONOUS_COMMIT') or '').strip().lower()
        if sync in ('on', 'off', 'local', 'remote_write', 'remote_apply'):
            self.settings['synchronous_commit'] = sync
        if schema:
            self.settings['search_path'] = schema
        self.idle: list = []
        self.open = 0
        self.cond = threading.Condition()
        self.pid = os.getpid()

    def _fork_check(self) -> None:
        if self.pid != os.getpid():  # forked: the parent's connections are not ours
            _ORPHANS.extend(raw for raw, _ in self.idle)
            self.idle, self.open, self.pid = [], 0, os.getpid()

    def _open(self):
        raw = psycopg.connect(self.url, autocommit=True, row_factory=_row_factory,
                              application_name=os.environ.get('PG_APPLICATION_NAME', 'mot-ngay-lam-nghe'))
        try:
            raw.adapters.register_loader('numeric', _NumericLoader)
            names = list(self.settings)
            raw.execute('SELECT ' + ', '.join('set_config(%s, %s, false)' for _ in names),
                        [x for n in names for x in (n, self.settings[n])])
        except BaseException:
            raw.close()
            raise
        return raw

    def connect(self) -> PgConnection:
        deadline = time.monotonic() + self.wait
        while True:
            raw = None
            with self.cond:
                self._fork_check()
                while True:
                    while self.idle:
                        raw, since = self.idle.pop()
                        if raw.closed or getattr(raw, 'broken', False):
                            self.open -= 1
                            raw = None
                            continue
                        break
                    if raw is not None or self.open < self.cap:
                        break
                    left = deadline - time.monotonic()
                    if left <= 0:
                        raise PoolTimeout(f'no database connection free after {self.wait:.0f} s (PG_POOL_MAX={self.cap})')
                    self.cond.wait(left)
                if raw is None:
                    self.open += 1
            if raw is None:
                break
            if time.monotonic() - since <= self.check or _alive(raw):
                return PgConnection(raw, self)
            self._forget()  # dead after a long idle: drop it and try the next one
            try:
                raw.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            return PgConnection(self._open(), self)
        except BaseException:
            with self.cond:
                self.open -= 1
                self.cond.notify()
            raise

    def give(self, raw) -> None:
        """Back to the pool only when idle: no transaction, nothing running."""
        keep = False
        if self.pid == os.getpid() and not raw.closed and not getattr(raw, 'broken', False):
            try:
                st = raw.info.transaction_status
                if st in (INTRANS, INERROR):
                    raw.execute('ROLLBACK')
                    st = raw.info.transaction_status
                keep = st == IDLE
            except Exception:  # noqa: BLE001 - a broken connection is simply dropped
                keep = False
        if self.pid != os.getpid():  # a connection of the parent, seen in a child: leave it alone
            _ORPHANS.append(raw)
            return
        with self.cond:
            if keep and len(self.idle) < self.keep:
                self.idle.append((raw, time.monotonic()))
                self.cond.notify()
                return
            self.open -= 1
            self.cond.notify()
        try:
            raw.close()
        except Exception:  # noqa: BLE001
            pass

    def _forget(self) -> None:
        """A checked-out connection is gone (closed by the caller): free its slot."""
        with self.cond:
            self.open -= 1
            self.cond.notify()

    def clear(self) -> None:
        """Close idle connections (before fork(), and in tests)."""
        with self.cond:
            if self.pid != os.getpid():
                self._fork_check()
                return
            idle, self.idle = self.idle, []
            self.open -= len(idle)
            self.cond.notify_all()
        for raw, _ in idle:
            try:
                raw.close()
            except Exception:  # noqa: BLE001
                pass

    def stats(self) -> dict:
        with self.cond:
            return dict(open=self.open, idle=len(self.idle), cap=self.cap, keep=self.keep)


# ---------------------------------------------------------------- pools per database path
_POOLS: dict = {}
_POOLS_LOCK = threading.Lock()


def pool_for(path: str) -> PgPool | None:
    """The PostgreSQL pool behind a Store(path), or None for SQLite. With DATABASE_URL
    every path shares one database; in test mode each path gets its own schema."""
    url = database_url()
    if not url:
        return None
    schema = _test_schema(path) if test_mode() else None
    with _POOLS_LOCK:
        key = (url, schema)
        pool = _POOLS.get(key)
        if pool is None or pool.pid != os.getpid():
            pool = _POOLS[key] = PgPool(url, schema)
    return pool


# ---------------------------------------------------------------- test mode: a schema per path
_TEST_SCHEMAS: dict = {}   # schema -> directory of the path, created by this process


def _test_run() -> str:
    run = os.environ.get('MNL_PG_TEST_RUN')
    if not run:
        run = os.environ['MNL_PG_TEST_RUN'] = secrets.token_hex(4)
        atexit.register(_drop_test_schemas, run)
    return run


def _test_schema(path: str) -> str:
    full = os.path.abspath(str(path))
    name = f't_{_test_run()}_{hashlib.sha1(full.encode()).hexdigest()[:12]}'
    if name not in _TEST_SCHEMAS:
        _sweep_test_schemas()
        with psycopg.connect(database_url(), autocommit=True) as c:
            c.execute(f'CREATE SCHEMA IF NOT EXISTS {name}')
        _TEST_SCHEMAS[name] = os.path.dirname(full)
    return name


def _sweep_test_schemas() -> None:
    """Drop the schemas of paths whose (temporary) directory is gone."""
    gone = [s for s, d in _TEST_SCHEMAS.items() if not os.path.isdir(d)]
    if not gone:
        return
    with _POOLS_LOCK:
        for key in [k for k in _POOLS if k[1] in gone]:
            _POOLS.pop(key).clear()
    try:
        with psycopg.connect(database_url(), autocommit=True) as c:
            for s in gone:
                c.execute(f'DROP SCHEMA IF EXISTS {s} CASCADE')
                _TEST_SCHEMAS.pop(s, None)
    except psycopg.Error:
        pass  # still in use: next sweep or the end of the run


def _drop_test_schemas(run: str) -> None:
    if os.environ.get('MNL_PG_TEST_KEEP'):
        return
    with _POOLS_LOCK:
        for pool in _POOLS.values():
            pool.clear()
    try:
        with psycopg.connect(database_url(), autocommit=True) as c:
            names = [r[0] for r in c.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE %s", (f't\\_{run}\\_%',))]
            for s in names:
                c.execute(f'DROP SCHEMA IF EXISTS {s} CASCADE')
    except Exception:  # noqa: BLE001
        pass


if test_mode():
    _test_run()  # decided in the test runner, inherited by the servers it starts
