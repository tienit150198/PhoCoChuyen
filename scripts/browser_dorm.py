"""🛏️ Ký túc xá Hẻm 7: a browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server, seeds one save (a named character on life day 20, chapter 3,
200 xu), then in the browser: opens "Nhà của bạn", rents the dorm bed, looks at the bunk room on the home card and
the journey card, answers a roommate moment (a life card seeded in the save), moves to the closed room and back,
then gives the bed up. Screenshots at 390x844 and 1280x800.

    python scripts/browser_dorm.py [out_dir]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_dorm_shots'


def mutate(db: str, token: str, fn) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def seed(s):
    from game import journey as jr
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=6)
    for d in range(6, 20):
        j['life_day'] = d
        jr._wallet(j, 30, 'salary', f'Lương ngày {d}')
    j['life_day'] = 20
    j['wallet'] = 200
    if j['chapter'] < 3:            # the dorm is cheaper than the attic from chapter 3 on
        j['chapter'], j['done'] = 3, [1, 2]


def roommate_moment(s):
    from game import life as lf
    L = lf._state(s)
    j = s['journey']
    L['day'] = j['life_day']
    card = lf._new_card(L, j['life_day'], 'dorm', 'ktx_mi', 'ktx', 'dorm', None)
    card['who'] += ['ktx_tuan']
    L['pending'] = card


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
                mutate(db, token, seed)
                tag = f'{w}x{h}'

                async def shot(name, full=False):
                    await page.wait_for_timeout(450)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=full)

                async def calm():
                    for _ in range(4):   # "Có gì mới", titles and other first-visit popups
                        if await page.locator('[data-wn="close"]:visible').count():
                            await page.click('[data-wn="close"]')
                            await page.wait_for_timeout(400)
                        b = page.locator('[data-action="jrSceneClose"]:visible')
                        if await b.count():
                            await b.first.click()
                            await page.wait_for_timeout(400)

                async def later():   # a life card that popped up on its own: put it off ("Để sau")
                    b = page.locator('#lfScene[open] [data-action="lfLater"]')
                    if await b.count():
                        await b.first.click()
                        await page.wait_for_timeout(400)

                async def reload():
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(1500)
                    await calm()
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

                async def see(sel):
                    await page.wait_for_timeout(300)
                    await page.evaluate("s=>document.querySelector(s)?.scrollIntoView({block:'center'})", sel)
                    await page.wait_for_timeout(300)

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await shot(f'confirm-{len(list(OUT.glob(tag + "-confirm-*")))}')
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(1000)
                    await calm()

                await reload()
                await later()
                await page.wait_for_selector('.jr-house-row', timeout=10000)
                await page.click('.jr-house-row')
                await page.wait_for_selector('.hs-sheet[open] .hs-market', timeout=10000)
                await see('.hs-sheet [data-hs="rent"][data-kind="ky_tuc_xa"]')
                await shot('1-listing')
                await page.click('.hs-sheet [data-hs="rent"][data-kind="ky_tuc_xa"]')
                await confirm()
                await page.wait_for_selector('.hs-sheet .hs-dorm', timeout=10000)
                await page.evaluate("document.querySelector('.hs-sheet .hs-body').scrollTo(0,0)")
                await shot('2-rented')
                await see('.hs-sheet .hs-dorm-say')
                await shot('3-bunk-room')
                flash = await page.inner_text('.hs-sheet .bk-flash')
                print(tag, 'rent:', flash[:200])
                # The journey card, then a roommate moment.
                mutate(db, token, roommate_moment)
                await reload()
                await page.wait_for_timeout(1200)
                for _ in range(20):
                    if await page.evaluate("!!document.getElementById('lfScene')?.open"):
                        break
                    await page.wait_for_timeout(250)
                else:
                    await page.click('[data-action="lfOpen"]')
                    await page.wait_for_timeout(600)
                await shot('4-moment')
                await page.click('#lfScene .lf-choice[data-choice="chip"]')
                await page.wait_for_timeout(900)
                await shot('5-moment-done')
                await page.click('#lfScene [data-action="lfClose"]')
                await page.wait_for_timeout(600)
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                await see('.jr-house')
                await shot('6-journey-card')
                # Move to the closed room, then back to the dorm, then give the bed up.
                await page.click('.jr-house-row')
                await page.wait_for_selector('.hs-sheet[open] .hs-market', timeout=10000)
                await page.wait_for_timeout(1200)
                await see('.hs-sheet [data-hs="rent"][data-kind="tro_moi"]')
                await shot('7-move-offer')
                await page.click('.hs-sheet [data-hs="rent"][data-kind="tro_moi"]')
                await confirm()
                print(tag, 'move:', (await page.inner_text('.hs-sheet .bk-flash'))[:200])
                await see('.hs-sheet [data-hs="rent"][data-kind="ky_tuc_xa"]')
                await page.click('.hs-sheet [data-hs="rent"][data-kind="ky_tuc_xa"]')
                await confirm()
                await page.evaluate("document.querySelector('.hs-sheet .hs-body').scrollTo(0,0)")
                await page.click('.hs-sheet [data-hs="leave"]')
                await confirm()
                print(tag, 'leave:', (await page.inner_text('.hs-sheet .bk-flash'))[:200])
                await shot('8-left')
                await ctx.close()
            # One English pass on the phone.
            ctx = await browser.new_context(viewport=dict(width=390, height=844), locale='en-US')
            page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            mutate(db, token, seed)

            def rent(s):
                from game import housing as hs
                hs.apply(s, 'jr_home_rent', dict(kind='ky_tuc_xa', confirm=True))
                roommate_moment(s)
                s['settings']['lang'] = 'en'
            mutate(db, token, rent)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(2500)
            for _ in range(4):
                if await page.locator('[data-wn="close"]:visible').count():
                    await page.click('[data-wn="close"]')
                    await page.wait_for_timeout(400)
            await page.screenshot(path=str(OUT / 'en-390-moment.png'))
            await page.click('#lfScene [data-action="lfLater"]')
            await page.wait_for_timeout(400)
            await page.click('.jr-house-row')
            await page.wait_for_selector('.hs-sheet[open] .hs-dorm', timeout=10000)
            await page.wait_for_timeout(800)
            await page.screenshot(path=str(OUT / 'en-390-home.png'))
            await page.evaluate("document.querySelector('.hs-sheet .hs-dorm-say')?.scrollIntoView({block:'center'})")
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(OUT / 'en-390-room.png'))
            await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
