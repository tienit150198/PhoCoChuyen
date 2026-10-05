#!/usr/bin/env bash
# PostgreSQL 16 for "Phố Có Chuyện" on the shared VPS. Idempotent: run it again at any time.
#
#   sudo bash deploy/pg/install_pg16.sh
#
# - apt postgresql-16 + python3-psycopg (skipped when installed)
# - cluster 16/main on 127.0.0.1 only (its own port: 5432 if free on the host, else 5433).
#   The dk_bike postgres containers are never touched (they publish nothing on the host).
# - tuning in /etc/postgresql/16/main/conf.d/mnl.conf (8 GB RAM shared with other apps, slow disk);
#   reload, or restart postgresql@16-main only when a restart-only setting changed.
# - role mnl + database phocochuyen (collation C: stable byte order), a random password
#   written ONLY to /etc/mot-ngay-lam-nghe/pg.env (root:root 600, read by systemd EnvironmentFile).
#   The password is never printed. An existing pg.env is kept (and its password re-applied).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/common.sh"
need_root

PGVER=16
CLUSTER=main
DBNAME=${DBNAME:-phocochuyen}
ROLE=${ROLE:-mnl}
CONF_DIR=/etc/postgresql/$PGVER/$CLUSTER/conf.d
CONF=$CONF_DIR/mnl.conf

