"""⚡ Cường hóa nhanh, auto (2.5.6, owner 23/10: "cường hóa nhanh sẽ tự ghép mà cường hóa chứ sao lại cường hóa từng lần",
"nó giống ghép tự động của áo quần ấy"): a browser walk-through (dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save per run straight in its database (a named
character with 50 triệu xu, a bank account, seven Samoyeds of ranks D and C, twelve wings of tiers D, C and S, six
pet clothes and three pet gear pieces). For the classic interface and the new map at 390x844:
- the "Có gì mới" card of 2.5.6;
- ⚒️ Cường hóa → 🪽: the ⚡ card (kind, "Ghép tới hạng", "Tiêu tối đa", the button); a budget chip and a rank picked
  redraw the sheet where it was (no jump to the top, owner 23/10); one question (no odds), ONE command, the summary;
- 🧬 Ghép thú, 👗 Đồ thú cưng, 🧰 Linh kiện thú: the same card, question and summary;
- the pets' dialog shows the card too (👗).
Fails on any console error or page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_forge_auto.py [out_dir]
"""
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_gadgets_classic import server, ROOT, PY  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'output' / 'playwright' / 'forge_auto'

SEED = r'''
import sys
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
    s['settings']['whatsNewSeen'] = '2.5.5'
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
    pets.action(s, 'jr_pet_gear_buy', {'slot': 'giay', 'model': 0, 'rank': 0, 'qty': 3, 'confirm': True})
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''
WIDE = "document.documentElement.scrollWidth-document.documentElement.clientWidth"
WALLET = "(async()=>{const r=await fetch('/api/state',{credentials:'same-origin',cache:'no-store'});const d=await r.json();return (Number(d.state?.journey?.wallet)||0)+(Number(d.state?.journey?.bank?.balance)||0)})()"
REGISTER = """async ([u, pw]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch('/api/account/register', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf},
    body: JSON.stringify({username: u, password: pw, confirm: pw, display: 'Lan'})});
  return r.status;
}"""
CLICK = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d);b.hidden=true;document.body.append(b);b.click();b.remove();})"
# the sheet's scrolling box (the one around the ⚡ card) and where it is
SCROLLER = """(sel)=>{let el=document.querySelector(sel);while(el&&el!==document.body){const st=getComputedStyle(el);
  if(/(auto|scroll)/.test(st.overflowY)&&el.scrollHeight>el.clientHeight+4)return el;el=el.parentElement;}return null;}"""
GET_Y = f"(sel)=>{{const el=({SCROLLER})(sel);return el?el.scrollTop:-1;}}"
SET_Y = f"([sel,y])=>{{const el=({SCROLLER})(sel);if(el)el.scrollTop=y;return el?el.scrollTop:-1;}}"
# a chip brought to the middle of the sheet (so the click needs no scrolling), then where the sheet is
CENTER = f"([sel,chip])=>{{const c=[...document.querySelectorAll(sel)].find(b=>b.textContent.trim()===chip);if(c)c.scrollIntoView({{block:'center'}});const el=({SCROLLER})(sel);return el?el.scrollTop:-1;}}"


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
            for mode in ('classic', 'new'):
                w, h = 390, 844
                tag = f'{mode}-{w}x{h}'
                ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2, has_touch=True, is_mobile=True)
                await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.tut.tips','done')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m, t=tag: m.type == 'error' and errors.append(f'{t}: {m.text}'))
                page.on('pageerror', lambda e, t=tag: errors.append(f'{t}: {e}'))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                status = await page.evaluate(REGISTER, [f'forge{mode}', 'matkhau-dai-lam'])
                check(status == 200, f'{tag}: an account (status {status})')
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                subprocess.run([PY, '-c', SEED, db, token, '1' if mode == 'new' else '0'], cwd=ROOT, check=True)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(2500)

                async def clear():
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#confirmDialog)').forEach(d=>d.close())")

                async def shot(name):
                    await page.wait_for_timeout(500)
                    if not name.endswith('confirm') and not name.startswith('0-'):
                        await clear()
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                async def confirm(name):
                    await page.wait_for_selector('#confirmDialog[open]', timeout=8000)
                    text = await page.inner_text('#confirmDialog')
                    await shot(name)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(1500)
                    return text

                async def wallet():
                    return await page.evaluate(WALLET)

                try:
                    await page.wait_for_selector('#wnDialog[open]', timeout=8000)
                    await shot('0-whatsnew')
                    card = await page.inner_text('#wnDialog')
                    check('Cường hóa nhanh tự ghép liên tục' in card, f'{tag}: Có gì mới 2.5.6 tells about ⚡')
                except Exception:  # noqa: BLE001
                    check(False, f'{tag}: Có gì mới 2.5.6 shown')
                for _ in range(6):   # close it as a player does (marks it read), then any other first-visit card
                    b = page.locator('#wnDialog[open] [data-wn="close"].btn, [data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                    if not await b.count():
                        break
                    await page.wait_for_timeout(600)   # a tap in the card's first 450 ms is ignored
                    await b.first.click()
                    await page.wait_for_timeout(500)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.wait_for_timeout(500)

                async def forge(t):
                    await clear()
                    await page.evaluate(CLICK, ['jrForge', {'tab': t}])
                    await page.wait_for_selector('#sheet[open] .fg .fg-kinds', timeout=15000)
                    await page.wait_for_selector(f'#sheet [data-action="jrAsForgeTab"][data-tab="{t}"][aria-selected="true"]', timeout=10000)

                # ---- 🪽 wings ----
                await forge('wing')
                await page.wait_for_selector('#sheet .fg-auto', timeout=15000)
                await shot('1-wing-card')
                check(await page.evaluate(WIDE) <= 0, f'{tag}: 🪽 no sideways scroll')
                go = page.locator('#sheet [data-action="jrAsWingAuto"]')
                label = (await go.inner_text()).strip()
                check(await go.is_enabled() and 'tiêu tối đa' in label, f'{tag}: 🪽 the button says the most to spend ({label})')
                body = await page.inner_text('#sheet .fg-auto')
                check('%' not in body and 'tỉ lệ' not in body, f'{tag}: 🪽 no odds on the card')
                prefs = ' '.join((await page.inner_text('#sheet .fg-prefs')).split())
                check(prefs == 'Không hỏi lại Ẩn tên', f'{tag}: two short ticks, no help text ({prefs})')
                check(await page.locator('#sheet .fg-intro').count() == 0, f'{tag}: no long intro')
                # no jump: scroll a bit, pick a chip and a rank; the sheet stays where it was
                await page.wait_for_timeout(2500)   # first-visit cards (🔥 x3 của tuần) open late
                await clear()
                y0 = await page.evaluate(CENTER, ['#sheet .fg-auto [data-action="jrAsWingBud"]', '×2'])
                await page.locator('#sheet .fg-auto [data-action="jrAsWingBud"]', has_text='×2').first.click()
                await page.wait_for_timeout(600)
                y1 = await page.evaluate(GET_Y, '#sheet .fg-auto')
                check(y0 > 0 and abs(y1 - y0) <= 2, f'{tag}: 🪽 a budget chip keeps the scroll ({y0} → {y1})')
                await page.select_option('#sheet [data-as-sel="watop"]', '4')
                await page.wait_for_timeout(600)
                y2 = await page.evaluate(GET_Y, '#sheet .fg-auto')
                body = await page.inner_text('#sheet .fg-auto')
                check(abs(y2 - y0) <= 2, f'{tag}: 🪽 "Ghép tới hạng" keeps the scroll ({y0} → {y2})')
                check('⚠️' not in body, f'{tag}: 🪽 up to S: no loss warning')
                await shot('2-wing-to-S')
                await page.select_option('#sheet [data-as-sel="watop"]', '7')
                await page.wait_for_timeout(600)
                check('⚠️' in await page.inner_text('#sheet .fg-auto'), f'{tag}: 🪽 up to Huyền thoại: the loss warning')
                await page.evaluate(SET_Y, ['#sheet .fg-auto', 0])
                before = await wallet()
                await clear()
                await go.click()
                text = await confirm('3-wing-confirm')
                check('Tiêu tối đa' in text and 'trượt' in text.lower() and '%' not in text, f'{tag}: 🪽 one question, what a miss loses, no odds')
                await page.wait_for_selector('#sheet .fg-ares', timeout=15000)
                res = await page.inner_text('#sheet .fg-ares')
                check('lượt ghép' in res and 'xu đã tiêu' in res, f'{tag}: 🪽 the summary ({" ".join(res.split())[:120]})')
                check(await wallet() < before, f'{tag}: 🪽 paid once')
                await shot('4-wing-result')

                # ---- 🧬 🧰 👗 ----
                for t, name in (('plab', 'lab'), ('pward', 'ward'), ('pgear', 'gear')):
                    await forge(t)
                    await page.wait_for_selector('#sheet .pt-embed .pt-auto', timeout=15000)
                    await shot(f'5-{name}-card')
                    check(await page.evaluate(WIDE) <= 0, f'{tag}: {name} no sideways scroll')
                    go = page.locator(f'#sheet .pt-embed [data-pt="auto"][data-kind="{name}"]')
                    check(await go.count() == 1 and await go.is_enabled(), f'{tag}: {name} ⚡ ready')
                    await clear()
                    y0 = await page.evaluate(CENTER, ['#sheet .pt-auto [data-pt="abud"]', '×2'])
                    await page.locator('#sheet .pt-auto [data-pt="abud"]', has_text='×2').first.click()
                    await page.wait_for_timeout(600)
                    y1 = await page.evaluate(GET_Y, '#sheet .pt-auto')
                    check(y0 > 0 and abs(y1 - y0) <= 2, f'{tag}: {name} a budget chip keeps the scroll ({y0} → {y1})')
                    await page.evaluate(SET_Y, ['#sheet .pt-auto', 0])
                    before = await wallet()
                    await clear()
                    if name == 'ward':   # ☑️ Không hỏi lại: ticked, the tap acts at once
                        await page.locator('#sheet [data-as-noask]').check()
                        await page.wait_for_timeout(500)
                        check(await page.evaluate("localStorage.getItem('mnl.noAsk')") == '1', f'{tag}: Không hỏi lại stored (mnl.noAsk)')
                        await go.click()
                        await page.wait_for_timeout(1200)
                        check(await page.locator('#confirmDialog[open]').count() == 0, f'{tag}: ward Không hỏi lại: no question')
                        await page.wait_for_selector('#sheet .pt-embed .pt-ares', timeout=15000)
                        await clear()
                        await page.locator('#sheet [data-as-noask]').uncheck(timeout=8000)
                        await page.wait_for_timeout(400)
                        check(await page.evaluate("localStorage.getItem('mnl.noAsk')") is None, f'{tag}: unticked, it asks again')
                    else:
                        await go.click()
                        text = await confirm(f'6-{name}-confirm')
                        check('Tiêu tối đa' in text and '%' not in text, f'{tag}: {name} one question, no odds')
                    await page.wait_for_selector('#sheet .pt-embed .pt-ares', timeout=15000)
                    res = await page.inner_text('#sheet .pt-embed .pt-ares')
                    check('xu đã tiêu' in res, f'{tag}: {name} the summary ({" ".join(res.split())[:120]})')
                    check(await wallet() < before, f'{tag}: {name} paid once')
                    await shot(f'7-{name}-result')

                # 🕶️ Ẩn tên: the save's setting (forgeAnon)
                await page.locator('#sheet [data-as-fzanon]').check()
                await page.wait_for_timeout(1500)
                anon = await page.evaluate("fetch('/api/state',{cache:'no-store'}).then(r=>r.json()).then(d=>d.state?.settings?.forgeAnon)")
                check(anon is True, f'{tag}: Ẩn tên saved ({anon})')
                await shot('7b-ticks')

                # the pets' dialog: the same card
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate(CLICK, ['pets', {'tab': 'gear'}])
                await page.wait_for_selector('.pt-sheet[open] .pt-auto', timeout=10000)
                await shot('8-dialog-gear')
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
