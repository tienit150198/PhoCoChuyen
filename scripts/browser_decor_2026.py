"""🛋️ Thêm đồ trang trí (21/10/2026): a browser look at the new pieces on a phone (dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save straight in its database: a character who owns
Biệt thự vườn Đà Lạt's little sister (biet_thu_vuon) with money to spend. At 390x844: the shop with its 🔎 search,
🆕 Mới về and style chips, buying and placing a piece with 📍 Đặt nhanh (no drag: góp ý #443) after checking every
spot button has a screen-reader name, then finishing the 🏯 Gian nhà xưa set the same way and looking at it in the
2D drawing and the 3D view. Screenshots to the out dir; exit 1 on a console error or a failed step.

    python scripts/browser_decor_2026.py [out_dir]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_deco import mutate, tz_for  # noqa: E402
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_decor_2026_shots'


def put(s, k, room='living'):
    """Buy `k` and set it down in the first free spot of `room`, by the server's own rules (left to right, back to front)."""
    from game import deco as dc
    L = dc.layout(s)
    rm = next(r for r in L['rooms'] if r['id'] == room)
    z = dc.zone(rm, k)
    for y in range(0, z[1] + 1, 10):
        for x in range(0, z[0] + 1, 10):
            q = dict(r=room, x=x, y=y, f=0)
            if not dc.check(rm, k, q, L['pos'], L['kinds']):
                return dc.apply(s, 'jr_deco_buy', dict(item=k, confirm=True, put=dict(r=room, x=x, y=y)))['uid']
    raise SystemExit(f'no room for {k}')


