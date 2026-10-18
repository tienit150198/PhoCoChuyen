"""📱 Mobile layout sweep (dev tool, needs playwright + chromium): every reachable screen at phone sizes.

Owner 15/10: "nhiều cái UI bị đè nhau ở màn mobile … quét hết rồi xử lý … check cẩn thận từng màn". Runs the real app
on a throwaway story-mode server (PostgreSQL scratch DB from TEST_DATABASE_URL), seeds one save (a named player on
life day 6, 50.000 xu, the tour and the announcements done), then for each viewport:

  * crawls the menus to list the screens: the 2.5D HUD, "Tiện ích" and each of its groups, "Thêm" and each rail
    group (and the classic interface's bars, with --classic);
  * opens every screen from a fresh load, scrolls its sheet page by page, takes a screenshot of each page and runs
    scripts/mobile_layout_detect.js (overlaps, covered controls, clipped text, sideways scroll, small targets);
  * with --careers, the work screen of every career (and with --deep the screen after its first main button).

Screens the dog-bark game and the pagoda visit lead to are skipped (other branches rebuild them).

    TEST_DATABASE_URL=postgresql://… python scripts/browser_mobile_sweep.py [--classic] [--careers] [--deep]
        [--vp 360x740,390x844,844x390] [--only REGEX] [--out DIR]

Writes DIR/<screen>__<viewport>[-pN].png and DIR/report.json; prints one line per screen with its issue count.
"""
import argparse
import asyncio
import contextlib
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from pg_test_support import test_env  # noqa: E402

VIEWPORTS = {'360x740': (360, 740, True), '375x667': (375, 667, True), '390x844': (390, 844, True),
             '412x915': (412, 915, True), '844x390': (844, 390, True), '1366x768': (1366, 768, False)}
SKIP = re.compile(r'chó|Công đức|chùa|Chùa|spendChua|liveBark')
GUIDES_SEEN = 'gd-' + 'v' * 10 + 'f'   # tutorial/store.js GUIDE_BITS: every workplace's guide card answered
CAREERS = ['mother_baby', 'pharmacy', 'accounting', 'customer_care', 'teacher', 'tour_guide', 'milk_tea', 'restaurant',
           'cafe_bakery', 'florist', 'grocery', 'repair', 'farm', 'delivery', 'homestay', 'pet_care', 'salon',
           'corp_accounting', 'tax_payroll', 'group_accounting', 'clothing', 'pet_shop', 'tra_da', 'fruit', 'garbage',
           'drain', 'pilot', 'flight_attendant', 'homemaker', 'hr_admin', 'secretary', 'it_helpdesk', 'ice_cream',
           'nail', 'pagoda', 'pho', 'com', 'photobooth', 'giupviec', 'naucom', 'babysitter', 'library', 'oil',
           'railway', 'nurse', 'lighthouse', 'rescue', 'lifeguard', 'police', 'zpop', 'art_studio', 'lawyer',
           'laundry', 'post_office']


def detector():
    text = (ROOT / 'scripts' / 'mobile_layout_detect.js').read_text()
    return text[text.index('(opts) =>'):]


@contextlib.contextmanager
def server():
    from browser_v04 import free_port
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-mobile-')
    env = test_env(QUIET='1', PUSH_DISABLED='1', STATIC_RECHECK_SECONDS='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.db')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--namespace', db], cwd=ROOT, env=env,
                         stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:
            if p.poll() is not None:
                break
            time.sleep(0.1)
    try:
        yield base, db
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)
        log.close()


def state_for(career, classic):
    from tests.helpers import Journey
    from game import journey
    s = Journey(career, day=6, slot=1).state
    journey.enable_story(s, 4242)
    s['name'] = 'Lan Thử'
    s['journey'].update(intro=True, gender='female', news=[], life_day=6, wallet=50000)
    s['journey']['interface'] = dict(newInterface=not classic, interfacePromptSeen=True)
    s['settings'].update(tutorialDone=True, whatsNewSeen='9.9.9', notesSeen='onb1,' + GUIDES_SEEN)
    return s


def seed(db, token, state):
    from game import marriage
    from game.storage import Store
    store = Store(db, story=True)
    try:
        marriage._mutate(store, {store.key(token): lambda old: (old.clear(), old.update(copy.deepcopy(state)))})
    finally:
        store.close_pool()


X3 = ("async()=>{const j=await (await fetch('/api/state')).json();const s=j.state||j;const w=s.x3&&s.x3.week;"
      "if(w)localStorage.setItem('mnl.x3.week',w)}")
