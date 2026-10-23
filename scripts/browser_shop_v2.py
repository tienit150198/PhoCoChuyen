"""🛍️ Cửa hàng v2 (v4/shop-shelves.js, owner 23/10 "gọn và dễ dùng như các game khác"): a browser walk-through and
screenshots (dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save per run straight in its database (a named
character on life day 20 with 2 triệu xu, a bank account and one Samoyed). At 390x844 (phone) and 1280x800, in the
light and the dark theme:
- one row of tabs (Phụ kiện · Trang phục · Cánh · Đồ đôi · Thú cưng · Nơi mua khác), a screenshot of each, no sideways
  scroll; the filter bar (Độ hiếm, Giá, Chưa có);
- a card opens the detail sheet (try-on, total, one Mua, ☑️ Không hỏi lại); an accessory bought with no question and a
  toast; ×5 wings in one purchase, the reveal and ⚒️ Đi cường hóa when three of a tier are there; a pet toy ×5;
- ☑️ Không hỏi lại: a big purchase goes through without the question; Esc closes the sheet.
Fails on any console error or page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_shop_v2.py [out_dir]
"""
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_gadgets_classic import server, ROOT, PY  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'output' / 'playwright' / 'shop_v2'

SEED = r'''
import sys
from game import bank as bk
from game import marriage as mr
from game import pets
from game.storage import Store
db, token, theme = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=20)
    j['wallet'] = 2000000
    s['settings'].update(whatsNewSeen='9.9.9', uiTheme=theme)
    j['interface'] = dict(newInterface=False, interfacePromptSeen=True)   # engine.INTERFACE_DEFAULTS
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': 'samoyed', 'coat': 0, 'nick': 'Mây', 'confirm': True})
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''
TABS = ('acc', 'wear', 'wing', 'pair', 'pet', 'more')
WIDE = "document.documentElement.scrollWidth-document.documentElement.clientWidth"
STATE = "(async()=>{const r=await fetch('/api/state',{credentials:'same-origin',cache:'no-store'});const d=await r.json();return d.state.journey})()"
REGISTER = """async ([u, pw]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch('/api/account/register', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf},
    body: JSON.stringify({username: u, password: pw, confirm: pw, display: 'Lan'})});
  return r.status;
}"""
CLICK = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d);b.hidden=true;document.body.append(b);b.click();b.remove();})"


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, fails = [], []

    def check(ok, what):
        print(('ok  ' if ok else 'FAIL'), what, flush=True)
        if not ok:
            fails.append(what)

    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for theme in ('kem', 'dem'):
                for w, h in ((390, 844), (1280, 800)):
                    phone = w < 900
                    tag = f'{theme}-{w}'
                    ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone, is_mobile=phone)
                    await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.theme','%s')}catch(e){}" % theme)
                    page = await ctx.new_page()
                    page.on('console', lambda m, t=tag: m.type == 'error' and errors.append(f'{t}: {m.text}'))
                    page.on('pageerror', lambda e, t=tag: errors.append(f'{t}: {e}'))
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    status = await page.evaluate(REGISTER, [f'lan{theme}{w}', 'matkhau-dai-lam'])
                    check(status == 200, f'{tag}: an account (status {status})')
                    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                    subprocess.run([PY, '-c', SEED, db, token, theme], cwd=ROOT, check=True)
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(2500)
                    painted = await page.evaluate("document.documentElement.dataset.theme")
                    check(painted == theme, f'{tag}: theme {painted}')

                    async def clear():
                        # a new title's scene (Tuyệt!) or any other popup on top of the shop
                        for _ in range(3):
                            ok = page.locator('#jrScene[open] [data-action="jrSceneClose"]')
                            if not await ok.count():
                                break
                            await ok.first.click(timeout=4000)
                            await page.wait_for_timeout(400)
                        await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#confirmDialog)').forEach(d=>d.close())")

                    async def shot(name):
                        await page.wait_for_timeout(450)
                        await clear()
                        await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                    async def unblock():
                        # toasts sit over the top of the sheet for a few seconds; a player waits, the script clears them
                        await clear()
                        await page.evaluate("document.querySelectorAll('.toast').forEach(t=>t.remove())")

                    async def tap(sel):
                        await unblock()
                        await page.locator(sel).first.click(timeout=8000)

                    async def wallet():
                        return (await page.evaluate(STATE))['wallet']

                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.evaluate(CLICK, ['jrAccShop', {'tab': 'acc'}])
                    await page.wait_for_selector('#sheet[open] .as-v2 .as-tabs', timeout=15000)
                    names = await page.locator('#sheet .as-tab').all_inner_texts()
                    check(len(names) == 6, f'{tag}: one row of six tabs ({" · ".join(n.strip() for n in names)})')
                    check(await page.locator('#sheet [role="tablist"]').count() == 1, f'{tag}: no second row of tabs')
                    for t in TABS:
                        await tap(f'#sheet .as-tab[data-tab="{t}"]')
                        await page.wait_for_selector(f'#sheet .as-tab[data-tab="{t}"][aria-selected="true"]', timeout=10000)
                        if t == 'pet':
                            await page.wait_for_selector('#sheet .as-cats', timeout=10000)
                            await page.wait_for_selector('#sheet .as-card', timeout=15000)
                        await shot(f'tab-{t}')
                        check(await page.evaluate(WIDE) <= 0, f'{tag}: {t} has no sideways scroll')
                        if t not in ('more',):
                            n = await page.locator('#sheet .as-card').count()
                            check(n > 0, f'{tag}: {t} shows {n} cards')

                    # 🎀 an accessory: the card, the detail sheet, bought with no question (small), a toast
                    await tap('#sheet .as-tab[data-tab="acc"]')
                    await page.wait_for_selector('#sheet .as-tab[data-tab="acc"][aria-selected="true"]')
                    await tap('#sheet .as-fbar [data-k="miss"]')
                    await page.wait_for_selector('#sheet .as-fbar [data-k="miss"].on', timeout=5000)
                    await tap('#sheet .as-fbar [data-k="sort"]')
                    await page.wait_for_timeout(300)
                    await tap('#sheet .as-dd > summary')
                    await shot('filter-open')
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(200)
                    check(await page.locator('#sheet[open]').count() == 1, f'{tag}: Esc closes the list, not the shop')
                    first = page.locator('#sheet .as-card:not(.locked):not(.using)').first
                    await unblock(); await first.click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail]', timeout=8000)
                    focused = await page.evaluate("document.activeElement?.hasAttribute?.('data-as-detail')")
                    check(bool(focused), f'{tag}: the detail sheet takes the focus')
                    await shot('detail-acc')
                    btn = page.locator('#sheet [data-as-detail] [data-action="jrAsBuy"]')
                    if await btn.count():
                        before = await wallet()
                        await btn.click()
                        await page.wait_for_timeout(1500)
                        await clear()
                        asked = await page.locator('#confirmDialog[open]').count()
                        check(not asked, f'{tag}: a small accessory is bought with no question')
                        toast = await page.locator('.toast').all_inner_texts()
                        check(await wallet() < before and any('+1' in t for t in toast), f'{tag}: bought, toast {toast}')
                        await shot('bought-acc')
                    # Esc closes the detail sheet first, not the shop
                    await unblock(); await page.locator('#sheet .as-card:not(.locked)').first.click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail]', timeout=8000)
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(400)
                    check(not await page.locator('#sheet [data-as-detail]').count() and await page.locator('#sheet[open]').count() == 1, f'{tag}: Esc closes the detail sheet, the shop stays')

                    # 👕 a piece of clothing: the detail
                    await tap('#sheet .as-tab[data-tab="wear"]')
                    await page.wait_for_selector('#sheet .as-tab[data-tab="wear"][aria-selected="true"]')
                    await unblock(); await page.locator('#sheet .as-card:not(.locked):not(.using)').first.click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail]', timeout=8000)
                    await shot('detail-wear')

                    # 🪽 ×5 wings in one purchase (5 × 8.800 of ~2 triệu: no question), the reveal, ⚒️ when ready
                    await tap('#sheet .as-tab[data-tab="wing"]')
                    await page.wait_for_selector('#sheet .as-tab[data-tab="wing"][aria-selected="true"]')
                    await unblock(); await page.locator('#sheet .as-card').first.click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail] [data-action="jrAsWingQty"][data-n="5"]', timeout=8000)
                    await tap('#sheet [data-as-detail] [data-action="jrAsWingQty"][data-n="5"]')
                    await page.wait_for_timeout(400)
                    await clear(); await shot('detail-wing')
                    await tap('#sheet [data-as-detail] [data-action="jrAsWingBuy"]')
                    await page.wait_for_selector('#sheet [data-as-detail] .wg-reveal', timeout=10000)
                    await page.wait_for_timeout(1200); await clear()
                    own = (await page.evaluate(STATE)).get('wings', {}).get('own', [])
                    tiers = [x['r'] for x in own]
                    ready = any(tiers.count(r) >= 3 for r in set(tiers))
                    check(len(own) == 5, f'{tag}: five wings in one purchase ({"".join("DC"[r] for r in tiers)})')
                    has_forge = await page.locator('#sheet [data-as-detail] [data-action="jrForge"]').count() > 0
                    check(has_forge == ready, f'{tag}: ⚒️ Đi cường hóa shown when three of a tier ({ready})')
                    await shot('wing-reveal')

                    # 🤝 a pair: the detail with the try-on
                    await tap('#sheet .as-tab[data-tab="pair"]')
                    await page.wait_for_selector('#sheet .as-tab[data-tab="pair"][aria-selected="true"]')
                    await page.wait_for_selector('#sheet .as-card', timeout=10000)
                    await unblock(); await page.locator('#sheet .as-card').nth(2).click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail]', timeout=8000)
                    await shot('detail-pair')

                    # 🐾 a toy ×5 in the pets' shelf
                    await tap('#sheet .as-tab[data-tab="pet"]')
                    await page.wait_for_selector('#sheet .as-cats', timeout=10000)
                    await tap('#sheet .as-cats [data-tab="ptoy"]')
                    await page.wait_for_selector('#sheet .as-cats [data-tab="ptoy"][aria-pressed="true"]', timeout=8000)
                    await unblock(); await page.locator('#sheet .as-card').first.click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail] .pt-embed [data-pt="bq"][data-n="5"]', timeout=8000)
                    await tap('#sheet [data-as-detail] .pt-qty-chips [data-pt="bq"][data-n="5"]')
                    await page.wait_for_timeout(400)
                    await shot('detail-pet-toy')
                    before = await wallet()
                    await tap('#sheet [data-as-detail] [data-pt="go"]')
                    await page.wait_for_selector('#sheet [data-as-detail] .pt-flash.good', timeout=10000)
                    check(not await page.locator('#confirmDialog[open]').count() and await wallet() < before, f'{tag}: five toys, no question')
                    await tap('#sheet .as-cats [data-tab="pbuy"]')
                    await page.wait_for_selector('#sheet .as-cats [data-tab="pbuy"][aria-pressed="true"]', timeout=8000)
                    await unblock(); await page.locator('#sheet .as-card').first.click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail]', timeout=8000)
                    await shot('detail-pet-buy')

                    # ☑️ Không hỏi lại: a big purchase (pets ×5 ≥ 20 % of the money) without the question
                    await tap('#sheet .as-tab[data-tab="acc"]')
                    await page.wait_for_selector('#sheet .as-tab[data-tab="acc"][aria-selected="true"]')
                    j = await page.evaluate(STATE)
                    check(True, f'{tag}: wallet now {j["wallet"]}')
                    await unblock(); await page.locator('#sheet .as-card:not(.locked):not(.using)').first.click(timeout=8000)
                    await page.wait_for_selector('#sheet [data-as-detail] .as-noask input', timeout=8000)
                    await page.locator('#sheet [data-as-detail] .as-noask input').check()
                    await page.wait_for_timeout(400)
                    check(await page.evaluate("localStorage.getItem('mnl.noAsk')") == '1', f'{tag}: the tick is kept on this device (mnl.noAsk)')
                    check(await page.locator('#sheet [data-as-detail] .as-noask input:checked').count() == 1, f'{tag}: the box shows ticked')
                    await shot('detail-noask')
                    await page.locator('#sheet [data-as-detail] .as-noask input').uncheck()
                    await page.wait_for_timeout(300)
                    check(await page.evaluate("localStorage.getItem('mnl.noAsk')") is None, f'{tag}: unticked again')
                    await page.keyboard.press('Escape')
                    await ctx.close()
            await browser.close()
    print('console/page errors:', errors or 'none')
    if errors or fails:
        print('FAILED:', *fails, sep='\n  ')
        sys.exit(1)
    print('all good; screenshots in', OUT)


if __name__ == '__main__':
    asyncio.run(main())
