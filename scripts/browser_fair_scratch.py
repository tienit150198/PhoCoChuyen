"""🎟️ Vé số cào at the fair: a browser check (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server with the fair open today, seeds one save with 300 xu, then at
390x844 (and 1280x800): walks to dì Hai's stand on the fairground, buys tickets and scratches them open
  1. with the mouse (zigzag strokes over the silver),
  2. with a finger (touch pointer events),
  3. with "Cào hết";
checking that the wallet shown leaves the prize out until the silver is off, that the result line waits for it, that
the money news (v4/sounds.js) waits too, the dialog does not scroll while scratching, that the grid reads as the result (3 boxes of the prize), and that the
wallet then matches the server's. Screenshots in out_dir. Exit 1 on any problem or console error.

    python scripts/browser_fair_scratch.py [out_dir]
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_fair_scratch_shots'

WALLET = "+(document.querySelector('.fh-sheet .fh-strip b')?.textContent||'').replace(/\\D/g,'')"
STATE = "globalThis.__fairScratch?.state()"


async def run(base, db, problems, errors):
    from playwright.async_api import async_playwright
    from browser_fair import seed
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for w, h in ((390, 844), (1280, 800)):
            ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=w == 390)
            await ctx.add_init_script("try{localStorage.setItem('mnl.home','list')}catch(e){}")  # the list as home (the town is the default): the fair's row
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
            tag = f'{w}x{h}'

            async def shot(name):
                await page.wait_for_timeout(300)
                await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

            async def poll(js, timeout=10):
                for _ in range(int(timeout * 10)):
                    if await page.evaluate(js):
                        return True
                    await page.wait_for_timeout(100)
                return False

            if not await page.locator('.jr-fair-row').count():
                await page.evaluate("document.querySelector('[data-action=\"home\"]')?.click()")
                await page.wait_for_selector('.jr-fair-row', timeout=10000)
            for _ in range(4):   # what's new and the like
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(400)
            await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close());document.querySelector('.jr-fair-row').click()")
            await page.wait_for_selector('.fh-sheet[open]', timeout=10000)
            await poll("globalThis.__fairWalk?.state().on")
            await page.wait_for_timeout(600)
            if await page.locator('.fh-sheet [data-fh="giftok"]').count():   # the fair's welcome gift
                await page.click('.fh-sheet [data-fh="giftok"]')
            if not await poll("__fairWalk.state().spots.includes('xs')"):
                problems.append(f'{tag}: no vé số stand on the fairground')
            await shot('0-ground')
            await page.evaluate("__fairWalk.go('xs')")                       # walk up to dì Hai: her page opens
            if not await poll("!!document.querySelector('.fh-sheet .fh-xs')", 6):
                problems.append(f'{tag}: walking to the stand did not open it')
                await page.evaluate("document.querySelector('.fh-sheet [data-tab=\"xs\"]')?.click()")
                await page.wait_for_selector('.fh-sheet .fh-xs', timeout=5000)
            await shot('1-stall')

            async def buy(price):
                before = await page.evaluate(WALLET)
                await page.click(f'.fh-sheet [data-fh="xstier"][data-v="{price}"]')
                await page.click('.fh-sheet [data-fh="xsbuy"]')
                await page.wait_for_selector('.fh-sheet .fh-xs-cv', timeout=8000)
                await page.wait_for_timeout(250)
                st = await page.evaluate(STATE)
                shown = await page.evaluate(WALLET)
                if shown != before - price:
                    problems.append(f'{tag}: wallet shown {shown} after buying, want {before - price} (prize hidden)')
                if await page.locator('.fh-sheet .fh-xs .fh-result').count():
                    problems.append(f'{tag}: result shown before scratching')
                await page.wait_for_timeout(2200)                   # the money news (ting ting, read-out, chip) waits too
                if await page.locator('.bank-chip').count():
                    problems.append(f'{tag}: the money chip told the prize before scratching')
                t = st['ticket']
                hits = [i for i, v in enumerate(t['cells']) if t['prize'] and v == t['prize']]
                if sorted(hits) != sorted(t['hits']) or (t['prize'] and len(hits) != 3) or (not t['prize'] and max(t['cells'].count(v) for v in t['cells']) > 2):
                    problems.append(f'{tag}: the grid does not read as the result {t}')
                return before, t

            async def finish(before, t, name):
                if not await poll(f"({STATE}).done", 5):
                    problems.append(f'{tag}: {name}: not revealed')
                await page.wait_for_selector('.fh-sheet .fh-xs .fh-result', timeout=5000)
                if await page.locator('.fh-sheet .fh-xs-cv').count():
                    problems.append(f'{tag}: {name}: the silver is still there')
                if t['prize'] and await page.locator('.fh-sheet .fh-xs-cell.hit').count() != 3:
                    problems.append(f'{tag}: {name}: the 3 winning boxes are not lit')
                after = await page.evaluate(WALLET)
                if after != before - t['price'] + t['prize']:
                    problems.append(f'{tag}: {name}: wallet {after}, want {before - t["price"] + t["prize"]}')
                await shot(f'{name}-done')
                print(f'{tag} {name}: vé {t["price"]} xu, trúng {t["prize"]} xu')

            # 1. the mouse
            before, t = await buy(5)
            await shot('2-ticket')
            box = await page.locator('.fh-sheet .fh-xs-cv').bounding_box()
            top0 = await page.evaluate("document.querySelector('.fh-sheet').scrollTop")
            rows = 9
            for r in range(rows):
                y = box['y'] + box['height'] * (r + .5) / rows
                await page.mouse.move(box['x'] + 4, y)
                await page.mouse.down()
                for k in range(1, 13):
                    await page.mouse.move(box['x'] + box['width'] * k / 12 - 2, y + (6 if k % 2 else -6), steps=2)
                await page.mouse.up()
                st = await page.evaluate(STATE)
                if r == 2:
                    await shot('3-scratching')
                    if st['done'] or await page.locator('.fh-sheet .fh-xs .fh-result').count():
                        problems.append(f'{tag}: revealed after a third of the silver')
                if st['done'] or st['pct'] >= 1:
                    break
            if await page.evaluate("document.querySelector('.fh-sheet').scrollTop") != top0:
                problems.append(f'{tag}: the dialog scrolled while scratching')
            pct = await page.locator('.fh-sheet .fh-xs-pct').count()
            await finish(before, t, '4-mouse')

            # 2. a finger: touch pointer events on the canvas
            before, t = await buy(2)
            done = await page.evaluate("""async()=>{
              const cv=document.querySelector('.fh-sheet .fh-xs-cv'),b=cv.getBoundingClientRect(),wait=ms=>new Promise(r=>setTimeout(r,ms));
              const ev=(type,x,y)=>cv.dispatchEvent(new PointerEvent(type,{clientX:x,clientY:y,pointerId:7,pointerType:'touch',isPrimary:true,bubbles:true,cancelable:true,button:0,buttons:1}));
              for(let r=0;r<10&&cv.isConnected;r++){const y=b.top+b.height*(r+.5)/10;ev('pointerdown',b.left+3,y);
                for(let k=1;k<=16;k++){ev('pointermove',b.left+b.width*k/16,y+(k%2?5:-5));}ev('pointerup',b.right-3,y);await wait(30);
                if(globalThis.__fairScratch.state().done)break;}
              await wait(600);return globalThis.__fairScratch.state().done;}""")
            if not done:
                problems.append(f'{tag}: touch scratching did not reveal the ticket')
            await finish(before, t, '5-touch')

            # 3. "Cào hết"
            before, t = await buy(10)
            await page.click('.fh-sheet [data-fh="xsall"]')
            await finish(before, t, '6-all')
            if w == 390:
                await page.evaluate("document.documentElement.dataset.theme='dem'")
                await shot('7-dem')
                await page.evaluate("document.documentElement.dataset.theme='kem'")
                await page.click('.fh-sheet [data-fh="tab"][data-tab="home"]')
                await page.wait_for_timeout(500)
                await page.evaluate("document.querySelector('.fh-sheet .fh-wlist')?.setAttribute('open','')")
                await shot('8-list')
            await ctx.close()
        await browser.close()


def main():
    from browser_fair import vn_today
    from browser_housing import server
    OUT.mkdir(parents=True, exist_ok=True)
    problems, errors = [], []
    os.environ['MNL_FAIR_START'] = vn_today()
    with server() as (base, db):
        asyncio.run(run(base, db, problems, errors))
    for p in problems + [f'console: {e}' for e in errors]:
        print('✗', p)
    if problems or errors:
        sys.exit(1)
    print('ok:', OUT)


if __name__ == '__main__':
    main()
