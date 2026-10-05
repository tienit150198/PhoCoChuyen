# PostgreSQL

PostgreSQL is the only supported database. Install `requirements.txt` before starting the game; `DATABASE_URL` is required for game, live and operational tools. See [POSTGRES_ONLY.md](POSTGRES_ONLY.md) for local, Docker and test setup.

## Connection settings

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | required | PostgreSQL URL (`postgresql://` or `postgres://`). Missing or malformed values stop startup. Keep passwords in the environment file (mode 600) or `~/.pgpass`; URL-encode special characters. The server never prints the URL. |
| `PG_POOL` | 6 | Idle connections kept indefinitely per worker process. Connections above it (up to `PG_POOL_MAX`) are kept too, and closed once unused for `PG_POOL_IDLE_MS`. |
| `PG_POOL_IDLE_MS` | 10000 | How long a connection above `PG_POOL` stays open unused (a reaper thread closes it). Before 0.9.5 those were closed as soon as they came back, so every burst above `PG_POOL` requests opened new backends (a fork and an authentication on the database server each). |
| `PG_POOL_LOG_S` | 60 | Every this many seconds, a worker that opened connections or waited for a free one logs a `[pg-pool]` line (opened, closed, checkouts, waited, timed out; open, idle). A steady stream of `opened` means churn; `waited` means the pool is too small for the load. 0 = off. |
| `PG_POOL_MAX` | 12 | Most connections one worker opens at once. With `WORKERS=4` that is 48 at most, under the `max_connections = 60` of `deploy/pg/install_pg16.sh` minus the reserved and tool connections. Keep `WORKERS` x `PG_POOL_MAX` under the server's `max_connections`, minus the connections that tools need. A request waits up to `PG_POOL_WAIT_MS` (10000) for a free connection. |
| `PG_POOL_CHECK_MS` | 5000 | An idle connection older than this is checked (`SELECT 1`) before use. After a PostgreSQL restart, a dead connection is also replaced when its first statement fails, and that statement is retried once. There is never a retry after a statement has succeeded, so a write is never repeated. |
| `PG_STATEMENT_TIMEOUT_MS` | 10000 | `statement_timeout` of every connection. Admin statistics raise it for their one heavy query (`ADMIN_STATS_TIMEOUT`, default `120s`). |
| `PG_LOCK_TIMEOUT_MS` | 5000 | `lock_timeout` of every connection. A player command's save write waits longer for its row lock: 12 s, the command write timeout (`BUSY_MS`). Its statement timeout is raised to match, so a burst of commands on one save queues instead of failing. |
| `PG_IDLE_TX_TIMEOUT_MS` | 30000 | `idle_in_transaction_session_timeout`. |
| `PG_SYNCHRONOUS_COMMIT` | server default (`on`) | Optional: `off` stops each commit from waiting for its WAL flush. A crash of PostgreSQL or of the machine can then lose the last ~0.6 s of commits, but never corrupts data. Use it only if the disk is the bottleneck. |
| `TEST_DATABASE_URL` | unset | **Tests only.** With no `DATABASE_URL`, it runs the test suite on PostgreSQL. Each temporary namespace gets its own schema `t_<run>_<hash>`, dropped afterwards. Never set it on a server. |


The synchronous game pool lives in `game/db.py`; the asynchronous live pool lives in `live/db.py`. No separate `psycopg_pool` package is used.

## Transactions and schema

Commands lock the affected save row with `SELECT ... FOR UPDATE`, then check revision and write the state, archive and receipt atomically. Different players can write concurrently; compute and JSON validation run outside the row lock until the contention fallback is needed.

Connections open lazily in each worker after `fork()`. A data change opens a transaction; `commit()`, `rollback()` or leaving `with store.connect() as db:` closes it. A SELECT outside a transaction fetches its rows immediately and leaves no transaction behind. A connection returns to the pool only when libpq reports it idle; otherwise it is rolled back or closed. Tests inspect `pg_stat_activity` for this guarantee.

The PostgreSQL schema is defined in `game/pg_schema.py`. Text uses `COLLATE "C"`, timestamps remain UTC text (`YYYY-MM-DD HH:MM:SS`), saves use compressed text, and generated IDs use identity columns. Versioned schema changes install at startup when required. Shared worker rate limits use the `hits` table with per-key advisory locks.

Queries use native PostgreSQL SQL: conflict handling uses `ON CONFLICT`, transactions use `BEGIN`, and timestamp offsets use PostgreSQL intervals. The connection adapter binds `?` placeholders and formats standard `CURRENT_TIMESTAMP` as UTC text to match the schema; it does not translate another database dialect.

Housekeeping prunes receipts by `created_at` and guests by `sid`. PostgreSQL manages its own WAL/checkpoints. Game logs include `[slow-cmd]`, `[slow-lock]`, `[slow-write]` and `[pg-pool]`; these do not contain the connection URL or player saves.

## Tests and recovery

Set `TEST_DATABASE_URL` to a disposable PostgreSQL database and unset `DATABASE_URL`. Every temporary namespace gets a separate schema; child servers inherit the test-run identifier. Run `python scripts/run_checks.py`.

Recovery uses PostgreSQL backups (`pg_dump` / `pg_restore`) and a compatible application release. Removing `DATABASE_URL` stops the application. The old cutover report is retained as historical context; its retired migration and file-database rollback tools are no longer shipped.
