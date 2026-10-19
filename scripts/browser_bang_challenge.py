"""⚔️ Thách đấu bang (game/bang_challenge.py, public/js/v4/pet-arena.js 🛡️ › ⚔️ Thách đấu, the Bang sheet's card): a
browser walk-through with two bangs of real players (dev tool, needs playwright; Chromium or Chrome: MNL_PW_CHANNEL).

A throwaway story-mode server; twelve registered accounts with pets, two bangs of six (🐉 Rồng Đỏ led by Lan, 🐟 Cá Xanh
led by Minh), everyone's pet on its bang's roster but Lan's (she registers hers in the page). At 390×844: Lan's Bang sheet
(the ⚔️ card, the 👑 ranking with its three parts), the arena's Thách đấu section, registering her pet, the order editor,
the list of bangs, the challenge sent; Minh's Bang sheet with the challenge to answer, Nhận, the five duels animated
(mid-fight and the end); Lan's results; the same section at 844×390. JPEG screenshots, console errors.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_bang_challenge.py [out_dir]
"""
import asyncio
import contextlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_pet_arena as BPA  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_bang_challenge_shots'

BANGS = r'''
import sys, time, json
from game import bang, pet_arena as A
from game.storage import Store
store = Store(sys.argv[1], story=True)
groups = json.loads(sys.argv[2])
t = time.time()
def run(db):
    for i, (bid, name, emoji, color, toks) in enumerate(groups):
        sids = [store.key(x) for x in toks]
        db.execute('INSERT INTO bangs(id, name, key, emoji, color, motto, leader, created, created_by, channel) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (bid, name, bang.name_key(name), emoji, color, 'Đoàn kết là sức mạnh', sids[0], t - 3 * 86400, sids[0], ''))
        db.execute("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, 'dai_sanh', 2), (?, 'san_pet', ?), (?, 'kho', 3)", (bid, bid, 2 + i, bid))
        for j, s in enumerate(sids):
            db.execute("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?,?,?,'in',?,?)",
                       (bid, s, bang.pid_of(s), ('chu', 'pho', 'lao')[j] if j < 3 else 'tv', t - 2 * 86400))
            db.execute("INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,'checkin',20,?,?,?)",
                       (f'c:{bang.pid_of(s)}:seed', bid, s, bang.vn_week(t), bang.vn_day(t), t))
store.transaction(run)
for bid, name, emoji, color, toks in groups:
    for x in toks[1:]:
        st = store.read(x)[0]
        A.act(store, x, 'tc_reg', dict(pet=A.candidates(st)[0]['id']), st, '9.9.9.9')
store.close_pool()
print('ok')
'''


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, shots = [], []
    async with async_playwright() as pw:
        ch = os.environ.get('MNL_PW_CHANNEL')
        browser = await (pw.chromium.launch(channel=ch) if ch else pw.chromium.launch())

        async def player(base, db, env, who, rank, ip, w=390, h=844):
            ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2, has_touch=True, locale='vi-VN')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.ui25d','0');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{who}: {m.text}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {e}'))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            login = BPA.py(BPA.SEED, db, token, who, str(rank), ip, env=env)
            await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1200)
            for _ in range(6):
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(300)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            return ctx, page, login

        async def shot(page, name, full=False):
            path = OUT / f'{name}.jpg'
            await page.screenshot(path=str(path), type='jpeg', quality=80, full_page=full)
            shots.append(str(path))

        async def scroll_shot(page, sel, name):
            """The dialog's body scrolled through: one picture a screen."""
            n = await page.evaluate(f"(()=>{{const b=document.querySelector('{sel}');return b?Math.max(1,Math.ceil(b.scrollHeight/b.clientHeight)):1}})()")
            for i in range(min(int(n), 4)):
                await page.evaluate(f"(()=>{{const b=document.querySelector('{sel}');if(b)b.scrollTop={i}*b.clientHeight*.9}})()")
                await page.wait_for_timeout(250)
                await shot(page, f'{name}-{i + 1}')
            await page.evaluate(f"(()=>{{const b=document.querySelector('{sel}');if(b)b.scrollTop=0}})()")

        async def bang_sheet(page):
            await page.evaluate(BPA.ACT, ['bang', {}])
            await page.wait_for_selector('dialog.bg-sheet[open] .sd-body', timeout=10000)
            await page.wait_for_timeout(900)

        async def flash(page, sel):
            return await page.evaluate(f"document.querySelector('{sel}')?.textContent||''")

        with BPA.server() as (base, db, env):
            red, blue = [], []
            for i, n in enumerate(['Hoa', 'Tuấn', 'Linh', 'Quân', 'Mai']):
                ctx, page, tok = await player(base, db, env, n, 2 + i % 4, f'10.0.0.{i}')
                red.append(tok)
                await ctx.close()
            for i, n in enumerate(['Hùng', 'Thảo', 'Phong', 'Ngọc', 'Bảo']):
                ctx, page, tok = await player(base, db, env, n, 1 + i % 5, f'10.0.1.{i}')
                blue.append(tok)
                await ctx.close()
            ca, a, ta = await player(base, db, env, 'Lan', 4, '1.1.1.1')
            cb, b, tb = await player(base, db, env, 'Minh', 3, '2.2.2.2')
            import json
            print(BPA.py(BANGS, db, json.dumps([['b00000000a1', 'Rồng Đỏ', '🐉', 'do', [ta] + red],
                                                 ['b00000000b2', 'Cá Xanh', '🐟', 'navy', [tb] + blue]]), env=env))
            # Lan: her Bang sheet's ⚔️ card and the 👑 ranking's three parts
            await bang_sheet(a)
            await scroll_shot(a, 'dialog.bg-sheet[open]', '01-lan-bang-home')
            await a.click('dialog.bg-sheet [data-bg="tab"][data-tab="rank"]')
            await a.wait_for_timeout(700)
            await shot(a, '02-lan-rank')
            await a.click('dialog.bg-sheet [data-bg="tab"][data-tab="home"]')
            await a.wait_for_timeout(500)
            # the arena's ⚔️ Thách đấu section from the card
            await a.click('dialog.bg-sheet [data-bg="tcopen"]:not([data-find])')
            await a.wait_for_selector('dialog.pa-sheet[open] .pa-seg', timeout=15000)
            await a.wait_for_timeout(1000)
            await scroll_shot(a, 'dialog.pa-sheet[open]', '03-lan-arena-tc')
            # register her pet
            await a.click('dialog.pa-sheet .pa-mypet [data-pa="tpet"]')
            await a.wait_for_timeout(300)
            await shot(a, '04-lan-pick')
            await a.click('dialog.pa-sheet [data-pa="go"]')
            await a.wait_for_timeout(1200)
            print('reg:', await flash(a, 'dialog.pa-sheet .pa-flash'))
            # the order editor (Bang chủ): Lan to the front
            await a.click('dialog.pa-sheet [data-pa="tcorder"]')
            await a.wait_for_timeout(500)
            for _ in range(6):
                up = a.locator('dialog.pa-sheet .pa-roster.edit li:last-child [data-pa="tcmove"][data-d="-1"]')
                if not await up.count() or await up.is_disabled():
                    break
                await up.click()
                await a.wait_for_timeout(120)
            await shot(a, '05-lan-order')
            await a.click('dialog.pa-sheet [data-pa="go"]')
            await a.wait_for_timeout(1000)
            # find a bang and challenge it
            await a.click('dialog.pa-sheet [data-pa="go"]')
            await a.wait_for_selector('dialog.pa-sheet [data-pa="tcsend"]', timeout=10000)
            await a.wait_for_timeout(400)
            await shot(a, '06-lan-find')
            await a.click('dialog.pa-sheet [data-pa="tcsend"]')
            await a.wait_for_timeout(1500)
            print('send:', await flash(a, 'dialog.pa-sheet .pa-flash'))
            await shot(a, '07-lan-sent')
            # Minh: the challenge on his Bang sheet, Nhận, the match
            await b.wait_for_timeout(1500)
            await bang_sheet(b)
            await shot(b, '08-minh-bang-incoming')
            await b.click('dialog.bg-sheet [data-bg="tcyes"]')
            await b.wait_for_selector('dialog.pa-sheet .pa-fight', timeout=20000)
            await b.wait_for_timeout(2600)
            await shot(b, '09-minh-duel1-mid')
            for i in range(5):
                with contextlib.suppress(Exception):
                    await b.click('dialog.pa-sheet [data-pa="skip"]', timeout=4000)
                await b.wait_for_timeout(700)
                if i == 1:
                    await shot(b, '10-minh-duel2-end')
                if await b.locator('dialog.pa-sheet .pa-after [data-pa="done"]').count():
                    break
                await b.wait_for_timeout(1800)
            await b.wait_for_selector('dialog.pa-sheet .pa-after [data-pa="done"]', timeout=20000)
            await shot(b, '11-minh-match-end')
            await b.click('dialog.pa-sheet .pa-after [data-pa="done"]')
            await b.wait_for_timeout(1200)
            await shot(b, '12-minh-after')
            # Lan: the result in her section, then the landscape phone
            await a.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await bang_sheet(a)
            await shot(a, '13-lan-card-result')
            await a.set_viewport_size(dict(width=844, height=390))
            await a.click('dialog.bg-sheet [data-bg="tcopen"]:not([data-find])')
            await a.wait_for_selector('dialog.pa-sheet[open] .pa-seg', timeout=15000)
            await a.wait_for_timeout(900)
            await shot(a, '14-lan-landscape')
            with contextlib.suppress(Exception):
                await a.click('dialog.pa-sheet [data-pa="tcwatch"]', timeout=5000)
                await a.wait_for_selector('dialog.pa-sheet .pa-fight', timeout=10000)
                await a.wait_for_timeout(2200)
                await shot(a, '15-lan-landscape-replay')
            await a.set_viewport_size(dict(width=390, height=844))
            await a.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await bang_sheet(a)
            await a.click('dialog.bg-sheet [data-bg="tab"][data-tab="rank"]')
            await a.wait_for_timeout(700)
            await shot(a, '16-lan-rank-after')
            await ca.close()
            await cb.close()
        await browser.close()
    print('\n'.join(shots))
    print('console errors:', errors or 'none')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
