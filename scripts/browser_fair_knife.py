"""🗡️ Phóng dao at the fair: a browser check (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server with the fair open today, seeds one save with 300 xu, then at
390x844 walks to anh Sáu's stall on the fairground and plays:
  1. a run of 5 xu: level 1 (the first knife by a real tap on the board, the rest timed into gaps), "Chơi tiếp",
     level 2, "Dừng": the wallet gains the prize the choice card promised;
  2. a run of 2 xu: level 1, "Chơi tiếp", then a knife aimed at a stuck one: everything is lost, the wallet shows it;
  3. runs of 2 xu cleared level after level until the "🔥 Màn sau x2" card shows (or 3 runs), then "Dừng";
checking the stage, the status bar, the choice card and the wallet against the server's after every step, in the
light and dark themes. At 320x640 and 430x932 it opens the stall and a level and checks nothing spills sideways.
Screenshots in out_dir. Exit 1 on any problem or console error.

    python scripts/browser_fair_knife.py [out_dir]
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_fair_knife_shots'

WALLET = "+(document.querySelector('.fh-sheet .fh-strip b')?.textContent||'').replace(/\\D/g,'')"
STATE = "globalThis.__fairKnife?.state()"
LADDER = (11, 12, 16, 21, 28, 39, 54, 80, 120, 190)

# In the page: the angles taken on the board now (the level's own knives and the ones thrown), and a wait for a moment
# when a knife thrown `ahead` ms from now (and for `span` ms after) sticks at least `gap + margin` from all of them.
JS_LIB = """
globalThis.__knT = {
  taken(){const s=__fairKnife.state(),b=s.run.board;return [...b.pre,...s.level.taps.map(t=>__fairKnife.lands(t))];},
  d(a,b){const x=Math.abs(a-b)%360;return x>180?360-x:x;},
  ok(t,gap){const tk=this.taken();return tk.every(x=>this.d(__fairKnife.lands(t),x)>=gap);},
  async gapAhead(ahead,span,gap){
    for(let i=0;i<2000;i++){
      const c=__fairKnife.clock();let good=c!==null;
      for(let dt=0;good&&dt<=span;dt+=10)good=this.ok(c+ahead+dt,gap);
      if(good)return c;
      await new Promise(r=>requestAnimationFrame(r));
    }
    return null;
  },
};
"""

# Throw the level's remaining knives, each into a gap (aim='safe'), or the next one at a stuck knife (aim='hit').
JS_THROW = """async ([aim,gap])=>{
  const s0=__fairKnife.state();if(!s0.level)return 'no level';
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const cv=document.querySelector('.fh-sheet .fh-kn-cv');
  const tap=()=>{const b=cv.getBoundingClientRect();cv.dispatchEvent(new PointerEvent('pointerdown',{clientX:b.left+b.width/2,clientY:b.top+b.height*.4,pointerId:3,pointerType:'touch',isPrimary:true,bubbles:true,cancelable:true,button:0,buttons:1}));};
  for(let n=0;n<20;n++){
    const s=__fairKnife.state();if(!s.level||s.level.over||s.level.taps.length>=s.level.need)return s.level?.over||'none';
    await wait(170);   // a knife in the air sticks first (min_tap)
    if(aim==='hit'){
      const tk=__knT.taken();
      for(let i=0;i<3000;i++){const c=__fairKnife.clock(),a=__fairKnife.lands(c+4);if(tk.some(x=>__knT.d(a,x)<3))break;await new Promise(r=>requestAnimationFrame(r));}
      tap();await wait(50);return __fairKnife.state().level?.over||'?';
    }
    if(await __knT.gapAhead(4,30,gap)===null)return 'no gap';
    tap();
  }
  return 'too many';
}"""


async def run(base, db, problems, errors):
    from playwright.async_api import async_playwright
    from browser_fair import seed
    async with async_playwright() as pw:
        browser = await getattr(pw, os.environ.get('MNL_BROWSER', 'chromium')).launch()
        for w, h in ((390, 844), (320, 640), (430, 932)):
            ctx = await browser.new_context(viewport=dict(width=w, height=h), has_touch=True)
            await ctx.add_init_script("try{localStorage.setItem('mnl.home','list')}catch(e){}")  # the list as home (the town is the default): the fair's row
            page = await ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
            seed(db, token, neighbours=False)
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1200)
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            tag = f'{w}x{h}'

            async def shot(name):
                await page.wait_for_timeout(300)
                await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

            async def poll(js, timeout=10):
                for _ in range(int(timeout * 10)):
                    if await page.evaluate(js):
                        return True
                    await page.wait_for_timeout(100)
                return False

            async def sideways(name):
                over = await page.evaluate("""()=>{const d=document.querySelector('.fh-sheet');const out=[];
                  for(const e of d.querySelectorAll('.fh-kn *, .fh-kn')){const b=e.getBoundingClientRect();if(b.width&&(b.right>innerWidth+1||b.left<-1))out.push(e.className||e.tagName);}
                  return {page:document.documentElement.scrollWidth>innerWidth,dlg:d.scrollWidth>d.clientWidth+1,out:out.slice(0,5)};}""")
                if over['page'] or over['dlg'] or over['out']:
                    problems.append(f'{tag}: {name}: spills sideways {over}')

            if not await page.locator('.jr-fair-row').count():
                await page.evaluate("document.querySelector('[data-action=\"home\"]')?.click()")
                await page.wait_for_selector('.jr-fair-row', timeout=10000)
            for _ in range(4):   # what's new and the like
                b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                if not await b.count():
                    break
                await b.first.click()
                await page.wait_for_timeout(400)
            await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close());document.querySelector('.jr-fair-row').click()")
            await page.wait_for_selector('.fh-sheet[open]', timeout=10000)
            await poll("globalThis.__fairWalk?.state().on")
            await page.wait_for_timeout(600)
            if await page.locator('.fh-sheet [data-fh="giftok"]').count():   # the fair's welcome gift
                await page.click('.fh-sheet [data-fh="giftok"]')
            if not await poll("__fairWalk.state().spots.includes('dt')"):
                problems.append(f'{tag}: no phóng dao stall on the fairground')
            if w == 390:
                await shot('0-ground')
            await page.evaluate("__fairWalk.go('dt')")                       # walk up to anh Sáu: his page opens
            if not await poll("!!document.querySelector('.fh-sheet .fh-kn')", 6):
                problems.append(f'{tag}: walking to the stall did not open it')
                await page.evaluate("document.querySelector('.fh-sheet [data-tab=\"dt\"]')?.click()")
                await page.wait_for_selector('.fh-sheet .fh-kn', timeout=5000)
            await page.evaluate(JS_LIB)
            await page.wait_for_timeout(500)
            await shot('1-stall')
            await sideways('stall')

            async def start(stake):
                before = await page.evaluate(WALLET)
                await page.click(f'.fh-sheet [data-fh="knstake"][data-v="{stake}"]')
                await page.click('.fh-sheet [data-fh="knstart"]')
                if not await poll(f"({STATE})?.run?.stage==='play'&&!!({STATE}).level", 8):
                    problems.append(f'{tag}: start {stake}: no level on the board')
                    return before
                await page.wait_for_timeout(300)
                if await page.evaluate(WALLET) != before - stake:
                    problems.append(f'{tag}: start {stake}: wallet {await page.evaluate(WALLET)}, want {before - stake}')
                return before

            async def clear(name, real_tap=False):
                st = await page.evaluate(STATE)
                lv = st['run']['lv']
                if real_tap:   # the first knife: a real finger on the board, in a wide gap
                    c = await page.evaluate("__knT.gapAhead(40,260,14)")
                    if c is None:
                        problems.append(f'{tag}: {name}: no gap for the real tap')
                    box = await page.locator('.fh-sheet .fh-kn-cv').bounding_box()
                    await page.touchscreen.tap(box['x'] + box['width'] * .3, box['y'] + box['height'] * .35)
                    await page.wait_for_timeout(250)
                    if len((await page.evaluate(STATE))['level']['taps']) != 1:
                        problems.append(f'{tag}: {name}: a tap on the board threw no knife')
                res = await page.evaluate(JS_THROW, ['safe', 14])
                if res != 'clear':
                    problems.append(f'{tag}: {name}: level {lv} ended {res!r}')
                ok = await poll(f"({STATE})?.run?.stage==='choice'&&!({STATE}).busy", 8)
                st = await page.evaluate(STATE)
                if not ok:
                    problems.append(f'{tag}: {name}: no choice after level {lv}: {st["run"] and st["run"].get("stage")}')
                return st['run']

            async def check_choice(r, stake, name):
                k = r['lv']
                base_ = (stake * LADDER[k - 1] + 5) // 10
                if r['prize'] < base_:
                    problems.append(f'{tag}: {name}: prize {r["prize"]} below the ladder {base_}')
                txt = await page.inner_text('.fh-sheet .fh-kn-choice')
                if f'Qua màn {k}!' not in txt or f'Chơi tiếp màn {k + 1}' not in txt:
                    problems.append(f'{tag}: {name}: choice card reads {txt!r}')
                if bool(r.get('nx')) != ('Màn sau x2' in txt):
                    problems.append(f'{tag}: {name}: x2 banner {"missing" if r.get("nx") else "shown without x2"}')
                if (await page.locator('.fh-sheet [data-fh="knstop"]:not([disabled])').count() != 1
                        or await page.locator('.fh-sheet [data-fh="knnext"]:not([disabled])').count() != 1):
                    problems.append(f'{tag}: {name}: Dừng / Chơi tiếp not both ready')

            async def nxt():
                await page.click('.fh-sheet [data-fh="knnext"]')
                if not await poll(f"({STATE})?.run?.stage==='play'&&!!({STATE}).level&&!({STATE}).busy", 8):
                    problems.append(f'{tag}: Chơi tiếp did not start the next level')

            async def stop(before, stake, r, name):
                await page.click('.fh-sheet [data-fh="knstop"]')
                if not await poll(f"({STATE})?.run?.stage==='done'&&!({STATE}).busy", 8):
                    problems.append(f'{tag}: {name}: Dừng did not pay')
                await page.wait_for_timeout(400)
                want = before - stake + r['prize']
                if await page.evaluate(WALLET) != want:
                    problems.append(f'{tag}: {name}: wallet {await page.evaluate(WALLET)} after Dừng, want {want}')
                txt = await page.inner_text('.fh-sheet .fh-kn .fh-result')
                if 'Nhận' not in txt or str(r['prize']) not in txt:
                    problems.append(f'{tag}: {name}: result reads {txt!r}')
                print(f'{tag} {name}: đặt {stake}, qua {r["lv"]} màn, nhận {r["prize"]}')

            if w != 390:   # the other widths: the stall and a level on the board, then out
                before = await start(2)
                await page.wait_for_timeout(600)
                await shot('2-level')
                await sideways('level')
                r = await clear('w1')
                await check_choice(r, 2, 'w1')
                await shot('3-choice')
                await sideways('choice')
                await stop(before, 2, r, 'w1')
                await ctx.close()
                continue

            # 1. 5 xu: level 1, play on, level 2, stop
            before = await start(5)
            await page.wait_for_timeout(700)
            await shot('2-level1')
            bar = await page.inner_text('.fh-sheet .fh-kn-bar')
            if 'Màn 1/10' not in bar or 'Qua màn được' not in bar:
                problems.append(f'{tag}: status bar reads {bar!r}')
            r = await clear('a1', real_tap=True)
            await check_choice(r, 5, 'a1')
            await shot('3-choice')
            await page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot('3-choice-dem')
            await page.evaluate("document.documentElement.dataset.theme='kem'")
            await nxt()
            await page.wait_for_timeout(500)
            st = await page.evaluate(STATE)
            if st['run']['lv'] != 2 or st['run'].get('prize') != r['prize']:
                problems.append(f'{tag}: level 2 should hold the level 1 prize: {st["run"]}')
            await page.evaluate("document.documentElement.dataset.theme='dem'")
            await shot('4-level2-dem')
            await page.evaluate("document.documentElement.dataset.theme='kem'")
            r = await clear('a2')
            await check_choice(r, 5, 'a2')
            await stop(before, 5, r, 'a')
            await shot('5-paid')

            # 2. 2 xu: level 1, play on, hit a knife: all lost
            before = await start(2)
            r = await clear('b1')
            await nxt()
            res = await page.evaluate(JS_THROW, ['hit', 14])
            if res != 'lost':
                problems.append(f'{tag}: aiming at a knife ended {res!r}')
            await page.wait_for_timeout(300)
            await shot('6-hit')
            if not await poll(f"({STATE})?.run?.stage==='lost'&&!({STATE}).busy&&!!document.querySelector('.fh-sheet .fh-kn .fh-result.bad')", 8):
                problems.append(f'{tag}: no lost result after the hit')
            await page.wait_for_timeout(400)
            if await page.evaluate(WALLET) != before - 2:
                problems.append(f'{tag}: wallet {await page.evaluate(WALLET)} after losing, want {before - 2}')
            txt = await page.inner_text('.fh-sheet .fh-kn .fh-result')
            if 'Dao chạm dao' not in txt or 'Mất' not in txt:
                problems.append(f'{tag}: lost result reads {txt!r}')
            await shot('7-lost')
            print(f'{tag} b: đặt 2, thua ở màn 2, mất {r["prize"]} thưởng')

            # 3. look for the 🔥 x2 card: 2 xu runs, level after level
            seen = False
            for k in range(3):
                before = await start(2)
                r = await clear(f'c{k}-1')
                while not r.get('nx') and r['lv'] < 6:
                    await nxt()
                    r = await clear(f'c{k}-{r["lv"] + 1}')
                if r.get('nx'):
                    seen = True
                    await check_choice(r, 2, f'c{k}')
                    await shot('8-x2')
                    await page.evaluate("document.documentElement.dataset.theme='dem'")
                    await shot('8-x2-dem')
                    await page.evaluate("document.documentElement.dataset.theme='kem'")
                    await nxt()
                    await page.wait_for_timeout(400)
                    if '🔥 x2' not in await page.inner_text('.fh-sheet .fh-kn-bar'):
                        problems.append(f'{tag}: the x2 level has no 🔥 x2 in its bar')
                    await shot('9-x2-level')
                    r = await clear(f'c{k}-x2')
                await stop(before, 2, r, f'c{k}')
                if seen:
                    break
            if not seen:
                print(f'{tag}: no 🔥 x2 drawn in 3 runs (a 1-in-4 draw): not a failure')
            await page.evaluate("document.querySelector('.fh-sheet .fh-kn details.fh-how')?.setAttribute('open','')")
            await shot('10-ladder')
            await page.click('.fh-sheet [data-fh="tab"][data-tab="home"]')
            await page.wait_for_timeout(500)
            await page.evaluate("document.querySelector('.fh-sheet .fh-wlist')?.setAttribute('open','')")
            await shot('11-home')
            await ctx.close()
        await browser.close()


def main():
    from browser_fair import vn_today
    from browser_housing import server
    OUT.mkdir(parents=True, exist_ok=True)
    problems, errors = [], []
    os.environ['MNL_FAIR_START'] = vn_today()
    with server() as (base, db):
        asyncio.run(run(base, db, problems, errors))
    for p in problems + [f'console: {e}' for e in errors]:
        print('✗', p)
    if problems or errors:
        sys.exit(1)
    print('ok:', OUT)


if __name__ == '__main__':
    main()
