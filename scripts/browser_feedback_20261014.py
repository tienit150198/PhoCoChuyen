"""Feedback 371: show source invoices beside arithmetic, submit the actual answer."""
import asyncio, copy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from browser_housing import server
from browser_business_licenses import mutate, read
from browser_creative_civic import open_work, send_click
from tests.helpers import Journey
from tests.test_career_lawyer import step
from game import journey
OUT=ROOT/'output/playwright/feedback-20261014'

def seed(namespace,token):
    j=Journey('lawyer',day=11,slot=2);j.act('ask')
    for _ in range(3):step(j)
    s=j.state;journey.enable_story(s,4242)
    s['name']='Thử chứng từ';s['journey'].update(intro=True,gender='female',news=[])
    s['journey']['interface']=dict(newInterface=True,interfacePromptSeen=True)
    s['settings'].update(tutorialDone=True,whatsNewSeen='2.3.0')
    mutate(namespace,token,lambda old:(old.clear(),old.update(copy.deepcopy(s))))
    return j.task['id']

async def main():
    from playwright.async_api import async_playwright,expect
    OUT.mkdir(parents=True,exist_ok=True);report=[];errors=[]
    with server() as (base,namespace):
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            for width in (390,1280):
                ctx=await browser.new_context(viewport=dict(width=width,height=860))
                page=await ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                await page.goto(base);await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                token=next(c['value'] for c in await ctx.cookies() if c['name']=='mnl_session')
                tid=seed(namespace,token)
                await open_work(page,reload=True)
                await expect(page.locator('.lw-work')).to_contain_text('190 xu là mức trần')
                assert await page.locator('.lw-invoices').count()==1
                assert await page.locator('.lw-work').evaluate('(e)=>e.querySelector(".lw-invoices").getBoundingClientRect().bottom<=e.querySelector(".lw-controls").getBoundingClientRect().top')
                field=page.locator('.lw-work input[data-sk-amt]')
                await field.fill('160')
                await send_click(page,page.locator('[data-action="car:lawAmount"]'),'lw_submit')
                await expect(page.locator('.lw-step')).to_have_text('Bước 4/6')
                await page.screenshot(path=str(OUT/f'lawyer-{width}.png'))
                assert await page.locator('#sheetContent').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                await field.fill('90')
                await send_click(page,page.locator('[data-action="car:lawAmount"]'),'lw_submit')
                await expect(page.locator('.lw-step')).to_have_text('Bước 5/6')
                saved=next(t for t in read(namespace,token)['careers']['lawyer']['tasks'] if t['id']==tid)
                assert saved['work']['amount']==90
                report.append(dict(width=width,cap=190,invoices=[30,60,30],credit=30,accepted=90,csp='normal'))
                await ctx.close()
            await browser.close()
    assert not errors,errors
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))

if __name__=='__main__':
    if sys.platform=='win32':asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
