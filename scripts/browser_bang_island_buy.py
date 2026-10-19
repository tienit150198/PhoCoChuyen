#!/usr/bin/env python3
"""🏝️ Đảo bang bought and upgraded (owner 21/10), in real browsers (dev tool; needs playwright, PostgreSQL through
TEST_DATABASE_URL; BROWSER_CHANNEL=chrome uses the installed Google Chrome instead of playwright's chromium).

The game server and the live service on one disposable database:
  * Lan founds 🐉 Rồng Đỏ (Bang chủ) and gives 50 M to the fund; Minh (Thành viên, 1280×800) and Tú (old interface,
    390×844) join; Hoa founds 🌊 Cá Xanh and never buys an island;
  * the offer: Lan's Bang sheet shows 🏝️ Mua Đảo bang first; Minh's says to ask an officer; Minh's 🏯 Đảo bang opens
    the offer, not an island; Hoa's pet arena is locked on the island;
  * Lan buys it (two taps), walks onto cấp 1 (2.5D, phone), opens the island card from the island's 🏝️ chip, upgrades
    to cấp 2: the card's timer, the island's 🚧 and its work site for Lan (phone) and Minh (desktop);
  * time passes (the database's ready time moved back): cấp 2 for Lan, then cấp 5 for Minh (2.5D) and Tú (old 2D).
Screenshots (PNG) go to OUT (argv[1]); exit 1 on a failed check or a page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_bang_island_buy.py [out_dir]
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_bang_island import ACT, check, errors, fails, py, servers  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'bang-island-buy-shots'

SEED = r'''
import sys, hashlib
from game import accounts, pets, promotion
from game import marriage as mr
from game.storage import Store
db, token, name, classic = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == '1'
store = Store(db, story=True)
out = accounts.register(store, token, dict(username='u' + hashlib.md5(name.encode()).hexdigest()[:12], password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
def fn(s):
    j = s['journey']
    s['name'] = name
    j.update(gender='female' if name != 'Minh' else 'male', intro=True, life_day=20)
    j['wallet'] = 120_000_000
    promotion.record(s, 'milk_tea', True)['rank'] = 1
    pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': 'corgi', 'coat': 0, 'nick': 'Mochi', 'confirm': True})
    j['interface'] = dict(newInterface=not classic, interfacePromptSeen=True)   # engine.INTERFACE_DEFAULTS
mr._mutate(store, {sid: fn})
store.close_pool()
print(tok)
'''

BANGS = r'''
import sys, json, secrets
from game import bang
from game.storage import Store
db, lan, minh, tu, hoa = sys.argv[1:6]
store = Store(db, story=True)
def cmd(tok, action, **p):
    return store.command(tok, 'seed-' + secrets.token_hex(6), store.read(tok)[1], None, action, p)
def mine(tok):
    with store.connect() as d:
        return bang._mine(d, store.key(tok))['bang']
cmd(lan, 'jr_bang_found', name='Rồng Đỏ', emoji='🐉', color='do', motto='Đoàn kết', open=True, confirm=True)
cmd(hoa, 'jr_bang_found', name='Cá Xanh', emoji='🌊', color='navy', motto='Bơi xa', open=True, confirm=True)
red, blue = mine(lan), mine(hoa)
for t in (minh, tu):
    bang.post(store, t, 'join', dict(bang=red))
cmd(lan, 'jr_bang_give', bang=red, amount=50_000_000, confirm=True)
def w(d):
    for fac, lv in (('dai_sanh', 3), ('kho', 2), ('xuong_may', 2), ('san_pet', 2), ('den_vang', 1), ('tuong', 3), ('cong', 2)):
        d.execute('INSERT INTO bang_facilities(bang, fac, level) VALUES(?,?,?) ON CONFLICT(bang, fac) DO UPDATE SET level=excluded.level', (red, fac, lv))
store.transaction(w)
store.close_pool()
print(json.dumps([red, blue]))
'''

TIME = r'''
import sys
from game.storage import Store
db, bid, level = sys.argv[1], sys.argv[2], int(sys.argv[3])
store = Store(db, story=True)
def run(d):
    if level:   # straight to a level (a test shortcut: the upgrades' own path is tests/test_bang_island_buy.py)
        d.execute('UPDATE bangs SET isle=?, isle_to=NULL, isle_ready=NULL WHERE id=?', (level, bid))
    else:       # the upgrade being built is due now
        d.execute('UPDATE bangs SET isle_ready=1 WHERE id=? AND isle_to IS NOT NULL', (bid,))
store.transaction(run)
store.close_pool()
print('ok')
'''


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='mnl-bisle-buy-')
    db = os.path.join(tmp, 'g.db')
    async with async_playwright() as pw:
        channel = os.environ.get('BROWSER_CHANNEL') or None
        browser = await pw.chromium.launch(**(dict(channel=channel) if channel else {}))

        async def open_page(base, w, h, who):
            phone = w < 900
            ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone, locale='vi-VN')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{who}: {m.text}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {e}'))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=40000)
            return ctx, page

        async def calm(page):
            await page.wait_for_timeout(1200)
            for _ in range(6):
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(300)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        async def shot(page, name):
            await page.screenshot(path=str(OUT / f'{name}.png'))
            print('SHOT', OUT / f'{name}.png', flush=True)

        async def leave(page):
            """Close the sheets, then walk off the island the player's way (← Về phố), so the next open starts fresh."""
            await page.evaluate("document.querySelectorAll('dialog[open]:not(.bisl-scene)').forEach(d=>d.close())")
            if await page.locator('dialog.bisl-scene[open] [data-close]').count():
                await page.click('dialog.bisl-scene[open] [data-close]')
                await page.wait_for_timeout(500)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        async def sheet(page, tab='home'):
            await leave(page)
            await page.evaluate(ACT, ['bang', {'tab': tab}])
            await page.wait_for_selector('dialog.bg-sheet[open] .sd-body .sd-card', timeout=15000)
            await page.wait_for_timeout(900)
            return await page.inner_text('dialog.bg-sheet[open] .sd-body')

        async def island(page, label):
            await leave(page)
            await page.evaluate(ACT, ['bangIsland', {}])
            await page.wait_for_selector('dialog.bisl-scene[open] canvas', timeout=20000)
            await page.wait_for_function("!document.querySelector('dialog.bisl-scene .bisl-loading')", timeout=25000)
            await page.wait_for_timeout(2500)
            status = await page.inner_text('dialog.bisl-scene [data-status]')
            print(label, 'status:', status, flush=True)
            return status

        with servers(db, tmp) as (base, env):
            people = {}
            for who, w, h, classic in (('Lan', 390, 844, '0'), ('Minh', 1280, 800, '0'), ('Tú', 390, 844, '1'), ('Hoa', 390, 844, '0')):
                ctx, page = await open_page(base, w, h, who)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                login = py(SEED, db, token, who, classic, env=env)
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
                people[who] = [ctx, page, login]
            red, blue = json.loads(py(BANGS, db, *(people[n][2] for n in ('Lan', 'Minh', 'Tú', 'Hoa')), env=env))
            for who, (ctx, page, _) in people.items():
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=40000)
                await calm(page)
            lan, minh, tu, hoa = (people[n][1] for n in ('Lan', 'Minh', 'Tú', 'Hoa'))

            # ---- the offer
            body = await sheet(lan)
            check('Mua Đảo bang' in body and '1 triệu' in body, 'Lan (Bang chủ) sees the island offer first', body[:160].replace('\n', ' '))
            check('Tất cả' in body, 'the fund has no cap: chips up to "Tất cả"')
            await shot(lan, '390x844-01-offer-officer')
            body = await sheet(minh)
            check('Nhờ Bang chủ hoặc Phó bang' in body, 'Minh (Thành viên) is told to ask an officer')
            await shot(minh, '1280x800-02-offer-member')
            await minh.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await minh.evaluate(ACT, ['bangIsland', {}])
            await minh.wait_for_selector('dialog.bg-sheet[open] .bg-isle-offer', timeout=15000)
            check(not await minh.locator('dialog.bisl-scene[open]').count(), 'no island before the purchase: 🏯 opens the offer')
            await hoa.evaluate(ACT, ['petArena', {}])
            await hoa.wait_for_selector('dialog.pa-sheet[open] .pa-locked', timeout=15000)
            await hoa.wait_for_timeout(700)
            text = await hoa.inner_text('dialog.pa-sheet .pa-locked')
            check('Đảo bang' in text, 'a bang without an island: the arena is locked on it', text[:120].replace('\n', ' '))
            await shot(hoa, '390x844-03-arena-locked')

            # ---- Lan buys it
            await sheet(lan)
            await lan.click('dialog.bg-sheet [data-bg="isle"][data-to="1"]')
            await lan.wait_for_timeout(300)
            await lan.click('dialog.bg-sheet [data-bg="isle"][data-to="1"]')
            await lan.wait_for_selector('dialog.bg-sheet .sd-flash.good', timeout=10000)
            flash = await lan.inner_text('dialog.bg-sheet .sd-flash')
            check('đã có đảo' in flash, 'bought', flash)
            await lan.wait_for_timeout(500)
            await shot(lan, '390x844-04-bought')
            st = await island(lan, 'Lan')
            check('Đảo cấp 1' in st and '/30' in st, 'on cấp 1: cap 30', st)
            await shot(lan, '390x844-05-island-cap1')
            # the island chip → the island card → upgrade to cấp 2
            await lan.click('dialog.bisl-scene [data-isle]')
            await lan.wait_for_selector('dialog.bg-sheet[open] .bg-isle', timeout=15000)
            await lan.wait_for_timeout(800)
            await lan.click('dialog.bg-sheet [data-bg="isle"][data-to="2"]')
            await lan.wait_for_timeout(300)
            await lan.click('dialog.bg-sheet [data-bg="isle"][data-to="2"]')
            await lan.wait_for_selector('dialog.bg-sheet .bg-isle.building', timeout=10000)
            await lan.wait_for_timeout(700)
            card = await lan.inner_text('dialog.bg-sheet .bg-isle')
            check('Đang mở rộng lên cấp 2' in card, 'the upgrade card with its timer', card[:160].replace('\n', ' '))
            await lan.locator('dialog.bg-sheet .bg-isle').scroll_into_view_if_needed()
            await shot(lan, '390x844-06-upgrade-card')
            st = await island(lan, 'Lan')
            check('🚧' in st, 'the island shows its upgrade under way', st)
            await shot(lan, '390x844-07-island-site')
            st = await island(minh, 'Minh')
            await shot(minh, '1280x800-08-island-site')
            await leave(minh)

            # ---- time passes
            py(TIME, db, red, '0', env=env)
            st = await island(lan, 'Lan')
            check('Đảo cấp 2' in st and '/40' in st, 'cấp 2 done: cap 40', st)
            await shot(lan, '390x844-09-island-cap2')
            await lan.click('dialog.bisl-scene [data-visit="vo_duong"]')
            await lan.wait_for_timeout(6000)
            await shot(lan, '390x844-10-vo-duong')
            py(TIME, db, red, '5', env=env)
            st = await island(minh, 'Minh')
            check('Đảo cấp 5' in st and '/80' in st, 'cấp 5: cap 80', st)
            await shot(minh, '1280x800-11-island-cap5')
            st = await island(tu, 'Tú')
            check('Đảo cấp 5' in st, 'the old interface draws cấp 5 too', st)
            await shot(tu, '390x844-12-island-cap5-classic')
            await tu.click('dialog.bisl-scene [data-visit="hai_dang"]')
            await tu.wait_for_timeout(6000)
            await shot(tu, '390x844-13-hai-dang-classic')
            body = await sheet(lan, 'build')
            check('Cấp 5/5' in body and 'cao nhất' in body, 'the island card at the top level')
            await shot(lan, '390x844-14-build-tab-cap5')
            await leave(minh)
            await minh.evaluate(ACT, ['petArena', {}])
            await minh.wait_for_selector('dialog.pa-sheet[open] .pa-body', timeout=15000)
            await minh.wait_for_timeout(1000)
            check(not await minh.locator('dialog.pa-sheet .pa-locked').count(), 'with the island the arena opens')
            for ctx, _, _ in people.values():
                await ctx.close()
        await browser.close()
    for name in ('game.log', 'live.log'):
        with contextlib.suppress(OSError):
            (OUT / name).write_text(Path(tmp, name).read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    print('errors:', len(errors))
    for e in errors[:30]:
        print('  ', e[:300])
    print('fails:', fails)
    return 1 if fails or errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
