"""🍚 No bụng · 😴 Tỉnh táo: a browser walk-through of one work day (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server, seeds one save (a named character on life day 4 at the tạp hóa, the
shift open), then in the browser: the morning bars, the lunch strip at 11:30 on the shop clock (one tap), the
afternoon, closing the day, the evening sheet (dinner, bedtime, "như mọi khi"), the night, and the next morning.
Screenshots at 390x844 and 1280x800, light (kem) and dark (dem), plus one English pass on the phone.

    python scripts/browser_needs.py [out_dir] [vi|en]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_needs_shots'
CAREER = 'grocery'
ONLY = (sys.argv[2] if len(sys.argv) > 2 else '').lower()   # 'vi' (the four themed passes) or 'en' (English only)


def mutate(db: str, token: str, fn) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def _replace(s, t):
    s.clear()
    s.update(t)


def act(s, action, **p):
    from game.engine import apply_action
    t, _ = apply_action(s, CAREER, action, p)
    _replace(s, t)


def tick_to(s, minute):
    from game import dayclock as dc
    for _ in range(80):
        if dc.minute_now(s['careers'][CAREER], CAREER) >= minute:
            return
        act(s, 'advance')


def seed(theme='kem', lang='vi'):
    def fn(s):
        from game import journey as jr
        from game import whats_new as wn
        j = s['journey']
        s['name'] = 'Lan'
        j.update(gender='female', intro=True, wallet=140)
        jr._welcome_settings(s)
        s['settings'].update(uiTheme=theme, lang=lang, tutorialDone=True, whatsNewSeen=wn.LATEST)
        act(s, 'select_career')
        act(s, 'start_day')
        for _ in range(3):              # three quiet days first: no first-day welcome, no onboarding hush
            act(s, 'end_day', carry_event=True)
            act(s, 'start_day')
        tick_to(s, 9 * 60 + 30)
    return fn


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for theme in ('kem', 'dem') if ONLY in ('', 'vi') else ():
                for w, h in ((390, 844), (1280, 800)):
                    ctx = await browser.new_context(viewport=dict(width=w, height=h))
                    await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0')}catch(e){}")
                    page = await ctx.new_page()
                    page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                    mutate(db, token, seed(theme))
                    tag = f'{theme}-{w}x{h}'

                    async def shot(name):
                        await page.wait_for_timeout(500)
                        await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                    async def calm():
                        for _ in range(6):
                            hit = False
                            for sel in ('[data-wn="close"]:visible', '[data-action="jrSceneClose"]:visible', '#lfScene[open] [data-action="lfLater"]'):
                                b = page.locator(sel)
                                if await b.count():
                                    await b.first.click()
                                    await page.wait_for_timeout(350)
                                    hit = True
                            if not hit:
                                break

                    async def reload():
                        await page.reload()
                        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                        await page.wait_for_timeout(1500)
                        await calm()
                        await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                        await page.evaluate("document.getElementById('sheet').open&&document.getElementById('sheet').close()")
                        await page.wait_for_timeout(300)

                    await reload()
                    # 1. Morning: the bars beside tinh thần (status sheet + Đời thường).
                    await page.click('#topbar [data-action="status"]')
                    await page.wait_for_selector('#sheet[open] .st-grid', timeout=8000)
                    await shot('1-status')
                    await page.click('#sheet [data-action="stView"][data-view="life"]')
                    await page.wait_for_selector('#sheet[open] .nd-bars', timeout=8000)
                    await shot('2-life-sheet')
                    # 2. Lunch: the clock at 11:30, the strip in the calm card.
                    mutate(db, token, lambda s: tick_to(s, 11 * 60 + 30))
                    await reload()
                    await page.wait_for_selector('.nd-lunch', timeout=8000)
                    await shot('3-lunch')
                    await page.click('.nd-lunch [data-meal="binh_dan"]')
                    await page.wait_for_timeout(900)
                    assert not await page.locator('.nd-lunch').count(), 'lunch strip still there'
                    await shot('4-after-lunch')
                    # 3. The afternoon, then close the day ("Khép ca" in the status sheet's clock card is a
                    # career-specific place; the calm card's "end" shows only once the work is done, so the day
                    # is closed on the server and the summary opened from the calm card).
                    mutate(db, token, lambda s: (tick_to(s, 18 * 60), act(s, 'end_day', carry_event=True)))
                    await reload()
                    await calm()
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                    await page.evaluate("document.querySelector('#taskHUD [data-action=\"summary\"]').click()")
                    await page.wait_for_selector('#sheet[open] .summary-v6', timeout=10000)
                    await page.wait_for_timeout(800)
                    await calm()
                    await page.evaluate("document.querySelector('#sheet .sheet-body')?.scrollTo(0,99999)")
                    await shot('5-summary')
                    # 4. The evening sheet.
                    await page.click('#sheet .sheet-foot [data-action="evening"]')
                    await page.wait_for_selector('#sheet[open] .nd-eve', timeout=8000)
                    await shot('6-evening')
                    await page.click('#sheet [data-action="ndMeal"][data-meal="an_vat"]')
                    await page.click('#sheet [data-action="ndBed"][data-bed="1320"]')
                    await page.evaluate("document.querySelector('#sheet .nd-beds')?.scrollIntoView({block:'center'})")
                    await shot('7-evening-picked')
                    await page.click('#sheet [data-action="ndEve"]')
                    await page.wait_for_selector('#sheet .nd-night', timeout=8000)
                    await shot('8-good-night')
                    # 5. The next morning.
                    await page.click('#sheet [data-action="start"]')
                    await page.wait_for_timeout(1200)
                    await calm()
                    await shot('9-morning')
                    await ctx.close()
            if ONLY == 'vi':
                await browser.close()
                print('errors:', [e for e in errors if 'favicon' not in e] or 'none')
                return
            # English, phone, the usual one-tap evening.
            ctx = await browser.new_context(viewport=dict(width=390, height=844), locale='en-US')
            await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')

            def en(s):
                seed('kem', 'en')(s)
                tick_to(s, 11 * 60 + 30)
            mutate(db, token, en)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(2500)
            await page.screenshot(path=str(OUT / 'en-390-lunch.png'))

            def evening(s):
                tick_to(s, 17 * 60)
                act(s, 'end_day', carry_event=True)
            mutate(db, token, evening)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(2000)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await page.click('[data-action="evening"]')
            await page.wait_for_selector('#sheet[open] .nd-eve', timeout=8000)
            await page.wait_for_timeout(800)
            await page.screenshot(path=str(OUT / 'en-390-evening.png'))
            await page.click('#sheet [data-action="ndUsual"]')
            await page.wait_for_selector('#sheet .nd-night', timeout=8000)
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUT / 'en-390-good-night.png'))
            # Vietnamese left on these screens (the i18n layer's QA list), for the needs words only.
            misses = await page.evaluate("[...(globalThis.__i18nMisses||[])]")
            ours = ('bụng', 'tỉnh táo', 'ăn', 'ngủ', 'bữa', 'cơm', 'tối', 'trưa')
            print('i18n misses (needs):', [m for m in misses if any(w in m.lower() for w in ours)] or 'none')
            await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')


if __name__ == '__main__':
    asyncio.run(main())
