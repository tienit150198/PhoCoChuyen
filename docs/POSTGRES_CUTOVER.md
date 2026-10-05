> Tài liệu lịch sử của bản phát hành cũ. Cấu hình và công cụ database mô tả dưới đây không còn áp dụng; cách chạy hiện tại dùng PostgreSQL duy nhất tại [POSTGRES_ONLY.md](POSTGRES_ONLY.md).

# Cutover runbook: SQLite to PostgreSQL

This runbook moves production from SQLite to PostgreSQL 16 without losing a row. The game stays up
for everything except a short downtime (about 10–25 s). The tools are `scripts/pg_migrate.py` and the scripts in
`deploy/pg/`. The schema is `game/pg_schema.py` (see [POSTGRES.md](POSTGRES.md)).

All commands run as root on the server. The scripts drop to the `mnl` user where needed. They
read the database password from `/etc/mot-ngay-lam-nghe/pg.env` and never print it.

Run them inside `tmux` (or `screen`). The scripts ignore a lost terminal (SIGHUP) and copy their
output to `/var/lib/mot-ngay-lam-nghe/pg-migration/<run>.out`, so an SSH drop never stops one
half way. Ctrl-C during the cutover or rollback downtime is a clean abort: the game goes back to
the backend it was on.

## Numbers from the rehearsal

Two rehearsals: a production twin (real systemd unit, the real game with 4 workers, a 745 MB
database, load through the real API), and a 2.09 GB synthetic database on a slow HDD with 1–4
writers. See "Rehearsal" at the end.

| Step | Game | Expected time on production (1.85 GB, slow disk) |
|---|---|---|
| `install_pg16.sh` | up | done |
| `precopy.sh` (init, copy, 2 syncs, live verify, sync) | up | about 10–20 min (the copy runs at about 7.5 MB/s) |
| `sync.sh` (as often as you like) | up | 1–10 s |
| `cutover.sh` phase A (syncs, maybe a live verify) | up | 10 s to a few min |
| `cutover.sh` phase B (stop … start) | **down** | about 10–25 s (twin: 4.3 s); under 60 s in the worst case |
| `rollback.sh` | up, then **down** | copy of the snapshot while up (a few min); down only for the reverse sync + swap + start |

## 0. Once: PostgreSQL

```bash
sudo bash deploy/pg/install_pg16.sh      # idempotent; already run on production 2026-09-30
```

## 1. The tool, before the pg-backend release is live

`pg_migrate.py` needs only python3, python3-psycopg and `game/pg_schema.py`. It does not import
the game. The `mnl` user must be able to read both files, so don't put them under `/root`:

```bash
install -d -m 755 /opt/mot-ngay-lam-nghe/pgdeploy/scripts /opt/mot-ngay-lam-nghe/pgdeploy/game
install -m 644 scripts/pg_migrate.py /opt/mot-ngay-lam-nghe/pgdeploy/scripts/
install -m 644 game/pg_schema.py     /opt/mot-ngay-lam-nghe/pgdeploy/game/
export APP=/opt/mot-ngay-lam-nghe/pgdeploy        # the deploy/pg scripts use $APP/scripts + $APP/game
```

The same thing by hand, as `mnl`:
`python3 $APP/scripts/pg_migrate.py <command> --schema-file $APP/game/pg_schema.py --sqlite /var/lib/mot-ngay-lam-nghe/game.sqlite3`
with `DATABASE_URL` in the environment.

## 2. Pre-copy (game up, off-peak)

```bash
sudo APP=/opt/mot-ngay-lam-nghe/pgdeploy bash deploy/pg/precopy.sh           # MBPS=8 by default
```

- It is safe to interrupt at any time (Ctrl-C, a lost SSH session): run it again and the copy
  resumes from the last committed chunk. `RESTART=1` throws the copy away and starts over.
- The copy reads SQLite in short chunks, each one its own short read. The WAL must stay small the
  whole time: `ls -la /var/lib/mot-ngay-lam-nghe/game.sqlite3-wal`. If the game gets slow, stop
  it with Ctrl-C and resume later with a smaller `MBPS`.
- Progress and ETA: `tail -f /var/lib/mot-ngay-lam-nghe/pg-migration/precopy-*.jsonl`.
- It ends with `verify --live`. Saves that changed during the verify count as "in flight", not as
  errors. That verify is the baseline of the fast verify at cutover.

Afterwards, you can run a sync as often as you like: `sudo APP=... bash deploy/pg/sync.sh`.
Each one only moves what changed, so each one is fast.

## 3. Deploy the pg-backend release (still on SQLite)

Deploy the release as usual. Keep `DATABASE_URL` **out of** `game.env`: the game stays on SQLite.
Check that the game works. `cutover.sh` refuses to run unless `$RELEASE/game/db.py`
(`/opt/mot-ngay-lam-nghe/current` by default) is the pg-backend code.

