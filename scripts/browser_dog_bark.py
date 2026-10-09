#!/usr/bin/env python3
"""🐕 Kéo co chó sủa in three phones (dev tool; needs `pip install playwright websockets` and TEST_DATABASE_URL).

Starts a game server and the live service with LIVE_DOG_BARK=1 (LIVE_TRUST_PROXY=1: each phone sends its own
X-Real-IP, as nginx would). Chromium runs with a fake microphone (a beep) and the fake permission prompt.

  * the header: Permissions-Policy microphone=(self);
  * Lan and Minh (two IPs) register, give a birth year, open 🐕 Kéo co chó sủa from Khu phố and stake 200 xu each:
    they are matched, the rope moves on the beep's loudness, the match ends (win / lose / draw) and the pot is paid once;
  * Hoa is alone: after the wait the house dog takes the match, shown as "🐕 Chó nhà Mây · <name>" (no player card);
  * a second phone on Lan's IP never meets Lan.
Shots at 390×844 and 360×780 (--shots DIR).

  python scripts/browser_dog_bark.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT))
from browser_live_chat import API, PW, free_port, wait_http  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for  # noqa: E402

OPEN = """() => {const b=document.createElement('button');b.dataset.action='liveBark';b.hidden=true;document.body.append(b);b.click();b.remove();}"""


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.db')
    env = test_env(QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live', LIVE_DOG_BARK='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    py = os.environ.get('MNL_PY') or sys.executable
    game = subprocess.Popen([py, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                            stderr=open(os.path.join(tmp, 'game.log'), 'w'))
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_TRUST_PROXY='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}',
                LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([py, '-m', 'live', '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


async def phone(browser, base, name, user, ip, problems, size=(390, 844)):
    ctx = await browser.new_context(viewport=dict(width=size[0], height=size[1]), has_touch=True, is_mobile=True, device_scale_factor=2,
                                    extra_http_headers={'X-Real-IP': ip})
    await ctx.grant_permissions(['microphone'])
    page = await ctx.new_page()
    page.on('console', lambda m: m.type == 'error' and problems.append(f'{name} console: {m.text[:200]}'))
    page.on('pageerror', lambda e: problems.append(f'{name} exception: {str(e)[:200]}'))
    await page.goto(base + '/')
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.click('[data-action=jrGender][data-gender=female]', timeout=10000)
    await page.fill('#jr-name', name)
    await page.click('form[data-jr-form=start] button[type=submit]')
    await page.wait_for_timeout(2000)
    for _ in range(8):
        if not await page.evaluate("!!document.querySelector('#sheet[open],#confirmDialog[open]')"):
            break
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(400)
    out = await page.evaluate(API, ['/api/account/register', dict(username=user, password=PW, confirm=PW, display=name)])
    assert out['status'] < 400, out
    out = await page.evaluate(API, ['/api/karaoke/birth', dict(year=2000)])
    assert out['status'] < 400, out
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_function("() => import('/js/v4/live.js').then(m => m.live.welcomed && m.live.flags.bark)", timeout=20000)
    for _ in range(6):
        if not await page.evaluate("!!document.querySelector('#sheet[open],#confirmDialog[open],dialog.whatsnew[open]')"):
            break
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(300)
    return ctx, page


async def run(shots: Path | None) -> list:
    from playwright.async_api import async_playwright
    problems: list = []

    async def shot(page, name):
        if shots:
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(shots / f'{name}.png'))

    def check(cond, what):
        print(('PASS ' if cond else 'FAIL ') + what, flush=True)
        if not cond:
            problems.append(what)

    with tempfile.TemporaryDirectory() as tmp, servers(tmp, ) as (base, db):
        import urllib.request
        h = urllib.request.urlopen(base + '/').headers
        check('microphone=(self)' in (h.get('Permissions-Policy') or ''), 'Permissions-Policy microphone=(self)')
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
                                                     '--autoplay-policy=no-user-gesture-required'])
            (_, lan), (_, minh) = await asyncio.gather(phone(browser, base, 'Lan', 'lan_bark', '10.1.0.1', problems),
                                                       phone(browser, base, 'Minh', 'minh_bark', '10.1.0.2', problems))
            for p in (lan, minh):
                await p.evaluate(OPEN)
                await p.wait_for_selector('.db-sheet[open] [data-db=find]', timeout=10000)
            await shot(lan, '01-lobby-390')
            words = await lan.evaluate("[...document.querySelectorAll('.db-sheet[open] .db-body')].map(e=>e.innerText).join(' ').split(/\\s+/).filter(Boolean).length")
            print('lobby words (body, incl. stake numbers):', words)
            await lan.click('[data-db=stake][data-v="200"]')
            await lan.click('[data-db=find]')
            await lan.wait_for_selector('.db-waiting', timeout=10000)
            await shot(lan, '02-waiting-390')
            await minh.click('[data-db=stake][data-v="200"]')
            await minh.click('[data-db=find]')
            await lan.wait_for_selector('.db-match', timeout=10000)
            await minh.wait_for_selector('.db-match', timeout=10000)
            check(True, 'Lan and Minh matched (two IPs)')
            await lan.wait_for_timeout(5000)
            await shot(lan, '03-match-pvp-390')
            await lan.wait_for_selector('.db-result', timeout=60000)
            await minh.wait_for_selector('.db-result', timeout=10000)
            await shot(lan, '04-result-390')
            rows = []
            with test_connect(db) as con:
                rows = con.execute("SELECT result, pay, stake FROM bark_tickets WHERE status='done' ORDER BY result").fetchall()
            check(len(rows) == 2 and sum(r[1] for r in rows) == 400, f'settled once, pot paid: {rows}')
            await lan.wait_for_timeout(1500)
            with test_connect(db) as con:
                fx = con.execute("SELECT status, COUNT(*) FROM live_effects WHERE kind='bark' GROUP BY status").fetchall()
            check(all(s == 'applied' for s, _ in fx), f'payout rows applied: {fx}')

            # Hoa is alone: the house dog after the wait (360×780)
            _, hoa = await phone(browser, base, 'Hoa', 'hoa_bark', '10.1.0.3', problems, size=(360, 780))
            await hoa.evaluate(OPEN)
            await hoa.wait_for_selector('.db-sheet[open] [data-db=find]', timeout=10000)
            await shot(hoa, '05-lobby-360')
            await hoa.click('[data-db=stake][data-v="100"]')
            await hoa.click('[data-db=find]')
            await hoa.wait_for_selector('.db-match', timeout=40000)
            tag = await hoa.evaluate("document.querySelector('.db-tag')?.innerText||''")
            check('Chó nhà Mây' in tag, f'house dog labelled: {tag!r}')
            await hoa.wait_for_timeout(5000)
            await shot(hoa, '06-match-dog-360')
            await hoa.wait_for_selector('.db-result', timeout=60000)
            await shot(hoa, '07-result-dog-360')
            await browser.close()
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path)
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(a.shots))
    for p in problems:
        print('PROBLEM', p)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
