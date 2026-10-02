#!/usr/bin/env python3
"""Inside / outside check (dev tool, needs playwright + chromium).

For each career with areas (or --careers a,b), in portrait (390×844) and landscape (1280×800): starts a day,
then steps into every area of the workplace (BobaWorld.enterArea, the same path as the area chips) and checks,
like scripts/check_scenes.py, that every hotspot there is reachable from where the player stands, that the
area chips show and name the current area, and that the page logs no error. With --shots DIR it saves a
screenshot of each area (<career>-<area>-<view>.png). Exits 1 on any problem.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_v04 import Sweep, server  # noqa: E402
from check_scenes import CHECK  # noqa: E402

AREA_CAREERS = ['pilot', 'flight_attendant', 'milk_tea', 'grocery', 'delivery', 'pet_care', 'florist', 'restaurant',
                'homestay', 'clothing', 'salon', 'mother_baby', 'cafe_bakery']
CHIPS = """(id)=>{const bar=document.getElementById('sceneAreas');if(!bar||bar.hidden)return 'no area chips';
  const on=bar.querySelector('.sa-chip.on');if(!on||on.dataset.area!==id)return 'chip not on '+id;
  const r=bar.getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect();
  if(r.right>s.right+1||r.left<s.left-1)return 'chips overflow the stage';return '';}"""


async def run(base: str, only: list[str], shots: Path | None, lang: str) -> list[str]:
    from playwright.async_api import async_playwright
    boot = json.loads(urllib.request.urlopen(base + '/api/bootstrap').read())
    ids = [c for c in (only or AREA_CAREERS) if c in boot['state']['careers']]
    posts = (boot['content'].get('employment') or {}).get('postings', {})
    problems: list[str] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for vname, (w, h, mobile) in {'portrait': (390, 844, True), 'landscape': (1280, 800, False)}.items():
            ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=mobile, has_touch=mobile)
            page = await ctx.new_page()
            s = Sweep(page, vname, None)
            await page.goto(base + '/?navdebug=1')
            await s.ready()
            if lang == 'en':
                await s.cmd('settings', {'lang': 'en'})
                await s.reload()
            for cid in ids:
                await s.cmd('select_career', {}, cid)
                if posts.get(cid):
                    await s.cmd('job_quick', {'posting': posts[cid][0]['id'], 'confirm': True}, cid)
                await s.cmd('start_day', {}, cid)
                await s.reload()
                await page.wait_for_timeout(900)  # lazily loaded scene kinds
                areas = await page.evaluate('globalThis.__navWorld.areaIds()')
                if not areas:
                    problems.append(f'[{vname}] {cid}: no areas')
                    continue
                for area in areas:
                    await page.evaluate('(id)=>{const w=globalThis.__navWorld;w.navDebug=false;w.enterArea(id);}', area)
                    await page.wait_for_timeout(700)
                    for p in await page.evaluate(CHECK):
                        problems.append(f'[{vname}] {cid}/{area}: {p}')
                    if (msg := await page.evaluate(CHIPS, area)):
                        problems.append(f'[{vname}] {cid}/{area}: {msg}')
                    if shots:
                        await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close());globalThis.__navWorld.navDebug=false")
                        await page.wait_for_timeout(150)
                        await page.screenshot(path=str(shots / f'{cid}-{area}-{vname}.png'))
            await s.collect_misses()
            if lang == 'en' and s.misses:
                problems.append(f'[{vname}] untranslated: ' + ' | '.join(sorted(s.misses)[:40]))
            problems += [p for p in s.problems if 'job_quick' not in p and 'select_career -> 409' not in p and '409 (Conflict)' not in p]
            await ctx.close()
        await browser.close()
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--careers', default='')
    ap.add_argument('--shots', type=Path)
    ap.add_argument('--lang', default='vi', choices=['vi', 'en'])
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    with server() as base:
        problems = asyncio.run(run(base, [x for x in a.careers.split(',') if x], a.shots, a.lang))
    for p in problems:
        print(p)
    print(f'{len(problems)} problems')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
