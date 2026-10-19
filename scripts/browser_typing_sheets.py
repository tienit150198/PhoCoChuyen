#!/usr/bin/env python3
"""⌨️ Typing in a sheet while the town goes on (owner 21/10: "gõ text ở phát lì xì thì bị tắt rồi scroll là sao, coi cái
khác có bị k"). Dev tool: needs playwright + a Chromium (or Chrome: BROWSER_CHANNEL=chrome), the live service's
websockets, PostgreSQL through TEST_DATABASE_URL.

Starts the game server and the live service on one disposable database. Lan (390×844 phone, touch) opens each sheet
that has a text field, taps the field and types slowly while the town goes on around her:
  * Minh gives 🧧 lì xì and Hà grabs the envelopes (live `lixi` / `lixi_upd` frames on every page),
  * Lan's own state moves every 2 s (the wallet, as when her staff earn: every keyed 'state' listener redraws).
After each key the field must still have focus (the phone keyboard would have closed), at the end it holds what was
typed, the field was never thrown away, and the sheet did not scroll by itself.
Exit 1 on a failed check, a page error or an HTTP 5xx.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_typing_sheets.py [only,these] [--secs 12]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
OUT = Path(tempfile.gettempdir()) / 'typing-sheets'
_argv, sys.argv = sys.argv, [sys.argv[0], str(OUT)]   # browser_bang reads its log folder from argv[1]
import browser_bang as bb  # noqa: E402  (servers, sql, mutate, popups, API)
sys.argv = _argv

# name, action, data, taps before the field (selectors inside the sheet; '@…': anywhere on the page), the field, the sheet
SHEETS = [
    ('lixi-text', 'lixi', {'tab': 'give'}, [], 'input[name="wtext"]', 'dialog.lxi-sheet'),
    ('lixi-total', 'lixi', {'tab': 'give'}, [], 'input[name="total"]', 'dialog.lxi-sheet'),
    ('garage-plate', 'garage', {}, ['[data-gr="look"]'], '#gr-plate', 'dialog.gr-sheet'),
    ('pets-nick', 'pets', {'tab': 'adopt'}, ['[data-pt="shelter"]:not([disabled])'], 'input[name="nick"]', 'dialog.pt-sheet'),
    ('spend-chua', 'spendChua', {}, ['@[data-cv="donate"]'], 'input[name="amount"]', 'dialog.sd-sheet'),
    ('lux-tiec', 'luxTiec', {}, [], '.lx-typed input', 'dialog.lx-sheet'),
    ('lux-mtq', 'luxMtq', {}, ['[data-lx="give"][data-id="thu_vien"]'], 'input[name="amount"]', 'dialog.lx-sheet'),
    ('bank-amount', 'bank', {}, ['[data-bk="open"]', '@#confirmDialog[open] [data-action="confirmYes"]'], '#bk-amt', 'dialog.bk-sheet'),
    # already safe before 21/10 (morph / their own focus keeper): kept in the sweep so they stay that way
    ('gopy-text', 'gopy', {}, [], '#fb-text', 'dialog#sheet'),
    ('bang-name', 'bang', {}, ['[data-bg="tab"][data-tab="found"]'], 'input[name="f-name"]', 'dialog.bg-sheet'),
    ('chat-town', 'liveChat', {}, [], '.ch-compose textarea', 'dialog.chat-sheet'),
]
# Cả phố stays at its newest message when one comes in (a lì xì card): that list scrolls on purpose, the field is below it
SCROLLS = {'chat-town'}

WATCH = r"""
(() => {
  if (window.__tw) return;
  const W = window.__tw = {lost: [], scroll: [], api: null};
  const de = EventTarget.prototype.dispatchEvent;
  EventTarget.prototype.dispatchEvent = function (e) {
    if (e?.type === 'state' && typeof this.command === 'function') W.api = this;
    return de.call(this, e);
  };
  W.arm = (dialog, field) => {
    const d = document.querySelector(dialog + '[open]'), el = d?.querySelector(field);
    W.d = d; W.el = el; W.lost = []; W.scroll = [];
    W.body = d?.querySelector('.sd-body, .sheet-body, [class$="-body"]') || d;
    W.top = W.body?.scrollTop || 0; W.y = window.scrollY;
    clearInterval(W.timer);
    W.timer = setInterval(() => {
      if (!W.el) return;
      if (!W.el.isConnected) W.lost.push('removed');
      else if (document.activeElement !== W.el) W.lost.push('blur:' + (document.activeElement?.tagName || 'none'));
      const b = W.d.querySelector('.sd-body, .sheet-body, [class$="-body"]') || W.d, t = b.scrollTop;
      if (Math.abs(t - W.top) > 40 || Math.abs(window.scrollY - W.y) > 40) W.scroll.push([W.top, t, window.scrollY]);
      W.top = t; W.y = window.scrollY;
    }, 40);
    return Boolean(el);
  };
  W.bump = () => {
    const a = W.api; if (!a?.state?.journey) return false;
    const j = a.state.journey;
    a.accept({state: {...a.state, journey: {...j, wallet: (j.wallet || 0) + 1000}}, revision: a.revision});
    return true;
  };
  W.done = () => { clearInterval(W.timer); return {lost: [...new Set(W.lost)], scroll: W.scroll, value: W.el?.value ?? null, connected: !!W.el?.isConnected}; };
})();
"""

GIVE = """async () => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const st = await fetch('/api/state').then(r => r.json());
  const r = await fetch('/api/command', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf},
    body: JSON.stringify({request_id: crypto.randomUUID(), expected_revision: st.revision, career: st.state.current || st.state.focus,
      action: 'jr_lixi_give', payload: {total: 100000, n: 5, confirm: true}})});
  return r.status;
}"""


async def run(base, db, args, problems, checks):
    from playwright.async_api import async_playwright

    def check(cond, what):
        checks.append(('PASS ' if cond else 'FAIL ') + what)
        if not cond:
            problems.append('check: ' + what)

    async def api(page, path, body=None):
        return (await page.evaluate(bb.API, [path, body]))['data']

    async with async_playwright() as pw:
        channel = os.environ.get('BROWSER_CHANNEL') or None
        browser = await pw.chromium.launch(**({'channel': channel} if channel else {}))

        async def player(name, user, watch=False):
            ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2, bypass_csp=True)
            if watch:
                await ctx.add_init_script(WATCH)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: problems.append(f'{name} exception: {str(e)[:300]}'))
            if os.environ.get('TYPING_DEBUG'):
                page.on('console', lambda m: m.type in ('warning', 'error') and print(f'{name} console {m.type}: {m.text[:300]}'))
            page.on('response', lambda r: r.status >= 500 and problems.append(f'{name} HTTP {r.status} {r.url}'))
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await page.evaluate(bb.API, ['/api/account/register', dict(username=user, password=bb.PW, confirm=bb.PW, display=name)])
            bb.sql(db, 'UPDATE accounts SET created_at=? WHERE username=?', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 30 * 86400)), user))
            sid = bb.sql(db, 'SELECT sid FROM accounts WHERE username=?', (user,))[0][0]
            from game import whats_new as wn

            def seed(s):
                j = s['journey']
                s['name'] = name
                s['settings'].update(whatsNewSeen=wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST), tutorialDone=True)
                j['interface'] = dict(newInterface=True, interfacePromptSeen=True)
                j.update(gender='female', intro=True, life_day=20, story=True)
                j['wallet'] = 300_000_000
                j['stats']['max_wallet'] = 300_000_000
                for t in ('m_save200', 'm_save1000'):   # no "Danh hiệu mới" scene over the sheet when the wallet moves
                    j['titles'].setdefault(t, j['life_day'])
            bb.mutate(db, sid, seed)
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await page.wait_for_timeout(2000)
            await bb.popups(page)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            return page

        lan = await player('Lan', 'lanmay', watch=True)
        minh = await player('Minh', 'minhpho')
        ha = await player('Hà', 'havi')

        stop = asyncio.Event()

        async def town():   # Minh gives, Hà grabs: lixi + lixi_upd frames on Lan's page
            while not stop.is_set():
                await minh.evaluate(GIVE)
                await asyncio.sleep(1.2)
                for p in (await api(ha, '/api/lixi')).get('packets') or []:
                    if p.get('left') and not stop.is_set():
                        await api(ha, '/api/lixi/grab', {'id': p['id']})
                        await asyncio.sleep(0.6)
                await asyncio.sleep(2.5)

        async def wallet():   # Lan's state moves (her staff earn)
            while not stop.is_set():
                await asyncio.sleep(2)
                await lan.evaluate('() => window.__tw.bump()')

        bg = [asyncio.create_task(town()), asyncio.create_task(wallet())]
        only = set(args.only.split(',')) if args.only else None
        try:
            for name, action, data, taps, field, dialog in SHEETS:
                if only and name not in only:
                    continue
                await lan.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await lan.evaluate("([a,d])=>{const b=document.createElement('button');b.dataset.action=a;for(const [k,v] of Object.entries(d||{}))b.dataset[k]=v;b.hidden=true;document.body.append(b);b.click();b.remove();}", [action, data])
                try:
                    for sel in taps:   # a tap from script: a lì xì chip / rain may lie over the sheet
                        sel = sel[1:] if sel.startswith('@') else f'{dialog}[open] {sel}'
                        await lan.wait_for_function('(s) => document.querySelector(s)', arg=sel, timeout=15000)
                        await lan.evaluate('(s) => document.querySelector(s).click()', sel)
                        await lan.wait_for_timeout(900)
                    await lan.wait_for_selector(f'{dialog}[open]', timeout=15000)
                    await bb.popups(lan)
                    loc = lan.locator(f'{dialog}[open] {field}').first
                    await loc.wait_for(timeout=10000)
                    await loc.tap()
                    await loc.fill('')
                except Exception as e:  # noqa: BLE001
                    seen = await lan.evaluate("()=>[...document.querySelectorAll('dialog[open]')].map(d=>d.className+': '+d.innerText.replace(/\\s+/g,' ').slice(0,240))")
                    check(False, f'{name}: open the sheet and its field ({type(e).__name__}: {str(e)[:120]}; open: {seen})')
                    continue
                await lan.wait_for_timeout(300)
                check(await lan.evaluate('([d,f]) => window.__tw.arm(d,f)', [dialog, field]), f'{name}: the field is there')
                numeric = 'total' in name or await loc.get_attribute('inputmode') == 'numeric'
                text = '1234567890' if numeric else 'Chuc mung ngay hai muoi'
                typed, end = '', time.monotonic() + args.secs
                while time.monotonic() < end and len(typed) < len(text):
                    ch = text[len(typed)]
                    await lan.keyboard.type(ch)
                    typed += ch
                    await asyncio.sleep(args.secs / len(text))
                res = await lan.evaluate('() => window.__tw.done()')
                check(not res['lost'], f'{name}: the field kept focus while the town went on ({res["lost"][:4]})')
                check(res['connected'], f'{name}: the field was never thrown away')
                if not numeric:
                    cap = int(await loc.get_attribute('maxlength') or 999)
                    check(res['value'] == typed[:cap], f'{name}: it holds what was typed ({res["value"]!r})')
                else:
                    check(any(c.isdigit() for c in res['value'] or ''), f'{name}: the typed number is still there ({res["value"]!r})')
                if name not in SCROLLS:
                    check(not res['scroll'], f'{name}: the sheet did not scroll by itself ({res["scroll"][:3]})')
        finally:
            stop.set()
            await asyncio.gather(*bg, return_exceptions=True)
            await browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('only', nargs='?', default='')
    ap.add_argument('--secs', type=float, default=12)
    args = ap.parse_args()
    problems, checks = [], []
    with tempfile.TemporaryDirectory(prefix='mnl-typing-', ignore_cleanup_errors=True) as tmp, bb.servers(tmp) as (base, db):
        try:
            asyncio.run(run(base, db, args, problems, checks))
        except AssertionError as e:
            problems.append(str(e))
    for c in checks:
        print(c)
    for p in problems:
        print('PROBLEM', p)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
