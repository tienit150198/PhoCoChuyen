#!/usr/bin/env python3
"""📌 Admin messages and the pinned message of Cả phố in two browsers (dev tool, needs `pip install playwright
websockets` + chromium).

Starts a game server (story mode, SQLite) and the live service (chat on, ADMIN_USERS=op_admin) on the same
database. MNL_PY picks the servers' Python (the live service needs websockets, Python 3.12) when playwright lives
in another one; MNL_PYTHONPATH their library path. Two phones (390×844):
  * the admin (account op_admin, a brand-new session: players would wait 10 minutes) posts on Cả phố at once, twice,
    no countdown; the message keeps its link and hotline, carries "📢 Quản trị", the link opens in a new tab;
  * a player's own link and phone number are still masked, never a link, and the slow mode still counts down;
  * the admin taps the player's message → "📌 Ghim tin này" → both phones show the pinned bar; the player taps
    the bar (whole text); the admin pins their own message instead (a clickable link in the bar), then "Bỏ ghim";
  * the operator's announcement (a row with pid 'admin', written straight into the database) is pinned with
    scripts/chat_pin.py and reaches the player within the 30 s poll; dark theme.
Fails on console errors, page errors or HTTP 5xx. Screenshots into --shots.

  MNL_PY=python3.12 python scripts/browser_live_pin.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import PW, free_port, phone, send, text_of, wait_http  # noqa: E402

ANN = '📢 Ban quản lý Phố'
ANN_TEXT = ('Chào cả phố! Từ tối nay Phố Có Chuyện mở sự kiện Trung thu 🏮 — rước đèn, phá cỗ, quà cho cả nhà.\n'
            'Chi tiết: https://phocochuyen.io.vn/trung-thu. Góp ý gửi Ban quản lý nhé!')


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.sqlite3')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live', ADMIN_USERS='OP_Admin')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    py = os.environ.get('MNL_PY') or sys.executable
    if os.environ.get('MNL_PYTHONPATH'):
        env['PYTHONPATH'] = os.environ['MNL_PYTHONPATH']
    game = subprocess.Popen([py, 'server.py', '--port', str(gp), '--db', db], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, LIVE_CHAT='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([py, '-m', 'live', '--db', db], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db, py, env
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


async def until(page, js: str, what: str, timeout=8.0):
    """Poll a JS expression with page.evaluate (the game's CSP forbids wait_for_function)."""
    end = time.monotonic() + timeout
    while True:
        if await page.evaluate(f'() => Boolean({js})'):
            return
        if time.monotonic() > end:
            raise AssertionError(f'timed out: {what}')
        await asyncio.sleep(0.2)


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-pin-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db, py, env):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Quản Lý', problems)
            b = await phone(browser, base, 'Minh Tú', problems)
            await a.api('/api/account/register', dict(username='op_admin', password=PW, confirm=PW, display='Ban Quản Lý'))
            await b.api('/api/account/register', dict(username='minhtu_t', password=PW, confirm=PW, display='Minh Tú'))
            with sqlite3.connect(db) as con:   # only the player is a long-time one; the admin's session is brand new
                con.execute("UPDATE stat_births SET day='2026-01-01' WHERE sid=(SELECT sid FROM accounts WHERE username='minhtu_t')")
            for p in (a, b):
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
                await p.page.click('.live-fab')
                await p.page.wait_for_selector('.chat-sheet[open] .ch-tabs')
            await until(a.page, "document.querySelector('.chat-sheet .ch-compose:not([hidden])')", 'the admin can write at once')
            check(await a.page.evaluate("document.querySelector('.chat-sheet textarea').maxLength") == 500, 'admin composer: 500 characters')

            # ---- the player first: masked, slow mode ----
            await send(b, 'Ai qua quán mình chơi: https://quanminh.vn gọi 0912 345 678')
            await until(a.page, "document.querySelectorAll('.ch-msg:not(.mine)').length>0", 'A sees B')
            got = await text_of(a.page, '.ch-msg:not(.mine) .ch-bub')
            check('0912' not in got and 'quanminh' not in got and '•••' in got, f'player link and phone masked ({got[:80]!r})')
            check(await a.page.evaluate("!document.querySelector('.ch-msg:not(.mine) a')"), 'no link in a player message')
            cd = await text_of(b.page, '.ch-send.wait')
            check(cd.strip().isdigit(), f'player slow mode still counts down ({cd!r})')

            # ---- the admin posts freely ----
            await send(a, 'Sự kiện Trung thu tối nay 🏮 https://phocochuyen.io.vn/trung-thu?tu=20h — hotline 0912 345 678')
            await until(a.page, "document.querySelectorAll('.ch-msg.mine').length===1", 'admin message 1')
            check(await a.page.evaluate("!document.querySelector('.ch-send.wait')"), 'admin: no countdown')
            await send(a, 'Nhớ mang đèn lồng nhé cả nhà!')
            await until(a.page, "document.querySelectorAll('.ch-msg.mine').length===2", 'admin message 2 right away')
            await until(b.page, "document.querySelectorAll('.ch-msg.adm:not(.mine)').length===2", 'B gets both admin messages')
            badge = await text_of(b.page, '.ch-msg.adm .ch-name')
            check('📢 Quản trị' in badge and 'Ban Quản Lý' in badge, f'admin badge next to the name ({badge!r})')
            link = await b.page.evaluate("""() => { const a = document.querySelector('.ch-msg.adm a.ch-link');
              return a && {href: a.getAttribute('href'), target: a.target, rel: a.rel, text: a.textContent}; }""")
            check(bool(link) and link['href'] == 'https://phocochuyen.io.vn/trung-thu?tu=20h' and link['target'] == '_blank'
                  and link['rel'] == 'noopener noreferrer', f'admin link is a safe link ({link})')
            check('0912 345 678' in await text_of(b.page, '.ch-msg.adm .ch-bub'), 'admin hotline not masked')
            await b.shot(shots, '01-player-sees-admin-messages')
            # the player taps an admin message: no report, no block
            await b.page.locator('.ch-msg.adm .ch-bub').first.click()
            bar = await text_of(b.page, '.ch-actbar')
            check('Báo cáo' not in bar and 'Chặn' not in bar and 'Ghim' not in bar, f'player on an admin message: no report/block/pin ({bar!r})')
            await b.page.locator('.ch-msg.adm .ch-bub').first.click()

            # ---- the admin taps the player's message → 📌 Ghim tin này ----
            await a.page.locator('.ch-msg:not(.mine) .ch-bub').first.click()
            await a.page.wait_for_selector('.ch-actbar [data-ch-act=pin]')
            bar = await text_of(a.page, '.ch-actbar')
            check('📌 Ghim tin này' in bar and 'Báo cáo' in bar, f'admin action row ({bar!r})')
            await a.shot(shots, '02-admin-message-menu-pin')
            await a.page.click('.ch-actbar [data-ch-act=pin]')
            for p in (a, b):
                await until(p.page, "document.querySelector('.ch-pinbar:not([hidden]) .ch-pin')", f'{p.name}: pinned bar')
            pin_b = await text_of(b.page, '.ch-pinbar')
            check('Minh Tú' in pin_b and '•••' in pin_b, f'pinned bar on the player ({pin_b!r})')
            check(await b.page.evaluate("!document.querySelector('.ch-pinbar [data-ch-act=unpin]')"), 'no "Bỏ ghim" for players')
            check(await a.page.evaluate("!!document.querySelector('.ch-pinbar [data-ch-act=unpin]')"), '"Bỏ ghim" on the bar for the admin')
            await a.shot(shots, '03-admin-pinned')
            await b.shot(shots, '04-player-pinned-bar')

            # ---- the admin pins their own message (a link in the bar), the player expands it ----
            await a.page.locator('.ch-msg.mine .ch-bub').first.click()
            await a.page.click('.ch-actbar [data-ch-act=pin]')
            await until(b.page, "document.querySelector('.ch-pinbar a.ch-link')", 'B: the admin pin with its link')
            await b.page.click('.ch-pin-main')
            await until(b.page, "document.querySelector('.ch-pin.open')", 'B: bar expanded')
            check(await b.page.evaluate("document.querySelector('.ch-pinbar .ch-adm')?.textContent") == '📢 Quản trị', 'admin badge in the bar')
            await b.shot(shots, '05-player-pin-admin-link-open')
            box = await b.page.evaluate("(() => { const r = document.querySelector('.ch-pinbar').getBoundingClientRect(); return [r.left, r.right, document.documentElement.scrollWidth]; })()")
            check(box[0] >= 0 and box[1] <= 390 and box[2] <= 390, f'pinned bar fits 390 px ({box})')

            # ---- Bỏ ghim ----
            await a.page.click('.ch-pinbar [data-ch-act=unpin]')
            for p in (a, b):
                await until(p.page, "document.querySelector('.ch-pinbar').hidden", f'{p.name}: bar gone')
            check(True, 'unpinned on both phones')

            # ---- the operator's announcement, pinned from the server ----
            with sqlite3.connect(db) as con:
                mid = con.execute("INSERT INTO chat_messages(channel, pid, name, av, text, at) VALUES('town', 'admin', ?, '📢', ?, ?) RETURNING id",
                                  (ANN, ANN_TEXT, time.time())).fetchone()[0]
            out = subprocess.run([py, 'scripts/chat_pin.py', '--db', db, '--msg', str(mid)], cwd=ROOT, env=env, capture_output=True,
                                 text=True, encoding='utf-8')
            check(out.returncode == 0 and 'Đã ghim' in out.stdout, f'scripts/chat_pin.py ({out.stdout.strip()[-80:]!r} {out.stderr[-200:]!r})')
            t0 = time.monotonic()
            await until(b.page, "document.querySelector('.ch-pinbar:not([hidden])')?.innerText.includes('Ban quản lý Phố')",
                        'B: the announcement pinned within 30 s', timeout=40)
            check(True, f'the announcement reached the player in {time.monotonic() - t0:.0f} s')
            check(await b.page.evaluate("document.querySelector('.ch-pinbar a.ch-link')?.getAttribute('href')") == 'https://phocochuyen.io.vn/trung-thu',
                  'announcement link (trailing dot left out)')
            await b.shot(shots, '06-player-announcement-pinned')
            await b.page.click('.ch-pin-main')
            await b.page.evaluate("document.documentElement.dataset.theme='dem'")
            await b.shot(shots, '07-player-announcement-open-dark')
            await a.page.evaluate("document.documentElement.dataset.theme='dem'")
            await a.page.locator('.ch-msg:not(.mine) .ch-bub').first.click()
            await a.shot(shots, '08-admin-dark-menu')
            await browser.close()
    for c in checks:
        print(c)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', default=str(ROOT / '_pin_shots'))
    a = ap.parse_args()
    shots = Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(shots))
    for p in problems:
        print('PROBLEM', p)
    print('OK' if not problems else f'{len(problems)} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
