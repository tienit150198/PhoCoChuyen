#!/usr/bin/env python3
"""v0.4 browser sweep (dev tool, needs `pip install playwright` + chromium).

Starts a throwaway server with every career, then on phone, tablet and
desktop viewports: opens home, every career's dock and menu sheets, settings tabs,
themes, Phố nghề and the teacher's class plan, in Vietnamese and English.
Fails on console errors, uncaught exceptions, failed API calls or horizontal
overflow. Writes artifacts/browser-v04-report.json (+ screenshots with --shots).
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
from pg_test_support import test_env, test_connect, schema_for

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = {'phone': (390, 844, True), 'tablet': (820, 1180, True), 'desktop': (1440, 900, False)}
THEMES = ('kem', 'tra_xanh', 'bien', 'keo', 'dem')

CMD = """async ([action,payload,career])=>{
  const st=await fetch('/api/state').then(r=>r.json());
  const csrf=window.__csrf||(window.__csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf);
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:career||st.state.current,action,payload})});
  const d=await r.json();return {status:r.status,error:d.error||null};
}"""

OVERFLOW = """()=>{
  const w=innerWidth,sheet=document.querySelector('dialog[open]'),scope=sheet||document.body,over=[];
  for(const el of scope.querySelectorAll('*')){
    const r=el.getBoundingClientRect();
    if(!r.width||r.right<=w+1&&r.left>=-1||getComputedStyle(el).position==='fixed')continue;
    let p=el.parentElement,clipped=false;
    while(p&&p!==document.body){const s=getComputedStyle(p);if(s.overflowX!=='visible'&&p.scrollWidth>p.clientWidth+1){clipped=true;break;}p=p.parentElement;}
    const cls=e=>e.tagName.toLowerCase()+'.'+String(e.className?.baseVal??e.className??'').trim().split(/\\s+/).slice(0,2).join('.');
    if(!clipped)over.push(cls(el)+' in '+(el.parentElement?cls(el.parentElement):'')+' '+Math.round(r.left)+'..'+Math.round(r.right)+' "'+(el.textContent||'').trim().slice(0,30)+'"');
  }
  return {page:document.scrollingElement.scrollWidth>w+1,sheet:sheet?sheet.scrollWidth>sheet.clientWidth+1:false,over:over.slice(0,6)};
}"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-v04-')
    env = test_env( QUIET='1', PUSH_DISABLED='1', MNL_DEV='1')  # MNL_DEV allows the job_quick shortcut
    env.pop('MNL_CAREERS', None)
    env.pop('LLM_API_KEY', None)
    # The server's output goes to a log file next to the throwaway database: a pipe that nobody reads fills
    # up after a few thousand lines and the server then blocks on its next write (the sweep froze mid-run).
    log_path = os.path.join(tmp, 'server.log')
    log = open(log_path, 'wb')
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--namespace', os.path.join(tmp, 'g.db')],
                         cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    # Up to a minute: a loaded machine can take a while to import every career.
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:
            if p.poll() is not None:
                break
            time.sleep(0.1)
    if p.poll() is not None:
        print(f'test server exited with code {p.returncode}; log: {log_path}', file=sys.stderr)
    try:
        yield base
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)
        log.close()
        print(f'server log: {log_path}', file=sys.stderr)


class Sweep:
    def __init__(self, page, name: str, shots: Path | None):
        self.page, self.name, self.shots = page, name, shots
        self.problems: list[str] = []
        self.visited: list[str] = []
        self.misses: set[str] = set()
        page.on('console', lambda m: m.type == 'error' and self.problem(f'console: {m.text[:200]}'))
        page.on('pageerror', lambda e: self.problem(f'exception: {str(e)[:200]}'))
        page.on('response', lambda r: '/api/' in r.url and r.status >= 500 and self.problem(f'HTTP {r.status} {r.url}'))

    def problem(self, text: str):
        self.problems.append(f'[{self.name}] {text}')

    async def cmd(self, action, payload=None, career=None):
        r = await self.page.evaluate(CMD, [action, payload or {}, career])
        if r['status'] != 200:
            self.problem(f'cmd {action} -> {r["status"]} {r["error"]}')
        return r

    async def ready(self):
        await self.page.wait_for_selector('#app:not([hidden])', timeout=20000)
        await self.page.wait_for_timeout(400)

    async def collect_misses(self):
        with contextlib.suppress(Exception):
            self.misses.update(await self.page.evaluate('[...(globalThis.__i18nMisses||[])]'))

    async def reload(self):
        await self.collect_misses()
        await self.page.reload()
        await self.ready()

    async def check(self, label: str):
        self.visited.append(label)
        info = await self.page.evaluate(OVERFLOW)
        if info['page'] or info['sheet'] or info['over']:
            self.problem(f'overflow at {label}: {info}')
        if self.shots:
            await self.page.screenshot(path=str(self.shots / f'{self.name}-{label}.png'))

    async def close_sheet(self):
        await self.page.keyboard.press('Escape')
        await self.page.wait_for_timeout(150)
        await self.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

    async def click(self, selector: str) -> bool:
        el = await self.page.query_selector(selector)
        if not el:
            return False
        await el.evaluate('e=>e.click()')
        await self.page.wait_for_timeout(350)
        return True

    async def dock_sweep(self, career: str):
        # The dock holds the in-shop actions; the rail ("Thêm" menu on phone) holds the shop book, reviews, feed, help…
        seen = set()
        for root in ('#dock', '#rail'):
            n = await self.page.eval_on_selector_all(f'{root} [data-action]', 'els=>els.length')
            for i in range(n):
                action = await self.page.eval_on_selector_all(f'{root} [data-action]', f'els=>els[{i}]?.dataset.action')
                if action in (None, 'sound', 'v4Menu', 'home', 'close') or action in seen:
                    continue
                seen.add(action)
                await self.page.eval_on_selector_all(f'{root} [data-action]', f'els=>els[{i}]?.click()')
                await self.page.wait_for_timeout(400)
                await self.check(f'{career}-{root[1:]}{i}-{action}')
                await self.close_sheet()


