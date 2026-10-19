#!/usr/bin/env python3
"""⚔️ Bang in real browsers (dev tool; needs playwright + chromium, PostgreSQL through TEST_DATABASE_URL).

Starts the game server and the live service (LIVE_CHAT, LIVE_STREET, LIVE_TOWN) on one disposable database, then:
  * Lan (390×844 phone, 2.5D) founds "Rồng Đỏ" from ⚔️ Bang (the checklist, the form, two taps), checks in, gives;
  * Minh (360×740 phone, 2.5D) finds it, joins, gives 1.000.000 xu (two taps), sees the members;
  * Tú (1280×800 desktop, the old interface) joins from its rail;
  * Lan appoints Minh Phó bang, builds a Kho bang level, buys the badge and the uniform with points, sets a Giờ vàng;
  * the 2.5D map: Minh sees Lan's name tag with the bang line and the uniform; the bang's chat carries the tag;
  * landscape 844×390 and desktop shots of the bang pages.
Screenshots go to OUT (argv[1], else the scratch dir); exit 1 on a failed check, a page error or an HTTP 5xx.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_bang.py [out_dir]
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import free_port, wait_http  # noqa: E402
from pg_test_support import test_env, test_connect, schema_for  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'bang-shots'
PW = 'matkhau-rat-dai'
API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""
SHEET = "() => { const d = document.querySelector('dialog.bg-sheet[open]'); if (!d) return null; return {title: d.querySelector('#bg-title')?.innerText || '', flash: d.querySelector('.sd-flash')?.innerText || '', main: d.querySelector('.sd-main')?.innerText || '', body: d.querySelector('.sd-body')?.innerText || ''}; }"


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.db')
    env = test_env(QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live', ADMIN_USERS='lanmay')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    glog = open(os.path.join(tmp, 'game.log'), 'w')
    game = subprocess.Popen([sys.executable, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env, stdout=glog, stderr=glog)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_STREET='1', LIVE_TOWN='1',
                LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp), LIVE_NEW_SECS='0')
    llog = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([sys.executable, '-m', 'live', '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=llog, stderr=llog)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        glog.close()
        llog.close()
        OUT.mkdir(parents=True, exist_ok=True)
        for name in ('game.log', 'live.log'):
            with contextlib.suppress(OSError):
                (OUT / name).write_text(Path(tmp, name).read_text(encoding='utf-8', errors='replace'), encoding='utf-8')


def mutate(db, sid, fn):
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    try:
        mr._mutate(store, {sid: fn})
    finally:
        store.close_pool()


def sql(db, q, args=()):
    con = test_connect(db)
    try:
        with con:
            cur = con.execute(q, args)
            try:
                return cur.fetchall()
            except Exception:  # noqa: BLE001 - no rows to fetch
                return []
    finally:
        con.close()


class P:
    def __init__(self, ctx, page, name, user, size):
        self.ctx, self.page, self.name, self.user, self.size = ctx, page, name, user, size


async def popups(page):
    for _ in range(8):
        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, [data-x3="close"]:visible, [data-fh-key="giftok"]:visible, [data-iface="new"]:visible')
        if not await b.count():
            break
        with contextlib.suppress(Exception):
            await b.first.click(timeout=1500)
        await page.wait_for_timeout(300)


async def run(base, db, problems, checks):
    from playwright.async_api import async_playwright

    def check(cond, what):
        checks.append(('PASS ' if cond else 'FAIL ') + what)
        if not cond:
            problems.append('check: ' + what)

    async def api(p, path, body=None):
        out = await p.page.evaluate(API, [path, body])
        if out['status'] >= 400:
            raise AssertionError(f'{p.name}: {path} -> {out}')
        return out['data']

    async def shot(p, name):
        await p.page.wait_for_timeout(450)
        await popups(p.page)
        path = OUT / f'{p.size[0]}x{p.size[1]}-{name}.png'
        await p.page.screenshot(path=str(path))
        checks.append(f'SHOT {path}')

    async def sheet(p):
        return await p.page.evaluate(SHEET)

    async def until(p, cond, what, timeout=10.0):
        end = time.monotonic() + timeout
        while True:
            s = await sheet(p)
            if s is not None and await p.page.evaluate(f's => {{ {cond} }}', s):
                return s
            if time.monotonic() > end:
                raise AssertionError(f'{p.name}: {what} (sheet: {json.dumps(s, ensure_ascii=False)[:600]})')
            await asyncio.sleep(0.2)

    async def tap(p, sel):
        await p.page.locator(f'dialog.bg-sheet[open] {sel}').first.click()
        await p.page.wait_for_timeout(250)

    async def act(p, action, data=None):
        await p.page.evaluate("([a,d])=>{const b=document.createElement('button');b.dataset.action=a;for(const [k,v] of Object.entries(d||{}))b.dataset[k]=v;b.hidden=true;document.body.append(b);b.click();b.remove();}", [action, data or {}])

    async def open_bang(p, tab=None):
        await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await act(p, 'bang', {'tab': tab} if tab else None)
        await p.page.wait_for_selector('dialog.bg-sheet[open] .sd-body', timeout=15000)
        await p.page.wait_for_timeout(700)

    async def player(browser, name, user, size, classic=False):
        w, h = size
        phone = w < 600
        ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=phone, is_mobile=phone, device_scale_factor=2 if phone else 1, bypass_csp=True)
        page = await ctx.new_page()
        page.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and problems.append(f'{name} console: {m.text[:300]}'))
        page.on('pageerror', lambda e: problems.append(f'{name} exception: {str(e)[:300]}'))
        page.on('response', lambda r: r.status >= 500 and problems.append(f'{name} HTTP {r.status} {r.url}'))
        await page.goto(base + '/')
        await page.wait_for_selector('#app:not([hidden])', timeout=60000)
        p = P(ctx, page, name, user, size)
        await api(p, '/api/account/register', dict(username=user, password=PW, confirm=PW, display=name))
        sql(db, 'UPDATE accounts SET created_at=? WHERE username=?', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 30 * 86400)), user))
        sid = sql(db, 'SELECT sid FROM accounts WHERE username=?', (user,))[0][0]
        from game import promotion
        from game import whats_new as wn

        def seed(s):
            j = s['journey']
            s['name'] = name
            s['settings'].update(whatsNewSeen=wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST), tutorialDone=True)
            j['interface'] = dict(newInterface=not classic, interfacePromptSeen=True)
            j.update(gender='female' if name in ('Lan', 'Tú') else 'male', intro=True, life_day=20, story=True)
            j['wallet'] = 30_000_000
            j['stats']['max_wallet'] = 30_000_000
            for t in ('m_save200', 'm_save1000'):
                j['titles'].setdefault(t, j['life_day'])
            promotion.record(s, 'milk_tea', True)['rank'] = 1
        mutate(db, sid, seed)
        await page.goto(base + ('/?isometricdebug=1' if not classic else '/'))
        await page.wait_for_selector('#app:not([hidden])', timeout=60000)
        await page.wait_for_timeout(1500)
        await popups(page)
        await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        p.sid = sid
        return p

    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        lan = await player(browser, 'Lan', 'lanmay', (390, 844))
        minh = await player(browser, 'Minh', 'minhpho', (360, 740))
        tu = await player(browser, 'Tú', 'tuxuan', (1280, 800), classic=True)

        # ---- Lan founds a bang ----
        await open_bang(lan)
        await shot(lan, '01-lan-find-empty')
        await tap(lan, '[data-bg="tab"][data-tab="found"]')
        await until(lan, "return s.body.includes('Tài khoản đủ')", 'the founding checklist')
        await lan.page.locator('dialog.bg-sheet[open] input[name="f-name"]').fill('Rồng Đỏ')
        await lan.page.locator('dialog.bg-sheet[open] input[name="f-motto"]').fill('Đoàn kết là sức mạnh')
        await tap(lan, '[data-bg="emoji"][data-e="🐉"]')
        await tap(lan, '[data-bg="color"][data-c="do"]')
        await shot(lan, '02-lan-found-form')
        s = await sheet(lan)
        check('5.000.000' in s['main'], f'the main button says the fee ({s["main"]})')
        await tap(lan, '[data-bg="found"]')
        await tap(lan, '[data-bg="found"]')
        s = await until(lan, "return s.title.includes('Rồng Đỏ')", 'Lan is in her new bang', 15)
        check('Bang chủ' in (await lan.page.locator('dialog.bg-sheet[open] .bg-sub').inner_text()), 'Lan is Bang chủ')
        await shot(lan, '03-lan-home-new')
        await tap(lan, '[data-bg="checkin"]')
        await until(lan, "return s.flash.includes('Điểm danh')", 'Lan checks in')
        await shot(lan, '04-lan-home-checked')

        # ---- Minh finds and joins ----
        await open_bang(minh)
        await until(minh, "return s.body.includes('Rồng Đỏ')", 'Minh sees Rồng Đỏ in the list')
        await shot(minh, '05-minh-find')
        await tap(minh, '[data-bg="join"]')
        await until(minh, "return s.title.includes('Rồng Đỏ')", 'Minh is in')
        await tap(minh, '[data-bg="checkin"]')
        await until(minh, "return s.main.includes('Góp')", 'after the check-in the main button gives')
        await tap(minh, '[data-bg="amount"][data-n="1000000"]')
        await tap(minh, '[data-bg="give"]')
        s = await sheet(minh)
        check('lần nữa' in s['main'], f'1.000.000 xu needs a second tap ({s["main"]})')
        await tap(minh, '[data-bg="give"]')
        await until(minh, "return s.flash.includes('góp') && s.body.includes('1.000.000')", 'Minh gave 1.000.000 xu')
        await shot(minh, '06-minh-gave')
        w = (await api(minh, '/api/bang/me'))['mine']
        check(w['points'] >= 1000 + 20, f'Minh earned points ({w["points"]})')

        # ---- Tú (the old interface) joins ----
        await open_bang(tu)
        await until(tu, "return s.body.includes('Rồng Đỏ')", 'Tú sees the list')
        await tap(tu, '[data-bg="join"]')
        await until(tu, "return s.title.includes('Rồng Đỏ')", 'Tú is in')
        await shot(tu, '07-tu-desktop-home')

        # ---- Lan: roles, fund, facilities, shop, Giờ vàng ----
        await open_bang(lan, 'members')
        await until(lan, "return s.body.includes('Minh')", 'Lan sees Minh')
        pid_minh = (await api(minh, '/api/bang/me'))['mine']['pid']
        await tap(lan, f'[data-bg="sel"][data-pid="{pid_minh}"]')
        await shot(lan, '08-lan-member-actions')
        await tap(lan, f'[data-bg="role"][data-pid="{pid_minh}"][data-role="pho"]')
        await until(lan, "return s.flash.includes('Phó bang')", 'Minh is Phó bang')
        await shot(lan, '09-lan-members')
        for _ in range(2):
            await tap(lan, '[data-bg="tab"][data-tab="home"]')
            await lan.page.locator('dialog.bg-sheet[open] input[data-qty]').fill('9000000')
            await lan.page.locator('dialog.bg-sheet[open] input[data-qty]').press('Enter')
            await lan.page.wait_for_timeout(300)
            await tap(lan, '[data-bg="give"]')
            await tap(lan, '[data-bg="give"]')
            await until(lan, "return s.flash.includes('góp')", 'Lan gave 9.000.000 xu')
        await tap(lan, '[data-bg="tab"][data-tab="build"]')
        await until(lan, "return s.body.includes('Kho bang')", 'the facilities')
        await tap(lan, '[data-bg="build"][data-id="kho"]')
        await tap(lan, '[data-bg="build"][data-id="kho"]')
        await until(lan, "return s.flash.includes('Kho bang')", 'Lan builds the Kho bang')
        await shot(lan, '10-lan-building')
        # time passes: the build is done; a few levels as a bang that played for weeks (Xưởng may, Cổng, Đền vàng)
        bid = (await api(lan, '/api/bang/me'))['mine']['bang']
        sql(db, 'UPDATE bang_facilities SET ready_at=? WHERE bang=? AND target IS NOT NULL', (time.time() - 1, bid))
        for fac, lv in (('xuong_may', 3), ('cong', 3), ('den_vang', 1), ('tuong', 2)):
            sql(db, 'INSERT INTO bang_facilities(bang, fac, level) VALUES(?,?,?) ON CONFLICT(bang, fac) DO UPDATE SET level=excluded.level', (bid, fac, lv))
        sql(db, "UPDATE bang_members SET points=points+2000 WHERE sid=?", (lan.sid,))
        await open_bang(lan, 'build')
        await until(lan, "return s.body.includes('Cấp 1/10')", 'the Kho bang is level 1')
        await shot(lan, '11-lan-facilities')
        await tap(lan, '[data-bg="tab"][data-tab="shop"]')
        await tap(lan, '[data-bg="buy"][data-id="huy"]')
        await until(lan, "return s.flash.includes('Huy hiệu')", 'Lan buys the badge with points')
        await tap(lan, '[data-bg="buy"][data-id="ao"]')
        await until(lan, "return s.flash.includes('Áo đồng phục')", 'Lan buys the uniform')
        await tap(lan, '[data-bg="buy"][data-id="co"]')
        await until(lan, "return s.flash.includes('Cờ bang')", 'Lan buys the flag')
        await tap(lan, '[data-bg="wear"][data-id="ao"][data-style="hoodie"]')
        await until(lan, "return s.flash.includes('mặc')", 'Lan wears the hoodie uniform')
        await shot(lan, '12-lan-shop')
        await tap(lan, '[data-bg="tab"][data-tab="home"]')
        await tap(lan, '[data-bg="ghDay"][data-n="1"]')
        await tap(lan, '[data-bg="ghSet"]')
        await until(lan, "return s.flash.includes('Giờ vàng')", 'Lan sets a Giờ vàng for tomorrow')
        await lan.page.evaluate("document.querySelector('dialog.bg-sheet[open] .bg-gh')?.scrollIntoView({block:'center'})")
        await shot(lan, '13-lan-golden')
        await tap(lan, '[data-bg="tab"][data-tab="rank"]')
        await until(lan, "return s.body.includes('Rồng Đỏ')", 'the week board')
        await shot(lan, '14-lan-rank')
        await tap(lan, '[data-bg="tab"][data-tab="more"]')
        await shot(lan, '15-lan-settings')

        # ---- the map: Minh sees Lan's tag, badge and uniform ----
        for p in (lan, minh):
            await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await p.page.reload()
            await p.page.wait_for_function('!!window.__isoWorld', timeout=60000)
            await p.page.wait_for_timeout(1500)
            await popups(p.page)
            await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            if await p.page.evaluate('__isoWorld.mode') != 'town':
                await p.page.locator('[data-action="isoTown"]').first.click()
        pid_lan = (await api(lan, '/api/bang/me'))['mine']['pid']
        end = time.monotonic() + 20
        peer = None
        while time.monotonic() < end:
            peer = await minh.page.evaluate("(pid)=>(__isoWorld.remotePlayers||[]).find(p=>p.pid===pid)||null", pid_lan)
            if peer and peer.get('tag'):
                break
            await asyncio.sleep(0.3)
        check(bool(peer and 'Rồng Đỏ' in (peer.get('tag') or '') and peer.get('badge') == '🐉'), f'Minh sees Lan on the map with the bang tag and badge ({peer and peer.get("tag")}, {peer and peer.get("badge")})')
        check(bool(peer and peer['look'].get('top') == 'ao_hoodie' and peer['look'].get('tint', {}).get('ao_hoodie') == 'do'), f'Lan wears the bang hoodie in red on the map ({peer and peer["look"]})')
        # walk Minh next to Lan so the tag is on screen
        for p in (lan, minh):
            await popups(p.page)
            await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await minh.page.evaluate("(pid)=>{const w=__isoWorld,p=(w.remotePlayers||[]).find(x=>x.pid===pid);if(p){w.player.x=p.x+1.5;w.player.y=p.y+1.1;w.player.path=[];w.recenter?.();w.zoomBy?.(1.5);w.wake?.();}}", pid_lan)
        await minh.page.wait_for_timeout(2500)
        await popups(minh.page)
        await shot(minh, '16-minh-map-tag')
        await lan.page.evaluate("()=>{__isoWorld.zoomBy?.(1.6);__isoWorld.recenter?.();}")
        await shot(lan, '17-lan-map-uniform')

        # ---- 🚩 the flag on Lan's wall at home ----
        await act(lan, 'jrEnterHome')
        await lan.page.wait_for_timeout(2500)
        flags = await lan.page.locator('.bg-flag').count()
        check(flags >= 1, f'the bang flag hangs in the home of Lan ({flags})')
        await shot(lan, '17b-lan-home-flag')
        await lan.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        # ---- the bang chat carries the tag ----
        ch = (await api(lan, '/api/bang/me'))['mine']['channel']
        await act(minh, 'liveChat', {'ch': ch})
        await minh.page.wait_for_timeout(1500)
        await minh.page.locator('dialog[open] textarea').last.fill('Chào cả bang 🐉')
        await minh.page.locator('dialog[open] .ch-send').last.click()
        await minh.page.wait_for_timeout(1500)
        await shot(minh, '18-minh-bang-chat')
        await act(lan, 'liveChat', {'ch': ch})
        await lan.page.wait_for_timeout(2000)
        chips = await lan.page.locator('dialog[open] .bg-chip').all_inner_texts()
        check(any('Rồng Đỏ' in c and 'Phó' in c for c in chips), f'the chat shows the bang chip beside Minh ({chips})')
        await shot(lan, '19-lan-bang-chat')

        # ---- landscape phone and desktop ----
        await lan.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await lan.page.set_viewport_size(dict(width=844, height=390))
        lan.size = (844, 390)
        await open_bang(lan)
        await shot(lan, '20-lan-landscape-home')
        await tap(lan, '[data-bg="tab"][data-tab="build"]')
        await shot(lan, '21-lan-landscape-build')
        await open_bang(tu, 'members')
        await shot(tu, '22-tu-desktop-members')
        await open_bang(tu, 'shop')
        await shot(tu, '23-tu-desktop-shop')
        # the old interface's rail has the entry
        await tu.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        n = await tu.page.locator('[data-action="bang"]').count()
        check(n >= 1, f'the old interface lists ⚔️ Bang ({n})')
        n = await minh.page.locator('[data-action="bang"]').count()
        check(n >= 1, f'the 2.5D menus list ⚔️ Bang ({n})')
        # ---- the operator's page (ADMIN_USERS=lanmay): every bang, hide / rename ----
        adm = await lan.ctx.new_page()
        adm.on('pageerror', lambda e: problems.append(f'admin exception: {str(e)[:300]}'))
        await adm.set_viewport_size(dict(width=1280, height=800))
        await adm.goto(base + '/admin#bang')
        try:
            await adm.wait_for_selector('[data-act="bgHide"]', timeout=20000)
            await adm.screenshot(path=str(OUT / 'admin-bang.png'))
            checks.append(f'SHOT {OUT / "admin-bang.png"}')
            adm.once('dialog', lambda d: asyncio.ensure_future(d.accept()))
            await adm.locator('[data-act="bgHide"]').first.click()
            await adm.wait_for_selector('[data-act="bgShow"]', timeout=10000)
            hidden = (await api(minh, '/api/bang?list=1'))['list']
            check(not any(c['id'] == bid for c in hidden), 'a hidden bang leaves the list')
            await adm.locator('[data-act="bgShow"]').first.click()
            await adm.wait_for_selector('[data-act="bgHide"]', timeout=10000)
            check(True, 'the operator hides and shows a bang')
        except Exception as e:  # noqa: BLE001 - the admin page is a bonus check
            problems.append(f'admin page: {type(e).__name__}: {str(e)[:200]}')
        await adm.close()
        # the fund never pays out: wallets only went down by what was given and the fee
        rows = sql(db, "SELECT kind, SUM(amount) FROM bang_fund WHERE bang=? GROUP BY kind", (bid,))
        check(all(k in ('give', 'build') for k, _ in rows), f'the ledger has gives and builds only ({rows})')
        await browser.close()


def main():
    problems, checks = [], []
    with tempfile.TemporaryDirectory(prefix='mnl-bang-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db):
        try:
            asyncio.run(run(base, db, problems, checks))
        except AssertionError as e:
            problems.append(str(e))
    for c in checks:
        print(c)
    for p in problems:
        print('PROBLEM', p)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
