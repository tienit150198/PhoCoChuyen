"""💸 Chuyển khoản bạn bè: a two-player browser walk-through at 390x844 (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server. Two registered accounts seeded straight in the database (a week
old, life day 20, a bank account with 5,000 xu, friends since yesterday). Lan opens Ngân hàng → Chuyển khoản, picks
Minh, taps a chip, writes a note, confirms, gets the receipt. Minh, online on the street, gets the toast from the
ticker's poll (no reload) and sees the line in the bank statement; a second transfer arrives on Minh's reload. Then
the caps: an amount above today's room is stopped on the confirm step, and Minh's daily receive cap is refused by
the server with its message. Any console error fails the run.

    python scripts/browser_bank_xfer.py [out_dir]
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
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_w095_shots' / 'bankxfer'
PY = os.environ.get('MNL_PY', sys.executable)


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-xfer-')
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
out = accounts.register(store, token, dict(username=name.lower() + '_x', password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
def fn(s):
    j = s['journey']
    s['name'] = name
    j.update(gender='female', intro=True, life_day=20, chapter=3, done=[1, 2])
    for n in (2, 3):
        jr._unlock_chapter(j, n)
    j['wallet'] = 8000
    j['stats']['max_wallet'] = 8000
mr._mutate(store, {sid: fn})
for i, (a, p) in enumerate((('jr_bk_open', {}), ('jr_bk_deposit', dict(amount=5000)))):
    rev = store.read(tok)[1]
    store.command(tok, f'seed-bank-{i}', rev, None, a, p)
mr.ensure_person(store, sid)
store.close_pool()
print(tok)
'''

FRIENDS = r'''
import sys, time
from game.storage import Store
db, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
x, y, t = store.key(a), store.key(b), time.time() - 86400
store.transaction(lambda d: [d.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', p) for p in ((x, y, t), (y, x, t))])
store.close_pool()
print('ok')
'''

NEAR_CAP = r'''
import sys
from game import bank_xfer as bx
from game.storage import Store
db, tok = sys.argv[1], sys.argv[2]
store = Store(db, story=True)
sid, day = store.key(tok), bx.vn_day()
store.transaction(lambda d: d.execute('UPDATE bank_xfer_days SET got=? WHERE sid=? AND day=?', (bx.RECV_DAY - 100, sid, day)))
store.close_pool()
print('ok')
'''

CHECK = r'''
import json, sys
from game.storage import Store
store = Store(sys.argv[1], story=True)
with store.connect() as db:
    rows = [dict(r) for r in db.execute('SELECT from_name, to_name, amount, note, status FROM bank_xfers ORDER BY at')]
print(json.dumps(rows, ensure_ascii=False))
store.close_pool()
'''


def py(code: str, *args) -> str:
    r = subprocess.run([PY, '-c', code, *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    return r.stdout.strip().splitlines()[-1]


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        w, h = 390, 844
        with server() as (base, db):
            tag = f'{w}x{h}'
            pages = {}
            for who in ('Lan', 'Minh'):
                ctx = await browser.new_context(viewport=dict(width=w, height=h), locale='vi-VN')
                page = await ctx.new_page()
                page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{who}: {m.text}'))
                page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {e}'))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                login = py(SEED, db, token, who)
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
                pages[who] = (page, login)
            py(FRIENDS, db, pages['Lan'][1], pages['Minh'][1])

            async def popups(page):
                for _ in range(6):   # "Có gì mới", new titles and other popups
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

            async def open_bank(page):
                await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='bank';b.hidden=true;document.body.append(b);b.click();})()")
                await page.wait_for_selector('.bk-sheet[open] .bk-hero', timeout=10000)
                await page.wait_for_timeout(400)

            async def click(page, sel):
                # a random life event or title card may pop over the dialog: it is not what this walk tests
                await page.evaluate("document.querySelectorAll('dialog[open]:not(.bk-sheet):not(#confirmDialog)').forEach(d=>d.close())")
                await page.click(sel)

            async def shot(page, name):
                await page.wait_for_timeout(350)
                await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

            async def toast(page, text, ms):
                for _ in range(ms // 500):   # polled (the page's CSP refuses wait_for_function's eval)
                    if await page.evaluate('t=>[...document.querySelectorAll("#toasts *")].some(e=>e.textContent.includes(t))', text):
                        return
                    await page.wait_for_timeout(500)
                raise AssertionError(f'no toast: {text}')

            async def send(page, amount=None, chip=None, note=''):
                await click(page, '.bk-sheet [data-bk="x-to"]')
                await page.wait_for_selector('.bk-sheet #bx-amt', timeout=5000)
                if chip:
                    await click(page, f'.bk-sheet [data-bk="x-chip"][data-n="{chip}"]')
                else:
                    await page.fill('.bk-sheet #bx-amt', str(amount))
                if note:
                    await page.fill('.bk-sheet #bx-note', note)

            lan, _ = pages['Lan']
            minh, _ = pages['Minh']
            try:
                # Minh is online on the street (the ticker polls); Lan opens the bank.
                await ready(minh)
                await ready(lan)
                await open_bank(lan)
                await shot(lan, '1-bank-home')
                await click(lan, '.bk-sheet [data-bk="xfer"]')
                await lan.wait_for_selector('.bk-sheet .bx-friend', timeout=10000)
                await shot(lan, '2-pick-friend')
                await send(lan, chip=500, note='Cảm ơn ly trà sữa nha 🧋')
                await shot(lan, '3-amount')
                await click(lan, '.bk-sheet [data-bk="x-next"]')
                await lan.wait_for_selector('.bk-sheet .bx-confirm', timeout=5000)
                await shot(lan, '4-confirm')
                await click(lan, '.bk-sheet [data-bk="x-send"]')
                await lan.wait_for_selector('.bk-sheet .bx-done', timeout=10000)
                text = await lan.inner_text('.bk-sheet .bx-done')
                assert 'Đã chuyển 500 xu cho Minh' in text and 'CK' in text, text
                await shot(lan, '5-receipt')
                # Minh: the ticker's poll (about a minute) credits it and says so, no reload.
                await minh.wait_for_timeout(3000)
                await popups(minh)   # "Có gì mới" comes a moment after the load
                await toast(minh, 'Lan chuyển cho bạn 500 xu', 80000)
                await minh.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await shot(minh, '6-minh-toast-online')
                await open_bank(minh)
                await click(minh, '.bk-sheet [data-bk="tab"][data-tab="tx"]')
                await minh.wait_for_timeout(500)
                text = await minh.inner_text('.bk-sheet .bk-tx')
                assert 'Lan chuyển khoản' in text, text
                await shot(minh, '7-minh-statement')
                await minh.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                # A second one while Minh is away: it lands on Minh's next load.
                await click(lan, '.bk-sheet [data-bk="x-again"]')
                await lan.wait_for_selector('.bk-sheet .bx-friend', timeout=10000)
                await send(lan, amount=120, note='')
                await click(lan, '.bk-sheet [data-bk="x-next"]')
                await click(lan, '.bk-sheet [data-bk="x-send"]')
                await lan.wait_for_selector('.bk-sheet .bx-done', timeout=10000)
                await minh.reload()
                await minh.wait_for_selector('#app:not([hidden])', timeout=30000)
                await toast(minh, 'Lan chuyển cho bạn 120 xu', 15000)
                await popups(minh)
                await minh.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await shot(minh, '8-minh-toast-on-load')
                # Caps: Lan's room today (2,000 - 620) is checked before the confirm step...
                await click(lan, '.bk-sheet [data-bk="x-again"]')
                await lan.wait_for_selector('.bk-sheet .bx-friend', timeout=10000)
                await shot(lan, '9-pick-recent')
                await send(lan, amount=1500)
                await click(lan, '.bk-sheet [data-bk="x-next"]')
                await lan.wait_for_selector('.bk-sheet .bx .bk-alert.bad', timeout=5000)
                text = await lan.inner_text('.bk-sheet .bx .bk-alert.bad')
                assert 'còn chuyển được 1.380 xu' in text, text
                await shot(lan, '10-limit-sender')
                # ... and Minh's daily receive cap is the server's answer.
                py(NEAR_CAP, db, pages['Minh'][1])
                await lan.fill('.bk-sheet #bx-amt', '300')
                await click(lan, '.bk-sheet [data-bk="x-next"]')
                await lan.wait_for_selector('.bk-sheet .bx-confirm', timeout=5000)
                await click(lan, '.bk-sheet [data-bk="x-send"]')
                await lan.wait_for_selector('.bk-sheet .bx-confirm .bk-alert.bad', timeout=10000)
                text = await lan.inner_text('.bk-sheet .bx-confirm .bk-alert.bad')
                assert 'Minh chỉ nhận thêm được 100 xu' in text, text
                await shot(lan, '11-limit-receiver')
                rows = json.loads(py(CHECK, db))
                assert [(r['amount'], r['status']) for r in rows] == [(500, 'done'), (120, 'done')], rows
                print(tag, 'ok', rows)
            except Exception:
                for who, (pg, _) in pages.items():
                    await pg.screenshot(path=str(OUT / f'{tag}-FAIL-{who}.png'))
                raise
            finally:   # before the server stops: a page left open would only log refused polls
                for pg, _ in pages.values():
                    await pg.context.close()
        await browser.close()
    errors = [e for e in errors if 'status of 429' not in e]   # the receive cap step answers 429 on purpose
    if errors:
        print('CONSOLE ERRORS:', *errors, sep='\n  ')
        sys.exit(1)
    print('no console errors; shots in', OUT)


if __name__ == '__main__':
    asyncio.run(main())
