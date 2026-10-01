#!/usr/bin/env python3
"""Tutorial browser check (dev tool, needs `pip install playwright` + chromium).

Starts a production-like server (journey story ON, MNL_DEV off) and, on a
phone (390×844) and a desktop (1280×800), checks how players learn the game
since 0.9.16 (no welcome card, no tour unless asked for):

1. a brand-new player: the one-screen intro (look, name, first workplace,
   milk tea recommended), no welcome card, no tour; day 1 opens straight into
   the first customer with the first-day tip on the button to press; the tips
   survive a reload; the first customer done, the tips move on; no guide card
   at this first workplace;
2. the "?" of the work screen opens that workplace's guide;
3. Cài đặt has one quiet "Xem hướng dẫn" link and nothing else; the guide's
   first page replays the tour (it rings the right things; "Bỏ qua" ends it);
   every storefront's "Cách làm" with its pictures;
4. the Thêm menu (phone) / rail (desktop) no longer lists the guides;
5. a workplace that hires first (delivery) through the intro: hired at once,
   the first-day tip shows (phone);
6. the first time at a workplace: one "Xem hướng dẫn / Bỏ qua" card, once per
   workplace, from the second workplace on.

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
from browser_first_day import PICK, STATE as ROOM  # noqa: E402

VIEWPORTS = {'phone': (390, 844, True), 'desktop': (1280, 800, False)}
CAREERS = ['milk_tea', 'grocery', 'delivery', 'cafe_bakery', 'florist']   # the guide's "Cách làm" pages
# What the spotlight should ring on each step (any match counts).
EXPECT = {
    'street': ['#sheet .jr-street'],
    'who': ['#sheet .jr-who', '#sheet .jr-intro .btn.primary'],
    'journey': ['#jrHud', '#rail [data-action="home"]', '.brand', '#dock [data-action="v4Menu"]'],
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


# Tour steps done by the player (the ring is on the control to press); the others are read and passed with "Tiếp".
ACT = {'journey', 'pick', 'open', 'task', 'do'}
TIP = """()=>{const b=[...document.querySelectorAll('.tut-layer.tips')].find(x=>!x.hidden&&x.isConnected);if(!b)return null;
  const s=b.querySelector('.tut-spot').getBoundingClientRect();
  return {id:b.dataset.tip,text:b.querySelector('.tut-text')?.textContent||'',spot:[s.left,s.top,s.width,s.height],host:b.parentElement.id||b.parentElement.tagName};}"""
TIPS_SAVED = "()=>{try{return localStorage.getItem('mnl.tut.tips')}catch{return 'blocked'}}"


async def wait_tip(r: Run, want=None, ms=6000):
    """The first-day tip bubble on screen (`want`: its id), or None."""
    for _ in range(ms // 200):
        t = await r.page.evaluate(TIP)
        if t and (want is None or t['id'] == want):
            return t
        await r.wait(200)
    return None


async def no_old_guidance(r: Run, where: str):
    """0.9.16 on: no welcome card, no tour that starts by itself, no guide card at a new player's first place."""
    p = r.page
    if await p.query_selector('#tutWelcome[open]'):
        r.problem(f'{where}: the old welcome card is back')
    if await r.tour():
        r.problem(f'{where}: the tour started by itself')
    if await p.query_selector('.tut-note:not([hidden])'):
        r.problem(f'{where}: guide card at a brand-new player\'s first workplace')


async def intro(r: Run, cid='milk_tea', name='Mây'):
    """The one-screen intro: look, name, first workplace (milk tea recommended), "Vào làm thôi"."""
    p = r.page
    if not await p.query_selector('#sheet[open] .onb-intro form[data-jr-form="start"]'):
        r.problem('no one-screen intro for a brand-new player')
        return False
    await no_old_guidance(r, 'intro')
    await r.shot('intro')
    rec = await p.get_attribute('.onb-job.active', 'data-career')
    if rec != 'milk_tea':
        r.problem(f'the recommended first workplace is {rec!r}, not milk_tea')
    await r.click('#sheet [data-action="jrGender"][data-gender="female"]')
    await p.fill('#jr-name', name)
    if cid != rec:
        await r.click(f'#sheet .onb-job[data-career="{cid}"]')
    await r.click('#sheet form[data-jr-form="start"] button[type=submit]')
    for _ in range(40):
        st = await p.evaluate(ROOM, cid)
        if st['open'] and st['current'] == cid:
            return st
        await r.wait(250)
    r.problem(f'day 1 at {cid} did not open by itself after the intro')
    return False


