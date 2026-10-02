#!/usr/bin/env python3
"""Restock sweep (dev tool, needs `pip install playwright` + chromium).

Players asked "xếp hàng mới lên kệ như nào?". This plays a grocery (Tạp Hoá Cô Ba) customer
whose basket needs an item the shelf has none of, on a 390×844 phone, pressing ONLY what the
game highlights (the pulse, the bottom button, the "Bước tiếp theo" hint) and saying yes to
confirm dialogs, the same "follow the game" picker as browser_first_day.py:

  counter → "📦 Nhập hàng" → stock room filtered to that item, order form open → "Đặt"
  → "⏳ Chờ thêm 20 phút" until the crate is at the door (the express courier: 30–60 minutes of
  shop time, each wait is one 20-minute beat, inventory.clock) → "Mở thùng & xếp lên kệ"
  → count the crate (once press-and-hold on the crate, then tap the rest) → "Nhận lên kệ" → "Về bán tiếp"
  → scan → bill → paid.

Passes when the item is back on the shelf, the customer is served with it on the bill, and no
console error, error toast or dead end happened on the way.

  python scripts/browser_restock.py [--shots DIR] [--report FILE]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_first_day import CMD, PICK, dev_start, server  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CID = 'grocery'
PREFER = ('milk', 'bread', 'egg', 'noodle', 'soda', 'snack')

STATE = """async (cid)=>{const s=await fetch('/api/state').then(r=>r.json());return s;}"""
COUNTED = "[document.querySelectorAll('#sheet[open] .inv-crate .inv-good.on').length,document.querySelectorAll('#sheet[open] .inv-crate .inv-good').length]"


def task_of(st: dict, tid: str) -> dict:
    return next(t for t in st['state']['careers'][CID]['tasks'] if t['id'] == tid)


async def setup(page) -> tuple[str, str]:
    """Open day 1, take a checkout customer's basket and empty the shelf of one item in it."""
    await page.evaluate(CMD, ['start_day', {}, CID])
    st = await page.evaluate(STATE, CID)
    c = st['state']['careers'][CID]
    tasks = [t for t in c['tasks'] if t.get('kind') == 'checkout' and t['status'] not in ('completed', 'cancelled', 'referred')]
    assert tasks, 'no checkout customer dealt on day 1'
    best = None
    for t in tasks:
        # A customer's basket is only known once they put it on the counter ("Mời khách" = ask).
        if c.get('active_task') != t['id']:
            await page.evaluate(CMD, ['task_select', {'task': t['id']}, CID])
        if not t.get('known'):
            await page.evaluate(CMD, ['ask', {'task': t['id']}, CID])
        st = await page.evaluate(STATE, CID)
        c = st['state']['careers'][CID]
        t = task_of(st, t['id'])
        items = [l['item'] for l in (t.get('needs') or {}).get('lines') or [] if not l.get('weighed') and l['item'] != 'beer']
        pick = next((k for k in PREFER if k in items), items[0] if items else None)
        if pick:
            best = (t, pick)
            break
    assert best, 'no checkout customer with a packaged item'
    t, item = best
    # Throw out every lot of that item (the public state lists them under inventory.lots).
    for lot in [l for l in c['inventory']['lots'] if l['item'] == item and l['qty'] > 0]:
        r = await page.evaluate(CMD, ['inv_discard', {'lot': lot['id'], 'confirm': True}, CID])
        assert r['status'] == 200, r
    st = await page.evaluate(STATE, CID)
    assert st['state']['careers'][CID]['inventory']['stock'][item] == 0, 'shelf not empty'
    return t['id'], item


