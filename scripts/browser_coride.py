#!/usr/bin/env python3
"""💑 Vợ chồng chung xe: a two-browser walk-through (dev tool; as scripts/browser_ride.py, whose servers it uses).

Minh (husband) owns a red scooter, Lan (wife) owns nothing; both have accounts and are married. At 390x844 and
1280x800:
  * the town: Lan's toggle offers "🛵 Xe của Minh" (the spouse's vehicle, GET /api/garage/spouse);
  * Đi dạo: Minh rides in first; Lan comes in wanting the same scooter: "Minh đang lái xe này — ngồi sau nhé?";
    "Ngồi sau" puts her behind him (her entry's `b`), she goes where he drives and her own taps do nothing;
    "Xuống xe" gets her off; "🛵 Ngồi sau" again, then Minh leaves: she is dropped on foot, safely;
  * the fair: the same at the fair; Minh parks at a stall: she gets off and walks in with him.
Screenshots of each step; exit 1 on a failed check, a console error, a page error or an HTTP 5xx.

    MNL_PY=<python with the server's requirements> python scripts/browser_coride.py [out_dir] [--one]
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_ride as br  # noqa: E402

PW = 'matkhau-rat-dai'
API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""
WALK, FAIR, TOWN = br.WALK, br.FAIR, br.TOWN


async def api(p, path, body=None):
    out = await p.page.evaluate(API, [path, body])
    if out['status'] >= 400:
        raise AssertionError(f'{p.name}: {path} -> {out}')
    return out['data']


def marry(db: str, a: str, b: str) -> None:
    con = sqlite3.connect(db)
    with con:
        cid = con.execute("INSERT INTO couples(a, b, status, since, married_at) VALUES(?, ?, 'married', ?, ?)", (a, b, time.time(), time.time())).lastrowid
        con.executemany('INSERT INTO marriage_bonds(sid, couple) VALUES(?, ?)', [(a, cid), (b, cid)])
    con.close()


def sid_of(db: str, username: str) -> str:
    con = sqlite3.connect(db)
    try:
        return con.execute('SELECT sid FROM accounts WHERE username=?', (username,)).fetchone()[0]
    finally:
        con.close()


async def run(size, problems, checks) -> None:
    from playwright.async_api import async_playwright
    tag = f'{size[0]}x{size[1]}'
    out = br.OUT

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + f' [{tag}] ' + what)
        if not cond:
            problems.append(f'check [{tag}]: ' + what)

    async def shot(p, name):
        await br.popups(p.page)
        await p.page.wait_for_timeout(350)
        await p.page.screenshot(path=str(out / f'{tag}-{name}.png'))

    async def reload(p):
        await p.page.reload()
        await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
        await p.page.wait_for_timeout(900)
        await br.popups(p.page)
        await p.page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

    async def stroll(p):
        await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await br.act(p.page, 'liveWalk')
        await p.page.wait_for_selector('.walk-sheet[open] .wk-canvas', timeout=15000)
        return await br.until(p.page, WALK, 'return s.room&&s.me', f'{p.name} strolls', 10)

    async def fair(p):
        await p.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
        await br.act(p.page, 'fair')
        await p.page.wait_for_selector('.fh-sheet[open] .fh-wcanvas', timeout=15000)
        await br.until(p.page, FAIR, 'return s&&s.on&&s.me&&s.crowd.on', f'{p.name}: the fairground is up', 10)
        await p.page.wait_for_timeout(500)
        await br.popups(p.page)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        minh = await br.player(browser, br.BASE, 'Minh', [('xe_ga', 'do', 'MINH 01')], size, problems)
        lan = await br.player(browser, br.BASE, 'Lan', [], size, problems)
        u = f'{size[0]}{size[1]}'
        await api(minh, '/api/account/register', dict(username=f'minh{u}', password=PW, confirm=PW, display='Minh'))
        await api(lan, '/api/account/register', dict(username=f'lan{u}', password=PW, confirm=PW, display='Lan'))
        marry(br.DB, sid_of(br.DB, f'minh{u}'), sid_of(br.DB, f'lan{u}'))
        for p in (minh, lan):
            await reload(p)
        sp = await api(lan, '/api/garage/spouse')
        check(sp['spouse'] and sp['spouse']['name'] == 'Minh' and [c['id'] for c in sp['spouse']['cars']] == ['xe_ga'],
              f"Lan's spouse and his scooter ({sp})")

        # ---- the town: his scooter in her toggle ----
        if not await lan.page.evaluate("!!document.querySelector('#sheet[open] .tw-stage')"):
            await br.act(lan.page, 'home')
        s = await br.until(lan.page, TOWN, "return s.on&&s.me&&(s.toggle||'').includes('Xe của')", 'Lan: the town offers his scooter', 15)
        check('Xe của Minh' in s['toggle'], f"Lan's toggle: {s['toggle']!r}")
        await shot(lan, '01-town-lan-his-scooter')

        # ---- Đi dạo ----
        await stroll(minh)
        s = await br.until(minh.page, WALK, 'return s.people.some(q=>q.pid===s.me&&q.ride==="xe_ga")', 'Minh rides in', 8)
        mpid = s['me']
        await stroll(lan)
        s = await br.until(lan.page, WALK, "return (s.co||'').includes('đang lái xe này')", 'Lan: the scooter is taken, sit behind?', 8)
        check('Minh đang lái xe này' in s['co'], f"taken: {s['co']!r}")
        check(not any(q.get('ride') for q in s['people'] if q['pid'] == s['me']), 'Lan stays on foot (first come drives)')
        await shot(lan, '02-walk-taken')
        await lan.page.click('.walk-sheet .rd-co [data-wk="back"]')
        s = await br.until(lan.page, WALK, f'return s.people.some(q=>q.pid===s.me&&q.b==="{mpid}")', 'Lan sits behind Minh', 6)
        check('Đang ngồi sau xe của Minh' in (s['co'] or ''), f"Lan's line: {s['co']!r}")
        await minh.page.evaluate("async()=>{const {walk}=await import('/js/v4/walk.js');const st=walk.state(),m=st.people.find(q=>q.pid===st.me);walk.moveTo(m.x>300?140:460,m.y-90);}")
        await lan.page.wait_for_timeout(500)
        await shot(lan, '03-walk-lan-behind')
        await shot(minh, '04-walk-minh-driving')
        s = await br.until(lan.page, WALK, f'const a=s.people.find(q=>q.pid===s.me),b=s.people.find(q=>q.pid==="{mpid}");return a&&b&&!b.walking||Math.hypot(a.x-b.x,a.y-b.y)<2',
                           'Lan goes where Minh drives', 6)
        a = next(q for q in s['people'] if q['pid'] == s['me'])
        b = next(q for q in s['people'] if q['pid'] == mpid)
        check(abs(a['x'] - b['x']) < 2 and abs(a['y'] - b['y']) < 2, f'Lan is on his scooter ({a["x"]:.0f},{a["y"]:.0f} / {b["x"]:.0f},{b["y"]:.0f})')
        await lan.page.evaluate("async()=>{const {walk}=await import('/js/v4/walk.js');walk.moveTo(60,60);}")   # her tap: nothing
        await lan.page.wait_for_timeout(700)
        s = await lan.page.evaluate(WALK)
        a = next(q for q in s['people'] if q['pid'] == s['me'])
        check(a['b'] == mpid, 'her own taps do not move her off his scooter')
        await lan.page.click('.walk-sheet .rd-co [data-wk="off"]')
        s = await br.until(lan.page, WALK, 'return s.people.some(q=>q.pid===s.me&&!q.b)', 'Lan gets off', 6)
        check(True, '"Xuống xe": Lan on foot again')
        s = await br.until(lan.page, WALK, "return (s.co||'').includes('Ngồi sau')", 'Lan: "🛵 Ngồi sau" offered', 6)
        await shot(lan, '05-walk-offer')
        await lan.page.click('.walk-sheet .rd-co [data-wk="back"]')
        await br.until(lan.page, WALK, f'return s.people.some(q=>q.pid===s.me&&q.b==="{mpid}")', 'Lan sits behind again', 6)
        await minh.page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")   # Minh leaves the stroll
        s = await br.until(lan.page, WALK, f'return !s.people.some(q=>q.pid==="{mpid}")&&s.people.some(q=>q.pid===s.me&&!q.b)', 'Minh left: Lan on foot', 8)
        check(not s['co'], 'no line left over')
        await shot(lan, '06-walk-dropped')

        # ---- the fair ----
        await fair(minh)
        await br.until(minh.page, FAIR, 'return s.ride==="xe_ga"&&s.riding', 'Minh rides at the fair', 6)
        await minh.page.evaluate("()=>__fairWalk.walk(.45,.6)")
        await minh.page.wait_for_timeout(600)
        await fair(lan)
        s = await br.until(lan.page, FAIR, "return (s.co||'').includes('Ngồi sau')", 'Lan at the fair: sit behind offered', 8)
        check(not s['riding'], f"Lan on foot at the fair ({s['co']!r})")
        await shot(lan, '07-fair-offer')
        await lan.page.click('.fh-sheet .rd-co [data-co="back"]')
        s = await br.until(lan.page, FAIR, f'return s.back==="{mpid}"', 'Lan sits behind at the fair', 6)
        check('Đang ngồi sau xe của Minh' in (s['co'] or ''), f"fair line: {s['co']!r}")
        await minh.page.evaluate("()=>__fairWalk.walk(.75,.45)")
        await minh.page.wait_for_timeout(450)
        await shot(lan, '08-fair-lan-behind')
        await shot(minh, '09-fair-minh-driving')
        await minh.page.wait_for_timeout(900)
        s = await lan.page.evaluate(FAIR)
        theirs = next((q for q in s['crowd']['people'] if q['pid'] == mpid), None)
        check(theirs is not None and theirs['ride'] == 'xe_ga', 'Lan sees Minh riding')
        spot = await minh.page.evaluate("()=>__fairWalk.state().spots.find(x=>x==='nv'||x==='bc')")
        await minh.page.evaluate(f"()=>__fairWalk.go('{spot}')")
        s = await br.until(lan.page, FAIR, 'return !s.back', 'Minh parks at a stall: Lan gets off', 8)
        check(True, f'Minh parks at {spot}: Lan walks in with him')
        await lan.page.wait_for_timeout(900)
        await shot(lan, '10-fair-off-at-stall')
        for p in (minh, lan):
            await p.ctx.close()
        await browser.close()


async def main_async():
    problems, checks = [], []
    for size in br.SIZES:
        try:
            await run(size, problems, checks)
        except AssertionError as e:
            problems.append(f'{size}: {e}')
    print(*checks, sep='\n')
    return problems


def main():
    br.OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mnl-coride-', dir=os.environ.get('TMPDIR'), ignore_cleanup_errors=True) as tmp, br.servers(tmp) as (base, db):
        br.BASE, br.DB = base, db
        problems = asyncio.run(main_async())
    if problems:
        print('problems:', *problems, sep='\n  ')
        sys.exit(1)
    print('ok:', br.OUT)


if __name__ == '__main__':
    main()
