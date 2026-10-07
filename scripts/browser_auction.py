#!/usr/bin/env python3
"""🔨 Nhà đấu giá: two players bid on one lot in real browsers (dev tool; the game server and the live service from
scripts/browser_ride.py, PostgreSQL through TEST_DATABASE_URL).

Lan on a 390x844 phone, Minh on a 1280x800 desktop, both with accounts older than 3 days and 300.000 xu:
  * an operator adds two lots (POST /api/admin/auction: a plate and a painting);
  * Lan bids the starting price: "🔒 Đang giữ" shows the escrow, her wallet drops;
  * Minh bids more: Lan's page hears it live (no reload): the new price, "Đã bị trả cao hơn", her money back;
  * Lan raises: Minh is outbid live in turn; then the lot ends and is settled: Lan gets "Bạn thắng", the plate is in
    "Của tôi", Minh sees the winner in "Đã chốt", every xu but the price is back with its owner.
Four JPEG screenshots; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    TEST_DATABASE_URL=postgresql://… MNL_PY=<python> python scripts/browser_auction.py [out_dir]
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_ride as br  # noqa: E402
from pg_test_support import test_connect  # noqa: E402

PW = 'matkhau-rat-dai'
API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""
STATE = """() => { const d = document.querySelector('dialog.au-sheet[open]'); if (!d) return null;
  return {price: d.querySelector('.au-price b')?.innerText || '', state: d.querySelector('.au-state')?.innerText || '',
          flash: d.querySelector('.sd-flash')?.innerText || '', held: d.querySelector('.au-held')?.innerText || '',
          wallet: d.querySelector('.sd-wallet')?.innerText || '', main: d.querySelector('.sd-main')?.innerText || '',
          body: d.querySelector('.sd-body')?.innerText || ''}; }"""
OUT = br.OUT if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'auction-shots'


async def api(p, path, body=None):
    out = await p.page.evaluate(API, [path, body])
    if out['status'] >= 400:
        raise AssertionError(f'{p.name}: {path} -> {out}')
    return out['data']


def age(db: str, username: str, days: int = 5) -> None:
    con = test_connect(db)
    with con:
        con.execute("UPDATE accounts SET created_at=? WHERE username=?",
                    (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - days * 86400)), username))
    con.close()


def money(db: str, username: str) -> int:
    from game.storage import Store
    store = Store(db, story=True)
    con = test_connect(db)
    sid = con.execute('SELECT sid FROM accounts WHERE username=?', (username,)).fetchone()[0]
    con.close()
    with store.connect() as d:
        st = store.parse_state(d.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()['state'], sid)
    store.close_pool()
    j = st['journey']
    return j['wallet'] + ((j.get('bank') or {}).get('balance') or 0) + sum(h['a'] for h in ((j.get('uniq') or {}).get('hold') or {}).values())


def settle_now(db: str, lot: str) -> str | None:
    from game import auction
    from game.storage import Store
    con = test_connect(db)
    with con:
        con.execute('UPDATE auction_lots SET ends_at=? WHERE id=?', (time.time() - 1, lot))
    con.close()
    store = Store(db, story=True)
    try:
        return auction.settle_one(store, lot)
    finally:
        store.close_pool()


async def run(problems, checks) -> None:
    from playwright.async_api import async_playwright
    out = OUT
    out.mkdir(parents=True, exist_ok=True)

    def check(cond, what):
        checks.append(('PASS ' if cond else 'FAIL ') + what)
        if not cond:
            problems.append('check: ' + what)

    async def shot(p, name):
        await p.page.wait_for_timeout(400)
        await p.page.screenshot(path=str(out / f'{name}.jpg'), type='jpeg', quality=72)

    async def until(p, cond: str, what: str, timeout=10.0):
        end = time.monotonic() + timeout
        while True:
            s = await p.page.evaluate(STATE)
            if s is not None and await p.page.evaluate(f's => {{ {cond} }}', s):
                return s
            if time.monotonic() > end:
                raise AssertionError(f'{what} (state: {s})')
            await asyncio.sleep(0.2)

    async def tap(p, sel):
        await p.page.locator(f'dialog.au-sheet[open] {sel}').first.click()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        lan = await br.player(browser, br.BASE, 'Lan', [], (390, 844), problems)
        minh = await br.player(browser, br.BASE, 'Minh', [], (1280, 800), problems)
        await api(lan, '/api/account/register', dict(username='lanmay', password=PW, confirm=PW, display='Lan Mây'))
        await api(minh, '/api/account/register', dict(username='minhpho', password=PW, confirm=PW, display='Minh Phố'))
        for u in ('lanmay', 'minhpho'):
            age(br.DB, u)
        from game import marriage as mr
        from game.storage import Store
        store = Store(br.DB, story=True)
        con = test_connect(br.DB)
        sids = {u: con.execute('SELECT sid FROM accounts WHERE username=?', (u,)).fetchone()[0] for u in ('lanmay', 'minhpho')}
        con.close()

        def rich(s):   # 300.000 xu each, like a well-off player (its saving titles already seen: no scene over the sheet)
            j = s['journey']
            j['wallet'] = 300_000
            j['stats']['max_wallet'] = 300_000
            for t in ('m_save200', 'm_save1000'):
                j['titles'].setdefault(t, j['life_day'])
        mr._mutate(store, {sid: rich for sid in sids.values()})
        store.close_pool()
        start = {u: money(br.DB, u) for u in sids}
        lot = (await api(lan, '/api/admin/auction', dict(item='pl_68loc68', tier=1, hours=2)))['id']
        await api(lan, '/api/admin/auction', dict(item='tr_cho_tet', tier=2, hours=3))
        for p in (lan, minh):
            await p.page.reload()
            await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await p.page.wait_for_timeout(1500)
            await br.popups(p.page)
            await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await br.act(p.page, 'auction')
            await p.page.wait_for_selector('dialog.au-sheet[open] .au-lot', timeout=15000)
            await p.page.wait_for_timeout(800)

        # Lan bids the starting price
        await tap(lan, f'[data-au=lot][data-id="{lot}"]')
        s = await until(lan, "return s.main.includes('5.000')", 'Lan sees the starting price on the button')
        await tap(lan, '[data-au=go]')
        s = await until(lan, "return s.held.includes('5.000') && s.state.includes('dẫn đầu')", 'Lan leads, 5.000 xu held')
        check(True, 'Lan bids 5.000: "Bạn đang dẫn đầu", "Đang giữ 5.000 xu"')
        # Minh bids more (the ×2 quick chip), Lan hears it live
        await tap(minh, f'[data-au=lot][data-id="{lot}"]')
        await until(minh, "return s.price.includes('5.000')", 'Minh sees 5.000')
        await tap(minh, '[data-au=amount] >> nth=1')
        await tap(minh, '[data-au=go]')
        await until(minh, "return s.state.includes('dẫn đầu')", 'Minh leads')
        s = await until(lan, "return s.price.includes('6.000') && s.state.includes('trả cao hơn') && !s.held", 'Lan is outbid live, her money back')
        check(True, f'Lan outbid live without a reload: price {s["price"]}, "{s["state"]}", escrow refunded')
        await shot(lan, '1-phone-outbid')
        await shot(minh, '2-desktop-leading')
        # Lan raises: Minh is outbid live
        await tap(lan, '[data-au=go]')
        await until(lan, "return s.state.includes('dẫn đầu')", 'Lan leads again')
        s = await until(minh, "return s.state.includes('trả cao hơn')", 'Minh is outbid live')
        check(True, f'Minh outbid live: {s["price"]}')
        # the lot ends: settled once, Lan wins
        got = settle_now(br.DB, lot)
        check(got == 'sold', f'settled: {got}')
        await until(lan, "return s.flash.includes('thắng')", 'Lan hears she won')
        await tap(lan, '[data-au=tab][data-tab=mine]')
        s = await until(lan, "return s.body.includes('68-LỘC-68')", 'the plate is in Của tôi')
        check(True, 'Lan: "Bạn thắng", 68-LỘC-68 in Của tôi')
        await shot(lan, '3-phone-won')
        await tap(minh, '[data-au=tab][data-tab=past]')
        s = await until(minh, "return s.body.includes('Lan Mây')", 'Minh sees the winner in Đã chốt')
        await shot(minh, '4-desktop-history')
        for who in (lan, minh):   # anything still in flight paid now (the pages already did it on the live frames)
            await api(who, '/api/live/effects', {})
        end = {u: money(br.DB, u) for u in sids}
        burned = sum(start.values()) - sum(end.values())
        con = test_connect(br.DB)
        price = con.execute('SELECT price FROM auction_lots WHERE id=?', (lot,)).fetchone()[0]
        con.close()
        check(burned == price and end['minhpho'] == start['minhpho'], f'only the price left the game: burned {burned} = price {price}; Minh {end["minhpho"]} = {start["minhpho"]}')
        await browser.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    br.OUT = OUT
    problems, checks = [], []
    os.environ['ADMIN_USERS'] = 'lanmay'   # the operator who adds the lots (POST /api/admin/auction)
    with tempfile.TemporaryDirectory(prefix='mnl-auc-', ignore_cleanup_errors=True) as tmp, br.servers(tmp) as (base, db):
        br.BASE, br.DB = base, db
        try:
            asyncio.run(run(problems, checks))
        except AssertionError as e:
            problems.append(str(e))
    print(*checks, sep='\n')
    if problems:
        print('problems:', *problems, sep='\n  ')
        sys.exit(1)
    print('ok:', OUT)


if __name__ == '__main__':
    main()
