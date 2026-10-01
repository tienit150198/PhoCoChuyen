#!/usr/bin/env python3
"""Tutorial browser check (dev tool, needs `pip install playwright` + chromium).

Starts a production-like server (journey story ON, MNL_DEV off) and, on a
phone (390×844) and a desktop (1280×800):

1. plays the whole first-run tour as a brand-new player: welcome card →
   every coach mark, doing the highlighted thing where the tour waits for it,
   and checks each spotlight rings the element it should;
2. "Bỏ qua" (skip) and "Tự khám phá" (explore) end it and remember it;
3. "Xem lại hướng dẫn" from Cài đặt → Xem hướng dẫn (the menu/rail no longer list the guides);
4. the guide: overview, every storefront's "Cách làm", the "?" on a work screen;
5. the first time at a workplace: one "Xem hướng dẫn / Bỏ qua" card, once per workplace, never at a
   brand-new player's first workplace.

Fails on console errors, uncaught exceptions or horizontal overflow.
Screenshots of every step go to --shots.
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
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_v04 import OVERFLOW  # noqa: E402

VIEWPORTS = {'phone': (390, 844, True), 'desktop': (1280, 800, False)}
CAREERS = ['milk_tea', 'grocery', 'delivery', 'cafe_bakery', 'florist']   # the guide's "Cách làm" pages
# What the spotlight should ring on each step (any match counts).
EXPECT = {
    'street': ['#sheet .jr-street'],
    'who': ['#sheet .jr-who', '#sheet .jr-intro .btn.primary'],
    'journey': ['#jrHud', '#rail [data-action="home"]', '.brand'],
    'pick': ['#sheet .jr-first-jobs .jr-job', '#sheet .jr-cta', '#sheet [data-action="choose"]'],
    'open': ['#sheet [data-action="start"]', '#taskHUD [data-action="prepare"]'],
    'money': ['#topbar .hud-fund', '#topbar .cozy-till'],
    'wallet': ['#jrHud .jr-hud-wallet', '#jrHud', '#topbar .hud-wallet', '#topbar .hud-day'],
    'task': ['#taskHUD .task-card', '#taskHUD .note-card'],
    'do': ['#sheet .sheet-body .btn.primary', '#sheet .sheet-body [data-command]'],
    'close': [],
}
STATE = """()=>{const L=document.getElementById('tutLayer');if(!L||!L.isConnected||L.hidden)return null;
  const s=L.querySelector('.tut-spot'),b=L.querySelector('.tut-bubble');
  const r=s.hidden?null:s.getBoundingClientRect(),br=b.getBoundingClientRect();
  return {step:L.dataset.step,text:L.querySelector('.tut-text')?.textContent,spot:r&&[r.left,r.top,r.width,r.height],
    bubble:[br.left,br.top,br.width,br.height],host:L.parentElement.id||L.parentElement.tagName};}"""
RINGS = """([sels,spot])=>{if(!spot)return false;const [x,y,w,h]=spot,cx=x+w/2,cy=y+h/2;
  for(const sel of sels)for(const e of document.querySelectorAll(sel)){const r=e.getBoundingClientRect();
    if(r.width&&Math.abs(r.left+r.width/2-cx)<3&&Math.abs(r.top+r.height/2-cy)<3)return true;}return false;}"""


@contextlib.contextmanager
def story_server():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    tmp = tempfile.mkdtemp(prefix='mnl-tut-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'LLM_API_KEY', 'MNL_CAREERS'):
        env.pop(k, None)
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


class Run:
    def __init__(self, page, name, shots: Path | None):
        self.page, self.name, self.shots, self.n = page, name, shots, 0
        self.problems: list[str] = []
        self.log: list[str] = []
        page.on('console', lambda m: m.type == 'error' and self.problem(f'console: {m.text[:200]}'))
        page.on('pageerror', lambda e: self.problem(f'exception: {str(e)[:200]}'))

    def problem(self, t):
        self.problems.append(f'[{self.name}] {t}')

    async def wait(self, ms=450):
        await self.page.wait_for_timeout(ms)

    async def shot(self, label):
        self.n += 1
        info = await self.page.evaluate(OVERFLOW)
        if info['page'] or info['over']:
            self.problem(f'overflow at {label}: {info}')
        if self.shots:
            await self.page.screenshot(path=str(self.shots / f'{self.name}-{self.n:02d}-{label}.png'))

    async def click(self, sel):
        el = await self.page.query_selector(sel)
        if not el:
            self.problem(f'missing {sel}')
            return False
        await el.evaluate('e=>e.click()')
        await self.wait()
        return True

    async def tour(self):
        return await self.page.evaluate(STATE)

    async def flags(self):
        return await self.page.evaluate("""async()=>{const st=await fetch('/api/state').then(r=>r.json());
          let ls={};try{ls={done:localStorage.getItem('mnl.tut.done'),notes:localStorage.getItem('mnl.notes.seen'),run:localStorage.getItem('mnl.tut.run')};}catch{}
          return {ls,settings:{tutorialDone:st.state.settings.tutorialDone,notesSeen:st.state.settings.notesSeen}};}""")


async def fresh(browser, name, w, h, touch, shots, base):
    ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=touch, is_mobile=touch and w < 700)
    page = await ctx.new_page()
    r = Run(page, name, shots)
    await page.goto(base)
    await page.wait_for_selector('#app:not([hidden])', timeout=20000)
    await r.wait(900)
    return ctx, page, r


async def play_tour(r: Run):
    """Welcome → start → every step, doing what the bubble asks."""
    p = r.page
    if not await p.query_selector('#tutWelcome[open]'):
        r.problem('no welcome card for a brand-new player')
        return
    await r.shot('welcome')
    await r.click('#tutWelcome [data-tut-w="start"]')
    await r.wait(700)
    seen = []
    for _ in range(40):
        st = await r.tour()
        if not st:
            break
        step = st['step']
        if not seen or seen[-1] != step:
            seen.append(step)
            await r.shot(f'tour-{step}')
            ok = step == 'close' or not EXPECT.get(step) or await p.evaluate(RINGS, [EXPECT[step], st['spot']])
            r.log.append(f"{step}: ring={'ok' if ok else 'MISS'} host={st['host']} text={st['text']!r}")
            if not ok:
                r.problem(f'step {step} rings the wrong element: {st}')
        # Do the highlighted thing (like a player would).
        if step == 'who':
            if await p.query_selector('#sheet [data-action="jrStep"][data-step="who"]'):
                await r.click('#sheet [data-action="jrStep"][data-step="who"]')
            else:
                await r.click('#sheet [data-action="jrGender"][data-gender="female"]')
                await p.fill('#jr-name', 'Mây')
                await r.click('#sheet form[data-jr-form] button[type=submit]')
                await r.wait(600)
        elif step == 'journey':
            await r.click('#jrHud:not([hidden])') or await r.click('#rail [data-action="home"]')
        elif step == 'pick':
            await r.click('#sheet [data-action="choose"][data-career="milk_tea"]')
            await r.wait(900)
        elif step == 'open':
            await r.click('#sheet [data-action="start"]')
            await r.wait(900)
        elif step == 'task':
            await r.click('#taskHUD .task-card .btn.primary')
            await r.wait(700)
        elif step == 'do':
            spot = st['spot']
            el = await p.evaluate_handle("""([x,y,w,h])=>document.elementFromPoint(x+w/2,y+h/2)?.closest('button')""", spot)
            await el.evaluate('e=>e&&e.click()')
            await r.wait(900)
        else:
            await r.click('#tutLayer [data-tut="next"]')
        await r.wait(300)
    r.log.append('steps: ' + ' → '.join(seen))
    await r.wait(600)
    await r.shot('tour-finished')
    f = await r.flags()
    if f['ls'].get('done') != '1' or f['settings'].get('tutorialDone') is not True:
        r.problem(f'tour end not remembered: {f}')
    await r.wait(2500)
    if await r.page.query_selector('.tut-note:not([hidden])'):
        r.problem('guide card shown at a brand-new player\'s first workplace')
    return seen


async def main_run(base, shots: Path | None):
    from playwright.async_api import async_playwright
    report = dict(problems=[], logs={})
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for vname, (w, h, touch) in VIEWPORTS.items():
            # 1) the whole tour as a brand-new story player
            ctx, page, r = await fresh(browser, f'{vname}-tour', w, h, touch, shots, base)
            await play_tour(r)
            # Replay from Cài đặt → Cách chơi (calm screen: the day opens the status sheet, Cài đặt is in it).
            await r.click('#topbar [data-action="status"]')
            await r.click('#sheet [data-action="settings"]')
            await r.shot('settings-play')
            await r.click('#sheet .tut-settings [data-action="tutGuide"]')
            await r.click('#tutGuide [data-action="tutReplay"]')
            await r.wait(900)
            st = await r.tour()
            r.log.append(f'replay from settings: {st and st["step"]}')
            if not st:
                r.problem('replay from settings did not start the tour')
            await r.shot('replay-settings')
            await r.click('#tutLayer [data-tut="skip"]')
            # The Thêm menu (phone) / rail (desktop) no longer lists the guides.
            if vname == 'phone':
                await r.click('#dock [data-action="v4Menu"]')
                await r.shot('menu')
            if await page.query_selector('#rail [data-action="help"], #rail [data-action="tutReplay"]'):
                r.problem('the menu still lists the guides')
            await page.keyboard.press('Escape')
            await r.wait(300)
            # The guide: overview, every storefront, the "?" on a work screen.
            await r.click('#topbar [data-action="status"]')
            await r.click('#sheet [data-action="settings"]')
            await r.click('#sheet .tut-settings [data-action="tutGuide"]')
            await r.shot('guide-play')
            await page.evaluate("document.querySelector('#tutGuide').scrollTop=900")
            await r.wait(300)
            await r.shot('guide-play-2')
            await r.click('#tutGuide [data-tut-tab="work"]')
            for cid in CAREERS:
                await r.click(f'#tutGuide [data-tut-career="{cid}"]')
                await r.shot(f'guide-{cid}')
                # The pictures load lazily (only near the viewport): load them all now, then look for missing files.
                await page.evaluate("document.querySelectorAll('#tutGuide img[loading=\"lazy\"]').forEach(i=>{i.loading='eager';})")
                for _ in range(25):
                    if await page.evaluate("[...document.querySelectorAll('#tutGuide img')].every(i=>i.complete)"):
                        break
                    await r.wait(200)
                broken = await page.evaluate("[...document.querySelectorAll('#tutGuide img')].filter(i=>!i.naturalWidth).map(i=>i.src)")
                if broken:
                    r.problem(f'broken pictures: {broken}')
            await r.click('#tutGuide [data-tut-close]')
            await r.click('#taskHUD .task-card .btn.primary')
            await r.wait(600)
            if not await r.click('#sheet .tut-help'):
                r.problem('no "?" on the work screen')
            else:
                await r.shot('work-help')
                sel = await page.evaluate("document.querySelector('#tutGuide [data-tut-career].selected')?.dataset.tutCareer")
                if sel != 'milk_tea':
                    r.problem(f'"?" opened {sel}, not milk_tea')
                await r.click('#tutGuide [data-tut-close]')
                if not await page.evaluate("document.querySelector('#sheet').open"):
                    r.problem('closing the guide lost the work screen')
            report['logs'][r.name] = r.log
            report['problems'] += r.problems
            await ctx.close()

            # 2) Bỏ qua in the middle of the tour
            ctx, page, r = await fresh(browser, f'{vname}-skip', w, h, touch, shots, base)
            await r.click('#tutWelcome [data-tut-w="start"]')
            await r.click('#tutLayer [data-tut="next"]')
            await r.shot('before-skip')
            await r.click('#tutLayer [data-tut="skip"]')
            await r.shot('after-skip')
            if await r.tour():
                r.problem('Bỏ qua did not end the tour')
            f = await r.flags()
            if f['ls'].get('done') != '1' or f['settings'].get('tutorialDone') is not True:
                r.problem(f'skip not remembered: {f}')
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])')
            await r.wait(1500)
            if await page.query_selector('#tutWelcome[open]') or await r.tour():
                r.problem('welcome/tour came back after Bỏ qua')
            report['problems'] += r.problems
            await ctx.close()

            # 3) Tự khám phá on the welcome card
            ctx, page, r = await fresh(browser, f'{vname}-explore', w, h, touch, shots, base)
            await r.click('#tutWelcome [data-tut-w="explore"]')
            await r.shot('after-explore')
            f = await r.flags()
            if f['ls'].get('done') != '1' or await r.tour():
                r.problem(f'explore not remembered: {f}')
            report['problems'] += r.problems
            await ctx.close()

            # 3b) A workplace that hires first (delivery): the tour points at the job form, never gets stuck.
            if vname == 'phone':
                ctx, page, r = await fresh(browser, f'{vname}-hire', w, h, touch, shots, base)
                await r.click('#tutWelcome [data-tut-w="start"]')
                await r.click('#tutLayer [data-tut="next"]')
                await r.click('#sheet [data-action="jrStep"][data-step="who"]')
                await r.click('#sheet [data-action="jrGender"][data-gender="male"]')
                await page.fill('#jr-name', 'Nam')
                await r.click('#sheet form[data-jr-form] button[type=submit]')
                await r.wait(700)
                await r.click('#sheet [data-action="choose"][data-career="delivery"]')
                await r.wait(1200)
                st = await r.tour()
                # Story day one hires a chapter-1 player at once (no CV + trial): then the tour goes straight on.
                job = await page.evaluate("fetch('/api/state').then(r=>r.json()).then(s=>(s.state.careers.delivery.job||{}).status||null)")
                r.log.append(f"hire: {st and st['step']} ring={st and st['spot'] is not None} job={job}")
                want = ('open',) if job == 'hired' else ('hire',)
                if not st or st['step'] not in want or not st['spot']:
                    r.problem(f'hiring workplace (job {job}): expected the {want[0]} step, got {st}')
                await r.shot('hire')
                for _ in range(8):   # "Tiếp" through to the end: never stuck
                    if not await r.tour():
                        break
                    await r.click('#tutLayer [data-tut="next"]')
                if await r.tour():
                    r.problem('tour stuck on a hiring workplace')
                report['logs'][r.name] = r.log
                report['problems'] += r.problems
                await ctx.close()

            # 4) The first time at each workplace: one "Xem hướng dẫn / Bỏ qua" card, once per workplace (on every
            #    device: settings.notesSeen), never at a brand-new player's first workplace.
            ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=touch, is_mobile=touch and w < 700)
            page = await ctx.new_page()
            r = Run(page, f'{vname}-guidecard', shots)
            await page.goto(base + '/privacy')
            CMDJS = """async([action,payload,career])=>{const b=await fetch('/api/bootstrap').then(r=>r.json());
              const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':b.csrf},
                body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:b.revision,career,action,payload})});return (await r.json()).error||null;}"""
            for c in (['jr_profile', {'name': 'Lan', 'gender': 'female'}, 'milk_tea'], ['select_career', {}, 'grocery'], ['start_day', {}, 'grocery']):
                if err := await page.evaluate(CMDJS, c):
                    r.problem(f'setup {c[0]}: {err}')
            await page.evaluate("try{localStorage.setItem('mnl.tut.done','1')}catch{}")   # the tour/tips are another check

            async def card(goto=None):
                if goto:
                    if err := await page.evaluate(CMDJS, ['select_career', {'confirm': True}, goto]):
                        r.problem(f'select {goto}: {err}')
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])')
                await page.evaluate("document.querySelectorAll('#sheet[open]').forEach(d=>d.close())")
                for _ in range(12):
                    if await page.query_selector('.tut-note:not([hidden])'):
                        return await page.evaluate("document.querySelector('.tut-note').dataset.note")
                    await r.wait(300)
                return None

            if (k := await card()) is not None:
                r.problem(f'card at the first workplace of a new player: {k}')
            if (k := await card('cafe_bakery')) != 'guide:cafe_bakery':
                r.problem(f'no card at a second workplace: {k}')
            await r.shot('guide-card')
            await r.click('.tut-note [data-note="later"]')   # Bỏ qua
            if (k := await card()) is not None:
                r.problem(f'card came back after Bỏ qua: {k}')
            if (k := await card('florist')) != 'guide:florist':
                r.problem(f'no card at a third workplace: {k}')
            await r.click('.tut-note [data-note="go"]')   # Xem hướng dẫn
            await r.wait(600)
            sel = await page.evaluate("document.querySelector('#tutGuide[open] [data-tut-career].selected')?.dataset.tutCareer")
            if sel != 'florist':
                r.problem(f'"Xem hướng dẫn" opened {sel}, not florist')
            await r.shot('guide-card-go')
            for back in (None, 'cafe_bakery', 'florist'):
                if (k := await card(back)) is not None:
                    r.problem(f'card came back ({back or "reload"}): {k}')
            f = await r.flags()
            if 'gd-' not in (f['settings'].get('notesSeen') or ''):
                r.problem(f'guide cards not synced to settings: {f}')
            report['problems'] += r.problems
            await ctx.close()
        await browser.close()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', type=Path, help='directory for screenshots')
    ap.add_argument('--report', type=Path, help='write the JSON report here')
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    with story_server() as base:
        report = asyncio.run(main_run(base, a.shots))
    if a.report:
        a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for name, lines in report['logs'].items():
        print(name)
        for line in lines:
            print('  ', line)
    for p in report['problems']:
        print('PROBLEM', p)
    print(f"{len(report['problems'])} problems")
    sys.exit(1 if report['problems'] else 0)


if __name__ == '__main__':
    main()
