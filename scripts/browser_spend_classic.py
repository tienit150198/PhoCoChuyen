"""☕ Chỗ tiêu xu (game/spend.py) on the CLASSIC client: a browser walk-through (dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save straight in its database (a named character on
life day 12 with 5.000 xu). At 390x844: Bản đồ phố → Chỉ đường "☕ Đi quán" → walk to the door → Vào; orders a cà phê
muối; 🙏 Công đức 50 xu by name, the weekly board; every tab's visible words are counted (≤ 25). At 844x390: 🎨 Phong
cách, buys the Hoàng hôn colour and the Sen vàng frame. At 1280x800: the town map's 🙏 Công đức door, then Rạp Mây.
Four JPEG screenshots at most.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_spend_classic.py [out_dir]
The server and the seeding run with MNL_PY (default: this interpreter), so playwright may live in another Python.
"""
import asyncio
import contextlib
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from pg_test_support import test_env

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_spend_classic_shots'
PY = os.environ.get('MNL_PY', sys.executable)
WORDS_MAX = 25


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-spend-')
    env = test_env(QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 's.db')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([PY, 'server.py', '--port', str(port), '--namespace', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:
            if p.poll() is not None:
                break
            time.sleep(0.1)
    try:
        yield base, db
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)
        log.close()


SEED = r'''
import sys
from game import marriage as mr
from game.storage import Store
db, token = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=12)
    j['wallet'] = 5000
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''

ACT = "(a=>{const b=document.createElement('button');b.dataset.action=a;b.hidden=true;document.body.append(b);b.click();b.remove();})"
WORDS = """(()=>{const d=document.querySelector('.sd-sheet');let t=d.innerText;
  for(const s of d.querySelectorAll('select'))for(const o of s.options)if(!o.selected)t=t.replace(o.text,'');   // a closed select shows one option
  return t.replace(/\\s+/g,' ').split(' ').filter(w=>/[A-Za-zÀ-ỹ]/.test(w)).length;})()"""


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, report = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (844, 390), (1280, 800)):
                ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if w < 900 else 1, has_touch=w < 900)
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
                tag = f'{w}x{h}'
                async def popups():
                    for _ in range(5):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            return
                        report.append(f'{tag} popup: ' + ' '.join((await page.locator('#jrScene').inner_text()).split())[:80] if await page.locator('#jrScene[open]').count() else f'{tag} popup')
                        await b.first.click()
                        await page.wait_for_timeout(400)
                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

                async def shot(name):
                    await page.wait_for_timeout(500)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.jpg'), type='jpeg', quality=80)

                async def go():
                    await page.click('.sd-sheet [data-sd="go"]')
                    await page.wait_for_timeout(300)
                    await page.wait_for_selector('.sd-sheet[aria-busy="false"]', timeout=30000)
                    await popups()
                    return (await page.inner_text('.sd-sheet .sd-flash')).strip()

                async def tab(t):
                    await page.click(f'.sd-sheet [data-sd="tab"][data-tab="{t}"]')
                    await page.wait_for_timeout(500)
                    n = await page.evaluate(WORDS)
                    report.append(f'{tag} {t}: {n} words')
                    if n > WORDS_MAX:
                        errors.append(f'{tag} {t}: {n} visible words (> {WORDS_MAX})')

                async def door(lm, action):
                    await page.evaluate(ACT + "('home')")
                    await page.wait_for_timeout(1200)
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                    sel = page.locator('.tw-route-picker select')
                    await sel.wait_for(state='attached', timeout=20000)
                    await sel.select_option(lm)
                    await page.click('.tw-route-picker button')
                    try:
                        await page.wait_for_selector(f'.tw-card:not([hidden]) .tw-go[data-action="{action}"]', timeout=60000)
                        return True
                    except Exception:
                        errors.append(f'{tag}: the walk to {lm} did not reach its door')
                        return False

                if w == 390:
                    if await door('lm:quan', 'spendQuan'):
                        await page.click('.tw-card .tw-go[data-action="spendQuan"]')
                    else:
                        await page.evaluate(ACT + "('spendQuan')")
                    await page.wait_for_selector('.sd-sheet[open]', timeout=10000)
                    report.append(f'{tag} order: {await go()}')
                    await tab('quan')
                    await shot('1-quan')
                    for t in ('spa', 'rap'):
                        await tab(t)
                    await tab('chua')
                    await page.click('.sd-sheet [data-sd="amount"][data-n="50"]')
                    anon = page.locator('.sd-sheet input[name="anon"]')
                    report.append(f'{tag} guest sees Ẩn danh toggle: {bool(await anon.count())}')   # a guest gives anonymously
                    await page.select_option('.sd-sheet select[name="wish"]', 'me_khoe')
                    report.append(f'{tag} give: {await go()}')
                    await page.wait_for_selector('.sd-sheet .sd-board', timeout=10000)
                    await shot('2-chua-board')
                    await tab('style')
                elif w == 844:
                    await page.evaluate(ACT + "('spendStyle')")
                    await page.wait_for_selector('.sd-sheet[open]', timeout=10000)
                    await page.click('.sd-sheet [data-sd="pick"][data-id="c_hoang_hon"]')
                    report.append(f'{tag} colour: {await go()}')
                    await page.click('.sd-sheet [data-sd="kind"][data-kind="frame"]')
                    await page.click('.sd-sheet [data-sd="pick"][data-id="f_sen_vang"]')
                    report.append(f'{tag} frame: {await go()}')
                    await shot('3-style')
                    ring = await page.locator('.sd-sheet .sd-preview .sd-av.st-fr').count()
                    report.append(f'{tag} preview framed: {bool(ring)}')
                else:
                    ok = await door('lm:congduc', 'spendChua')
                    await shot('4-map-door-congduc')
                    if ok:
                        await page.click('.tw-card .tw-go[data-action="spendChua"]')
                        await page.wait_for_selector('.sd-sheet[open]', timeout=10000)
                        await tab('rap')
                        report.append(f'{tag} film: {await go()}')
                await ctx.close()
            await browser.close()
    print('\n'.join(report))
    if errors:
        print('ERRORS:\n' + '\n'.join(dict.fromkeys(errors)))
        sys.exit(1)
    print('OK, shots in', OUT)


if __name__ == '__main__':
    asyncio.run(main())
