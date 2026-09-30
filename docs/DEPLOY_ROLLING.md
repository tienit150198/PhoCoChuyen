# Rolling release: deploys without a restart gap

Until 0.9.4 a release ran `systemctl restart mot-ngay-lam-nghe`. For the ~2–4 s the service took to come
back, nginx answered **502** to everything. At ~1,300 commands a minute that is ~200 clicks, each of which
became an error toast. Since 0.9.5 there are two layers of protection:

1. **The client rides out a restart** (`public/js/api.js`). Reads (GET) and commands that get 502/503/504 or no
   answer at all are sent again, **byte for byte**, after 0.3, 0.6, 1, 1.5, 2, 2… s, within at most 14 s. A
   command keeps its `request_id` and `expected_revision`, so one that already landed is replayed from its
   receipt and is never applied twice. The command queue waits meanwhile, so commands keep their order. After
   400 ms a small "Đang cập nhật máy chủ…" note shows ("Updating the server…" in English) instead of an
   error toast. 4xx answers, 500, and other writes (posts, account, AI) are never re-sent. This also
   covers a plain restart, a worker crash, and a PostgreSQL blip (503 `db_unavailable`).
2. **The deploy has no gap** (`deploy/rolling_release.sh`, this document). nginx only ever sends
   requests to a server that is up.

## Design

```
            before            step 1            step 2              step 3               step 4 / after
nginx  ->  :8765 (old)       :8765 (old)       :8766 (bridge,new)  :8766 (bridge,new)   :8765 (new)
units      canonical=old     + bridge=new      old drains          canonical restarts   bridge drains, stops
                             (health checked)  (graceful reload)   on new (no traffic)  (graceful reload)
```

* **Canonical unit**: `mot-ngay-lam-nghe.service` on 127.0.0.1:8765, `WorkingDirectory=/opt/mot-ngay-lam-nghe/current`.
  It is not changed. Between releases the layout is exactly as before, so `mnl-selfheal`, the `deploy/pg/*`
  scripts, `journalctl -u mot-ngay-lam-nghe` and the plain restart release scripts all keep working.
* **Bridge unit**: `mot-ngay-lam-nghe-bridge.service`, generated for each run in `/run/systemd/system/`
  (it is gone after a reboot). It is the output of `systemctl cat mot-ngay-lam-nghe` (the unit plus every
  drop-in: `50-postgres.conf`, `workers.conf`, `assets.conf`, `keepdata.conf`), so it has the same
  `User`, `EnvironmentFile`s, sandbox and `ReadWritePaths`. It gets its **own cgroup** with the same
  `MemoryMax` (set `BRIDGE_MEMORY_MAX=2G` to lower it), and these overrides:
  * `WorkingDirectory=<new release>`;
  * `ExecStart=/usr/bin/env PG_POOL=2 PG_POOL_MAX=6 PG_APPLICATION_NAME=mot-ngay-lam-nghe-bridge <the unit's ExecStart> --port 8766`.
    `env` runs after systemd has set the environment, so these values beat `EnvironmentFile=` and
    `Environment=`. The last `--port` wins in argparse.
* **Switch**: the script edits only the `127.0.0.1:<port>` addresses of `/etc/nginx/sites-enabled/phocochuyen`
  (the real file behind the symlink). It saves a copy first (`/root/nginx-rolling/`), runs `nginx -t` (and
  restores the copy if the test fails), then `systemctl reload nginx`. A reload is graceful: old nginx
  workers finish their in-flight requests on the old port, and new requests go to the new port.
  No other nginx file is read or written. Before starting, the script aborts if any other enabled site
  (`nginx -T`) uses port 8766. dk_bike (`api/cms.dkbike.vn`) is never touched.
* **Drain**: the script waits until the old port has had no established connection for 2 s
  (`ss state established sport = :port`), for at most `DRAIN_MAX=75` s (`proxy_read_timeout` is 60 s).
  Anything still running after that is cut, and its client re-sends it.
* **Old nginx workers**: a graceful reload leaves the previous nginx workers running until their clients
  are done, and an HTTP/2 client can keep one alive for a while, still pointed at the old port. Before the
  canonical unit restarts, and before the bridge stops, the script waits until no "worker process is
  shutting down" is left (`OLD_NGINX_MAX`, 90 s). Without it, one long-lived client got 502s for ~40 s
  after the bridge stopped (0.9.6 release, 30/09).
* **Why flip back instead of an A/B pair of units**: an `@8765`/`@8766` template pair would save one switch,
  but every ops script, the self-heal watchdog and `journalctl -u` would then need to know which unit is
  live. It would also have to survive reboots with the right one enabled. Flipping back costs about 3 more
  seconds of script time and keeps a single, well-known live unit.

A release takes about 6 s of script time (bridge start ~2 s, two drains of ~2 s each, canonical restart ~2 s).

