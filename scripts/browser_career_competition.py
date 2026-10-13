"""Real NPC case commands and persistence at mobile/desktop on isolated local PG."""
import asyncio, copy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from browser_housing import server
from browser_business_licenses import mutate, read
from tests.helpers import Journey
from tests.test_career_laundry import solve
from game import journey, promotion, engine
OUT=ROOT/'output/playwright/career-competition'


def seed(namespace,token):
    j=Journey('laundry');solve(j,j.task['id']);s=j.state
    journey.enable_story(s,4242)
    s['name']='Thử thi đua'
    s['journey'].update(intro=True,gender='female',news=[])
    s['settings'].update(tutorialDone=True,whatsNewSeen='2.2.1')
    rec=promotion.record(s,'laundry',True)
    rec.update(rank=3,good=30,worked=30)
    engine.validate_state(s)
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
                seed(namespace,token)
                await page.reload();await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                async def open_panel():
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='promo';b.hidden=true;document.body.append(b);b.click();b.remove();})()")
                await open_panel()
                card=page.locator('section[aria-label="Thi đua cùng đồng nghiệp"]')
                await expect(card).to_be_visible()
                assert await card.locator('.cc-standing').count()==4
                await card.locator('[data-command="competition_start"]').click()
                options=card.locator('[data-command="competition_answer"]')
                await expect(options).to_have_count(3)
                assert await card.evaluate('(x)=>x.scrollWidth<=x.clientWidth+1')
                assert await options.evaluate_all('(xs)=>xs.every(x=>x.getBoundingClientRect().height>=44)')
                await page.screenshot(path=str(OUT/f'case-{width}.png'))
                turn=read(namespace,token)['careers']['laundry']['turn']
                await options.first.click()
                await expect(card.locator('.cc-case-result')).to_be_visible()
                saved=read(namespace,token)['careers']['laundry']
                assert saved['competition']['today']['case']['option'] is not None
                assert saved['turn']==turn
                await page.reload();await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                await open_panel();await expect(card.locator('.cc-case-result')).to_be_visible()
                await expect(card.locator('[data-command="competition_answer"]')).to_have_count(0)
                await page.screenshot(path=str(OUT/f'result-{width}.png'))
                report.append(dict(width=width,peers=3,answered=True,persisted=True,no_turn_cost=True))
                await context.close()
            await browser.close()
    assert not errors,errors
    (OUT/'report.json').write_bytes(json.dumps(report,ensure_ascii=False,indent=2).encode())
    print(json.dumps(report))


if __name__=='__main__':
    if sys.platform=='win32':asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
