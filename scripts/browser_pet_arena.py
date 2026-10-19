"""🐾 Đấu trường pet (game/pet_arena.py, public/js/v4/pet-arena.js): a browser walk-through with real players (dev tool,
needs playwright + chromium).

Two throwaway story-mode servers (MNL_PET_WAR_DEMO=1: demo teams stand in for the bangs). Ten registered accounts are
seeded straight in the database with pets of different ranks; two of them (Lan, Minh) play in Chromium at 390x844,
360x740, 844x390 and 1280x800: the arena home, the team picker, a ranked battle (mid-fight and its result), a
practice challenge, the ladder, the weekly cup, the bang war (pick phase on the first server; on the second the war
started a minute ago: the bracket and a live duel). Also the 2.5D Tiện ích entry. JPEG screenshots, console errors.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_pet_arena.py [out_dir]
"""
import asyncio
import contextlib
import datetime
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg_test_support import test_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_pet_arena_shots'
PY = os.environ.get('MNL_PY', sys.executable)
VN = datetime.timezone(datetime.timedelta(hours=7))


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server(**extra):
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-arena-')
    env = test_env(QUIET='1', PUSH_DISABLED='1', MNL_PET_WAR_DEMO='1', **extra)
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.db')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([PY, 'server.py', '--port', str(port), '--namespace', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:
            if p.poll() is not None:
                break
            time.sleep(0.1)
    try:
        yield base, db, env
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)
        log.close()


SEED = r'''
import sys
from game import accounts
from game import journey as jr
from game import marriage as mr
from game import pets
from game import pet_arena
from game.storage import Store
db, token, name, rank, ip = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
store = Store(db, story=True)
import hashlib
out = accounts.register(store, token, dict(username='u' + hashlib.md5(name.encode()).hexdigest()[:12], password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
tok = out['token']
sid = store.key(tok)
store.transaction(lambda d: d.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))
BREEDS = [('samoyed', 'Mây'), ('bengal', 'Bơ'), ('corgi', 'Mochi'), ('shiba', 'Cốm'), ('ragdoll', 'Na'), ('husky', 'Tôm')]
def fn(s):
    j = s['journey']
    s['name'] = name
    j.update(gender='female', intro=True, life_day=20)
    j['wallet'] = 900000
    k = sum(map(ord, name))
    for i in range(3):
        b, n = BREEDS[(k + i) % len(BREEDS)]
        pets.action(s, 'jr_pet_adopt', {'from': 'shop', 'breed': b, 'coat': 0, 'nick': n, 'confirm': True})
    for i, p in enumerate(j['pets']['list']):
        r = j['petx']['t'][p['id']]
        r['r'] = max(0, min(6, rank - (i == 2)))
        r['fx'] = 'cau_vong' if r['r'] == 6 else ''
mr._mutate(store, {sid: fn})
pet_arena.view(store, tok, store.read(tok)[0], ip)
store.close_pool()
print(tok)
'''

PLAY_WAR = r'''
import sys, time
from game import pet_war
from game.storage import Store
store = Store(sys.argv[1], story=True)
print(pet_war.run_due(store))
store.close_pool()
'''

PICKS = r'''
import sys, time, json
from game import pet_arena as A, pet_war as PW
from game.storage import Store
store = Store(sys.argv[1], story=True)
t = time.time()
week = A.vn_week(t)
def w(db):
    n = 0
    for r in db.execute('SELECT sid, name, snap FROM pet_arena').fetchall():
        team = PW.team_of(db, r['sid'])
        snap = json.loads(r['snap'])
        if team and snap:
            db.execute('INSERT INTO pet_war_picks(week, sid, team_kind, team_id, name, pet, snap, at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                       (week, r['sid'], team[0], team[1], r['name'], snap[0]['id'], json.dumps(snap[0]), t))
            n += 1
    # the housekeeping locked the war before the players were seeded (nobody had a pet out): play it again with them
    db.execute("DELETE FROM pet_war WHERE week=? AND status='cancelled'", (week,))
    return n
print(store.transaction(w))
store.close_pool()
'''

NAMES = ['Lan', 'Minh', 'Hoa', 'Tuấn', 'Linh', 'Quân', 'Mai', 'Hùng', 'Thảo', 'Phong']
ACT = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d||{});b.hidden=true;document.body.append(b);b.click();b.remove();})"
SIZES = ((390, 844), (360, 740), (844, 390), (1280, 800))


