# PostgreSQL latency diagnosis — 2026-10-06

This records read-only observations from the earlier 600-second capacity run, before PostgreSQL tuning. Workload context supplied by the parent task: 1,000 users, approximately 200 command requests/second, `feed_like` commands, and 10% of users with approximately 4.7 MB saves. The application already had the reusable command worker pool, delta-encoder ownership fix, two-second HTTP idle timeout, and explicit closure of command responses.

All database sample timestamps below are **UTC on 2026-10-05**, corresponding to the morning of October 6 in Asia/Bangkok. Queries inspected PostgreSQL statistics/activity, schema metadata, and container counters; no settings or application files were changed during diagnosis.

## Finding

**A sampled latency spike spent approximately 0.56–0.60 seconds inside COMMIT waiting for WAL writing.** This is direct evidence that WAL flush contention contributes to the tail. It does not establish that every slow request has the same cause, or identify the underlying storage component responsible for each stall.

Earlier snapshots often showed application backends waiting for the client between statements. Later samples captured simultaneous COMMIT waiters and a WAL synchronization waiter. Those later samples distinguish at least one concrete database commit stall from Python computation or request admission time.

## Exact wait evidence

At **23:32:34.607 UTC**, one backend was executing COMMIT with wait `IO / WALSync`; seven other sampled backends executing COMMIT were waiting on `LWLock / WALWrite`:

| Backend PID | Wait | Transaction age, ms |
| --- | --- | ---: |
| 599 | LWLock / WALWrite | 402 |
| 375 | IO / WALSync | 295 |
| 549 | LWLock / WALWrite | 280 |
| 555 | LWLock / WALWrite | 280 |
| 429 | LWLock / WALWrite | 276 |
| 559 | LWLock / WALWrite | 266 |
| 608 | LWLock / WALWrite | 264 |
| 597 | LWLock / WALWrite | 239 |

**These are transaction ages, not isolated fsync durations.** This sample established a simultaneous flush backlog, but could not alone attribute all elapsed transaction time to COMMIT.

A subsequent sample included both `query_start` and `xact_start`. Every row in the following table was executing **COMMIT**, with wait **LWLock / WALWrite**, at both sample times:

| PID | COMMIT age at 23:33:10.586, ms | Transaction age, ms | COMMIT age at 23:33:10.924, ms | Transaction age, ms |
| --- | ---: | ---: | ---: | ---: |
| 677 | 266 | 270 | 603 | 607 |
| 372 | 260 | 263 | 597 | 601 |
| 349 | 260 | 263 | 597 | 601 |
| 413 | 246 | 250 | 583 | 588 |
| 745 | 239 | 243 | 576 | 581 |
| 600 | 237 | 242 | 574 | 579 |
| 748 | 235 | 239 | 572 | 577 |
| 586 | 235 | 256 | 572 | 594 |
| 591 | 223 | 228 | 560 | 566 |
| 585 | 221 | 225 | 559 | 562 |

The same PIDs and statements remained present approximately 338 ms later. At the second sample, only approximately 3–22 ms of each transaction preceded COMMIT. The COMMIT statement ages therefore account for nearly all of these transactions' elapsed time. Sampling cannot prove that each backend spent every intervening instant in the identical wait event.

The query was limited to the ten oldest qualifying active client backends. It did **not** capture every backend or necessarily the backend performing the synchronization at that instant.

The second sampling query was equivalent to:

```sql
SELECT clock_timestamp()::time(3), pid,
       coalesce(wait_event_type, 'CPU'), coalesce(wait_event, 'CPU'),
       round(extract(epoch FROM (clock_timestamp() - query_start)) * 1000) AS statement_ms,
       round(extract(epoch FROM (clock_timestamp() - xact_start)) * 1000) AS tx_ms,
       left(query, 85)
FROM pg_stat_activity
WHERE datname = current_database()
  AND backend_type = 'client backend'
  AND pid <> pg_backend_pid()
  AND state = 'active'
  AND (clock_timestamp() - query_start > interval '40 milliseconds'
       OR wait_event_type IN ('IO', 'Lock', 'LWLock'))
ORDER BY query_start
LIMIT 10;
```

