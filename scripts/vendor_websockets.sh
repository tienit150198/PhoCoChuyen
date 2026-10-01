#!/bin/sh
# Vendor `websockets`, the WebSocket library of the live service (live/, `python3 -m live`), for the production
# server (CPython 3.12, PYTHONPATH=/opt/mot-ngay-lam-nghe/shared/pyvendor), the same way as orjson
# (scripts/vendor_orjson.sh). The game server does not use it; only mnl-live.service does.
#
#   scripts/vendor_websockets.sh download <wheel dir> [version]     on any machine with pip + internet
#   scripts/vendor_websockets.sh install <wheel file> <vendor dir>  unpack it (replaces an older websockets)
#   scripts/vendor_websockets.sh <vendor dir> [version]             both at once
#
# 17.1 ships as one pure-Python wheel (py3-none-any; the optional C speed-up is not needed at our frame
# sizes). Its sha256 is checked. Afterwards: systemctl restart mnl-live. Check with:
#   PYTHONPATH=<vendor dir> python3 -c 'import websockets; print(websockets.__version__)'
# To remove it: rm -rf <vendor dir>/websockets <vendor dir>/websockets-*.dist-info
set -eu

VERSION_DEFAULT=17.1     # tested with this release (tests/test_live_*.py, scripts/live_load.py)
SHA256_17_1=f221081107b8c48184d99f7019604486376e7ef826037e70aad6b02540732c23
PY=${PYTHON:-python3}

download() {  # <wheel dir> [version] -> prints the wheel path
  mkdir -p "$1"
  "$PY" -m pip download --quiet --no-deps --only-binary=:all: \
    --platform manylinux_2_17_x86_64 --python-version 3.12 --implementation cp --abi cp312 \
    -d "$1" "websockets==${2:-$VERSION_DEFAULT}" >&2
  ls "$1"/websockets-"${2:-$VERSION_DEFAULT}"-*.whl | head -n 1
}

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

install() {  # <wheel file> <vendor dir>
  case "$1" in *websockets-*.whl) ;; *) echo "not a websockets wheel: $1" >&2; exit 1;; esac
  case "$(basename "$1")" in websockets-17.1-py3-none-any.whl)
    [ "$(sha256 "$1")" = "$SHA256_17_1" ] || { echo "sha256 mismatch for $1" >&2; exit 1; };; esac
  mkdir -p "$2"
  rm -rf "$2"/websockets "$2"/websockets-*.dist-info
  "$PY" -m zipfile -e "$1" "$2"
  echo "websockets unpacked into $2 ($(basename "$1"), sha256 $(sha256 "$1"))"
  if "$PY" -c 'import sys; sys.exit(sys.version_info[:2] < (3, 11))'; then
    PYTHONPATH="$2" "$PY" -c 'import websockets; from websockets.asyncio.server import serve; print("import ok: websockets", websockets.__version__)'
  fi
}

case "${1:-}" in
  download) [ $# -ge 2 ] || { sed -n '2,16p' "$0"; exit 2; }
            w=$(download "$2" "${3:-}"); echo "$w (sha256 $(sha256 "$w"))";;
  install)  [ $# -eq 3 ] || { sed -n '2,16p' "$0"; exit 2; }
            install "$2" "$3";;
  ""|-h|--help) sed -n '2,16p' "$0"; exit 2;;
  *)        tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
            w=$(download "$tmp" "${2:-}"); install "$w" "$1";;
esac
