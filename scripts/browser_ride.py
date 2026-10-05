#!/usr/bin/env python3
"""🛵 Đi xe quanh phố: a browser walk-through (dev tool, needs `pip install playwright websockets` + chromium).

Starts a game server (story mode, PostgreSQL, the hội chợ open today) and the live service (LIVE_STREET=1, so the fair's
crowd too) on the same database, then plays two players, at 390x844 (a phone) and 1280x800:
  * Lan owns a scooter (pink, plate "MÂY 01") and an SUV; Minh owns nothing;
  * the town (the home screen): Lan rides (the toggle shows "🛵 Đi xe"), goes to a shop's door: the scooter is parked
    beside it and Lan walks the last steps; the next walk hops back on; the toggle goes SUV → walking → scooter and
    survives a reload (localStorage); Minh walks, has no toggle, and the garage's card says "Mua xe để chạy quanh phố";
  * the fair: Lan rides the scooter through the fairground (two-wheelers only), parks at a stall; Minh, on the same
    fairground, sees Lan riding (the optional `r` of the crowd's walks);
  * Đi dạo (the strolls): Lan rides there too and Minh sees it (the optional `r` of the street's people, and the
    rider's own speed `v`); toggling to walking mid-stroll reaches Minh too;
  * frame times of the town while riding stay well under a frame (median and 95th percentile printed).
Screenshots of each step; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    MNL_PY=<python with the server's requirements> python scripts/browser_ride.py [out_dir] [--one]
(--one: the phone size only)
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import free_port, wait_http  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else ROOT.parent / '_ride_shots'
VN = datetime.timezone(datetime.timedelta(hours=7))
PY = os.environ.get('MNL_PY', sys.executable)   # the servers' Python (the live service needs a recent websockets)
TOWN = "()=>globalThis.__townWalk?.state()"
FAIR = "()=>globalThis.__fairWalk?.state()"
WALK = "async () => (await import('/js/v4/walk.js')).walk.state()"


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.db')
    env = test_env( QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live',
               MNL_FAIR_START=datetime.datetime.now(VN).date().isoformat())
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    glog = open(os.path.join(tmp, 'game.log'), 'w')
    game = subprocess.Popen([PY, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env, stdout=glog, stderr=glog)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_STREET='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    llog = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([PY, '-m', 'live', '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=llog, stderr=llog)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        glog.close()
        llog.close()
        for name in ('game.log', 'live.log'):
            with contextlib.suppress(OSError):
                (OUT / name).write_text(Path(tmp, name).read_text(encoding='utf-8', errors='replace'), encoding='utf-8')


def seed(db: str, token: str, name: str, cars: list) -> None:
    """A named story-mode character on life day 20 who owns `cars` [(id, paint, plate)]."""
    from game import garage
    from game import marriage as mr
    from game import whats_new as wn
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        j = s['journey']
        s['name'] = name
        s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
        j.update(gender='female' if name == 'Lan' else 'male', intro=True, life_day=20, story=True)
        j['wallet'] = 20000
        for vid, color, plate in cars:
            garage.action(s, 'jr_garage_buy', dict(id=vid, color=color, plate=plate, confirm=True))
        j['wallet'] = 500
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


class Player:
    def __init__(self, ctx, page, name):
        self.ctx, self.page, self.name = ctx, page, name


async def player(browser, base, name, cars, size, problems) -> Player:
    w, h = size
    phone = w < 600
    ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=phone, is_mobile=phone, device_scale_factor=2 if phone else 1)
    page = await ctx.new_page()
    page.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and problems.append(f'{name} console: {m.text[:200]}'))
    page.on('pageerror', lambda e: problems.append(f'{name} exception: {str(e)[:200]}'))
    page.on('response', lambda r: r.status >= 500 and problems.append(f'{name} HTTP {r.status} {r.url}'))
    await page.goto(base + '/')
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
    seed(DB, token, name, cars)
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_timeout(1200)
    await popups(page)
    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
    return Player(ctx, page, name)


async def popups(page):
    """"Có gì mới", titles, the week's x3 card and other first-visit popups."""
    for _ in range(6):
        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, [data-x3="close"]:visible, [data-fh-key="giftok"]:visible')
        if not await b.count():
            break
        await b.first.click()
        await page.wait_for_timeout(400)


async def until(page, js: str, cond: str, what: str, timeout=8.0):
    end = time.monotonic() + timeout
    while True:
        s = await page.evaluate(js)
        if s is not None and await page.evaluate(f's => {{ {cond} }}', s):
            return s
        if time.monotonic() > end:
            raise AssertionError(f'{what} (state: {json.dumps(s, ensure_ascii=False)[:500]})')
        await asyncio.sleep(0.15)


async def act(page, action: str):
    await page.evaluate(f"(()=>{{const b=document.createElement('button');b.dataset.action='{action}';b.hidden=true;document.body.append(b);b.click();b.remove();}})()")


