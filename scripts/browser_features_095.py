#!/usr/bin/env python3
"""0.9.5 features on a phone (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (like production: no MNL_DEV), seeds one save in its
database (a named character on life day 20 with two weeks of salary, a bank account, a job at the milk tea
shop and a crate that came short), then walks each new feature's happy path on a 390x844 phone:

  whatsnew   "Có gì mới" opens by itself with the 0.9.5 notes; "Thử ngay" opens Nhà của bạn
  wardrobe   Tủ đồ: try on, buy (wallet goes down by the price), wear, work clothes switch, the avatar
  house      Nhà của bạn: rent a room and give it back (deposit back), buy a home with a mortgage,
             pay the next installment, pay it off, sell (money lands in the account)
  bank       a 12-month term deposit with auto-renew
  money      the 💰 chip on the bank, the house and the stock room; "còn thiếu" in a confirm
  claim      a short crate: "Khiếu nại phần thiếu" right in the stock room, refund into the shop fund
  retry      a command answered 503 twice is sent again under "Đang cập nhật máy chủ…", then lands
  toast      a result that chains several notes shows one row per note

After every step it checks the open screen: console errors, failed API calls, horizontal overflow, empty
buttons/headings, "undefined"/"NaN" text, and that the step really changed the game (else: a dead end).
Screenshots of every step go to OUT (default artifacts/features-095). Exits 1 on any problem.

    python scripts/browser_features_095.py [--shots DIR] [--only wardrobe,house] [--width 390 --height 844]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_v04 import OVERFLOW, free_port  # noqa: E402

STEPS = ('whatsnew', 'wardrobe', 'house', 'bank', 'money', 'claim', 'retry', 'toast')

# Visible text problems on the open screen (top dialog, else the page): empty controls/headings, leaked JS values.
PROBE = r"""()=>{
  const open=[...document.querySelectorAll('dialog[open]')],top=open[open.length-1]||document.querySelector('#app');
  const vis=el=>{const r=el.getBoundingClientRect();if(!r.width||!r.height)return false;const s=getComputedStyle(el);return s.visibility!=='hidden'&&s.display!=='none'&&s.opacity!=='0';};
  const out=[];
  for(const el of top.querySelectorAll('button,a[href],h1,h2,h3,h4,label,th,td,dt,dd,summary,.btn')){
    if(!vis(el)||el.closest('details:not([open])>:not(summary)'))continue;
    const text=(el.innerText||'').trim();
    if(text||el.getAttribute('aria-label')||el.title||el.querySelector('svg,img,input,select,canvas,i[class]'))continue;
    out.push('empty '+el.outerHTML.slice(0,90));
  }
  const text=top.innerText||'';
  const m=text.match(/\b(undefined|NaN|null)\b|\[object [A-Za-z]+\]|\$\{/);
  if(m)out.push('leaked "'+m[0]+'" near "'+text.slice(Math.max(0,m.index-40),m.index+20).replace(/\s+/g,' ')+'"');
  return out.slice(0,6);
}"""

STATE = "fetch('/api/state').then(r=>r.json()).then(d=>d.state)"


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-f095-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.sqlite3')
    log_path = os.path.join(tmp, 'server.log')
    log = open(log_path, 'wb')
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--db', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
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
        log.close()
        print(f'server log: {log_path}', file=sys.stderr)


def seed(db: str, token: str) -> None:
    """Life day 20, two weeks of salary (the bank's income check), 4.000 xu in cash + 1.000 in the account,
    hired at the flower shop with a crate that came 2 short."""
    from game import bank as bk
    from game import employment as emp
    from game import inventory as iv
    from game import journey as jr
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        j = s['journey']
        s['name'] = 'Lan'
        j.update(gender='female', intro=True, life_day=6)
        for d in range(6, 20):
            j['life_day'] = d
            jr._wallet(j, 60, 'salary', f'Lương ngày {d}')
        j['life_day'] = 20
        j['wallet'] = 4000
        bk.apply(s, 'jr_bk_open', {})
        bk.apply(s, 'jr_bk_deposit', {'amount': 1000})
        c = s['careers']['florist']
        c['job'] = emp.hired_record('florist')
        c['started'] = True
        s['current'] = 'florist'
        it = iv.catalogue('florist')[0]
        iv.action(s, c, 'florist', 'inv_order', {'item': it['id'], 'qty': 6, 'supplier': iv.suppliers('florist')[0]['id'], 'confirm': True})
        o = iv.inv(c)['orders'][-1]
        o.update(status='received', actual=4)
    mr._mutate_retry(store, {store.key(token): fn}, tries=20)
    store.close_pool()


class Walk:
    def __init__(self, page, out: Path, tag: str):
        self.page, self.out, self.tag = page, out, tag
        self.problems: list[str] = []
        self.n = 0
        self.where = 'boot'
        self.flaky_503 = False   # the retry step answers 503 on purpose
        page.on('console', lambda m: m.type == 'error' and not self._expected(m.text) and self.problem(f'console: {m.text[:200]}'))
        page.on('pageerror', lambda e: self.problem(f'exception: {str(e)[:200]}'))
        page.on('response', lambda r: '/api/' in r.url and r.status >= 500 and not self.flaky_503 and self.problem(f'HTTP {r.status} {r.url}'))

    def _expected(self, text: str) -> bool:
        return 'favicon' in text or (self.flaky_503 and '503' in text)

    def problem(self, text: str) -> None:
        self.problems.append(f'[{self.tag}:{self.where}] {text}')

    def need(self, ok, text: str) -> bool:
        if not ok:
            self.problem('dead end: ' + text)
        return bool(ok)

    async def state(self) -> dict:
        return await self.page.evaluate(STATE)

    async def wait(self, ms: int = 400) -> None:
        await self.page.wait_for_timeout(ms)

    async def check(self, name: str) -> None:
        """Screenshot + screen checks for this step."""
        self.n += 1
        await self.wait(350)
        await self.page.screenshot(path=str(self.out / f'{self.n:02d}-{name}.png'))
        info = await self.page.evaluate(OVERFLOW)
        if info['page'] or info['sheet'] or info['over']:
            self.problem(f'overflow at {name}: {info}')
        for p in await self.page.evaluate(PROBE):
            self.problem(f'{name}: {p}')

    async def click(self, selector: str, what: str, timeout: int = 8000) -> bool:
        try:
            await self.page.wait_for_selector(selector, state='visible', timeout=timeout)
        except Exception:
            self.problem(f'dead end: no {what} ({selector})')
            return False
        el = self.page.locator(selector).first
        await el.scroll_into_view_if_needed()
        await el.click()
        await self.wait(450)
        return True

    async def confirm(self, name: str | None = None) -> bool:
        try:
            await self.page.wait_for_selector('#confirmDialog[open]', timeout=6000)
        except Exception:
            self.problem('dead end: no confirm dialog')
            return False
        if name:
            await self.check(name)
        await self.page.click('#confirmDialog [data-action="confirmYes"]')
        await self.wait(900)
        await self.celebrate()
        return True

    async def celebrate(self) -> None:
        """Title scenes ("Danh hiệu mới") and the what's-new card cover the page until closed."""
        for _ in range(4):
            b = self.page.locator('[data-action="jrSceneClose"]:visible, #wnDialog[open] [data-wn="close"]:visible')
            if not await b.count():
                return
            await self.wait(500)   # the what's-new card ignores a tap in its first 450 ms
            await b.first.evaluate('e=>e.click()')
            await self.wait(450)

    async def close_all(self) -> None:
        await self.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await self.wait(200)

    async def act(self, action: str, **data) -> None:
        """Press the app's own control for `action` (a hidden button with that data-action, like the menu's)."""
        await self.page.evaluate("""([a,d])=>{const b=document.createElement('button');b.type='button';b.hidden=true;b.dataset.action=a;
          for(const [k,v] of Object.entries(d))b.dataset[k]=v;document.querySelector('#app').append(b);b.click();b.remove();}""", [action, data])
        await self.wait(600)

    async def journey(self) -> bool:
        """The journey page (the story player's home)."""
        await self.close_all()
        await self.act('home')
        try:
            await self.page.wait_for_selector('#sheet[open] .jr-home', timeout=8000)
        except Exception:
            self.problem('dead end: the journey page did not open')
            return False
        await self.celebrate()
        return True


async def s_whatsnew(w: Walk) -> None:
    p = w.page
    try:
        await p.wait_for_selector('#wnDialog[open]', timeout=8000)
    except Exception:
        w.problem('dead end: the what\'s-new card did not open by itself')
        return
    await w.check('whatsnew')
    meta = await p.inner_text('#wnDialog .wn-meta')
    items = await p.locator('#wnDialog .wn-body > .wn-list > .wn-item').count()
    w.need('0.9.5' in meta, f'whatsnew shows {meta!r}, not 0.9.5')
    w.need(items >= 6, f'only {items} notes')
    older = await p.locator('#wnDialog [data-wn="older"]').count()
    w.need(older == 0, 'older notes still listed')
    tries = p.locator('#wnDialog .wn-item:has-text("mua nhà") .wn-try')
    if w.need(await tries.count(), 'no "Thử ngay" on the house note'):
        await p.wait_for_timeout(500)
        await tries.first.click()
        await w.wait(900)
        w.need(await p.locator('.hs-sheet[open]').count(), '"Thử ngay" did not open Nhà của bạn')
        await w.check('whatsnew-try-house')
    await w.close_all()


async def s_wardrobe(w: Walk) -> None:
    p = w.page
    if not await w.journey():
        return
    await w.check('journey-home')
    if not await w.click('.jr-wd-chip', 'the "Thay đồ" chip on the journey card'):
        return
    await p.wait_for_selector('.wd-mirror svg', timeout=8000)
    await w.check('wardrobe')
    before = await w.state()
    wallet0 = before['journey']['wallet']
    # Hair: try on the bob (40 xu), buy it.
    await w.click('[data-action="jrWdTab"][data-tab="hair"]', 'the hair tab')
    await w.click('.wd-item[data-item="toc_bob"]', 'the bob hair tile')
    await w.check('wardrobe-try-bob')
    if await w.click('[data-action="jrWdBuy"][data-item="toc_bob"]', 'the buy button'):
        try:
            await p.wait_for_selector('#confirmDialog[open] .mn-confirm', timeout=4000)
        except Exception:
            w.problem('no wallet line in the wardrobe confirm')
        await w.confirm('wardrobe-buy-confirm')
        s = await w.state()
        w.need(s['journey']['wallet'] == wallet0 - 40, f'wallet {wallet0} -> {s["journey"]["wallet"]} after a 40 xu hair cut')
        w.need('toc_bob' in (s.get('wardrobe') or {}).get('owned', []), 'the bob is not in the wardrobe')
        w.need((s.get('wardrobe') or {}).get('look', {}).get('hair') == 'toc_bob', 'the bob is not worn')
        await w.check('wardrobe-bought')
    # A free top: try on and wear.
    await w.click('[data-action="jrWdTab"][data-tab="top"]', 'the top tab')
    await w.click('.wd-item[data-item="ao_thun_xanh"]', 'a free top')
    if await w.click('[data-action="jrWdWear"]', 'the "Mặc bộ này" button'):
        s = await w.state()
        w.need(s['wardrobe']['look']['top'] == 'ao_thun_xanh', 'the free top is not worn')
    # A locked item says why and offers no buy.
    await w.click('.wd-item[data-item="ao_cuoi"]', 'the wedding dress tile')
    w.need(await p.locator('.wd-lock').count(), 'a locked item gives no reason')
    w.need(not await p.locator('[data-action="jrWdBuy"][data-item="ao_cuoi"]').count(), 'a locked item can be bought')
    await w.check('wardrobe-locked')
    await w.click('[data-action="jrWdReset"]', 'the reset button')
    # Work clothes switch.
    uni = (await w.state())['wardrobe']['look']['uniform']
    await p.locator('[data-action="jrWdUniform"]').scroll_into_view_if_needed()
    await p.evaluate("document.querySelector('[data-action=\"jrWdUniform\"]').click()")
    await w.wait(900)
    w.need((await w.state())['wardrobe']['look']['uniform'] != uni, 'the work clothes switch did nothing')
    await w.check('wardrobe-uniform')
    # Back on the journey: the avatar wears the new look.
    await w.click('.wd .jr-back, .jr-back', 'the back button')
    await w.wait(400)
    w.need(await p.locator('#sheet[open] .jr-home').count(), 'back from the wardrobe does not reach the journey')


async def s_house(w: Walk) -> None:
    p = w.page
    if not await w.journey():
        return
    if not await w.click('.jr-house-row', 'the house card on the journey'):
        return
    await p.wait_for_selector('.hs-sheet[open] .hs-market', timeout=10000)
    await w.check('house')
    w.need(await p.locator('.hs-sheet[open] .mn-chip').count(), 'no money chip on Nhà của bạn')
    s0 = await w.state()
    cash0, acc0 = s0['journey']['wallet'], s0['journey']['bank']['balance']
    # Rent the room, then give it back: the deposit comes back.
    if await w.click('.hs-sheet [data-hs="rent"][data-kind="tro_moi"]', 'the rent button'):
        await w.confirm('house-rent-confirm')
        s = await w.state()
        w.need((s['journey']['home'].get('rent') or {}).get('kind') == 'tro_moi', 'renting did not happen')
        w.need(cash0 + acc0 - 60 == s['journey']['wallet'] + s['journey']['bank']['balance'], 'the deposit was not 60 xu')
        await w.check('house-rented')
        if await w.click('.hs-sheet [data-hs="leave"]', 'the leave button'):
            await w.confirm()
            s = await w.state()
            w.need(not s['journey']['home'].get('rent'), 'leaving did not happen')
            w.need(cash0 + acc0 == s['journey']['wallet'] + s['journey']['bank']['balance'], 'the deposit did not come back')
    # Buy the mini apartment with a mortgage.
    if not await w.click('.hs-sheet [data-hs="look"][data-kind="can_ho_mini"]', 'the "Xem & mua" button'):
        return
    await p.wait_for_selector('.hs-sheet .hs-buy', timeout=5000)
    await p.fill('#hs-down', '900')
    await p.dispatch_event('#hs-down', 'change')
    await p.select_option('.hs-buy select[name="months"]', '36')
    await w.check('house-buy')
    await p.locator('.hs-buy [data-hs="sign"]').scroll_into_view_if_needed()
    await w.check('house-buy-sign')
    await w.click('.hs-buy [data-hs="sign"]', 'the sign button')
    await w.confirm('house-buy-confirm')
    try:
        await p.wait_for_selector('.hs-place.own', timeout=8000)
    except Exception:
        w.problem('dead end: buying did not end in the own home')
        return
    s = await w.state()
    own = s['journey']['home']['own']
    w.need(own and own['kind'] == 'can_ho_mini' and own['loan'], 'no home or no mortgage after signing')
    w.need(cash0 + acc0 - 900 - 60 == s['journey']['wallet'] + s['journey']['bank']['balance'], 'the down payment + fee was not 960 xu')
    await w.check('house-bought')
    # Pay the next installment early.
    nxt = own['loan']['next']
    money = s['journey']['wallet'] + s['journey']['bank']['balance']
    if await w.click('.hs-sheet [data-hs="pay"]', 'the pay button'):
        await w.confirm('house-pay-confirm')
        s = await w.state()
        L = s['journey']['home']['own']['loan']
        w.need(L['paid_rows'] == 1, 'the first installment is not paid')
        w.need(money - nxt['amount'] == s['journey']['wallet'] + s['journey']['bank']['balance'], 'the installment took the wrong amount')
        await w.check('house-paid')
    # Pay it off.
    total = s['journey']['home']['own']['loan']['payoff']['total']
    money = s['journey']['wallet'] + s['journey']['bank']['balance']
    if await w.click('.hs-sheet [data-hs="payoff"]', 'the payoff button'):
        await w.confirm('house-payoff-confirm')
        s = await w.state()
        w.need(not s['journey']['home']['own']['loan'], 'the loan is still there after paying it off')
        w.need(money - total == s['journey']['wallet'] + s['journey']['bank']['balance'], 'paying off took the wrong amount')
        await w.check('house-free')
    # Sell: the money lands in the account.
    get = s['journey']['home']['own']['sell']['get']
    acc = s['journey']['bank']['balance']
    if await w.click('.hs-sheet [data-hs="sell"]', 'the sell button'):
        await w.confirm('house-sell-confirm')
        s = await w.state()
        w.need(not s['journey']['home']['own'], 'the home is still owned after selling')
        w.need(s['journey']['bank']['balance'] == acc + get, 'the sale did not land in the account')
        await w.check('house-sold')
    await w.close_all()
    # The journey card after all that.
    await w.journey()
    await p.locator('.jr-house').scroll_into_view_if_needed()
    await w.check('journey-house-card')


async def s_bank(w: Walk) -> None:
    p = w.page
    await w.close_all()
    await w.act('bank')
    try:
        await p.wait_for_selector('.bk-sheet:not(.hs-sheet)[open]', timeout=8000)
    except Exception:
        w.problem('dead end: the bank did not open')
        return
    await w.wait(900)
    await w.celebrate()
    w.need(await p.locator('.bk-sheet:not(.hs-sheet)[open] .mn-chip').count(), 'no money chip on the bank')
    await w.check('bank')
    await w.click('.bk-sheet:not(.hs-sheet) [data-bk="tab"][data-tab="save"]', 'the savings tab', timeout=4000)
    try:
        await p.wait_for_selector('#bk-term', timeout=6000)
    except Exception:
        w.problem('dead end: no term deposit form')
        return
    n0 = len((await w.state())['journey']['bank']['savings']['terms'])
    await p.fill('#bk-save-amt', '200')
    await p.select_option('#bk-term', '60')
    await p.evaluate("(()=>{const x=document.querySelector('#bk-renew');if(x&&!x.checked)x.click();})()")
    await w.wait(400)
    await w.check('bank-term-form')
    await w.click('.bk-sheet:not(.hs-sheet) [data-bk="save"]', 'the deposit button')
    await w.confirm('bank-term-confirm')
    terms = (await w.state())['journey']['bank']['savings']['terms']
    w.need(len(terms) == n0 + 1, 'no new term deposit')
    if terms:
        t = terms[-1]
        w.need(t.get('term') == 60 and t.get('renew') is True, f'the deposit is {t}')
    await p.locator('.bk-term').first.scroll_into_view_if_needed()
    await w.check('bank-term-opened')
    await w.close_all()


async def open_stock(w: Walk) -> bool:
    p = w.page
    await w.close_all()
    await w.act('inventory')
    try:
        await p.wait_for_selector('#sheet[open] .inv-door, #sheet[open] .inv-shorts, #sheet[open] [data-action="v4InvTab"]', timeout=8000)
        return True
    except Exception:
        w.problem('dead end: the stock room did not open')
        return False


async def s_money(w: Walk) -> None:
    p = w.page
    if not await open_stock(w):
        return
    chip = p.locator('#sheet[open] .mn-chip')
    if w.need(await chip.count(), 'no money chip in the stock room'):
        text = await chip.inner_text()
        w.need('Ví' in text and ('Quỹ' in text or 'Két' in text or 'tiệm' in text.lower()), f'chip reads {text!r}')
    await w.check('stock-chip')
    # An order: the confirm repeats the balances.
    first = p.locator('#sheet[open] [data-action="v4Order"][data-item]').first
    if await first.count():
        await first.click()
        await w.wait(500)
        if await w.click('#order-go', 'the order button'):
            try:
                await p.wait_for_selector('#confirmDialog[open] .mn-confirm', timeout=4000)
                await w.check('order-confirm')
            except Exception:
                w.problem('no balance line in the order confirm')
            await p.evaluate("document.querySelector('#confirmDialog [data-action=\"confirmNo\"]')?.click()")
    await w.close_all()


async def s_claim(w: Walk) -> None:
    p = w.page
    if not await open_stock(w):
        return
    card = p.locator('#sheet[open] [data-command="inv_claim"]')
    if not w.need(await card.count(), 'no "Khiếu nại phần thiếu" card on top of the stock room'):
        await w.check('claim-missing')
        return
    await w.check('claim-card')
    fund0 = (await w.state())['careers']['florist']['money']
    await card.first.click()
    await w.wait(600)
    if await p.locator('#confirmDialog[open]').count():
        await w.confirm()
    await w.wait(700)
    c = (await w.state())['careers']['florist']
    w.need(c['money'] > fund0, f'no refund: fund {fund0} -> {c["money"]}')
    w.need(not await p.locator('#sheet[open] .inv-shorts').count(), 'the short card is still there after the claim')
    await w.check('claim-done')
    await w.close_all()


async def s_retry(w: Walk) -> None:
    p = w.page
    hits = {'n': 0}

    async def flaky(route):
        hits['n'] += 1
        if hits['n'] <= 2:   # two misses: the retry lasts ~0,9 s, past the note's 0,4 s delay
            await route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'Máy chủ đang bận', 'code': 'db_unavailable'}))
        else:
            await route.continue_()
    await w.close_all()
    await w.act('jrWardrobe')
    try:
        await p.wait_for_selector('[data-action="jrWdUniform"]', state='attached', timeout=8000)
    except Exception:
        w.problem('dead end: the wardrobe did not open')
        return
    uni = ((await w.state()).get('wardrobe') or {}).get('look', {}).get('uniform', True)
    w.flaky_503 = True
    await p.route('**/api/command', flaky)
    seq0 = uni
    await p.evaluate("document.querySelector('[data-action=\"jrWdUniform\"]').click()")
    seen = False
    for _ in range(20):
        if await p.locator('.net-hold').count():
            seen = True
            await w.check('retry-note')
            break
        await w.wait(100)
    await w.wait(1500)
    await p.unroute('**/api/command')
    w.flaky_503 = False
    w.need(hits['n'] >= 3, f'the command was not sent again (sent {hits["n"]}x)')
    w.need(((await w.state()).get('wardrobe') or {}).get('look', {}).get('uniform', True) != seq0, 'the retried command did not land')
    if not seen:
        w.problem('no "Đang cập nhật máy chủ…" note during the retry')
    w.need(not await p.locator('.net-hold').count(), 'the retry note stays after the command landed')


