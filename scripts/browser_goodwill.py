"""💛 Thân thiết với NPC (game/goodwill.py, public/js/v4/closeness.js): a browser walk-through (dev tool, needs playwright
+ chromium, TEST_DATABASE_URL).

Runs the real server on a throwaway namespace, seeds a story save at the tạp hóa with a few close people (Cô Ba như
người nhà, Bé Tí thân thiết, a customer như người nhà), then on a phone (390×844) and desktop (1280×800): 👥 Người quen
with the first-time guide card (Tiếp → Xong), today's việc nhờ, Cô Ba's profile (perk ladder, weekly favour, gift
picker with her prices and the hidden jar), the favour, a customer's profile (pay percent, 🔒 ??? rows). Checks: nothing
overflows sideways, no page error.

    python scripts/browser_goodwill.py [out_dir]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402
from browser_needs import mutate, act  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_goodwill_shots'
WIDE = '()=>document.documentElement.scrollWidth-innerWidth'


def seed_fn(s):
    from game import closeness as qn
    from game import journey as jr
    from game import whats_new as wn
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, wallet=300)
    jr._welcome_settings(s)
    s['settings'].update(tutorialDone=True, whatsNewSeen=wn.LATEST)
    from browser_needs import CAREER  # the tạp hóa
    act(s, 'select_career')
    act(s, 'start_day')
    for pid, v in (('co_ba', 85), ('be_ti', 65), ('ba_tam', 70)):
        qn._set(s, pid, v)
    c = s['careers'][CAREER]
    npc = next(k for k, x in qn._npcs().items() if x['career_id'] == CAREER and k not in qn.ALIAS)
    c['relationships'][npc] = 85
    act(s, 'qn_chat', who=npc)


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, fails = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (1280, 800)):
                ctx = await browser.new_context(viewport=dict(width=w, height=h))
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                mutate(db, token, seed_fn)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1500)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                tag = f'{w}x{h}'

                async def shot(name):
                    await page.wait_for_timeout(600)
                    wide = await page.evaluate(WIDE)
                    if wide > 1:
                        fails.append(f'{tag} {name}: {wide}px sideways')
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'), full_page=False)

                await page.evaluate("globalThis.__mnlAct?globalThis.__mnlAct('people'):null")
                if not await page.locator('#sheet[open] .qn').count():
                    await page.evaluate("""()=>{const b=[...document.querySelectorAll('[data-action="people"]')][0];b&&b.click();}""")
                await page.wait_for_selector('#sheet[open] .qn', timeout=10000)
                await page.wait_for_selector('#sheet[open] .qn-guide', timeout=8000)
                await shot('1-guide')
                await page.click('#sheet [data-action="gwGuide"][data-go="next"]')
                await shot('2-guide-step2')
                await page.click('#sheet [data-action="gwGuide"][data-go="end"]')
                await page.wait_for_timeout(400)
                if await page.locator('#sheet .qn-guide').count():
                    fails.append(f'{tag}: guide card still there after Bỏ qua')
                await shot('3-list')
                await page.click('#sheet [data-action="qnOpen"][data-who="co_ba"]')
                await page.wait_for_selector('#sheet .qn-perks', timeout=8000)
                await shot('4-co-ba')
                await page.evaluate("document.querySelector('#sheet .qn-perks')?.scrollIntoView({block:'center'})")
                await shot('5-co-ba-perks')
                await page.click('#sheet [data-action="qnFavour"]')
                await page.wait_for_timeout(800)
                await shot('6-favour')
                await page.click('#sheet [data-action="qnPick"]')
                await page.wait_for_selector('#sheet .qn-gifts', timeout=8000)
                await page.evaluate("document.querySelector('#sheet .qn-gifts')?.scrollIntoView({block:'start'})")
                await shot('7-gifts')
                await page.click('#sheet [data-action="qnBack"]')
                await page.click('#sheet [data-action="qnTab"][data-tab="work"]')
                await page.wait_for_timeout(400)
                await shot('8-customers')
                await page.locator('#sheet .qn-list [data-action="qnOpen"]').first.click()
                await page.wait_for_selector('#sheet .qn-perks', timeout=8000)
                await page.evaluate("document.querySelector('#sheet .qn-perks')?.scrollIntoView({block:'center'})")
                await shot('9-customer-perks')
                await ctx.close()
            await browser.close()
    print('errors:', errors[:10])
    print('fails:', fails)
    print('shots in', OUT)
    return 1 if fails or errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
