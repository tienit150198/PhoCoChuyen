"""♿ Feedback #519 (a blind player: "chọn vô mục du lịch thì chỗ làm hộ chiếu tôi không thể vô được"): ✈️ Du lịch →
🛂 visa → book → airport → on board, played with the KEYBOARD ONLY (Tab / Shift+Tab / Enter / Space) on the real app,
the way a screen reader moves (dev tool, needs playwright + chromium).

Runs a throwaway story-mode server and seeds one save (life day 12, 6.000.000 xu, a bank account, three days worked).
At 390x844 it checks, on every screen of the flow:
  - focus never falls out of the open dialog after a key press (it used to drop to <body> on every redraw);
  - a newly opened dialog / a new screen puts focus on its heading;
  - every button in the dialog has an accessible name (accessibility tree snapshot), dimmed main buttons stay
    focusable (aria-disabled) and name their reason (aria-describedby);
  - results are announced (the dialog's live region).
Screenshots (JPEG) go to the out dir.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_a11y_travel.py [out_dir]
"""
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_lux import server, ACT, PY, ROOT  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_a11y_travel_shots'

SEED = r'''
import sys
from game import marriage as mr
from game.engine import apply_action
from game.storage import Store
db, token = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=12)
    j['wallet'] = 6_000_000
    j['days'] = [dict(c=c, d=n, m='normal') for n, c in enumerate(('florist', 'pho', 'milk_tea'), 1)]
    t = s
    for name, p in (('jr_bk_open', {}), ('jr_bk_deposit', dict(amount=300_000))):
        t, _ = apply_action(t, None, name, p)
    s.clear()
    s.update(t)
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''

FOCUS = """(()=>{const a=document.activeElement,d=a?.closest?.('dialog[open]');
  const name=a?(a.getAttribute('aria-label')||a.textContent||'').replace(/\\s+/g,' ').trim():'';
  const desc=(a?.getAttribute?.('aria-describedby')||'').split(/\\s+/).filter(Boolean).map(id=>document.getElementById(id)?.textContent||'').join(' ').trim();
  return {tag:a?.tagName||'',name,desc,dialog:d?d.className:'',disabled:a?.getAttribute?.('aria-disabled')==='true',pressed:a?.getAttribute?.('aria-pressed'),
    data:a?.dataset?{...a.dataset}:{}};})()"""
UNNAMED = """(sel=>{const d=document.querySelector(sel);if(!d)return ['no dialog'];
  return [...d.querySelectorAll('button,summary,a[href],[role=tab]')].filter(b=>b.getClientRects().length).filter(b=>{
    const n=(b.getAttribute('aria-label')||b.textContent||'').replace(/[\\s\\u{1F000}-\\u{1FAFF}\\u2600-\\u27BF\\uFE0F]/gu,'');return !n;}).map(b=>b.outerHTML.slice(0,90));})"""
LIVE = "(sel=>document.querySelector(sel+' > .sf-live')?.textContent||'')"


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, report = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844), device_scale_factor=2, has_touch=True)
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.tut.tips','done')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            subprocess.run([PY, '-c', SEED, db, token], cwd=ROOT, check=True)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1500)
            for _ in range(8):   # the seeded save's new titles: their popups come first
                await page.wait_for_timeout(700)
                b = page.locator('[data-wn="close"]:visible, #jrScene[open] [data-action="jrSceneClose"]')
                if not await b.count():
                    break
                await b.first.click()
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            n_shot = [0]

            async def shot(name):
                n_shot[0] += 1
                await page.wait_for_timeout(300)
                await page.screenshot(path=str(OUT / f'{n_shot[0]}-{name}.jpg'), type='jpeg', quality=78)

            async def focus():
                return await page.evaluate(FOCUS)

            async def settle(sel):
                await page.wait_for_timeout(250)
                with __import__('contextlib').suppress(Exception):
                    await page.wait_for_selector(f'{sel}[aria-busy="false"]', timeout=20000)
                await page.wait_for_timeout(250)

            async def check(sel, step):
                f = await focus()
                if sel.strip('.') not in f['dialog']:
                    errors.append(f'{step}: focus left the dialog ({f["tag"]} {f["name"][:40]!r})')
                bad = await page.evaluate(UNNAMED, sel)
                if bad:
                    errors.append(f'{step}: unnamed controls {bad}')
                report.append(f'{step}: focus {f["tag"]} {f["name"][:60]!r}' + (f' desc={f["desc"]!r}' if f['desc'] else '') + (' [aria-disabled]' if f['disabled'] else ''))
                return f

            async def tab_to(sel, test, step, limit=90):
                wraps = 0
                for _ in range(limit):
                    await page.keyboard.press('Tab')
                    f = await focus()
                    if f['tag'] in ('BODY', 'HTML'):   # past the last control: the browser's own chrome, then back to the first
                        wraps += 1
                        if wraps > 2:
                            break
                        continue
                    if sel.strip('.') not in f['dialog']:
                        errors.append(f'{step}: Tab left the dialog ({f["tag"]} {f["name"][:40]!r})')
                        return f
                    if test(f):
                        return f
                errors.append(f'{step}: not reached with Tab')
                return await focus()

            async def press(sel, key, step):
                await page.keyboard.press(key)
                await settle(sel)
                for _ in range(4):   # a game popup over the sheet (a new title…): closed with Enter on its own button, as a reader would
                    if not await page.locator('#jrScene[open]').count():
                        break
                    report.append(f'  popup over the sheet: {(await focus())["name"][:40]!r}, closed')
                    await page.click('#jrScene [data-action="jrSceneClose"]')
                    await page.wait_for_timeout(500)
                return await check(sel, step)

            try:
                TV, LX = '.tv-sheet', '.lx-sheet'
                # 1. ✈️ Du lịch opens on its heading
                await page.evaluate(ACT + "('travel')")
                await page.wait_for_selector('.tv-sheet[open] .tv-place', timeout=10000)
                await page.wait_for_timeout(400)
                f = await check(TV, '1 open Du lịch')
                if f['tag'] != 'H2':
                    errors.append(f'1: focus on {f["tag"]}, not the heading')
                snap = await page.accessibility.snapshot()
                report.append(f'  a11y tree root: {snap.get("role")} {snap.get("name")!r}, {len(snap.get("children") or [])} nodes')
                # 2. Hàn Quốc (needs a visa), by keyboard
                await tab_to(TV, lambda f: f['data'].get('id') == 'han_quoc', '2 Tab to Hàn Quốc')
                f = await press(TV, 'Enter', '2 Hàn Quốc')
                if 'Hàn Quốc' not in f['name']:
                    errors.append(f'2: focus not on the place heading ({f["name"]!r})')
                await shot('han-quoc')
                # 3. the main button goes to the visa office and says why
                f = await tab_to(TV, lambda f: f['data'].get('tv') == 'go', '3 Tab to the main button')
                if 'Làm visa' not in f['name'] or 'Cần visa' not in f['desc']:
                    errors.append(f'3: main button {f["name"]!r} / {f["desc"]!r}')
                await page.keyboard.press('Enter')
                await page.wait_for_selector('.lx-sheet[open]', timeout=10000)
                await settle(LX)
                f = await check(LX, '3 Làm visa opened')
                if f['tag'] != 'H2' or 'Làm visa' not in f['name']:
                    errors.append(f'3: the visa office did not open on its heading ({f["tag"]} {f["name"]!r})')
                await shot('visa')
                # 4. the help, the papers (Space toggles, focus stays on the chip), the photo
                f = await tab_to(LX, lambda f: f['tag'] == 'SUMMARY', '4 Tab to the help')
                report.append(f'  help: {f["name"]!r}')
                for doc in ('anh', 'sao_ke', 'cong_viec'):
                    await tab_to(LX, lambda f, doc=doc: f['data'].get('lx') == 'doc' and f['data'].get('id') == doc, f'4 Tab to {doc}')
                    f = await press(LX, 'Space', f'4 toggle {doc}')
                    if f['data'].get('id') != doc or f['pressed'] != 'true':
                        errors.append(f'4: after Space focus is {f["data"]} pressed={f["pressed"]}')
                await tab_to(LX, lambda f: f['data'].get('lx') == 'photo', '4 Tab to the photo')
                await press(LX, 'Enter', '4 photo taken')
                report.append(f'  said: {await page.evaluate(LIVE, LX)!r}')
                # 5. file the visa
                f = await tab_to(LX, lambda f: f['data'].get('lx') == 'go', '5 Tab to Nộp hồ sơ')
                report.append(f'  main: {f["name"]!r}')
                f = await press(LX, 'Enter', '5 visa filed')
                said = await page.evaluate(LIVE, LX)
                report.append(f'  said: {said!r}')
                if not said:
                    errors.append('5: nothing announced after filing the visa')
                if f['data'].get('lx') != 'go' or 'Đặt vé' not in f['name']:
                    errors.append(f'5: focus not on "Đặt vé máy bay" ({f["name"]!r})')
                await shot('visa-done')
                # 6. back to ✈️ Du lịch on Hàn Quốc: today, book
                await page.keyboard.press('Enter')
                await page.wait_for_selector('.tv-sheet[open] .tv-days', timeout=10000)
                await settle(TV)
                f = await check(TV, '6 back in Du lịch')
                if 'Hàn Quốc' not in f['name']:
                    errors.append(f'6: not on the place heading ({f["name"]!r})')
                await tab_to(TV, lambda f: f['data'].get('tv') == 'ahead' and f['data'].get('n') == '0', '6 Tab to Hôm nay')
                await press(TV, 'Enter', '6 Hôm nay picked')
                f = await tab_to(TV, lambda f: f['data'].get('tv') == 'go', '6 Tab to Đặt vé')
                if 'Đặt vé' not in f['name'] or f['disabled']:
                    errors.append(f'6: main {f["name"]!r} disabled={f["disabled"]}')
                f = await press(TV, 'Enter', '6 booked')
                report.append(f'  said: {await page.evaluate(LIVE, TV)!r}')
                await shot('ticket')
                # 7. the airport, by keyboard: Ra sân bay, two steps, on board
                if f['data'].get('tv') != 'go':
                    await tab_to(TV, lambda f: f['data'].get('tv') == 'go', '7 Tab to Ra sân bay')
                f = await press(TV, 'Enter', '7 at the airport')
                if f['tag'] != 'H3':
                    errors.append(f'7: the airport did not put focus on its heading ({f["tag"]} {f["name"]!r})')
                for i in range(2):
                    await tab_to(TV, lambda f: f['data'].get('tv') == 'step', f'7 Tab to step {i}')
                    await press(TV, 'Enter', f'7 step {i}')
                f = await tab_to(TV, lambda f: f['data'].get('tv') == 'go', '7 Tab to Lên máy bay')
                f = await press(TV, 'Enter', '7 on board')
                await page.wait_for_selector('.tv-sheet .tv-window', timeout=10000)
                report.append(f'  said: {await page.evaluate(LIVE, TV)!r}')
                await shot('cabin')
            except Exception as e:  # a step that did not come: the report so far says where
                errors.append(f'stopped: {type(e).__name__}: {str(e)[:200]}')
                await shot('stopped')
            await browser.close()
    print('\n'.join(report))
    if errors:
        print('ERRORS:\n' + '\n'.join(dict.fromkeys(errors)))
        sys.exit(1)
    print('OK, shots in', OUT)


if __name__ == '__main__':
    asyncio.run(main())
