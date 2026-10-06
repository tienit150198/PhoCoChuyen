#!/usr/bin/env python3
"""Build a deployable release zip from the LIVE release plus a git change, instead of from scratch.

    python3 scripts/release_from_live.py --live DIR --ref REF --out ZIP [--base live-1.7.15]
    python3 scripts/release_from_live.py --live DIR --check-base [--base live-1.7.15]

DIR is the live release directory (/opt/mot-ngay-lam-nghe/current, or a copy of it:
`ssh root@host 'tar cf - -C /opt/mot-ngay-lam-nghe/current --exclude=__pycache__ .' | tar xf - -C DIR`).
BASE is the commit that describes DIR (docs/LIVE_BASE.md); REF is what to ship.

The zip is the live release, file for file. It keeps the live release's minified front end, so an
unchanged JS/CSS file keeps its bytes, its ?v= URL and the players' cache. Only the files that differ
between BASE and REF change:
  * added/modified: REF's bytes. A public/ .js/.css file is minified the way scripts/package.py does it
    (scripts/build_static.py of REF: esbuild, same flags, same static-import and boot.js checks, source
    kept when the minified copy is not smaller);
  * deleted: left out;
  * files scripts/package.py never ships (storage/, i18n/todo/, *.sqlite, .env …) are skipped.
MANIFEST.json is the live one with those entries rewritten, plus the new version (REF's
game/__init__.py) and a `release_from_live` block saying what was built from what.

It refuses when:
  * a file of DIR does not hash to its MANIFEST entry (an incomplete or edited copy);
  * BASE does not describe DIR. Each MANIFEST entry must equal BASE's file, or be a public/ JS/CSS file
    whose BASE source minifies to exactly the shipped bytes, or be listed as minified-only;
  * a changed file is listed as minified-only (no source) in BASE's docs/LIVE_BASE.md.

The zip has the layout scripts/package.py writes and deploy/rolling_release.sh expects: one top
directory `mot-ngay-lam-nghe/` holding server.py, game/__init__.py with __version__, and MANIFEST.json.
After writing it, the script reopens the zip and checks every entry against the new MANIFEST, as
scripts/verify_package.py does. Run the task-compatibility gate yourself before deploying:
`python3 scripts/check_task_compat.py <BASE tree> <REF tree>`.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

TOP = 'mot-ngay-lam-nghe'
DEFAULT_BASE = 'live-1.7.15'
MINI_BEGIN, MINI_END = '<!-- minified-only:begin -->', '<!-- minified-only:end -->'


class Refuse(SystemExit):
    def __init__(self, msg: str):
        super().__init__(f'release_from_live: REFUSED: {msg}')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str, binary: bool = False):
    run = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if run.returncode:
        raise SystemExit(f'git {" ".join(args)}: {run.stderr.decode(errors="replace").strip()}')
    return run.stdout if binary else run.stdout.decode()


def export(repo: Path, commit: str, dest: Path) -> Path:
    """The commit's tree, as files (exec bits kept): build_static and game.webassets run from it."""
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(git(repo, 'archive', '--format=tar', commit, binary=True))) as tar:
        tar.extractall(dest, filter='tar')
    return dest


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_web_asset(rel: str) -> bool:
    p = PurePosixPath(rel)
    return p.parts[0] == 'public' and p.suffix in ('.js', '.css') and \
        not any(part in ('_v', 'node_modules') or part.startswith('.') for part in p.parts[1:])


def packaged(rel: str, package) -> bool:
    """scripts/package.py's file filter (its constants, its inline rules)."""
    p = PurePosixPath(rel)
    if any(part in package.BLOCKED_DIRS for part in p.parts):
        return False
    if p.suffix.lower() in package.BLOCKED_SUFFIXES or p.name in {'.env', '.DS_Store', 'vapid.json'} or rel == 'MANIFEST.json':
        return False
    if p.parts[0] == 'storage' and p.name != '.gitkeep':
        return False
    if 'failure' in p.name and p.name.startswith('browser'):
        return False
    return not p.name.endswith(('-wal', '-shm'))


def minified_only(base_tree: Path) -> dict[str, str]:
    """docs/LIVE_BASE.md: files production ships minified with no source on the branch."""
    doc = base_tree / 'docs/LIVE_BASE.md'
    if not doc.is_file():
        return {}
    text = doc.read_text(encoding='utf-8')
    if MINI_BEGIN not in text:
        return {}
    block = text.split(MINI_BEGIN, 1)[1].split(MINI_END, 1)[0]
    return {m.group(1): m.group(2) for m in re.finditer(r'^\|\s*`([^`]+)`\s*\|\s*`?([0-9a-f]{64})`?\s*\|', block, re.M)}


