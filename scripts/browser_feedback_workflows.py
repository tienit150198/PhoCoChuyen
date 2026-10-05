"""Actual mobile/desktop input on feedback controls; static assets and fixture state only.

Run with a prepared JSON fixture containing cafe/clothing/tea public states and content.
The browser environment owns no player database or live-service connection.
"""
import argparse
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class Assets(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'public'), **kwargs)

    def do_GET(self):
        if self.path == '/':
            body = b'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body></body></html>'
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', required=True, type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding='utf-8'))
    out = ROOT / 'output' / 'playwright' / 'feedback-workflows'
    out.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for width, height in [(428, 879), (1280, 900)]:
                page = browser.new_page(viewport=dict(width=width, height=height))
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.evaluate("""async ({fixture,width}) => {
                  const {careerContext,careerSwitchButton}=await import('/js/v4/careers.js');
                  const {inventoryView,v4Action}=await import('/js/v4/views.js');
                  const {operationsView}=await import('/js/operations-ui.js');
                  const cafe=(await import('/js/careers/cafe_bakery.js')).default;
                  document.documentElement.dataset.layout=width<600?'phone':'desktop';
                  document.head.insertAdjacentHTML('beforeend',['app','lifesheets','operations','stock','careers/food_kit','careers/cafe_bakery'].map(s=>`<link rel="stylesheet" href="/css/${s}.css">`).join(''));
                  document.body.innerHTML=`<main class="stage" style="height:180px"><div id="sceneHeading" class="scene-heading"><div class="scene-title"><h1>Tiệm thử giao diện</h1></div>${careerSwitchButton()}</div></main><dialog id="sheet" open style="position:relative;margin:0 auto;width:calc(100% - 12px);max-height:none"></dialog>`;
                  const ui={view:'inventory',orderItem:'tee'},sent=[];
                  const env={api:{state:fixture.clothing,content:fixture.content},ui,renderSheet:()=>render('stock'),openSheet(){},confirmAction:async()=>true,cmd:async(op,p)=>{sent.push([op,p]);return {};}};
                  const render=kind=>{const sheet=document.querySelector('#sheet');
                    if(kind==='stock')sheet.innerHTML=inventoryView(env);
                    if(kind==='staff'){const s=fixture.tea;sheet.innerHTML=operationsView('milk_tea',s.careers.milk_tea,fixture.content.operations,{},s);}
                    if(kind==='cafe'){const x=careerContext({api:{state:fixture.cafe,content:fixture.content},ui:{}});sheet.innerHTML=cafe.job(x.room.tasks[0],x);}
                  };
                  document.addEventListener('click',e=>{const el=e.target.closest('[data-action]');if(!el)return;if(el.dataset.action==='home'){document.body.dataset.pickerOpened='yes';return;}v4Action(el.dataset.action,el.dataset,el,env);});
                  window.feedbackHarness={env,sent,render};render('stock');
                }""", dict(fixture=fixture, width=width))
                switch = page.get_by_role('button', name='Đổi nghề hoặc nơi làm việc')
                switch.click()
                expect(page.locator('body')).to_have_attribute('data-picker-opened', 'yes')
                page.locator('[data-action="v4OrderSize"][data-size="XL"]').click()
                expect(page.locator('[data-action="v4OrderSize"][data-size="XL"]')).to_have_attribute('aria-pressed', 'true')
                page.get_by_role('button', name='Đặt ngay', exact=True).click()
                page.wait_for_function("feedbackHarness.sent.length===1")
                assert page.evaluate('feedbackHarness.sent[0][1].size') == 'XL'
                page.screenshot(path=str(out / f'stock-{width}.png'), full_page=True)
                page.evaluate("feedbackHarness.render('staff')")
                expect(page.locator('.ops-body')).to_contain_text('Bạn vẫn tự tay pha từng ly')
                expect(page.get_by_role('button', name='🏪 Quầy của bạn', exact=True)).to_be_visible()
                page.screenshot(path=str(out / f'staff-{width}.png'), full_page=True)
                page.evaluate("feedbackHarness.render('cafe')")
                expect(page.get_by_role('button', name='4× · Rất nhanh', exact=True)).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(out / f'cafe-{width}.png'), full_page=True)
                page.close()
            browser.close()
        assert not errors, errors
        print('Feedback browser input passed:428x879 and1280x900; screenshots in output/playwright/feedback-workflows.')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
