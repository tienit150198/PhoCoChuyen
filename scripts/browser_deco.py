"""🪴 Bày trí phòng: a browser walk-through with real drags (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (as scripts/browser_housing.py) and seeds one save straight in its
database: a named character who bought the old tập thể 24 life days ago and set it up in 1.3.2 (a grid layout in
journey.deco, no journey.decor: it converts on load). In the browser, at 390x844 and 1280x800 (pointer down, move in
steps, up, like a finger):
  1. own home: the converted room; drag the sofa, drag the coffee table (its lamp rides along), drag a vase up out of
     the shop onto the table, flip, bring a picture forward, a free wallpaper and a bought one, undo, the cats, the
     photo, 🛠️ Sửa nhà;
  2. the home is sold and a phòng trọ rented (server side): everything is in the bag; drag a rug, the sofa onto it,
     a table and a lamp onto the table, then the gác lửng;
  3. the dorm: the bunk corner (curtain on the wall, teddy on the pillow, a night light on the shelf, sheets).
Light theme and "Phố đêm"; the day shots at 10:00 local, then a night pass at 21:00. Exit 1 on any console error or
a failed step.

    python scripts/browser_deco.py [out_dir]
"""
import asyncio
import datetime as dt
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_decofree_shots'


def tz_for(hour: int) -> str:
    """An Etc/GMT zone where the local time is about `hour` o'clock now."""
    off = (hour - dt.datetime.now(dt.timezone.utc).hour + 12) % 24 - 12
    return 'UTC' if off == 0 else f'Etc/GMT{"-" if off > 0 else "+"}{abs(off)}'


def mutate(db: str, token: str, fn) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def seed_own(s):
    from game import deco as dc
    from game import housing as hs
    from game import journey as jr
    from game import reno as rn
    from game import whats_new as wn
    j = s['journey']
    s['name'] = 'Lan'
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    j.update(gender='female', intro=True, life_day=6, wallet=5000)
    hs.apply(s, 'jr_home_buy', {'kind': 'tap_the', 'down': 1800, 'confirm': True})
    for d in range(7, 31):
        j['life_day'] = d
        jr._wallet(j, 60, 'salary', f'Lương ngày {d}')
        hs.on_life_day(s)
    # the 1.3.2 way: a grid layout in journey.deco (deco.layout converts it to free units)
    r = rn.ensure_block(s)
    ids = {}
    for k in ('tham', 'sofa', 'tranh', 'anh', 'ban_tra', 'den_ban', 'cay_canh'):
        ids[k] = rn.new_uid(r)
        r['items'].append(dict(id=ids[k], k=k, r=None, x=None))
    d = j['deco'] = dc.blank(j['life_day'], dc.place(j)['key'])
    d['pos'] = {ids['tham']: ['living', 0, 1, 0], ids['sofa']: ['living', 0, 1, 0], ids['tranh']: ['living', 3, 0, 0],
                ids['anh']: ['living', 4, 1, 0], ids['ban_tra']: ['living', 3, 2, 0], ids['den_ban']: ['living', 4, 2, 0],
                ids['cay_canh']: ['living', 5, 1, 0]}
    j['wallet'] = max(j['wallet'], 4000)


