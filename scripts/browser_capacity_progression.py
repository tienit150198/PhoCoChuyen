"""Paid warehouse purchase/reload on isolated local PostgreSQL; no live services."""
import asyncio, copy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from browser_housing import server
from browser_business_licenses import mutate, read
from tests.helpers import Journey
from game import journey, inventory, boba
OUT=ROOT/'output/playwright/capacity-progression'

def seed(namespace,token,cid):
    j=Journey(cid);s=j.state
    journey.enable_story(s,4242)
    s['name']='Thử nâng kho'
    s['journey'].update(intro=True,gender='female',news=[])
    s['settings'].update(tutorialDone=True,whatsNewSeen='2.2.1')
    c=s['careers'][cid]
    c['ops']['finance']['opening_balance']+=100000-c['money'];c['money']=100000
    mutate(namespace,token,lambda old:(old.clear(),old.update(copy.deepcopy(s))))

async def main():
    from playwright.async_api import async_playwright,expect
    OUT.mkdir(parents=True,exist_ok=True);report=[];errors=[]
    with server() as (base,namespace):
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            for width in (390,1280):
                context=await browser.new_context(viewport=dict(width=width,height=860))
                page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                await page.goto(base);await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                token=next(x['value'] for x in await context.cookies() if x['name']=='mnl_session')
                for cid in ('clothing','com','milk_tea','farm'):
                    seed(namespace,token,cid)
                    await page.reload();await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='decor';b.hidden=true;document.body.append(b);b.click();b.remove();})()")
                    section=page.locator('section[aria-label="Sức chứa kho nghề"]')
                    await expect(section).to_be_visible()
                    first=section.locator('[data-item="warehouse_storage_'+cid+'_1"]')
                    second=section.locator('[data-item="warehouse_storage_'+cid+'_2"]')
                    await expect(second).to_be_disabled()
                    await first.click();await page.wait_for_selector('#confirmDialog[open]')
                    await page.locator('#confirmDialog [data-action="confirmYes"]').click()
                    await expect(first).to_be_disabled();await expect(second).to_be_enabled()
                    saved=read(namespace,token)['careers'][cid]
                    assert saved['money']==97000,(cid,saved['money'])
                    cap=boba.shelf_cap(saved) if cid=='milk_tea' else inventory.capacity(cid,saved)
                    assert cap==dict(clothing=120,com=180,milk_tea=90,farm=120)[cid]
                    assert await section.evaluate('(x)=>x.scrollWidth<=x.clientWidth+1')
                    assert await section.locator('.upgrade-card').evaluate_all('(cards)=>cards.every(c=>{const p=c.querySelector("p").getBoundingClientRect(),b=c.querySelector("button").getBoundingClientRect();return p.bottom<=b.top+1})')
                    await page.screenshot(path=str(OUT/f'{cid}-{width}.png'))
                    await page.reload();await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                    assert 'warehouse_storage_'+cid+'_1' in read(namespace,token)['careers'][cid]['upgrades']
                    report.append(dict(career=cid,width=width,paid=3000,capacity=cap,persisted=True))
                await context.close()
            await browser.close()
    assert not errors,errors
    (OUT/'report.json').write_bytes(json.dumps(report,ensure_ascii=False,indent=2).encode())
    print(json.dumps(report))

if __name__=='__main__':
    if sys.platform=='win32':asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
