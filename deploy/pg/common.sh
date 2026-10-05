# Shared PostgreSQL installation settings. No file database or migration fallback.
SERVICE=${SERVICE:-mot-ngay-lam-nghe}
RUN_USER=${RUN_USER:-mnl}
DATA=${DATA:-/var/lib/mot-ngay-lam-nghe}
ETC=${ETC:-/etc/mot-ngay-lam-nghe}
PG_ENV=${PG_ENV:-$ETC/pg.env}
die() { echo "ERROR: $*" >&2; exit 1; }
need_root() { [ "$(id -u)" = 0 ] || die "run as root (sudo)"; }
