"""🧩 Ghép ba Phố Mây, levels 201–300 (2.5.7): a browser walk-through (dev tool, needs `pip install playwright` + chromium,
TEST_DATABASE_URL), adapted from scripts/browser_tile_match.py.

Seeds a story save that has cleared 239 levels (stars on the map), then at 390 × 844 light and dark, 360 × 780 and
1280 × 800: the lobby's level map near 200–300, level 201's 🎁 card and a revealed box, 211's 🌈 card and the joker on the
board, 221's ⛓️ card and a chained tile, 231's 💣 card and a lit bomb, a 🌈 clear (the pair, the joker and the pulled
third tile), and level 240 played through: the win card with its ⭐ stars and the 🎁 chest. Checks: no console error, no
sideways scroll (the document AND the game sheet), every tile inside the stage.

    python scripts/browser_tile_300.py [out_dir]
"""
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_tile300_shots'
FIT = """()=>{const st=document.querySelector('.tm-stage');if(!st)return 'no stage';const r=st.getBoundingClientRect();
  const out=[];for(const el of document.querySelectorAll('.tm-tile:not(.tm-gone)')){const b=el.getBoundingClientRect();
    if(b.left<r.left-1||b.right>r.right+1||b.top<r.top-1||b.bottom>r.bottom+1)out.push(el.dataset.id);}
  return out.length?'outside: '+out.slice(0,8).join(','):'';}"""
WIDE = """()=>{const bad=[];const d=document.documentElement;if(d.scrollWidth>innerWidth+1)bad.push('document '+d.scrollWidth);
  for(const sel of ['.tm-sheet','.tm-root','.tm-body','.tm-grid','.tm-play','.tm-boosts']){const el=document.querySelector(sel);
    if(el&&el.scrollWidth>el.clientWidth+1)bad.push(sel+' '+el.scrollWidth+'>'+el.clientWidth);}
  return bad.join(', ');}"""
DONE = 239


def mutate(db, token, fn):
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def seed(theme):
    def fn(s):
        from game import journey as jr, tile_match as tm, whats_new as wn
        j = s['journey']
        s['name'] = 'Lan'
        j.update(gender='female', intro=True, wallet=24000, life_day=6)
        jr._welcome_settings(s)
        s['settings'].update(uiTheme=theme, tutorialDone=True, whatsNewSeen=wn.LATEST)
        j['interface'] = dict(newInterface=False, interfacePromptSeen=True)
        j['tile'] = dict(lv=100, d=tm.today(), n=0, u={}, cur=dict(lv=100, t=0, b={}, p={}))
        j['tile_hi'] = dict(lv=100)
        j['tile_hi2'] = dict(lv=DONE - 200)
        j['tile_st'] = ''.join('3' if n % 4 else '2' if n % 3 else '1' for n in range(1, DONE + 1))
    return fn


