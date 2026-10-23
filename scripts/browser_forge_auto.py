"""⚒️ Cường hóa v2 (owner 23/10: "gọn và dễ dùng như các game khác"): a browser walk-through (dev tool, needs playwright +
chromium). Before it, the 2.5.6 ⚡ card walk-through (git history of this file).

Runs the real app on a throwaway story-mode server and seeds one save per run straight in its database (a named
character with 50 triệu xu, a bank account, seven Samoyeds of ranks D and C, twelve wings of tiers D, C and S, six
pet clothes and four pet gear pieces, one wing 🔒 locked). At 390x844 and 1280x800, light and dark (mnl.theme 'dem'):
- ⚒️ Cường hóa: the kind tabs, the grid (rank colours, ⚡ dots, 🔒), ⚡ Ghép tất cả, the three short ticks; no sideways
  scroll;
- a tap on a wing: the panel (rank → next rank, what changes, the slots 3/3, the fee, Cường hóa / Cường hóa tối đa);
  the sheet stays where it was (no jump to the top);
- Cường hóa: one question, ONE command, the result card; 🔒 Khóa / Mở khóa (the save's forge_locks);
- ⚡ Ghép tất cả: one question, every kind's ⚡ in turn, one result card (lượt, thành công, trượt, xu đã tiêu);
- ⏩ Bỏ qua hiệu ứng (mnl.forgeFast), 🕶️ Ẩn tên (settings forgeAnon).
Fails on any console error or page error. Screenshots in out_dir.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_forge_auto.py [out_dir]
"""
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_gadgets_classic import server, ROOT, PY  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else ROOT / 'output' / 'playwright' / 'forge_v2'

