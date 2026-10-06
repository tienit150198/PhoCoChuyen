"""📱 Cửa hàng điện thoại (game/gadgets.py, F#205) on the CLASSIC client: a browser walk-through (dev tool, needs
playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save straight in its database (a named character on
life day 12 with 30.000 xu and a bank account). At 390x844: Bản đồ phố → Chỉ đường "📱 Điện thoại" (Phố dịch vụ),
walks to the door and goes in; the old phone, the phone tab, buys the gold phone (the old one traded in), earbuds, a
camera and a watch; the gold selfie frame; sells the earbuds; the profile chip on Hành trình; "📱 Vừa đi" in the
route picker; the classic avatar holding the phone. At 844x390 and 1280x800 (seeded with a gold phone, a camera and a
watch): the shop, the selfie, the home screen. JPEG screenshots.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_gadgets_classic.py [out_dir]
The server and the seeding run with MNL_PY (default: this interpreter), so playwright may live in another Python.
"""
import asyncio
import contextlib
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from pg_test_support import test_env

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_gadgets_classic_shots'
PY = os.environ.get('MNL_PY', sys.executable)


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-gadgets-')
    env = test_env(QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.db')
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
from game import bank as bk
from game import marriage as mr
from game.storage import Store
db, token, own = sys.argv[1], sys.argv[2], sys.argv[3] == '1'
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=12)
    j['wallet'] = 30000
    bk.apply(s, 'jr_bk_open', {})
    bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
    if own:   # the other layouts: already a gold phone, a camera and a watch
        from game import gadgets as gd
        for iid in ('kim_long', 'may_anh', 'dong_ho'):
            gd.action(s, 'jr_gadget_buy', {'id': iid, 'confirm': True})
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''


def seed(db: str, token: str, own: bool) -> None:
    subprocess.run([PY, '-c', SEED, db, token, '1' if own else '0'], cwd=ROOT, check=True)


ACT = "(a=>{const b=document.createElement('button');b.dataset.action=a;b.hidden=true;document.body.append(b);b.click();b.remove();})"


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (844, 390), (1280, 800)):
                ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if w < 900 else 1,
                                                has_touch=w < 900)
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                seed(db, token, w != 390)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(2000)
                tag = f'{w}x{h}'

                async def popups():
                    for _ in range(5):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            return
                        await b.first.click()
                        await page.wait_for_timeout(400)
                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

                async def shot(name):
                    await page.wait_for_timeout(500)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.jpg'), type='jpeg', quality=82)

                async def confirm():
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(300)
                    await page.wait_for_selector('.gd-sheet[aria-busy="false"]', timeout=30000)
                    await popups()

                async def flash():
                    return (await page.inner_text('.gd-sheet .bk-flash')).strip()

                async def home():
                    await page.evaluate(ACT + "('home')")
                    await page.wait_for_timeout(1200)
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

                if w == 390:
                    # Bản đồ phố → Chỉ đường "📱 Điện thoại" (Phố dịch vụ) → walk → the card → Vào.
                    await home()
                    sel = page.locator('.tw-route-picker select')
                    await sel.wait_for(state='attached', timeout=20000)
                    opts = await sel.locator('option').all_inner_texts()
                    print(tag, 'map has the shop:', any('Điện thoại' in o for o in opts))
                    await sel.select_option('lm:gadgets')
                    await page.click('.tw-route-picker button')
                    try:
                        await page.wait_for_selector('.tw-card:not([hidden]) .tw-go[data-action="gadgets"]', timeout=60000)
                        await shot('0-map-door')
                        await page.click('.tw-card .tw-go[data-action="gadgets"]')
                    except Exception:
                        errors.append('the walk to the shop on the town map did not reach its door')
                        await page.evaluate(ACT + "('gadgets')")
                    await page.wait_for_selector('.gd-sheet[open]', timeout=10000)
                    await shot('1-old-phone')
                    await page.click('.gd-sheet [data-gd="tab"][data-tab="phone"]')
                    await shot('2-phones')
                    await page.click('.gd-sheet [data-gd="look"][data-id="kim_long"]')
                    await page.click('.gd-sheet [data-gd="buy"]')
                    await confirm()
                    print(tag, 'buy:', await flash())
                    for gid in ('tai_nghe', 'may_anh', 'dong_ho'):
                        await page.click('.gd-sheet [data-gd="tab"][data-tab="gear"]')
                        await page.click(f'.gd-sheet [data-gd="look"][data-id="{gid}"]')
                        await page.click('.gd-sheet [data-gd="buy"]')
                        await confirm()
                    await page.click('.gd-sheet [data-gd="tab"][data-tab="mine"]')
                    await shot('3-mine')
                    await page.click('.gd-sheet [data-gd="selfie"]')
                    await shot('4-selfie-gold')
                    await page.click('.gd-sheet [data-gd="back"]')
                    await page.click('.gd-sheet [data-gd="sell"][data-id="tai_nghe"]')
                    await confirm()
                    print(tag, 'sell:', await flash())
                    await page.evaluate("document.querySelector('.gd-sheet').close()")
                    # The profile chip (rim: perk 'skin'), "📱 Vừa đi" in the route picker, the avatar holding the phone.
                    await home()
                    await page.evaluate(ACT + "('jrList')")   # Hành trình as a list: the profile card and its chips
                    await page.wait_for_timeout(1000)
                    chip = page.locator('.jr-title-chip[data-action="gadgets"]')
                    print(tag, 'profile chip:', (await chip.first.inner_text()).strip() if await chip.count() else None,
                          await chip.first.get_attribute('style') if await chip.count() else None)
                    await shot('5-profile-chip')
                    await page.evaluate(ACT + "('jrTown')")
                    await page.wait_for_timeout(1000)
                    sel = page.locator('.tw-route-picker select')
                    await sel.select_option('lm:bank')
                    await page.click('.tw-route-picker button')
                    await page.wait_for_timeout(800)
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                    await page.evaluate(ACT + "('jrTown')")
                    await page.wait_for_timeout(1000)
                    groups = page.locator('.tw-route-picker optgroup')
                    print(tag, 'recent group:', await groups.first.get_attribute('label') if await groups.count() else None)
                    await page.evaluate("""async()=>{const L=await import('/js/v4/look.js');
                      const svg=L.figureSVG({...L.lookOf({journey:{gender:'female'}}),held:'#d4af37'},'female',{w:240,h:340});
                      const box=document.createElement('div');box.id='stampbox';box.style.cssText='position:fixed;inset:0;z-index:99999;background:#cfe6c9;display:grid;place-items:center';box.innerHTML=svg;document.body.append(box);}""")
                    await shot('6-avatar-phone')
                    await page.evaluate("document.getElementById('stampbox')?.remove()")
                else:
                    await page.evaluate(ACT + "('gadgets')")
                    await page.wait_for_selector('.gd-sheet[open]', timeout=10000)
                    await shot('3-mine')
                    await page.click('.gd-sheet [data-gd="tab"][data-tab="phone"]')
                    await shot('2-phones')
                    await page.click('.gd-sheet [data-gd="tab"][data-tab="mine"]')
                    await page.click('.gd-sheet [data-gd="selfie"]')
                    await shot('4-selfie')
                    await page.evaluate("document.querySelector('.gd-sheet').close()")
                    await home()
                    await shot('5-home')
                await ctx.close()
            await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
