#!/usr/bin/env python3
"""First-day sweep (dev tool, needs `pip install playwright` + chromium).

Plays a brand-new STORY-mode player the way production runs (story on, MNL_DEV
off) on a 390×844 phone: the one intro screen (look, name, a chapter-1 workplace)
→ day 1 opens by itself → finish the first task, only ever pressing the control the game highlights
(the first-time pulse), the bottom button (.gd-cta) or the "Bước tiếp theo"
hint, and saying yes to confirm dialogs. A career passes when its first task is
completed without console errors, error toasts or a step that goes nowhere.

  python scripts/browser_first_day.py [--careers a,b] [--shots DIR] [--report FILE]

--dev plays careers the story opens later (and office jobs): a server with MNL_DEV=1,
the career picked by command and hired through the dev shortcut, then the same
"press what glows" loop for its first task.
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
CHAPTER_ONE = ('milk_tea', 'grocery', 'delivery', 'cafe_bakery', 'florist', 'mother_baby', 'restaurant')

# One step of "follow the game": what would a new player press next?
PICK = """()=>{
  const vis=e=>{if(!e||e.disabled)return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden';};
  const acts=e=>e&&(e.matches('[data-action],[data-command]')||e.closest('[data-action],[data-command]'));
  const say=e=>(e.innerText||e.getAttribute('aria-label')||'').replace(/\\s+/g,' ').trim().slice(0,90);
  const confirm=document.querySelector('#confirmDialog[open] [data-action="confirmYes"]');
  if(confirm)return {kind:'confirm',sel:'#confirmDialog[open] [data-action="confirmYes"]',text:say(document.querySelector('#confirmContent'))};
  const sheet=document.querySelector('#sheet[open]');
  const scope=sheet||document;
  const hint=sheet?.querySelector('.gd-next');
  const tag=(e,kind)=>{e.setAttribute('data-fd-pick','1');return {kind,text:say(e),hint:hint?say(hint):''};};
  document.querySelectorAll('[data-fd-pick]').forEach(e=>e.removeAttribute('data-fd-pick'));
  const pulse=[...scope.querySelectorAll('.gd-pulse')].find(e=>vis(e)&&acts(e));
  if(pulse)return tag(pulse,'pulse');
  if(sheet){
    const cta=[...sheet.querySelectorAll('.gd-cta')].find(vis);
    if(cta)return tag(cta,'cta');
    const h=sheet.querySelector('.gd-next .gd-hint');
    if(h&&vis(h)&&acts(h))return tag(h,'hint');
    // Host screens between tasks: the one primary way on.
    for(const s of ['[data-action="nextJob"]','[data-action="start"]','[data-command="more_work"]'])
      {const e=[...sheet.querySelectorAll(s)].find(vis);if(e)return tag(e,'host');}
    return {kind:'none',hint:hint?say(hint):'',text:say(sheet).slice(0,200)};
  }
  const e=[...document.querySelectorAll('[data-action="job"],[data-action="prepare"].btn,[data-action="jobapp"]')].find(vis);
  if(e)return tag(e,'scene');
  return {kind:'none',text:''};
}"""

CMD = """async ([action,payload,career])=>{
  const st=await fetch('/api/state').then(r=>r.json());
  const csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf;
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:career||st.state.current,action,payload})});
  const d=await r.json();return {status:r.status,error:d.error||null};
}"""

STATE = """async (cid)=>{const s=await fetch('/api/state').then(r=>r.json());const c=s.state.careers[cid]||{};
  return {served:(c.metrics||{}).served||0,open:!!c.open,revision:s.revision,current:s.state.current,job:(c.job||{}).status||null};}"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server(dev: bool = False):
    """Like production: the story is on (MNL_DEV unset), no AI key, no push. `dev`: every place open."""
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-first-day-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY'):
        env.pop(k, None)
    if dev:
        env['MNL_DEV'] = '1'
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--db', os.path.join(tmp, 'g.sqlite3')],
                         cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base = f'http://127.0.0.1:{port}'
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    try:
        yield base
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)


async def dev_start(page, cid: str):
    """No story: pick the place by command; a job that hires is taken through the dev shortcut."""
    await page.evaluate(CMD, ['select_career', {}, cid])
    boot = await page.evaluate("fetch('/api/bootstrap').then(r=>r.json())")
    st = await page.evaluate("fetch('/api/state').then(r=>r.json())")
    job = st['state']['careers'][cid].get('job') or {}
    if job.get('required') and job.get('status') != 'hired':
        post = ((boot['content'].get('employment') or {}).get('postings', {}).get(cid) or [{}])[0].get('id')
        await page.evaluate(CMD, ['job_quick', {'posting': post, 'confirm': True}, cid])
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=20000)
    await page.wait_for_timeout(700)


