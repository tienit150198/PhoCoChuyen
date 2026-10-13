"""Real browser / local isolated PostgreSQL walkthrough of business licensing.

Uses synthetic saves only. Requires TEST_DATABASE_URL and Playwright Chromium.
"""
import asyncio
import copy
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
from browser_housing import server
from game import certificates, marriage, quay, business_progression as bp
from game.engine import apply_action
from game.storage import Store
from tests.test_quay import owner

OUT=ROOT/'output/playwright/business-licenses'

def mutate(namespace,token,fn):
    store=Store(namespace,story=True)
    try:marriage._mutate(store,{store.key(token):fn})
    finally:store.close_pool()

def read(namespace,token):
    store=Store(namespace,story=True)
    try:return store.read(token)[0]
    finally:store.close_pool()

def seed(namespace,token,place='kiot'):
    state=owner(wallet=200000)
    j=state['journey'];j.update(intro=True,gender='female',news=[])
    state['name']='Chủ quầy thử nghiệm'
    state['settings'].update(tutorialDone=True,whatsNewSeen='2.0.5')
    for gid in bp.CERTS:j['certificates'][gid]=dict(score=100,best=100,earned_day=1,attempts=1)
    for n in range(3):
        state,_=apply_action(state,None,'jr_quay_open',dict(trade='milk_tea',place=place,name=f'Tiệm thử {n+1}',confirm=True))
    j=state['journey'];j['certificates']={};j['quay'].pop(bp.KEY,None)
    j['wallet']=20000;j['news']=[]
    mutate(namespace,token,lambda s:(s.clear(),s.update(copy.deepcopy(state))))

def expire(namespace,token):
    def change(s):
        case=s['journey']['quay'][bp.KEY]
        case.update(issued_at=int((time.time()-bp.GRACE_SECONDS-2)*1000))
        case['deadline']=case['issued_at']+bp.GRACE_SECONDS*1000
    mutate(namespace,token,change)

async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True,exist_ok=True)
    report=[];errors=[]
    with server() as (base,namespace):
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            for width,height in ((390,844),(1280,860)):
                context=await browser.new_context(viewport=dict(width=width,height=height))
                page=await context.new_page()
                page.on('pageerror',lambda e:errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])',timeout=45000)
                token=next(c['value'] for c in await context.cookies() if c['name']=='mnl_session')
                seed(namespace,token)
                await page.reload()
                await page.wait_for_selector('#business-license-notice',timeout=45000)
                # Unrelated story popups in a synthetic save are not part of this flow.
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.locator('#business-license-notice button').click()
                await page.wait_for_selector('.qy-sheet[open] .qy-license')
                assert '72 giờ' in await page.locator('.qy-license').inner_text()
                await page.screenshot(path=str(OUT/f'{width}-notice.png'))
                issued=read(namespace,token)['journey']['quay'][bp.KEY]['issued_at']
                await page.reload()
                await page.wait_for_selector('#business-license-notice')
                assert read(namespace,token)['journey']['quay'][bp.KEY]['issued_at']==issued
                expire(namespace,token)
                await page.reload()
                await page.wait_for_selector('#business-license-notice')
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.locator('#business-license-notice button').click()
                await page.wait_for_selector('.qy-sheet[open] .qy-license')
                assert '2 quầy' in await page.locator('.qy-license').inner_text()
                assert await page.locator('[data-qk="st:q2"] [data-qy="runstart"]').is_disabled()
                await page.screenshot(path=str(OUT/f'{width}-restricted.png'))
                for level,gid in enumerate(bp.CERTS,1):
                    await page.locator('.qy-license [data-qy="licenseLearn"]').click()
                    await page.wait_for_selector(f'#ct-{gid} [data-action="jrCertEnrol"]')
                    assert await page.locator(f'#ct-{gid} [data-mode="self"]').count()==0
                    await page.locator(f'#ct-{gid} [data-mode="class"]').click()
                    await page.locator('#confirmDialog [data-action="confirmYes"]').click()
                    await page.wait_for_selector('[data-action="jrCertAnswer"]')
                    state=read(namespace,token)
                    paper=state['journey']['study']['paper']
                    for qid in paper['qs']:
                        answer=certificates.KEY[gid][qid]['answer']
                        await page.locator(f'[data-action="jrCertAnswer"][data-q="{qid}"][data-option="{answer}"]').click()
                    await page.wait_for_selector('#dpDialog[open]',timeout=15000)
                    await page.locator('#dpDialog [data-action="jrCertDipClose"]').click()
                    await page.locator('[data-action="quay"][data-resume="true"]').click()
                    await page.wait_for_selector('.qy-sheet[open] .qy-license')
                    current=read(namespace,token)
                    assert certificates.earned(current['journey'],gid)
                    assert len(bp.evaluate(current)['blocked_ids'])==max(0,3-max(1,level))
                assert read(namespace,token)['journey']['wallet']==11750
                await page.screenshot(path=str(OUT/f'{width}-qualified.png'))
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                report.append(dict(viewport=[width,height],paid=8250,courses=3,restored=3))
                # Return from a lower stall's expansion panel without losing context.
                seed(namespace,token,place='xe')
                await page.reload()
                await page.wait_for_selector('#business-license-notice')
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.locator('#business-license-notice button').click()
                panel=await page.locator('.qy-license').inner_text()
                assert 'Chứng chỉ Kinh doanh nâng cao' not in panel and 'Chứng chỉ Quản lý chuỗi' not in panel
                await page.locator('[data-qy="more"][data-id="q3"][data-part="up"]').click()
                course=page.locator('[data-qk="st:q3"] [data-qy="licenseLearn"]').first
                await course.scroll_into_view_if_needed()
                await course.click()
                await page.wait_for_selector('#ct-business_basics')
                await page.locator('[data-action="quay"][data-resume="true"]').click()
                await page.wait_for_selector('.qy-sheet[open]')
                assert await page.locator('[data-qk="st:q3"] .qy-grow').count()==1
                assert await page.locator('.qy-sheet').evaluate('(d)=>d.scrollTop')>500
                assert await course.is_visible()
                await context.close()
            await browser.close()
    assert not errors,errors
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    # psycopg's imported helpers select a Windows selector loop; Chromium needs subprocesses.
    if sys.platform=='win32':asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
