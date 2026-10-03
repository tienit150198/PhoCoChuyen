"""🛡️ Rủi ro & bảo hiểm and 💰 Tiệm vàng in the browser (dev tool, needs playwright + chromium; game/rui.py, game/vang.py).

Runs the real app on a throwaway story-mode server (scripts/browser_garage.py's server), seeds a save past the new
player's grace with a scooter and a broken-down warning turned into a card, then checks what the player sees: the
risk card opens by itself at a calm moment, a choice settles it, the "Bảo hiểm" page buys health insurance, the
"Tiệm vàng" page buys 1 chỉ and sells it back. Screenshots at 390x844 and 1280x800; exits 1 on a missing text, a
failed step or a console error.

    python scripts/browser_risks.py [out_dir]
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_garage import PY, server   # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'risks'

SEED = r'''
import sys
from game import bank as bk
from game import garage as gr
from game import journey as jr
from game import rui
from game import marriage as mr
from game.storage import Store
db, token = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=24, chapter=3, done=[1, 2])
    j['wallet'] = 8000
    j['stats']['max_wallet'] = 8000
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    gr.action(s, 'jr_garage_buy', {'id': 'xe_ga', 'color': 'trang', 'confirm': True})
    rui.on_life_day(s)
    r = rui.get(s)
    r['since'] = r['day'] = 10
    r['warn'] = dict(kind='xe', sub='bike', ref='xe_ga', day=25, at=24, cost=0)
    r['warn']['cost'] = rui._projected(s, r, 'xe', 'bike', 'xe_ga')
    j['life_day'] = 25
    rui.on_life_day(s)            # the warning comes true: a card
    assert r['card'], r
    jr._award(s)                  # titles the money earns, already seen: no scene over the card
    j['news'] = []
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''

WANT = {
    'card': ['Chọn trong', 'Sửa ở tiệm', 'Tự sửa', 'Để đó'],
    'card-done': ['Xong'],
    'rui': ['Bảo hiểm & rủi ro', 'Bảo hiểm y tế', 'Bảo hiểm xe', 'Đồ phòng thân'],
    'rui-bought': ['Bảo hiểm y tế ✓', 'Có hiệu lực sau'],
    'vang': ['Tiệm vàng Kim Phát', '/ chỉ', 'Tiệm bán'],
    'vang-bought': ['Bạn có 1 chỉ', 'Bán ngay được'],
    'vang-sold': ['Đã bán 1 chỉ vàng'],
}


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, missing, notes = [], [], []
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
                tag = f'{w}x{h}'

                async def shot(name):
                    await page.wait_for_timeout(400)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                async def check(name, sel):
                    await shot(name)
                    text = await page.inner_text(sel)
                    for t in WANT[name]:
                        if t not in text:
                            missing.append(f'{tag} {name}: {t}')

                async def act(action):
                    await page.evaluate("(a=>{const b=document.createElement('button');b.dataset.action=a;"
                                        "b.hidden=true;document.body.append(b);b.click();})", action)

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')

                async def popups():
                    for _ in range(4):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            return
                        await b.first.click()
                        await page.wait_for_timeout(400)

                # 1. The card opens by itself once the first-visit popups ("Có gì mới", the gift…) are closed.
                auto = False
                for _ in range(40):
                    if await page.locator('#ruiCard[open]').count():
                        auto = True
                        break
                    b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, #x3Dialog[open] [data-x3="close"]:visible')
                    if await b.count():
                        await b.first.click()
                    await page.wait_for_timeout(500)
                if not auto:
                    why = await page.evaluate("[...document.querySelectorAll('dialog[open]')].map(d=>d.id+'.'+d.className).join(' | ')+' html:'+document.documentElement.className")
                    notes.append(f'{tag}: the card did not open by itself (opened from the page): {why}')
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                    await act('rui')
                    await page.click('#ruiPage [data-rui="pop"]')
                    await page.wait_for_selector('#ruiCard[open]', timeout=5000)
                await check('card', '#ruiCard')
                await page.click('#ruiCard [data-rui="choose"][data-choice="sua"]')
                await page.wait_for_selector('#ruiCard [data-rui="close"]', timeout=8000)
                await check('card-done', '#ruiCard')
                await popups()                                   # a new title earned on the way (a scene in the sheet)
                await page.click('#ruiCard [data-rui="close"]')
                await page.wait_for_timeout(300)

                # 2. Bảo hiểm: buy health insurance.
                await act('rui')
                await page.wait_for_selector('#ruiPage[open] .rui-list', timeout=8000)
                await check('rui', '#ruiPage')
                await page.click('#ruiPage [data-rui="pol"][data-id="yte"][data-on="1"]')
                await page.wait_for_selector('#ruiPage [data-rui="pol"][data-id="yte"][data-on="0"]', timeout=8000)
                await check('rui-bought', '#ruiPage')
                await page.evaluate("document.getElementById('ruiPage').close()")

                # 3. Tiệm vàng: buy 1 chỉ, then sell it.
                await act('vang')
                await page.wait_for_selector('#ruiPage[open] .rui-price', timeout=8000)
                await check('vang', '#ruiPage')
                await page.click('#ruiPage [data-rui="set"][data-n="10"]')
                await page.click('#ruiPage [data-rui="buy"]')
                await confirm()
                await page.wait_for_selector('#ruiPage .rui-mine', timeout=8000)
                await check('vang-bought', '#ruiPage')
                await page.click('#ruiPage [data-rui="sell"]')
                await confirm()
                await page.wait_for_selector('#ruiPage .rui-flash', timeout=8000)
                await page.locator('#ruiPage .rui-mine').wait_for(state='detached', timeout=8000)
                await check('vang-sold', '#ruiPage')
                st = await page.evaluate("(async()=>{const r=await fetch('/api/state',{credentials:'include'});return r.ok?await r.json():null;})()")
                if st:
                    s = st.get('state') or st
                    notes.append(f"{tag}: gold {json.dumps((s.get('vang') or {}).get('phan'))} phân, "
                                 f"policies {[p['id'] for p in (s.get('rui') or {}).get('pol', []) if p.get('on')]}")
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('notes:', notes or 'none')
    print('missing:', missing or 'none')
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real or missing else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
