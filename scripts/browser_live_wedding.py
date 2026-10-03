#!/usr/bin/env python3
"""💍 A live wedding in five browsers: the couple and three guests (dev tool, needs `pip install playwright websockets`).

Starts a game server (story mode, SQLite) and the live service (chat, street, wedding on) on the same database. Here a
paid minute is 10 s (the party 100 s), at most 4 avatars are visible (so the third guest watches from the gate) and
the schedule is read every 2 s; everything else is as in production. MNL_PY picks the servers' Python (the live
service needs websockets 17, Python 3.12) when playwright lives in another one. Five phones (390×844):
  * the couple get 400 xu each through the game's own gift path, become friends, get engaged, and plan the wedding
    in the Hôn nhân planner (a real date and time); the partner confirms; both cards say "Cưới lúc …";
  * the party is moved to "now" in the test database; everyone opens Khu phố › Lịch cưới and walks in: the couple
    stand on the stage ("💍 Cô dâu", "💍 Chú rể"), two guests with accounts come in through the flower gate, the
    third has no account and watches from outside the gate ("Tạo tài khoản để vào dự"), never counted;
  * a guest cheers in a bubble (a phone number masked) and sends ❤️; a guest takes the group photo (3-2-1, flash),
    which lands in the couple's Kỷ niệm; the ceremony starts (hearts), the show runs (MC, neighbours, kids, the lion
    dance, lights); everyone present earns +20 xu a minute, the couple too;
  * 🎁 a guest with an account gets the admin's 500 xu once on walking in; 🧧 they give the couple four envelopes,
    650 xu (no cap; the panel stays open), all on the board; an amount the wallet cannot cover is off;
  * 1.3.0: the couple's name tags stand out (gold and rose); the speakers and the stage lights; a guest taps a table:
    the mâm cỗ opens, three dishes give +1 tinh thần each and the fourth nothing (fixed ids), a beer −1 and "Dzô! 🍻"
    for the room, a soft drink nothing; a guest walks onto the stage and dances (💃); the new lion bites the lì xì; the
    MC's bouquet toss: the bride presses "💐 Tung hoa", it flies to a guest present who gets 20 xu (once); fireworks;
    the recorded wedding music is fetched (/music/wedding-*.mp3);
  * the party ends: everyone sees the end card, the couple get the private card with 15 xu a guest, guests appear on
    Xếp hạng › Khách mời; dark theme;
  * two guests marry with an older plan (no date and time): Hôn nhân offers "Tổ chức tiệc cưới", they pick a time
    and invite their friends for free. Fails on console errors, page errors or HTTP 5xx.

  python scripts/browser_live_wedding.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT))
from browser_live_chat import PW, free_port, phone, wait_http  # noqa: E402

LIVE_DEV = """
import sys
import game.wedding_live as WL
import live.wedding as w
WL.MINUTE_SECS = 10
WL.PARTY_SECS = 100
WL.PARTY_MINUTES = 10
WL.VISIBLE = 4
WL.TOSS_AT = 84
WL.TOSS_WAIT = 8
w.REFRESH = 2.0
w.CLOSE_AFTER = 90.0
from live.app import main
main(sys.argv[1:])
"""
STATE = "async () => (await import('/js/v4/walk.js')).walk.state()"


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.sqlite3')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    py = os.environ.get('MNL_PY') or sys.executable
    if os.environ.get('MNL_PYTHONPATH'):   # the servers' own library path (e.g. a vendored websockets for MNL_PY)
        env['PYTHONPATH'] = os.environ['MNL_PYTHONPATH']
    game = subprocess.Popen([py, 'server.py', '--port', str(gp), '--db', db], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, LIVE_CHAT='1', LIVE_STREET='1', LIVE_WEDDING='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([py, '-c', LIVE_DEV, '--db', db], cwd=ROOT, env=lenv, stdout=log, stderr=log)
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


async def until(p, js_cond: str, what: str, timeout=10.0):
    end = time.monotonic() + timeout
    while True:
        s = await state(p)
        if await p.page.evaluate(f's => {{ {js_cond} }}', s):
            return s
        if time.monotonic() > end:
            raise AssertionError(f'{p.name}: {what} (state: {json.dumps(s, ensure_ascii=False)[:500]})')
        await asyncio.sleep(0.2)


async def tap_world(p, x, y):
    """Tap the party's canvas at world (x, y) (the 600 × 900 scene)."""
    pt = await p.page.evaluate("""async ([x, y]) => {const {walk} = await import('/js/v4/walk.js'); const v = walk.state().view;
        const b = document.querySelector('.walk-sheet .wk-canvas').getBoundingClientRect(); return [b.left + v.ox + x * v.k, b.top + v.oy + y * v.k];}""", [x, y])
    await p.page.mouse.click(pt[0], pt[1])