async def main():
    from playwright.async_api import async_playwright
    from game import tile_match as tm
    OUT.mkdir(parents=True, exist_ok=True)
    errors, problems = [], []
    passes = [('390-light', 390, 844, 'kem', True), ('390-dark', 390, 844, 'dem', True), ('360-light', 360, 780, 'kem', False),
              ('1280-light', 1280, 800, 'kem', True)]
    with server() as (base, db):
        async with async_playwright() as pw:
            exe = os.environ.get('PW_CHROMIUM')
            browser = await pw.chromium.launch(**({'executable_path': exe} if exe else {}))
            for tag, w, h, theme, full in passes:
                phone = w < 500
                ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=phone, has_touch=phone, bypass_csp=True)
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0');localStorage.setItem('mnl.x3.week','blocked')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(f'[{tag}] {m.text}'))
                page.on('pageerror', lambda e: errors.append(f'[{tag}] {e}'))

                async def snap(name, wait=350):
                    await page.wait_for_timeout(wait)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))
                    bad = await page.evaluate(WIDE)
                    if bad:
                        problems.append(f'[{tag}] {name}: sideways {bad}')
                    if await page.query_selector('.tm-stage'):
                        bad = await page.evaluate(FIT)
                        if bad:
                            problems.append(f'[{tag}] {name}: {bad}')

                async def tap(t, wait=45):
                    await page.dispatch_event(f'.tm-tile[data-id="{t}"]', 'pointerdown')
                    await page.wait_for_timeout(wait)

                async def open_level(n, intro=True, shot=None):
                    # the page's own "play" action, from wherever the dialog is (a map cell does the same in the lobby)
                    await page.evaluate("""(n)=>{const b=document.createElement('button');b.dataset.tm='play';b.dataset.lv=String(n);
                      b.id='tm-go';document.querySelector('.tm-sheet .tm-root').append(b);b.click();b.remove();}""", n)
                    await page.wait_for_function(f"()=>document.querySelector('.tm-sheet h2')?.textContent.includes('{n}')&&document.querySelector('.tm-sheet .tm-tile')", timeout=8000)
                    if intro:
                        await page.wait_for_selector('.tm-intro', timeout=4000)
                        if shot:
                            await snap(shot, 600)
                    else:
                        await page.wait_for_timeout(300)
                    while await page.query_selector('.tm-intro [data-tm="intro"]'):
                        await page.click('.tm-intro [data-tm="intro"]')
                        await page.wait_for_timeout(150)
                    await page.wait_for_timeout(400)

                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                mutate(db, token, seed(theme))
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1200)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate("""()=>{const b=document.createElement('button');b.dataset.action='tileMatch';b.id='tm-open';
                  b.style.cssText='position:fixed;left:0;top:0;width:4px;height:4px;opacity:0;z-index:2147483647';document.body.append(b);}""")
                await page.click('#tm-open')
                await page.wait_for_selector('.tm-sheet[open] .tm-hero', timeout=8000)
                await page.evaluate("()=>{const g=document.querySelector('.tm-grid'),n=g&&g.querySelector('.tm-now');if(g&&n)g.scrollTop=n.offsetTop-g.offsetTop-60;}")
                await snap('01-map', 500)

                # 🎁 201: the card, then a box revealed
                lv = tm.level(201)
                await open_level(201, shot='02-intro-box')
                boxes = [t for t, x in enumerate(lv['tiles']) if x[4] & tm.BOX]
                g = tm.Game(lv)
                for m in lv['solution']:
                    if any(g.open(b) for b in boxes):
                        break
                    g.tap(m)
                    await tap(m, 30)
                await snap('03-box-revealed', 700)
                if full:
                    # 🌈 211
                    lv = tm.level(211)
                    await open_level(211, shot='04-intro-joker')
                    jk = next(t for t, x in enumerate(lv['tiles']) if x[4] & tm.JOKER)
                    g = tm.Game(lv)
                    shown = False
                    for m in lv['solution']:
                        if not shown and g.open(jk):
                            await snap('05-joker-on-board', 500)
                            shown = True
                        if m == jk:
                            break
                        g.tap(m)
                        await tap(m, 30)
                    await tap(jk, 10)
                    await snap('06-joker-clear', 160)
                    # ⛓️ 221
                    lv = tm.level(221)
                    await open_level(221, shot='07-intro-chain')
                    g = tm.Game(lv)
                    for m in lv['solution'][:6]:
                        g.tap(m)
                        await tap(m, 30)
                    await snap('08-chain', 500)
                    # 💣 231
                    lv = tm.level(231)
                    await open_level(231, shot='09-intro-bomb')
                    g = tm.Game(lv)
                    for m in lv['solution']:
                        if g.lit:
                            break
                        g.tap(m)
                        await tap(m, 30)
                    for m in lv['solution'][g.taps:g.taps + 2]:
                        g.tap(m)
                        await tap(m, 30)
                    await snap('10-bomb-lit', 500)
                # 240 played through: ⭐ and the 🎁 chest
                lv = tm.level(DONE + 1)
                await open_level(DONE + 1, intro=False)
                for m in lv['solution']:
                    await tap(m, 25)
                try:
                    await page.wait_for_selector('.tm-done.win', timeout=10000)
                except Exception:
                    await page.screenshot(path=str(OUT / f'{tag}-debug.png'))
                    print(await page.evaluate("()=>({h2:document.querySelector('.tm-sheet h2')?.textContent,done:document.querySelector('.tm-done')?.outerHTML?.slice(0,300),left:document.querySelectorAll('.tm-tile:not(.tm-gone)').length,flash:document.querySelector('.tm-flash')?.textContent})"))
                    raise
                await snap('11-win-stars-chest', 1600)
                await ctx.close()
            await browser.close()
    report = dict(errors=errors, problems=problems, shots=sorted(p.name for p in OUT.glob('*.png')))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if errors or problems else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