def py(code: str, *args, env=None) -> str:
    r = subprocess.run([PY, '-c', code, *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', env=env)
    if r.returncode:
        raise RuntimeError(r.stderr[-3000:])
    return r.stdout.strip().splitlines()[-1]


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    shots = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def player(base, db, env, who, rank, ip, w, h, ui25d='0'):
            phone = w < 900
            ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1, has_touch=phone, locale='vi-VN')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.ui25d','%s');localStorage.setItem('mnl.wn.seen','9.9.9');"
                                      "localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}" % ui25d)
            page = await ctx.new_page()
            page.on('console', lambda m, who=who: m.type == 'error' and errors.append(f'{who}: {m.text}'))
            page.on('pageerror', lambda e, who=who: errors.append(f'{who}: {e}'))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            login = py(SEED, db, token, who, str(rank), ip, env=env)
            await ctx.add_cookies([dict(name='mnl_session', value=login, url=base)])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1500)
            for _ in range(6):
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(300)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            return ctx, page

        async def shot(page, name):
            path = OUT / f'{name}.jpg'
            await page.screenshot(path=str(path), type='jpeg', quality=80)
            shots.append(str(path))

        async def arena(page, tab=None):
            await page.evaluate(ACT, ['petArena', {'tab': tab} if tab else {}])
            await page.wait_for_selector('dialog.pa-sheet[open] .pa-body', timeout=10000)
            await page.wait_for_timeout(900)

        async def tab(page, t):
            await page.click(f'dialog.pa-sheet [data-pa="tab"][data-tab="{t}"]')
            await page.wait_for_timeout(900)

        # ---- server 1: the arena, the cup, the war's pick phase
        with server() as (base, db, env):
            for i, n in enumerate(NAMES[2:]):
                ctx, page = await player(base, db, env, n, 1 + i % 6, f'10.0.0.{i}', 390, 844)
                await ctx.close()
            for w, h in SIZES:
                tag = f'{w}x{h}'
                ctxs = []
                for who, rank, ip in (('Lan', 4, '1.1.1.1'), ('Minh', 3, '2.2.2.2')):
                    nm = who if (w, h) == SIZES[0] else f'{who} {w}'
                    ctxs.append(await player(base, db, env, nm, rank, ip, w, h))
                (ca, a), (cb, b) = ctxs
                await arena(a)
                await shot(a, f'{tag}-1-home')
                await a.click('dialog.pa-sheet [data-pa="team"]')
                await a.wait_for_timeout(600)
                await shot(a, f'{tag}-2-team')
                await a.click('dialog.pa-sheet [data-pa="back"]')
                await a.wait_for_timeout(300)
                await a.click('dialog.pa-sheet [data-pa="go"]')
                await a.wait_for_selector('dialog.pa-sheet .pa-fight', timeout=10000)
                await a.wait_for_timeout(2600)
                await shot(a, f'{tag}-3-fight')
                await a.wait_for_timeout(1700)
                await shot(a, f'{tag}-3b-fight')
                await a.click('dialog.pa-sheet [data-pa="skip"]')
                await a.wait_for_timeout(900)
                await shot(a, f'{tag}-4-result')
                await a.click('dialog.pa-sheet [data-pa="done"]')
                await a.wait_for_timeout(700)
                await tab(a, 'npc')
                await shot(a, f'{tag}-5-npc')
                await a.click('dialog.pa-sheet [data-pa="go"]')
                await a.wait_for_selector('dialog.pa-sheet .pa-fight', timeout=10000)
                await a.wait_for_timeout(1500)
                await shot(a, f'{tag}-6-npc-fight')
                await a.click('dialog.pa-sheet [data-pa="skip"]')
                await a.wait_for_timeout(600)
                await a.click('dialog.pa-sheet [data-pa="done"]')
                await a.wait_for_timeout(600)
                await tab(a, 'rank')
                await shot(a, f'{tag}-7-rank')
                await tab(a, 'cup')
                await shot(a, f'{tag}-8-cup')
                if (w, h) == SIZES[0]:
                    await a.click('dialog.pa-sheet [data-pa="go"]')
                    await a.wait_for_timeout(900)
                    await shot(a, f'{tag}-8b-cup-joined')
                await tab(a, 'war')
                pick = a.locator('dialog.pa-sheet [data-pa="wpet"]')
                if await pick.count():
                    await pick.first.click()
                    await a.wait_for_timeout(300)
                    await a.click('dialog.pa-sheet [data-pa="go"]')
                    await a.wait_for_timeout(900)
                await shot(a, f'{tag}-9-war-pick')
                # Minh watches the replay of the battle he was attacked in
                await arena(b)
                await shot(b, f'{tag}-10-minh-home')
                rep = b.locator('dialog.pa-sheet [data-pa="replay"]')
                if await rep.count():
                    await rep.first.click()
                    await b.wait_for_selector('dialog.pa-sheet .pa-fight', timeout=10000)
                    await b.wait_for_timeout(2200)
                    await shot(b, f'{tag}-11-minh-replay')
                for c, _ in ctxs:
                    await c.close()
            # 2.5D: the Tiện ích entry
            ctx, page = await player(base, db, env, 'Hà', 2, '3.3.3.3', 390, 844, ui25d='1')
            with contextlib.suppress(Exception):
                await page.click('.iso-tools summary', timeout=5000)
                await page.wait_for_timeout(500)
                await page.click('[data-iso-group="life"] summary', timeout=5000)
                await page.wait_for_timeout(500)
            await shot(page, '390x844-12-iso-tools')
            with contextlib.suppress(Exception):
                await page.click('[data-action="petArena"]:visible', timeout=5000)
                await page.wait_for_timeout(1500)
                await shot(page, '390x844-13-iso-arena')
            await ctx.close()

        # ---- server 2: the war started a minute ago (round 1 live, round 2 later)
        now = datetime.datetime.now(VN) - datetime.timedelta(minutes=4)   # round 1 over, round 2 about to start
        when = dict(PET_WAR_DOW=str(now.weekday()), PET_WAR_HOUR=str(now.hour), PET_WAR_MIN=str(now.minute))
        with server(**when) as (base, db, env):
            ctxs = []
            for i, n in enumerate(NAMES):
                ctx, page = await player(base, db, env, n, 1 + i % 6, f'20.0.0.{i}', 390, 844)
                if n in ('Lan', 'Minh'):
                    ctxs.append((ctx, page))
                else:
                    await ctx.close()
            print('picks', py(PICKS, db, env=env))
            print('war', py(PLAY_WAR, db, env=env))
            (ca, a), (cb, b) = ctxs
            await arena(a, 'war')
            await shot(a, '390x844-14-war-bracket')

            async def watch(sel, name, wait=2400):
                m = a.locator(sel)
                if not await m.count():
                    return False
                await m.first.scroll_into_view_if_needed()
                await m.first.click()
                try:
                    await a.wait_for_selector('dialog.pa-sheet .pa-fight', timeout=10000)
                    await a.wait_for_timeout(wait)
                except Exception:   # noqa: BLE001 - say what the page said
                    errors.append('watch: ' + str(await a.evaluate("document.querySelector('dialog.pa-sheet .pa-flash')?.textContent")))
                await shot(a, name)
                return True
            # a finished match: its five duels one after the other
            if await watch('dialog.pa-sheet .pa-match.done:not(:disabled)', '390x844-15-war-replay', 2000):
                with contextlib.suppress(Exception):
                    await a.click('dialog.pa-sheet [data-pa="skip"]', timeout=5000)
                    await a.wait_for_timeout(900)
                    await shot(a, '390x844-15b-war-replay-end')
                await a.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            for _ in range(24):   # round 2 goes live within a few minutes
                await arena(a, 'war')
                if await a.locator('dialog.pa-sheet .pa-match.live').count():
                    await shot(a, '390x844-16-war-live')
                    await watch('dialog.pa-sheet .pa-match.live', '390x844-17-war-live-duel')
                    break
                await a.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await a.wait_for_timeout(10000)
            await b.set_viewport_size(dict(width=844, height=390))
            await arena(b, 'war')
            await shot(b, '844x390-18-war')
            await ca.close()
            await cb.close()
        await browser.close()
    print('\n'.join(shots))
    print('errors:', len(errors))
    for e in errors[:30]:
        print('  ', e[:300])


if __name__ == '__main__':
    asyncio.run(main())
