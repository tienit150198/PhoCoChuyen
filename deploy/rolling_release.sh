#!/bin/bash
# Zero-downtime release of Phố Có Chuyện (docs/DEPLOY_ROLLING.md). Run as root on the game host.
#
#   deploy/rolling_release.sh /tmp/mnl-release.zip     unpack a release zip and switch to it
#   deploy/rolling_release.sh --to /opt/mot-ngay-lam-nghe/releases/<dir>
#                                                        switch to a release already unpacked (rollback)
#   deploy/rolling_release.sh --check                   check the preconditions, change nothing
#   deploy/rolling_release.sh --recover                 after a run stopped half-way: nginx back to the
#                                                        canonical unit, bridge stopped (see the doc)
#
# How: a "bridge" copy of the service (the same unit, drop-ins and environment, its own cgroup) starts
# from the new release on BRIDGE_PORT; nginx is pointed at it (graceful reload: requests in flight finish
# on the old server); once the old port has drained, the canonical unit restarts on the new release with
# no traffic on it; nginx is pointed back at PORT, the bridge drains and stops. Between releases the
# layout is exactly as before: one unit (mot-ngay-lam-nghe) on 127.0.0.1:8765, `current` -> the live
# release. Only the one nginx site file below is edited, and only its 127.0.0.1:<port> addresses.
set -Eeuo pipefail

APP=${APP:-/opt/mot-ngay-lam-nghe}
SERVICE=${SERVICE:-mot-ngay-lam-nghe}
BRIDGE=${BRIDGE:-mot-ngay-lam-nghe-bridge}
PORT=${PORT:-8765}                  # the canonical unit's port: nginx points here between releases
BRIDGE_PORT=${BRIDGE_PORT:-8766}
SITE=${SITE:-/etc/nginx/sites-enabled/phocochuyen}
HEALTH_MAX=${HEALTH_MAX:-90}        # seconds for a server to answer /api/health
DRAIN_MAX=${DRAIN_MAX:-75}          # seconds for in-flight requests to finish (proxy_read_timeout is 60 s)
KEEP=${KEEP:-3}                     # releases kept on disk (never the live one nor the previous one)
BRIDGE_PG_POOL=${BRIDGE_PG_POOL:-2}          # the bridge's PostgreSQL pool per worker: two servers
BRIDGE_PG_POOL_MAX=${BRIDGE_PG_POOL_MAX:-6}  # share max_connections for a minute
BRIDGE_MEMORY_MAX=${BRIDGE_MEMORY_MAX:-}     # e.g. 2G; empty = the unit's own MemoryMax
SMOKE_URL=${SMOKE_URL:-}            # optional, e.g. https://phocochuyen.io.vn/api/health (asked via 127.0.0.1)
BACKUPS=${BACKUPS:-/root/nginx-rolling}      # copies of the site file before each edit (outside /etc/nginx)
UNIT_FILE=/run/systemd/system/$BRIDGE.service   # a runtime unit: gone after a reboot
LOCK=/run/mnl-rolling-release.lock

LOG=${LOG:-/var/log/mnl-rolling-release.log}

log(){ printf '%s %s\n' "$(date +%T)" "$*"; }
die(){ log "ABORT: $*"; exit 1; }
[ "$(id -u)" = 0 ] || die "run as root"
exec 9>"$LOCK"; flock -n 9 || die "another rolling release is running"
# A dropped SSH session must not stop a run half-way (players could be left on the bridge): ignore
# SIGHUP and keep a copy of the output in $LOG. Still, run it inside tmux.
trap '' HUP
exec > >(tee -a -p "$LOG") 2>&1
log "---- $0 $* (pid $$)"

MODE=zip ZIP="" REL=""
case "${1:-}" in
  --to) MODE=to; REL=$(readlink -f "${2:?--to needs a release directory}");;
  --check) MODE=check;;
  --recover) MODE=recover;;
  ""|-h|--help) sed -n '2,17p' "$0"; exit 2;;
  *) ZIP=$1; [ -f "$ZIP" ] || die "no such zip: $ZIP";;
esac

