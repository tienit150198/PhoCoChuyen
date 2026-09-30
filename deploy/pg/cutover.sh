#!/usr/bin/env bash
# Switch the game from SQLite to PostgreSQL with a short downtime (twin: 4.3 s; prod: about 10-25 s).
# Prerequisites: install_pg16.sh ran, precopy.sh finished (status: every table "synced"),
# and the running release ($RELEASE) is the pg-backend one (it still runs on SQLite until now).
#
#   sudo bash deploy/pg/cutover.sh
#   sudo BASELINE=1 bash deploy/pg/cutover.sh      # force a new live verify baseline first (slow, no downtime)
#   sudo AUTO_ROLLBACK=0 bash deploy/pg/cutover.sh # on a failed health check, stop and ask instead of rolling back
#
# Phase A (game up):   sync, [verify --live baseline], sync, sync
# Phase B (game DOWN): stop -> snapshot SQLite (hard links, instant) -> final sync -> fast verify
#                      [ABORT: start the game on SQLite, untouched] -> finalize (stat triggers,
#                      schema version, sequences) -> mark-cutover -> systemd drop-in with
#                      EnvironmentFile=pg.env -> start -> health -> smoke test (a real save read)
# Rollback later: sudo bash deploy/pg/rollback.sh   (keeps the progress made on PostgreSQL)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/common.sh"
need_root
install -d -o "$RUN_USER" -g "$RUN_USER" -m 750 "$LOGDIR"
RUN=cutover-$(stamp)
keep_running
BK=$DATA/pre-pg-$(stamp)
echo "log: $LOGDIR/$RUN.jsonl"

