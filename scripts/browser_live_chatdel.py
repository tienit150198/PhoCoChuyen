#!/usr/bin/env python3
"""🗑️ Deleting in chat and 🚫 the blocked list in real browsers (dev tool, needs `pip install playwright websockets` +
chromium; MNL_PY / MNL_PYTHONPATH pick the Python of the servers, as in scripts/browser_live_pin.py).

Two friends on phones (390×844, touch):
  * B holds A's message with a finger (CDP touch, 600 ms): the emoji bar and the action row open; "Xóa ở phía tôi"
    asks "Xóa thật?", then the message leaves B's screen only (A still has it); no "Thu hồi" on someone else's;
  * A holds their own message: "Thu hồi" → "Thu hồi thật?" → B sees "Tin nhắn đã thu hồi"; B right-clicks that line:
    only "Xóa ở phía tôi";
  * B's Tin nhắn: holding the chat ticks it ("Chọn"), "Xóa (1)" → "Xóa 1 cuộc trò chuyện?" → gone from B's list,
    still in A's;
  * B blocks A (DM header), Tin nhắn → "🚫 Đã chặn" lists A, "Bỏ chặn" empties the list;
  * nothing wider than 390 px. Fails on console errors, page errors or HTTP 5xx. Screenshots into --shots.

  MNL_PY=python3.12 MNL_PYTHONPATH=<websockets 17> python scripts/browser_live_chatdel.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import PW, phone, send, text_of  # noqa: E402
from browser_live_pin import servers, until  # noqa: E402
from browser_live_react import hold_touch  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for

COUNT = "document.querySelectorAll('.ch-msg .ch-bub').length"
FITS = "(() => { const b = document.querySelector('.chat-sheet .ch-body'); return b.scrollWidth <= b.clientWidth + 1 && document.documentElement.scrollWidth <= 391; })()"


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-chatdel-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db, py, env):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Lan Anh', problems)
            b = await phone(browser, base, 'Minh Tú', problems)
            await a.api('/api/account/register', dict(username='lananh_t', password=PW, confirm=PW, display='Lan Anh'))
            await b.api('/api/account/register', dict(username='minhtu_t', password=PW, confirm=PW, display='Minh Tú'))
            await a.api('/api/marriage/friend_request', dict(username='minhtu_t'))
            rid = (await b.api('/api/marriage'))['friends']['incoming'][0]['id']
            await b.api('/api/marriage/friend_respond', dict(id=rid, answer='accept'))
            with test_connect(db) as con:
                con.execute("UPDATE stat_births SET day='2026-01-01'")
            for p in (a, b):
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
                await p.page.click('.live-fab')
                await p.page.wait_for_selector('.chat-sheet[open] .ch-tabs')
            check(await b.page.evaluate("(async () => (await import('/js/v4/live.js')).live.flags.chatdel)()"), 'the service says chatdel')

            # ---- A writes to B ----
            await a.page.click('[data-ch-act=tab][data-tab=friends]')
            await a.page.click('.ch-row[data-ch-act=dm]')
            await until(a.page, "document.querySelector('.chat-sheet .ch-compose:not([hidden])')", 'A: DM composer')
            for t in ('Tối nay đi chợ đêm không?', 'Mình mua bánh rồi nè', 'Nhầm, tin này gửi lộn'):
                await send(a, t)
                await a.page.wait_for_timeout(250)
            await until(a.page, f'{COUNT}===3', 'A: three messages')
            await b.page.click('[data-ch-act=tab][data-tab=inbox]')
            await until(b.page, "document.querySelector('.ch-row[data-ch-act=open]')", 'B: the DM in Tin nhắn')
            await b.shot(shots, '01-inbox-tools')
            check(await b.page.evaluate("!!document.querySelector('[data-ch-act=selMode]') && !!document.querySelector('[data-ch-act=blocks]')"),
                  'Tin nhắn: "Chọn" and "Đã chặn"')
            await b.page.click('.ch-row[data-ch-act=open]')
            await until(b.page, f'{COUNT}===3', 'B: three messages')

            # ---- B holds A's first message: delete on my side ----
            await hold_touch(b, '.ch-msg:not(.mine) .ch-bub')
            await until(b.page, "document.querySelector('.ch-react-bar') && document.querySelector('.ch-actbar [data-ch-act=hide]')",
                        'B: emoji bar and action row after a long press')
            check(await b.page.evaluate("!document.querySelector('.ch-actbar [data-ch-act=del]')"), 'no "Thu hồi" on a friend\'s message')
            check(await b.page.evaluate("getSelection().toString()===''"), 'no text selected by the long press')
            check(await b.page.evaluate(FITS), 'the held message fits 390 px')
            await b.shot(shots, '02-long-press-menu')
            await b.page.tap('.ch-actbar [data-ch-act=hide]')
            await until(b.page, "document.querySelector('.ch-actbar [data-ch-act=hide].warn')", 'B: "Xóa thật?"')
            check('Xóa thật?' in await text_of(b.page, '.ch-actbar [data-ch-act=hide]'), 'asks before deleting')
            await b.shot(shots, '03-delete-confirm')
            await b.page.tap('.ch-actbar [data-ch-act=hide]')
            await until(b.page, f'{COUNT}===2', 'B: one message less')
            check('Tối nay' not in await text_of(b.page, '.ch-bub'), 'the deleted message left B\'s screen')
            await b.shot(shots, '04-deleted-for-me')
            await a.page.wait_for_timeout(500)
            check(await a.page.evaluate(f'{COUNT}===3'), 'A still has all three')

            # ---- A takes back their last message ----
            await hold_touch(a, '.ch-msg.mine:last-child .ch-bub')
            await until(a.page, "document.querySelector('.ch-actbar [data-ch-act=del]')", 'A: "Thu hồi" on my own')
            await a.shot(shots, '05-own-long-press')
            await a.page.tap('.ch-actbar [data-ch-act=del]')
            await until(a.page, "document.querySelector('.ch-actbar [data-ch-act=del].warn')", 'A: "Thu hồi thật?"')
            await a.page.tap('.ch-actbar [data-ch-act=del]')
            await until(b.page, "document.querySelector('.ch-bub.del')", 'B: "Tin nhắn đã thu hồi"')
            await b.page.click('.ch-bub.del', button='right')
            await until(b.page, "document.querySelector('.ch-actbar [data-ch-act=hide]')", 'B: right click on the recalled line')
            check(await b.page.evaluate("document.querySelectorAll('.ch-actbar button').length===1"), 'a recalled line: only "Xóa ở phía tôi"')
            await b.shot(shots, '06-recalled-menu')

            # ---- B empties the chat from the list ----
            await b.page.click('[data-ch-act=back]')
            await until(b.page, "document.querySelector('.ch-row[data-ch-act=open]')", 'B: back in Tin nhắn')
            await hold_touch(b, '.ch-row[data-ch-act=open]')
            await until(b.page, "document.querySelector('.ch-selrow input:checked')", 'B: holding a chat ticks it')
            check('Xóa (1)' in await text_of(b.page, '[data-ch-act=clearGo]'), '"Xóa (1)"')
            check(await b.page.evaluate(FITS), 'choosing fits 390 px')
            await b.shot(shots, '07-choose')
            await b.page.tap('[data-ch-act=clearGo]')
            await until(b.page, "document.querySelector('[data-ch-act=clearGo].warn')", 'B: asks again')
            check('Xóa 1 cuộc trò chuyện?' in await text_of(b.page, '[data-ch-act=clearGo]'), '"Xóa 1 cuộc trò chuyện?"')
            await b.shot(shots, '08-choose-confirm')
            await b.page.tap('[data-ch-act=clearGo]')
            await until(b.page, "!document.querySelector('.ch-row[data-ch-act=open]') && !document.querySelector('.ch-selrow')", 'B: the chat left the list')
            await b.shot(shots, '09-list-emptied')
            await a.page.click('[data-ch-act=back]')
            await until(a.page, "document.querySelector('.ch-row[data-ch-act=open]')", 'A: the chat is still in A\'s list')

            # ---- 🚫 B blocks A, then unblocks from "Đã chặn" ----
            await b.page.click('[data-ch-act=tab][data-tab=friends]')
            await b.page.click('.ch-row[data-ch-act=dm]')
            await until(b.page, "document.querySelector('.ch-head [data-ch-act=block]')", 'B: Chặn in the header')
            check(await b.page.evaluate(f'{COUNT}===0'), 'the emptied chat opens empty for B')
            await b.page.click('.ch-head [data-ch-act=block]')
            await b.page.click('.ch-head [data-ch-act=block]')
            await until(b.page, "document.querySelector('.ch-tabs')", 'B: blocked, back to the lists')
            await b.page.click('[data-ch-act=tab][data-tab=inbox]')
            await b.page.click('[data-ch-act=blocks]')
            await until(b.page, "document.querySelector('[data-ch-act=unblock]')", 'B: Đã chặn lists A')
            check('Lan Anh' in await text_of(b.page, '.ch-row'), 'the blocked friend by name')
            check(await b.page.evaluate(FITS), 'Đã chặn fits 390 px')
            await b.shot(shots, '10-blocked-list')
            await b.page.click('[data-ch-act=unblock]')
            await until(b.page, "!document.querySelector('[data-ch-act=unblock]')", 'B: unblocked')
            check('Bạn chưa chặn ai.' in await text_of(b.page, '.ch-empty'), '"Bạn chưa chặn ai."')
            await b.shot(shots, '11-unblocked')
            await b.page.evaluate("document.documentElement.dataset.theme='dem'")
            await b.page.click('[data-ch-act=back]')
            await until(b.page, "document.querySelector('[data-ch-act=blocks]')", 'B: back in Tin nhắn (dark)')
            await b.shot(shots, '12-dark-inbox')
            await browser.close()
    for c in checks:
        print(c)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', default=str(ROOT / '_chatdel_shots'))
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
