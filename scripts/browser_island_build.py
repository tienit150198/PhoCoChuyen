"""🏗️ Xây trên đảo + 🌍 đảo mở cửa (game/island_build.py, game/island_trips.py): a browser walk-through (dev tool, needs
playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds two saves through the real command path: the owner (Lan)
with Đảo Hoàng Hôn and Đảo Dừa, a dozen buildings finished at every level (built "in the past"), two crews at work
now (a new pool, a villa going to level 2), an open trip opened to everyone; and a visitor (Minh) without an island.
At 390x844, 360x740, 844x390 and 1280x800 on the new interface, and 390x844 on the old one: the 🏗️ Xây tab (the plot
map, an empty plot's list, a building's card), building a nhà sàn (confirm → scaffolding), the 🛥️ Ra đảo card with 🌍
Mở cửa, on the island (buildings, scaffolding with ⏳, a home's inside, the pool), the visitor's 🌍 Ghé đảo list and
visit, and the 🏝️ Đảo đẹp board. JPEG screenshots; console errors are printed.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_island_build.py [out_dir]
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_gadgets_classic import server, ROOT, PY  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_island_build_shots'

SEED = r'''
import json, sys, time, uuid
from unittest.mock import patch
from game import accounts
from game import bank as bk
from game import marriage as mr
from game import island_trips as it
from game import leaderboard as lb
from game.storage import Store
db, owner, guest, classic = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == '1'
store = Store(db, story=True)
def setup(name, wallet):
    def fn(s):
        j = s['journey']
        s['name'] = name
        j.update(gender='female' if name == 'Lan' else 'male', intro=True, life_day=20)
        j['wallet'] = wallet
        bk.apply(s, 'jr_bk_open', {})
        bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
        j['interface'] = dict(newInterface=not classic, interfacePromptSeen=True)
    return fn
mr._mutate(store, {store.key(owner): setup('Lan', 900_000_000), store.key(guest): setup('Minh', 50_000)})
with patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):   # trips need an account (game/island_trips.py)
    owner = accounts.register(store, owner, dict(username='lan_dao', password='mat-khau-dai-1', confirm='mat-khau-dai-1', display='Lan'))['token']
    guest = accounts.register(store, guest, dict(username='minh_khach', password='mat-khau-dai-1', confirm='mat-khau-dai-1', display='Minh'))['token']
def cmd(tok, action, **p):
    return store.command(tok, str(uuid.uuid4()), store.read(tok)[1], None, action, p)
cmd(owner, 'jr_island_buy', id='dao_hoang_hon', confirm=True)
cmd(owner, 'jr_island_buy', id='dao_dua', confirm=True)
H = 'dao_hoang_hon'
plan = [(0, 'lau_dai', 3), (1, 'biet_thu', 2), (2, 'nha_san', 1), (3, 'cong_vien', 3), (4, 'golf', 2), (6, 'ho_boi', 3),
        (7, 'cam_trai', 2), (12, 'nha_san', 3), (13, 'biet_thu', 1), (23, 'ben_thuyen', 3), (18, 'cong_vien', 1), (14, 'biet_thu', 1),
        (9, 'cam_trai', 3), (16, 'nha_san', 2)]
t = time.time() - 4000 * 3600
for plot, kind, lv in plan:
    for n in range(lv):
        t += 60 * 3600
        with patch('game.island_build.now', lambda t=t: t):
            if n == 0:
                cmd(owner, 'jr_isle_build', island=H, plot=plot, kind=kind, confirm=True)
            else:
                cmd(owner, 'jr_isle_up', island=H, plot=plot, confirm=True)
cmd(owner, 'jr_isle_build', island=H, plot=19, kind='ho_boi', confirm=True)      # two crews at work now
cmd(owner, 'jr_isle_up', island=H, plot=14, confirm=True)
trip = it.post(store, owner, 'start', dict(island=H, vehicle=''))['trip']['id']
it.post(store, owner, 'public', dict(trip=trip, open=True))
lb.set_visible(store, owner, store.read(owner)[0], True)
store.close_pool()
print(json.dumps([owner, guest]))
'''

INIT = ("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.tut.tips','done');"
        "localStorage.setItem('mnl.clean','on')}catch(e){}")
ACT = ("(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d||{});b.hidden=true;"
       "document.body.append(b);b.click();b.remove();})")


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    sizes = [(390, 844, False), (360, 740, False), (844, 390, False), (1280, 800, False), (390, 844, True)]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for w, h, classic in sizes:
            with server() as (base, db):
                tag = f'{w}x{h}{"-classic" if classic else ""}'
                phone = w < 900
                pages = []
                for _ in range(2):
                    ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone)
                    await ctx.add_init_script(INIT)
                    page = await ctx.new_page()
                    page.on('console', lambda m, tag=tag: m.type == 'error' and errors.append(f'{tag}: {m.text}'))
                    page.on('pageerror', lambda e, tag=tag: errors.append(f'{tag}: {e}'))
                    page.on('response', lambda r, tag=tag: r.status >= 400 and errors.append(f'{tag}: {r.status} {r.request.method} {r.url}'))
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=60000)
                    pages.append((ctx, page))
                tokens = [next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session') for ctx, _ in pages]
                out = subprocess.run([PY, '-c', SEED, db, tokens[0], tokens[1], '1' if classic else '0'], cwd=ROOT, check=True,
                                     capture_output=True, text=True).stdout
                for (ctx, _), tok in zip(pages, json.loads(out.strip().splitlines()[-1])):
                    await ctx.add_cookies([dict(name='mnl_session', value=tok, url=base)])
                owner, guest = pages[0][1], pages[1][1]
                for p in (owner, guest):
                    await p.reload()
                    await p.wait_for_selector('#app:not([hidden])', timeout=60000)
                    await p.wait_for_timeout(2500)
                    await p.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

                async def popups(page):
                    for _ in range(6):
                        b = page.locator('[data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            return
                        try:
                            await b.first.click(timeout=3000)
                        except Exception:
                            return
                        await page.wait_for_timeout(400)

                async def shot(page, name):
                    await page.wait_for_timeout(700)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.jpg'), type='jpeg', quality=80)
                    print(tag, name, flush=True)

                async def confirm(page):
                    await page.wait_for_selector('#confirmDialog[open]', timeout=8000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_selector('.isl-sheet[aria-busy="false"]', timeout=30000)
                    await page.wait_for_timeout(800)
                    await popups(page)

                # ---- the owner: the build tab
                await owner.evaluate(ACT, ['island', {'tab': 'build'}])
                await owner.wait_for_selector('.isl-sheet[open] .isl-map', timeout=15000)
                await shot(owner, '0-build-small-island')
                if (w, h) == (390, 844):   # Đảo Dừa: both crews free, build a nhà sàn (confirm → scaffolding)
                    await owner.click('.isl-sheet .sd-main')
                    await confirm(owner)
                    await shot(owner, '4-build-started')
                await owner.click('.isl-sheet .sd-chip[data-id="dao_hoang_hon"]')
                await shot(owner, '1-build-map')
                await owner.click('.isl-plot[data-id="0"]')
                await shot(owner, '2-build-castle')
                await owner.click('.isl-plot[data-id="5"]')
                await owner.click('.sd-item[data-id="nha_san"]')
                await shot(owner, '3-build-empty-plot')
                await owner.click('.isl-plot[data-id="1"]')
                await shot(owner, '3b-upgrade')
                # ---- Ra đảo: the open trip, 🌍 open to everyone
                await owner.click('.isl-sheet [data-is="tab"][data-tab="go"]')
                await owner.wait_for_selector('.isl-pub', timeout=15000)
                await shot(owner, '5-trip-public')
                # ---- on the island
                await owner.click('.isl-sheet .sd-main')
                await owner.wait_for_selector('dialog.isl-scene[open] canvas', timeout=20000)
                await owner.wait_for_timeout(6000)
                await shot(owner, '6-on-island')
                chips = owner.locator('.isl-chip-b')
                if await chips.count():
                    home = owner.locator('.isl-chip-b', has_text='Vào')
                    if await home.count():
                        await home.first.click()
                        try:
                            await owner.wait_for_selector('.isl-inside', timeout=20000)
                            await shot(owner, '7-inside-home')
                            await owner.click('.isl-inside [data-out]')
                        except Exception:
                            errors.append(f'{tag}: the home door was not reached')
                    pool = owner.locator('.isl-chip-b', has_text='Hồ bơi')
                    if await pool.count():
                        await pool.first.click()
                        await owner.wait_for_timeout(9000)
                        await shot(owner, '8-pool')
                else:
                    errors.append(f'{tag}: no building spots on the island')
                await popups(owner)
                await owner.click('dialog.isl-scene [data-close]')
                # ---- the visitor: 🌍 Ghé đảo
                await guest.evaluate(ACT, ['islandOpen', {}])
                await guest.wait_for_selector('.isl-sheet[open] .isl-opens', timeout=15000)
                await shot(guest, '9-visitor-list')
                await guest.click('.isl-open [data-is="visit"]')
                await guest.wait_for_selector('dialog.isl-scene[open] canvas', timeout=20000)
                await guest.wait_for_timeout(6000)
                await shot(guest, '10-visitor-on-island')
                await popups(guest)
                await guest.click('dialog.isl-scene [data-close]')
                # ---- the board
                if not classic and w in (390, 1280):
                    await owner.evaluate(ACT, ['rank', {}])
                    await owner.wait_for_timeout(1500)
                    tab = owner.locator('[data-action="lbKind"][data-kind="island"]')
                    if await tab.count():
                        await tab.click()
                        await owner.wait_for_timeout(2500)
                        await shot(owner, '11-board')
                    else:
                        errors.append(f'{tag}: no Đảo đẹp tab')
                for ctx, _ in pages:
                    await ctx.close()
        await browser.close()
    print('errors:', len(errors))
    for e in errors[:40]:
        print(' ', e[:300])


if __name__ == '__main__':
    asyncio.run(main())
