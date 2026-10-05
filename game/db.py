"""PostgreSQL connections, SQL parameter adaptation, pooling and isolated test schemas.

DATABASE_URL=postgresql://user@host:port/db is required (the password comes from
the URL, ~/.pgpass or PGPASSWORD; never log the URL). TEST_DATABASE_URL may be used
instead for isolated tests. There is no local database fallback.

The game uses native PostgreSQL SQL; PgConnection adapts its parameters:
* `?` placeholders -> `%s` (never inside string literals), a literal `%` -> `%%`;
* CURRENT_TIMESTAMP -> UTC timestamp TEXT,
  'YYYY-MM-DD HH:MM:SS' in UTC (the columns stay text, see game/pg_schema.py);
Unsupported database syntax is rejected. Rows are read by name AND by
index; SUM() of integers comes back as int.

Transactions preserve the Store interface: the psycopg connection is in autocommit
mode, a data change (INSERT/UPDATE/DELETE) opens a transaction, commit()/rollback()
or leaving `with store.connect() as db:` ends it. A SELECT outside a transaction runs
on its own and leaves nothing open: rows are fetched completely by execute(), there is
never a server-side cursor. A connection goes back to the pool only when libpq reports
it idle (no transaction, nothing in progress); otherwise it is rolled back or closed.

Pool (per Store, per process): at most PG_POOL_MAX connections are open at once (default 12;
a thread waits up to PG_POOL_WAIT_MS for one). A connection handed back is kept for the next
request: PG_POOL of them (default 6) indefinitely, the others until they have been idle for
PG_POOL_IDLE_MS (default 10000), when a reaper thread closes them. (Closing everything above
PG_POOL at once, as before 0.9.5, made every burst above 6 requests open and close backends:
a fork plus authentication on the database server each time.) Every PG_POOL_LOG_S (60) a
process that opened connections or waited for one logs `[pg-pool]` counts to stderr.
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
import sys
import threading
import time
import weakref

try:
    import psycopg
    from psycopg import pq
    from psycopg.adapt import Loader
    from psycopg.conninfo import conninfo_to_dict
except ImportError as exc:  # pragma: no cover - deployment dependency guard
    raise SystemExit('[db] PostgreSQL requires psycopg; install the project dependencies') from exc

Error = (psycopg.Error,)
IntegrityError = (psycopg.IntegrityError,)
OperationalError = (psycopg.OperationalError,)
# bad client data the database refuses (e.g. a NUL in a text value on PostgreSQL): a 400, not a 500
DataError = (psycopg.DataError,)

NOW_TEXT = "to_char(statement_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"
# The interval is a bound parameter, so housekeeping uses the database's UTC clock.
UTC_INTERVAL_TEXT = "to_char((statement_timestamp() AT TIME ZONE 'UTC') + CAST(? AS interval), 'YYYY-MM-DD HH24:MI:SS')"
FMT = '%Y-%m-%d %H:%M:%S'


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, '') or default)
    except ValueError:
        return default


def utc_text(offset_seconds: float = 0.0) -> str:
    """Now (+ offset) as timestamp text: 'YYYY-MM-DD HH:MM:SS', UTC."""
    return time.strftime(FMT, time.gmtime(time.time() + offset_seconds))


# ---------------------------------------------------------------- configuration
def validate_url(url: str | None, setting: str = 'DATABASE_URL') -> str:
    """Require a PostgreSQL URL, reporting configuration errors without credentials."""
    url = (url or '').strip()
    if not url:
        raise SystemExit(f'[db] {setting} is required; set a postgresql:// URL')
    if not url.startswith(('postgresql://', 'postgres://')):
        raise SystemExit(f'[db] {setting} must be a postgresql:// URL')
    try:
        config = conninfo_to_dict(url)
        for port in (config.get('port') or '').split(','):
            if port and (not port.isdigit() or not 1 <= int(port) <= 65535):
                raise ValueError('invalid PostgreSQL port')
    except (psycopg.Error, ValueError):
        raise SystemExit(f'[db] {setting} is not a valid PostgreSQL URL') from None
    return url


def database_url() -> str:
    """The required PostgreSQL URL; tests can use TEST_DATABASE_URL in its absence."""
    url = (os.environ.get('DATABASE_URL') or '').strip()
    if url:
        return validate_url(url)
    test = (os.environ.get('TEST_DATABASE_URL') or '').strip()
    return validate_url(test, 'TEST_DATABASE_URL') if test else validate_url(url)


def test_mode() -> bool:
    return not (os.environ.get('DATABASE_URL') or '').strip() and bool((os.environ.get('TEST_DATABASE_URL') or '').strip())


def for_update(db, of: str = '') -> str:
    """Lock the selected rows until the PostgreSQL transaction ends."""
    return ' FOR UPDATE' + (' OF ' + of if of else '')


# ---------------------------------------------------------------- SQL parameter adaptation
_TOKENS = re.compile(r"('(?:[^']|'')*')|(\"(?:[^\"]|\"\")*\")|(\?\d*)|(%)")
_SQLITE_SYNTAX = re.compile(r'\b(?:INSERT\s+OR\s+(?:IGNORE|REPLACE)|REPLACE\s+INTO|BEGIN\s+(?:IMMEDIATE|EXCLUSIVE)|PRAGMA)\b|\b(?:datetime|julianday|strftime|unixepoch)\s*\(', re.I)
_FIRST = re.compile(r'^\s*(\w+)(?:\s+(\w+))?')
_KINDS = dict(SELECT='select', WITH='select', VALUES='select', SHOW='select', INSERT='dml', UPDATE='dml', DELETE='dml',
              CREATE='ddl', DROP='ddl', ALTER='ddl', DO='ddl', BEGIN='begin', COMMIT='commit', END='commit',
              ROLLBACK='rollback', SET='set')


def _validate_sql(sql: str) -> None:
    syntax = _TOKENS.sub(lambda m: ' ' * len(m.group()) if m.group(1) or m.group(2) else m.group(), sql)
    if _SQLITE_SYNTAX.search(syntax):
        raise NotImplementedError('SQLite-only SQL syntax is not supported; write native PostgreSQL SQL')


@functools.lru_cache(maxsize=1024)
def translate(sql: str, params: bool = True) -> tuple[str, str]:
    """(Parameter-adapted PostgreSQL SQL, kind) of a statement. kind: select, dml, ddl,
    begin, commit, rollback, set. `params`: placeholders will be bound (psycopg
    then needs `%` doubled)."""
    _validate_sql(sql)
    m = _FIRST.match(sql)
    kind = _KINDS.get(m.group(1).upper(), 'select') if m else 'select'
    if kind in ('begin', 'commit', 'rollback'):
        return '', kind
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
    return ''.join(out), kind


# ---------------------------------------------------------------- rows and cursors
@functools.lru_cache(maxsize=512)
def _row_class(names: tuple):
    index = {n: i for i, n in enumerate(names)}

    class Row(tuple):
        """A row with positional and named access: r[0], r['name'], keys(), dict(r)."""
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
    __slots__ = ('_rows', '_i', 'rowcount', 'description')

    def __init__(self, rows=(), rowcount=-1, description=None):
        self._rows = rows
        self._i = 0
        self.rowcount = rowcount
        self.description = description

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


class _NumericLoader(Loader):
    """numeric -> int when whole (SUM of integers), else float."""
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


class PgConnection:
    """A pooled psycopg connection compatible with existing game queries."""
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
        """PostgreSQL SQL using ? placeholders (see translate)."""
        q, kind = translate(sql, bool(params))
        return self._run(q, kind, params)

    def pg(self, sql: str, params=()):
        """Native PostgreSQL SQL (%s / %(name)s placeholders), same transaction rules."""
        _validate_sql(sql)
        m = _FIRST.match(sql)
        kind = _KINDS.get(m.group(1).upper(), 'select') if m else 'select'
        return self._run(sql, kind, params)

    def _run(self, q: str, kind: str, params):
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
        """One game statement for each parameter tuple (a data change opens a transaction)."""
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
        self.url = validate_url(url)
        self.schema = schema
        self.keep = max(0, _env_int('PG_POOL', 6))
        self.cap = max(1, _env_int('PG_POOL_MAX', 12), self.keep)
        # connections above `keep` are closed after this long unused (by the reaper, see _reap_loop)
        self.idle_max = max(0, _env_int('PG_POOL_IDLE_MS', 10000)) / 1000
        self.log_every = max(0, _env_int('PG_POOL_LOG_S', 60))
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
        self.idle: list = []   # (connection, monotonic time it came back), oldest first
        self.open = 0
        self.cond = threading.Condition()
        self.pid = os.getpid()
        self.counts = dict(opened=0, closed=0, checkouts=0, waits=0, timeouts=0)  # since start
        self._logged = dict(self.counts)
        self._log_at = time.monotonic() + self.log_every
        self._reaped = False  # this process's reaper knows the pool

    def _fork_check(self) -> None:
        if self.pid != os.getpid():  # forked: the parent's connections are not ours
            _ORPHANS.extend(raw for raw, _ in self.idle)
            self.idle, self.open, self.pid = [], 0, os.getpid()
            self.counts = dict.fromkeys(self.counts, 0)
            self._logged, self._reaped = dict(self.counts), False

    def _open(self):
        self.counts['opened'] += 1  # (an int += under the GIL; a lost update would only blur a log line)
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
                if not self._reaped:
                    self._reaped = True
                    _reap(self)
                self.counts['checkouts'] += 1
                waited = False
                while True:
                    while self.idle:
                        raw, since = self.idle.pop()
                        if raw.closed or getattr(raw, 'broken', False):
                            self.open -= 1
                            self.counts['closed'] += 1
                            raw = None
                            continue
                        break
                    if raw is not None or self.open < self.cap:
                        break
                    left = deadline - time.monotonic()
                    if not waited:
                        waited = True
                        self.counts['waits'] += 1
                    if left <= 0:
                        self.counts['timeouts'] += 1
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
            if keep and len(self.idle) < self.cap:  # kept for the next request (see reap)
                self.idle.append((raw, time.monotonic()))
                self.cond.notify()
                return
            self.open -= 1
            self.counts['closed'] += 1
            self.cond.notify()
        try:
            raw.close()
        except Exception:  # noqa: BLE001
            pass

    def _forget(self) -> None:
        """A checked-out connection is gone (closed by the caller): free its slot."""
        with self.cond:
            self.open -= 1
            self.counts['closed'] += 1
            self.cond.notify()

    def reap(self, now: float | None = None) -> int:
        """Close the idle connections above `keep` that nobody used for idle_max seconds (the
        least recently used first); log the counters when due. The number closed."""
        now = time.monotonic() if now is None else now
        gone = []
        with self.cond:
            if self.pid != os.getpid():
                return 0
            while len(self.idle) > self.keep and now - self.idle[0][1] >= self.idle_max:
                gone.append(self.idle.pop(0)[0])
            self.open -= len(gone)
            self.counts['closed'] += len(gone)
            line = self._log_line(now)
        for raw in gone:
            try:
                raw.close()
            except Exception:  # noqa: BLE001
                pass
        if line:
            sys.stderr.write(line)
        return len(gone)

    def _log_line(self, now: float) -> str:
        """`[pg-pool]` counts of the last PG_POOL_LOG_S seconds, when a connection was opened or a
        request waited for one (connection churn and pool exhaustion); '' otherwise."""
        if not self.log_every or now < self._log_at:
            return ''
        d = {k: v - self._logged.get(k, 0) for k, v in self.counts.items()}
        self._logged, self._log_at = dict(self.counts), now + self.log_every
        if not (d['opened'] or d['waits']):
            return ''
        return (f"[pg-pool] pid={os.getpid()} last {self.log_every}s: opened {d['opened']}, closed {d['closed']}, "
                f"checkouts {d['checkouts']}, waited {d['waits']}, timed out {d['timeouts']}; "
                f"open {self.open}/{self.cap}, idle {len(self.idle)}, keep {self.keep}\n")

    def clear(self) -> None:
        """Close idle connections (before fork(), and in tests)."""
        with self.cond:
            if self.pid != os.getpid():
                self._fork_check()
                return
            idle, self.idle = self.idle, []
            self.open -= len(idle)
            self.counts['closed'] += len(idle)
            self.cond.notify_all()
        for raw, _ in idle:
            try:
                raw.close()
            except Exception:  # noqa: BLE001
                pass

    def stats(self) -> dict:
        with self.cond:
            return dict(open=self.open, idle=len(self.idle), cap=self.cap, keep=self.keep, **self.counts)


# ---------------------------------------------------------------- the reaper (one thread per process)
_REAP_POOLS: weakref.WeakSet = weakref.WeakSet()
_REAP_LOCK = threading.Lock()
_REAP_PID = [0]


def _reap(pool: PgPool) -> None:
    """Have this process's reaper thread look after `pool` (started on first use, after fork)."""
    with _REAP_LOCK:
        if _REAP_PID[0] != os.getpid():  # none yet in this process (threads do not survive fork)
            _REAP_POOLS.clear()
            _REAP_PID[0] = os.getpid()
            threading.Thread(target=_reap_loop, daemon=True, name='pg-pool-reaper').start()
        _REAP_POOLS.add(pool)


def _reap_loop() -> None:
    pid = os.getpid()
    while _REAP_PID[0] == pid:
        with _REAP_LOCK:
            pools = list(_REAP_POOLS)
        every = min([max(0.5, min(p.idle_max / 2, 5.0)) for p in pools] or [5.0])
        del pools
        time.sleep(every)
        with _REAP_LOCK:
            pools = list(_REAP_POOLS)
        for p in pools:
            try:
                p.reap()
            except Exception:  # noqa: BLE001 - the reaper never dies
                pass
        del pools


# ---------------------------------------------------------------- pools per database path
_POOLS: dict = {}
_POOLS_LOCK = threading.Lock()


def pool_for(path: str) -> PgPool:
    """The PostgreSQL pool behind a Store namespace. Production namespaces share one
    database; in test mode each namespace gets its own schema."""
    url = database_url()
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
