#!/usr/bin/env python3
"""🎙️ Phòng hát mic trực tiếp in four phones with a REAL LiveKit server (dev tool; needs `pip install playwright
websockets`, TEST_DATABASE_URL, and a livekit-server binary: LIVEKIT_BIN, e.g. the release tarball or Homebrew).

Starts LiveKit on 127.0.0.1 (room.auto_create off, like production: deploy/livekit/livekit.yaml), a game server and
the live service with LIVE_KARAOKE=1 LIVE_KARAOKE_MIC=1. Chromium runs with a fake microphone (a beep) and fake media
UI. The YouTube player is the stand-in of browser_live_karaoke.py. The LiveKit SDK is served from a local copy at its
real jsDelivr URL when --sdk FILE is given (its SRI is still checked by the browser), else fetched from jsDelivr.

  * the headers: Permissions-Policy microphone=(self), the SDK and the SFU in the CSP;
  * Hoa blocks Lan (👥 › 🚫) before anything plays;
  * Lan queues a song; on stage she taps 🎙️: the headphones note, then the birth year (2000), then the mic goes
    live; everyone sees "🎤 Đang phát trực tiếp giọng hát";
  * Minh hears her: his inbound RTP packets/bytes grow (getStats), Lan's outbound ones too; Hoa (who blocked her)
    sees the notice but gets no audio; the SFU lists Lan as the only publisher and Minh as a hidden listener;
  * Minh's video follows Lan's own video time (kara_vt) minus the voice's delay: Lan's video − Minh's ≈ that delay,
    and his once-a-song "kara_mic sync jb=… lag=…" beacon is stored;
  * Lan's song is skipped: her mic is cut (the SFU room is gone: no participant left), Minh stops hearing;
  * Bé joins late (the mic is already live) on a network where the SDK cannot load (both copies fail): "🎧 Đang nối
    giọng…", two quiet retries, then "Chưa nghe được giọng · Thử lại", and the page's error beacon stores
    "kara_mic listen sdk: …" (stat_client_errors); the network comes back, Thử lại, and Bé hears Lan too. Nobody
    fetched the SDK from jsDelivr (our own copy, public/js/vendor/); Minh's stages reach `audio`, Lan's too;
  * Bé (born this year − 15: maybe still 15) is next on stage: 🎙️ → birth year → "từ 16 tuổi", no SFU room.
--tcp-only runs Chromium with `--force-webrtc-ip-handling-policy=disable_non_proxied_udp` (no UDP at all, as on the
production server whose provider drops UDP): media must go over ICE/TCP (rtc.tcp_port).
At most four PNG shots at 390×844 (--shots DIR).

  python scripts/browser_live_karaoke_mic.py [--shots DIR] [--sdk FILE] [--tcp-only]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT))
from browser_live_chat import PW, free_port, phone, wait_http  # noqa: E402
from browser_live_karaoke import FAKE_YT, PIXEL, VID  # noqa: E402
from browser_live_wedding import hub  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for  # noqa: E402

STATE = "async () => (await import('/js/v4/karaoke.js')).karaoke.state()"
STATS = "async () => (await import('/js/v4/karaoke.js')).karaoke.micStats()"
SDK_URL = 'https://cdn.jsdelivr.net/npm/livekit-client@2.22.3/dist/livekit-client.umd.js'
OWN_SDK = '/js/vendor/livekit-client-2.22.3.umd.js'
KEY, SECRET = 'devkey', secrets.token_hex(24)


@contextlib.contextmanager
def sfu(tmp: str):
    binary = os.environ.get('LIVEKIT_BIN') or 'livekit-server'
    port, tcp, udp = free_port(), free_port(), free_port()
    conf = Path(tmp, 'livekit.yaml')
    conf.write_text(f"""port: {port}
bind_addresses: ["127.0.0.1"]
rtc:
  tcp_port: {tcp}
  udp_port: {udp}
  use_external_ip: false
  node_ip: 127.0.0.1
  enable_loopback_candidate: true
room:
  auto_create: false
  empty_timeout: 60
keys:
  {KEY}: {SECRET}
logging:
  level: info
