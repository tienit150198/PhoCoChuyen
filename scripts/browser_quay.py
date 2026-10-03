"""🏪 Quầy của bạn + 💼 Làm thêm: a two-player browser walk-through (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server. Two browser contexts, two registered accounts (seeded straight in
the database: chapter 3, 12 milk-tea jobs, life day 20, accounts a week old): the owner opens a cart from the dialog,
hires an NPC, posts a shift for players; the other player opens "Làm thêm", takes it, taps "Vào làm"; the shift's
day is then played through the server (start, 3 tasks, close), the worker's reload settles it (wage once), and the
owner sees the shift paid and the till grown. At 390x844 and 1280x800; any console error fails the run.

    python scripts/browser_quay.py [out_dir]
The server and the seeding run with MNL_PY (default: this interpreter), so playwright may live in another Python.
"""
import asyncio
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'quay'
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


def py(code: str, *args) -> str:
    return subprocess.run([PY, '-c', code, *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for w, h in ((390, 844), (1280, 800)):
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
