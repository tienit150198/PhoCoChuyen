"""🎖️ Thăng tiến + 🧑‍💼 Ca quản lý: a browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server and seeds two saves straight in its database:
* an employee (giao hàng, step 2, the boss's review waiting): the morning card's strip opens the review, two
  answers and the pay ask make step 3, then the ladder opens a manager shift that is played to the end
  (assign by strength, check with ✅ / ↩️, settle the crisis, close) and the day closes;
* an owner (phở, step 3, one hired helper): the strip's 🧑‍💼 opens the ladder, a manager shift with the hired
  staff plus a temporary helper is played and closed.
Screenshots at 390x844 and 1280x800; any console error fails the run.

    python scripts/browser_promo.py [out_dir]
The server and the seeding run with MNL_PY (default: this interpreter), so playwright may live in another Python.
"""
import asyncio
import contextlib
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from pg_test_support import test_env, test_connect, schema_for

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'promo'
PY = os.environ.get('MNL_PY', sys.executable)


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-promo-')
    env = test_env( QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'p.db')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([PY, 'server.py', '--port', str(port), '--namespace', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:
            if p.poll() is not None:
                break
            time.sleep(0.1)
    try:
        yield base, db
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)
        log.close()


SEED = r'''
import sys
from game import marriage as mr
from game import promotion as pm
from game import operations as ops
from game.employment import hired_record
from game.journey import CH_UNLOCKS
from game.storage import Store
db, token, who = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=30, chapter=6, done=[1, 2, 3, 4, 5], wallet=900)
    for n in range(1, 7):
        for cid in CH_UNLOCKS.get(n, ()):
            if cid in s['careers'] and cid not in j['unlocked']:
                j['unlocked'].append(cid)
    s['settings']['tutorialDone'] = True
    c = s['careers'][who]
    c.update(started=True, day=12, day_start_money=c['money'])
    c['metrics']['served'] = 120
    rec = pm.new_record()
    if who == 'delivery':
        c['job'] = hired_record('delivery', None, 2)
        rec.update(emp=c['job']['employer'], hd=c['job']['hired_day'], rank=2, good=12, worked=13,
                   due=dict(to=3, day=12, qs=['t1', 't2'], ans={}),
                   log=[dict(d=10, to=1, pct=8), dict(d=20, to=2, pct=16)])
    else:
        rec.update(rank=3, good=4, worked=4, log=[dict(d=10, to=1, pct=3), dict(d=18, to=2, pct=6), dict(d=26, to=3, pct=9)])
        cand = ops.CANDIDATE_INDEX[who + '-staff-1']
        c['ops']['staff'].append(dict(cand, status='hired', hired_day=1, schedule='daily', on_shift=False, morale=85, fatigue=0,
                                      progress=0, jobs=0, errors=0, training=0, trained_day=0, bonus_day=0, rest_until=0,
                                      last_work='Chưa bắt đầu công việc.', warnings=0))
    j['promo'] = {who: rec}
    s['current'] = who
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''


def seed(db: str, token: str, who: str) -> None:
    subprocess.run([PY, '-c', SEED, db, token, who], cwd=ROOT, check=True)


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (1280, 800)):
                for who in ('delivery', 'pho'):
                    ctx = await browser.new_context(viewport=dict(width=w, height=h))
                    page = await ctx.new_page()
                    page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                    seed(db, token, who)
                    await page.reload()
                    try:
                        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    except Exception:
                        print('page errors:', errors)
                        raise
                    await page.wait_for_timeout(1500)
                    tag = f'{w}x{h}-{who}'

                    async def popups():
                        for _ in range(5):   # "Có gì mới", titles, the x3 week, story scenes
                            b = page.locator('[data-wn="close"]:visible, [data-x3="close"]:visible, [data-action="jrSceneClose"]:visible, '
                                             '[data-action="jrArcDismiss"]:visible')
                            if not await b.count():
                                return
                            await b.first.click()
                            await page.wait_for_timeout(400)

                    async def click(sel):
                        await popups()
                        await page.click(sel)

                    async def shot(name):
                        await page.wait_for_timeout(450)
                        await popups()
                        await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                    async def calm():
                        await popups()
                        await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                        await page.evaluate("document.querySelector('#sheet')?.open&&document.querySelector('#sheet').close()")
                        await page.wait_for_timeout(300)

                    await page.wait_for_timeout(2500)   # the x3 week card opens at the first calm moment
                    await calm()
                    strip = page.locator('#taskHUD .pm-strip').first
                    try:
                        await strip.wait_for(timeout=10000)
                    except Exception:
                        await shot('0-no-strip')
                        print(tag, 'HUD:', (await page.inner_html('#taskHUD'))[:1500])
                        raise
                    await shot('1-morning-strip')
                    if who == 'delivery':
                        await click('#taskHUD .pm-strip.due')
                        await page.wait_for_selector('#sheet[open] .pm-review', timeout=10000)
                        await shot('2-review-q1')
                        for q in ('t1', 't2'):
                            sel = f'#sheet .pm-review [data-command="pm_answer"][data-payload*=\'"{q}"\'][data-payload*=\'"option":"a"\']'
                            try:
                                await page.wait_for_selector(sel, timeout=8000)
                            except Exception:
                                print(tag, q, 'sheet:', (await page.inner_html('#sheet'))[:2500])
                                raise
                            await click(sel)
                            await page.wait_for_timeout(700)
                        await page.wait_for_selector('#sheet .pm-review [data-command="pm_ask"]', timeout=5000)
                        await shot('3-review-ask')
                        await click('#sheet .pm-review [data-command="pm_ask"].primary')
                        await page.wait_for_selector('#sheet .pm-ladder', timeout=5000)
                    else:
                        await click('#taskHUD .pm-strip.mgr')
                        await page.wait_for_selector('#sheet[open] .pm-ladder', timeout=10000)
                    await shot('4-ladder')
                    await click('#sheet .pm-more>summary')
                    await shot('4b-ladder-more')
                    await click('#sheet .pm-ladder [data-action="pmStart"]')
                    await page.wait_for_selector('#sheet[open] .pm-board', timeout=10000)
                    await shot('5-board')
                    crises = 0
                    for step in range(80):
                        await page.wait_for_timeout(250)
                        await popups()
                        if await page.locator('#sheet .pm-done').count():
                            break
                        if await page.locator('#sheet .pm-esc').count():
                            crises += 1
                            await shot(f'6-crisis-{crises}')
                            await click('#sheet .pm-esc .pm-opts .btn >> nth=0')
                            continue
                        done = page.locator('#sheet .pm-row.st-d').first
                        if await done.count():
                            bad = await done.locator('.pm-res.bad').count()
                            if step < 12:
                                await shot(f'6-check-{step}')
                            await done.locator('[data-command="pm_check"]').nth(1 if bad else 0).click()
                            continue
                        pick = page.locator('#sheet .pm-pick:not([disabled])').first
                        if await pick.count() and await page.locator('#sheet .pm-mate:not(.busy):not(.off)').count():
                            await pick.click()
                            await page.wait_for_timeout(200)
                            mate = page.locator('#sheet .pm-mate.fit:not([disabled])')
                            if not await mate.count():
                                mate = page.locator('#sheet .pm-mate:not([disabled])')
                            if step == 0:
                                await shot('5b-picked')
                            await mate.first.click()
                            continue
                        wait = page.locator('#sheet [data-command="pm_wait"]:not([disabled])')
                        if await wait.count():
                            await wait.click()
                            continue
                        await click('#sheet [data-command="pm_close"]')
                    await page.wait_for_selector('#sheet .pm-done', timeout=10000)
                    pay = (await page.inner_text('#sheet .pm-pay')).strip()
                    print(tag, 'crises:', crises, 'pay:', pay)
                    await shot('7-closed')
                    await click('#sheet .pm-done [data-action="end"]')
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_selector('#sheet[open] .summary-v6', timeout=10000)
                    await popups()
                    await shot('8-summary')
                    txt = await page.inner_text('#sheet .summary-v6')
                    if 'Ca quản lý' not in txt:
                        errors.append(f'{tag}: the day summary has no manager line')
                    await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