""")
    log = open(Path(tmp, 'livekit.log'), 'w')
    proc = subprocess.Popen([binary, '--config', str(conf)], stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{port}/')
    try:
        yield f'ws://127.0.0.1:{port}', f'http://127.0.0.1:{port}', str(Path(tmp, 'livekit.log'))
    finally:
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(5)
        log.close()


@contextlib.contextmanager
def servers(tmp: str, ws: str, api: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.db')
    env = test_env(QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live', LIVE_KARAOKE_MIC='1', LIVEKIT_URL=ws)
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    py = os.environ.get('MNL_PY') or sys.executable
    game = subprocess.Popen([py, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_KARAOKE='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp),
                LIVEKIT_API_URL=api, LIVEKIT_API_KEY=KEY, LIVEKIT_API_SECRET=SECRET)
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([py, '-m', 'live', '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db, os.path.join(tmp, 'live.log')
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


def sql(db, q, *args):
    with test_connect(db) as con:
        return con.execute(q, args).fetchall()


async def run(shots: Path | None, sdk_file: Path | None, tcp_only: bool) -> list:
    from playwright.async_api import async_playwright
    from live.sfu import Sfu
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
        await p.page.screenshot(path=str(shots / f'{nshots[0]}-{name}.png'))

    async def until(p, js, what, timeout=20.0):
        end = time.monotonic() + timeout
        while True:
            s = await p.page.evaluate(STATE)
            if await p.page.evaluate(f's => ({js})', s):
                return s
            if time.monotonic() > end:
                print('problems so far:', *problems[-12:], sep='\n  ', flush=True)
                raise AssertionError(f'{p.name}: {what} (state: {json.dumps(s, ensure_ascii=False)[:600]})')
            await asyncio.sleep(0.2)

    async def mock(ctx):
        await ctx.route('**/iframe_api*', lambda r: r.fulfill(status=200, content_type='text/javascript', body=FAKE_YT))
        await ctx.route('https://i.ytimg.com/**', lambda r: r.fulfill(status=200, content_type='image/png', body=PIXEL))
        if sdk_file:
            body = sdk_file.read_bytes()
            await ctx.route(SDK_URL, lambda r: r.fulfill(status=200, content_type='application/javascript', body=body,
                                                         headers={'Access-Control-Allow-Origin': '*'}))

    async def enter(p):
        await hub(p, 'liveKara')
        await p.page.wait_for_selector('.kr-sheet[open] .kr-room', timeout=15000)
        await p.page.click('.kr-sheet[open] .kr-room[data-id="kara:tre"]')
        await p.page.wait_for_selector('.kr-sheet[open] .kr-bar:not([hidden])', timeout=10000)

    async def queue(p):
        await p.page.click('.kr-sheet[open] .kr-main')
        await p.page.fill('.kr-sheet[open] [data-kr-link]', f'https://youtu.be/{VID}')
        await p.page.click('.kr-sheet[open] [data-kr=check]')
        await p.page.wait_for_selector('.kr-sheet[open] [data-kr=queue]', timeout=10000)
        await p.page.click('.kr-sheet[open] [data-kr=queue]')

    async def mic_flow(p, year):
        """🎙️ → (the note) Bật mic → (the birth year) Lưu."""
        await p.page.click('.kr-sheet[open] [data-kr=mic]', timeout=15000)
        await p.page.click('.kr-sheet[open] [data-kr=micgo]', timeout=5000)
        await p.page.wait_for_selector('.kr-sheet[open] [data-kr-year]', timeout=8000)
        await p.page.select_option('.kr-sheet[open] [data-kr-year]', str(year))
        await p.page.click('.kr-sheet[open] [data-kr=birthgo]')

    async def rtp(p, side):
        out = await p.page.evaluate(STATS)
        return out.get(side) or {'packets': 0, 'bytes': 0}

    args = ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--autoplay-policy=no-user-gesture-required']
    if tcp_only:
        args.append('--force-webrtc-ip-handling-policy=disable_non_proxied_udp')
    with tempfile.TemporaryDirectory(prefix='mnl-kmic-', dir=os.environ.get('TMPDIR')) as tmp, sfu(tmp) as (ws, api, lk_log), servers(tmp, ws, api) as (base, db, live_log):
        api_client = Sfu(ws, api, KEY, SECRET)
        sql(db, "INSERT INTO kara_songs(vid, title, channel, ok, why, checked_at) VALUES(?, 'Nơi này có anh (Official MV)', 'Sơn Tùng M-TP', 1, '', ?)", VID, time.time())
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=args)
            people = {}
            for name, user in (('Lan', 'lan_m'), ('Minh', 'minh_m'), ('Hoa', 'hoa_m'), ('Bé', 'be_m')):
                p = await phone(browser, base, name, problems)
                await mock(p.ctx)
                await p.ctx.grant_permissions(['microphone'], origin=base)
                p.page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
                await p.api('/api/account/register', dict(username=user, password=PW, confirm=PW, display=name))
                people[name] = p
            sql(db, "UPDATE accounts SET created_at='2026-01-01 00:00:00'")
            for p in people.values():
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.page.wait_for_timeout(1200)
            lan, minh, hoa, be = people['Lan'], people['Minh'], people['Hoa'], people['Bé']
            resp = await lan.page.request.get(base + '/')
            h = resp.headers
            check('microphone=(self)' in h.get('permissions-policy', '') and 'camera=()' in h.get('permissions-policy', ''), f'Permissions-Policy: {h.get("permissions-policy")}')
            csp = h.get('content-security-policy', '')
            check(SDK_URL in csp and ws in csp and "'unsafe-eval'" not in csp and "default-src 'self'" in csp, 'CSP: the pinned SDK and the SFU only')
            cdn = []
            for p in (lan, minh, hoa):   # (Bé's network fails on purpose below: she falls back to jsDelivr)
                p.page.on('request', lambda r: cdn.append(r.url) if 'cdn.jsdelivr.net' in r.url else None)
            for p in (lan, minh, hoa):   # Bé comes in later, once the mic is live
                await enter(p)
            # Hoa blocks Lan in the room (👥 › 🚫)
            await hoa.page.click('.kr-sheet[open] [data-kr=people]')
            from game.karaoke import pid_of

            def pid(user):
                return pid_of(sql(db, 'SELECT sid FROM accounts WHERE username=?', user)[0][0])
            lan_pid, minh_pid, hoa_pid = pid('lan_m'), pid('minh_m'), pid('hoa_m')
            await hoa.page.click(f'.kr-sheet[open] [data-kr=block][data-pid="{lan_pid}"]', timeout=8000)
            await hoa.page.wait_for_timeout(800)
            check(len(sql(db, 'SELECT 1 FROM blocks WHERE target=?', lan_pid)) == 1, 'Hoa blocked Lan from the room')
            # Lan sings, then turns the mic on (note → birth year → permission (fake UI) → live)
            await queue(lan)
            await until(lan, 's.stage && s.stage.vid', 'Lan on stage')
            await until(lan, 's.ps === 1', 'Lan plays', 25)
            await mic_flow(lan, 2000)
            await until(lan, 's.pub', 'Lan publishes', 25)
            check(sql(db, 'SELECT year FROM account_birth')[0][0] == 2000, 'the birth year is stored on the account (account_birth)')
            for p in (lan, minh, hoa):
                await p.page.wait_for_selector('.kr-sheet[open] .kr-live', timeout=10000)
                txt = await p.page.inner_text('.kr-sheet[open] .kr-live')
                check('Đang phát trực tiếp giọng hát' in txt, f'{p.name} sees "🎤 Đang phát trực tiếp giọng hát"')
            await until(minh, 's.sub && s.heard', 'Minh hears Lan', 30)
            a = await rtp(minh, 'sub')
            await asyncio.sleep(2.5)
            b = await rtp(minh, 'sub')
            print('Minh inbound RTP', a, '→', b, flush=True)
            check(b['packets'] > a['packets'] + 50 and b['bytes'] > a['bytes'], f'Minh receives Lan\'s audio (inbound-rtp packets {a["packets"]} → {b["packets"]})')
            pair = await minh.page.evaluate("""async () => { const m = await import('/js/v4/karaoke.js'); const r = await m.karaoke.micPath(); return r; }""")
            print('Minh ICE path:', pair, flush=True)
            if tcp_only:
                check(pair and pair.get('protocol') == 'tcp', f'no UDP: the voice comes over ICE/TCP ({pair})')
            o = await rtp(lan, 'pub')
            check(o['packets'] > 100, f'Lan sends audio (outbound-rtp packets {o["packets"]})')
            await asyncio.sleep(3.0)
            sm, sl = await minh.page.evaluate(STATE), await lan.page.evaluate(STATE)
            check(sm['at'] == 'audio' and sm['ls'] == 'live' and sl['pubAt'] == 'audio', f'stages: Minh {sm["at"]} ({sm["ls"]}), Lan {sl["pubAt"]}')
            # 🎙️ voice and music together: Minh's video follows Lan's own (kara_vt) minus the voice's delay (getStats)
            sm = await until(minh, 's.follow && s.vt && s.vt.age < 3 && s.jb !== null', "Minh follows Lan's video", 20)
            check(0 < sm['lag'] <= 1.5 and not sl['vtOff'], f"Minh's voice delay {sm['lag']:.3f} s (jitter buffer {sm['jb']:.3f} s), Lan sends her video time")
            await until(minh, 's.follow && s.rate === 1 && Math.abs(s.cur - s.target) < 0.12', 'Minh settles on that target (nudged at 5 %, a seek past 0.6 s)', 45)
            gaps = []
            for _ in range(5):
                cl, cm = await asyncio.gather(lan.page.evaluate(STATE), minh.page.evaluate(STATE))
                gaps.append(round(cl['cur'] - cm['cur'] - cm['lag'], 3))
                await asyncio.sleep(0.4)
            print("Lan's video − Minh's − delay:", gaps, '| Lan', {k: cl[k] for k in ('pos', 'cur', 'rate')}, '| Minh', {k: cm[k] for k in ('pos', 'cur', 'target', 'rate', 'lag')}, flush=True)
            check(max(abs(g) for g in gaps) < 0.2, f"Minh's music is where Lan's was when she sang what he hears (± {max(abs(g) for g in gaps):.3f} s)")
            sh = await hoa.page.evaluate(STATE)
            check(sh['live'] and not sh['sub'] and sh['ls'] == '', f'Hoa (who blocked Lan) sees the notice and gets no audio, and no "đang nối" either ({sh["ls"]!r})')
            txt = await hoa.page.inner_text('.kr-sheet[open] .kr-live')
            check('nối giọng' not in txt and 'Chưa nghe' not in txt, f'Hoa: nothing says why ({txt!r})')
            # Bé joins late; the SDK cannot load on her network (our copy and jsDelivr both fail)
            dead = lambda r: r.abort()
            await be.ctx.route('**' + OWN_SDK + '*', dead)
            await be.ctx.route(SDK_URL, dead)
            await enter(be)
            await be.page.wait_for_selector('.kr-sheet[open] .kr-live', timeout=10000)
            txt = await be.page.inner_text('.kr-sheet[open] .kr-live')
            check('Đang nối giọng' in txt, f'Bé (late) sees "🎧 Đang nối giọng…" ({txt!r})')
            sb = await until(be, "s.ls === 'fail'", 'Bé gives up after the retries', 30)
            check(sb['tries'] == 3 and not sb['sub'], f'Bé: two quiet retries, then the failure ({sb["tries"]})')
            txt = await be.page.inner_text('.kr-sheet[open] .kr-live')
            check('Chưa nghe được giọng' in txt and await be.page.is_visible('.kr-sheet[open] [data-kr=voiceretry]'), f'Bé sees "Chưa nghe được giọng · Thử lại" ({txt!r})')
            await shot(be, 'listener-fail')
            rows = []
            for _ in range(40):
                rows = sql(db, "SELECT kind, message_key, screen, count FROM stat_client_errors WHERE message_key LIKE 'kara_mic%'")
                if rows:
                    break
                await asyncio.sleep(0.5)
            print('beacon rows:', rows, flush=True)
            check(any(r[0] == 'toast' and r[1].startswith('kara_mic listen sdk:') and 'self' in r[1] and 'cdn' in r[1] for r in rows),
                  f'the error beacon has the stage: kara_mic listen sdk (self + cdn) ({rows})')
            problems[:] = [x for x in problems if not x.startswith('Bé console: Failed to load resource: net::ERR_FAILED')]   # the cut network
            await be.ctx.unroute('**' + OWN_SDK + '*', dead)
            await be.ctx.unroute(SDK_URL, dead)
            await be.page.click('.kr-sheet[open] [data-kr=voiceretry]')
            await until(be, 's.sub && s.heard', 'Bé hears Lan after Thử lại', 30)
            check(True, 'Bé hears Lan after Thử lại (late joiner)')
            rooms = [r for r in await api_client.rooms() if r.startswith('kara-')]
            parts = await api_client.participants(rooms[0]) if rooms else []
            who = {x.get('identity'): x for x in parts}
            pubs = [i for i, x in who.items() if x.get('tracks')]
            check(not cdn, f'the SDK came from our own origin, not jsDelivr ({cdn[:2]})')
            check(len(rooms) == 1 and pubs == [lan_pid] and minh_pid in who and hoa_pid not in who,
                  f'the SFU: one room, Lan the only publisher, Minh listening, Hoa absent ({sorted(who)})')
            perm = (who.get(minh_pid) or {}).get('permission') or {}
            check(not perm.get('can_publish') and (who.get(minh_pid) or {}).get('is_publisher') in (None, False), f'Minh cannot publish ({perm})')
            await shot(minh, 'listener-live')
            await shot(lan, 'singer-live')
            for p in (lan, minh):   # 390 px: the stage line, its buttons and the live banner stay on screen
                lay = await p.page.evaluate("""() => { const d = document.querySelector('.kr-sheet[open]'); const r = e => e && e.getBoundingClientRect();
                    const btns = [...d.querySelectorAll('.kr-on button, .kr-live button, .kr-live input')].map(r);
                    return {iw: innerWidth, sw: d.querySelector('.kr-body').scrollWidth, cw: d.querySelector('.kr-body').clientWidth,
                            right: Math.max(...btns.map(b => b.right), r(d.querySelector('.kr-live')).right)}; }""")
                check(lay['sw'] <= lay['cw'] + 1 and lay['right'] <= lay['iw'], f'{p.name}: the stage line and the live banner fit 390 px ({lay})')
            # Bé queues; Lan's song is skipped: the mic is cut
            await queue(be)
            await until(be, 's.queue >= 1', 'Bé queued')
            await lan.page.click('.kr-sheet[open] [data-kr=skip]')
            await until(lan, '!s.pub', 'Lan\'s mic is off', 10)
            await until(minh, '!s.sub && !s.live', 'Minh stops hearing', 10)
            rows = []
            for _ in range(30):   # Minh's once-a-song sync beacon (letters: the server masks digits)
                rows = sql(db, "SELECT message_key FROM stat_client_errors WHERE message_key LIKE 'kara_mic sync%'")
                if rows:
                    break
                await asyncio.sleep(0.5)
            print('sync beacon:', rows, flush=True)
            check(rows and all(' novt' not in r[0] for r in rows) and any('jb=-' not in r[0] and 'lag=' in r[0] for r in rows),
                  f'the sync beacon (Minh; Bé too if she heard 10 s): {rows}')
            await asyncio.sleep(1.0)
            left = [r for r in await api_client.rooms() if r.startswith('kara-')]
            check(left == [], f'the SFU room is deleted on the stage change ({left})')
            # Bé (maybe 15): refused
            await until(be, 's.stage && s.stage.phase !== "clap" && s.ps === 1', 'Bé on stage', 30)
            year = time.gmtime(time.time() + 7 * 3600).tm_year - 15
            await mic_flow(be, year)
            await until(be, "s.panel === 'young'", 'Bé is refused', 10)
            txt = await be.page.inner_text('.kr-sheet[open] .kr-panel')
            check('từ 16 tuổi' in txt, f'Bé is told the mic is from 16 ({txt[:80]!r})')
            await shot(be, 'under16')
            await asyncio.sleep(1.5)
            sb, sm = await be.page.evaluate(STATE), await minh.page.evaluate(STATE)
            check(not sb['pub'] and not sm['live'] and [r for r in await api_client.rooms() if r.startswith('kara-')] == [], 'no mic, no SFU room for Bé')
            await browser.close()
        logtxt = Path(live_log).read_text(errors='replace')
        for line in logtxt.splitlines():
            if 'handler' in line or ('karaoke' in line.lower() and 'error' in line.lower()) or 'sfu:' in line:
                problems.append('live log: ' + line[:200])
    print('\n'.join(checks))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path)
    ap.add_argument('--sdk', type=Path)
    ap.add_argument('--tcp-only', action='store_true')
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(a.shots, a.sdk, a.tcp_only))
    if problems:
        print('PROBLEMS:\n  ' + '\n  '.join(problems))
        sys.exit(1)
    print('OK')


if __name__ == '__main__':
    main()
