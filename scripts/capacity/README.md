# Disposable capacity benchmark

This harness creates 1,000 synthetic accounts in a disposable PostgreSQL database. It must never target production. `seed.py` checks the Docker-only database hostname/name; `load.py` accepts only the dedicated loopback ports or the test container names. The ordinary developer preview is not a target.

The workload uses real authentication, CSRF, revisions, idempotency, HTTP state deltas and WebSockets. It opens 1,000 sockets, moves players about every 300 ms, sends three shared-chat messages/s, and issues one `feed_like` per player every five seconds (200 commands/s). Each client has at most one pending command; missed scheduled slots and errors are reported, not counted as throughput. 100 users have a 4.7 MB save; 900 have a roughly 162 KB save. All 41 careers are started. This is one storage-heavy workload, not a benchmark of every career or AI provider.

## Build a reviewable source snapshot

Use an immutable Git archive into an **empty, newly created** `output/capacity-<run>/app` directory. Copy these scripts and both Dockerfiles beside `app`. Do not copy `.env`, local saves or unrelated uncommitted work. If benchmarking a local patch, copy only the explicitly reviewed changed source files over the archive and record their hashes.

From that build context:

```sh
docker build -t mnl-capacity:local -f Dockerfile .
docker build -t mnl-capacity-client:local -f Dockerfile.load .
docker network create mnl-capacity-local
docker run -d --name mnl-cap-pg --network mnl-capacity-local --cpus 2 --memory 1536m -e POSTGRES_USER=capacity -e POSTGRES_PASSWORD=local-capacity-only -e POSTGRES_DB=capacity postgres:16-alpine -c max_connections=120 -c shared_buffers=256MB
```

Wait for `docker exec mnl-cap-pg pg_isready -U capacity -d capacity`. The password above is solely for the unexposed disposable database. Pass `DATABASE_URL=postgresql://capacity:local-capacity-only@mnl-cap-pg:5432/capacity` to seed/API/live containers. Bind-mount the absolute build-context path to `/result` for all containers. Run `python /result/seed.py` once against the empty database. Set the validation boundary with:

```sh
docker exec mnl-cap-pg psql -U capacity -d capacity -c 'UPDATE sessions SET revision=40'
```

The command above uses baseline PostgreSQL WAL settings (compression off, max WAL size 1 GB). Keep `fsync`, `synchronous_commit` and `full_page_writes` enabled. Capture `pg_stat_wal`, `pg_stat_bgwriter`, cgroup `io.stat` and effective settings at the end. The separate WAL/memory/CPU tuning experiment did not improve latency and is retained only as failed diagnostic evidence, not a recommended profile.

Launch `mnl-cap-api` from `mnl-capacity:local` with `python /result/supervise.py api`: CPU quota 6, memory/swap both 6g, `WORKERS=8`, `PG_POOL=3`, `PG_POOL_MAX=8`, `MNL_DEV=1`, `ALLOWED_HOSTS=127.0.0.1,localhost`, `STATIC_CAS_DIR=/tmp/cas`, `MNL_MARKET_EPOCH=1791200000`, `MNL_MARKET_SALT=CapacityLocalOnly-6af7148d012f8bce`. If host access is needed, publish only `127.0.0.1:18893:8765`. Record any `COMMAND_CONCURRENCY`, `HTTP_KEEPALIVE_SECONDS` or allocator overrides; omit them when measuring defaults.

Launch `mnl-cap-live` with `python /result/supervise.py live`: CPU quota 1, memory 768m, `LIVE_TOWN=1`, `LIVE_CHAT=1`, `LIVE_ORIGINS=http://127.0.0.1:18893`, `LIVE_PER_IP=2000`, `LIVE_HANDSHAKES_PER_IP=10000`, `LIVE_NEW_SECS=0`; optional loopback publication `127.0.0.1:18894:8770`. The IP overrides only allow this one-machine load generator; do not transfer them to production.

Launch the generator from `mnl-capacity-client:local` on the same network with CPU quota 2, memory/swap both 4g, `CAP_API=http://mnl-cap-api:8765`, `CAP_LIVE=ws://mnl-cap-live:8770/live`, and the same `/result` mount. It retains per-delivery latency samples and needs memory for final aggregation; this is separate from the game services' quotas:

```sh
python /result/load.py --users 1000 --movers 1000 --duration 600 --period 5 --chat-rate 3 --name soak-200
```

For the 100 commands/s comparison, use `--duration 300 --period 10 --name final-100` with a freshly seeded database and unchanged service quotas.

## Read and retain evidence

`<name>.json` contains arrivals, successful completions in the measurement window, errors, latency percentiles, room counts, generator lag and resource samples. API/live resource JSONL files contain cgroup counters. After the run, retain `docker logs` and `/sys/fs/cgroup/memory.events` for each service, including the command-drain period. Pass criteria require the requested throughput, zero errors/OOMs/disconnections and acceptable tails, not just 1,000 idle sockets. Record both configured/monotonic duration and wall timestamps: a VM clock adjustment can make them differ.

The generator retains a bounded superset of known hashes (up to 8,000), which is valid protocol input but differs from the browser's current-state pruning. Reports include the final set-size distribution. Synthetic history compresses well in PostgreSQL. Traffic runs without TLS/Internet latency; 1,000 users occupy 34 rooms of up to 30, not a single 1,000-avatar viewport.

Run browser frame tests and integration suites separately. Recreate the scratch database after schema-heavy integration tests so checkpoint I/O cannot contaminate capacity runs. After evidence is saved, remove only the named test containers, their anonymous PostgreSQL volume, the test network and the generated `players.json` credentials. Keep reports. Never stop the user's ordinary preview.

For admission diagnosis only, `CAP_CLOSE_COMMANDS=1` asks for `Connection: close` on each command request. Leave it unset for acceptance: the application must behave correctly with an ordinary client. The report records this override. `server_command`/`outside_handler` latency fields are diagnostic hints derived from server wall-clock timestamps; VM clock adjustments can distort them. Use the monotonic `command_all` measurements for acceptance.
