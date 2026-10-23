"""🪽 Cánh on Bảng xếp hạng (game/wing_lb.py, owner 23/10 "có hạng cánh nữa nhé, xếp hạng cánh ấy"): a browser walk-through
(dev tool, needs playwright + chromium).

Runs the real app on a throwaway story-mode server and seeds it straight in its database: fourteen accounts (two with 23–24 letter names without a space) on the 🪽
board (a Huyền thoại on top, SSS, SS … down to D), the weekly titles refreshed, and the viewer (Lan) with a few wings of
her own, ranked outside the top 10. At 390x844 light and dark, and 1280x900: the 🪽 tab (the podium of the top 3 with
each best wing in its tier's colour, the rows, "Bạn" pinned), then 🛍️ Cửa hàng → 🪽 Cánh, its "🏆 Xếp hạng cánh" link
opening the board. Fails on a console error, a page error or a horizontal scroll.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_wing_lb.py [out_dir]
"""
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_gadgets_classic import server, ROOT, PY  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'output' / 'playwright' / 'wing_lb'

SEED_OTHERS = r'''
import json, sys
from game import accounts, lb_titles as lbt, wing_lb as WL
from game.storage import Store
store = Store(sys.argv[1], story=True)
people = [('Thiên Thần Phố Núi', 'phuong', [0, 2, 1, 3, 2, 1, 2, 1]), ('RồngBayRấtCaoTrênPhốNúi', 'rong', [3, 2, 0, 1, 0, 2, 3, 0]),
          ('Cô Tiên Có Tên Thật Dài', 'tien', [5, 1, 1, 0, 3, 4, 0, 0]), ('Dơi Đêm', 'doi', [0, 0, 0, 2, 4, 1, 0, 0]),
          ('Bướm Xinh', 'buom', [6, 2, 0, 0, 5, 0, 0, 0]), ('Mây Trắng', 'thien_than', [2, 2, 3, 3, 1, 0, 0, 0]),
          ('Hạc Giấy', 'tien', [0, 1, 0, 4, 0, 0, 0, 0]), ('Phượng Lửa', 'phuong', [1, 0, 2, 2, 0, 0, 0, 0]),
          ('Cánh Cụt', 'doi', [3, 3, 3, 0, 0, 0, 0, 0]), ('Gió Lào', 'rong', [0, 6, 1, 0, 0, 0, 0, 0]),
          ('Sẻ Nâu', 'buom', [4, 2, 1, 0, 0, 0, 0, 0]), ('Én Bạc', 'thien_than', [9, 1, 0, 0, 0, 0, 0, 0]),
          ('Chim Non', 'buom', [3, 1, 0, 0, 0, 0, 0, 0]), ('WWWWWWWWWWWWWWWWWWWWWWWW', 'tien', [2, 0, 0, 0, 0, 0, 0, 0])]
accounts.hash_password = lambda pw: 'scrypt$test$' + pw
for i, (name, k, n) in enumerate(people):
    tok, _, _ = store.session()
    out = accounts.register(store, tok, dict(username=f'wing{i:02d}', password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))
    sid = store.key(out['token'])
    best = max(r for r, c in enumerate(n) if c)
    pts = sum(WL.POINTS[r] * c for r, c in enumerate(n))
    store.transaction(lambda db: db.execute('INSERT INTO wing_board(sid, pts, best, k, n, at) VALUES(?,?,?,?,?,?)',
                                            (sid, pts, best, k, json.dumps(n), 1000.0 + i)))
store.transaction(lambda db: db.execute("DELETE FROM leaderboard_meta WHERE k='weekly'"))
lbt._done.clear()
print(lbt.refresh(store))
store.close_pool()
'''
SEED_ME = r'''
import sys
from game import marriage as mr, pets, wings as W, wing_lb as WL, whats_new as wn
from game.storage import Store
db, token, theme = sys.argv[1], sys.argv[2], sys.argv[3]
store = Store(db, story=True)
def fn(s):
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, life_day=20)
    j['wallet'] = 5000000
    s['settings'].update(uiTheme=theme, tutorialDone=True, whatsNewSeen=wn.LATEST)
    j['interface'] = dict(newInterface=False, interfacePromptSeen=True)
    pets.action(s, 'jr_pet_wing_buy', {'style': 'thien_than', 'qty': 5, 'confirm': True})
    for i, x in enumerate(W.get(s)['own']):
        x['r'] = (2, 1, 1, 0, 0)[i]
mr._mutate(store, {store.key(token): fn})
sid = store.key(token)
s = store.read(token)[0]
store.transaction(lambda db: WL.write(db, sid, s, 2000.0))
store.close_pool()
'''
WIDE = "document.documentElement.scrollWidth-document.documentElement.clientWidth"
REGISTER = """async ([u, pw]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch('/api/account/register', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf},
    body: JSON.stringify({username: u, password: pw, confirm: pw, display: 'Lan'})});
  return r.status;
}"""
CLICK = "(([a,d])=>{const b=document.createElement('button');b.dataset.action=a;Object.assign(b.dataset,d);b.hidden=true;document.body.append(b);b.click();b.remove();})"


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, fails = [], []

    def check(ok, what):
        print(('ok  ' if ok else 'FAIL'), what, flush=True)
        if not ok:
            fails.append(what)

    with server() as (base, db):
        subprocess.run([PY, "-c", SEED_OTHERS, db], cwd=ROOT, check=True)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for i, (w, h, theme) in enumerate(((390, 844, 'kem'), (390, 844, 'dem'), (1280, 900, 'kem'))):
                tag = f'{w}x{h}-{"dark" if theme == "dem" else "light"}'
                phone = w < 500
                ctx = await browser.new_context(viewport=dict(width=w, height=h), device_scale_factor=2 if phone else 1,
                                                has_touch=phone, is_mobile=phone)
                await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.tut.tips','done')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m, t=tag: m.type == 'error' and errors.append(f'{t}: {m.text}'))
                page.on('pageerror', lambda e, t=tag: errors.append(f'{t}: {e}'))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                status = await page.evaluate(REGISTER, [f'lanwing{i}', 'matkhau-dai-lam'])
                check(status == 200, f'{tag}: an account (status {status})')
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                subprocess.run([PY, '-c', SEED_ME, db, token, theme], cwd=ROOT, check=True)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(2000)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")

                async def shot(name):
                    await page.wait_for_timeout(600)
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#confirmDialog)').forEach(d=>d.close())")
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))
                    check(await page.evaluate(WIDE) <= 0, f'{tag} {name}: no horizontal scroll')

                await page.evaluate(CLICK, ['rank', {'board': 'wings'}])
                await page.wait_for_selector('#sheet[open] .lb-wpod', timeout=15000)
                check(await page.locator('#sheet [data-action="lbKind"][data-kind="wings"][aria-selected="true"]').count() == 1,
                      f'{tag}: the 🪽 tab is on')
                await shot('1-top')
                pod = await page.locator('#sheet .lb-wpod .lb-pod-card').count()
                check(pod == 3, f'{tag}: a podium of three ({pod})')
                icons = await page.locator('#sheet .lb-wpod svg.wing-icon').count()
                check(icons == 3, f'{tag}: each podium card draws its wing ({icons})')
                me = await page.inner_text('#sheet .lb-me')
                check('Hạng' in me and '🪽' in me, f'{tag}: Bạn pinned with a rank')
                titles = await page.locator('#sheet .lb-wpod .lb-held').count()
                check(titles == 3, f'{tag}: the top 3 hold their weekly titles ({titles})')
                await page.evaluate("document.querySelector('#sheet .lb-wpod').scrollIntoView({block:'start'})")
                await shot('2-podium')
                await page.evaluate("document.querySelector('#sheet .lb-wlist').scrollIntoView({block:'start'})")
                await shot('3-rows')
                rows = await page.locator('#sheet .lb-wlist .lb-wrow').count()
                check(rows == 12, f'{tag}: the rows after the podium ({rows})')
                wide = await page.evaluate("[...document.querySelectorAll('#sheet .lb-wpod .lb-pod-card, #sheet .lb-wrow, #sheet .lb-me')].filter(e=>e.scrollWidth>e.clientWidth+1).length")
                check(wide == 0, f'{tag}: no card or row wider than its box ({wide})')
                await page.evaluate("document.querySelector('#sheet .lb-wlist .lb-wrow:last-child').scrollIntoView({block:'end'})")
                await shot('5-long-name')
                if i == 0:   # the link from 🛍️ Cửa hàng → 🪽 Cánh
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.evaluate(CLICK, ['jrAccShop', {'tab': 'wing'}])
                    link = page.locator('#sheet [data-action="rank"][data-board="wings"]')
                    await link.first.wait_for(state='attached', timeout=15000)
                    await link.first.scroll_into_view_if_needed()
                    await shot('4-shop-link')
                    await link.first.click()
                    await page.wait_for_selector('#sheet[open] .lb-wpod', timeout=15000)
                    check(True, f'{tag}: 🏆 Xếp hạng cánh opens the board')
                await ctx.close()
            await browser.close()
    for e in errors:
        print('ERR ', e)
    print(f'{len(fails)} failed, {len(errors)} errors · shots in {OUT}')
    sys.exit(1 if fails or errors else 0)


if __name__ == '__main__':
    asyncio.run(main())
