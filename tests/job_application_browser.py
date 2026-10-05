"""Browser check of real hiring bodies in the shipping dialog/CSS (no player server).

Run: python -m tests.job_application_browser [--engine chromium|webkit]
"""
import argparse
import asyncio
import http.server
import json
from pathlib import Path
import threading
import sys

from playwright.sync_api import expect, sync_playwright
from tests.test_job_application_ui import fixtures

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
    # tests/__init__.py selects the PostgreSQL loop; this browser-only runner
    # needs Windows subprocess support and opens no database connections.
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('chromium', 'webkit'), default='chromium')
    args = parser.parse_args()
    fixture = json.loads(json.dumps(fixtures()))
    app_source = (ROOT / 'public/js/app.js').read_text(encoding='utf-8')
    morph_source = app_source[app_source.index('const morphTpl='):app_source.index('const lowOpen=')]
    gesture_start = app_source.index("{const d=$('#sheet'),HANDLE=")
    gesture_source = app_source[gesture_start:app_source.index("$('#sheet').addEventListener('close'", gesture_start)]
    out = ROOT / 'output' / 'playwright' / 'job-application'
    out.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    results = []
    try:
        with sync_playwright() as pw:
            browser = getattr(pw, args.engine).launch()
            for width, height in ((390, 844), (1280, 900)):
                page = browser.new_page(viewport=dict(width=width, height=height), has_touch=width < 600)
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.evaluate("""async ({fixture,width,morphSource,gestureSource}) => {
                  const {jobView}=await import('/js/v4/views.js');
                  const {applyGuide}=await import('/js/v4/guide.js');
                  const {moneyBoot}=await import('/js/v4/money.js');
                  const morph=new Function('i18nT',`${morphSource}; return morph;`)(text=>text);
                  document.documentElement.dataset.layout=width<600?'phone':'desktop';
                  await Promise.all(['app','lifesheets','certificates','money'].map(s=>new Promise((resolve,reject)=>{
                    const link=document.createElement('link');link.rel='stylesheet';link.href=`/css/${s}.css`;
                    link.onload=resolve;link.onerror=reject;document.head.append(link);
                  })));
                  document.body.innerHTML='<main style="height:100vh">Phòng tổ bay</main><dialog id="sheet" class="sheet medium v4-sheet"><div id="sheetContent"></div></dialog>';
                  const sheet=document.querySelector('#sheet'),box=document.querySelector('#sheetContent');
                  new Function('$','layout',gestureSource)(s=>document.querySelector(s),()=>width<600?'phone':'desktop');
                  sheet.addEventListener('cancel',e=>{e.preventDefault();sheet.close();});
                  const api={state:fixture.states[0].state,content:fixture.content};
                  moneyBoot({api,scope:()=>({fund:null}),phone:()=>width<600,css:null});
                  window.hiring={events:[],render(index,preserve=false){
                    if(!preserve)sheet.resetGesture?.();
                    api.state=fixture.states[index].state;
                    const env={api,ui:{}},html=jobView(env),scroll=preserve?sheet.scrollTop:0;
                    if(preserve)morph(box,html);else box.innerHTML=html;
                    applyGuide(sheet);sheet.scrollTop=scroll;
                    if(!sheet.open)sheet.showModal();
                    document.dispatchEvent(new Event('sheetrender'));
                  }};
                  for(const name of ['pointerdown','pointermove','pointercancel','lostpointercapture'])sheet.addEventListener(name,e=>hiring.events.push({name,id:e.pointerId,type:e.pointerType}));
                  document.addEventListener('click',event=>{if(event.target.closest('[data-action="close"]'))sheet.close();});
                }""", dict(fixture=fixture, width=width, morphSource=morph_source, gestureSource=gesture_source))
                captured = set()
                for index, row in enumerate(fixture['states']):
                    # Every later state follows app.js's in-place morph with its
                    # existing scroll offset, including long CV -> short interview.
                    page.evaluate('index=>hiring.render(index,index>0)', index)
                    page.wait_for_function("document.querySelector('#sheet').getAnimations().every(a=>a.playState==='finished')")
                    body = page.locator('#sheetContent > .sheet-body')
                    expect(body).to_be_visible()
                    bounds = body.bounding_box()
                    assert bounds and bounds['height'] > 60 and bounds['width'] > 100, row['label']
                    state = row['state']
                    job = state['careers'][state['current']]['job']
                    stage = (job.get('application') or {}).get('stage')
                    target = body.locator('button').first
                    target.scroll_into_view_if_needed()
                    expect(target).to_be_in_viewport()
                    if state['current'] == 'flight_attendant' and stage in ('cv', 'interview') and stage not in captured:
                        page.evaluate("document.querySelector('#sheet').scrollTop=0")
                        page.screenshot(path=str(out / f'{args.engine}-{width}-{stage}.png'))
                        captured.add(stage)
                    results.append(dict(engine=args.engine, width=width, state=row['label'], body=bounds))
                if width < 600 and args.engine == 'chromium':
                    # CDP starts a trusted touchscreen pointer, so capture uses the
                    # browser's real pointer ownership. Eight pixels stays below
                    # native scrolling's cancellation threshold.
                    page.evaluate('hiring.render(1)')
                    page.wait_for_function("document.querySelector('#sheet').getAnimations().every(a=>a.playState==='finished')")
                    head = page.locator('.sheet-head').bounding_box()
                    x, y = width / 2, head['y'] + 9
                    touch = page.context.new_cdp_session(page)
                    touch.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=x, y=y)]))
                    touch.send('Input.dispatchTouchEvent', dict(type='touchMove', touchPoints=[dict(x=x, y=y + 8)]))
                    assert page.evaluate("document.querySelector('#sheet').style.transform !== ''"), 'trusted touch must move the handle'
                    page.evaluate("window.dispatchEvent(new Event('blur'))")
                    assert page.evaluate("document.querySelector('#sheet').style.transform === ''"), 'blur restores a partially dragged sheet'
                    touch.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[]))
                    expect(page.locator('#sheet > #sheetContent > .sheet-body')).to_be_visible()
                    touch.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=x, y=y)]))
                    touch.send('Input.dispatchTouchEvent', dict(type='touchMove', touchPoints=[dict(x=x, y=y + 8)]))
                    page.evaluate("""()=>{
                      const sheet=document.querySelector('#sheet'),id=hiring.events.filter(e=>e.name==='pointerdown').at(-1).id;
                      sheet.releasePointerCapture(id);
                    }""")
                    touch.send('Input.dispatchTouchEvent', dict(type='touchMove', touchPoints=[dict(x=x, y=y + 9)]))
                    assert page.evaluate("document.querySelector('#sheet').style.transform === ''"), 'lost native capture restores the sheet'
                    touch.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[]))
                    # Keep a trusted pointer active while replaying the final
                    # fast-drag events, then replace the view before its timer.
                    touch.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=x, y=y)]))
                    page.evaluate("""({y})=>{
                      const sheet=document.querySelector('#sheet'),id=hiring.events.filter(e=>e.name==='pointerdown').at(-1).id;
                      sheet.dispatchEvent(new PointerEvent('pointermove',{pointerId:id,pointerType:'touch',clientY:y+130,bubbles:true}));
                      sheet.dispatchEvent(new PointerEvent('pointerup',{pointerId:id,pointerType:'touch',clientY:y+130,bubbles:true}));
                      if(sheet.style.transform!=='translateY(100%)')throw Error('dismissal did not begin');
                      hiring.render(1);
                    }""", dict(y=y))
                    touch.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[]))
                    # The behavior under test is specifically a 190ms delayed close.
                    page.wait_for_timeout(260)
                    assert page.evaluate("document.querySelector('#sheet').open && document.querySelector('#sheet').style.transform === ''"), 'old dismissal cannot close the new application'
                    page.screenshot(path=str(out / 'chromium-390-after-drag-reopen.png'))
                    results.append(dict(engine=args.engine, width=width, gesture='trusted touch blur/lost capture and drag/reopen timer passed'))
                page.get_by_role('button', name='Đóng', exact=True).click()
                assert page.evaluate("!document.querySelector('#sheet').open && !document.querySelector(':modal')")
                page.close()
            browser.close()
        assert not errors, errors
        (out / f'{args.engine}-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        renders = sum('state' in result for result in results)
        gestures = sum('gesture' in result for result in results)
        print(f'{args.engine}: {renders} hiring renders visible with reachable controls; {gestures} touch lifecycle checks; close releases the modal.')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
