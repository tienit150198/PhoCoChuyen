"""♿ Chạm chọn, chạm đặt (góp ý #443): the room editor without dragging, on a phone (dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server with the home of scripts/browser_decor_2026.py (a villa with seven
pieces in the living room). At 390x844 with touch: tap a piece (chosen: outline, steps, ✕ Bỏ chọn, a line in the live
region), tap a free spot of the floor (it moves there), press a named cell button from the keyboard (focus stays on it),
step one cell, let go; then in the 3D view choose a shop card and put it down with the small cell map. Checks every
piece and cell has a screen-reader name and the sheet never scrolls sideways. Screenshots to the out dir; exit 1 on a
console error or a failed step.

    python scripts/browser_deco_tap.py [out_dir]
"""
import asyncio
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_deco import mutate, tz_for  # noqa: E402
from browser_decor_2026 import seed  # noqa: E402
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_deco_tap_shots'
CELL = re.compile(r'^(tường )?hàng \d+ cột \d+, ')


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, failed = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844), timezone_id=tz_for(10), has_touch=True, is_mobile=True)
            await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.decoTip2','1')}catch(e){}")
            page = await ctx.new_page()
            known = []   # the friends' change log answers this guest 401 (no card): expected, as in browser_decor_2026.py
            page.on('response', lambda r: r.status == 401 and r.url.endswith('/api/home-guests/deco/log') and known.append(r.url))
            page.on('console', lambda m: m.type == 'error' and not (known and '401' in m.text) and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')

            def expect(ok, what):
                print('  ✓' if ok else '  ✗', what)
                if not ok:
                    failed.append(what)

            async def popups():
                for _ in range(4):
                    b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, button:has-text("Đã hiểu"):visible, button:has-text("Tuyệt!"):visible')
                    if not await b.count():
                        break
                    await b.first.click()
                    await page.wait_for_timeout(400)

            async def shot(name, sel=None):
                await page.wait_for_timeout(400)
                if sel:
                    await page.locator(sel).first.scroll_into_view_if_needed()
                    await page.wait_for_timeout(200)
                await page.screenshot(path=str(OUT / f'390x844-{name}.png'))

            async def live():
                await page.wait_for_timeout(150)
                await page.wait_for_function("document.querySelector('.dc-sheet')?.getAttribute('aria-busy')!=='true'", timeout=10000)
                await page.wait_for_timeout(450)
                return await page.evaluate("document.querySelector('.dc-sheet .dc-live')?.textContent||''")

            async def where(k):
                return await page.evaluate(f"document.querySelector('.dc-sheet svg.dc-room g.dc-it[data-k=\"{k}\"]')?.getAttribute('aria-label')||''")

            async def sideways():
                return await page.evaluate("(()=>{const d=document.querySelector('.dc-sheet');return Math.max(d.scrollWidth-d.clientWidth,document.documentElement.scrollWidth-innerWidth);})()")

            mutate(db, token, seed)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await page.wait_for_timeout(1500)
            await popups()
            await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
            if not await page.locator('.jr-house-row:visible').count():
                await page.get_by_role('button', name='Công việc').first.click()
                await page.wait_for_timeout(800)
            await page.wait_for_selector('.jr-house-row', timeout=10000)
            await page.click('.jr-house-row')
            await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
            await popups()
            await page.click('.hs-sheet [data-hs="inside"]:not([data-mode])')
            await page.wait_for_selector('.dc-sheet[open] .dc-stage', timeout=10000)
            await page.wait_for_timeout(800)
            await page.click('.dc-sheet [data-dc="view3d"][data-mode="2d"]')
            await page.wait_for_selector('.dc-sheet svg.dc-room[data-room="living"]', timeout=8000)
            await page.click('.dc-sheet [data-dc="edit"]')
            await page.wait_for_timeout(500)

            # ---- every placed piece says its name and where it is
            labels = await page.evaluate("[...document.querySelectorAll('.dc-sheet svg.dc-room g.dc-it[data-uid]')].map(g=>g.getAttribute('aria-label'))")
            expect(len(labels) >= 7 and all(re.search(r', ((tường )?hàng \d+ cột \d+|trên .+)$', l or '') for l in labels), f'each piece: name and place ({labels})')

            # ---- tap a piece: chosen (the seed stacks the pieces in one corner: the one on top is chosen)
            g = page.locator('.dc-sheet svg.dc-room g.dc-it[data-k="cay_bang_sing"] .dc-hit')
            box = await g.bounding_box()
            await page.touchscreen.tap(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            said = await live()
            k = await page.evaluate("document.querySelector('.dc-sheet svg.dc-room g.dc-it[aria-pressed=\"true\"]')?.dataset.k||''")
            label = await where(k) if k else ''
            expect(k and said == f'Đã chọn {label}. Chạm chỗ muốn đặt.', f'chosen: {k}; the live region: {said!r}')
            expect(await page.locator('.dc-sheet svg.dc-room .dc-selbox').count() == 1, 'the piece shows it is chosen (outline, aria-pressed)')
            steps = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-steps button')].map(b=>b.getAttribute('aria-label')||b.textContent)")
            expect(len(steps) == 5 and 'Dời sang trái một ô' in steps and '✕ Bỏ chọn' in steps, f'⬅️⬆️⬇️➡️ and ✕ Bỏ chọn ({steps})')
            cells = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-cells.over button.dc-cell')].map(b=>b.getAttribute('aria-label'))")
            expect(len(cells) >= 10 and all(CELL.match(c or '') for c in cells), f'{len(cells)} cell buttons, each named ({cells[:3]}…)')
            expect(await sideways() <= 0, 'no sideways scroll')
            await shot('01-chosen', '.dc-sheet .dc-roomwrap')
            await shot('02-chosen-tools', '.dc-sheet .dc-tools')

            # ---- tap a free spot of the floor: it moves there
            before = await where(k)
            free = page.locator('.dc-sheet .dc-cells.over button.dc-cell[aria-label$=", trống"]')
            box = await free.nth(await free.count() // 2).bounding_box()
            await page.touchscreen.tap(box['x'] + box['width'] / 2, box['y'] + box['height'] * .8)
            said = await live()
            after = await where(k)
            expect(after != before and 'giờ ở' in said, f'a tap on the floor moves it ({before} → {after}; {said!r})')
            await shot('03-moved', '.dc-sheet .dc-roomwrap')
            await popups()   # the first move of the day may bring the building's notice (a scene over the sheet)

            # ---- a cell button from the keyboard (a screen reader's double tap is the same click)
            free = page.locator('.dc-sheet .dc-cells.over button.dc-cell[aria-label$=", trống"]')
            target = free.first
            name = await target.get_attribute('aria-label')
            await target.focus()
            await page.keyboard.press('Enter')
            said = await live()
            after = await where(k)
            expect(after.endswith(name.split(',')[0]), f'Enter on "{name}" puts it there ({after})')
            focus = await page.evaluate("(document.activeElement?.outerHTML||'').slice(0,120)")
            expect('dc-cell' in focus, f'focus stays on the cell ({focus})')
            await shot('04-cell-keyboard', '.dc-sheet .dc-roomwrap')

            # ---- one step right
            await page.click('.dc-sheet .dc-steps [data-dc="step"][data-dx="1"]')
            await page.wait_for_timeout(900)
            said = await live()
            expect('giờ ở' in said, f'➡️ one cell ({said!r})')

            # ---- a cell that cannot take it says why
            bad = page.locator('.dc-sheet .dc-cells.over button.dc-cell.bad')
            if await bad.count():
                await bad.first.focus()
                await page.keyboard.press('Enter')
                said = await live()
                expect(said.startswith('Chỗ này') or 'không' in said, f'a blocked cell says why ({said!r})')

            # ---- let go
            await page.click('.dc-sheet [data-dc="unsel"]')
            said = await live()
            expect(said.startswith('Đã bỏ chọn'), f'✕ Bỏ chọn ({said!r})')
            expect(await page.locator('.dc-sheet .dc-cells').count() == 0, 'nothing chosen: no cells')

            # ---- the 3D view: a shop card, then the small map
            await page.click('.dc-sheet [data-dc="view3d"][data-mode="3d"]')
            await page.wait_for_timeout(2000)
            await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
            await page.fill('.dc-sheet [data-dc-search]', 'chau sen da')
            await page.wait_for_timeout(700)
            await page.click('.dc-sheet [data-dc="hold"][data-k="chau_sen_da"]')
            said = await live()
            expect(said.startswith('Đã chọn Chậu sen đá.'), f'a card chosen ({said!r})')
            n = await page.locator('.dc-sheet .dc-cells.map button.dc-cell').count()
            expect(n >= 10, f'under the 3D view: a map of {n} cells')
            expect(await sideways() <= 0, 'no sideways scroll (3D)')
            await shot('05-3d-map', '.dc-sheet .dc-cells.map')
            await page.locator('.dc-sheet .dc-cells.map button.dc-cell[aria-label$=", trống"]').first.click()
            await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
            await page.click('#confirmDialog [data-action="confirmYes"]')
            await page.wait_for_timeout(1200)
            await popups()
            said = await live()
            expect('Chậu sen đá giờ ở' in said, f'bought and placed from the map ({said!r})')
            await shot('06-3d-placed', '.dc-sheet .dc-stage')
            await ctx.close()
            await browser.close()
    for e in errors:
        print('console:', e)
    for f in failed:
        print('FAILED:', f)
    print('shots in', OUT)
    sys.exit(1 if errors or failed else 0)


if __name__ == '__main__':
    asyncio.run(main())
