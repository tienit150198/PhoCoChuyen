#!/usr/bin/env python3
"""🏥 Phòng sinh & nhận nuôi (game/birth.py, public/js/v4/birth.js): a four-browser walk-through at 390x844 (dev tool, the
servers of scripts/browser_ride.py: story mode, PostgreSQL, the live service).

Lan and Minh are married (life day 20). Cúc owns a homestay (scale tier 1) and offers "Phòng Đồi Thông" at 650.000 xu;
Đào has started the nurse career.
  * Cúc: 🏡 Phòng sinh của bạn (a price under the floor is refused, the floor itself is taken);
  * Lan: 👶 Đón con chung: 🏥 Sinh con with Nhà hộ sinh Phố Mây 800.000 xu and Cúc's room, 📄 Nhận nuôi 300.000 xu;
    she books Cúc's room for Bông, Lan pays: nothing is charged yet;
  * Minh: the invitation (dot on the tab), Đồng ý: Lan's wallet −650.000; the booked card (Nhận phòng, Hủy · hoàn);
  * Đào: 🩺 Ca sinh cần điều dưỡng, Nhận hỗ trợ;
  * Lan: Nhận phòng → the countdown (3 giờ); the stay's end is moved to a few seconds from now in the database;
    the clock reaches 0, "Đón bé" taps itself, the birth moment (once), 🤱 Bế bé → the baby card with "🏥 Chào đời ở
    Phòng Đồi Thông … · 🩺 Điều dưỡng Đào hỗ trợ", needs 85;
  * Cúc's credit lands on her next load (617.500 + her 1.000: price − 5 %); Lan rates the room ⭐⭐⭐⭐⭐.
Screenshots of each step; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    MNL_PY=<python with the server's requirements + playwright> BROWSER_CHANNEL=chrome python scripts/browser_birth.py [out_dir]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_ride as br  # noqa: E402
from browser_coride import PW, api, marry, sid_of  # noqa: E402
from pg_test_support import test_connect  # noqa: E402

_wait = br.wait_http
br.wait_http = lambda url, secs=60: _wait(url, max(secs, 240))
STATE = "fetch('/api/state').then(r=>r.json()).then(d=>d.state)"


def mutate(token: str, fn) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(br.DB, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def homestay_owner(s):
    from game import career_scale as scale, career_scale_resources as resources
    c = s['careers']['homestay']
    c.update(started=True, open=True)
    r = scale.ensure(c, 'homestay')
    r['tier'] = 1
    r['today']['requires_contract'] = True
    resources.ensure(c, 'homestay')


def nurse(s):
    from game import employment
    c = s['careers']['nurse']
    c['started'] = True
    if employment.required('nurse'):
        c['job'] = employment.hired_record('nurse')


def married_block(spouse: str, cid: int, side: str):
    def fn(s):
        from game import marriage as mr
        mr._apply_effect(s, dict(id=f'birth-wed-{cid}-{side}', kind='status',
                                 data=json.dumps(dict(set='married', name=spouse, couple=cid, side=side))))
    return fn


async def run(size, problems, checks) -> None:
    from playwright.async_api import async_playwright
    tag = f'{size[0]}x{size[1]}'
    out = br.OUT

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + f' [{tag}] ' + what)
        if not cond:
            problems.append(f'check [{tag}]: ' + what)

    async def shot(p, name):
        await br.popups(p.page)
        await p.page.wait_for_timeout(450)
        await p.page.screenshot(path=str(out / f'{tag}-{name}.png'))

    async def token(p):
        return next(c['value'] for c in await p.ctx.cookies() if c['name'] == 'mnl_session')

    async def family(p):
        await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await p.page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='marriage';b.dataset.tab='family';b.hidden=true;document.body.append(b);b.click();b.remove();})()")
        await p.page.wait_for_selector('.mr-family', timeout=15000)
        await p.page.wait_for_timeout(900)

    async def confirm(p):
        await p.page.wait_for_selector('#confirmDialog[open] [data-action="confirmYes"]', timeout=8000)
        await p.page.wait_for_timeout(250)
        await p.page.click('#confirmDialog[open] [data-action="confirmYes"]')
        await p.page.wait_for_timeout(1200)

    async def flash(p):
        return await p.page.evaluate("document.querySelector('.mr-flash')?.textContent||''")

    async def wallet(p):
        return (await p.page.evaluate(STATE))['journey']['wallet']

    async def to(p, sel):
        await p.page.locator(sel).first.scroll_into_view_if_needed()
        await p.page.wait_for_timeout(250)

    async def steps(lan, minh, cuc, dao):
        u = f'{size[0]}{size[1]}'
        for p, name in ((lan, 'Lan'), (minh, 'Minh'), (cuc, 'Cúc'), (dao, 'Đào')):
            await api(p, '/api/account/register', dict(username=f'{p.name.lower()}{u}', password=PW, confirm=PW, display=name))
        sl, sm = sid_of(br.DB, f'lan{u}'), sid_of(br.DB, f'minh{u}')
        marry(br.DB, sm, sl)
        con = test_connect(br.DB)
        cid = con.execute('SELECT couple FROM marriage_bonds WHERE sid=?', (sl,)).fetchone()[0]
        con.close()
        mutate(await token(lan), lambda s: (married_block('Minh', cid, 'b')(s), s['journey'].__setitem__('wallet', 2_000_000)))
        mutate(await token(minh), lambda s: (married_block('Lan', cid, 'a')(s), s['journey'].__setitem__('wallet', 400_000)))
        mutate(await token(cuc), lambda s: (homestay_owner(s), s['journey'].__setitem__('wallet', 1000)))
        mutate(await token(dao), nurse)
        for p in (lan, minh, cuc, dao):
            await p.page.reload()
            await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await p.page.wait_for_timeout(800)
            await br.popups(p.page)

        # ---- Cúc: her birth room (the floor holds) ----
        await family(cuc)
        await to(cuc, '#mr-family-room')
        await shot(cuc, '01-provider-empty')
        await cuc.page.fill('[data-mr-field="family:room:name"]', 'Phòng Đồi Thông')
        await cuc.page.fill('[data-mr-field="family:room:price"]', '450000')
        await cuc.page.click('[data-mr="fam:room-save"]')
        await cuc.page.wait_for_timeout(1200)
        f = await flash(cuc)
        check('tối thiểu 500.000' in f, f'a price under the floor is refused: {f!r}')
        expected = [x for x in problems if x.startswith('Cuc console:') and 'status of 400' in x]
        for x in expected[:1]:   # that refusal is the HTTP 400 the browser logs: expected here, nowhere else
            problems.remove(x)
        await shot(cuc, '02-provider-below-floor')
        await cuc.page.fill('[data-mr-field="family:room:price"]', '650000')
        await cuc.page.click('[data-mr="fam:room-save"]')
        await cuc.page.wait_for_timeout(1200)
        f = await flash(cuc)
        check('Phòng Đồi Thông' in f and '650.000' in f, f'the room is open: {f!r}')
        await to(cuc, '#mr-family-room')
        await shot(cuc, '03-provider-open')

        # ---- Lan: choose ----
        await family(lan)
        await to(lan, '#mr-family-children')
        txt = await lan.page.inner_text('#mr-family-children')
        check('800.000 xu' in txt and 'Phòng Đồi Thông' in txt and '650.000 xu' in txt, 'NPC hospital and Cúc\'s room with their prices')
        await shot(lan, '04-choose-birth')
        await lan.page.click('[data-mr="fam:birth-mode"][data-mode="adopt"]')
        await lan.page.wait_for_timeout(400)
        txt = await lan.page.inner_text('#mr-family-children')
        check('300.000 xu' in txt and 'Trung tâm bảo trợ' in txt, 'adoption: the paperwork fee')
        await to(lan, '#mr-family-children')
        await shot(lan, '05-choose-adopt')
        await lan.page.click('[data-mr="fam:birth-mode"][data-mode="birth"]')
        await lan.page.wait_for_timeout(400)
        await lan.page.fill('[data-mr-field="family:name"]', 'Bông')
        await lan.page.locator('.mr-opt', has_text='Phòng Đồi Thông').click()
        await lan.page.click('[data-mr="fam:birth-book"]')
        await shot(lan, '06-book-confirm')
        w0 = await wallet(lan)
        await confirm(lan)
        check(await wallet(lan) == w0, 'nothing charged on the proposal')
        await to(lan, '#mr-family-children')
        await shot(lan, '07-proposal-sent')

        # ---- Minh: agree ----
        await family(minh)
        dot = await minh.page.evaluate("document.querySelector('[data-tab=\"family\"]')?.textContent||''")
        check(any(ch.isdigit() for ch in dot), f'the family tab carries a dot: {dot!r}')
        await to(minh, '#mr-family-invite-children')
        await shot(minh, '08-invitation')
        await minh.page.click('[data-mr="fam:birth-answer"][data-answer="accept"]')
        await shot(minh, '09-accept-confirm')
        await confirm(minh)
        check(await wallet(minh) == 400_000, 'Minh pays nothing (Lan pays)')
        await to(minh, '#mr-family-children')
        await shot(minh, '10-booked')
        await lan.page.reload()
        await lan.page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await br.popups(lan.page)
        check(await wallet(lan) == w0 - 650_000, f'Lan paid 650.000 once ({w0} → {await wallet(lan)})')

        # ---- Đào: the nurse's call ----
        await family(dao)
        await to(dao, '#mr-family-nurse')
        await shot(dao, '11-nurse-calls')
        await dao.page.click('[data-mr="fam:birth-nurse"]')
        await confirm(dao)
        f = await flash(dao)
        check('Bông' in f, f'Đào helps Bông\'s birth: {f!r}')
        await to(dao, '#mr-family-nurse')
        await shot(dao, '12-nurse-helping')

        # ---- Lan: check in, the countdown, the birth ----
        await family(lan)
        await lan.page.click('[data-mr="fam:birth-checkin"]')
        await confirm(lan)
        await to(lan, '#mr-family-children')
        txt = await lan.page.inner_text('#mr-family-children')
        check('giờ' in txt and 'Đào' in txt, f'the countdown and the nurse: {txt[:160]!r}')
        await shot(lan, '13-staying-countdown')
        con = test_connect(br.DB)
        with con:
            con.execute("UPDATE birth_stays SET ends=? WHERE status='staying'", (time.time() + 6,))
            n = con.execute("SELECT COUNT(*) FROM birth_stays WHERE status='staying' AND ends<?", (time.time() + 10,)).fetchone()[0]
        con.close()
        v = await api(lan, '/api/marriage')
        st = ((v.get('family') or {}).get('birth') or {}).get('stay') or {}
        check(n == 1 and st.get('left') is not None and st['left'] <= 10, f'the stay ends in a few seconds (db {n}, view left {st.get("left")})')
        await family(lan)          # a fresh read: 6 seconds left
        await to(lan, '#mr-family-children')
        await shot(lan, '14-last-seconds')
        try:
            await lan.page.wait_for_selector('.mr-born', timeout=20000)
            born = True
        except Exception:  # noqa: BLE001
            born = False
        check(born, 'the clock reached 0, "Đón bé" tapped itself, the birth moment shows')
        await lan.page.wait_for_timeout(1500)
        await lan.page.screenshot(path=str(out / f'{tag}-15-birth-moment.png'))
        if born:
            await lan.page.click('.mr-born [data-mr="fam:born-seen"]')
            await lan.page.wait_for_timeout(500)
        check(not await lan.page.locator('.mr-born').count(), 'the moment closes and stays closed')
        child = await lan.page.inner_text('.mr-family-child')
        check('Chào đời ở Phòng Đồi Thông' in child and 'Điều dưỡng Đào' in child and '85/100' in child, f'the baby card: {child[:200]!r}')
        await to(lan, '.mr-family-child')
        await shot(lan, '16-baby-card')
        await to(lan, '[data-mr="fam:birth-rate"]')
        await shot(lan, '17-rate')
        await lan.page.click('[data-mr="fam:birth-rate"][data-stars="5"]')
        await lan.page.wait_for_timeout(1000)
        check('5 sao' in await flash(lan), 'rated 5 stars')
        await family(minh)
        await minh.page.wait_for_timeout(1200)
        check(await minh.page.locator('.mr-born').count() == 1, 'Minh sees the birth moment on his device too (once per device)')
        await minh.page.screenshot(path=str(out / f'{tag}-18-minh-birth-moment.png'))

        # ---- Cúc: paid 95 % on her next load ----
        await cuc.page.reload()
        await cuc.page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await br.popups(cuc.page)
        await family(cuc)
        await cuc.page.wait_for_timeout(600)
        got = await wallet(cuc)
        check(got == 1000 + 617_500, f'Cúc credited 650.000 − 5 % = 617.500 ({got})')
        await to(cuc, '#mr-family-room')
        await shot(cuc, '19-provider-after')
        wide = await lan.page.evaluate("document.querySelector('dialog[open]')?.scrollWidth>innerWidth+1")
        check(not wide, 'no sideways scroll in the sheet')

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL') or None)
        players = [await br.player(browser, br.BASE, n, [], size, problems) for n in ('Lan', 'Minh', 'Cuc', 'Dao')]
        try:
            await steps(*players)
        except Exception:
            for p in players:
                await p.page.screenshot(path=str(out / f'{tag}-FAIL-{p.name}.png'))
            raise
        for p in players:
            await p.ctx.close()
        await browser.close()


async def main_async():
    problems, checks = [], []
    try:
        await run((390, 844), problems, checks)
    except AssertionError as e:
        problems.append(str(e))
    print(*checks, sep='\n')
    return problems


def main():
    br.OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mnl-birth-', dir=os.environ.get('TMPDIR'), ignore_cleanup_errors=True) as tmp, br.servers(tmp) as (base, db):
        br.BASE, br.DB = base, db
        problems = asyncio.run(main_async())
    if problems:
        print('problems:', *problems, sep='\n  ')
        sys.exit(1)
    print('ok:', br.OUT)


if __name__ == '__main__':
    main()
