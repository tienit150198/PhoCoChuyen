"""📦 🍳 💭 Feedback #373, #485, #170 in a browser at 390x844 (dev tool, needs `pip install playwright` + chromium).

1. 📦 Tạp hóa at level 5 (real app, throwaway story server): 🧺 Giỏ quen with the wholesale buyers, the new goods.
2. 🍳 The evening in a rented room: "Vào bếp nấu cơm tối" → menu → market → prep → the heat bar → season → plate.
3. 💭 Chat notes (the real chat module with controlled socket frames, no live service): the strip on Tin nhắn and
   Bạn bè, writing mine, reading and reporting a friend's.

    python scripts/browser_fb_social.py [out_dir]
"""
import asyncio
import http.server
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402
from browser_needs import act, mutate, tick_to  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / '_fb_social_shots'
W, H = 390, 844


def seed(s):
    from game import journey as jr
    from game import whats_new as wn
    j = s['journey']
    s['name'] = 'Lan'
    j.update(gender='female', intro=True, wallet=900)
    jr._welcome_settings(s)
    s['settings'].update(uiTheme='kem', lang='vi', tutorialDone=True, whatsNewSeen=wn.LATEST)
    act(s, 'select_career')
    act(s, 'start_day')
    for _ in range(3):
        act(s, 'end_day', carry_event=True)
        s['careers']['grocery']['xp'] = 90 * 4          # level 5: two buyers may call, three new goods
        act(s, 'start_day')
    tick_to(s, 9 * 60 + 30)


def evening(s):
    from game import housing as hs
    tick_to(s, 17 * 60)
    act(s, 'end_day', carry_event=True)
    s['journey']['wallet'] = 900
    hs.apply(s, 'jr_home_rent', dict(kind=next(k for k in hs.RENT if k != hs.DORM), confirm=True))