async def run(size, problems, checks) -> None:
    from playwright.async_api import async_playwright
    tag = f'{size[0]}x{size[1]}'

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + f' [{tag}] ' + what)
        if not cond:
            problems.append(f'check [{tag}]: ' + what)

    async def shot(p, name):
        await popups(p.page)
        await p.page.wait_for_timeout(350)
        await p.page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        lan = await player(browser, BASE, 'Lan', [('xe_ga', 'hong', 'MÂY 01'), ('o_to_suv', 'xanh', 'LAN 88')], size, problems)
        minh = await player(browser, BASE, 'Minh', [], size, problems)

        # ---- the town (the home screen) ----
        for p in (lan, minh):
            if not await p.page.evaluate("!!document.querySelector('#sheet[open] .tw-stage')"):
                await act(p.page, 'home')
            await until(p.page, TOWN, 'return s.on&&s.me', f'{p.name}: the town is up', 15)
        s = await lan.page.evaluate(TOWN)
        check(s['ride'] == 'xe_ga' and s['toggle'] and 'Đi xe' in s['toggle'], f'Lan rides her scooter in town ({s["ride"]}, {s["toggle"]!r})')
        s = await minh.page.evaluate(TOWN)
        check(s['ride'] is None and s['toggle'] is None, 'Minh (no vehicle) walks, no toggle')
        await shot(lan, '01-town-lan-at-start')
        # A shop's door some way off: ride there, park beside the door, walk in.
        key = await lan.page.evaluate("""()=>{const st=__townWalk.state();const ks=['lm:bank','lm:board','lm:garage','lm:fair'];return ks.find(k=>__townWalk.go(k))||null;}""")
        check(key is not None, f'Lan heads for a door ({key})')
        await lan.page.wait_for_timeout(250)
        s = await lan.page.evaluate(TOWN)
        check(s['riding'] and s['walking'], 'on the way she rides')
        await shot(lan, '02-town-riding')
        s = await until(lan.page, TOWN, 'return s.card&&!s.walking', 'Lan arrives at the door', 10)
        check(s['park'] is not None and not s['riding'], f'the scooter is parked by the door ({s["park"]}), Lan on foot')
        await shot(lan, '03-town-parked')
        await lan.page.evaluate("()=>__townWalk.go('lm:house')")
        await lan.page.wait_for_timeout(500)
        s = await lan.page.evaluate(TOWN)
        check(s['riding'] or s['walking'], 'the next walk hops back on')
        s = await until(lan.page, TOWN, 'return s.card&&!s.walking', 'Lan arrives home', 12)
        check(s['park'] is not None, 'parked by the house')
        frames = await lan.page.evaluate("()=>__townWalk.frames(true)")
        await lan.page.evaluate("()=>__townWalk.go('lm:bank')")
        await until(lan.page, TOWN, 'return s.card&&!s.walking', 'Lan rides to the bank', 12)
        frames = await lan.page.evaluate("()=>__townWalk.frames(true)")
        if frames:
            fs = sorted(frames)
            med, p95 = fs[len(fs) // 2], fs[int(len(fs) * .95) - 1 if len(fs) > 1 else 0]
            checks.append(f'INFO [{tag}] town draw while riding: {len(fs)} frames, median {med:.2f} ms, p95 {p95:.2f} ms')
            check(p95 < 12, f'town frames stay light while riding (p95 {p95:.2f} ms)')
        # The toggle: SUV, then walking, then the scooter again; remembered over a reload.
        t1 = await lan.page.evaluate("()=>__townWalk.toggle()")
        check(t1 == 'o_to_suv', f'toggle → the SUV ({t1})')
        await lan.page.evaluate("()=>__townWalk.go('lm:board')")
        await lan.page.wait_for_timeout(500)
        await shot(lan, '04-town-suv')
        await until(lan.page, TOWN, 'return !s.walking', 'Lan drives to the board', 12)
        await shot(lan, '05-town-suv-parked')
        t2 = await lan.page.evaluate("()=>__townWalk.toggle()")
        s = await lan.page.evaluate(TOWN)
        check(t2 is None and s['toggle'] and 'Đi bộ' in s['toggle'] and s['park'] is None, f'toggle → walking ({s["toggle"]!r})')
        await lan.page.reload()
        await lan.page.wait_for_selector('#app:not([hidden])', timeout=30000)
        if not await lan.page.evaluate("!!document.querySelector('#sheet[open] .tw-stage')"):
            await act(lan.page, 'home')
        s = await until(lan.page, TOWN, 'return s.on&&s.me', 'the town after a reload', 15)
        check(s['ride'] is None and 'Đi bộ' in (s['toggle'] or ''), 'walking is remembered over a reload')
        t3 = await lan.page.evaluate("()=>__townWalk.toggle()")
        check(t3 == 'xe_ga', f'toggle → the scooter again ({t3})')
        # Minh: the garage's card has the soft line.
        await minh.page.evaluate("()=>__townWalk.go('lm:garage')")
        await until(minh.page, TOWN, 'return s.card&&!s.walking', 'Minh walks to the garage', 12)
        txt = await minh.page.inner_text('.tw-card')
        check('Mua xe để chạy quanh phố' in txt, 'the garage card tells Minh what a vehicle is for')
        await shot(minh, '06-town-minh-garage')

        # ---- the fair ----
        for p in (lan, minh):
            await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await act(p.page, 'fair')
            await p.page.wait_for_selector('.fh-sheet[open] .fh-wcanvas', timeout=15000)
            await until(p.page, FAIR, 'return s&&s.on&&s.me', f'{p.name}: the fairground is up', 10)
            await p.page.wait_for_timeout(600)
            await popups(p.page)   # the organisers' 500 xu, once
        s = await until(lan.page, FAIR, 'return s.ride', 'Lan rides at the fair', 5)
        check(s['ride'] == 'xe_ga', f'Lan rides the scooter at the fair ({s.get("ride")})')
        s = await minh.page.evaluate(FAIR)
        check(not s.get('ride') and not s.get('toggle'), 'Minh walks the fair, no toggle')
        await until(minh.page, FAIR, 'return s.crowd.on&&s.crowd.people.length>0', 'Minh sees Lan at the fair', 10)
        await lan.page.evaluate("()=>__fairWalk.walk(.8,.5)")
        await lan.page.wait_for_timeout(300)
        await shot(lan, '07-fair-riding')
        s = await until(minh.page, FAIR, 'return s.crowd.people.some(q=>q.ride==="xe_ga")', 'Minh sees Lan riding at the fair', 8)
        check(True, 'Minh sees Lan riding the scooter at the fair')
        await minh.page.wait_for_timeout(600)
        await shot(minh, '08-fair-minh-sees-lan')
        spot = await lan.page.evaluate("()=>__fairWalk.state().spots.find(x=>x==='nv'||x==='bc')")
        await lan.page.evaluate(f"()=>__fairWalk.go('{spot}')")
        await lan.page.wait_for_timeout(2500)
        s = await lan.page.evaluate(FAIR)
        check(s.get('park') is not None, f'the scooter waits by the stall ({spot}: {s.get("park")})')
        await lan.page.click('.fh-sheet .fh-back')   # ← Ra lối đi
        await until(lan.page, FAIR, 'return s.on&&!s.riding&&s.park', 'back on the walk: on foot beside the parked scooter', 6)
        await shot(lan, '09-fair-parked')
        await lan.page.evaluate("()=>__fairWalk.walk(.15,.6)")
        await lan.page.wait_for_timeout(900)
        s = await lan.page.evaluate(FAIR)
        check(s['riding'] and s['park'] is None, 'the next walk at the fair hops back on')
        await shot(lan, '09b-fair-hop-on')

        # ---- Đi dạo ----
        for p in (lan, minh):
            await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await act(p.page, 'liveWalk')
            await p.page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=15000)
        s = await until(lan.page, WALK, 'return s.room&&s.me', 'Lan strolls', 10)
        await until(minh.page, WALK, 'return s.room&&s.people.length>=2', 'Minh sees Lan on the stroll', 10)
        s = await until(minh.page, WALK, 'return s.people.some(q=>q.ride==="xe_ga")', 'Minh sees Lan on her scooter', 6)
        check(True, 'Minh sees Lan riding on the stroll')
        await lan.page.evaluate("async()=>{const {walk}=await import('/js/v4/walk.js');const st=walk.state(),m=st.people.find(q=>q.pid===st.me);walk.moveTo(m.x>300?120:480,m.y-60);}")
        await lan.page.wait_for_timeout(450)
        await shot(lan, '10-walk-riding')
        await shot(minh, '11-walk-minh-sees-lan')
        await lan.page.evaluate("()=>document.querySelector('.walk-sheet .rd-toggle')?.click()")   # → the SUV is a car: walking here
        s = await until(minh.page, WALK, 'return s.people.every(q=>!q.ride)', 'Minh sees Lan walking now', 6)
        check(True, 'toggling to walking reaches the others')
        await shot(lan, '12-walk-walking')
        for p in (lan, minh):
            await p.ctx.close()
        await browser.close()


async def main_async():
    problems, checks = [], []
    for size in SIZES:
        try:
            await run(size, problems, checks)
        except AssertionError as e:
            problems.append(f'{size}: {e}')
    print(*checks, sep='\n')
    return problems


def main():
    global BASE, DB
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mnl-ride-', dir=os.environ.get('TMPDIR'), ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db):
        BASE, DB = base, db
        problems = asyncio.run(main_async())
    if problems:
        print('problems:', *problems, sep='\n  ')
        sys.exit(1)
    print('ok:', OUT)


BASE = DB = ''
SIZES = ((390, 844), (1280, 800)) if '--one' not in sys.argv else ((390, 844),)
if __name__ == '__main__':
    main()
