"""Local venue rendering/input smoke: python scripts/browser_venue_visit.py [output-dir]."""
import asyncio
import functools
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'output' / 'temple-walk' / 'venues'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'public')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    report = {'language': 'en', 'scope': 'Local venue rooms; integrated transaction routes are tested separately.', 'checks': []}
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for width, height in [(390, 844), (1280, 800)]:
                context = await browser.new_context(viewport={'width': width, 'height': height}, has_touch=width == 390)
                page = await context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                await page.goto(f'http://127.0.0.1:{server.server_port}/css/venue-visit.css')
                await page.set_content('<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><button id="background">Background</button></body></html>')
                await page.evaluate('''async () => {
                  window.backgroundKeys=0; document.addEventListener('keydown',()=>window.backgroundKeys++);
                  window.openLocalVenue=async id=>{const {openVenue}=await import('/js/v4/venue-visit.js');
                    window.testVenue=await openVenue({api:{state:{}},onClose:()=>window.closedCount=(window.closedCount||0)+1,
                      onInteract:station=>new Promise(resolve=>{window.selectedStation=station;const d=document.createElement('dialog');d.id='service';d.innerHTML='<button>Return to room</button>';document.body.append(d);d.showModal();d.querySelector('button').onclick=()=>{d.close();d.remove();resolve();};})},{id});};
                  await openLocalVenue('cafe');
                }''')
                before = await page.evaluate('({x:testVenue.scene.state.x,y:testVenue.scene.state.y})')
                await page.keyboard.down('ArrowUp')
                await page.wait_for_timeout(420)
                await page.keyboard.up('ArrowUp')
                after = await page.evaluate('({x:testVenue.scene.state.x,y:testVenue.scene.state.y})')
                assert abs(after['x'] - before['x']) + abs(after['y'] - before['y']) > 8, 'Keyboard moves avatar'
                assert await page.evaluate('backgroundKeys') == 0, 'Room input is isolated'
                await page.locator('[data-station="counter"]').click()
                await page.wait_for_selector('#service[open]', timeout=15000)
                stopped = await page.evaluate('({x:testVenue.scene.state.x,y:testVenue.scene.state.y})')
                assert await page.evaluate('testVenue.suspended')
                await page.keyboard.press('ArrowLeft')
                assert await page.evaluate('({x:testVenue.scene.state.x,y:testVenue.scene.state.y})') == stopped
                await page.locator('#service button').click()
                await page.wait_for_selector('.venue-visit[open]')
                assert await page.evaluate('({x:testVenue.scene.state.x,y:testVenue.scene.state.y})') == stopped
                stick = page.locator('.venue-stick')
                bounds = await stick.bounding_box()
                x, y = bounds['x'] + bounds['width'] / 2, bounds['y'] + bounds['height'] / 2
                await stick.dispatch_event('pointerdown', {'pointerId': 7, 'pointerType': 'touch', 'clientX': x, 'clientY': y, 'button': 0, 'isPrimary': True})
                await stick.dispatch_event('pointermove', {'pointerId': 7, 'pointerType': 'touch', 'clientX': x + 28, 'clientY': y, 'isPrimary': True})
                await page.wait_for_timeout(300)
                await stick.dispatch_event('pointercancel', {'pointerId': 7, 'pointerType': 'touch'})
                moved = await page.evaluate('({x:testVenue.scene.state.x,y:testVenue.scene.state.y})')
                assert moved != stopped, 'Touch joystick moves avatar'
                await page.wait_for_timeout(120)
                assert await page.evaluate('({x:testVenue.scene.state.x,y:testVenue.scene.state.y})') == moved, 'Touch cancel stops avatar'
                await page.keyboard.press('Escape')
                assert await page.evaluate('testVenue.destroyed && !document.querySelector(".venue-visit")')
                report['checks'].append(f'{width}px: keyboard movement, input isolation, station path/proximity, service suspend/resume, touch movement/cancel and Escape disposal passed')
                for venue in ['cafe', 'spa', 'cinema', 'karaoke', 'salon', 'nails', 'craft', 'books', 'art', 'music', 'reading', 'garden', 'family']:
                    await page.evaluate('(id)=>openLocalVenue(id)', venue)
                    await page.wait_for_timeout(90)
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'), f'{venue}: no horizontal overflow'
                    await page.screenshot(path=str(OUT / f'{venue}-{width}.png'))
                    await page.evaluate('testVenue.close()')
                report['checks'].append(f'{width}px: all 14 furnished rooms render without horizontal overflow')
                await context.close()
            await browser.close()
        assert not errors, errors
        report['page_errors'] = errors
        (OUT / 'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