SITE_REAL=$(readlink -f "$SITE")
listening(){ ss -Hltn "sport = :$1" | grep -q .; }
conns(){ ss -Htn state established "( sport = :$1 )" | wc -l; }
health(){ curl -fsS -m 3 -H 'Host: 127.0.0.1' "http://127.0.0.1:$1/api/health"; }
field(){ python3 -c 'import json,sys;print(json.load(sys.stdin).get(sys.argv[1],""))' "$1"; }
wait_health(){  # port [version]: until /api/health answers (for that release version)
  local port=$1 want=${2:-} out i
  for i in $(seq 1 $((HEALTH_MAX*2))); do
    if out=$(health "$port" 2>/dev/null) && { [ -z "$want" ] || [ "$(field version <<<"$out")" = "$want" ]; }; then
      log "  :$port healthy: $(field game_version <<<"$out")"; return 0
    fi
    sleep 0.5
  done
  return 1
}
points_at(){ grep -Eq "127\.0\.0\.1:$1([^0-9]|$)" "$SITE_REAL"; }
switch_upstream(){  # from to: point every 127.0.0.1:<from> of the site at <to>, test, reload gracefully
  local from=$1 to=$2 bak
  mkdir -p "$BACKUPS"; bak=$BACKUPS/$(basename "$SITE_REAL").$(date +%Y%m%d-%H%M%S).$from
  cp -a "$SITE_REAL" "$bak"
  sed -i -E "s/127\.0\.0\.1:$from([^0-9]|$)/127.0.0.1:$to\1/g" "$SITE_REAL"
  if ! points_at "$to" || points_at "$from" || ! nginx -t -q; then
    cp -a "$bak" "$SITE_REAL"; die "nginx switch :$from -> :$to failed (site file restored from $bak, nothing reloaded)"
  fi
  systemctl reload nginx
  log "  nginx -> 127.0.0.1:$to (graceful reload; previous file $bak)"
}
drain(){  # port: until nginx has no request in flight to it (2 quiet seconds), at most DRAIN_MAX s
  local port=$1 i n quiet=0
  for i in $(seq 1 "$DRAIN_MAX"); do
    n=$(conns "$port")
    if [ "$n" -eq 0 ]; then quiet=$((quiet+1)); if [ $quiet -ge 2 ]; then log "  :$port drained after ${i}s"; return 0; fi
    else quiet=0; fi
    if [ $((i % 5)) -eq 0 ]; then log "  :$port still has $n connection(s)"; fi
    sleep 1
  done
  log "  :$port still had $(conns "$port") connection(s) after ${DRAIN_MAX}s: stopping anyway (clients re-send)"
}
old_nginx_gone(){  # an old nginx worker (from before a reload) can keep an HTTP/2 client and its upstream
  # port alive long after the reload: wait until every "shutting down" worker has exited before the
  # port it still points at goes away, at most OLD_NGINX_MAX s.
  local i
  for i in $(seq 1 "${OLD_NGINX_MAX:-90}"); do
    pgrep -f 'nginx: worker process is shutting down' >/dev/null || { [ "$i" -gt 1 ] && log "  old nginx workers gone after ${i}s"; return 0; }
    if [ $((i % 10)) -eq 0 ]; then log "  waiting for old nginx workers to finish (${i}s)"; fi
    sleep 1
  done
  log "  old nginx workers still there after ${OLD_NGINX_MAX:-90}s: going on"
}
stop_bridge(){ systemctl stop "$BRIDGE" 2>/dev/null || true; rm -f "$UNIT_FILE"; systemctl daemon-reload; }
release_version(){ sed -n 's/^__version__ *= *"\(.*\)".*/\1/p' "$1/game/__init__.py" | head -1; }
# Enabled nginx files (nginx -T) other than our site that use a port: dk_bike must never be touched.
others_using(){ nginx -T 2>/dev/null | awk -v p="127\\\\.0\\\\.0\\\\.1:$1([^0-9]|$)" '/^# configuration file /{f=$4;sub(/:$/,"",f)} $0~p{print f}' \
  | sort -u | while read -r f; do [ "$(readlink -f "$f")" = "$SITE_REAL" ] || echo "$f"; done; }

[ -f "$SITE_REAL" ] || die "no nginx site $SITE"

