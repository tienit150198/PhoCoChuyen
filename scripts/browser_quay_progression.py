"""Paid quay UI against an isolated local server and TEST_DATABASE_URL only."""
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from browser_housing import server
from browser_business_licenses import mutate, read
from tests.test_quay import opened, ST

OUT = ROOT / 'output/paid-convenience/quay-browser'


def seed(namespace, token):
    state = opened(wallet=1000000, staff=False)
    state['name'] = 'Quầy thử nghiệm'
    state['journey'].update(intro=True, gender='female', news=[])
    state['settings'].update(tutorialDone=True, whatsNewSeen='2.2.1')
    ST(state)['business']['stock'] = {'hong_tra': 495}
    ST(state)['fund'] = 100000
    mutate(namespace, token, lambda s: (s.clear(), s.update(copy.deepcopy(state))))


async def main():
    from playwright.async_api import async_playwright, expect
    OUT.mkdir(parents=True, exist_ok=True)
    report, errors = [], []
    with server() as (base, namespace):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for width, height in ((390, 844), (1280, 860)):
                context = await browser.new_context(viewport=dict(width=width, height=height))
                page = await context.new_page()
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=45000)
                token = next(c['value'] for c in await context.cookies() if c['name'] == 'mnl_session')
                seed(namespace, token)
                initial_wallet = read(namespace, token)['journey']['wallet']
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=45000)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='quay';b.hidden=true;document.body.append(b);b.click();b.remove();})()")
                await page.wait_for_selector('.qy-sheet[open] .qy-slots')

                async def buy(track):
                    await page.locator(f'[data-qy="convenience"][data-track="{track}"]').click()
                    await page.wait_for_selector('#confirmDialog[open]')
                    await page.locator('#confirmDialog [data-action="confirmYes"]').click()
                    await page.wait_for_selector('#confirmDialog[open]', state='hidden')
                    await expect(page.locator(f'[data-qy="convenience"][data-track="{track}"]')).to_be_enabled()

                assert '1 / 1' in await page.locator('.qy-slots h3').inner_text()
                await buy('slots')
                await expect(page.locator('.qy-slots h3')).to_contain_text('1 / 2')
                await page.locator('[data-qy="more"][data-id="q1"][data-part="stock"]').click()
                await page.wait_for_selector('.qy-stock-item')
                box = page.locator('#qy-stock-q1-hong_tra')
                assert await box.get_attribute('max') == '5'
                await box.fill('6')
                await box.dispatch_event('input')
                assert await page.locator('[data-qy="restock"]').is_disabled()
                await buy('storage')
                await buy('restock')
                await expect(box).to_have_attribute('max','10')
                await box.fill('10')
                await box.dispatch_event('input')
                await page.locator('[data-qy="restock"]').click()
                await page.wait_for_selector('#confirmDialog[open]')
                await page.locator('#confirmDialog [data-action="confirmYes"]').click()
                await expect(page.locator('.qy-part h4').first).to_contain_text('505')
                await page.locator('[data-qy="again"]').click()
                await page.wait_for_selector('#confirmDialog[open]')
                await page.locator('#confirmDialog [data-action="confirmYes"]').click()
                await expect(page.locator('.qy-part h4').first).to_contain_text('515')
                state = read(namespace, token)
                assert ST(state)['business']['paid_tier'] == {'storage': 1, 'restock': 1}
                assert state['journey']['quay']['paid_tier'] == {'slots': 1}
                assert sum(ST(state)['business']['stock'].values()) == 515
                assert state['journey']['wallet'] == initial_wallet - 9000
                await page.screenshot(path=str(OUT / f'{width}-paid-restock.png'))
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert await page.locator('.qy-sheet').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1')
                report.append(dict(viewport=[width,height],paid=9000,stock=515,slots=2,storage=750,batch=10))
                await context.close()
            await browser.close()
    assert not errors, errors
    (OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
