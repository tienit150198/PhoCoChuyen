#!/usr/bin/env python3
"""🔔 Notifications per chat and 💕 shorter waits at Góc hẹn hò in real browsers (dev tool, needs `pip install playwright
websockets` + chromium).

Starts a game server and the live service (chat and dates on, LIVE_DATE_SPEED=40 so the neighbour comes after 3 s)
on one SQLite database. MNL_PY picks the servers' Python (the live service needs websockets), MNL_PYTHONPATH their
library path. Two phones (390×844, touch), friends:
  * An makes a group with Bình, taps 🔔 in its header, picks "🔕 Tắt": the bell turns 🔕; Bình writes in the group:
    An's list shows the chat quiet (🔕, a grey count), the chat button's badge leaves it out; "🔔 Bật" again counts it;
  * An sits on the dating bench: "Chỉ có bạn đang chờ", the 📣 button; Bình is on Cả phố; An taps "📣 Rủ mọi người":
    Bình sees "An đang chờ ở góc hẹn hò" with "Ghé góc hẹn hò", which opens Góc hẹn hò ("1 người đang chờ");
    the button on An's phone now counts down; after a while alone a neighbour (NPC) sits down: lines, a quick quiz.
Fails on console errors, page errors or HTTP 5xx. Screenshots into --shots (light and dark).

  MNL_PY=python3.12 python scripts/browser_live_notify_bench.py [--shots DIR]
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
from browser_live_pin import until  # noqa: E402


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.sqlite3')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    py = os.environ.get('MNL_PY') or sys.executable
    if os.environ.get('MNL_PYTHONPATH'):
        env['PYTHONPATH'] = os.environ['MNL_PYTHONPATH']
    game = subprocess.Popen([py, 'server.py', '--port', str(gp), '--db', db], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, LIVE_CHAT='1', LIVE_DATING='1', LIVE_DATE_SPEED='40', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([py, '-m', 'live', '--db', db], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-bell-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'An', problems)
            b = await phone(browser, base, 'Bình', problems)
            await a.api('/api/account/register', dict(username='an_test', password=PW, confirm=PW, display='An'))
            await b.api('/api/account/register', dict(username='binh_test', password=PW, confirm=PW, display='Bình'))
            with sqlite3.connect(db) as con:
                sa, sb = (con.execute('SELECT sid FROM accounts WHERE username=?', (u,)).fetchone()[0] for u in ('an_test', 'binh_test'))
                con.execute("UPDATE stat_births SET day='2026-01-01' WHERE sid IN (?, ?)", (sa, sb))
                for x, y in ((sa, sb), (sb, sa)):
                    con.execute('INSERT INTO friends(sid, friend, since) VALUES(?, ?, ?)', (x, y, time.time()))
            for p in (a, b):
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
                await p.page.click('.live-fab')
                await p.page.wait_for_selector('.chat-sheet[open] .ch-tabs')

            # ---- 🔔 a group, turned off ----
            await a.page.click('[data-ch-act=tab][data-tab=inbox]')
            await a.page.click('.ch-new')
            await a.page.fill('[data-ch-field=gtitle]', 'Hội chợ đêm')
            await a.page.check('.ch-pick input')
            await a.page.click('[data-ch-act=groupMake]')
            await until(a.page, "document.querySelector('.ch-bell')", 'A: the group opens with a bell')
            check('🔔' in await text_of(a.page, '.ch-bell'), 'bell on by default')
            await a.page.click('.ch-bell')
            await until(a.page, "document.querySelector('.ch-notify')", 'A: notification choices')
            await a.shot(shots, '01-group-bell-menu')
            await a.page.click('.ch-notify [data-v=off]')
            await until(a.page, "document.querySelector('.ch-bell.off')", 'A: bell off')
            flash = await text_of(a.page, '.ch-flash')
            check('tắt thông báo' in flash.lower(), f'flash after turning off ({flash!r})')
            await a.page.click('[data-ch-act=back]')
            await until(a.page, "document.querySelector('.ch-row.quiet')", 'A: the quiet row')
            # Bình writes in the group (from the group in his list)
            await b.page.click('[data-ch-act=tab][data-tab=inbox]')
            await until(b.page, "document.querySelector('.ch-row[data-ch^=\"g:\"]')", 'B: the group in his list')
            await b.page.click('.ch-row[data-ch^="g:"]')
            await until(b.page, "document.querySelector('.chat-sheet .ch-compose:not([hidden])')", 'B: can write')
            await send(b, 'Tối nay 8 giờ gặp ở cổng chợ nha!')
            await until(a.page, "document.querySelector('.ch-row.quiet .badge.mute')", 'A: a grey count on the quiet row')
            tab_badge = await a.page.evaluate("document.querySelector('[data-tab=inbox] .badge')?.textContent||''")
            check(tab_badge == '', f'a quiet chat is left out of the badges ({tab_badge!r})')
            check('🔕' in await text_of(a.page, '.ch-row.quiet .ch-meta'), '🔕 on the row')
            mute = await a.page.evaluate("""(() => { const b = document.querySelector('.ch-row.quiet .badge.mute'), s = b && getComputedStyle(b);
              return b && {text: b.textContent, w: b.getBoundingClientRect().width, bg: s.backgroundColor, color: s.color, display: s.display}; })()""")
            check(bool(mute) and mute['text'] == '1' and mute['w'] > 0, f'the grey count on the quiet row ({mute})')
            await a.shot(shots, '02-inbox-quiet-row')
            after = await a.page.evaluate("""(() => { const m = document.querySelector('.ch-row.quiet .ch-meta');
              return m && m.outerHTML + JSON.stringify([...m.children, m.parentElement].map(e => { const r = e.getBoundingClientRect(); return [r.top, r.bottom, getComputedStyle(e).visibility, getComputedStyle(e).opacity]; })); })()""")
            check('badge mute' in (after or ''), f'the grey count is still there after a moment ({after})')
            await a.page.click('.ch-row.quiet')
            await a.page.click('.ch-bell')
            await a.page.click('.ch-notify [data-v=on]')
            await until(a.page, "document.querySelector('.ch-bell:not(.off)')", 'A: bell on again')
            await a.page.click('[data-ch-act=back]')
            check(await a.page.evaluate("!document.querySelector('.ch-row.quiet')"), 'on again: not quiet')

            # ---- 💕 the bench ----
            await b.page.click('[data-ch-act=back]')
            await b.page.click('[data-ch-act=tab][data-tab=town]')   # Bình reads Cả phố
            await until(b.page, "document.querySelector('.ch-here,.ch-empty')", 'B: on Cả phố')
            await a.page.click('[data-ch-act=date]')
            await a.page.wait_for_selector('.dt-sheet[open] [data-dt=sit]', timeout=15000)
            await a.page.click('[data-dt=sit]')
            await until(a.page, "document.querySelector('.dt-call')", 'A: waiting, the 📣 button')
            who = await text_of(a.page, '.dt-who-n')
            check('Chỉ có bạn đang chờ' in who, f'who waits ({who!r})')
            await a.page.click('.dt-call')
            await until(a.page, "document.querySelector('.dt-call[disabled]')", 'A: 📣 counts down')
            check('Rủ lại sau' in await text_of(a.page, '.dt-call'), 'the button says when again')
            await until(b.page, "document.querySelector('.ch-sys')", 'B: the invitation on Cả phố')
            line = await text_of(b.page, '.ch-sys')
            check('An' in line and 'góc hẹn hò' in line, f'the line on Cả phố ({line!r})')
            await b.shot(shots, '03-town-invitation')
            await until(a.page, "document.querySelector('.dt-npc')", 'A: a neighbour sits down', timeout=15)
            check('NPC' in await text_of(a.page, '.dt-npc-head'), 'the neighbour is marked NPC')
            await a.page.click('[data-dt=npcAsk]')
            await a.page.click('.dt-npc-opts .dt-chip')
            await until(a.page, "document.querySelector('.dt-npc-res')", 'A: the quiz answer')
            await a.shot(shots, '04-bench-npc-quiz')
            box = await a.page.evaluate("(() => [document.documentElement.scrollWidth, document.querySelector('.dt-npc').getBoundingClientRect().right])()")
            check(box[0] <= 390 and box[1] <= 390, f'fits 390 px ({box})')
            await b.page.click('.ch-sys-go')
            await b.page.wait_for_selector('.dt-sheet[open]', timeout=15000)
            await until(b.page, "document.querySelector('.dt-who-n')?.innerText.includes('1 người đang chờ')", 'B: Góc hẹn hò, 1 waiting')
            await b.shot(shots, '05-guest-opens-bench')
            for p in (a, b):
                await p.page.evaluate("document.documentElement.dataset.theme='dem'")
            await a.shot(shots, '06-bench-npc-dark')
            await b.shot(shots, '07-bench-idle-dark')
            await browser.close()
    for c in checks:
        print(c)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', default=str(ROOT / '_mute_date_shots'))
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
