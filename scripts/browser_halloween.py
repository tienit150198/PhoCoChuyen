"""🎃 Lễ hội Ma Phố (game/halloween.py): a browser walk-through on a phone (dev tool, needs playwright + chromium, TEST_DATABASE_URL).

Runs the real server with the season's clock moved (game.halloween.now only: the rest of the game keeps the real time):
- before (25/10 23:50 VN): no menu entry, no card, no Tiện ích entry, the API says 'before';
- day 1 (26/10 10:00 VN): the start card opens by itself (after "Có gì mới"), "Nhận kẹo" checks in and opens the sheet;
  the four tabs (a riddle solved, a knock on a neighbour's door, an exchange paid into the save), the town's decor;
- the night (31/10 20:00 VN): the night card, the giant pumpkin.
Screenshots at 390×844; checks: nothing overflows sideways, no page error, the server took each act.

    python scripts/browser_halloween.py [out_dir]
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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_v04 import free_port  # noqa: E402
from pg_test_support import test_env  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_halloween_shots'
WIDE = '()=>document.documentElement.scrollWidth-innerWidth'
VN = 7 * 3600
BEFORE = 1792947600 - 600            # 25/10 23:50 VN
DAY1 = 1792947600 + 10 * 3600        # 26/10 10:00 VN
NIGHT = 1793448000 + 3600            # 31/10 20:00 VN
# the server with the season's clock moved: game.halloween.now (and the ticker's and bootstrap's hint) only
LAUNCH = '''
import os, runpy, sys, time
sys.path.insert(0, os.getcwd())
from game import halloween as h
t0, at = time.time(), float(os.environ["HW_AT"])
h.now = lambda: at + (time.time() - t0)
hint, line = h.hint, h.news_line
h.hint = lambda t=None: hint(h.now())
h.news_line = lambda t=None: line(h.now())
sys.argv = ["server.py"] + sys.argv[1:]
runpy.run_path("server.py", run_name="__main__")
'''


@contextlib.contextmanager
def server(at: float):
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-hween-')
    env = test_env(QUIET='1', PUSH_DISABLED='1', HW_AT=str(at), MNL_HALLOWEEN_OFF='0')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.db')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([sys.executable, '-c', LAUNCH, '--port', str(port), '--namespace', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:  # noqa: BLE001
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


def account(db: str, token: str, user: str, display: str, life: int = 5) -> str:
    from game import accounts
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    with patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):
        tok = accounts.register(store, token, dict(username=user, password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=display))['token']

    def fn(s):
        s['name'] = display
        s['journey'].update(story=True, intro=True, life_day=life, gender='female')
    mr._mutate(store, {store.key(tok): fn})
    store.close_pool()
    return tok


def sql(db: str, q: str, args=()):
    from game.storage import Store
    store = Store(db, story=True)
    with store.connect() as c:
        cur = c.execute(q, args)
        out = [dict(r) for r in cur.fetchall()] if cur.description else []
    store.close_pool()
    return out


async def phone(browser):
    ctx = await browser.new_context(viewport=dict(width=390, height=844), device_scale_factor=2, has_touch=True, is_mobile=True)
    return ctx, await ctx.new_page()


async def enter(page, ctx, base, db, user, display, errors):
    """A story save with an account, past the first questions, on the town."""
    page.on('pageerror', lambda e: errors.append(str(e)))
    await page.goto(base)
    await page.wait_for_timeout(2500)
    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
    tok = account(db, token, user, display)
    host = base.split('//')[1].split(':')[0]
    await ctx.add_cookies([dict(name='mnl_session', value=tok, domain=host, path='/', httpOnly=True, sameSite='Strict')])
    await page.goto(base)
    for sel in ('text=Nữ', 'text=Lưu và tiếp tục', '[data-interface="new"]'):
        try:
            await page.click(sel, timeout=8000)
            await page.wait_for_timeout(800)
        except Exception:  # noqa: BLE001 - not asked
            pass
    try:   # "Có gì mới" goes first (v4/break-gate.js)
        await page.wait_for_selector('#wnDialog[open]', timeout=15000)
        await page.wait_for_timeout(900)
        await page.click('#wnDialog [data-wn="close"].btn')
    except Exception:  # noqa: BLE001
        pass
    return tok


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, fails = [], []
    check = lambda ok, what: ok or fails.append(what)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        # 1 · before 26/10 00:00 VN: nothing at all
        with server(BEFORE) as (base, db):
            ctx, page = await phone(browser)
            await enter(page, ctx, base, db, 'an_hw', 'An', errors)
            await page.wait_for_timeout(5000)
            check(not await page.evaluate("!!document.getElementById('hwCard')"), 'before: no card')
            check(await page.locator('[data-action="halloween"]').count() == 0, 'before: no entry')
            v = json.loads(await page.evaluate("fetch('/api/halloween').then(r=>r.text())"))
            check(v.get('state') == 'before', f'before: the API says before ({v.get("state")})')
            await page.screenshot(path=str(OUT / '00-before.png'))
            await ctx.close()
        # 2 · day 1
        with server(DAY1) as (base, db):
            nctx, n = await phone(browser)   # a neighbour whose door is knocked on
            await enter(n, nctx, base, db, 'mai_hw', 'Mai', errors)
            r = json.loads(await n.evaluate("fetch('/api/halloween').then(r=>r.text())"))
            check(r.get('state') == 'open', f'day 1: open ({r.get("state")})')
            try:   # the neighbour joins the season: the card's "Nhận kẹo"
                await n.wait_for_selector('#hwCard[open]', timeout=40000)
                await n.wait_for_timeout(700)
                await n.click('#hwCard [data-hwc="go"]')
                await n.wait_for_selector('.hw-sheet[open] .hw-candy', timeout=15000)
            except Exception as e:  # noqa: BLE001
                fails.append(f'the neighbour could not check in: {e}')
            ctx, page = await phone(browser)
            await enter(page, ctx, base, db, 'lan_hw', 'Lan', errors)
            try:
                await page.wait_for_selector('#hwCard[open]', timeout=40000)
                await page.wait_for_timeout(700)
                await page.screenshot(path=str(OUT / '01-start-card.png'))
                check('kẹo' in await page.inner_text('#hwCard'), 'the card offers candy')
                check(await page.evaluate(WIDE) <= 0, 'card overflows sideways')
                await page.click('#hwCard [data-hwc="go"]')
            except Exception as e:  # noqa: BLE001
                await page.screenshot(path=str(OUT / '01-start-card.png'))
                fails.append(f'the start card did not open: {e}')
            await page.wait_for_selector('.hw-sheet[open] .hw-candy', timeout=15000)
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(OUT / '02-today.png'))
            me = sql(db, "SELECT candy FROM hw_players p JOIN accounts a ON a.sid=p.sid WHERE a.username='lan_hw'")
            check(me and me[0]['candy'] == 15, f'checked in on the opening day: 15 candy ({me})')
            # a riddle: pick the right place (the server's answer, read from the DB-free helper)
            from game import halloween as h
            spot = h.spots(h.vn_day(DAY1))[0]['key']
            await page.click(f'[data-hw="pick"][data-spot="0"][data-place="{spot}"]')
            await page.click('[data-hw="guess"][data-spot="0"]')
            await page.wait_for_timeout(900)
            await page.screenshot(path=str(OUT / '03-riddle-found.png'), full_page=True)
            check(await page.evaluate(WIDE) <= 0, 'sheet overflows sideways')
            # enough candy for an exchange (the knock's answer brings the new balance)
            sql(db, "UPDATE hw_players SET candy=candy+300, earned=earned+300 WHERE sid=(SELECT sid FROM accounts WHERE username='lan_hw')")
            await page.click('[data-hw="tab"][data-tab="knock"]')
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(OUT / '04-knock.png'))
            doors = await page.locator('[data-hw="knock"]').count()
            check(doors >= 1, 'a door to knock on (the neighbour of the season)')
            if doors:
                await page.locator('[data-hw="knock"]').first.click()
                await page.wait_for_timeout(900)
                await page.screenshot(path=str(OUT / '05-knocked.png'))
            await page.click('[data-hw="tab"][data-tab="shop"]')
            await page.wait_for_timeout(900)
            await page.screenshot(path=str(OUT / '06-shop.png'))
            await page.click('[data-hw="buy"][data-item="t_hw_san_bi_ngo"]')
            await page.wait_for_timeout(1200)
            await page.screenshot(path=str(OUT / '07-bought.png'))
            st = sql(db, "SELECT status FROM live_effects WHERE kind='hween'")
            check(st and all(x['status'] != 'pending' for x in st), f'the exchange is paid into the save ({st})')
            await page.click('[data-hw="tab"][data-tab="board"]')
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUT / '08-board.png'))
            await page.click('.hw-sheet [data-hw="close"]')
            await page.wait_for_timeout(1500)
            await page.screenshot(path=str(OUT / '09-town.png'))
            check(await page.evaluate("!!document.querySelector('.hw-town:not([hidden])')"), "the town's decor shows")
            check(await page.locator('[data-action="halloween"]').count() > 0, 'the menu / Tiện ích entry is there')
            await page.reload()
            await page.wait_for_timeout(7000)
            check(not await page.evaluate("!!document.getElementById('hwCard')?.open"), 'the card: not again today')
            await ctx.close()
            await nctx.close()
        # 3 · the night of 31/10
        with server(NIGHT) as (base, db):
            ctx, page = await phone(browser)
            await enter(page, ctx, base, db, 'hoa_hw', 'Hoa', errors)
            try:
                await page.wait_for_selector('#hwCard[open]', timeout=40000)
                await page.wait_for_timeout(700)
                await page.screenshot(path=str(OUT / '10-night-card.png'))
                await page.click('#hwCard [data-hwc="go"]')
                await page.wait_for_selector('.hw-sheet[open] [data-hw="giant"]', timeout=15000)
                await page.click('[data-hw="giant"]')
                await page.wait_for_timeout(900)
                await page.screenshot(path=str(OUT / '11-night-giant.png'))
                me = sql(db, "SELECT candy FROM hw_players p JOIN accounts a ON a.sid=p.sid WHERE a.username='hoa_hw'")
                check(me and me[0]['candy'] == 2 * 10 + 30, f'night: the check-in doubled, the giant pumpkin ({me})')
                await page.click('.hw-sheet [data-hw="close"]')
                await page.wait_for_timeout(1500)
                await page.screenshot(path=str(OUT / '12-night-town.png'))
            except Exception as e:  # noqa: BLE001
                await page.screenshot(path=str(OUT / '10-night-card.png'))
                fails.append(f'the night: {e}')
            await ctx.close()
        await browser.close()
    print(json.dumps(dict(out=str(OUT), errors=errors[:10], fails=fails), ensure_ascii=False, indent=1))
    return 1 if errors or fails else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
