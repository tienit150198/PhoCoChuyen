"""🛎️ Phố dịch vụ (game/service_market.py, public/js/v4/service-market.js): a browser walk-through with two real players
(dev tool, needs playwright; Chromium or the installed Chrome: MNL_PW_CHANNEL=chrome).

A throwaway story-mode server (MNL_SVC_DEMO=1 adds one generic service, 🧋 Pha trà tại nhà, to the legacy ones). Lan
(milk tea) and Minh register and start a day. At 390×844: Lan's 🧰 Dịch vụ của tôi (switches, ×3, 🤝 thương lượng), she
opens her legacy order ×3 and the tea service as thương lượng; Minh's 🔎 directory, Lan's card, his offer and its
confirmation; Lan's 📥 inbox with the offer, her counter; Minh accepts (the money is held); Lan does the work (Xong
việc); Minh confirms and rates ⭐; Lan's reputation; the directory at 844×390. JPEG screenshots, console errors.

    TEST_DATABASE_URL=postgresql://… MNL_PW_CHANNEL=chrome python scripts/browser_service_market.py [out_dir]
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_pet_arena as BPA  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_service_market_shots'

SEED = r'''
import sys, hashlib
from game import accounts
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
    j.update(gender='female' if name == 'Lan' else 'male', intro=True, life_day=20, wallet=90000)
mr._mutate(store, {sid: fn})
rev = store.read(tok)[1]
store.command(tok, 'seed-a-' + name, rev, 'milk_tea', 'select_career', {})
rev = store.read(tok)[1]
store.command(tok, 'seed-b-' + name, rev, 'milk_tea', 'start_day', {})
store.close_pool()
print(tok)
'''


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, shots = [], []
    async with async_playwright() as pw:
        ch = os.environ.get('MNL_PW_CHANNEL')
        browser = await (pw.chromium.launch(channel=ch) if ch else pw.chromium.launch())

        async def player(base, db, env, who, w=390, h=844, ip='10.0.0.1'):
            # each player on a network of their own (TRUST_PROXY: X-Forwarded-For); one network never trades with itself
            ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2, has_touch=True, locale='vi-VN',
                                            extra_http_headers={'X-Forwarded-For': ip})
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.ui25d','0');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{who}: {m.text}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {e}'))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            login = BPA.py(SEED, db, token, who, env=env)
            await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1500)
            for _ in range(6):
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(300)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            return ctx, page

        async def shot(page, name):
            await page.evaluate("document.querySelectorAll('dialog[open]:not(.svc-sheet)').forEach(d=>d.close())")
            path = OUT / f'{name}.jpg'
            await page.screenshot(path=str(path), type='jpeg', quality=80)
            shots.append(str(path))

        async def market(page, data=None):
            await page.evaluate(BPA.ACT, ['svcMarket', data or {}])
            await page.wait_for_selector('dialog.svc-sheet[open] .sd-body', timeout=10000)
            await page.wait_for_timeout(900)

        async def tap(page, sel, wait=900):
            # a life scene (lfScene) or a career sheet may pop up over the market: close it, keep the market
            await page.evaluate("document.querySelectorAll('dialog[open]:not(.svc-sheet)').forEach(d=>d.close())")
            await page.locator(sel).first.click()
            await page.wait_for_timeout(wait)

        with BPA.server(MNL_SVC_DEMO='1', TRUST_PROXY='1') as (base, db, env):
            lan_ctx, lan = await player(base, db, env, 'Lan', ip='10.0.0.1')
            minh_ctx, minh = await player(base, db, env, 'Minh', ip='10.0.0.2')
            # Lan opens her services
            await market(lan, {'tab': 'mine'})
            await shot(lan, '01-lan-mine')
            await tap(lan, 'dialog.svc-sheet [data-svc="set"][data-what="on"][data-id="milk_tea.job"]')
            await tap(lan, 'dialog.svc-sheet [data-svc="set"][data-what="mode"][data-mode="nego"][data-id="milk_tea.tra_tai_nha"]', 300)
            await tap(lan, 'dialog.svc-sheet [data-svc="set"][data-what="on"][data-id="milk_tea.tra_tai_nha"]')
            await shot(lan, '02-lan-mine-on')
            # Minh finds her
            await market(minh)
            await shot(minh, '03-minh-directory')
            await tap(minh, 'dialog.svc-sheet .svc-card[data-service="tra_tai_nha"]')
            await minh.fill('dialog.svc-sheet input[data-f="price"]', '1500')
            await minh.wait_for_timeout(200)
            await minh.fill('dialog.svc-sheet input[data-f="note"]', 'Tối nay 8 giờ nhé!')
            await minh.locator('dialog.svc-sheet input[data-f="note"]').dispatch_event('change')
            await minh.wait_for_timeout(300)
            await shot(minh, '04-minh-offer')
            await tap(minh, 'dialog.svc-sheet [data-svc="review"]')
            await shot(minh, '05-minh-confirm')
            await tap(minh, 'dialog.svc-sheet [data-svc="buy"]', 1500)
            await shot(minh, '06-minh-inbox-talk')
            # Lan counters
            await tap(lan, 'dialog.svc-sheet [data-svc="tab"][data-tab="inbox"]', 1200)
            await shot(lan, '07-lan-inbox-offer')
            await tap(lan, 'dialog.svc-sheet [data-svc="do"][data-action="counter"]', 400)
            await tap(lan, 'dialog.svc-sheet .svc-form input[data-f="price"]', 100)
            await lan.keyboard.type('2500')   # typed like a player
            await shot(lan, '08-lan-counter')
            await tap(lan, 'dialog.svc-sheet .svc-form [data-svc="do"][data-action="counter"]', 1500)
            # Minh accepts: the money is held
            await tap(minh, 'dialog.svc-sheet [data-svc="tab"][data-tab="inbox"]', 1200)
            await shot(minh, '09-minh-counter-received')
            await tap(minh, 'dialog.svc-sheet [data-svc="do"][data-action="accept"]', 1500)
            await shot(minh, '10-minh-accepted')
            # Lan does the work
            await tap(lan, 'dialog.svc-sheet [data-svc="tab"][data-tab="inbox"]', 1200)
            await tap(lan, 'dialog.svc-sheet [data-svc="do"][data-action="done"]', 1500)
            await shot(lan, '11-lan-delivered')
            # Minh confirms and rates
            await tap(minh, 'dialog.svc-sheet [data-svc="tab"][data-tab="inbox"]', 1200)
            await tap(minh, 'dialog.svc-sheet [data-svc="do"][data-action="confirm"]', 1500)
            await tap(minh, 'dialog.svc-sheet [data-svc="do"][data-action="rate"]', 400)
            await tap(minh, 'dialog.svc-sheet [data-svc="star"][data-n="5"]', 300)
            await shot(minh, '12-minh-rate')
            await tap(minh, 'dialog.svc-sheet .svc-form [data-svc="do"][data-action="rate"]', 1500)
            await shot(minh, '13-minh-done')
            # Lan's reputation and payment
            await tap(lan, 'dialog.svc-sheet [data-svc="tab"][data-tab="mine"]', 1200)
            await shot(lan, '14-lan-reputation')
            await tap(lan, 'dialog.svc-sheet [data-svc="tab"][data-tab="inbox"]', 1200)
            await shot(lan, '15-lan-paid')
            # the legacy order ×3 from the directory
            await tap(minh, 'dialog.svc-sheet [data-svc="tab"][data-tab="dir"]', 1200)
            await tap(minh, 'dialog.svc-sheet .svc-card[data-service="job"]')
            await shot(minh, '16-minh-legacy-x3')
            await minh_ctx.close()
            # landscape
            ctx, page = await player(base, db, env, 'Hoa', 844, 390, ip='10.0.0.3')
            await market(page)
            await shot(page, '17-hoa-directory-844x390')
            await ctx.close()
            await lan_ctx.close()
        await browser.close()
    print('\n'.join(shots))
    print('console errors:', len(errors))
    for e in errors[:20]:
        print('  ', e)


if __name__ == '__main__':
    asyncio.run(main())
