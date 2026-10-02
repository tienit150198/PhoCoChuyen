"""🚗 Xe & phương tiện: a browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server, seeds one save straight in its database (a named character on
life day 20 with 3.500 xu and a bank account holding 1.000), then in the browser: opens the garage from the menu
hub "Tiền & nhà", looks at each tab, buys a scooter in another colour with a plate, rides out once (the second ride is
shut with its reason), repaints it, checks the chip on the profile and the vehicle parked by the house, and sells it.
Screenshots at 390x844 and 1280x800.

    python scripts/browser_garage.py [out_dir]
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

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'garage'
PY = os.environ.get('MNL_PY', sys.executable)


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-garage-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.sqlite3')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([PY, 'server.py', '--port', str(port), '--db', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
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
from game import bank as bk
from game import journey as jr
from game import marriage as mr
from game.storage import Store
db, token = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=20)
    j['wallet'] = 3500
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''


def seed(db: str, token: str) -> None:
    subprocess.run([PY, '-c', SEED, db, token], cwd=ROOT, check=True)


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (1280, 800)):
                ctx = await browser.new_context(viewport=dict(width=w, height=h))
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                seed(db, token)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1500)

                async def popups():
                    for _ in range(4):   # "Có gì mới", new titles and other first-visit popups
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            return
                        await b.first.click()
                        await page.wait_for_timeout(400)
                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                tag = f'{w}x{h}'

                async def shot(name):
                    await page.wait_for_timeout(400)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await shot('confirm-' + str(len(list(OUT.glob(tag + '-confirm-*')))))
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(900)
                    await popups()

                async def flash():
                    return (await page.inner_text('.gr-sheet .bk-flash')).strip()

                # Open the garage the way a player does (the app's own action; the menu hub differs by layout).
                await page.evaluate("document.querySelector('#sheet')?.open&&document.querySelector('#sheet').close()")
                await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='garage';b.hidden=true;document.body.append(b);b.click();})()")
                await page.wait_for_selector('.gr-sheet[open] .gr-tabs', timeout=10000)
                await shot('1-empty-garage')
                for gid in ('bike', 'car', 'boat', 'plane'):
                    await page.click(f'.gr-sheet [data-gr="tab"][data-tab="{gid}"]')
                    await page.wait_for_timeout(300)
                    await shot(f'2-tab-{gid}')
                disabled = await page.locator('.gr-sheet [data-gr="look"]').count()
                print(tag, 'plane tab buttons:', disabled)
                await page.click('.gr-sheet [data-gr="tab"][data-tab="bike"]')
                await page.click('.gr-sheet [data-gr="look"][data-id="xe_ga"]')
                await page.wait_for_selector('.gr-sheet .gr-swatches', timeout=5000)
                await page.click('.gr-sheet [data-gr="paint"][data-color="hong"]')
                await page.fill('#gr-plate', 'MÂY 01')
                await shot('3-buy-form')
                await page.click('.gr-sheet [data-gr="buy"]')
                await confirm()
                print(tag, 'buy:', await flash())
                await page.wait_for_selector('.gr-sheet .gr-car', timeout=5000)
                await shot('4-mine')
                await page.click('.gr-sheet [data-gr="trip"][data-id="xe_ga"]')
                await page.wait_for_timeout(900)
                print(tag, 'trip:', await flash())
                if not await page.locator('.gr-sheet [data-gr="trip"][data-id="xe_ga"][disabled]').count():
                    errors.append('second ride out is not shut')
                await shot('5-after-trip')
                await page.click('.gr-sheet [data-gr="edit"][data-id="xe_ga"]')
                await page.click('.gr-sheet [data-gr="paint"][data-color="navy"]')
                await page.click('.gr-sheet [data-gr="save"]')
                await page.wait_for_timeout(900)
                print(tag, 'paint:', await flash())
                # The profile: the chip next to Thay đồ.
                await page.evaluate("document.querySelector('.gr-sheet').close()")
                await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='home';b.hidden=true;document.body.append(b);b.click();})()")
                await page.wait_for_selector('#sheet[open] .jr-me [data-action="garage"]', timeout=10000)
                await shot('6-profile-chip')
                await page.evaluate("document.querySelector('#sheet').close()")
                # The house card: the scooter parked out front.
                await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='house';b.hidden=true;document.body.append(b);b.click();})()")
                await page.wait_for_selector('.hs-sheet[open] [data-hs="garage"]', timeout=10000)
                await shot('6-house-parked')
                await page.click('.hs-sheet [data-hs="garage"]')
                await page.wait_for_selector('.gr-sheet[open] .gr-car', timeout=10000)
                await page.click('.gr-sheet [data-gr="sell"][data-id="xe_ga"]')
                await confirm()
                print(tag, 'sell:', await flash())
                await shot('7-sold')
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