async def game_part(browser, errors):
    with server() as (base, db):
        ctx = await browser.new_context(viewport=dict(width=W, height=H), has_touch=True, device_scale_factor=2)
        await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0')}catch(e){}")
        page = await ctx.new_page()
        page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
        page.on('pageerror', lambda e: errors.append(str(e)))
        await page.goto(base)
        await page.wait_for_selector('#app:not([hidden])', timeout=30000)
        token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
        mutate(db, token, seed)

        async def reload():
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=30000)
            await page.wait_for_timeout(1500)
            for _ in range(6):
                hit = False
                for sel in ('[data-wn="close"]:visible', '[data-action="jrSceneClose"]:visible', '[data-action="lfLater"]:visible'):
                    b = page.locator(sel)
                    if await b.count():
                        await b.first.click()
                        await page.wait_for_timeout(350)
                        hit = True
                if not hit:
                    break
            await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
            for txt in ('Biết rồi',):   # the weekly x3 card and other notices
                b = page.locator('button:visible', has_text=txt)
                if await b.count():
                    await b.first.click()
                    await page.wait_for_timeout(300)
            await page.wait_for_timeout(300)

        async def shot(name, full=False):
            await page.wait_for_timeout(400)
            await page.screenshot(path=str(OUT / f'{name}.png'), full_page=full)

        async def no_hscroll(where):
            wide = await page.evaluate("document.documentElement.scrollWidth>innerWidth+1")
            assert not wide, f'{where}: horizontal scroll'

        await reload()
        await shot('0-home')
        await page.evaluate("document.querySelector('[data-action=workbench]').click()")
        await page.wait_for_timeout(1200)
        await shot('0b-workbench')
        ev = page.locator('[data-action="v4Cmd"]:visible')   # the morning surprise: the honest answer
        if await ev.count():
            await ev.first.click()
            await page.wait_for_timeout(600)
            yes = page.locator('[data-action="confirmYes"]:visible')
            if await yes.count():
                await yes.first.click()
            await page.wait_for_timeout(1500)
        if not await page.locator('[data-action="car:tab"]').count():   # the full career screen (Giao diện đầy đủ)
            await page.evaluate("document.querySelector('[data-action=uiSide]')?.click()")
            await page.wait_for_timeout(1500)
        await shot('0c-career')
        # 1. 📦 Giỏ quen: khách sỉ
        await page.evaluate("document.querySelector('.gr-tabs [data-tab=lists]').click()")
        await page.wait_for_timeout(1000)
        await shot('0d-lists')
        await page.wait_for_selector('.gr-ws-head', state='attached', timeout=8000)
        await page.evaluate("document.querySelector('.gr-ws-head')?.scrollIntoView({block:'start'})")
        await no_hscroll('grocery lists')
        await shot('1-grocery-wholesale')
        goods = page.locator('.gr-ws-goods')
        if await goods.count():
            await goods.first.scroll_into_view_if_needed()
            await shot('2-grocery-new-goods')
        take = page.locator('.gr-ws-acts button', has_text='Nhận')
        if await take.count():
            await take.first.click()
            await page.wait_for_timeout(1200)
            await page.evaluate("document.querySelector('.gr-ws-head')?.scrollIntoView({block:'start'})")
            await shot('3-grocery-order-taken')

        # 2. 🍳 the evening kitchen
        mutate(db, token, evening)
        await reload()
        if await page.locator('[data-action="evening"]:visible').count():
            await page.click('[data-action="evening"]:visible')
        else:   # the island view: the same action the calm card's 🌙 button sends
            await page.evaluate("(()=>{const b=document.createElement('button');b.dataset.action='evening';document.querySelector('#app').append(b);b.click();b.remove();})()")
        await page.wait_for_selector('#sheet[open] .nd-cook', timeout=8000)
        await page.evaluate("document.querySelector('#sheet .nd-cook')?.scrollIntoView({block:'center'})")
        await shot('4-evening-cook-entry')
        await page.click('#sheet .nd-cook')
        await page.wait_for_selector('dialog[open] .ck-dishes', timeout=8000)
        await no_hscroll('cook menu')
        await shot('5-cook-menu')
        await page.click('dialog[open] [data-ck="pick"][data-id="canh"]')
        await page.wait_for_selector('dialog[open] .ck-items', timeout=5000)
        for b in await page.locator('dialog[open] [data-ck="take"]').all():
            await b.click()
        await shot('6-cook-market')
        await page.click('dialog[open] [data-ck="go"][data-to="prep"]')
        await page.wait_for_selector('dialog[open] .ck-board', timeout=5000)
        for _ in range(12):
            cut = page.locator('dialog[open] [data-ck="cut"]:not([disabled])')
            if not await cut.count():
                break
            await cut.first.click()
        await shot('7-cook-prep')
        await page.click('dialog[open] [data-ck="go"][data-to="cook"]')
        await page.wait_for_selector('dialog[open] .ck-gauge', timeout=5000)
        await shot('8-cook-heat')
        await page.evaluate("""()=>new Promise(r=>{const t=()=>{const z=document.querySelector('dialog[open] .ck-zone'),n=document.querySelector('dialog[open] .ck-needle');
          const l=parseFloat(z.style.left),w=parseFloat(z.style.width),p=parseFloat(n.style.left);
          if(p>l+w*.3&&p<l+w*.7){document.querySelector('dialog[open] [data-ck="stop"]').click();r(p);}else requestAnimationFrame(t);};t();})""")
        await page.wait_for_selector('dialog[open] .ck-say', timeout=3000)
        await shot('9-cook-stopped')
        await page.click('dialog[open] [data-ck="go"][data-to="season"]')
        await page.wait_for_selector('dialog[open] .ck-rack', timeout=5000)
        for sid in ('me', 'duong', 'mam'):
            b = page.locator(f'dialog[open] [data-ck="spice"][data-id="{sid}"]')
            if await b.count():
                await b.click()
        await shot('10-cook-season')
        await page.click('dialog[open] [data-ck="go"][data-to="plate"]')
        await page.click('dialog[open] [data-ck="serve"]')
        await page.wait_for_selector('dialog[open] .ck-stars', timeout=8000)
        await no_hscroll('cook done')
        await shot('11-cook-done')
        await page.click('dialog[open] [data-ck="close"]')
        await page.wait_for_selector('#sheet[open] .nd-cook.done', timeout=8000)
        await page.evaluate("document.querySelector('#sheet .nd-cook')?.scrollIntoView({block:'center'})")
        await shot('12-evening-after-cook')
        await ctx.close()


class Assets(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'public'), **kwargs)

    def do_GET(self):
        if self.path == '/':
            body = (b'<!doctype html><html lang="vi" data-layout="phone"><head><meta charset="utf-8">'
                    b'<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css">'
                    b'</head><body></body></html>')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, *_):
        pass


