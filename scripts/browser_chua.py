"""🛕 Vào chùa: a browser walk-through of the walkable pagoda (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server, seeds one save (a named character on a rằm, life day 5), then
in the browser at 390x844 (phone) and 1280x800 (desktop): the Đời thường sheet's "Vào chùa", the yard, incense at
the burner, the wish fence, the main hall, talking with thầy Huệ Minh, khấn (who and what picked by tapping), a
chant with the mõ kept on the beat (taps sent at the beats, three of twelve left out), the dining hall's vegetarian
lunch. Checks the server took each act (journey.chua.did), the wallet never moved, every hotspot of each area is
reachable, the page logged no error. Then a reduced-motion pass and an English pass (phone) that lists any
Vietnamese left on screen (build public/i18n/en.json first: python scripts/i18n_extract.py build).

    python scripts/browser_chua.py [out_dir] [--lang en]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = Path(ARGS[0]) if ARGS else ROOT.parent / '_chua_shots'
EN = '--lang' in sys.argv and sys.argv[sys.argv.index('--lang') + 1] == 'en'
REACH = """()=>{const st=__chua.state();return st.spots.filter(id=>{const r=__chua.route(id);return !r||!r.length;});}"""
BEATS = """async(skip)=>{const c=__chua.chantClock();const mo=document.querySelector('.cv-mo');
  for(let i=0;i<c.beats;i++){const wait=(c.start+i*c.period)*1000-performance.now();if(wait>0)await new Promise(r=>setTimeout(r,wait));
    if(i%4!==skip)mo.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));}}"""


def mutate(db: str, token: str, fn) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def read(db: str, token: str) -> dict:
    out = {}
    mutate(db, token, lambda s: out.update(chua=dict(s['journey'].get('chua') or {}), wallet=s['journey']['wallet'],
                                           spirit=s['journey']['life']['spirit']))
    return out


def seed(lang='vi', theme='kem', day=5):
    def fn(s):
        from game import journey as jr
        from game import whats_new as wn
        j = s['journey']
        s['name'] = 'Lan'
        j.update(gender='female', intro=True, wallet=140, life_day=day)
        j.pop('chua', None)
        jr._welcome_settings(s)
        s['settings'].update(uiTheme=theme, lang=lang, tutorialDone=True, whatsNewSeen=wn.LATEST)
        j['life']['spirit'] = 40
    return fn


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, problems, misses, sounds = [], [], set(), []
    passes = [('en', 390, 844, False, 'kem', 6)] if EN else [
        ('vi', 390, 844, False, 'kem', 5), ('vi', 1280, 800, False, 'kem', 5), ('vi', 390, 844, True, 'dem', 6)]
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for lang, w, h, reduced, theme, day in passes:
                tag = f'{lang}-{w}x{h}{"-reduced" if reduced else ""}-{theme}'
                ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=w < 500, has_touch=w < 500,
                                                reduced_motion='reduce' if reduced else 'no-preference')
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('response', lambda r: '/audio/chua/' in r.url and sounds.append((r.url.rsplit('/', 1)[-1].split('?')[0], r.status)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                mutate(db, token, seed(lang, theme, day))
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1500)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                before = read(db, token)

                async def shot(name, wait=450):
                    await page.wait_for_timeout(wait)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                async def go(spot, wait=2600):
                    await page.evaluate('(id)=>__chua.go(id)', spot)
                    await page.wait_for_timeout(200 if reduced else wait)

                async def reach(area):
                    bad = await page.evaluate(REACH)
                    if bad:
                        problems.append(f'[{tag}] {area}: unreachable {bad}')

                await page.click('#topbar [data-action="status"]')
                await page.wait_for_selector('#sheet[open]', timeout=8000)
                await page.click('#sheet [data-action="stView"][data-view="life"]')
                await page.wait_for_selector('#sheet[open] .cg-enter', timeout=8000)
                await page.evaluate("document.querySelector('#sheet .cg-enter').scrollIntoView({block:'center'})")
                await shot('01-sheet')
                await page.click('#sheet .cg-enter')
                await page.wait_for_selector('.cv-sheet[open] canvas', timeout=8000)
                await shot('02-yard', 900)
                await reach('san')
                # incense at the burner
                await go('huong')
                await page.wait_for_selector('.cv-panel:not([hidden]) [data-act="huong"]', timeout=5000)
                await shot('03-huong')
                await page.click('.cv-panel [data-act="huong"]')
                await page.wait_for_selector('.cv-panel .cv-result', timeout=8000)
                await shot('04-huong-done', 900)
                if not reduced:
                    # a wish at the fence
                    await go('nguyen')
                    await page.wait_for_selector('.cv-panel [data-act="nguyen"]', timeout=5000)
                    await shot('05-nguyen')
                # into the main hall through its door
                await go('go:dien', 3200)
                st = await page.evaluate('__chua.state()')
                if st['area'] != 'dien':
                    problems.append(f'[{tag}] the hall door did not lead in ({st["area"]})')
                    await page.evaluate("__chua.enter('dien')")
                await shot('06-hall', 600)
                await reach('dien')
                await go('npc:thay')
                await page.wait_for_selector('.cv-panel [data-cv="talk"]', timeout=5000)
                await shot('07-thay')
                await page.click('.cv-panel [data-cv="talk"]')
                await shot('07b-thay-more', 250)
                # khấn: the player picks who and what
                await go('khan')
                await page.wait_for_selector('.cv-panel [data-cv="who"]', timeout=5000)
                if await page.locator('.cv-panel [data-act="khan"]:not([disabled])').count():
                    problems.append(f'[{tag}] khấn could be sent before anything was picked')
                await page.click('.cv-panel [data-cv="who"][data-id="cha_me"]')
                if await page.locator('.cv-panel [data-cv="what"][data-id="yen_nghi"]:not([disabled])').count():
                    problems.append(f'[{tag}] yên nghỉ offered for cha mẹ')
                await page.click('.cv-panel [data-cv="what"][data-id="khoe"]')
                await page.evaluate("document.querySelector('.cv-panel .cv-prayer')?.scrollIntoView({block:'nearest'})")
                await shot('08-khan')
                await page.click('.cv-panel [data-act="khan"]')
                await page.wait_for_selector('.cv-panel .cv-result', timeout=8000)
                await shot('09-khan-done', 900)
                # tụng kinh: the mõ on the beat (every fourth beat left out: 9 of 12)
                await go('tung')
                await page.wait_for_selector('.cv-panel [data-cv="chant"]', timeout=5000)
                await page.click('.cv-panel [data-cv="chant"]')
                await page.wait_for_selector('.cv-mo', timeout=5000)
                await page.wait_for_timeout(3600)
                await page.screenshot(path=str(OUT / f'{tag}-10-chant.png'))
                await page.evaluate(BEATS, 3)
                await page.wait_for_selector('.cv-panel .cv-result', timeout=9000)
                await shot('11-chant-done', 600)
                # the dining hall (rằm: the lunch is on)
                await page.click('.cv-areas [data-id="trai"]')
                await page.wait_for_timeout(300 if reduced else 4500)
                st = await page.evaluate('__chua.state()')
                if st['area'] != 'trai':
                    problems.append(f'[{tag}] the chip did not lead to the dining hall ({st["area"]})')
                await reach('trai')
                await go('com')
                await page.wait_for_selector('.cv-panel [data-act="com"]', timeout=5000)
                await shot('12-com')
                after = read(db, token)
                did = after['chua'].get('did', [])
                for a in ('huong', 'khan', 'tung'):
                    if a not in did:
                        problems.append(f'[{tag}] {a} not done on the server: {did}')
                if after['wallet'] != before['wallet']:
                    problems.append(f'[{tag}] the wallet moved {before["wallet"]} -> {after["wallet"]}')
                if after['spirit'] <= before['spirit']:
                    problems.append(f'[{tag}] no tinh thần gained')
                print(tag, 'did', did, 'spirit', before['spirit'], '->', after['spirit'])
                if lang == 'en':
                    misses.update(await page.evaluate('[...(globalThis.__i18nMisses||[])]'))
                await page.click('.cv-head [data-cv="close"]')
                await page.wait_for_timeout(300)
                if await page.locator('.cv-sheet[open]').count():
                    problems.append(f'[{tag}] the pagoda did not close')
                await ctx.close()
            await browser.close()
    errs = [e for e in errors if 'favicon' not in e and '409 (Conflict)' not in e]   # 409: the save was changed under the page (mutate)
    bad = sorted({f'{f} {st}' for f, st in sounds if st >= 400})
    if bad:
        problems.append(f'sounds not served: {bad}')
    print('sounds fetched:', sorted({f for f, st in sounds if st < 400}) or 'none')
    for p in problems:
        print('PROBLEM', p)
    print('errors:', errs or 'none')
    if EN:
        print('untranslated:', sorted(m for m in misses) or 'none')
    sys.exit(1 if problems or errs else 0)


if __name__ == '__main__':
    asyncio.run(main())
