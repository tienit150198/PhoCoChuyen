"""🧾 The xu sinks of 03/10 in the browser (dev tool, needs playwright + chromium; docs/ECONOMY_SINKS.md).

Runs the real app on a throwaway story-mode server (scripts/browser_garage.py's server), seeds one rich save (a jet, a
small car, a villa, 50 000 xu of Mây savings, the bills block), then checks what the player sees: the garage's
"Xe của bạn" with each vehicle's fee and the month's bill, the plane tab's fee chips and the new models, the buy page's
fee line, the home's phí bảo trì (owned home, listing), and the savings tier on Đầu tư. Screenshots at 390x844 and
1280x800; exits 1 on a missing text or a console error.

    python scripts/browser_sinks.py [out_dir]
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_garage import PY, server   # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'sinks'

SEED = r'''
import sys
from game import bank as bk
from game import garage as gr
from game import housing as hs
from game import invest as iv
from game import upkeep as up
from game import marriage as mr
from game.storage import Store
db, token = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=21)
    j['wallet'] = 400000
    j['stats']['max_wallet'] = 400000
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    gr.action(s, 'jr_garage_buy', {'id': 'phan_luc', 'color': 'trang', 'confirm': True})
    gr.action(s, 'jr_garage_buy', {'id': 'o_to_mini', 'color': 'hong', 'confirm': True})
    k = 'biet_thu_song'; p = hs.HOMES[k]['price']
    h = j['home'] = hs.initial(21)
    h['own'] = dict(id='h1', kind=k, price=p, day=21, down=p, fee=hs.buy_fee(p), joint=0, loan=None, mv=0, let=None, keep=None)
    j['wallet'] -= p
    iv.migrate(s)
    iv.apply(s, 'iv_save', {'amount': 50000})
    up.on_life_day(s)
    j['upk']['acc']['car'] = 450000
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''

WANT = {
    'garage-mine': ['Phí giữ xe & bảo dưỡng khoảng 1.148 xu/tháng', 'Giữ xe & bảo dưỡng 1.125 xu/tháng', 'Giữ xe & bảo dưỡng 23 xu/tháng'],
    'garage-plane': ['Trực thăng riêng', 'Giữ xe & bảo dưỡng 750 xu/tháng'],
    'garage-buy': ['Phí giữ xe & bảo dưỡng khoảng 225 xu/tháng (5 ngày sống)'],
    'house': ['Phí bảo trì', '210 xu/tháng', 'Bảo trì 65 xu/tháng'],
    'invest': ['cho 20.000 xu đầu, phần trên lãi 0,1%/ngày'],
}


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, missing = [], []
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
                subprocess.run([PY, '-c', SEED, db, token], cwd=ROOT, check=True)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1500)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                tag = f'{w}x{h}'

                async def check(name, sel):
                    await page.wait_for_timeout(500)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=False)
                    text = await page.inner_text(sel)
                    for t in WANT[name]:
                        if t not in text:
                            missing.append(f'{tag} {name}: {t}')

                async def act(action, extra=''):
                    await page.evaluate("(([a,x])=>{const b=document.createElement('button');b.dataset.action=a;if(x)b.dataset.view=x;"
                                        "b.hidden=true;document.body.append(b);b.click();})", [action, extra])

                await act('garage')
                try:
                    await page.wait_for_selector('.gr-sheet[open] .gr-car', timeout=15000)
                except Exception:
                    await page.screenshot(path=str(OUT / f'{tag}-fail.png'))
                    print('FAIL garage:', (await page.evaluate("document.querySelector('.gr-sheet')?.innerText||document.body.innerText"))[:1500])
                    raise
                await check('garage-mine', '.gr-sheet')
                await page.click('.gr-sheet [data-gr="tab"][data-tab="plane"]')
                await check('garage-plane', '.gr-sheet')
                await page.click('.gr-sheet [data-gr="tab"][data-tab="car"]')
                await page.click('.gr-sheet [data-gr="look"][data-id="sieu_xe"]')
                await check('garage-buy', '.gr-sheet')
                await page.evaluate("document.querySelector('.gr-sheet').close()")
                await act('house')
                await page.wait_for_selector('.hs-sheet:not(.gr-sheet)[open]', timeout=10000)
                await check('house', '.hs-sheet:not(.gr-sheet)[open]')
                await page.evaluate("document.querySelector('.hs-sheet:not(.gr-sheet)').close()")
                await act('home')                                # the journey sheet, then its Đầu tư view
                await page.wait_for_selector('#sheet[open]', timeout=10000)
                await act('jrView', 'invest')
                await page.wait_for_selector('#ivBankT', timeout=10000)
                await check('invest', '#sheet')
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('missing:', missing or 'none')
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real or missing else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
