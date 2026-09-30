#!/usr/bin/env bash
# One live delta sync SQLite -> PostgreSQL (no downtime). Safe to run any number of times
# before the cutover; refuses after it. sudo bash deploy/pg/sync.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/common.sh"
need_root
install -d -o "$RUN_USER" -g "$RUN_USER" -m 750 "$LOGDIR"
RUN=sync-$(stamp)
keep_running
timed "sync (live)" sync --max-mb-per-s "${MBPS:-15}"
