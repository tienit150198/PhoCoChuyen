"""🌳 Vườn ước nguyện + the 2.5D pagoda: a browser walk-through (dev tool, needs playwright + chromium, TEST_DATABASE_URL).

Runs the real app on a throwaway story-mode server, seeds one save (a named character) and a few dozen wishes of
other players on the trees, then for each screen size (phone 360×740 and 390×844 portrait, 844×390 landscape, desktop
1280×800): the Đời thường sheet, "Vào chùa" (the 2.5D courtyard), incense through the step bar, tapping a wish tree in
the courtyard (walks there, the tree opens), reading a ribbon (‹ › to the next, 🙏 cùng cầu, ⚑ báo cáo), writing and
hanging a wish (the ribbon flies onto the tree), the garden of all trees, "Của tôi", then the garden straight from the
Đời thường sheet. Checks: the server took the act, the wish is in the table under the right tree with the right colour,
nothing overflows the screen sideways, no two visible buttons overlap, no page error.

    python scripts/browser_wish_trees.py [out_dir] [--lang en]   (en: phone only, lists any Vietnamese left on screen)
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402
from browser_chua import mutate, read, seed  # noqa: E402

ARGS = [a for a in sys.argv[1:] if not a.startswith('--') and a != 'en']
OUT = Path(ARGS[0]) if ARGS else ROOT.parent / '_wish_shots'
EN = '--lang' in sys.argv and sys.argv[sys.argv.index('--lang') + 1] == 'en'
SIZES = [(390, 844, 'en-phone')] if EN else [(390, 844, 'phone'), (360, 740, 'small'), (844, 390, 'landscape'), (1280, 800, 'desktop')]
VIETNAMESE = """()=>{const out=[];for(const root of document.querySelectorAll('.wt-sheet[open],.cv-sheet[open]')){const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  for(let n=walk.nextNode();n;n=walk.nextNode()){const el=n.parentElement,t=n.textContent.trim();
    if(!t||el.closest('input,textarea,[data-no-translate]')||!el.getClientRects().length)continue;
    if(/[àáảãạăâèéẻẽẹêìíỉĩịòóỏõọôơùúủũụưỳýỷỹỵđ]/i.test(t))out.push(t);}}
  return [...new Set(out)];}"""
OTHERS = [
    ('binh_an', 'do', 'Mong cả xóm mình năm nay bình an, không ai đau ốm 🙏', 'Bà Sáu'),
    ('binh_an', 'vang', 'Cầu cho bố đi biển về an toàn.', ''),
    ('binh_an', 'xanh', 'Mong em trai thi đỗ, mẹ bớt lo.', 'Hoa'),
    ('gia_dao', 'hong', 'Mong ba mẹ đừng cãi nhau nữa, cả nhà ăn cơm chung mỗi tối.', 'Bé Tí'),
    ('gia_dao', 'do', 'Năm nay xây xong nhà cho mẹ ❤️', 'Minh'),
    ('suc_khoe', 'xanh', 'Ông nội mau khỏe để còn đi câu cá với con.', 'Tú'),
    ('hoc_hanh', 'vang', 'Đỗ đại học Bách Khoa!!! 📚', 'Lan Anh'),
    ('hoc_hanh', 'tim', 'Thi IELTS 7.0 lần này nha', ''),
    ('su_nghiep', 'do', 'Tiệm trà sữa đông khách, trả hết nợ trong năm.', 'Khoa'),
    ('tai_loc', 'vang', 'Đủ tiền đưa mẹ đi Đà Lạt.', ''),
    ('tinh_duyen', 'hong', 'Mong gặp được người thương mình thật lòng 💕', 'Ngọc'),
    ('uoc_mo', 'tim', 'Một ngày mở được tiệm sách nhỏ ven sông.', 'Vy'),
    ('tuong_nho', 'xanh', 'Bà ơi, con nhớ bà nhiều lắm. Con sống tốt rồi bà yên lòng nhé.', 'Huy'),
]
OVERLAP = """(sel)=>{const root=document.querySelector(sel);if(!root)return {wide:false,hits:[]};
  const vis=[...root.querySelectorAll('button,a,input,textarea')].filter(el=>{const r=el.getBoundingClientRect();if(!r.width||!r.height)return false;
    const s=getComputedStyle(el);if(s.visibility==='hidden'||s.opacity==='0')return false;if(el.closest('[hidden]'))return false;
    const cx=r.left+r.width/2,cy=r.top+r.height/2;const top=document.elementFromPoint(Math.min(innerWidth-1,Math.max(0,cx)),Math.min(innerHeight-1,Math.max(0,cy)));return top&&(el===top||el.contains(top));});
  const hits=[];for(let i=0;i<vis.length;i++)for(let j=i+1;j<vis.length;j++){const a=vis[i].getBoundingClientRect(),b=vis[j].getBoundingClientRect();
    if(vis[i].contains(vis[j])||vis[j].contains(vis[i]))continue;
    if(!vis[i].closest('.wt-cta')!==!vis[j].closest('.wt-cta'))continue;   // the sticky bar floats over the list on purpose
    const w=Math.min(a.right,b.right)-Math.max(a.left,b.left),h=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);if(w>3&&h>3)hits.push([vis[i].textContent.trim().slice(0,30)||vis[i].className,vis[j].textContent.trim().slice(0,30)||vis[j].className]);}
  return {wide:document.documentElement.scrollWidth>innerWidth+1||root.scrollWidth>root.clientWidth+1,hits};}"""


def plant(db):
    """Other players' wishes, written straight into the table (as command_commit would)."""
    from game import chua_wish as cw
    from game.storage import Store
    store = Store(db, story=True)
    with store.connect() as conn:
        for i in range(3):
            for k, (tree, color, text, name) in enumerate(OTHERS):
                conn.execute('INSERT INTO chua_wishes(key,sid,tree,color,text,raw,name,at,day,life_day,prayers) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                             (f'seed{i}{k:04d}'.ljust(24, '0'), f'seed-sid-{k % 5}', tree, color, text if not i else f'{text} ({i})', None, name,
                              time.time() - 3600 * (40 - i * 13 - k), cw.vn_day(time.time() - 86400), 3, (k * 3 + i) % 7))
    store.close_pool()


