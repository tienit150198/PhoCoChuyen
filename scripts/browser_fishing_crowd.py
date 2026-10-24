#!/usr/bin/env python3
"""🎣 2.6.5.2 hotfix of the shared lake in real browsers (dev tool; needs playwright + chromium, PostgreSQL through
TEST_DATABASE_URL; the game server and the live service as in scripts/browser_fishing_shared.py).

Lan wears a 🪽 Huyền thoại dragon pair, carries a 300 kg fish and holds a Cần Long Vương. She opens 🎣 Câu cá at Hồ phố
on a 390×844 phone and on a 1280×800 desktop; the live room is then replaced (frames injected into the page's live
socket) by a crowd of 80 fishers with looks, wings, carried fish and every rod:
  1. 🪽 her wings and the others' are whole (owner 25/10 "bị mất cái cánh"): no sprite narrower than its wings;
  2. ↔️ a drag on the lake pans along the boardwalk (no cast), a fling glides on; the bar under the boardwalk shows
     where the view is and its thumb drags to the far end; 📍 Về chỗ tôi comes back; the mouse wheel pans (desktop);
     a tap on a fisher still opens their card (with their rod drawn); a hold on the lake still fills the power meter;
  3. 🐋 catches next to their fishers: a 300 kg one lies on the boardwalk beside them, bigger than they are;
  4. 🎣 each rod drawn its own way in the hands;
  5. ⌨️ #515: a text field behind the lake (a work screen's form) cannot take the focus while the lake is open, and a
     press blurs any focused one.
Screenshots (PNG) go to OUT (argv[1]); exit 1 on a failed check or a page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_fishing_crowd.py [out_dir]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_bang_island import servers, py  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'fishing-crowd-shots'
ACT = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d||{});b.hidden=true;document.body.append(b);b.click();b.remove();})"
VIEW = "(async()=>(await import('/js/v4/fishing.js')).lakeView())()"
WS = """(()=>{const W=window.WebSocket;const socks=[];window.__socks=socks;
  const X=function(...a){const s=new W(...a);socks.push(s);return s;};X.prototype=W.prototype;Object.assign(X,{CONNECTING:0,OPEN:1,CLOSING:2,CLOSED:3});
  window.WebSocket=X;window.__inject=f=>{let n=0;for(const s of socks)if(s.readyState===1&&s.onmessage){s.onmessage({data:JSON.stringify(f)});n++;}return n;};})()"""
fails: list = []
errors: list = []


def check(ok, what, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (f' ({detail})' if detail else ''), flush=True)
    if not ok:
        fails.append(what)


SEED = r'''
import sys, hashlib, time
from game import accounts, whats_new as wn, fishing as F, wings as WG
from game import fishing_content as C
from game import marriage as mr
from game.storage import Store
db, token, name = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
out = accounts.register(store, token, dict(username='u' + hashlib.md5(name.encode()).hexdigest()[:12], password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
sp = next(x for x in C.SPECIES.values() if x['r'] >= 4 and x['w'][0] <= 300 <= x['w'][1])
def fn(s):
    j = s['journey']
    s['name'] = name
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    j.update(gender='female', intro=True, life_day=20, wallet=2_000_000)
    d = F.ensure(s)
    d['rods'] = list(C.ROD_IDS); d['rod'] = 'long_vuong'
    d['seq'] = 1; d['bag'].append(dict(i=1, s=sp['id'], g=300_000, d=F.vn_day(time.time()), p=0, k=0, o=0, od=0)); d['carry'] = 1
    j['wings'] = dict(v=WG.VERSION, own=[dict(id='w1', k='rong', r=7, z=int(time.time()))], on='w1', seq=2, day=dict(d=0, got=0), rq={})
mr._mutate(store, {sid: fn})
store.close_pool()
print(tok)
'''

SPECIES = r'''
import json
from game import fishing
print(json.dumps(fishing.catalogue()['species']))
'''

CROWD = """([species,me])=>{
  const pick=(a,i)=>a[i%a.length],big=species.filter(s=>s.r>=3);
  const fhOf=(sp,kg)=>({sp:sp.id,r:sp.r,kg,fam:sp.fam,body:sp.body,belly:sp.belly,fin:sp.fin,pat:sp.pat});
  const rods=['tre','truc','carbon','bien','vang','bach_kim','long_vuong'],wings=['buom','tien','doi','thien_than','rong','phuong'];
  const hair=['toc_ngan','toc_dai','toc_xoan','toc_bui'],tops=['ao_thun','ao_so_mi','ao_khoac'];
  const people=[];
  for(let s=1;s<=80;s++){const sp=pick(big,s*7),kg=[2,20,80,150,300,900][s%6];
    people.push({pid:'p'+s,name:'Ngư '+s,s,lk:{hair:pick(hair,s),top:pick(tops,s)},g:s%2?'male':'female',rod:pick(rods,s),
      ...(s%3===0?{wg:{k:pick(wings,s),r:s%8}}:{}),...(s%4===1?{fh:fhOf(sp,Math.max(sp.w[0],Math.min(sp.w[1],kg)))}:{}),
      ...(s%5===0?{a:{k:'cast',d:30+s,x:0}}:{})});}
  return window.__inject({t:'fl_room',spot:'ho',room:'crowd',me,s:0,n:81,people,far:[],feed:[]});
}"""

CATCH = """([species])=>{
  const huge=species.find(s=>s.w[0]<=300&&s.w[1]>=300&&s.r>=4),small=species.find(s=>s.r>=3&&s.w[1]<=5);
  return window.__inject({t:'fl',room:'crowd',ev:[{k:'catch',pid:'p1',s:huge.id,g:300000,r:huge.r,feed:{name:'Ngư 1',s:huge.id,g:300000,r:huge.r,pid:'p1'}},
    {k:'catch',pid:'p2',s:small.id,g:Math.round(small.w[1]*800),r:small.r}]});
}"""

SPRITES = """(async()=>{const L=await import('/js/v4/look.js');
  const out=[];for(const k of L.WING_STYLES){const [l,t,r]=L.figBounds(L.figureOf({wg:{k,r:7}},'female'));out.push(-l>=122&&r>=122&&-t>=155);}
  return out.every(Boolean);})()"""


ENGINE = os.environ.get('MNL_ENGINE', 'chromium')
PHASE = "(async()=>(await import('/js/v4/fishing.js')).lakeView().phase)()"
TEN = """(()=>{const d=document.querySelector('dialog.fs-sheet[open]');const t=d&&d.querySelector('.fs-ten');if(!t||t.hidden)return null;
  const g=t.querySelector('.fs-ten-bar b'),i=t.querySelector('.fs-ten-bar i'),p=t.querySelector('.fs-prog i');
  return {g0:parseFloat(g.style.left),gw:parseFloat(g.style.width),tau:parseFloat(i.style.left),prog:parseFloat(p.style.width),red:t.classList.contains('red'),
    active:document.activeElement?.matches?.('input,textarea')||false};})()"""


async def reel_ancient(page, ctx, shot):
    """3. the reel on a phone with touches: a 🔴 Cổ đại fight (Long Vương's own numbers from fight_of, put into the hook's
    answer) played by a player who hardly looks (holds 3,5 s, lets go 2 s): landed; no field ever focused."""
    cdp = await ctx.new_cdp_session(page)
    go = await page.evaluate("(()=>{const r=document.querySelector('dialog.fs-sheet[open] .fs-go').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];})()")

    async def touch(kind):
        await cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [] if kind == 'touchEnd' else [{'x': go[0], 'y': go[1]}]})

    hooked = {'n': 0}

    async def route(r):
        req = r.request
        if req.method == 'POST' and '"jr_fish_hook"' in (req.post_data or ''):
            resp = await r.fetch()
            data = await resp.json()
            h = (data.get('result') or {}).get('hook')
            if isinstance(h, dict) and 'secs' in h:
                h.update(pull=0.78, dart=0.64, green=0.3, secs=10.8, heavy=False, snap_at=None)
                hooked['n'] += 1
            await r.fulfill(response=resp, json=data)
            return
        await r.continue_()

    await page.route('**/api/command', route)
    await page.evaluate("document.querySelector('dialog.fs-sheet[open] [data-fs=home]')?.click()")
    landed, samples = False, []
    for attempt in range(10):
        for _ in range(60):
            if await page.evaluate(PHASE) in ('idle', 'card'):
                break
            await page.wait_for_timeout(250)
        await page.evaluate("document.querySelector('dialog.fs-sheet[open] [data-fs=again]')?.click()")
        await touch('touchStart')
        await page.wait_for_timeout(80)
        await touch('touchEnd')
        ph = ''
        for _ in range(140):
            ph = await page.evaluate(PHASE)
            if ph in ('bite', 'lost', 'idle'):
                break
            await page.wait_for_timeout(200)
        if ph != 'bite':
            continue
        await touch('touchStart')
        await page.wait_for_timeout(60)
        await touch('touchEnd')
        for _ in range(30):
            ph = await page.evaluate(PHASE)
            if ph != 'hooking':
                break
            await page.wait_for_timeout(100)
        if ph != 'fight':
            continue
        t, shotted = 0.0, False
        while t < 70:
            await touch('touchStart')
            for _ in range(7):
                st = await page.evaluate(TEN)
                if st:
                    samples.append(st)
                await page.wait_for_timeout(500)
                t += 0.5
            if not shotted:
                await shot(page, 'phone-08-reel-ancient', 0)
                shotted = True
            await touch('touchEnd')
            for _ in range(4):
                st = await page.evaluate(TEN)
                if st:
                    samples.append(st)
                await page.wait_for_timeout(500)
                t += 0.5
            ph = await page.evaluate(PHASE)
            if ph != 'fight':
                break
        for _ in range(40):
            ph = await page.evaluate(PHASE)
            if ph not in ('fight', 'landing'):
                break
            await page.wait_for_timeout(250)
        landed = ph in ('jump', 'card')
        await shot(page, 'phone-09-reel-landed', 900)
        break
    await page.unroute('**/api/command')
    check(hooked['n'] >= 1, 'phone: a 🔴 Cổ đại fight was played', hooked['n'])
    gw = max((x['gw'] for x in samples), default=0)
    check(gw >= 40, f'phone: the green is wide even for 🔴 Cổ đại ({gw:.0f}% of the bar)')
    check(landed, 'phone: holding 3,5 s / letting go 2 s without watching lands the 🔴 Cổ đại fish', f'{len(samples)} samples')
    check(not any(x['active'] for x in samples), 'phone: #515 no text field focused while reeling')
    reds = sum(1 for x in samples if x['red'])
    print('INFO reel samples', len(samples), 'red', reds, 'tau range', min((x['tau'] for x in samples), default=0), max((x['tau'] for x in samples), default=0))


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='mnl-fcrowd-')
    db = os.path.join(tmp, 'g.db')
    async with async_playwright() as pw:
        browser = await getattr(pw, ENGINE).launch()   # MNL_ENGINE=webkit: Safari's engine (#515), no CDP reel run

        async def open_page(base, w, h, who):
            phone = w < 900
            ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone, is_mobile=phone, locale='vi-VN')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            await ctx.add_init_script(WS)
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and 'favicon' not in m.text and errors.append(f'{who}: {m.text[:200]}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {str(e)[:200]}'))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=40000)
            return ctx, page

        async def shot(page, name, wait=250):
            await page.wait_for_timeout(wait)
            await page.screenshot(path=str(OUT / f'{name}.png'))
            print('SHOT', OUT / f'{name}.png', flush=True)

        async def until(page, js, secs=8.0):
            for _ in range(int(secs * 10)):
                v = await page.evaluate(js)
                if v:
                    return v
                await page.wait_for_timeout(100)
            return await page.evaluate(js)

        async def view(page):
            return await page.evaluate(VIEW)

        with servers(db, tmp) as (base, env):
            species = json.loads(py(SPECIES, env=env))
            login = None
            for size, tag in (((390, 844), 'phone'), ((1280, 800), 'desk')):
                ctx, page = await open_page(base, *size, f'Lan-{tag}')
                if login is None:
                    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                    login = py(SEED, db, token, 'Lan', env=env)
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=40000)
                await page.wait_for_timeout(1500)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                # ⌨️ #515: a work screen's text field behind, focused before the lake opens
                await page.evaluate("(()=>{const i=document.createElement('input');i.type='text';i.id='behind';i.setAttribute('enterkeyhint','send');document.body.append(i);i.focus();})()")
                await page.evaluate(ACT, ['fishing', {'spot': 'ho'}])
                await page.wait_for_selector('dialog.fs-sheet[open] .fs-stall', timeout=15000)
                online = await until(page, "(async()=>(await import('/js/v4/fishing.js')).lakeView().online)()", 12)
                check(bool(online), f'{tag}: the live lake is on')
                v = await view(page)
                n = await page.evaluate(CROWD, [species, v['me']])
                check(n >= 1, f'{tag}: a crowd of 80 injected into the live socket', n)
                crowd = await until(page, "(async()=>{const v=(await import('/js/v4/fishing.js')).lakeView();return v.n===81&&v.peers.length===80;})()", 5)
                check(bool(crowd), f'{tag}: 👥 81 at the lake')
                await page.wait_for_timeout(600)
                check(await page.evaluate(SPRITES), f'{tag}: every Huyền thoại pair fits its sprite box')
                await shot(page, f'{tag}-01-crowd-wings-rods', 300)
                focus = await page.evaluate("document.activeElement?.id||document.activeElement?.tagName")
                check(focus != 'behind', f'{tag}: #515 the field behind lost the focus when the lake opened', focus)
                await page.evaluate("document.getElementById('behind').focus()")
                focus = await page.evaluate("document.activeElement?.id||document.activeElement?.tagName")
                check(focus != 'behind', f'{tag}: #515 a field behind cannot take the focus while the lake is open', focus)
                bar = await page.evaluate("(()=>{const e=document.querySelector('dialog.fs-sheet[open] .fs-scroll');return e&&!e.hidden?e.getBoundingClientRect().toJSON():null})()")
                check(bool(bar) and bar['width'] > 100, f'{tag}: the bar under the boardwalk', bar)
                cv = await page.evaluate("document.querySelector('dialog.fs-sheet[open] .fs-cv').getBoundingClientRect().toJSON()")
                y = cv['top'] + cv['height'] * .45
                # ↔️ a drag on the lake pans (no cast)
                cam0 = (await view(page))['cam']
                await page.mouse.move(cv['left'] + cv['width'] * .7, y)
                await page.mouse.down()
                for i in range(1, 13):
                    await page.mouse.move(cv['left'] + cv['width'] * .7 - i * 25, y)
                    await page.wait_for_timeout(16)
                await page.mouse.up()
                v = await view(page)
                check(v['cam'] > cam0 + 2 and v['phase'] == 'idle', f'{tag}: a drag left looks right along the boardwalk, no cast', f"{cam0} → {v['cam']:.2f}, {v['phase']}")
                await page.wait_for_timeout(700)
                v2 = await view(page)
                check(v2['cam'] >= v['cam'], f'{tag}: the fling glides on', f"{v['cam']:.2f} → {v2['cam']:.2f}")
                home = await page.evaluate("!document.querySelector('dialog.fs-sheet[open] .fs-home').hidden")
                await shot(page, f'{tag}-02-panned', 100)
                check(home or abs(v2['cam']) < 3, f'{tag}: 📍 Về chỗ tôi once I am out of sight', v2['cam'])
                # the thumb dragged to the far left end
                bar = await page.evaluate("document.querySelector('dialog.fs-sheet[open] .fs-scroll').getBoundingClientRect().toJSON()")
                th = await page.evaluate("document.querySelector('dialog.fs-sheet[open] .fs-sthumb').getBoundingClientRect().toJSON()")
                await page.mouse.move(th['left'] + th['width'] / 2, th['top'] + th['height'] / 2)
                await page.mouse.down()
                await page.mouse.move(bar['left'] - 40, th['top'] + th['height'] / 2, steps=8)
                await page.mouse.up()
                v = await view(page)
                check(v['cam'] <= -38.9, f'{tag}: the thumb dragged to the left end shows the far left of the crowd', v['cam'])
                await shot(page, f'{tag}-03-thumb-left-end', 200)
                await page.click('dialog.fs-sheet[open] .fs-home')
                back = await until(page, "(async()=>Math.abs((await import('/js/v4/fishing.js')).lakeView().cam)<.05)()", 4)
                check(bool(back), f'{tag}: 📍 Về chỗ tôi brings the view back to me')
                if tag == 'desk':
                    await page.mouse.move(cv['left'] + cv['width'] / 2, y)
                    await page.mouse.wheel(0, 600)
                    await page.wait_for_timeout(700)
                    v = await view(page)
                    check(v['cam'] > 3, f'{tag}: the mouse wheel pans along the boardwalk', v['cam'])
                    await page.click('dialog.fs-sheet[open] .fs-home')
                    await until(page, "(async()=>Math.abs((await import('/js/v4/fishing.js')).lakeView().cam)<.05)()", 4)
                # 🐋 catches beside their fishers
                await page.evaluate(CATCH, [species])
                await shot(page, f'{tag}-04-catch-leaps', 450)
                await shot(page, f'{tag}-05-catch-big-beside', 900)
                # a tap on a fisher: their card (with their rod)
                await page.wait_for_timeout(3000)
                v = await view(page)
                p = next(q for q in v['peers'] if q['s'] == 2)
                await page.mouse.click(v['left'] + p['x'], v['top'] + p['y'] - 25)
                card = await until(page, "(()=>{const e=document.querySelector('dialog.fs-sheet[open] .fs-pcard');return e&&!e.hidden?e.innerHTML:''})()", 5)
                check('fs-rod' in card and 'Ngư 2' in card, f'{tag}: a tap on a fisher opens their card with their rod drawn')
                await shot(page, f'{tag}-06-card', 200)
                await page.evaluate("document.querySelector('dialog.fs-sheet[open] [data-fs=pcardX]')?.click()")
                # a hold on the lake (away from everyone) still fills the power meter, then casts
                await page.mouse.move(cv['left'] + cv['width'] * .5, cv['top'] + cv['height'] * .3)
                await page.mouse.down()
                await page.wait_for_timeout(700)
                meter = await page.evaluate("!document.querySelector('dialog.fs-sheet[open] .fs-meter').hidden")
                await page.mouse.up()
                check(meter, f'{tag}: a hold on the lake still fills the power meter')
                await page.wait_for_timeout(900)
                check((await view(page))['phase'] in ('casting', 'fly', 'wait', 'bite'), f'{tag}: …and casts', (await view(page))['phase'])
                await shot(page, f'{tag}-07-my-cast', 200)
                active = await page.evaluate("document.activeElement?.matches?.('input,textarea')||false")
                check(not active, f'{tag}: #515 no text field focused after pressing')
                if tag == 'phone' and ENGINE == 'chromium':
                    await reel_ancient(page, ctx, shot)
                await ctx.close()
        await browser.close()
    for e in errors:
        print('ERROR', e)
    print(f'{len(fails)} failed; shots in {OUT}')
    return 1 if fails or errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