ENUM = r"""(rootSel)=>{
  const root=document.querySelector(rootSel); if(!root) return [];
  const out=[], seen={};
  for(const el of root.querySelectorAll('[data-action],[data-command],summary')){
    if(!el.checkVisibility()) continue;
    let sel;
    if(el.tagName==='SUMMARY'&&!el.dataset.action){const d=el.parentElement;
      sel=d.dataset.isoGroup?`details[data-iso-group="${d.dataset.isoGroup}"]>summary`:d.className?'details.'+[...d.classList].join('.')+'>summary':null;
      if(!sel) continue;}
    else{sel='';for(const a of el.attributes){if(a.name.startsWith('data-')&&!['data-menu-stay','data-preserve','data-iso-focus'].includes(a.name)&&a.value.length<60&&!/^\{/.test(a.value))sel+=`[${a.name}="${a.value.replace(/"/g,'\\"')}"]`;}if(!sel) continue;}
    const full=rootSel+' '+sel; seen[full]=(seen[full]||0)+1;
    out.push({sel:full,nth:seen[full]-1,label:((el.innerText||'').trim()||el.getAttribute('aria-label')||el.dataset.action||'').replace(/\s+/g,' ').slice(0,40)});
  }
  return out;}"""
SCROLLER = r"""()=>{
  const top=[...document.querySelectorAll('dialog[open]')].pop(), root=top||document.querySelector('#app');
  const c=[root,...root.querySelectorAll('*')].filter(e=>{if(!e.checkVisibility())return false;const s=getComputedStyle(e);return (s.overflowY==='auto'||s.overflowY==='scroll')&&e.scrollHeight>e.clientHeight+30&&e.clientHeight>120;});
  c.sort((a,b)=>b.clientHeight*b.clientWidth-a.clientHeight*a.clientWidth);
  document.querySelectorAll('[data-mob-scroll]').forEach(e=>e.removeAttribute('data-mob-scroll'));
  if(!c[0])return null;c[0].setAttribute('data-mob-scroll','1');return {h:c[0].clientHeight,sh:c[0].scrollHeight};}"""
OPEN_WORK = [['js', "(()=>{const s=document.querySelector('.iso-go[data-action=isoMission]');if(s&&s.checkVisibility()){s.click();return}"
                    "const b=[...document.querySelectorAll('[data-action=job],[data-action=workbench]')].find(e=>e.checkVisibility());if(b)b.click()})()"],
             ['js', "(()=>{})()"]]
MAIN_BUTTON = ['js', "(()=>{const b=[...document.querySelectorAll('#sheet .gd-cta, #sheet [class*=-bar] .btn.primary, #sheet .btn.primary')]"
                     ".find(e=>e.checkVisibility()&&!e.disabled);if(b)b.click()})()"]


async def settle(page, ms=700):
    with contextlib.suppress(Exception):
        await page.wait_for_function("!document.body.classList.contains('busy')", timeout=8000)
    await page.wait_for_timeout(ms)


async def fresh(page):
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=45000)
    await settle(page, 1500)
    for _ in range(2):   # automatic cards (x3 week, gifts) close; the sheet stays
        await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>{if(d.id!=='sheet')d.close()})")
        await page.wait_for_timeout(300)


async def run_steps(page, steps):
    for s in steps:
        if s[0] == 'click':
            ok = await page.evaluate("([s,n])=>{const e=document.querySelectorAll(s)[n];if(!e)return false;e.click();return true}", [s[1], s[2]])
            if not ok:
                return f'missing {s[1]}'
            await settle(page, 800)
            if s[1].endswith('>summary'):   # a re-render may have closed the disclosure again
                await page.evaluate("([s,n])=>{const e=document.querySelectorAll(s)[n];if(e&&!e.parentElement.open)e.click()}", [s[1], s[2]])
                await settle(page, 500)
        elif s[0] == 'js':
            await page.evaluate(s[1])
            await settle(page, 800)
    return None


async def new_page(browser, vp):
    w, h, mobile = VIEWPORTS[vp]
    ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=mobile, has_touch=mobile,
                                    device_scale_factor=2 if mobile else 1)
    page = await ctx.new_page()
    page.errors = []
    page.on('pageerror', lambda e: page.errors.append(str(e)))
    return ctx, page


async def login(browser, base, db, vp, career, classic):
    ctx, page = await new_page(browser, vp)
    await page.goto(base)
    await page.wait_for_selector('#app:not([hidden])', timeout=45000)
    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
    seed(db, token, state_for(career, classic))
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=45000)
    await page.evaluate(X3)
    return ctx, page, token


