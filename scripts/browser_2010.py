"""💐 Thiệp 20/10 (/2010, game/event2010.py): a browser walk-through (dev tool, needs playwright + chromium, TEST_DATABASE_URL).

Runs the real server on a throwaway namespace. A player registers an account (life day 5) and, on a phone (390×844):
opens /2010, picks direction / theme / stickers, writes, sends (the share panel, the reward row, the queued system gift);
an anonymous reader (no cookie, another context) opens the link: the envelope, the reveal, ❤ thả tim (taps gathered and
stored), a report; the sender's own view shows "Xóa thiệp". Then every theme opened on a phone, the writer on a small
phone (360×740) and desktop (1280×800). Checks: nothing overflows sideways, no page error, the server took each act.

    python scripts/browser_2010.py [out_dir]
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_2010_shots'
os.environ['EV2010_CARDS_PER_MINUTE'] = '100'   # one card per theme in a few seconds
WIDE = '()=>document.documentElement.scrollWidth-innerWidth'


def account(db: str, token: str, life: int = 5, user: str = 'lan_2010') -> str:
    from game import accounts
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    with patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):
        tok = accounts.register(store, token, dict(username=user, password='matkhau-dai-lam', confirm='matkhau-dai-lam', display='Lan'))['token']

    def fn(s):
        s['name'] = 'Lan'
        s['journey'].update(story=True, intro=True, life_day=life)
    mr._mutate(store, {store.key(tok): fn})
    store.close_pool()
    return tok


def rows(db: str, sql: str, args=()):
    from game.storage import Store
    store = Store(db, story=True)
    with store.connect() as c:
        out = [dict(r) for r in c.execute(sql, args).fetchall()]
    store.close_pool()
    return out


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, fails = [], []
    check = lambda ok, what: ok or fails.append(what)
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            host = base.split('//')[1].split(':')[0]
            # the writer: a session from the game page, then an account
            ctx = await browser.new_context(viewport=dict(width=390, height=844), device_scale_factor=2, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text) if 'status of 404' not in m.text else None)
            await page.goto(base + '/2010')
            await page.wait_for_selector('.ev-signin', timeout=20000)
            await page.screenshot(path=str(OUT / '01-signed-out.png'), full_page=True)
            await page.goto(base)
            await page.wait_for_timeout(2500)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            tok = account(db, token)
            await ctx.add_cookies([dict(name='mnl_session', value=tok, domain=host, path='/', httpOnly=True, sameSite='Strict')])
            await page.goto(base + '/2010')
            await page.wait_for_selector('#ev-form', timeout=20000)
            await page.screenshot(path=str(OUT / '02-writer.png'), full_page=True)
            check(await page.evaluate(WIDE) <= 0, 'writer overflows sideways (phone)')
            await page.click('[data-dir="nam_nu"]')
            await page.click('[data-theme-pick="anh_dao"]')
            await page.fill('#ev-to', 'Mai <b>xinh</b>')
            await page.click('[data-act="idea"]')
            for s in ('🌸', '💖', '🎀'):
                await page.click(f'[data-stick="{s}"]')
            await page.fill('#ev-from', 'Anh Nam')
            await page.wait_for_timeout(300)
            await page.locator('#ev-preview').screenshot(path=str(OUT / '03-preview.png'))
            check('<b>' in await page.inner_text('#ev-preview .ev-to'), 'the name is shown as text, not HTML')
            await page.click('#ev-send')
            await page.wait_for_selector('.ev-sent', timeout=15000)
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUT / '04-sent.png'), full_page=True)
            url = await page.input_value('.ev-url input')
            cid = url.rsplit('/', 1)[1]
            rw = rows(db, 'SELECT uid, coins, gift FROM ev2010_rewards')
            check(len(rw) == 1 and rw[0]['coins'] == 100000, f'one reward row: {rw}')
            gift = rows(db, 'SELECT status, coins FROM system_gifts WHERE id=?', (rw[0]['gift'],)) if rw else []
            check(gift and gift[0]['status'] == 'pending', f'the gift is queued: {gift}')
            # more cards: one per theme (the API, as the page does)
            themes = json.loads(await page.evaluate("fetch('/api/2010/me').then(r=>r.text())"))['themes']
            csrf = json.loads(await page.evaluate("fetch('/api/2010/me').then(r=>r.text())"))['csrf']
            ids = {}
            for i, th in enumerate(themes):
                body = dict(op='create', theme=th, direction=['nam_nu', 'nu_nam', 'khac'][i % 3], to='Hoa', text='Chúc em 20/10 thật xinh, thật vui và luôn được yêu thương nhé 💐\nThương em nhiều!', stickers=['💖', '✨', '🌷'][: i % 4])
                res = await page.evaluate("([b,c])=>fetch('/api/2010/cards',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':c},body:JSON.stringify(b)}).then(r=>r.json())", [body, csrf])
                ids[th] = res['card']['id']
            await page.goto(base + '/2010')
            await page.wait_for_selector('.ev-mi', timeout=15000)
            await page.locator('#ev-mine-sec').screenshot(path=str(OUT / '05-mine.png'))
            # the sender's own card: "Xóa thiệp"
            await page.goto(f'{base}/2010/c/{cid}?open')
            await page.wait_for_selector('[data-act="delete"]', timeout=15000)
            # an anonymous reader: no cookie at all
            rctx = await browser.new_context(viewport=dict(width=390, height=844), device_scale_factor=2, has_touch=True, is_mobile=True)
            r = await rctx.new_page()
            r.on('pageerror', lambda e: errors.append(str(e)))
            r.on('console', lambda m: m.type == 'error' and errors.append(m.text) if 'status of 404' not in m.text else None)
            await r.goto(url)
            await r.wait_for_selector('#ev-env', timeout=15000)
            await r.wait_for_timeout(400)
            await r.screenshot(path=str(OUT / '06-envelope.png'))
            await r.click('#ev-env', force=True)
            await r.wait_for_selector('#ev-opened:not([hidden])', timeout=8000)
            await r.wait_for_timeout(2600)
            await r.screenshot(path=str(OUT / '07-opened.png'), full_page=True)
            check(await r.evaluate(WIDE) <= 0, 'reader overflows sideways')
            for _ in range(5):
                await r.click('#ev-heart')
            await r.wait_for_timeout(1500)
            h = rows(db, 'SELECT hearts FROM ev2010_cards WHERE id=?', (cid,))
            check(h and h[0]['hearts'] == 5, f'5 hearts stored: {h}')
            await r.click('[data-act="report"]')
            await r.click('[data-reason="spam"]')
            await r.wait_for_timeout(800)
            check(len(rows(db, 'SELECT 1 FROM ev2010_reports WHERE card=?', (cid,))) == 1, 'the report is stored')
            for th, i in ids.items():
                await r.goto(f'{base}/2010/c/{i}')
                await r.wait_for_selector('#ev-env', timeout=15000)
                await r.click('#ev-env', force=True)
                await r.wait_for_selector('#ev-opened:not([hidden])', timeout=8000)
                await r.wait_for_timeout(2600)
                await r.screenshot(path=str(OUT / f'theme-{th}.png'))
                check(await r.evaluate(WIDE) <= 0, f'{th}: overflows sideways')
            await r.goto(base + '/2010/c/AAAAAAAAAAAA')
            await r.wait_for_selector('.ev-gone', timeout=15000)
            await r.screenshot(path=str(OUT / '08-gone.png'))
            for w, hgt, name in ((360, 740, 'small'), (1280, 800, 'desktop')):
                await page.set_viewport_size(dict(width=w, height=hgt))
                await page.goto(base + '/2010')
                await page.wait_for_selector('#ev-form', timeout=15000)
                await page.wait_for_timeout(500)
                await page.screenshot(path=str(OUT / f'09-writer-{name}.png'), full_page=True)
                check(await page.evaluate(WIDE) <= 0, f'writer overflows sideways ({name})')
            # in the game: the season's card opens once by itself (v4/ev2010.js), the Tiện ích entry, the journey card
            gctx = await browser.new_context(viewport=dict(width=390, height=844), device_scale_factor=2, has_touch=True, is_mobile=True)
            g = await gctx.new_page()
            g.on('pageerror', lambda e: errors.append(str(e)))
            await g.goto(base)
            await g.wait_for_timeout(2500)
            gtok = next(c['value'] for c in await gctx.cookies() if c['name'] == 'mnl_session')
            gtok = account(db, gtok, 4, 'hoa_2010')
            await gctx.add_cookies([dict(name='mnl_session', value=gtok, domain=host, path='/', httpOnly=True, sameSite='Strict')])
            await g.goto(base)
            # what any player answers first on this build: the character (a test save has no gender) and the interface
            for sel in ('text=Nữ', 'text=Lưu và tiếp tục', '[data-interface="new"]'):
                try:
                    await g.click(sel, timeout=15000)
                    await g.wait_for_timeout(800)
                except Exception:  # noqa: BLE001 - not asked
                    pass
            try:   # "Có gì mới" goes first (v4/break-gate.js); a tap in its first 450 ms is ignored
                await g.wait_for_selector('#wnDialog[open]', timeout=20000)
                await g.wait_for_timeout(900)
                await g.click('#wnDialog [data-wn="close"].btn')
            except Exception:  # noqa: BLE001
                pass
            try:
                await g.wait_for_selector('#ev10Dialog[open]', timeout=40000)
                await g.wait_for_timeout(500)
                await g.screenshot(path=str(OUT / '10-game-card.png'))
                check('100.000 xu' in await g.inner_text('#ev10Dialog'), 'the card tells the reward')
                await g.click('#ev10Dialog [data-ev10="close"].btn')
                check(not await g.evaluate("document.getElementById('ev10Dialog').open"), 'Để sau closes it')
                check(await g.evaluate("localStorage.getItem('mnl.ev2010.seen')") == '1', 'seen once on this device')
            except Exception as e:  # noqa: BLE001
                await g.screenshot(path=str(OUT / '10-game-card.png'))
                fails.append(f'the season card did not open: {e}')
            check(await g.locator('[data-action="ev2010"]').count() > 0, 'the Tiện ích entry is there')
            try:
                await g.click('.iso-tools > summary', timeout=8000)
                await g.wait_for_timeout(400)
                await g.screenshot(path=str(OUT / '11-game-tools.png'))
                await g.click('.iso-tools-options [data-action="ev2010"]')
                await g.wait_for_url('**/2010', timeout=15000)
                await g.wait_for_selector('#ev-form', timeout=15000)
            except Exception as e:  # noqa: BLE001
                fails.append(f'Tiện ích → Thiệp 20/10 → /2010: {e}')
            await g.goto(base)
            try:   # the journey home ("Công việc"): the season's line at the top of the first column
                await g.wait_for_selector('.iso-nav', timeout=20000)
                await g.click('.iso-nav [data-action="isoCareers"]', timeout=8000)
                await g.wait_for_selector('.jr-2010', timeout=15000)
                await g.wait_for_timeout(400)
                await g.screenshot(path=str(OUT / '12-game-journey.png'))
            except Exception as e:  # noqa: BLE001
                fails.append(f'the journey card: {e}')
            await g.reload()
            await g.wait_for_timeout(6000)
            check(not await g.evaluate("!!document.getElementById('ev10Dialog')?.open"), 'not again on this device')
            await browser.close()
    print(json.dumps(dict(out=str(OUT), errors=errors[:10], fails=fails), ensure_ascii=False, indent=1))
    return 1 if errors or fails else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
