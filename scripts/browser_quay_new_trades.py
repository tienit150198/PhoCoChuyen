"""🏪 #501/#507: the new counter trades in the real app at 390x844 (dev tool, playwright + chromium, TEST_DATABASE_URL).

A story save with 12 nail jobs (chapter 3): the "Bán gì?" chips show 💄 Mỹ phẩm open and 🎀 Phụ kiện dễ thương locked
("… ở nghề Văn phòng phẩm (bạn đã làm 0/10)", a "Vào nghề Văn phòng phẩm" button only when that career is open), then a
💄 cart is opened and its card draws the lipstick stand. Any console error fails the run.

    python scripts/browser_quay_new_trades.py [out_dir]
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_quay as bq  # noqa: E402  (the server, the seeding helpers)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else bq.ROOT.parent / '_w095_shots' / 'quay-new-trades'
SEED = bq.SEED.replace("s['careers']['milk_tea']['metrics']['served'] = 12", "s['careers']['nail']['metrics']['served'] = 12")


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        with bq.server() as (base, db):
            ctx = await browser.new_context(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True, device_scale_factor=2)
            page = await ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            login = bq.py(SEED, db, token, 'Lan')
            await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1200)
            for _ in range(5):
                await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet)').forEach(d=>d.close())")
                await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='quay';b.hidden=true;document.body.append(b);b.click();b.remove();})()")
                await page.wait_for_timeout(800)
                if await page.locator('.qy-sheet[open] .qy-root h2').count():
                    break

            async def tap(sel):
                await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet):not(#confirmDialog)').forEach(d=>d.close())")
                await page.locator('.qy-sheet ' + sel).first.dispatch_event('click')   # (the sheet's sticky head may cover it)
                await page.wait_for_timeout(350)

            await tap('[data-qy="new"]')
            chips = await page.locator('.qy-sheet [data-qy="trade"]').all_inner_texts()
            print('chips', chips)
            assert any('Mỹ phẩm' in c and '🔒' not in c for c in chips), chips
            assert any('Phụ kiện dễ thương' in c and '🔒' in c for c in chips), chips
            assert any('Cá viên chiên' in c and '🔒' in c for c in chips), chips
            await page.locator('.qy-sheet [data-qy="trade"][data-id="cute_acc"]').scroll_into_view_if_needed()
            await tap('[data-qy="trade"][data-id="cute_acc"]')
            why = await page.locator('.qy-sheet .qy-why').inner_text()
            print('why', why)
            assert 'Văn phòng phẩm' in why and '0/10' in why, why
            await page.locator('.qy-sheet .qy-why').scroll_into_view_if_needed()
            await page.screenshot(path=str(OUT / '390x844-1-chips.png'))
            await tap('[data-qy="trade"][data-id="cosmetics"]')
            await tap('[data-qy="open"]')
            await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
            await page.click('#confirmDialog [data-action="confirmYes"]')
            await page.wait_for_selector('.qy-sheet canvas.qy-scene', timeout=10000)
            await page.wait_for_timeout(600)
            for _ in range(3):   # the game's own popups (new titles) come up after the first purchase
                await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet)').forEach(d=>d.close());document.querySelectorAll('.celebrate,.toast').forEach(e=>e.remove())")
                await page.wait_for_timeout(400)
            await page.locator('.qy-sheet canvas.qy-scene').first.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
            await page.screenshot(path=str(OUT / '390x844-2-cosmetics-cart.png'))
            fits = await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert fits
            await ctx.close()
        await browser.close()
    print('OK' if not errors else 'FAIL ' + repr(errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    asyncio.run(main())
