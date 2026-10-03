#!/usr/bin/env python3
"""📸 The fair's photobooth when the live socket comes and goes (dev tool, needs `pip install playwright websockets` +
chromium). Owner 03/10: "buồng photobooth hội chợ mở 24/24 chứ k được nghỉ" and "cái tìm buồng lỗi rồi, k vào phòng
người khác đc".

Starts a game server (the fair open today) and the live service, two phones (390×844). Each page's WebSocket is
wrapped (an init script) so a test can drop it (`__ws.kill()`) or refuse new ones (`__ws.block`, a service that is
down), then:
  1. the booth opened with the socket down: "Đang nối buồng chung…" (never "đang nghỉ"), Một mình still there; after
     10 s a "Thử lại" button, which connects at once; a drop while on the lobby: it shows, and the socket's own
     return enables the shared ways again without a tap;
  2. Người lạ: A finds, B finds: they meet in one room;
  3. Bạn bè: A makes a room, A's phone drops the socket (another app to send the code), B joins by the code in the
     meantime, A comes back in by itself (same room, still the host); both get ready, the host shoots, both get
     the strip.
Fails on console errors, page errors or HTTP 5xx.

  MNL_PY=python3.12 MNL_PYTHONPATH=… python scripts/browser_fair_booth_conn.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_fair_booth import ST, WALLET, seed  # noqa: E402
from browser_live_chat import phone  # noqa: E402

# The page's sockets, for the test: kill() drops them (as a phone in another app does), block refuses new ones.
WS_HOOK = """(()=>{const W=window.WebSocket;if(!W||W.__hooked)return;const all=[];
globalThis.__ws={all,block:false,kill(){for(const s of all.splice(0))try{s.close();}catch{}}};
function X(u,p){if(globalThis.__ws.block)throw new DOMException('blocked by the test','NetworkError');const s=p===undefined?new W(u):new W(u,p);all.push(s);return s;}
X.prototype=W.prototype;Object.assign(X,{CONNECTING:0,OPEN:1,CLOSING:2,CLOSED:3,__hooked:true});window.WebSocket=X;})();"""
LOBBY = """(()=>{const q=s=>document.querySelector('.fh-sheet '+s),t=q('.fh-pb')?.textContent||'';
return {shared:!!globalThis.__fairBooth?.state().shared,connecting:/Đang nối buồng chung/.test(t),retry:!!q('[data-fh="pbretry"]'),
resting:/đang nghỉ/.test(t),find:!q('[data-fh="pbfind"]')?.disabled,make:!q('[data-fh="pbmake"]')?.disabled,
join:!q('[data-fh="pbjoin"]')?.disabled,solo:!q('[data-fh="pbsolo"]')?.disabled};})()"""


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    from browser_live_pin import servers
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-boothc-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db, py, env):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Lan', problems, intro=False)
            b = await phone(browser, base, 'Minh', problems, intro=False)
            for p, name in ((a, 'Lan'), (b, 'Minh')):
                await p.ctx.add_init_script(WS_HOOK)
                await p.ctx.add_init_script("try{localStorage.setItem('mnl.home','list')}catch(e){}")  # the list as home (the town is the default): the fair's row
                token = next(c['value'] for c in await p.ctx.cookies() if c['name'] == 'mnl_session')
                seed(db, token, name)
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.page.wait_for_timeout(1200)

            async def poll(page, js, timeout=10.0):
                end = time.monotonic() + timeout
                while time.monotonic() < end:
                    if await page.evaluate(f'() => Boolean({js})'):
                        return True
                    await asyncio.sleep(0.15)
                return False

            async def shot(p, name, at='.fh-pb-booth'):   # the booth's stage at the top of the screen
                await p.page.evaluate(f"document.querySelector('.fh-sheet {at}')?.scrollIntoView({{block:'start'}})")
                await p.page.wait_for_timeout(300)
                await p.page.screenshot(path=str(shots / f'{name}.png'))

            async def open_booth(p):
                page = p.page
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                if not await page.locator('.jr-fair-row').count():
                    await page.evaluate("document.querySelector('[data-action=\"home\"]')?.click()")
                    await page.wait_for_selector('.jr-fair-row', timeout=10000)
                for _ in range(4):
                    x = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                    if not await x.count():
                        break
                    await x.first.click()
                    await page.wait_for_timeout(400)
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close());document.querySelector('.jr-fair-row').click()")
                await page.wait_for_selector('.fh-sheet[open]', timeout=10000)
                await page.wait_for_timeout(600)
                if await page.locator('.fh-sheet [data-fh="giftok"]').count():
                    await page.click('.fh-sheet [data-fh="giftok"]')
                await page.evaluate("document.querySelector('.fh-sheet .fh-wlist')?.setAttribute('open','');document.querySelector('.fh-sheet [data-tab=\"pb\"]').click()")
                await page.wait_for_selector('.fh-sheet .fh-pb', timeout=6000)

            async def click(p, op, v=None):
                sel = f'.fh-sheet [data-fh="{op}"]' + (f'[data-v="{v}"]' if v is not None else '')
                await p.page.locator(sel).first.scroll_into_view_if_needed()
                await p.page.click(sel)

            # ---------------- 1. the booth with the socket down ----------------
            await a.page.evaluate("__ws.block=true;__ws.kill()")
            await open_booth(a)
            st = await a.page.evaluate(LOBBY)
            check(st['connecting'] and not st['resting'] and not st['retry'], f'socket down: "Đang nối buồng chung…", never "đang nghỉ" ({st})')
            check(st['solo'] and not st['find'] and not st['join'], f'socket down: Một mình open, the shared ways wait ({st})')
            await shot(a, '01-connecting')
            check(await poll(a.page, f"{LOBBY}.retry", 12), 'after 10 s: a "Thử lại" button')
            check(not (await a.page.evaluate(LOBBY))['resting'], 'still never "đang nghỉ"')
            await shot(a, '02-retry')
            await a.page.evaluate("__ws.block=false")
            await click(a, 'pbretry')
            check(await poll(a.page, f"{LOBBY}.shared&&{LOBBY}.find&&{LOBBY}.join&&!{LOBBY}.connecting", 6), '"Thử lại" connects at once: the shared ways open')
            await a.page.evaluate("__ws.block=true;__ws.kill()")       # a drop while on the lobby (a deploy, the network)
            check(await poll(a.page, f"{LOBBY}.connecting&&!{LOBBY}.find", 4), 'a drop shows at once (no dead buttons)')
            await a.page.wait_for_timeout(1500)
            await a.page.evaluate("__ws.block=false")
            check(await poll(a.page, f"{LOBBY}.shared&&{LOBBY}.find&&!{LOBBY}.connecting", 20), 'the socket comes back by itself: the page redraws, no tap')

            # ---------------- 2. Người lạ: A finds, B finds ----------------
            await open_booth(b)
            check(await poll(b.page, f"({ST}).shared", 10), 'B: shared booth on')
            await click(a, 'pbfind')
            check(await poll(a.page, f"({ST}).step==='wait'", 5), 'A waits for a stranger')
            await click(b, 'pbfind')
            for p in (a, b):
                check(await poll(p.page, f"({ST}).mode==='stranger'&&({ST}).room?.people?.length===2", 8), f'{p.name} meets a stranger')
            for p in (a, b):
                await click(p, 'pbout')
            for p in (a, b):
                check(await poll(p.page, f"({ST}).step==='lobby'", 4), f'{p.name} back in the lobby')

            # ---------------- 3. Bạn bè: the host's socket drops while sharing the code ----------------
            await click(a, 'pbmake')
            check(await poll(a.page, f"({ST}).room?.code", 6), 'a room code')
            code = (await a.page.evaluate(ST))['room']['code']
            await a.page.evaluate("__ws.block=true;__ws.kill()")       # off to another app to send the code
            check(await poll(a.page, "/đang nối lại phòng/.test(document.querySelector('.fh-sheet .fh-flash')?.textContent||'')", 4),
                  'A: "Mất kết nối, đang nối lại phòng…", still in the room')
            check((await a.page.evaluate(ST))['step'] == 'room', 'A keeps the room on screen')
            await b.page.fill('.fh-sheet .fh-pb-code', code.lower())
            await click(b, 'pbjoin')
            check(await poll(b.page, f"({ST}).room?.people?.length===2", 6), 'B gets in by the code while A is away')
            await shot(b, '03-joined-host-away')
            await a.page.evaluate("__ws.block=false")
            check(await poll(a.page, f"({ST}).room?.code==='{code}'&&({ST}).room?.people?.length===2&&!({ST}).room.people.some(p=>p.away)", 20),
                  'A comes back into the same room by itself')
            sa = await a.page.evaluate(ST)
            check(sa['room']['host'] == sa['me'], 'A is still the host')
            check(await poll(b.page, f"!({ST}).room.people.some(p=>p.away)", 5), 'B sees A back')
            await shot(a, '04-host-back')
            before = [await p.page.evaluate(WALLET) for p in (a, b)]
            for p in (a, b):
                await click(p, 'pbready')
            for p in (a, b):
                check(await poll(p.page, f"({ST}).ready", 8), f'{p.name} is ready')
            check(await poll(a.page, "!document.querySelector('.fh-sheet [data-fh=\"pbgo\"]').disabled", 8), 'the host can shoot')
            for p, w0 in zip((a, b), before):
                check(await poll(p.page, f"{WALLET}==={w0 - 5}", 6), f'{p.name} paid 5 xu')
            await click(a, 'pbgo')
            for p in (a, b):
                check(await poll(p.page, f"({ST}).step==='print'&&({ST}).url", 25), f'{p.name} gets the shared strip')
                check((await p.page.evaluate(ST))['shots'] == 4, f'{p.name}: 4 shots')
            await shot(b, '05-strip')
            await browser.close()
    print('\n'.join(checks))
    return problems


def main() -> int:
    from browser_fair import vn_today
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default=str(ROOT.parent / '_fair_booth_conn_shots'))
    args = ap.parse_args()
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    os.environ['MNL_FAIR_START'] = vn_today()
    os.environ['LIVE_FAIR'] = '1'
    problems = asyncio.run(run(shots))
    for p in problems:
        print('✗', p)
    print('ok:' if not problems else 'FAILED:', shots)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
