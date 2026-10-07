"""🏅 Danh hiệu bên tên in the real chat modules (public/js/v4/chat.js + honours.js) with controlled socket frames:
Cả phố with several title holders (2 chips + "+N" on a phone, 3 on a wide screen), a tap on the name opens every
title, a reply's quote, a DM header; no horizontal overflow at 360 px. No database or live service.

Run: python scripts/browser_chat_titles.py [--shots DIR]   (writes chat-titles-phone.jpg, chat-titles-desktop.jpg)
"""
import argparse
import base64
import http.server
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

PUBLIC = Path(__file__).resolve().parents[1] / 'public'
ME, A, B, C = 'aaaaaaaaaaaaaaaa', 'bbbbbbbbbbbbbbbb', 'cccccccccccccccc', 'dddddddddddddddd'


class Assets(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

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


SETUP = """async ([me,a,b,c]) => {
  const {live}=await import('/js/v4/live.js');
  const handlers=new Map(),sent=[];
  Object.assign(live,{state:'open',welcomed:true,me:{pid:me,account:true,name:'Mình'},flags:{chat:true},friends:[],limits:{},
    chans:[{id:'dm:'+[me,a].sort().join(':'),kind:'dm',unread:0,peer:{pid:a,name:'Lan Anh',av:'🌷'}}]});
  live.on=(type,fn)=>handlers.set(type,fn);
  live.send=frame=>{sent.push(frame);return true;};
  const {openChat}=await import('/js/v4/chat.js');
  const t0=1791370800;
  const msg=(id,pid,name,av,text,extra={})=>({t:'msg',ch:'town',id,pid,name,av,text,at:t0+id*20,...extra});
  const q={id:1,pid:a,name:'Lan Anh',text:'Có ai biết hội chợ mấy giờ đóng cửa không ạ?',tt:['lb_milk_tea_1','lb_wealth_3','f_bao','f_dart']};
  const msgs=[
    msg(1,a,'Lan Anh','🌷',q.text,{tt:q.tt}),
    msg(2,b,'Nguyễn Hoàng Minh Tú','🐯','10h tối nha bạn, Hũ đêm hội từ 8h đó 🏺',{tt:['lb_all_1','lb_titles_2','lb_certs_7','f_king','w_vip','f_hu','f_loto','f_raid'],reply:q,st:{t:'t_mot_phim'}}),
    msg(3,c,'Bé Bơ','🐰','cảm ơn nhaa',{tt:['f_oaq']}),
    msg(4,me,'Mình','🙂','Mình vừa trúng bão bầu cua 🌪️',{tt:['f_bao']}),
    msg(5,'eeeeeeeeeeeeeeee','Khách quen','🍵','Không có danh hiệu thì vẫn như cũ'),
  ];
  window.H={live,sent,emit:(type,f)=>handlers.get(type)?.(f),msgs};
  await openChat({api:{content:{}}},{ch:'town'});
  H.emit('joined',{ch:'town',msgs,more:false,why:'ok',wait:0,n:12,pin:null});
}"""


def no_overflow(page):
    return page.evaluate("""() => {
      const b=document.querySelector('.ch-body');
      const bad=[...document.querySelectorAll('.ch-name,.hn-chips,.hn-pop,.ch-quote')].filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+0.5||r.left<-0.5;});
      return {body:b.scrollWidth<=b.clientWidth+1,doc:document.documentElement.scrollWidth<=innerWidth+1,bad:bad.map(e=>e.className)};
    }""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default='')
    args = ap.parse_args()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    runner = threading.Thread(target=server.serve_forever, daemon=True)
    runner.start()
    errors, shots = [], {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for width, height, touch in [(360, 780, True), (390, 844, True), (1280, 900, False)]:
                ctx = browser.new_context(viewport=dict(width=width, height=height), has_touch=touch, device_scale_factor=2 if touch else 1)
                page = ctx.new_page()
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.evaluate(SETUP, [ME, A, B, C])
                expect(page.locator('.ch-bub')).to_have_count(5)
                inline = 2 if width < 700 else 3
                minh = page.locator('.ch-name.hn-btn', has_text='Minh Tú')
                expect(minh.locator('.hn-chip:not(.hn-more)')).to_have_count(inline)
                expect(minh.locator('.hn-more')).to_have_text(f'+{8 - inline}')
                expect(minh.locator('.hn-chip').first).to_contain_text('Top 1 Trải nghiệm')
                expect(page.locator('.ch-name.hn-btn', has_text='Lan Anh').locator('.hn-chip').first).to_contain_text('Trùm trà sữa')
                expect(page.locator('.ch-name', has_text='Khách quen').locator('.hn-chip')).to_have_count(0)
                expect(page.locator('.ch-quote .hn-chip')).to_have_count(1)     # the reply's quote: the best one
                assert page.locator('.ch-msg.mine .hn-chip').count() == 0       # my own lines carry no name row
                ok = no_overflow(page)
                assert ok['body'] and ok['doc'] and not ok['bad'], (width, ok)
                # a tap on the name: every title, full names and where they come from; a tap elsewhere closes it
                minh.click()
                pop = page.locator('.hn-pop')
                expect(pop.locator('li')).to_have_count(8)
                expect(pop).to_contain_text('Trùm cuối của phố')
                expect(pop).to_contain_text('Top 1 Trải nghiệm · tuần này')
                expect(pop).to_contain_text('Vua trò chơi')
                expect(pop).to_contain_text('Khách quý của phố')
                expect(pop).to_contain_text('Bị công an hỏi thăm')
                ok = no_overflow(page)
                assert ok['body'] and ok['doc'] and not ok['bad'], (width, ok)
                if width != 390:
                    minh.evaluate("e=>e.scrollIntoView({block:'start'})")
                    page.wait_for_timeout(150)
                    shots[width] = page.screenshot(type='png')
                page.locator('.ch-here').click()
                expect(pop).to_have_count(0)
                if width == 390:
                    shots[width] = page.screenshot(type='png')
                    # a DM: the peer's titles under their name in the header, tap: all of them
                    dm = 'dm:' + ':'.join(sorted([ME, A]))
                    page.evaluate("""dm => {H.live.chan=id=>H.live.chans.find(c=>c.id===id);}""", dm)
                    page.locator('[data-ch-act="tab"][data-tab="inbox"]').click()
                    page.locator('.ch-row[data-ch-act="open"]').click()
                    page.evaluate("""dm => H.emit('history',{ch:dm,msgs:[{t:'msg',ch:dm,id:40,pid:'%s',name:'Lan Anh',av:'🌷',text:'tối ghé hội chợ hông',at:1791371800,tt:['lb_milk_tea_1','lb_wealth_3','f_bao','f_dart']}],more:false})""" % A, dm)
                    head = page.locator('.hn-head')
                    expect(head.locator('.hn-chip:not(.hn-more)')).to_have_count(2)
                    expect(head.locator('.hn-more')).to_have_text('+2')
                    head.click()
                    expect(page.locator('.ch-body > .hn-pop li')).to_have_count(4)
                print(f'PASS {width}x{height}: chips inline {inline} + "+N", popover, quote, no overflow')
                ctx.close()
            if args.shots:
                out = Path(args.shots)
                out.mkdir(parents=True, exist_ok=True)
                ctx = browser.new_context(viewport=dict(width=1500, height=1600))
                page = ctx.new_page()
                imgs = ''.join(f'<figure><img src="data:image/png;base64,{base64.b64encode(shots[w]).decode()}"><figcaption>{w} px</figcaption></figure>'
                               for w in (360, 390))
                page.set_content(f'<body style="margin:0;background:#ddd;display:flex;gap:24px;padding:16px;font:14px sans-serif;align-items:flex-start">'
                                 f'<style>img{{width:{360}px;height:auto;display:block;box-shadow:0 2px 10px #0003}} figure{{margin:0}}</style>{imgs}</body>')
                page.wait_for_timeout(200)
                page.screenshot(path=str(out / 'chat-titles-phone.jpg'), type='jpeg', quality=72, full_page=True)
                page.set_content(f'<body style="margin:0"><img style="width:1280px;display:block" src="data:image/png;base64,{base64.b64encode(shots[1280]).decode()}"></body>')
                page.wait_for_timeout(200)
                page.screenshot(path=str(out / 'chat-titles-desktop.jpg'), type='jpeg', quality=72, full_page=True)
                print('shots:', out / 'chat-titles-phone.jpg', out / 'chat-titles-desktop.jpg')
                ctx.close()
            browser.close()
        assert not errors, errors
        print('PASS: no browser JavaScript errors')
    finally:
        server.shutdown()
        server.server_close()
        runner.join()


if __name__ == '__main__':
    main()
