# PostgreSQL

The game runs on SQLite by default. When `DATABASE_URL` is set to a `postgresql://`
URL, it runs on PostgreSQL 16 instead. The code is the same for both. The dialect
details live in `game/db.py` and the schema lives in `game/pg_schema.py`.

## Backend switch (game server)

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | unset | `postgresql://user@127.0.0.1:5432/dbname`. A value that is not a `postgresql://` URL stops the server at start-up (it never falls back to SQLite). When set, the server uses PostgreSQL and ignores `--db`/`GAME_DB` for the data. The password belongs in the env file (mode 600) or in `~/.pgpass`, never in the repository, and never in logs. The server never prints the URL. |
| `PG_POOL` | 6 | Idle connections kept indefinitely per worker process. Connections above it (up to `PG_POOL_MAX`) are kept too, and closed once unused for `PG_POOL_IDLE_MS`. |
| `PG_POOL_IDLE_MS` | 10000 | How long a connection above `PG_POOL` stays open unused (a reaper thread closes it). Before 0.9.5 those were closed as soon as they came back, so every burst above `PG_POOL` requests opened new backends (a fork and an authentication on the database server each). |
| `PG_POOL_LOG_S` | 60 | Every this many seconds, a worker that opened connections or waited for a free one logs a `[pg-pool]` line (opened, closed, checkouts, waited, timed out; open, idle). A steady stream of `opened` means churn; `waited` means the pool is too small for the load. 0 = off. |
| `PG_POOL_MAX` | 12 | Most connections one worker opens at once. With `WORKERS=4` that is 48 at most, under the `max_connections = 60` of `deploy/pg/install_pg16.sh` minus the reserved and tool connections. Keep `WORKERS` x `PG_POOL_MAX` under the server's `max_connections`, minus the connections that tools need. A request waits up to `PG_POOL_WAIT_MS` (10000) for a free connection. |
| `PG_POOL_CHECK_MS` | 5000 | An idle connection older than this is checked (`SELECT 1`) before use. After a PostgreSQL restart, a dead connection is also replaced when its first statement fails, and that statement is retried once. There is never a retry after a statement has succeeded, so a write is never repeated. |
| `PG_STATEMENT_TIMEOUT_MS` | 10000 | `statement_timeout` of every connection. Admin statistics raise it for their one heavy query (`ADMIN_STATS_TIMEOUT`, default `120s`). |
| `PG_LOCK_TIMEOUT_MS` | 5000 | `lock_timeout` of every connection. A player command's save write waits longer for its row lock: 12 s, the same as SQLite's writer turn (`BUSY_MS`). Its statement timeout is raised to match, so a burst of commands on one save queues instead of failing. |
| `PG_IDLE_TX_TIMEOUT_MS` | 30000 | `idle_in_transaction_session_timeout`. |
| `PG_SYNCHRONOUS_COMMIT` | server default (`on`) | Optional: `off` stops each commit from waiting for its WAL flush. A crash of PostgreSQL or of the machine can then lose the last ~0.6 s of commits, but never corrupts data. That is close to SQLite's `synchronous=NORMAL` today. Use it only if the disk is the bottleneck. |
| `TEST_DATABASE_URL` | unset | **Tests only.** With no `DATABASE_URL`, it runs the test suite on PostgreSQL. Each database path gets its own schema `t_<run>_<hash>`, dropped afterwards. Never set it on a server. |

Requirements: `python3-psycopg` 3.1 or later (`apt install python3-psycopg`). The game does
not use `psycopg_pool`: `game/db.py` has its own small pool.

### What changes on PostgreSQL

- **No global writer turn.** SQLite lets one writer in at a time (the thread lock plus the
  `-writer.lock` flock). On PostgreSQL, a command's compare-and-set is one short
  transaction: `SELECT … FROM sessions WHERE sid=… FOR UPDATE`, then the revision check,
  then the save, the archive rows and the receipt. The row lock only serializes commands of
  the **same** save, so different players never wait for each other. The CPU work (the
  reducer, validation, JSON) still runs outside any lock, as before. The "compute under
  the lock" fallback holds only that save's row lock.
- **Connections.** They are opened lazily in each worker, after `fork()`. The parent closes
  its own before forking. The connection runs in autocommit mode. A data change opens a
  transaction; `commit()`/`rollback()`, or leaving `with store.connect() as db:`, closes it.
  This is the same rule as Python's `sqlite3`. A SELECT outside a transaction leaves
  nothing open, because every row is fetched at once and there are no server-side cursors.
  A connection goes back to the pool only when libpq reports it idle; otherwise it is
  rolled back or closed. The WAL-pinning bug of the SQLite pool cannot happen on
  PostgreSQL. `tests/test_pg_backend.py` checks `pg_stat_activity` for this.
- **Schema.** The schema matches SQLite column for column:
  - text columns are `text COLLATE "C"` (byte order, like SQLite);
  - timestamps stay text, `'YYYY-MM-DD HH:MM:SS'` UTC;
  - `sessions.state` stays text, with lz4 TOAST compression;
  - AUTOINCREMENT columns become identity columns.

  The stat_* triggers of the admin dashboard are PL/pgSQL triggers with the same names.
  The server creates the schema at start-up only when it is missing (`mnl_meta.schema_version`).
- **Rate limits shared by workers** (`hits`) live in the same database, not in
  `<db>-limits.sqlite3`. A per-key advisory lock stands in for SQLite's `BEGIN IMMEDIATE`.
- **Housekeeping.**
  - The WAL checkpointer thread does nothing on PostgreSQL.
  - Receipt pruning has no rowid to go by, so it keeps the newest receipts by `created_at`.
  - The guest sweep walks the table by `sid`.
- **Logs.**
  - `[slow-cmd]` is unchanged.
  - `[slow-lock]` reports how long the command waited for its save's row lock, plus the wait for a pooled connection.
  - `[slow-write]` is unchanged.

### SQLite changes in the same release

`DB_POOL` now defaults to **0**, so SQLite connections are not pooled. A pooled connection
could keep a read snapshot open: a SELECT whose rows were not all fetched leaves its
statement running, and `sqlite3`'s `in_transaction` does not see it. That pins the WAL, which
then grows without bound. This happened on 2026-09-30. Opening a connection costs about 1 ms.
`DB_POOL=n` brings the old pool back.

### Rolling back

Unset `DATABASE_URL` and restart: the game is back on the SQLite file. Anything written to
PostgreSQL in the meantime is not in that file.

### Tests

```
python -m unittest discover -s tests                                   # SQLite
TEST_DATABASE_URL=postgresql://user:pw@127.0.0.1:5432/test python -m unittest discover -s tests   # PostgreSQL 16
```

A few tests check SQLite-only mechanics (the writer turn across processes, WAL files,
the limits file). They are skipped on PostgreSQL, and `tests/test_pg_backend.py` covers
the PostgreSQL side of the same guarantees:

- players do not block each other, and one save is serialized;
- conflicts;
- the pool never keeps a transaction or snapshot;
- timestamp text;
- identity ids after a copy.

## Migration

Cutover runbook: [POSTGRES_CUTOVER.md](POSTGRES_CUTOVER.md) (`scripts/pg_migrate.py`, `deploy/pg/`).
