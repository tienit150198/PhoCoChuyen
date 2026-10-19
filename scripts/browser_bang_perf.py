#!/usr/bin/env python3
"""⚔️ Bang sheet tap performance (dev tool; playwright + Chrome/chromium, PostgreSQL through TEST_DATABASE_URL).

A phone (390×844, touch, 2.5D town behind the sheet), Chrome CPU throttled 4× and 80 ms of network latency, a bang of 30
members with weeks of history (points, log), 15 other bangs. For each main interaction (open the sheet, switch tabs,
check in, contribute, upgrade a building, open a member, appoint, kick, shop buy, wear) it measures from the finger
(pointerdown) to:
  * feedback: the first change in the sheet (the pending state) painted;
  * settled: the last change in the sheet (the answer drawn);
and in that span: long tasks (count, total, worst), frames slower than 50 ms, main-thread script / style / layout time
(CDP Performance.getMetrics), whole-sheet rebuilds (the .sd-root subtree replaced) and scroll jumps (the sheet's
scrollTop moved by the redraw). Prints a table and writes JSON to argv[1] (optional).

    TEST_DATABASE_URL=postgresql://… python scripts/browser_bang_perf.py [out.json] [--reps 3] [--chrome]
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
OUT_JSON = next((a for a in sys.argv[1:] if not a.startswith('--') and a.endswith('.json')), '')
REPS = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 3
CHROME = '--chrome' in sys.argv or bool(os.environ.get('PW_CHROME'))   # the installed Google Chrome, not playwright's chromium
CPU = int(sys.argv[sys.argv.index('--cpu') + 1]) if '--cpu' in sys.argv else 4   # Chrome CPU throttling (4: a mid phone)
sys.argv = sys.argv[:1]   # browser_bang reads argv[1] as its screenshot folder
from browser_bang import servers, popups, mutate, sql, PW, API  # noqa: E402

PROBE = r"""() => {
  if (window.__pf) return;
  const pf = window.__pf = {lt: [], frames: [], muts: [], roots: 0, down: 0, inflight: 0, cls: 0, dis: 0, sel: '', top: null};
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) pf.lt.push([e.startTime, e.duration]); }).observe({type: 'longtask', buffered: false}); } catch {}
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) pf.cls += e.value; }).observe({type: 'layout-shift', buffered: false}); } catch {}
  const greyed = () => document.querySelectorAll('dialog.bg-sheet[open] button:disabled').length;
  const loop = t => { pf.frames.push(t); if (pf.down) pf.grey = Math.max(pf.grey, greyed() - pf.dis0); requestAnimationFrame(loop); }; requestAnimationFrame(loop);
  addEventListener('pointerdown', () => { pf.down = performance.now(); pf.dis0 = greyed(); pf.grey = 0; const d = document.querySelector('dialog.bg-sheet'); pf.y0 = d ? d.scrollTop : 0; pf.top = topOf(pf.sel); }, true);   // where the finger came down (after any scroll into view)
  const f = window.fetch; window.fetch = (...a) => { pf.inflight++; return f(...a).finally(() => { pf.inflight--; }); };
  const tick = n => !!(n && (n.nodeType === 3 ? n.parentElement : n)?.closest?.('[data-bg-until]'));   // the 1 s countdowns
  pf.watch = () => {
    const d = document.querySelector('dialog.bg-sheet'); if (!d || pf.mo) return;
    pf.mo = new MutationObserver(list => { const t = performance.now(); let real = false;
      for (const m of list) { if (tick(m.target)) continue; real = true;
        if (m.target.classList?.contains('sd-root') && m.type === 'childList') pf.roots++;
        if (m.type === 'attributes' && m.attributeName === 'disabled') pf.dis++; }
      if (real) pf.muts.push(t); });
    pf.mo.observe(d, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['class', 'disabled', 'aria-busy', 'aria-selected']});
  };
  const topOf = s => { const e = s && document.querySelector('dialog.bg-sheet[open] ' + s); return e ? Math.round(e.getBoundingClientRect().top) : null; };
  pf.reset = (sel = '') => { pf.lt = []; pf.frames = []; pf.muts = []; pf.roots = 0; pf.down = 0; pf.cls = 0; pf.dis = 0; pf.grey = 0; pf.dis0 = 0; pf.watch();
    pf.sel = sel; pf.top = topOf(sel);
    const d = document.querySelector('dialog.bg-sheet'); pf.y0 = d ? d.scrollTop : 0; };
  pf.read = () => { const d = document.querySelector('dialog.bg-sheet'); const t0 = pf.down || pf.t0 || 0;
    const fr = pf.frames.filter(x => x >= t0); const gaps = fr.slice(1).map((x, i) => x - fr[i]);
    const lt = pf.lt.filter(([s]) => s >= t0 - 5);
    const first = pf.muts.find(x => x >= t0), last = pf.muts.length ? pf.muts[pf.muts.length - 1] : 0;
    const paint = first ? fr.find(x => x >= first) : 0, top = topOf(pf.sel);
    return {feedback: first ? (paint || first) - t0 : null, settled: last >= t0 ? last - t0 : null,
      lt_n: lt.length, lt_ms: lt.reduce((a, [, d]) => a + d, 0), lt_max: lt.reduce((a, [, d]) => Math.max(a, d), 0),
      slow_frames: gaps.filter(g => g > 50).length, worst_frame: gaps.length ? Math.max(...gaps) : 0,
      rebuilds: pf.roots, cls: Math.round(pf.cls * 1000) / 1000, dis: pf.grey,   // dis: buttons greyed (disabled) at once while the tap was on its way
      moved: pf.top !== null && top !== null ? top - pf.top : null,   // the tapped control moved under the finger (px)
      y0: pf.y0, y1: d ? d.scrollTop : 0, muts: pf.muts.filter(x => x >= t0).length};
  };
}"""
METRICS = ('ScriptDuration', 'RecalcStyleDuration', 'LayoutDuration', 'TaskDuration', 'LayoutCount', 'RecalcStyleCount')


def seed_bang(db, lan_sid, members=29, others=15):
    """30 members in Lan's bang (her the leader), weeks of points and log, other bangs: in this process, same schema."""
    from game import bang, promotion
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    try:
        bid = bang._mine(store.connect(), lan_sid)['bang']

        def person(name):
            token, _, _ = store.session()
            store.read(token)
            sid = store.key(token)

            def fn(s):
                s['name'] = name
                promotion.record(s, 'milk_tea', True)['rank'] = 2
            mr._mutate(store, {sid: fn})
            login = secrets.token_hex(32)
            born = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 60 * 86400))
            with store.connect() as c:
                c.execute('INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?, ?, ?, ?, ?)', ('p' + secrets.token_hex(5), name, 'x', sid, born))
                c.execute("INSERT INTO logins(token, sid, csrf) VALUES(?, ?, 'c')", (store.digest(login), sid))
            return login
        for fac, lv in (('dai_sanh', 5), ('kho', 6), ('xuong_may', 3), ('cong', 3), ('tuong', 2)):
            sql(db, 'INSERT INTO bang_facilities(bang, fac, level) VALUES(?,?,?) ON CONFLICT(bang, fac) DO UPDATE SET level=excluded.level', (bid, fac, lv))
        sql(db, 'UPDATE bangs SET fund=?, isle=5 WHERE id=?', (150_000_000, bid))   # 🏝️ cấp 5: no island gate on Cổng bang 4–5 (21/10)
        for i in range(members):
            bang.post(store, person(f'Thành viên {i + 1}'), 'join', dict(bang=bid))
        for b in range(others):
            tk = person(f'Trùm {b}')
            sid = store.key(tk)
            store.transaction(lambda c, sid=sid, b=b: c.execute(
                "INSERT INTO bangs(id, name, key, emoji, color, leader, created, created_by) VALUES(?,?,?,?,?,?,?,?)",
                (f'b{secrets.token_hex(5)}', f'Bang Số {b}', f'bangso{b}', '🐯', 'mint', sid, time.time() - 9 * 86400, sid)))
        import random
        with store.connect() as c:
            sids = [r['sid'] for r in c.execute("SELECT sid FROM bang_members WHERE bang=? AND status='in'", (bid,)).fetchall()]
        now = time.time()

        def bulk(c):
            c.executemany('INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,?,?,?,?,?)',
                          [(f'x:{k}', bid, random.choice(sids), random.choice(('give', 'checkin', 'work')), random.randint(1, 60),
                            bang.vn_week(at), bang.vn_day(at), at) for k, at in ((k, now - random.random() * 40 * 86400) for k in range(30_000))])
            c.executemany('INSERT INTO bang_log(bang, sid, kind, text, at) VALUES(?,?,?,?,?)',
                          [(bid, '', 'join', f'Thành viên {k % 29 + 1} góp {k * 1000} xu vào quỹ bang.', now - 3600 + k) for k in range(3000)])
            c.execute("UPDATE bang_members SET points=1000000, earned=points+5000 WHERE bang=?", (bid,))
        store.transaction(bulk)
        return bid
    finally:
        store.close_pool()