async def new_player(r: Run):
    """A brand-new player through the first customer: the tips teach it, nothing else does."""
    p = r.page
    if not await intro(r):
        return
    await r.wait(700)
    if await p.query_selector('#sheet[open].prep-sheet, #wnDialog[open]'):
        r.problem('"Chuẩn bị" or "Có gì mới" is in the way of the first customer')
    if not await p.query_selector('#sheet[open]'):
        await r.click('#taskHUD .task-card .btn.primary')
    t = await wait_tip(r, 'work')
    if not t:
        r.problem(f'no first-day tip on the work screen (tips saved: {await p.evaluate(TIPS_SAVED)})')
        return
    r.log.append(f"tip work: {t['text']!r} host={t['host']}")
    await r.shot('tip-work')
    if t['host'] != 'sheet':
        r.problem(f'the work tip is not over the work screen: {t}')
    rung = await p.evaluate("""([x,y,w,h])=>{const e=document.elementFromPoint(x+w/2,y+h/2);return !!e?.closest('#sheet[open] button, #sheet[open] [data-command], #sheet[open] [data-action]')}""", t['spot'])
    if not rung:
        r.problem(f'the work tip rings no control of the work screen: {t}')
    await no_old_guidance(r, 'first customer')
    # A reload in the middle: the tips pick up where they were, still no welcome card or tour.
    await p.reload()
    await p.wait_for_selector('#app:not([hidden])')
    await r.wait(1200)
    if await p.evaluate(TIPS_SAVED) != 'work':
        r.problem(f'tips progress lost on reload: {await p.evaluate(TIPS_SAVED)!r}')
    await no_old_guidance(r, 'reload')
    if not await p.query_selector('#sheet[open]'):
        await r.click('#taskHUD .task-card .btn.primary')
    if not await wait_tip(r, 'work'):
        r.problem('the work tip did not come back after a reload')
    # Press what the game highlights (like browser_first_day) until the first customer is served.
    for _ in range(60):
        st = await p.evaluate(ROOM, 'milk_tea')
        if st['served'] >= 1:
            break
        pick = await p.evaluate(PICK)
        if pick['kind'] == 'none':
            r.problem(f'stuck on the first customer: {pick}')
            return
        await p.eval_on_selector(pick.get('sel') or '[data-fd-pick]', 'e=>e.click()')
        await r.wait(650)
    else:
        r.problem('the first customer was not served in 60 presses')
        return
    await r.wait(1200)
    saved = await p.evaluate(TIPS_SAVED)
    now = await p.evaluate(TIP)
    r.log.append(f"after the first customer: tips at {saved!r}, bubble {now and now['id']!r}")
    if saved == 'work' or (now and now['id'] == 'work'):
        r.problem(f'the work tip did not move on after the first customer: {saved!r}')
    await r.shot('first-customer-done')
    await no_old_guidance(r, 'first customer done')


async def work_help(r: Run, cid='milk_tea'):
    """The "?" in the work screen's header opens this workplace's guide; closing it keeps the work screen."""
    p = r.page
    if not await p.query_selector('#sheet[open]'):
        await r.click('#taskHUD [data-action="job"]')
        await r.wait(600)
    if not await p.query_selector('#sheet[open] .sheet-head .tut-help'):
        r.problem('no "?" in the work screen header')
        return
    await r.click('#sheet .sheet-head .tut-help')
    await r.wait(700)
    await r.shot('work-help')
    sel = await p.evaluate("document.querySelector('#tutGuide[open] [data-tut-career].selected')?.dataset.tutCareer")
    if sel != cid:
        r.problem(f'"?" opened {sel}, not {cid}')
    await r.click('#tutGuide [data-tut-close]')
    if not await p.evaluate("document.querySelector('#sheet').open"):
        r.problem('closing the guide lost the work screen')