SEED = r'''
import sys
import game
from game import bank as bk
from game import marriage as mr
from game import pets, pet_tiers as px, wings as W
from game.storage import Store
db, token, new = sys.argv[1], sys.argv[2], sys.argv[3] == '1'
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=20)
    j['wallet'] = 50000000
    j['stats']['max_wallet'] = 50000000
    s['settings']['whatsNewSeen'] = game.__version__
    j['interface'] = dict(newInterface=new, interfacePromptSeen=True)
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': 'samoyed', 'coat': 0, 'nick': 'Mây', 'qty': 7, 'confirm': True})
    for i, p in enumerate(px.all_pets(s)):
        px._record(s, p)['r'] = 0 if i < 4 else 1
    pets.action(s, 'jr_pet_wing_buy', {'style': 'buom', 'qty': 9, 'confirm': True})
    pets.action(s, 'jr_pet_wing_buy', {'style': 'rong', 'qty': 3, 'confirm': True})
    for i, x in enumerate(W.get(s)['own']):
        x['r'] = 0 if i < 6 else 1 if i < 9 else 4
    pets.action(s, 'jr_pet_wbuy', {'id': 'no_hong', 'qty': 6, 'confirm': True})
    pets.action(s, 'jr_pet_gear_buy', {'slot': 'giay', 'model': 0, 'rank': 0, 'qty': 4, 'confirm': True})
    pets.action(s, 'jr_pet_lock', {'ids': [W.get(s)['own'][5]['id']], 'on': True})
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''
WIDE = "document.documentElement.scrollWidth-document.documentElement.clientWidth"
STATE = "(async()=>{const r=await fetch('/api/state',{credentials:'same-origin',cache:'no-store'});return (await r.json()).state})()"
WALLET = f"{STATE}.then(s=>(Number(s?.journey?.wallet)||0)+(Number(s?.journey?.bank?.balance)||0))"
REGISTER = """async ([u, pw]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch('/api/account/register', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf},
    body: JSON.stringify({username: u, password: pw, confirm: pw, display: 'Lan'})});
  return r.status;
}"""
CLICK = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d);b.hidden=true;document.body.append(b);b.click();b.remove();})"
# the sheet's scrolling box and where it is
SCROLLER = """(sel)=>{let el=document.querySelector(sel);while(el&&el!==document.body){const st=getComputedStyle(el);
  if(/(auto|scroll)/.test(st.overflowY)&&el.scrollHeight>el.clientHeight+4)return el;el=el.parentElement;}return null;}"""
GET_Y = f"(sel)=>{{const el=({SCROLLER})(sel);return el?el.scrollTop:-1;}}"
SET_Y = f"([sel,y])=>{{const el=({SCROLLER})(sel);if(el)el.scrollTop=y;return el?el.scrollTop:-1;}}"
RUNS = [('new', 390, 844, 'light')] if '--one' in sys.argv else [('new', 390, 844, 'light'), ('new', 390, 844, 'dark'), ('classic', 390, 844, 'light'), ('new', 1280, 800, 'light'), ('new', 1280, 800, 'dark')]


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
            for n, (mode, w, h, theme) in enumerate(RUNS):
                tag = f'{mode}-{w}x{h}-{theme}'
                phone = w < 600
                ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1,
                                                has_touch=phone, is_mobile=phone)
                await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.tut.tips','done');"
                                          + ("localStorage.setItem('mnl.theme','dem')" if theme == 'dark' else "localStorage.removeItem('mnl.theme')")
                                          + "}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m, t=tag: m.type == 'error' and errors.append(f'{t}: {m.text}'))
                page.on('pageerror', lambda e, t=tag: errors.append(f'{t}: {e}'))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                status = await page.evaluate(REGISTER, [f'forge{n}{mode}', 'matkhau-dai-lam'])
                check(status == 200, f'{tag}: an account (status {status})')
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                subprocess.run([PY, '-c', SEED, db, token, '1' if mode == 'new' else '0'], cwd=ROOT, check=True)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(3000)

                async def clear():
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#confirmDialog)').forEach(d=>d.close())")

                async def shot(name):
                    await page.wait_for_timeout(450)
                    if not name.endswith('confirm'):
                        await clear()
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                async def confirm(name=None):
                    await page.wait_for_selector('#confirmDialog[open]', timeout=8000)
                    text = await page.inner_text('#confirmDialog')
                    if name:
                        await shot(name)
                    await page.wait_for_timeout(500)   # the button wakes up a moment later (double tap guard)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    return text

                for _ in range(6):   # any first-visit card
                    b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                    if not await b.count():
                        break
                    await page.wait_for_timeout(600)
                    await b.first.click()
                    await page.wait_for_timeout(500)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

                # ---- the overview ----
                await page.evaluate(CLICK, ['jrForge', {'tab': 'wing'}])
                await page.wait_for_selector('#sheet[open] .fv .fv-kinds', timeout=15000)
                await page.wait_for_selector('#sheet .fv-kind.on[data-tab="wing"]', timeout=10000)
                await page.wait_for_timeout(2500)   # first-visit cards (🔥 x3 của tuần) open late
                await shot('1-overview')
                check(await page.evaluate(WIDE) <= 0, f'{tag}: no sideways scroll')
                prefs = ' '.join((await page.inner_text('#sheet .fv-prefs')).split())
                check(prefs == 'Không hỏi lại Ẩn tên Bỏ qua hiệu ứng', f'{tag}: three short ticks ({prefs})')
                check(await page.locator('#sheet .fv-tile').count() == 12, f'{tag}: a tile per wing')
                check(await page.locator('#sheet .fv-tile .fv-dot').count() > 0, f'{tag}: ⚡ dots')
                check(await page.locator('#sheet .fv-tile .fv-lk').count() == 1, f'{tag}: 🔒 on the locked wing')
                check(await page.locator('#sheet [data-action="jrFgAll"]').is_enabled(), f'{tag}: ⚡ Ghép tất cả ready')
                body = await page.inner_text('#sheet .fv')
                check('tỉ lệ' not in body and 'tỷ lệ' not in body, f'{tag}: no odds')

                # ---- a tap: the panel; the sheet stays where it was ----
                tiles = page.locator('#sheet .fv-tile')
                last = tiles.nth(await tiles.count() - 1)
                await last.scroll_into_view_if_needed()
                y0 = await page.evaluate(GET_Y, '#sheet .fv-grid')
                await last.click()
                await page.wait_for_selector('#fv-panel', timeout=8000)
                await page.wait_for_timeout(700)
                y1 = await page.evaluate(GET_Y, '#sheet .fv-grid')
                check(y1 > 0 or y0 <= 0, f'{tag}: the panel opens without jumping to the top ({y0} → {y1})')
                panel = ' '.join((await page.inner_text('#fv-panel')).split())
                check('3/3' in panel and 'Phí' in panel and 'Cường hóa' in panel, f'{tag}: the panel ({panel[:120]})')
                check(await page.evaluate("document.activeElement?.id") == 'fv-ptitle', f'{tag}: focus on the panel title')
                await page.evaluate(SET_Y, ['#sheet .fv-grid', 0])
                await shot('2-panel')
                check(await page.evaluate(WIDE) <= 0, f'{tag}: panel: no sideways scroll')

                # ---- Cường hóa: one question, one command, the result card ----
                before = await page.evaluate(WALLET)
                await page.click('#fv-panel [data-action="jrFgOne"]')
                text = await confirm('3-one-confirm' if n == 0 else None)
                check('Phí' in text and '%' not in text, f'{tag}: one question, no odds')
                await page.wait_for_selector('#sheet .fv-res', timeout=15000)
                check(await page.evaluate(WALLET) < before, f'{tag}: paid once')
                res = ' '.join((await page.inner_text('#sheet .fv-res')).split())
                check('lượt' in res and 'xu đã tiêu' in res, f'{tag}: the result ({res[:100]})')
                await page.evaluate(SET_Y, ['#sheet .fv-res', 0])
                await shot('4-one-result')

                # ---- 🔒 Khóa ----
                await page.click('#sheet [data-action="jrFgRes"]')
                await page.wait_for_timeout(300)
                if not await page.locator('#fv-panel').count():
                    await page.locator('#sheet .fv-tile').first.click()
                    await page.wait_for_selector('#fv-panel', timeout=8000)
                was = len((await page.evaluate(STATE)).get('journey', {}).get('forge_locks') or [])
                await page.click('#fv-panel [data-action="jrFgLock"]')
                await page.wait_for_timeout(1200)
                now = len((await page.evaluate(STATE)).get('journey', {}).get('forge_locks') or [])
                check(now == was + 1 or now == was - 1, f'{tag}: 🔒 saved ({was} → {now})')
                check(await page.locator('#fv-panel .fv-lock[aria-pressed="true"]').count() == (1 if now > was else 0), f'{tag}: the button says it')
                await page.evaluate(SET_Y, ['#sheet .fv-grid', 0])
                await shot('5-lock')

                # ---- ⚡ Ghép tất cả ----
                await page.evaluate(SET_Y, ['#sheet .fv-grid', 0])
                before = await page.evaluate(WALLET)
                await page.click('#sheet [data-action="jrFgAll"]')
                text = await confirm('6-all-confirm' if n == 0 else None)
                check('Tiêu tối đa' in text and '🔒' in text, f'{tag}: Ghép tất cả: one question ({" ".join(text.split())[:100]})')
                await page.wait_for_selector('#sheet .fv-res', timeout=30000)
                await page.wait_for_function("!document.querySelector('#sheet [data-action=\"jrFgAll\"]')?.textContent.includes('⚒️')", timeout=30000)
                res = ' '.join((await page.inner_text('#sheet .fv-res')).split())
                check('lượt' in res and 'thành công' in res and 'trượt' in res and 'xu đã tiêu' in res, f'{tag}: one result card ({res[:120]})')
                check(await page.evaluate(WALLET) < before, f'{tag}: Ghép tất cả paid')
                await page.evaluate(SET_Y, ['#sheet .fv-res', 0])
                await shot('7-all-result')
                check(await page.evaluate(WIDE) <= 0, f'{tag}: result: no sideways scroll')

                # ---- the ticks ----
                await page.locator('#sheet [data-fv-pref="fast"]').check()
                await page.wait_for_timeout(400)
                check(await page.evaluate("localStorage.getItem('mnl.forgeFast')") == '1', f'{tag}: Bỏ qua hiệu ứng stored')
                await page.locator('#sheet [data-fv-pref="anon"]').check()
                await page.wait_for_timeout(1500)
                anon = (await page.evaluate(STATE)).get('settings', {}).get('forgeAnon')
                check(anon is True, f'{tag}: Ẩn tên saved ({anon})')
                for t in ('plab', 'pward', 'pgear'):
                    await clear()
                    try:
                        await page.click(f'#sheet .fv-kind[data-tab="{t}"]', timeout=8000)
                    except Exception:  # noqa: BLE001
                        await page.screenshot(path=str(OUT / f'{tag}-x-tab-{t}.png'))
                        raise
                    await page.wait_for_selector(f'#sheet .fv-kind.on[data-tab="{t}"]', timeout=8000)
                    check(await page.locator('#sheet .fv-tile').count() > 0, f'{tag}: {t} tiles')
                    if t == 'pgear':
                        await page.locator('#sheet .fv-tile').first.click()
                        await page.wait_for_selector('#fv-panel', timeout=8000)
                        await shot('8-gear-panel')
                    check(await page.evaluate(WIDE) <= 0, f'{tag}: {t} no sideways scroll')
                await ctx.close()
            await browser.close()
    for e in errors:
        print('ERROR', e)
    if errors or fails:
        print(f'{len(fails)} failed checks, {len(errors)} page errors')
        sys.exit(1)
    print('all good')


if __name__ == '__main__':
    asyncio.run(main())