def minify(build_static, root: Path, rels: list[str]) -> dict[str, bytes]:
    """build_static.minify() for some files only: same esbuild, flags and checks."""
    out: dict[str, bytes] = {}
    for suffix, flags in (('.js', build_static.JS_FLAGS), ('.css', build_static.CSS_FLAGS)):
        files = [root / r for r in rels if r.endswith(suffix)]
        if not files:
            continue
        for path, data in build_static.esbuild(files, root, flags).items():
            source = path.read_bytes()
            rel = path.relative_to(root).as_posix()
            if suffix == '.js':
                before = sorted(build_static.module_imports(source.decode('utf-8')))
                after = sorted(build_static.module_imports(data.decode('utf-8')))
                if before != after:
                    raise Refuse(f'{rel}: static imports changed in the minified copy: {before} != {after}')
                if path.name == 'boot.js' and '</script' in data.decode('utf-8').lower():
                    raise Refuse('boot.js: the minified copy can not be inlined (</script)')
            if data.strip() and len(data) < len(source):
                out[rel] = data
    return out


def read_live(live: Path) -> tuple[dict, dict[str, bytes]]:
    mpath = live / 'MANIFEST.json'
    if not mpath.is_file():
        raise Refuse(f'{live} has no MANIFEST.json')
    manifest = json.loads(mpath.read_text(encoding='utf-8'))
    files, bad = {}, []
    for entry in manifest['files']:
        p = live / entry['path']
        data = p.read_bytes() if p.is_file() else None
        if data is None or sha(data) != entry['sha256']:
            bad.append(entry['path'])
        else:
            files[entry['path']] = data
    if bad:
        raise Refuse(f'{len(bad)} live file(s) missing or not matching MANIFEST (an incomplete or edited copy?): {bad[:10]}')
    return manifest, files


def check_base(manifest: dict, live_files: dict[str, bytes], base_tree: Path, build_static, no_source: dict[str, str]):
    """BASE must describe the live release: equal bytes, or a source that minifies to them."""
    same, need_min, bad = 0, [], []
    for entry in manifest['files']:
        rel, want = entry['path'], entry['sha256']
        src = base_tree / rel
        if rel in no_source:
            if no_source[rel] != want:
                bad.append(f'{rel} (listed as minified-only with another sha256)')
            continue
        if not src.is_file():
            bad.append(f'{rel} (not in BASE)')
        elif sha(src.read_bytes()) == want:
            same += 1
        elif is_web_asset(rel):
            need_min.append(rel)
        else:
            bad.append(rel)
    reproduced = []
    if need_min:
        built = minify(build_static, base_tree, need_min)
        for rel in need_min:
            if rel in built and sha(built[rel]) == sha(live_files[rel]):
                reproduced.append(rel)
            else:
                bad.append(f'{rel} (BASE source does not minify to the shipped bytes)')
    if bad:
        raise Refuse(f'BASE does not describe this live release; {len(bad)} file(s): {bad[:12]}')
    return dict(identical=same, minified_reproduced=len(reproduced), minified_only=len(no_source))