async def settings_guide(r: Run, vname: str):
    """Cài đặt: one quiet link to the guide. The guide: its first page replays the tour; every storefront."""
    p = r.page
    await p.evaluate("document.querySelectorAll('#sheet[open]').forEach(d=>d.close())")
    await r.click('#topbar [data-action="status"]')
    await r.click('#sheet [data-action="settings"]')
    await r.wait(500)
    links = await p.evaluate("[...document.querySelectorAll('#sheet[open] .tut-settings [data-action]')].map(e=>e.dataset.action)")
    r.log.append(f'Cài đặt guide links: {links}')
    if links != ['tutGuide']:
        r.problem(f'Cài đặt should keep one quiet "Xem hướng dẫn" link, has {links}')
    await r.shot('settings')
    await r.click('#sheet .tut-settings [data-action="tutGuide"]')
    if not await p.query_selector('#tutGuide[open]'):
        r.problem('"Xem hướng dẫn" in Cài đặt did not open the guide')
        return
    await r.shot('guide-play')
    await r.click('#tutGuide [data-tut-tab="work"]')
    for cid in CAREERS:
        await r.click(f'#tutGuide [data-tut-career="{cid}"]')
        await r.shot(f'guide-{cid}')
        # The pictures load lazily (only near the viewport): load them all now, then look for missing files.
        await p.evaluate("document.querySelectorAll('#tutGuide img[loading=\"lazy\"]').forEach(i=>{i.loading='eager';})")
        for _ in range(25):
            if await p.evaluate("[...document.querySelectorAll('#tutGuide img')].every(i=>i.complete)"):
                break
            await r.wait(200)
        broken = await p.evaluate("[...document.querySelectorAll('#tutGuide img')].filter(i=>!i.naturalWidth).map(i=>i.src)")
        if broken:
            r.problem(f'broken pictures: {broken}')
    # The tour, on request only: "Xem lại hướng dẫn" on the guide's first page.
    await r.click('#tutGuide [data-tut-tab="play"]')
    await r.click('#tutGuide [data-action="tutReplay"]')
    await r.wait(900)
    st = await r.tour()
    if not st:
        r.problem('"Xem lại hướng dẫn" did not start the tour')
        return
    steps = []
    for _ in range(24):   # play it like a player: do what a ring asks, "Tiếp" on the look-only cards
        if not st:
            break
        if not steps or steps[-1] != st['step']:
            steps.append(st['step'])
            # A step whose control is not on this screen is a centred card (no ring): its bubble must be in view.
            b = st['bubble']
            ok = (0 <= b[0] and b[0] + b[2] <= p.viewport_size['width'] + 1) if not st['spot'] else \
                not EXPECT.get(st['step']) or await p.evaluate(RINGS, [EXPECT[st['step']], st['spot']])
            if not ok:
                r.problem(f'tour step {st["step"]} rings the wrong element: {st}')
            await r.shot(f'tour-{st["step"]}')
        if st['step'] == 'task':   # "Bấm Làm tiếp." rings the whole task card: press its button
            await r.click('#taskHUD .task-card .btn.primary')
            await r.wait(600)
        elif st['step'] in ACT and st['spot']:
            el = await p.evaluate_handle("""([x,y,w,h])=>document.elementFromPoint(x+w/2,y+h/2)?.closest('button,[data-action],[data-command]')""", st['spot'])
            await el.evaluate('e=>e&&e.click()')
            await r.wait(900)
        else:
            await r.click('#tutLayer [data-tut="next"]')
        await r.wait(300)
        for _ in range(15):   # a step that waits for its control (a sheet opening) is hidden meanwhile
            st = await r.tour()
            if st or not await p.evaluate("!!document.getElementById('tutLayer')?.isConnected"):
                break
            await r.wait(300)
    if len(steps) < 4:
        r.problem(f'the tour replay stopped early: {steps}')
    r.log.append('tour replay: ' + ' → '.join(steps))
    if st:
        await r.click('#tutLayer [data-tut="skip"]')
    if await r.tour():
        r.problem('"Bỏ qua" did not end the tour')
    f = await r.flags()
    if f['settings'].get('tutorialDone') is not True:
        r.problem(f'tour end not remembered: {f}')


async def menu_has_no_guides(r: Run, vname: str):
    p = r.page
    await p.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
    if vname == 'phone':
        await r.click('#dock [data-action="v4Menu"]')
        await r.shot('menu')
    if await p.query_selector('#rail [data-action="help"], #rail [data-action="tutReplay"], #rail [data-action="tutGuide"]'):
        r.problem('the menu still lists the guides')
    if not await p.query_selector('#rail [data-action="settings"]'):
        r.problem('Cài đặt is missing from the menu')
    await p.keyboard.press('Escape')
    await r.wait(300)


async def main_run(base, shots: Path | None):
    from playwright.async_api import async_playwright
    report = dict(problems=[], logs={})
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for vname, (w, h, touch) in VIEWPORTS.items():
            # 1–4) a brand-new story player
            ctx, page, r = await fresh(browser, f'{vname}-new', w, h, touch, shots, base)
            await new_player(r)
            await work_help(r)
            await settings_guide(r, vname)
            await menu_has_no_guides(r, vname)
            report['logs'][r.name] = r.log
            report['problems'] += r.problems
            await ctx.close()

            # 5) A workplace that hires first (delivery), picked on the intro: hired at once, the tips teach it.
            if vname == 'phone':
                ctx, page, r = await fresh(browser, f'{vname}-hire', w, h, touch, shots, base)
                st = await intro(r, 'delivery', 'Nam')
                if st:
                    r.log.append(f"delivery: job={st['job']}")
                    if st['job'] != 'hired':
                        r.problem(f'story day one did not hire at delivery: {st}')
                    if not await page.query_selector('#sheet[open]'):
                        await r.click('#taskHUD .task-card .btn.primary')
                    if not await wait_tip(r, 'work'):
                        r.problem('no first-day tip at a hiring workplace')
                    await r.shot('hire')
                    await no_old_guidance(r, 'delivery')
                report['logs'][r.name] = r.log
                report['problems'] += r.problems
                await ctx.close()

            # 6) The first time at each workplace: one "Xem hướng dẫn / Bỏ qua" card, once per workplace (on every
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
