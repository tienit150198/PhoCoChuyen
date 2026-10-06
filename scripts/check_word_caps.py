#!/usr/bin/env python3
"""Word caps on the migrated screens (UI foundation, docs/UI_KIT.md; owner 06/10 "ít chữ hơn").

Opens each career on a 390×844 phone (clean layout on), starts the day, opens the work sheet and counts the words a
player sees: text inside the viewport, on top, not folded away (the same count as ui-kit.js wordBudget, which also
warns in the console of a dev build). Fails when a migrated screen is over its cap:

  intro (street-kit "Giới thiệu nghề" card)  ≤ 30   every street-kit career (21 + police/oil)
  toast (each note on screen)                ≤ 8    every career opened
  work  (the work sheet, mid-task)           ≤ 25   the careers in WORK_DONE (the per-screen waves add theirs);
                                                    ≤ 30 where WORK_CAP says a deciding cue needs the room

Other screens are listed with their counts but do not fail (--all shows every one).

  --life: the life sheets instead (story-mode player, wave 5), each ≤ 30 (LIFE): HUD, town map, house, bank (before and
  after opening an account), fair (gift card, then the gate), stall, wardrobe, spending. Karaoke needs the live service
  and is measured by hand (15 words at 1.9.8).

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
         'naucom', 'babysitter', 'library', 'oil', 'railway', 'nurse', 'lighthouse', 'rescue', 'lifeguard', 'police', 'tra_da',
         'pilot', 'flight_attendant')   # wave 2: the air crew uses the same short card
# Work screens already cut to ≤ 25 words. Each per-screen wave adds its careers here once they pass.
WORK_DONE: tuple[str, ...] = ('drain', 'com', 'lighthouse', 'railway', 'tra_da', 'babysitter', 'pho', 'pagoda', 'rescue', 'giupviec',   # wave 1
                               'police', 'nurse', 'lifeguard', 'oil', 'pilot', 'flight_attendant')   # wave 2
# A screen may take up to 30 when a cue the right answer depends on needs the room (never fold such a cue away):
# drain's appointments, cơm's water rule and dish names, the logbook notes, pagoda's chores, trà đá's spot cues;
# the pilot's first hop: whoever stands at the cockpit door says what they want, in full (Anh Kiệt's hurry is a trap).
WORK_CAP = {'drain': 30, 'com': 30, 'lighthouse': 30, 'railway': 30, 'pagoda': 30, 'tra_da': 30, 'pilot': 30}
DEFAULT = INTRO + ('florist', 'repair', 'restaurant', 'clothing', 'teacher', 'tour_guide')

# Wave 3: the office desks (their first screen is the dossier's envelope: who asks and their words), the support desk
# and the pet shop. 30 where the ask itself needs the room (its demand is never cut): the timesheet, the mail sorting
# ("cái gì anh phải xem thì để riêng"), the helpdesk's call, the voucher tray, the support customer's words.
WAVE3 = ('group_accounting', 'hr_admin', 'secretary', 'it_helpdesk', 'corp_accounting', 'tax_payroll', 'customer_care', 'pet_shop')
WORK_DONE += WAVE3
WORK_CAP.update(hr_admin=30, secretary=30, it_helpdesk=30, corp_accounting=30, customer_care=30)
DEFAULT += WAVE3

# Wave 5: the last career screens. 30 where the deciding cue needs the room: delivery's customer ask stays whole
# (16 words: where, what, the awkward extra), the salon's title is the customer's demand ("Nâu lạnh đi làm, tỉa ngọn")
# and is never cut. Repair's and the salon's titles are the symptom/demand, so app.js header never shortens them.
WAVE5 = ('mother_baby', 'pharmacy', 'accounting', 'teacher', 'tour_guide', 'grocery', 'repair', 'farm', 'delivery',
         'homestay', 'pet_care', 'salon', 'clothing')
WORK_DONE += WAVE5
WORK_CAP.update(delivery=30, salon=30, pharmacy=30, mother_baby=30)   # the lot states; an occasion order's ask (day 2+)
DEFAULT += tuple(c for c in WAVE5 if c not in DEFAULT)

# Life sheets (cap 30, docs/UI_KIT.md): [name, rail action, rail group]; HUD is the home screen with no sheet open.
LIFE = (('HUD', '', ''), ('town', 'jrTown', 'pho'), ('house', 'house', 'tien'), ('bank', 'bank', 'tien'), ('fair', 'fair', 'pho'),
        ('stall', 'quay', 'tien'), ('wardrobe', 'jrWardrobe', 'minh'), ('spend', 'spend', 'pho'))
LIFE_CAP = 30
# One step further on a life sheet: the fair's gift card closed, the bank's account opened (its confirm accepted).
LIFE_DEEP = r"""()=>{const b=document.querySelector('dialog[open] [data-fh="giftok"]')||[...document.querySelectorAll('dialog[open] button')].find(b=>/Mở tài khoản miễn phí/.test(b.innerText));
  if(!b)return false;b.click();return true;}"""
LIFE_OK = r"""()=>{const b=[...document.querySelectorAll('button')].reverse().find(b=>/^(Mở tài khoản)$/.test(b.innerText.trim())&&b.offsetParent);b?.click();}"""
HUB = r"""async ([action, group]) => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  document.querySelector('[data-action=v4Menu]')?.click(); await wait(250);
  document.querySelector(`#rail .rail-group[data-group=${group}]`)?.click(); await wait(300);
  const b = document.querySelector(`#rail .rail-sub[data-group=${group}] [data-action=${action}]`) || document.querySelector(`#rail [data-action=${action}]`);
  if (!b) return false; b.click(); return true;}"""
LIFE_COUNT = r"""async () => {
  const d = [...document.querySelectorAll('dialog[open]')].pop();
  const kit = await import('/js/ui-kit.js');
  if (d) return kit.wordBudget(d).words;
  const app = document.getElementById('app'), vh = innerHeight, vw = innerWidth; let n = 0;   // the HUD: no sheet
  const tw = document.createTreeWalker(app, NodeFilter.SHOW_TEXT);
  for (let t; (t = tw.nextNode());) { const s = t.textContent.trim(), p = t.parentElement; if (!s || !p || p.closest('[hidden],.sr-only')) continue;
    const rg = document.createRange(); rg.selectNodeContents(t); if (![...rg.getClientRects()].some(r => r.width >= 1 && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw)) continue;
    if (p.checkVisibility && !p.checkVisibility({opacityProperty: true, visibilityProperty: true})) continue;
    n += s.split(/\s+/).filter(k => /\p{L}/u.test(k)).length; }
  return n;
}"""


async def run_life(args) -> int:
    """The life sheets of a new story-mode player (wave 5): each ≤ LIFE_CAP visible words on a 390×844 phone."""
    import datetime
    import os
    from playwright.async_api import async_playwright
    vn = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    os.environ.setdefault('MNL_FAIR_START', (vn - datetime.timedelta(days=1)).date().isoformat())   # the fair is on
    os.environ.setdefault('MNL_FAIR_DAYS', '7')
    rows, over = [], []
    with server(story=True) as base:
        async with async_playwright() as pw:
            browser = await getattr(pw, args.engine).launch()
            ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=args.engine != 'firefox')
            await ctx.add_init_script("try{localStorage.setItem('mnl.tut.done','1');localStorage.setItem('mnl.ui25d','0');localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.tut.tips','done');localStorage.setItem('mnl.clean','on')}catch(e){}")
            page = await ctx.new_page()
            page.set_default_timeout(15000)
            await page.goto(base + '/')
            await page.wait_for_selector('#app:not([hidden])', timeout=60000)
            await page.click('[data-action=jrGender][data-gender=female]')
            await page.fill('#jr-name', 'Mây')
            await page.click('form[data-jr-form=start] button[type=submit]')
            await settle(page, 2500)
            for _ in range(6):
                await page.keyboard.press('Escape')
                await settle(page, 400)
            for name, action, group in LIFE:
                try:
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close());document.documentElement.classList.remove('menu-open')")
                    await settle(page, 600)
                    if action and not await page.evaluate(HUB, [action, group]):
                        rows.append(dict(screen=name, error='no menu entry'))
                        print(f'{name:10} ERROR no menu entry', flush=True)
                        continue
                    await settle(page, 2500)
                    for state in ('', '+'):
                        if state:
                            if not await page.evaluate(LIFE_DEEP):
                                break
                            await page.wait_for_timeout(1200)
                            await page.evaluate(LIFE_OK)
                            await page.wait_for_timeout(7000 if name == 'bank' else 2000)   # the bank's good-news line fades after 6 s
                        n = await page.evaluate(LIFE_COUNT)
                        rows.append(dict(screen=name + state, life=n))
                        if n > LIFE_CAP:
                            over.append(f'{name + state} life: {n} words (cap {LIFE_CAP})')
                        print(f'{name + state:10} life {n:>3}', flush=True)
                except Exception as e:  # noqa: BLE001
                    rows.append(dict(screen=name, error=str(e)[:160]))
                    print(f'{name:10} ERROR {str(e)[:160]}', flush=True)
            await browser.close()
    if args.json:
        Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    if over:
        print('\nOVER THE CAP:\n  ' + '\n  '.join(over))
        return 1
    errors = [r for r in rows if 'error' in r]
    if errors and len(errors) == len(rows):
        return 2
    print(f'\nOK: {len(rows) - len(errors)} life screens within {LIFE_CAP} words.')
    return 0


COUNT = r"""async () => {
  const d = [...document.querySelectorAll('dialog[open]')].pop();
  const kit = await import('/js/ui-kit.js');
  const b = d ? kit.wordBudget(d) : null;
  const toasts = [...document.querySelectorAll('#toasts>.toast:not(.open):not(.leaving), .ui-bar-note:not(.open)')].filter(t => t.getClientRects().length).map(t => (t.innerText.match(/\S+/g) || []).filter(k => /\p{L}/u.test(k)).length);
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
                        v, cap = row.get(kind), WORK_CAP.get(cid, CAPS[kind]) if kind == 'work' else CAPS[kind]
                        if v is not None and v > cap and enforced:
                            over.append(f'{cid} {kind}: {v} words (cap {cap})')
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
    ap.add_argument('--life', action='store_true', help='the life sheets (town, house, bank, fair…) instead of careers')
    args = ap.parse_args()
    sys.exit(asyncio.run(run_life(args) if args.life else run(args)))


if __name__ == '__main__':
    main()
