#!/usr/bin/env python3
"""💍 A live wedding in five browsers: the couple and three guests (dev tool, needs `pip install playwright websockets`).

Starts a game server (story mode, SQLite) and the live service (chat, street, wedding on) on the same database. Here a
5-minute step is 15 s, at most 4 avatars are visible (so the third guest watches from the gate) and the schedule is
read every 2 s; everything else is as in production. Five phones (390×844):
  * the couple get 400 xu each through the game's own gift path, become friends, get engaged, and plan the wedding
    in the Hôn nhân planner (a real date and time); the partner confirms; both cards say "Cưới lúc …";
  * the party is moved to "now" in the test database; everyone opens Khu phố › Lịch cưới and walks in: the couple
    stand on the stage ("💍 Cô dâu", "💍 Chú rể"), two guests with accounts come in through the flower gate, the
    third has no account and watches from outside the gate ("Tạo tài khoản để vào dự"), never counted;
  * a guest cheers in a bubble (a phone number masked) and sends ❤️; a guest takes the group photo (3-2-1, flash),
    which lands in the couple's Kỷ niệm; the ceremony starts (hearts); every guest earns +15 xu per step;
  * the party ends: everyone sees the end card, the couple get the private card with their total, guests appear on
    Xếp hạng › Khách mời; dark theme. Fails on console errors, page errors or HTTP 5xx.

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
WL.GUEST_STEP = 15
WL.VISIBLE = 4
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
    game = subprocess.Popen([sys.executable, 'server.py', '--port', str(gp), '--db', db], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, LIVE_CHAT='1', LIVE_STREET='1', LIVE_WEDDING='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([sys.executable, '-c', LIVE_DEV, '--db', db], cwd=ROOT, env=lenv, stdout=log, stderr=log)
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


async def hub(p, action, group='pho'):
    """Open an entry of a menu hub (Khu phố, Quan hệ, Của mình…; the "Thêm" sheet on a phone)."""
    await p.page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
    await p.page.wait_for_selector(f'#rail .rail-group[data-group={group}]', timeout=15000)
    await p.page.click(f'#rail .rail-group[data-group={group}]')
    await p.page.click(f'#rail .rail-sub[data-group={group}] [data-action={action}]')


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
        if not cond:
            problems.append('check: ' + what)

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
            for p, name in ((bride, 'lananh_w'), (groom, 'minhtu_w')):    # pocket money through the game's own gift path
                sid = sql(db, 'SELECT sid FROM accounts WHERE username=?', name)[0][0]
                system_gift.grant(store, sid, 400, 'Quà cưới thử', 'Tiền để cưới (thử nghiệm).', f'wedtest-{name}')
                # a couple who has lived in the phố a while (test database only): past a new player's quiet first day
                sql(db, "UPDATE sessions SET state=json_set(state, '$.journey.life_day', 3) WHERE sid=?", sid)
            store.close_pool()
            for p in [bride, groom, *guests]:
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
            for p in (bride, groom):   # their pocket money arrives as the private gift card: "Nhận quà"
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
            banner = await g3.page.inner_text('.walk-sheet .wk-banner')
            check('Tạo tài khoản' in banner, f'a player without an account watches from the gate ({banner!r})')
            await shot(g3, '05-overflow-watcher')
            # ---- cheers, a heart, the group photo
            await g1.page.fill('.walk-sheet .wk-say input', 'Chúc mừng hạnh phúc! Trăm năm hạnh phúc nha 🎉 0912345678')
            await g1.page.click('.walk-sheet .wk-send')
            s = await until(bride, "return s.people.some(q=>q.said);", 'the bride sees the cheer')
            said = next(q['said'] for q in s['people'] if q['said'])
            check('hạnh phúc' in said and '0912' not in said, f'a bubble, phone masked ({said!r})')
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
            await bride.page.wait_for_function("() => document.querySelector('.walk-sheet .wk-toast:not([hidden])')?.innerText.includes('Lễ cưới')", timeout=80000)
            await shot(g2, '07-ceremony-starts', wait=300)
            rows = []
            end = time.monotonic() + 30
            while time.monotonic() < end and len({r[0] for r in rows}) < 2:
                rows = sql(db, "SELECT sid FROM live_effects WHERE id LIKE 'wedg:%'")
                await asyncio.sleep(0.5)
            check(len({r[0] for r in rows}) == 2, f'the two guests with accounts earned +15 xu ({len(rows)} rows), the watcher without one nothing')
            await shot(g1, '08-guest-xu')
            await g1.page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot(g1, '09-party-dark')
            await g1.page.evaluate("document.documentElement.dataset.theme='kem'")
            # ---- the end: the couple's total, the end card
            sql(db, 'UPDATE wedding_parties SET at=? WHERE wedding=?', time.time() - 1800 + 4, wid)
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
            check(host == [(60,), (60,)], f'each spouse 2 × 30 xu ({host})')
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
