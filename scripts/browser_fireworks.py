#!/usr/bin/env python3
"""🎆 Pháo hoa cả phố as a show every online player sees (dev tool; the game server and the live service from
scripts/browser_ride.py, PostgreSQL through TEST_DATABASE_URL).

Lan, Minh and Hoa on 390x844 phones (Hoa with prefers-reduced-motion), Lan with an account and 2,000,000 xu:
  * Lan opens "Bắn pháo hoa" from the menu (action luxFw): the shop on 🎆, the wish list, "🎆 Bắn · … xu";
  * she sets off Pháo hoa lớn with "Mừng sinh nhật": her sheet closes, the sky lights up on her page and on Minh's,
    who has the bank sheet open (the show is in the top layer), with the long banner (name, wish, ✕, the button);
  * a Đại tiệc a bit later (the street's gap moved back in the database) on Minh's page and Hoa's gentler one;
  * Minh's ✕ closes it.
JPEG screenshots; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    TEST_DATABASE_URL=postgresql://… MNL_PY=<python> python scripts/browser_fireworks.py [out_dir]
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
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
BANNER = "() => { const b = document.querySelector('.fw-root .fw-banner'); return b ? b.innerText : null; }"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'fireworks-shots'


async def api(p, path, body=None):
    out = await p.page.evaluate(API, [path, body])
    if out['status'] >= 400:
        raise AssertionError(f'{p.name}: {path} -> {out}')
    return out['data']


async def run(problems, checks) -> None:
    from playwright.async_api import async_playwright
    out = OUT
    out.mkdir(parents=True, exist_ok=True)

    def check(cond, what):
        checks.append(('PASS ' if cond else 'FAIL ') + what)
        if not cond:
            problems.append('check: ' + what)

    async def shot(p, name, wait=0):
        if wait:
            await p.page.wait_for_timeout(wait)
        await p.page.screenshot(path=str(out / f'{name}.jpg'), type='jpeg', quality=78)

    async def banner(p, timeout=10.0):
        end = asyncio.get_running_loop().time() + timeout
        while True:
            t = await p.page.evaluate(BANNER)
            if t:
                return t
            if asyncio.get_running_loop().time() > end:
                raise AssertionError(f'{p.name}: no fireworks banner')
            await asyncio.sleep(0.15)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        lan = await br.player(browser, br.BASE, 'Lan', [], (390, 844), problems)
        minh = await br.player(browser, br.BASE, 'Minh', [], (390, 844), problems)
        hoa = await br.player(browser, br.BASE, 'Hoa', [], (390, 844), problems)
        await hoa.page.emulate_media(reduced_motion='reduce')
        await api(lan, '/api/account/register', dict(username='lanmay', password=PW, confirm=PW, display='Lan Mây'))
        from game import marriage as mr
        from game.storage import Store
        store = Store(br.DB, story=True)
        con = test_connect(br.DB)
        sid = con.execute("SELECT sid FROM accounts WHERE username='lanmay'").fetchone()[0]
        con.close()

        def rich(s):
            j = s['journey']
            j['wallet'] = 2_000_000
            j['stats']['max_wallet'] = 2_000_000
            for t in ('m_save200', 'm_save1000'):
                j['titles'].setdefault(t, j['life_day'])
        mr._mutate(store, {sid: rich})
        store.close_pool()
        for p in (lan, minh, hoa):
            await p.page.reload()
            await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await p.page.wait_for_timeout(2500)   # the live socket opens on the first idle moment
            await br.popups(p.page)
            await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        # the menu: Khu phố has "Bắn pháo hoa"
        await lan.page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
        await lan.page.wait_for_selector('#rail [data-action=v4Group][data-group=pho]', timeout=15000)
        await lan.page.click('#rail [data-action=v4Group][data-group=pho]')
        await lan.page.wait_for_timeout(600)
        has = await lan.page.locator('#rail [data-action=luxFw]:visible').count() == 1
        check(has, 'the Khu phố hub lists "Bắn pháo hoa"')
        await shot(lan, '1-menu-khu-pho')
        await lan.page.click('#rail [data-action=luxFw]')
        await lan.page.wait_for_selector('dialog.lx-sheet[open] select[name=fwish]', timeout=15000)
        await lan.page.locator('dialog.lx-sheet[open] [data-lx=size][data-id=lon]').click()
        await lan.page.select_option('dialog.lx-sheet[open] select[name=fwish]', 'sinh_nhat')
        main = await lan.page.locator('dialog.lx-sheet[open] .sd-main').first.inner_text()
        check('Bắn' in main and '80.000' in main, f'the main button says what it does: {main!r}')
        await shot(lan, '2-shop-fireworks', 300)

        # Minh is in the bank sheet: the show must still be on top
        await br.act(minh.page, 'bank')
        await minh.page.wait_for_timeout(1200)
        await lan.page.locator('dialog.lx-sheet[open] .sd-main').first.click()
        t = await banner(lan)
        check('Lan Mây' in t and 'Mừng sinh nhật' in t, f'Lan sees her own show: {t!r}')
        await lan.page.wait_for_timeout(700)
        check(not await lan.page.evaluate("!!document.querySelector('dialog.lx-sheet[open]')"), 'the shop closed so the sky shows')
        t = await banner(minh)
        check('Lan Mây' in t and 'pháo hoa lớn' in t and 'Mừng sinh nhật' in t, f'Minh sees it in another sheet: {t!r}')
        t = await banner(hoa)
        check('Lan Mây' in t, f'Hoa (reduced motion) sees it: {t!r}')
        await asyncio.gather(shot(lan, '3-lan-own-show', 1600), shot(minh, '4-minh-over-bank-sheet', 1600), shot(hoa, '5-hoa-reduced-motion', 2600))
        await shot(minh, '6-minh-later', 2500)

        # a Đại tiệc after the street's gap (moved back here), Minh on the town page
        await minh.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await minh.page.wait_for_timeout(16000)   # the first banner goes away by itself
        check(not await minh.page.evaluate("!!document.querySelector('.fw-root')"), 'the banner leaves by itself')
        con = test_connect(br.DB)
        with con:
            con.execute("UPDATE lux_gifts SET at=at-3600 WHERE kind='phao_hoa'")
        con.close()
        await br.act(lan.page, 'luxFw')
        await lan.page.wait_for_selector('dialog.lx-sheet[open] [data-lx=size][data-id=dai_tiec]', timeout=15000)
        await lan.page.evaluate("fetch('/api/mtq')")   # fresh wait time
        await lan.page.locator('dialog.lx-sheet[open] [data-lx=tab][data-tab=mtq]').click()
        await lan.page.wait_for_timeout(800)
        await lan.page.locator('dialog.lx-sheet[open] [data-lx=size][data-id=dai_tiec]').click()
        await lan.page.select_option('dialog.lx-sheet[open] select[name=fwish]', '')
        await lan.page.locator('dialog.lx-sheet[open] .sd-main').first.click()
        t = await banner(minh)
        check('đại tiệc' in t.lower(), f'Minh sees the Đại tiệc: {t!r}')
        await shot(minh, '7-minh-dai-tiec', 2200)
        await shot(minh, '8-minh-dai-tiec-finale', 9500)
        await minh.page.locator('.fw-root [data-fw=x]').click()
        await minh.page.wait_for_timeout(800)
        check(not await minh.page.evaluate("!!document.querySelector('.fw-root')"), '✕ closes the show')
        await browser.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    br.OUT = OUT
    problems, checks = [], []
    with tempfile.TemporaryDirectory(prefix='mnl-fw-', ignore_cleanup_errors=True) as tmp, br.servers(tmp) as (base, db):
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
