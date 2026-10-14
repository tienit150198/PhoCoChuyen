"""Two real players exercise temple card privacy on a disposable local PostgreSQL server.

python scripts/browser_chua_visibility.py [output_dir]
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_chua import mutate, seed
from browser_housing import server

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'output/temple-visibility/browser'


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, results = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for width, new_interface in ((390, True), (1280, True), (390, False), (1280, False)):
                tag = f'{width}-{"new" if new_interface else "classic"}'

                async def setup(name):
                    context = await browser.new_context(viewport=dict(width=width, height=844 if width == 390 else 800),
                                                        reduced_motion='reduce', is_mobile=width == 390, has_touch=width == 390)
                    await context.add_init_script("localStorage.setItem('mnl.wn.seen','99.0.0');localStorage.setItem('mnl.x3.week','blocked')")
                    page = await context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    token = next(c['value'] for c in await context.cookies() if c['name'] == 'mnl_session')
                    def fixture(save):
                        seed(new_interface=new_interface)(save)
                        save['name'] = name
                    mutate(db, token, fixture)
                    await page.reload()
                    return context, page, token

                async def open_fence(page):
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(1400)
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    if new_interface:
                        await page.locator('[data-action="isoCareers"]:visible').first.click()
                        await page.locator('#sheet [data-action="jrView"][data-view="life"]').first.click()
                    else:
                        await page.click('#topbar [data-action="status"]')
                        await page.click('#sheet [data-action="stView"][data-view="life"]')
                    await page.click('#sheet .cg-enter')
                    await page.wait_for_selector('.cv-sheet[open] canvas')
                    await page.click('.cv-path [data-cv="step"][data-id="board"]')
                    await page.wait_for_selector('.cv-card-board')
                    await ready(page)

                async def ready(page):
                    await page.locator('.cv-card-board').wait_for()
                    await page.locator('.cv-card-board [role=status]').wait_for(state='hidden', timeout=30000)
                    await page.locator('.cv-card-board [data-cv=card-toggle][disabled]').first.wait_for(state='hidden', timeout=30000)

                async def public_board(page):
                    await page.click('[data-cv="card-tab"][data-id="public"]')
                    await ready(page)

                async def refresh(page):
                    await page.click('[data-cv="card-refresh"]')
                    await ready(page)

                async def create_card(page, message, public=False):
                    if await page.locator('.cv-panel [data-cv="compose"]').count():
                        await page.click('.cv-panel [data-cv="compose"]')
                    await page.click('[data-cv="card-recipient"][data-id="ca_nha"]')
                    await page.click('[data-cv="card-blessing"][data-id="binh_an"]')
                    assert await page.locator('[data-cv="card-public"][data-public="false"]').get_attribute('aria-pressed') == 'true'
                    await page.fill('[name="card-name"]', 'Gia đình Lan')
                    await page.fill('[name="card-message"]', message)
                    if public:
                        await page.click('[data-cv="card-public"][data-public="true"]')
                    await page.click('[data-cv="card-send"]')
                    await page.wait_for_selector('.cv-result')
                    await page.click('.cv-panel [data-cv="board"]')
                    await ready(page)
                    row = page.locator('.cv-card').filter(has_text=message)
                    await row.wait_for()
                    return await row.get_attribute('data-card-id')

                owner_context, owner, token = await setup('Lan')
                reader_context, reader, reader_token = await setup('Minh')
                await open_fence(owner)
                private_text, public_text = f'Riêng {tag}', f'Chung {tag}'
                private_id = await create_card(owner, private_text)
                public_id = await create_card(owner, public_text, public=True)
                await owner.screenshot(path=str(OUT / f'{tag}-owner.png'))
                await open_fence(reader)
                await public_board(reader)
                assert await reader.locator(f'.cv-card[data-card-id="{public_id}"]').count() == 1
                assert private_text not in await reader.locator('.cv-card-board').inner_text()
                assert await reader.locator('[data-cv="card-toggle"]').count() == 0
                response = await reader_context.request.get(base + '/api/chua/cards?scope=public&limit=20')
                data = await response.json()
                assert all(not {'sid', 'owner', 'owner_sid', 'token'}.intersection(row) for row in data['rows'])
                assert token not in json.dumps(data) and reader_token not in json.dumps(data)
                await reader.screenshot(path=str(OUT / f'{tag}-public.png'))
                # Public -> private disappears for the other player on the next read.
                await owner.locator(f'[data-cv="card-toggle"][data-id="{public_id}"]').click()
                await ready(owner)
                await refresh(reader)
                assert await reader.locator(f'.cv-card[data-card-id="{public_id}"]').count() == 0
                # Existing private -> public and back, independent of creation-time choice.
                await owner.locator(f'[data-cv="card-toggle"][data-id="{private_id}"]').click()
                await ready(owner)
                await refresh(reader)
                assert await reader.locator(f'.cv-card[data-card-id="{private_id}"]').count() == 1
                await owner.locator(f'[data-cv="card-toggle"][data-id="{private_id}"]').click()
                await ready(owner)
                # Archive the initial cards and exercise more than 100 rows of owner paging.
                def older(save):
                    from game import chua
                    for index in range(101):
                        chua.action(save, 'jr_chua_do', dict(act='nguyen', recipient='ca_nha', blessing='binh_an', message=f'Archive {tag} {index}'))
                mutate(db, token, older)
                await owner.reload()
                await open_fence(owner)
                for _ in range(8):
                    if await owner.locator(f'.cv-card[data-card-id="{public_id}"]').count():
                        break
                    await owner.click('[data-cv="card-more"]')
                    await ready(owner)
                assert await owner.locator('.cv-card').count() == 103
                await owner.locator(f'[data-cv="card-toggle"][data-id="{public_id}"]').click()
                await ready(owner)
                assert await owner.locator(f'.cv-card[data-card-id="{public_id}"] .cv-card-privacy').inner_text() == 'Công khai'
                await refresh(reader)
                assert await reader.locator(f'.cv-card[data-card-id="{public_id}"]').count() == 1
                await owner.screenshot(path=str(OUT / f'{tag}-archived-public.png'))
                await owner.locator(f'[data-cv="card-toggle"][data-id="{public_id}"]').click()
                await ready(owner)
                await refresh(reader)
                assert await reader.locator(f'.cv-card[data-card-id="{public_id}"]').count() == 0
                assert await reader.locator(f'.cv-card[data-card-id="{private_id}"]').count() == 0
                results.append(dict(viewport=width, interface='new' if new_interface else 'classic', owner_cards=103,
                                    private_hidden=True, public_visible=True, revoked_hidden=True, archived_toggle=True))
                print(tag, 'passed public/private creation, owner controls, revoke, and 103-card archive paging', flush=True)
                await owner_context.close()
                await reader_context.close()
            await browser.close()
    (OUT / 'results.json').write_text(json.dumps(dict(passes=results, errors=errors), indent=2), encoding='utf-8')
    assert not errors, errors
    print('page errors: none', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
