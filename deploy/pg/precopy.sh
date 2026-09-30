#!/usr/bin/env bash
# Pre-copy while the game runs (no downtime): schema, full copy (throttled, resumable), a sync,
# and a live verify that sets the baseline of the fast verify at cutover. Run it off-peak.
#
#   sudo bash deploy/pg/precopy.sh             # MBPS=8 by default (read cap on the game disk)
#   sudo MBPS=15 bash deploy/pg/precopy.sh     # faster when the night is quiet
#   sudo RESTART=1 bash deploy/pg/precopy.sh   # throw the copy away and start again
#
# Interrupt it at any time (Ctrl-C): run it again and the copy resumes where it stopped.
# Watch: tail -f /var/lib/mot-ngay-lam-nghe/pg-migration/precopy-*.jsonl
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/common.sh"
need_root
MBPS=${MBPS:-8}
install -d -o "$RUN_USER" -g "$RUN_USER" -m 750 "$LOGDIR"
RUN=precopy-$(stamp)
keep_running
[ -f "$APP/scripts/pg_migrate.py" ] && [ -f "$APP/game/pg_schema.py" ] || die "$APP has no scripts/pg_migrate.py + game/pg_schema.py (deploy the pg-backend release first, or set APP=)"
[ -f "$DROPIN" ] && die "$DROPIN exists: the game already runs on PostgreSQL"
echo "log: $LOGDIR/$RUN.jsonl"
wal() { stat -c %s "$DB-wal" 2>/dev/null || echo 0; }
echo "SQLite: $(du -h "$DB" | cut -f1)  WAL: $(( $(wal) / 1048576 )) MB"

timed "init (tables, tuning)" init
restart=(); [ "${RESTART:-0}" = 1 ] && restart=(--restart)
timed "copy (live, ${MBPS} MB/s cap)" copy --max-mb-per-s "$MBPS" --pause-ms 20 "${restart[@]}"
echo "WAL after copy: $(( $(wal) / 1048576 )) MB (must stay small: the copy never pins a snapshot)"
timed "sync #1 (live)" sync --max-mb-per-s "$MBPS"
timed "sync #2 (live)" sync --max-mb-per-s "$MBPS"
if ! timed "verify --live (baseline)" verify --live --max-mb-per-s "$MBPS"; then
  echo "   verify --live found differences (ids in $LOGDIR/$RUN.jsonl): repairing with a sync, then verifying again"
  timed "sync (repairs)" sync --max-mb-per-s "$MBPS"
  timed "verify --live (baseline #2)" verify --live --max-mb-per-s "$MBPS" || echo "   !!! still different: do not cut over; send $LOGDIR/$RUN.jsonl"
fi
timed "sync #3 (live)" sync --max-mb-per-s "$MBPS"
print_times
mig status
echo "Pre-copy done. Keep syncing now and then (sudo bash $HERE/sync.sh) until the cutover."