async def hub(p, action, group='pho'):
    """Open an entry of a menu hub (Khu phố, Quan hệ, Của mình…; the "Thêm" sheet on a phone)."""
    await p.page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
    await p.page.wait_for_selector(f'#rail .rail-group[data-group={group}]', timeout=15000)
    await p.page.evaluate(f"document.querySelector('#rail .rail-group[data-group={group}]').click()")   # the rail may be
    await p.page.wait_for_timeout(300)                                                                  # off-screen on a phone
    await p.page.evaluate(f"document.querySelector('#rail .rail-sub[data-group={group}] [data-action={action}]').click()")


async def cards(p, first=6.0):
    """Press "Nhận quà" on every gift card that shows (each waits for the game to be calm)."""
    wait = first
    while True:
        try:
            await p.page.wait_for_selector('#gfDialog[open] [data-gf=ok]', timeout=wait * 1000)
        except Exception:  # noqa: BLE001 - no (more) card
            return
        await p.page.wait_for_timeout(700)    # a tap right after the card pops up is ignored on purpose
        await p.page.click('#gfDialog[open] [data-gf=ok]')
        await p.page.wait_for_timeout(500)
        wait = 2.5


async def phone_as(browser, base, name, problems, gender):
    """A phone through the intro with this gender (browser_live_chat.phone picks female)."""
    p = await phone(browser, base, name, problems, intro=False)
    await p.page.click(f'[data-action=jrGender][data-gender={gender}]', timeout=10000)
    await p.page.fill('#jr-name', name)
    await p.page.click('form[data-jr-form=start] button[type=submit]')
    await p.page.wait_for_timeout(2500)
    for _ in range(8):
        if not await p.page.evaluate("!!document.querySelector('#sheet[open],#confirmDialog[open]')"):
            break
        await p.page.keyboard.press('Escape')
        await p.page.wait_for_timeout(500)
    return p


