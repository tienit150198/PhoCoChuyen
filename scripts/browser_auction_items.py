#!/usr/bin/env python3
"""🔨 Đồ đấu giá mới (20/10): the new kinds in a real browser on a 390x844 phone (dev tool; the game server from
scripts/browser_housing.py, PostgreSQL through TEST_DATABASE_URL).

Lan owns the tập thể flat, has an account older than 3 days and 3.000.000 xu. An operator adds four lots (🪑 Sập gụ khảm
xà cừ, 🐾 Vòng kim cương SSS, 🧰 Máy espresso, 🏎️ Tia Chớp Hồng Ngọc). In the browser:
  1. the auction's lot list: each new card with its picture and what it does (✨ the use line);
  2. Lan bids on the sập; the lot ends and is settled; "Của tôi" shows it with its use;
  3. she opens Bày trí at home, drags the sập out of the bag into the living room: it stands there and Ấm cúng goes up.
JPEG screenshots in out_dir; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_auction_items.py [out_dir]
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402
from pg_test_support import test_connect  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'auction-items-shots'
PW = 'matkhau-rat-dai'
API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""
LOTS = ('dc_sap_kham', 'pw_vong_kc_sss', 'tl_espresso', 'lx_sieu_xe_02')


def store(db):
    from game.storage import Store
    return Store(db, story=True)


def mutate(db, token, fn):
    from game import marriage as mr
    st = store(db)
    mr._mutate(st, {st.key(token): fn})
    st.close_pool()


def read(db, token):
    st = store(db)
    try:
        return st.read(token)[0]
    finally:
        st.close_pool()


def seed(s):
    """A home of her own (the tập thể flat, as scripts/browser_deco.py), 3.000.000 xu, the saving titles seen."""
    from browser_deco import seed_own
    seed_own(s)
    j = s['journey']
    j['wallet'] = 3_000_000
    j['stats']['max_wallet'] = 3_000_000
    for t in ('m_save200', 'm_save1000'):
        j['titles'].setdefault(t, j['life_day'])


def age(db, username, days=5):
    con = test_connect(db)
    with con:
        con.execute('UPDATE accounts SET created_at=? WHERE username=?',
                    (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - days * 86400)), username))
    con.close()


def add_lots(db):
    from game import auction as au
    st = store(db)
    out = {}
    try:
        for item in LOTS:
            out[item] = au.admin_add(st, 'op', dict(item=item, hours=2))['id']
            time.sleep(0.01)   # lot ids come from the clock
    finally:
        st.close_pool()
    return out


def settle_now(db, lot):
    from game import auction as au
    con = test_connect(db)
    with con:
        con.execute('UPDATE auction_lots SET ends_at=? WHERE id=?', (time.time() - 1, lot))
    con.close()
    st = store(db)
    try:
        return au.settle_one(st, lot)
    finally:
        st.close_pool()


async def main() -> int:
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    problems, checks = [], []

    def check(ok, what):
        checks.append(('PASS ' if ok else 'FAIL ') + what)
        print(checks[-1])
        if not ok:
            problems.append(what)

    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2)
            await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','9.9.9')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and problems.append(f'console: {m.text[:200]}'))
            page.on('pageerror', lambda e: problems.append(f'exception: {str(e)[:200]}'))
            page.on('response', lambda r: r.status >= 500 and problems.append(f'HTTP {r.status} {r.url}'))
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            out = await page.evaluate(API, ['/api/account/register', dict(username='lanmay', password=PW, confirm=PW, display='Lan Mây')])
            check(out['status'] < 400, f'register ({out["status"]})')
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            age(db, 'lanmay')
            mutate(db, token, seed)
            lots = add_lots(db)

            async def popups():
                for _ in range(6):
                    b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, [data-x3="close"]:visible, '
                                     '[data-fh-key="giftok"]:visible, button:has-text("Đã hiểu"):visible')
                    if not await b.count():
                        break
                    await b.first.click()
                    await page.wait_for_timeout(400)

            async def reload():
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=60000)
                await page.wait_for_timeout(1500)
                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

            async def shot(name):
                await page.wait_for_timeout(450)
                await page.screenshot(path=str(OUT / f'{name}.jpg'), type='jpeg', quality=80)

            async def act(action):
                await page.evaluate(f"(()=>{{const b=document.createElement('button');b.dataset.action='{action}';b.hidden=true;"
                                    "document.body.append(b);b.click();b.remove();})()")

            async def box(sel):
                b = await page.evaluate("""(s)=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();
                    return [r.left,r.top,r.width,r.height];}""", sel)
                assert b, f'nothing at {sel}'
                return b

            async def tap(sel, wait=500):
                await popups()
                await page.click(sel, timeout=8000)
                await page.wait_for_timeout(wait)
                await popups()

            # ---- 1. the lot list: the new cards
            await reload()
            await act('auction')
            await page.wait_for_selector('dialog.au-sheet[open] .au-lot', timeout=15000)
            await page.wait_for_timeout(900)
            names = {'dc_sap_kham': ('au-decor', 'Ấm cúng'), 'pw_vong_kc_sss': ('au-petgear', 'Tủ đồ thú cưng'),
                     'tl_espresso': ('au-tool', 'Sớm Mai'), 'lx_sieu_xe_02': ('au-ltd', 'Nhà xe')}
            for n, item in enumerate(LOTS, 1):
                await tap(f'dialog.au-sheet[open] [data-au=lot][data-id="{lots[item]}"]', 400)
                cls, word = names[item]
                card = await page.evaluate("()=>{const c=document.querySelector('dialog.au-sheet[open] .au-lot');"
                                           "return {html:c?.innerHTML||'',use:c?.querySelector('.au-use')?.innerText||''};}")
                check(cls in card['html'] and word in card['use'], f'{item}: its card ({cls}) and what it does: {card["use"][:80]}')
                await shot(f'0{n}-lot-{item}')
            await tap(f'dialog.au-sheet[open] [data-au=lot][data-id="{lots["lx_sieu_xe_02"]}"]', 400)
            main = await page.inner_text('dialog.au-sheet[open] [data-au=go]')
            check('1.000.000' in main, f'the premium starting price on the button: {main}')

            # ---- 2. bid on the sập, the lot ends, Của tôi
            await tap(f'dialog.au-sheet[open] [data-au=lot][data-id="{lots["dc_sap_kham"]}"]', 400)
            await tap('dialog.au-sheet[open] [data-au=go]', 1500)
            flash = await page.inner_text('dialog.au-sheet[open] .sd-flash')
            check('500.000' in flash, f'the bid: {flash[:90]}')
            check(settle_now(db, lots['dc_sap_kham']) == 'sold', 'the lot is settled: sold')
            await page.evaluate("document.querySelector('dialog.au-sheet[open]')?.close()")
            await act('auction')
            await page.wait_for_selector('dialog.au-sheet[open] .au-lot', timeout=15000)
            await page.wait_for_timeout(1200)
            await tap('dialog.au-sheet[open] [data-au=tab][data-tab=mine]', 800)
            mine = await page.inner_text('dialog.au-sheet[open] .sd-body')
            check('Sập gụ khảm xà cừ' in mine and 'Ấm cúng +6' in mine, 'Của tôi: the sập and what it does')
            await shot('05-mine')
            s = read(db, token)
            check(any(x['k'] == 'uq_dc_sap_kham' for x in s['journey']['reno']['items']), 'the piece is in the bag')
            await page.evaluate("document.querySelector('dialog.au-sheet[open]')?.close()")

            # ---- 3. Bày trí: drag it out of the bag into the living room
            await reload()
            await act('house')   # Hành trình → Nơi bạn ở (the town map is the phone's first page)
            await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
            await popups()
            await page.click('.hs-sheet [data-hs="inside"]:not([data-mode])')
            await page.wait_for_selector('.dc-sheet[open] [data-dc="view3d"][data-mode="2d"]', timeout=10000)
            if await page.locator('.dc-sheet svg.dc-room').count() == 0:   # the house opens in 3D now: the drawn room to place
                await tap('.dc-sheet [data-dc="view3d"][data-mode="2d"]', 800)
            await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)
            await page.wait_for_timeout(600)
            cozy0 = await page.evaluate("document.querySelector('.dc-sheet .dc-cozy b, .dc-sheet [data-cozy]')?.innerText||''")
            await tap('.dc-sheet [data-dc="edit"]')
            if await page.locator('.dc-sheet [data-dc="tipOk"]').count():
                await tap('.dc-sheet [data-dc="tipOk"]')
            if not await page.locator('.dc-sheet .dc-buycard[data-k="uq_dc_sap_kham"]').count():
                await tap('.dc-sheet [data-dc="drawer"][data-d="bag"]')
            await page.evaluate("document.querySelector('.dc-sheet .dc-buycard[data-k=\"uq_dc_sap_kham\"]')?.scrollIntoView({block:'nearest',inline:'center'})")
            await page.evaluate("""()=>{const w=document.querySelector('.dc-sheet .dc-roomwrap'),h=document.querySelector('.dc-sheet .sheet-head');if(!w)return;
                w.scrollIntoView({block:'start'});let s=w.parentElement;while(s&&s.scrollHeight<=s.clientHeight+2)s=s.parentElement;
                if(s&&h)s.scrollBy(0,-(h.getBoundingClientRect().bottom-s.getBoundingClientRect().top)-8);}""")
            await page.wait_for_timeout(300)
            await shot('06-bag')
            l, t, bw, bh = await box('.dc-sheet .dc-buycard[data-k="uq_dc_sap_kham"]')
            if t + 70 > 844:
                await page.evaluate("""(dy)=>{let s=document.querySelector('.dc-sheet .dc-roomwrap').parentElement;
                    while(s&&s.scrollHeight<=s.clientHeight+2)s=s.parentElement;if(s)s.scrollBy(0,dy);}""", t + 80 - 844)
                await page.wait_for_timeout(150)
                l, t, bw, bh = await box('.dc-sheet .dc-buycard[data-k="uq_dc_sap_kham"]')
            rl, rt, rw, rh = await box('.dc-sheet svg.dc-room')
            x0, y0, x1, y1 = l + bw / 2, min(t + bh / 2, 844 - 30), rl + rw * .45, rt + rh * .9
            await page.mouse.move(x0, y0)
            await page.mouse.down()
            await page.mouse.move(x0, y0 - 40, steps=5)
            await page.mouse.move(x1, y1, steps=14)
            await page.wait_for_timeout(150)
            await shot('07-dragging')
            await page.mouse.up()
            await page.wait_for_timeout(1300)
            await popups()
            kinds = await page.evaluate("[...document.querySelectorAll('.dc-sheet .dc-it[data-uid]')].map(g=>g.dataset.k)")
            check('uq_dc_sap_kham' in kinds, 'the sập stands in the living room')
            if await page.locator('.dc-sheet [data-dc="done"]').count():
                await tap('.dc-sheet [data-dc="done"]', 2500)
            await shot('08-placed')
            from game import deco as dc
            s = read(db, token)
            L = dc.layout(s)
            placed = [u for u, k in L['kinds'].items() if k == 'uq_dc_sap_kham' and u in L['pos']]
            check(bool(placed), 'the save has it placed')
            print('cozy before:', cozy0, 'after:', dc.points(L))
            await browser.close()
    for c in checks:
        print(c)
    for p in problems:
        print('PROBLEM', p)
    print('shots:', OUT)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