### Two versions at once, one database
For a few seconds both releases serve the same PostgreSQL database:
* Row locks and receipts keep this safe: a save is changed by one transaction at a time, and a request id
  is applied once, whichever server gets it.
* After the switch the old server only finishes requests already in flight, so a player's later commands
  all reach the new server. A save written by the new code can still carry keys the old code would reject
  in `validate_state`. That matters for a **rollback** (below), not during the switch. Keep `LAZY_SAVES=0`
  until no older release will ever be rolled back to.
* **Single-instance jobs.** Housekeeping (receipt, guest and save pruning, push delivery, rate-limit
  pruning, the leaderboard backfill) now runs only in the server that holds the flock of
  `<GAME_DB>-maintenance.lock` next to the game database (`server.py maintenance_lock`). A second server
  logs `[maintenance] another server on this database runs housekeeping: waiting for it to stop` and
  takes over within 10 s of the first one exiting. The admin statistics job already had its own lock
  file (`<GAME_DB>-adminstats.lock`). Rate limits live in PostgreSQL (`hits`), so they are shared. The
  SQLite checkpointer is safe to run twice (and does nothing on PostgreSQL). Release 0.9.4 does not
  have the housekeeping lock yet: during the one switch from 0.9.4 to 0.9.5, and during a rollback to
  0.9.4, both servers may run a prune/push pass at the same moment. Those passes are idempotent deletes;
  the worst case is one web push sent twice.
* **PostgreSQL connections**: canonical unit 4 workers × `PG_POOL_MAX` 12 = 48, bridge 4 × 6 = 24. The
  theoretical sum of 72 is above `max_connections = 60`. In practice the server being drained holds
  only idle connections (≤ 6 per worker once unused for `PG_POOL_IDLE_MS`, 10 s), and real load uses 19–24 connections in total (see PG_E2E).
  A request that finds its pool full waits up to `PG_POOL_WAIT_MS` (10 s) rather than failing. For a
  hard guarantee, run with `BRIDGE_PG_POOL_MAX=3`.
* **Memory**: for a few seconds 2 × 4 workers run. Each is ~70–200 MB at normal load, far from the 3 GB
  `MemoryMax` of either cgroup.
* **Static files**: the bridge writes the new release's hashed files into `shared/_v` (STATIC_CAS_DIR)
  **before** it answers `/api/health`, so a page from the new release never asks for a missing `?v=`.
  Nothing ever deletes old hashed files, so pages of the old release that are still open keep working.
  `current` is flipped at the first nginx switch, so un-versioned static files come from the new
  release as soon as the new server does.

## One-time setup (production)

Nothing changes in the unit, the drop-ins or the nginx config. Only install the script. Run as root, inside tmux:

```bash
# 1. the script, from the release zip (after uploading it to /tmp/mnl-release.zip)
python3 -c "import zipfile;print(zipfile.ZipFile('/tmp/mnl-release.zip').read('mot-ngay-lam-nghe/deploy/rolling_release.sh').decode(),end='')" > /usr/local/sbin/mnl-rolling-release
chmod 755 /usr/local/sbin/mnl-rolling-release
# 2. what it will edit: every line printed must be the game's (upstream "server 127.0.0.1:8765 max_fails=0;")
grep -n '127\.0\.0\.1:87' "$(readlink -f /etc/nginx/sites-enabled/phocochuyen)"
# 3. preconditions only (unit active and healthy, nginx -t OK, 8766 free, no other site on 8766)
mnl-rolling-release --check
```

## Every release

**Required before building the zip: the task compatibility gate.** Saves keep every generated task, and each
command regenerates the task's original with the new code and compares its facts. If generation changed, every
player with an open task of that kind is blocked on "Dữ kiện gốc của nhiệm vụ không hợp lệ" (0.9.6: clothing
lines gained `ask`/`told`). Run it with the live release as OLD, on the dev machine:

```bash
git worktree add /tmp/live <live branch or tag>        # or: mkdir /tmp/live && git archive <live> | tar -x -C /tmp/live
python3 scripts/check_task_compat.py /tmp/live .       # must print "OK" and exit 0
git worktree remove /tmp/live
```

It compares `make_task` for every career, day 1..40, slot 0..11, desk and classic, plus the legacy tour trips and the
situation script ids. A failure lists each differing field. Fix it by keeping generation identical (change what the
screen shows instead), or, for a display-only key, add it to `engine.LATE_TASK_KEYS` inside a field the validators
already compare with that tolerance. `tests/test_task_compat.py` runs the same gate against `LIVE_REF` (update it
to the new live commit after each release).

```bash
tmux new -s release            # or: tmux attach -t release
# (same pre-steps as before if the release needs them: env additions, the MNL_DEV guard…)
mnl-rolling-release /tmp/mnl-release.zip
# optional: SMOKE_URL=https://phocochuyen.io.vn/api/health mnl-rolling-release /tmp/mnl-release.zip
```

