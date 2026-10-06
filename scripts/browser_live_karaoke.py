#!/usr/bin/env python3
"""🎤 Phòng hát in two phones (dev tool, needs `pip install playwright websockets` and TEST_DATABASE_URL).

Starts a game server (story mode, PostgreSQL) and the live service with LIVE_KARAOKE=1 on the same database. The
YouTube IFrame API is replaced by a stand-in served at its real URL (https://www.youtube.com/iframe_api, so the page's
CSP is exercised): a player whose clock runs from playVideo() after a random 0.2-0.9 s "buffering", like a phone on
4G; --real uses the real embed instead (needs the network; the game is then served as http://localhost, since YouTube
refuses an embedding page whose Referer is an IP address: error 150, and any embed without a Referer: error 153).
Thumbnails (i.ytimg.com) answer a 1 px image.

  * Lan and Minh (accounts) open Khu phố › Phòng hát and walk into Nhạc trẻ;
  * Lan pastes a YouTube link, Kiểm tra (the oEmbed answer is in the cache already: no network), Xếp hàng (the first song
    of the day is free); both phones start the same video at the same server second, and their video times agree
    within MAX_SKEW (0.25 s) a few seconds in;
  * Minh gives an emoji round (🌧️💔🏠, answer "Nơi này có anh"), Lan types "noi nay co anh": both see the answer and
    "🎉 Lan" with +5 xu;
  * WebKit: a third phone opens the same room: no horizontal scroll, the player at least 200 px high and fully on
    screen, the bottom bar on screen.
Fails on console errors, page errors or HTTP 5xx. At most four JPEG shots (--shots DIR).

  python scripts/browser_live_karaoke.py [--shots DIR] [--real]
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
sys.path.insert(0, str(ROOT))
from browser_live_chat import PW, free_port, phone, wait_http  # noqa: E402
from browser_live_wedding import hub  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for  # noqa: E402

VID = 'dQw4w9WgXcQ'
MAX_SKEW = 0.25
STATE = "async () => (await import('/js/v4/karaoke.js')).karaoke.state()"
PIXEL = bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010806000000'
                      '1f15c4890000000d49444154789c6360f8cfc0f01f0005000201a5d6e7d70000000049454e44ae426082')
FAKE_YT = r"""
(() => {
  const S = {UNSTARTED: -1, ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3, CUED: 5};
  class Player {
    constructor(el, o) {
      const box = typeof el === 'string' ? document.getElementById(el) : el;
      const f = document.createElement('div'); f.className = 'fake-yt'; f.style.cssText = 'position:absolute;inset:0;display:grid;place-items:center;color:#fff;background:#202020;font:600 15px system-ui';
      f.textContent = '▶ YouTube'; window.__ytRef = box.referrerPolicy || ''; window.__ytSrc = box.src || ''; box.replaceWith(f); this.f = f; this.o = o; this.vid = o.videoId || ((box.src || '').match(/embed\/([\w-]{11})/) || [])[1]; this.base = 0; this.t0 = null; this.st = -1; this.dur = 213;
      setTimeout(() => o.events?.onReady?.({target: this}), 120);
    }
    _emit(st) { this.st = st; this.o.events?.onStateChange?.({target: this, data: st}); }
    getPlayerState() { return this.st; }
    getDuration() { return this.dur; }
    getCurrentTime() { return this.t0 == null ? this.base : this.base + (performance.now() - this.t0) / 1000; }
    seekTo(s) { this.base = s; if (this.t0 != null) this.t0 = performance.now(); }
    playVideo() {
      if (this.st === 1 || this.loading) return;
      this.loading = true; this._emit(3);
      setTimeout(() => { this.loading = false; this.t0 = performance.now(); this.f.textContent = '▶ ' + this.vid; this._emit(1); }, 200 + Math.random() * 700);
    }
    pauseVideo() { this.base = this.getCurrentTime(); this.t0 = null; this._emit(2); }
    stopVideo() { this.base = 0; this.t0 = null; this._emit(5); }
    cueVideoById(a) { this.vid = a.videoId || a; this.base = 0; this.t0 = null; this._emit(5); }
    loadVideoById(a) { this.vid = a.videoId || a; this.base = a.startSeconds || 0; this.t0 = null; this.playVideo(); }
    setVolume() {} mute() {} unMute() {}
  }
  window.YT = {Player, PlayerState: S};
  setTimeout(() => window.onYouTubeIframeAPIReady && window.onYouTubeIframeAPIReady(), 0);
})();
"""


@contextlib.contextmanager
def servers(tmp: str, host: str = '127.0.0.1'):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.db')
    env = test_env(QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://{host}:{lp}/live')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    py = os.environ.get('MNL_PY') or sys.executable
    game = subprocess.Popen([py, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_KARAOKE='1', LIVE_ORIGINS=f'http://{host}:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([py, '-m', 'live', '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://{host}:{gp}', db, os.path.join(tmp, 'live.log')
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


def sql(db, q, *args):
    with test_connect(db) as con:
        return con.execute(q, args).fetchall()


async def run(shots: Path | None, real: bool) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []
    nshots = [0]

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        print(checks[-1], flush=True)
        if not cond:
            problems.append('check: ' + what)

    async def shot(p, name):
        if shots is None or nshots[0] >= 4:
            return
        nshots[0] += 1
        await p.page.wait_for_timeout(400)
        await p.page.screenshot(path=str(shots / f'{nshots[0]}-{name}.jpg'), type='jpeg', quality=70)

    async def until(p, js, what, timeout=15.0):
        end = time.monotonic() + timeout
        while True:
            s = await p.page.evaluate(STATE)
            if await p.page.evaluate(f's => ({js})', s):
                return s
            if time.monotonic() > end:
                raise AssertionError(f'{p.name}: {what} (state: {json.dumps(s, ensure_ascii=False)[:400]})')
            await asyncio.sleep(0.15)

    async def mock(ctx):
        if not real:
            await ctx.route('**/iframe_api*', lambda r: r.fulfill(status=200, content_type='text/javascript', body=FAKE_YT))
        await ctx.route('https://i.ytimg.com/**', lambda r: r.fulfill(status=200, content_type='image/png', body=PIXEL))

    async def enter(p):
        await hub(p, 'liveKara')
        await p.page.wait_for_selector('.kr-sheet[open] .kr-room', timeout=15000)
        await p.page.click('.kr-sheet[open] .kr-room[data-id="kara:tre"]')
        await p.page.wait_for_selector('.kr-sheet[open] .kr-bar:not([hidden])', timeout=10000)

    with tempfile.TemporaryDirectory(prefix='mnl-kara-', dir=os.environ.get('TMPDIR')) as tmp, servers(tmp, 'localhost' if real else '127.0.0.1') as (base, db, live_log):   # YouTube refuses an IP as the embedding site (150)
        sql(db, "INSERT INTO kara_songs(vid, title, channel, ok, why, checked_at) VALUES(?, 'Nơi này có anh (Official MV)', 'Sơn Tùng M-TP', 1, '', ?)", VID, time.time())
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'] if real else [])
            lan = await phone(browser, base, 'Lan', problems)
            minh = await phone(browser, base, 'Minh', problems)
            for p, user in ((lan, 'lan_k'), (minh, 'minh_k')):
                await mock(p.ctx)
                await p.api('/api/account/register', dict(username=user, password=PW, confirm=PW, display=p.name))
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.page.wait_for_timeout(1500)
            await enter(lan)
            await enter(minh)
            # Lan: + Thêm bài → paste → Kiểm tra → Xếp hàng
            await lan.page.click('.kr-sheet[open] .kr-main')
            await lan.page.fill('.kr-sheet[open] [data-kr-link]', f'https://youtu.be/{VID}?si=share')
            await lan.page.click('.kr-sheet[open] [data-kr=check]')
            await lan.page.wait_for_selector('.kr-sheet[open] [data-kr=queue]', timeout=10000)
            check('Phát được' in await lan.page.inner_text('.kr-sheet[open] .kr-song'), 'the link is checked (cached oEmbed): "✓ Phát được"')
            await lan.page.click('.kr-sheet[open] [data-kr=queue]')
            sa = await until(lan, 's.stage && s.stage.vid', 'Lan sees her song on stage')
            sb = await until(minh, 's.stage && s.stage.vid', 'Minh sees the song on stage')
            check(sa['stage']['vid'] == sb['stage']['vid'] == VID and sa['stage']['at'] == sb['stage']['at'], 'one song, one shared start (at)')
            if real:
                await asyncio.sleep(4)
                for p in (lan, minh):   # a phone that blocked the sound shows one "▶ Nghe" button: tap it
                    if await p.page.evaluate("document.querySelector('.kr-sheet[open] .kr-main')?.dataset.mode==='play'"):
                        await p.page.click('.kr-sheet[open] .kr-main')
            await until(lan, 's.ps === 1 && s.cur > 1.5', 'Lan plays', 25)
            await until(minh, 's.ps === 1 && s.cur > 1.5', 'Minh plays', 25)
            if not real:
                ref = await lan.page.evaluate('[window.__ytRef, window.__ytSrc]')
                check(ref[0] == 'strict-origin-when-cross-origin' and ref[1].startswith('https://www.youtube-nocookie.com/embed/' + VID), f'the nocookie iframe sends its origin as Referer (YouTube error 153 otherwise): {ref}')
            await asyncio.sleep(2.2)   # the drift control runs every second
            skews = []
            for _ in range(5):
                a = await lan.page.evaluate('async () => { const s = (await import("/js/v4/karaoke.js")).karaoke.state(); return [s.cur, Date.now()]; }')
                b = await minh.page.evaluate('async () => { const s = (await import("/js/v4/karaoke.js")).karaoke.state(); return [s.cur, Date.now()]; }')
                skews.append(abs((a[0] - a[1] / 1000) - (b[0] - b[1] / 1000)))
                await asyncio.sleep(0.4)
            skew = max(skews)
            print(f'video time skew between the phones: max {skew * 1000:.0f} ms over {len(skews)} samples', flush=True)
            check(skew <= MAX_SKEW, f'both phones at the same video second (max skew {skew * 1000:.0f} ms ≤ {MAX_SKEW * 1000:.0f} ms)')
            with test_connect(db) as con:
                row = con.execute("SELECT used, played FROM kara_tickets WHERE kind='queue'").fetchone()
            check(row and row[0] == 1 and row[1], 'the free ticket was redeemed and stamped played')
            await shot(minh, 'room-playing-chromium')
            # Minh: ⋯ → 🧩 Đố bài → Emoji
            await minh.page.click('.kr-sheet[open] [data-kr=more]')
            await minh.page.click('.kr-sheet[open] [data-kr=round]')
            await minh.page.click('.kr-sheet[open] [data-kr=mode][data-m=emoji]')
            await minh.page.fill('.kr-sheet[open] [data-kr-clue]', '🌧️💔🏠')
            await minh.page.fill('.kr-sheet[open] [data-kr-ans]', 'Nơi này có anh')
            await minh.page.click('.kr-sheet[open] [data-kr=start]')
            await until(lan, 's.round && s.round.clue', 'Lan sees the round')
            check('🌧️💔🏠' in await lan.page.inner_text('.kr-sheet[open] .kr-round'), 'the emoji clue shows on the guesser')
            check(await lan.page.evaluate("getComputedStyle(document.querySelector('.kr-sheet[open] .kr-video')).display!=='none'"), 'the YouTube player stays visible during the round')
            await asyncio.sleep(5.3)   # a right guess in the first 5 s pays nothing
            await lan.page.fill('.kr-sheet[open] .kr-input', 'noi nay co anh')
            await lan.page.click('.kr-sheet[open] .kr-main')
            rv = await until(minh, 's.reveal', 'Minh sees the answer')
            check(rv['reveal']['by'] and rv['reveal']['by']['name'] == 'Lan' and rv['reveal']['xu'] == 5, 'the round is won by Lan, +5 xu')
            await until(lan, 's.reveal', 'Lan sees the answer')
            txt = await lan.page.inner_text('.kr-sheet[open] .kr-round')
            check('Nơi này có anh' in txt and '+5 xu' in txt, f'the answer and the prize on the winner ({txt!r})')
            await shot(lan, 'round-won-chromium')
            words = await lan.page.evaluate("""() => { const d = document.querySelector('.kr-sheet[open]'); const t = [...d.querySelectorAll('.kr-head, .kr-bar')].map(e => e.innerText).join(' ');
                return t.split(/\\s+/).filter(w => /[A-Za-zÀ-ỹ]/.test(w)).length; }""")
            check(words <= 25, f'few words on the room chrome ({words} ≤ 25)')
            # WebKit layout
            wk = await pw.webkit.launch()
            ctx = await wk.new_context(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True, device_scale_factor=2)
            await mock(ctx)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: problems.append(f'webkit exception: {str(e)[:200]}'))
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.click('[data-action=jrGender][data-gender=male]', timeout=10000)
            await page.fill('#jr-name', 'Khoa')
            await page.click('form[data-jr-form=start] button[type=submit]')
            await page.wait_for_timeout(2500)
            for _ in range(8):
                if not await page.evaluate("!!document.querySelector('#sheet[open],#confirmDialog[open]')"):
                    break
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(400)

            class P:
                pass
            k = P()
            k.page, k.name = page, 'webkit'
            await page.wait_for_timeout(1500)
            await enter(k)
            await page.wait_for_timeout(1500)
            lay = await page.evaluate("""() => { const d = document.querySelector('.kr-sheet[open]'), v = d.querySelector('.kr-video'), b = d.querySelector('.kr-bar');
                const rv = v.getBoundingClientRect(), rb = b.getBoundingClientRect();
                return {sw: document.documentElement.scrollWidth, iw: innerWidth, ih: innerHeight, vh: rv.height, vw: rv.width, vtop: rv.top, vbot: rv.bottom,
                        btop: rb.top, bbot: rb.bottom, hidden: v.hidden, dw: d.getBoundingClientRect().width}; }""")
            print('webkit layout:', lay, flush=True)
            check(lay['sw'] <= lay['iw'] and lay['dw'] <= lay['iw'] + 1, 'webkit: no horizontal scroll at 390 px')
            check(not lay['hidden'] and lay['vh'] >= 200 and lay['vtop'] >= 0 and lay['vbot'] <= lay['ih'], 'webkit: the player ≥ 200 px high, fully on screen')
            check(lay['btop'] >= lay['vbot'] - 1 and lay['bbot'] <= lay['ih'] + 1, 'webkit: the bottom bar on screen, under the player')
            await page.wait_for_timeout(2500)
            st = await page.evaluate(STATE)
            mode = await page.evaluate("document.querySelector('.kr-sheet[open] .kr-main').dataset.mode")
            check(st['ps'] == 1 or mode == 'play', f'webkit: playing, or one "▶ Nghe" button when the phone blocks sound (state {st["ps"]}, button {mode})')
            k.ctx = ctx
            await shot(k, 'room-webkit')
            await wk.close()
            await browser.close()
        logtxt = Path(live_log).read_text(errors='replace')
        for line in logtxt.splitlines():
            if 'handler' in line or 'karaoke' in line.lower() and ('error' in line.lower() or 'Error' in line):
                problems.append('live log: ' + line[:200])
    print('\n'.join(checks))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path)
    ap.add_argument('--real', action='store_true')
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(a.shots, a.real))
    if problems:
        print('PROBLEMS:\n  ' + '\n  '.join(problems))
        sys.exit(1)
    print('OK')


if __name__ == '__main__':
    main()
