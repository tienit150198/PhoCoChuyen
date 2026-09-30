#!/usr/bin/env bash
# Nightly PostgreSQL backup of the game: pg_dump -Fc (compressed, restorable with pg_restore), keep 7.
# Installed by:  sudo bash deploy/pg/pg_backup.sh --install   (systemd timer mnl-pg-backup.timer, 03:40)
# Run once:      sudo systemctl start mnl-pg-backup.service
# Restore:       sudo -u postgres pg_restore -d phocochuyen --clean --if-exists <file>.dump   (game stopped)
set -euo pipefail
DBNAME=${DBNAME:-phocochuyen}
DEST=${DEST:-/var/backups/mot-ngay-lam-nghe-pg}
KEEP=${KEEP:-7}
HERE=$(cd "$(dirname "$0")" && pwd)

if [ "${1:-}" = --install ]; then
  [ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 1; }
  install -D -m 755 "$HERE/pg_backup.sh" /usr/local/sbin/mnl-pg-backup
  install -m 644 "$HERE/mnl-pg-backup.service" /etc/systemd/system/mnl-pg-backup.service
  install -m 644 "$HERE/mnl-pg-backup.timer" /etc/systemd/system/mnl-pg-backup.timer
  systemctl daemon-reload
  systemctl enable --now mnl-pg-backup.timer
  systemctl list-timers mnl-pg-backup.timer --no-pager
  exit 0
fi

install -d -o postgres -g postgres -m 700 "$DEST"
find "$DEST" -maxdepth 1 -name "$DBNAME-*.dump.part" -mmin +60 -delete   # leftovers of a killed run
# A full disk must never be caused by the backup: /var/backups usually shares the disk with PostgreSQL,
# which stops (PANIC) when it cannot write its WAL. Need 2x the newest dump (or 1/3 of the database) free.
last=$(ls -1t "$DEST"/"$DBNAME"-*.dump 2>/dev/null | head -1 || true)
if [ -n "$last" ]; then need=$(( $(stat -c %s "$last") * 2 ))
else need=$(( $(runuser -u postgres -- psql -Atq -c "select pg_database_size('$DBNAME')" postgres) / 3 )); fi
free=$(df --output=avail -B1 "$DEST" | tail -1)
if [ "$free" -lt "$need" ]; then
  echo "backup skipped: $((free / 1048576)) MB free in $DEST, need $((need / 1048576)) MB (free some disk, or DEST= another disk)" >&2
  exit 1
fi
f="$DEST/$DBNAME-$(date -u +%Y%m%d-%H%M%S).dump"
trap 'rm -f "$f.part"' EXIT   # never leave a partial dump behind (a failed one could fill the disk)
# pg_dump reads one consistent snapshot; low CPU/IO priority so the game keeps the disk.
runuser -u postgres -- nice -n 10 ionice -c2 -n7 pg_dump -Fc -Z 6 -f "$f.part" "$DBNAME"
mv "$f.part" "$f"
runuser -u postgres -- pg_restore -l "$f" >/dev/null   # the archive is readable
ls -1t "$DEST"/"$DBNAME"-*.dump | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "backup $f ($(du -h "$f" | cut -f1)); kept $(ls -1 "$DEST"/"$DBNAME"-*.dump | wc -l)"
