#!/usr/bin/env python3
"""🧭 First-day coach walkthrough (dev tool, needs `pip install playwright` and a Chrome/Chromium).

For each career and each work layout (gọn = data-clean on, đầy đủ = off): a dev server (MNL_DEV=1), the career picked
and hired by command, the coach opened from its "🧭 Có hướng dẫn mới" chip (or ⋯ → 🧭 Hướng dẫn), then played the way
a new player follows it: press what the coach rings; where it rings nothing (a words-only step, a "where is it"
bubble), press what the game itself highlights (the first-task pulse, the bottom button) like scripts/browser_first_day.py.
Each new coach step is screenshotted; the report lists every step with how it was shown (spot = ringed on screen,
via = its tab/fold ringed, nav = the way to the work screen, fallback = words only, text = a words-only step).

  TEST_DATABASE_URL=postgresql://…/scratch python scripts/browser_coach.py milk_tea,grocery [--sides on,off]
      [--size 390x844] [--town iso|classic] [--shots DIR] [--report FILE] [--server-python PATH] [--steps 120]
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

CMD = """async ([action,payload,career])=>{
  const st=await fetch('/api/state').then(r=>r.json());
  const csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf;
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:career||st.state.current,action,payload})});
  const d=await r.json();return {status:r.status,error:d.error||null};
}"""
# A click through the game's own delegate, as the tutorial buttons do (no element needed on screen).
ACT = """([a,data])=>{const b=document.createElement('button');b.dataset.action=a;Object.entries(data||{}).forEach(([k,v])=>b.dataset[k]=v);b.hidden=true;document.body.append(b);b.click();b.remove();}"""
# What would a player press next when the coach rings nothing: the game's own guidance (browser_first_day.py PICK, short).
PICK = """()=>{
  const vis=e=>{if(!e||e.disabled)return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('#coachLayer,#coachChip');};
  const acts=e=>e&&(e.matches('[data-action],[data-command]')||e.closest('[data-action],[data-command]'));
  const confirm=document.querySelector('#confirmDialog[open] [data-action="confirmYes"]');
  if(confirm){confirm.click();return 'confirm';}
  const top=[...document.querySelectorAll('dialog[open]')].pop();
  if(top&&top.id!=='sheet'){const b=[...top.querySelectorAll('.btn.primary,[data-action],[data-command]')].find(vis);if(b){b.click();return 'dialog:'+(b.innerText||'').trim().slice(0,30);}}
  const sheet=document.querySelector('#sheet[open]'),scope=sheet||document;
  const pulse=[...scope.querySelectorAll('.gd-pulse')].find(e=>vis(e)&&acts(e));
  if(pulse){pulse.click();return 'pulse:'+(pulse.innerText||'').trim().slice(0,30);}
  if(sheet){
    const cta=[...sheet.querySelectorAll('.gd-cta')].find(vis);
    if(cta){cta.click();return 'cta:'+(cta.innerText||'').trim().slice(0,30);}
    const h=sheet.querySelector('.gd-next .gd-hint');if(h&&vis(h)&&acts(h)){h.click();return 'hint';}
    for(const s of ['[data-action="nextJob"]','[data-action="start"]','[data-command="more_work"]','.sk-intro-go']){const e=[...sheet.querySelectorAll(s)].find(vis);if(e){e.click();return 'host:'+s;}}
    return 'none';
  }
  const e=[...document.querySelectorAll('#taskHUD [data-action="job"],#taskHUD [data-action="prepare"],#isoHUD [data-action="isoMission"],#isoHUD [data-action="isoOpen"],#isoHUD [data-action="isoWork"]')].find(vis);
  if(e){e.click();return 'scene:'+(e.dataset.action||'');}
  return 'none';
}"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server(python: str):
    if not (os.environ.get('TEST_DATABASE_URL') or '').startswith(('postgresql://', 'postgres://')):
        raise SystemExit('Set TEST_DATABASE_URL to a disposable PostgreSQL database.')
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-coach-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1', MNL_DEV='1')
    env.setdefault('MNL_PG_TEST_RUN', 'coach' + os.urandom(3).hex())
    for k in ('DATABASE_URL', 'MNL_CAREERS', 'LLM_API_KEY'):
        env.pop(k, None)
    p = subprocess.Popen([python, 'server.py', '--port', str(port), '--namespace', os.path.join(tmp, 'g.db')],
                         cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f'http://127.0.0.1:{port}'
    for _ in range(900):
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


async def settle(page):
    """Close what a fresh dev save opens by itself (Có gì mới, the interface question)."""
    for _ in range(3):
        with contextlib.suppress(Exception):
            await page.eval_on_selector('#wnDialog[open] .wn-foot [data-wn="close"]', 'e=>e.click()')
        with contextlib.suppress(Exception):
            await page.eval_on_selector('#interfacePrompt[open] .btn.primary', 'e=>e.click()')
        await page.wait_for_timeout(300)


async def walk(browser, base, cid, side, args, shots: Path | None) -> dict:
    w, h = (int(x) for x in args.size.split('x'))
    ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=True, is_mobile=w < 700, device_scale_factor=1)
    page = await ctx.new_page()
    out = dict(career=cid, side=side, steps=[], problems=[], ended=False)
    page.on('pageerror', lambda e: out['problems'].append(f'exception: {str(e)[:200]}'))
    page.on('console', lambda m: m.type == 'error' and 'coach' in m.text and out['problems'].append(f'console: {m.text[:200]}'))
    await page.goto(base)
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_timeout(700)
    await settle(page)
    await page.evaluate(CMD, ['select_career', {}, cid])
    boot = await page.evaluate("fetch('/api/bootstrap').then(r=>r.json())")
    st = await page.evaluate("fetch('/api/state').then(r=>r.json())")
    job = st['state']['careers'][cid].get('job') or {}
    if job.get('required') and job.get('status') != 'hired':
        post = ((boot['content'].get('employment') or {}).get('postings', {}).get(cid) or [{}])[0].get('id')
        await page.evaluate(CMD, ['job_quick', {'posting': post, 'confirm': True}, cid])
    await page.evaluate(CMD, ['settings', {'newInterface': args.town == 'iso', 'interfacePromptSeen': True}, cid])
    await page.evaluate("v=>{try{localStorage.setItem('mnl.clean',v);localStorage.removeItem('mnl.clean.c');localStorage.removeItem('mnl.coach.run');}catch{}}", side)
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_timeout(1200)
    await settle(page)

    async def shot(name):
        if shots:
            await page.screenshot(path=str(shots / f'{cid}-{side}-{name}.png'))

    # The chip first (a dev save is not a coach-native save), else ⋯ → 🧭 Hướng dẫn.
    for _ in range(40):   # the tutorial module boots a few idle slots after the first frame
        if await page.evaluate('!!globalThis.__mnlCoach?.chip?.()'):
            break
        await settle(page)
    if await page.evaluate('!!globalThis.__mnlCoach?.chip?.()'):
        out['chip'] = True
        await shot('00-chip')
        await page.click('#coachChip [data-chip="go"]')
    else:
        out['chip'] = False
        await page.evaluate(ACT, ['coachStart', {'career': cid}])
    await page.wait_for_timeout(900)
    seen, last_key, same = {}, None, 0
    for it in range(args.steps):
        c = await page.evaluate('globalThis.__mnlCoach?.get?.()||null')
        if not c:
            out['ended'] = True
            break
        key = f"{c['n']:02d}-{c['id']}"
        rec = seen.get(key)
        if rec is None:
            rec = seen[key] = dict(n=c['n'], id=c['id'], t=c['t'], modes=[])
            out['steps'].append(rec)
            await page.wait_for_timeout(350)
            await shot(f"{c['n']:02d}-{c['id']}-{c['mode']}")
        if c['mode'] and (not rec['modes'] or rec['modes'][-1] != c['mode']):
            rec['modes'].append(c['mode'])
            if c['mode'] in ('spot', 'via', 'nav', 'dock-spot'):   # what is ringed, to check it is the right control
                rec.setdefault('ring', []).append(c['mode'] + ': ' + await page.evaluate(
                    "()=>{const e=globalThis.__mnlCoach.el();return e?(e.innerText||e.getAttribute('aria-label')||e.className||'').replace(/\\s+/g,' ').trim().slice(0,50):''}"))
        # Act like a player who follows the coach.
        if c['id'] == 'sum':
            did = await page.evaluate("()=>{const b=document.querySelector('#coachLayer [data-coach-btn=\"next\"]');if(b){b.click();return 'coach:done';}return 'none';}")
        elif c['mode'] in ('spot', 'via', 'nav', 'dock-spot'):
            if c['id'] == 'close' and c['mode'] == 'dock-spot' and it < args.steps // 2 and rec.get('served', 0) < 1:
                rec['served'] = 1   # serve one more customer before closing
                did = await page.evaluate(PICK)
            else:
                did = await page.evaluate("()=>{const e=globalThis.__mnlCoach.el();if(!e||e.disabled)return 'disabled';e.click();return 'ring:'+(e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,30);}")
                if did == 'disabled':
                    did = await page.evaluate(PICK)
        elif c['mode'] == 'dock' and c['id'] == 'close':
            did = await page.evaluate(PICK)
            if did == 'none':
                did = await page.evaluate("()=>{const e=document.querySelector('#taskHUD [data-action=\"end\"],#isoHUD [data-action=\"isoEnd\"]');if(e){e.click();return 'end'};return 'none'}")
                if did == 'none':
                    await page.evaluate(ACT, ['end', {}])
                    did = 'act:end'
        else:
            did = await page.evaluate(PICK)
            if did == 'none' and c['mode'] in ('text', 'fallback'):
                did = await page.evaluate("()=>{const b=document.querySelector('#coachLayer [data-coach-btn=\"next\"],#coachLayer [data-coach-btn=\"skip\"]');if(b){b.click();return 'coach:'+b.dataset.coachBtn;}return 'none';}")
        rec.setdefault('did', []).append(did)
        k2 = (c['id'], c['mode'], did)
        same = same + 1 if k2 == last_key else 0
        last_key = k2
        if same >= 6:
            # Stuck on this step: skip it like a player would.
            await page.evaluate("()=>document.querySelector('#coachLayer [data-coach-btn=\"skip\"],#coachLayer [data-coach-btn=\"next\"]')?.click()")
            rec['skipped'] = True
            same = 0
        await page.wait_for_timeout(900)   # longer than the coach's SETTLE: one tap at a time
    out['shown'] = {s['id']: s['modes'] for s in out['steps']}
    await ctx.close()
    return out


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('careers')
    ap.add_argument('--sides', default='on,off')
    ap.add_argument('--size', default='390x844')
    ap.add_argument('--town', default='iso', choices=['iso', 'classic'])
    ap.add_argument('--shots')
    ap.add_argument('--report')
    ap.add_argument('--steps', type=int, default=120)
    ap.add_argument('--server-python', default=sys.executable)
    ap.add_argument('--channel', default='chrome', help="playwright browser channel ('' for the bundled chromium)")
    ap.add_argument('--jobs', type=int, default=2)
    args = ap.parse_args()
    from playwright.async_api import async_playwright
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    results = []
    with server(args.server_python) as base:
        async with async_playwright() as p:
            browser = await p.chromium.launch(**({'channel': args.channel} if args.channel else {}), headless=True)
            sem = asyncio.Semaphore(args.jobs)

            async def one(cid, side):
                async with sem:
                    try:
                        r = await walk(browser, base, cid, side, args, shots)
                    except Exception as e:  # report and go on with the next career
                        r = dict(career=cid, side=side, problems=[f'walk failed: {e}'[:300]], steps=[])
                    results.append(r)
                    lines = '\n'.join(f"   {s['n']:>2} {s['id']:6} {'/'.join(s['modes']):22} {s['t'][:48]:48} | {' ; '.join(s.get('ring', []))[:70]}"
                                      for s in r['steps'])
                    print(f"{cid} [{side}] chip={r.get('chip')} ended={r.get('ended')}" + (f"  PROBLEMS {r['problems'][:3]}" if r['problems'] else '') + '\n' + lines, flush=True)
            await asyncio.gather(*(one(c, s) for c in args.careers.split(',') for s in args.sides.split(',')))
            await browser.close()
    if args.report:
        Path(args.report).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main())
