#!/usr/bin/env python3
"""Optional browser smoke suite; runtime game itself has no third-party dependency.

Start server first. Install development-only playwright and httpx, then:
  python scripts/browser_smoke.py --base http://127.0.0.1:8765 --bridge --chromium /usr/bin/chromium
Without --bridge this uses normal browser navigation and browser networking.
The bridge is ONLY a test adapter for environments that block navigation.
"""
import argparse,datetime,json,sys,time,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_harness import BrowserHarness
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts';ART.mkdir(exist_ok=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',default='http://127.0.0.1:8765');ap.add_argument('--bridge',action='store_true');ap.add_argument('--chromium',default=None);args=ap.parse_args()
    checks=[];errors=[];start=time.monotonic();h=None
    def record(name):checks.append(name);print('PASS',name,flush=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=args.chromium)
        context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1,accept_downloads=True)
        page=context.new_page();page.set_default_timeout(6500)
        page.on('pageerror',lambda e:errors.append(str(e)))
        h=BrowserHarness(page,args.base,args.bridge)
        def settle():
            page.wait_for_timeout(100)
            page.wait_for_function("!document.body.classList.contains('busy')")
            page.wait_for_timeout(70)
        def click(sel):page.locator(sel).first.click();settle()
        def action(a,extra='',root='#sheet'):
            # Shell pages moved from the dock to the rail in v0.5.
            if root=='#dock' and not page.locator(f'#dock [data-action="{a}"]{extra}').count():root='#rail'
            click(f'{root} [data-action="{a}"]{extra}')
        def command(c,contains=None):
            sel=f'#sheet [data-command="{c}"]'+(f'[data-payload*="{contains}"]' if contains else '')
            click(sel)
        def confirm():action('confirmYes',root='#confirmDialog')
        def close():action('close')
        def state():
            if args.bridge:return h.client.get('/api/state').json()['state']
            return page.evaluate("async()=> (await(await fetch('/api/state')).json()).state")
        def rawsave():
            if args.bridge:return h.client.get('/api/save/export').json()
            return page.evaluate("async()=> (await(await fetch('/api/save/export')).json())")
        def shot(name):
            page.wait_for_function("document.querySelectorAll('#toasts .toast:not(.leaving)').length===0",timeout=7000)
            page.wait_for_timeout(350)
            page.screenshot(path=str(ART/name),full_page=True)
        def choose(c):
            if not page.locator('#sheet[open] [data-action="choose"]').count():
                if page.locator('#sheet[open]').count():close()
                action('home',root='#rail')
            action('choose',f'[data-career="{c}"]');settle()
            assert state()['current']==c
            if not state()['careers'][c]['open']:action('start')
            elif page.locator('#sheet[open]').count():close()
        def job():action('job',root='#taskHUD')
        def finish_event():
            command('event_read','observe');command('event_read','record')
            command('event_choose','b');action('confirmEvent');confirm()
            action('eventStep');action('eventStep')
            assert state()['careers'][state()['current']]['event']['stage']=='resolved'
        try:
            h.load();settle()
            assert page.locator('#sheet [data-action="choose"]').count()==7
            shot('01-career-select.png');record('Home: seven playable careers and 12 future previews')
            choose('mother_baby');shot('02-mother-baby-scene.png');job()
            command('ask');command('shop_pick','cat_bag')
            action('jobTab','[data-tab="pack"]');action('paper','[data-value="cream"]')
            page.locator('#gift-card').fill('Chúc bạn một ngày vui!')
            action('pack');action('jobTab','[data-tab="checkout"]');command('shop_check')
            shot('03-shop-workbench.png')
            action('deliverMB');confirm()
            s=state()['careers']['mother_baby'];assert s['money']==402,s['money'];assert s['day_completed']==1
            assert len(s['feed'])>=1
            record('Mother & baby: ask, pick, pack, verify, deliver, stock/money and review')
            close();action('event',root='#taskHUD');finish_event();command('event_dismiss')
            record('Story director: real event evidence, choice, execution and completion')
            action('practice','[data-event="MB-E07"]')
            command('event_read','observe');command('event_read','record');command('event_choose','b')
            shot('04-influencer-story.png');action('confirmEvent');confirm();action('eventStep');action('eventStep')
            assert state()['careers']['mother_baby']['money']==402
            command('event_dismiss');record('Influencer vignette rehearsal: no economic reward or loss')
            close();action('phone',root='#dock')
            page.locator('#post-text').fill('Góc cửa sổ hôm nay thật đẹp!')
            click('#postForm button[type="submit"]')
            command('advance');command('advance')
            s=state()['careers']['mother_baby'];post=next(x for x in s['feed'] if x.get('text')=='Góc cửa sổ hôm nay thật đẹp!')
            assert len(post['comments'])>=1
            # Reply to a real NPC review, then advance to read an acknowledgement.
            reply=page.locator('form[data-reply-post]').first
            reply.locator('input').fill('Cảm ơn bạn đã ghé tiệm nhé!')
            reply.locator('button').click();settle();command('advance')
            shot('05-neighbourhood-feed.png');record('Feed: player post, NPC comment, review reply and follow-up')
            close();action('people',root='#rail');action('chat')
            page.locator('#chat-input').fill('Bạn còn nhớ lần ghé tiệm vừa rồi không?')
            click('#chatForm button[type="submit"]')
            assert page.locator('.bubble').count()>=2
            shot('06-npc-conversation.png');record('Free text NPC conversation and event-backed memory')
            close();action('decor',root='#dock');action('buyUpgrade','[data-item="plant"]');confirm()
            page.locator('[data-decor-item="plant"]').select_option('front');settle()
            assert state()['careers']['mother_baby']['decor']['plant']['spot']=='front'
            close();action('album',root='#rail');action('photo');settle()
            assert len(state()['careers']['mother_baby']['album'])==1
            record('Decor: purchase, placement and actual canvas photo in album')
            choose('pharmacy');shot('07-pharmacy-scene.png');job();command('ask')
            page.locator('#ph-filter').select_option('P-01');settle()
            command('ph_inspect','P-01-A');command('ph_pick','P-01-A')
            for k in ['code','quantity','lot']:page.locator(f'[data-phcheck="{k}"]').check()
            action('verifyPH');shot('08-pharmacy-workbench.png');action('deliverPH');confirm()
            s=state()['careers']['pharmacy'];assert s['money']==360,s['money'];assert s['day_completed']==1
            record('Pharmacy: fictional code, lot inspection, triple check and delivery')
            choose('accounting');shot('09-accounting-scene.png');job()
            for doc in ['CT-01','CT-02','CT-03','CT-04']:command('ac_inspect',doc)
            shot('10-accounting-workbench.png');command('ac_duplicate','CT-04')
            for doc in ['CT-01','CT-02']:action('selectDoc',f'[data-id="{doc}"]')
            action('selectTx','[data-id="GD-01"]');action('match')
            action('selectDoc','[data-id="CT-03"]');action('selectTx','[data-id="GD-02"]');action('match')
            action('completeAC');confirm()
            s=state()['careers']['accounting'];assert s['money']==390,s['money'];assert s['day_completed']==1
            record('Accounting: source inspection, duplicate exclusion, many-to-one groups and handover')
            choose('customer_care');shot('11-customer-care-scene.png');job();command('cs_identity')
            for ev in ['BC-1','BC-2','BC-3']:command('cs_evidence',ev)
            command('cs_propose','reship');action('executeCS');confirm()
            command('advance');command('advance');command('cs_confirm')
            shot('12-customer-care-workbench.png');action('closeCS');confirm()
            s=state()['careers']['customer_care'];assert s['money']==385,s['money'];assert s['day_completed']==1
            record('Customer care: identity, evidence, proposal, execution, confirmation and closure')
            close();action('settings',root='#topbar');page.locator('#player-name').fill('Bạn Mây')
            page.locator('#setting-reduceMotion').check();click('#settingsForm button[type="submit"]')
            save=rawsave();before={k:v['money'] for k,v in state()['careers'].items()}
            with page.expect_download() as info:action('export')
            exported=json.loads(Path(info.value.path()).read_text());assert exported['format']==save['format']
            page.locator('#player-name').fill('Tên tạm');click('#settingsForm button[type="submit"]')
            payload=json.dumps(save,ensure_ascii=False).encode()
            page.locator('#import-file').set_input_files({'name':'save.json','mimeType':'application/json','buffer':payload})
            settle();confirm();assert state()['name']=='Bạn Mây'
            h.reload();settle();assert state()['name']=='Bạn Mây'
            assert {k:v['money'] for k,v in state()['careers'].items()}==before
            record('Settings, UI export/import and fresh-page reload retain all four careers')
            # Fresh portrait session proves first-time onboarding and small-screen controls.
            mobile=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
            mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
            mh=BrowserHarness(mp,args.base,args.bridge);mh.load();mp.wait_for_timeout(400)
            mp.screenshot(path=str(ART/'13-mobile-career-select.png'),full_page=True)
            mp.locator('[data-action="choose"][data-career="mother_baby"]').click();mp.wait_for_timeout(500)
            mp.wait_for_function("!document.body.classList.contains('busy')")
            mp.locator('#sheet [data-action="start"]').click();mp.wait_for_timeout(400)
            mp.screenshot(path=str(ART/'14-mobile-scene.png'),full_page=True)
            assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            mp.locator('#taskHUD [data-action="job"]').click();mp.wait_for_timeout(500)
            mp.locator('#sheet [data-command="ask"]').click();mp.wait_for_timeout(300)
            mp.wait_for_function("document.querySelectorAll('#toasts .toast:not(.leaving)').length===0",timeout=7000)
            mp.wait_for_timeout(350)
            mp.screenshot(path=str(ART/'15-mobile-workbench.png'),full_page=True)
            assert mp.evaluate("document.querySelector('#sheet').scrollWidth<=document.querySelector('#sheet').clientWidth+2")
            mp.locator('#sheet [data-action="close"]').first.click();mp.locator('#dock [data-action="help"], #rail [data-action="help"]').first.click()
            assert mp.locator('#sheet [data-action="album"]').count()==1
            assert mp.locator('#sheet [data-action="journal"]').count()==1
            mh.close();mobile.close();record('390px touch viewport: onboarding, scene, workbench and more-menu access')
            assert not errors,errors
            record('No uncaught JavaScript errors during the tested workflows')
            success=True
        except Exception:
            success=False;traceback.print_exc()
            try:shot('browser-failure.png');(ART/'browser-failure.html').write_text(page.content())
            except Exception:pass
        finally:
            report={'run_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'transport':'about:blank + local HTTP bridge' if args.bridge else 'direct browser HTTP','browser':browser.version,'desktop':'1440x1000','mobile':'390x844','seconds':round(time.monotonic()-start,2),'passed':success,'checks':checks,'uncaught_errors':errors,'limitations':['Not Safari/iPhone device testing.','No real LLM endpoint tested.']+(['Bridge test does not validate direct browser network or CSP enforcement.'] if args.bridge else [])}
            (ART/'browser-test-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            h.close();browser.close()
    return 0 if success else 1
if __name__=='__main__':sys.exit(main())
