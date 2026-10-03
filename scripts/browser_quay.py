"""🏪 Quầy của bạn + 💼 Làm thêm: a two-player browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server. Two browser contexts, two registered accounts (seeded straight in
the database: chapter 3, 12 milk-tea jobs, life day 20, accounts a week old): the owner opens a cart from the dialog,
hires an NPC, posts a shift for players; the other player opens "Làm thêm", takes it, taps "Vào làm"; the shift's
day is then played through the server (start, 3 tasks, close), the worker's reload settles it (wage once), and the
owner sees the shift paid and the till grown. At 390x844 and 1280x800; any console error fails the run.
The scroll regression: 6 taps lower in the scrolled dialog keep its scroll and the tapped control on screen.
🧑‍🍳 Tự tay (--self runs only this): an owner opens a cart with no staff, sets its board (a dish on, a price up) and
its look (colour, decor, a table, the sign), turns "Bán online" on, stands at the counter: every customer served by
hand (dishes from the tiles, the change from the coins, a thank-you), the tricky moments answered, two online
orders packed (one ridden there by the map's turns, one by a shipper), then "Đóng ca".

    python scripts/browser_quay.py [out_dir] [--self]
The server and the seeding run with MNL_PY (default: this interpreter), so playwright may live in another Python.
"""
import asyncio
import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = Path(ARGS[0]) if ARGS else ROOT.parent / '_w095_shots' / 'quay'
PY = os.environ.get('MNL_PY', sys.executable)


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-quay-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.sqlite3')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([PY, 'server.py', '--port', str(port), '--db', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
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
from game import accounts
from game import journey as jr
from game import marriage as mr
from game.storage import Store
db, token, name = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
out = accounts.register(store, token, dict(username=name.lower() + '_q', password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
sid = store.key(out['token'])
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
def fn(s):
    j = s['journey']
    s['name'] = name
    j.update(gender='female', intro=True, life_day=20, chapter=3, done=[1, 2])
    for n in (2, 3):
        jr._unlock_chapter(j, n)
    j['wallet'] = 30000
    j['stats']['max_wallet'] = 30000
    s['careers']['milk_tea']['metrics']['served'] = 12
mr._mutate(store, {sid: fn})
store.close_pool()
print(out['token'])
'''

WORK = r'''
import sys
from game import marriage as mr
from game.storage import Store
db, token = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
def cmd(action, **p):
    rev = store.read(token)[1]
    return store.command(token, 'smoke-' + action + str(rev), rev, 'milk_tea', action, p)
if not store.read(token)[0]['careers']['milk_tea']['open']:
    cmd('start_day')
mr._mutate(store, {store.key(token): lambda s: s['careers']['milk_tea'].__setitem__('day_completed', 3)})
r = cmd('end_day', carry_event=True)
print(r['result'].get('quay'))
store.close_pool()
'''

CHECK = r'''
import json, sys
from game.storage import Store
store = Store(sys.argv[1], story=True)
with store.connect() as db:
    rows = [dict(r) for r in db.execute('SELECT status, wage, earned FROM quay_jobs')]
    fx = [dict(r) for r in db.execute("SELECT kind, amount, status FROM live_effects")]
print(json.dumps(dict(jobs=rows, fx=fx)))
store.close_pool()
'''


RUN = r'''
import json, sys
from game.storage import Store
store = Store(sys.argv[1], story=True)
st = store.read(sys.argv[2])[0]['journey']['quay']['stalls'][0]
print(json.dumps(dict(run=st.get('run'), rate=st.get('rate'), menu=st.get('menu'), look=st.get('look'), online=st.get('online'),
                      name=st['name'], till=st['till'], hist=st['hist'][-1:])))
store.close_pool()
'''

TURNS_JS = '''() => {   // the app's dotted route on the ride map, as turns
  const pl=[...document.querySelectorAll('.qy-sheet .qy-map polyline')].find(p=>p.getAttribute('stroke-dasharray'));
  const pts=pl.getAttribute('points').trim().split(/ +/).map(p=>p.split(',').map(Number));
  const dir=(a,b)=>[Math.sign(b[0]-a[0]),Math.sign(b[1]-a[1])].join();
  const H=['0,-1','1,0','0,1','-1,0'];const out=[];let h=0;
  for(let i=1;i<pts.length-1;i++){const n=H.indexOf(dir(pts[i],pts[i+1]));out.push(n===h?'S':n===(h+1)%4?'R':'L');h=n;}
  return out;}'''


def py(code: str, *args) -> str:
    return subprocess.run([PY, '-c', code, *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]


async def self_day(browser, w, h, errors):
    """🧑‍🍳 One owner, a cart with no staff: board, look, online, a day at the counter by hand."""
    tag = f'{w}x{h}'
    with server() as (base, db):
        ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=w < 500, has_touch=w < 500)
        page = await ctx.new_page()
        page.on('console', lambda m: m.type == 'error' and errors.append(f'{tag} self: {m.text}'))
        page.on('pageerror', lambda e: errors.append(f'{tag} self: {e}'))
        await page.goto(base)
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
        login = py(SEED, db, token, 'Lan')
        await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
        await page.reload()
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await page.wait_for_timeout(1200)
        await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        async def shot(name):
            await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet):not(#confirmDialog)').forEach(d=>d.close())")
            await page.wait_for_timeout(350)
            await page.screenshot(path=str(OUT / f'{tag}-self-{name}.png'))

        async def tap(sel, n=1):
            for _ in range(n):
                await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet):not(#confirmDialog)').forEach(d=>d.close())")
                await page.locator('.qy-sheet ' + sel).first.click()
                await page.wait_for_timeout(120)

        async def confirm():
            await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
            await page.click('#confirmDialog [data-action="confirmYes"]')
            await page.wait_for_timeout(900)

        async def idle():   # polled from here: the page's CSP has no 'unsafe-eval' for wait_for_function
            for _ in range(100):
                if await page.evaluate("document.querySelector('.qy-sheet')?.getAttribute('aria-busy')!=='true'"):
                    break
                await page.wait_for_timeout(100)
            await page.wait_for_timeout(150)

        def state():
            return json.loads(py(RUN, db, login))

        try:
            for _ in range(5):   # the game's own popups (titles, the x3 week) may come up late: closed, then tried again
                await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet)').forEach(d=>d.close())")
                await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='quay';b.hidden=true;document.body.append(b);b.click();b.remove();})()")
                await page.wait_for_timeout(800)
                if await page.locator('.qy-sheet[open] .qy-root h2').count():
                    break
            await page.wait_for_selector('.qy-sheet[open] .qy-root h2', timeout=10000)
            await tap('[data-qy="new"]')
            await tap('[data-qy="trade"][data-id="milk_tea"]')
            await tap('[data-qy="open"]')
            await confirm()
            await page.wait_for_selector('.qy-sheet canvas.qy-scene', timeout=10000)
            await shot('1-cart')
            # the board: matcha on, its price up twice
            await tap('[data-qy="more"][data-part="menu"]')
            await tap('[data-qy="dish"][data-k="matcha"]')
            await tap('[data-qy="dprice"][data-k="matcha"][data-by="1"]', 2)
            await shot('2-menu')
            await tap('[data-qy="menusave"]')
            await idle()
            got = state()
            assert 'matcha' in got['menu']['on'] and got['menu']['p']['matcha'] == 13, got['menu']
            # the look: pink awning, a lucky cat and lanterns, one stool set, a new sign
            await tap('[data-qy="more"][data-part="look"]')
            await tap('[data-qy="color"][data-k="6"]')
            await tap('[data-qy="decor"][data-k="meo"]')
            await tap('[data-qy="decor"][data-k="long_den"]')
            await tap('[data-qy="tables"][data-by="1"]')
            await page.fill('.qy-sheet input[name="qy-sign"]', 'Trà Mây Lan')
            await shot('3-look')
            await tap('[data-qy="looksave"]')
            await confirm()
            await idle()
            got = state()
            assert got['look'] == dict(c=6, d=['long_den', 'meo'], t=1) and got['name'] == 'Trà Mây Lan', got
            await tap('[data-qy="online"]')
            await idle()
            assert state()['online'] is True
            await shot('4-ready')
            # the day at the counter
            await tap('[data-qy="runstart"]')
            await page.wait_for_selector('.qy-sheet .qy-runbar', timeout=10000)
            await shot('5-run')
            shipped, served, moments = 0, 0, 0
            for _ in range(60):
                await idle()
                await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet):not(#confirmDialog)').forEach(d=>d.close())")
                if shipped < 2 and await page.locator('.qy-sheet .qy-phone-btn i').count():
                    await tap('.qy-phone-btn')
                    if shipped == 0:
                        await shot('6-phone')
                    await tap('[data-qy="pack"]')
                    line = await page.inner_text('.qy-sheet .qy-pack .qy-say p')
                    for tile in await page.locator('.qy-sheet .qy-pack .qy-tile-btn').all():
                        name = (await tile.locator('b').inner_text()).strip()
                        for part in line.split('·'):
                            if part.strip().split(' ', 1)[-1].split(' ×')[0] == name:
                                n = int(part.split('×')[1]) if '×' in part else 1
                                for _ in range(n):
                                    await tile.click()
                                    await page.wait_for_timeout(80)
                    say = await page.inner_text('.qy-sheet .qy-pack .qy-say')
                    note = await page.locator('.qy-sheet .qy-pack .qy-say .qy-note').count()
                    await tap('[data-qy="ptog"][data-k="seal"]')
                    if 'Không lấy' not in say:
                        await tap('[data-qy="ptog"][data-k="tool"]')
                    if note:
                        await tap('[data-qy="ptog"][data-k="note"]')
                    if shipped == 0:
                        await shot('7-pack')
                    await tap('[data-qy="packdone"]')
                    if shipped == 0:
                        await tap('[data-qy="way"][data-k="self"]')
                        for t in await page.evaluate(TURNS_JS):
                            await tap(f'[data-qy="turn"][data-k="{t}"]')
                        await shot('8-ride')
                        await tap('[data-qy="deliver"]')
                    else:
                        await tap('[data-qy="way"][data-k="ship"]')
                    await idle()
                    shipped += 1
                    if shipped == 1:
                        await shot('8b-shipped')
                    await tap('[data-qy="phone"]')
                    continue
                if await page.locator('.qy-sheet .qy-event').count():
                    if moments == 0:
                        await shot('9-moment')
                    await tap('.qy-event [data-qy="pick"]')
                    moments += 1
                    continue
                if not await page.locator('.qy-sheet .qy-cust').count():
                    break
                say = (await page.inner_text('.qy-sheet .qy-cust .qy-say p')).lower().strip('“”. ')
                say = say.removesuffix(' nha').removesuffix('nha')
                for who in ('cho mình ', 'cho em ', 'cho cô ', 'cho chú '):
                    say = say.replace(who, '')
                want = {}
                for chunk in say.split(' với '):
                    n, _, name = chunk.strip().partition(' ')
                    want[name.strip()] = int(n)
                for tile in await page.locator('.qy-sheet .qy-cust .qy-tile-btn').all():
                    name = (await tile.locator('b').inner_text()).strip().lower()
                    for _ in range(want.get(name, 0)):
                        await tile.click()
                        await page.wait_for_timeout(80)
                if served == 0:
                    await shot('10-tray')
                await tap('[data-qy="charge"]')
                bill = await page.inner_text('.qy-sheet .qy-cust .qy-bill >> nth=0')
                nums = [int(x.replace('.', '')) for x in re.findall(r'([0-9.]+) xu', bill)]
                change = nums[1] - nums[0]
                for coin in (200, 100, 50, 20, 10, 5, 2, 1):
                    while change >= coin and await page.locator(f'.qy-sheet [data-qy="coin"][data-k="{coin}"]').count():
                        await tap(f'[data-qy="coin"][data-k="{coin}"]')
                        change -= coin
                if served == 0:
                    await shot('11-change')
                await tap('[data-qy="paid"]')
                await tap('[data-qy="serve"][data-k="1"]')
                served += 1
            await idle()
            await shot('12-done')
            await tap('[data-qy="runclose"]')
            if await page.locator('#confirmDialog[open]').count():
                await confirm()
            await page.wait_for_selector('.qy-sheet .qy-sum', timeout=10000)
            await shot('13-summary')
            got = state()
            run = got['run']
            assert run['x'] and served >= 3 and shipped == 2 and moments >= 1, (served, shipped, moments, run)
            assert run['ss'] == 5 * run['sn'], run                         # every customer served right, with a smile
            assert run['on'][0] == 5, run['on']                            # ridden there by the map's turns, packed right
            assert got['hist'][-1].get('s') == 1 and got['hist'][-1]['net'] > 0, got['hist']
            await tap('[data-qy="back"]')
            await shot('14-after')
            print(tag, 'self day ok', dict(served=served, shipped=shipped, moments=moments, net=got['hist'][-1]['net'], stars=run['sum']['st']))
        except Exception:
            await page.screenshot(path=str(OUT / f'{tag}-self-FAIL.png'))
            raise
        finally:
            await ctx.close()


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for w, h in ((390, 844), (1280, 800)):
            await self_day(browser, w, h, errors)
        for w, h in (() if '--self' in sys.argv else ((390, 844), (1280, 800))):
            with server() as (base, db):
                tag = f'{w}x{h}'
                pages = {}
                for who in ('Lan', 'Minh'):
                    ctx = await browser.new_context(viewport=dict(width=w, height=h))
                    page = await ctx.new_page()
                    page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{tag} {who}: {m.text}'))
                    page.on('pageerror', lambda e, who=who: errors.append(f'{tag} {who}: {e}'))
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                    login = py(SEED, db, token, who)
                    await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
                    pages[who] = (page, login)

                async def popups(page):
                    for _ in range(5):   # "Có gì mới", new titles and other popups
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            break
                        await b.first.click()
                        await page.wait_for_timeout(400)

                async def ready(page):
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(1200)
                    await popups(page)
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

                async def open_quay(page):
                    await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='quay';b.hidden=true;document.body.append(b);b.click();})()")
                    await page.wait_for_selector('.qy-sheet[open] .qy-root h2', timeout=10000)
                    await page.wait_for_timeout(400)

                async def shot(page, name):
                    await page.wait_for_timeout(350)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                async def confirm(page):
                    await page.wait_for_selector('#confirmDialog[open]', timeout=5000)
                    await page.click('#confirmDialog [data-action="confirmYes"]')
                    await page.wait_for_timeout(900)
                    await popups(page)

                async def qclick(page, sel):
                    # a random life event or title card may pop over the dialog: it is not what this walk tests
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet):not(#confirmDialog)').forEach(d=>d.close())")
                    await page.click(sel)

                async def flash(page):
                    return (await page.inner_text('.qy-sheet .bk-flash')).strip()

                async def scroll_check(page, sels):
                    """The scroll regression (owner 03/10: "bấm vào là tự scroll lên"): scrolled down the dialog, each
                    tap on a control lower in it keeps the dialog's scrollTop and the control where it was on screen."""
                    held = 0
                    for sel in sels:
                        await page.evaluate("document.querySelectorAll('dialog[open]:not(.qy-sheet):not(#confirmDialog)').forEach(d=>d.close())")
                        loc = page.locator('.qy-sheet ' + sel).last
                        await loc.scroll_into_view_if_needed()
                        # the control at mid-screen, never under the sticky sheet head (Playwright would scroll it out itself)
                        await loc.evaluate("el=>{const d=el.closest('.qy-sheet'),r=el.getBoundingClientRect(),dr=d.getBoundingClientRect();d.scrollTop+=r.top-(dr.top+dr.height*.55);}")
                        await page.wait_for_timeout(150)
                        box = await loc.bounding_box()
                        top0 = await page.evaluate("document.querySelector('.qy-sheet').scrollTop")
                        assert top0 > 40, (sel, top0, 'the dialog should be scrolled down for this check')
                        await loc.click()
                        await page.wait_for_timeout(500)
                        if await page.locator('#confirmDialog[open]').count():
                            await page.click('#confirmDialog [data-action="confirmYes"]')
                            await page.wait_for_timeout(900)
                        top1 = await page.evaluate("document.querySelector('.qy-sheet').scrollTop")
                        after = page.locator('.qy-sheet ' + sel).last
                        box1 = await after.bounding_box() if await after.count() else None
                        # never back up the page; when a row above reflows (a "Lưu" button appears) the dialog follows it
                        # by exactly that much, so the tapped control stays under the finger
                        assert top1 >= top0 - 2, (sel, top0, top1, 'the dialog jumped up')
                        assert box1 is None or abs(box1['y'] - box['y']) <= 4, (sel, box, box1, 'the control moved on screen')
                        print('   ', sel, 'scrollTop', top0, '->', top1, 'control y', round(box['y']), '->', round(box1['y']) if box1 else '-')
                        held += 1
                    return held

                owner, _ = pages['Lan']
                worker, wtoken = pages['Minh']
                try:
                    # 1. The owner opens a cart selling milk tea, hires an NPC, posts a shift for players.
                    await ready(owner)
                    await open_quay(owner)
                    await shot(owner, '1-owner-empty')
                    await qclick(owner, '.qy-sheet [data-qy="new"]')
                    await qclick(owner, '.qy-sheet [data-qy="trade"][data-id="milk_tea"]')
                    await shot(owner, '2-owner-open')
                    await qclick(owner, '.qy-sheet [data-qy="open"]')
                    await confirm(owner)
                    assert 'đã mở' in await flash(owner), await flash(owner)
                    await qclick(owner, '.qy-sheet [data-qy="more"][data-part="staff"]')
                    await owner.wait_for_selector('.qy-sheet [data-qy="post"]', timeout=10000)
                    await qclick(owner, '.qy-sheet [data-qy="hire"]')
                    await owner.wait_for_timeout(700)
                    held = await scroll_check(owner, ['[data-qy="step"][data-by="1"][data-key^="s:"]', '[data-qy="help"][data-key="hire"]',
                                                      '[data-qy="step"][data-by="-1"][data-key^="s:"]', '[data-qy="to"][data-code=""]',
                                                      '[data-qy="help"][data-key="hire"]', '[data-qy="more"][data-part="stock"]'])
                    print(tag, 'scroll held on', held, 'taps')
                    await qclick(owner, '.qy-sheet [data-qy="more"][data-part="staff"]')
                    await owner.wait_for_selector('.qy-sheet [data-qy="post"]', timeout=10000)
                    await qclick(owner, '.qy-sheet [data-qy="step"][data-by="1"][data-key^="p:"]')
                    await qclick(owner, '.qy-sheet [data-qy="post"]')
                    await confirm(owner)
                    await owner.wait_for_selector('.qy-sheet [data-qy="cancel"]', timeout=10000)
                    assert 'Đã đăng' in await flash(owner), await flash(owner)
                    await shot(owner, '3-owner-posted')
                    # 2. The other player takes it from Làm thêm and goes to work.
                    await ready(worker)
                    await open_quay(worker)
                    await qclick(worker, '.qy-sheet [data-qy="tab"][data-tab="jobs"]')
                    await worker.wait_for_selector('.qy-sheet [data-qy="accept"]', timeout=10000)
                    await shot(worker, '4-worker-board')
                    await qclick(worker, '.qy-sheet [data-qy="accept"]')
                    await worker.wait_for_selector('.qy-sheet .qy-shift [data-qy="go"]', timeout=10000)
                    assert 'Đã nhận ca' in await flash(worker), await flash(worker)
                    await shot(worker, '5-worker-shift')
                    await qclick(worker, '.qy-sheet [data-qy="go"]')
                    await worker.wait_for_timeout(2500)
                    await worker.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await shot(worker, '6-worker-at-work')
                    # 3. The shift's day is played (3 tasks) and closed; the reload settles it.
                    assert py(WORK, db, wtoken) == 'shift'
                    await ready(worker)
                    await open_quay(worker)
                    await qclick(worker, '.qy-sheet [data-qy="tab"][data-tab="jobs"]')
                    await worker.wait_for_timeout(800)
                    assert not await worker.locator('.qy-sheet .qy-shift').count()
                    await shot(worker, '7-worker-paid')
                    state = json.loads(py(CHECK, db))
                    assert [j['status'] for j in state['jobs']] == ['paid'], state
                    # 4. The owner sees the shift paid and the till grown (inbox applied on load).
                    await ready(owner)
                    await open_quay(owner)
                    await qclick(owner, '.qy-sheet [data-qy="more"][data-part="staff"]')
                    await owner.wait_for_selector('.qy-sheet .qy-part li', timeout=10000)
                    await owner.wait_for_timeout(800)
                    text = await owner.inner_text('.qy-sheet .qy-part')
                    assert 'xong ca' in text, text
                    await shot(owner, '8-owner-paid')
                    state = json.loads(py(CHECK, db))
                    assert [f['status'] for f in state['fx']] == ['applied'], state
                    print(tag, 'ok', state)
                except Exception:
                    for who, (pg, _) in pages.items():
                        await pg.screenshot(path=str(OUT / f'{tag}-FAIL-{who}.png'))
                    raise
                finally:   # before the server stops: a page left open would only log refused polls
                    for pg, _ in pages.values():
                        await pg.context.close()
        await browser.close()
    if errors:
        print('CONSOLE ERRORS:', *errors, sep='\n  ')
        sys.exit(1)
    print('no console errors; shots in', OUT)


if __name__ == '__main__':
    asyncio.run(main())
