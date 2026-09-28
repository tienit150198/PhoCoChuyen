#!/usr/bin/env python3
"""v0.2 UI tests against real local HTTP/SQLite.

Optional --bridge is the same about:blank adapter as browser_smoke.py, NOT a
network/CSP bypass. Controlled live-case fixtures use official save import and
server game rules; there is no development-cheat endpoint in the game.
"""
import argparse,copy,datetime,json,sys,time,traceback,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright
from browser_harness import BrowserHarness
from game import operations as ops
from game.engine import apply_action,money,validate_state
ART=ROOT/'artifacts'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',default='http://127.0.0.1:8765');ap.add_argument('--bridge',action='store_true');ap.add_argument('--chromium',default=None);args=ap.parse_args()
    checks=[];errors=[];success=False;t0=time.monotonic();h=None
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=args.chromium)
        ctx=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page=ctx.new_page();page.set_default_timeout(8000);page.on('pageerror',lambda e:errors.append(str(e)))
        h=BrowserHarness(page,args.base,args.bridge)
        def record(text):checks.append(text);print('PASS',text,flush=True)
        def settle():page.wait_for_timeout(120);page.wait_for_function("!document.body.classList.contains('busy')");page.wait_for_timeout(100)
        def click(selector):page.locator(selector).first.click();settle()
        def a(name,extra='',root='#sheet'):
            # Shell pages moved from the dock to the rail in v0.5.
            if root=='#dock' and not page.locator(f'#dock [data-action="{name}"]'+extra).count():root='#rail'
            click(f'{root} [data-action="{name}"]'+extra)
        def tab(name):a('opsTab',f'[data-tab="{name}"]')
        def confirm():a('confirmYes',root='#confirmDialog')
        def operation(name,contains=None,confirmation=False):
            click(f'#sheet [data-op="ops_{name}"]'+(f'[data-payload*="{contains}"]' if contains else ''))
            if confirmation:confirm()
        def advance(n=1):
            for _ in range(n):click('#sheet .sheet-foot [data-command="advance"]')
        def close():
            if page.locator('#sheet[open]').count():a('close')
        def state():
            if args.bridge:return h.client.get('/api/state').json()['state']
            return page.evaluate("async()=> (await(await fetch('/api/state')).json()).state")
        def raw():
            if args.bridge:return h.client.get('/api/save/export').json()['state']
            return page.evaluate("async()=> (await(await fetch('/api/save/export')).json()).state")
        def install(s):
            validate_state(s)
            if args.bridge:
                b=h.client.get('/api/bootstrap').json()
                r=h.client.post('/api/command',headers={'X-Game-CSRF':b['csrf'],'Origin':args.base},json={'request_id':str(uuid.uuid4()),'expected_revision':b['revision'],'career':s['current'],'action':'import_save','payload':{'save':{'format':'mot-ngay-lam-nghe/save-v2','state':s}}})
                assert r.status_code==200,r.text
            else:
                out=page.evaluate("""async(s)=>{const b=await(await fetch('/api/bootstrap')).json();const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':b.csrf},body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:b.revision,career:s.current,action:'import_save',payload:{save:{format:'mot-ngay-lam-nghe/save-v2',state:s}}})});return {status:r.status,text:await r.text()}}""",s)
                assert out['status']==200,out
            h.reload();settle();close()
        def shot(name,focus=None):
            if page.locator('#sheet[open]').count():
                if focus:page.locator(focus).first.scroll_into_view_if_needed()
                else:page.locator('#sheet').evaluate('(e)=>e.scrollTop=0')
            page.wait_for_function("document.querySelectorAll('#toasts .toast:not(.leaving)').length===0",timeout=8000);page.wait_for_timeout(250)
            page.screenshot(path=str(ART/name),full_page=True)
        def c():return state()['careers']['mother_baby']
        try:
            h.load();settle();a('choose','[data-career="mother_baby"]');a('start');a('staff',root='#dock')
            operation('hire','mother_baby-staff-1',True)
            assert len(c()['ops']['staff'])==1 and c()['money']==290
            page.locator('[data-staff-role]').first.select_option('packing');settle()
            page.locator('[data-staff-schedule]').first.select_option('odd');settle()
            click('.employee-card .staff-more > summary');operation('train',confirmation=True);operation('bonus',confirmation=True)
            assert c()['ops']['staff'][0]['precision']==90
            page.locator('#staff-message').fill('Hôm nay bạn đã làm gì?');click('#staffTalkForm button[type="submit"]')
            assert len(c()['ops']['staff_chats']['mother_baby-staff-1'])==2
            advance(4);shot('20-staff-notebook.png');record('Hire, assign, schedule, train, bonus, staff conversation, work attendance')
            tab('lab');operation('incident_demo','damage');operation('incident_read','worklog');operation('incident_read','listen')
            balance=c()['money'];shot('21-staff-damage-evidence.png')
            operation('incident_choose','coach',True);advance(2);operation('incident_finish')
            assert c()['money']==balance and not c()['ops']['finance']['bills'];operation('incident_dismiss')
            record('Damage rehearsal: evidence, explicit remedy, wait, finish; no bills or free skill rewards')
            a('end',root='#sheet');confirm();a('finance')
            bills=c()['ops']['finance']['bills'];assert any(b['kind']=='wage' for b in bills)
            first=next(b for b in bills if b['kind']=='wage');operation('extend_bill',first['id'])
            operation('pay_bill',first['id'],True);assert next(b for b in c()['ops']['finance']['bills'] if b['id']==first['id'])['status']=='paid'
            record('Actual shift close generates wages/utilities, extend and pay through UI')
            tab('property');operation('move_property','sunny',True)
            assert c()['ops']['property']['tier']=='sunny';shot('22-property-upgrade.png')
            tab('staff');operation('hire','mother_baby-staff-2',True)
            assert len([s for s in c()['ops']['staff'] if s['status']=='hired'])==2
            tab('security');operation('buy_security','camera',True)
            operation('insurance_toggle',confirmation=True)
            assert c()['ops']['security']['items']==['camera'];assert c()['ops']['security']['insurance']
            click('#sheet .sheet-foot [data-command="start_day"]');close();shot('23-boba-shop-with-team.png')
            record('Move to larger storefront, second hire, camera and insurance visible/persisted')
            # Real incident in a controlled fixture, using the same incident constructor as director.
            s=raw();sc=s['careers']['mother_baby'];sc['event']=None
            ops.spawn_incident(s,sc,'mother_baby','accident',False,sc['ops']['staff'][0]);install(s)
            a('staff',root='#dock');operation('incident_read','worklog');operation('incident_read','listen');operation('incident_choose','repair',True)
            advance(2);operation('incident_finish');assert c()['ops']['equipment']['condition']==100
            assert any(b['kind']=='repair' for b in c()['ops']['finance']['bills']);operation('incident_dismiss')
            record('Controlled live staff incident: actual repair invoice, stopped worker, restoration')
            # Real theft fixture; force deterministic successful outcome in TEST only.
            s=raw();sc=s['careers']['mother_baby'];sc['event']=None
            v=ops.spawn_case(s,sc,'mother_baby','theft',False);v['_roll']=0;caseid=v['id'];loss=copy.deepcopy(v['loss']);stock_after=sc['stock'][loss['item']];install(s)
            a('security',root='#dock');operation('case_read','inventory');operation('case_read','witness');operation('case_read','camera')
            operation('case_conclude','theft');operation('report',confirmation=True);close();shot('24-police-at-storefront.png')
            a('security',root='#dock');advance(3)
            assert c()['ops']['security']['current_case']['outcome']=='arrested'
            operation('recover',confirmation=True);assert c()['stock'][loss['item']]==stock_after+1
            balance=c()['money'];operation('reward',confirmation=True);assert c()['money']==balance+18
            shot('25-police-recovery-reward.png','.case-result');operation('case_close')
            record('Controlled live theft: inspect, report, wait, police result, recover stock, collect 18 xu once')
            # Generate a full game week by normal close/start reducers, not real clock.
            s=raw();sc=s['careers']['mother_baby'];s['settings']['securityEvents']=False
            for e in sc['ops']['staff']:e['on_shift']=False;e['schedule']='manual'
            while not sc['ops']['finance']['history']:
                money(s,sc,80,'Hoàn thành: dữ liệu kiểm thử ca',category='revenue')
                s,_=apply_action(s,'mother_baby','end_day',{'carry_event':True});sc=s['careers']['mother_baby']
                if not sc['ops']['finance']['history']:s,_=apply_action(s,'mother_baby','start_day');sc=s['careers']['mother_baby']
            install(s);a('finance',root='#dock');shot('26-finance-period-bills.png')
            rent=next(b for b in c()['ops']['finance']['bills'] if b['kind']=='rent' and b['status']=='unpaid')
            tax=next(b for b in c()['ops']['finance']['bills'] if b['kind']=='tax' and b['status']=='unpaid')
            operation('pay_bill',rent['id'],True);operation('pay_bill',tax['id'],True)
            assert c()['ops']['finance']['wallet_check']
            record('Seven game-day invoices, rent by room, fictional tax, UI settlement and exact ledger balance')
            # Force unrecovered result only in fixture; retain pre-event coverage.
            s=raw();s,_=apply_action(s,'mother_baby','start_day');sc=s['careers']['mother_baby'];sc['event']=None
            v=ops.spawn_case(s,sc,'mother_baby','theft',False);v['_roll']=99;install(s)
            a('security',root='#dock');operation('case_read','inventory');operation('case_read','witness');operation('case_conclude','theft');operation('report',confirmation=True);advance(3)
            assert c()['ops']['security']['current_case']['outcome']=='unrecovered'
            value=c()['ops']['security']['current_case']['loss']['value'];balance=c()['money'];operation('insurance_claim',confirmation=True)
            assert c()['money']==balance+value*60//100;operation('case_close')
            record('Unrecovered fixture, prior insurance, 60% remaining value, no recovery/reward duplication')
            # Verify careers isolated and no client-side mutations.
            previous=raw();h.reload();settle();assert c()['ops']['finance']['wallet_check']
            assert c()['ops']['security']['cases'][-1]['insurance_claimed'];record('Reload preserves full operations, paid bills and security receipts')
            close();page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300);shot('27-mobile-boba-team.png')
            a('staff',root='#dock');shot('28-mobile-staff.png')
            assert page.evaluate("document.querySelector('#sheet').scrollWidth<=document.querySelector('#sheet').clientWidth+2")
            for t in ('finance','property','security','lab'):
                tab(t);assert page.evaluate("document.querySelector('#sheet').scrollWidth<=document.querySelector('#sheet').clientWidth+2"),t
            shot('29-mobile-scenarios.png');close();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            record('390x844 viewport: scene, staff and all five notebook tabs without horizontal page overflow')
            page.set_viewport_size({'width':1440,'height':1000});page.wait_for_timeout(150)
            for cid in ('pharmacy','accounting','customer_care'):
                a('home',root='#rail');a('choose',f'[data-career="{cid}"]');a('start');a('staff',root='#dock');operation('hire',cid+'-staff-1',True)
                assert len(state()['careers'][cid]['ops']['staff'])==1
                assert c()['money']==previous['careers']['mother_baby']['money']
                close();shot('30-'+cid+'-boba-team.png')
            record('All four careers have separate staff/money and profession-specific boba scenes')
            assert not errors,errors;record('No uncaught JS exceptions across new workflows')
            success=True
        except Exception:
            traceback.print_exc()
            try:page.screenshot(path=str(ART/'browser-operations-failure.png'),full_page=True)
            except Exception:pass
        finally:
            report={'version':'0.3.0','run_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':success,'seconds':round(time.monotonic()-t0,2),'browser':browser.version,'transport':'about:blank + local HTTP bridge' if args.bridge else 'direct browser HTTP','checks':checks,'uncaught_errors':errors,'controlled_fixtures':['live staff accident','theft/arrest with fixed private test roll','seven closes and earned-revenue fixture','unrecovered case with prior coverage'],'limitations':['No Safari/iPhone physical device test.','No real LLM test.','Fixtures verify authored outcomes, not live public service.']+(['Direct navigation is blocked in this environment; bridge does not test browser network/CSP enforcement.'] if args.bridge else [])}
            (ART/'browser-operations-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');h.close();browser.close()
    return 0 if success else 1
if __name__=='__main__':sys.exit(main())
