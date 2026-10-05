"""Deterministic real-browser reproduction of inbox/thread history races.

Uses the real chat modules and dialog with controlled socket frames. No player
database is opened. Run: python scripts/browser_chat_history.py
"""
import http.server
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

PUBLIC = Path(__file__).resolve().parents[1] / 'public'
CH = 'dm:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb'


class Assets(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def do_GET(self):
        if self.path == '/':
            body = b'<!doctype html><html><head><meta charset="utf-8"></head><body></body></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, *_):
        pass


def main():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    runner = threading.Thread(target=server.serve_forever, daemon=True)
    runner.start()
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for width, height in [(390, 844), (1280, 900)]:
                context = browser.new_context(viewport=dict(width=width, height=height))
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.evaluate("""async ch => {
                  const {live}=await import('/js/v4/live.js');
                  const handlers=new Map(),sent=[];
                  Object.assign(live,{state:'open',welcomed:true,me:{pid:'aaaaaaaaaaaaaaaa',account:true},
                    flags:{chat:true},friends:[],limits:{},chans:[{id:ch,kind:'dm',unread:0,
                      peer:{pid:'bbbbbbbbbbbbbbbb',name:'Bạn thử',av:'🌸'}}]});
                  live.on=(type,fn)=>handlers.set(type,fn);
                  live.send=frame=>{sent.push(frame);return live.state==='open';};
                  const {openChat}=await import('/js/v4/chat.js');
                  const msg=(id,text)=>({t:'msg',ch,id,pid:'bbbbbbbbbbbbbbbb',name:'Bạn thử',av:'🌸',text,at:1700000000+id});
                  window.chatHarness={live,sent,emit:(type,frame)=>handlers.get(type)?.(frame),msg};
                  await openChat({api:{}},{ch});
                }""", CH)
                expect(page.locator('.ch-body')).to_contain_text('Đang tải')
                page.evaluate("""ch => {
                  const h=chatHarness,m=h.msg(12,'tin mới đến khi đang tải');
                  h.live.chan(ch).last=m;h.emit('msg',m);
                  h.emit('history',{ch,msgs:[h.msg(11,'tin trước đó')],more:false});
                }""", CH)
                expect(page.locator('.ch-bub')).to_have_count(2)
                expect(page.locator('.ch-body')).to_contain_text('tin mới đến khi đang tải')
                page.locator('[data-ch-act="back"]').click()
                expect(page.locator('.ch-row')).to_contain_text('tin mới đến khi đang tải')
                page.evaluate("""ch => {
                  const h=chatHarness;h.live.state='down';h.emit('down',{});
                  const latest=h.msg(20,'tin gửi khi mất mạng');
                  h.live.chans=[{id:ch,kind:'dm',unread:1,last:latest,peer:{pid:latest.pid,name:'Bạn thử',av:'🌸'}}];
                  h.live.state='open';h.emit('welcome',{});h.sent.length=0;
                }""", CH)
                expect(page.locator('.ch-row')).to_contain_text('tin gửi khi mất mạng')
                page.locator('.ch-row[data-ch-act="open"]').click()
                assert page.evaluate("chatHarness.sent.some(f=>f.t==='history')"), 'cached thread did not reload'
                page.evaluate("""ch => {
                  const h=chatHarness;h.emit('history',{ch,msgs:[h.msg(20,'tin gửi khi mất mạng')],more:true});
                }""", CH)
                expect(page.locator('.ch-body')).to_contain_text('tin gửi khi mất mạng')
                expect(page.locator('.ch-bub')).to_have_count(1)
                expect(page.get_by_role('button', name='Xem cũ hơn')).to_be_visible()
                page.get_by_role('button', name='Xem cũ hơn').click()
                page.evaluate("""ch => {
                  const h=chatHarness;h.emit('history',{ch,before:20,msgs:[h.msg(19,'tin cũ hơn')],more:false});
                }""", CH)
                expect(page.locator('.ch-bub')).to_have_count(2)
                expect(page.locator('.ch-body')).to_contain_text('tin gửi khi mất mạng')
                print(f'PASS {width}x{height}: loading race, matching preview, reconnect, cached thread and older history')
                context.close()
            browser.close()
        assert not errors, errors
        print('PASS: no browser JavaScript errors')
    finally:
        server.shutdown()
        server.server_close()
        runner.join()


if __name__ == '__main__':
    main()
