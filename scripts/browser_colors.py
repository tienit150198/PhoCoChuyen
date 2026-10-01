"""🎨 Bảng màu: a browser walk-through (dev tool, needs `pip install playwright websockets` + chromium).

Runs the game and the live street (as scripts/browser_live_walk.py) on a throwaway story-mode database and seeds
one save straight in it (scripts/browser_deco.py: Lan owns the old tập thể, a sofa in the living room). In the
browser, at 390x844 and 1280x800, light theme and "Phố đêm":
  1. Tủ đồ: the colour row under the shirt, the palette sheet ("Bảng màu của bạn"), unlocking Xanh navy there,
     wearing the shirt in navy, then the shoes in Đỏ (unlocked from the wardrobe's own button, worn at once);
  2. the home: select the sofa, 🎨 Màu, try a colour, use navy (already unlocked: free), the room and the 📸 photo;
  3. the dorm: buy the bunk curtain, recolour it navy;
  4. (phone only) the street: a second player sees Lan in her navy shirt and red shoes.
Exit 1 on any console error, page error or failed check.

    python scripts/browser_colors.py [out_dir]

MNL_SERVER_PY=<python>: run the game and the live service with another interpreter than the one driving the browser
(e.g. Playwright in one install, the server's Python and websockets in another).
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_deco import move_to, mutate, seed_own  # noqa: E402
from browser_live_chat import phone  # noqa: E402
from browser_live_walk import STATE, open_walk, servers  # noqa: E402

if os.environ.get('MNL_SERVER_PY'):
    sys.executable = os.environ['MNL_SERVER_PY']   # servers() starts both services with sys.executable
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_colors_shots'


def seed(s):
    seed_own(s)
    s['journey']['wallet'] = 400


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, checks = [], []

    def check(cond, what):
        checks.append(('PASS ' if cond else 'FAIL ') + what)
        if not cond:
            errors.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-colors-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db, _log):
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
                    await page.evaluate("try{localStorage.setItem('mnl.wn.seen','9.9.9')}catch(e){}")
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(1500)
                    await popups()
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

                async def shot(name, full=False):
                    await page.wait_for_timeout(500)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=full)

                async def theme(name):
                    await page.evaluate(f"document.documentElement.dataset.theme='{name}'")

                async def both(name):
                    for th in ('kem', 'dem'):
                        await theme(th)
                        await shot(f'{name}-{th}')
                    await theme('kem')

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(900)
                    await popups()

                async def colors():
                    return await page.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json()).then(b=>b.state&&b.state.colors||null)")

                async def wallet():
                    return await page.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json()).then(b=>b.state&&b.state.journey.wallet)")

                async def center(sel):
                    box = await page.evaluate("""s=>{const e=document.querySelector(s);if(!e)return null;
                        e.scrollIntoView?.({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];}""", sel)
                    assert box, f'nothing at {sel}'
                    return box

                mutate(db, token, seed)
                await reload()

                # ---- 1. Tủ đồ
                await page.evaluate("document.querySelector('[data-action=jrWardrobe]').click()")
                await page.wait_for_selector('#sheet[open] .wd-colors', timeout=10000)
                await page.wait_for_timeout(600)
                await both('01-wardrobe-top')
                await page.click('#sheet [data-action="jrWdPalette"]')
                await page.wait_for_selector('dialog.pl-sheet[open] .pl-grid', timeout=10000)
                await both('02-palette')
                w0 = await wallet()
                await page.click('dialog.pl-sheet [data-pl="unlock"][data-c="navy"]')
                await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                await shot('03-unlock-confirm')
                await confirm()
                await page.wait_for_timeout(600)
                await both('04-palette-navy')
                w1 = await wallet()
                check(w0 - w1 == 40, f'{tag}: unlocking navy costs 40 xu ({w0} -> {w1})')
                check('navy' in ((await colors()) or {}).get('have', []), f'{tag}: navy is in the palette')
                await page.click('dialog.pl-sheet [data-pl="close"]')
                await page.wait_for_timeout(500)
                await page.click('#sheet .wd-colors [data-action="jrWdTint"][data-color="navy"]')
                await page.wait_for_selector('#sheet [data-action="jrWdWear"]', timeout=5000)
                await shot('05-shirt-navy-try')
                await page.click('#sheet [data-action="jrWdWear"]')
                await page.wait_for_timeout(1200)
                c = await colors()
                top = await page.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json()).then(b=>b.state.wardrobe.look.top)")
                check(c['wear'].get(top) == 'navy', f'{tag}: the shirt ({top}) is worn in navy: {c["wear"]}')
                check(await wallet() == w1, f'{tag}: wearing an unlocked colour is free')
                await page.click('#sheet [data-action="jrWdTab"][data-tab="shoes"]')
                await page.wait_for_timeout(400)
                await page.click('#sheet .wd-colors [data-action="jrWdTint"][data-color="do"]')
                await page.wait_for_selector('#sheet [data-action="jrWdColorBuy"][data-color="do"]', timeout=5000)
                await both('06-shoes-red-locked')
                await page.click('#sheet [data-action="jrWdColorBuy"][data-color="do"]')
                await confirm()
                await page.wait_for_timeout(1200)
                await both('07-shoes-red-worn')
                c = await colors()
                check(set(c['have']) == {'navy', 'do'} and 'do' in c['wear'].values(), f'{tag}: red shoes unlocked and worn at once: {c}')
                check(w1 - await wallet() == 40, f'{tag}: red cost 40 xu')
                await reload()

                # ---- 2. the home: the sofa
                await page.wait_for_selector('.jr-house-row', timeout=10000)
                await page.click('.jr-house-row')
                await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                await popups()
                await page.click('.hs-sheet [data-hs="inside"]:not([data-mode])')
                await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)
                await page.click('.dc-sheet [data-dc="edit"]')
                await page.wait_for_selector('.dc-sheet svg.dc-room.edit')
                if await page.locator('.dc-sheet [data-dc="tipOk"]').count():
                    await page.click('.dc-sheet [data-dc="tipOk"]')
                uid = await page.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json()).then(b=>([...b.state.journey.deco.items,...b.state.journey.deco.bag].find(i=>i.k==='sofa')||{}).id)")
                await page.mouse.click(*(await center(f'.dc-sheet .dc-it[data-uid="{uid}"] .dc-hit')))
                await page.wait_for_selector('.dc-sheet .dc-tools [data-dc="tint"]', timeout=5000)
                await shot('08-sofa-selected')
                await page.click('.dc-sheet .dc-tools [data-dc="tint"]')
                await page.wait_for_selector('dialog.pl-pick[open] .pl-sws', timeout=5000)
                await both('09-sofa-picker')
                box = await page.evaluate("(()=>{const d=document.querySelector('dialog.pl-pick');const r=d.getBoundingClientRect(),c=getComputedStyle(d);return [Math.round(r.top),Math.round(r.height),c.height,c.minHeight,c.maxHeight,c.display,c.gridTemplateRows||'']})()")
                check(box[1] < h * 0.7, f'{tag}: the picker leaves the room in sight ({box})')
                await page.click('dialog.pl-pick [data-pl="try"][data-c="mint"]')
                await shot('10-sofa-try-mint-locked')
                await page.click('dialog.pl-pick [data-pl="try"][data-c="navy"]')
                w2 = await wallet()
                await page.click('dialog.pl-pick [data-pl="apply"]')
                await page.wait_for_timeout(1200)
                c = await colors()
                check(c['deco'].get(uid) == 'navy', f'{tag}: the sofa is navy: {c["deco"]}')
                check(await wallet() == w2, f'{tag}: a colour already unlocked costs nothing on the sofa')
                await page.click('.dc-sheet [data-dc="done"]')
                await page.wait_for_timeout(500)
                await both('11-room-navy-sofa')
                await page.click('.dc-sheet [data-dc="photo"]')
                await page.wait_for_selector('.dc-sheet .dc-photo img', timeout=10000)
                await shot('12-polaroid')
                await page.click('.dc-sheet [data-dc="photoClose"]')
                await page.click('.dc-sheet [data-dc="close"]')

                # ---- 3. the dorm
                mutate(db, token, move_to('ky_tuc_xa'))
                await reload()
                c = await colors()
                check(c['deco'].get(uid) == 'navy', f'{tag}: moving out keeps the sofa navy (in the bag)')
                await page.wait_for_selector('.jr-house-row', timeout=10000)
                await page.click('.jr-house-row')
                await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                await popups()
                await page.click('.hs-sheet [data-hs="inside"]')
                await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)
                await page.click('.dc-sheet [data-dc="edit"]')
                await page.click('.dc-sheet [data-dc="drawer"][data-d="shop"]')
                await page.click('.dc-sheet .dc-card[data-k="rem_giuong"]')
                await page.wait_for_selector('.dc-sheet .dc-ok rect')
                ok = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-ok rect')].length")
                await page.mouse.click(*(await page.evaluate("""(()=>{const l=[...document.querySelectorAll('.dc-sheet .dc-ok rect')];const e=l[l.length-1];
                    e.scrollIntoView?.({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];})()""")))
                await confirm()
                curtain = await page.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json()).then(b=>([...b.state.journey.deco.items,...b.state.journey.deco.bag].find(i=>i.k==='rem_giuong')||{}).id)")
                check(bool(curtain), f'{tag}: the bunk curtain is up ({ok} spots)')
                if not await page.locator('.dc-sheet .dc-tools [data-dc="tint"]').count():
                    await page.mouse.click(*(await center(f'.dc-sheet .dc-it[data-uid="{curtain}"] .dc-hit')))
                await page.click('.dc-sheet .dc-tools [data-dc="tint"]')
                await page.wait_for_selector('dialog.pl-pick[open] .pl-sws', timeout=5000)
                await page.click('dialog.pl-pick [data-pl="try"][data-c="navy"]')
                await shot('13-dorm-picker')
                await page.click('dialog.pl-pick [data-pl="apply"]')
                await page.wait_for_timeout(1200)
                check((await colors())['deco'].get(curtain) == 'navy', f'{tag}: the bunk curtain is navy')
                await page.click('.dc-sheet [data-dc="done"]')
                await both('14-dorm-navy-curtain')
                await page.click('.dc-sheet [data-dc="close"]')
                await page.wait_for_timeout(400)

                # ---- 4. the street, seen by another player
                if w == 390:
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    b = await phone(browser, base, 'Minh Tú', errors)
                    await b.page.reload()
                    await b.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await b.chat_button()
                    await open_walk(b)
                    await page.wait_for_selector('.live-fab:not([hidden])', timeout=25000)
                    await page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
                    await page.wait_for_selector('#rail [data-action=v4Group][data-group=pho]', timeout=15000)
                    await page.click('#rail [data-action=v4Group][data-group=pho]')
                    await page.wait_for_selector('#rail [data-action=liveWalk]:visible', timeout=15000)
                    await page.click('#rail [data-action=liveWalk]')
                    await page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=10000)
                    seen = None
                    for _ in range(60):
                        s = await b.page.evaluate(STATE)
                        seen = next((p for p in s['people'] if p['name'] == 'Lan'), None)
                        if seen:
                            break
                        await asyncio.sleep(0.2)
                    c = await colors()
                    check(bool(seen) and seen.get('tint') and all(seen['tint'].get(k) == v for k, v in c['wear'].items()),
                          f'the other player sees Lan in her colours: {seen and seen.get("tint")} (worn {c["wear"]})')
                    await b.page.wait_for_timeout(1200)
                    await b.page.screenshot(path=str(OUT / f'{tag}-15-street-seen-by-other.png'))
                    await page.screenshot(path=str(OUT / f'{tag}-16-street-own.png'))
                    if seen:
                        s = await b.page.evaluate(STATE)
                        me = next(p for p in s['people'] if p['name'] == 'Lan')
                        box = await b.page.locator('.walk-sheet .wk-canvas').bounding_box()
                        v = s['view']
                        await b.page.mouse.click(box['x'] + v['ox'] + me['x'] * v['k'], box['y'] + v['oy'] + (me['y'] - 20) * v['k'])
                        await b.page.wait_for_timeout(1200)
                        await b.page.screenshot(path=str(OUT / f'{tag}-17-street-card.png'))
                    await b.ctx.close()
                await ctx.close()
            await browser.close()
    for line in checks:
        print(line)
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
