# Chat History and PostgreSQL-only Implementation Plan

> **For agentic workers:** Use the dispatching-parallel-agents workflow for the separate ownership areas below. Run PostgreSQL checks against an isolated local instance and review the integrated diff before completion.

**Goal:** Keep private chat history consistent with its inbox preview and remove SQLite support from the current application, configuration and test workflows.

**Architecture:** Chat buffers live messages while history loads, invalidates stale cached pages and requests a complete latest page after reconnect. PostgreSQL becomes the required storage backend; the existing SQL adapter, save revisions, pool and namespace-based test schemas remain compatible with their callers. Stored player data is outside this source-code change.

**Tech Stack:** Python, psycopg, PostgreSQL, WebSockets, browser JavaScript and Node regression tests.

## 1. Chat history — parent ownership

Files: `public/js/v4/chat.js`, `tests/chat_history.mjs`.

- [x] Reproduce delivery during initial history loading, stale inbox previews and interrupted requests: `node --test tests/chat_history.mjs` fails six cases before the fix.
- [x] Buffer messages for an existing thread regardless of its `loaded` state:

```js
if(t&&!t.msgs.some(m=>m.id===f.id)){t.msgs.push(f);t.msgs.sort((a,b)=>a.id-b.id);}
```

- [x] On a new welcome, clear private thread cache and request the latest page for the active thread. Stop sending a capped resume cursor because it can leave a gap between old cached messages and the newest page.
- [x] Before reopening a cached thread, compare `live.chan(ch)?.last?.id` with `lastId(t.msgs)` and invalidate a stale page before marking it read.
- [x] Run `node --test tests/chat_history.mjs`; expected: every scenario passes, including duplicate delivery and older-page merging.
- [x] Verify in a real browser that a message arriving during history loading remains visible, and an updated inbox preview leads to matching thread content after reconnect.

## 2. Required PostgreSQL core — postgres_core ownership

Files: `game/db.py`, `game/storage.py`, `live/db.py`, `server.py`, core backend tests, `tests/pg_support.py`, `tests/__init__.py`.

- [x] Add and run regressions for missing/invalid database configuration before changing runtime behavior.
- [x] Require a PostgreSQL URL and psycopg; remove SQLite connections, pools, schema creation, checkpoints and file-backed shared limits. Preserve the game SQL adapter and atomic PostgreSQL transactions.
- [x] Preserve `Store(path)` as a namespace for locks/test schema names; it must never create a database file.
- [x] Run core storage/configuration/pool/concurrency tests with `TEST_DATABASE_URL`; expected: passing behavior on PostgreSQL and clear refusal without configuration.

## 3. Remaining runtime — postgres_runtime ownership

Files: remaining active `game/*.py` and `live/*.py`, excluding core ownership.

- [x] Inventory backend branches and SQLite dependencies before edits.
- [x] Keep each existing PostgreSQL query and remove the unsupported backend branch and obsolete SQLite schemas/migration helpers.
- [x] Keep admin directory name matching, chat authorization and all current save/runtime behaviors intact.
- [x] Run account/admin/chat/statistics checks on the isolated PostgreSQL instance; expected: unchanged PostgreSQL behavior.

## 4. Tooling and tests — postgres_tooling ownership

Files: current startup/deploy scripts, README, environment example, Docker/Compose, requirements, remaining tests.

- [x] Make setup instructions require PostgreSQL and install psycopg.
- [x] Convert useful direct SQLite fixtures to isolated PostgreSQL fixtures; remove tests/tools that only exercise the deleted backend.
- [x] Add an active-runtime guard against importing or opening SQLite; it must fail on the original source and pass after integration.
- [x] Run the integrated Python suite against isolated PostgreSQL, Node chat/admin regressions, JavaScript checks and syntax checks; preserve the full-scan result and rerun affected cases after fixes.

## 5. Integrated review