async def play(browser, base: str, shots: Path | None, max_steps: int = 90) -> dict:
    ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2)
    page = await ctx.new_page()
    out = dict(ok=False, steps=[], problems=[], item=None)
    page.on('console', lambda m: m.type == 'error' and out['problems'].append(f'console: {m.text[:200]}'))
    page.on('pageerror', lambda e: out['problems'].append(f'exception: {str(e)[:200]}'))
    page.on('response', lambda r: '/api/' in r.url and r.status >= 500 and out['problems'].append(f'HTTP {r.status} {r.url}'))
    n = [0]

    async def shot(name):
        if shots:
            n[0] += 1
            await page.evaluate("document.querySelectorAll('.toast').forEach(t=>t.remove())")
            await page.screenshot(path=str(shots / f'flow-{n[0]:02d}-{name}.png'))

    try:
        await page.goto(base)
        await page.wait_for_selector('#app:not([hidden])', timeout=20000)
        # "Có gì mới" opens by itself on a fresh save and writes whatsNewSeen; let that write land before the
        # setup's own writes, or it races them (a harmless 409 "đã thay đổi ở tab khác" in the console).
        with contextlib.suppress(Exception):
            await page.wait_for_selector('#wnDialog[open]', timeout=4000)
            await page.eval_on_selector('#wnDialog .wn-foot [data-wn="close"]', 'e=>e.click()')
        await page.wait_for_timeout(600)
        await dev_start(page, CID)
        tid, item = await setup(page)
        out['item'] = item
        await page.reload()
        await page.wait_for_selector('#app:not([hidden])', timeout=20000)
        await page.wait_for_timeout(800)
        seen: set[str] = set()
        views: list[str] = []
        last, same, restocked, held = None, 0, False, False
        for i in range(max_steps):
            st = await page.evaluate(STATE, CID)
            c = st['state']['careers'][CID]
            t = task_of(st, tid)
            if c['inventory']['stock'].get(item, 0) > 0:
                restocked = True
            if t['status'] == 'completed':
                out['ok'] = True
                out['result'] = t.get('result')
                out['scanned'] = t.get('scanned')
                break
            pick = await page.evaluate(PICK)
            view = await page.evaluate("document.querySelector('#sheet[open] .career-job')?'job':document.querySelector('#sheet[open] .inv-status')?'stock room':document.querySelector('#sheet[open]')?'sheet':'scene'")
            if not views or views[-1] != view:
                views.append(view)
                await shot(view.replace(' ', '-'))
            out['steps'].append(f"[{view}] {pick['kind']}: {pick.get('text', '')}" + (f"  [hint: {pick['hint']}]" if pick.get('hint') else ''))
            if pick['kind'] == 'none':
                out['problems'].append(f'stuck in {view}: nothing highlighted ({pick.get("hint") or pick.get("text", "")[:120]})')
                break
            if pick['kind'] == 'host':
                out['problems'].append(f'had to press a host control: {pick.get("text")}')
            key = (pick['kind'], pick.get('text'), pick.get('hint'), st['revision'])
            same = same + 1 if key == last else 0
            last = key
            if same >= 3:
                out['problems'].append(f'stuck: pressing "{pick.get("text")}" changes nothing')
                break
            # The crate's goods: the first time, press and hold the crate's rim (counts one after another),
            # then the picker taps whatever is left, one good at a time.
            if not held and await page.evaluate("!!document.querySelector('[data-fd-pick].inv-good')"):
                held = True
                before, total = await page.evaluate(COUNTED)
                # A real finger cannot reach through a popup: close "Có gì mới" first, as a player would.
                if await page.evaluate("!!document.querySelector('#wnDialog[open]')"):
                    await page.eval_on_selector('#wnDialog .wn-foot [data-wn="close"]', 'e=>e.click()')
                    await page.wait_for_timeout(400)
                await page.evaluate("document.querySelector('#sheet[open] .inv-crate')?.scrollIntoView({block:'center'})")
                await page.wait_for_timeout(300)
                # Press on the crate's last uncounted good (the guide's arrow sits by the first one).
                box = await page.locator('#sheet[open] .inv-crate').first.locator('.inv-good:not(.on)').last.bounding_box()
                px, py = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
                under = await page.evaluate("([x,y])=>{const e=document.elementFromPoint(x,y);return e?.closest('.inv-crate')?'':(e?.className||e?.tagName||'nothing')}", [px, py])
                if under:
                    out['problems'].append(f'press-and-hold: the crate is covered by "{under}"')
                await page.mouse.move(px, py)
                await page.mouse.down()
                await page.wait_for_timeout(1000)
                await page.mouse.up()
                await page.wait_for_timeout(500)
                after, _ = await page.evaluate(COUNTED)
                out['steps'].append(f'[stock room] hold: counted {before} → {after} of {total}')
                if after - before < min(3, total - before):
                    out['problems'].append(f'press-and-hold on the crate counted {after - before} goods in 1 s')
                continue
            sel = pick.get('sel') or '[data-fd-pick]'
            await page.eval_on_selector(sel, 'e=>e.click()')
            await page.wait_for_timeout(650)
            for msg in await page.evaluate("[...document.querySelectorAll('.toast.error')].map(e=>e.dataset.msg||e.textContent)"):
                if msg not in seen:
                    seen.add(msg)
                    out['problems'].append(f'error toast after "{pick.get("text")}": {msg}')
        else:
            out['problems'].append(f'customer not served in {max_steps} presses')
        out['views'] = views
        st = await page.evaluate(STATE, CID)
        c = st['state']['careers'][CID]
        out['stock_after'] = c['inventory']['stock'].get(item)
        got = [o for o in c['inventory']['orders'] if o['item'] == item and o['status'] == 'received']
        if not got:
            out['problems'].append(f'no {item} crate was counted onto the shelf')
        if not restocked:
            out['problems'].append(f'{item} never came back on the shelf')
        if out['ok'] and not (out.get('scanned') or {}).get(item):
            out['problems'].append(f'customer served without the {item} they came for')
        if 'stock room' not in views:
            out['problems'].append('the glowing path never led to the stock room')
        await shot('done')
    except Exception as e:
        out['problems'].append(f'error: {str(e)[:300]}')
        with contextlib.suppress(Exception):
            await shot('error')
    await ctx.close()
    return out


async def run(base: str, shots: Path | None) -> dict:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        r = await play(browser, base, shots)
        await browser.close()
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shots', type=Path, help='directory for screenshots')
    ap.add_argument('--report', type=Path, default=ROOT / 'artifacts' / 'browser-restock.json')
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    with server(dev=True) as base:
        r = asyncio.run(run(base, a.shots))
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
    ok = r['ok'] and not r['problems']
    print(f"{'PASS' if ok else 'FAIL'} grocery restock ({r.get('item')}): {len(r['steps'])} presses · {' → '.join(r.get('views', []))}")
    for s in r['steps']:
        print('   ', s)
    for p in r['problems']:
        print('   !', p)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
