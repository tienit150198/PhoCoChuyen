#!/usr/bin/env python3
"""🎁 Quà từ Phố Có Chuyện on a phone (dev tool, needs `pip install playwright` + chromium).

A story server like production (MNL_DEV off) and a 390×844 phone. For three players:

* light theme, Vietnamese: grant 100 xu (game/system_gift.py, like scripts/grant_gift.py), load the
  game: the card shows "🎁 +100 xu", the title and the text and the wallet is +100; press
  "Nhận quà 💛": the card closes, the row is 'seen'; reload: no card, the wallet is still +100 and
  Sổ ví has one "Quà từ Phố Có Chuyện" row;
* dark theme ("Đêm"), two gifts: the cards come one after another (1/2, then the second);
* English: the card reads in English.

Every card must fit the screen (no sideways scroll), with no console error. Screenshots go to
--shots (gift-light.png, gift-dark-1.png, gift-dark-2.png, gift-en.png, after-reload.png).

  python scripts/browser_gift.py [--shots DIR] [--engine chromium|webkit]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TITLE = 'Quà xin lỗi từ Phố Có Chuyện'
TEXT = ('Tối qua sau khi cập nhật, game của bạn bị lỗi kết nối vài phút. Phố gửi bạn 100 xu thay lời xin lỗi, '
        'cảm ơn bạn đã kiên nhẫn 💛')
STATE = "fetch('/api/state').then(r=>r.json()).then(d=>d.state)"
FIT = """()=>{const d=document.querySelector('#gfDialog'),r=d.getBoundingClientRect(),b=d.querySelector('[data-gf="ok"]').getBoundingClientRect();
  return {scroll:document.scrollingElement.scrollWidth>innerWidth+1,inside:r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight,
          button:b.bottom<=innerHeight&&b.height>=44,text:d.innerText};}"""
VI = 'ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ'


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    """Like production: the story is on, no AI key, no push. The temporary database goes afterwards."""
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-gift-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL', 'DATABASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.sqlite3')
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--db', db], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
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
        yield base, db
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)
        shutil.rmtree(tmp, ignore_errors=True)


def seed(db: str, token: str, name: str, theme: str = 'kem', lang: str = 'vi') -> None:
    """A player past the first steps and the tour (the card waits for those), in a chosen theme and language."""
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        s['name'] = name
        s['journey'].update(gender='female', intro=True)
        s['settings'].update(tutorialDone=True, uiTheme=theme, lang=lang)
    mr._mutate_retry(store, {store.key(token): fn}, tries=20)
    store.close_pool()


def grant(db: str, token: str, gid: str, coins: int = 100, title: str = TITLE, text: str = TEXT) -> str:
    from game import system_gift as sg
    from game.storage import Store
    store = Store(db, story=True)
    try:
        return sg.grant(store, store.key(token), coins, title, text, gid)['status']
    finally:
        store.close_pool()


def status(db: str, gid: str) -> str | None:
    from game.storage import Store
    store = Store(db, story=True)
    try:
        with store.connect() as c:
            r = c.execute('SELECT status FROM system_gifts WHERE id=?', (gid,)).fetchone()
        return r['status'] if r else None
    finally:
        store.close_pool()


class Run:
    def __init__(self, browser, base: str, db: str, shots: Path, engine: str):
        self.browser, self.base, self.db, self.shots, self.engine = browser, base, db, shots, engine
        self.problems: list[str] = []
        self.tag = ''

    def need(self, ok, text: str) -> bool:
        if not ok:
            self.problems.append(f'[{self.tag}] {text}')
        return bool(ok)

    async def player(self, tag: str, name: str, theme: str = 'kem', lang: str = 'vi'):
        self.tag = tag
        ctx = await self.browser.new_context(viewport=dict(width=390, height=844), is_mobile=self.engine == 'chromium', has_touch=True,
                                             device_scale_factor=2, service_workers='block', locale='vi-VN')
        await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1')}catch(e){}")
        page = await ctx.new_page()
        page.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and self.need(False, f'console: {m.text[:200]}'))
        page.on('pageerror', lambda e: self.need(False, f'exception: {str(e)[:200]}'))
        await page.goto(self.base)
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
        seed(self.db, token, name, theme, lang)
        return ctx, page, token

    async def reload(self, page) -> None:
        await page.reload()
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)

    async def card(self, page, timeout: int = 12000) -> bool:
        """Wait for the gift card (a "Có gì mới" card first is closed, as a player would)."""
        t0 = time.time()
        while time.time() - t0 < timeout / 1000:
            if await page.locator('#gfDialog[open]').count():
                await page.wait_for_timeout(700)   # the pop animation, and the tap guard
                return True
            if await page.locator('#wnDialog[open]').count():
                await page.wait_for_timeout(600)
                await page.locator('#wnDialog .wn-foot [data-wn="close"]').click()
            await page.wait_for_timeout(200)
        return False

    async def fits(self, page, what: str) -> dict:
        info = await page.evaluate(FIT)
        self.need(not info['scroll'], f'{what}: the page scrolls sideways')
        self.need(info['inside'], f'{what}: the card is not fully on screen')
        self.need(info['button'], f'{what}: "Nhận quà" is off screen or too small')
        return info

    async def light(self) -> None:
        ctx, page, token = await self.player('light', 'Lan')
        w0 = (await page.evaluate(STATE))['journey']['wallet']
        self.need(grant(self.db, token, 'sorry-browser-1') == 'created', 'grant did not create the gift')
        await self.reload(page)
        if not self.need(await self.card(page), 'no gift card after the load'):
            await page.screenshot(path=str(self.shots / 'fail-light.png'))
            return await ctx.close()
        info = await self.fits(page, 'light')
        for part in ('+100 xu', TITLE, 'kiên nhẫn', 'Nhận quà 💛'):
            self.need(part in info['text'], f'the card lacks {part!r}: {info["text"]!r}')
        st = await page.evaluate(STATE)
        self.need(st['journey']['wallet'] == w0 + 100, f'wallet {st["journey"]["wallet"]}, expected {w0 + 100}')
        chip = (await page.inner_text('#topbar .hud-wallet')).replace('\n', ' ')
        self.need(str(w0 + 100) in chip.replace('.', ''), f'the wallet chip reads {chip!r}, expected {w0 + 100}')
        await page.screenshot(path=str(self.shots / 'gift-light.png'))
        await page.locator('#gfDialog [data-gf="ok"]').click()
        await page.wait_for_timeout(700)
        self.need(not await page.locator('#gfDialog[open]').count(), 'the card stays open after "Nhận quà"')
        for _ in range(20):
            if status(self.db, 'sorry-browser-1') == 'seen':
                break
            await page.wait_for_timeout(150)
        self.need(status(self.db, 'sorry-browser-1') == 'seen', f'the gift is {status(self.db, "sorry-browser-1")!r} after "Nhận quà"')
        await self.reload(page)
        await page.wait_for_timeout(3000)
        self.need(not await page.locator('#gfDialog[open]').count(), 'the card came back after a reload')
        boot = await page.evaluate("fetch('/api/bootstrap?lite=1').then(r=>r.json())")
        self.need(boot.get('gifts') == [], f'bootstrap still lists {boot.get("gifts")}')
        st = boot['state']
        self.need(st['journey']['wallet'] == w0 + 100, f'after the reload the wallet is {st["journey"]["wallet"]}, expected {w0 + 100}')
        rows = [h for h in st['journey']['history'] if h['label'] == '🎁 Quà từ Phố Có Chuyện']
        self.need(len(rows) == 1 and rows[0]['amount'] == 100, f'Sổ ví rows: {rows}')
        await page.screenshot(path=str(self.shots / 'after-reload.png'))
        await ctx.close()

    async def dark(self) -> None:
        ctx, page, token = await self.player('dark', 'Minh', theme='dem')
        grant(self.db, token, 'sorry-browser-2a')
        grant(self.db, token, 'sorry-browser-2b', coins=20, title='Cảm ơn bạn', text='Cảm ơn bạn đã góp ý cho phố 💛')
        await self.reload(page)
        if not self.need(await self.card(page), 'no gift card after the load'):
            return await ctx.close()
        self.need(await page.evaluate("document.documentElement.dataset.theme") == 'dem', 'the dark theme is not on')
        first = await self.fits(page, 'dark 1/2')
        self.need('+100 xu' in first['text'] and '1/2' in first['text'], f'first card: {first["text"]!r}')
        await page.screenshot(path=str(self.shots / 'gift-dark-1.png'))
        await page.locator('#gfDialog [data-gf="ok"]').click()
        await page.wait_for_timeout(900)
        self.need(await page.locator('#gfDialog[open]').count(), 'the second card did not follow')
        second = await self.fits(page, 'dark 2/2')
        self.need('+20 xu' in second['text'] and 'Cảm ơn bạn' in second['text'] and '1/1' not in second['text'], f'second card: {second["text"]!r}')
        await page.screenshot(path=str(self.shots / 'gift-dark-2.png'))
        await page.locator('#gfDialog [data-gf="ok"]').click()
        await page.wait_for_timeout(700)
        self.need(not await page.locator('#gfDialog[open]').count(), 'a card stays after the last "Nhận quà"')
        await ctx.close()

    async def english(self) -> None:
        ctx, page, token = await self.player('en', 'Lan', lang='en')
        grant(self.db, token, 'sorry-browser-3')
        await self.reload(page)
        if not self.need(await self.card(page), 'no gift card after the load'):
            return await ctx.close()
        info = await self.fits(page, 'en')
        text = info['text']
        self.need('+100 coins' in text and 'Accept gift' in text and 'patience' in text, f'English card: {text!r}')
        left = [w for w in text.split() if any(ch in VI for ch in w.lower()) and w not in ('Phố', 'Có', 'Chuyện')]
        self.need(not left, f'Vietnamese left on the English card: {left}')
        await page.screenshot(path=str(self.shots / 'gift-en.png'))
        await ctx.close()


async def main() -> int:
    from playwright.async_api import async_playwright
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', type=Path, default=ROOT / 'artifacts' / 'gift')
    ap.add_argument('--engine', default='chromium', choices=('chromium', 'webkit'))
    a = ap.parse_args()
    a.shots.mkdir(parents=True, exist_ok=True)
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await getattr(pw, a.engine).launch()
            run = Run(browser, base, db, a.shots, a.engine)
            for step in (run.light, run.dark, run.english):
                t0 = time.time()
                try:
                    await step()
                except Exception as e:  # noqa: BLE001 - a step that throws is a problem, the others still run
                    run.need(False, f'step failed: {type(e).__name__}: {str(e)[:300]}')
                print(f'{step.__name__}: {time.time() - t0:.1f}s', flush=True)
            await browser.close()
    for p in run.problems:
        print(p)
    print(f'{len(run.problems)} problems · shots: {a.shots}')
    return 1 if run.problems else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
