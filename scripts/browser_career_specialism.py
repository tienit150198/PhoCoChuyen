"""Real HTTP/PostgreSQL learning, reception and settlement at mobile/desktop sizes."""
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from browser_housing import server
from browser_career_mastery import open_mastery
from browser_creative_civic import read,send_click
from browser_v04 import OVERFLOW
from tests.test_career_specialism import prepared
from tests.test_quay import owner
from game import marriage,career_specialism as sp,__version__
from game.engine import validate_state
from game.storage import Store

OUT=ROOT/'output/playwright/career-specialism'

def seed(namespace,token):
    state=owner(wallet=10000,trade='grocery',chapter=4)
    _,c=prepared('grocery');state['careers']['grocery']=c
    state.update(current='grocery',focus='grocery',name='Người kiểm thử')
    state['settings'].update(tutorialDone=True,whatsNewSeen=__version__)
    state['journey'].update(intro=True,gender='female',news=[])
    state['journey']['interface']=dict(newInterface=True,interfacePromptSeen=True)
    validate_state(state)
    store=Store(namespace,story=True)
    try:marriage._mutate(store,{store.key(token):lambda s:(s.clear(),s.update(copy.deepcopy(state)))})
    finally:store.close_pool()

async def command(page,name,value=None,button=None):
    if button is None:button=page.locator(f'[data-command-name="{name}"]').first
    await button.wait_for()
    await page.wait_for_timeout(400)
    form=button.locator('..')
    if value is not None:
        field=form.locator('[data-special-field]')
        if await field.evaluate('e=>e.tagName')=='SELECT':await field.select_option(str(value))
        else:await field.fill(str(value))
    return await send_click(page,button,name)

async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True,exist_ok=True);cases=[];errors=[]
    with server() as (base,namespace):
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            for width in (390,1280):
                context=await browser.new_context(viewport=dict(width=width,height=860));page=await context.new_page()
                page.on('pageerror',lambda e:errors.append(str(e)))
                try:
                    await page.goto(base);await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                    token=next(c['value'] for c in await context.cookies() if c['name']=='mnl_session')
                    seed(namespace,token);await page.reload();await open_mastery(page)
                    await command(page,'special_enrol')
                    for step in range(5):
                        await command(page,'special_practice',sp.exercise('grocery',1,step,1)['answer'])
                    await command(page,'special_offer')
                    await page.wait_for_timeout(450)
                    if not await page.locator('.special-stock').evaluate('e=>e.open'):
                        await page.locator('.special-stock > summary').click()
                    for index in range(2):
                        item=page.locator('.special-stock-item').nth(index)
                        await page.wait_for_timeout(450)
                        await item.locator('summary').scroll_into_view_if_needed()
                        await page.wait_for_timeout(450)
                        await item.locator('summary').click()
                        await command(page,'special_stock_buy',1,item.locator('[data-command-name="special_stock_buy"]'))
                        await command(page,'special_stock_receive',1)
                    await command(page,'special_start')
                    o=read(namespace,token)['careers']['grocery']['specialism']['job']
                    for step in range(5):
                        await command(page,'special_work',sp.exercise('grocery',1,step,o['quantity'],o['id'])['answer'])
                    await command(page,'special_settle')
                    c=read(namespace,token)['careers']['grocery'];assert c['specialism']['history'][-1]['net']==200
                    assert c['money']==800000000-3000+200
                    await page.locator('.special-history summary').click()
                    await page.wait_for_timeout(450)
                    overflow=await page.evaluate(OVERFLOW);assert not(overflow['page'] or overflow['sheet'] or overflow['over']),overflow
                    await page.screenshot(path=str(OUT/f'{width}-settled.png'))
                    cases.append(dict(width=width,passed=True,net=200,overflow=overflow));print(f'{width}: passed',flush=True)
                except Exception:
                    print(await page.locator('.special-stock-item').evaluate_all("es=>es.map(e=>({rect:e.getBoundingClientRect().toJSON(),open:e.open,parentOpen:e.parentElement.open}))"),flush=True)
                    await page.screenshot(path=str(OUT/f'{width}-FAILED.png'))
                    (OUT/f'{width}-FAILED.html').write_text(await page.content(),encoding='utf-8');raise
                finally:await context.close()
            await browser.close()
    assert not errors,errors
    (OUT/'report.json').write_text(json.dumps(dict(version=__version__,cases=cases,errors=errors),ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    if sys.platform=='win32':asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
