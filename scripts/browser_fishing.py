#!/usr/bin/env python3
"""🎣 Câu cá (24/10): the lake in a real browser on a 390x844 phone (dev tool; the game server from
scripts/browser_housing.py, PostgreSQL through TEST_DATABASE_URL).

Lan (a story save with 2.000.000 xu) opens Khu phố → 🎣 Câu cá and, with fingers only:
  1. sees the lake (zones, buoys, rod range), the three stalls on the bank and the HUD;
  2. holds the button (the power meter swings), releases: the bobber flies and splashes;
  3. waits for the bite ("!"), taps, plays the tension reel to the end: the catch card (retries a lost round);
  4. 🎣 Quầy bán cần: buys Cần trúc; 🐟 Quầy thu mua: sells the bag (a haggle is answered); 📖 Sổ cá and 🐋 the board.
JPEG screenshots in out_dir; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_fishing.py [out_dir]
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'fishing-shots'
PW = 'matkhau-rat-dai'
API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""


def store(db):
    from game.storage import Store
    return Store(db, story=True)


def mutate(db, token, fn):
    from game import marriage as mr
    st = store(db)
    mr._mutate(st, {st.key(token): fn})
    st.close_pool()


def seed(s):
    from game import whats_new as wn
    j = s['journey']
    s['name'] = 'Lan'
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    j.update(gender='female', intro=True, wallet=2_000_000)


async def main() -> int:
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    problems, checks = [], []

    def check(ok, what):
        checks.append(('PASS ' if ok else 'FAIL ') + what)
        print(checks[-1])
        if not ok:
            problems.append(what)

    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2)
            await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','9.9.9')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and problems.append(f'console: {m.text[:200]}'))
            page.on('pageerror', lambda e: problems.append(f'exception: {str(e)[:200]}'))
            page.on('response', lambda r: r.status >= 500 and problems.append(f'HTTP {r.status} {r.url}'))
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            out = await page.evaluate(API, ['/api/account/register', dict(username='lanmay', password=PW, confirm=PW, display='Lan Mây')])
            check(out['status'] < 400, f'register ({out["status"]})')
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            mutate(db, token, seed)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await page.wait_for_timeout(1500)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

            async def shot(name, wait=300):
                await page.wait_for_timeout(wait)
                await page.screenshot(path=str(OUT / f'{name}.jpg'), type='jpeg', quality=82)

            async def act(action):
                await page.evaluate(f"(()=>{{const b=document.createElement('button');b.dataset.action='{action}';b.hidden=true;"
                                    "document.body.append(b);b.click();b.remove();})()")

            async def go_box():
                b = await page.evaluate("()=>{const r=document.querySelector('dialog.fs-sheet[open] .fs-go').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];}")
                return b

            async def cls():
                return await page.evaluate("document.querySelector('dialog.fs-sheet[open] .fs-go')?.className||''")

            await act('fishing')
            await page.wait_for_selector('dialog.fs-sheet[open] .fs-stall', timeout=15000)
            await page.wait_for_timeout(800)
            stalls = await page.inner_text('dialog.fs-sheet[open] .fs-bank')
            check('Quầy bán cần' in stalls and 'Quầy thu mua' in stalls and 'Bảng bộ sưu tập' in stalls, 'three stalls on the bank')
            hud = await page.inner_text('dialog.fs-sheet[open] .fs-hud')
            check('Cần tre' in hud and '0/20' in hud, f'the HUD: {hud!r}')
            await shot('01-lake')
            fps = await page.evaluate("""()=>new Promise(done=>{let n=0;const t0=performance.now();const f=()=>{n++;if(performance.now()-t0<1000)requestAnimationFrame(f);else done(n);};requestAnimationFrame(f);})""")
            check(fps >= 40, f'the lake animates ({fps} frames in a second)')

            caught = None
            for attempt in range(12):
                x, y = await go_box()
                await page.mouse.move(x, y)
                await page.mouse.down()
                await page.wait_for_timeout(520)
                if attempt == 0:
                    await shot('02-charge', 0)
                    meter = await page.evaluate("!document.querySelector('dialog.fs-sheet[open] .fs-meter').hidden")
                    check(meter, 'the power meter shows while holding')
                await page.mouse.up()
                # wait for the bite (or a lost round)
                phase = ''
                for _ in range(400):
                    await page.wait_for_timeout(100)
                    c = await cls()
                    if 'hook' in c:
                        phase = 'bite'
                        break
                    tip = await page.inner_text('dialog.fs-sheet[open] .fs-go')
                    if tip.startswith('🎣 Giữ'):
                        phase = 'lost'
                        break
                    if attempt == 0 and _ == 40:
                        await shot('03-wait', 0)
                if phase != 'bite':
                    continue
                await shot('04-bite', 0)
                await page.mouse.down()
                await page.wait_for_timeout(60)
                await page.mouse.up()
                # the fight: hold while the needle is left of the green's middle
                await page.wait_for_timeout(500)
                fought = False
                for k in range(600):
                    st = await page.evaluate("""()=>{const d=document.querySelector('dialog.fs-sheet[open]');const t=d.querySelector('.fs-ten');
                        if(t.hidden)return null;const n=parseFloat(d.querySelector('.fs-ten-bar i').style.left)||0,b=d.querySelector('.fs-ten-bar b');
                        return [n,(parseFloat(b.style.left)||0)+(parseFloat(b.style.width)||0)/2];}""")
                    if st is None:
                        if fought or k > 20:
                            break
                        await page.wait_for_timeout(50)
                        continue
                    fought = True
                    if st[0] < st[1]:
                        await page.mouse.down()
                    else:
                        await page.mouse.up()
                    if k == 25:
                        await shot('05-fight', 0)
                    await page.wait_for_timeout(40)
                await page.mouse.up()
                try:
                    await page.wait_for_selector('dialog.fs-sheet[open] .fs-card:not([hidden])', timeout=6000)
                except Exception:
                    continue
                caught = await page.inner_text('dialog.fs-sheet[open] .fs-card')
                if 'Giá lái' in caught:
                    break
                await shot('06-junk', 500)
                await page.click('dialog.fs-sheet[open] .fs-card [data-fs="again"]')
            check(caught is not None, f'a catch card after playing a round: {(caught or "")[:80]!r}')
            if caught:
                await shot('06-card', 700)
                await page.click('dialog.fs-sheet[open] .fs-card [data-fs="again"]')
            # 🎣 Quầy bán cần
            await page.click('dialog.fs-sheet[open] .fs-st-shop')
            await page.wait_for_selector('dialog.fs-sheet[open] .fs-panel:not([hidden]) .fs-item')
            await shot('07-shop')
            await page.click('dialog.fs-sheet[open] .fs-panel [data-fs="buy"][data-item="truc"]')
            await page.wait_for_selector('#confirmDialog[open] [data-action="confirmYes"]', timeout=5000)
            await shot('07b-confirm', 100)
            await page.click('#confirmDialog[open] [data-action="confirmYes"]')
            await page.wait_for_timeout(1200)
            hud = await page.inner_text('dialog.fs-sheet[open] .fs-hud')
            check('Cần trúc' in hud, f'bought and holding Cần trúc: {hud!r}')
            await page.click('dialog.fs-sheet[open] .fs-panel [data-fs="tab"][data-t="bait"]')
            await shot('08-bait')
            await page.click('dialog.fs-sheet[open] .fs-panel [data-fs="panelX"]')
            # 🐟 Quầy thu mua
            await page.click('dialog.fs-sheet[open] .fs-st-market')
            await page.wait_for_selector('dialog.fs-sheet[open] .fs-panel:not([hidden])')
            await shot('09-market')
            if await page.locator('dialog.fs-sheet[open] [data-fs="sellAll"]').count():
                await page.click('dialog.fs-sheet[open] [data-fs="sellAll"]')
                await page.wait_for_timeout(900)
                if await page.locator('dialog.fs-sheet[open] .fs-deal').count():
                    await shot('10-haggle')
                    await page.click('dialog.fs-sheet[open] .fs-deal [data-pick="accept"]')
                    await page.wait_for_timeout(800)
                said = await page.inner_text('dialog.fs-sheet[open] .fs-say')
                check('xu' in said, f'sold: {said!r}')
            await page.click('dialog.fs-sheet[open] .fs-panel [data-fs="panelX"]')
            # 📖 Bảng bộ sưu tập
            await page.click('dialog.fs-sheet[open] .fs-st-board')
            await page.wait_for_selector('dialog.fs-sheet[open] .fs-panel .fs-grid')
            dex = await page.inner_text('dialog.fs-sheet[open] .fs-panel')
            check('Đã câu' in dex and '???' in dex, 'Sổ cá: progress and the uncaught silhouettes')
            await shot('11-dex', 600)
            await page.click('dialog.fs-sheet[open] .fs-panel [data-fs="tab"][data-t="fish_big"]')
            await page.wait_for_timeout(1200)
            board = await page.inner_text('dialog.fs-sheet[open] .fs-panel')
            check('1.000.000' in board and ('Lan' in board or 'Câu một con' in board or 'Bạn: hạng' in board), f'the 🐋 board with its weekly rewards: {board[:160]!r}')
            await shot('12-board')
            await browser.close()
    for p in problems:
        print('PROBLEM', p)
    print(f'{len(checks) - len([c for c in checks if c.startswith("FAIL")])}/{len(checks)} checks passed; shots in {OUT}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
