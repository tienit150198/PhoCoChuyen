"""Real-app public venue entry and return flows against an isolated PostgreSQL namespace."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server
from browser_chua import seed, mutate, read

OUT = ROOT / 'output' / 'temple-walk' / 'venue-routes'


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for new, width, height in [(True, 390, 844), (False, 1280, 800)]:
                tag = f'{"new" if new else "classic"}-{width}'
                ctx = await browser.new_context(viewport={'width': width, 'height': height}, has_touch=width < 500)
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0');localStorage.setItem('mnl.x3.week','blocked')}catch(e){}")
                page = await ctx.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])')
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                mutate(db, token, seed('vi', 'kem', 20, new))
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])')
                await page.wait_for_timeout(1800)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                wallet = read(db, token)['wallet']
                await page.screenshot(path=str(OUT / f'{tag}-boot.png'))

                async def open_home():
                    await page.locator(f'[data-action="{"isoCareers" if new else "home"}"]:visible').first.click()
                    await page.wait_for_selector('#sheet[open]')

                async def outings():
                    await open_home()
                    await page.wait_for_selector('#sheet [data-action="jrView"][data-view="outings"], #sheet [data-action="jrList"], #sheet [data-action="jrOutTab"]', timeout=12000)
                    if await page.locator('#sheet [data-action="jrOutTab"]:visible').count():
                        return
                    listing = page.locator('#sheet [data-action="jrList"]:visible')
                    if await listing.count():
                        await listing.first.click()
                        await page.wait_for_selector('#sheet [data-action="jrView"][data-view="outings"]')
                    household = page.locator('#sheet [data-action="jrView"][data-view="household"]:visible')
                    if await household.count():
                        await household.first.click()
                    else:
                        direct = page.locator('#sheet [data-action="jrView"][data-view="outings"]:visible')
                        if not await direct.count():
                            await page.locator('#sheet [data-action="marriage"][data-tab="family"]').first.click()
                            await page.locator('[data-mr="nav:personal"]:visible').click()
                    await page.locator('#sheet [data-action="jrView"][data-view="outings"]').click()
                    await page.wait_for_selector('#sheet [data-action="jrOutTab"]')

                async def verify_room(venue, station, panel, close_selector):
                    await page.wait_for_selector('.venue-visit[open]')
                    assert await page.evaluate('document.querySelector(".venue-visit").venueVisit.scene.room.id') == venue
                    assert read(db, token)['wallet'] == wallet, f'{venue} free entry changed wallet'
                    await page.locator(f'.venue-visit [data-station="{station}"]').click()
                    await page.wait_for_selector(panel, timeout=16000)
                    position = await page.evaluate('(()=>{const s=document.querySelector(".venue-visit").venueVisit.scene.state;return {x:s.x,y:s.y}})()')
                    assert await page.evaluate('document.querySelector(".venue-visit").venueVisit.suspended')
                    await page.locator(close_selector).first.click()
                    await page.wait_for_selector('.venue-visit[open]', timeout=8000)
                    assert await page.evaluate('(()=>{const s=document.querySelector(".venue-visit").venueVisit.scene.state;return {x:s.x,y:s.y}})()') == position
                    assert read(db, token)['wallet'] == wallet, f'{venue} viewing service changed wallet'
                    await page.screenshot(path=str(OUT / f'{tag}-{venue}.png'))
                    await page.locator('.venue-close').click()
                    await page.wait_for_selector('.venue-visit', state='detached')
                    checks.append(f'{tag}: {venue} real entry, physical station, existing panel, unchanged wallet, return at same position and exit passed')
                    print(checks[-1], flush=True)

                for venue, action, landmark, station in [('cafe', 'spendQuan', 'quan', 'counter'), ('spa', 'spendSpa', 'spa', 'reception'), ('cinema', 'spendRap', 'rap', 'screen')]:
                    await outings()
                    await page.locator(f'#sheet [data-action="{action}"]').click()
                    await verify_room(venue, station, '.sd-sheet[open]', '.sd-sheet [data-sd="close"]')

                await outings()
                await page.locator('#sheet [data-action="jrOutTab"][data-tab="salon"]').click()
                await verify_room('salon', 'reception', '#sheet[open] .out-preview', '#sheet [data-action="close"]')
                await outings()
                await page.locator('#sheet [data-action="jrOutVenue"][data-place="books"]').click()
                await verify_room('books', 'books', 'dialog[open] [data-choice]', 'dialog[open] [data-exit]')
                if not new:
                    for kind in ['fishing', 'boat', 'pool']:
                        await outings()
                        await page.locator(f'#sheet [data-action="leisurePlace"][data-kind="{kind}"]').click()
                        await page.wait_for_selector('.pixel-place[open]', timeout=15000)
                        assert read(db, token)['wallet'] == wallet
                        await page.screenshot(path=str(OUT / f'{tag}-{kind}.png'))
                        await page.keyboard.press('Escape')
                        checks.append(f'{tag}: {kind} outdoor entry is accessible and free')
                        print(checks[-1], flush=True)
                await ctx.close()
            await browser.close()
    report = {'checks': checks, 'page_errors': errors}
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert not errors, errors
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
