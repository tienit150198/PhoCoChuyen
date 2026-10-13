"""Real purchases and 528-unit delivery on isolated local PostgreSQL."""
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server
from browser_business_licenses import mutate, read
from tests.helpers import Journey
from tests.test_inventory_flow import set_money
from game import inventory, journey
from game.careers import clothing

OUT = ROOT / 'output/playwright/order-progression'


def seed(namespace, token):
    j = Journey('clothing'); s = j.state
    journey.enable_story(s, 4242)
    s['name'] = 'Thử hạn mức nhập'
    s['journey'].update(intro=True, gender='female', news=[])
    s['journey']['interface'] = dict(newInterface=True, interfacePromptSeen=True)
    s['settings'].update(tutorialDone=True, whatsNewSeen='2.3.0')
    for n in range(1, 6):
        j.c['upgrades'].append(f'warehouse_storage_clothing_{n}')
    inventory.add_lot(j.c, 'tee', 6, 0, 999, 'opening')
    clothing.on_stock(s, j.c, 'inv_receive')
    set_money(j.c, 1_000_000)
    mutate(namespace, token, lambda old: (old.clear(), old.update(copy.deepcopy(s))))


async def action(page, name):
    await page.evaluate("name=>{const b=document.createElement('button');b.dataset.action=name;b.hidden=true;document.body.append(b);b.click();b.remove();}", name)


async def main():
    from playwright.async_api import async_playwright, expect
    OUT.mkdir(parents=True, exist_ok=True)
    report, errors = [], []
    with server() as (base, namespace):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for width in (390, 1280):
                ctx = await browser.new_context(viewport=dict(width=width, height=860))
                page = await ctx.new_page()
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=45000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                seed(namespace, token)
                await page.reload(); await page.wait_for_selector('#app:not([hidden])')
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await action(page, 'inventory')
                await page.locator('[data-action=v4Order][data-item=tee]').click()
                await expect(page.locator('#order-qty')).to_have_attribute('max', '80')
                await page.locator('[data-action=v4OrderUpgrade]').click()
                section = page.locator('[data-gear-group=warehouse_order]')
                await expect(section).to_be_visible()
                await expect(section.locator('[data-item=warehouse_order_clothing_2]')).to_be_disabled()
                for n in range(1, 5):
                    button = section.locator(f'[data-item=warehouse_order_clothing_{n}]')
                    await button.click()
                    await page.locator('#confirmDialog[open] [data-action=confirmYes]').click()
                    await expect(button).to_be_disabled()
                saved = read(namespace, token)['careers']['clothing']
                assert saved['money'] == 858000, saved['money']
                assert inventory.capacity('clothing', saved) == 550
                await action(page, 'inventory')
                await page.locator('[data-action=v4Order][data-item=tee]').click()
                await expect(page.locator('#order-qty')).to_have_attribute('max', '528')
                await page.locator('[data-action=v4Qty][data-set="528"]').click()
                await expect(page.locator('#order-qty')).to_have_value('528')
                assert await page.locator('#sheetContent').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                await page.screenshot(path=str(OUT / f'order-528-{width}.png'))
                await page.locator('#order-go').click()
                await page.locator('#confirmDialog[open] [data-action=confirmYes]').click()
                await expect(page.locator('#order-go')).to_have_count(0)
                saved = read(namespace, token)['careers']['clothing']
                order = saved['ext']['inv']['orders'][-1]
                assert order['qty'] == 528
                # Advance the synthetic clock only; receipt still uses the real UI/action.
                def ready(s):
                    c = s['careers']['clothing']
                    c['turn'] += 100
                mutate(namespace, token, ready)
                await page.reload(); await page.wait_for_selector('#app:not([hidden])')
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await action(page, 'inventory')
                count = page.locator('#count-' + order['id'])
                await expect(count).to_be_visible()
                assert await page.locator('.inv-good').count() <= 100
                await page.locator('.inv-tray-tap:not([disabled])').first.click()
                counted = await count.input_value()
                await page.locator('[data-action=v4CratePage][data-page="1"]').click()
                await expect(count).to_have_value(counted)
                await page.locator('[data-action=v4CratePage][data-page="0"]').click()
                assert await page.locator('.inv-good.on').count() == int(counted)
                await page.screenshot(path=str(OUT / f'counting-{width}.png'))
                await count.fill(str(order['actual']))
                await page.locator('[data-action=v4Receive]').click()
                await expect(count).to_have_count(0)
                await page.reload(); await page.wait_for_selector('#app:not([hidden])')
                saved = read(namespace, token)['careers']['clothing']
                assert inventory.count(saved, 'tee') == 22 + order['actual']
                assert saved['ext']['inv']['orders'][-1]['status'] == 'received'
                assert 'warehouse_order_clothing_4' in saved['upgrades']
                report.append(dict(width=width, upgrade_paid=142000, ordered=528,
                                   received=order['actual'], persisted=True, csp='normal'))
                await ctx.close()
            await browser.close()
    assert not errors, errors
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
