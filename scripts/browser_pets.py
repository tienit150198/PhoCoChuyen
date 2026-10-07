"""🐾 Nuôi thú cưng (game/pets.py) on the CLASSIC client: a browser walk-through (dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save straight in its database (a named character on
life day 12 with 40.000 xu and a bank account). At 390x844: Bản đồ phố → Chỉ đường "🐾 Nuôi thú cưng" (Phố dịch vụ),
walks to the door and goes in; adopts at Góc nhận nuôi Chân Nhỏ with a 50 xu donation, buys a corgi at the shop, buys a
bow, an áo dài, a ball and a bed; dresses the corgi; feeds, plays, bathes; the photo booth; the weekly board; the pet
trailing the character on the town map; the pets at home. At 1280x800 (seeded with two pets): the dialog, the town
map, home. Prints the visible word count of each screen (cap 30, docs/UI_KIT.md) and JPEG screenshots.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_pets.py [out_dir]
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_gadgets_classic import server, ROOT, PY  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_pets_shots'

SEED = r'''
import sys
from game import bank as bk
from game import marriage as mr
from game import pets
from game.storage import Store
db, token, own = sys.argv[1], sys.argv[2], sys.argv[3] == '1'
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=12)
    j['wallet'] = 40000
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    if own:
        pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': 'samoyed', 'coat': 0, 'nick': 'Mây', 'confirm': True})
        pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': 'scottish', 'coat': 1, 'nick': 'Bơ', 'confirm': True})
        for iid in ('vuong_mien', 'vay_cong_chua', 'no_hong', 'nem_may'):
            pets.action(s, 'jr_pet_buy', {'id': iid, 'confirm': True})
        a, b = (p['id'] for p in j['pets']['list'])
        pets.action(s, 'jr_pet_wear', {'pet': a, 'slot': 'head', 'id': 'vuong_mien'})
        pets.action(s, 'jr_pet_wear', {'pet': a, 'slot': 'body', 'id': 'vay_cong_chua'})
        pets.action(s, 'jr_pet_wear', {'pet': b, 'slot': 'head', 'id': 'no_hong'})
        pets.action(s, 'jr_pet_wear', {'pet': b, 'slot': 'bed', 'id': 'nem_may'})
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''

ACT = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d||{});b.hidden=true;document.body.append(b);b.click();b.remove();})"
WORDS = "async()=>{const d=[...document.querySelectorAll('dialog[open]')].pop();const kit=await import('/js/ui-kit.js');return d?kit.wordBudget(d).words:-1;}"


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, counts = [], {}
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (1280, 800)):
                phone = w < 900
                ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone)
                await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.ui25d','0');localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                subprocess.run([PY, '-c', SEED, db, token, '0' if phone else '1'], cwd=ROOT, check=True)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(2000)
                tag = f'{w}x{h}'

                async def popups():
                    for _ in range(5):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, #confirmDialog[open] [data-action="confirmYes"]')
                        if not await b.count():
                            return
                        await b.first.click()
                        await page.wait_for_timeout(400)

                async def shot(name, count=True):
                    await page.wait_for_timeout(600)
                    if count:
                        n = await page.evaluate(WORDS)
                        counts[f'{tag} {name}'] = n
                        print(f'{tag} {name}: {n} words', flush=True)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.jpg'), type='jpeg', quality=82)

                async def tap(sel):
                    await page.click(f'.pt-sheet {sel}')
                    await page.wait_for_timeout(250)

                async def main_btn(confirm=False):
                    await tap('[data-pt="go"]')
                    if confirm:
                        await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                        await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_selector('.pt-sheet[aria-busy="false"]', timeout=30000)
                    await page.wait_for_timeout(300)
                    text = (await page.inner_text('.pt-sheet .pt-flash')).strip()
                    await popups()
                    return text

                async def home():
                    await page.evaluate(ACT, ['home', {}])
                    await page.wait_for_timeout(1200)
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                if phone:
                    await home()
                    sel = page.locator('.tw-route-picker select')
                    await sel.wait_for(state='attached', timeout=20000)
                    opts = await sel.locator('option').all_inner_texts()
                    print(tag, 'map has the door:', any('thú cưng' in o for o in opts))
                    await sel.select_option('lm:pets')
                    await page.click('.tw-route-picker button')
                    try:
                        await page.wait_for_selector('.tw-card:not([hidden]) .tw-go[data-action="pets"]', timeout=60000)
                        await shot('0-map-door', False)
                        await page.click('.tw-card .tw-go[data-action="pets"]')
                    except Exception:
                        errors.append('the walk to the pet door on the town map did not reach it')
                        await page.evaluate(ACT, ['pets', {}])
                    await page.wait_for_selector('.pt-sheet[open]', timeout=10000)
                    await shot('1-adopt-empty')
                    await tap('[data-pt="shelter"][data-i="0"]')
                    await tap('[data-pt="donate"][data-n="50"]')
                    await shot('2-adopt-pick')
                    print(tag, 'adopt:', await main_btn())
                    await shot('3-home-first')
                    await tap('[data-pt="tab"][data-tab="shop"]')
                    await shot('4-shop-dogs')
                    await tap('[data-pt="breed"][data-id="corgi"]')
                    await tap('[data-pt="coat"][data-c="1"]')
                    await page.fill('.pt-sheet input[name="nick"]', 'Tofu')
                    await shot('5-shop-corgi')
                    print(tag, 'buy corgi:', await main_btn(True))
                    await tap('[data-pt="tab"][data-tab="shop"]')
                    await tap('[data-pt="kind"][data-kind="do"]')
                    for iid in ('no_hong', 'ao_dai', 'bong', 'o_bong'):
                        await tap(f'[data-pt="item"][data-id="{iid}"]')
                        print(tag, 'buy', iid, await main_btn(iid == 'o_bong' and False))
                    await shot('6-shop-items')
                    await tap('[data-pt="tab"][data-tab="home"]')
                    pets = await page.locator('.pt-sheet .pt-mini').count()
                    if pets:
                        await page.locator('.pt-sheet .pt-mini').last.click()
                    await tap('[data-pt="sub"][data-sub="dress"]')
                    await tap('[data-pt="wear"][data-id="no_hong"]')
                    await tap('[data-pt="slot"][data-slot="body"]')
                    await tap('[data-pt="wear"][data-id="ao_dai"]')
                    await shot('7-dress')
                    await tap('[data-pt="back"]')
                    await shot('8-home')
                    await tap('[data-pt="sub"][data-sub="feed"]')
                    await tap('[data-pt="food"][data-id="pate"]')
                    print(tag, 'feed:', await main_btn())
                    await tap('[data-pt="back"]')
                    await tap('[data-pt="sub"][data-sub="play"]')
                    await tap('[data-pt="toy"][data-id="bong"]')
                    print(tag, 'play:', await main_btn())
                    await shot('9-play')
                    await tap('[data-pt="back"]')
                    await tap('[data-pt="sub"][data-sub="clean"]')
                    await shot('10-clean')
                    await tap('[data-pt="back"]')
                    await tap('[data-pt="sub"][data-sub="photo"]')
                    await shot('11-photo')
                    await tap('[data-pt="back"]')
                    await tap('[data-pt="tab"][data-tab="board"]')
                    await page.wait_for_timeout(800)
                    await shot('12-board')
                    await page.evaluate("document.querySelector('.pt-sheet').close()")
                else:
                    await page.evaluate(ACT, ['pets', {}])
                    await page.wait_for_selector('.pt-sheet[open]', timeout=10000)
                    await shot('1-home')
                    await tap('[data-pt="tab"][data-tab="shop"]')
                    await tap('[data-pt="kind"][data-kind="cat"]')
                    await shot('2-shop-cats')
                    await tap('[data-pt="tab"][data-tab="home"]')
                    await tap('[data-pt="sub"][data-sub="photo"]')
                    await shot('3-photo')
                    await page.evaluate("document.querySelector('.pt-sheet').close()")
                # The pet trails the character on the town map, and lives at home.
                await home()
                sel = page.locator('.tw-route-picker select')
                await sel.wait_for(state='attached', timeout=20000)
                await sel.select_option('lm:bank')
                await page.click('.tw-route-picker button')
                await page.wait_for_timeout(1500)
                await shot('13-town-walking', False)
                await page.wait_for_timeout(5000)
                await shot('14-town-stop', False)
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                await page.evaluate(ACT, ['jrEnterHome', {}])
                await page.wait_for_timeout(2500)
                await shot('15-home-room', False)
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    over = {k: v for k, v in counts.items() if k.startswith('390') and v > 30}
    print('words over 30:', over or 'none')
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real or over else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