- [x] Check ownership diffs and preserve unrelated work already present in this checkout.
- [x] Confirm there are no active SQLite fallback paths or SQLite dependency imports.
- [x] Confirm missing configuration fails rather than silently opening a file.
- [x] Record fresh verification results, stop the disposable PostgreSQL service and report deployment status accurately.

## 6. Native PostgreSQL SQL and lifecycle follow-up

- [x] Replace active INSERT OR IGNORE and BEGIN IMMEDIATE queries with PostgreSQL ON CONFLICT and BEGIN.
- [x] Replace SQLite datetime cutoffs with native UTC interval expressions.
- [x] Remove the old SQL rewrites and reject SQLite-only syntax before starting a transaction.
- [x] Remove obsolete migration catalog metadata; inspect the PostgreSQL catalog in schema fixtures.
- [x] Verify listener cancellation completes before closing PostgreSQL sockets; reproduce the old shutdown ordering failure and pass a real socket check after fixing it.
- [x] Preserve existing deployment auxiliary-file locations through GAME_NAMESPACE/VAPID_KEY_FILE upgrade instructions.
- [x] Verify shared-fund writes with PostgreSQL row locks and concurrent cap checks: both cap races fail before the row lock and pass after it; seven native conflict/concurrency regressions plus the existing joint-spend check pass.
- [x] Remove SQLite labels and backend display branches from both admin statistics interfaces; keep the existing Python sampling fallback label accurate.
- [x] Run the final frozen PostgreSQL source through the full Python scan and record actual results below; fixture and runner repairs are verified separately.

Fresh checks completed before final sweep: Node admin/chat 11 scenarios; browser chat at 390x844 and 1280x900 with no JavaScript errors; 509 browser module syntax checks; PostgreSQL admin/chat/catalog/shutdown integration 39 tests. The first full sweep was incomplete due to Windows async listener teardown, which now has a regression test and a fix.

Final bounded review found no additional fund-lock or shutdown defect. The three updated admin modules pass syntax checks; the 11 Node chat/admin regressions pass again. Python compileall and the integrated diff whitespace check pass.

The Python 3.12.12 / PostgreSQL 17 full scan ran 5,640 tests in 2,426 seconds: 5,621 passed, 11 skipped, 5 failures and 3 errors. The unmodified scan report is preserved as `output/postgresql-full-scan-report.json`, with its complete test log alongside it. This scan is **not** recorded as a fully passing run.

The Windows multiprocessing runner lacked a main guard, causing spawned workers to execute the suite again; guarded startup and a child-import regression now fix that. The affected real PostgreSQL multiprocessing test and five tooling checks passed through the corrected runner (6 tests, 1.761 seconds).

The journey payload-size failure reproduces unchanged on the original HEAD `5a9b10e`: 10,865 characters against the old 8,650-character cap. Baseline source was exported to a separate output folder and the same test failed there in 0.139 seconds. It is outside the chat/PostgreSQL change; the test cap and product payload remain unchanged.

The seven remaining failures/errors were repaired in the test runner and fixtures: required PostgreSQL configuration, dependency paths for isolated compatibility workers, Python JSON recursion expectations, and exact socket-event synchronization. The affected seven cases plus five tooling regressions passed together through the corrected runner: **12 passed, zero skipped, 16.842 seconds** (`output/postgresql-affected-final-report.json`). Separately, socket repeats passed 9/9 and their neighboring suite passed 7/7; tooling verified 24 focused cases including the real old-release compatibility check. No product runtime changes were needed for these fixture repairs.

Final read-only review found no additional issue or weakened assertion in these repairs. Python compileall and integrated diff checks pass after all edits. The temporary PostgreSQL cluster at localhost:58239 was stopped successfully with its exact owned data directory. All changes remain local and uncommitted; no deployment was performed. The original full scan retains the baseline payload-size failure and eleven platform/old-release skips, so it must not be advertised as entirely passing.
