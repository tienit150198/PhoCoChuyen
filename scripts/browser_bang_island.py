#!/usr/bin/env python3
"""⚔️ Đảo bang + 🛡️ Bang chiến pet on the real bangs, in real browsers (dev tool; needs playwright + chromium,
PostgreSQL through TEST_DATABASE_URL).

The game server and the live service on one disposable database (MNL_BANG_ISLAND on by default, no demo teams):
  * four accounts seeded with pets; Lan founds 🐉 Rồng Đỏ (Minh joins), Hoa founds 🌊 Cá Xanh (Tuấn joins), with the
    real commands; Rồng Đỏ gets a fund and a few facility levels;
  * Lan (390×844 phone, 2.5D) opens 🏯 Đảo bang from the Bang sheet; Minh (1280×800 desktop, 2.5D) from the menu action:
    both on the island, each sees the other; Lan walks to the Kho bang, ⬆️ Nâng cấp → the confirm with the price → the
    build starts, scaffolding (🚧) for both (Minh's island repaints through the live notice); 🏟️ opens the pet arena;
  * the pet arena's 🛡️ Bang chiến tab shows each player's real bang; the four pick a pet each;
  * the game server restarts with the war's start 4 minutes ago: the bracket Rồng Đỏ vs Cá Xanh is played, the
    result shows, and the winner's war points are in 👑 Xếp hạng tuần.
Screenshots (PNG) go to OUT (argv[1]); exit 1 on a failed check or a page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_bang_island.py [out_dir]
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import free_port, wait_http  # noqa: E402
from pg_test_support import test_env, schema_for  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'bang-island-shots'
VN = datetime.timezone(datetime.timedelta(hours=7))
ACT = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d||{});b.hidden=true;document.body.append(b);b.click();b.remove();})"
fails: list = []
errors: list = []


def check(ok, what, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (f' ({detail})' if detail else ''), flush=True)
    if not ok:
        fails.append(what)


SEED = r'''
import sys, hashlib
from game import accounts, pets, promotion, pet_arena
from game import marriage as mr
from game.storage import Store
db, token, name, rank = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
store = Store(db, story=True)
out = accounts.register(store, token, dict(username='u' + hashlib.md5(name.encode()).hexdigest()[:12], password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
BREEDS = [('samoyed', 'Mây'), ('bengal', 'Bơ'), ('corgi', 'Mochi'), ('shiba', 'Cốm')]
def fn(s):
    j = s['journey']
    s['name'] = name
    j.update(gender='female', intro=True, life_day=20)
    j['wallet'] = 60_000_000
    promotion.record(s, 'milk_tea', True)['rank'] = 1
    k = sum(map(ord, name))
    for i in range(2):
        b, n = BREEDS[(k + i) % len(BREEDS)]
        pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': b, 'coat': 0, 'nick': n, 'confirm': True})
    for p in j['pets']['list']:
        j['petx']['t'][p['id']]['r'] = rank
mr._mutate(store, {sid: fn})
pet_arena.view(store, tok, store.read(tok)[0], '10.0.0.%d' % (sum(map(ord, name)) % 200))
store.close_pool()
print(tok)
'''

BANGS = r'''
import sys, json, secrets
from game import bang
from game.storage import Store
db, lan, minh, hoa, tuan = sys.argv[1:6]
store = Store(db, story=True)
def cmd(tok, action, **p):
    return store.command(tok, 'seed-' + secrets.token_hex(6), store.read(tok)[1], None, action, p)
def mine(tok):
    with store.connect() as d:
        return bang._mine(d, store.key(tok))['bang']
cmd(lan, 'jr_bang_found', name='Rồng Đỏ', emoji='🐉', color='do', motto='Đoàn kết', open=True, confirm=True)
cmd(hoa, 'jr_bang_found', name='Cá Xanh', emoji='🌊', color='navy', motto='Bơi xa', open=True, confirm=True)
red, blue = mine(lan), mine(hoa)
bang.post(store, minh, 'join', dict(bang=red))
bang.post(store, tuan, 'join', dict(bang=blue))
cmd(lan, 'jr_bang_give', bang=red, amount=10_000_000, confirm=True)
cmd(minh, 'jr_bang_give', bang=red, amount=5_000_000, confirm=True)
def w(d):
    for fac, lv in (('dai_sanh', 3), ('kho', 2), ('xuong_may', 4), ('san_pet', 2), ('den_vang', 1), ('tuong', 5), ('cong', 2)):
        d.execute('INSERT INTO bang_facilities(bang, fac, level) VALUES(?,?,?) ON CONFLICT(bang, fac) DO UPDATE SET level=excluded.level', (red, fac, lv))
    d.execute("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, 'san_pet', 1)", (blue,))
    d.execute('UPDATE bangs SET fund=40000000 WHERE id=?', (red,))
store.transaction(w)
store.close_pool()
print(json.dumps([red, blue]))
'''

PLAY_WAR = r'''
import sys
from game import bang_pets, pet_war
from game.storage import Store
store = Store(sys.argv[1], story=True)
print(pet_war.run_due(store))
store.close_pool()
'''


def py(code, *args, env=None):
    r = subprocess.run([sys.executable, '-c', code, *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', env=env)
    if r.returncode:
        raise RuntimeError(r.stderr[-3000:])
    return r.stdout.strip().splitlines()[-1]


@contextlib.contextmanager
def servers(db, tmp, **extra):
    gp, lp = free_port(), free_port()
    env = test_env(QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live', **extra)
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL', 'MNL_PET_WAR_DEMO', 'MNL_BANG_ISLAND', 'MNL_BANG_ISLAND_STUB'):
        env.pop(k, None)
    glog = open(os.path.join(tmp, 'game.log'), 'a')
    game = subprocess.Popen([sys.executable, 'server.py', '--port', str(gp), '--namespace', db], cwd=ROOT, env=env, stdout=glog, stderr=glog)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, DATABASE_URL=env['TEST_DATABASE_URL'], LIVE_CHAT='1', LIVE_STREET='1', LIVE_TOWN='1',
                LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp), LIVE_NEW_SECS='0')
    llog = open(os.path.join(tmp, 'live.log'), 'a')
    live = subprocess.Popen([sys.executable, '-m', 'live', '--schema', schema_for(db)], cwd=ROOT, env=lenv, stdout=llog, stderr=llog)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', env
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        glog.close()
        llog.close()


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='mnl-bisle-')
    db = os.path.join(tmp, 'g.db')
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def open_page(base, w, h, who, login=None):
            phone = w < 900
            ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone, locale='vi-VN')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.ui25d','1');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{who}: {m.text}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {e}'))
            if login:
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=40000)
            return ctx, page

        async def calm(page):
            await page.wait_for_timeout(1200)
            for _ in range(6):
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(300)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

        async def shot(page, name):
            await page.screenshot(path=str(OUT / f'{name}.png'))
            print('SHOT', OUT / f'{name}.png', flush=True)

        # ---- phase 1: the island and the picks
        with servers(db, tmp) as (base, env):
            people = {}
            for who, w, h, rank in (('Lan', 390, 844, 4), ('Minh', 1280, 800, 3), ('Hoa', 390, 844, 4), ('Tuấn', 390, 844, 3)):
                ctx, page = await open_page(base, w, h, who)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                login = py(SEED, db, token, who, str(rank), env=env)
                await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
                people[who] = [ctx, page, login]
            red, blue = json.loads(py(BANGS, db, *(people[n][2] for n in ('Lan', 'Minh', 'Hoa', 'Tuấn')), env=env))
            for who, (ctx, page, _) in people.items():
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=40000)
                await calm(page)
            lan, minh = people['Lan'][1], people['Minh'][1]
            # Lan: Bang sheet → 🏯 Đảo bang
            await lan.evaluate(ACT, ['bang', {}])
            await lan.wait_for_selector('dialog.bg-sheet[open] [data-bg="island"]', timeout=15000)
            await shot(lan, '390x844-01-bang-sheet-island-button')
            await lan.click('dialog.bg-sheet[open] [data-bg="island"]')
            await lan.wait_for_selector('dialog.bisl-scene[open]', timeout=20000)
            await lan.wait_for_function("!document.querySelector('dialog.bisl-scene .bisl-loading')||document.querySelector('dialog.bisl-scene .bisl-loading').hidden||getComputedStyle(document.querySelector('dialog.bisl-scene .bisl-loading')).display==='none'", timeout=30000)
            await lan.wait_for_timeout(2500)
            title = await lan.inner_text('dialog.bisl-scene #bislTitle')
            check(title == 'Rồng Đỏ', 'Lan is on her bang\'s island', title)
            chips = await lan.eval_on_selector_all('dialog.bisl-scene .bisl-facs .bisl-chip', 'els=>els.map(e=>e.innerText.replace(/\\s+/g," ").trim())')
            check(len(chips) == 7 and any('Tượng bang 5' in c for c in chips), 'the seven facilities with the bang\'s levels', '; '.join(chips))
            await shot(lan, '390x844-02-island-lan')
            # Minh from the menu action (desktop)
            await minh.evaluate(ACT, ['bangIsland', {}])
            await minh.wait_for_selector('dialog.bisl-scene[open]', timeout=20000)
            await minh.wait_for_timeout(4000)
            tags = await minh.eval_on_selector_all('dialog.bisl-scene .bisl-tags b', 'els=>els.map(e=>e.innerText)')
            check(any('Lan' in t for t in tags), 'Minh sees Lan on the island', '; '.join(tags))
            await shot(minh, '1280x800-03-island-minh')
            tags = await lan.eval_on_selector_all('dialog.bisl-scene .bisl-tags b', 'els=>els.map(e=>e.innerText)')
            check(any('Minh' in t for t in tags), 'Lan sees Minh on the island', '; '.join(tags))
            # Lan: Kho bang → ⬆️ Nâng cấp → confirm → building
            await lan.click('dialog.bisl-scene [data-visit="kho_bang"]')
            await lan.wait_for_selector('dialog.bisl-scene [data-panel]:not([hidden]) [data-op="nang_cap"]', timeout=10000)
            await lan.wait_for_timeout(1500)
            await shot(lan, '390x844-04-kho-panel')
            await lan.click('dialog.bisl-scene [data-panel] [data-op="nang_cap"]')
            await lan.wait_for_selector('#confirmDialog[open] [data-action="confirmYes"]', timeout=10000)
            await shot(lan, '390x844-05-upgrade-confirm')
            await lan.click('#confirmDialog[open] [data-action="confirmYes"]')
            await lan.wait_for_selector('dialog.bisl-scene [data-panel] .bisl-build', timeout=10000)
            await lan.wait_for_timeout(1500)
            msg = await lan.inner_text('dialog.bisl-scene [data-panel]')
            check('Đang xây lên' in msg and 'cấp 3' in msg, 'the upgrade started from the island', msg.replace('\n', ' ')[:160])
            await shot(lan, '390x844-06-upgrade-building')
            await lan.click('dialog.bisl-scene [data-panel-close]')
            await lan.wait_for_timeout(800)
            await shot(lan, '390x844-07-scaffolding')
            await minh.wait_for_timeout(3000)
            chip = await minh.inner_text('dialog.bisl-scene [data-visit="kho_bang"]')
            check('🚧' in chip, 'Minh\'s island shows the build (live notice)', chip)
            await shot(minh, '1280x800-08-scaffolding-minh')
            # a guest's view of a button that opens a sheet: Lan → 👥 members opens the Bang sheet on top
            await lan.click('dialog.bisl-scene [data-visit="dai_sanh"]')
            await lan.wait_for_selector('dialog.bisl-scene [data-panel] [data-op="thanh_vien"]', timeout=10000)
            await lan.click('dialog.bisl-scene [data-panel] [data-op="thanh_vien"]')
            await lan.wait_for_selector('dialog.bg-sheet[open]', timeout=10000)
            await lan.wait_for_timeout(800)
            await shot(lan, '390x844-09-members-over-island')
            await lan.evaluate("document.querySelector('dialog.bg-sheet[open]')?.close()")
            await lan.click('dialog.bisl-scene [data-visit="san_pet"]')
            await lan.wait_for_selector('dialog.bisl-scene [data-panel] [data-op="dau_truong"]', timeout=10000)
            await lan.wait_for_timeout(600)
            await shot(lan, '390x844-10-san-pet-panel')
            await lan.click('dialog.bisl-scene [data-panel] [data-op="dau_truong"]')
            await lan.wait_for_selector('dialog.pa-sheet[open] .pa-body', timeout=15000)
            await lan.wait_for_timeout(1500)
            head = await lan.inner_text('dialog.pa-sheet .pa-body')
            check('Rồng Đỏ' in head, 'the island\'s 🏟️ opens the bang war tab with the real bang', head[:200].replace('\n', ' '))
            await shot(lan, '390x844-11-war-tab-real-bang')
            await lan.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await minh.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            # everyone picks a pet for the war
            for who in ('Lan', 'Minh', 'Hoa', 'Tuấn'):
                page = people[who][1]
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate(ACT, ['petArena', {'tab': 'war'}])
                await page.wait_for_selector('dialog.pa-sheet[open] [data-pa="wpet"]', timeout=15000)
                await page.click('dialog.pa-sheet [data-pa="wpet"]')
                await page.wait_for_timeout(300)
                await page.click('dialog.pa-sheet [data-pa="go"]')
                await page.wait_for_timeout(1200)
                body = await page.inner_text('dialog.pa-sheet .pa-body')
                want = 'Rồng Đỏ' if who in ('Lan', 'Minh') else 'Cá Xanh'
                check(want in body, f'{who} fields a pet for {want}')
                if who in ('Lan', 'Hoa'):
                    await shot(page, f'{"390x844" if who != "Minh" else "1280x800"}-12-war-pick-{who}')
            for ctx, _, _ in people.values():
                await ctx.close()

        # ---- phase 2: the war started 4 minutes ago
        now = datetime.datetime.now(VN) - datetime.timedelta(minutes=4)
        when = dict(PET_WAR_DOW=str(now.weekday()), PET_WAR_HOUR=str(now.hour), PET_WAR_MIN=str(now.minute))
        with servers(db, tmp, **when) as (base, env):
            print('war played:', py(PLAY_WAR, db, env=dict(env, **when)))
            ctx, lan = await open_page(base, 390, 844, 'Lan', people['Lan'][2])
            await calm(lan)
            await lan.evaluate(ACT, ['petArena', {'tab': 'war'}])
            await lan.wait_for_selector('dialog.pa-sheet[open] .pa-bracket', timeout=15000)
            await lan.wait_for_timeout(1200)
            body = await lan.inner_text('dialog.pa-sheet .pa-body')
            check('Rồng Đỏ' in body and 'Cá Xanh' in body, 'the bracket: Rồng Đỏ vs Cá Xanh', body[:240].replace('\n', ' '))
            check('vô địch' in body, 'a champion is named', '')
            await shot(lan, '390x844-13-war-result')
            m = lan.locator('dialog.pa-sheet .pa-match.done:not(:disabled)')
            if await m.count():
                await m.first.click()
                with contextlib.suppress(Exception):
                    await lan.wait_for_selector('dialog.pa-sheet .pa-fight', timeout=10000)
                    await lan.wait_for_timeout(2500)
                await shot(lan, '390x844-14-war-duel')
            await lan.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await lan.evaluate(ACT, ['bang', {'tab': 'rank'}])
            await lan.wait_for_selector('dialog.bg-sheet[open]', timeout=15000)
            await lan.wait_for_timeout(1500)
            rank = await lan.inner_text('dialog.bg-sheet[open] .sd-body')
            check('Bang chiến pet' in rank, 'the weekly ranking explains the pet war points', rank[:200].replace('\n', ' '))
            await shot(lan, '390x844-15-bang-rank-after-war')
            await ctx.close()
        await browser.close()
    for name in ('game.log', 'live.log'):
        with contextlib.suppress(OSError):
            (OUT / name).write_text(Path(tmp, name).read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    print('errors:', len(errors))
    for e in errors[:30]:
        print('  ', e[:300])
    print('fails:', fails)
    return 1 if fails or errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