The `CPU` label above was only a display fallback for a NULL wait event; it does not prove continuous CPU execution.

## Observed baseline configuration

| Setting / resource | Observed value |
| --- | --- |
| PostgreSQL | 16.15, Alpine / Linux x86-64 |
| PostgreSQL container limit | 2 CPUs; 1,610,612,736 bytes RAM (1.5 GiB) |
| `shared_buffers` | 256 MiB |
| `wal_buffers` | 8 MiB |
| `max_wal_size` / `min_wal_size` | 1,024 MiB / 80 MiB |
| `checkpoint_timeout` | 300 seconds |
| `checkpoint_completion_target` | 0.9 |
| `wal_compression` | off |
| `fsync` / `synchronous_commit` / `full_page_writes` | on / on / on |
| `wal_sync_method` | fdatasync |
| `track_io_timing` / `track_wal_io_timing` | off / off |
| `autovacuum_max_workers` | 3 |
| `autovacuum_vacuum_cost_delay` | 2 ms |
| `autovacuum_vacuum_cost_limit` | -1 (uses the configured vacuum cost limit) |
| `bgwriter_delay` / `bgwriter_lru_maxpages` / `bgwriter_lru_multiplier` | 200 ms / 100 / 2 |
| Global `default_toast_compression` | pglz |
| Actual `sessions.state` column compression | **LZ4**, `attcompression = 'l'` |
| Installed extensions | plpgsql only; no pg_stat_statements |
| PostgreSQL data mount | Docker volume at `/var/lib/postgresql/data`; not a Windows-directory bind mount |

The PostgreSQL build supports LZ4. Global TOAST defaults must not be mistaken for the save column's actual compression policy: schema tuning already sets that column to LZ4.

## Statistics supporting write-pressure investigation

The following counters came from separate snapshots during the same run; the exact timestamps of these counter reads were not printed. They are cumulative since the statistics reset, **2026-10-05 23:22:37.716917 UTC**, and include fixture preparation and background activity. They are not isolated workload deltas.

| Counter | Earlier snapshot | Later snapshot |
| --- | ---: | ---: |
| WAL bytes | 2,617,427,759 | 3,651,375,122 |
| WAL full-page images | 181,667 | 298,660 |
| WAL synchronizations | 54,927 | 76,641 |
| `wal_buffers_full` | 0 | 0 |
| Requested checkpoints | 5 | 7 |
| Timed checkpoints | 0 | 0 |
| Checkpointer buffers written | 45,522 | 55,230 |
| Background-writer buffers written | 110,103 | 162,970 |
| Background-writer max-write-limit events | 1,073 | 1,588 |
| Backend buffers written | 548,389 | 787,242 |

Other snapshots:

- At 23:29:21 UTC, `pg_stat_io` reported approximately 320,000 autovacuum writes in its vacuum context versus approximately 48,000 checkpointer writes. I/O timing columns were zero because timing collection was disabled; zero does not mean free I/O.
- The database later occupied approximately 738 MB; `sessions` including TOAST and indexes occupied approximately 660 MB. `work_visit_places` was 33 MB and `receipts` 29 MB. The main statistics tables were each below 1 MB.
- One snapshot reported 66,500 session updates and **zero HOT updates**. The `stat_sessions_seen` index includes `(updated_at, revision, sid)`; each command changes indexed fields. By contrast, `stat_play` had 64,500 updates, of which 64,441 were HOT.
- The session TOAST relation was observed at different sizes as writes and vacuum progressed. This is consistent with substantial turnover; it does not by itself prove harmful bloat or a vacuum lock stall.
- PostgreSQL cgroup I/O pressure reported `full avg10=3.51`, `avg60=3.46`, `avg300=2.92` percent, with approximately 15.84 GB of block-device writes recorded. These are cumulative/container-level observations, not per-request latency measurements.
- CPU quota throttling was small in the sampled counters: approximately 0.69 seconds for the API container and 2.09 seconds for PostgreSQL over roughly 500 seconds of container operation. This weakens the CPU-quota-throttling hypothesis, but does not rule out Python GIL pauses, garbage collection, or ordinary CPU scheduling delays.

