"""🏮 Hội chợ dân gian: a browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server with the fair open today (MNL_FAIR_START = today, Vietnam date),
seeds one save (a named character with 300 xu) and three neighbours with accounts and a few fair points, then in the
browser: the journey banner, the gate, Ô ăn quan (a game against Bé Bi to the end), Ném vòng (aimed at each
bottle), Bầu cua (bets, the bowl, the result), Lô tô (buys a card, marks the called numbers,
"Kinh!" or the neighbour's), Chiếu trong (and a raid card: the raid itself is random, so its result is swapped in
on the wire for the screenshot only), the Bảng vàng; then the "đã tàn" card on a server whose fair ended yesterday.
390x844 and 1280x800, light theme and "Phố đêm". Exit 1 on any console error.

    python scripts/browser_fair.py [out_dir]
"""
import asyncio
import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_fair_shots'
VN = datetime.timezone(datetime.timedelta(hours=7))


def vn_today(days=0):
    return (datetime.datetime.now(VN) + datetime.timedelta(days=days)).date().isoformat()


def seed(db: str, token: str, neighbours: bool) -> None:
    from game import accounts
    from game import marriage as mr
    from game import whats_new as wn
    from game.storage import Store
    store = Store(db, story=True)

    def me(s):
        s['name'] = 'Lan'
        s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
        s['journey'].update(gender='female', intro=True, wallet=300)
    mr._mutate(store, {store.key(token): me})
    if neighbours:
        for i, (name, rounds) in enumerate((('Anh Ba Gánh', 9), ('Chị Tư Xôi', 6), ('Bé Na', 3))):
            tok, _, _ = store.session()
            tok = accounts.register(store, tok, dict(username=f'hoicho{i}x', password='mat-khau-dai-1', confirm='mat-khau-dai-1', display=name))['token']

            def fn(s, name=name):
                s['name'] = name
                s['journey'].update(gender='male', intro=True, wallet=400)
            mr._mutate(store, {store.key(tok): fn})
            import time
            for k in range(rounds):
                rev = store.read(tok)[1]
                try:
                    store.command(tok, f'seed-fair-{i}-{k:03d}', rev, None, 'fair_bc', {'bets': {f: 1 for f in ('bau', 'cua', 'tom')}})
                except Exception as e:  # noqa: BLE001 - a too-fast round: wait and go on
                    print('seed:', e)
                time.sleep(1.25)
    store.close_pool()


