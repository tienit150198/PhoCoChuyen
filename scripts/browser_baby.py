#!/usr/bin/env python3
"""👶 Bé nhà mình + bế bé đi chơi (feedback #252 / #145): a two-browser walk-through (dev tool, as scripts/browser_ride.py,
whose servers it uses: story mode, PostgreSQL, the live service with the strolls and the fair).

Lan and Minh are married. Lan has her own child Mây (biết bò, 9 life days at home) and the couple's shared child Bông
(chập chững, born 25 days ago); Minh has his own newborn Tí. Both own the old tập thể. At 390x844:
  * Lan's home screen: the 🎉 card for a baby (once per baby on this device) → "🏡 Vào nhà thăm bé";
  * her home: the babies in the room (crawling on a mat, toddling), the 👶 card with the three free moments; one moment
    (gắn bó +1, tinh thần +1, the button ticks); "🤱 Bế bé đi chơi" with Bông;
  * the town: Lan carries Bông, walking (no vehicle while carrying);
  * Đi dạo: Lan carries Bông, Minh sees it (`bb` of the street's people);
  * the fair: Minh wants to carry Bông too: she is already in Lan's arms (`bb_taken`), he walks with Tí instead
    and Lan sees Minh with Tí;
  * Minh's home: Tí asleep in the cradle after "Ru bé ngủ".
Screenshots of each step; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    MNL_PY=<python with the server's requirements> python scripts/browser_baby.py [out_dir]
"""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_ride as br  # noqa: E402
from browser_coride import PW, api, marry, sid_of  # noqa: E402
from pg_test_support import test_connect  # noqa: E402

WALK, FAIR, TOWN = br.WALK, br.FAIR, br.TOWN
_wait = br.wait_http
br.wait_http = lambda url, secs=60: _wait(url, max(secs, 240))   # a busy machine: the first build of the static bundle
VN = datetime.timezone(datetime.timedelta(hours=7))
STATE = "fetch('/api/state').then(r=>r.json()).then(d=>d.state)"
ART = """async () => {
  const L = await import('/js/v4/look.js'), A = await import('/js/v4/baby-art.js');
  const st = await fetch('/api/state').then(r => r.json()).then(d => d.state);
  const box = document.createElement('div');
  box.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#f6efe3;display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px';
  const cv = document.createElement('canvas'); cv.width = 760; cv.height = 620; cv.style.cssText = 'width:380px;height:310px';
  box.append(cv);
  const all = [['so_sinh', 'basic'], ['biet_bo', 'yem'], ['chap_chung', 'flower']];
  const row = document.createElement('div'); row.style.cssText = 'display:flex;flex-wrap:wrap;justify-content:center;gap:6px';
  for (const [g, o] of all) for (const asleep of [false, true])
    row.insertAdjacentHTML('beforeend', `<div style="background:#fff;border-radius:12px;padding:4px">${A.babyPortrait({g, o}, {size: 112, asleep})}</div>`);
  box.append(row); document.body.append(box);
  const c = cv.getContext('2d');
  all.forEach(([g, o], i) => { const F = L.figureOf(L.lookOf(st), st.journey.gender); F.bb = {g, o};
    c.save(); c.translate(130 + i * 250, 590); c.scale(3, 3); L.paintPlayer(c, F, L.CANVAS); c.restore(); });
}"""


def seed_home(db: str, token: str, child: str, age: int, spouse: str, cid: int, side: str) -> None:
    """Own the old tập thể (a sofa, a bed), adopt a personal child `age` life days ago, and carry the married block a
    real wedding leaves in the save (the couple row itself is written by browser_coride.marry)."""
    from game import deco as dc
    from game import household as hh
    from game import housing as hs
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        j = s['journey']
        j['wallet'] = 8000
        hs.apply(s, 'jr_home_buy', {'kind': 'tap_the', 'down': 1800, 'confirm': True})
        for k, room, x, y in (('sofa', 'living', 0, 30), ('giuong', 'bed', 0, 20)):
            dc.apply(s, 'jr_deco_buy', dict(item=k, confirm=True, put=dict(r=room, x=x, y=y)))
        hh.action(s, 'jr_hh_adopt', dict(kind='child', name=child, confirm=True))
        j['household']['child']['since'] = j['life_day'] - age
        j['household']['child']['day'] = j['life_day'] - age
        j['wallet'] = 600
        j['life']['spirit'] = 55
        mr._apply_effect(s, dict(id=f'bb-wed-{cid}-{side}', kind='status',
                                 data=json.dumps(dict(set='married', name=spouse, couple=cid, side=side))))
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def shared_child(db: str, a: str, name: str, age: int) -> None:
    from game import family
    born = (datetime.datetime.now(VN).date() - datetime.timedelta(days=age)).isoformat()
    state = dict(family._child(name, 'adopt'), born=born, bond=12, outfit='flower', owned=['basic', 'flower'])
    con = test_connect(db)
    with con:
        cid = con.execute('SELECT couple FROM marriage_bonds WHERE sid=?', (a,)).fetchone()[0]
        con.execute('INSERT INTO family_children(couple, state) VALUES(?, ?)', (cid, json.dumps(state, ensure_ascii=False)))
    con.close()