echo "== packages"
missing=()
dpkg -s postgresql-$PGVER >/dev/null 2>&1 || missing+=(postgresql-$PGVER)
dpkg -s python3-psycopg >/dev/null 2>&1 || missing+=(python3-psycopg)
if [ ${#missing[@]} -gt 0 ]; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
else
  echo "   installed: postgresql-$PGVER python3-psycopg ($(dpkg-query -W -f='${Version}' python3-psycopg))"
fi

echo "== cluster $PGVER/$CLUSTER"
if ! pg_lsclusters -h | awk '{print $1"/"$2}' | grep -qx "$PGVER/$CLUSTER"; then
  port=5432
  if ss -Hltn "sport = :5432" | grep -q .; then port=5433; fi
  pg_createcluster "$PGVER" "$CLUSTER" --port "$port" --locale C.UTF-8 -- --lc-collate=C >/dev/null
fi
PORT=$(pg_lsclusters -h | awk -v v="$PGVER" -v c="$CLUSTER" '$1==v && $2==c {print $3}')
echo "   port $PORT"
# Somebody else on this port (a docker-proxy)? Then our cluster would not be reachable: refuse.
if ss -Hltnp "sport = :$PORT" | grep -v postgres | grep -q .; then
  die "port $PORT is used by another program: set a free port in /etc/postgresql/$PGVER/$CLUSTER/postgresql.conf"
fi

echo "== tuning ($CONF)"
mkdir -p "$CONF_DIR"
grep -Eq "^\s*include_dir\s*=\s*'conf.d'" /etc/postgresql/$PGVER/$CLUSTER/postgresql.conf || die "postgresql.conf has no include_dir 'conf.d'"
tmp=$(mktemp)
cat >"$tmp" <<'EOF'
# Phố Có Chuyện (mot-ngay-lam-nghe): managed by deploy/pg/install_pg16.sh. 8 GB RAM shared with other apps.
listen_addresses = 'localhost'
max_connections = 60                    # 4 workers x pool + tools; each backend costs RAM
shared_buffers = 768MB
effective_cache_size = 2GB
work_mem = 8MB
maintenance_work_mem = 256MB
huge_pages = try
# Data safety: every commit is flushed (a crash never loses a committed save).
synchronous_commit = on
fsync = on
full_page_writes = on
wal_compression = lz4                   # saves are 100 KB-1.3 MB of JSON: much less WAL on a slow disk
default_toast_compression = lz4
wal_buffers = 16MB
# Slow disk: few, spread checkpoints.
checkpoint_timeout = 15min
checkpoint_completion_target = 0.9
max_wal_size = 2GB
min_wal_size = 256MB
effective_io_concurrency = 2
random_page_cost = 2.0
# Every command rewrites a whole save: keep autovacuum ahead of the dead rows.
autovacuum_naptime = 30s
autovacuum_vacuum_cost_limit = 1000
# A transaction left open pins old row versions (long-running readers retain old row versions).
idle_in_transaction_session_timeout = 5min
log_min_duration_statement = 1000
# Never log bind parameters: they are whole saves (100 KB-1.3 MB of player data) -> huge logs, more IO, privacy.
log_parameter_max_length = 0
log_parameter_max_length_on_error = 0
log_checkpoints = on
log_lock_waits = on
EOF
changed=0
if ! cmp -s "$tmp" "$CONF"; then install -m 644 -o postgres -g postgres "$tmp" "$CONF"; changed=1; fi
rm -f "$tmp"

svc="postgresql@$PGVER-$CLUSTER"
systemctl enable --now "$svc" >/dev/null 2>&1 || true
if [ $changed = 1 ]; then
  # restart only if a restart-only setting differs from the running value
  need_restart=$(runuser -u postgres -- psql -p "$PORT" -XAtc "SELECT count(*) FROM pg_settings WHERE pending_restart" 2>/dev/null || echo 0)
  systemctl reload "$svc"
  sleep 1
  need_restart=$(runuser -u postgres -- psql -p "$PORT" -XAtc "SELECT count(*) FROM pg_settings WHERE pending_restart")
  if [ "$need_restart" != 0 ]; then
    echo "   restart needed (shared_buffers/max_connections/...): restarting $svc only"
    systemctl restart "$svc"
  else
    echo "   reloaded"
  fi
else
  echo "   unchanged"
fi
for i in $(seq 1 30); do runuser -u postgres -- pg_isready -q -p "$PORT" && break; sleep 1; done
runuser -u postgres -- pg_isready -q -p "$PORT" || die "PostgreSQL does not answer on port $PORT"

echo "== role $ROLE, database $DBNAME, $PG_ENV"
install -d -m 755 "$ETC"
psql_pg() { runuser -u postgres -- psql -p "$PORT" -X -v ON_ERROR_STOP=1 -q "$@"; }
if [ -s "$PG_ENV" ] && grep -q '^DATABASE_URL=postgresql://' "$PG_ENV"; then
  PW=$(sed -n 's#^DATABASE_URL=postgresql://[^:]*:\([^@]*\)@.*#\1#p' "$PG_ENV")
  [ -n "$PW" ] || die "$PG_ENV has no password in DATABASE_URL"
  echo "   keeping the password of the existing $PG_ENV"
else
  PW=$(python3 -c 'import secrets;print(secrets.token_hex(24))')
  umask 077
  printf 'DATABASE_URL=postgresql://%s:%s@127.0.0.1:%s/%s\n' "$ROLE" "$PW" "$PORT" "$DBNAME" >"$PG_ENV.new"
  chown root:root "$PG_ENV.new"; chmod 600 "$PG_ENV.new"; mv -f "$PG_ENV.new" "$PG_ENV"
  umask 022
  echo "   wrote a new password to $PG_ENV (600 root)"
fi
# SQL on stdin: the password never shows in a process list. psql's :'pw' quotes it.
psql_pg -v pw="$PW" -v role="$ROLE" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'role') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'role', :'pw') \gexec
SQL
unset PW
psql_pg -v db="$DBNAME" -v role="$ROLE" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I TEMPLATE template0 ENCODING ''UTF8'' LC_COLLATE ''C'' LC_CTYPE ''C.UTF-8''', :'db', :'role')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db') \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db') \gexec
SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'db', :'role') \gexec
SQL
psql_pg -d "$DBNAME" -v role="$ROLE" <<'SQL'
SELECT format('ALTER SCHEMA public OWNER TO %I', :'role') \gexec
SQL
coll=$(runuser -u postgres -- psql -p "$PORT" -XAtc "SELECT datcollate FROM pg_database WHERE datname='$DBNAME'")
[ "$coll" = C ] || echo "   NOTE: $DBNAME has collation $coll (game columns use COLLATE \"C\" anyway)"

echo "== connection test as $RUN_USER"
( set -a; . "$PG_ENV"; set +a
  runuser -u "$RUN_USER" -- python3 -c 'import os,psycopg
c=psycopg.connect(os.environ["DATABASE_URL"]);v=c.execute("select current_setting($$server_version$$),current_user,current_database()").fetchone();c.close()
print("   ok: PostgreSQL",v[0],"as",v[1],"db",v[2],"psycopg",psycopg.__version__)' )
echo "== done (backups: see deploy/pg/pg_backup.sh + mnl-pg-backup.timer)"
