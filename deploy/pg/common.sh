# Shared settings of the deploy/pg scripts (sourced, not run). Override any of them in the environment.
# APP: a directory with scripts/pg_migrate.py and game/pg_schema.py, readable by $RUN_USER (not under /root).
# Before the pg-backend release is live, e.g. APP=/opt/mot-ngay-lam-nghe/pgdeploy (see docs/POSTGRES_CUTOVER.md).
APP=${APP:-/opt/mot-ngay-lam-nghe/current}
RELEASE=${RELEASE:-/opt/mot-ngay-lam-nghe/current}       # the release the service runs (must be pg-backend at cutover)
SERVICE=${SERVICE:-mot-ngay-lam-nghe}
RUN_USER=${RUN_USER:-mnl}
DATA=${DATA:-/var/lib/mot-ngay-lam-nghe}
DB=${DB:-$DATA/game.sqlite3}
LIMITS=${LIMITS:-$DATA/game-limits.sqlite3}
ETC=${ETC:-/etc/mot-ngay-lam-nghe}
PG_ENV=${PG_ENV:-$ETC/pg.env}
DROPIN_DIR=${DROPIN_DIR:-/etc/systemd/system/$SERVICE.service.d}
DROPIN=${DROPIN:-$DROPIN_DIR/50-postgres.conf}
HEALTH_URL=${HEALTH_URL:-http://127.0.0.1:8765}
LOGDIR=${LOGDIR:-$DATA/pg-migration}
MIG_NICE=${MIG_NICE-nice -n 10 ionice -c2 -n7}                # low priority while the game runs; "" in the downtime

die() { echo "ERROR: $*" >&2; exit 1; }
need_root() { [ "$(id -u)" = 0 ] || die "run as root (sudo)"; }
stamp() { date +%Y%m%d-%H%M%S; }

# A lost terminal (SSH drop, closed laptop) must never stop a script half way, least of all in the
# downtime: ignore SIGHUP/SIGPIPE and copy all output to $LOGDIR/$RUN.out (tee keeps writing the file
# when the terminal is gone: -p). Ctrl-C (SIGINT) still works; cutover/rollback turn it into a clean abort.
keep_running() {
  trap '' HUP PIPE
  exec > >(tee -a -p "$LOGDIR/$RUN.out") 2>&1
  echo "output: $LOGDIR/$RUN.out (the script goes on if the terminal is lost; still, prefer tmux)"
}

# Run pg_migrate.py as the game user with DATABASE_URL in its environment (never on a command line).
mig() {
  [ -r "$PG_ENV" ] || die "$PG_ENV missing: run install_pg16.sh"
  runuser -u "$RUN_USER" -- test -r "$APP/scripts/pg_migrate.py" -a -r "$APP/game/pg_schema.py"     || die "$RUN_USER cannot read $APP/scripts/pg_migrate.py and $APP/game/pg_schema.py (APP=...; not under /root)"
  ( set -a; . "$PG_ENV"; set +a
    cd /
    # shellcheck disable=SC2086
    exec runuser -u "$RUN_USER" -- $MIG_NICE python3 "$APP/scripts/pg_migrate.py" \
      --sqlite "$DB" --limits "$LIMITS" --pg-env-file /nonexistent --schema-file "$APP/game/pg_schema.py" "$@" )
}

# `mig` with timing; appends the JSON lines to the log and prints the final result line.
T_START=$(date +%s.%N)
declare -a TIMES=()
timed() {
  local name=$1; shift
  local t0 t1 rc
  t0=$(date +%s.%N)
  set +e
  mig "$@" --json >>"$LOGDIR/$RUN.jsonl" 2>>"$LOGDIR/$RUN.err"
  rc=$?
  set -e
  t1=$(date +%s.%N)
  local el; el=$(awk "BEGIN{printf \"%.1f\", $t1-$t0}")
  TIMES+=("$(printf '%-34s %7ss  rc=%s' "$name" "$el" "$rc")")
  if [ "$rc" = 0 ]; then
    printf '%-34s %7ss  rc=%s   %s\n' "$name" "$el" "$rc" "$(grep '"event": "result"' "$LOGDIR/$RUN.jsonl" | tail -1 | cut -c1-220)"
  else  # the reason of THIS step (not the previous result line)
    printf '%-34s %7ss  rc=%s   %s\n' "$name" "$el" "$rc" "$(grep -E '"event": "(error|verify-done)"' "$LOGDIR/$RUN.jsonl" | tail -1 | cut -c1-300)"
    grep '"event": "verify"' "$LOGDIR/$RUN.jsonl" | grep -v '"mismatch": 0,' | tail -5 | cut -c1-300 || true
    tail -3 "$LOGDIR/$RUN.err" 2>/dev/null | cut -c1-300 || true
  fi
  return $rc
}

print_times() {
  echo "---- timings ----"
  local l; for l in "${TIMES[@]}"; do echo "$l"; done
}

HEALTH_S=${HEALTH_S:-45}
health() {  # wait at most $1 seconds of wall clock (default $HEALTH_S) for /api/health
  local deadline r0 r
  deadline=$(( $(date +%s) + ${1:-$HEALTH_S} ))
  r0=$(systemctl show -p NRestarts --value "$SERVICE" 2>/dev/null || echo 0)
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if curl -fsS -m 2 "$HEALTH_URL/api/health" >/dev/null 2>&1; then return 0; fi
    # a crash loop (e.g. the database is unreachable) never becomes healthy: stop waiting
    if systemctl is-failed --quiet "$SERVICE" 2>/dev/null; then
      echo "   $SERVICE is in the failed state: not waiting any longer" >&2; return 1
    fi
    r=$(systemctl show -p NRestarts --value "$SERVICE" 2>/dev/null || echo 0)
    if [[ "$r" =~ ^[0-9]+$ && "$r0" =~ ^[0-9]+$ ]] && [ $((r - r0)) -gt 2 ]; then
      echo "   $SERVICE restarted $((r - r0)) times (crash loop): not waiting any longer" >&2; return 1
    fi
    sleep 1
  done
  return 1
}

# The old SQLite backup timer(s) (they copy game.sqlite3). SQLITE_BACKUP_TIMERS="a.timer b.timer" overrides the search.
TIMERS_FILE=${TIMERS_FILE:-$LOGDIR/sqlite-backup-timers.disabled}
sqlite_backup_timers() {
  if [ -n "${SQLITE_BACKUP_TIMERS:-}" ]; then printf '%s\n' $SQLITE_BACKUP_TIMERS; return 0; fi
  systemctl list-unit-files --type=timer --no-legend 2>/dev/null | awk '{print $1}' | grep -E '^(mot-ngay-lam-nghe|mnl|phocochuyen)[-_.a-z0-9]*backup[-_.a-z0-9]*\.timer$' | grep -vx 'mnl-pg-backup.timer' || true
}
disable_sqlite_backups() {  # after the cutover: the SQLite files are frozen (mode 000)
  local t found=0
  : >"$TIMERS_FILE.new"
  for t in $(sqlite_backup_timers); do
    found=1
    if systemctl disable --now "$t" >/dev/null 2>&1; then echo "disabled the old SQLite backup timer $t"; echo "$t" >>"$TIMERS_FILE.new"
    else echo "!!! could not disable $t: do it by hand (systemctl disable --now $t)" >&2; fi
  done
  mv -f "$TIMERS_FILE.new" "$TIMERS_FILE"
  [ $found = 1 ] || echo "NOTE: no SQLite backup timer found (SQLITE_BACKUP_TIMERS=... names it): disable it by hand if there is one"
}
# A periodic sync (e.g. a transient mnl-pgsync.timer) would race the cutover's own syncs for the one
# advisory lock (the loser fails: in the downtime that is an abort). Stop it and let a running one finish.
stop_pgsync() {
  local i
  if systemctl is-active --quiet mnl-pgsync.timer 2>/dev/null; then
    systemctl stop mnl-pgsync.timer || true
    echo "stopped mnl-pgsync.timer (a transient timer is gone once stopped: recreate it if the cutover is aborted)"
  fi
  for i in $(seq 1 300); do systemctl is-active --quiet mnl-pgsync.service 2>/dev/null || return 0; sleep 1; done
  die "mnl-pgsync.service still runs after 5 min: stop it (systemctl stop mnl-pgsync.service), then run the cutover again"
}
enable_sqlite_backups() {  # after a rollback to SQLite: the timers the cutover disabled (or the ones found)
  local t list
  if [ -s "$TIMERS_FILE" ]; then list=$(cat "$TIMERS_FILE"); else list=$(sqlite_backup_timers); fi
  for t in $list; do
    if systemctl enable --now "$t" >/dev/null 2>&1; then echo "re-enabled the SQLite backup timer $t"
    else echo "!!! could not re-enable $t: systemctl enable --now $t" >&2; fi
  done
  [ -n "$list" ] || echo "NOTE: no SQLite backup timer to re-enable (none recorded or found): check your SQLite backups"
  rm -f "$TIMERS_FILE"
}
