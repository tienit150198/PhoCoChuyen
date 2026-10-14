"""Returning players see the combined notice once; settings can reopen it."""
import asyncio
import copy
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from browser_housing import server
from browser_creative_civic import read
from game import marriage,whats_new
from game.engine import validate_state
from game.storage import Store
from tests.test_quay import owner
OUT=ROOT/'output/playwright/whats-new'

def seed(namespace,token,seen):
    s=owner();s.update(name='Người kiểm thử',current='milk_tea',focus='milk_tea')
    s['journey'].update(intro=True,gender='female',life_day=4,news=[])
    s['settings'].update(tutorialDone=True,whatsNewSeen=seen,reduceMotion=True)
    validate_state(s);store=Store(namespace,story=True)
    try:marriage._mutate(store,{store.key(token):lambda old:(old.clear(),old.update(copy.deepcopy(s)))})
    finally:store.close_pool()

async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True,exist_ok=True);errors=[];cases=[]
    with server() as (base,namespace):
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            for width,seen in [(390,'2.0.5'),(1280,'2.4.1')]:
                context=await browser.new_context(viewport=dict(width=width,height=844));page=await context.new_page()
                page.on('pageerror',lambda e:errors.append(str(e)))
                await page.goto(base);await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                token=next(c['value'] for c in await context.cookies() if c['name']=='mnl_session')
                seed(namespace,token,seen);await page.reload()
                await page.locator('#interfacePrompt [data-interface="new"]').click(timeout=45000)
                try:await page.wait_for_selector('#wnDialog[open]',timeout=30000)
                except Exception:
                    await page.screenshot(path=str(OUT/f'{width}-FAILED.png'))
                    print(await page.evaluate("({dialogs:[...document.querySelectorAll('dialog[open]')].map(d=>({id:d.id,text:d.innerText.slice(0,800)})),hidden:document.hidden})"),flush=True)
                    state=read(namespace,token);print(dict(seen=state['settings']['whatsNewSeen'],day=state['journey']['life_day'],intro=state['journey']['intro']),flush=True)
                    raise
                await page.wait_for_timeout(700)
                card=page.locator('#wnDialog');assert '540' in await card.inner_text()
                assert whats_new.LATEST in await card.locator('#wnMeta').inner_text()
                assert await card.locator('.wn-list').first.locator('.wn-item').count()==len(whats_new.ENTRIES[0]['items'])
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert await card.evaluate('e=>{let r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth}')
                await page.screenshot(path=str(OUT/f'{width}-notice.png'))
                await card.locator('.wn-foot [data-wn="close"]').click()
                await page.wait_for_timeout(500)
                assert read(namespace,token)['settings']['whatsNewSeen']==whats_new.LATEST
                await page.reload();await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                await page.wait_for_timeout(2500);assert not await page.locator('#wnDialog[open]').count()
                # Close incidental notices so the settings controls are reachable.
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.locator('.iso-tools > summary').click()
                await page.locator('[data-action="settings"]:visible').first.click()
                await page.locator('[data-action="v4SetTab"][data-tab="play"]').click()
                await page.locator('[data-action="whatsNew"]').click()
                await page.wait_for_selector('#wnDialog[open]')
                cases.append(dict(width=width,previous_seen=seen,automatic=True,persisted=True,no_repeat=True,settings_reopen=True))
                print(f'{width}: passed',flush=True);await context.close()
            await browser.close()
    assert not errors,errors
    (OUT/'report.json').write_text(json.dumps(dict(cases=cases,errors=errors),indent=2),encoding='utf-8')

if __name__=='__main__':
    if sys.platform=='win32':asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