def sql(db, q, *args):
    with sqlite3.connect(db) as con:
        return con.execute(q, args).fetchall()


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    from game import system_gift
    from game.storage import Store
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        print(checks[-1], flush=True)   # as it goes: a later timeout still shows what passed
        if not cond:
            problems.append('check: ' + what)

    async def dom(p, selector, timeout=15):
        """The text of an element once it is there (polled: the game's CSP forbids wait_for_function)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            text = await p.page.evaluate('(q) => document.querySelector(q)?.innerText || ""', selector)
            if text:
                return text
            await asyncio.sleep(0.2)
        return ''

    async def shot(p, name, wait=450):
        await p.page.wait_for_timeout(wait)
        await p.page.screenshot(path=str(shots / f'{name}.png'))

    with tempfile.TemporaryDirectory(prefix='mnl-wed-', dir=os.environ.get('TMPDIR')) as tmp, servers(tmp) as (base, db, live_log):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            bride = await phone(browser, base, 'Lan Anh', problems)
            groom = await phone_as(browser, base, 'Minh Tú', problems, 'male')
            guests = [await phone_as(browser, base, n, problems, g) for n, g in (('Hà Vy', 'female'), ('Bảo', 'male'), ('Khánh', 'male'))]
            await bride.api('/api/account/register', dict(username='lananh_w', password=PW, confirm=PW, display='Lan Anh'))
            await groom.api('/api/account/register', dict(username='minhtu_w', password=PW, confirm=PW, display='Minh Tú'))
            for p, user in ((guests[0], 'havy_w'), (guests[1], 'bao_w')):   # Khánh stays a guest without an account
                await p.api('/api/account/register', dict(username=user, password=PW, confirm=PW, display=p.name))
            await bride.api('/api/marriage/friend_request', dict(username='minhtu_w'))
            rid = (await groom.api('/api/marriage'))['friends']['incoming'][0]['id']
            await groom.api('/api/marriage/friend_respond', dict(id=rid, answer='accept'))
            sql(db, "UPDATE stat_births SET day='2026-01-01'")          # long-time players: counted guests
            store = Store(db, story=True)
            for p, name in ((bride, 'lananh_w'), (groom, 'minhtu_w'), (guests[0], 'havy_w'), (guests[1], 'bao_w')):   # pocket money (the game's gift path)
                sid = sql(db, 'SELECT sid FROM accounts WHERE username=?', name)[0][0]
                system_gift.grant(store, sid, 400, 'Quà cưới thử', 'Tiền để cưới (thử nghiệm).', f'wedtest-{name}')
                # a couple who has lived in the phố a while (test database only): past a new player's quiet first day
                sql(db, "UPDATE sessions SET state=json_set(state, '$.journey.life_day', 3) WHERE sid=?", sid)
            store.close_pool()
            for p in [bride, groom, *guests]:
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
            for p in (bride, groom, guests[0], guests[1]):   # their pocket money arrives as the private gift card: "Nhận quà"
                await cards(p)
            # ---- engaged, then the planner with a real date and time
            await bride.api('/api/marriage/ring_buy', dict(tier='bac'))
            ring = [r for r in (await bride.api('/api/marriage'))['rings'] if r['status'] == 'owned'][0]['id']
            code = (await groom.api('/api/marriage'))['me']['code']
            await bride.api('/api/marriage/propose', dict(code=code, ring=ring, message='hem', announce=True))
            pid = (await groom.api('/api/marriage'))['incoming'][0]['id']
            await groom.api('/api/marriage/respond', dict(id=pid, answer='accept', announce=True))
            await hub(bride, 'marriage', 'ban')
            await bride.page.wait_for_selector('[data-tab=plan]', timeout=10000)
            await bride.page.click('[data-tab=plan]')
            await bride.page.wait_for_selector('[data-mr-field=at_date]', timeout=10000)
            await bride.page.evaluate("document.querySelector('[data-mr-field=at_date]').scrollIntoView({block:'center'})")
            await shot(bride, '01-planner-date-time')
            at = int(time.time()) + 2 * 3600
            plan = dict(venue='home', tables=5, menu='binh_dan', ceremonies={}, extras=[], days=3, at=at)
            await bride.api('/api/marriage/plan', dict(plan=plan, mine=50, announce=True))
            w = (await groom.api('/api/marriage'))['wedding']
            await groom.api('/api/marriage/confirm', dict(id=w['id'], version=w['version'], announce=True))
            view = await bride.api('/api/marriage')
            check(view['wedding']['at_label'] and view['couple']['wed_label'].startswith('💍 Cưới ngày'), f"booked: {view['couple']['wed_label']}")
            await bride.page.keyboard.press('Escape')
            await bride.page.wait_for_timeout(400)
            await hub(bride, 'marriage', 'ban')
            await bride.page.wait_for_selector('[data-tab=home]', timeout=10000)
            await bride.page.click('[data-tab=home]')
            await bride.page.wait_for_selector('.mr-countdown', timeout=10000)
            await shot(bride, '02-booked-card')
            await bride.page.click('[data-mr=pinvite]')
            await bride.page.wait_for_selector('.mr-flash', timeout=10000)
            flash = await bride.page.inner_text('.mr-flash')
            check('Miễn phí' in flash or 'mời' in flash, f'"Mời khách" is free ({flash!r})')
            check(bool(sql(db, "SELECT 1 FROM news WHERE kind='invite'")), 'the phố gets the invitation on the news line')
            await shot(bride, '02b-invited')
            await bride.page.keyboard.press('Escape')
            # ---- the party is now (test database only): opens at once, starts in ~70 s
            wid = w['id']
            start = time.time() + 70
            sql(db, 'UPDATE wedding_parties SET at=? WHERE wedding=?', start, wid)
            await asyncio.sleep(2.5)
            g1, g2, g3 = guests
            await hub(g1, 'liveWed')
            await g1.page.wait_for_selector('.wd-sheet[open] [data-wd=go]', timeout=15000)
            await shot(g1, '03-wedding-list')
            check(True, 'Lịch cưới lists the party with "Vào dự"')
            order = [bride, groom, g1, g2, g3]
            for p in order:
                if p is not g1:
                    await hub(p, 'liveWed')
                    await p.page.wait_for_selector('.wd-sheet[open] [data-wd=go]', timeout=15000)
                await p.page.click('.wd-sheet[open] [data-wd=go]')
                await p.page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=10000)
                await until(p, "return s.room&&s.room.startsWith('wed:');", 'in the party room')
            s = await until(g1, 'return s.people.length===4;', 'four visible')
            titles = sorted(q['name'] for q in s['people'])
            check(titles == sorted(['Lan Anh', 'Minh Tú', 'Hà Vy', 'Bảo']), f'the couple and two guests visible ({titles})')
            await shot(g1, '04a-couple-name-tags')
            banner = await g3.page.inner_text('.walk-sheet .wk-banner')
            check('Tạo tài khoản' in banner, f'a player without an account watches from the gate ({banner!r})')
            await shot(g3, '05-overflow-watcher')
            # ---- cheers, a heart, the group photo
            await g1.page.fill('.walk-sheet .wk-say input', 'Chúc mừng hạnh phúc! Trăm năm hạnh phúc nha 🎉 0912345678')
            await g1.page.click('.walk-sheet .wk-send')
            s = await until(bride, "return s.people.some(q=>q.said);", 'the bride sees the cheer')
            said = next(q['said'] for q in s['people'] if q['said'])
            check('hạnh phúc' in said and '0912' not in said, f'a bubble, phone masked ({said!r})')
            board = await dom(bride, '.walk-sheet .wk-wishes:not([hidden])')
            check('hạnh phúc' in board, f'the cheer stays on the "Lời chúc" board ({board!r})')
            await g2.page.click('.walk-sheet [data-wk=emotes]')
            await g2.page.click('.walk-sheet [data-wk=emote][data-e=heart]')
            await until(groom, "return s.people.some(q=>q.emote==='❤️');", 'the groom sees ❤️')
            await shot(bride, '04-party-bubble-heart')
            await g1.page.click('.walk-sheet [data-wk=photo]')
            await g1.page.wait_for_timeout(1200)
            await shot(groom, '06-photo-countdown', wait=0)
            end = time.monotonic() + 12
            while time.monotonic() < end and not sql(db, 'SELECT 1 FROM wedding_photos WHERE image IS NOT NULL'):
                await asyncio.sleep(0.3)
            check(bool(sql(db, 'SELECT 1 FROM wedding_photos WHERE image IS NOT NULL')), 'the group photo is uploaded for the couple')
            # ---- the ceremony starts, guests earn their steps
            end = time.monotonic() + 80    # (no wait_for_function: the game's CSP forbids eval)
            while time.monotonic() < end and 'Lễ cưới' not in (await bride.page.evaluate("() => document.querySelector('.walk-sheet .wk-toast:not([hidden])')?.innerText || ''")):
                await asyncio.sleep(0.2)
            await shot(g2, '07-ceremony-starts', wait=300)
            recorded = sql(db, 'SELECT COUNT(*), SUM(ok) FROM wedding_guests WHERE wedding=?', wid)[0]
            check(recorded == (3, 2), f'every guest recorded on entry, the watcher without an account not counted ({recorded})')
            rows = []
            end = time.monotonic() + 30
            while time.monotonic() < end and len({r[0] for r in rows}) < 4:
                rows = sql(db, "SELECT sid FROM live_effects WHERE id LIKE 'wedm:%'")
                await asyncio.sleep(0.5)
            check(len({r[0] for r in rows}) == 4, f'the couple and the two guests with accounts earn +20 xu a minute ({len(rows)} rows), the watcher nothing')
            await shot(g1, '08-guest-xu', wait=900)
            await g2.page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot(g2, '08a-speakers-lights-dark', wait=600)
            await g2.page.evaluate("document.documentElement.dataset.theme='kem'")
            got = await g2.page.evaluate("performance.getEntriesByType('resource').map(e => e.name).filter(n => n.includes('/music/wedding-'))")
            check(bool(got), f'the recorded wedding music is fetched ({[g.rsplit("/", 1)[1] for g in got]})')
            # ---- 🧧 a red envelope for the couple, on everyone's wishes board
            check(not await bride.page.query_selector('.walk-sheet [data-wk=env]'), 'the couple do not give themselves an envelope')
            await g1.page.click('.walk-sheet [data-wk=env]')
            await g1.page.click('.walk-sheet [data-wk=envAmt][data-n="50"]')
            await g1.page.click('.walk-sheet [data-wk=envWish][data-n="1"]')
            await shot(g1, '08c-envelope-picker')
            await g1.page.click('.walk-sheet [data-wk=envSend]')
            env = await dom(bride, '.walk-sheet .wk-wish.env')
            check('50 xu' in env and 'Bách niên' in env, f'the room sees the envelope and the wish ({env!r})')
            halves = sql(db, "SELECT amount FROM live_effects WHERE id LIKE 'wedenv:%'")
            check(halves == [(25,), (25,)], f'the couple get half each ({halves})')
            await shot(bride, '08d-envelope-board', wait=600)
            # 🎁 the admin's 500 xu, paid once when a guest walked in; no cap, "cho gửi thoải mái": the panel stays open
            hist = (await g1.api('/api/state'))['state']['journey']
            gifts = [h for h in hist['history'] if 'Quà từ admin' in h['label']]
            check(hist['wed_gift'] is True and len(gifts) == 1 and gifts[0]['amount'] == 500, f'the admin gift once ({gifts})')
            await g1.page.click('.walk-sheet [data-wk=envAmt][data-n="200"]')
            for i in range(3):                       # 50 + 3 × 200 = 650: past the old 500 a wedding
                await g1.page.wait_for_selector('.walk-sheet [data-wk=envSend]:not([disabled])', timeout=10000)
                await g1.page.click('.walk-sheet [data-wk=envSend]')
                for _ in range(250):                 # SQLite shared with the live service: a write may wait a while
                    if len(sql(db, "SELECT 1 FROM marriage_effects WHERE id LIKE 'wenv:%'")) >= 2 + i:
                        break
                    await asyncio.sleep(0.1)
                else:
                    check(False, f"envelope {i + 2} sent ({await dom(g1, '.walk-sheet .wk-toast', 1)!r})")
            for _ in range(100):                     # the cheer and the four envelopes
                if await dom(bride, '.walk-sheet .wk-wish-head small') == '5':
                    break
                await asyncio.sleep(0.2)
            paid = sql(db, "SELECT amount FROM marriage_effects WHERE id LIKE 'wenv:%' ORDER BY at")
            check(paid[:4] == [(-50,), (-200,), (-200,), (-200,)], f"four envelopes, 650 xu at one wedding ({paid})")
            board = await dom(bride, '.walk-sheet .wk-wish-head small')
            check(board == '5', f'every envelope on the board ({board!r})')
            await shot(g1, '08f-envelope-after-four')
            offs = []
            for _ in range(12):                                                               # 200 more until the wallet runs thin
                await asyncio.sleep(0.6)
                offs = await g1.page.evaluate("[...document.querySelectorAll('.walk-sheet [data-wk=envAmt]')].map(b => b.disabled)")
                if offs[-1]:
                    break
                await g1.page.click('.walk-sheet [data-wk=envSend]')
            cash = (await g1.api('/api/state'))['state']['journey']['wallet']
            why = await dom(g1, '.walk-sheet .wk-env-why')
            off = await g1.page.evaluate("document.querySelector('.walk-sheet [data-wk=envSend]').disabled")
            check(offs == [n > cash for n in (10, 20, 50, 100, 200)] and off and 'chưa đủ phong bì 200 xu' in why,
                  f'an amount the wallet cannot cover is off, with the reason ({cash}: {offs}, {off}, {why!r})')
            await shot(g1, '08g-envelope-thin-wallet')
            await g1.page.click('.walk-sheet [data-wk=env]')
            await bride.page.click('.walk-sheet .wk-wish-head')
            await shot(bride, '08e-wishes-open')
            await bride.page.click('.walk-sheet .wk-wish-head')
            # ---- 🍽️ the mâm cỗ: three dishes count, the fourth does not; a beer; a soft drink
            await tap_world(g1, 125, 470)
            await g1.page.wait_for_selector('.walk-sheet .wk-tray:not([hidden]) .wk-dish', timeout=10000)
            await shot(g1, '16-table-tray')
            for d in (0, 1, 2, 3):
                await g1.page.click(f'.walk-sheet .wk-tray [data-k=dish][data-d="{d}"]')
                await g1.page.wait_for_timeout(450)
            await g1.page.click('.walk-sheet .wk-tray [data-k=beer]')
            await until(bride, "return s.people.some(q=>q.emote==='🍻');", 'the bride sees "Dzô! 🍻"')
            await shot(bride, '17-cheers-seen-by-bride', wait=350)
            await g1.page.wait_for_timeout(450)
            await g1.page.click('.walk-sheet .wk-tray [data-k=soda]')
            await g1.page.wait_for_timeout(700)
            await shot(g1, '17b-tray-after', wait=0)
            eats = sql(db, "SELECT id, amount FROM live_effects WHERE id LIKE 'weat:%' OR id LIKE 'wbeer:%' ORDER BY id")
            check([a for _, a in eats] == [-1, 1, 1, 1], f'3 dishes +1 each, the 4th nothing; a beer −1 ({eats})')
            await g1.page.click('.walk-sheet .wk-tray [data-wk=tray]')
            # ---- 💃 the stage: Bảo walks up and dances
            await g2.page.evaluate("async () => (await import('/js/v4/walk.js')).walk.moveTo(395, 296)")
            await g2.page.wait_for_selector('.walk-sheet .wk-float:not([hidden]) [data-wk=dance]', timeout=10000)
            off = await g1.page.evaluate("document.querySelector('.walk-sheet .wk-float').hidden")
            if not off:
                print('   g1 me:', await g1.page.evaluate("async () => {const st = (await import('/js/v4/walk.js')).walk.state(); return JSON.stringify(st.people.find(q => q.pid === st.me))}"))
            check(off, 'the dance button only for whoever stands on the stage')
            await g2.page.click('.walk-sheet .wk-float [data-wk=dance]')
            await until(g1, "return s.people.some(q=>q.emote==='💃');", 'the room sees 💃')
            await shot(g2, '18-stage-dance', wait=300)
            # ---- 🎧 the groom picks the music; the room hears it from that moment (the MC says so)
            check(await bride.page.query_selector('.walk-sheet .wk-dj-btn') is None, 'the groom is here: only he has 🎧')
            await groom.page.click('.walk-sheet [data-wk=dj]')
            await groom.page.wait_for_selector('.walk-sheet .wk-dj:not([hidden]) .wk-dj-song', timeout=10000)
            await shot(groom, '23-dj-picker', wait=200)
            await groom.page.click('.walk-sheet .wk-dj [data-wk=djPick][data-k=edm]')
            for _ in range(50):
                if await g1.page.evaluate("async () => (await import('/js/v4/wedfeast.js')).picked()") == 'edm':
                    break
                await asyncio.sleep(0.2)
            got = await g1.page.evaluate("async () => (await import('/js/v4/wedfeast.js')).picked()")
            check(got == 'edm', f'every guest switches to the groom\'s song ({got})')
            await shot(g2, '24-music-changed', wait=600)
            await g2.page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot(g2, '24b-music-changed-dark', wait=400)
            await g2.page.evaluate("document.documentElement.dataset.theme='kem'")
            lion = start + 58 - time.time()
            if lion > 0:
                await asyncio.sleep(lion)
            await shot(g2, '08b-lion-dance-kids', wait=0)
            await g1.page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot(g1, '09-party-dark')
            await g1.page.evaluate("document.documentElement.dataset.theme='kem'")
            bite = start + 77.6 - time.time()        # the lion window 40-110: it bites the lì xì at 78.5
            if bite > 0:
                await asyncio.sleep(bite)
            await shot(g2, '08f-lion-bites-li-xi', wait=0)
            # ---- 💐 the bouquet (TOSS_AT 84 here): the bride throws it, a guest present catches it; fireworks (last 25 s)
            await bride.page.wait_for_selector('.walk-sheet .wk-float:not([hidden]) [data-wk=toss]', timeout=30000)
            await shot(bride, '19-toss-button', wait=200)
            await bride.page.click('.walk-sheet .wk-float [data-wk=toss]', force=True)   # it glows (an endless animation)
            await g1.page.wait_for_timeout(450)
            await shot(g1, '20-bouquet-flying', wait=0)
            caught = sql(db, "SELECT s.display, e.amount FROM live_effects e JOIN accounts s ON s.sid=e.sid WHERE e.id LIKE 'wtoss:%'")
            check(len(caught) == 1 and caught[0][0] in ('Hà Vy', 'Bảo') and caught[0][1] == 20, f'one guest present catches the bouquet, 20 xu ({caught})')
            catcher, other = (g1, g2) if caught and caught[0][0] == 'Hà Vy' else (g2, g1)
            told = {}
            for _ in range(60):   # the toast comes when the bouquet lands (1.7 s), on every phone
                for p in (catcher, other):
                    if p.name not in told:
                        t = await p.page.evaluate("(() => {const e = document.querySelector('.walk-sheet .wk-toast'); return e && !e.hidden ? e.textContent : ''})()")
                        if 'bắt được hoa cưới' in t or 'rơi xuống sàn' in t:
                            told[p.name] = t
                            if p is catcher:
                                await shot(catcher, '21-bouquet-caught', wait=0)
                if len(told) == 2:
                    break
                await asyncio.sleep(0.1)
            check(told.get(catcher.name, '').startswith('💐 Bạn bắt được hoa cưới! +20 xu') and caught[0][0] in told.get(other.name, ''),
                  f'the catcher and the room are told ({told})')
            fw = start + 90 - time.time()
            if fw > 0:
                await asyncio.sleep(fw)
            await shot(g2, '22-fireworks', wait=0)
            await g2.page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot(g2, '22b-fireworks-dark', wait=600)
            await g2.page.evaluate("document.documentElement.dataset.theme='kem'")
            # ---- the end: the couple's total, the end card
            sql(db, 'UPDATE wedding_parties SET at=? WHERE wedding=?', time.time() - 100 + 4, wid)
            await bride.page.wait_for_selector('.walk-sheet .wk-end:not([hidden])', timeout=20000)
            await g2.page.wait_for_selector('.walk-sheet .wk-end:not([hidden])', timeout=20000)
            await shot(g2, '10-party-end')
            await bride.page.wait_for_selector('#gfDialog[open] [data-gf=ok]', timeout=20000)
            card = await bride.page.inner_text('#gfTitle')
            check('Đám cưới' in card, f'the private card for the couple ({card!r})')
            await shot(bride, '11-couple-card')
            party = sql(db, 'SELECT status, guests FROM wedding_parties WHERE wedding=?', wid)
            check(party == [('done', 2)], f'settled once with 2 counted guests ({party})')
            host = sql(db, "SELECT amount FROM live_effects WHERE id LIKE 'wedhost:%' AND kind='coins'")
            check(host == [(30,), (30,)], f'each spouse 2 × 15 xu ({host})')
            await cards(bride, 2.0)
            await bride.page.keyboard.press('Escape')
            await bride.page.wait_for_timeout(500)
            # ---- Kỷ niệm: the photo; Xếp hạng: Khách mời của tuần
            await hub(bride, 'album', 'minh')
            await bride.page.wait_for_selector('[data-wed-album] img', timeout=10000)
            await bride.page.evaluate("document.querySelector('[data-wed-album]').scrollIntoView({block:'center'})")
            await shot(bride, '12-album-wedding-photo')
            check(True, 'the photo is in the couple\'s Kỷ niệm')
            await g1.page.keyboard.press('Escape')
            await hub(g1, 'rank')
            await g1.page.wait_for_selector('[data-action=lbKind][data-kind=wed]', timeout=10000)
            await g1.page.click('[data-action=lbKind][data-kind=wed]')
            await g1.page.wait_for_selector('.lb-list .lb-row', timeout=10000)
            top = await g1.page.inner_text('.lb-list')
            check('Hà Vy' in top and 'Bảo' in top and top.count('đám cưới') == 2, f'Xếp hạng › Khách mời: the two counted guests ({top!r})')
            await shot(g1, '13-race-board')
            # ---- an older wedding without a date and time: "Tổ chức tiệc cưới", free
            await g1.page.keyboard.press('Escape')
            await g1.api('/api/marriage/friend_request', dict(username='bao_w'))
            rid = (await g2.api('/api/marriage'))['friends']['incoming'][0]['id']
            await g2.api('/api/marriage/friend_respond', dict(id=rid, answer='accept'))
            await g1.api('/api/marriage/ring_buy', dict(tier='bac'))
            ring = [r for r in (await g1.api('/api/marriage'))['rings'] if r['status'] == 'owned'][0]['id']
            code = (await g2.api('/api/marriage'))['me']['code']
            await g1.api('/api/marriage/propose', dict(code=code, ring=ring, message='hem', announce=True))
            pid = (await g2.api('/api/marriage'))['incoming'][0]['id']
            await g2.api('/api/marriage/respond', dict(id=pid, answer='accept', announce=True))
            plan = dict(venue='home', tables=5, menu='binh_dan', ceremonies={}, extras=['cards'], days=3)   # no `at`: an older client
            await g1.api('/api/marriage/plan', dict(plan=plan, mine=50, announce=True))
            w2 = (await g2.api('/api/marriage'))['wedding']
            await g2.api('/api/marriage/confirm', dict(id=w2['id'], version=w2['version'], announce=True))
            await g1.page.wait_for_timeout(600)
            await hub(g1, 'marriage', 'ban')
            await g1.page.wait_for_selector('[data-mr=party]', timeout=10000)
            await g1.page.evaluate("document.querySelector('[data-mr=party]').scrollIntoView({block:'center'})")
            await shot(g1, '14-party-pick-time')
            await g1.page.click('[data-mr=party]')
            await g1.page.wait_for_selector('[data-mr=pinvite]', timeout=10000)
            await shot(g1, '15-party-booked')
            party2 = sql(db, "SELECT status FROM wedding_parties WHERE wedding=?", w2['id'])
            check(party2 == [('booked',)], f'an older wedding books its party for free ({party2})')
            await browser.close()
        print(Path(live_log).read_text()[-800:], file=sys.stderr)
    for line in checks:
        print(line)
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path, default=Path(tempfile.gettempdir()) / 'mnl-wedding-shots')
    args = ap.parse_args()
    args.shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(args.shots))
    print(json.dumps(dict(ok=not problems, problems=problems, shots=str(args.shots)), ensure_ascii=False, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
