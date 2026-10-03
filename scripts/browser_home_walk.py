"""🚶 Ở nhà + 🧊 tủ lạnh: a browser smoke check (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (scripts/browser_gift.py's server(), like production) and seeds one
save straight in its database: a hungry character (no bụng 40) who owns the old tập thể with a fridge in the kitchen.
On a phone (touch) at 390x844, then 320 and 430 wide, in the light theme and "Phố đêm":
  1. Nhà của bạn → 🚪 Vào nhà: the character stands in the room; a tap on the floor walks them there;
  2. the kitchen: a tap on the fridge walks up to it and opens it; 🛒 Cất tủ a hộp cơm (wallet −5, 1/10), 🍽️ Ăn it
     (no bụng +40, a line over the character), 🍽️ Mua ăn liền a bánh bao; with an empty wallet the buttons are
     disabled with the reason; a page talking to a server from before (no `fridge` in the state): the fridge only
     says a line;
  3. the dorm: the shared fridge's card under the bunk opens your shelf (4 things);
  4. a rented room with its own fridge.
Every screen: no sideways scroll, the fridge's buttons at least 44 px tall, nothing over the controls. Screenshots to
the out dir; exit 1 on a console error or a failed step.

    python scripts/browser_home_walk.py [out_dir]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_deco import mutate, tz_for  # noqa: E402
from browser_gift import server  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_home_walk_shots'
STATE = "fetch('/api/state').then(r=>r.json()).then(d=>d.state)"
FITS = """()=>{const d=document.querySelector('.dc-sheet[open]'),wide=document.scrollingElement.scrollWidth>innerWidth+1;
  const inner=d?[...d.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&(r.right>innerWidth+1||r.left<-1)&&!e.closest('.dc-strip,.rn-rooms,.dc-rooms,svg.dc-room')}).map(e=>e.tagName.toLowerCase()+'.'+(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)+'@'+(e.parentElement?.className?.baseVal??e.parentElement?.className)).slice(0,5):[];
  const small=[...document.querySelectorAll('.hw-fridge button,.hw-fridge-door button')].filter(b=>b.getBoundingClientRect().height<44).map(b=>b.textContent.trim()).slice(0,5);
  return {wide,inner,small};}"""


def put(s, k, room, x, y, on=None):
    from game import deco as dc
    q = dict(r=room, x=x, y=y)
    if on:
        q['on'] = on
    return dc.apply(s, 'jr_deco_buy', dict(item=k, confirm=True, put=q))['uid']


def hungry(s, full=40):
    from game import needs as nd
    n = nd.ensure(s)
    n['full'], n['wake'] = full, 60


def seed_home(s):
    from game import housing as hs
    from game import journey as jr
    from game import whats_new as wn
    j = s['journey']
    s['name'] = 'Lan'
    s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
    s['settings'].update(tutorialDone=True)
    j.update(gender='female', intro=True, life_day=6, wallet=4000)
    hs.apply(s, 'jr_home_buy', {'kind': 'tap_the', 'down': 1800, 'confirm': True})
    put(s, 'tu_lanh', 'kitchen', 80, 20)
    put(s, 'ban_an', 'kitchen', 0, 40)
    put(s, 'noi_com', 'kitchen', 0, 0, on='#counter')
    put(s, 'sofa', 'living', 0, 30)
    put(s, 'tv', 'living', 0, 0)
    put(s, 'giuong', 'bed', 0, 20)
    put(s, 'tu_quan_ao', 'bed', 80, 0)
    j['wallet'] = 120
    jr._wallet(j, 0, 'salary', 'Lương')
    hungry(s)


def move(kind):
    def fn(s):
        from game import housing as hs
        j = s['journey']
        h = hs.get(s)
        if h and h['own']:
            hs.apply(s, 'jr_home_sell', {'confirm': True, 'value': hs.value_of(h['own'], j['life_day'])})
        hs.apply(s, 'jr_home_rent', {'kind': kind, 'confirm': True})
        j['wallet'] = max(j['wallet'], 400)
        if kind == 'tro_moi':
            from game import deco as dc
            bag = [it['id'] for it in s['journey']['reno']['items'] if it['k'] == 'tu_lanh']
            dc.apply(s, 'jr_deco_put', dict(uid=bag[0], r='tro', x=100, y=40, f=0))
        hungry(s)
    return fn


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, failed, passed = [], [], [0]
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for w in (390, 320, 430):
                tag = f'{w}'
                ctx = await browser.new_context(viewport=dict(width=w, height=844), timezone_id=tz_for(10), has_touch=True, is_mobile=True,
                                                device_scale_factor=2, service_workers='block', locale='vi-VN')
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','9.9.9');localStorage.setItem('mnl.decoTip2','1');localStorage.setItem('mnl.tut.done','1')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')

                def expect(ok, what):
                    passed[0] += bool(ok)
                    if not ok:
                        failed.append(f'{tag}: {what}')
                        print('  ✗', what)
                    return ok

                async def popups():
                    for _ in range(4):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible, button:has-text("Đã hiểu"):visible, button:has-text("Tuyệt!"):visible, button:has-text("Biết rồi"):visible')
                        if not await b.count():
                            break
                        try:
                            await b.first.click(timeout=3000)
                        except Exception:
                            await b.first.evaluate('e=>e.click()')
                        await page.wait_for_timeout(400)

                async def reload():
                    await page.reload()
                    await page.wait_for_selector('#app:not([hidden])', timeout=60000)
                    await page.wait_for_timeout(1500)
                    await popups()
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")

                async def shot(name):
                    await page.wait_for_timeout(450)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))
                    for th in ('dem',) if w == 390 else ():
                        await page.evaluate(f"document.documentElement.dataset.theme='{th}'")
                        await page.wait_for_timeout(250)
                        await page.screenshot(path=str(OUT / f'{tag}-{name}-dark.png'))
                        await page.evaluate("document.documentElement.dataset.theme='kem'")

                async def fits(what):
                    f = await page.evaluate(FITS)
                    expect(not f['wide'], f'{what}: the page scrolls sideways')
                    expect(not f['inner'], f'{what}: something sticks out of the sheet {f["inner"]}')
                    expect(not f['small'], f'{what}: buttons under 44 px {f["small"]}')

                async def click(sel):
                    await popups()
                    try:
                        await page.click(sel, timeout=8000)
                    except Exception:   # a popup that came late (the x3 week, new titles)
                        await popups()
                        await page.click(sel, timeout=8000)

                async def see(sel):
                    await popups()
                    await page.locator(sel).scroll_into_view_if_needed(timeout=8000)

                async def open_inside():
                    await popups()
                    try:
                        await page.wait_for_selector('.jr-house-row', timeout=10000)
                    except Exception:
                        await page.screenshot(path=str(OUT / f'{tag}-FAIL-house.png'))
                        raise
                    await click('.jr-house-row')
                    await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                    await popups()
                    await click('.hs-sheet [data-hs="inside"]:not([data-mode])')
                    await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)
                    await page.wait_for_timeout(300)

                async def room(rid):
                    await click(f'.dc-sheet [data-dc="room"][data-room="{rid}"]')
                    await page.wait_for_selector(f'.dc-sheet svg.dc-room[data-room="{rid}"]', timeout=5000)
                    await see('.dc-sheet svg.dc-room')
                    await page.wait_for_timeout(300)

                async def walked():
                    for _ in range(30):
                        st = await page.evaluate('__homeWalk.state()')
                        if not st['to']:
                            return st
                        await page.wait_for_timeout(120)
                    return await page.evaluate('__homeWalk.state()')

                async def tap_piece(k):
                    uid = await page.evaluate(f"""document.querySelector('.dc-sheet svg.dc-room g[data-k="{k}"]')?.dataset.uid""")
                    if not expect(uid, f'no {k} in the room'):
                        return None
                    xy = await page.evaluate(f'__homeWalk.screen({uid!r})')
                    await page.touchscreen.tap(xy[0], xy[1])
                    return await walked()

                async def fridge_btn(op, item):
                    await popups()   # e.g. new titles after the first purchase
                    return page.locator(f'.hw-fridge [data-dc="{op}"][data-item="{item}"]')

                # ---- 1. own home: walk in, walk
                mutate(db, token, seed_home)
                await reload()
                await open_inside()
                expect(await page.locator('.dc-sheet svg.dc-room .hw-me').count() == 1, 'the character stands in the room')
                hint = await page.inner_text('.dc-sheet .dc-hint')
                expect('Chạm sàn để đi' in hint, f'the hint says how to walk ({hint!r})')
                await room('living')
                before = (await page.evaluate('__homeWalk.state()'))['me']
                r = await page.evaluate("(()=>{const r=document.querySelector('.dc-sheet svg.dc-room').getBoundingClientRect();return [r.left,r.top,r.width,r.height];})()")
                await page.touchscreen.tap(r[0] + r[2] * .7, r[1] + r[3] * .78)
                await page.wait_for_timeout(200)
                mid = await page.evaluate('__homeWalk.state()')
                expect(mid['to'], 'a tap on the floor starts a walk')
                after = (await walked())['me']
                expect(abs(after[0] - before[0]) > 20, f'the character walked ({before} → {after})')
                expect(not await page.locator('.dc-sheet .dc-room.edit').count(), 'a tap walks, it does not start decorating')
                await shot('01-living-walk')
                st = await tap_piece('tv')
                say = st and st['say']
                expect(say, 'the TV says a line')
                await shot('02-tv-line')
                await fits('living')

                # ---- 2. the kitchen and the fridge
                await room('kitchen')
                st = await tap_piece('tu_lanh')
                await page.wait_for_selector('.hw-fridge', timeout=4000)
                await see('.hw-fridge')
                await shot('03-fridge-open')
                await fits('fridge')
                s0 = await page.evaluate(STATE)
                await (await fridge_btn('hwBuy', 'com_hop')).click()
                await page.wait_for_selector('.hw-fridge .hw-note.good', timeout=5000)
                s1 = await page.evaluate(STATE)
                expect(s1['journey']['wallet'] == s0['journey']['wallet'] - 5, 'storing a hộp cơm costs 5 xu')
                expect('1/10' in await page.inner_text('.hw-fridge .hw-cap'), 'the fridge shows 1/10')
                expect(await page.locator('.hw-fridge .hw-in li').count() == 1, 'the hộp cơm is in the fridge')
                await (await fridge_btn('hwEat', 'com_hop')).click()
                await page.wait_for_timeout(900)
                s2 = await page.evaluate(STATE)
                expect(s2['journey']['deco']['fridge']['full'] == s1['journey']['deco']['fridge']['full'] + 40, f'eating it: no bụng +40 ({s1["journey"]["deco"]["fridge"]["full"]} → {s2["journey"]["deco"]["fridge"]["full"]})')
                expect(s2['journey']['wallet'] == s1['journey']['wallet'], 'eating from the fridge costs nothing more')
                expect(s2['journey']['deco']['fridge']['used'] == 0, 'the fridge is empty again')
                note = await page.inner_text('.hw-fridge .hw-note')
                expect('No bụng 80' in note, f'the fridge says what happened ({note!r})')
                await see('.dc-sheet svg.dc-room')
                await shot('04-after-eat')
                await see('.hw-fridge')
                for k in ('banh_bao', 'flan'):
                    await (await fridge_btn('hwBuy', k)).click()
                    await page.wait_for_timeout(600)
                await (await fridge_btn('hwEat', 'banh_bao')).click()
                await page.wait_for_timeout(900)
                s3 = await page.evaluate(STATE)
                expect(s3['journey']['wallet'] == s2['journey']['wallet'] - 5 and s3['journey']['deco']['fridge']['full'] == 100,
                       f'store two, eat one: −5 xu, full ({s3["journey"]["wallet"]}, {s3["journey"]["deco"]["fridge"]["full"]})')
                dis = await (await fridge_btn('hwEat', 'flan')).is_disabled()
                expect(dis, 'full: eating is disabled')
                why = await page.inner_text('.hw-fridge .hw-in li:has([data-item="flan"]) em')
                expect('Bụng no rồi' in why, f'with the reason ({why!r})')
                await shot('05-full')
                if w == 390:
                    # an empty wallet: storing is disabled with the reason
                    def poor(s):
                        s['journey']['wallet'] = 1
                        hungry(s)
                    mutate(db, token, poor)
                    await reload()
                    await open_inside()
                    await room('kitchen')
                    await tap_piece('tu_lanh')
                    await page.wait_for_selector('.hw-fridge', timeout=4000)
                    expect(await (await fridge_btn('hwBuy', 'com_hop')).is_disabled(), 'no money: storing is disabled')
                    why = await page.inner_text('.hw-fridge .hw-buy[data-item="com_hop"] em')
                    expect('Chưa đủ xu' in why, f'with the reason ({why!r})')
                    await see('.hw-fridge')
                    await shot('06-poor')
                # ---- 3. the dorm: the shared fridge
                mutate(db, token, move('ky_tuc_xa'))
                await reload()
                await page.wait_for_selector('.jr-house-row', timeout=10000)
                await click('.jr-house-row')
                await page.wait_for_selector('.hs-sheet[open] .hs-place', timeout=10000)
                btn = await page.inner_text('.hs-sheet [data-hs="inside"]:not([data-mode])')
                expect('Về góc giường' in btn, f'the dorm button says "Về góc giường" ({btn!r})')
                await click('.hs-sheet [data-hs="inside"]:not([data-mode])')
                await page.wait_for_selector('.dc-sheet[open] svg.dc-room', timeout=10000)
                await page.wait_for_timeout(300)
                expect(await page.locator('.dc-sheet svg.dc-room .hw-me').count() == 1, 'the character is in the bunk corner')
                await shot('07-dorm')
                await click('.hw-fridge-door [data-dc="hwOpen"]')
                await page.wait_for_selector('.hw-fridge', timeout=4000)
                expect('1/4' in await page.inner_text('.hw-fridge .hw-cap'), 'your shelf holds 4, the flan came along')
                for _ in range(3):
                    await (await fridge_btn('hwBuy', 'sua')).click()
                    await page.wait_for_timeout(500)
                expect(await (await fridge_btn('hwBuy', 'flan')).is_disabled(), 'the shelf is full')
                await see('.hw-fridge')
                await shot('08-dorm-shelf')
                await fits('dorm fridge')

                # ---- 4. a rented room with its own fridge
                mutate(db, token, move('tro_moi'))
                await reload()
                await open_inside()
                head = await page.inner_text('.dc-sheet .eyebrow')
                expect('TRONG PHÒNG' in head, f'the rented room is walked in ({head!r})')
                st = await tap_piece('tu_lanh')
                await page.wait_for_selector('.hw-fridge', timeout=4000)
                expect('4/10' in await page.inner_text('.hw-fridge .hw-cap'), 'the flan and the milk came along from the dorm (4/10)')
                await (await fridge_btn('hwEat', 'sua')).click()
                await page.wait_for_timeout(900)
                expect('3/10' in await page.inner_text('.hw-fridge .hw-cap'), 'one drunk')
                await see('.dc-sheet svg.dc-room')
                await shot('09-tro-fridge')
                await fits('rented room')
                if w == 390:
                    # a page talking to a server from before (no `fridge` in the state): the fridge only says a line
                    await page.evaluate("localStorage.setItem('mnl.deltacheck','1')")   # dev hook: the page's api as __mnlApi
                    await reload()
                    await open_inside()
                    await page.evaluate("""(()=>{const a=globalThis.__mnlApi,s=a.state,d={...s.journey.deco};delete d.fridge;
                        a.state={...s,journey:{...s.journey,deco:d}};})()""")
                    st = await tap_piece('tu_lanh')
                    expect(st and 'mát rượi' in st['say'] and not await page.locator('.hw-fridge').count(), f'an older server: a line only ({st})')
                    await shot('10-older-server')
                    await page.evaluate("localStorage.removeItem('mnl.deltacheck')")
                await ctx.close()
            await browser.close()
    for e in errors:
        print('console:', e)
    for f in failed:
        print('FAILED:', f)
    print(f'{passed[0]} checks passed, {len(failed)} failed; shots in', OUT)
    sys.exit(1 if errors or failed else 0)


if __name__ == '__main__':
    asyncio.run(main())