The output ends with `done: <version> is live, no restart gap (rollback: … --to <previous release>)`. It is also
appended to `/var/log/mnl-rolling-release.log`. It keeps the 3 newest releases and never deletes the live one
or the previous one.

The plain `release_09x.sh` (restart) still works. It is the fallback when the service is **not** running, which
the rolling script refuses.

## Rollback

```bash
mnl-rolling-release --to /opt/mot-ngay-lam-nghe/releases/<previous dir>    # printed at the end of each run
```

This is the same zero-gap switch, onto a directory that is already unpacked. Saves written by the newer release
must still pass the older release's checks (see "Two versions at once"). This holds whenever the newer
release only added optional fields that the older one ignores. Check the release notes before rolling back
across a save-format change.

## If it stops half-way

The script prints where the players are. A failure, Ctrl-C or `kill` runs the exit handler:

| Stopped at | Players are on | What the script already did | What to run |
|---|---|---|---|
| 1 (bridge does not become healthy) | old release, :8765 | bridge stopped and removed; `current` unchanged | fix the release; nothing else |
| 2 (nginx switch fails `nginx -t`) | old release, :8765 | site file restored, not reloaded; bridge stopped | fix nginx |
| 2–3 (killed while draining, canonical restart fails) | **bridge** (new), :8766 | nothing | once `mot-ngay-lam-nghe` answers on :8765: `mnl-rolling-release --recover` |
| 4 (killed while the bridge drains) | new release, :8765 | bridge stopped | nothing (`--recover` is harmless) |

`--recover` is idempotent. If nginx points at the bridge, it waits for :8765 to be healthy, switches nginx back,
drains, and then stops and removes the bridge unit. It never changes `current`. If the canonical unit cannot
start on the new release while players are on the bridge:

```bash
ln -sfn /opt/mot-ngay-lam-nghe/releases/<previous dir> /opt/mot-ngay-lam-nghe/current
systemctl restart mot-ngay-lam-nghe      # the old release, still no traffic on it
mnl-rolling-release --recover            # players move to it
```

A normal run refuses to start while nginx points at 8766 or the bridge is active (`--check` shows why).
**Do not reboot while players are on the bridge.** The bridge unit lives in `/run` and is gone after a
reboot, while nginx would still point at 8766. Run `--recover` first. If it does happen, edit the site
back to 8765 by hand (`sed -i 's/127.0.0.1:8766/127.0.0.1:8765/' …`, `nginx -t`, reload).

## Rehearsal (2026-09-30)

The rehearsal ran in a Docker Ubuntu 24.04 container with systemd as PID 1, nginx 1.24 and PostgreSQL 16. The
unit and drop-ins were copies of production's (WORKERS=4, PG_POOL 6/12, STATIC_CAS_DIR, MemoryMax=3G). The
nginx site used the same upstream line and locations, next to a dk_bike stand-in site. The load generator ran
30 players through nginx, about 1,350 commands/min plus state, page and leaderboard reads, **with no client
retries**. At the end it compared every save's server revision with the last revision its player saw.

| Run | Requests | Non-2xx / dropped | Revision mismatches |
|---|---|---|---|
| Plain `systemctl restart` (today's method), 1.7 s | 1,268 | **33 × 502** | 0 |
| Rolling: 0.9.4 → 0.9.5, rollback `--to` 0.9.4, → 0.9.6 (260 s) | 7,868 | **0** | 0 |
| Broken release (bridge never healthy), SIGKILL of the script with players on the bridge, `--check` refusal, `--recover` (150 s) | 4,568 | **0** | 0 |
| Final script (installed as `/usr/local/sbin/mnl-rolling-release`), one release (90 s) | 2,768 | **0** | 0 |

In all runs the dk_bike site file, `nginx.conf` and `conf.d/*` were byte for byte unchanged (md5), and
`/run/systemd/system` held no leftover bridge unit. During the switch there were at most 18 PostgreSQL
connections, and the two cgroups used at most 471 MB together.

The client side was checked in a real browser (Chromium through the same nginx). The test clicked a
command every 350 ms while the service was restarted (`systemctl restart`) and then killed with
`kill -9` (systemd restarts it 3 s later).
* **0.9.4 client**: 11 of 65 clicks were lost, with the "Mất kết nối…" error toast.
* **0.9.5 client**: 57 of 57 clicks were applied exactly once (the server's revision delta equals the
  number of distinct request ids answered 200). 7 attempts got 502 and were re-sent. There was no
  error toast, and the "Đang cập nhật máy chủ…" note showed for about 5 s.


## nginx: close old workers' connections

A reload leaves old nginx workers alive for their open HTTP/2 connections. If such a worker still points at the
bridge when the release stops it, that player gets instant 502s until the connection closes (01/10: 52 errors
for one player). `worker_shutdown_timeout 20s;` in the main `nginx.conf` makes old workers close those
connections after 20 s, well inside the release's 90 s wait for old workers.
