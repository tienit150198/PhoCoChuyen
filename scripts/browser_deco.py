"""🪴 Bày trí phòng: a browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (as scripts/browser_housing.py) and seeds one save straight in its
database: a named character who bought the old tập thể 24 life days ago, with a sofa and a picture placed the 1.2.0
way (room slots, migrated on the fly). In the browser, at 390x844 and 1280x800:
  1. own home: view, edit mode with the tip, the shop, buy a plant by tapping a lit cell, select it, flip it, drag it,
     put it back in the bag, undo, drag a card up out of the drawer into the room, 📸 the photo, 🛠️ Sửa nhà;
  2. the home is sold and a phòng trọ rented (server side): everything is back in the bag; set up the trọ and the
     gác lửng, by tap and by drag;
  3. the dorm: the bunk corner.
Light theme and "Phố đêm" for the main screens. Exit 1 on any console error.

    python scripts/browser_deco.py [out_dir]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_deco_shots'


def mutate(db: str, token: str, fn) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def seed_own(s):
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
    # the 1.2.0 way: pieces in room slots (deco.layout turns them into grid spots)
    r = rn.ensure_block(s)
    for k, room, slot in (('sofa', 'living', 'f1'), ('tranh', 'living', 'w0'), ('cay_canh', 'living', 'f0')):
        r['items'].append(dict(id=rn.new_uid(r), k=k, r=room, x=slot))
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
    errors = []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (1280, 800)):
                ctx = await browser.new_context(viewport=dict(width=w, height=h))
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                tag = f'{w}x{h}'

                async def popups():
                    for _ in range(4):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            break
                        await b.first.click()
                        await page.wait_for_timeout(400)

                async def reload():
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(1500)
                    await popups()
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

                async def shot(name, full=False):
                    await page.wait_for_timeout(500)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=full)

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

                async def center(sel, last=False):
                    box = await page.evaluate("""([s,last])=>{const l=[...document.querySelectorAll(s)];const e=last?l[l.length-1]:l[0];if(!e)return null;
                        e.scrollIntoView?.({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];}""", [sel, last])
                    assert box, f'nothing at {sel}'
                    return box

                async def flash():
                    return (await page.inner_text('.dc-sheet .bk-flash'))[:160]

                async def open_place(button):
                    await page.wait_for_selector('.jr-house-row', timeout=10000)
                    await page.click('.jr-house-row')
                    await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                    await popups()
                    await page.click(f'.hs-sheet [data-hs="inside"]{button}')
                    await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)

                async def drag(src, dst_sel, name, dy=-24, last=True):
                    x, y = src
                    await page.mouse.move(x, y)
                    await page.mouse.down()
                    await page.mouse.move(x + 2, y + dy, steps=4)
                    await page.wait_for_timeout(250)
                    tx, ty = await center(dst_sel, last)
                    await page.mouse.move(tx, ty, steps=8)
                    await shot(name)
                    print(tag, name, 'ghost:', await page.evaluate("(()=>{const e=document.querySelector('.dc-float');if(!e)return null;const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),getComputedStyle(e).position]})()"))
                    await page.mouse.up()
                    await page.wait_for_timeout(1000)

                async def uids():
                    return await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-it')].map(g=>g.dataset.uid)")

                # ---- 1. a home you own
                mutate(db, token, seed_own)
                await reload()
                await open_place(':not([data-mode])')
                await both('01-own-view')
                await page.click('.dc-sheet [data-dc="edit"]')
                await page.wait_for_selector('.dc-sheet svg.dc-room.edit')
                await shot('02-edit-tip')
                await page.click('.dc-sheet [data-dc="tipOk"]')
                await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await page.click('.dc-sheet .dc-card[data-k="den_cay"]')
                await page.wait_for_selector('.dc-sheet .dc-ok rect')
                await both('03-holding-lamp')
                before = set(await uids())
                await page.mouse.click(*(await center('.dc-sheet .dc-ok rect', last=True)))
                await confirm()
                await page.wait_for_timeout(300)
                await shot('04-bought-pop')
                new = [u for u in await uids() if u not in before]
                print(tag, 'buy:', await flash(), new)
                assert new, 'the lamp is not in the room'
                lamp = new[0]
                await page.wait_for_selector('.dc-sheet .dc-tools')   # a piece just placed is selected
                await shot('05-selected')
                await page.click('.dc-sheet [data-dc="flip"]')
                await page.wait_for_timeout(600)
                print(tag, 'flip:', await flash())
                await drag(await center(f'.dc-sheet .dc-it[data-uid="{lamp}"] .dc-hit'), '.dc-sheet .dc-ok rect', '06-dragging', dy=12, last=False)
                print(tag, 'drag:', await flash())
                await page.click('.dc-sheet [data-dc="pick"]')   # still selected after the drag
                await page.wait_for_timeout(700)
                print(tag, 'pick:', await flash())
                await page.click('.dc-sheet [data-dc="drawer"][data-d="bag"]')
                await shot('07-in-bag')
                await page.click('.dc-sheet [data-dc="undo"]')
                await page.wait_for_timeout(700)
                print(tag, 'undo:', await flash())
                assert lamp in await uids(), 'undo did not put the lamp back'
                # buy two plants to the bag, drag one up out of the drawer
                await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await page.click('.dc-sheet .dc-card[data-k="cay_monstera"]')
                await page.click('.dc-sheet [data-dc="buyBag"]')
                await confirm()
                await page.click('.dc-sheet [data-dc="unhold"]')
                await page.click('.dc-sheet [data-dc="drawer"][data-d="bag"]')
                await shot('08-bag')
                before = set(await uids())
                await drag(await center('.dc-sheet .dc-card[data-k="cay_monstera"]'), '.dc-sheet .dc-ok rect', '09-drag-from-bag')
                print(tag, 'drop from bag:', await flash())
                assert set(await uids()) - before, 'the plant did not land'
                # the kitchen, Ấm cúng card
                await page.click('.dc-sheet [data-dc="room"][data-room="kitchen"]')
                await both('10-kitchen-edit')
                await page.click('.dc-sheet [data-dc="done"]')
                await page.click('.dc-sheet [data-dc="room"][data-room="living"]')
                await both('11-living-done')
                await shot('11b-full', full=True)
                await page.click('.dc-sheet [data-dc="photo"]')
                await page.wait_for_selector('.dc-sheet .dc-photo img', timeout=10000)
                await shot('12-photo')
                await page.click('.dc-sheet [data-dc="photoClose"]')
                await page.click('.dc-sheet [data-dc="tab"][data-tab="fix"]')
                await page.wait_for_selector('.dc-sheet .rn-parts')
                await both('13-fix')
                await page.click('.dc-sheet [data-dc="close"]')

                # ---- 2. sold the home, renting the phòng trọ: everything is in the bag
                mutate(db, token, move_to('tro_moi'))
                await reload()
                await open_place('')
                await page.wait_for_selector('.dc-sheet svg.dc-room')
                await page.click('.dc-sheet [data-dc="edit"]')
                n = await page.evaluate("document.querySelectorAll('.dc-sheet .dc-card[data-src=bag]').length")
                print(tag, 'tro bag kinds:', n, 'placed:', len(await uids()))
                assert n >= 4 and not await uids(), 'moving did not put things in the bag'
                await both('14-tro-bag')
                for k in ('den_cay', 'cay_monstera', 'tranh'):
                    if await page.locator(f'.dc-sheet .dc-card[data-k="{k}"]:not([disabled])').count():
                        if not await page.locator(f'.dc-sheet .dc-card.on[data-k="{k}"]').count():
                            await page.click(f'.dc-sheet .dc-card[data-k="{k}"]')
                        await page.wait_for_selector(f'.dc-sheet .dc-card.on[data-k="{k}"]')
                        await page.mouse.click(*(await center('.dc-sheet .dc-ok rect')))
                        await page.wait_for_timeout(700)
                        print(tag, k, await flash())
                await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await page.click('.dc-sheet .dc-card[data-k="ban_hoc"]')
                await page.mouse.click(*(await center('.dc-sheet .dc-ok rect')))
                await confirm()
                await page.click('.dc-sheet .dc-card[data-k="den_ban"]')
                await page.wait_for_selector('.dc-sheet .dc-ok circle')
                await shot('15-tro-lamp-on-desk')
                await page.mouse.click(*(await center('.dc-sheet .dc-ok circle')))
                await confirm()
                print(tag, 'desk lamp:', await flash())
                await page.click('.dc-sheet [data-dc="done"]')
                await both('16-tro-done')
                await page.click('.dc-sheet [data-dc="room"][data-room="loft"]')
                await page.click('.dc-sheet [data-dc="edit"]')
                await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await page.click('.dc-sheet .dc-card[data-k="nem"]')
                await page.mouse.click(*(await center('.dc-sheet .dc-ok rect')))
                await confirm()
                await page.click('.dc-sheet [data-dc="done"]')
                await both('17-loft')
                await page.click('.dc-sheet [data-dc="close"]')

                # ---- 3. the dorm: the bunk corner
                mutate(db, token, move_to('ky_tuc_xa'))
                await reload()
                await open_place('')
                await page.click('.dc-sheet [data-dc="edit"]')
                await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await page.click('.dc-sheet .dc-card[data-k="rem_giuong"]')
                await page.mouse.click(*(await center('.dc-sheet .dc-ok rect', last=True)))
                await confirm()
                await page.click('.dc-sheet [data-dc="drawer"][data-d="bag"]')
                if await page.locator('.dc-sheet .dc-card[data-k="den_cay"]:not([disabled])').count():
                    await page.click('.dc-sheet .dc-card[data-k="den_cay"]')
                    await shot('18-dorm-holding')
                    await page.click('.dc-sheet [data-dc="unhold"]')
                await page.click('.dc-sheet [data-dc="done"]')
                await both('19-dorm')
                await page.click('.dc-sheet [data-dc="back"]')
                await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                await shot('20-house-card')
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