def sort_key(rel: str):
    return PurePosixPath(rel).parts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--live', type=Path, required=True, help='the live release directory (or a copy)')
    ap.add_argument('--base', default=DEFAULT_BASE, help=f'the commit that describes the live release (default {DEFAULT_BASE})')
    ap.add_argument('--ref', help='the commit to ship')
    ap.add_argument('--out', type=Path, help='the release zip to write')
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1], help='the git repository')
    ap.add_argument('--check-base', action='store_true', help='only check that BASE describes the live release')
    args = ap.parse_args(argv)
    if not args.check_base and not (args.ref and args.out):
        ap.error('--ref and --out are needed (or --check-base)')
    repo, live = args.repo.resolve(), args.live.resolve()
    base = git(repo, 'rev-parse', '--verify', f'{args.base}^{{commit}}').strip()
    ref = git(repo, 'rev-parse', '--verify', f'{args.ref}^{{commit}}').strip() if args.ref else None

    t0 = time.time()
    manifest, live_files = read_live(live)
    with tempfile.TemporaryDirectory(prefix='mnl-from-live-') as tmp:
        tmp = Path(tmp)
        base_tree = export(repo, base, tmp / 'base')
        base_build = load_module(base_tree / 'scripts/build_static.py', 'build_static_base')
        no_source = minified_only(base_tree)
        base_report = check_base(manifest, live_files, base_tree, base_build, no_source)
        print(f'base {args.base} ({base[:10]}) describes {live.name}: {base_report}', file=sys.stderr)
        if args.check_base:
            print(json.dumps(dict(live=str(live), base=base, **base_report)))
            return 0

        ref_tree = export(repo, ref, tmp / 'ref')
        sys.modules.pop('game', None)
        sys.modules.pop('game.webassets', None)
        ref_build = load_module(ref_tree / 'scripts/build_static.py', 'build_static_ref')
        package = load_module(ref_tree / 'scripts/package.py', 'package_ref')

        changed, deleted, skipped = [], [], []
        status = git(repo, 'diff', '--name-status', '--no-renames', '-z', base, ref).split('\0')
        for code, rel in zip(status[0::2], status[1::2]):
            if not rel:
                continue
            if not packaged(rel, package):
                skipped.append(rel)
            elif code == 'D':
                deleted.append(rel)
            else:
                changed.append(rel)
        blocked = sorted(set(changed + deleted) & set(no_source))
        if blocked:
            raise Refuse(f'changed file(s) shipped minified with no source on {args.base}: {blocked} (docs/LIVE_BASE.md)')
        for rel in changed:
            if (ref_tree / rel).is_symlink() or not (ref_tree / rel).is_file():
                raise Refuse(f'{rel} is not a regular file in REF')
        built = minify(ref_build, ref_tree, [r for r in changed if is_web_asset(r)])

        version = re.search(r'^__version__\s*=\s*"([^"]+)"', (ref_tree / 'game/__init__.py').read_text(encoding='utf-8'), re.M).group(1)
        now = datetime.datetime.now(datetime.timezone.utc)
        content: dict[str, bytes] = {rel: data for rel, data in live_files.items() if rel not in deleted}
        modes: dict[str, int] = {rel: (live / rel).stat().st_mode & 0o777 for rel in content}
        for rel in changed:
            content[rel] = built.get(rel) or (ref_tree / rel).read_bytes()
            modes[rel] = (ref_tree / rel).stat().st_mode & 0o777
        live_manifest_sha = sha((live / 'MANIFEST.json').read_bytes())
        new_manifest = {k: v for k, v in manifest.items() if k != 'files'}
        new_manifest.update(version=version, created_at_utc=now.isoformat(),
                            minified=int(manifest.get('minified') or 0) + len(built))
        new_manifest['release_from_live'] = dict(
            live_release=live.name, live_version=manifest.get('version'), live_manifest_sha256=live_manifest_sha,
            base=base, ref=ref, changed=sorted(changed, key=sort_key), deleted=sorted(deleted, key=sort_key),
            minified=sorted(built, key=sort_key))
        paths = sorted(content, key=sort_key)
        new_manifest['files'] = [dict(path=rel, bytes=len(content[rel]), sha256=sha(content[rel])) for rel in paths]
        mbytes = json.dumps(new_manifest, ensure_ascii=False, indent=2).encode('utf-8')

        args.out.parent.mkdir(parents=True, exist_ok=True)
        stamp = now.astimezone().timetuple()[:6]
        with zipfile.ZipFile(args.out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
            for rel in [*paths, 'MANIFEST.json']:
                info = zipfile.ZipInfo(f'{TOP}/{rel}', date_time=stamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = ((0o100000 | modes.get(rel, 0o644)) & 0xFFFF) << 16
                out.writestr(info, mbytes if rel == 'MANIFEST.json' else content[rel], compresslevel=9)

    verify_zip(args.out, version)
    report = dict(zip=str(args.out), version=version, live=live.name, base=base, ref=ref, files=len(paths) + 1,
                  changed=len(changed), deleted=len(deleted), minified=len(built), skipped=skipped,
                  bytes=args.out.stat().st_size, sha256=sha(args.out.read_bytes()), seconds=round(time.time() - t0, 1))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for rel in sorted(changed, key=sort_key):
        print(f'  {"M" if rel in live_files else "A"} {rel}{"  (minified)" if rel in built else ""}', file=sys.stderr)
    for rel in sorted(deleted, key=sort_key):
        print(f'  D {rel}', file=sys.stderr)
    print('next: python3 scripts/check_task_compat.py <BASE tree> <REF tree> must print OK before deploying', file=sys.stderr)
    return 0


def verify_zip(path: Path, version: str):
    """What deploy/rolling_release.sh and scripts/verify_package.py rely on."""
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f'corrupt zip member {bad}')
        names = z.namelist()
        if {n.split('/', 1)[0] for n in names} != {TOP} or any('..' in PurePosixPath(n).parts or n.startswith('/') for n in names):
            raise SystemExit('zip layout: every entry must be under one safe mot-ngay-lam-nghe/ directory')
        if f'{TOP}/server.py' not in names:
            raise SystemExit('zip has no server.py')
        init = z.read(f'{TOP}/game/__init__.py').decode('utf-8')
        if re.search(r'^__version__ *= *"(.*)"', init, re.M).group(1) != version:
            raise SystemExit('zip version mismatch')
        manifest = json.loads(z.read(f'{TOP}/MANIFEST.json'))
        listed = {e['path'] for e in manifest['files']}
        if listed | {'MANIFEST.json'} != {n[len(TOP) + 1:] for n in names if not n.endswith('/')}:
            raise SystemExit('zip entries and MANIFEST differ')
        for e in manifest['files']:
            data = z.read(f'{TOP}/{e["path"]}')
            if sha(data) != e['sha256'] or len(data) != e['bytes']:
                raise SystemExit(f'hash mismatch in zip: {e["path"]}')


if __name__ == '__main__':
    sys.exit(main())
