"""🏠 Nhà của bạn + yearly savings: a browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (no MNL_DEV: homes exist only in the journey), seeds one
save straight in its database (a named character on life day 20 with two weeks of salary, 1.800 xu and a
bank account), then in the browser: opens "Nhà của bạn" from the journey, opens a 12-month savings deposit
in the bank, and buys a mini apartment with a mortgage. Screenshots at 390x844 and 1280x800.

    python scripts/browser_housing.py [out_dir]
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_v04 import free_port  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'housing'


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-home-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.sqlite3')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--db', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
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


def seed(db: str, token: str) -> None:
    from game import bank as bk
    from game import journey as jr
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        j = s['journey']
        s['name'] = 'Lan'
        j.update(gender='female', intro=True, life_day=6)
        for d in range(6, 20):
            j['life_day'] = d
            jr._wallet(j, 60, 'salary', f'Lương ngày {d}')
        j['life_day'] = 20
        j['wallet'] = 1800
        bk.apply(s, 'jr_bk_open', {})
        bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


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
                for _ in range(3):   # "Có gì mới" and other first-visit popups
                    if await page.locator('[data-wn="close"]:visible').count():
                        await page.click('[data-wn="close"]')
                        await page.wait_for_timeout(400)
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                tag = f'{w}x{h}'

                async def shot(name, full=False):
                    await page.wait_for_timeout(400)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=full)

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(900)
                    await celebrate()

                async def celebrate():   # "Danh hiệu mới" scenes cover the page until closed
                    for _ in range(3):
                        b = page.locator('[data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            return
                        await shot(f'title-{len(list(OUT.glob(tag + "-title-*")))}')
                        await b.first.click()
                        await page.wait_for_timeout(500)

                # The journey card, then the home screen.
                await page.wait_for_selector('.jr-house-row', timeout=10000)
                await page.locator('.jr-house').scroll_into_view_if_needed()
                await celebrate()
                if await page.locator('[data-wn="close"]:visible').count():
                    await page.click('[data-wn="close"]')
                    await page.wait_for_timeout(400)
                await shot('1-journey-card')
                await page.click('.jr-house-row')
                await page.wait_for_selector('.hs-sheet[open] .hs-market', timeout=10000)
                await shot('2-home-screen')
                await page.locator('.hs-sheet .hs-market').scroll_into_view_if_needed()
                await shot('3-market')
                # Savings: a 12-month deposit in the bank.
                await page.click('.hs-sheet [data-hs="bank"][data-tab="save"]')
                await page.wait_for_selector('.bk-sheet:not(.hs-sheet)[open] #bk-term', timeout=10000)
                await page.wait_for_timeout(1500)
                await celebrate()
                await page.fill('#bk-save-amt', '200')
                await page.select_option('#bk-term', '60')
                await page.evaluate("(()=>{const x=document.querySelector('#bk-renew');x.scrollIntoView({block:'center'});x.click();})()")
                if not await page.is_checked('#bk-renew'):
                    errors.append('renew checkbox did not check')
                await page.wait_for_timeout(600)
                await celebrate()
                await shot('4-savings-form')
                await page.click('.bk-sheet:not(.hs-sheet) [data-bk="save"]')
                await page.wait_for_selector('#confirmDialog[open]')
                await shot('5-savings-confirm')
                await confirm()
                await page.locator('.bk-term').first.scroll_into_view_if_needed()
                await shot('6-savings-opened')
                # Buy a mini apartment with a mortgage.
                await page.click('.bk-sheet:not(.hs-sheet) [data-bk="house"]')
                await page.wait_for_selector('.hs-sheet[open] .hs-market', timeout=10000)
                await page.click('.hs-sheet [data-hs="look"][data-kind="can_ho_mini"]')
                await page.wait_for_selector('.hs-sheet .hs-buy', timeout=5000)
                from game import housing as hs
                await page.fill('#hs-down', str(hs.down_min(hs.HOMES['can_ho_mini']['price'])))
                await page.dispatch_event('#hs-down', 'change')
                await page.select_option('.hs-buy select[name="months"]', '36')
                await shot('7-buy-form')
                await page.locator('.hs-buy [data-hs="sign"]').scroll_into_view_if_needed()
                await shot('8-buy-preview')
                await page.click('.hs-buy [data-hs="sign"]')
                await confirm()
                await page.wait_for_selector('.hs-place.own', timeout=10000)
                await shot('9-bought')
                await page.locator('.hs-sheet .bk-card.bk-late, .hs-sheet .hs-sched').first.scroll_into_view_if_needed()
                await shot('10-mortgage')
                flash = await page.inner_text('.hs-sheet .bk-flash')
                print(tag, 'buy:', flash[:160])
                # Back on the journey (a fresh load, like the next visit): the card now shows the loan.
                await page.reload()
                await page.wait_for_selector('.jr-house-row', timeout=30000)
                await page.wait_for_timeout(1200)
                await celebrate()
                if await page.locator('[data-wn="close"]:visible').count():
                    await page.click('[data-wn="close"]')
                await page.locator('.jr-house').scroll_into_view_if_needed()
                await shot('11-journey-after')
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
