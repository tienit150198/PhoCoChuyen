#!/usr/bin/env python3
"""Loads on a weak network (dev tool, needs `pip install playwright` + chromium).

01/10: 163 "Cannot read properties of undefined (reading 'filter')" promise rejections a day, counted on the loading
screen. A returning player whose workplace's code or data part failed to come (the game opens anyway) got the
customer-care view for their own workplace's task (app.js jobView → supportJob: `t.evidence.filter`), thrown from
the async paths that open the job sheet (a scene tap, "Nhận thêm", ensureCareerUI) before telemetry.js was in.

Starts a game server (story mode, SQLite) on --tree (default: this checkout; give an unzipped release or a
scripts/build_static.py --out tree to test the minified files) and checks, each in a fresh phone browser (390×844):
  * part: a returning restaurant player; the workplace's data part fails three times (500) and its workbench
    module once: the job sheet shows a skeleton (never another workplace's view), then the workbench by itself;
  * slow: cold loads on DevTools "Slow 4G" + 4× CPU (a new player, a returning one): the first frame comes, and
    the first taps work;
  * reload: a reload in the middle of a cold load.
Fails on page errors, unhandled rejections, console errors or HTTP 5xx (other than the ones it makes up).

  python scripts/browser_weak_load.py [--tree DIR] [--only part,slow,reload]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOW4G = dict(offline=False, latency=562.5, downloadThroughput=180000, uploadThroughput=84375)
HOOK = """(()=>{window.__errs=[];
addEventListener('unhandledrejection',e=>{const r=e.reason;window.__errs.push('promise: '+String(r&&r.message||r)+' '+String(r&&r.stack||'').split('\\n').slice(1,4).join(' '));});
})();"""
CMD = """async ([action,payload,career])=>{
  const st=await fetch('/api/state').then(r=>r.json());
  const csrf=(await fetch('/api/bootstrap?lite=1').then(r=>r.json())).csrf;
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:career||st.state.current,action,payload})});
  return r.status;
}"""
OPEN_JOB = """()=>{const vis=e=>e&&!e.disabled&&e.getBoundingClientRect().width>0;
  const b=[...document.querySelectorAll('[data-action="job"],[data-action="nextJob"],[data-action="shelf"]')].find(vis);
  if(b){b.click();return true;}return false;}"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server(tree: Path, tmp: str):
    port = free_port()
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL', 'LIVE_URL'):
        env.pop(k, None)
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--db', os.path.join(tmp, 'g.sqlite3')], cwd=tree, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f'http://127.0.0.1:{port}'
    end = time.time() + 60
    while True:
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:  # noqa: BLE001
            if p.poll() is not None or time.time() > end:
                raise SystemExit('the game server did not start')
            time.sleep(0.15)
    try:
        yield base
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)


class Phone:
    """One fresh browser context with its error log."""
    def __init__(self, pw, base: str):
        self.pw, self.base, self.errors, self.allowed = pw, base, [], 0

    async def __aenter__(self):
        self.browser = await self.pw.chromium.launch()
        self.ctx = await self.browser.new_context(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True, locale='vi-VN')
        self.page = p = await self.ctx.new_page()
        p.on('pageerror', lambda e: self.errors.append(f'pageerror: {e} {(e.stack or "").splitlines()[1:3]}'))
        p.on('console', lambda m: m.type == 'error' and self.errors.append(f'console: {m.text[:200]}'))
        p.on('response', lambda r: r.status >= 500 and self.errors.append(f'HTTP {r.status} {r.url.split("?")[0]}'))
        await p.add_init_script(HOOK)
        return self

    async def __aexit__(self, *exc):
        await self.browser.close()

    async def returning(self, career='restaurant'):
        """A player who already works at `career` (day 1 open), then leaves the page."""
        p = self.page
        await p.goto(self.base)
        await p.wait_for_selector('#app:not([hidden])', timeout=60000)
        for action, payload, c in (('jr_profile', {'name': 'An', 'gender': 'female'}, None), ('select_career', {}, career), ('start_day', {}, career)):
            assert await p.evaluate(CMD, [action, payload, c]) == 200, action
        await p.goto('about:blank')

    async def throttle(self):
        cdp = await self.ctx.new_cdp_session(self.page)
        await cdp.send('Network.enable')
        await cdp.send('Network.clearBrowserCache')
        await cdp.send('Network.emulateNetworkConditions', SLOW4G)
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})

    async def problems(self) -> list[str]:
        made_up = [e for e in self.errors if not (e.startswith('HTTP 500') or 'status of 500' in e or 'net::ERR_FAILED' in e)]
        return made_up + await self.page.evaluate('window.__errs||[]')


