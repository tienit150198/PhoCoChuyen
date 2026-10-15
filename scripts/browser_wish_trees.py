"""🌳 Vườn ước nguyện + the 2.5D pagoda: a browser walk-through (dev tool, needs playwright + chromium, TEST_DATABASE_URL).

Runs the real app on a throwaway story-mode server, seeds one save (a named character) and a few dozen wishes of
other players on the trees, then for each screen size (phone 360×740 and 390×844 portrait, 844×390 landscape, desktop
1280×800): the Đời thường sheet, "Vào chùa" (the 2.5D courtyard), incense through the step bar, tapping a wish tree in
the courtyard (walks there, the tree opens), reading a ribbon (‹ › to the next, 🙏 cùng cầu, ⚑ báo cáo), writing and
hanging a wish (the ribbon flies onto the tree), the garden of all trees, "Của tôi", then the garden straight from the
Đời thường sheet. Checks: the server took the act, the wish is in the table under the right tree with the right colour,
nothing overflows the screen sideways, no two visible buttons overlap, no page error.
📜 Old shared lời chúc (owner 15/10: "đưa vào 1 cái đi, sử dụng chung mà"): another player's old cards (shared, private,
shared then un-shared) and two of the player's own; the Sức khỏe tree shows the shared ones only (slips on the tree, the
"Lời chúc cũ" list), 🙏 on one is in chua_card_prayers, "Của tôi" lists the player's own with their switch ("Thôi chia
sẻ" takes it off the board), "Quanh đây" has no "Bảng lời chúc cũ" any more; the operator site hides an old card.
The courtyard's tree name boards (owner 15/10: cut off at the left edge of a narrow phone): all nine on screen at the
first look, each wholly visible, none on another board, the grove's sign or a badge (`boards`).

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
SIZES = [(390, 844, 'en-phone')] if EN else [(390, 844, 'phone'), (360, 740, 'small'), (375, 667, 'se'), (412, 915, 'tall'), (844, 390, 'landscape'), (1280, 800, 'desktop')]
if os.environ.get('WISH_SIZES'):   # e.g. WISH_SIZES=small,landscape
    SIZES = [s for s in SIZES if s[2] in os.environ['WISH_SIZES'].split(',')]
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
# 📜 another player's old cards: (recipient, blessing, name, message, shared); REVOKED is shared then un-shared
SHOWN = 'Mong mẹ mau hết ho để Tết về quê.'
PRIVATE = 'BÍ MẬT riêng tư'
REVOKED = 'THU HỒI rồi'
OLD_CARDS = [('ca_nha', 'khoe', 'Mẹ', SHOWN, True), ('ban', 'khoe', 'Tú', 'Tú ơi mau khỏe đi đá bóng nha.', True),
             ('ong_ba', 'yen_nghi', '', 'Con nhớ ông bà nhiều lắm.', True), ('pho', 'thuong', '', '', True),
             ('ca_nha', 'khoe', 'Bố', PRIVATE, False), ('ca_nha', 'khoe', 'Chị', REVOKED, True)]
MINE = 'Thẻ cũ của Lan, đang chia sẻ.'

OVERLAP = """(sel)=>{const root=document.querySelector(sel);if(!root)return {wide:false,hits:[]};
  const vis=[...root.querySelectorAll('button,a,input,textarea')].filter(el=>{const r=el.getBoundingClientRect();if(!r.width||!r.height)return false;
    const s=getComputedStyle(el);if(s.visibility==='hidden'||s.opacity==='0')return false;if(el.closest('[hidden]'))return false;
    const cx=r.left+r.width/2,cy=r.top+r.height/2;const top=document.elementFromPoint(Math.min(innerWidth-1,Math.max(0,cx)),Math.min(innerHeight-1,Math.max(0,cy)));return top&&(el===top||el.contains(top));});
  // what shows of an element: its box cut by every scrolling ancestor (a card half scrolled out of a list is only half there)
  const shown=el=>{let r=el.getBoundingClientRect(),l=r.left,t=r.top,rr=r.right,bb=r.bottom;
    for(let p=el.parentElement;p&&p!==document.body;p=p.parentElement){const s=getComputedStyle(p);if(s.overflowX==='visible'&&s.overflowY==='visible')continue;
      const q=p.getBoundingClientRect();l=Math.max(l,q.left);t=Math.max(t,q.top);rr=Math.min(rr,q.right);bb=Math.min(bb,q.bottom);}
    return {left:l,top:t,right:rr,bottom:bb};};
  const hits=[];for(let i=0;i<vis.length;i++)for(let j=i+1;j<vis.length;j++){const a=shown(vis[i]),b=shown(vis[j]);
    if(vis[i].contains(vis[j])||vis[j].contains(vis[i]))continue;
    if(!vis[i].closest('.wt-cta')!==!vis[j].closest('.wt-cta'))continue;   // the sticky bar floats over the list on purpose
    const w=Math.min(a.right,b.right)-Math.max(a.left,b.left),h=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);if(w>3&&h>3)hits.push([vis[i].textContent.trim().slice(0,30)||vis[i].className,vis[j].textContent.trim().slice(0,30)||vis[j].className]);}
  return {wide:document.documentElement.scrollWidth>innerWidth+1||root.scrollWidth>root.clientWidth+1,hits};}"""


async def boards(page, name, tag, problems, want=None):
    """The courtyard's tree name boards (owner 15/10: cut off at the left edge of a narrow phone): each wholly inside the
    canvas and not hidden under the step bar, none on another board, the grove's sign, Nhà trai's sign or a badge.
    `want`: how many boards must be on screen (all nine at the first look)."""
    await page.wait_for_timeout(250)
    got = await page.evaluate('__chua.labels()')
    cv, rows = got['canvas'], got['boards']
    bar = await page.evaluate("(()=>{const r=document.querySelector('.cv-sheet[open] .cv-path')?.getBoundingClientRect();return r?r.top:1e9})()")
    if want is not None and len(rows) < want:
        problems.append(f'[{name}] {tag}: only {len(rows)}/{want} tree boards on screen: {[r["tree"] for r in rows]}')
    for r in rows + ([dict(got['sign'], tree='grove sign')] if got.get('sign') else []):
        if r['x'] < cv['x'] - .5 or r['y'] < cv['y'] - .5 or r['x'] + r['w'] > cv['x'] + cv['w'] + .5 or r['y'] + r['h'] > min(cv['y'] + cv['h'], bar) + .5:
            problems.append(f'[{name}] {tag}: the {r["tree"]} board is cut off ({round(r["x"])},{round(r["y"])} {round(r["w"])}×{round(r["h"])})')
    hit = lambda a, b: min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x']) > 1 and min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y']) > 1
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if hit(a, b):
                problems.append(f'[{name}] {tag}: the {a["tree"]} board overlaps the {b["tree"]} board')
        for f in got['fixed']:
            if hit(a, f):
                problems.append(f'[{name}] {tag}: the {a["tree"]} board overlaps the {f["what"]}')
    return rows


def plant_cards(db):
    """Another player's old temple cards, made the way the old board made them (jr_chua_do with `public`)."""
    from game import chua_board
    from game.storage import Store
    from tests.test_chua import story
    store = Store(db, story=True)
    token, _, _ = store.session()
    with store.connect() as conn:
        conn.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(story()), store.key(token)))
    rev = 0
    for i, (who, what, name, message, shared) in enumerate(OLD_CARDS):
        out = store.command(token, f'old-card-{i:04d}', rev, None, 'jr_chua_do',
                            dict(act='nguyen', recipient=who, blessing=what, name=name, message=message, public=shared))
        rev = out['revision']
        if message == REVOKED:
            chua_board.set_visibility(store, token, dict(id=out['state']['chua']['cards'][-1]['id'], public=False))
    store.close_pool()