async def run(size, problems, checks) -> None:
    from playwright.async_api import async_playwright
    tag = f'{size[0]}x{size[1]}'
    out = br.OUT

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + f' [{tag}] ' + what)
        if not cond:
            problems.append(f'check [{tag}]: ' + what)

    async def popups(p):
        """browser_ride's popups, then the gift cards that come a moment later (🎁 "Quà cả phố", the fair's 500 xu)."""
        await br.popups(p.page)
        for _ in range(4):
            await p.page.wait_for_timeout(500)
            b = p.page.locator('[data-gf="ok"]:visible, [data-fh-key="giftok"]:visible')
            if not await b.count():
                break
            await b.first.click()

    async def shot(p, name, quiet=True):
        if quiet:
            await popups(p)
        await p.page.wait_for_timeout(400)
        await p.page.screenshot(path=str(out / f'{tag}-{name}.png'))

    async def reload(p):
        await p.page.reload()
        await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await p.page.wait_for_timeout(900)
        await br.popups(p.page)

    async def town(p):
        if not await p.page.evaluate("!!document.querySelector('#sheet[open] .tw-stage')"):
            await br.act(p.page, 'home')
        return await br.until(p.page, TOWN, 'return s.on&&s.me', f'{p.name}: the town is up', 15)

    async def close_all(p):
        await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

    async def home(p):
        await close_all(p)
        await br.act(p.page, 'jrEnterHome')
        await p.page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=15000)
        await p.page.wait_for_timeout(700)

    async def hello_off(p):
        await p.page.evaluate("document.querySelectorAll('dialog.jr-scene[open]').forEach(d=>d.close())")   # a title scene, if any, first
        if await p.page.locator('dialog.bb-hello[open]').count():
            await p.page.click('dialog.bb-hello [data-bb="close"]')
            await p.page.wait_for_timeout(300)

    async def steps(lan, minh):
        u = f'{size[0]}{size[1]}'
        await api(minh, '/api/account/register', dict(username=f'minh{u}', password=PW, confirm=PW, display='Minh'))
        await api(lan, '/api/account/register', dict(username=f'lan{u}', password=PW, confirm=PW, display='Lan'))
        sl, sm = sid_of(br.DB, f'lan{u}'), sid_of(br.DB, f'minh{u}')
        marry(br.DB, sm, sl)
        con = test_connect(br.DB)
        cid = con.execute('SELECT couple FROM marriage_bonds WHERE sid=?', (sl,)).fetchone()[0]
        con.close()
        for p in (lan, minh):
            tok = next(c['value'] for c in await p.ctx.cookies() if c['name'] == 'mnl_session')
            seed_home(br.DB, tok, 'Mây' if p is lan else 'Tí', 9 if p is lan else 0, 'Minh' if p is lan else 'Lan', cid, 'b' if p is lan else 'a')
        shared_child(br.DB, sl, 'Bông', 25)
        fam = await api(lan, '/api/family/baby')
        check(fam.get('child', {}).get('grow') == 'chap_chung' and fam['child']['name'] == 'Bông', f'GET /api/family/baby: {fam.get("child", {}).get("grow")}')

        # ---- Lan: the 🎉 card on the home screen (Minh: reloaded too, his card put aside for later) ----
        await reload(minh)
        await town(minh)
        await hello_off(minh)
        await lan.page.reload()
        await lan.page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await lan.page.wait_for_timeout(900)
        await br.popups(lan.page)
        await town(lan)
        try:
            await lan.page.wait_for_selector('dialog.bb-hello[open]', timeout=12000)
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        check(ok, 'the 🎉 baby card shows on the home screen')
        if ok:
            txt = await lan.page.inner_text('dialog.bb-hello')
            check('Bông' in txt or 'Mây' in txt, f'the card names a baby ({txt[:60]!r})')
            await shot(lan, '01-hello-card', quiet=False)
            await lan.page.click('dialog.bb-hello [data-bb="home"]')
        else:
            await home(lan)
        await lan.page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=15000)
        await lan.page.wait_for_timeout(900)
        if await lan.page.locator('dialog.bb-hello[open]').count():
            await shot(lan, '02-hello-in-the-room', quiet=False)
            await hello_off(lan)
        n = await lan.page.locator('.dc-sheet svg.dc-room g.dc-baby').count()
        check(n == 2, f'two babies in Lan\'s room ({n})')
        await shot(lan, '03-home-room')
        # tap the baby: Lan walks over, says a line, the card scrolls into view
        await lan.page.locator('.dc-sheet svg.dc-room g.dc-baby').first.click()
        await lan.page.wait_for_timeout(1400)
        await shot(lan, '04-home-tap-baby')
        card = lan.page.locator('#dc-baby-card')
        check(await card.count() == 1, 'the 👶 card beside the room')
        await card.scroll_into_view_if_needed()
        await shot(lan, '05-baby-card')
        wallet0 = (await lan.page.evaluate(STATE))['journey']['wallet']
        await lan.page.click('#dc-baby-card [data-dc="bbMoment"][data-baby="child"][data-act="choi"]')
        await lan.page.wait_for_timeout(1200)
        await shot(lan, '05b-moment-line', quiet=False)
        await br.popups(lan.page)   # the first command after seeding: new titles (wallet, home)
        did = ((await lan.page.evaluate(STATE))['journey'].get('cradle') or {}).get('did')
        check(did and 'child:choi' in did, f'a free moment with Mây ({did})')
        btn = lan.page.locator('#dc-baby-card [data-dc="bbMoment"][data-baby="child"][data-act="choi"]')
        check(await btn.is_disabled(), 'the moment is done for today (✓, disabled)')
        await lan.page.click('#dc-baby-card [data-dc="bbMoment"][data-baby="shared"][data-act="ru"]')
        await lan.page.wait_for_timeout(1500)
        await br.popups(lan.page)
        btn = lan.page.locator('#dc-baby-card [data-dc="bbMoment"][data-baby="shared"][data-act="ru"]')
        check(await btn.is_disabled(), 'a moment with the shared child Bông (POST /api/marriage/family_child_moment)')
        wallet1 = (await lan.page.evaluate(STATE))['journey']['wallet']
        check(wallet0 == wallet1, f'moments are free ({wallet0} → {wallet1})')
        await card.scroll_into_view_if_needed()
        await shot(lan, '06-baby-card-after-moments')
        await lan.page.click('#dc-baby-card [data-dc="bbCarry"][data-baby="shared"]')
        await lan.page.wait_for_timeout(700)
        await card.scroll_into_view_if_needed()
        await shot(lan, '07-carry-bong')
        n = await lan.page.locator('.dc-sheet svg.dc-room g.dc-baby').count()
        check(n == 1, f'Bông left the room in Lan\'s arms ({n} baby left)')

        # ---- the town: carrying means walking ----
        await close_all(lan)
        s = await town(lan)
        check(s['ride'] is None, f'carrying Bông, Lan walks in town (ride {s["ride"]})')
        tg = await lan.page.evaluate("document.querySelector('.tw-stage .bb-toggle')?.textContent||''")
        check('Bông' in tg, f'the 👶 toggle: {tg!r}')
        await lan.page.evaluate("()=>__townWalk.go('lm:bank')")
        await lan.page.wait_for_timeout(900)
        await shot(lan, '08-town-carrying')

        # ---- Đi dạo: Minh sees Bông in Lan's arms ----
        for p in (lan, minh):
            await close_all(p)
            await br.act(p.page, 'liveWalk')
            await p.page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=15000)
        await br.until(lan.page, WALK, 'return s.room&&s.me', 'Lan strolls', 10)
        s = await br.until(minh.page, WALK, 'return s.room&&s.people.some(q=>q.bb&&q.bb.g==="chap_chung")', 'Minh sees Lan carrying Bông', 10)
        theirs = next(q for q in s['people'] if q.get('bb'))
        check(theirs['bb'].get('n') == 'Bông' and theirs['bb'].get('sh') == 1, f"Bông on the wire: {theirs['bb']}")
        await lan.page.evaluate("async()=>{const {walk}=await import('/js/v4/walk.js');const st=walk.state(),m=st.people.find(q=>q.pid===st.me);walk.moveTo(m.x>300?140:460,m.y-70);}")
        await lan.page.wait_for_timeout(700)
        await shot(lan, '09-walk-lan-carrying')
        await shot(minh, '10-walk-minh-sees-bong')

        # ---- the fair: Bông is already in Lan's arms (she is still on the stroll) ----
        async def to_fair(p):
            await close_all(p)
            await br.act(p.page, 'fair')
            await p.page.wait_for_selector('.fh-sheet[open] .fh-wcanvas', timeout=15000)
            await br.until(p.page, FAIR, 'return s&&s.on&&s.me&&s.crowd.on', f'{p.name}: the fairground is up', 10)

        await minh.page.evaluate("()=>globalThis.__baby.set('shared')")
        await to_fair(minh)
        try:
            await minh.page.wait_for_function("(document.querySelector('.fh-sheet .fh-wsay')?.textContent||'').includes('đang bế bé rồi')", timeout=4000)
            told = True
        except Exception:  # noqa: BLE001
            told = False
        check(told, 'Minh is told Lan already carries Bông (a bubble over him)')
        await popups(minh)                                          # the organisers' 500 xu, once
        await shot(minh, '11-fair-bong-taken', quiet=False)
        carried = await minh.page.evaluate("()=>globalThis.__baby.carried(null)")
        check(carried is None, f'Minh walks without Bông this visit ({carried})')
        await minh.page.evaluate("()=>__fairWalk.walk(.42,.56)")
        await to_fair(lan)                                          # Lan leaves the stroll for the fair, Bông in her arms
        await popups(lan)
        await lan.page.evaluate("()=>__fairWalk.walk(.58,.58)")
        s = await br.until(minh.page, FAIR, 'return s.crowd.people.some(q=>q.bb&&q.bb.sh===1)', 'Minh sees Lan carrying Bông at the fair', 10)
        check(True, 'Minh sees Lan carrying Bông at the fair (`bb` of the crowd)')
        await minh.page.wait_for_timeout(1500)
        await shot(minh, '12-fair-minh-sees-bong')
        await shot(lan, '13-fair-lan-carrying')

        # ---- Minh's home: Tí asleep in the cradle ----
        await minh.page.evaluate("()=>globalThis.__baby.set('')")
        await home(minh)
        await hello_off(minh)
        await minh.page.evaluate("document.querySelectorAll('dialog.jr-scene[open]').forEach(d=>d.close())")   # a title scene left from the fair
        await hello_off(minh)
        await minh.page.click('#dc-baby-card [data-dc="bbMoment"][data-baby="child"][data-act="ru"]')
        await minh.page.wait_for_timeout(1200)
        await minh.page.evaluate("document.querySelectorAll('dialog.jr-scene[open]').forEach(d=>d.close())")
        await hello_off(minh)
        await shot(minh, '14-home-ti-asleep', quiet=False)
        await minh.page.locator('#dc-baby-card').scroll_into_view_if_needed()
        await shot(minh, '15-baby-card-minh', quiet=False)
        wide = await minh.page.evaluate("document.scrollingElement.scrollWidth>innerWidth+1")
        check(not wide, 'no sideways scroll')

        # ---- the art, large: the three stages in the arms (canvas pen) and at home (SVG), awake and asleep ----
        await close_all(lan)
        await lan.page.evaluate(ART)
        await lan.page.wait_for_timeout(300)
        await lan.page.screenshot(path=str(out / f'{tag}-16-art-stages.png'))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        lan = await br.player(browser, br.BASE, 'Lan', [('xe_ga', 'hong', 'MÂY 01')], size, problems)
        minh = await br.player(browser, br.BASE, 'Minh', [], size, problems)
        for p in (lan, minh):
            p.page.on('response', lambda r, n=p.name: 400 <= r.status < 500 and checks.append(f'INFO [{tag}] {n}: HTTP {r.status} {r.url}'))
        try:
            await steps(lan, minh)
        except Exception:
            for p in (lan, minh):
                await p.page.screenshot(path=str(out / f'{tag}-FAIL-{p.name}.png'))
                print(p.name, 'dialogs:', await p.page.evaluate("[...document.querySelectorAll('dialog[open]')].map(d=>d.className)"))
            raise
        for p in (lan, minh):
            await p.ctx.close()
        await browser.close()


async def main_async():
    problems, checks = [], []
    for size in ((390, 844),):
        try:
            await run(size, problems, checks)
        except AssertionError as e:
            problems.append(f'{size}: {e}')
    print(*checks, sep='\n')
    return problems


def main():
    br.OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mnl-baby-', dir=os.environ.get('TMPDIR'), ignore_cleanup_errors=True) as tmp, br.servers(tmp) as (base, db):
        br.BASE, br.DB = base, db
        problems = asyncio.run(main_async())
    if problems:
        print('problems:', *problems, sep='\n  ')
        sys.exit(1)
    print('ok:', br.OUT)


if __name__ == '__main__':
    main()
