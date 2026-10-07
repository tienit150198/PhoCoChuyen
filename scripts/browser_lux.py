"""🛍️ Mua sắm (game/lux.py) and 🏰 the villas' insides (game/estates.py) on the CLASSIC client: a browser walk-through
(dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds one save straight in its database: a rich character on
life day 12 (6.000.000 xu, a bank account, three days worked) who owns Dinh thự đảo Hòn Mây, lives there and has set
up a few pieces. At 390x844: Bản đồ phố → Chỉ đường "✈️ Đại lý vé" → Vào; every tab's visible words are counted
(≤ 30), the visa paperwork is filed (refused for a missing paper, then granted), a business-class trip; the villa tab,
then inside: the cinema and the infinity pool (the floor switcher). At 1280x800: Mạnh Thường Quân (a bench plaque and
fireworks, the board), then the villa's library. Seven JPEG screenshots at most (4 shop + 3 interiors).

    TEST_DATABASE_URL=postgresql://… python scripts/browser_lux.py [out_dir]
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
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_lux_shots'
PY = os.environ.get('MNL_PY', sys.executable)
WORDS_MAX = 30


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-lux-')
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
    for name, p in (('jr_bk_open', {}), ('jr_bk_deposit', dict(amount=300_000)),
                    ('jr_lux_buy', dict(id='dinh_thu_dao', confirm=True)), ('jr_lux_live', dict(id='dinh_thu_dao')),
                    ('jr_deco_buy', dict(item='ghe_rap_doi', confirm=True, put=dict(r='cinema', x=60, y=40))),
                    ('jr_deco_buy', dict(item='may_bong_ngo', confirm=True, put=dict(r='cinema', x=10, y=50))),
                    ('jr_deco_buy', dict(item='loa_cot', confirm=True, put=dict(r='cinema', x=200, y=10))),
                    ('jr_deco_buy', dict(item='ghe_tam_nang', confirm=True, put=dict(r='infinity', x=20, y=70))),
                    ('jr_deco_buy', dict(item='quay_bar_ho', confirm=True, put=dict(r='infinity', x=180, y=70))),
                    ('jr_deco_buy', dict(item='ban_go_lim', confirm=True, put=dict(r='study', x=100, y=30))),
                    ('jr_deco_buy', dict(item='ghe_da_bo', confirm=True, put=dict(r='study', x=60, y=50))),
                    ('jr_deco_buy', dict(item='qua_dia_cau', confirm=True, put=dict(r='study', x=120, y=50)))):
        t, _ = apply_action(t, None, name, p)
    s.clear()
    s.update(t)
mr._mutate(store, {store.key(token): fn})
store.close_pool()
'''

ACT = "(a=>{const b=document.createElement('button');b.dataset.action=a;b.hidden=true;document.body.append(b);b.click();b.remove();})"
WORDS = """(sel=>{const d=document.querySelector(sel);if(!d)return -1;const r=d.getBoundingClientRect();let n=0;
  const tw=document.createTreeWalker(d,NodeFilter.SHOW_TEXT);
  for(let t;(t=tw.nextNode());){const s=t.textContent.trim(),p=t.parentElement;if(!s||!p||p.closest('[hidden],.sr-only,details:not([open])>:not(summary)'))continue;
    if(p.closest('select')&&!p.closest('option')?.selected&&p.tagName==='OPTION')continue;
    const rg=document.createRange();rg.selectNodeContents(t);if(![...rg.getClientRects()].some(q=>q.width>=1&&q.bottom>0&&q.top<innerHeight))continue;
    n+=s.split(/\\s+/).filter(k=>/\\p{L}/u.test(k)).length;}
  return n;})"""


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, report = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w, h in ((390, 844), (1280, 800)):
                ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if w < 900 else 1, has_touch=w < 900)
                await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.decoTip2','1')}catch(e){}")
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
                    for _ in range(6):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            return
                        await b.first.click()
                        await page.wait_for_timeout(400)
                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

                async def shot(name):
                    await page.wait_for_timeout(600)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.jpg'), type='jpeg', quality=78)

                async def go():
                    await page.click('.lx-sheet [data-lx="go"]')
                    await page.wait_for_timeout(300)
                    await page.wait_for_selector('.lx-sheet[aria-busy="false"]', timeout=30000)
                    await popups()
                    return (await page.inner_text('.lx-sheet .sd-flash')).strip()

                async def tab(t):
                    await page.click(f'.lx-sheet [data-lx="tab"][data-tab="{t}"]')
                    await page.wait_for_timeout(600)
                    n = await page.evaluate(WORDS, '.lx-sheet')
                    report.append(f'{tag} {t}: {n} words')
                    if n > WORDS_MAX:
                        errors.append(f'{tag} {t}: {n} visible words (> {WORDS_MAX})')

                if w == 390:
                    await page.evaluate(ACT + "('jrTown')")
                    await page.wait_for_timeout(1500)
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                    sel = page.locator('.tw-route-picker select')
                    walked = False
                    with contextlib.suppress(Exception):
                        await sel.wait_for(state='attached', timeout=15000)
                        await sel.select_option('lm:travel')
                        await page.click('.tw-route-picker button')
                        await page.wait_for_selector('.tw-card:not([hidden]) .tw-go[data-action="luxTrip"]', timeout=60000)
                        await page.click('.tw-card .tw-go[data-action="luxTrip"]')
                        walked = True
                    report.append(f'{tag} town map door ✈️ Đại lý vé reached: {walked}')
                    if not walked:
                        await page.evaluate(ACT + "('luxTrip')")
                    await page.wait_for_selector('.lx-sheet[open]', timeout=10000)
                    for t in ('suu', 'nha', 'bay', 'tiec', 'hoc', 'mtq', 'trip'):
                        await tab(t)
                    await page.click('.lx-sheet [data-lx="country"][data-id="han_quoc"]')
                    for d in ('anh', 'sao_ke'):
                        await page.click(f'.lx-sheet [data-lx="doc"][data-id="{d}"]')
                    report.append(f'{tag} visa without a photo: {await go()}')
                    await page.click('.lx-sheet [data-lx="photo"]')
                    await page.wait_for_selector('.lx-sheet[aria-busy="false"]', timeout=30000)
                    await page.click('.lx-sheet [data-lx="doc"][data-id="cong_viec"]')
                    await shot('1-visa')
                    report.append(f'{tag} visa: {await go()}')
                    await page.click('.lx-sheet [data-lx="cls"][data-id="thuong_gia"]')
                    report.append(f'{tag} trip: {await go()}')
                    await tab('suu')
                    await page.click('.lx-sheet [data-lx="set"][data-id="dong_ho"]')
                    await page.click('.lx-sheet [data-lx="piece"][data-id="dh_lan_bien"]')
                    report.append(f'{tag} buy: {await go()}')
                    await shot('2-suu')
                    await tab('nha')
                    await shot('3-dinh-thu')
                    await page.click('.lx-sheet [data-lx="go"]')   # 🏠 Vào nhà
                    await page.wait_for_selector('.dc-sheet[open]', timeout=15000)
                    await page.wait_for_timeout(1200)
                    await page.click('.dc-sheet [data-dc="room"][data-room="cinema"]')
                    n = await page.evaluate(WORDS, '.dc-sheet')
                    report.append(f'{tag} villa cinema: {n} words; floors: {await page.locator(".dc-floors button").count()}')
                    await shot('5-cinema')
                    await page.click('.dc-sheet [data-dc="floor"][data-fl="3"]')
                    await page.wait_for_timeout(600)
                    with contextlib.suppress(Exception):
                        await page.click('.dc-sheet [data-dc="room"][data-room="infinity"]', timeout=3000)
                    await shot('6-infinity')
                else:
                    await page.evaluate(ACT + "('luxMtq')")
                    await page.wait_for_selector('.lx-sheet[open]', timeout=10000)
                    await page.wait_for_timeout(800)
                    await page.click('.lx-sheet [data-lx="give"][data-id="ghe_da"]')
                    await page.click('.lx-sheet [data-lx="slot"][data-n="7"]')
                    report.append(f'{tag} bench: {await go()}')
                    await page.click('.lx-sheet [data-lx="give"][data-id="phao_hoa"]')
                    report.append(f'{tag} fireworks: {await go()}')
                    await page.wait_for_timeout(1500)
                    await shot('4-mtq')
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.evaluate(ACT + "('luxNha')")
                    await page.wait_for_selector('.lx-sheet[open]', timeout=10000)
                    await page.click('.lx-sheet [data-lx="go"]')
                    await page.wait_for_selector('.dc-sheet[open]', timeout=15000)
                    await page.click('.dc-sheet [data-dc="floor"][data-fl="2"]')
                    await page.click('.dc-sheet [data-dc="room"][data-room="study"]')
                    await shot('7-thu-vien')
                await ctx.close()
            await browser.close()
    print('\n'.join(report))
    if errors:
        print('ERRORS:\n' + '\n'.join(dict.fromkeys(errors)))
        sys.exit(1)
    print('OK, shots in', OUT)


if __name__ == '__main__':
    asyncio.run(main())
