#!/usr/bin/env python3
"""🐕 Kéo co chó sủa with a fake microphone (dev tool; needs `pip install playwright websockets` and TEST_DATABASE_URL).

Starts a game server and the live service with LIVE_DOG_BARK=1 (LIVE_TRUST_PROXY=1: each phone sends its own
X-Real-IP, as nginx would). Each phone is its own Chromium whose microphone is a generated WAV
(--use-file-for-fake-audio-capture): a quiet room, with or without shouts over it.

  * the header: Permissions-Policy microphone=(self);
  * Lan (shouting) and Hoa (silent room) register, give a birth year, open 🐕 Kéo co chó sủa and stake (different
    stakes, so they wait for the house dog): the page calibrates the floor, the match starts after the wait against
    "🐕 Chó nhà Mây · <name>" (owner 10/10: the rope moves only on barks);
  * Lan wins by shouting, Hoa loses slowly (28 s or more) to the barking dog; no match under 15 s;
  * the pot is paid once; the live log has one telemetry line per match (numbers only).
Shots at 390×844 (--shots DIR).

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

# The words a player sees in the open sheet (the ui-kit.js wordBudget way: text on screen, not inside a closed <details>)
WORDS = r"""() => {const d=document.querySelector('.db-sheet[open]');if(!d)return 0;let n=0;
  const w=document.createTreeWalker(d,NodeFilter.SHOW_TEXT);let t;
  while((t=w.nextNode())){const el=t.parentElement;if(!el||el.closest('details:not([open])>:not(summary)'))continue;
    const r=el.getBoundingClientRect(),cs=getComputedStyle(el);if(!r.width||!r.height||cs.visibility==='hidden'||r.bottom<0||r.top>innerHeight)continue;
    n+=t.textContent.split(/\s+/).filter(x=>/[\p{L}\p{N}]/u.test(x)).length;}
  return n;}"""
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


def wav(path: str, bark: bool, seconds: int = 90) -> str:
    """A fake microphone (Chromium reads it as the capture device, looping): a quiet room (white noise at about −62 dBFS)
    and, when `bark`, barks over it (syllables of varying loudness up to about −9 dBFS, 0.8 s on, 0.25 s off: shouting hard
    and often)."""
    import random
    import struct
    import wave
    rate, rng = 48000, random.Random(7)
    frames = bytearray()
    for i in range(rate * seconds):
        t = i / rate
        x = rng.gauss(0, 0.0008)
        if bark and t % 1.05 < 0.8:   # "gâu gâu": syllables of 0.16 s, each its own loudness, a dip between them
            k = int(t / 0.16)
            env = (0.25 + 0.75 * random.Random(k).random()) * (0.35 + 0.65 * abs(__import__('math').sin(3.1416 * (t % 0.16) / 0.16)))
            x += rng.gauss(0, 0.35 * env)
        frames += struct.pack('<h', max(-32767, min(32767, int(x * 32767))))
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path


async def run(shots: Path | None) -> list:
    from playwright.async_api import async_playwright
    problems: list = []

    async def shot(page, name):
        await page.wait_for_timeout(500)
        n = await page.evaluate(WORDS)
        print(f'{name}: {n} visible words in the sheet', flush=True)
        check(n <= 30, f'{name} within 30 words ({n})')
        if shots:
            await page.screenshot(path=str(shots / f'{name}.png'))

    def check(cond, what):
        print(('PASS ' if cond else 'FAIL ') + what, flush=True)
        if not cond:
            problems.append(what)

    async def match(pw, base, tmp, name, user, ip, stake, loud):
        """One phone (its own Chromium: its own fake mic file) against the house dog. Returns (page, browser, result)."""
        browser = await pw.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
                                                 f'--use-file-for-fake-audio-capture={wav(os.path.join(tmp, user + ".wav"), loud)}',
                                                 '--autoplay-policy=no-user-gesture-required'])
        _, page = await phone(browser, base, name, user, ip, problems)
        await page.evaluate(OPEN)
        await page.wait_for_selector('.db-sheet[open] [data-db=find]', timeout=10000)
        await page.click(f'[data-db=stake][data-v="{stake}"]')
        await page.click('[data-db=find]')
        await page.wait_for_selector('.db-waiting', timeout=15000)
        await page.wait_for_selector('.db-match', timeout=45000)
        tag = await page.evaluate("document.querySelector('.db-tag')?.innerText||''")
        check('Chó nhà Mây' in tag, f'{name}: house dog labelled ({tag!r})')
        await page.wait_for_timeout(9000)
        await shot(page, f'{"01" if loud else "03"}-{"shout" if loud else "silent"}-match-390')
        await page.wait_for_selector('.db-result', timeout=60000)
        await shot(page, f'{"02" if loud else "04"}-{"shout" if loud else "silent"}-result-390')
        res = await page.evaluate("document.querySelector('.db-result')?.className||''")
        return page, browser, res

    with tempfile.TemporaryDirectory() as tmp, servers(tmp) as (base, db):
        import urllib.request
        h = urllib.request.urlopen(base + '/').headers
        check('microphone=(self)' in (h.get('Permissions-Policy') or ''), 'Permissions-Policy microphone=(self)')
        async with async_playwright() as pw:
            (lp, lb, lres), (hp, hb, hres) = await asyncio.gather(
                match(pw, base, tmp, 'Lan', 'lan_bark', '10.1.0.1', 200, True),
                match(pw, base, tmp, 'Hoa', 'hoa_bark', '10.1.0.2', 100, False))
            check('win' in lres, f'Lan shouting beats the house dog ({lres})')
            check('lose' in hres, f'Hoa silent loses to the barking dog ({hres})')
            with test_connect(db) as con:
                rows = con.execute("SELECT stake, result, pay, ended-started FROM bark_tickets WHERE status='done' ORDER BY stake").fetchall()
            print('tickets:', rows)
            check(all(r[3] >= 15 for r in rows), 'no match under 15 s')
            silent = [r for r in rows if r[0] == 100]
            check(bool(silent) and silent[0][3] >= 28, f'the silent player loses slowly ({silent})')
            await lp.wait_for_timeout(1500)
            with test_connect(db) as con:
                fx = con.execute("SELECT status, COUNT(*) FROM live_effects WHERE kind='bark' GROUP BY status").fetchall()
            check(fx == [('applied', 1)], f'the pot paid once: {fx}')
            for b in (lb, hb):
                await b.close()
        lines = [x.strip() for x in open(os.path.join(tmp, 'live.log'), encoding='utf-8') if 'bark match' in x]
        for x in lines:
            print('telemetry:', x)
        check(len(lines) == 2 and all('floor=' in x and 'barks=' in x for x in lines), 'one telemetry line per match')
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
