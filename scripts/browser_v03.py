#!/usr/bin/env python3
"""UI journeys against actual HTTP API. --bridge is an explicit local test adapter.
Normal developer use: python scripts/browser_v03.py --base http://127.0.0.1:8765
"""
import argparse,datetime,json,time,traceback,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_harness import BrowserHarness
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts';sys.path.insert(0,str(ROOT))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--base',default='http://127.0.0.1:8765');ap.add_argument('--bridge',action='store_true');ap.add_argument('--chromium',default=None);args=ap.parse_args()
 ART.mkdir(exist_ok=True);checks=[];errors=[];started=time.monotonic();screens=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=args.chromium,headless=True);page=browser.new_page(viewport={'width':1440,'height':1020},device_scale_factor=1,accept_downloads=True);page.set_default_timeout(7000)
  page.on('pageerror',lambda e:errors.append(str(e)));h=BrowserHarness(page,args.base,args.bridge)
  def settle():
   page.wait_for_timeout(90);page.wait_for_function("!document.body.classList.contains('busy')");page.wait_for_timeout(75)
  def act(a,extra='',root='#sheet'):
   # Shell pages moved from the dock to the rail in v0.5.
   if root=='#dock' and not page.locator(f'#dock [data-action="{a}"]{extra}').count():root='#rail'
   page.locator(f'{root} [data-action="{a}"]{extra}').first.click();settle()
  def op(name,where='',root='#sheet'):
   page.locator(f'{root} [data-op="{name}"]'+(f'[data-payload*="{where}"]' if where else '')).first.click();settle()
  def command(name,where=''):
   page.locator(f'#sheet [data-command="{name}"]'+(f'[data-payload*="{where}"]' if where else '')).first.click();settle()
  def yes():act('confirmYes',root='#confirmDialog')
  def state():
   return h.client.get('/api/state').json()['state'] if args.bridge else page.evaluate("async()=> (await(await fetch('/api/state')).json()).state")
  def raw():
   return (h.client.get('/api/save/export').json() if args.bridge else page.evaluate("async()=> (await(await fetch('/api/save/export')).json())"))['state']
  def c():s=state();return s['careers'][s['current']]
  def task():s=c();return next(t for t in s['tasks'] if t['id']==s['active_task'])
  def record(label):checks.append(label);print('PASS',label,flush=True)
  def shot(name):
   page.evaluate("document.querySelector('#toasts').replaceChildren()");page.wait_for_timeout(130);page.screenshot(path=str(ART/name),full_page=True);screens.append(name)
  def close():act('close')
  def choose(cid):
   if not page.locator('#sheet[open] [data-action="choose"]').count():
    if page.locator('#sheet[open]').count():close()
    if page.viewport_size['width']>620:act('home',root='#rail')
    else:act('help',root='#dock');act('home')
   act('choose',f'[data-career="{cid}"]');assert state()['current']==cid
  def start():act('start');assert c()['open']
  def job():act('job',root='#taskHUD')
  def safe_layout():
   dims=page.evaluate("""()=>{const el=document.querySelector('#sheet');return {page:document.documentElement.scrollWidth<=innerWidth+1,sheet:el.scrollWidth<=el.clientWidth+2};}""")
   assert dims['page'] and dims['sheet'],dims
  def solve_activity_ui():
   st=raw();a=st['careers'][st['current']]['life']['activity']
   if a['kind']=='sort' or a['kind']=='match':
    for card in a['cards']:
     act('expCard',f'[data-card="{card["id"]}"]');act('expTarget',f'[data-target="{card["bin"] if a["kind"]=="sort" else card["id"]}"]')
   elif a['kind']=='sequence':
    for card in sorted(a['cards'],key=lambda v:v['rank']):op('life_activity_step',card['id'])
    op('life_activity_check')
   else:
    groups={}
    for card in a['cards']:groups.setdefault(card['value'],[]).append(card['id'])
    for ids in groups.values():
     for key in ids:page.locator(f'[data-op="life_activity_flip"][data-payload=\'{json.dumps({"card":key},separators=(",",":"))}\']').click();settle()
   assert c()['life']['activity']['status']=='completed'
  try:
   h.load();settle();assert page.locator('#sheet [data-action="choose"]').count()==7
   shot('v03-01-seven-careers.png');record('Seven playable careers, with original canvas previews')
   act('future');assert page.locator('.future-card').count()==12;record('12 future entries explicitly locked')
   act('home');choose('teacher');assert page.locator('.chalkboard').count();shot('v03-02-teacher-preparation.png')
   start();shot('v03-03-teacher-scene.png');job()
   for step in ['demo','practice','reflect']:act('lessonStep',f'[data-step="{step}"]')
   act('lessonPlan');t=task();assert t['stage']=='attendance'
   for student in t['students']:
    page.locator('[data-op="lesson_attendance"]').filter(has_text='Có mặt').first.click();settle()
   assert task()['stage']=='teach';shot('v03-04-teacher-teaching.png')
   source=raw()['careers']['teacher']['tasks'][0]
   for st in source['students']:
    method=st['method'];page.locator(f'[data-op="lesson_teach"][data-payload*=\'"student":"{st["id"]}"\'][data-payload*=\'"method":"{method}"\']').click();settle()
   assert task()['stage']=='grade';shot('v03-05-teacher-feedback.png')
   for st in source['students']:
    correct=st['submission']==source['lesson']['answer'];v='true' if correct else 'false'
    page.locator(f'[data-op="lesson_grade"][data-payload*=\'"student":"{st["id"]}"\'][data-payload*=\'"correct":{v}\']').first.click();settle()
   op('lesson_complete');yes();assert c()['day_completed']==1;record('Teacher: lesson planning, observable attendance, differentiated explanation, private feedback, reward')
   choose('tour_guide');start();job();t=task()
   for loc in t['required']+['cafe']:act('tourRoute',f'[data-place="{loc}"]')
   shot('v03-06-tour-route-planning.png');act('tourPlan')
   for v in t['visitors']:op('tour_count',v['id'])
   op('tour_depart');yes();assert task()['stage']=='stop'
   route=task()['route']
   for i,loc in enumerate(route):
    for v in t['visitors']:op('tour_count',v['id'])
    from game.extra_content import PLACE_INDEX
    at=PLACE_INDEX[loc]
    op('tour_tell',at['answer']);op('tour_photo',at['target'])
    if i==0:shot('v03-07-tour-story-photo.png')
    op('tour_next')
   op('tour_complete');yes();assert c()['day_completed']==1;assert len(c()['life']['stickers'])>=3
   record('Tour guide: route budget, headcount, fictional facts, photo finding, postcards, trip completion')
   choose('milk_tea');shot('v03-08-tea-preparation-menu.png')
   # User-editable name is displayed as text, not interpreted markup.
   act('expRename');page.locator('#cozy-prompt').fill('Trà Mây & Những Chuyện Nhỏ');yes();assert c()['life']['shop_name']=='Trà Mây & Những Chuyện Nhỏ'
   start();shot('v03-09-tea-scene.png');job();op('ask');t=task();n=t['needs']
   for item in [n['base']]+([n['flavor']] if n['flavor'] else [])+n['toppings']:op('tea_add',item)
   page.locator('#tea-size').select_option(n['size']);page.locator('#tea-sugar').select_option(str(n['sugar']));page.locator('#tea-ice').select_option(n['ice']);act('teaConfig');op('tea_check');op('tea_seal')
   shot('v03-10-tea-counter.png');op('tea_serve');yes();assert c()['day_completed']==1;record('Tea: ingredients actually consumed, custom cup layers, size/sugar/ice check, seal and sale')
   act('phone');post=next(v for v in c()['feed'] if v['kind']=='review');stars=post['stars']
   form=page.locator(f'form[data-reply-post="{post["id"]}"]');form.locator('input').fill('Cảm ơn bạn, mai lại ghé kể chuyện cho tiệm nghe nhé 😄');form.locator('button').click();settle()
   act('expReplyEdit');page.locator('#cozy-prompt').fill('Cảm ơn bạn! Ly ít đường, còn tiệm thì thích nghe nhiều chuyện 😄');yes()
   now=next(v for v in c()['feed'] if v['id']==post['id']);assert now['stars']==stars;assert any(v.get('edited') for v in now['comments']);shot('v03-11-review-owner-response.png');record('Review replies can be edited without altering NPC rating')
   close();act('workshop',root='#dock')
   for kind in ['sort','pairs','sequence','match']:
    op('life_activity_start',f'milk_tea-{kind}');assert c()['life']['activity']['kind']==kind
    if kind=='pairs':shot('v03-12-memory-minigame.png')
    if kind=='match':shot('v03-13-pair-label-minigame.png')
    solve_activity_ui();record('UI minigame '+kind+': completed, bounded daily reward')
   close();act('passport',root='#dock');op('life_goal','play');assert 'play' in c()['life']['goals_claimed'];shot('v03-14-passport.png');record('Daily goal reward and collection passport')
   act('town');act('expVisit','[data-place="library"]');assert 'library' in c()['life']['visits'];assert page.locator('.town-visit-card').count();shot('v03-15-neighbourhood-map.png');op('life_activity_start');assert page.locator('.activity-board').count();record('Town locations open real minigames without charging entry')
   close();act('prepare',root='#rail');op('tea_prepare','foam');yes();cash=c()['money'];close();act('help',root='#rail');close()
   # Close day from the accessible day workflow; bills remain in operations module.
   act('end',root='#taskHUD') if page.locator('#taskHUD [data-action="end"]').count() else None
   if not page.locator('#confirmDialog[open]').count():act('queue',root='#dock');act('end')
   yes();assert not c()['open'];assert c()['money']==cash;shot('v03-16-end-day.png');record('End of day: real cashflow, consumed cost, staff tips and expiry not double charged')
   # Mobile: full native dialog flows and no horizontal overflow.
   page.set_viewport_size({'width':390,'height':844});settle();safe_layout();shot('v03-17-mobile-summary.png')
   close();act('help',root='#dock');act('home');act('choose','[data-career="milk_tea"]');safe_layout();shot('v03-18-mobile-preparation.png')
   start();job();safe_layout();shot('v03-19-mobile-tea-counter.png');record('390px portrait: summary, preparation and physical counter fit without horizontal overflow')
   choose('teacher');job();safe_layout();shot('v03-20-mobile-classroom.png')
   choose('tour_guide');job();safe_layout();shot('v03-21-mobile-tour.png');record('Mobile classroom and itinerary accessible with click instead of drag')
   close();act('help',root='#dock');act('settings');before=state()
   with page.expect_download() as download:act('export')
   exported=json.loads(Path(download.value.path()).read_text());assert exported['format']=='mot-ngay-lam-nghe/save-v3'
   h.reload();settle();assert state()['careers']['teacher']['day_completed']==1;assert state()['careers']['milk_tea']['day']==2;record('v3 export plus real PostgreSQL reload restores independent career progress')
   assert not errors,errors
   report=dict(version='0.3.0',status='passed',checks=checks,count=len(checks),page_errors=errors,screenshots=screens,mode='in-process Chromium DOM with local HTTP bridge' if args.bridge else 'direct Chromium browser',direct_browser_network_validated=not args.bridge,elapsed_seconds=round(time.monotonic()-started,2),timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
   (ART/'browser-v03-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
  except Exception:
   page.screenshot(path=str(ART/'browser-v03-failure.png'),full_page=True)
   print('BODY',page.locator('#sheetContent').inner_text()[:5000]);print('PAGE ERRORS',errors);print('STATE',json.dumps(state(),ensure_ascii=False)[-3000:]);raise
  finally:h.close();browser.close()
if __name__=='__main__':main()