if [ "$MODE" = recover ]; then
  log "== recover"
  if points_at "$BRIDGE_PORT"; then
    wait_health "$PORT" || die "$SERVICE does not answer on :$PORT; players stay on the bridge. Fix it first (journalctl -u $SERVICE), then run --recover again"
    switch_upstream "$BRIDGE_PORT" "$PORT"; drain "$BRIDGE_PORT"; old_nginx_gone
  fi
  stop_bridge
  points_at "$PORT" || die "$SITE_REAL does not point at 127.0.0.1:$PORT"
  log "recovered: nginx -> :$PORT ($(health "$PORT" | field game_version)), current -> $(readlink -f "$APP/current")"
  exit 0
fi

# ---- preconditions (nothing changes before these pass) ------------------------------------------------
log "== preconditions"
systemctl is-active --quiet "$SERVICE" || die "$SERVICE is not running (use a plain restart release instead)"
points_at "$PORT" || die "$SITE_REAL does not point at 127.0.0.1:$PORT (a run stopped half-way? $0 --recover)"
if points_at "$BRIDGE_PORT"; then die "$SITE_REAL already uses 127.0.0.1:$BRIDGE_PORT (a run stopped half-way? $0 --recover)"; fi
other=$(others_using "$BRIDGE_PORT"); [ -z "$other" ] || die "port $BRIDGE_PORT is used by another nginx site: $other"
if listening "$BRIDGE_PORT"; then die "something already listens on $BRIDGE_PORT"; fi
if systemctl is-active --quiet "$BRIDGE"; then die "$BRIDGE is running (a run stopped half-way? $0 --recover)"; fi
nginx -t -q || die "nginx -t fails before any change: fix nginx first"
health "$PORT" >/dev/null || die "$SERVICE does not answer on :$PORT"
EXEC=$(systemctl show -p ExecStart --value "$SERVICE" | sed -n 's/.*argv\[\]=\([^;]*\) ;.*/\1/p' | head -1 | sed 's/ *$//')
[ -n "$EXEC" ] || EXEC="/usr/bin/python3 server.py"
if systemctl cat "$SERVICE" | grep -Eq '^Exec(StartPre|StartPost|Stop)='; then log "  note: $SERVICE has ExecStartPre/Post/Stop lines; the bridge runs them too"; fi
OLD=$(readlink -f "$APP/current")
log "  live: $OLD ($(release_version "$OLD")) on :$PORT; :$BRIDGE_PORT is free; ExecStart: $EXEC"
if [ "$MODE" = check ]; then log "check OK (nothing changed)"; exit 0; fi

# ---- the release directory ---------------------------------------------------------------------------
if [ "$MODE" = zip ]; then
  log "== unpack $ZIP"
  TMP=$(mktemp -d)
  python3 -m zipfile -e "$ZIP" "$TMP"
  top=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d)
  if [ "$(printf '%s\n' "$top" | wc -l)" != 1 ] || [ ! -f "$top/server.py" ]; then rm -rf "$TMP"; die "the zip must hold one directory with server.py"; fi
  VER=$(release_version "$top"); [ -n "$VER" ] || { rm -rf "$TMP"; die "no __version__ in the zip"; }
  REL="$APP/releases/$VER-$(date +%Y%m%d%H%M%S)"
  mv "$top" "$REL"; rmdir "$TMP"
  rm -rf "$REL/artifacts" "$REL/tests"
  chown -R root:root "$REL"; chmod -R u=rwX,go=rX "$REL"
