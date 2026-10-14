"""🧩 Ghép ba Phố Mây: plays whole levels in a real browser by tapping the tiles a player sees (dev tool / regression;
needs `pip install playwright` + chromium and TEST_DATABASE_URL).

Runs the real app on a throwaway story-mode server, seeds one save, opens the game and plays every level of the range
with the server's own solution (game.tile_match.level(n)['solution']), tapping each tile AT ITS CENTRE on screen
(touchscreen on a phone, mouse on a desktop), never by dispatching an event to the element. Before each tap:
  * the tile is drawn (not gone), face up (not a stack back), lit (not covered), inside the viewport and the stage;
  * document.elementFromPoint at its centre is the tile itself (not a neighbour, the tray, the boosters, the header);
  * its face is the level's icon for its kind.
After each tap the tray and the hold row on screen hold the icons the rules say (the Python Game replayed alongside).
Each level must end on the win card; the finished levels must reach "✓ Đã ghi nhận" (the server's journey.tile.lv).
Also: a level's icons are distinct, and each renders as a real glyph (not the blank box of a missing emoji).

    python scripts/browser_tile_levels.py [--levels 1-20] [--sizes 390x844,360x740] [--out DIR] [--shots 8,9]
Exit status 1 on any problem (listed in the JSON report).
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

BATCH = 12   # new levels per seeded session (the daily cap is 15)

CHECK = """([id,icon])=>{
  const el=document.querySelector(`.tm-tile[data-id="${id}"]`);if(!el)return 'no element';
  const out=[];
  if(el.classList.contains('tm-gone')||!el.getClientRects().length)return 'not drawn';
  if(el.classList.contains('tm-back'))out.push('face down');
  if(el.classList.contains('tm-off'))out.push('drawn as covered');
  const face=el.querySelector('.tm-face')?.textContent||'';if(face!==icon)out.push(`face ${JSON.stringify(face)} not ${icon}`);
  const b=el.getBoundingClientRect(),st=document.querySelector('.tm-stage').getBoundingClientRect();
  if(b.left<-0.5||b.top<-0.5||b.right>innerWidth+0.5||b.bottom>innerHeight+0.5)out.push('outside the viewport');
  if(b.left<st.left-1||b.top<st.top-1||b.right>st.right+1||b.bottom>st.bottom+1)out.push('outside the stage');
  const x=b.left+b.width/2,y=b.top+b.height/2,hit=document.elementFromPoint(x,y);
  if(!hit||hit.closest('.tm-tile')!==el){const o=hit?.closest('.tm-tile');
    out.push('covered at its centre by '+(o?`tile ${o.dataset.id}${o.classList.contains('tm-back')?' (face down)':''}`:(hit?(hit.className||hit.tagName):'nothing')));}
  return out.length?out.join('; '):{x,y};}"""
ROWS = """()=>{const pick=sel=>[...document.querySelectorAll('.tm-tile.tm-small:not(.tm-gone):not(.tm-pop)')]
    .map(el=>({el,b:el.getBoundingClientRect()})).filter(sel).sort((a,c)=>a.b.left-c.b.left).map(o=>o.el.textContent);
  const tray=document.querySelector('.tm-tray').getBoundingClientRect(),hold=document.querySelector('.tm-holdrow').getBoundingClientRect();
  const inside=(r,b)=>b.top>=r.top-2&&b.bottom<=r.bottom+2&&b.left>=r.left-2&&b.right<=r.right+2;
  return {tray:pick(o=>inside(tray,o.b)),hold:pick(o=>inside(hold,o.b)),
    all:document.querySelectorAll('.tm-tile.tm-small:not(.tm-gone):not(.tm-pop)').length};}"""
SETTLED = """()=>[...document.querySelectorAll('.tm-tile')].every(el=>!el.getAnimations().some(a=>a.playState==='running'))"""
# A glyph the font does not have draws like an unassigned code point (U+10FFFD): compare the pixels.
GLYPHS = """(icons)=>{const c=document.createElement('canvas');c.width=c.height=40;const x=c.getContext('2d');
  const px=s=>{x.clearRect(0,0,40,40);x.font='28px sans-serif';x.textBaseline='top';x.fillText(s,4,4);return x.getImageData(0,0,40,40).data.join(',');};
  const tofu=px('\\u{10FFFD}');return icons.filter(i=>px(i)===tofu);}"""


def mutate(db, token, fn):
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def seed(lv):
    def fn(s):
        from game import journey as jr, tile_match as tm, whats_new as wn
        j = s['journey']
        s['name'] = 'Lan'
        j.update(gender='female', intro=True, wallet=2400, life_day=6)
        jr._welcome_settings(s)
        s['settings'].update(tutorialDone=True, whatsNewSeen=wn.LATEST)
        j['interface'] = dict(newInterface=False, interfacePromptSeen=True)
        j['tile'] = dict(lv=lv, d=tm.today(), n=0, u={})
    return fn


def span(text):
    out = []
    for part in text.split(','):
        a, _, b = part.partition('-')
        out += range(int(a), int(b or a) + 1)
    return out


async def play_level(page, n, touch, problems, shots, out, tag):
    from game import tile_match as tm
    lv = tm.level(n)
    icons = lv['icons']
    if len(set(icons)) != len(icons):
        problems.append(f'[{tag}] level {n}: two kinds share an icon {icons}')
    missing = await page.evaluate(GLYPHS, icons)
    if missing:
        problems.append(f'[{tag}] level {n}: no glyph for {missing}')
    g = tm.Game(lv)
    await page.wait_for_selector('.tm-sheet .tm-tile', timeout=8000)
    await page.wait_for_timeout(500)
    if n in shots:
        await page.screenshot(path=str(out / f'{tag}-level{n}-start.png'))
    bad = 0
    for step, t in enumerate(lv['solution']):
        await page.wait_for_function(SETTLED, timeout=5000)
        icon = icons[g.kind[t]]
        r = await page.evaluate(CHECK, [t, icon])
        if isinstance(r, str):
            problems.append(f'[{tag}] level {n} step {step + 1}/{len(lv["solution"])} tile {t} {icon}: {r}')
            bad += 1
            if n in shots and bad == 1:
                await page.screenshot(path=str(out / f'{tag}-level{n}-step{step + 1}-tile{t}.png'))
            if bad > 3:
                return False
            el = await page.query_selector(f'.tm-tile[data-id="{t}"]')
            box = await el.bounding_box() if el else None
            if not box:
                return False
            r = dict(x=box['x'] + box['width'] / 2, y=box['y'] + box['height'] / 2)
        if touch:
            await page.touchscreen.tap(r['x'], r['y'])
        else:
            await page.mouse.click(r['x'], r['y'])
        g.tap(t)
        await page.wait_for_timeout(40)
        if g.won:
            break
        await page.wait_for_function(SETTLED, timeout=5000)
        await page.wait_for_timeout(380)   # a triple pops over .36 s
        rows = await page.evaluate(ROWS)
        want = dict(tray=[icons[g.kind[x]] for x in g.tray], hold=[icons[g.kind[x]] for x in g.hold])
        if rows['tray'] != want['tray'] or rows['hold'] != want['hold']:
            problems.append(f'[{tag}] level {n} step {step + 1}: tray shows {rows} not {want}')
            return False
    if not g.won:
        problems.append(f'[{tag}] level {n}: the solution did not win in the Python replay')
        return False
    try:
        await page.wait_for_selector('.tm-done.win', timeout=8000)
    except Exception:
        problems.append(f'[{tag}] level {n}: no win card after the last tile')
        await page.screenshot(path=str(out / f'{tag}-level{n}-nowin.png'))
        return False
    if n in shots:
        await page.wait_for_timeout(700)
        await page.screenshot(path=str(out / f'{tag}-level{n}-win.png'))
    return True


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--levels', default='1-20')
    ap.add_argument('--sizes', default='390x844,360x740')
    ap.add_argument('--out', default=str(ROOT.parent / '_tile_levels'))
    ap.add_argument('--shots', default='8')
    a = ap.parse_args()
    from playwright.async_api import async_playwright
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    levels, shots = span(a.levels), set(span(a.shots)) if a.shots else set()
    errors, problems, played = [], [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            exe = os.environ.get('PW_CHROMIUM')
            browser = await pw.chromium.launch(**({'executable_path': exe} if exe else {}))
            for size in a.sizes.split(','):
                w, h = map(int, size.split('x'))
                phone = min(w, h) < 600
                tag = size
                ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=phone, has_touch=phone)
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0');localStorage.setItem('mnl.x3.week','blocked')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m, tag=tag: m.type == 'error' and errors.append(f'[{tag}] {m.text}'))
                page.on('pageerror', lambda e, tag=tag: errors.append(f'[{tag}] {e}'))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                # consecutive runs of levels, at most BATCH new ones per seeded session (the daily cap)
                runs, cur = [], []
                for n in levels:
                    if cur and (n != cur[-1] + 1 or len(cur) >= BATCH):
                        runs.append(cur)
                        cur = []
                    cur.append(n)
                if cur:
                    runs.append(cur)
                for run in runs:
                    mutate(db, token, seed(run[0] - 1))
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                    await page.wait_for_timeout(1000)
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    await page.evaluate("""()=>{document.getElementById('tm-open')?.remove();const b=document.createElement('button');b.dataset.action='tileMatch';b.id='tm-open';
                      b.style.cssText='position:fixed;left:0;top:0;width:4px;height:4px;opacity:0;z-index:2147483647';document.body.append(b);}""")
                    await page.click('#tm-open')
                    await page.wait_for_selector('.tm-sheet[open] .tm-hero', timeout=8000)
                    await page.click('.tm-sheet .tm-bar [data-tm="play"]')
                    last = run[0] - 1
                    for i, n in enumerate(run):
                        if i:
                            await page.click('.tm-sheet .tm-bar [data-tm="next"]')
                        if not await play_level(page, n, phone, problems, shots, out, tag):
                            break
                        played.append(f'{tag}:{n}')
                        last = n
                    if last < run[0]:
                        continue
                    # the background sync: the card says "✓ Đã ghi nhận" and the server has every level of the run
                    try:
                        await page.wait_for_function("()=>!localStorage.getItem('mnl.tile.q')", timeout=30000 + 25000 * len(run))
                        await page.wait_for_selector('.tm-done.win .tm-gain', timeout=10000)
                        if '✓ Đã ghi nhận' not in await page.inner_text('.tm-done'):
                            problems.append(f'[{tag}] level {last}: the card does not say ✓ Đã ghi nhận')
                    except Exception:
                        problems.append(f'[{tag}] levels {run[0]}–{last}: the sync queue did not drain')
                    got = {}
                    mutate(db, token, lambda s: got.update(s['journey'].get('tile') or {}))
                    if got.get('lv') != last:
                        problems.append(f'[{tag}] server journey.tile.lv {got.get("lv")} after playing to {last}')
                    if last in shots:
                        await page.screenshot(path=str(out / f'{tag}-level{last}-synced.png'))
                await ctx.close()
            await browser.close()
    report = dict(played=len(played), errors=errors, problems=problems)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if errors or problems else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
