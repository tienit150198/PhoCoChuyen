#!/usr/bin/env python3
"""Workplace scene check (dev tool, needs playwright + chromium).

For every career (or --careers a,b), in portrait (390×844) and landscape
(1280×800): opens the stage with ?navdebug=1, then checks in the live world
that every hotspot has an approach spot that is walkable and reachable from
the player's home, that the home itself is walkable, and that each hotspot's
hit point lies inside the scene frame. With --shots DIR it also saves a
screenshot of each stage. Exits 1 on any problem.
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

CHECK = """()=>{const w=globalThis.__navWorld,out=[];if(!w)return ['no world (navdebug off?)'];
  const portrait=w.isPortrait(),frame=portrait?[0,0,700,890]:[0,0,1200,790],home=w.navHome();
  w.player.x=home.x;w.player.y=home.y;w.player.path=[];w.navBuild(true);
  if(!w.navFree(home.x,home.y))out.push('home is not walkable');
  for(const h of w.hotspots){if(h.id.startsWith('staff:'))continue;
    const pt=h.point;if(!(pt.x>=frame[0]&&pt.x<=frame[2]&&pt.y>=frame[1]&&pt.y<=frame[3]))out.push(h.id+' hit point outside the frame');
    const spots=h.approach||[];if(!spots.length){out.push(h.id+' has no approach spot');continue;}
    const ok=spots.some(s=>w.navFree(s.x,s.y)&&w.navPath(s.x,s.y,true)!==null);
    if(!ok)out.push(h.id+' unreachable ('+spots.map(s=>{const p=w.project(s.x,s.y);return Math.round(p.x)+','+Math.round(p.y)+(w.navFree(s.x,s.y)?'':' blocked');}).join(' | ')+')');}
  return out;}"""


async def run(base: str, only: list[str], shots: Path | None) -> list[str]:
    from playwright.async_api import async_playwright
    boot = json.loads(urllib.request.urlopen(base + '/api/bootstrap').read())
    ids = [c for c in boot['state']['careers'] if not only or c in only]
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
            for cid in ids:
                await s.cmd('select_career', {}, cid)
                if posts.get(cid):
                    await s.cmd('job_quick', {'posting': posts[cid][0]['id'], 'confirm': True}, cid)
                await s.cmd('start_day', {}, cid)
                await s.reload()
                await page.wait_for_timeout(700)  # lazily loaded scene kinds
                for p in await page.evaluate(CHECK):
                    problems.append(f'[{vname}] {cid}: {p}')
                if shots:
                    await page.evaluate("globalThis.__navWorld.navDebug=false")
                    await page.screenshot(path=str(shots / f'{cid}-{vname}.png'))
            problems += [p for p in s.problems if 'job_quick' not in p]
            await ctx.close()
        await browser.close()
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--careers', default='')
    ap.add_argument('--shots', type=Path)
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    with server() as base:
        problems = asyncio.run(run(base, [x for x in a.careers.split(',') if x], a.shots))
    for p in problems:
        print(p)
    print(f'{len(problems)} problems')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