else
  [ -f "$REL/server.py" ] || die "$REL is not a release directory"
  case "$REL" in "$APP"/releases/*) ;; *) die "$REL is not under $APP/releases";; esac
  touch "$REL"  # the newest: never pruned below
fi
VER=$(release_version "$REL")
log "  new: $REL ($VER)"

STAGE=bridge
on_exit(){
  local code=$?
  [ "$STAGE" = done ] && return
  log "!! stopped at stage '$STAGE' (exit $code)"
  if points_at "$PORT"; then       # players never left, or are back on, the canonical unit
    stop_bridge
    log "!! players are on $SERVICE (:$PORT, $(readlink -f "$APP/current")); the bridge is stopped"
  else
    log "!! players are on $BRIDGE (:$BRIDGE_PORT, $REL). Once $SERVICE answers on :$PORT: $0 --recover"
    log "!! (a reboot now would leave nginx on :$BRIDGE_PORT with nothing there: recover first). docs/DEPLOY_ROLLING.md"
  fi
}
trap on_exit EXIT

# ---- 1. the bridge: the new release on BRIDGE_PORT -----------------------------------------------------
log "== 1/4 start $BRIDGE (the new release) on :$BRIDGE_PORT"
{
  echo "# Generated by deploy/rolling_release.sh at $(date -Is): $SERVICE (unit + drop-ins), then the bridge overrides."
  systemctl cat "$SERVICE"
  echo
  echo "[Unit]"
  echo "Description=Pho Co Chuyen bridge for a rolling release (:$BRIDGE_PORT)"
  echo "[Service]"
  echo "WorkingDirectory=$REL"
  echo "ExecStart="
  # env(1) runs after systemd has set the environment, so these win over EnvironmentFile= and Environment=.
  echo "ExecStart=/usr/bin/env PG_POOL=$BRIDGE_PG_POOL PG_POOL_MAX=$BRIDGE_PG_POOL_MAX PG_APPLICATION_NAME=$BRIDGE $EXEC --port $BRIDGE_PORT"
  echo "Restart=always"
  if [ -n "$BRIDGE_MEMORY_MAX" ]; then echo "MemoryMax=$BRIDGE_MEMORY_MAX"; fi
} > "$UNIT_FILE"
systemctl daemon-reload
systemctl start "$BRIDGE"
wait_health "$BRIDGE_PORT" "$VER" || { journalctl -u "$BRIDGE" --since "-3min" --no-pager | tail -20; die "$BRIDGE did not become healthy on $VER"; }

# ---- 2. players -> bridge ----------------------------------------------------------------------------
log "== 2/4 nginx -> the bridge; drain :$PORT"
switch_upstream "$PORT" "$BRIDGE_PORT"
ln -sfn "$REL" "$APP/current"      # nginx serves un-versioned static files from current/public
drain "$PORT"

# ---- 3. the canonical unit restarts on the new release, with no traffic on it -----------------------------
log "== 3/4 restart $SERVICE on the new release (players are on the bridge)"
old_nginx_gone
systemctl restart "$SERVICE"
wait_health "$PORT" "$VER" || { journalctl -u "$SERVICE" --since "-3min" --no-pager | tail -20; die "$SERVICE did not come back on $VER"; }

# ---- 4. players -> canonical unit; the bridge drains and stops --------------------------------------------
log "== 4/4 nginx -> :$PORT; drain and stop the bridge"
switch_upstream "$BRIDGE_PORT" "$PORT"
drain "$BRIDGE_PORT"
old_nginx_gone
stop_bridge
STAGE=done

# ---- checks and housekeeping -----------------------------------------------------------------------------
log "== checks"
systemctl is-active "$SERVICE"
health "$PORT"; echo
if [ -n "$SMOKE_URL" ]; then
  host=$(sed -E 's#^https?://([^/:]+).*#\1#' <<<"$SMOKE_URL"); case "$SMOKE_URL" in https*) p=443;; *) p=80;; esac
  curl -fsS -m 10 --resolve "$host:$p:127.0.0.1" -o /dev/null -w "  via nginx: %{http_code} %{time_total}s\n" "$SMOKE_URL" || log "  WARNING: $SMOKE_URL did not answer 200"
fi
journalctl -u "$SERVICE" --since "-2min" --no-pager | tail -6 || true
log "current -> $(readlink -f "$APP/current") (previous: $OLD)"
ls -dt "$APP"/releases/* | tail -n +$((KEEP+1)) | while read -r d; do
  d=$(readlink -f "$d"); if [ "$d" != "$REL" ] && [ "$d" != "$OLD" ]; then rm -rf "$d"; fi
done
ls "$APP/releases"
if [ "$MODE" = zip ] && [ "$ZIP" = /tmp/mnl-release.zip ]; then rm -f "$ZIP"; fi
log "done: $VER is live, no restart gap (rollback: $0 --to $OLD)"
