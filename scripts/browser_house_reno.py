"""🛠️ Trong nhà (sửa và trang trí nhà): a browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (as scripts/browser_housing.py), seeds one save straight in its
database (a named character who bought the old tập thể 24 life days ago, 3.000 xu, a sofa and a picture already
placed), then in the browser: 🏠 Nhà của bạn → Vào nhà, the repair list (fixes the whole home), decorate mode (picks
an empty slot, buys a plant), selects a piece and moves it, then upgrades walls, floor and kitchen. Every screen at 390x844 and 1280x800, in the light
theme and in "Phố đêm". Exit 1 on any console error.

    python scripts/browser_house_reno.py [out_dir]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_house_shots'


def seed(db: str, token: str) -> None:
    from game import housing as hs
    from game import journey as jr
    from game import marriage as mr
    from game import reno as rn
    from game import whats_new as wn
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        j = s['journey']
        s['name'] = 'Lan'
        s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)   # no "Có gì mới" over the shots
        j.update(gender='female', intro=True, life_day=6, wallet=5000)
        hs.apply(s, 'jr_home_buy', {'kind': 'tap_the', 'down': 1800, 'confirm': True})
        for d in range(7, 31):
            j['life_day'] = d
            jr._wallet(j, 60, 'salary', f'Lương ngày {d}')
            hs.on_life_day(s)
        rn.apply(s, 'jr_reno_buy', {'item': 'sofa', 'room': 'living', 'slot': 'f1', 'confirm': True})
        rn.apply(s, 'jr_reno_buy', {'item': 'tranh', 'room': 'living', 'slot': 'w0', 'confirm': True})
        j['wallet'] = max(j['wallet'], 3000)
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

                async def popups():
                    for _ in range(4):   # "Có gì mới", title scenes and other first-visit popups
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            break
                        await b.first.click()
                        await page.wait_for_timeout(400)
                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                tag = f'{w}x{h}'

                async def shot(name):
                    await page.wait_for_timeout(450)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(900)
                    await popups()

                async def theme(name):
                    await page.evaluate(f"document.documentElement.dataset.theme='{name}'")

                await page.wait_for_selector('.jr-house-row', timeout=10000)
                await page.click('.jr-house-row')
                await page.wait_for_selector('.hs-sheet[open] .hs-place.own', timeout=10000)
                await popups()
                await shot('1-house')
                await page.click('.hs-sheet [data-hs="inside"]:not([data-mode])')
                await page.wait_for_selector('.rn-sheet[open] .rn-scene', timeout=10000)
                for th in ('kem', 'dem'):
                    await theme(th)
                    await shot(f'2-look-{th}')
                await theme('kem')
                # Sửa nhà: the list, then fix everything.
                await page.click('.rn-sheet [data-rn="mode"][data-mode="fix"]')
                await page.wait_for_selector('.rn-sheet .rn-parts')
                for th in ('kem', 'dem'):
                    await theme(th)
                    await shot(f'3-fix-{th}')
                await theme('kem')
                await page.click('.rn-sheet [data-rn="fix"][data-part="all"]')
                await shot('4-fix-confirm')
                await confirm()
                await page.locator('.rn-sheet .rn-scene').scroll_into_view_if_needed()
                await shot('5-fixed')
                # Trang trí: an empty floor slot in the living room, buy a plant.
                await page.click('.rn-sheet [data-rn="mode"][data-mode="decor"]')
                await page.wait_for_selector('.rn-sheet .rn-slot')
                for th in ('kem', 'dem'):
                    await theme(th)
                    await shot(f'6-decor-{th}')
                await theme('kem')
                await page.click('.rn-sheet .rn-slot[data-slot="f0"]')
                await page.wait_for_selector('.rn-sheet .rn-pick .rn-shop')
                for th in ('kem', 'dem'):
                    await theme(th)
                    await shot(f'7-pick-{th}')
                await theme('kem')
                await page.click('.rn-sheet [data-rn="buy"][data-item="cay_canh"]')
                await confirm()
                await page.wait_for_selector('.rn-sheet .rn-item[data-uid="d3"]', timeout=5000)
                await shot('8-bought')
                # Select the sofa, move it to the bedroom… no: sofas belong in the living room. Move the plant instead.
                await page.click('.rn-sheet .rn-item[data-uid="d3"]')
                await page.wait_for_selector('.rn-sheet [data-rn="pickup"]')
                await shot('9-selected')
                await page.click('.rn-sheet [data-rn="pickup"]')
                await page.click('.rn-sheet [data-rn="room"][data-room="bed"]')
                await page.wait_for_selector('.rn-sheet .rn-slot.go')
                for th in ('kem', 'dem'):
                    await theme(th)
                    await shot(f'10-moving-{th}')
                await theme('kem')
                await page.click('.rn-sheet .rn-slot.go[data-slot="f1"]')
                await page.wait_for_selector('.rn-sheet .rn-item[data-uid="d3"]', timeout=5000)
                await theme('dem')
                await shot('11-bedroom-dem')
                await theme('kem')
                flash = await page.inner_text('.rn-sheet .bk-flash')
                print(tag, 'move:', flash[:120])
                # Upgrades: walls, floor and kitchen to level 2, then the living room and the kitchen.
                await page.click('.rn-sheet [data-rn="mode"][data-mode="fix"]')
                for part in ('wall', 'wall', 'floor', 'floor', 'kitchen', 'kitchen', 'roof', 'power'):
                    await page.click(f'.rn-sheet [data-rn="up"][data-part="{part}"]')
                    await confirm()
                for room in ('living', 'kitchen'):
                    await page.click(f'.rn-sheet [data-rn="room"][data-room="{room}"]')
                    await page.locator('.rn-sheet .rn-scene').scroll_into_view_if_needed()
                    for th in ('kem', 'dem'):
                        await theme(th)
                        await shot(f'12-upgraded-{room}-{th}')
                await theme('kem')
                # Back to Nhà của bạn: the card shows Ấm cúng.
                await page.click('.rn-sheet [data-rn="back"]')
                await page.wait_for_selector('.hs-sheet[open] .hs-place.own', timeout=10000)
                await shot('13-house-after')
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