async def discover(browser, base, db, classic):
    """The menu screens, as click paths from a fresh load (390x844)."""
    ctx, page, _ = await login(browser, base, db, '390x844', 'milk_tea', classic)
    screens = [dict(id='home', steps=[])]
    await fresh(page)
    for root in (['#isoHUD'] if not classic else ['#topbar', '#stage', '#side']):
        for it in await page.evaluate(ENUM, root):
            screens.append(dict(id='hud:' + it['label'][:24], steps=[['click', it['sel'], it['nth']]]))
    if not classic:
        tools = [['click', 'details.iso-tools>summary', 0]]
        await fresh(page)
        await run_steps(page, tools)
        for it in await page.evaluate(ENUM, '#isoToolsOptions'):
            if not it['sel'].endswith('>summary'):
                screens.append(dict(id='tools:' + it['label'][:24], steps=tools + [['click', it['sel'], it['nth']]]))
                continue
            group = tools + [['click', it['sel'], it['nth']]]
            await fresh(page)
            await run_steps(page, group)
            gid = re.search(r'data-iso-group="([^"]+)"', it['sel'])
            root = f'#isoUtility-{gid.group(1)}' if gid else 'details.iso-outings:not([data-iso-group])[open] .iso-outings-menu'
            for sub in await page.evaluate(ENUM, root):
                screens.append(dict(id=f'tools:{it["label"][:14]}>{sub["label"][:24]}', steps=group + [['click', sub['sel'], sub['nth']]]))
    rail = [] if classic else [['click', '[data-action="isoMore"]', 0]]
    await fresh(page)
    await run_steps(page, rail)
    for it in await page.evaluate(ENUM, '#rail'):
        if 'v4Group' not in it['sel']:
            screens.append(dict(id='rail:' + it['label'][:24], steps=rail + [['click', it['sel'], it['nth']]]))
            continue
        if 'data-group=""' in it['sel']:
            continue
        group = rail + [['click', it['sel'], it['nth']]]
        screens.append(dict(id='railgrp:' + it['label'][:24], steps=group))
        await fresh(page)
        await run_steps(page, group)
        gid = it['sel'].split('data-group="')[1].split('"')[0]
        for sub in await page.evaluate(ENUM, f'#rail .rail-sub[data-group="{gid}"]'):
            if 'v4Group' not in sub['sel']:
                screens.append(dict(id=f'rail:{it["label"][:12]}>{sub["label"][:24]}', steps=group + [['click', sub['sel'], sub['nth']]]))
    await ctx.close()
    seen, out = {}, []
    for s in screens:
        if SKIP.search(s['id']):
            continue
        seen[s['id']] = seen.get(s['id'], 0) + 1
        if seen[s['id']] > 1:
            s['id'] += f'#{seen[s["id"]]}'
        out.append(s)
    return out


def safe(name):
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', name)[:60]


async def sweep_vp(browser, base, db, vp, screens, classic, out, results):
    ctx, page, token = await login(browser, base, db, vp, 'milk_tea', classic)
    current, detect = 'milk_tea', detector()
    for sc in screens:
        rec = dict(id=sc['id'], vp=vp, pages=[])
        try:
            want = sc.get('career', 'milk_tea')
            if want != current:
                seed(db, token, state_for(want, classic))
                current = want
            await fresh(page)
            err = await run_steps(page, sc['steps'])
            if err:
                rec['error'] = err
            await settle(page, sc.get('settle', 1200))
            info = await page.evaluate(SCROLLER)
            pages = 1 if not info else min(5, 1 + int((info['sh'] - info['h']) / (info['h'] * 0.85) + 0.99))
            for k in range(pages):
                if k:
                    await page.evaluate("(k)=>{const s=document.querySelector('[data-mob-scroll]');if(s)s.scrollTop=s.clientHeight*0.85*k}", k)
                    await page.wait_for_timeout(350)
                found = await page.evaluate(detect, {})
                shot = out / f'{safe(sc["id"])}__{vp}{"-p" + str(k) if k else ""}.png'
                await page.screenshot(path=str(shot))
                rec['pages'].append(dict(shot=str(shot.relative_to(out)), root=found['root'], issues=found['issues']))
        except Exception as e:   # one broken screen never stops the sweep
            rec['error'] = repr(e)[:300]
        rec['errors'] = page.errors[:]
        page.errors.clear()
        results.append(rec)
        n = sum(1 for pg in rec['pages'] for i in pg['issues'] if i['t'] != 'small-tap')
        print(f'{vp:9} {sc["id"][:48]:48} {n:3} {rec.get("error", "")}', flush=True)
    await ctx.close()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--classic', action='store_true', help='the classic interface instead of the 2.5D town')
    ap.add_argument('--careers', action='store_true', help='the work screen of every career instead of the menus')
    ap.add_argument('--deep', action='store_true', help='with --careers: also the screen after the first main button')
    ap.add_argument('--vp', default='360x740,375x667,390x844,412x915,844x390')
    ap.add_argument('--only', default='', help='regex on screen ids')
    ap.add_argument('--out', default=str(ROOT / 'output' / 'playwright' / 'mobile-sweep'))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright
    results = []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            if args.careers:
                screens = [dict(id='job:' + c, career=c, steps=OPEN_WORK, settle=2500) for c in CAREERS]
                if args.deep:
                    screens += [dict(id='job2:' + c, career=c, steps=OPEN_WORK + [MAIN_BUTTON], settle=2500) for c in CAREERS]
            else:
                screens = await discover(browser, base, db, args.classic)
            if args.only:
                screens = [s for s in screens if re.search(args.only, s['id'])]
            await asyncio.gather(*[sweep_vp(browser, base, db, vp, screens, args.classic, out, results) for vp in args.vp.split(',')])
            await browser.close()
    (out / 'report.json').write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf8')
    bad = [r for r in results if any(i['t'] in ('covered', 'text-overlap', 'offscreen-x', 'hscroll-page') for pg in r['pages'] for i in pg['issues'])]
    print(f'{len(results)} screen×viewport runs, {len(bad)} with an overlap/off-screen finding; report: {out / "report.json"}')


if __name__ == '__main__':
    asyncio.run(main())
