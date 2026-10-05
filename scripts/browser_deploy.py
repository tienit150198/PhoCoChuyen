#!/usr/bin/env python3
"""Deploy check in a real browser (dev tool, needs playwright + chromium).

Copies the game to a temp dir and serves release v1; a phone browser loads it (filling its cache).
Then v2 is "deployed" (an eagerly imported module and a lazily imported career module change, the
server restarts on the same port and content-addressed store, like the rolling deploy). Checks:
- the tab still open on v1 lazily imports the career module and gets the v1 bytes (no mix), and
  shows the "Đã có phiên bản mới" pill once it learns the server runs v2 while the player is typing;
- brought back with nothing going on, that tab reloads onto v2 by itself;
- a new load gets v2 for every module (nothing stale from the cache), lazily loads v2, no pill;
- no console errors or CSP violations.
usage: python scripts/browser_deploy.py
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from pg_test_support import test_env, test_connect, schema_for

ROOT = Path(__file__).resolve().parents[1]
EAGER, LATE = 'public/js/ui-kit.js', 'public/js/careers/grocery.js'


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def mark(app: Path, version: str):
    for rel, name in ((EAGER, '__eagerMark'), (LATE, '__lateMark')):
        p = app / rel
        src = re.sub(r"\nglobalThis\.__\w+Mark='v\d';\n$", '\n', p.read_text(encoding='utf-8'))
        p.write_text(src + f"\nglobalThis.{name}='{version}';\n", encoding='utf-8')


@contextlib.contextmanager
def serve(app: Path, port: int, db: str, cas: str):
    env = test_env( QUIET='1', PUSH_DISABLED='1', MNL_DEV='1', STATIC_CAS_DIR=cas)
    env.pop('LLM_API_KEY', None)
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--namespace', db], cwd=app, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(600):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    try:
        yield f'http://127.0.0.1:{port}'
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)


async def main() -> int:
    from playwright.async_api import async_playwright
    tmp = Path(tempfile.mkdtemp(prefix='mnl-deploy-'))
    app = tmp / 'app'
    for rel in ('server.py', 'game', 'public', 'reference'):
        src = ROOT / rel
        (shutil.copytree(src, app / rel, ignore=shutil.ignore_patterns('_v', '__pycache__')) if src.is_dir() else (app.mkdir(exist_ok=True), shutil.copy(src, app / rel)))
    db, cas, port = str(tmp / 'g.db'), str(tmp / 'cas'), free_port()
    problems: list[str] = []
    check = lambda ok, what: ok or problems.append(what)
    mark(app, 'v1')
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(str(tmp / 'chrome'), viewport=dict(width=390, height=844), is_mobile=True, has_touch=True)
        errors: list[str] = []
        def watch(page, tag):
            page.on('pageerror', lambda e: errors.append(f'{tag}: {e}'))
            page.on('console', lambda m: m.type == 'error' and errors.append(f'{tag}: {m.text}'))
        with serve(app, port, db, cas) as base:
            a = await ctx.new_page(); watch(a, 'v1 tab')
            await a.goto(base); await a.wait_for_selector('#app:not([hidden])', timeout=60000)
            check(await a.evaluate('()=>globalThis.__eagerMark') == 'v1', 'v1 page did not run v1 code')
            v1 = await a.evaluate("()=>document.querySelector('meta[name=mnl-version]').content")
        mark(app, 'v2')  # the deploy: new files, then the server restarts
        with serve(app, port, db, cas) as base:
            v2 = urllib.request.urlopen(base + '/api/health').headers['X-Game-Version']
            check(v1 != v2, 'version did not change')
            late = await a.evaluate("async()=>{await import('/js/careers/grocery.js');return globalThis.__lateMark;}")
            check(late == 'v1', f'open v1 tab lazily loaded {late!r} (mixed versions)')
            # Back to the tab while typing: nothing reloads, the pill offers it.
            await a.evaluate("()=>{const i=document.createElement('input');i.id='deploy-typing';(document.querySelector('dialog[open]')||document.body).append(i);i.value='chưa gửi';i.focus();}")
            await a.evaluate("()=>document.dispatchEvent(new Event('visibilitychange'))")
            await a.wait_for_selector('.update-pill', timeout=10000)
            pill = await a.inner_text('.update-pill .update-go')
            check('phiên bản mới' in pill, f'pill text {pill!r}')
            # Back to the tab with nothing going on: it reloads onto v2 by itself (update.js autoReload).
            await a.evaluate("()=>document.getElementById('deploy-typing').remove()")
            async with a.expect_navigation(timeout=15000):
                await a.evaluate("()=>document.dispatchEvent(new Event('visibilitychange'))")
            await a.wait_for_selector('#app:not([hidden])', timeout=60000)
            check(await a.evaluate('()=>globalThis.__eagerMark') == 'v2', 'the tab brought back did not reload onto v2')
            check(await a.evaluate("()=>!document.querySelector('.update-pill')"), 'pill still shown after the reload')
            b = await ctx.new_page(); watch(b, 'v2 tab')
            await b.goto(base); await b.wait_for_selector('#app:not([hidden])', timeout=60000)
            check(await b.evaluate('()=>globalThis.__eagerMark') == 'v2', 'new load ran stale v1 code')
            check(await b.evaluate("()=>document.querySelector('meta[name=mnl-version]').content") == v2, 'new page is not v2')
            late = await b.evaluate("async()=>{await import('/js/careers/grocery.js');return globalThis.__lateMark;}")
            check(late == 'v2', f'v2 tab lazily loaded {late!r}')
            imports = await b.evaluate("()=>JSON.parse(document.querySelector('script[type=importmap]').textContent).imports")
            loaded = await b.evaluate("()=>performance.getEntriesByType('resource').map(e=>e.name).filter(u=>/\\/(js|css)\\//.test(u))")
            from game.webassets import content_hash  # noqa: E402  (after the copy exists)
            for url in loaded:
                path, _, v = url.split('://', 1)[1].split('/', 1)[1].partition('?v=')
                if v:
                    check(content_hash((app / 'public' / path).read_bytes()) == v, f'v2 tab loaded a stale /{path}?v={v}')
            check(all(u.split('?v=')[1] == content_hash((app / 'public' / k.lstrip('/')).read_bytes()) for k, u in imports.items()), 'import map names stale bytes')
            await b.wait_for_timeout(500)
            dbg = await b.evaluate("()=>[document.querySelector('.update-pill')?.dataset.version, globalThis.__mnlBoot?.version]")
            check(dbg[0] is None, f'pill shown on an up-to-date page {dbg}')
        await ctx.close()
    problems += [e for e in errors if 'Failed to load resource' not in e]
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'deploy check: v1 {v1} -> v2 {v2}: ' + ('OK' if not problems else f'{len(problems)} problem(s)'))
    for p in problems:
        print('  -', p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    raise SystemExit(asyncio.run(main()))
