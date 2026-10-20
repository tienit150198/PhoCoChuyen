#!/usr/bin/env python3
"""🔑 Lễ tân Hoa Sứ walkthrough (dev tool, needs `pip install playwright` and a Chrome/Chromium).

For each work layout (gọn = data-clean on, đầy đủ = off) and each screen size: a dev server (MNL_DEV=1), the desk
picked and hired by command, the shift opened, then the three trial check-ins played the way a player does on the
screen: tap the needs, drag the first guest card onto a room (the rest by tap card → tap room), pick the keys on the
hook board, load the luggage cart, write the handover; a desk situation is answered when one pops up. Then one job of
every other kind (check-out, the cleaning plan, the morning timeline, a complaint, lost property) and the Sổ nghề page.
Every step is screenshotted; the report lists overflow (a page wider than the screen) and page errors.

  TEST_DATABASE_URL=postgresql://…/scratch python scripts/browser_reception.py [--sides on,off]
      [--sizes 360x740,390x844,844x390,1366x900] [--shots DIR] [--server-python PATH]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.browser_coach import ACT, CMD, server, settle  # noqa: E402
from game.careers import PLUGINS  # noqa: E402

R = PLUGINS['reception']
SHEET = '#sheet[open]'
LANG = os.environ.get('MNL_LANG', 'vi')   # MNL_LANG=en: the English pack
# A command through the game's own delegate (a hidden data-command button): the page's state follows it.
SEND = """([c,p])=>{const b=document.createElement('button');b.dataset.command=c;b.dataset.payload=JSON.stringify(p||{});b.hidden=true;document.body.append(b);b.click();b.remove();}"""
OVERFLOW = "()=>{const d=document.documentElement;const s=document.querySelector('#sheet[open] .sheet-body')||d;return [d.scrollWidth>d.clientWidth+1,s.scrollWidth>s.clientWidth+1]}"


def key_of(t: dict):
    """The answers of a job as the server holds them (pure: day, slot, trial)."""
    slot = int(t['id'].rsplit('-', 1)[1])
    if t.get('trial') in ('normal', 'early', 'group'):
        return R.trial_brief(t['day'], slot, t['trial'])
    full = R.make_task(t['day'], slot, t['created_turn'])
    return full['needs'], full['needs']['steps'], full['_key']


async def state(page):
    return (await page.evaluate("fetch('/api/state').then(r=>r.json())"))['state']['careers']['reception']


async def desk(page, log, shot=None):
    """Answer a desk situation with its first option (the walkthrough is about the screen, not the choice)."""
    sel = f'{SHEET} .sk-event .sk-opt'
    if await page.locator(sel).count():
        log.append('desk: ' + (await page.locator(f'{SHEET} .sk-event h3').first.inner_text()))
        if shot:
            await page.locator(f'{SHEET} .sk-event').first.scroll_into_view_if_needed()
            await shot(f'desk-{len(log):02d}')
        await page.locator(sel).first.click()
        await page.wait_for_timeout(500)
        if shot:
            await shot(f'desk-{len(log):02d}-after')


async def play_step(page, t, st, key, work, log):
    sid, typ = st['id'], st['type']
    want = sorted(f'k{no}' for no in (work.get('arrival.rooms') or {}).values()) if sid == 'arrival.keys' else key[sid]
    if typ == 'choice':
        await page.evaluate("([v])=>{const b=[...document.querySelectorAll('#sheet[open] .rc-option')].find(e=>JSON.parse(e.dataset.payload).value===v);b.scrollIntoView({block:'center'});b.click();}", [want])
    elif typ in ('multi', 'order'):
        for v in want:
            await page.locator(f'{SHEET} .rc-chip[data-id="{v}"]').click()
        await page.locator(f'{SHEET} .rc-send').click()
    elif typ == 'assign':
        drag, drop = ('.rc-guest', '.rc-room') if sid == 'arrival.rooms' else ('.rc-item', '.rc-shelf')
        first = True
        for card, target in want.items():
            src = page.locator(f'{SHEET} {drag}[data-id="{card}"]')
            dst = page.locator(f'{SHEET} {drop}[data-target="{target}"]')
            if first:   # one real drag (pointer down, move, up) per board
                await src.scroll_into_view_if_needed()
                a, b = await src.bounding_box(), await dst.bounding_box()
                ax, ay = a['x'] + a['width'] / 2, a['y'] + a['height'] / 2
                bx, by = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
                await page.mouse.move(ax, ay)
                await page.mouse.down()
                for i in range(1, 9):
                    await page.mouse.move(ax + (bx - ax) * i / 8, ay + (by - ay) * i / 8)
                await page.mouse.up()
                await page.wait_for_timeout(500)
                first = False
                if await page.evaluate(f"([c])=>!!document.querySelector('#sheet[open] {drag}[data-id=\"'+c+'\"].placed')", [card]):
                    log.append(f'drag ok: {card} → {target}')
                    continue
                log.append(f'drag missed: {card} → {target}, tapping')
                await page.locator(f'{SHEET} .rc-row .ghost').first.click()   # Làm lại: start the board clean
                await page.wait_for_timeout(300)
            await src.click()
            await dst.click()
        await page.locator(f'{SHEET} .rc-send').click()
    elif typ == 'times':
        for fid, minutes in want.items():
            await page.locator(f'{SHEET} select[data-id="{fid}"]').select_option(str(minutes))
            await page.wait_for_timeout(150)
        await page.locator(f'{SHEET} .rc-send').click()
    else:
        box = page.locator(f'{SHEET} [data-sk-amt]')
        await box.fill(str(want))
        await box.dispatch_event('input')
        await page.locator(f'{SHEET} .sk-amt-go').click()
    await page.wait_for_timeout(700)


async def play_job(page, tid, shot, log):
    for n in range(30):
        await desk(page, log, shot)
        c = await state(page)
        t = next(x for x in c['tasks'] if x['id'] == tid)
        if t['status'] == 'completed':
            await shot(f'{tid}-done')
            return t
        if not t['known']:
            await page.evaluate(ACT, ['job', {'task': tid}])
            await page.wait_for_timeout(400)
            await shot(f'{tid}-ask')
            await page.locator(f'{SHEET} .sk-ask').click()
            await page.wait_for_timeout(700)
            continue
        brief, steps, key = key_of(t)
        st = steps[t['at']]
        await shot(f'{tid}-{t["at"]:02d}-{st["id"]}')
        await play_step(page, t, st, key, t.get('work') or {}, log)
    raise RuntimeError('job did not finish: ' + tid)


async def walk(browser, base, side, size, shots, report):
    w, h = (int(x) for x in size.split('x'))
    ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=True, is_mobile=w < 700, device_scale_factor=1)
    page = await ctx.new_page()
    out = dict(side=side, size=size, problems=[], log=[], overflow=[])
    page.on('pageerror', lambda e: out['problems'].append(f'exception: {str(e)[:200]}'))
    tag = f'{side}-{size}'

    async def shot(name):
        if shots:
            await page.screenshot(path=str(shots / f'{tag}-{name}.png'))
        o = await page.evaluate(OVERFLOW)
        if any(o):
            out['overflow'].append(name)

    await page.goto(base)
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_timeout(700)
    await settle(page)
    await page.evaluate(CMD, ['select_career', {}, 'reception'])
    await page.evaluate(CMD, ['job_quick', {'posting': 'rc-hoasu', 'confirm': True}, 'reception'])
    await page.evaluate(CMD, ['settings', {'newInterface': True, 'interfacePromptSeen': True, **({'lang': LANG} if LANG != 'vi' else {})}, 'reception'])
    await page.evaluate("v=>{try{localStorage.setItem('mnl.clean',v);localStorage.removeItem('mnl.clean.c');localStorage.setItem('mnl.coach.off','1');}catch{}}", side)
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_timeout(1200)
    await settle(page)
    await page.evaluate(SEND, ['start_day', {}])
    await page.wait_for_timeout(1500)
    await page.evaluate(ACT, ['workbench', {}])
    await page.wait_for_timeout(1200)
    await page.evaluate("()=>document.querySelector('#coachLayer [data-coach-btn=\"off\"],#coachChip [data-chip=\"x\"]')?.click()")
    await shot('00-intro')
    if await page.locator(f'{SHEET} .sk-intro-go').count():
        await page.locator(f'{SHEET} .sk-intro-go').click()
        await page.wait_for_timeout(700)
    c = await state(page)
    for t in [x for x in c['tasks'] if x['status'] != 'completed']:
        done = await play_job(page, t['id'], shot, out['log'])
        out['log'].append(f'{done["id"]} {done.get("trial")} q{done["quality"]}')
    c = await state(page)
    out['trial'] = c['data']['trial']
    # day 2 (desk situations start from day 2): every job of the day, then more until every kind was played
    await page.evaluate(SEND, ['end_day', {'carry_event': True}])
    await page.wait_for_timeout(1500)
    await shot('50-summary')
    await settle(page)
    await page.evaluate("()=>document.querySelectorAll('dialog[open] [data-action=\"close\"]').forEach(b=>b.click())")
    await page.evaluate(SEND, ['start_day', {}])
    await page.wait_for_timeout(1500)
    await page.evaluate(ACT, ['workbench', {}])
    await page.wait_for_timeout(1000)
    kinds = set()
    for _ in range(12):
        c = await state(page)
        open_ = [x for x in c['tasks'] if x['status'] not in ('completed', 'cancelled', 'referred')]
        if not open_:
            if kinds >= {'arrival', 'checkout', 'rooms', 'services', 'complaint', 'lost'}:
                break
            before = len(c['tasks'])
            await page.evaluate(SEND, ['more_work', {}])
            await page.wait_for_timeout(1200)
            if len((await state(page))['tasks']) <= before:
                break
            continue
        done = await play_job(page, open_[0]['id'], shot, out['log'])
        kinds.add(done['kind'])
        out['log'].append(f'{done["id"]} {done["kind"]} q{done["quality"]}')
    out['kinds'] = sorted(kinds)
    await page.evaluate(ACT, ['car:notes', {}])
    await page.wait_for_timeout(700)
    await shot('99-book')
    await ctx.close()
    report.append(out)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sides', default='on,off')
    ap.add_argument('--sizes', default='360x740,390x844,844x390,1366x900')
    ap.add_argument('--shots', default='')
    ap.add_argument('--report', default='')
    ap.add_argument('--server-python', default=sys.executable)
    a = ap.parse_args()
    shots = Path(a.shots) if a.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright
    report = []
    with server(a.server_python) as base:
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL') or None)
            for side in a.sides.split(','):
                for size in a.sizes.split(','):
                    try:
                        await walk(browser, base, side, size, shots, report)
                    except Exception as e:  # noqa: BLE001 - one layout failing still reports the others
                        report.append(dict(side=side, size=size, problems=[f'walk failed: {e!r}'[:400]]))
            await browser.close()
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if a.report:
        Path(a.report).write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    asyncio.run(main())