def seed(s):
    from game import housing as hs
    from game import journey as jr
    from game import whats_new as wn
    j = s['journey']
    s['name'] = 'Lan'
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    j.update(gender='female', intro=True, life_day=8, wallet=60000)
    j['life']['spirit'] = 55
    hs.apply(s, 'jr_home_buy', {'kind': 'biet_thu_vuon', 'down': 36000, 'confirm': True})
    jr._wallet(j, 20000, 'salary', 'Lương')
    put(s, 'sap_gu')          # two of the three pieces of 🏯 Gian nhà xưa; the third is placed in the browser
    put(s, 'tu_che')
    put(s, 'chieu_hoa')
    put(s, 'den_hoi_an')
    put(s, 'non_la')
    put(s, 'cay_bang_sing')
    put(s, 'hon_non_bo')


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, failed = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844), timezone_id=tz_for(10), has_touch=True)
            await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.decoTip2','1')}catch(e){}")
            page = await ctx.new_page()
            # 🎨 the friends' change log (GET /api/home-guests/deco/log) wants a signed-in account and answers this guest 401;
            # reno.js shrugs it off (no card), so that one 401 is expected here. Any other console error fails the run.
            known = []
            page.on('response', lambda r: r.status == 401 and r.url.endswith('/api/home-guests/deco/log') and known.append(r.url))
            page.on('console', lambda m: m.type == 'error' and not (known and '401' in m.text) and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')

            def expect(ok, what):
                print('  ✓' if ok else '  ✗', what)
                if not ok:
                    failed.append(what)

            async def popups():
                for _ in range(4):
                    b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, button:has-text("Đã hiểu"):visible, button:has-text("Tuyệt!"):visible')
                    if not await b.count():
                        break
                    await b.first.click()
                    await page.wait_for_timeout(400)

            async def shot(name, sel=None):
                await page.wait_for_timeout(500)
                if sel:
                    await page.locator(sel).first.scroll_into_view_if_needed()
                    await page.wait_for_timeout(200)
                await page.screenshot(path=str(OUT / f'390x844-{name}.png'))

            async def confirm():
                await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                await page.click('#confirmDialog [data-action="confirmYes"]')
                await page.wait_for_timeout(900)

            mutate(db, token, seed)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await page.wait_for_timeout(1500)
            await popups()
            await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
            if not await page.locator('.jr-house-row:visible').count():   # the town map comes first: the journey card is under 💼 Công việc
                await page.get_by_role('button', name='Công việc').first.click()
                await page.wait_for_timeout(800)
            await page.wait_for_selector('.jr-house-row', timeout=10000)
            await page.click('.jr-house-row')
            await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
            await popups()
            await page.click('.hs-sheet [data-hs="inside"]:not([data-mode])')
            await page.wait_for_selector('.dc-sheet[open] .dc-stage', timeout=10000)
            await page.wait_for_timeout(800)
            await page.click('.dc-sheet [data-dc="view3d"][data-mode="2d"]')
            await page.wait_for_selector('.dc-sheet svg.dc-room[data-room="living"]', timeout=8000)
            await shot('01-living-2d')

            # ---- the shop: search, 🆕 Mới về, styles
            await page.click('.dc-sheet [data-dc="edit"]')
            await page.wait_for_timeout(500)
            await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
            await page.wait_for_timeout(500)
            n_all = await page.locator('.dc-sheet .dc-strip [data-dc="hold"]').count()
            expect(n_all > 150, f'the shop lists the whole catalogue for this home ({n_all})')
            expect(await page.locator('.dc-sheet [data-dc-search]').count() == 1, 'a search field')
            await shot('02-shop', '.dc-sheet .dc-drawer')
            await page.click('.dc-sheet [data-dc="cat"][data-cat="new"]')
            await page.wait_for_timeout(400)
            n_new = await page.locator('.dc-sheet .dc-strip [data-dc="hold"]').count()
            expect(40 <= n_new <= 60, f'🆕 Mới về shows the new pieces ({n_new})')
            await shot('03-shop-new', '.dc-sheet .dc-drawer')
            await page.click('.dc-sheet [data-dc="style"][data-style="viet"]')
            await page.wait_for_timeout(400)
            ks = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-strip [data-dc=\"hold\"]')].map(b=>b.dataset.k)")
            expect(ks and 'tu_che' in ks and 'sofa_goc' not in ks, f'the 🏮 Nét Việt xưa style ({len(ks)} new pieces)')
            await shot('04-shop-new-viet', '.dc-sheet .dc-drawer')
            await page.click('.dc-sheet [data-dc="cat"][data-cat=""]')
            await page.click('.dc-sheet [data-dc="style"][data-style="viet"]')   # off again
            await page.wait_for_timeout(300)
            await page.fill('.dc-sheet [data-dc-search]', 'den long')
            await page.wait_for_timeout(700)
            ks = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-strip [data-dc=\"hold\"]')].map(b=>b.dataset.k)")
            expect('den_hoi_an' in ks and 'den_long' in ks and len(ks) < 12, f'🔎 "den long" finds the lanterns, marks or not ({ks})')
            focused = await page.evaluate("document.activeElement?.matches?.('[data-dc-search]')")
            expect(focused, 'the search field keeps its focus while the cards follow')
            await shot('05-shop-search', '.dc-sheet .dc-drawer')
            await page.fill('.dc-sheet [data-dc-search]', '')
            await page.wait_for_timeout(500)

            # ---- 📍 Đặt nhanh: tap a card, then a named spot (no drag)
            await page.fill('.dc-sheet [data-dc-search]', 'chum den')
            await page.wait_for_timeout(600)
            await page.click('.dc-sheet [data-dc="hold"][data-k="chum_den_hoi_an"]')
            await page.wait_for_selector('.dc-sheet .dc-spots [data-dc="spot"]', timeout=5000)
            labels = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-spots [data-dc=\"spot\"]')].map(b=>b.getAttribute('aria-label'))")
            expect(len(labels) >= 2 and all(l and 'Chùm đèn lồng Hội An'.lower() in l.lower() for l in labels), f'every spot has a screen-reader name ({labels})')
            group = await page.get_attribute('.dc-sheet .dc-spots', 'role')
            expect(group == 'group', 'the spots are one named group')
            await shot('06-held-quick-spots', '.dc-sheet .dc-held')
            await page.locator('.dc-sheet .dc-spots [data-dc="spot"]').first.focus()
            await page.keyboard.press('Enter')                                  # a keyboard / screen reader press
            await confirm()
            n = await page.locator('.dc-sheet svg.dc-room g.dc-it[data-k="chum_den_hoi_an"]').count()
            expect(n == 1, 'the lantern string hangs in the living room')
            await popups()                                                      # 🏅 new titles may pop up over the sheet
            await shot('07-placed-lanterns')
            if not await page.locator('.dc-sheet [data-dc-search]:visible').count():
                await page.keyboard.press('Escape')                             # the new piece is picked: let go of it, back to the shop
                await page.wait_for_timeout(400)

            # ---- finish 🏯 Gian nhà xưa with the third piece, the same way
            expect(await page.locator('.dc-sheet[open]').count() == 1, 'Esc lets go of the piece, the sheet stays open')
            await page.fill('.dc-sheet [data-dc-search]', 'binh phong')
            await page.wait_for_timeout(600)
            await page.click('.dc-sheet [data-dc="hold"][data-k="binh_phong"]')
            await page.wait_for_selector('.dc-sheet .dc-spots [data-dc="spot"]', timeout=5000)
            await page.locator('.dc-sheet .dc-spots [data-dc="spot"]').last.click()
            await confirm()
            await popups()
            flash = await page.evaluate("document.querySelector('.dc-sheet .bk-flash')?.innerText||''")
            expect('Gian nhà xưa' in flash, f'the set is announced ({flash!r})')
            done = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-sets li.done b')].map(b=>b.innerText)")
            expect('Gian nhà xưa' in done, f'🏅 the set card shows it done ({done})')
            await page.click('.dc-sheet [data-dc="done"]')
            await page.wait_for_timeout(500)
            await shot('08-set-done-2d')
            await shot('09-set-card', '.dc-sheet .dc-sets-card')
            await page.click('.dc-sheet [data-dc="view3d"][data-mode="3d"]')
            await page.wait_for_timeout(2500)
            await shot('10-set-done-3d', '.dc-sheet .dc-stage')
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