Build the release from a commit (`git archive`), not from a working tree that is still changing.
Then check that `time sudo systemctl restart mot-ngay-lam-nghe` stops cleanly in under 5 s: a
stop that hangs until the SIGKILL timeout adds 90 s to the downtime.

## 4. Cutover

```bash
sudo APP=/opt/mot-ngay-lam-nghe/pgdeploy bash deploy/pg/cutover.sh
```

After the release, `APP` can stay at its default, the release's own `scripts/` and `game/`.

**Phase A: game up.**
1. Preflight: every table is copied or synced, no drop-in exists yet, the service is running, and
   there is enough disk space. A periodic `mnl-pgsync.timer` is stopped, and a sync it is still
   running is allowed to finish (the tool runs only one at a time; a race would abort the cutover).
2. A live sync.
3. If there is no baseline from the last 6 h (`BASELINE=1` forces one), a `verify --live` and a
   sync that repairs what it found (up to 2 attempts).
4. Without a baseline, the script stops here, before any downtime: the fast verify would have to
   hash every save while the game is down. `ALLOW_FULL_VERIFY=1` accepts that.
5. Two more syncs, so the final one has almost nothing left to do.

**Phase B: game down.**

| # | Step | Rehearsal | On failure |
|---|---|---|---|
| 1 | `systemctl stop mot-ngay-lam-nghe` | 2–5 s | nothing has changed |
| 2 | Snapshot `pre-pg-<ts>/`: hard links to game.sqlite3 (+`-wal`) and the limits DB | < 1 s | |
| 3 | Final `sync` | see the rehearsal | **ABORT**: the game restarts on SQLite, untouched |
| 4 | `verify --fast`: counts of every table; `(sid, revision, updated_at)` of every save; sha256 of every save and every row that a sync wrote since the baseline; per-save counts of receipts/archive; the small tables in full | see the rehearsal | **ABORT**, as above. The mismatching ids are in the log. |
| 5 | `finalize`: stat triggers (no FKs, by design), schema version, sequences past `max(id)` and `sqlite_sequence` | < 2 s | **ABORT**, as above |
| 6 | `mark-cutover`: copy/sync now refuse to overwrite PostgreSQL | < 1 s | |
| 7 | Drop-in `/etc/systemd/system/mot-ngay-lam-nghe.service.d/50-postgres.conf` (`EnvironmentFile=/etc/mot-ngay-lam-nghe/pg.env`, `PG_POOL=6 PG_POOL_MAX=12`: 4 workers x 12 = 48 connections, under `max_connections` 60), then daemon-reload | < 1 s | **ABORT** (unmark-cutover first) |
| 8 | The old SQLite files (and `-wal`, `-shm`, the limits DB) become mode 000, so a game started without the drop-in fails loudly instead of serving old saves. Then start | 3–10 s | |
| 9 | Wait for `/api/health` (45 s of wall clock, `HEALTH_S=`; it gives up early when the unit fails or restarts more than twice) | | see below |

Any unexpected error between the stop and the start (an ERR trap) also aborts: the game restarts on
SQLite, untouched, and the snapshot links are removed.

If the health check fails, the game is stopped and a `verify --fast` decides:
- PostgreSQL still equals SQLite (the game never wrote there): unmark-cutover, remove the drop-in,
  restore the SQLite file modes, start on SQLite. Fix the cause and run `cutover.sh` again.
- PostgreSQL is unreachable: same, back to SQLite, but PostgreSQL stays marked. Recreate the
  database and pre-copy again (section 6, last step).
- Otherwise PostgreSQL has taken writes: `rollback.sh` runs (`AUTO_ROLLBACK=0` stops and asks instead).

**Game up again.**
- Smoke test: `GET /api/bootstrap?lite=1` creates a guest save, then `GET /api/state` reads it
  back with its cookie. The script also checks that the save count in PostgreSQL went up by one,
  which proves the game really writes to PostgreSQL. The guest save has no progress, so the guest
  prune removes it later.
- In the background, at idle IO priority, the snapshot hard links are replaced by independent copies.
  `pre-pg-<ts>/COPIED` shows up when that is done.

The script prints every step's time, plus the downtime.

## 5. After the cutover

- Look at `journalctl -u mot-ngay-lam-nghe -f` for a few minutes, and check the admin page.
- Backups: `sudo bash deploy/pg/pg_backup.sh --install` sets up a nightly `pg_dump -Fc` at 03:40
  and keeps 7, in `/var/backups/mot-ngay-lam-nghe-pg/`. Test one: `systemctl start mnl-pg-backup`.
  It skips a run (and says why) when the disk has less than twice the last dump free, and never
  leaves a partial `.part` file behind.
