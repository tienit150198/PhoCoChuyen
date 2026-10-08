#!/usr/bin/env python3
"""💌 Thiệp mời cưới cả phố in a real browser (dev tool; the game server and the live service from
scripts/browser_ride.py, PostgreSQL through TEST_DATABASE_URL).

Lan and Minh are engaged with their party booked; Hoa is a neighbour; all on 390x844 phones:
  * Lan opens Khu phố › "Thiệp mời cưới": the sheet with both names, the party's time, ideas, the live preview and
    "💌 Gửi thiệp · 10.000 xu"; she picks an idea, edits it, pays from the wallet (the payment sheet);
  * Hoa, online in the street, gets the card a few seconds later (live frame → GET /api/wedinvite): names, words,
    the party's time, "Chúc mừng 🎉", "Xem lịch cưới", "Đóng"; she cheers; Minh (the partner) gets no card;
  * Hoa reloads: the card does not come back; Lan's sheet shows the cheer.
JPEG screenshots; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    TEST_DATABASE_URL=postgresql://… MNL_PY=<python> python scripts/browser_wedinvite.py [out_dir]
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_ride as br  # noqa: E402

PW = 'matkhau-rat-dai'
API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'wedinvite-shots'
PLAN = dict(venue='restaurant', tables=20, menu='tieu_chuan', ceremonies=dict(dam_ngo=True, an_hoi=5, gia_tien=True, le_duong=False),
            extras=['dress', 'makeup', 'mc', 'cards'], days=3)


async def api(p, path, body=None):
    out = await p.page.evaluate(API, [path, body])
    if out['status'] >= 400:
        raise AssertionError(f'{p.name}: {path} -> {out}')
    return out['data']


async def calm(p):
    """The cards that open by themselves first (🎁 the town's gifts, Có gì mới, x3…), closed with their own buttons so
    the popup queue (v4/break-gate.js) moves on, until the screen stays calm for a moment."""
    quiet = 0
    for _ in range(20):
        await br.popups(p.page)
        b = p.page.locator('[data-gf="ok"]:visible')
        if await b.count():
            await b.first.click()
            quiet = 0
        elif await p.page.evaluate("[...document.querySelectorAll('dialog[open]')].some(d=>d.id!=='sheet')"):
            await p.page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#wiDialog)').forEach(d=>d.close())")
            quiet = 0
        else:
            quiet += 1
            if quiet >= 3:
                break
        await p.page.wait_for_timeout(600)
    await p.page.evaluate("document.getElementById('sheet')?.open&&document.getElementById('sheet').close()")


async def token(p):
    return next(c['value'] for c in await p.ctx.cookies() if c['name'] == 'mnl_session')


def engage(db, ta, tb):
    """Lan and Minh: rich, friends, engaged, their wedding (and live party) booked three hours from now."""
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    sa, sb = store.key(ta), store.key(tb)

    def rich(s):
        s['journey']['wallet'] = 60_000
    mr._mutate(store, {sa: rich, sb: rich})

    def friends(dbc):
        for x, y in ((sa, sb), (sb, sa)):
            dbc.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?) ON CONFLICT DO NOTHING', (x, y, time.time()))
    store.transaction(friends)
    view = lambda t: mr.view(store, t, store.read(t)[0])
    mr.act(store, ta, 'ring_buy', dict(tier='bac'))
    ring = [r for r in view(ta)['rings'] if r['status'] == 'owned'][-1]['id']
    mr.act(store, ta, 'propose', dict(code=view(tb)['me']['code'], ring=ring, message='hem', announce=True))
    mr.act(store, tb, 'respond', dict(id=view(tb)['incoming'][0]['id'], answer='accept', announce=True))
    mr.act(store, ta, 'plan', dict(plan=dict(PLAN, at=time.time() + 3 * 3600), mine=50, announce=True))
    w = view(tb)['wedding']
    mr.act(store, tb, 'confirm', dict(id=w['id'], version=w['version'], announce=True))
    mr._mutate(store, {sa: rich, sb: rich})
    store.close_pool()


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
        await p.page.screenshot(path=str(out / f'{name}.jpg'), type='jpeg', quality=80)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        lan = await br.player(browser, br.BASE, 'Lan', [], (390, 844), problems)
        minh = await br.player(browser, br.BASE, 'Minh', [], (390, 844), problems)
        hoa = await br.player(browser, br.BASE, 'Hoa', [], (390, 844), problems)
        await api(lan, '/api/account/register', dict(username='lanmay', password=PW, confirm=PW, display='Lan Mây'))
        await api(minh, '/api/account/register', dict(username='minhtu', password=PW, confirm=PW, display='Minh Tú'))
        engage(br.DB, await token(lan), await token(minh))
        for p in (lan, minh, hoa):
            await p.page.reload()
            await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await p.page.wait_for_timeout(2500)   # the live socket opens on the first idle moment
            await p.page.wait_for_timeout(1500)
            await calm(p)

        # Khu phố has "Thiệp mời cưới" for the engaged couple, not for Hoa
        await calm(lan)
        await lan.page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
        await lan.page.wait_for_selector('#rail [data-action=v4Group][data-group=pho]', timeout=15000)
        await lan.page.click('#rail [data-action=v4Group][data-group=pho]')
        await lan.page.wait_for_timeout(600)
        check(await lan.page.locator('#rail [data-action=wedInvite]:visible').count() == 1, 'the Khu phố hub lists "Thiệp mời cưới"')
        await shot(lan, '1-menu-khu-pho')
        await lan.page.click('#rail [data-action=wedInvite]')
        await lan.page.wait_for_selector('dialog.wi-sheet[open] #wi-text', timeout=15000)
        btn = lan.page.locator('dialog.wi-sheet[open] [data-wic=send]')
        check(await btn.is_disabled() and '10.000' in await btn.inner_text(), 'the button shows the price and waits for words')
        await shot(lan, '2-compose-empty', 300)
        await lan.page.locator('dialog.wi-sheet[open] [data-wic=idea]').nth(1).click()
        await lan.page.locator('#wi-text').press('Control+End')
        await lan.page.locator('#wi-text').type(' Hẹn gặp mọi người ở tiệc nhé!')
        pv = await lan.page.locator('dialog.wi-sheet[open] .wi-preview').inner_text()
        check('Hẹn gặp mọi người' in pv and 'Lan Mây' in pv and 'Minh Tú' in pv, f'the preview follows the text: {pv[:80]!r}')
        await shot(lan, '3-compose-preview', 300)
        await lan.page.locator('dialog.wi-sheet[open] .wi-body').evaluate('b=>b.scrollTop=b.scrollHeight')
        await shot(lan, '4-compose-preview-scrolled', 200)
        await btn.click()
        await lan.page.wait_for_selector('#confirmDialog[open] [data-action=confirmYes]', timeout=10000)
        await shot(lan, '5-confirm-payment', 300)
        await lan.page.click('#confirmDialog[open] [data-action=confirmYes]')
        await lan.page.wait_for_selector('dialog.wi-sheet[open] .wi-sent', timeout=15000)
        wallet = (await api(lan, '/api/state'))['state']['journey']['wallet']
        check(wallet == 50_000, f'10.000 xu paid once: {wallet}')
        await shot(lan, '6-sent', 400)

        # Hoa gets the card on her screen; Minh (the partner) does not
        try:
            await hoa.page.wait_for_selector('#wiDialog[open] .wi-names', timeout=20000)
        except Exception:  # noqa: BLE001
            problems.append('Hoa: no card')
            dbg = await hoa.page.evaluate('''async () => ({due: await fetch('/api/wedinvite').then(r => r.json()), dlg: !!document.querySelector('#wiDialog'),
              open: [...document.querySelectorAll('dialog[open]')].map(d => d.id || d.className), menu: document.documentElement.className,
              res: performance.getEntriesByType('resource').map(e => e.name).filter(n => n.includes('wedinv')),
              gate: await import('/js/v4/break-gate.js').then(m => [m.why(null, {strict: false}), m.turn('wedinvite'), m.turn('zzz')]),
              sheet: document.getElementById('sheet')?.className,
              wn: await import('/js/v4/whatsnew.js').then(m => m.LATEST), seen: (await fetch('/api/state').then(r => r.json())).state.settings.whatsNewSeen})''')
            problems.append(f'Hoa debug: {dbg}')
        text = await hoa.page.locator('#wiDialog[open]').inner_text() if await hoa.page.locator('#wiDialog[open]').count() else ''
        check('Lan Mây' in text and 'Minh Tú' in text and 'Hẹn gặp mọi người' in text and 'Xem lịch cưới' in text, f'Hoa sees the card: {text[:120]!r}')
        await shot(hoa, '7-hoa-card', 900)
        check(not await minh.page.locator('#wiDialog[open]').count(), 'the partner gets no card')
        if text:
            await hoa.page.click('#wiDialog[open] [data-wi=cheer]')
            await hoa.page.wait_for_timeout(1500)
            await shot(hoa, '8-hoa-cheered')
        await hoa.page.reload()
        await hoa.page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await hoa.page.wait_for_timeout(2000)
        await calm(hoa)
        await hoa.page.wait_for_timeout(4000)
        check(not await hoa.page.locator('#wiDialog[open]').count(), 'after a reload the card does not come back')
        me = await api(lan, '/api/wedinvite/me')
        check(me['sent']['cheers'] == 1, f'Lan sees one cheer: {me["sent"]}')
        # the dark theme ("Đêm"): a second neighbour
        tu = await br.player(browser, br.BASE, 'Tu', [], (390, 844), problems)
        await tu.page.emulate_media(color_scheme='dark')
        await tu.page.evaluate("document.documentElement.dataset.theme='dem'")
        await tu.page.wait_for_timeout(1500)
        await calm(tu)
        try:
            await tu.page.wait_for_selector('#wiDialog[open] .wi-names', timeout=20000)
            await shot(tu, '9-tu-card-dark', 900)
        except Exception:  # noqa: BLE001
            problems.append('Tu: no card after loading')
        await browser.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    br.OUT = OUT
    problems, checks = [], []
    with tempfile.TemporaryDirectory(prefix='mnl-wi-', ignore_cleanup_errors=True) as tmp, br.servers(tmp) as (base, db):
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
