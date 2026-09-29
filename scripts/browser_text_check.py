#!/usr/bin/env python3
"""Text check for work sheets (dev tool, needs `pip install playwright` + chromium/webkit).

"Game mất chữ": a work sheet whose cards and buttons render with no text. This sweep plays
each career's tasks on a 390×844 phone (WebKit gets the iPhone profile), pressing only what
the guide highlights, and after every press checks the open sheet:

- every visible card, button, tag and summary has text (or an aria-label/title);
- every text inside the sheet is painted: not transparent, not hidden, not a 0 px font, and
  not the colour of its own background;
- after a re-render (morph), no text of the sheet's markup stands blank on screen;
- the same after coming back to the tab (the sheet is written whole again, app.js repaintSheet).

  python scripts/browser_text_check.py [--engines chromium,webkit] [--careers grocery,milk_tea]
                                       [--lang vi|en|both] [--tasks 6] [--shots DIR] [--report FILE]

A career is played through `--tasks` tasks (grocery: checkout, shelf and, from day 2, the rush);
when the day runs out of work it is closed and the next one opened.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_first_day import PICK  # noqa: E402  (the "press what glows" picker)
from browser_v04 import CMD, server  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ('grocery', 'milk_tea', 'restaurant', 'cafe_bakery', 'florist', 'delivery', 'mother_baby')

# In-page check of the open sheet (or the main screen when no sheet is open). Returns problems.
CHECK = r"""async (label)=>{
  const out=[];
  const sheet=document.querySelector('#sheet[open]');
  const scope=sheet||document.querySelector('#app');
  if(!scope)return out;
  // Laid out and meant to be seen: not in a closed <details> (its content keeps a box in Chromium), not hidden.
  const shown=e=>{const r=e.getBoundingClientRect();if(r.width<2||r.height<2)return false;
    const fold=e.closest('details:not([open])');if(fold&&!e.closest('summary'))return false;
    if(e.checkVisibility&&!e.checkVisibility({visibilityProperty:true,contentVisibilityAuto:true}))return false;
    const s=getComputedStyle(e);return s.visibility==='visible'&&s.display!=='none';};
  const name=e=>(e.tagName.toLowerCase()+'.'+String(e.className?.baseVal??e.className??'').trim().split(/\s+/).slice(0,3).join('.')).replace(/\.$/,'');
  const words=e=>(e.innerText||'').replace(/\s+/g,' ').trim();
  // 1. Cards and controls with no words at all (the reported bug: empty cards, a label-less button).
  for(const e of scope.querySelectorAll('.card,article,.btn,button,.tag,summary,.gd-cta,.gd-hint')){
    if(!shown(e)||e.closest('[hidden],[aria-hidden="true"],.update-pill,.toast,.toasts'))continue;
    if(words(e))continue;
    if(e.getAttribute('aria-label')||e.getAttribute('title'))continue;
    if(e.matches('.card,article')&&e.querySelector('input,textarea,select,canvas,progress,meter'))continue;
    out.push(`empty ${name(e)}${e.dataset.command?' cmd='+e.dataset.command:''}${e.dataset.action?' action='+e.dataset.action:''}: ${e.outerHTML.replace(/\s+/g,' ').slice(0,160)}`);
  }
  // 2. Text that is there but not painted.
  const rgba=c=>{const m=String(c).match(/rgba?\(([^)]+)\)/);if(!m)return null;const p=m[1].split(/[ ,/]+/).filter(Boolean).map(Number);return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1};};
  const lum=({r,g,b})=>{const f=v=>{v/=255;return v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4;};return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b);};
  const bgOf=el=>{for(let e=el;e&&e.nodeType===1;e=e.parentElement){const s=getComputedStyle(e);if(s.backgroundImage&&s.backgroundImage!=='none')return null;const c=rgba(s.backgroundColor);if(c&&c.a>0.6)return c;}return null;};
  const seen=new Set();
  const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);
  for(let n=walker.nextNode();n;n=walker.nextNode()){
    const el=n.parentElement;if(!el||seen.has(el)||!n.nodeValue.trim())continue;
    // Toasts fade out on purpose; they are not part of the sheet.
    if(el.closest('script,style,template,[hidden],[aria-hidden="true"],.update-pill,.toast,.toasts,option,.sr-only,.visually-hidden'))continue;
    seen.add(el);
    if(!shown(el))continue;
    const s=getComputedStyle(el);
    let op=1;for(let e=el;e&&e.nodeType===1;e=e.parentElement)op*=Number(getComputedStyle(e).opacity);
    const fill=rgba(s.webkitTextFillColor||s.color)||rgba(s.color),size=parseFloat(s.fontSize);
    const text=n.nodeValue.trim().slice(0,40);
    if(op<0.05){out.push(`invisible (opacity ${op.toFixed(2)}) ${name(el)} "${text}"`);continue;}
    if(size<6){out.push(`invisible (font ${size}px) ${name(el)} "${text}"`);continue;}
    if(fill&&fill.a<0.1){out.push(`invisible (transparent colour) ${name(el)} "${text}"`);continue;}
    const bg=bgOf(el);
    if(fill&&bg&&/\p{L}/u.test(text)){
      const a=lum(fill),b=lum(bg),ratio=(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
      if(ratio<1.35)out.push(`unreadable (contrast ${ratio.toFixed(2)}) ${name(el)} "${text}"`);
    }
  }
  // 3. After a morph, every text of the markup is still on screen.
  const box=document.querySelector('#sheetContent');
  if(sheet&&box&&typeof box._html==='string'){
    const fresh=document.createElement('div');fresh.innerHTML=box._html;
    // The guide moves the hint into the header and drops the subtitle; compare the rest.
    const body=root=>{const c=root.querySelector('.sheet-body')?.cloneNode(true);if(c)c.querySelectorAll('.gd-next,textarea,input,select').forEach(e=>e.remove());return c;};
    const texts=root=>{const r=[];if(!root)return r;const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);for(let n=w.nextNode();n;n=w.nextNode())r.push(n.nodeValue.replace(/\s+/g,' ').trim());return r;};
    const a=texts(body(box)),b=texts(body(fresh));
    // Words may differ (English is translated on display, workbench timers tick in place);
    // what must never happen is a text of the markup standing blank on screen.
    const lost=b.map((v,i)=>v&&!a[i]?v:null).filter(Boolean);
    const len=list=>list.join('').length;
    if(a.length===b.length){if(lost.length)out.push(`morph: ${lost.length} texts blank on screen: "${lost.slice(0,3).join('" · "').slice(0,120)}"`);}
    else if(len(a)<len(b)*0.5)out.push(`morph: ${len(a)} characters on screen, ${len(b)} in the markup`);
  }
  return out;
}"""

TASKS = """async (cid)=>{const s=await fetch('/api/state').then(r=>r.json());const c=s.state.careers[cid]||{};
  const live=(c.tasks||[]).filter(t=>!['completed','referred','cancelled'].includes(t.status));
  return {open:!!c.open,day:c.day,served:(c.metrics||{}).served||0,live:live.map(t=>({id:t.id,kind:t.kind||t.variant||'',title:t.title})),
    done:(c.tasks||[]).filter(t=>['completed','referred','cancelled'].includes(t.status)).map(t=>t.id)};}"""

OPEN_JOB = """(id)=>{const b=document.createElement('button');b.type='button';b.dataset.action='job';if(id)b.dataset.task=id;
  b.hidden=true;document.body.append(b);b.click();b.remove();}"""


async def open_page(pw, engine: str, base: str):
    browser = await getattr(pw, engine).launch()
    if engine == 'webkit':
        ctx = await browser.new_context(**pw.devices['iPhone 13'])   # 390×844, iOS Safari UA, touch
    else:
        ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2)
    return browser, ctx


async def play(pw, engine: str, base: str, cid: str, lang: str, tasks: int, shots: Path | None, max_steps: int) -> dict:
    browser, ctx = await open_page(pw, engine, base)
    page = await ctx.new_page()
    tag = f'{engine}/{lang}/{cid}'
    out = dict(engine=engine, lang=lang, career=cid, checks=0, tasks=[], problems=[], notes=[])
    seen: set[str] = set()

    def problem(text: str):
        if text not in seen:
            seen.add(text)
            out['problems'].append(text)

    page.on('pageerror', lambda e: problem(f'exception: {str(e)[:200]}'))
    page.on('console', lambda m: m.type == 'error' and problem(f'console: {m.text[:200]}'))

    async def ready():
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await page.wait_for_timeout(500)

    async def cmd(action, payload=None):
        return await page.evaluate(CMD, [action, payload or {}, cid])

    async def check(label: str):
        out['checks'] += 1
        for p in await page.evaluate(CHECK, label):
            problem(f'{label}: {p}')
        if shots:
            await page.screenshot(path=str(shots / f'{engine}-{lang}-{cid}-{out["checks"]:03d}.png'))

    try:
        await page.goto(base)
        await ready()
        await cmd('settings', {'lang': lang})
        await cmd('select_career')
        st = await page.evaluate("fetch('/api/state').then(r=>r.json())")
        job = st['state']['careers'][cid].get('job') or {}
        if job.get('required') and job.get('status') != 'hired':
            boot = await page.evaluate("fetch('/api/bootstrap').then(r=>r.json())")
            post = ((boot['content'].get('employment') or {}).get('postings', {}).get(cid) or [{}])[0].get('id')
            await cmd('job_quick', {'posting': post, 'confirm': True})
        await cmd('start_day')
        await page.reload()
        await ready()
        await check('main')
        done_ids: set[str] = set()
        current = None
        steps = 0
        while len(done_ids) < tasks and steps < max_steps:
            info = await page.evaluate(TASKS, cid)
            done_ids = set(info['done'])
            if len(done_ids) >= tasks:
                break
            if not info['live']:
                # Out of work: close the day, open the next one.
                with contextlib.suppress(Exception):
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                if info['open']:
                    await cmd('end_day', {'carry_event': True})
                r = await cmd('start_day')
                if r['status'] != 200:
                    out['notes'].append(f'start_day: {r["error"]}')
                    break
                await page.reload()
                await ready()
                current = None
                continue
            live = {t['id']: t for t in info['live']}
            if current not in live:
                current = next(iter(live))
                out['tasks'].append(f'{live[current]["kind"]}: {live[current]["title"]}')
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate(OPEN_JOB, current)
                await page.wait_for_timeout(700)
                await check(f'task{len(out["tasks"])}-open')
                if len(out['tasks']) == 1:
                    # Back to the tab (iOS resume): the open sheet is written whole again (app.js repaintSheet).
                    await page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                    await page.wait_for_timeout(400)
                    await check('task1-back-to-tab')
            pick = await page.evaluate(PICK)
            if pick['kind'] in ('none', 'scene'):
                # Nothing glows in this sheet: report the dead end and move on to another task.
                out['notes'].append(f'no next step in "{live[current]["title"]}" ({pick.get("hint") or pick.get("text", "")[:80]})')
                await cmd('defer', {'task': current})
                current = None
                steps += 1
                continue
            sel = pick.get('sel') or '[data-fd-pick]'
            await page.eval_on_selector(sel, 'e=>e.click()')
            await page.wait_for_timeout(650)
            steps += 1
            await check(f'task{len(out["tasks"])}-step{steps}-{pick["kind"]}')
        out['tasks_done'] = len(done_ids)
        if steps >= max_steps:
            out['notes'].append(f'stopped after {max_steps} presses')
    except Exception as e:  # noqa: BLE001 — a crash is a problem of this run, not of the sweep
        problem(f'error: {str(e)[:300]}')
        with contextlib.suppress(Exception):
            if shots:
                await page.screenshot(path=str(shots / f'{engine}-{lang}-{cid}-error.png'))
    await ctx.close()
    await browser.close()
    out['problems'] = [f'[{tag}] {p}' for p in out['problems']]
    return out


async def run(base: str, engines: list[str], careers: list[str], langs: list[str], tasks: int, shots: Path | None, max_steps: int) -> dict:
    from playwright.async_api import async_playwright
    report = dict(base=base, runs=[], problems=[])
    async with async_playwright() as pw:
        for engine in engines:
            for lang in langs:
                for cid in careers:
                    r = await play(pw, engine, base, cid, lang, tasks, shots, max_steps)
                    report['runs'].append(r)
                    report['problems'] += r['problems']
                    state = 'PASS' if not r['problems'] else 'FAIL'
                    print(f"{state} {engine}/{lang}/{cid}: {r.get('tasks_done', 0)} tasks, {r['checks']} checks", flush=True)
                    for p in r['problems'][:12]:
                        print('   !', p, flush=True)
                    for n in r['notes'][:4]:
                        print('   ~', n, flush=True)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', help='use a running MNL_DEV=1 server instead of starting one')
    ap.add_argument('--engines', default='chromium,webkit')
    ap.add_argument('--careers', default=','.join(DEFAULT))
    ap.add_argument('--lang', default='vi', choices=['vi', 'en', 'both'])
    ap.add_argument('--tasks', type=int, default=3, help='tasks to play per career')
    ap.add_argument('--max-steps', type=int, default=160, help='presses per career before giving up')
    ap.add_argument('--shots', type=Path, help='directory for a screenshot after every check')
    ap.add_argument('--report', type=Path, default=ROOT / 'artifacts' / 'browser-text-check.json')
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    langs = ['vi', 'en'] if a.lang == 'both' else [a.lang]
    engines = [x for x in a.engines.split(',') if x]
    careers = [x for x in a.careers.split(',') if x]
    with (contextlib.nullcontext(a.base) if a.base else server()) as base:
        report = asyncio.run(run(base, engines, careers, langs, a.tasks, a.shots, a.max_steps))
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{len(report['runs'])} runs, {len(report['problems'])} problems")
    sys.exit(1 if report['problems'] else 0)


if __name__ == '__main__':
    main()