- cutover.sh disables the old SQLite backup timer (`systemctl disable --now`), prints its name, and
  records it in `pg-migration/sqlite-backup-timers.disabled`. It finds any timer named
  `mot-ngay-lam-nghe*backup*`, `mnl*backup*` or `phocochuyen*backup*` (not `mnl-pg-backup`);
  `SQLITE_BACKUP_TIMERS="x.timer"` names it explicitly. rollback.sh re-enables it.
  `pre-pg-<ts>/` is the last SQLite backup.
- Keep `pre-pg-<ts>/` until then too. It is the rollback base.
- The bookkeeping schema `pgmig` (progress and touched keys) is small. Keep it until you no
  longer need a rollback, then drop it: `DROP SCHEMA pgmig CASCADE`.

## 6. Rollback (keeps the progress made on PostgreSQL)

```bash
sudo bash deploy/pg/rollback.sh              # or: rollback.sh /var/lib/mot-ngay-lam-nghe/pre-pg-<ts>
```

1. While the game still runs on PostgreSQL, copy the frozen snapshot to `rollback-<ts>.sqlite3`
   (low IO priority).
2. Stop the game.
3. `pg_migrate reverse-sync` writes into that copy every row that changed in PostgreSQL since the
   cutover (inserts, updates, deletes). It never writes the snapshot or the live file.
   The SQLite stat triggers of the copy are dropped during the reverse sync and recreated after it
   (the stat tables come from PostgreSQL as they are).
4. Swap the files. The frozen files are kept as `*.pg-era-<ts>`.
5. Remove the drop-in, then daemon-reload and start.

If the reverse sync fails, or anything fails before the swap is complete, the new files are
removed and the game restarts on PostgreSQL: the drop-in is still there. `rollback.sh` refuses
to run when the game is not on PostgreSQL (no drop-in; `FORCE=1` overrides).

Trying again after a rollback: PostgreSQL is marked cut over, and its data is now stale. Recreate
the database, then start again from step 2:

```bash
sudo -u postgres dropdb phocochuyen && sudo bash deploy/pg/install_pg16.sh
```

## What the tool guarantees

- **Live SQLite:**
  - it is opened read-only (URI `mode=ro`, `query_only`);
  - every read is one statement, read to the end;
  - no snapshot is held between chunks;
  - there are no `count(*)` or `sum(length())` scans on the live file during the copy (the ETA
    comes from rowid ranges).
- **Resume and idempotency:** each chunk commits in PostgreSQL together with its checkpoint row
  (`pgmig.progress`). A table that is already copied is skipped.
- **Deletes:**
  - saves: a `(sid, revision)` diff;
  - receipts and archive: per-save counts, then a key diff of the saves that differ;
  - small tables: a key-ordered merge. A key is deleted only after it has been re-checked in the source;
  - `hits` (no key): a multiset diff, so only the rows that changed are written.
- **Verify** prints only table names, counts and (truncated) row keys, never player data. It exits
  with 1 on a mismatch. Rows that a verify finds different, while their version or count looks
  equal, are queued, and the next sync rewrites them.
- **Cutover guard:** after `mark-cutover`, `copy` and `sync` refuse to run. Only `reverse-sync` works.

## Rehearsal

**Production twin** (Ubuntu 24.04, PG 16.15, psycopg 3.1.17, the production unit, 745 MB,
1500 saves, about 10 commands/s through the real API, quiet host):

| Step | Time |
|---|---|
| precopy: copy of 607 MB at the 8 MB/s cap | 78.7 s (SQLite WAL max 2 MB) |
| sync.sh | 1.2 s |
| downtime: stop + snapshot | about 0.8 s |
| downtime: final sync | 1.1 s |
| downtime: verify --fast (7 MB re-hashed since the baseline) | 1.1 s |
| downtime: finalize + mark-cutover | 0.2 s |
| downtime: start + health | 1.1 s |
| **downtime, total** | **4.3 s** (client-visible 4.65 s, 0 lost acknowledged writes, 40/40 players intact) |
| same without a verify baseline (now refused) | 12.0 s: verify --fast re-hashed all 607 MB |
| pg_backup.sh: dump of a 425 MB database | 22.9 s (148 MB file); restore 22.6 s, 1554/1554 saves identical |

**2.09 GB synthetic database on a 7200 rpm HDD** (4200 saves, 105k receipts, 693k archive rows):

| Run | Result |
|---|---|
| 1 writer (10.6 writes/s) | whole copy in about 283 s, **7.3 MB/s**, SQLite WAL max 4.2 MB |
| 4 writers, disk saturated by other workloads | rows in 40 min (saves at 2.9 MB/s); writer "database is locked" errors at the same rate as with no copy at all, so the copy does not cause them |

Production, pre-copy started 2026-09-30 04:58: about 7.5 MB/s, game health 2–36 ms, WAL 0 MB.