async def run(base: str, shots: Path | None, only: list[str], lang: str = 'vi'):
    from playwright.async_api import async_playwright
    report = dict(base=base, viewports={}, problems=[])
    boot = json.loads(urllib.request.urlopen(base + '/api/bootstrap').read())
    careers = boot['state']['careers']
    postings = (boot['content'].get('employment') or {}).get('postings', {})
    ids = [c for c in careers if not only or c in only]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for vname, (w, h, touch) in VIEWPORTS.items():
            ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=touch, is_mobile=touch and w < 700,
                                            device_scale_factor=1)
            page = await ctx.new_page()
            s = Sweep(page, vname, shots)
            await page.goto(base)
            await s.ready()
            if lang == 'en':
                await s.cmd('settings', {'lang': 'en'})
                await s.reload()
            await s.check('home')
            for cid in ids:
                await s.cmd('select_career', {}, cid)
                state = await page.evaluate("fetch('/api/state').then(r=>r.json())")
                job = state['state']['careers'][cid].get('job') or {}
                if job.get('required') and job.get('status') != 'hired':
                    # Office careers: see the job hunt, then take a trial job.
                    await s.reload()
                    await s.check(f'{cid}-jobhunt')
                    await s.close_sheet()
                    post = postings.get(cid, [{}])[0].get('id')
                    await s.cmd('job_quick', {'posting': post, 'confirm': True}, cid)
                await s.cmd('start_day', {}, cid)
                await s.reload()
                await s.check(f'{cid}-stage')
                await s.dock_sweep(cid)
            # Settings: every tab and theme.
            if await s.click('[data-action="settings"]'):
                for tab in await page.eval_on_selector_all('[data-action="v4SetTab"]', 'els=>els.map(e=>e.dataset.tab)'):
                    await page.evaluate(f"document.querySelector('[data-action=\"v4SetTab\"][data-tab=\"{tab}\"]')?.click()")
                    await page.wait_for_timeout(250)
                    await s.check(f'settings-{tab}')
                await s.close_sheet()
            for theme in THEMES:
                await s.cmd('settings', {'uiTheme': theme})
                await s.reload()
                await s.check(f'theme-{theme}')
            await s.cmd('settings', {'uiTheme': 'kem'})
            # Phố nghề.
            await page.evaluate("""async()=>{const csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf;
              await fetch('/api/social/profile',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
              body:JSON.stringify({name:'Quán thử """ + vname + """',bio:'Kiểm thử',avatar:'🌸',visible:true})});}""")
            await s.reload()
            if await s.click('.top-social'):
                for tab in ('street', 'board', 'market', 'inbox', 'me'):
                    await page.evaluate(f"document.querySelector('[data-action=\"socTab\"][data-tab=\"{tab}\"]')?.click()")
                    await page.wait_for_timeout(500)
                    await s.check(f'social-{tab}')
                await s.close_sheet()
            else:
                s.problem('no Phố nghề button')
            # English.
            await s.cmd('settings', {'lang': 'en'})
            await s.reload()
            await page.wait_for_timeout(600)
            await s.check('en-stage')
            if 'teacher' in ids:
                await s.cmd('select_career', {}, 'teacher')
                await s.reload()
                await s.dock_sweep('en-teacher')
            await s.collect_misses()
            misses = sorted(s.misses)
            if lang != 'en':
                await s.cmd('settings', {'lang': 'vi'})
            report['viewports'][vname] = dict(visited=s.visited, problems=s.problems, i18n_misses=len(misses), sample_misses=misses[:400])
            report['problems'] += s.problems
            await ctx.close()
        await browser.close()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', help='use a running server instead of starting one')
    ap.add_argument('--shots', type=Path, help='directory for screenshots')
    ap.add_argument('--careers', default='', help='comma list to limit careers')
    ap.add_argument('--lang', default='vi', choices=['vi', 'en'], help='play the whole sweep in this language')
    ap.add_argument('--report', type=Path, default=ROOT / 'artifacts' / 'browser-v04-report.json', help='where to write the JSON report')
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    only = [x for x in a.careers.split(',') if x]
    with (contextlib.nullcontext(a.base) if a.base else server()) as base:
        report = asyncio.run(run(base, a.shots, only, a.lang))
    out = a.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for p in report['problems']:
        print(p)
    for v, r in report['viewports'].items():
        print(f'{v}: {len(r["visited"])} screens, {len(r["problems"])} problems, {r["i18n_misses"]} untranslated strings')
    sys.exit(1 if report['problems'] else 0)


if __name__ == '__main__':
    main()