# ---- preflight (nothing changes yet)
[ -f "$DROPIN" ] && die "$DROPIN exists: already cut over"
[ -r "$PG_ENV" ] || die "$PG_ENV missing (install_pg16.sh)"
grep -q "DATABASE_URL" "$RELEASE/game/db.py" 2>/dev/null || die "$RELEASE is not the pg-backend release (game/db.py without DATABASE_URL): deploy it (on SQLite) first"
[ -f "$APP/scripts/pg_migrate.py" ] || die "$APP/scripts/pg_migrate.py missing"
systemctl is-active --quiet "$SERVICE" || die "$SERVICE is not running: start it (on SQLite) first"
mig status --json >"$LOGDIR/$RUN.status.json" 2>&1 || die "pg_migrate status failed: $(tail -3 "$LOGDIR/$RUN.status.json")"
python3 - "$LOGDIR/$RUN.status.json" <<'PY' || die "precopy is not complete (run precopy.sh)"
import json,sys
st=[json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
st=[e for e in st if e.get("event")=="status"][-1]
bad=[t for t,v in st["tables"].items() if v["phase"] not in ("copied","synced")]
if bad or not st["tables"] or st.get("cutover_at"): print("not ready:",bad or "cutover already marked"); sys.exit(1)
PY
free=$(df --output=avail -B1 "$DATA" | tail -1)
size=$(stat -c %s "$DB")
[ "$free" -gt $((size / 4)) ] || die "not enough free disk in $DATA"

stop_pgsync

# ---- phase A: game up
timed "A sync (live)" sync --max-mb-per-s "${MBPS:-20}"
if [ "${BASELINE:-auto}" = 1 ] || { [ "${BASELINE:-auto}" = auto ] && python3 - "$LOGDIR/$RUN.status.json" <<'PY'
import json,sys,time
st=[e for e in (json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")) if e.get("event")=="status"][-1]
v=float(st.get("verified_at") or 0)
sys.exit(0 if time.time()-v>6*3600 else 1)   # no baseline in the last 6 h: make one (live, no downtime)
PY
}; then
  for attempt in 1 2; do
    if timed "A verify --live (baseline #$attempt)" verify --live --max-mb-per-s "${MBPS:-20}"; then break; fi
    timed "A sync (repairs)" sync --max-mb-per-s "${MBPS:-20}"
  done
fi
# The fast verify in the downtime needs a baseline; without one it would hash every save while the game is down.
mig status --json >"$LOGDIR/$RUN.status2.json" 2>&1 || true
if ! python3 - "$LOGDIR/$RUN.status2.json" <<'PY'
import json,sys
st=[e for e in (json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")) if e.get("event")=="status"]
sys.exit(0 if st and st[-1].get("verified_at") else 1)
PY
then
  [ "${ALLOW_FULL_VERIFY:-0}" = 1 ] || die "no verify baseline (verify --live keeps failing: see $LOGDIR/$RUN.jsonl). Fix that, or ALLOW_FULL_VERIFY=1 (full verify inside the downtime)"
fi
timed "A sync (just before stop)" sync
timed "A sync (just before stop #2)" sync

# ---- phase B: downtime
MIG_NICE=""
T_DOWN=$(date +%s.%N)
STAGE=stopped            # stopped -> marked (PG is the database of record) -> started
MODES=()
freeze_sqlite() {        # the game must never fall back to the old SQLite file silently (it fails loudly instead)
  local f; for f in "$DB" "$DB-wal" "$DB-shm" "$LIMITS" "$LIMITS-wal" "$LIMITS-shm"; do
    if [ -e "$f" ]; then MODES+=("$(stat -c %a "$f") $f"); chmod 000 "$f"; fi
  done
}
thaw_sqlite() { local m; for m in "${MODES[@]}"; do chmod "${m%% *}" "${m#* }" || true; done; MODES=(); }
back_to_sqlite() {
  thaw_sqlite
  rm -f "$DROPIN"; systemctl daemon-reload
  systemctl start "$SERVICE" || true
  if health; then echo "game is up on SQLite (its file is untouched since the stop)"
  else echo "!!! the game does not answer on SQLite either: journalctl -u $SERVICE" >&2; fi
}
abort() {
  trap - ERR INT TERM
  echo "!!! $1: ABORT, the game goes back to SQLite untouched" >&2
  rm -rf "$BK"   # only hard links to the live files: never leave them next to a live database
  if [ "$STAGE" = marked ]; then timed "B unmark-cutover" unmark-cutover || true; fi
  back_to_sqlite
  print_times
  exit 1
}
on_err() {
  case "$STAGE" in
    stopped|marked) abort "unexpected error ($1) (the game never served on PostgreSQL)";;
    *) echo "!!! unexpected error ($1) after the start: check the game (journalctl -u $SERVICE)" >&2; print_times; exit 1;;
  esac
}
echo ">>> DOWNTIME starts $(date -u +%H:%M:%S) UTC"
systemctl stop "$SERVICE"
trap 'on_err "line $LINENO"' ERR
trap 'on_err "interrupted by a signal"' INT TERM   # Ctrl-C in the downtime: a clean abort, never a stopped game
t=$(date +%s.%N)
install -d -o root -g root -m 700 "$BK"
for f in "$DB" "$DB-wal" "$LIMITS" "$LIMITS-wal"; do
  if [ -f "$f" ]; then ln "$f" "$BK/$(basename "$f")"; fi
done
TIMES+=("$(printf '%-34s %7ss' "B stop + snapshot (hard links)" "$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$t}")")")
echo "snapshot: $BK"

timed "B final sync" sync || abort "final sync failed"
timed "B verify --fast" verify --fast || abort "verify found differences (ids in $LOGDIR/$RUN.jsonl)"
timed "B finalize (triggers, seq)" finalize || abort "finalize failed"
timed "B mark-cutover" mark-cutover || abort "mark-cutover failed"
STAGE=marked

# Count saves in PostgreSQL (smoke test proof that the game writes there)
pgcount() { ( set -a; . "$PG_ENV"; set +a; runuser -u "$RUN_USER" -- python3 -c 'import os,psycopg
c=psycopg.connect(os.environ["DATABASE_URL"],connect_timeout=5);print(c.execute("select count(*) from sessions").fetchone()[0]);c.close()' ) 2>/dev/null || echo "?"; }
before=$(pgcount)

install -d -m 755 "$DROPIN_DIR"
{
  echo "# PostgreSQL backend (deploy/pg/cutover.sh $(date -u '+%F %T') UTC). Rollback: deploy/pg/rollback.sh"
  echo "[Unit]"
  echo "After=postgresql.service"
  echo "Wants=postgresql.service"
  echo "[Service]"
  echo "EnvironmentFile=$PG_ENV"
  echo "# 4 workers x 12 = 48 connections at most: under max_connections, with room for tools"
  echo "Environment=PG_POOL=6 PG_POOL_MAX=12"
  echo "IPAddressAllow=localhost"
} >"$DROPIN.new"
mv -f "$DROPIN.new" "$DROPIN"
systemctl daemon-reload
freeze_sqlite
t=$(date +%s.%N)
systemctl start "$SERVICE"
STAGE=started
trap - ERR INT TERM
if ! health; then
  echo "!!! health check failed on PostgreSQL" >&2
  systemctl stop "$SERVICE" || true
  if timed "B verify --fast (did PG take writes?)" verify --fast; then
    # PostgreSQL still equals SQLite: the game never wrote there. Go back without a reverse sync.
    timed "B unmark-cutover" unmark-cutover || true
    back_to_sqlite
    rm -rf "$BK"
    echo "PostgreSQL is unchanged; fix the cause (journalctl -u $SERVICE), then run cutover.sh again."
  elif ! ( set -a; . "$PG_ENV"; set +a; runuser -u "$RUN_USER" -- python3 -c 'import os,psycopg;psycopg.connect(os.environ["DATABASE_URL"],connect_timeout=5).close()' ) 2>/dev/null; then
    echo "!!! PostgreSQL is unreachable: the game never served on it (no health answer). Back to SQLite." >&2
    back_to_sqlite
    rm -rf "$BK"   # hard links to the live SQLite file (the game never served on PG): never keep them next to it
    echo "PostgreSQL stays marked cut over: after fixing it, recreate the database and precopy again (docs/POSTGRES_CUTOVER.md, section 6)."
  elif [ "${AUTO_ROLLBACK:-1}" = 1 ]; then
    print_times
    exec bash "$HERE/rollback.sh" "$BK"
  else
    echo "!!! the game is DOWN; PostgreSQL has new writes: run bash $HERE/rollback.sh $BK (keeps them) or fix and start" >&2
  fi
  print_times
  exit 1
fi
TIMES+=("$(printf '%-34s %7ss' "B start + health" "$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$t}")")")
DOWN=$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$T_DOWN}")
echo ">>> DOWNTIME ends $(date -u +%H:%M:%S) UTC: ${DOWN}s"

# ---- smoke test: a new guest save through the API, then a real read of it (GET /api/state)
if python3 - "$HEALTH_URL" <<'PY'
import json,sys,urllib.request
base=sys.argv[1]
r=urllib.request.urlopen(urllib.request.Request(base+"/api/bootstrap?lite=1",headers={"Host":"127.0.0.1"}),timeout=15)
boot=json.load(r); cookie=r.headers.get("Set-Cookie","").split(";")[0]
assert cookie and "revision" in boot, "bootstrap"
r=urllib.request.urlopen(urllib.request.Request(base+"/api/state",headers={"Host":"127.0.0.1","Cookie":cookie}),timeout=15)
st=json.load(r); assert st["revision"]==boot["revision"] and st["state"], "state"
print("smoke: bootstrap + /api/state ok, revision", st["revision"])
PY
then
  after=$(pgcount)
  if [[ "$after" =~ ^[0-9]+$ && "$before" =~ ^[0-9]+$ ]] && [ "$after" -gt "$before" ]; then echo "smoke: the new save is in PostgreSQL ($before -> $after saves)"
  else echo "!!! smoke: no new save in PostgreSQL ($before -> $after): is the game really on PostgreSQL? journalctl -u $SERVICE" >&2; fi
else
  echo "!!! smoke test failed (the game answers /api/health): check journalctl -u $SERVICE; rollback: bash $HERE/rollback.sh $BK" >&2
fi
print_times
echo "downtime: ${DOWN}s   snapshot of the SQLite files: $BK (keep it until PostgreSQL has proven itself)"
echo "The old SQLite files are now mode 000: a game started without the drop-in fails loudly instead of serving old data."

# An independent copy of the snapshot (the hard links share the files' inodes), after the downtime.
if [ "$(df --output=avail -B1 "$DATA" | tail -1)" -gt $((size * 2)) ]; then
  ( for f in "$BK"/*; do ionice -c3 nice -n 19 cp --sparse=always "$f" "$f.copy" && mv -f "$f.copy" "$f"; done
    chmod 400 "$BK"/*; echo "snapshot copied $(date -u +%T)" >"$BK/COPIED" ) >/dev/null 2>&1 &
  echo "copying the snapshot into independent files in the background (ionice idle): $BK/COPIED when done"
else
  echo "NOTE: not enough disk for an independent copy of $BK: the hard links protect the files as long as nobody writes to $DB"
fi
disable_sqlite_backups || true
echo "Next: enable PostgreSQL backups: sudo bash $HERE/pg_backup.sh --install   ($BK is the last SQLite backup)"
