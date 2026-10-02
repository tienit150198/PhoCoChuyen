#!/usr/bin/env python3
"""😍 Reactions in chat and 🔎 the admin "Tin nhắn" tab in real browsers (dev tool, needs `pip install playwright
websockets` + chromium).

Starts a game server and the live service (chat on, ADMIN_USERS=op_admin) on one SQLite database (servers() of
scripts/browser_live_pin.py; MNL_PY / MNL_PYTHONPATH as there). Two phones (390×844, touch):
  * the player holds the admin's message with a real touch (CDP touchStart, 600 ms, touchEnd): the emoji bar opens,
    with the action row under it (🗑️ since 03/10), no text selected; ❤️ → a chip "❤️ 1" on both phones (highlighted on the player's own);
  * the admin holds the same message with the mouse and picks ❤️ too (2), then the player taps their chip
    (takes it back: 1); a short tap still opens the action row (📌 Ghim tin này for the admin); dark theme;
  * the admin page (/admin.html#chat › Tin nhắn): 200 a page, searching "0912" finds the player's masked message
    and shows "Gốc: …" (what was typed); filtering by that player; phone and desktop, light and dark.
Fails on console errors, page errors or HTTP 5xx. Screenshots into --shots.

  MNL_PY=python3.12 python scripts/browser_live_react.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import PW, phone, send, text_of  # noqa: E402
from browser_live_pin import servers, until  # noqa: E402

TYPED = 'Ai cần bánh trung thu nhắn mình nha, gọi 0912 345 678'


async def hold_touch(p, sel: str, ms=600):
    """A real long press with a finger: touch events through the DevTools protocol (pointerType 'touch')."""
    box = await p.page.locator(sel).first.bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    cdp = await p.ctx.new_cdp_session(p.page)
    await cdp.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=x, y=y)]))
    await p.page.wait_for_timeout(ms)
    await cdp.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[]))
    await cdp.detach()


async def hold_mouse(p, sel: str, ms=600):
    box = await p.page.locator(sel).first.bounding_box()
    await p.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    await p.page.mouse.down()
    await p.page.wait_for_timeout(ms)
    await p.page.mouse.up()


async def chips(p) -> str:
    """The chips under the messages as 'emoji:count,…'."""
    return await p.page.evaluate("[...document.querySelectorAll('.ch-chip')].map(c=>c.dataset.e+':'+c.querySelector('b').textContent).join(',')")


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-react-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db, py, env):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Quản Lý', problems)
            b = await phone(browser, base, 'Minh Tú', problems)
            await a.api('/api/account/register', dict(username='op_admin', password=PW, confirm=PW, display='Ban Quản Lý'))
            await b.api('/api/account/register', dict(username='minhtu_t', password=PW, confirm=PW, display='Minh Tú'))
            with sqlite3.connect(db) as con:
                con.execute("UPDATE stat_births SET day='2026-01-01' WHERE sid=(SELECT sid FROM accounts WHERE username='minhtu_t')")
            for p in (a, b):
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
                await p.page.click('.live-fab')
                await p.page.wait_for_selector('.chat-sheet[open] .ch-tabs')
            await until(b.page, "document.querySelector('.chat-sheet .ch-compose:not([hidden])')", 'B can write')
            await send(b, TYPED)
            await until(a.page, "document.querySelectorAll('.ch-msg:not(.mine)').length===1", 'A sees B')
            got = await text_of(a.page, '.ch-msg:not(.mine) .ch-bub')
            check('0912' not in got and '•••' in got, f'the phone number is masked for players ({got[-40:]!r})')
            await send(a, 'Tối nay rước đèn ở Bờ hồ nhé cả phố 🏮')
            await until(b.page, "document.querySelectorAll('.ch-msg.adm:not(.mine)').length===1", 'B sees the admin message')

            # ---- the player holds the admin's message (touch) ----
            await hold_touch(b, '.ch-msg.adm .ch-bub')
            await until(b.page, "document.querySelector('.ch-react-bar')", 'B: the emoji bar after a long press')
            emo = await b.page.evaluate("[...document.querySelectorAll('.ch-react-bar .ch-emo')].map(e=>e.textContent).join(' ')")
            check(emo == '❤️ 😂 😮 😢 👍 🔥', f'six reactions in order ({emo!r})')
            check(await b.page.evaluate("!!document.querySelector('.ch-actbar')"), 'a long press opens the action row too (🗑️ owner, 03/10)')
            check(await b.page.evaluate("getSelection().toString()===''"), 'no text selected by the long press')
            await b.page.wait_for_timeout(500)
            check(await chips(b) == '' and await b.page.evaluate("!!document.querySelector('.ch-react-bar')"),
                  'lifting the finger picks nothing (the bar opened under it), the bar stays open')
            box = await b.page.evaluate("(() => { const r = document.querySelector('.ch-react-bar').getBoundingClientRect(); return [r.left, r.right]; })()")
            check(box[0] >= 0 and box[1] <= 390, f'the emoji bar fits 390 px ({box})')
            await b.shot(shots, '01-player-long-press-emoji-bar')
            await b.page.tap('.ch-react-bar .ch-emo[data-e="❤️"]')
            await until(b.page, "document.querySelector('.ch-reacts .ch-chip.on')", 'B: my chip')
            await until(a.page, "document.querySelector('.ch-reacts .ch-chip')?.innerText.includes('1')", 'A: the chip arrives')
            check(await b.page.evaluate("!document.querySelector('.ch-react-bar')"), 'the bar closes after picking')
            check(await chips(a) == '❤️:1', f'A sees ❤️ 1 ({await chips(a)})')
            check(await a.page.evaluate("!document.querySelector('.ch-chip.on')"), "A's view: not highlighted (not mine)")
            await b.shot(shots, '02-player-reacted-chip')

            # ---- the admin holds it with the mouse, ❤️ too ----
            await hold_mouse(a, '.ch-msg.mine .ch-bub')
            await until(a.page, "document.querySelector('.ch-react-bar')", 'A: the emoji bar (mouse)')
            check(await a.page.evaluate("!!document.querySelector('.ch-actbar')"), 'mouse long press: the action row too')
            await a.page.click('.ch-react-bar .ch-emo[data-e="😂"]')
            await until(b.page, "document.querySelectorAll('.ch-reacts .ch-chip').length===2", 'B: two kinds')
            await hold_mouse(a, '.ch-msg.mine .ch-bub')
            await until(a.page, "document.querySelector('.ch-react-bar .ch-emo.on')", 'A: the bar shows my 😂')
            await a.page.click('.ch-react-bar .ch-emo[data-e="❤️"]')   # replaces 😂
            await until(b.page, "document.querySelectorAll('.ch-reacts .ch-chip').length===1 && document.querySelector('.ch-chip').innerText.includes('2')",
                        'B: ❤️ 2 (😂 replaced)')
            check(await chips(b) == '❤️:2' and await chips(a) == '❤️:2', f'replaced: ❤️ 2 ({await chips(b)})')
            await a.shot(shots, '03-admin-reacted-two')
            await b.shot(shots, '04-player-sees-two')
            await b.page.tap('.ch-reacts .ch-chip')                       # the player takes theirs back
            await until(a.page, "document.querySelector('.ch-chip')?.innerText.includes('1')", 'A: back to 1')
            check(await b.page.evaluate("!document.querySelector('.ch-chip.on')"), 'B: taken back, not highlighted')
            # a short tap is still the action row (📌 for the admin)
            await a.page.locator('.ch-msg:not(.mine) .ch-bub').first.click()
            await until(a.page, "document.querySelector('.ch-actbar [data-ch-act=pin]')", 'A: a tap opens the menu with 📌')
            check(await a.page.evaluate("!document.querySelector('.ch-react-bar')"), 'a tap does not open the emoji bar')
            await a.page.locator('.ch-msg:not(.mine) .ch-bub').first.click()
            await b.page.evaluate("document.documentElement.dataset.theme='dem'")
            await hold_touch(b, '.ch-msg:not(.mine) .ch-bub')
            await until(b.page, "document.querySelector('.ch-react-bar')", 'B: bar in dark')
            await b.shot(shots, '05-player-dark-emoji-bar')
            await b.page.tap('.ch-react-bar .ch-emo[data-e="🔥"]')
            await until(b.page, "document.querySelector('.ch-chip.on')", 'B: 🔥 chip')
            await b.shot(shots, '06-player-dark-chips')

            # ---- the admin page: Tin nhắn, search, Gốc ----
            adm = await a.ctx.new_page()
            adm.on('console', lambda m: m.type == 'error' and problems.append(f'admin console: {m.text[:200]}'))
            adm.on('pageerror', lambda e: problems.append(f'admin exception: {str(e)[:200]}'))
            adm.on('response', lambda r: r.status >= 500 and problems.append(f'admin HTTP {r.status} {r.url}'))
            await adm.goto(base + '/admin.html#chat')
            await adm.wait_for_selector('[data-act=chatTab][data-value=msgs]', timeout=20000)
            await adm.click('[data-act=chatTab][data-value=msgs]')
            await until(adm, "document.querySelectorAll('.chat-town .chat-line').length>=2", 'admin: messages listed')
            await adm.fill('.chat-search input[name=q]', '0912')
            await adm.click('.chat-search button[type=submit]')
            await until(adm, "document.querySelector('.chat-filters') && document.querySelectorAll('.chat-town .chat-line').length===1", 'admin: one hit')
            raw = await text_of(adm, '.chat-raw')
            line = await text_of(adm, '.chat-line .chat-text')
            check('Gốc:' in raw and '0912 345 678' in raw, f'the original next to the masked text ({raw!r})')
            check('•••' in line, f'the masked text is shown too ({line[:60]!r})')
            check('1.2.2' in await text_of(adm, '.note'), 'the note: older messages stay masked')
            await adm.wait_for_timeout(300)
            await adm.screenshot(path=str(shots / '07-admin-phone-search-original.png'), full_page=True)
            await adm.click('.chat-line [data-act=chatPid]')   # that player's messages
            await until(adm, "[...document.querySelectorAll('.chat-filters .chip')].some(c=>c.innerText.includes('👤'))", 'admin: player filter')
            # desktop, light and dark (same session cookie)
            for scheme in ('light', 'dark'):
                ctx = await browser.new_context(viewport=dict(width=1280, height=900), color_scheme=scheme)
                await ctx.add_cookies(await a.ctx.cookies())
                pg = await ctx.new_page()
                pg.on('pageerror', lambda e: problems.append(f'desktop exception: {str(e)[:200]}'))
                await pg.goto(base + '/admin.html#chat')
                await pg.wait_for_selector('[data-act=chatTab][data-value=msgs]', timeout=20000)
                await pg.click('[data-act=chatTab][data-value=msgs]')
                await until(pg, "document.querySelectorAll('.chat-town .chat-line').length>=2", f'desktop {scheme}: listed')
                await pg.fill('.chat-search input[name=q]', '0912')
                await pg.click('.chat-search button[type=submit]')
                await until(pg, "document.querySelector('.chat-raw')", f'desktop {scheme}: Gốc')
                await pg.wait_for_timeout(300)
                await pg.screenshot(path=str(shots / f'08-admin-desktop-search-{scheme}.png'))
                await ctx.close()
            # players never see the original (their pages and the endpoint)
            for p in (a, b):
                html = await p.page.evaluate('document.body.innerHTML')
                check('0912 345 678' not in html,f'{p.name}: no original in the game page')
            status = await b.page.evaluate("fetch('/api/admin/chat/messages?q=0912').then(r=>r.status)")
            await b.page.wait_for_timeout(200)
            problems[:] = [x for x in problems if not (x.startswith('Minh Tú console') and '403' in x)]   # that one, on purpose
            check(status == 403, f'player: /api/admin/chat/messages is 403 ({status})')
            await browser.close()
    for c in checks:
        print(c)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', default=str(ROOT / '_react_shots'))
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