async def part(pw, base) -> list[str]:
    async with Phone(pw, base) as ph:
        await ph.returning('restaurant')
        p = ph.page
        fails = {'part': 3, 'module': 1}

        async def route(r):
            url = r.request.url
            if '&career=restaurant' in url and fails['part'] > 0:
                fails['part'] -= 1
                return await r.fulfill(status=500, body='{"error":"x"}', content_type='application/json')
            if '/js/careers/restaurant.js' in url and fails['module'] > 0:
                fails['module'] -= 1
                return await r.abort('failed')
            await r.continue_()
        await p.route('**/*', route)
        await p.goto(ph.base)
        await p.wait_for_selector('#app:not([hidden])', timeout=60000)
        out = []
        await p.wait_for_function(OPEN_JOB, timeout=10000)
        try:
            await p.wait_for_selector('#sheet[open]', timeout=5000)
        except Exception:  # noqa: BLE001
            out.append('the job sheet did not open')
        first = await p.evaluate("()=>({skel:!!document.querySelector('#sheet[open] .mnl-skel'),job:!!document.querySelector('#sheet[open] .career-job')})")
        if not first['skel']:
            out.append(f'job sheet while the workbench is missing: {first}')
        try:
            await p.wait_for_selector('#sheet[open] .career-job', timeout=40000)
        except Exception:  # noqa: BLE001
            out.append('the workbench never came back by itself')
        print(f'  part: first view {first}, failures left {fails}', flush=True)
        return out + await ph.problems()


async def slow(pw, base) -> list[str]:
    out = []
    for who in ('new', 'returning'):
        async with Phone(pw, base) as ph:
            if who == 'returning':
                await ph.returning('grocery')
            await ph.throttle()
            t0 = time.time()
            await ph.page.goto(base, wait_until='commit')
            await ph.page.wait_for_selector('#app:not([hidden])', timeout=120000)
            frame = time.time() - t0
            for _ in range(6):   # the first taps, while the rest of the page is still on its way
                with contextlib.suppress(Exception):
                    await ph.page.evaluate("()=>{const b=[...document.querySelectorAll('#app [data-action],#sheet[open] [data-action]')].filter(e=>!e.disabled&&e.getBoundingClientRect().width>0&&!/reset|delete|logout/i.test(e.dataset.action));b[0]?.click();}")
                await ph.page.wait_for_timeout(700)
            await ph.page.wait_for_timeout(4000)
            print(f'  slow/{who}: first frame {frame:.1f} s', flush=True)
            out += [f'{who}: {e}' for e in await ph.problems()]
    return out


async def reload(pw, base) -> list[str]:
    async with Phone(pw, base) as ph:
        await ph.returning('restaurant')
        await ph.throttle()
        await ph.page.goto(base, wait_until='commit')
        await ph.page.wait_for_timeout(1500)
        await ph.page.reload(wait_until='commit')
        await ph.page.wait_for_selector('#app:not([hidden])', timeout=120000)
        await ph.page.wait_for_timeout(4000)
        return await ph.problems()


async def main():
    from playwright.async_api import async_playwright
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tree', type=Path, default=ROOT)
    ap.add_argument('--only', default='part,slow,reload')
    args = ap.parse_args()
    bad = {}
    with tempfile.TemporaryDirectory(prefix='mnl-weak-', dir=os.environ.get('TMPDIR')) as tmp, server(args.tree.resolve(), tmp) as base:
        async with async_playwright() as pw:
            for name in args.only.split(','):
                got = await {'part': part, 'slow': slow, 'reload': reload}[name](pw, base)
                print(f'{name}: {"ok" if not got else "FAIL"}', flush=True)
                if got:
                    bad[name] = got
    if bad:
        print(json.dumps(bad, ensure_ascii=False, indent=1))
        raise SystemExit(1)
    print('browser_weak_load: ok')


if __name__ == '__main__':
    asyncio.run(main())