async def play(browser, base: str, cid: str, shots: Path | None, max_steps: int = 90, dev: bool = False) -> dict:
    ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=1)
    page = await ctx.new_page()
    out = dict(career=cid, ok=False, steps=[], problems=[])
    page.on('console', lambda m: m.type == 'error' and out['problems'].append(f'console: {m.text[:200]}'))
    page.on('pageerror', lambda e: out['problems'].append(f'exception: {str(e)[:200]}'))
    page.on('response', lambda r: '/api/' in r.url and r.status >= 500 and out['problems'].append(f'HTTP {r.status} {r.url}'))

    async def shot(name):
        if shots:
            await page.screenshot(path=str(shots / f'{cid}-{name}.png'))

    async def toasts():
        return await page.evaluate("[...document.querySelectorAll('.toast.error')].map(e=>e.dataset.msg||e.textContent)")

    try:
        await page.goto(base)
        await page.wait_for_selector('#app:not([hidden])', timeout=20000)
        await page.wait_for_timeout(600)
        if dev:
            await dev_start(page, cid)
        else:
            # The story intro is one screen: look, name, first workplace (milk tea is picked already), go.
            # Day 1 of that first workplace then opens by itself, straight into the first customer.
            await page.click('[data-action="jrGender"][data-gender="female"]')
            await page.fill('#sheet[open] input', 'Lan')
            rec = await page.get_attribute('.onb-job.active', 'data-career')
            if rec != 'milk_tea':
                out['problems'].append(f'the recommended first workplace is {rec!r}, not milk_tea')
            if cid != rec:
                await page.click(f'.onb-job[data-career="{cid}"]')
            await page.get_by_role('button', name='Vào làm thôi').click()
            for _ in range(40):
                st = await page.evaluate(STATE, cid)
                if st['open'] and st['current'] == cid:
                    break
                await page.wait_for_timeout(250)
            else:
                out['problems'].append('day 1 did not open by itself after the intro')
            await page.wait_for_timeout(700)
            if await page.evaluate("()=>!!document.querySelector('#sheet[open].prep-sheet, #wnDialog[open], #tutWelcome[open]')"):
                out['problems'].append('a "Chuẩn bị", "Có gì mới" or welcome sheet is in the way of the first customer')
        await shot('0-start')
        seen_errors: set[str] = set()
        last, same = None, 0
        for i in range(max_steps):
            st = await page.evaluate(STATE, cid)
            if st['served'] >= 1:
                out['ok'] = True
                break
            pick = await page.evaluate(PICK)
            out['steps'].append(f"{pick['kind']}: {pick.get('text', '')}" + (f"  [hint: {pick['hint']}]" if pick.get('hint') else ''))
            if pick['kind'] == 'none':
                out['problems'].append(f'stuck: nothing highlighted to press ({pick.get("hint") or pick.get("text", "")[:120]})')
                break
            key = (pick['kind'], pick.get('text'), st['revision'])
            same = same + 1 if key == last else 0
            last = key
            if same >= 3:
                out['problems'].append(f'stuck: pressing "{pick.get("text")}" changes nothing')
                break
            sel = pick.get('sel') or '[data-fd-pick]'
            await page.eval_on_selector(sel, 'e=>e.click()')
            await page.wait_for_timeout(650)
            for msg in await toasts():
                if msg not in seen_errors:
                    seen_errors.add(msg)
                    out['problems'].append(f'error toast after "{pick.get("text")}": {msg}')
            if i in (2, 5, 9) or pick['kind'] == 'pulse' and i < 12:
                await shot(f'{i + 1:02d}-{pick["kind"]}')
        else:
            out['problems'].append(f'did not finish the first task in {max_steps} presses')
        if not out['ok'] and not any(p.startswith('stuck') or p.startswith('did not') for p in out['problems']):
            out['problems'].append('first task not completed')
        await page.wait_for_timeout(400)
        await shot('9-done')
    except Exception as e:  # a missing intro control is a problem too
        out['problems'].append(f'error: {str(e)[:300]}')
        with contextlib.suppress(Exception):
            await shot('9-error')
    await ctx.close()
    return out


async def run(base: str, careers: list[str], shots: Path | None, dev: bool = False) -> dict:
    from playwright.async_api import async_playwright
    report = dict(base=base, careers={}, problems=[])
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for cid in careers:
            r = await play(browser, base, cid, shots, dev=dev)
            report['careers'][cid] = r
            report['problems'] += [f'[{cid}] {p}' for p in r['problems']]
        await browser.close()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', help='use a running (story-mode) server instead of starting one')
    ap.add_argument('--careers', default=','.join(CHAPTER_ONE))
    ap.add_argument('--shots', type=Path, help='directory for screenshots')
    ap.add_argument('--report', type=Path, default=ROOT / 'artifacts' / 'browser-first-day.json')
    ap.add_argument('--dev', action='store_true', help='MNL_DEV server: any career, hired through the dev shortcut')
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    careers = [x for x in a.careers.split(',') if x]
    with (contextlib.nullcontext(a.base) if a.base else server(a.dev)) as base:
        report = asyncio.run(run(base, careers, a.shots, a.dev))
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for cid, r in report['careers'].items():
        print(f"{'PASS' if r['ok'] and not r['problems'] else 'FAIL'} {cid}: {len(r['steps'])} presses")
        for s in r['steps']:
            print('   ', s)
        for p in r['problems']:
            print('   !', p)
    sys.exit(1 if report['problems'] or not all(r['ok'] for r in report['careers'].values()) else 0)


if __name__ == '__main__':
    main()
