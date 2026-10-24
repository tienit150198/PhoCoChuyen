#!/usr/bin/env python3
"""🌧️ Danh hiệu độc nhất (game/exclusive.py: "Cuồng Vũ Tán Tiên" and the frame "Mưa rơi" of mnt2410) in real browsers
(dev tool; needs playwright + chromium, PostgreSQL through TEST_DATABASE_URL). The game server and the live service
(chat, street, town, lake) on one disposable database; two 390×844 phones: Mưa (username mnt2410) and Lan.

  1. Mưa's Hành trình → Danh hiệu: the "Độc nhất" card, her frame first in the chooser; she wears it (jr_frame);
     Lan's save cannot (refused through the real command path);
  2. Cả phố chat: Lan sees Mưa's line with the rain frame on her avatar, the rain bubble and the chip; the popover says
     "Độc nhất";
  3. Đi dạo: Lan sees Mưa's name tag raining with her title; Mưa's card (frame + chip);
  4. 🎣 the lake: Lan sees Mưa's tag; her mini card;
  5. 🗺️ the town (isometric): Mưa's name tag carries her title;
  6. reduced motion: the still frame; Mưa puts the frame away ('off'): plain again.
Screenshots (JPEG) go to OUT (argv[1]); exit 1 on a failed check or a page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_exclusive.py [out_dir]
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

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'exclusive-shots'
ACT = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d||{});b.hidden=true;document.body.append(b);b.click();b.remove();})"
XID = 'ex_cuong_vu'
fails: list = []
errors: list = []


def check(ok, what, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (f' ({detail})' if detail else ''), flush=True)
    if not ok:
        fails.append(what)


SEED = r'''
import sys
from game import accounts, whats_new as wn
from game import marriage as mr
from game.storage import Store
db, token, name, user = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
store = Store(db, story=True)
out = accounts.register(store, token, dict(username=user, password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
def fn(s):
    j = s['journey']
    s['name'] = name
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    s['settings']['tutorialDone'] = True
    j.update(gender='female', intro=True, life_day=20, wallet=2_000_000, news=[])
mr._mutate(store, {sid: fn})
store.close_pool()
print(tok)
'''

ISO = r'''
import sys
from game import marriage as mr
from game.storage import Store
db, tok = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def fn(s):
    s['journey']['interface'] = dict(newInterface=True, interfacePromptSeen=True)
mr._mutate(store, {store.key(tok): fn})
store.close_pool()
print('ok')
'''

FRAME = r'''
import sys, json, secrets
from game.storage import Store
db, tok, v = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
try:
    out = store.command(tok, 'frame-' + secrets.token_hex(6), store.read(tok)[1], None, 'jr_frame', {'id': v})
    print(json.dumps(out['result']['message']))
except Exception as e:
    print(json.dumps('refused: ' + getattr(e, 'code', type(e).__name__)))
store.close_pool()
'''


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='mnl-excl-')
    db = os.path.join(tmp, 'g.db')
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def open_page(base, who, path='/'):
            ctx = await browser.new_context(viewport=dict(width=390, height=844), device_scale_factor=2, has_touch=True, is_mobile=True, locale='vi-VN', bypass_csp=True)
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and 'favicon' not in m.text and errors.append(f'{who}: {m.text[:200]}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {str(e)[:200]}'))
            await page.goto(base + path)
            await page.wait_for_selector('#app:not([hidden])', timeout=40000)
            return ctx, page

        async def calm(page):
            await page.wait_for_timeout(1200)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        async def shot(page, name, wait=250, clip=None):
            await page.wait_for_timeout(wait)
            await page.screenshot(path=str(OUT / f'{name}.jpg'), type='jpeg', quality=85, clip=clip)
            print('SHOT', OUT / f'{name}.jpg', flush=True)

        async def until(page, js, secs=8.0):
            for _ in range(int(secs * 10)):
                v = await page.evaluate(js)
                if v:
                    return v
                await page.wait_for_timeout(100)
            return await page.evaluate(js)

        with servers(db, tmp) as (base, env):
            people = {}
            for who, user in (('Mưa', 'mnt2410'), ('Lan', 'lan_pho')):
                ctx, page = await open_page(base, who)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                login = py(SEED, db, token, who, user, env=env)
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=40000)
                await calm(page)
                people[who] = (ctx, page, login)
            mua, lan = people['Mưa'][1], people['Lan'][1]
            boot = await mua.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json()).then(d=>d.ex_titles||null)")
            check(boot and boot[0]['id'] == XID and boot[0]['frame'] == 'Mưa rơi', 'her load carries the exclusive honour', str(boot))
            other = await lan.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json()).then(d=>d.ex_titles||null)")
            check(other is None, "Lan's load has none", str(other))

            # 1. the honours screen; she wears it; Lan cannot
            await mua.evaluate(ACT, ['home', {}])
            await mua.wait_for_selector('#sheet[open]', timeout=10000)
            await mua.evaluate(ACT, ['jrView', {'view': 'titles'}])
            await mua.wait_for_selector('#sheet[open] .ex-card', timeout=10000)
            card = await mua.inner_text('#sheet[open] .ex-card')
            check('Cuồng Vũ Tán Tiên' in card and 'Độc nhất' in card, 'the "Độc nhất" card', card.replace('\n', ' '))
            first = await mua.evaluate("document.querySelector('#sheet[open] .hf-opts .hf-opt:nth-child(2)')?.dataset.id")
            check(first == XID, 'her frame leads the chooser (after automatic)', str(first))
            await shot(mua, '01-mua-honours-screen', 900)
            await mua.click(f'#sheet[open] [data-action=jrFrame][data-id={XID}]')
            await until(mua, f"!!document.querySelector('#sheet[open] .hf-opt.on[data-id={XID}]')", 8)
            await mua.evaluate(f"document.querySelector('#sheet[open] .hf-opt[data-id={XID}]')?.scrollIntoView({{block:'center'}})")
            await shot(mua, '02-mua-wears-mua-roi', 1500)
            res = json.loads(py(FRAME, db, people['Lan'][2], XID, env=env))
            check(res == 'refused: not_yours', "Lan's jr_frame with her id is refused", res)
            await mua.evaluate(ACT, ['jrView', {'view': 'home'}])
            await mua.wait_for_timeout(800)
            chip = await mua.evaluate("document.querySelector('.jr-title-chip.ex-chip')?.innerText||''")
            check('Cuồng Vũ Tán Tiên' in chip, 'her own card shows the title first', chip)
            await mua.evaluate("document.querySelector('.jr-me')?.scrollIntoView({block:'start'})")
            await shot(mua, '03-mua-own-card', 600)
            await mua.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

            # 2. Cả phố chat
            for page in (mua, lan):
                ok = await until(page, "(async()=>{const {live}=await import('/js/v4/live.js');return live.welcomed&&live.flags.chat})()", 30)
                check(bool(ok), 'the live service is up')
                await page.evaluate(ACT, ['liveChat', {}])
                await page.wait_for_selector('.chat-sheet textarea', timeout=15000)
            await mua.fill('.chat-sheet textarea', 'Mưa rơi rồi cả phố ơi ☔ ai che ô cho mình với')
            await mua.click('.chat-sheet .ch-send')
            got = await until(lan, "!!document.querySelector('.chat-sheet .ch-bub.hf-ex')", 10)
            check(bool(got), "Lan sees Mưa's rain bubble")
            av = await lan.evaluate("!!document.querySelector('.chat-sheet .hf-av.hf-ex')")
            check(av, "and the rain frame on her avatar")
            hn = await lan.evaluate("document.querySelector('.chat-sheet .hn-chip.hn-ex')?.innerText||''")
            check('Cuồng Vũ Tán Tiên' in hn, 'and the title chip', hn)
            frame_img = await lan.evaluate("getComputedStyle(document.querySelector('.chat-sheet .hf-av.hf-ex'),'::after').backgroundImage.slice(0,40)")
            check(frame_img.startswith('url("data:image/svg+xml'), 'the frame is the animated svg', frame_img)
            await shot(lan, '04-lan-sees-mua-chat', 900)
            await lan.click('.chat-sheet .ch-name.hn-btn')
            pop = await until(lan, "document.querySelector('.chat-sheet .hn-pop')?.innerText||''", 5)
            check('Độc nhất' in pop and 'Mưa rơi' in pop, 'the popover marks it one of a kind', pop.replace('\n', ' '))
            await shot(lan, '05-lan-mua-titles-popover', 300)
            await mua.wait_for_timeout(500)
            await shot(mua, '06-mua-own-chat', 300)
            await lan.evaluate("document.documentElement.dataset.theme='dem'")
            await shot(lan, '07-lan-chat-dark', 500)
            await lan.evaluate("document.documentElement.dataset.theme='kem'")
            for page in (mua, lan):
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

            # 3. Đi dạo
            st = "(async()=>(await import('/js/v4/walk.js')).walk.state())()"
            for page in (mua, lan):
                await page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
                await page.wait_for_selector('#rail [data-action=v4Group][data-group=pho]', timeout=15000)
                await page.click('#rail [data-action=v4Group][data-group=pho]')
                await page.wait_for_selector('#rail [data-action=liveWalk]:visible', timeout=15000)
                await page.click('#rail [data-action=liveWalk]')
                await page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=15000)
            s = await until(lan, f"(async()=>{{const s=await {st[:-2]}();return s.people.length===2?s:null}})()", 12)
            check(bool(s), 'both strolling in one place')
            pm = await mua.evaluate("(async()=>(await import('/js/v4/walk.js')).walk.state().me)()")
            q = next((x for x in (s or {}).get('people', []) if x['pid'] == pm), None)
            check(bool(q), "Lan sees Mưa")
            await shot(lan, '08-lan-walk-sees-mua-tag', 1200)
            if q:
                box = await lan.locator('.walk-sheet .wk-canvas').bounding_box()
                v = s['view']
                x, y = box['x'] + v['ox'] + q['x'] * v['k'], box['y'] + v['oy'] + q['y'] * v['k']
                await shot(lan, '09-lan-walk-mua-tag-zoom', 0, clip=dict(x=max(0, x - 110), y=max(0, y - 230 * v['k'] - 40), width=220, height=200))
                await lan.touchscreen.tap(x, y - 40 * v['k'])
                c = await until(lan, "document.querySelector('.walk-sheet .wk-who')?.innerText||''", 6)
                fr = await lan.evaluate("!!document.querySelector('.walk-sheet .wk-who .hf-av.hf-ex')")
                check('Cuồng Vũ Tán Tiên' in c and fr, "Mưa's card: the frame and the title", c.replace('\n', ' ')[:160])
                await shot(lan, '10-lan-walk-mua-card', 500)
            for page in (mua, lan):
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.wait_for_timeout(400)

            # 4. 🎣 the lake
            for page in (mua, lan):
                await page.evaluate(ACT, ['fishing', {'spot': 'ho'}])
                await page.wait_for_selector('dialog.fs-sheet[open] .fs-stall', timeout=15000)
            both = "(async()=>{const v=(await import('/js/v4/fishing.js')).lakeView();return v.online&&v.n===2&&v.peers.length===1&&v.peers[0].whole?v:null;})()"
            v = await until(lan, both, 14)
            check(bool(v), 'both at the lake')
            await shot(lan, '11-lan-lake-sees-mua-tag', 1200)
            if v:
                p = v['peers'][0]
                cx, cy = v['left'] + p['x'], v['top'] + p['y']
                await shot(lan, '12-lan-lake-mua-tag-zoom', 0, clip=dict(x=max(0, cx - 110), y=max(0, cy - 190), width=220, height=150))
                await lan.mouse.click(cx, cy - 25)
                c = await until(lan, "(()=>{const e=document.querySelector('dialog.fs-sheet[open] .fs-pcard');return e&&!e.hidden?e.innerText:''})()", 6)
                fr = await lan.evaluate("!!document.querySelector('dialog.fs-sheet[open] .fs-pcard .hf-av.hf-ex')")
                check('Cuồng Vũ Tán Tiên' in c and fr, "Mưa's lake card: the frame and the title", c.replace('\n', ' ')[:160])
                await shot(lan, '13-lan-lake-mua-card', 400)
            for page in (mua, lan):
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.wait_for_timeout(400)

            # 5. 🗺️ the town (isometric)
            for who in ('Mưa', 'Lan'):
                py(ISO, db, people[who][2], env=env)
            for page in (mua, lan):
                await page.goto(base + '/?isometricdebug=1')
                await page.wait_for_function('!!window.__isoWorld', timeout=60000)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                if await page.evaluate('__isoWorld.mode') != 'town':
                    await page.locator('[data-action="isoTown"]').first.click()
                await page.wait_for_timeout(2500)
            pm = await mua.evaluate("(async()=>{const {live}=await import('/js/v4/live.js');return live.me?.pid})()")
            peer = await until(lan, f"(()=>{{const p=__isoWorld.getSocialAnchor('{pm}');return p||null}})()", 15)
            check(bool(peer), 'Lan sees Mưa in the town')
            tag = await lan.evaluate(f"(__isoWorld.remotePlayers.find(p=>p.pid==='{pm}')||{{}})")
            check(str(tag.get('tag', '')).startswith('🌧️ Cuồng Vũ Tán Tiên') and tag.get('tb') == '#e8ecff', "her town name tag carries the title", str({k: tag.get(k) for k in ('name', 'tag', 'ink', 'tb')}))
            await lan.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await lan.wait_for_timeout(1200)
            peer = await lan.evaluate(f"__isoWorld.getSocialAnchor('{pm}')")
            await shot(lan, '14-lan-town-sees-mua', 300)
            if peer:
                await shot(lan, '15-lan-town-mua-tag-zoom', 0, clip=dict(x=max(0, peer['x'] - 120), y=max(0, peer['y'] - 170), width=240, height=230))

            # 6. reduced motion and 'off'
            res = json.loads(py(FRAME, db, people['Mưa'][2], 'off', env=env))
            check('cất khung' in res, 'she puts the frame away', res)
        await browser.close()
    for e in errors:
        print('ERROR', e)
    print(f'{len(fails)} failed; shots in {OUT}')
    return 1 if fails or errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
