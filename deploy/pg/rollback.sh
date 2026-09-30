#!/usr/bin/env bash
# Go back from PostgreSQL to SQLite WITHOUT losing the progress made on PostgreSQL:
#   (game up)   copy the cutover snapshot to a new file (low IO priority; the snapshot is frozen)
#   (game down) stop -> reverse-sync PG into that new file -> swap it in -> remove the drop-in -> start
# The snapshot and the old SQLite file are never modified (the old one is kept as *.pg-era-<ts>).
#
#   sudo bash deploy/pg/rollback.sh [/var/lib/mot-ngay-lam-nghe/pre-pg-<ts>]   (default: the newest)
#   FORCE=1: run although the drop-in is missing (the game is not on PostgreSQL): normally refused.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/common.sh"
need_root
install -d -o "$RUN_USER" -g "$RUN_USER" -m 750 "$LOGDIR"
RUN=rollback-$(stamp)
keep_running
if [ ! -f "$DROPIN" ] && [ "${FORCE:-0}" != 1 ]; then
  die "the game is not on PostgreSQL (no $DROPIN): nothing to roll back (FORCE=1 to override)"
fi
BK=${1:-$(ls -1d "$DATA"/pre-pg-* 2>/dev/null | sort | tail -1)}
[ -n "$BK" ] && [ -f "$BK/$(basename "$DB")" ] || die "no cutover snapshot found (pass its directory)"
# A snapshot that is still the live file (same inode) while the game is on SQLite is not frozen: refuse.
if [ ! -f "$DROPIN" ] && [ "$(stat -c %i "$BK/$(basename "$DB")")" = "$(stat -c %i "$DB" 2>/dev/null || echo none)" ]; then
  die "$BK/$(basename "$DB") is the live SQLite file (same inode): not a usable cutover snapshot"
fi
TS=$(stamp)
NEW=$DATA/rollback-$TS.sqlite3
NEWLIM=$DATA/rollback-$TS-limits.sqlite3
echo "snapshot: $BK   log: $LOGDIR/$RUN.jsonl"
free=$(df --output=avail -B1 "$DATA" | tail -1)
[ "$free" -gt $(( $(stat -c %s "$BK/$(basename "$DB")") * 12 / 10 )) ] || die "not enough disk in $DATA for a new copy"
cleanup_new() { rm -f "$NEW" "$NEW-wal" "$NEW-shm" "$NEW-journal" "$NEWLIM" "$NEWLIM-wal" "$NEWLIM-shm" "$NEWLIM-journal"; }
restore_swap() {  # undo a half-done swap: the new files go back to $NEW*, the SQLite files to their names
  local f
  if [ -e "$DB.pg-era-$TS" ] && [ -e "$DB" ]; then mv -f "$DB" "$NEW"; fi
  if [ -e "$LIMITS.pg-era-$TS" ] && [ -e "$LIMITS" ]; then mv -f "$LIMITS" "$NEWLIM"; fi
  for f in "$DB" "$DB-wal" "$DB-shm" "$LIMITS" "$LIMITS-wal" "$LIMITS-shm"; do
    if [ -e "$f.pg-era-$TS" ]; then mv -f "$f.pg-era-$TS" "$f"; fi
  done
}
STAGE=up   # up -> down (stopped, still configured for PG) -> swap -> sqlite (drop-in removed)
on_err() {
  trap - ERR INT TERM
  echo "!!! unexpected error ($1) (stage $STAGE)" >&2
  case "$STAGE" in
    up) cleanup_new; echo "nothing changed; the game still runs on PostgreSQL" >&2;;
    down|swap)
      if [ "$STAGE" = swap ]; then restore_swap || true; fi
      cleanup_new
      echo "the game stays on PostgreSQL (drop-in kept); starting it again" >&2
      systemctl start "$SERVICE" || true;;
    *) echo "the files are swapped and the drop-in is removed: start the game on SQLite (systemctl start $SERVICE), check journalctl -u $SERVICE" >&2;;
  esac
  print_times
  exit 1
}
trap 'on_err "line $LINENO"' ERR
trap 'on_err "interrupted by a signal"' INT TERM   # Ctrl-C: a clean way back, never a stopped game

# 1) game still up: copy the frozen snapshot (mode 600, owned by the game user)
t=$(date +%s.%N)
cpy() { ionice -c2 -n7 nice -n 10 cp --sparse=always --no-preserve=mode,ownership "$1" "$2"; }
for f in "$DB" "$DB-wal"; do
  if [ -f "$BK/$(basename "$f")" ]; then cpy "$BK/$(basename "$f")" "$NEW${f#"$DB"}"; fi
done
limflag=()
if [ -f "$BK/$(basename "$LIMITS")" ]; then
  cpy "$BK/$(basename "$LIMITS")" "$NEWLIM"
  if [ -f "$BK/$(basename "$LIMITS")-wal" ]; then cpy "$BK/$(basename "$LIMITS")-wal" "$NEWLIM-wal"; fi
  limflag=(--limits-out "$NEWLIM")
fi
chmod 600 "$NEW"* "$NEWLIM"* 2>/dev/null || true
chown "$RUN_USER:$RUN_USER" "$NEW"* "$NEWLIM"* 2>/dev/null || true
TIMES+=("$(printf '%-34s %7ss' "copy snapshot (game up)" "$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$t}")")")

# 2) downtime
MIG_NICE=""
T_DOWN=$(date +%s.%N)
echo ">>> DOWNTIME starts $(date -u +%H:%M:%S) UTC"
systemctl stop "$SERVICE"
STAGE=down
if ! timed "reverse-sync PG -> new SQLite" reverse-sync --out "$NEW" --copy-ready "${limflag[@]}"; then
  cleanup_new
  echo "!!! reverse-sync failed: the game stays on PostgreSQL (drop-in kept); starting it again" >&2
  systemctl start "$SERVICE"; exit 1
fi
for f in "$NEW-wal" "$NEWLIM-wal"; do
  if [ -s "$f" ]; then
    echo "!!! $f is not empty: the new file is not self-contained; the game stays on PostgreSQL" >&2
    cleanup_new; systemctl start "$SERVICE"; exit 1
  fi
done
rm -f "$NEW-wal" "$NEW-shm" "$NEWLIM-wal" "$NEWLIM-shm"
STAGE=swap
# swap: the current SQLite files (frozen since the cutover) are kept aside, never deleted
for f in "$DB" "$DB-wal" "$DB-shm" "$LIMITS" "$LIMITS-wal" "$LIMITS-shm"; do
  if [ -e "$f" ]; then mv -f "$f" "$f.pg-era-$TS"; fi
done
mv "$NEW" "$DB"
if [ -f "$NEWLIM" ]; then mv "$NEWLIM" "$LIMITS"; fi
chown "$RUN_USER:$RUN_USER" "$DB" "$LIMITS" 2>/dev/null || true
chmod 640 "$DB" "$LIMITS" 2>/dev/null || true
rm -f "$DROPIN"
STAGE=sqlite
systemctl daemon-reload
systemctl start "$SERVICE"
trap - ERR INT TERM
enable_sqlite_backups || true
health || die "the game does not answer on SQLite: journalctl -u $SERVICE"
DOWN=$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N)-$T_DOWN}")
print_times
echo ">>> back on SQLite, downtime ${DOWN}s. PostgreSQL is kept as it is (marked cut over: copy/sync refuse)."
echo "    To try the cutover again later: sudo -u postgres dropdb phocochuyen && sudo bash $HERE/install_pg16.sh,"
echo "    then precopy.sh (docs/POSTGRES_CUTOVER.md)."
