"""🏨 Phòng cho người chơi (game/hotel_stay.py, public/js/v4/hotel-stay.js): a browser walk-through with two real players
(dev tool, needs playwright; Chromium or the installed Chrome: MNL_PW_CHANNEL=chrome).

A throwaway story-mode server. Lan runs a homestay, Minh is her guest. At 390×844: Lan opens 🛏️ Phòng nghỉ qua đêm in
🧰 Dịch vụ của tôi; Minh finds it in 🔎 Phố dịch vụ and books (the price is held); Lan's 🏨 Sổ phòng shows the booking,
she confirms; Minh taps 🧳 Tôi tới rồi; Lan checks him in (his wish, his temperament, the arrival quirk, the room);
the night goes by (the stay's clock is moved in the database): Minh asks for a late check-out, Lan answers the night's
situations, the time is up and she checks him out (the check-out quirk); Minh sees the rest he got and rates her ⭐.
Lan's check-in card again at 844×390 (a second guest, Hoa). JPEG screenshots, console errors.

    TEST_DATABASE_URL=postgresql://… MNL_PW_CHANNEL=chrome python scripts/browser_hotel_stay.py [out_dir]
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if os.environ.get('MNL_PW_SITE'):   # playwright installed in another environment of the same Python (its site-packages)
    sys.path.append(os.environ['MNL_PW_SITE'])
import browser_pet_arena as BPA  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_hotel_stay_shots'

SEED = r'''
import sys, hashlib
from game import accounts
from game import marriage as mr
from game.storage import Store
db, token, name, host = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == '1'
store = Store(db, story=True)
out = accounts.register(store, token, dict(username='u' + hashlib.md5(name.encode()).hexdigest()[:12], password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
def fn(s):
    j = s['journey']
    s['name'] = name
    j.update(gender='female' if name in ('Lan', 'Hoa') else 'male', intro=True, life_day=20, wallet=9000)
    if host:
        s['careers']['homestay']['started'] = True
mr._mutate(store, {sid: fn})
store.close_pool()
print(tok)
'''

SHIFT = r'''
import sys, json
from game.storage import Store
store = Store(sys.argv[1], story=True)
sec = float(sys.argv[2])
def w(d):
    n = 0
    for r in d.execute("SELECT order_id, ev FROM hotel_stays WHERE stage='in'").fetchall():
        ev = json.loads(r['ev'])
        for e in ev:
            e['at'] -= sec
        d.execute('UPDATE hotel_stays SET in_at=in_at-?, due_at=due_at-?, next_at=next_at-?, ev=? WHERE order_id=?',
                  (sec, sec, sec, json.dumps(ev, ensure_ascii=False), r['order_id']))
        n += 1
    return n
print(store.transaction(w))
store.close_pool()
'''


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, shots = [], []
    async with async_playwright() as pw:
        ch = os.environ.get('MNL_PW_CHANNEL')
        browser = await (pw.chromium.launch(channel=ch) if ch else pw.chromium.launch())

        async def context(base, w, h, ip, login=None):
            ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2, has_touch=True, locale='vi-VN',
                                            extra_http_headers={'X-Forwarded-For': ip})
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.ui25d','0');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            if login:
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            return ctx, page

        async def settle(page):
            await page.wait_for_timeout(1500)
            for _ in range(6):
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(300)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        async def player(base, db, env, who, host=False, w=390, h=844, ip='10.0.0.1'):
            ctx, page = await context(base, w, h, ip)
            page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{who}: {m.text}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {e}'))
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            login = BPA.py(SEED, db, token, who, '1' if host else '0', env=env)
            await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await settle(page)
            return ctx, page, login

        async def shot(page, name, keep='.hs-sheet'):
            await page.evaluate(f"document.querySelectorAll('dialog[open]:not({keep})').forEach(d=>d.close())")
            path = OUT / f'{name}.jpg'
            await page.screenshot(path=str(path), type='jpeg', quality=80)
            shots.append(str(path))

        async def market(page, data=None):
            await page.evaluate(BPA.ACT, ['svcMarket', data or {}])
            await page.wait_for_selector('dialog.svc-sheet[open] .sd-body', timeout=10000)
            await page.wait_for_timeout(900)

        async def hotel(page, data=None):
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await page.evaluate(BPA.ACT, ['hotelBook', data or {}])
            await page.wait_for_selector('dialog.hs-sheet[open] .sd-body', timeout=10000)
            await page.wait_for_timeout(1000)

        async def tap(page, sel, wait=900, keep='.hs-sheet'):
            await page.evaluate(f"document.querySelectorAll('dialog[open]:not({keep}):not(.svc-sheet)').forEach(d=>d.close())")
            await page.locator(sel).first.click()
            await page.wait_for_timeout(wait)

        async def scroll_to(page, sel):
            await page.locator(sel).first.scroll_into_view_if_needed()
            await page.wait_for_timeout(250)

        with BPA.server(TRUST_PROXY='1') as (base, db, env):
            lan_ctx, lan, lan_login = await player(base, db, env, 'Lan', True, ip='10.0.0.1')
            minh_ctx, minh, _ = await player(base, db, env, 'Minh', ip='10.0.0.2')
            # Lan opens her rooms in 🧰
            await market(lan, {'tab': 'mine'})
            await tap(lan, 'dialog.svc-sheet [data-svc="set"][data-what="on"][data-id="homestay.stay_night"]', 1200, '.svc-sheet')
            await scroll_to(lan, 'dialog.svc-sheet [data-id="homestay.stay_night"]')
            await shot(lan, '01-lan-rooms-on', '.svc-sheet')
            # Minh books a night
            await market(minh, {'tab': 'dir'})
            await tap(minh, 'dialog.svc-sheet .svc-card[data-service="stay_night"]', 1200, '.svc-sheet')
            await shot(minh, '02-minh-room-card', '.svc-sheet')
            await tap(minh, 'dialog.svc-sheet [data-svc="review"]', 600, '.svc-sheet')
            await tap(minh, 'dialog.svc-sheet [data-svc="buy"]', 1500, '.svc-sheet')
            await shot(minh, '03-minh-inbox-held', '.svc-sheet')
            # Lan's Sổ phòng: the booking
            await hotel(lan)
            await shot(lan, '04-lan-booking')
            await tap(lan, 'dialog.hs-sheet [data-hs="confirm"]', 1500)
            await shot(lan, '05-lan-confirmed')
            # Minh arrives
            await hotel(minh, {'tab': 'guest'})
            await shot(minh, '06-minh-booked')
            await tap(minh, 'dialog.hs-sheet [data-hs="arrive"]', 1500)
            # Lan checks him in
            await lan.evaluate("document.querySelector('dialog.hs-sheet')?.close()")
            await hotel(lan)
            await shot(lan, '07-lan-checkin')
            await tap(lan, 'dialog.hs-sheet [data-hs="quirk"]', 300)
            await tap(lan, 'dialog.hs-sheet [data-hs="room"]:not([disabled])', 300)
            await scroll_to(lan, 'dialog.hs-sheet [data-hs="checkin"]')
            await shot(lan, '08-lan-checkin-picked')
            # the same card in landscape (Lan's account on a phone turned sideways)
            land_ctx, land = await context(base, 844, 390, '10.0.0.1', lan_login)
            await settle(land)
            await hotel(land)
            await scroll_to(land, 'dialog.hs-sheet .hs-ev.open')
            await shot(land, '09-lan-checkin-844x390')
            await scroll_to(land, 'dialog.hs-sheet [data-hs="checkin"]')
            await shot(land, '09b-lan-rooms-844x390')
            await land_ctx.close()
            await tap(lan, 'dialog.hs-sheet [data-hs="checkin"]', 1500)
            # the night goes by (the stay's clock moved back 2 h 50 min): Minh asks, Lan answers
            BPA.py(SHIFT, db, str(170 * 60), env=env)
            await minh.evaluate("document.querySelector('dialog.hs-sheet')?.close()")
            await hotel(minh, {'tab': 'guest'})
            await shot(minh, '10-minh-in-room')
            await tap(minh, 'dialog.hs-sheet [data-hs="ask"][data-ask="late"]', 1500)
            await lan.evaluate("document.querySelector('dialog.hs-sheet')?.close()")
            await hotel(lan)
            await shot(lan, '11-lan-night-situations')
            for _ in range(4):
                b = lan.locator('dialog.hs-sheet [data-hs="handle"]')
                if not await b.count():
                    break
                await b.first.click()
                await lan.wait_for_timeout(1300)
            await shot(lan, '12-lan-handled')
            # time is up (+ the late hour): check-out
            BPA.py(SHIFT, db, str(80 * 60), env=env)
            await lan.evaluate("document.querySelector('dialog.hs-sheet')?.close()")
            await hotel(lan)
            await scroll_to(lan, 'dialog.hs-sheet [data-hs="checkout"]')
            await shot(lan, '13-lan-checkout')
            await tap(lan, 'dialog.hs-sheet [data-hs="checkout"]', 2000)
            await shot(lan, '14-lan-paid')
            # Minh's rest and his rating
            await minh.evaluate("document.querySelector('dialog.hs-sheet')?.close()")
            await hotel(minh, {'tab': 'guest'})
            await shot(minh, '15-minh-rested')
            await tap(minh, 'dialog.hs-sheet [data-hs="star"][data-n="5"]', 300)
            await tap(minh, 'dialog.hs-sheet [data-hs="rate"]', 1500)
            await shot(minh, '16-minh-rated')
            # landscape guest view
            hoa_ctx, hoa, _ = await player(base, db, env, 'Hoa', w=844, h=390, ip='10.0.0.3')
            await hotel(hoa, {'tab': 'guest'})
            await shot(hoa, '17-hoa-empty-844x390')
            await hoa_ctx.close()
            await minh_ctx.close()
            await lan_ctx.close()
        await browser.close()
    print('\n'.join(shots))
    print('console errors:', len(errors))
    for e in errors[:20]:
        print('  ', e)


if __name__ == '__main__':
    asyncio.run(main())