def move_to(kind):
    def fn(s):
        from game import housing as hs
        j = s['journey']
        h = hs.get(s)
        if h['own']:
            hs.apply(s, 'jr_home_sell', {'confirm': True, 'value': hs.value_of(h['own'], j['life_day'])})
        j['wallet'] = max(j['wallet'], 6000)
        hs.apply(s, 'jr_home_rent', {'kind': kind, 'confirm': True})
    return fn


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, failed = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h, hour, full in ((390, 844, 10, True), (1280, 800, 10, True), (390, 844, 21, False), (1280, 800, 21, False)):
                if os.environ.get('DECO_ONLY') and os.environ['DECO_ONLY'] != str(w):
                    continue
                ctx = await browser.new_context(viewport=dict(width=w, height=h), timezone_id=tz_for(hour), has_touch=w < 500)
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','9.9.9')}catch(e){}")
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
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, button:has-text("Đã hiểu"):visible')
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

                async def shot(name, fullpage=False):
                    await page.wait_for_timeout(450)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=fullpage)

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(900)
                    await popups()

                async def theme(name):
                    await page.evaluate(f"document.documentElement.dataset.theme='{name}'")

                async def both(name):
                    for th in ('kem', 'dem'):
                        await theme(th)
                        await shot(f'{name}-{th}')
                    await theme('kem')

                async def box(sel, scroll=False):
                    b = await page.evaluate("""([s,scroll])=>{const e=document.querySelector(s);if(!e)return null;if(scroll)e.scrollIntoView({block:'center'});
                        const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height];}""", [sel, scroll])
                    if not b:
                        await page.screenshot(path=str(OUT / f'{tag}-FAIL.png'))
                    assert b, f'nothing at {sel}'
                    return b

                async def tap(sel, wait=500):
                    await popups()
                    try:
                        await page.click(sel, timeout=8000)
                    except Exception:
                        await page.screenshot(path=str(OUT / f'{tag}-FAIL.png'))
                        print('  ✗ could not tap', sel, await page.evaluate("[...document.querySelectorAll('dialog[open]')].map(d=>d.id||d.className)"))
                        raise
                    await page.wait_for_timeout(wait)
                    await popups()

                async def flash():
                    return (await page.inner_text('.dc-sheet .bk-flash'))[:170]

                async def open_place(button):
                    await page.wait_for_selector('.jr-house-row', timeout=10000)
                    await page.click('.jr-house-row')
                    await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                    await popups()
                    await page.click(f'.hs-sheet [data-hs="inside"]{button}')
                    await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)

                async def room_top():
                    await page.evaluate("""()=>{const w=document.querySelector('.dc-sheet .dc-roomwrap'),h=document.querySelector('.dc-sheet .sheet-head');if(!w)return;
                        w.scrollIntoView({block:'start'});let s=w.parentElement;while(s&&s.scrollHeight<=s.clientHeight+2)s=s.parentElement;
                        if(s&&h)s.scrollBy(0,-(h.getBoundingClientRect().bottom-s.getBoundingClientRect().top)-8);}""")
                    await page.wait_for_timeout(250)

                async def finger(x0, y0, x1, y1, name=None, lift=0):
                    """Press at (x0, y0), move like a finger to (x1, y1) (first `lift` px straight up), release."""
                    await page.mouse.move(x0, y0)
                    await page.mouse.down()
                    if lift:
                        await page.mouse.move(x0, y0 - lift, steps=5)
                    await page.mouse.move(x1, y1, steps=14)
                    await page.wait_for_timeout(120)
                    if name:
                        await shot(name)
                    await page.mouse.up()
                    await page.wait_for_timeout(1100)
                    await popups()

                async def drag_piece(k, dx, dy, name=None):
                    l, t, bw, bh = await box(f'.dc-sheet .dc-it[data-k="{k}"] .dc-hit')
                    x, y = l + bw / 2, t + bh * .6
                    await finger(x, y, x + dx, y + dy, name)

                async def drag_card(k, target, name=None):
                    """Drag a drawer card up into the room; `target` (x, y): where the piece's base should land."""
                    await page.evaluate(f"document.querySelector('.dc-sheet .dc-buycard[data-k=\"{k}\"]')?.scrollIntoView({{block:'nearest',inline:'center'}})")
                    await room_top()
                    l, t, bw, bh = await box(f'.dc-sheet .dc-buycard[data-k="{k}"]')
                    if t + 70 > h:   # the card is below the fold: scroll just enough to grab it, as a thumb would
                        await page.evaluate("""(dy)=>{let s=document.querySelector('.dc-sheet .dc-roomwrap').parentElement;
                            while(s&&s.scrollHeight<=s.clientHeight+2)s=s.parentElement;if(s)s.scrollBy(0,dy);}""", t + 80 - h)
                        await page.wait_for_timeout(150)
                        l, t, bw, bh = await box(f'.dc-sheet .dc-buycard[data-k="{k}"]')
                    if callable(target):
                        target = await target()
                    await finger(l + bw / 2, min(t + bh / 2, h - 30), target[0], target[1] + 4, name, lift=40)

                async def top_of(k):
                    l, t, bw, bh = await box(f'.dc-sheet .dc-it[data-k="{k}"] .dc-hit')
                    return l + bw / 2, t + 7

                def at(fx, fy):
                    async def go():
                        l, t, rw, rh = await box('.dc-sheet svg.dc-room')
                        return l + rw * fx, t + rh * fy
                    return go

                async def ons():
                    return await page.evaluate("Object.fromEntries([...document.querySelectorAll('.dc-sheet .dc-it[data-on]')].map(g=>[g.dataset.k,g.dataset.on]))")

                async def kinds():
                    return await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-it[data-uid]')].map(g=>g.dataset.k)")

                # ---- 1. a home you own (set up in 1.3.2: converted on load)
                mutate(db, token, seed_own)
                await reload()
                await open_place(':not([data-mode])')
                got = sorted(await kinds())
                print(tag, 'converted:', got, await ons())
                expect(got == sorted(['tham', 'sofa', 'tranh', 'anh', 'ban_tra', 'den_ban', 'cay_canh']), 'every 1.3.2 piece is placed after the conversion')
                expect((await ons()).get('den_ban'), 'the lamp stands on the coffee table')
                await both('01-own-view')
                if not full:
                    await page.wait_for_timeout(5000)
                    await both('02-own-cats')
                    await tap('.dc-sheet [data-dc="close"]')
                    await ctx.close()
                    continue
                await tap('.dc-sheet [data-dc="edit"]')
                await page.wait_for_selector('.dc-sheet svg.dc-room.edit')
                await shot('02-edit-tip')
                await tap('.dc-sheet [data-dc="tipOk"]')
                await room_top()
                await drag_piece('sofa', 46, 14, '03-dragging-sofa')
                f = await flash()
                print(tag, 'sofa:', f)
                expect('Đã dời sofa' in f, 'drag the sofa')
                await drag_piece('ban_tra', -70, 18, '04-dragging-table')
                f = await flash()
                print(tag, 'table:', f)
                expect('Đèn bàn đi theo' in f and (await ons()).get('den_ban'), 'the lamp rides along with the table')
                await tap('.dc-sheet [data-dc="drawer"][data-d="shop"]', 300)
                await drag_card('binh_hoa', lambda: top_of('ban_tra'), '05-dragging-vase')
                await confirm()
                f = await flash()
                print(tag, 'vase:', f, await ons())
                expect('binh_hoa' in await ons(), 'the vase landed on the table')
                await shot('06-vase-on-table')
                # a piece's tools: flip, forward
                l, t, bw, bh = await box('.dc-sheet .dc-it[data-k="tranh"] .dc-hit', scroll=True)
                await page.mouse.click(l + bw / 2, t + bh / 2)
                await page.wait_for_selector('.dc-sheet .dc-tools')
                await shot('07-selected')
                await tap('.dc-sheet [data-dc="zup"]', 700)
                print(tag, 'zup:', await flash())
                await tap('.dc-sheet [data-dc="flip"]', 700)
                f = await flash()
                print(tag, 'flip:', f)
                expect('Đã lật' in f, 'flip')
                await tap('.dc-sheet [data-dc="undo"]', 700)
                print(tag, 'undo:', await flash())
                # 🎨 walls and floors
                await tap('.dc-sheet [data-dc="drawer"][data-d="skin"]', 300)
                await tap('.dc-sheet [data-dc="skin"][data-part="wall"][data-skin="bac_ha"]', 700)
                f = await flash()
                print(tag, 'paint:', f)
                expect('bạc hà' in f, 'a free paint')
                await tap('.dc-sheet [data-dc="skin"][data-part="wall"][data-skin="hoa_nhi"]', 400)
                await shot('08-trying-wallpaper')
                await confirm()
                f = await flash()
                print(tag, 'paper:', f)
                expect('hoa nhí' in f, 'buy a wallpaper')
                await tap('.dc-sheet [data-dc="skin"][data-part="floor"][data-skin="go_sang"]', 700)
                await room_top()
                await both('09-skins')
                await tap('.dc-sheet [data-dc="done"]', 5500)   # the cats wander
                await both('10-living-done')
                await shot('10b-full', fullpage=True)
                await tap('.dc-sheet [data-dc="photo"]')
                await page.wait_for_selector('.dc-sheet .dc-photo img', timeout=10000)
                await shot('11-photo')
                await tap('.dc-sheet [data-dc="photoClose"]')
                await tap('.dc-sheet [data-dc="tab"][data-tab="fix"]')
                await page.wait_for_selector('.dc-sheet .rn-parts')
                await shot('12-fix')
                await tap('.dc-sheet [data-dc="close"]')

                # ---- 2. sold the home, renting the phòng trọ: everything is in the bag
                mutate(db, token, move_to('tro_moi'))
                await reload()
                await open_place('')
                await tap('.dc-sheet [data-dc="edit"]')
                n = await page.evaluate("document.querySelectorAll('.dc-sheet .dc-buycard[data-src=bag]').length")
                print(tag, 'tro bag kinds:', n, 'placed:', len(await kinds()))
                expect(n >= 6 and not await kinds(), 'moving put everything in the bag')
                await room_top()
                l, t, rw, rh = await box('.dc-sheet svg.dc-room')
                await drag_card('tham', at(.42, .9), '13-tro-drag-rug')
                await drag_card('sofa', at(.45, .86))
                await drag_card('ban_tra', at(.2, .95))
                await drag_card('den_ban', lambda: top_of('ban_tra'))
                print(tag, 'tro:', await kinds(), await ons(), await flash())
                expect({'tham', 'sofa', 'ban_tra', 'den_ban'} <= set(await kinds()) and 'den_ban' in await ons(), 'set up the trọ by dragging')
                await tap('.dc-sheet [data-dc="drawer"][data-d="skin"]')
                await tap('.dc-sheet [data-dc="skin"][data-part="floor"][data-skin="gach_trang"]', 600)
                await tap('.dc-sheet [data-dc="done"]', 4000)
                await both('14-tro-done')
                await tap('.dc-sheet [data-dc="room"][data-room="loft"]')
                await tap('.dc-sheet [data-dc="edit"]')
                await tap('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await room_top()
                l, t, rw, rh = await box('.dc-sheet svg.dc-room')
                await drag_card('nem', at(.4, .74))
                await confirm()
                print(tag, 'loft nem:', await flash())
                await drag_card('gau_bong', lambda: top_of('nem'))
                await confirm()
                print(tag, 'loft:', await kinds(), await ons(), await flash())
                expect('nem' in await kinds(), 'a mattress in the loft')
                await tap('.dc-sheet [data-dc="done"]', 3000)
                await both('15-loft')
                await tap('.dc-sheet [data-dc="close"]')

                # ---- 3. the dorm: the bunk corner
                mutate(db, token, move_to('ky_tuc_xa'))
                await reload()
                await open_place('')
                await tap('.dc-sheet [data-dc="edit"]')
                await tap('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await room_top()
                l, t, rw, rh = await box('.dc-sheet svg.dc-room')
                await drag_card('rem_giuong', at(.86, .62), '16-dorm-drag-curtain')
                await confirm()
                await drag_card('den_ngu', at(.16, .3))   # onto the shelf over the pillow
                await confirm()
                await drag_card('poster', at(.55, .62))
                await confirm()
                pl = await box('.dc-sheet svg.dc-room')
                await drag_card('gau_bong', at(.1, .66))   # onto the pillow
                await confirm()
                print(tag, 'dorm:', await kinds(), await ons(), await flash())
                expect({'rem_giuong', 'den_ngu', 'poster'} <= set(await kinds()), 'curtain, night light, poster in the bunk corner')
                expect((await ons()).get('den_ngu') == '#shelf', 'the night light stands on the bunk shelf')
                expect((await ons()).get('gau_bong') == '#pillow', 'the teddy sits on the pillow')
                await tap('.dc-sheet [data-dc="drawer"][data-d="skin"]')
                await tap('.dc-sheet [data-dc="skin"][data-part="floor"][data-skin="ga_ke"]', 600)
                expect(not await page.locator('.dc-sheet [data-dc="skin"][data-part="wall"]').count(), 'a dorm bed has no walls to paint')
                await tap('.dc-sheet [data-dc="skin"][data-part="floor"][data-skin="ga_meo"]', 400)
                await confirm()
                print(tag, 'sheets:', await flash())
                await shot('17-dorm-edit')
                await tap('.dc-sheet [data-dc="done"]', 4000)
                await both('18-dorm')
                await tap('.dc-sheet [data-dc="back"]')
                await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                await shot('19-house-card')
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('failed steps:', failed or 'none')
    print('shots:', OUT)
    return 1 if real or failed else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
