"""🛍️ Cửa hàng and ⚒️ Cường hóa (v4/acc-shop.js, 2.5.5): a browser walk-through (dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save per run straight in its database (a named
character on life day 20 with 2 triệu xu, a bank account and one Samoyed). For the classic interface and the new map,
at 390x844 and 1280x800:
- opens Cửa hàng from the menu (classic: its own entry in the rail / "Thêm"; new map: Tiện ích → Cửa hàng), switches
  every shelf of 👤 Cho bạn, 🐾 Thú cưng and 🏠 Nhà & xe, and buys an accessory, wings, a piece of clothing, a pet item
  and a pet gear piece;
- opens ⚒️ Cường hóa from the menu, switches its shelves, and runs ⚡ Cường hóa nhanh once on the wings and once on
  the pet gear (the question names what is used and the fee, never the odds);
- checks the pets' dialog still sells and that the old links land on their shelf (🤝, Tủ đồ's clothes button).
The first run also shows the "Có gì mới" card of 2.5.5. Fails on any console error or page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_shop.py [out_dir]
"""
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_gadgets_classic import server, ROOT, PY  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'output' / 'playwright' / 'shop'

SEED = r'''
import sys
from game import bank as bk
from game import marriage as mr
from game import pets
from game.storage import Store
db, token, new = sys.argv[1], sys.argv[2], sys.argv[3] == '1'
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=20)
    j['wallet'] = 2000000
    s['settings']['whatsNewSeen'] = '2.5.4'
    j['interface'] = dict(newInterface=new, interfacePromptSeen=True)   # engine.INTERFACE_DEFAULTS
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': 'samoyed', 'coat': 0, 'nick': 'Mây', 'confirm': True})
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''
ME = ('acc', 'pair', 'wing', 'wear')
PET = ('pbuy', 'pwear', 'pwing', 'ptoy', 'pgear')
FORGE = ('wing', 'plab', 'pward', 'pgear')
WIDE = "document.documentElement.scrollWidth-document.documentElement.clientWidth"
# the wallet as the server has it (the sheet's money chip rounds on phones)
WALLET = "(async()=>{const r=await fetch('/api/state',{credentials:'same-origin',cache:'no-store'});const d=await r.json();return Number(d.state?.journey?.wallet)||0})()"
WINGS = "(async()=>{const r=await fetch('/api/state',{credentials:'same-origin',cache:'no-store'});const d=await r.json();return d.state?.journey?.wings?.own||[]})()"
# an account (🤝 pairs live on accounts: charms.js refreshCharms, game/friend_charms.py)
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
            first = True
            for mode in ('classic', 'new'):
                for w, h in ((390, 844), (1280, 800)):
                    phone = w < 900
                    tag = f'{mode}-{w}x{h}'
                    ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone, is_mobile=phone)
                    await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.tut.tips','done')}catch(e){}")
                    page = await ctx.new_page()
                    page.on('console', lambda m, t=tag: m.type == 'error' and errors.append(f'{t}: {m.text}'))
                    page.on('pageerror', lambda e, t=tag: errors.append(f'{t}: {e}'))
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    status = await page.evaluate(REGISTER, [f'lan{mode}{w}', 'matkhau-dai-lam'])
                    check(status == 200, f'{tag}: an account (status {status})')
                    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                    subprocess.run([PY, '-c', SEED, db, token, '1' if mode == 'new' else '0'], cwd=ROOT, check=True)
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(2500)

                    async def shot(name):
                        await page.wait_for_timeout(500)
                        await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                    async def popups():
                        for _ in range(6):
                            b = page.locator('#wnDialog[open] [data-wn="close"].btn, [data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                            if not await b.count():
                                return
                            await page.wait_for_timeout(600)   # a tap in the card's first 450 ms is ignored
                            await b.first.click()
                            await page.wait_for_timeout(500)

                    try:
                        await page.wait_for_selector('#wnDialog[open]', timeout=8000)
                        if first:
                            await shot('0-whatsnew')
                            card = await page.inner_text('#wnDialog')
                            check('Cửa hàng riêng' in card and 'Cường hóa nhanh' in card, f'{tag}: Có gì mới 2.5.5 tells about Cửa hàng and Cường hóa')
                    except Exception:  # noqa: BLE001 - another popup first
                        pass
                    await popups()
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.wait_for_timeout(500)

                    async def clear():   # other first-visit cards (🔥 x3 của tuần, a new title…) that open over the sheet
                        await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#confirmDialog)').forEach(d=>d.close())")

                    async def tap(sel, name):
                        """Click like a player; a card that opened over it (🔥 x3, a title) is closed first, a stuck
                        click leaves a screenshot."""
                        for i in range(3):
                            await clear()
                            try:
                                await page.locator(sel).first.click(timeout=6000)
                                return
                            except Exception:  # noqa: BLE001
                                await page.screenshot(path=str(OUT / f'{tag}-stuck-{name}-{i}.png'))
                                print(tag, 'stuck on', sel, 'open dialogs:', await page.evaluate("[...document.querySelectorAll('dialog[open]')].map(d=>d.id||d.className).join(',')"), flush=True)
                        await page.locator(sel).first.click(timeout=6000)

                    async def from_menu(action, name):
                        """Open an entry of the menu the way a player does; checks it is a top-level entry."""
                        await clear()
                        await page.evaluate("document.getElementById('sheet')?.open&&document.getElementById('sheet').close()")
                        await page.wait_for_timeout(300)
                        if mode == 'classic':
                            if phone:
                                await tap('[data-action="v4Menu"]', f'menu-{action}')
                                await page.wait_for_timeout(600)
                            entry = page.locator(f'#rail > [data-action="{action}"]').first
                            check(await entry.is_visible(), f'{tag}: {name} is its own entry in the menu')
                            check(not await page.locator(f'#rail .rail-sub [data-action="{action}"]').count(), f'{tag}: {name} is in no hub')
                        else:
                            await page.wait_for_selector('.iso-tools > summary', timeout=60000)
                            entry = page.locator(f'.iso-tools-options .iso-tool[data-action="{action}"]')
                            for _ in range(4):   # a first-visit card (🔥 x3 của tuần) closes Tiện ích when it opens
                                await page.wait_for_timeout(800)
                                await clear()
                                if not await page.locator('#isoHUD .iso-tools[open]').count():
                                    await page.click('.iso-tools > summary')
                                    await page.wait_for_timeout(600)
                                if await entry.is_visible():
                                    break
                            check(await entry.is_visible(), f'{tag}: Tiện ích has {name} on top')
                            check(not await page.locator(f'[data-iso-group] [data-action="{action}"]').count(), f'{tag}: {name} is not repeated in a Tiện ích group')
                        await shot(f'1-menu-{action}')
                        if mode == 'classic':
                            await tap(f'#rail > [data-action="{action}"]', action)
                        else:
                            await entry.click(timeout=8000)

                    async def tab(t, action='jrAsTab'):
                        await tap(f'#sheet [data-action="{action}"][data-tab="{t}"]', f'tab-{t}')
                        await page.wait_for_selector(f'#sheet [data-action="{action}"][data-tab="{t}"][aria-selected="true"]', timeout=10000)
                        await page.wait_for_timeout(500)

                    async def group(g):
                        await tap(f'#sheet [data-action="jrAsGroup"][data-group="{g}"]', f'group-{g}')
                        await page.wait_for_selector(f'#sheet [data-action="jrAsGroup"][data-group="{g}"][aria-selected="true"]', timeout=10000)
                        await page.wait_for_timeout(500)

                    async def confirm(name='confirm'):
                        await page.wait_for_selector('#confirmDialog[open]', timeout=8000)
                        text = await page.inner_text('#confirmDialog')
                        await shot(name)
                        await page.click('#confirmDialog [data-action="confirmYes"]')
                        await page.wait_for_timeout(1500)
                        return text

                    async def maybe_confirm():
                        try:
                            await page.wait_for_selector('#confirmDialog[open]', timeout=1500)
                            await page.click('#confirmDialog [data-action="confirmYes"]')
                        except Exception:  # noqa: BLE001 - under 1.000 xu: no question
                            pass

                    async def wallet():
                        return await page.evaluate(WALLET)

                    # ---- 🛍️ Cửa hàng, from the menu ----
                    await from_menu('jrAccShop', 'Cửa hàng')
                    await page.wait_for_selector('#sheet[open] .as .wd-tabs', timeout=15000)
                    await shot('2-shop')
                    check('Cửa hàng' in await page.inner_text('#sheet .sheet-head'), f'{tag}: the sheet is Cửa hàng')
                    check(await page.evaluate(WIDE) <= 0, f'{tag}: no sideways scroll')
                    for t in ME:
                        await tab(t)
                        await shot(f'3-me-{t}')
                        check(await page.evaluate(WIDE) <= 0, f'{tag}: {t} has no sideways scroll')
                    await group('pet')
                    for t in PET:
                        await tab(t)
                        await page.wait_for_selector('#sheet .pt-embed', timeout=15000)
                        await shot(f'4-pet-{t}')
                        check(await page.evaluate(WIDE) <= 0, f'{tag}: {t} has no sideways scroll')
                    if await page.locator('#sheet [data-action="jrAsGroup"][data-group="more"]').count():
                        await group('more')
                        n = await page.locator('#sheet .as-more').count()
                        await shot('4-more')
                        check(n >= 1 and await page.evaluate(WIDE) <= 0, f'{tag}: 🏠 Nhà & xe shows {n} other shops')
                    else:
                        check(False, f'{tag}: 🏠 Nhà & xe group missing')

                    # ---- buy: an accessory, wings, a piece of clothing, a pet item, a pet gear piece ----
                    await group('me')
                    await tab('acc')
                    await page.locator('#sheet .wd-item:has(.wd-tag.price)').first.click()
                    await page.wait_for_selector('#sheet [data-action="jrAsBuy"]', timeout=8000)
                    before = await wallet()
                    await page.click('#sheet [data-action="jrAsBuy"]')
                    await confirm()
                    await page.wait_for_selector('#sheet .wd-item.on .wd-tag.worn', timeout=10000)
                    check(await wallet() < before, f'{tag}: an accessory bought and worn')
                    await shot('5-bought-acc')

                    await tab('wing')
                    check(not await page.locator('#sheet [data-action="jrAsWingPick"]').count(), f'{tag}: the Cánh shelf buys and wears, the ghép is in Cường hóa')
                    before = await wallet()
                    # 🛒 many at once (owner 23/10): ×5 on the first style, one confirm, one jr_pet_wing_buy (D or C each:
                    # five make three of one tier for ⚒️)
                    await tap('#sheet .wg-style [data-action="jrAsWingQty"][data-n="5"]', 'wingqty')
                    label = await page.inner_text('#sheet .wg-style [data-action="jrAsWingBuy"] >> nth=0')
                    check('×5' in label, f'{tag}: the quantity shows on the buy button ({label.strip()})')
                    await shot('6-wing-qty')
                    await tap('#sheet [data-action="jrAsWingBuy"]', 'wingbuy')
                    text = await confirm('confirm-wing')
                    check('5 đôi' in text and 'trả một lần' in text, f'{tag}: one confirm with the total of the five')
                    await page.wait_for_selector('#sheet .wg-reveal [data-action="jrAsWingReveal"]', timeout=10000)
                    await shot('6-bought-wing')
                    await tap('#sheet [data-action="jrAsWingReveal"]', 'reveal')
                    await page.wait_for_selector('#sheet .wg-reveal', state='detached', timeout=8000)
                    own = await page.evaluate(WINGS)
                    check(len(own) == 5 and await wallet() < before, f'{tag}: five pairs of wings bought in one purchase ({"".join("DC"[x["r"]] for x in own)})')
                    await shot('6-wings')
                    check(await page.locator('#sheet [data-action="jrForge"][data-tab="wing"]').count() == 1, f'{tag}: the Cánh shelf links to ⚒️ Cường hóa')

                    await tab('wear')
                    await page.locator('#sheet .wd-item:has(.wd-tag.price)').first.click()
                    await page.wait_for_selector('#sheet [data-action="jrAsClBuy"]', timeout=8000)
                    before = await wallet()
                    await page.click('#sheet [data-action="jrAsClBuy"]')
                    await confirm()
                    await page.wait_for_selector('#sheet .wd-item.on .wd-tag.worn', timeout=10000)
                    check(await wallet() < before, f'{tag}: a piece of clothing bought and worn')
                    await shot('7-bought-clothes')

                    # 🧺 the cart: two accessories and a piece of clothing, one jr_wd_buy items
                    await tab('acc')
                    await tap('#sheet [data-action="jrAsMulti"]', 'multi')
                    for i in range(2):
                        await page.locator('#sheet .wd-item:has(.wd-tag.price):not(.in-cart)').first.click()
                        await page.wait_for_timeout(300)
                    await tab('wear')
                    await page.locator('#sheet .wd-item:has(.wd-tag.price):not(.in-cart)').first.click()
                    await page.wait_for_selector('#sheet .as-cart', timeout=8000)
                    head = await page.inner_text('#sheet .as-cart-head')
                    check('3 món' in head, f'{tag}: the cart holds pieces from both shelves ({head.strip()})')
                    await shot('7-cart')
                    before = await wallet()
                    await tap('#sheet [data-action="jrAsBuyMany"]', 'buymany')
                    text = await confirm('confirm-cart')
                    check('trả một lần' in text, f'{tag}: one confirm for the cart')
                    await page.wait_for_selector('#sheet .as-cart', state='detached', timeout=10000)
                    check(await wallet() < before, f'{tag}: three pieces bought in one purchase')
                    # 🤝 two pairs at once
                    await tab('pair')
                    await page.wait_for_selector('#sheet [data-action="jrAsPairQty"][data-n="2"]', timeout=10000)
                    await tap('#sheet [data-action="jrAsPairQty"][data-n="2"]', 'pairqty')
                    before = await wallet()
                    await tap('#sheet .as-kind [data-action="jrAsPairBuy"]', 'pairbuy')
                    await confirm('confirm-pairs')
                    await page.wait_for_selector('#sheet .as-box', timeout=10000)
                    box = await page.inner_text('#sheet .as-box h3')
                    check('2/' in box and await wallet() < before, f'{tag}: two pairs bought in one purchase ({box.strip()})')
                    await shot('7-pairs')

                    await group('pet')
                    await tab('ptoy')
                    await page.click('#sheet .pt-embed [data-pt="item"]')
                    await page.wait_for_selector('#sheet .pt-embed [data-pt="bq"][data-n="5"]', timeout=8000)
                    await page.click('#sheet .pt-embed .pt-qty-chips [data-pt="bq"][data-n="5"]')
                    await page.wait_for_timeout(400)
                    before = await wallet()
                    await page.click('#sheet .pt-embed [data-pt="go"]')
                    await confirm('confirm-toys')
                    await page.wait_for_selector('#sheet .pt-embed .pt-flash.good', timeout=10000)
                    flash = (await page.inner_text('#sheet .pt-embed .pt-flash')).strip()
                    check('×5' in flash and await wallet() < before, f'{tag}: five toys bought in one purchase ({flash})')
                    await shot('8-toys')
                    await tab('pwear')
                    await page.click('#sheet .pt-embed [data-pt="wk"]')
                    await page.wait_for_selector('#sheet .pt-embed .pt-wsel', timeout=8000)
                    before = await wallet()
                    await page.click('#sheet .pt-embed [data-pt="go"]')
                    await maybe_confirm()
                    await page.wait_for_selector('#sheet .pt-embed .pt-flash.good', timeout=10000)
                    flash = (await page.inner_text('#sheet .pt-embed .pt-flash')).strip()
                    await shot('8-bought-pet-item')
                    check(await wallet() < before and bool(flash), f'{tag}: a pet item bought ({flash})')

                    await tab('pgear')
                    before = await wallet()
                    await page.click('#sheet .pt-embed [data-pt="go"]')
                    await maybe_confirm()
                    await page.wait_for_selector('#sheet .pt-embed .pt-flash.good', timeout=10000)
                    await shot('9-bought-gear')
                    check(await wallet() < before, f'{tag}: a pet gear piece bought')

                    # ---- ⚒️ Cường hóa, from the menu ----
                    await from_menu('jrForge', 'Cường hóa')
                    await page.wait_for_selector('#sheet[open] .fg .fg-kinds', timeout=15000)
                    await page.wait_for_function("[...document.querySelectorAll('#sheet .fg-kind small')].every(x=>x.textContent!=='…')", timeout=10000)
                    check('Cường hóa' in await page.inner_text('#sheet .sheet-head'), f'{tag}: the sheet is Cường hóa')
                    kinds = await page.locator('#sheet .fg-kind').all_inner_texts()
                    check(len(kinds) == 4 and 'đôi' in kinds[0], f'{tag}: what can be ghép, by kind, counted: {" | ".join(k.replace(chr(10), " ") for k in kinds)}')
                    for t in FORGE:
                        await tab(t, 'jrAsForgeTab')
                        await page.wait_for_selector('#sheet .fg-quick, #sheet .pt-quick', timeout=15000)
                        await shot(f'10-forge-{t}')
                        check(await page.evaluate(WIDE) <= 0, f'{tag}: ⚒️ {t} has ⚡ Cường hóa nhanh, no sideways scroll')
                    await tab('wing', 'jrAsForgeTab')
                    quick = page.locator('#sheet [data-action="jrAsWingQuick"]')
                    check(await quick.is_enabled(), f'{tag}: ⚡ on the wings is ready (three of one tier)')
                    before, n0 = await wallet(), len(await page.evaluate(WINGS))
                    await quick.click()
                    text = await confirm('11-quick-wing-confirm')
                    check('Dùng:' in text and 'Phí' in text and '%' not in text, f'{tag}: ⚡ asks with the wings used and the fee, no odds')
                    await page.wait_for_timeout(800)
                    n1 = len(await page.evaluate(WINGS))
                    check(await wallet() < before, f'{tag}: ⚡ ran one wing fusion ({"thành" if n1 == n0 - 2 else "trượt"}, {n0} → {n1} pairs)')
                    await clear()
                    if await page.locator('#sheet [data-action="jrAsWingReveal"]').count():
                        await page.locator('#sheet [data-action="jrAsWingReveal"]').click(timeout=8000)
                    await shot('12-quick-wing-done')

                    await tab('pgear', 'jrAsForgeTab')
                    await page.wait_for_selector('#sheet .pt-embed .pt-quick', timeout=15000)
                    pq = page.locator('#sheet .pt-embed [data-pt="quick"]')
                    check(await pq.is_enabled(), f'{tag}: ⚡ on the pet gear is ready')
                    before = await wallet()
                    await pq.click()
                    text = await confirm('13-quick-gear-confirm')
                    check('%' not in text, f'{tag}: ⚡ gear question without odds ({text.splitlines()[0] if text else ""})')
                    await page.wait_for_selector('#sheet .pt-embed .pt-flash:not(:empty)', timeout=10000)
                    check(await wallet() < before, f'{tag}: ⚡ strengthened one gear piece')
                    await shot('14-quick-gear-done')

                    # the old pets UI still sells (players are used to it)
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.evaluate(CLICK, ['pets', {'tab': 'shop'}])
                    await page.wait_for_selector('.pt-sheet[open] .pt-tabs', timeout=10000)
                    check(await page.locator('.pt-sheet[open] [data-pt="kind"][data-kind="wear"]').count() == 1, f'{tag}: the pets dialog keeps its own shop')
                    await shot('15-pets-dialog')
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    # the old links land on their shelf: marriage.js 🤝, Tủ đồ's clothes buy button (tab wear + the piece)
                    await page.evaluate(CLICK, ['jrAccShop', {'tab': 'pair'}])
                    await page.wait_for_selector('#sheet[open] [data-action="jrAsTab"][data-tab="pair"][aria-selected="true"]', timeout=10000)
                    check(True, f'{tag}: jrAccShop tab=pair lands on 🤝')
                    await page.evaluate(CLICK, ['jrWardrobe', {}])
                    await page.wait_for_selector('#sheet[open] [data-action="jrWdTab"][data-tab="top"]', timeout=10000)
                    await page.click('#sheet [data-action="jrWdTab"][data-tab="top"]')
                    await page.wait_for_timeout(400)
                    await page.locator('#sheet .wd-item:has(.wd-tag.price)').first.click()
                    btn = page.locator('#sheet .wd-actions [data-action="jrAccShop"][data-tab="wear"]')
                    check(await btn.count() == 1, f'{tag}: Tủ đồ\'s buy button opens Cửa hàng')
                    await btn.click()
                    await page.wait_for_selector('#sheet[open] [data-action="jrAsClBuy"]', timeout=10000)
                    await shot('16-from-wardrobe')
                    check(True, f'{tag}: … on 👕 Trang phục with the piece on the mirror')
                    first = False
                    await ctx.close()
            await browser.close()
    print('console/page errors:', errors or 'none')
    if errors or fails:
        print('FAILED:', *fails, sep='\n  ')
        sys.exit(1)
    print('all good; screenshots in', OUT)


if __name__ == '__main__':
    asyncio.run(main())
