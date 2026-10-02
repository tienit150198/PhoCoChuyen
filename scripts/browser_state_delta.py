#!/usr/bin/env python3
"""Smaller state answers in a real browser (dev tool, needs `pip install playwright` + chromium).

A story server like production and a 390×844 phone, the page opened with ?deltacheck=1 (public/js/api.js: every
adopted state is frozen, so a change in place throws, and each command's state is compared with GET /api/state).
A new player goes through the intro and serves the first milk-tea customer by pressing what the game highlights
(scripts/browser_first_day.py), then more customers through the page's own api.command (one sensible step at a time,
game/boba.py next_move); after every press and step the page's state must equal a fresh GET /api/state. On the way:

* an old server: for a few presses the requests lose X-Game-Delta and `known` (what a server from before
  answers: the whole state), then the header is back;
* another tab acts on the same save (the page then meets a 409 and takes the whole state);
* the server restarts (same database and port);
* a save is imported in another tab (the page's parts refer to the old save).

It fails on any difference, console error or exception, or when no answer used references at all.

  python scripts/browser_state_delta.py [--steps 40] [--engine chromium|webkit]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT))
from browser_first_day import CMD, PICK  # noqa: E402  (the same "press what glows" loop)
from game import boba  # noqa: E402

IMPORT = """async ()=>{const e=await fetch('/api/save/export').then(r=>r.json());
  const st=await fetch('/api/state').then(r=>r.json());const csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf;
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:null,action:'import_save',payload:{save:e}})});
  return {status:r.status};}"""

# The page's state vs a fresh GET /api/state (the fair's clock aside: the second it was read).
SAME = """async ()=>{
  const canon=x=>Array.isArray(x)?`[${x.map(canon).join(',')}]`:x&&typeof x==='object'?`{${Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')}}`:JSON.stringify(x);
  // The fair's clock and its rotating stall modes (game/fair.py public()) move with the minute, not with the save.
  const plain=s=>s?.fair?{...s,fair:{...s.fair,now:0,ganh:s.fair.ganh&&{...s.fair.ganh,modes:0}}}:s;
  for(let i=0;i<20;i++){
    const api=globalThis.__mnlApi;if(!api)return {error:'no __mnlApi (deltacheck off?)'};
    const whole=await fetch('/api/state',{cache:'no-store'}).then(r=>r.json());
    if(whole.revision!==api.revision){await new Promise(r=>setTimeout(r,150));continue;}
    const a=canon(plain(api.state)),b=canon(plain(whole.state));
    if(a===b)return {ok:true,revision:api.revision,held:api.held.parts.size};
    let i0=0;while(a[i0]===b[i0])i0++;
    return {ok:false,revision:api.revision,at:a.slice(Math.max(0,i0-120),i0+80),want:b.slice(Math.max(0,i0-120),i0+80)};
  }
  return {error:'revision never settled'};
}"""


class _Skip(list):
    def __init__(self, items, text):
        super().__init__(items)
        self.text = text

    def append(self, item):
        if self.text not in item:
            super().append(item)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Server:
    """Like production: the story is on, no AI key, no push; restartable on the same database and port."""

    def __init__(self):
        self.port = free_port()
        self.tmp = tempfile.mkdtemp(prefix='mnl-delta-')
        self.base = f'http://127.0.0.1:{self.port}'
        self.p = None

    def start(self):
        env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
        for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL', 'DATABASE_URL'):
            env.pop(k, None)
        self.p = subprocess.Popen([sys.executable, 'server.py', '--port', str(self.port), '--db', os.path.join(self.tmp, 'g.sqlite3')],
                                  cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(600):
            try:
                urllib.request.urlopen(self.base + '/api/health', timeout=1)
                return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError('server did not start')

    def stop(self):
        if self.p:
            self.p.terminate()
            with contextlib.suppress(Exception):
                self.p.wait(10)
            self.p = None

    def close(self):
        self.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)


async def run(srv: Server, steps: int, engine: str) -> dict:
    from playwright.async_api import async_playwright
    out = dict(problems=[], checks=0, answers=0, with_refs=0, old=0)
    old_server = [False]
    async with async_playwright() as pw:
        browser = await getattr(pw, engine).launch()
        ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=1,
                                        service_workers='block')  # requests through page.route (an old server below)
        page = await ctx.new_page()
        # A 409 is expected when another tab moved the save (the page then takes the whole state).
        # HTTP errors are judged by their answers below (a 409 is expected when another tab moved the save).
        page.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and out['problems'].append(f'console: {m.text[:600]}'))
        page.on('response', lambda r: '/api/' in r.url and r.status >= 400 and not (r.status == 409 and r.url.endswith('/api/command'))
                and not r.url.endswith('/api/beacon') and out['problems'].append(f'HTTP {r.status} {r.url}'))
        page.on('pageerror', lambda e: out['problems'].append(f'exception: {str(e)[:300]}'))

        async def seen(r):  # (headless WebKit's beacons get a 403 from the Origin check, with or without this change)
            if os.environ.get('DELTA_DEBUG') and '/api/' in r.url:
                print('  ', r.request.method, r.url.split('/api/')[1][:40], r.status, flush=True)
            if r.url.endswith('/api/command') and r.status == 200:
                with contextlib.suppress(Exception):
                    data = json.loads(await r.body())
                    out['answers'] += 1
                    if (data.get('delta') or {}).get('refs'):
                        out['with_refs'] += 1
        page.on('response', lambda r: asyncio.ensure_future(seen(r)))
        if engine == 'webkit':  # its own warning about the viewport meta of every page
            out['problems'] = _Skip(out['problems'], 'interactive-widget')
        if os.environ.get('DELTA_DEBUG'):
            page.on('request', lambda r: '/api/command' in r.url and print('   send', (r.post_data or '')[:160], r.headers.get('x-game-delta'), flush=True))
            page.on('requestfailed', lambda r: print('   FAILED', r.url, r.failure, flush=True))
            page.on('console', lambda m: print('   console', m.type, m.text[:300], flush=True))

        async def as_old_server(route):  # what a server from before receives: no header, no `known`
            if not old_server[0]:
                await route.continue_()
                return
            headers = {k: v for k, v in route.request.headers.items() if k.lower() != 'x-game-delta'}
            out['old'] += 1
            body = route.request.post_data
            if body:
                data = json.loads(body)
                data.pop('known', None)
                body = json.dumps(data)
            await route.fulfill(response=await route.fetch(headers=headers, post_data=body))
        await page.route('**/api/**', as_old_server)

        async def check(label):
            r = await page.evaluate(SAME)
            out['checks'] += 1
            if not r.get('ok'):
                out['problems'].append(f'{label}: {r}')

        async def other_tab(js, arg):
            p2 = await ctx.new_page()
            await p2.goto(srv.base + '/api/health')
            r = await p2.evaluate(js, arg)
            await p2.close()
            return r

        await page.goto(srv.base + '/?deltacheck=1')
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await page.wait_for_timeout(600)
        await page.click('[data-action="jrGender"][data-gender="female"]')
        await page.fill('#sheet[open] input', 'Lan')
        await page.get_by_role('button', name='Vào làm thôi').click()
        await page.wait_for_timeout(1500)
        await check('after the intro')
        # The first customer by hand: press what the game highlights (later customers only point at the station).
        for i in range(30):
            if await page.evaluate("fetch('/api/state').then(r=>r.json()).then(d=>d.state.careers.milk_tea.metrics.served||0)"):
                break
            pick = await page.evaluate(PICK)
            if pick['kind'] == 'none':
                out['problems'].append(f'first customer: nothing to press ({pick.get("text", "")[:80]})')
                break
            with contextlib.suppress(Exception):
                await page.eval_on_selector(pick.get('sel') or '[data-fd-pick]', 'e=>e.click()')
            await page.wait_for_timeout(700)
            await check(f'press {i + 1} ({pick.get("kind")}: {pick.get("text", "")[:40]})')
        else:
            out['problems'].append('the first customer was not served')
        # Then the page's own api.command, one sensible step at a time (game/boba.py next_move on the save),
        # with an old server, another tab, a restart and an import on the way.
        await page.keyboard.press('Escape')
        for i in range(steps):
            if i == 4:
                old_server[0] = True
            if i == 8:
                old_server[0] = False
            if i == 12:  # another tab moves the save on
                r = await other_tab(CMD, ['settings', {'largeText': True}, None])
                if r['status'] != 200:
                    out['problems'].append(f'other tab: {r}')
            if i == 18:  # a server restart
                srv.stop()
                srv.start()
            if i == 24:  # a save imported in another tab
                r = await other_tab(IMPORT, None)
                if r['status'] != 200:
                    out['problems'].append(f'import in another tab: {r}')
            raw = await page.evaluate("fetch('/api/save/export').then(r=>r.json()).then(d=>d.state)")
            c = raw['careers']['milk_tea']
            active = [t for t in c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
            if active:
                t = next((t for t in active if t['id'] == c['active_task']), active[0])
                action, payload = boba.next_move(c, t)
            elif c['open'] and not raw['careers']['milk_tea'].get('closing'):
                action, payload = 'more_work', {}
            else:
                action, payload = ('start_day', {}) if not c['open'] else ('end_day', {'carry_event': True})
            r = await page.evaluate("""async ([a,p])=>{try{await __mnlApi.command(a,p,'milk_tea');return 'ok';}
              catch(e){return `${e.status||''} ${e.data?.code||''} ${e.message}`;}}""", [action, payload])
            if r != 'ok' and action == 'more_work':
                await page.evaluate("async ()=>{try{await __mnlApi.command('end_day',{carry_event:true},'milk_tea');}catch{}}")
            await page.wait_for_timeout(250)
            await check(f'step {i + 1} ({action}: {r})')
        stats = await page.evaluate('globalThis.__mnlDelta||{checked:0,bad:0}')
        out['self_check'] = stats
        if stats['bad']:
            out['problems'].append(f'the page\'s own check found {stats["bad"]} difference(s)')
        if not out['with_refs']:
            out['problems'].append('no answer used references')
        if not out['old']:
            out['problems'].append('the old server was never played (requests not intercepted)')
        await browser.close()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--steps', type=int, default=40)
    ap.add_argument('--engine', default='chromium', choices=('chromium', 'webkit'))
    a = ap.parse_args()
    srv = Server()
    try:
        srv.start()
        out = asyncio.run(run(srv, a.steps, a.engine))
    finally:
        srv.close()
    print(f"checks {out['checks']}, command answers {out['answers']} ({out['with_refs']} with references), "
          f"requests as to an old server {out['old']}, page self-check {out.get('self_check')}")
    for p in out['problems']:
        print('  !', p)
    print('PASS' if not out['problems'] else 'FAIL')
    sys.exit(1 if out['problems'] else 0)


if __name__ == '__main__':
    main()