## Application and schema review

- `game/storage.py`, `Store._store`: every committed command replaces the serialized `sessions.state`, increments revision and updates `updated_at`, then inserts a receipt within the transaction. A small feed-like change still rewrites the large serialized save.
- The `[slow-write]` timer includes rentals and work-visit hooks, Python projection work, multiple SQL round trips, the save update, receipt insertion, and COMMIT. It is **not** an isolated disk-write or fsync measurement.
- `game/work_visits.py`, `sync`: commands read account/person metadata and existing workplace projections; the fixture had 41,000 workplace rows. Unchanged projections are not rewritten, but reads and projection computation still occur. This is a possible independent optimization area, not evidence that it caused the captured COMMIT stall.
- `game/pg_schema.py`: the active-player and play-time triggers use per-player keys, `(day, sid)`. They do not update one global counter row on every command.
- `game/kpi.py` buffers global counters and flushes batches. `command_metrics.py` writes per-process local snapshots, not per-command PostgreSQL counter rows.
- No shared-row lock blocker was captured by the activity/lock snapshots. `VacuumDelay` was observed. A previously reported `VacuumTruncate` observation alone is insufficient to blame vacuum truncation for the latency spikes.

## Durability-preserving next comparisons

1. **Test `wal_compression=lz4`.** The baseline has many full-page images and WAL compression disabled. This can reduce WAL volume while preserving crash recovery, at some CPU cost. It is separate from save-column TOAST compression, which is already LZ4. [PostgreSQL 16 WAL configuration](https://www.postgresql.org/docs/16/runtime-config-wal.html#GUC-WAL-COMPRESSION)
2. **Test `max_wal_size=4GB`.** The baseline has repeated requested checkpoints and no timed checkpoints. More WAL headroom can reduce checkpoint frequency and repeated full-page images, with more disk use and potentially longer crash recovery. Keep `fsync`, `synchronous_commit`, and `full_page_writes` enabled. [PostgreSQL 16 checkpoint configuration](https://www.postgresql.org/docs/16/runtime-config-wal.html#GUC-MAX-WAL-SIZE)
3. If pressure persists, compare **384–512 MiB shared buffers** within the existing 1.5 GiB database memory limit. The present evidence does not justify assigning 1 GiB blindly or increasing WAL buffers: `wal_buffers_full` remained zero. [PostgreSQL 16 memory configuration](https://www.postgresql.org/docs/16/runtime-config-resource.html#GUC-SHARED-BUFFERS)
4. Collect I/O and WAL synchronization timing in the next run. The baseline timing flags were off, so there is no isolated cumulative fsync-time measurement to compare retrospectively. [PostgreSQL 16 statistics configuration](https://www.postgresql.org/docs/16/runtime-config-statistics.html)

The parent task subsequently started `tuned-soak-200`: the same application image, quotas and data, with **WAL compression LZ4**, **maximum WAL size 4 GiB**, and **I/O timing enabled for observability**. Shared buffers remain 256 MiB and durability settings remain enabled. That run's results are not included here; no further database commands or load were performed to prepare this document.

## Limits of the conclusion

The captured COMMIT ages prove that database WAL waiting explains specific sampled hundreds-of-milliseconds stalls. They do not establish the proportion of the complete run's p95 attributable to WAL, identify physical-disk versus host/VM/Docker effects, or isolate checkpoint pressure from other I/O. The Docker-volume mount excludes a direct Windows-directory bind mount, but does not exclude host or virtualization storage latency. Correlating the next run's request tails, WAL timings and checkpoint events is needed to assess the configuration changes.
