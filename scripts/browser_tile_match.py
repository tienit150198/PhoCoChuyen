"""🧩 Ghép ba Phố Mây: a browser walk-through (dev tool, needs `pip install playwright` + chromium, TEST_DATABASE_URL).

Runs the real app on a throwaway story-mode server, seeds one save (a named character; levels already cleared set
per pass), then in the browser: opens the game from its menu entry, starts a level, taps through it with the level's
intended solution, waits for the server to accept the replay and shows the level-complete card. JPG screenshots of
level 1, a mid level and a level past 80 at 390 × 844, the complete card, plus 360 × 780 and a landscape phone.
Checks: no console error, no sideways scroll, every tile inside the stage, the server's journey.tile after the win.

    python scripts/browser_tile_match.py [out_dir]
"""
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_tile_shots'
FIT = """()=>{const st=document.querySelector('.tm-stage');if(!st)return 'no stage';const r=st.getBoundingClientRect();
  const out=[];for(const el of document.querySelectorAll('.tm-tile:not(.tm-gone)')){const b=el.getBoundingClientRect();
    if(b.left<r.left-1||b.right>r.right+1||b.top<r.top-1||b.bottom>r.bottom+1)out.push(el.dataset.id);}
  return out.length?'outside: '+out.slice(0,8).join(','):'';}"""
WORDS = """()=>{const root=document.querySelector('.tm-sheet[open]');if(!root)return 0;let n=0;
  const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  for(let t=walk.nextNode();t;t=walk.nextNode()){const el=t.parentElement;if(!el||!el.getClientRects().length||el.closest('[hidden],.tm-tile,details:not([open])>:not(summary)'))continue;
    n+=(t.textContent.match(/[A-Za-zÀ-ỹ]+/g)||[]).length;}
  return n;}"""
WORD_CAP = 30   # docs/UI_KIT.md: a life sheet
WIDE ="()=>document.documentElement.scrollWidth>innerWidth+1||document.querySelector('.tm-sheet')?.scrollWidth>document.querySelector('.tm-sheet')?.clientWidth+1"


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


async def main():
    from playwright.async_api import async_playwright
    from game import tile_match as tm
    OUT.mkdir(parents=True, exist_ok=True)
    errors, problems, words = [], [], {}
    passes = [('lv1', 390, 844, 0, 1, True), ('mid', 390, 844, 44, 45, False), ('lv85', 390, 844, 84, 85, False),
              ('small', 360, 780, 59, 60, False), ('landscape', 844, 390, 29, 30, False)]
    with server() as (base, db):
        async with async_playwright() as pw:
            exe = os.environ.get('PW_CHROMIUM')   # an already installed Chromium when the package's build is not cached
            browser = await pw.chromium.launch(**({'executable_path': exe} if exe else {}))
            for tag, w, h, done, lv, play in passes:
                ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=True, has_touch=True)
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0');localStorage.setItem('mnl.x3.week','blocked')}catch(e){}")
                page = await ctx.new_page()

                async def snap(name):
                    await page.screenshot(path=str(OUT / name), type='jpeg', quality=82)
                    n = await page.evaluate(WORDS)
                    words[name] = n
                    if n > WORD_CAP:
                        problems.append(f'[{tag}] {name}: {n} words (cap {WORD_CAP})')
                page.on('console', lambda m: m.type == 'error' and errors.append(f'{m.text}'))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                mutate(db, token, seed(done))
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1200)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                # the menu entry, as Khu phố draws it
                await page.evaluate("""()=>{const b=document.createElement('button');b.dataset.action='tileMatch';b.id='tm-open';
                  b.style.cssText='position:fixed;left:0;top:0;width:4px;height:4px;opacity:0;z-index:2147483647';document.body.append(b);}""")
                await page.click('#tm-open')
                await page.wait_for_selector('.tm-sheet[open] .tm-hero', timeout=8000)
                await page.wait_for_timeout(400)
                if tag in ('lv1', 'mid'):
                    await snap(f'{tag}-lobby.jpg')
                await page.click('.tm-sheet .tm-bar [data-tm="play"]')
                await page.wait_for_selector('.tm-sheet .tm-tile', timeout=8000)
                await page.wait_for_timeout(700)
                level = tm.level(lv)
                path = level['solution']
                first = 0 if play else min(len(path) // 5, 9)
                for t in path[:first]:
                    await page.dispatch_event(f'.tm-tile[data-id="{t}"]', 'pointerdown')
                    await page.wait_for_timeout(60)
                await page.wait_for_timeout(500)
                bad = await page.evaluate(FIT)
                if bad:
                    problems.append(f'[{tag}] {bad}')
                if await page.evaluate(WIDE):
                    problems.append(f'[{tag}] sideways scroll')
                await snap(f'{tag}-level{lv}.jpg')
                if play:
                    for t in path:
                        await page.dispatch_event(f'.tm-tile[data-id="{t}"]', 'pointerdown')
                        await page.wait_for_timeout(90)
                    await page.wait_for_selector('.tm-done.win', timeout=8000)
                    await page.wait_for_timeout(900)
                    await snap(f'{tag}-complete-pending.jpg')
                    await page.wait_for_selector('.tm-gain', timeout=40000)
                    if '✓ Đã ghi nhận' not in await page.inner_text('.tm-done'):
                        problems.append(f'[{tag}] no "✓ Đã ghi nhận" on the card')
                    await page.wait_for_timeout(900)
                    await snap(f'{tag}-complete.jpg')
                    got = {}
                    mutate(db, token, lambda s: got.update(s['journey'].get('tile') or {}))
                    if got.get('lv') != lv or got.get('n') != 1 or (got.get('cur') or {}).get('b'):
                        problems.append(f'[{tag}] server tile after the win: {got}')
                    # a booster on the next level: checked on the page (free today), paid with the level's end
                    await page.click('.tm-sheet .tm-bar [data-tm="next"]')
                    await page.wait_for_selector('.tm-sheet .tm-tile', timeout=8000)
                    await page.wait_for_timeout(500)
                    await page.dispatch_event(f'.tm-tile[data-id="{tm.level(lv + 1)["solution"][0]}"]', 'pointerdown')
                    await page.wait_for_timeout(300)
                    await page.click('.tm-boost[data-k="undo"]')
                    await page.wait_for_timeout(700)
                    got = {}
                    mutate(db, token, lambda s: got.update(s['journey'].get('tile') or {}))
                    if (got.get('u') or {}).get('undo'):
                        problems.append(f'[{tag}] the undo booster reached the server before the end: {got}')
                    tag_free = await page.inner_text('.tm-boost[data-k="undo"] em')
                    if tag_free.strip() != '2':
                        problems.append(f'[{tag}] the undo booster shows {tag_free!r} free uses left, not 2')
                    await snap(f'{tag}-level{lv + 1}-undo.jpg')
                await ctx.close()
            await browser.close()
    report = dict(errors=errors, problems=problems, words=words, shots=sorted(p.name for p in OUT.glob('*.jpg')))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if errors or problems else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