API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""


async def admin(page, db, problems):
    """The operator site: a wish hidden by three reports comes first; "Treo lại" puts it back on its tree."""
    from game.storage import Store
    out = await page.evaluate(API, ['/api/account/register', dict(username='wishadmin', password='matkhau-123', confirm='matkhau-123', display='Lan')])
    if out['status'] >= 400:
        problems.append(f'[admin] register: {out}')
        return
    store = Store(db, story=True)
    with store.connect() as conn:
        wid = conn.execute("SELECT id FROM chua_wishes WHERE tree='tinh_duyen' ORDER BY id LIMIT 1").fetchone()[0]
        for k in range(3):
            conn.execute("INSERT INTO reports(reporter,kind,target,reason,at) VALUES(?,'wish',?,?,?) ON CONFLICT DO NOTHING", (f'pid{k}', str(wid), ('rude', 'spam', 'private')[k], time.time()))
        conn.execute("UPDATE chua_wishes SET reports=3, status='hidden' WHERE id=?", (wid,))
    await page.goto(page.url.split('#')[0].rsplit('/', 1)[0] + '/admin.html#uoc-nguyen')
    await page.wait_for_selector('.gift-admin', timeout=15000)
    await page.wait_for_timeout(400)
    await page.screenshot(path=str(OUT / 'desktop-18-admin.png'))
    await page.locator(f'[data-act="wsShow"][data-id="{wid}"]').click()
    await page.wait_for_timeout(800)
    with store.connect() as conn:
        row = conn.execute('SELECT status, by_admin, reviewed_at FROM chua_wishes WHERE id=?', (wid,)).fetchone()
    store.close_pool()
    if row['status'] != 'live' or row['by_admin'] != 'wishadmin' or row['reviewed_at'] is None:
        problems.append(f'[admin] "Treo lại" did not put the wish back: {dict(row)}')
    await page.screenshot(path=str(OUT / 'desktop-19-admin-shown.png'))


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, problems, vietnamese = [], [], []
    os.environ['ADMIN_USERS'] = 'wishadmin'   # the operator site's "Ước nguyện" (desktop pass)
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            planted = False
            for w, h, name in SIZES:
                phone = w < 900
                ctx = await browser.new_context(viewport=dict(width=w, height=h), is_mobile=phone, has_touch=phone, device_scale_factor=2 if phone else 1, bypass_csp=True)
                await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0');localStorage.setItem('mnl.x3.week','blocked')}catch(e){}")
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                mutate(db, token, seed('en' if EN else 'vi', 'kem', 5, True))
                if not planted:
                    plant(db)
                    planted = True
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1200)
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                before = read(db, token)

                async def shot(tag, wait=500, sel=None):
                    await page.wait_for_timeout(wait)
                    await page.screenshot(path=str(OUT / f'{name}-{tag}.png'))
                    if EN:
                        left = [t for t in await page.evaluate(VIETNAMESE) if t not in ('Lan',)]
                        if left:
                            vietnamese.append(dict(screen=tag, text=left))
                    if sel:
                        res = await page.evaluate(OVERLAP, sel)
                        if res['wide']:
                            problems.append(f'[{name}] {tag}: overflows sideways')
                        for a, b in res['hits']:
                            problems.append(f'[{name}] {tag}: "{a}" overlaps "{b}"')

                async def tap(sel, force=False):
                    el = page.locator(sel).first
                    if phone:
                        await el.tap(force=force)
                    else:
                        await el.click(force=force)

                # Đời thường → the temple section
                await page.locator('[data-action="isoCareers"]:visible').first.click()
                await page.locator('#sheet [data-action="jrView"][data-view="life"]').first.click()
                await page.wait_for_selector('#sheet[open] .cg-trees', timeout=8000)
                await page.evaluate("document.querySelector('#sheet .cg-enter').scrollIntoView({block:'center'})")
                await shot('01-sheet')   # (the Đời thường sheet itself is not this feature's: its back button overlaps a card in landscape)
                await tap('#sheet .cg-enter[data-action="lfChuaVisit"]')
                await page.wait_for_selector('.cv-sheet[open] canvas', timeout=8000)
                await page.wait_for_function('__chua.state().trees>0', timeout=8000)
                await shot('02-courtyard', 1400, '.cv-sheet[open]')
                # a drag looks around, a step walks to the burner
                box = await page.locator('.cv-canvas').bounding_box()
                await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await page.mouse.down()
                await page.mouse.move(box['x'] + box['width'] / 2 + 140, box['y'] + box['height'] / 2 + 40, steps=8)
                await page.mouse.up()
                await shot('03-dragged', 600)
                await tap('.cv-path [data-cv="step"][data-id="huong"]')
                await page.wait_for_selector('.cv-panel:not([hidden]) [data-act="huong"]', timeout=8000)
                await shot('04-huong', 300, '.cv-sheet[open]')
                await tap('.cv-panel [data-act="huong"]')
                await page.wait_for_selector('.cv-panel .cv-result', timeout=8000)
                await shot('05-huong-done', 700, '.cv-sheet[open]')
                await tap('.cv-panel [data-cv="shut"]')
                # tap the Học hành tree in the courtyard: walk there, the tree opens
                await page.evaluate("__chua.look('tree:hoc_hanh')")   # as a drag would bring it into view
                await page.wait_for_timeout(300)
                xy = await page.evaluate("__chua.screen('tree:hoc_hanh')")
                st = await page.evaluate('__chua.state()')
                if not xy:
                    problems.append(f'[{name}] no hoc_hanh tree in the courtyard: {st}')
                else:
                    if phone:
                        await page.touchscreen.tap(xy[0], xy[1])
                    else:
                        await page.mouse.click(xy[0], xy[1])
                await page.wait_for_selector('.wt-sheet[open] .wt-stage', timeout=12000)
                await page.wait_for_selector('.wt-sheet[open] .wt-rib', timeout=8000)
                await shot('06-tree', 700, '.wt-sheet[open]')
                await page.evaluate("document.querySelector('.wt-sheet .wt-list')?.scrollIntoView({block:'start'})")
                await shot('07-tree-list', 300, '.wt-sheet[open]')
                await tap('.wt-sheet .wt-rib', True)   # the ribbons sway: never "stable"
                await page.wait_for_selector('.wt-read', timeout=5000)
                await shot('08-read', 400, '.wt-sheet[open]')
                await tap('.wt-read [data-wt="next"]')
                await tap('.wt-read [data-wt="pray"]')
                await page.wait_for_selector('.wt-read [data-wt="pray"][disabled]', timeout=5000)
                await tap('.wt-read [data-wt="report-ask"]')
                await shot('09-read-prayed-report', 400, '.wt-sheet[open]')
                await tap('.wt-read [data-wt="shut"]')
                # write and hang
                await tap('.wt-sheet [data-wt="write"]')
                await page.wait_for_selector('.wt-compose textarea', timeout=5000)
                text = f'Mong thi học kỳ này được điểm cao để mẹ vui ({name}) 🌟'
                await page.fill('.wt-compose textarea', text)
                await tap('.wt-compose [data-wt="color"][data-id="tim"]')
                await shot('10-compose', 300, '.wt-sheet[open]')
                await tap('.wt-compose [data-wt="hang"]')
                await page.wait_for_selector('.wt-rib.mine', timeout=8000)
                await page.wait_for_timeout(300)
                await shot('11-hung', 900, '.wt-sheet[open]')
                from game import chua_wish as cw
                from game.storage import Store
                store = Store(db, story=True)
                with store.connect() as conn:
                    row = conn.execute("SELECT tree,color,text,name FROM chua_wishes WHERE text=?", (text,)).fetchone()
                store.close_pool()
                if not row or (row['tree'], row['color'], row['name']) != ('hoc_hanh', 'tim', 'Lan'):
                    problems.append(f'[{name}] the hung wish is not in the table as written: {dict(row) if row else None}')
                # the whole garden, then mine
                await tap('.wt-sheet [data-wt="back"]')
                await page.wait_for_selector('.wt-sheet .wt-tile', timeout=8000)
                await shot('12-garden', 600, '.wt-sheet[open]')
                await tap('.wt-sheet [data-wt="mine"]')
                await page.wait_for_selector('.wt-sheet .wt-card.mine', timeout=8000)
                await shot('13-mine', 400, '.wt-sheet[open]')
                await tap('.wt-sheet [data-wt="close"]')
                await page.wait_for_function('!__chua.state().covered', timeout=5000)
                await shot('14-courtyard-after', 900, '.cv-sheet[open]')
                # khấn and the chant are still there (the hall's steps)
                await tap('.cv-path [data-cv="step"][data-id="khan"]')
                await page.wait_for_selector('.cv-panel [data-cv="who"]', timeout=8000)
                await shot('15-khan', 400, '.cv-sheet[open]')
                await tap('.cv-panel [data-cv="who"][data-id="cha_me"]')
                await tap('.cv-panel [data-cv="what"][data-id="may_man"]')
                await tap('.cv-panel [data-act="khan"]')
                await page.wait_for_selector('.cv-panel .cv-result', timeout=8000)
                await tap('.cv-panel [data-cv="shut"]')
                await tap('.cv-path [data-cv="here"]')
                await page.wait_for_selector('.cv-panel .cv-tiles', timeout=5000)
                await shot('16-quanh-day', 300, '.cv-sheet[open]')
                after = read(db, token)
                for a in ('huong', 'khan', 'nguyen'):
                    if a not in after['chua'].get('did', []):
                        problems.append(f'[{name}] {a} not done on the server: {after["chua"].get("did")}')
                if after['wallet'] != before['wallet']:
                    problems.append(f'[{name}] the wallet moved')
                if 'cards' in after['chua']:
                    problems.append(f'[{name}] a tree wish went into the save')
                await page.click('.cv-head [data-cv="close"]')
                await page.wait_for_timeout(300)
                # the garden straight from the Đời thường sheet
                if not await page.locator('#sheet[open] .cg-trees').count():
                    await page.locator('[data-action="isoCareers"]:visible').first.click()
                    await page.locator('#sheet [data-action="jrView"][data-view="life"]').first.click()
                await tap('#sheet .cg-trees')
                await page.wait_for_selector('.wt-sheet[open] .wt-tile', timeout=8000)
                await shot('17-garden-from-sheet', 600, '.wt-sheet[open]')
                await tap('.wt-sheet [data-wt="close"]')
                if name == 'desktop':
                    await admin(page, db, problems)
                print(name, 'did', after['chua'].get('did'), 'spirit', before['spirit'], '->', after['spirit'])
                await ctx.close()
            await browser.close()
    errs = [e for e in errors if 'favicon' not in e and '409 (Conflict)' not in e]
    for p in problems:
        print('PROBLEM', p)
    if EN:
        print('visible Vietnamese:', sorted({t for row in vietnamese for t in row['text']}) or 'none')
    print('errors:', errs or 'none')
    (OUT / 'report.json').write_text(json.dumps(dict(problems=problems, errors=errs), ensure_ascii=False, indent=2), encoding='utf-8')
    sys.exit(1 if problems or errs else 0)


if __name__ == '__main__':
    asyncio.run(main())