ME, A, B = 'aaaaaaaaaaaaaaaa', 'bbbbbbbbbbbbbbbb', 'cccccccccccccccc'
SETUP = """async ([me,a,b]) => {
  const {live}=await import('/js/v4/live.js');
  const handlers=new Map(),sent=[],now=Date.now()/1000;
  Object.assign(live,{state:'open',welcomed:true,me:{pid:me,account:true,name:'Mình',av:'🙂',nt:null,online:true},flags:{chat:true,blocks:true},limits:{},
    friends:[{pid:a,name:'Lan Anh',av:'🌷',on:true,nt:{t:'Đang ôn thi, tối nhắn nha 📚',at:now-600}},
             {pid:b,name:'Nguyễn Hoàng Minh Tú',av:'🐯',on:false,nt:{t:'Ra hồ câu cá 🎣 ai đi hông',at:now-3600}},
             {pid:'dddddddddddddddd',name:'Bé Bơ',av:'🐰',on:true}],
    chans:[{id:'dm:'+[me,a].sort().join(':'),kind:'dm',unread:2,peer:{pid:a,name:'Lan Anh',av:'🌷',on:true,nt:{t:'Đang ôn thi, tối nhắn nha 📚',at:now-600}},last:{id:9,pid:a,name:'Lan Anh',text:'mai đi chợ hông',at:now-300}}]});
  live.chan=id=>live.chans.find(c=>c.id===id);
  live.friend=pid=>live.friends.find(f=>f.pid===pid);
  live.on=(type,fn)=>{const l=handlers.get(type)||[];l.push(fn);handlers.set(type,l);};
  live.send=frame=>{sent.push(frame);return true;};
  const {openChat}=await import('/js/v4/chat.js');
  window.H={live,sent,emit:(type,f)=>{for(const fn of handlers.get(type)||[])fn(f);}};
  await openChat({api:{content:{}}},{});
}"""


async def chat_part(browser, errors):
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        ctx = await browser.new_context(viewport=dict(width=W, height=H), has_touch=True, device_scale_factor=2)
        page = await ctx.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        await page.goto(f'http://127.0.0.1:{srv.server_port}/')
        await page.evaluate(SETUP, [ME, A, B])
        await page.click('[data-ch-act="tab"][data-tab="inbox"]')
        await page.wait_for_selector('.ch-notes .ch-ntcell', timeout=5000)
        n = await page.locator('.ch-notes .ch-ntcell').count()
        assert n == 3, n                                   # mine + two friends (Lan Anh once, though also a DM peer)
        assert await page.evaluate("document.querySelector('.ch-body').scrollWidth<=document.querySelector('.ch-body').clientWidth+1")
        await page.screenshot(path=str(OUT / '13-chat-notes-inbox.png'))
        await page.click('.ch-ntcell[data-ch-act="note"]')
        await page.fill('[data-ch-field="note"]', 'Tối nay nấu canh chua 🍲 ai ghé ăn hông')
        assert await page.locator('.ch-ntview .ch-ntbub').inner_text() == 'Tối nay nấu canh chua 🍲 ai ghé ăn hông'
        await page.screenshot(path=str(OUT / '14-chat-note-write.png'))
        await page.click('[data-ch-act="noteSave"]')
        sent = await page.evaluate('H.sent.at(-1)')
        assert sent == {'t': 'note', 'text': 'Tối nay nấu canh chua 🍲 ai ghé ăn hông', 'cid': 'note'}, sent
        await page.evaluate("""me=>{const nt={t:'Tối nay nấu canh chua 🍲 ai ghé ăn hông',at:Date.now()/1000};H.live.me.nt=nt;H.emit('noted',{t:'noted',pid:me,nt});}""", ME)
        await page.wait_for_selector('.ch-notes', timeout=3000)
        await page.click('[data-ch-act="tab"][data-tab="friends"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / '15-chat-notes-friends.png'))
        await page.click(f'.ch-ntcell[data-pid="{B}"]')
        await page.wait_for_selector('.ch-ntview', timeout=3000)
        await page.click('[data-ch-act="noteReport"]')
        await page.screenshot(path=str(OUT / '16-chat-note-report.png'))
        await page.click('[data-ch-act="noteReason"][data-reason="spam"]')
        sent = await page.evaluate('H.sent.at(-1)')
        assert sent == {'t': 'note_report', 'pid': B, 'reason': 'spam', 'cid': 'noteReport'}, sent
        assert await page.locator(f'.ch-ntcell[data-pid="{B}"]').count() == 0
        await ctx.close()
    finally:
        srv.shutdown()
        srv.server_close()
        th.join()


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        await chat_part(browser, errors)
        print('PASS chat notes')
        await game_part(browser, errors)
        print('PASS grocery + cook')
        await browser.close()
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)


if __name__ == '__main__':
    asyncio.run(main())
