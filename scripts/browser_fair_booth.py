#!/usr/bin/env python3
"""📸 Buồng chụp ảnh at the fair in two browsers (dev tool, needs `pip install playwright websockets` + chromium).

Starts a game server (story mode, SQLite, the fair open today) and the live service (chat and the fairground on) on
the same database, two phones (390×844) with 300 xu each, then:
  1. Bạn bè: Lan walks up to the booth on the fairground, makes a room and gets a 4-character code; Minh types it
     in and joins; the host's frame and backdrop reach Minh, each picks a pose and a prop; both pay their ticket
     (5 xu each, the wallets drop) and get ready, the host shoots: 3-2-1 × 4 on both phones, then the strip
     (frame Tết, then Trung thu after "Chụp lượt nữa"); Minh's own filter and stickers;
  2. Người lạ: both look for a stranger and are paired into one room, shoot in the frame Dễ thương;
  3. Một mình: Lan alone, frame Phim cũ; the save button downloads a PNG; then Tết rộn ràng with a 🎲 pose and
     Dán sticker, each with its own colour;
  4. the lobby and a room at 320 and 430 px wide, and "Phố đêm".
1.5.5 (thirty poses, the fair's frames): a pose made together reaches the whole room, the 🎲 picks one; Thu and Bảo
join by code: four in the room, a pose for all and poses changing between the shots, strips in Hội chợ đêm with the
colours Dịu and Đen trắng and the words; the pose picker, the countdown and the strips at 390 and 1280 px.
Each strip is also saved at full size (the page's own renderer, ×3) as strip-*.png. Fails on console errors, page
errors or HTTP 5xx.

  MNL_PY=python3.12 MNL_PYTHONPATH=… python scripts/browser_fair_booth.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import phone  # noqa: E402

ST = "globalThis.__fairBooth?.state()"
WALLET = "+(document.querySelector('.fh-sheet .fh-strip b')?.textContent||'').replace(/\\D/g,'')"


def seed(db: str, token: str, name: str) -> None:
    from game import marriage as mr
    from game import whats_new as wn
    from game.storage import Store
    store = Store(db, story=True)

    def me(s):
        s['name'] = name
        s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
        s['journey'].update(gender='female' if name in ('Lan', 'Thu') else 'male', intro=True, wallet=300)
    mr._mutate(store, {store.key(token): me})
    store.close_pool()


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    from browser_live_pin import servers
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-booth-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db, py, env):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Lan', problems, intro=False)
            b = await phone(browser, base, 'Minh', problems, intro=False)
            c = await phone(browser, base, 'Thu', problems, intro=False)
            d = await phone(browser, base, 'Bảo', problems, intro=False)
            for p, name in ((a, 'Lan'), (b, 'Minh'), (c, 'Thu'), (d, 'Bảo')):
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

            async def shot(p, name):
                await p.page.wait_for_timeout(350)
                await p.page.screenshot(path=str(shots / f'{name}.png'))

            async def save_strip(p, name):
                url = await p.page.evaluate("globalThis.__fairBooth.print(3)")
                (shots / f'strip-{name}.png').write_bytes(base64.b64decode(url.split(',', 1)[1]))

            async def open_fair(p):
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
                await poll(page, "globalThis.__fairWalk?.state().on", 8)
                # the fair's one-time 500 xu gift pops up when its claim comes back (late on a slow machine)
                if await poll(page, "document.querySelector('.fh-sheet [data-fh=giftok]')", 4):
                    await gift_away(p)

            async def gift_away(p):
                """Close the fair's gift card if it is up: it covers the sheet, so a click under it never lands."""
                await p.page.evaluate("document.querySelector('.fh-sheet [data-fh=giftok]')?.click()")

            PANE = {'pbframe': 'frame', 'pbbg': 'bg', 'pbprop': 'prop', 'pbpose': 'pose', 'pbdice': 'pose', 'pbtab': 'pose'}

            async def pane(p, v):
                """Open one of the room's pickers (Dáng / Khung ảnh / Phông nền / Đạo cụ) when it is not open."""
                await p.page.evaluate("v=>{const b=document.querySelector(`.fh-sheet [data-fh=pbpane][data-v=${v}]`);if(b&&b.getAttribute('aria-pressed')!=='true')b.click();}", v)
                await poll(p.page, f"!document.querySelector('.fh-sheet [data-fh=pbpane]')||document.querySelector('.fh-sheet [data-fh=pbpane][data-v={v}]').getAttribute('aria-pressed')==='true'", 3)

            async def click(p, op, v=None):
                sel = f'.fh-sheet [data-fh="{op}"]' + (f'[data-v="{v}"]' if v is not None else '')
                await gift_away(p)
                if op in PANE:
                    await pane(p, PANE[op])
                try:
                    for attempt in range(3):   # the room redraws while the camera counts: a control can be swapped mid-click
                        try:
                            await p.page.locator(sel).first.scroll_into_view_if_needed(timeout=10000)
                            await bring_up(p, sel)
                            await p.page.click(sel, timeout=10000)
                            break
                        except Exception as e:
                            if attempt == 2 or 'not attached' not in str(e):
                                raise
                            await p.page.wait_for_timeout(150)
                except Exception:
                    if shots:
                        await p.page.screenshot(path=str(shots / f'zz-click-{p.name}-{op}.png'))
                    info = await p.page.evaluate("s=>{const e=document.querySelector(s);if(!e)return 'missing';const r=e.getBoundingClientRect();"
                                                 "const t=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);"
                                                 "return {r:[r.x,r.y,r.width,r.height],dis:e.disabled,top:t&&(t.className||t.tagName)}}", sel)
                    print(f'click {p.name} {op} {v}: {info}', flush=True)
                    raise

            async def bring_up(p, sel):
                """A control the room's stuck booth sits over is scrolled to the bottom of the screen, as a thumb does."""
                await p.page.evaluate("""s=>{const e=document.querySelector(s),top=document.querySelector('.fh-sheet .fh-pb-top');if(!e||!top)return;
                  const r=e.getBoundingClientRect(),t=top.getBoundingClientRect();if(e.closest('.fh-pb-top'))return;
                  if(r.top<t.bottom&&r.right>t.left&&r.left<t.right)e.scrollIntoView({block:'end'});}""", sel)

            async def shoot_round(host, others, frame_id, tag, between=()):
                """Everyone pays and gets ready, the host shoots; every phone ends on its strip. between: (after shot n,
                phone, op, v) clicks made while the camera counts (poses change between the shots)."""
                ppl = [host] + others
                before = [await p.page.evaluate(WALLET) for p in ppl]
                for p in ppl:
                    await click(p, 'pbready')
                for p in ppl:
                    check(await poll(p.page, f"({ST}).ready", 8), f'{tag}: {p.name} is ready')
                check(await poll(host.page, "!document.querySelector('.fh-sheet [data-fh=\"pbgo\"]').disabled", 8), f'{tag}: the host can shoot')
                for p, w0 in zip(ppl, before):
                    check(await poll(p.page, f"{WALLET}==={w0 - 5}", 6), f'{tag}: {p.name} paid 5 xu ({w0} → {await p.page.evaluate(WALLET)})')
                await click(host, 'pbgo')
                for p in ppl:
                    check(await poll(p.page, f"({ST}).step==='shoot'", 5), f'{tag}: {p.name} sees the countdown')
                await host.page.wait_for_timeout(2300)
                await host.page.evaluate("document.querySelector('.fh-sheet .fh-pb-booth')?.scrollIntoView({block:'center'})")
                await host.page.screenshot(path=str(shots / f'{tag}-countdown-{host.name}.png'))
                for n, p, op, v in between:
                    await poll(host.page, f"({ST}).shots>={n}", 8)
                    await click(p, op, v)
                for p in ppl:
                    check(await poll(p.page, f"({ST}).step==='print'&&({ST}).url", 25), f'{tag}: {p.name} gets the strip')
                    st = await p.page.evaluate(ST)
                    check(st['shots'] == 4 and st['frame'] == frame_id, f'{tag}: {p.name}: 4 shots in frame {frame_id} ({st["shots"]}, {st["frame"]})')

            # ---------------- 1. Bạn bè: a room by code ----------------
            await open_fair(a)
            check(await poll(a.page, "__fairWalk.state().spots.includes('pb')", 8), 'the booth stands on the fairground')
            await shot(a, '00-fairground')
            await a.page.evaluate("__fairWalk.go('pb')")
            if not await poll(a.page, "!!document.querySelector('.fh-sheet .fh-pb')", 8):
                problems.append('walking to the booth did not open it')
                await a.page.evaluate("document.querySelector('.fh-sheet [data-tab=\"pb\"]')?.click()")
            check(await poll(a.page, f"({ST}).shared", 10), 'the live service offers the shared booth (welcome.flags.booth)')
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '01-lobby')
            await click(a, 'pbmake')
            check(await poll(a.page, f"({ST}).room?.code", 6), 'a room code')
            code = (await a.page.evaluate(ST))['room']['code']
            check(len(code) == 4 and code.isalnum() and code.isupper(), f'the code reads like A7K2 ({code})')

            await open_fair(b)
            await b.page.evaluate("document.querySelector('.fh-sheet .fh-wlist')?.setAttribute('open','');document.querySelector('.fh-sheet [data-tab=\"pb\"]').click()")
            await b.page.wait_for_selector('.fh-sheet .fh-pb', timeout=6000)
            check(await poll(b.page, f"({ST}).shared", 10), 'B: shared booth on')
            await b.page.fill('.fh-sheet .fh-pb-code', 'zzzz')
            await click(b, 'pbjoin')
            check(await poll(b.page, "/Không thấy phòng/.test(document.querySelector('.fh-sheet .fh-flash')?.textContent||'')", 5), 'a wrong code is refused')
            await b.page.fill('.fh-sheet .fh-pb-code', code.lower())
            await b.page.keyboard.press('Enter')
            check(await poll(b.page, f"({ST}).room?.people?.length===2", 6), 'B joins by code')
            check(await poll(a.page, f"({ST}).room?.people?.length===2", 6), 'A sees B come in')
            await click(a, 'pbframe', 'tet')
            await click(a, 'pbbg', 'hoa')
            check(await poll(b.page, f"({ST}).frame==='tet'&&({ST}).bg==='hoa'", 5), "the host's frame and backdrop reach B")
            await pane(b, 'frame')
            check(await b.page.evaluate("document.querySelector('.fh-sheet [data-fh=\"pbframe\"]').disabled"), 'B cannot pick the frame')
            await click(a, 'pbpose', 'v')
            await click(a, 'pbprop', 'non_la')
            await click(b, 'pbpose', 'tim')
            await click(b, 'pbprop', 'tai_tho')
            check(await poll(a.page, f"({ST}).room.people.some(p=>p.pose==='tim'&&p.prop==='tai_tho')", 5), "B's pose and prop reach A")
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await b.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '02-friends-room-host')
            await shot(b, '03-friends-room-guest')
            await shoot_round(a, [b], 'tet', '04-friends')
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '05-friends-strip-tet-Lan')
            await save_strip(a, 'tet')
            await click(b, 'pbfilter', 'film')
            for s in ('tim', 'sao', 'phao_hoa'):
                await click(b, 'pbsticker', s)
            await click(b, 'pbtext', 'ban')
            check(await poll(b.page, f"({ST}).filter==='film'&&({ST}).stickers.length===3&&({ST}).text==='ban'&&({ST}).url", 5), "B's own colour, stickers and words")
            check((await a.page.evaluate(ST))['filter'] == 'none', "B's filter stays on B's strip")
            await b.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(b, '06-friends-strip-tet-Minh-filter')
            await save_strip(b, 'tet-film-stickers')
            # another round in another frame
            for p in (a, b):
                await click(p, 'pbagain')
            await click(a, 'pbframe', 'trung_thu')
            await click(a, 'pbbg', 'kim_tuyen')
            await click(a, 'pbpose', 'hoan_ho')
            await click(a, 'pbprop', 'long_den')
            await click(b, 'pbpose', 'vay')
            await click(b, 'pbprop', 'bong_bay')
            await shoot_round(a, [b], 'trung_thu', '07-again')
            await save_strip(a, 'trung-thu')
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '08-friends-strip-trung-thu')

            # ---------------- 1b. poses made together, the 🎲, four friends ----------------
            for p in (a, b):
                await click(p, 'pbagain')
            await click(a, 'pbtab', 'group')
            await click(a, 'pbpose', 'tim_to')
            check(await poll(b.page, f"({ST}).room.people.every(p=>p.pose==='tim_to')&&({ST}).pose==='tim_to'", 5), 'a pose made together reaches the whole room')
            await click(b, 'pbtab', 'solo')
            await click(b, 'pbpose', 'v')
            check(await poll(a.page, f"({ST}).room.people.some(p=>p.pose==='v')&&({ST}).pose==='tim_to'", 5), 'then each one their own pose again')
            before = (await b.page.evaluate(ST))['pose']
            await click(b, 'pbdice')
            check(await poll(b.page, f"({ST}).pose!=='{before}'", 5), 'the 🎲 picks another pose')
            for p in (c, d):
                await open_fair(p)
                await p.page.evaluate("document.querySelector('.fh-sheet .fh-wlist')?.setAttribute('open','');document.querySelector('.fh-sheet [data-tab=\"pb\"]').click()")
                await p.page.wait_for_selector('.fh-sheet .fh-pb', timeout=6000)
                await poll(p.page, f"({ST}).shared", 10)
                await p.page.fill('.fh-sheet .fh-pb-code', code)
                await p.page.keyboard.press('Enter')
            check(await poll(a.page, f"({ST}).room?.people?.length===4", 8), 'four friends in the room')
            await click(a, 'pbframe', 'hoi_dem')
            await click(a, 'pbbg', 'day_den')
            await click(a, 'pbtab', 'group')
            await click(a, 'pbpose', 'khoac_vai')
            await click(c, 'pbprop', 'tai_tho')
            await click(d, 'pbprop', 'non_la')
            check(await poll(d.page, f"({ST}).room.people.every(p=>p.pose==='khoac_vai')&&({ST}).frame==='hoi_dem'", 5), 'four: one pose for all, the frame Hội chợ đêm')
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '09a-four-room-390')
            await pane(a, 'pose')
            await a.page.evaluate("document.querySelector('.fh-sheet .fh-pb-posehead').scrollIntoView({block:'start'})")
            await shot(a, '09b-pose-picker-group-390')
            await pane(c, 'pose')
            await c.page.evaluate("document.querySelector('.fh-sheet .fh-pb-posehead').scrollIntoView({block:'start'})")
            await shot(c, '09c-pose-picker-solo-390')
            await shoot_round(a, [b, c, d], 'hoi_dem', '09d-four', between=((1, a, 'pbpose', 'tim_to'), (2, a, 'pbpose', 'cung_nhay'), (3, b, 'pbdice', None)))
            await save_strip(a, 'four-hoi-dem')
            await click(c, 'pbfilter', 'mo')
            await click(c, 'pbtext', 'vui')
            await click(d, 'pbfilter', 'den_trang')
            await click(d, 'pbdate', '1')
            check(await poll(c.page, f"({ST}).filter==='mo'&&({ST}).url", 6) and await poll(d.page, f"({ST}).filter==='den_trang'&&!({ST}).date&&({ST}).url", 6), "four: each one's colour and words")
            await save_strip(c, 'four-mo-vui')
            await save_strip(d, 'four-den-trang')
            await d.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(d, '09e-four-strip-390')
            # the same on a desktop
            await a.page.set_viewport_size(dict(width=1280, height=900))
            await a.page.wait_for_timeout(500)
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '09f-four-strip-1280')
            await click(a, 'pbagain')
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '09g-four-room-1280')
            await pane(a, 'pose')
            await a.page.evaluate("document.querySelector('.fh-sheet .fh-pb-posehead').scrollIntoView({block:'start'})")
            await shot(a, '09h-pose-picker-1280')
            await a.page.set_viewport_size(dict(width=390, height=844))
            for p in (c, d):
                await click(p, 'pbout')
            check(await poll(a.page, f"({ST}).room?.people?.length===2", 5), 'Thu and Bảo leave')
            await click(b, 'pbout')
            check(await poll(a.page, f"({ST}).room?.people?.length===1", 5), 'B leaves: A sees it')
            await click(a, 'pbout')
            check(await poll(a.page, f"({ST}).step==='lobby'", 3), 'A back in the lobby')

            # ---------------- 2. Người lạ: paired by the live service ----------------
            await click(a, 'pbfind')
            check(await poll(a.page, f"({ST}).step==='wait'", 5), 'A waits for a stranger')
            await shot(a, '09-stranger-wait')
            await click(b, 'pbfind')
            for p in (a, b):
                check(await poll(p.page, f"({ST}).mode==='stranger'&&({ST}).room?.people?.length===2", 8), f'{p.name} paired with a stranger')
            st = await a.page.evaluate(ST)
            host, guest = (a, b) if st['room']['host'] == st['me'] else (b, a)
            check(not (await host.page.evaluate(ST))['room']['code'], 'a stranger room has no code to share')
            await click(host, 'pbframe', 'kawaii')
            await click(host, 'pbbg', 'hong')
            await click(guest, 'pbpose', 'nhay')
            await click(guest, 'pbprop', 'kinh_tim')
            await click(host, 'pbpose', 'nghieng')
            await click(host, 'pbprop', 'mu_tiec')
            await host.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(host, '10-stranger-room')
            await shoot_round(host, [guest], 'kawaii', '11-stranger')
            await save_strip(guest, 'kawaii-stranger')
            await guest.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(guest, '12-stranger-strip')
            for p in (a, b):
                await click(p, 'pbout')

            # ---------------- 3. Một mình ----------------
            await click(a, 'pbsolo')
            # one screen: the booth stays in view while a pose far down the list is tapped, on every size
            for w, h in ((320, 568), (390, 844), (430, 932), (1280, 900)):
                await a.page.set_viewport_size(dict(width=w, height=h))
                await pane(a, 'pose')
                ids = await a.page.evaluate("[...document.querySelectorAll('.fh-sheet [data-fh=pbpose]')].map(b=>b.dataset.v)")
                pid = ids[-1 - (w % 3)]
                await a.page.locator(f'.fh-sheet [data-fh="pbpose"][data-v="{pid}"]').scroll_into_view_if_needed()
                await bring_up(a, f'.fh-sheet [data-fh="pbpose"][data-v="{pid}"]')
                await a.page.click(f'.fh-sheet [data-fh="pbpose"][data-v="{pid}"]')
                ok = await poll(a.page, f"({ST}).pose==='{pid}'", 3)
                await a.page.wait_for_timeout(300)
                box = await a.page.evaluate("(()=>{const r=document.querySelector('.fh-sheet .fh-pb-cv').getBoundingClientRect(),t=document.querySelector('.fh-sheet [data-fh=pbpose].on').getBoundingClientRect(),s=document.querySelector('.fh-sheet .fh-pb-room').getBoundingClientRect();"
                                            "return {top:Math.round(r.top),bot:Math.round(r.bottom),h:innerHeight,tile:[Math.round(t.top),Math.round(t.bottom)],over:document.querySelector('.fh-sheet').scrollWidth-document.querySelector('.fh-sheet').clientWidth}})()")
                check(ok and box['top'] >= 0 and box['bot'] <= box['h'], f'{w}×{h}: a pose far down the list ({pid}), the booth shows it without scrolling ({box})')
                check(box['tile'][0] >= box['bot'] - 2 or w >= 700, f'{w}×{h}: the tapped pose is not under the booth ({box})')
                check(box['tile'][1] <= box['h'] + 1, f'{w}×{h}: the tapped pose is on screen ({box})')
                check(box['over'] <= 1, f'{w}×{h}: nothing wider than the sheet ({box["over"]}px)')
                await a.page.screenshot(path=str(shots / f'L-{w}-pose.png'))
                await pane(a, 'frame')
                await a.page.wait_for_timeout(250)
                await a.page.screenshot(path=str(shots / f'L-{w}-frame.png'))
            await a.page.set_viewport_size(dict(width=390, height=844))
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await click(a, 'pbframe', 'retro')
            await click(a, 'pbbg', 'den')
            await click(a, 'pbpose', 'vay')
            await click(a, 'pbprop', 'kinh_ram')
            w0 = await a.page.evaluate(WALLET)
            await click(a, 'pbshoot')
            check(await poll(a.page, f"({ST}).step==='print'&&({ST}).url", 25), 'solo: the strip')
            check(await a.page.evaluate(WALLET) == w0 - 5, 'solo: paid 5 xu')
            await save_strip(a, 'retro-solo')
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '13-solo-strip')
            async with a.page.expect_download(timeout=8000) as dl:
                await a.page.evaluate("matchMedia=()=>({matches:false})")   # the desktop path: a download
                await click(a, 'pbsave')
            d = await dl.value
            check(d.suggested_filename.endswith('.png'), f'the strip downloads as a PNG ({d.suggested_filename})')
            for frame, bg, filt, text, tag in (('tet_vui', 'hoa_dao', 'am', 'hoi', 'tet-solo'), ('sticker', 'pastel', 'trong', 'none', 'sticker-solo')):
                await click(a, 'pbagain')
                await click(a, 'pbframe', frame)
                await click(a, 'pbbg', bg)
                await click(a, 'pbprop', 'none')
                await click(a, 'pbdice')
                await click(a, 'pbshoot')
                await a.page.wait_for_timeout(2300)
                await a.page.evaluate("document.querySelector('.fh-sheet .fh-pb-booth')?.scrollIntoView({block:'center'})")
                await a.page.screenshot(path=str(shots / f'13b-solo-countdown-{tag}.png'))
                for n in (1, 2, 3):
                    await poll(a.page, f"({ST}).shots>={n}", 8)
                    await click(a, 'pbdice')
                check(await poll(a.page, f"({ST}).step==='print'&&({ST}).url", 25), f'solo: the strip in {frame}')
                await click(a, 'pbfilter', filt)
                await click(a, 'pbtext', text)
                await poll(a.page, f"({ST}).filter==='{filt}'&&({ST}).url", 6)
                await save_strip(a, tag)
            await a.page.set_viewport_size(dict(width=1280, height=900))
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '13c-solo-strip-1280')
            await a.page.set_viewport_size(dict(width=390, height=844))

            # ---------------- 4. widths and the dark theme ----------------
            await click(a, 'pbagain')
            for w in (320, 430):
                await a.page.set_viewport_size(dict(width=w, height=844))
                await a.page.wait_for_timeout(400)
                await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
                await shot(a, f'14-solo-room-{w}')
                over = await a.page.evaluate("document.querySelector('.fh-sheet .fh-body').scrollWidth-document.querySelector('.fh-sheet .fh-body').clientWidth")
                wide = '' if over <= 1 else await a.page.evaluate("""(()=>{const b=document.querySelector('.fh-sheet .fh-body').getBoundingClientRect();
                  return [...document.querySelectorAll('.fh-sheet .fh-body *')].filter(e=>e.getBoundingClientRect().right>b.right+.5).slice(0,6).map(e=>e.className+':'+Math.round(e.getBoundingClientRect().right-b.right)).join(', ');})()""")
                check(over <= 1, f'{w}px: no sideways scroll ({over}) {wide}')
            await a.page.set_viewport_size(dict(width=390, height=844))
            await click(a, 'pbout')
            await a.page.evaluate("document.documentElement.dataset.theme='dem'")
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '15-lobby-dem')
            small = await a.page.evaluate("""[...document.querySelectorAll('.fh-sheet .fh-pb button,.fh-sheet .fh-pb input')].filter(e=>e.offsetParent)
                .map(e=>[e.dataset.fh||e.className,e.getBoundingClientRect().height]).filter(([,h])=>h<43.5)""")
            check(not small, f'touch targets ≥ 44 px ({small})')
            await click(a, 'pbsolo')
            await a.page.evaluate("document.querySelector('.fh-sheet').scrollTop=0")
            await shot(a, '16-solo-room-dem')
            await browser.close()
    print('\n'.join(checks))
    return problems


def main() -> int:
    from browser_fair import vn_today
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default=str(ROOT.parent / '_fair_booth_shots'))
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
