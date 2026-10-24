#!/usr/bin/env python3
"""👥 Hồ câu đông vui (24/10): two players at the same lake in real browsers (dev tool; needs playwright + chromium,
PostgreSQL through TEST_DATABASE_URL). The game server and the live service (LIVE_TOWN=1: LIVE_FISH on) on one
disposable database.

  1. Lan (390×844 phone) and Minh (390×844 phone) open 🎣 Câu cá at 🏞️ Hồ phố: each sees "👥 2" and the other drawn as
     their character on the boardwalk (a whole entry with the look), each their own character instead of a stick;
  2. Lan casts (a plain tap): Minh sees her bobber fly out and land (her hint 'cast');
  3. Lan lands a 🟡 Huyền thoại fish through the real command path (the round put in her save, jr_fish_land through
     game/storage.py: the commit's NOTIFY): Minh sees it leap into her hands with its name and weight, the feed line
     "🎣 Lan … vừa câu được …" and the lake-wide banner; a landing refused (reeled too soon) shows nothing;
  4. Minh taps Lan: her mini card (🐟 Hôm nay, 🐋 Lớn nhất, 📖 Sổ cá);
  5. Lan says something (💬): the bubble over her head on Minh's screen;
  6. Lan closes the lake: Minh sees "👥 1".
Screenshots (JPEG) go to OUT (argv[1]); exit 1 on a failed check or a page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_fishing_shared.py [out_dir]
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

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'fishing-shared-shots'
ACT = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d||{});b.hidden=true;document.body.append(b);b.click();b.remove();})"
VIEW = "(async()=>(await import('/js/v4/fishing.js')).lakeView())()"
fails: list = []
errors: list = []


def check(ok, what, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (f' ({detail})' if detail else ''), flush=True)
    if not ok:
        fails.append(what)


SEED = r'''
import sys, hashlib
from game import accounts, whats_new as wn
from game import marriage as mr
from game.storage import Store
db, token, name = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
out = accounts.register(store, token, dict(username='u' + hashlib.md5(name.encode()).hexdigest()[:12], password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
def fn(s):
    j = s['journey']
    s['name'] = name
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    j.update(gender='female' if name == 'Lan' else 'male', intro=True, life_day=20, wallet=2_000_000)
mr._mutate(store, {sid: fn})
store.close_pool()
print(tok)
'''

LAND = r'''
import sys, json, secrets, time
from game import fishing as F
from game import marriage as mr
from game.storage import Store
db, tok, sp, g, early = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] == '1'
store = Store(db, story=True)
t = time.time()
rnd = secrets.token_hex(16)
hook = t - (0.2 if early else 10)
def put(s):
    d = F.ensure(s)
    d['act'] = dict(id=rnd, at=t - 30, spot='ho', trip='', rod='tre', dist=42.0, zone=0, kind='fish', sp=sp, g=g, bite=hook - 2, hook=hook,
                    reel=4.0, snap=0, nib=[])
mr._mutate(store, {store.key(tok): put})
try:
    out = store.command(tok, 'land-' + rnd[:8], store.read(tok)[1], None, 'jr_fish_land', {'round': rnd, 'ok': True})
    print(json.dumps(out.get('result', out).get('land', {}).get('res') if isinstance(out, dict) else None))
except Exception as e:
    print(json.dumps('refused: ' + type(e).__name__))
store.close_pool()
'''

PICK = r'''
import json
from game import fishing_content as C
sp = next((x for x in C.SPECIES.values() if x['r'] == 5 and 'ho' in x['spots']), None) or next(x for x in C.SPECIES.values() if x['r'] == 5)
print(json.dumps([sp['id'], sp['name'], int(sp['w'][1] * 800)]))
'''


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='mnl-fshare-')
    db = os.path.join(tmp, 'g.db')
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def open_page(base, who):
            ctx = await browser.new_context(viewport=dict(width=390, height=844), device_scale_factor=2, has_touch=True, is_mobile=True, locale='vi-VN')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and 'favicon' not in m.text and errors.append(f'{who}: {m.text[:200]}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {str(e)[:200]}'))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=40000)
            return ctx, page

        async def calm(page):
            await page.wait_for_timeout(1200)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        async def shot(page, name, wait=250):
            await page.wait_for_timeout(wait)
            await page.screenshot(path=str(OUT / f'{name}.jpg'), type='jpeg', quality=82)
            print('SHOT', OUT / f'{name}.jpg', flush=True)

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
            people = {}
            for who in ('Lan', 'Minh'):
                ctx, page = await open_page(base, who)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                login = py(SEED, db, token, who, env=env)
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=40000)
                await calm(page)
                people[who] = (ctx, page, login)
            lan, minh = people['Lan'][1], people['Minh'][1]
            sp_id, sp_name, grams = json.loads(py(PICK, env=env))

            # 1. both at Hồ phố
            for page in (lan, minh):
                await page.wait_for_timeout(1500)   # the live socket (loaded when idle)
                await page.evaluate(ACT, ['fishing', {'spot': 'ho'}])
                await page.wait_for_selector('dialog.fs-sheet[open] .fs-stall', timeout=15000)
            both = "(async()=>{const v=(await import('/js/v4/fishing.js')).lakeView();return v.online&&v.n===2&&v.peers.length===1&&v.peers[0].whole;})()"
            ok_l, ok_m = await until(lan, both, 12), await until(minh, both, 12)
            vl, vm = await view(lan), await view(minh)
            check(ok_l and ok_m, 'both see "👥 2" with the other drawn whole', f'Lan {vl["n"]} {[p["name"] for p in vl["peers"]]}, Minh {vm["n"]} {[p["name"] for p in vm["peers"]]}')
            check(vm['peers'] and vm['peers'][0]['name'] == 'Lan', 'Minh sees Lan by name', str(vm['peers'][:1]))
            chip = await minh.inner_text('dialog.fs-sheet[open] .fs-feed-n')
            check('👥 2' in chip, 'the feed bar counts the fishers', chip)
            await shot(minh, '01-minh-sees-lan', 600)
            await shot(lan, '02-lan-sees-minh', 0)
            fps = await minh.evaluate("()=>new Promise(done=>{let n=0;const t0=performance.now();const f=()=>{n++;if(performance.now()-t0<1000)requestAnimationFrame(f);else done(n);};requestAnimationFrame(f);})")
            check(fps >= 40, f'the shared lake animates ({fps} frames in a second)')

            # 2. Lan casts: Minh sees it
            b = await lan.evaluate("(()=>{const r=document.querySelector('dialog.fs-sheet[open] .fs-go').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];})()")
            await lan.mouse.move(*b)
            await lan.mouse.down()
            await lan.wait_for_timeout(60)
            await lan.mouse.up()
            cast = await until(minh, "(async()=>(await import('/js/v4/fishing.js')).lakeView().peers.some(p=>p.a==='cast'))()", 6)
            await shot(minh, '03-minh-sees-lan-cast', 350)
            check(bool(cast), "Minh sees Lan's cast fly out")
            await minh.wait_for_timeout(1400)
            await shot(minh, '04-lan-bobber-on-the-water', 0)
            await lan.evaluate("document.querySelector('dialog.fs-sheet[open] .fs-x[data-fs=close]')?.click()")   # leave the round: confirm needed only while fighting
            await lan.wait_for_timeout(400)
            await lan.evaluate(ACT, ['fishing', {'spot': 'ho'}])
            await lan.wait_for_selector('dialog.fs-sheet[open] .fs-stall', timeout=15000)
            await until(lan, both, 10)
            await until(minh, both, 10)

            # 3. a refused landing shows nothing; a real one leaps into her hands, the feed, the banner
            res = json.loads(py(LAND, db, people['Lan'][2], sp_id, str(grams), '1', env=env))
            await minh.wait_for_timeout(1200)
            vm = await view(minh)
            check(str(res).startswith('refused') and not vm['feed'] and not any(p['got'] for p in vm['peers']),
                  'a landing reeled too soon is refused and shows nothing', str(res))
            res = json.loads(py(LAND, db, people['Lan'][2], sp_id, str(grams), '0', env=env))
            check(res == 'fish', 'Lan lands a 🟡 Huyền thoại fish through the real command', str(res))
            got = await until(minh, "(async()=>{const v=(await import('/js/v4/fishing.js')).lakeView();return v.peers.some(p=>p.got)&&v.feed.length?v:null;})()", 6)
            await shot(minh, '05-lan-catch-leaps', 300)
            await shot(minh, '06-lan-holds-it-up', 900)
            check(bool(got) and got['peers'][0]['got']['s'] == sp_id, "Minh sees Lan's catch in her hands", str(got and got['peers'][0]['got']))
            line = await minh.inner_text('dialog.fs-sheet[open] .fs-feed-line')
            check('Lan' in line and 'vừa câu được' in line and sp_name in line, 'the feed line', line)
            check(bool(got) and 'HUYỀN THOẠI' in (got['banner'] or '').upper(), 'the lake-wide banner', got and got['banner'])
            await minh.click('dialog.fs-sheet[open] .fs-feed-line')
            await minh.wait_for_timeout(300)
            await shot(minh, '07-feed-open', 0)
            await minh.click('dialog.fs-sheet[open] .fs-feed-line')
            mine = await view(lan)
            check(any('vừa câu được' in x for x in mine['feed']), "Lan's own feed has her catch too", str(mine['feed'][-1:]))

            # 4. Minh taps Lan: her mini card
            await minh.wait_for_timeout(3500)   # the fish held up fades
            vm = await view(minh)
            p = vm['peers'][0]
            check(vm['phase'] == 'idle', 'Minh is idle before the tap', vm['phase'])
            await minh.mouse.click(vm['left'] + p['x'], vm['top'] + p['y'] - 25)   # canvas → page
            card = await until(minh, "(()=>{const e=document.querySelector('dialog.fs-sheet[open] .fs-pcard');return e&&!e.hidden&&/Hôm nay/.test(e.innerText)?e.innerText:''})()", 6)
            await shot(minh, '08-lan-card', 200)
            check('Lan' in card and 'Hôm nay' in card and sp_name in card and 'Sổ cá' in card, "Lan's mini card", card.replace('\n', ' ')[:200])
            if card:
                await minh.click('dialog.fs-sheet[open] .fs-pcard [data-fs="pcardX"]')

            # 5. 💬 a bubble to the people near
            await lan.click('dialog.fs-sheet[open] [data-fs="sayOpen"]')
            await lan.fill('dialog.fs-sheet[open] .fs-sayrow input', 'Cá to quá trời!')
            await lan.click('dialog.fs-sheet[open] .fs-sayrow button[type=submit]')
            said = await until(minh, "(async()=>(await import('/js/v4/fishing.js')).lakeView().peers.find(p=>p.said)?.said||'')()", 6)
            await shot(minh, '09-lan-bubble', 200)
            check(said == 'Cá to quá trời!', "Minh sees Lan's bubble", said)

            # 6. Lan leaves
            await lan.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            alone = await until(minh, "(async()=>{const v=(await import('/js/v4/fishing.js')).lakeView();return v.online&&v.n===1&&!v.peers.length;})()", 8)
            check(bool(alone), 'Lan left: Minh sees "👥 1"')
            await shot(minh, '10-minh-alone', 300)
        await browser.close()
    for e in errors:
        print('ERROR', e)
    print(f'{len(fails)} failed; shots in {OUT}')
    return 1 if fails or errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