async def walk(base, db, errors):
    from playwright.async_api import async_playwright
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
            seed(db, token, neighbours=w == 390)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1500)
            tag = f'{w}x{h}'

            async def popups():
                for _ in range(4):
                    b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                    if not await b.count():
                        break
                    await b.first.click()
                    await page.wait_for_timeout(400)
            await popups()
            await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

            async def shot(name):
                await page.wait_for_timeout(500)
                await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

            async def theme(name):
                await page.evaluate(f"document.documentElement.dataset.theme='{name}'")

            async def poll(js, timeout=30):
                for _ in range(int(timeout * 5)):
                    if await page.evaluate(js):
                        return True
                    await page.wait_for_timeout(200)
                return False

            # The journey: the banner
            if not await page.locator('.jr-fair-row').count():
                await page.evaluate("document.querySelector('[data-action=\"home\"]')?.click()")
                await page.wait_for_selector('.jr-fair-row', timeout=10000)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'1-banner-{th}')
            await theme('kem')
            await page.click('.jr-fair-row')
            await page.wait_for_selector('.fh-sheet[open] .fh-gate', timeout=10000)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'0-gate-{th}')
            await theme('kem')
            # 🪨 Ô ăn quan: pick Bé Bi, play to the end (first ô with dân, to the right)
            await page.click('.fh-sheet [data-fh="tab"][data-tab="oaq"]')
            await page.wait_for_selector('.fh-sheet .fh-opps', timeout=5000)
            await shot('0a-oaq-pick')
            await page.click('.fh-sheet [data-fh="oaqstart"][data-lv="de"]')
            await page.wait_for_selector('.fh-sheet .fh-oaq', timeout=10000)
            await page.click('.fh-sheet .fh-o.pick >> nth=1')
            await shot('0b-oaq-dir')
            await page.click('.fh-sheet [data-fh="oaqmove"][data-d="1"]')
            await page.wait_for_timeout(900)
            await page.screenshot(path=str(OUT / f'{tag}-0c-oaq-sowing.png'))
            await page.click('.fh-sheet [data-fh="oaqfast"]')
            for _ in range(80):
                state = await page.evaluate("""()=>{
                  if(document.querySelector('.fh-sheet .fh-oend'))return 'end';
                  const c=document.querySelector('.fh-sheet .fh-o.pick');if(!c)return 'wait';
                  c.click();const d=document.querySelector('.fh-sheet [data-fh="oaqmove"][data-d="1"]');d&&d.click();return 'moved';}""")
                if state == 'end':
                    break
                await page.wait_for_timeout(700)
            await page.wait_for_selector('.fh-sheet .fh-oend', timeout=30000)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'0d-oaq-end-{th}')
            await theme('kem')
            # 💍 Ném vòng: aim at each bottle (reads the ring's x from the page)
            await page.click('.fh-sheet [data-fh="tab"][data-tab="home"]')
            await page.click('.fh-sheet [data-fh="tab"][data-tab="ring"]')
            await page.wait_for_selector('.fh-sheet .fh-ringstage', timeout=5000)
            await shot('0e-ring-idle')
            await page.click('.fh-sheet [data-fh="ringstart"]')
            await page.wait_for_selector('.fh-sheet [data-fh="throw"]', timeout=10000)
            aim = """async(n)=>{let thrown=0;const t0=performance.now();
              while(thrown<n&&performance.now()-t0<20000){await new Promise(r=>requestAnimationFrame(r));
                const a=document.querySelector('.fh-sheet .fh-aim'),b=document.querySelector('.fh-sheet [data-fh="throw"]');
                if(!a||!b||b.disabled||a.dataset.x==null)continue;
                const x=+a.dataset.x,i=[...document.querySelectorAll('.fh-sheet .fh-bottle:not(.ringed)')].findIndex(e=>Math.abs(+e.dataset.x-x)<1.2);
                if(i>=0){b.click();thrown++;await new Promise(r=>setTimeout(r,650));}}
              return thrown;}"""
            await page.evaluate(aim, 2)
            await page.screenshot(path=str(OUT / f'{tag}-0f-ring-live.png'))
            await page.evaluate(aim, 3)
            await page.wait_for_selector('.fh-sheet .fh-ringres', timeout=10000)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'0g-ring-result-{th}')
            await theme('kem')
            await page.click('.fh-sheet [data-fh="tab"][data-tab="home"]')
            await page.click('.fh-sheet [data-fh="tab"][data-tab="bc"]')
            await page.wait_for_selector('.fh-sheet .fh-mat', timeout=5000)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'2-baucua-{th}')
            await theme('kem')
            # Bets: cua 1+1, then chip 5 on cá
            await page.click('.fh-sheet [data-fh="bet"][data-face="cua"]')
            await page.click('.fh-sheet [data-fh="bet"][data-face="cua"]')
            await page.click('.fh-sheet [data-fh="chip"][data-v="5"]')
            await page.click('.fh-sheet [data-fh="bet"][data-face="ca"]')
            await shot('3-bets')
            await page.click('.fh-sheet [data-fh="roll"]')
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(OUT / f'{tag}-4-shaking.png'))
            await page.wait_for_selector('.fh-sheet .fh-plate.open', timeout=10000)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'5-result-{th}')
            await theme('kem')
            # Lô tô
            await page.click('.fh-sheet [data-fh="tab"][data-tab="home"]')
            await page.click('.fh-sheet [data-fh="tab"][data-tab="lt"]')
            await page.wait_for_selector('.fh-sheet [data-fh="buy"]', timeout=5000)
            await shot('6-loto-buy')
            await page.click('.fh-sheet [data-fh="buy"]')
            await page.wait_for_selector('.fh-sheet .fh-ticketcard', timeout=10000)
            await page.click('.fh-sheet [data-fh="fast"]')
            await poll("(document.querySelector('.fh-callrow small')?.textContent||'').match(/Đã gọi (\\d+)/)?.[1]>=8")
            await page.evaluate("document.querySelectorAll('.fh-sheet .fh-cell.called').forEach(b=>b.click())")
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'7-loto-{th}')
            await theme('kem')
            # Keep marking until a row is full (Kinh!) or a neighbour shouts
            for _ in range(200):
                done = await page.evaluate("""()=>{
                  document.querySelectorAll('.fh-sheet .fh-cell.called').forEach(b=>b.click());
                  const k=document.querySelector('.fh-sheet [data-fh="kinh"]');
                  if(k&&!k.disabled){k.click();return 'kinh';}
                  return document.querySelector('.fh-sheet .fh-buy')?'over':'';
                }""")
                if done:
                    break
                await page.wait_for_timeout(400)
            await page.wait_for_selector('.fh-sheet .fh-buy', timeout=15000)
            await shot('8-loto-end')
            # Chiếu trong (a normal round, then a raid swapped in on the wire)
            await page.click('.fh-sheet [data-fh="tab"][data-tab="home"]')
            await page.click('.fh-sheet [data-fh="tab"][data-tab="xd"]')
            await page.wait_for_selector('.fh-sheet .fh-sides', timeout=5000)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'9-chieu-{th}')
            await theme('kem')

            async def raid(route):
                resp = await route.fetch()
                data = await resp.json()
                if isinstance(data.get('result'), dict) and data['result'].get('fair', {}).get('game') == 'xd':
                    data['result']['fair'] = dict(game='xd', raid=True, side='chan', stake=20, fine=10, net=-30, cooldown=120, titles=['f_raid'], points=0)
                await route.fulfill(response=resp, body=json.dumps(data))
            await page.click('.fh-sheet [data-fh="stake"][data-v="20"]')
            await page.route('**/api/command', raid)
            await page.click('.fh-sheet [data-fh="shakexd"]')
            await page.wait_for_selector('.fh-sheet .fh-raid', timeout=10000)
            await page.unroute('**/api/command')
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'10-raid-{th}')
            await theme('kem')
            await page.click('.fh-sheet [data-fh="raidok"][data-tab="bc"]')
            # Bảng vàng (the points pill)
            await page.click('.fh-sheet .fh-pts')
            await page.wait_for_selector('.fh-sheet .fh-board, .fh-sheet .fh-wait', timeout=10000)
            await poll("!!document.querySelector('.fh-sheet .fh-board')", 8)
            for th in ('kem', 'dem'):
                await theme(th)
                await shot(f'11-board-{th}')
            await theme('kem')
            await page.click('.fh-sheet [data-fh="close"]')
            # The phone's "Thêm" menu → Khu phố hub shows the entry
            if w == 390:
                await page.evaluate("document.querySelector('[data-action=\"v4Menu\"]')?.click()")
                await page.wait_for_timeout(400)
                await page.evaluate("document.querySelector('#rail [data-action=\"v4Group\"][data-group=\"pho\"]')?.click()")
                await shot('12-menu')
            await ctx.close()
        await browser.close()


async def closed(base, db, errors):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport=dict(width=390, height=844))
        page = await ctx.new_page()
        page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
        page.on('pageerror', lambda e: errors.append(str(e)))
        await page.goto(base)
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
        seed(db, token, neighbours=False)
        await page.reload()
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await page.wait_for_timeout(1200)
        await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await page.evaluate("document.querySelector('#rail [data-action=\"fair\"]')?.click()")
        await page.wait_for_selector('.fh-sheet[open]', timeout=10000)
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(OUT / '390x844-13-closed.png'))
        await browser.close()


def main():
    from browser_housing import server
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    os.environ['MNL_FAIR_START'] = vn_today()
    with server() as (base, db):
        asyncio.run(walk(base, db, errors))
    os.environ['MNL_FAIR_START'] = vn_today(-6)   # ended yesterday: "đã tàn"
    with server() as (base, db):
        asyncio.run(closed(base, db, errors))
    if errors:
        print('console errors:', *errors, sep='\n  ')
        sys.exit(1)
    print('ok:', OUT)


if __name__ == '__main__':
    main()
