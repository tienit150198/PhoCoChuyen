#!/usr/bin/env python3
"""💕 A full in-game date in two browsers (dev tool, needs `pip install playwright websockets` + chromium).

Starts a game server (story mode, PostgreSQL) and the live service (LIVE_CHAT=1, LIVE_DATING=1; the date runs
LIVE_DATE_SPEED times faster so the run takes about a minute), then plays phones at 390×844:
  * Lan Anh (Nữ, account) opens "Góc hẹn hò" from the chat's heart, wants a boy, sits; closes the dialog: the 💕
    pill waits on the scene; Minh Tú (Nam, account) opens it from the menu entry, wants a girl, sits;
  * the match opens Lan Anh's dialog by itself; three cards (private picks, revealed together, "Hợp nhau 2/3"),
    "Chọn món cho nhau", a minute of chat (a contact id is masked), both ❤️ → "Đang tìm hiểu 💕", friends,
    +tinh thần paid on the next load, the bond on the chat's friend list and on the Bạn bè card;
  * Bé Na, a guest, sees the bench with "Tạo tài khoản để hẹn hò." and the register button, registers; then
    Lan Anh and Bé Na: Bé Na opens the safety menu and leaves early → Lan Anh gets the gentle line;
  * Lan Anh and Tí Sún: ❤️ / 👋 → both see the same kind line, nobody learns who declined;
  * Đi dạo: the bench of the place glows; a tap opens Góc hẹn hò and sits down (LIVE_STREET=1 too);
  * light and dark screenshots. Fails on console errors, page errors or HTTP 5xx.

  python scripts/browser_live_dating.py [--shots DIR] [--speed 3]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import API, PW, free_port, text_of, wait_http  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for


@contextlib.contextmanager
def servers(tmp: str, speed: float):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.db')
    env = test_env( QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    game = subprocess.Popen([sys.executable, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_STREET='1', LIVE_DATING='1', LIVE_DATE_SPEED=str(speed), LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([sys.executable, '-m', 'live', '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db, os.path.join(tmp, 'live.log')
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


class Phone:
    def __init__(self, ctx, page, name):
        self.ctx, self.page, self.name = ctx, page, name

    async def api(self, path, body=None):
        out = await self.page.evaluate(API, [path, body])
        if out['status'] >= 400:
            raise AssertionError(f'{self.name}: {path} -> {out}')
        return out['data']

    async def shot(self, shots: Path, name: str, wait=300):
        await self.page.wait_for_timeout(wait)
        await self.page.screenshot(path=str(shots / f'{name}.png'))

    async def click(self, sel, timeout=8000):
        await self.page.click(sel, timeout=timeout)

    async def step(self, step, timeout=15000):
        await self.page.wait_for_selector(f'.dt-sheet[open] .dt-body[data-step="{step}"]', timeout=timeout)


async def phone(browser, base, name, gender, problems) -> Phone:
    ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2)
    page = await ctx.new_page()
    page.on('console', lambda m: m.type == 'error' and problems.append(f'{name} console: {m.text[:200]}'))
    page.on('pageerror', lambda e: problems.append(f'{name} exception: {str(e)[:200]}'))
    page.on('response', lambda r: r.status >= 500 and problems.append(f'{name} HTTP {r.status} {r.url}'))
    await page.goto(base + '/')
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.click(f'[data-action=jrGender][data-gender={gender}]', timeout=10000)
    await page.fill('#jr-name', name)
    await page.click('form[data-jr-form=start] button[type=submit]')
    await page.wait_for_timeout(2500)
    for _ in range(8):
        if not await page.evaluate("!!document.querySelector('#sheet[open],#confirmDialog[open]')"):
            break
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(500)
    return Phone(ctx, page, name)


async def ready(p: Phone):
    await p.page.reload()
    await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await p.page.wait_for_selector('.live-fab:not([hidden])', timeout=25000)


async def open_from_chat(p: Phone):
    await p.click('.live-fab')
    await p.page.wait_for_selector('.chat-sheet[open] .ch-date')
    await p.click('.chat-sheet .ch-date')
    await p.page.wait_for_selector('.dt-sheet[open] .dt-bench')


async def menu(p: Phone, action: str, group: str, click=True):
    """Open "Thêm", unfold the hub (`group`: ban = Quan hệ, pho = Khu phố) and tap the entry."""
    await p.page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
    await p.page.wait_for_timeout(500)
    if not await p.page.is_visible(f'#rail [data-action={action}]'):
        await p.click(f'#rail .rail-group[data-group={group}]')
    await p.page.wait_for_selector(f'#rail [data-action={action}]', state='visible', timeout=8000)
    if click:
        await p.click(f'#rail [data-action={action}]')


async def open_from_menu(p: Phone):
    await menu(p, 'liveDate', 'ban')
    await p.page.wait_for_selector('.dt-sheet[open] .dt-bench')


WALK = "async () => (await import('/js/v4/walk.js')).walk.state()"


async def tap_bench(p: Phone):
    """Tap the bench of the place the stroll opened on (world point → canvas)."""
    for _ in range(60):
        s = await p.page.evaluate(WALK)
        at = await p.page.evaluate("async () => (await import('/js/v4/walk.js')).walk.spot('bench')")
        if s['room'] and at:
            break
        await p.page.wait_for_timeout(200)
    box = await p.page.locator('.walk-sheet .wk-canvas').bounding_box()
    v = s['view']
    await p.page.touchscreen.tap(box['x'] + v['ox'] + at['x'] * v['k'], box['y'] + v['oy'] + at['y'] * v['k'])


async def sit(p: Phone, pref: str):
    await p.click(f'.dt-pref[data-v={pref}]')
    await p.click('.dt-go')
    await p.page.wait_for_selector('.dt-bench.wait')


async def cards(a: Phone, b: Phone, shots: Path | None, same=(0, 1, 0)):
    for i in range(3):
        for p in (a, b):
            await p.page.wait_for_selector(f'.dt-step[data-step=card] .dt-kicker:has-text("Câu {i + 1}/3")', timeout=15000)
        await a.click('.dt-opt[data-i="0"]')
        if shots and i == 0:
            await a.shot(shots, '06-card-picked-waiting', wait=150)
            await b.shot(shots, '07-card-other-side', wait=0)
        await b.click(f'.dt-opt[data-i="{same[i]}"]')
        await a.page.wait_for_selector('.dt-verdict', timeout=8000)
        if shots and i == 0:
            await a.shot(shots, '08-card-revealed', wait=0)


async def run(shots: Path, speed: float) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-date-') as tmp, servers(tmp, speed) as (base, db, live_log):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Lan Anh', 'female', problems)
            b = await phone(browser, base, 'Minh Tú', 'male', problems)
            await a.api('/api/account/register', dict(username='lananh_d', password=PW, confirm=PW, display='Lan Anh'))
            await b.api('/api/account/register', dict(username='minhtu_d', password=PW, confirm=PW, display='Minh Tú'))
            with test_connect(db) as con:
                con.execute("UPDATE stat_births SET day='2026-01-01'")
            for p in (a, b):
                await ready(p)

            # ---- the bench: from the chat's heart, and from the menu ----
            await open_from_chat(a)
            await a.shot(shots, '01-bench')
            await sit(a, 'm')
            await a.shot(shots, '02-bench-waiting')
            await a.page.keyboard.press('Escape')
            await a.page.wait_for_selector('.dt-pill:not([hidden])', timeout=5000)
            check('Đang chờ' in await text_of(a.page, '.dt-pill'), 'the 💕 pill waits on the scene while the dialog is closed')
            await a.shot(shots, '03-scene-pill-waiting')
            await menu(b, 'liveDate', 'ban', click=False)
            order = await b.page.evaluate("[...document.querySelectorAll('#rail .rail-sub[data-group=ban] .rail-item[data-action]')].map(e=>e.dataset.action)")
            check(order[:1] == ['liveDate'], f'"Góc hẹn hò" first in Quan hệ ({order})')
            await b.shot(shots, '04-menu-entry')
            await b.click('#rail [data-action=liveDate]')
            await b.page.wait_for_selector('.dt-sheet[open] .dt-bench')
            await sit(b, 'f')

            # ---- matched: A's dialog opens by itself ----
            await a.step('hello', 8000)
            await b.step('hello', 8000)
            check('Minh Tú' in await text_of(a.page, '.dt-head h2'), 'A meets Minh Tú')
            await a.shot(shots, '05-matched-hello', wait=100)
            await cards(a, b, shots)
            await a.step('menu')
            check('Hợp nhau 2/3' in await text_of(a.page, '.dt-who small'), 'Hợp nhau 2/3 in the header')
            await a.shot(shots, '09-menu-want')
            await a.click('.dt-dish >> nth=0')
            await a.shot(shots, '10-menu-give', wait=100)
            await a.click('.dt-dish >> nth=1')
            await b.click('.dt-dish >> nth=1')
            await b.click('.dt-dish >> nth=2')
            await a.page.wait_for_selector('.dt-order', timeout=8000)
            hit = await text_of(a.page, '.dt-order')
            check('Trúng phóc' in hit, f'an order that was right: Trúng phóc ({hit[:80]!r})')
            await a.shot(shots, '11-menu-revealed', wait=0)

            # ---- a minute of chat ----
            await a.step('chat')
            await b.step('chat')
            await a.page.fill('.dt-compose input', 'Chào Minh Tú 😆 zalo minh123 nha')
            await a.click('.dt-send')
            await b.page.wait_for_selector('.dt-msg:not(.mine) .dt-bub', timeout=5000)
            got = await text_of(b.page, '.dt-bub')
            check('•••' in got and 'minh123' not in got, f'date chat goes through the filters ({got!r})')
            await b.click('.dt-quick .dt-chip >> nth=1')
            await a.page.wait_for_function("document.querySelectorAll('.dt-msg:not(.mine)').length>0", timeout=5000)
            await b.page.evaluate("document.documentElement.dataset.theme='dem'")
            await b.shot(shots, '12-chat-dark')
            await a.shot(shots, '13-chat-light')
            await a.click('.dt-done')
            await b.click('.dt-done')

            # ---- the vote, privately ----
            await a.step('vote')
            await b.step('vote')
            await a.shot(shots, '14-vote')
            await a.click('.dt-vote.heart')
            await a.page.wait_for_selector('.dt-vote-wait')
            await b.click('.dt-vote.heart')
            for p in (a, b):
                await p.step('end')
            end = await text_of(a.page, '.dt-end')
            check('Đang tìm hiểu' in end and 'tinh thần' in end and 'bạn bè' in end, f'mutual ❤️: bond, spirit, friends ({end[:90]!r})')
            await a.shot(shots, '15-match-light')
            await b.shot(shots, '16-match-dark')

            # the bond on cards: the chat's friend list and the Bạn bè card
            await a.page.keyboard.press('Escape')
            await a.click('.live-fab')
            await a.click('[data-ch-act=tab][data-tab=friends]')
            await a.page.wait_for_selector('.ch-bond', timeout=8000)
            check(True, '"Đang tìm hiểu 💕" on the chat friend list')
            await a.shot(shots, '17-chat-friends-bond')
            await a.page.keyboard.press('Escape')
            await menu(a, 'friends', 'ban')
            await a.page.wait_for_timeout(1500)
            card = await a.page.evaluate("document.body.innerText")
            check('Đang tìm hiểu 💕' in card, 'the bond on the Bạn bè card')
            await a.shot(shots, '18-friend-card-bond')
            await a.page.keyboard.press('Escape')
            # the spirit lands on the next load, once
            await ready(a)
            with test_connect(db) as con:
                rows = con.execute("SELECT status FROM live_effects").fetchall()
            check(('applied',) in rows, f'+tinh thần applied on load ({rows})')

            # ---- leaving early, gently ----
            c = await phone(browser, base, 'Bé Na', 'male', problems)
            with test_connect(db) as con:
                con.execute("UPDATE stat_births SET day='2026-01-01'")
            await ready(c)
            # a guest sees the bench, but only accounts date (owner, 01/10)
            await open_from_chat(c)
            await c.page.wait_for_selector('.dt-go[data-dt=account]', timeout=5000)
            check('Tạo tài khoản để hẹn hò' in await text_of(c.page, '.dt-bench'), 'a guest: "Tạo tài khoản để hẹn hò." and the register button')
            await c.shot(shots, '19a-guest-bench')
            await c.click('.dt-go[data-dt=account]')
            await c.page.wait_for_timeout(800)
            check(await c.page.evaluate("!document.querySelector('.dt-sheet[open]')"), 'the register button leaves the date corner for the account form')
            await c.page.keyboard.press('Escape')
            await c.api('/api/account/register', dict(username='bena_d', password=PW, confirm=PW, display='Bé Na'))
            await ready(c)
            await open_from_chat(a)
            await sit(a, 'any')
            await open_from_chat(c)
            await sit(c, 'any')
            for p in (a, c):
                await p.step('hello', 8000)
            check('Bé Na' in await text_of(a.page, '.dt-head h2'), 'not Minh Tú again today: a new person')
            await c.click('[data-dt=menu]')
            await c.shot(shots, '19-safety-menu')
            await c.click('[data-dt=leave]')
            await c.click('[data-dt=leave]')
            await a.step('end')
            line = await text_of(a.page, '.dt-end')
            check('phải đi trước' in line, f'left early: the other gets a gentle line ({line[:60]!r})')
            await a.shot(shots, '20-other-left')

            # ---- ❤️ / 👋: the same kind line for both ----
            d = await phone(browser, base, 'Tí Sún', 'male', problems)
            await d.api('/api/account/register', dict(username='tisun_d', password=PW, confirm=PW, display='Tí Sún'))
            with test_connect(db) as con:
                con.execute("UPDATE stat_births SET day='2026-01-01'")
            await ready(d)
            await a.click('[data-dt=again]')
            await open_from_chat(d)
            await sit(d, 'any')
            for p in (a, d):
                await p.step('hello', 10000)
            await cards(a, d, None, same=(0, 0, 1))
            await a.step('menu')
            for p, (w, g) in ((a, (0, 1)), (d, (2, 3))):
                await p.click(f'.dt-dish >> nth={w}')
                await p.click(f'.dt-dish >> nth={g}')
            for p in (a, d):
                await p.step('chat')
                await p.click('.dt-done')
            for p in (a, d):
                await p.step('vote')
            await a.click('.dt-vote.heart')
            await d.click('.dt-vote:not(.heart)')
            for p in (a, d):
                await p.step('end')
            la, ld = await text_of(a.page, '.dt-end .dt-line'), await text_of(d.page, '.dt-end .dt-line')
            check(la == ld and 'chưa hợp' in la, f'one-sided: the same line for both ({la!r} / {ld!r})')
            await d.page.evaluate("document.documentElement.dataset.theme='dem'")
            await a.shot(shots, '21-nope-hearted-side')
            await d.shot(shots, '22-nope-waved-side-dark')

            # ---- Đi dạo: every place's bench is the dating bench ----
            await a.page.keyboard.press('Escape')
            await menu(a, 'liveWalk', 'pho')
            await a.page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=10000)
            await a.page.wait_for_timeout(1500)
            await a.shot(shots, '23-walk-bench')
            await tap_bench(a)
            await a.page.wait_for_selector('.dt-sheet[open] .dt-bench.wait', timeout=8000)
            check(True, 'tapping the bench in Đi dạo opens Góc hẹn hò and sits down')
            await a.shot(shots, '24-walk-bench-sat')
            await browser.close()
        print(Path(live_log).read_text()[-600:], file=sys.stderr)
    for line in checks:
        print(line)
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path, default=Path(tempfile.gettempdir()) / 'mnl-date-shots')
    ap.add_argument('--speed', type=float, default=3.0, help='LIVE_DATE_SPEED: the date runs this many times faster')
    args = ap.parse_args()
    args.shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(args.shots, args.speed))
    print(json.dumps(dict(ok=not problems, problems=problems, shots=str(args.shots)), ensure_ascii=False, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
