#!/usr/bin/env python3
"""Word caps on the migrated screens (UI foundation, docs/UI_KIT.md; owner 06/10 "ít chữ hơn").

Opens each career on a 390×844 phone (clean layout on), starts the day, opens the work sheet and counts the words a
player sees: text inside the viewport, on top, not folded away (the same count as ui-kit.js wordBudget, which also
warns in the console of a dev build). Fails when a migrated screen is over its cap:

  intro (street-kit "Giới thiệu nghề" card)  ≤ 30   every street-kit career (21 + police/oil)
  toast (each note on screen)                ≤ 8    every career opened
  work  (the work sheet, mid-task)           ≤ 25   the careers in WORK_DONE (the per-screen waves add theirs)

Other screens are listed with their counts but do not fail (--all shows every one).

  TEST_DATABASE_URL=postgresql://… python scripts/check_word_caps.py [--careers a,b] [--engine chromium|webkit]
                                                                    [--all] [--json FILE]
Needs `pip install playwright` + the browser. Exit code 0 = within caps, 1 = over, 2 = could not run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_v04 import CMD, server  # noqa: E402

CAPS = {'work': 25, 'intro': 30, 'toast': 8}
# Careers whose intro is the street kit's card (public/js/careers/street_kit.js introCard).
INTRO = ('fruit', 'garbage', 'drain', 'homemaker', 'ice_cream', 'com', 'nail', 'pagoda', 'pho', 'photobooth', 'giupviec',
         'naucom', 'babysitter', 'library', 'oil', 'railway', 'nurse', 'lighthouse', 'rescue', 'lifeguard', 'police', 'tra_da')
# Work screens already cut to ≤ 25 words. Each per-screen wave adds its careers here once they pass.
WORK_DONE: tuple[str, ...] = ()
DEFAULT = INTRO + ('florist', 'repair', 'restaurant', 'clothing', 'teacher', 'tour_guide')

COUNT = r"""async () => {
  const d = [...document.querySelectorAll('dialog[open]')].pop();
  const kit = await import('/js/ui-kit.js');
  const b = d ? kit.wordBudget(d) : null;
  const toasts = [...document.querySelectorAll('#toasts>.toast:not(.open):not(.leaving)')].map(t => (t.innerText.match(/\S+/g) || []).filter(k => /\p{L}/u.test(k)).length);
  return {words: b ? b.words : 0, kind: b ? b.kind : 'none', toasts};
}"""

CHOOSE = """cid=>{const b=document.createElement('button');b.type='button';b.dataset.action='choose';b.dataset.career=cid;b.style.cssText='position:fixed;opacity:0';document.body.append(b);b.click();b.remove();}"""


async def settle(page, ms=1200):
    await page.wait_for_timeout(ms)
    for _ in range(4):
        n = await page.evaluate("""()=>{let n=0;for(const d of document.querySelectorAll('#wnDialog[open]')){d.close();n++;}
          for(const b of document.querySelectorAll('#confirmDialog[open] [data-action="confirmYes"]')){b.click();n++;}
          document.querySelectorAll('.tut-pill-x,.tut-note [data-note=later]').forEach(b=>{b.click();n++;});return n;}""")
        if not n:
            break
        await page.wait_for_timeout(400)


async def open_career(page, cid):
    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
    await page.evaluate(CHOOSE, cid)
    for _ in range(40):
        await settle(page, 300)
        if await page.evaluate("fetch('/api/state').then(r=>r.json()).then(s=>s.state.current)") == cid:
            break
    else:
        return False
    from game import employment
    posts = employment.postings(cid)   # an office job: hired at once (MNL_DEV job_quick)
    if posts:
        await page.evaluate(CMD, ['job_quick', {'posting': posts[0]['id'], 'confirm': True}, cid])
        await page.reload()
        await page.wait_for_selector('#app:not([hidden])', timeout=40000)
    await settle(page, 1500)
    if await page.evaluate("!!document.querySelector('[data-action=start]')"):
        await page.evaluate("document.querySelector('[data-action=start]').click()")
        await settle(page, 2200)
    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
    await settle(page, 2500)
    await page.evaluate("""()=>{const b=document.querySelector('.calm-what ~ [data-action=job], [data-action=job].btn')||document.querySelector('.dock-btn.main');b?.click();}""")
    await settle(page, 2200)
    return True


async def run(args) -> int:
    from playwright.async_api import async_playwright
    careers = [c for c in (args.careers.split(',') if args.careers else DEFAULT) if c]
    rows, over = [], []
    with server() as base:
        async with async_playwright() as pw:
            browser = await getattr(pw, args.engine).launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=args.engine != 'firefox')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.set_default_timeout(10000)
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await settle(page)
            for cid in careers:
                try:
                    if not await open_career(page, cid):
                        rows.append(dict(career=cid, error='could not open'))
                        continue
                    m = await page.evaluate(COUNT)
                    row = dict(career=cid, toast=max(m['toasts'] or [0]))
                    if m['kind'] == 'intro':
                        row['intro'] = m['words']
                        await page.evaluate("""()=>{const d=[...document.querySelectorAll('dialog[open]')].pop();
                          const b=d&&[...d.querySelectorAll('.ui-bar button,.sk-intro button')].find(b=>/Vào|Bắt đầu/.test(b.innerText)&&b.offsetParent);b?.click();}""")
                        await settle(page, 2200)
                        m = await page.evaluate(COUNT)
                        row['toast'] = max([row['toast'], *(m['toasts'] or [0])])
                    row['work'] = m['words']
                    rows.append(row)
                    checks = [('toast', True), ('intro', cid in INTRO), ('work', cid in WORK_DONE)]
                    for kind, enforced in checks:
                        v = row.get(kind)
                        if v is not None and v > CAPS[kind] and enforced:
                            over.append(f'{cid} {kind}: {v} words (cap {CAPS[kind]})')
                    print(f"{cid:18} intro {row.get('intro', '-')!s:>3}  work {row['work']:>3}  toast {row['toast']}", flush=True)
                except Exception as e:  # noqa: BLE001
                    rows.append(dict(career=cid, error=str(e)[:160]))
                    print(f'{cid:18} ERROR {str(e)[:160]}', flush=True)
            await browser.close()
    if args.json:
        Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    if args.all:
        for r in rows:
            print(r)
    errors = [r for r in rows if 'error' in r]
    if over:
        print('\nOVER THE CAP:\n  ' + '\n  '.join(over))
        return 1
    if errors and len(errors) == len(rows):
        return 2
    print(f'\nOK: {len(rows) - len(errors)} screens within the caps (enforced: intro on {len(INTRO)} street-kit careers, '
          f'toasts everywhere, work on {len(WORK_DONE)}).')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--careers', default='')
    ap.add_argument('--engine', default='chromium', choices=['chromium', 'webkit', 'firefox'])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--json', default='')
    sys.exit(asyncio.run(run(ap.parse_args())))


if __name__ == '__main__':
    main()