async def s_toast(w: Walk) -> None:
    p = w.page
    await w.close_all()
    await p.evaluate("""async()=>{const m=await import('/js/toast-lines.js');const box=document.querySelector('#toasts');
      const el=document.createElement('div');el.className='toast';m.fillToast(el,'💵 Thu 100 xu. ✅ Giao thành công. 💛 Bé Vy quý bạn hơn.');box.append(el);}""")
    await w.wait(300)
    rows = await p.locator('.toast.multi .toast-lines li').count()
    w.need(rows == 3, f'multi-note toast shows {rows} rows')
    await w.check('toast-lines')


async def main() -> int:
    from playwright.async_api import async_playwright
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', type=Path, default=ROOT / 'artifacts' / 'features-095')
    ap.add_argument('--only', default='')
    ap.add_argument('--width', type=int, default=390)
    ap.add_argument('--height', type=int, default=844)
    ap.add_argument('--engine', default='chromium', choices=('chromium', 'webkit'))
    a = ap.parse_args()
    only = [x for x in a.only.split(',') if x] or list(STEPS)
    a.shots.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await getattr(pw, a.engine).launch()
            phone = a.width < 700
            ctx = await browser.new_context(viewport=dict(width=a.width, height=a.height), is_mobile=phone and a.engine == 'chromium',
                                            has_touch=phone, device_scale_factor=2 if phone else 1)
            page = await ctx.new_page()
            w = Walk(page, a.shots, f'{a.width}x{a.height}')
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            seed(db, token)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await w.wait(1200)
            for name in STEPS:
                if name not in only:
                    continue
                w.where = name
                if name != 'whatsnew':
                    await w.celebrate()
                t0 = time.time()
                try:
                    await globals()[f's_{name}'](w)
                except Exception as e:  # noqa: BLE001 - a step that throws is a problem, the walk goes on
                    w.problem(f'step failed: {type(e).__name__}: {str(e)[:300]}')
                    with contextlib.suppress(Exception):
                        await page.screenshot(path=str(a.shots / f'fail-{name}.png'))
                print(f'{name}: {time.time() - t0:.1f}s', flush=True)
            problems = w.problems
            await ctx.close()
            await browser.close()
    for p in problems:
        print(p)
    print(f'{len(problems)} problems · shots: {a.shots}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
