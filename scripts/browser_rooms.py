"""🛁 Nhà tắm, 🏊 hồ bơi (1.4.11): a browser look at the new rooms (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (as scripts/browser_deco.py) and seeds one save straight in its
database: a character who owns Biệt thự Sông Hồng with a bathroom and the pool deck set up. In the browser, at 390x844
and 1280x800, by day and at night: the bathroom, the pool (its water moves), "Bơi một vòng", then the save is moved to
the tập thể (a small bathroom) and to the dorm (the shared one). Screenshots to the out dir; exit 1 on a console error
or a failed step.

    python scripts/browser_rooms.py [out_dir]
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_deco import mutate, tz_for  # noqa: E402
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_rooms_shots'


def put(s, k, room, x, y, on=None):
    from game import deco as dc
    q = dict(r=room, x=x, y=y)
    if on:
        q['on'] = on
    return dc.apply(s, 'jr_deco_buy', dict(item=k, confirm=True, put=q))['uid']


def seed_villa(s):
    from game import housing as hs
    from game import journey as jr
    from game import whats_new as wn
    j = s['journey']
    s['name'] = 'Lan'
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    j.update(gender='female', intro=True, life_day=8, wallet=80000)
    j['life']['spirit'] = 55
    hs.apply(s, 'jr_home_buy', {'kind': 'biet_thu_song', 'down': 60000, 'confirm': True})
    jr._wallet(j, 9000, 'salary', 'Lương')
    tub = put(s, 'bon_tam', 'bath', 0, 40)
    put(s, 'vit_cao_su', 'bath', 12, 0, on=tub)
    put(s, 'bon_rua', 'bath', 80, 0)
    put(s, 'guong_tam', 'bath', 80, 0)
    put(s, 'ke_khan', 'bath', 40, 20)
    put(s, 'cay_monstera', 'bath', 100, 50)
    put(s, 'tham_tam', 'bath', 80, 50)
    put(s, 'ghe_tam_nang', 'pool', 0, 60)
    put(s, 'ghe_tam_nang', 'pool', 120, 60)
    put(s, 'du_che', 'pool', 80, 55)
    put(s, 'phao', 'pool', 70, 30)
    put(s, 'cay_dua', 'pool', 0, 0)
    put(s, 'lo_nuong', 'pool', 160, 0)
    put(s, 'den_vuon', 'pool', 20, 0)


def move(kind):
    def fn(s):
        from game import housing as hs
        j = s['journey']
        h = hs.get(s)
        if h['own']:
            hs.apply(s, 'jr_home_sell', {'confirm': True, 'value': hs.value_of(h['own'], j['life_day'])})
        if kind == 'tap_the':
            hs.apply(s, 'jr_home_buy', {'kind': 'tap_the', 'down': 1800, 'confirm': True})
            put(s, 'buong_tam', 'bath', 0, 20)
            put(s, 'xuong_rong', 'bath', 0, 0, on='#toilet')   # a little cactus on the cistern
            put(s, 'may_giat', 'bath', 20, 40)
        else:
            hs.apply(s, 'jr_home_rent', {'kind': kind, 'confirm': True})
            put(s, 'gio_do_tam', 'bath', 0, 0, on='#shelf')
            put(s, 'tham_tam', 'bath', 20, 20)
    return fn


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, failed = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h, hour in ((390, 844, 10), (1280, 800, 10), (390, 844, 21), (1280, 800, 21)):
                if os.environ.get('ROOMS_ONLY') and os.environ['ROOMS_ONLY'] != str(w):
                    continue
                ctx = await browser.new_context(viewport=dict(width=w, height=h), timezone_id=tz_for(hour), has_touch=w < 500)
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.decoTip2','1')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                tag = f'{w}x{h}' + ('' if hour < 18 else '-night')

                def expect(ok, what):
                    if not ok:
                        failed.append(f'{tag}: {what}')
                        print('  ✗', what)

                async def popups():
                    for _ in range(4):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, button:has-text("Đã hiểu"):visible, button:has-text("Tuyệt!"):visible')
                        if not await b.count():
                            break
                        await b.first.click()
                        await page.wait_for_timeout(400)

                async def reload():
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=60000)
                    await page.wait_for_timeout(1500)
                    await popups()
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

                async def shot(name, full=False):
                    await page.wait_for_timeout(450)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=full)

                async def open_inside():
                    await page.wait_for_selector('.jr-house-row', timeout=10000)
                    await page.click('.jr-house-row')
                    await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                    await popups()
                    await page.click('.hs-sheet [data-hs="inside"]:not([data-mode])')
                    await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)

                async def room(rid):
                    await page.click(f'.dc-sheet [data-dc="room"][data-room="{rid}"]')
                    await page.wait_for_selector(f'.dc-sheet svg.dc-room[data-room="{rid}"]', timeout=5000)
                    await page.evaluate("""()=>{const w=document.querySelector('.dc-sheet .dc-rooms'),h=document.querySelector('.dc-sheet .sheet-head');if(!w)return;
                        w.scrollIntoView({block:'start'});let s=w.parentElement;while(s&&s.scrollHeight<=s.clientHeight+2)s=s.parentElement;
                        if(s&&h)s.scrollBy(0,-(h.getBoundingClientRect().bottom-s.getBoundingClientRect().top)-8);}""")
                    await page.wait_for_timeout(300)

                async def tabs():
                    return await page.evaluate("[...document.querySelectorAll('.dc-sheet [data-dc=\"room\"]')].map(b=>b.dataset.room)")

                # ---- the villa
                mutate(db, token, seed_villa)
                await reload()
                await open_inside()
                got = await tabs()
                print(tag, 'rooms:', got)
                expect(got == ['living', 'bed', 'bed2', 'kitchen', 'yard', 'bath', 'pool'], 'the villa shows its bathroom and its pool')
                await room('bath')
                await shot('01-villa-bath')
                await room('pool')
                await shot('02-villa-pool')
                waves = await page.evaluate("document.querySelectorAll('.dc-sheet svg.dc-room .dc-wave').length")
                anim = await page.evaluate("getComputedStyle(document.querySelector('.dc-sheet svg.dc-room .dc-wave')).animationName")
                expect(waves == 3 and anim == 'dc-wave', f'the water moves ({waves}, {anim})')
                if hour < 18:
                    await page.evaluate("document.body.classList.add('reduce-motion')")
                    anim = await page.evaluate("getComputedStyle(document.querySelector('.dc-sheet svg.dc-room .dc-wave')).animationName")
                    expect(anim == 'none', 'still water with reduced motion')
                    await page.evaluate("document.body.classList.remove('reduce-motion')")
                    btn = '.dc-sheet [data-dc="relax"][data-act="boi"]'
                    await page.locator(btn).scroll_into_view_if_needed()
                    await shot('03-pool-relax-card')
                    await page.click(btn)
                    await page.wait_for_timeout(1000)
                    await popups()
                    f = await page.inner_text('.dc-sheet .bk-flash')
                    print(tag, 'swim:', f)
                    expect('🏊' in f and 'tinh thần +3' in f, 'a swim lifts the spirit')
                    expect(await page.locator('.dc-sheet [data-dc="relax"][data-act="nam"][disabled]').count() == 1, 'one moment by the pool a day')
                    await shot('04-after-swim')
                    await page.click('.dc-sheet [data-dc="edit"]')
                    await page.wait_for_timeout(500)
                    await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                    await page.wait_for_timeout(400)
                    await shot('05-pool-shop')
                    await page.click('.dc-sheet [data-dc="done"]')
                    await page.wait_for_timeout(300)
                await page.click('.dc-sheet [data-dc="close"]')
                # ---- a small bathroom (tập thể) and the dorm's shared one (day only)
                if hour < 18:
                    for kind, name in (('tap_the', '06-tapthe-bath'), ('ky_tuc_xa', '07-dorm-shared-bath')):
                        mutate(db, token, move(kind))
                        await reload()
                        await open_inside()
                        got = await tabs()
                        expect('bath' in got, f'{kind} has a bathroom ({got})')
                        await room('bath')
                        await shot(name)
                        await page.click('.dc-sheet [data-dc="close"]')
                await ctx.close()
            await browser.close()
    for e in errors:
        print('console:', e)
    for f in failed:
        print('FAILED:', f)
    print('shots in', OUT)
    sys.exit(1 if errors or failed else 0)


if __name__ == '__main__':
    asyncio.run(main())
