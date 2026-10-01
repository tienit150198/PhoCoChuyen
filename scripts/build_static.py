#!/usr/bin/env python3
"""Release build of public/: minified JS and CSS for the release zip (scripts/package.py).

The files in git stay as written (readable, what the tests and a developer's server use); only the
release carries the minified bytes. Nothing else changes: game/webassets.py hashes whatever bytes
public/ holds, so every minified file still gets its own ?v=<hash> URL, import map entry and CAS copy.

- JS: esbuild --minify (whitespace, syntax, local names), --charset=utf8 (Vietnamese text stays UTF-8,
  not \\u escapes), --target=es2022 (never newer syntax than the source already needs: top-level await).
  Per file, never bundled: a deploy that changes one module still changes one URL.
- CSS: whitespace only (comments, indentation); rules are printed as written.
- Checks: every module keeps exactly its static imports (the modulepreload graph), boot.js can still be
  inlined, and a file whose output is not smaller keeps its source bytes.

esbuild is pinned (ESBUILD below): the same source gives the same bytes, so an unchanged file keeps
its URL (and the players' cache) across releases. It runs through npx (node is needed to package,
never on the server). The first release built this way changes every URL once.

    python3 scripts/build_static.py [--out DIR]    report the savings (and write the files to DIR)
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game.webassets import module_imports  # noqa: E402

ESBUILD = "esbuild@0.28.2"
JS_FLAGS = ["--minify", "--charset=utf8", "--target=es2022", "--log-level=warning"]
CSS_FLAGS = ["--minify-whitespace", "--charset=utf8", "--log-level=warning"]
SKIP_DIRS = {"_v", "node_modules"}


class BuildError(RuntimeError):
    pass


def sources(root: Path, suffix: str) -> list[Path]:
    public = root / "public"
    return sorted(p for p in public.rglob(f"*{suffix}")
                  if p.is_file() and not any(part in SKIP_DIRS or part.startswith(".") for part in p.relative_to(public).parts))


def esbuild(files: list[Path], root: Path, flags: list[str]) -> dict[Path, bytes]:
    npx = shutil.which("npx")
    if not npx:
        raise BuildError("npx (node) is needed to minify the release: install node, or package with --no-minify")
    with tempfile.TemporaryDirectory(prefix="mnl-build-") as out:
        # Paths relative to root: esbuild writes <out>/<path under public/>.
        for i in range(0, len(files), 40):   # local Windows packaging: the npx.cmd line limit
            cmd = [npx, "--yes", ESBUILD, "--outbase=public", f"--outdir={out}", *flags, *(str(f.relative_to(root)) for f in files[i:i + 40])]
            run = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            if run.returncode:
                raise BuildError(f"esbuild failed:\n{run.stderr[-4000:]}")
        if run.stderr.strip():
            print(run.stderr.strip()[-2000:], file=sys.stderr)
        result = {}
        for f in files:
            built = Path(out) / f.relative_to(root / "public")
            if not built.is_file():
                raise BuildError(f"esbuild wrote no {built.name}")
            result[f] = built.read_bytes()
        return result


def minify(root: Path = ROOT) -> dict[str, bytes]:
    """{path relative to root (posix): minified bytes} for every public/ JS and CSS file that got smaller."""
    root = Path(root).resolve()
    js, css = sources(root, ".js"), sources(root, ".css")
    out: dict[str, bytes] = {}
    for files, flags in ((js, JS_FLAGS), (css, CSS_FLAGS)):
        if not files:
            continue
        for path, data in esbuild(files, root, flags).items():
            source = path.read_bytes()
            rel = path.relative_to(root).as_posix()
            if path.suffix == ".js":
                before, after = sorted(module_imports(source.decode("utf-8"))), sorted(module_imports(data.decode("utf-8")))
                if before != after:
                    raise BuildError(f"{rel}: static imports changed in the minified copy: {before} != {after}")
                if path.name == "boot.js" and "</script" in data.decode("utf-8").lower():
                    raise BuildError("boot.js: the minified copy can not be inlined (</script)")
            if data.strip() and len(data) < len(source):   # a comment-only file (a retired stylesheet) keeps its bytes
                out[rel] = data
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, help="also write the minified files under this directory (same relative paths)")
    args = ap.parse_args()
    built = minify(ROOT)
    raw = gz = raw_min = gz_min = 0
    for rel, data in built.items():
        src = (ROOT / rel).read_bytes()
        raw += len(src); raw_min += len(data)
        gz += len(gzip.compress(src, 6)); gz_min += len(gzip.compress(data, 6))
        if args.out:
            dest = args.out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    print(json.dumps(dict(files=len(built), raw_kb=[raw // 1024, raw_min // 1024], gzip_kb=[gz // 1024, gz_min // 1024], esbuild=ESBUILD)))


if __name__ == "__main__":
    try:
        main()
    except BuildError as e:
        sys.exit(f"build_static: {e}")
