#!/usr/bin/env python3
"""⌨️ Phones can type (owner 22/10: "nhiều người than k hiển thị bàn phím của game đó, nên nhập này kia k đc"; iPhone video:
a tap on the bank's amount showed no keyboard; copy/paste did nothing). Dev tool: needs playwright with WebKit and
Chromium, the live service's websockets, PostgreSQL through TEST_DATABASE_URL.

Runs the real game + live service on one disposable database. For each browser (WebKit as an iPhone 13, Chromium as a
Pixel 7) and each interface (2.5D isometric, classic), Lan opens every sheet with a text field and, with page.tap()
(a real touch: the tap must reach the field, nothing may lie over it):
  * the field has focus right after the tap and still 1.5 s later, never thrown away (iOS opens the keyboard only for a
    focus made inside the touch; a later re-focus by script brings no keyboard),
  * the keyboard "opens" (the viewport shrinks, as with interactive-widget=resizes-content on Android / the visual
    viewport on iOS) and the field keeps focus and its value,
  * a second tap on the focused field (placing the caret, the long press for Dán) neither blurs nor re-focuses it,
  * typed keys and an inserted (pasted) text land in it; while the field has focus no card opens over it by itself
    (🔥 x3 tuần, Có gì mới, a new title: break-gate.js / journey.js / life.js wait for the field to be left),
  * a whole-number field (type=number) takes a pasted "1.000.000" as 1000000 and a typed "50.000" as 50000.
Every focusin / focusout / focus() / blur() on the page is logged with its stack: a failed check prints them.
Exit 1 on a failed check or a page error.

    TEST_DATABASE_URL=postgresql://… python scripts/browser_keyboard.py [webkit,chromium] [iso,classic] [only,these]
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
OUT = Path(tempfile.gettempdir()) / 'keyboard-shots'
_argv, sys.argv = sys.argv, [sys.argv[0], str(OUT)]   # browser_bang reads its log folder from argv[1]
import browser_bang as bb  # noqa: E402  (servers, sql, mutate, popups, API)
sys.argv = _argv
_wait = bb.wait_http
bb.wait_http = lambda url, secs=60: _wait(url, 600)   # a fresh schema on a busy PostgreSQL can take minutes

# name, action, data, taps before the field ('@…': anywhere on the page, else inside the sheet), the field, the sheet
SHEETS = [
    ('bank-amount', 'bank', {}, ['[data-bk="open"]', '@#confirmDialog[open] [data-action="confirmYes"]'], '#bk-amt', 'dialog.bk-sheet'),
    ('bank-xfer-amount', 'bank', {}, ['[data-bk="xfer"]', '[data-bk="x-to"]'], '#bx-amt', 'dialog.bk-sheet'),
    ('bank-xfer-note', 'bank', {}, ['?[data-bk="xfer"]', '?[data-bk="x-to"]'], '#bx-note', 'dialog.bk-sheet'),
    ('gopy-text', 'gopy', {}, [], '#fb-text', 'dialog#sheet'),
    ('chat-town', 'liveChat', {}, [], '.ch-compose textarea', 'dialog.chat-sheet'),
    ('lixi-total', 'lixi', {'tab': 'give'}, [], 'input[name="total"]', 'dialog.lxi-sheet'),
    ('bang-name', 'bang', {}, ['[data-bg="tab"][data-tab="found"]'], 'input[name="f-name"]', 'dialog.bg-sheet'),
    ('find-career', 'home', {}, [], 'input[data-jr-find]', 'dialog#sheet'),   # (2.5D: Danh sách; classic opens the map)
    ('iso-guide', 'isoGuide', {}, [], '.iso-guide-search input', 'dialog.iso-guide-sheet'),
    ('account', 'v4AccountOpen', {'mode': 'login'}, [], 'input.input:not([type=hidden])', 'dialog#sheet'),
]

ISO_ONLY = {'find-career', 'iso-guide'}

PROBE = r"""
(() => {
  if (window.__kb) return;
  const K = window.__kb = {log: [], t0: performance.now()};
  const name = el => !el ? 'null' : el === document ? 'document' : el === window ? 'window' :
    (el.tagName || '?').toLowerCase() + (el.id ? '#' + el.id : '') + (el.getAttribute?.('name') ? `[name=${el.getAttribute('name')}]` : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
  const stack = () => (new Error().stack || '').split('\n').slice(2, 9).map(s => s.trim().replace(/https?:\/\/[^/]+/, '')).join(' < ');
  const at = () => Math.round(performance.now() - K.t0);
  K.push = (t, el, s) => { K.log.push({t, el: name(el), at: at(), stack: s || ''}); if (K.log.length > 400) K.log.splice(0, 100); };
  for (const t of ['focusin', 'focusout']) document.addEventListener(t, e => K.push(t, e.target), true);
  for (const t of ['touchstart', 'touchend', 'pointerdown', 'mousedown', 'click']) document.addEventListener(t, e => K.push(t + (e.defaultPrevented ? '!prevented' : ''), e.target), true);
  for (const t of ['touchstart', 'touchend', 'pointerdown', 'mousedown']) window.addEventListener(t, e => { if (e.defaultPrevented) K.push(t + ' prevented (bubble)', e.target); }, false);
  const P = HTMLElement.prototype, f0 = P.focus, b0 = P.blur;
  P.focus = function (o) { K.push('focus()', this, stack()); return f0.call(this, o); };
  P.blur = function () { K.push('blur()', this, stack()); return b0.call(this); };
  K.arm = (dialog, field) => {
    const d = document.querySelector(dialog + '[open]'), el = d?.querySelector(field);
    K.d = d; K.el = el; K.log = []; K.lost = [];
    clearInterval(K.timer);
    K.timer = setInterval(() => {
      if (!K.el) return;
      if (!K.el.isConnected) K.lost.push('removed');
      else if (document.activeElement !== K.el) K.lost.push('blur:' + name(document.activeElement));
    }, 30);
    return Boolean(el);
  };
  K.state = () => ({active: document.activeElement === K.el, activeName: name(document.activeElement), connected: !!K.el?.isConnected,
    value: K.el?.value ?? null, kb: document.documentElement.classList.contains('kb-open'), lost: [...new Set(K.lost)],
    layout: document.documentElement.dataset.layout, game: document.documentElement.dataset.game});
  K.done = () => { clearInterval(K.timer); return K.state(); };
})();
"""

DEVICES = {'webkit': 'iPhone 13', 'chromium': 'Pixel 7'}


async def run(base, db, args, problems, checks):
    from playwright.async_api import async_playwright

    def check(cond, what, log=None):
        checks.append(('PASS ' if cond else 'FAIL ') + what)
        if not cond:
            problems.append('check: ' + what)
            if log:
                for row in log[-40:]:
                    problems.append(f"    {row['at']:>6} {row['t']:<22} {row['el']:<40} {row['stack'][:300]}")

    async with async_playwright() as pw:
        n = 0
        for engine in args.engines:
            browser = await getattr(pw, engine).launch()
            device = dict(pw.devices[DEVICES[engine]])
            device.pop('default_browser_type', None)
            for ui in args.uis:
                n += 1
                user = f'lan{engine[:2]}{ui[:2]}{n}'
                friend = f'minh{engine[:2]}{ui[:2]}{n}'
                tag = f'{engine}/{ui}'
                ctx = await browser.new_context(**device, bypass_csp=True, locale='vi-VN')
                await ctx.add_init_script(PROBE)
                page = await ctx.new_page()
                page.on('pageerror', lambda e, tag=tag: problems.append(f'{tag} exception: {str(e)[:300]}'))
                await page.goto(base + '/')
                await page.wait_for_selector('#app:not([hidden])', timeout=60000)
                sids = {}
                for who, u in (('Lan', user), ('Minh', friend)):
                    if who == 'Minh':   # a second account, made through the API from a fresh cookie jar
                        c2 = await browser.new_context(bypass_csp=True)
                        p2 = await c2.new_page()
                        await p2.goto(base + '/')
                        await p2.wait_for_selector('#app:not([hidden])', timeout=60000)
                        await p2.evaluate(bb.API, ['/api/account/register', dict(username=u, password=bb.PW, confirm=bb.PW, display=who)])
                        await c2.close()
                    else:
                        await page.evaluate(bb.API, ['/api/account/register', dict(username=u, password=bb.PW, confirm=bb.PW, display=who)])
                    bb.sql(db, 'UPDATE accounts SET created_at=? WHERE username=?', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 30 * 86400)), u))
                    sids[who] = bb.sql(db, 'SELECT sid FROM accounts WHERE username=?', (u,))[0][0]
                from game import whats_new as wn
                from game import journey as jr

                def seed(s, who):
                    j = s['journey']
                    s['name'] = who
                    s['settings'].update(whatsNewSeen=wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST), tutorialDone=True)
                    j['interface'] = dict(newInterface=ui == 'iso', interfacePromptSeen=True)
                    j.update(gender='female', intro=True, life_day=20, story=True, chapter=3, done=[1, 2])
                    for c in (2, 3):
                        jr._unlock_chapter(j, c)
                    j['wallet'] = 30_000_000
                    j['stats']['max_wallet'] = 30_000_000
                    for t in ('m_save200', 'm_save1000'):
                        j['titles'].setdefault(t, j['life_day'])
                for who, sid in sids.items():
                    bb.mutate(db, sid, lambda s, who=who: seed(s, who))
                t = time.time() - 86400
                for a, b in ((sids['Lan'], sids['Minh']), (sids['Minh'], sids['Lan'])):
                    bb.sql(db, 'INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', (a, b, t))
                await page.goto(base + '/')
                await page.wait_for_selector('#app:not([hidden])', timeout=60000)
                await page.wait_for_timeout(2500)
                await bb.popups(page)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                game = await page.evaluate('document.documentElement.dataset.game')
                check(game == ('isometric' if ui == 'iso' else 'classic'), f'{tag}: interface {game}')
                vw, vh = device['viewport']['width'], device['viewport']['height']
                banked = False
                for name, action, data, taps, field, dialog in SHEETS:
                    if args.only and name not in args.only:
                        continue
                    if ui != 'iso' and name in ISO_ONLY:
                        continue
                    if name == 'bank-amount' and banked:
                        taps = []
                    await page.set_viewport_size(dict(width=vw, height=vh))
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.wait_for_timeout(300)
                    await page.evaluate("([a,d])=>{const b=document.createElement('button');b.dataset.action=a;for(const [k,v] of Object.entries(d||{}))b.dataset[k]=v;b.hidden=true;document.body.append(b);b.click();b.remove();}", [action, data])
                    try:
                        for sel in taps:
                            opt = sel.startswith('?')   # only when it is there (the bank keeps its transfer step)
                            sel = sel.lstrip('?')
                            sel = sel[1:] if sel.startswith('@') else f'{dialog}[open] {sel}'
                            try:
                                await page.locator(sel).first.wait_for(state='attached', timeout=3000 if opt else 15000)   # (WebKit: the CSP refuses wait_for_function)
                            except Exception:  # noqa: BLE001
                                if opt:
                                    continue
                                raise
                            await page.evaluate('(s) => document.querySelector(s).click()', sel)
                            await page.wait_for_timeout(900)
                        if name == 'bank-amount':
                            banked = True
                        await page.wait_for_selector(f'{dialog}[open]', timeout=15000)
                        await bb.popups(page)
                        loc = page.locator(f'{dialog}[open] {field}').first
                        await loc.wait_for(timeout=10000)
                        await loc.scroll_into_view_if_needed()
                        await page.wait_for_timeout(400)
                    except Exception as e:  # noqa: BLE001
                        seen = await page.evaluate("()=>[...document.querySelectorAll('dialog[open]')].map(d=>d.className+': '+d.innerText.replace(/\\s+/g,' ').slice(0,200))")
                        check(False, f'{tag} {name}: open the sheet and its field ({type(e).__name__}: {str(e)[:160]}; open: {seen})')
                        continue
                    await bb.popups(page)   # a card that opened by itself before the tap (🔥 x3 tuần, Có gì mới): closed, as a player would
                    check(await page.evaluate('([d,f]) => window.__kb.arm(d,f)', [dialog, field]), f'{tag} {name}: the field is there')
                    # 1. the tap reaches the field (Playwright's actionability: nothing intercepts it) and focuses it
                    try:
                        await loc.tap(timeout=4000)
                        tapped = True
                    except Exception as e:  # noqa: BLE001
                        tapped = False
                        check(False, f'{tag} {name}: tap reaches the field ({" ".join(l.strip() for l in str(e).splitlines() if "intercept" in l or "not stable" in l or "not visible" in l or "outside" in l)[:600] or str(e)[:600]})')
                    s = await page.evaluate('window.__kb.state()')
                    log = await page.evaluate('window.__kb.log')
                    if tapped:
                        check(s['active'], f'{tag} {name}: focused right after the tap (active: {s["activeName"]})', log)
                        blurs = [r for r in log if r['t'] == 'blur()']
                        check(not blurs, f'{tag} {name}: the tap blurs nothing by script ({[(r["t"], r["el"]) for r in blurs][:4]})', log)
                    await page.evaluate('window.__kb.lost=[]')
                    await page.wait_for_timeout(1500)
                    s = await page.evaluate('window.__kb.state()')
                    check(s['active'] and s['connected'] and not s['lost'], f'{tag} {name}: still focused 1.5 s later ({s["activeName"]}, lost {s["lost"][:3]})', await page.evaluate('window.__kb.log'))
                    # 2. the keyboard opens: the viewport loses ~40 %
                    await page.evaluate('window.__kb.log=[]')
                    await page.set_viewport_size(dict(width=vw, height=int(vh * .58)))
                    await page.wait_for_timeout(900)
                    s = await page.evaluate('window.__kb.state()')
                    check(s['active'] and s['connected'] and not s['lost'], f'{tag} {name}: keeps focus when the keyboard opens (kb-open {s["kb"]}, {s["activeName"]}, lost {s["lost"][:3]})', await page.evaluate('window.__kb.log'))
                    # 3. a second tap on the field, keyboard open (the caret / the long press for Dán)
                    await page.evaluate('window.__kb.log=[]')
                    with contextlib.suppress(Exception):
                        await loc.tap(timeout=3000)
                    await page.wait_for_timeout(300)
                    log = await page.evaluate('window.__kb.log')
                    bounce = [r for r in log if r['t'] in ('focusout', 'blur()', 'focus()')]
                    s = await page.evaluate('window.__kb.state()')
                    check(s['active'] and not bounce, f'{tag} {name}: a second tap leaves the typing field alone ({[(r["t"], r["el"]) for r in bounce][:4]})', log)
                    # 4. typing and pasting land in it
                    numeric = (await loc.get_attribute('inputmode')) == 'numeric' or (await loc.get_attribute('type')) == 'number' or name == 'lixi-total'
                    await page.evaluate('window.__kb.el.select?.()')
                    await page.keyboard.type('12' if numeric else 'Chao ')
                    await page.keyboard.insert_text('34' if numeric else 'pho')
                    await page.wait_for_timeout(400)
                    s = await page.evaluate('window.__kb.done()')
                    want = '1234' if numeric else 'Chao pho'
                    got = (s['value'] or '').replace('.', '').replace(',', '')
                    check(want in got, f'{tag} {name}: typed + pasted text lands ({s["value"]!r})', await page.evaluate('window.__kb.log'))
                    check(s['active'], f'{tag} {name}: still typing at the end ({s["activeName"]}, lost {s["lost"][:3]})')
                    # 5. a whole-number field (type=number) takes the game's own "1.000.000" pasted, and "50.000" typed
                    if await loc.get_attribute('type') == 'number':
                        got = await page.evaluate('''() => { const el = window.__kb.el; el.value = ''; let dt = null;
                          try { dt = new DataTransfer(); dt.setData('text/plain', '1.000.000'); } catch { return 'no DataTransfer'; }
                          const ev = new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true});
                          if (!ev.clipboardData) return 'no clipboardData';
                          el.dispatchEvent(ev); return el.value; }''')
                        if got in ('no DataTransfer', 'no clipboardData'):
                            checks.append(f'SKIP {tag} {name}: paste event ({got})')
                        else:
                            check(got == '1000000', f'{tag} {name}: a pasted "1.000.000" is 1000000 ({got!r})')
                        await page.evaluate("window.__kb.el.value=''")
                        await page.keyboard.type('50.000')
                        got = await page.evaluate('window.__kb.el.value')
                        check(got == '50000', f'{tag} {name}: a typed "50.000" is 50000 ({got!r})')
                await ctx.close()
            await browser.close()


def main():
    args = type('A', (), {})()
    a = sys.argv[1:]
    args.engines = a[0].split(',') if len(a) > 0 and a[0] else ['webkit', 'chromium']
    args.uis = a[1].split(',') if len(a) > 1 and a[1] else ['iso', 'classic']
    args.only = set(a[2].split(',')) if len(a) > 2 and a[2] else None
    problems, checks = [], []
    os.environ.setdefault('REGISTER_PER_10MIN', '1000')   # two accounts per browser × interface, all from 127.0.0.1
    os.environ.setdefault('REGISTER_PER_HOUR', '1000')
    with tempfile.TemporaryDirectory(prefix='mnl-kbd-', ignore_cleanup_errors=True) as tmp, bb.servers(tmp) as (base, db):
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