async def main():
    from playwright.async_api import async_playwright
    rows, problems, checks = [], [], []
    with tempfile.TemporaryDirectory(prefix='mnl-bang-perf-', ignore_cleanup_errors=True) as tmp, servers(tmp) as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**(dict(channel='chrome') if CHROME else {}))
            ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2, bypass_csp=True)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: problems.append(f'exception: {str(e)[:300]}'))
            page.on('response', lambda r: r.status >= 500 and problems.append(f'HTTP {r.status} {r.url}'))
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)

            async def api(path, body=None):
                out = await page.evaluate(API, [path, body])
                if out['status'] >= 400:
                    raise AssertionError(f'{path} -> {out}')
                return out['data']
            await api('/api/account/register', dict(username='lanmay', password=PW, confirm=PW, display='Lan'))
            sql(db, 'UPDATE accounts SET created_at=? WHERE username=?', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 30 * 86400)), 'lanmay'))
            sid = sql(db, 'SELECT sid FROM accounts WHERE username=?', ('lanmay',))[0][0]
            from game import promotion
            from game import whats_new as wn

            def seed(s):
                j = s['journey']
                s['name'] = 'Lan'
                s['settings'].update(whatsNewSeen=wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST), tutorialDone=True)
                j['interface'] = dict(newInterface=True, interfacePromptSeen=True)
                j.update(gender='female', intro=True, life_day=20, story=True)
                j['wallet'] = 90_000_000
                j['stats']['max_wallet'] = 90_000_000
                for t in ('m_save200', 'm_save1000'):   # no title popup over the sheet
                    j['titles'].setdefault(t, j['life_day'])
                promotion.record(s, 'milk_tea', True)['rank'] = 1
            mutate(db, sid, seed)
            await page.goto(base + '/?isometricdebug=1')
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await page.wait_for_timeout(1500)
            await popups(page)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            # found the bang through the sheet (two taps), then seed it big
            await act(page, 'bang')
            await page.wait_for_selector('dialog.bg-sheet[open] .sd-body', timeout=15000)
            await page.locator('dialog.bg-sheet[open] [data-bg="tab"][data-tab="found"]').first.click()
            await page.wait_for_selector('dialog.bg-sheet[open] input[name="f-name"]')
            await page.wait_for_timeout(800)
            await page.locator('dialog.bg-sheet[open] input[name="f-name"]').fill('Rồng Đỏ')
            await page.locator('dialog.bg-sheet[open] [data-bg="emoji"]').first.click()
            await page.wait_for_timeout(300)
            for _ in range(2):
                await page.locator('dialog.bg-sheet[open] [data-bg="found"]').click()
                await page.wait_for_timeout(400)
            await page.wait_for_function("document.querySelector('#bg-title')?.innerText.includes('Rồng Đỏ')", timeout=20000)
            bid = seed_bang(db, sid)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            await page.evaluate(PROBE)

            cdp = await ctx.new_cdp_session(page)
            await cdp.send('Performance.enable')
            await cdp.send('Network.enable')
            await cdp.send('Emulation.setCPUThrottlingRate', dict(rate=CPU))
            await cdp.send('Network.emulateNetworkConditions', dict(offline=False, latency=80, downloadThroughput=-1, uploadThroughput=-1))

            async def metrics():
                m = (await cdp.send('Performance.getMetrics'))['metrics']
                return {x['name']: x['value'] for x in m if x['name'] in METRICS}


            def check(cond, what):
                checks.append(('PASS ' if cond else 'FAIL ') + what)

            async def settle(timeout=12.0):
                end = time.monotonic() + timeout
                quiet = 0
                while time.monotonic() < end:
                    s = await page.evaluate("()=>{const d=document.querySelector('dialog.bg-sheet');const m=__pf.muts;return {busy:d?.getAttribute('aria-busy')==='true',fl:__pf.inflight,last:m.length?performance.now()-m[m.length-1]:1e9};}")
                    if not s['busy'] and s['fl'] == 0 and s['last'] > 600:
                        quiet += 1
                        if quiet >= 2:
                            return
                    else:
                        quiet = 0
                    await asyncio.sleep(0.15)

            async def record(name, m0):
                r = await page.evaluate('__pf.read()')
                m1 = await metrics()
                r.update({k: round((m1.get(k, 0) - m0.get(k, 0)) * (1000 if k.endswith('Duration') else 1), 1) for k in METRICS})
                r['name'] = name
                rows.append(r)
                print(f"{name:26s} fb {fmt(r['feedback'])} settled {fmt(r['settled'])} LT {r['lt_n']}/{r['lt_ms']:.0f}ms max {r['lt_max']:.0f} "
                      f"slow {r['slow_frames']} worst {r['worst_frame']:.0f} script {r['ScriptDuration']:.0f} style {r['RecalcStyleDuration']:.0f} "
                      f"layout {r['LayoutDuration']:.0f} rebuilds {r['rebuilds']} greyed {r['dis']} cls {r['cls']} moved {r['moved']} y {r['y0']}→{r['y1']}", flush=True)
                return r

            async def step(name, sel):
                """Tap `sel` in the sheet; the numbers from the finger to the last redraw."""
                await page.evaluate('s=>__pf.reset(s)', sel)
                m0 = await metrics()
                await page.locator(f'dialog.bg-sheet[open] {sel}').first.tap()
                await settle()
                return await record(name, m0)

            async def state():
                return await page.evaluate("""()=>{const d=document.querySelector('dialog.bg-sheet[open]');if(!d)return null;
                  return {tab:d.querySelector('.sd-tabs .on')?.dataset.tab||'',main:d.querySelector('.sd-main')?.innerText||'',flash:d.querySelector('.sd-flash')?.innerText||'',
                    chip:d.querySelector('.sd-amounts .sd-chip.on')?.dataset.n||'',open:d.querySelector('.bg-members li.open [data-bg=sel]')?.dataset.pid||'',y:d.scrollTop};}""")

            async def opened():
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate("__pf.t0=performance.now();__pf.down=performance.now()")
                await act(page, 'bang')
                await page.wait_for_selector('dialog.bg-sheet[open] .bg-hero', timeout=20000)
                await page.evaluate('__pf.watch()')

            # ⏰ no Đền vàng yet (owner 21/10 "bang chủ chưa chọn được giờ vàng"): the fund short → what it lacks + 🙌 Góp quỹ
            sql(db, 'UPDATE bangs SET fund=? WHERE id=?', (1_000_000, bid))
            await opened()   # (also warms the module and the css)
            await settle()
            gold = "()=>{const c=document.querySelector('dialog.bg-sheet[open] [data-k=golden]');return c?{text:c.innerText,btn:c.querySelector('[data-bg=build][data-id=den_vang]')?.innerText||'',off:!!c.querySelector('[data-bg=build][data-id=den_vang]')?.disabled,fund:!!c.querySelector('[data-bg=toFund]')}:null;}"
            g = await page.evaluate(gold)
            check(bool(g) and 'Xây Đền vàng · 10 triệu · 4 giờ' in g['btn'] and g['off'] and 'Quỹ còn thiếu 9.000.000 xu' in g['text'] and g['fund'],
                  f'⏰ no Đền vàng, fund short: the build button (off), what the fund lacks, 🙌 Góp quỹ ({g})')
            if g and g['fund']:   # (the release before had a note only: the rest of the run still measures it)
                await page.locator('dialog.bg-sheet[open] [data-bg="toFund"]').tap()
                await page.wait_for_timeout(900)
                seen = await page.evaluate("()=>{const r=document.querySelector('dialog.bg-sheet [data-k=fund]').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;}")
                check(seen, '🙌 Góp quỹ brings the 💰 Quỹ bang card into view')
            sql(db, 'UPDATE bangs SET fund=? WHERE id=?', (150_000_000, bid))
            for rep in range(REPS):
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.wait_for_timeout(500)
                await page.evaluate('__pf.reset()')
                m0 = await metrics()
                await opened()
                await settle()
                await record('open sheet', m0)
                for t in ('members', 'build', 'shop', 'rank', 'more', 'home'):
                    await step(f'tab {t}', f'[data-bg="tab"][data-tab="{t}"]')
            # 📅 check-in, 💰 contribute three times in a row (owner 21/10: the amount stays chosen, one more tap gives again)
            await step('checkin', '[data-bg="checkin"]')
            # (the fund has no cap since 21/10: the chips are 1tr · 10tr · 100tr · Tất cả, and 1 triệu or more takes two taps)
            await step('contribute: amount 1 triệu', '[data-bg="amount"][data-n="1000000"]')
            for rep in range(3):
                await step('contribute 1 triệu: arm', '[data-bg="give"]')
                await page.wait_for_timeout(250)   # past ARM_GAP: the confirming tap, not a double tap
                await step('contribute 1 triệu', '[data-bg="give"]')
                s = await state()
                check(s['tab'] == 'home' and s['chip'] == '1000000' and '1.000.000' in s['main'] and 'Bấm lần nữa' not in s['main'],
                      f'contribute #{rep + 1}: still on 🏯 with 1 triệu chosen ({s})')
            # ⏰ the fund is enough now: Bang chủ builds Đền vàng from the Giờ vàng card (two taps), the card counts down
            g = await page.evaluate(gold)
            check(bool(g) and 'Xây Đền vàng · 10 triệu · 4 giờ' in g['btn'] and not g['off'], f'⏰ the Đền vàng build is the card\'s main button ({g})')
            if g and g['btn']:
                await page.evaluate("document.querySelector('dialog.bg-sheet [data-k=golden]').scrollIntoView({block:'center'})")
                await step('golden: build arm', '[data-bg="build"][data-id="den_vang"]')
                await step('golden: build confirm', '[data-bg="build"][data-id="den_vang"]')
                g, s = await page.evaluate(gold), await state()
                check(bool(g) and 'Đang xây' in g['text'] and 'xong là chọn được giờ vàng' in g['text'] and s['tab'] == 'home',
                      f'⏰ Đền vàng building: the countdown on the card, still on 🏯 ({g}, {s["tab"]})')
            # 🏗️ upgrade the same facility twice in a row (owner 21/10): the card stays where it was, its next level ready
            await step('tab build', '[data-bg="tab"][data-tab="build"]')
            for rep in range(2):
                sql(db, 'UPDATE bangs SET fund=? WHERE id=?', (150_000_000, bid))
                if rep:   # the first build is done (time passes): the sheet notices when the phone comes back to the game
                    sql(db, 'UPDATE bang_facilities SET ready_at=? WHERE bang=? AND target IS NOT NULL', (time.time() - 1, bid))
                    await page.wait_for_timeout(5500)
                    await page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                    await settle()
                await page.evaluate("document.querySelector('dialog.bg-sheet [data-bg=build][data-id=cong]')?.scrollIntoView({block:'center'})")
                await page.wait_for_timeout(300)
                if not await page.locator('dialog.bg-sheet[open] [data-bg="build"][data-id="cong"]').count():
                    check(False, f'build #{rep + 1}: the next level of Cổng bang is offered once the last one is done')
                    continue
                card = "()=>Math.round(document.querySelector('dialog.bg-sheet[open] section.bg-fac:nth-of-type(5)').getBoundingClientRect().top)"   # ⛩️ Cổng bang
                y0 = await page.evaluate(card)
                await step('build: arm', '[data-bg="build"][data-id="cong"]')
                r = await step('build: confirm', '[data-bg="build"][data-id="cong"]')
                s, y1 = await state(), await page.evaluate(card)
                check(s['tab'] == 'build' and abs(y1 - y0) <= 2 and 'Cổng' in s['flash'], f'build #{rep + 1}: still on 🏗️, the Cổng bang card where it was ({s}, card top {y0} → {y1})')
            # 👥 a member near the bottom: open, appoint, kick
            await step('tab members', '[data-bg="tab"][data-tab="members"]')
            await settle()
            pids = await page.evaluate("[...document.querySelectorAll('dialog.bg-sheet [data-bg=sel]:not([disabled])')].map(b=>b.dataset.pid)")
            for rep in range(REPS):
                pid = pids[-1 - rep]
                await page.evaluate("document.querySelector('dialog.bg-sheet').scrollTop=1e5")
                await step('member: open', f'[data-bg="sel"][data-pid="{pid}"]')
                await step('member: appoint Tinh anh', f'[data-bg="role"][data-pid="{pid}"][data-role="tinh"]')
                s = await state()
                check(s['tab'] == 'members' and s['open'] == pid, f'appoint #{rep + 1}: the member stays open ({s})')
                await step('member: kick arm', f'[data-bg="kick"][data-pid="{pid}"]')
                await step('member: kick confirm', f'[data-bg="kick"][data-pid="{pid}"]')
            await step('tab shop', '[data-bg="tab"][data-tab="shop"]')
            await settle()
            await step('shop: buy badge', '[data-bg="buy"][data-id="huy"]')
            await step('shop: buy uniform', '[data-bg="buy"][data-id="ao"]')
            for rep in range(REPS):
                await step('shop: wear toggle', '[data-bg="wear"][data-id="ao"]:not([data-style])')
            for rep in range(REPS):
                await step('shop: buy fireworks', '[data-bg="buy"][data-id="phao"]')
                s = await state()
                check(s['tab'] == 'shop', f'buy #{rep + 1}: still on 🛍️ ({s})')
            await browser.close()
    summary = {}
    for r in rows:
        summary.setdefault(r['name'], []).append(r)
    head = ('interaction', 'n', 'fb ms', 'settle', 'LT n', 'LT ms', 'LTmax', 'slow', 'script', 'style', 'layout', 'rebld', 'greyd', 'CLS', 'moved', 'scroll')
    print('\n%-26s %3s %7s %7s %5s %6s %6s %5s %7s %6s %6s %5s %5s %6s %6s %s' % head)
    out = {}
    for name, rs in summary.items():
        def med(k):
            v = [x[k] for x in rs if x.get(k) is not None]
            return statistics.median(v) if v else None
        jumps = sum(1 for x in rs if abs((x['y1'] or 0) - (x['y0'] or 0)) > 2)
        out[name] = {k: med(k) for k in ('feedback', 'settled', 'lt_n', 'lt_ms', 'lt_max', 'slow_frames', 'worst_frame', 'ScriptDuration',
                                         'RecalcStyleDuration', 'LayoutDuration', 'rebuilds', 'dis', 'cls', 'moved')}
        out[name]['scroll_jumps'] = f'{jumps}/{len(rs)}'
        o = out[name]
        print('%-26s %3d %7s %7s %5s %6s %6s %5s %7s %6s %6s %5s %5s %6.3f %6s %s' % (
            name, len(rs), fmt(o['feedback']), fmt(o['settled']), fmt(o['lt_n']), fmt(o['lt_ms']), fmt(o['lt_max']), fmt(o['slow_frames']),
            fmt(o['ScriptDuration']), fmt(o['RecalcStyleDuration']), fmt(o['LayoutDuration']), fmt(o['rebuilds']), fmt(o['dis']), o['cls'] or 0,
            fmt(o['moved']), o['scroll_jumps']))
    for c in checks:
        print(c)
    if OUT_JSON:
        Path(OUT_JSON).write_text(json.dumps(dict(summary=out, rows=rows, checks=checks), ensure_ascii=False, indent=1))
    for p in problems:
        print('PROBLEM', p)
    return 1 if problems or any(c.startswith('FAIL') for c in checks) else 0


def fmt(v):
    return '-' if v is None else f'{v:.0f}'


async def act(page, action, data=None):
    await page.evaluate("([a,d])=>{const b=document.createElement('button');b.dataset.action=a;for(const [k,v] of Object.entries(d||{}))b.dataset[k]=v;b.hidden=true;document.body.append(b);b.click();b.remove();}", [action, data or {}])


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
