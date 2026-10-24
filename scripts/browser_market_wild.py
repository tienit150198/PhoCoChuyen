"""🎢 Sàn Phố in the browser (dev tool, needs playwright + chromium; game/market_wild.py, game/san.py).

Runs the real app on a throwaway story-mode server whose wild market opened three days ago (MNL_MARKET_WILD_AT),
seeds a rich save holding a few coins and stocks bought at the opening, then checks what the player sees on Đầu tư:
the third market tile, the coin and stock lists (prices, 1-hour change, sparklines, the hot-news ticker), a risky
coin's warning and a holding's card (value, profit, the regret note when the peak was higher). Screenshots at
390x844; exits 1 on a missing text or a console error.

    TEST_DATABASE_URL=... python scripts/browser_market_wild.py [out_dir]
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'market_wild'
os.environ['MNL_MARKET_WILD_AT'] = str(int(time.time()) - 3 * 86400)
from browser_garage import PY, server   # noqa: E402
from game import market_wild as mw      # noqa: E402

SEED = r'''
import sys
from game import invest as iv
from game import market_wild as mw
from game import san
from game.storage import Store
db, token = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=21)
    j['wallet'] = 400000
    j['stats']['max_wallet'] = 400000
    iv.migrate(s)
    t = mw.tick_of()
    live = [a for a in mw.NEW if mw.price_at(a, t) > 0 and a not in ('mai', 'dua', 'mtech')]
    drop = max(live, key=lambda a: mw.peak_since(a, mw.WILD_TICK, t) / mw.price_at(a, t))   # the regret note's case
    print(drop)
    for a, x in (('mai', 20000), ('dua', 8000), ('mtech', 30000), (drop, 15000)):
        san.action(s, 'jr_san_buy', dict(a=a, amount=x))
        j['san']['h'][a]['t'] = mw.WILD_TICK          # held since the opening: the peak covers three days
from game import marriage as mr
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''

WANT = {
    'list-coin': ['Sàn Phố', 'Mèo Mai Coin', 'Phở Coin', 'Dưa Hấu Coin', '1 giờ'],
    'list-stock': ['Mây Tech', 'Phố Mây Food', 'Nhà Thuốc Phố'],
    'card-mai': ['Mèo Mai Coin', 'Đang giữ', 'Trị giá hiện tại', 'Phí 2%'],
    'card-dua': ['Rủi ro rất cao', 'hủy niêm yết'],
    'card-mtech': ['Mây Tech', 'Phí 1%'],
}


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, missing, regret = [], [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844))
            page = await ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            drop = subprocess.run([PY, '-c', SEED, db, token], cwd=ROOT, check=True, env=dict(os.environ),
                                  capture_output=True, text=True).stdout.split()[-1]
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1500)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

            async def act(action, **data):
                await page.evaluate("(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;"
                                    "Object.assign(b.dataset,d);b.hidden=true;document.body.append(b);b.click();})",
                                    [action, data])

            async def check(name, sel, scroll=None):
                await page.wait_for_timeout(700)
                if scroll:
                    await page.evaluate("s=>{const e=document.querySelector(s);if(!e)return;e.scrollIntoView({block:'start'});"
                                        "let p=e.parentElement;while(p&&p.scrollHeight<=p.clientHeight)p=p.parentElement;"
                                        "p?.scrollBy(0,-72);}", scroll)
                    await page.wait_for_timeout(300)
                await page.screenshot(path=str(OUT / f'390x844-{name}.png'), full_page=False)
                text = await page.inner_text(sel)
                for t in WANT.get(name, ()):
                    if t not in text:
                        missing.append(f'{name}: {t}')
                return text

            await act('home')
            await page.wait_for_selector('#sheet[open]', timeout=10000)
            await act('jrView', view='invest')
            await page.wait_for_selector('.sv-tile', timeout=15000)
            await page.click('.sv-tile')
            await page.wait_for_selector('.sv-row', timeout=10000)
            await page.wait_for_function("!document.querySelector('.sv-q b')?.textContent.includes('…')", timeout=15000)
            await check('list-coin', '#sheet', '.sv')
            await page.click('.sv-tabs [data-tab="stock"]')
            await check('list-stock', '#sheet', '.sv')
            await page.click('.sv-tabs [data-tab="coin"]')
            for a in ('mai', 'dua', drop):
                if a == drop:
                    await page.click(f'.sv-tabs [data-tab="{"stock" if mw.ASSETS[a]["kind"] == "stock" else "coin"}"]')
                await page.click(f'.sv-row[data-market="{a}"]')
                await page.wait_for_selector('.sv-card', timeout=10000)
                text = await check(f'card-{a}', '#sheet', '.sv-card')
                if 'Nếu bán lúc đỉnh' in text:
                    regret.append(a)
                    await page.evaluate("document.querySelector('.sv-regret')?.scrollIntoView({block:'center'})")
                    await page.screenshot(path=str(OUT / f'390x844-regret-{a}.png'))
            await page.click('.sv-tabs [data-tab="stock"]')
            await page.click('.sv-row[data-market="mtech"]')
            await page.wait_for_selector('.sv-card', timeout=10000)
            await check('card-mtech', '#sheet', '.sv-card')
            await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('missing:', missing or 'none')
    print('regret note on:', regret or 'none (no holding is 10 % under its peak right now)')
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real or missing else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
