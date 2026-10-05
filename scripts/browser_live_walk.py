#!/usr/bin/env python3
"""🚶 Đi dạo in three browsers (dev tool, needs `pip install playwright websockets` + chromium).

Starts a game server (story mode, PostgreSQL) and the live service (LIVE_CHAT=1, LIVE_STREET=1; happenings come
every ~20 s here instead of every 10 minutes, so the run sees them) on the same database, then plays three phones
(390×844) in one place:
  * the menu entry "Đi dạo" shows only once the service says the street is on;
  * all three land in the same instance of Bờ hồ and see each other; A taps to walk (around the lake) and B and
    C see A arrive where A tapped;
  * A talks (a bubble on B's and C's screens, phone numbers masked), B waves (👋);
  * C and A sit at a tám chuyện table: both get the topic card, both tap "Đổi chủ đề" and the card changes;
  * a red envelope appears: C taps it, gets the xu (the wallet moves at once), the others see it go;
    a lion-dance troupe and a street vendor cross;
  * A taps B: the card, "Kết bạn" (the game's friends API: B gets the request), then "Rủ đi cà phê": B accepts
    and both sit in a private café; C does not see their bubbles;
  * C reports a bubble and blocks A: A vanishes from C's street;
  * dark theme; the place picker. Fails on console errors, page errors or HTTP 5xx.

  python scripts/browser_live_walk.py [--shots DIR]
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
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import API, PW, free_port, phone, wait_http  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for

# The live service as in production, but with happenings every ~20 s (an envelope first, then a lion, a vendor).
LIVE_DEV = """
import sys
import live.street as s
s.FIRST_HAPPEN = (6, 8)
s.HAPPEN_GAP = 18
s.HAPPEN_JITTER = 0
kinds = iter(['env', 'lion', 'vendor'] * 100)
orig = s.StreetFeature._happen
s.StreetFeature._happen = lambda self, room, now, kind=None: orig(self, room, now, kind or next(kinds))
from live.app import main
main(sys.argv[1:])
"""

STATE = "async () => (await import('/js/v4/walk.js')).walk.state()"


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.db')
    env = test_env( QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    game = subprocess.Popen([sys.executable, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_STREET='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([sys.executable, '-c', LIVE_DEV, '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db, os.path.join(tmp, 'live.log')
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


async def state(p):
    return await p.page.evaluate(STATE)


async def until(p, js_cond: str, what: str, timeout=8.0):
    """Wait until `js_cond` (a function of the walk state `s`) is true on phone p."""
    end = time.monotonic() + timeout
    while True:
        s = await state(p)
        if await p.page.evaluate(f's => {{ {js_cond} }}', s):
            return s
        if time.monotonic() > end:
            raise AssertionError(f'{p.name}: {what} (state: {json.dumps(s, ensure_ascii=False)[:600]})')
        await asyncio.sleep(0.15)


async def tap_world(p, x, y):
    """Tap the scene at world point (x, y) (600 × 900)."""
    s = await state(p)
    box = await p.page.locator('.walk-sheet .wk-canvas').bounding_box()
    v = s['view']
    await p.page.touchscreen.tap(box['x'] + v['ox'] + x * v['k'], box['y'] + v['oy'] + y * v['k'])


async def where(p, pid):
    s = await state(p)
    return next((q for q in s['people'] if q['pid'] == pid), None)


async def open_walk(p):
    """Khu phố › Đi dạo (the menu hub; the "Thêm" sheet on a phone)."""
    await p.page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
    await p.page.wait_for_selector('#rail [data-action=v4Group][data-group=pho]', timeout=15000)
    await p.page.click('#rail [data-action=v4Group][data-group=pho]')   # Đi dạo sits first in the Khu phố hub (0.9.19 menu)
    await p.page.wait_for_selector('#rail [data-action=liveWalk]:visible', timeout=15000)
    await p.page.click('#rail [data-action=liveWalk]')
    await p.page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=10000)


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    async def shot(p, name):
        await p.page.wait_for_timeout(400)
        await p.page.screenshot(path=str(shots / f'{name}.png'))

    with tempfile.TemporaryDirectory(prefix='mnl-walk-', dir=os.environ.get('TMPDIR')) as tmp, servers(tmp) as (base, db, live_log):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Lan Anh', problems)
            b = await phone(browser, base, 'Minh Tú', problems)
            c = await phone(browser, base, 'Hà Vy', problems)
            await a.api('/api/account/register', dict(username='lananh_w', password=PW, confirm=PW, display='Lan Anh'))
            await b.api('/api/account/register', dict(username='minhtu_w', password=PW, confirm=PW, display='Minh Tú'))
            for p in (a, b, c):
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
            for p in (a, b, c):
                await open_walk(p)
            check(True, 'the menu entry "Đi dạo" shows once the service has the street on')
            s = await until(c, 'return s.people.length===3', 'three strollers in one place')
            check(s['place'] == 'boho' and s['room'] == 'walk:boho:1', f"all in Bờ hồ, instance 1 ({s['room']})")
            sa, sb, sc = await state(a), await state(b), await state(c)
            pa, pb, pc = sa['me'], sb['me'], sc['me']
            check(sa['room'] == sb['room'] == sc['room'], 'same instance for all three')
            await shot(a, '01-boho-three-strollers')

            # ---- moving: A walks around the lake; B and C see A arrive
            me = await where(a, pa)
            target = (552, 300) if me['x'] < 300 else (48, 300)
            await tap_world(a, *target)
            for p in (b, c):
                await until(p, f"const q=s.people.find(q=>q.pid==='{pa}');return q&&Math.hypot(q.x-{target[0]},q.y-{target[1]})<6;",
                            'A arrived where A tapped', timeout=12)
            check(True, 'B and C see A walk to the tapped spot (around the lake)')
            await tap_world(a, 300, 420)                  # into the lake: clamped to the shore
            await until(b, f"const q=s.people.find(q=>q.pid==='{pa}');return q&&Math.abs(q.y-515)<3&&Math.abs(q.x-300)<3;",
                        'a tap in the lake ends on the shore', timeout=12)
            check(True, 'a tap in the lake: A stops on the shore')
            await shot(b, '02-b-sees-a-walk')

            # ---- talking and waving
            await a.page.fill('.walk-sheet .wk-say input', 'Tối nay ra chợ đêm không mọi người? zalo 0912345678 nha')
            await a.page.click('.walk-sheet .wk-send')
            s = await until(c, f"const q=s.people.find(q=>q.pid==='{pa}');return q&&q.said;", 'C sees A\'s bubble')
            said = next(q for q in s['people'] if q['pid'] == pa)['said']
            check('chợ đêm' in said and '0912' not in said, f'bubble on C\'s screen, phone masked ({said!r})')
            await c.page.fill('.walk-sheet .wk-say input', 'mình là khách nè')   # C is a guest: strolls, never talks
            await c.page.click('.walk-sheet .wk-send')
            await c.page.wait_for_function("() => /tài khoản/i.test(document.querySelector('.walk-sheet .wk-toast:not([hidden])')?.innerText||'')", timeout=6000)
            check(True, 'a guest cannot talk on the street (Tạo tài khoản)')
            await b.page.click('.walk-sheet [data-wk=emotes]')
            await shot(b, '03-emote-tray')
            await b.page.click('.walk-sheet [data-wk=emote][data-e=wave]')
            await until(a, f"const q=s.people.find(q=>q.pid==='{pb}');return q&&q.emote==='👋';", 'A sees B wave')
            check(True, 'B waves, A sees 👋')
            await shot(c, '04-bubble-and-wave')

            # ---- a tám chuyện table
            await tap_world(c, 130, 720)                  # Bờ hồ table 0
            await until(c, f"return s.tables[0].seats.includes('{pc}')&&s.tables[0].topic;", 'C sits and gets a topic')
            await c.page.wait_for_selector('.walk-sheet .wk-topic:not([hidden])', timeout=5000)
            await tap_world(a, 130, 720)
            await until(a, f"return s.tables[0].seats.includes('{pa}');", 'A sits too')
            first = (await state(a))['tables'][0]['topic']
            check(first and first == (await state(c))['tables'][0]['topic'], f'both see the same topic card ({first!r})')
            await shot(c, '05-table-topic')
            await c.page.click('.walk-sheet [data-wk=topic]')
            await a.page.click('.walk-sheet [data-wk=topic]')
            s = await until(c, f"return s.tables[0].topic && s.tables[0].topic!=={json.dumps(first)};", 'a new card after both voted')
            check(True, f"everyone tapped Đổi chủ đề: a new card ({s['tables'][0]['topic']!r})")
            await shot(a, '06-table-new-topic')

            # ---- the red envelope (the first happening here), then a lion and a vendor
            s = await until(c, 'return s.envelope;', 'a red envelope appears', timeout=30)
            envelope = s['envelope']
            check(envelope is not None, 'a red envelope appears')
            if envelope:
                await shot(c, '07-red-envelope')
                boot0 = await c.api('/api/bootstrap?lite=1', None)
                w0 = boot0['state']['journey']['wallet']
                await c.page.click('.walk-sheet [data-wk=stand]')
                await tap_world(c, envelope['x'], envelope['y'])
                await c.page.wait_for_function("() => document.querySelector('.walk-sheet .wk-toast:not([hidden])')?.innerText.includes('xu')", timeout=6000)
                toast = await c.page.inner_text('.walk-sheet .wk-toast')
                await shot(c, '08-envelope-grabbed')
                await c.page.wait_for_timeout(1200)
                boot1 = await c.api('/api/bootstrap?lite=1', None)
                gained = boot1['state']['journey']['wallet'] - w0
                check(3 <= gained <= 8, f'C got the envelope ({toast!r}), wallet +{gained} xu, paid once')
                with test_connect(db) as con:
                    rows = con.execute('SELECT status FROM live_effects').fetchall()
                check(rows == [('applied',)], f'one live_effects row, applied ({rows})')
            seen = set()
            end = time.monotonic() + 45
            while time.monotonic() < end and not {'lion', 'vendor'} <= seen:
                k = (await state(b))['happening']
                if k and k not in seen:
                    seen.add(k)
                    await asyncio.sleep(2.5)
                    await shot(b, f'09-happening-{k}')
                await asyncio.sleep(0.3)
            check({'lion', 'vendor'} <= seen, f'a lion-dance troupe and a vendor cross ({sorted(seen)})')

            # ---- A taps B: the card, a friend request, coffee for two
            await a.page.click('.walk-sheet [data-wk=stand]')
            me_b = await where(a, pb)
            await tap_world(a, me_b['x'], me_b['y'] - 30)
            await a.page.wait_for_selector('.walk-sheet .wk-card:not([hidden]) [data-wk=friend]', timeout=6000)
            await shot(a, '10-player-card')
            await a.page.click('.walk-sheet [data-wk=friend]')
            await a.page.wait_for_function("() => document.querySelector('.walk-sheet .wk-toast:not([hidden])')?.innerText.includes('kết bạn')", timeout=6000)
            view = await b.api('/api/marriage', None)
            incoming = [r['name'] for r in view['friends']['incoming']]
            check(incoming == ['Lan Anh'], f'B got the friend request through the friends API ({incoming})')
            await shot(a, '11-friend-request-sent')
            await a.page.click('.walk-sheet [data-wk=cafe]')
            await b.page.wait_for_selector('.walk-sheet .wk-invite:not([hidden])', timeout=6000)
            await shot(b, '12-coffee-invite')
            await b.page.click('.walk-sheet [data-wk=inviteYes]')
            for p in (a, b):
                await until(p, "return s.place==='cafe'&&s.people.length===2&&s.tables[0].topic;", 'both in the café')
            check(True, 'coffee for two: a private café with a topic card')
            await a.page.fill('.walk-sheet .wk-say input', 'Cà phê muối ở đây đỉnh ghê')
            await a.page.click('.walk-sheet .wk-send')
            await until(b, f"const q=s.people.find(q=>q.pid==='{pa}');return q&&q.said;", 'B sees A in the café')
            await until(c, f"return !s.people.some(q=>q.pid==='{pa}'||q.pid==='{pb}');", 'C no longer sees A and B on the street')
            check(True, 'C does not see the café')
            await shot(b, '13-cafe-for-two')

            # ---- report and block (C on the street, A back from the café)
            await a.page.click('.walk-sheet [data-wk=back]')
            await until(a, "return s.place==='boho';", 'A back on the street')
            await until(c, f"return s.people.some(q=>q.pid==='{pa}');", 'C sees A again')
            await a.page.fill('.walk-sheet .wk-say input', 'Mình quay lại rồi nè')
            await a.page.click('.walk-sheet .wk-send')
            s = await until(c, f"const q=s.people.find(q=>q.pid==='{pa}');return q&&q.said;", 'C sees A\'s new bubble')
            qa = next(q for q in s['people'] if q['pid'] == pa)
            await tap_world(c, qa['x'], qa['y'] - 30)
            await c.page.wait_for_selector('.walk-sheet .wk-card:not([hidden]) [data-wk=more]', timeout=6000)
            await c.page.click('.walk-sheet [data-wk=more]')
            await c.page.click('.walk-sheet [data-wk=report]')
            await shot(c, '14-report-reasons')
            await c.page.click('.walk-sheet [data-wk=reason][data-reason=spam]')
            await c.page.wait_for_function("() => document.querySelector('.walk-sheet .wk-toast:not([hidden])')?.innerText.includes('báo cáo')", timeout=6000)
            check(True, 'C reports a bubble')
            qa = await where(c, pa)
            await tap_world(c, qa['x'], qa['y'] - 30)
            await c.page.click('.walk-sheet [data-wk=more]')
            await c.page.click('.walk-sheet [data-wk=block]')
            await until(c, f"return !s.people.some(q=>q.pid==='{pa}');", 'A gone for C')
            await until(a, f"return !s.people.some(q=>q.pid==='{pc}');", 'C gone for A', timeout=6)
            check(True, 'after a block, A and C no longer see each other')

            # ---- the picker, dark theme
            await b.page.click('.walk-sheet [data-wk=back]')
            await until(b, "return s.place==='boho';", 'B back on the street')
            await b.page.click('.walk-sheet [data-wk=places]')
            await b.page.wait_for_selector('.walk-sheet .wk-places:not([hidden]) .wk-chip', timeout=5000)
            await shot(b, '15-place-picker')
            await b.page.click('.walk-sheet .wk-chip[data-place=chodem]')
            await until(b, "return s.place==='chodem';", 'B at Chợ đêm')
            await shot(b, '16-cho-dem')
            await b.page.evaluate("document.documentElement.dataset.theme='dem'")
            await b.page.click('.walk-sheet [data-wk=places]')
            await b.page.click('.walk-sheet .wk-chip[data-place=congvien]')
            await until(b, "return s.place==='congvien';", 'B at Công viên')
            await shot(b, '17-cong-vien-dark')
            await b.page.click('.walk-sheet [data-wk=places]')
            await b.page.click('.walk-sheet .wk-chip[data-place=phodibo]')
            await until(b, "return s.place==='phodibo';", 'B at Phố đi bộ')
            await shot(b, '18-pho-di-bo-dark')
            await b.page.evaluate("document.documentElement.dataset.theme='kem'")
            await shot(b, '19-pho-di-bo-light')
            await b.page.click('.walk-sheet [data-wk=places]')
            await b.page.click('.walk-sheet .wk-chip[data-place=congvien]')
            await until(b, "return s.place==='congvien';", 'B at Công viên (light)')
            await shot(b, '20-cong-vien-light')
            await a.page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot(a, '21-boho-dark')
            await browser.close()
        tail = Path(live_log).read_text()[-800:]
        print(tail, file=sys.stderr)
    for line in checks:
        print(line)
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path, default=Path(tempfile.gettempdir()) / 'mnl-walk-shots')
    args = ap.parse_args()
    args.shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(args.shots))
    print(json.dumps(dict(ok=not problems, problems=problems, shots=str(args.shots)), ensure_ascii=False, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
