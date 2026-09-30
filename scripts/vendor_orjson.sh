#!/bin/sh
# Vendor orjson, the optional fast JSON of game/fastjson.py, for the production server
# (Linux x86_64, CPython 3.12, PYTHONPATH=/opt/mot-ngay-lam-nghe/shared/pyvendor).
# The game runs without it (standard-library json, slower); with it, a save parses ~2x
# faster and writes ~4x faster, with byte-identical stored text (tests/test_fastjson.py).
#
#   scripts/vendor_orjson.sh download <wheel dir> [version]     on any machine with pip + internet:
#                                                               fetch the manylinux x86_64 cp312 wheel
#   scripts/vendor_orjson.sh install <wheel file> <vendor dir>  unpack it (replaces an older orjson)
#   scripts/vendor_orjson.sh <vendor dir> [version]             both at once
#
# On the server, then restart the service (a rolling release picks it up too); the start-up
# line does not change, check with:
#   PYTHONPATH=<vendor dir> python3 -c 'import orjson, game.fastjson as f; print(orjson.__version__, f.FAST)'
# To go back to the standard library: remove <vendor dir>/orjson and <vendor dir>/orjson-*.dist-info.
set -eu

VERSION_DEFAULT=3.12.0     # tested with this release (tests/test_fastjson.py, the 0.9.5 suite)
PY=${PYTHON:-python3}

download() {  # <wheel dir> [version] -> prints the wheel path
  mkdir -p "$1"
  "$PY" -m pip download --quiet --no-deps --only-binary=:all: \
    --platform manylinux_2_17_x86_64 --python-version 3.12 --implementation cp --abi cp312 \
    -d "$1" "orjson==${2:-$VERSION_DEFAULT}" >&2
  ls "$1"/orjson-"${2:-$VERSION_DEFAULT}"-cp312-cp312-manylinux*x86_64*.whl | head -n 1
}

install() {  # <wheel file> <vendor dir>
  case "$1" in *cp312-cp312-manylinux*x86_64*.whl) ;; *) echo "not a manylinux x86_64 cp312 orjson wheel: $1" >&2; exit 1;; esac
  mkdir -p "$2"
  rm -rf "$2"/orjson "$2"/orjson-*.dist-info
  "$PY" -m zipfile -e "$1" "$2"
  echo "orjson unpacked into $2 ($(basename "$1"), sha256 $(sha256 "$1"))"
  if [ "$(uname -s)-$(uname -m)" = Linux-x86_64 ] && "$PY" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))'; then
    PYTHONPATH="$2" "$PY" -c 'import orjson; assert orjson.loads(orjson.dumps({"a": [1, 2.5, "Phở"]})) == {"a": [1, 2.5, "Phở"]}; print("import ok: orjson", orjson.__version__)'
  fi
}

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

case "${1:-}" in
  download) [ $# -ge 2 ] || { sed -n '2,15p' "$0"; exit 2; }
            w=$(download "$2" "${3:-}"); echo "$w (sha256 $(sha256 "$w"))";;
  install)  [ $# -eq 3 ] || { sed -n '2,15p' "$0"; exit 2; }
            install "$2" "$3";;
  ""|-h|--help) sed -n '2,15p' "$0"; exit 2;;
  *)        tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
            w=$(download "$tmp" "${2:-}"); install "$w" "$1";;
esac