def own_cards(db, token):
    """Two old cards of the player: one shared (it hangs on Tài lộc), one private."""
    from game.storage import Store
    store = Store(db, story=True)
    rev = store.read(token)[1]
    for i, shared in enumerate((True, False)):
        rev = store.command(token, f'own-card-{i:04d}', rev, None, 'jr_chua_do', dict(act='nguyen', recipient='ca_nha', blessing='may_man',
                                                                                     message=MINE if shared else 'Thẻ riêng của Lan.', public=shared))['revision']
    store.close_pool()


def shared_of(db, token):
    from game.storage import Store
    store = Store(db, story=True)
    with store.connect() as conn:
        n = conn.execute('SELECT count(*) FROM chua_public_cards WHERE sid=?', (store.key(token),)).fetchone()[0]
        prayed = conn.execute('SELECT count(*) FROM chua_card_prayers WHERE by_sid=?', (store.key(token),)).fetchone()[0]
    store.close_pool()
    return n, prayed


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
    # 📜 an old shared card: "Gỡ" takes it off the garden for good (chua_card_marks), the card itself stays
    card = page.locator('[data-act="wsHide"][data-card]').first
    if not await card.count():
        problems.append('[admin] no old shared card in "Ước nguyện"')
        return
    pos = int(await card.get_attribute('data-card'))
    page.once('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await card.scroll_into_view_if_needed()
    await page.screenshot(path=str(OUT / 'desktop-20-admin-cards.png'))
    await card.click()
    await page.wait_for_timeout(800)
    store = Store(db, story=True)
    with store.connect() as conn:
        row = conn.execute('SELECT m.status, m.by_admin FROM chua_public_cards p JOIN chua_card_marks m ON m.sid=p.sid AND m.card_id=p.card_id '
                           'WHERE p.position=?', (pos,)).fetchone()
    store.close_pool()
    if not row or (row['status'], row['by_admin']) != ('removed', 'wishadmin'):
        problems.append(f'[admin] "Gỡ" did not take the old card off: {dict(row) if row else None}')


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
                own_cards(db, token)
                if not planted:
                    plant(db)
                    plant_cards(db)
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
                await boards(page, name, '02-courtyard', problems, 9)
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
                # 📜 the old shared lời chúc hang on the tree of their theme, for everyone; private / un-shared ones never
                if not EN and 'lời chúc cũ' not in await page.inner_text('.wt-sheet .wt-body'):
                    problems.append(f'[{name}] the garden does not count the old shared cards')
                await tap('.wt-sheet [data-wt="tree"][data-id="suc_khoe"]')
                await page.wait_for_selector('.wt-sheet .wt-card.wt-old', timeout=8000)
                await page.wait_for_selector('.wt-sheet .wt-rib.wt-old', timeout=8000)
                await shot('12b-tree-old', 600, '.wt-sheet[open]')
                body = await page.inner_text('.wt-sheet .wt-body')
                if SHOWN not in body:
                    problems.append(f'[{name}] a shared old card is not on Cây Sức khỏe')
                for t in (PRIVATE, REVOKED):
                    if t in body:
                        problems.append(f'[{name}] "{t}" shows in the garden (not shared)')
                await page.evaluate("document.querySelector('.wt-sheet .wt-old-h')?.scrollIntoView({block:'start'})")
                await shot('12c-tree-old-list', 300, '.wt-sheet[open]')
                await tap('.wt-sheet .wt-card.wt-old')
                await page.wait_for_selector('.wt-read.wt-old', timeout=5000)
                await tap('.wt-read [data-wt="pray"]')
                await page.wait_for_selector('.wt-read [data-wt="pray"][disabled]', timeout=5000)
                await shot('12d-read-old', 400, '.wt-sheet[open]')
                if shared_of(db, token)[1] != 1:
                    problems.append(f'[{name}] 🙏 on an old card is not in chua_card_prayers')
                await tap('.wt-read [data-wt="shut"]')
                await tap('.wt-sheet [data-wt="back"]')
                await page.wait_for_selector('.wt-sheet .wt-tile', timeout=8000)
                await tap('.wt-sheet [data-wt="mine"]')
                await page.wait_for_selector('.wt-sheet .wt-card.mine', timeout=8000)
                await page.wait_for_selector('.wt-sheet .wt-mycard', timeout=8000)
                await shot('13-mine', 400, '.wt-sheet[open]')
                await page.evaluate("document.querySelector('.wt-sheet .wt-mine-old')?.scrollIntoView({block:'start'})")
                await shot('13b-mine-old', 300, '.wt-sheet[open]')
                if shared_of(db, token)[0] != 1:
                    problems.append(f'[{name}] the player\'s shared old card is not on the board')
                await tap('.wt-sheet .wt-mycard.on [data-wt="card-share"]')
                await page.wait_for_function("(__wish.state().cards||[]).length===2&&__wish.state().cards.every(c=>!c.public)", timeout=8000)
                if shared_of(db, token)[0] != 0:
                    problems.append(f'[{name}] "Thôi chia sẻ" left the card on the board')
                await shot('13c-mine-unshared', 400, '.wt-sheet[open]')
                await tap('.wt-sheet [data-wt="close"]')
                await page.wait_for_function('!__chua.state().covered', timeout=5000)
                await shot('14-courtyard-after', 900, '.cv-sheet[open]')
                await boards(page, name, '14-courtyard-after', problems)
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
                if await page.locator('.cv-panel [data-cv="board"]').count():
                    problems.append(f'[{name}] "Quanh đây" still has the separate old board')
                after = read(db, token)
                for a in ('huong', 'khan', 'nguyen'):
                    if a not in after['chua'].get('did', []):
                        problems.append(f'[{name}] {a} not done on the server: {after["chua"].get("did")}')
                if after['wallet'] != before['wallet']:
                    problems.append(f'[{name}] the wallet moved')
                if any(text in c['text'] for c in after['chua'].get('cards', [])):   # (the player's two old cards are there on purpose)
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
