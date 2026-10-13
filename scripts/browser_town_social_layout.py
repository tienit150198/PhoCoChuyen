"""Real Phaser/HUD/social layout regression; only the live transport is local.

Run: python scripts/browser_town_social_layout.py
No game server or database required. Screenshots go to output/playwright/.
"""
import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/town-social-layout'
MODULE = r"""
import {PhaserWorld} from '/js/isometric/phaser-world.js';
import {bootIsometricShell,isometricAction} from '/js/isometric-shell.js';
import {bootIsometricMovement} from '/js/isometric-movement.js';
import {createTownSocial} from '/js/isometric-social.js';
document.querySelector('#loading').remove();document.querySelector('#app').hidden=false;
document.documentElement.dataset.game='isometric';
document.documentElement.dataset.layout=innerWidth<=699?'phone':innerWidth<=1100?'tablet':'desktop';
document.documentElement.dataset.orientation=innerWidth>innerHeight?'landscape':'portrait';
const state={name:'Lan',journey:{intro:true,gender:'female'},settings:{reduceMotion:true},careers:{}};
const world=new PhaserWorld(document.querySelector('#world'),()=>{});
world.update(state,{catalogue:[]});await world.ready;
const env={api:{state,content:{catalogue:[]}},world,ui:{},bootLive(){},act(){}};
bootIsometricShell(env);bootIsometricMovement(env);
document.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(b)isometricAction(b.dataset.action,b.dataset,b,env);});
const listeners=new Map(),sent=[];
const transport={state:'open',on(t,f){listeners.set(t,f);return()=>listeners.delete(t)},send(f){sent.push(f);return true}};
const social=createTownSocial(env,{transport});
const at=world.getPresence();
const snapshot={enabled:true,active:true,room:'layout',me:'me',peers:[{pid:'peer',name:'Minh',x:at.x,y:at.y}]};
social.update(snapshot);
// Keep the speech anchor on screen while using the real projected player position.
window.fixture={world,social,sent,snapshot,emit:(t,f)=>listeners.get(t)?.(f)};
window.ready=true;
"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith('/layout'):
            html = (ROOT / 'public/index.html').read_text(encoding='utf8')
            html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.S)
            html = html.replace('rel="preload" as="style"', 'rel="stylesheet"')
            html = html.replace('</head>', '<link rel="stylesheet" href="/css/isometric.css"></head>')
            html = html.replace('</body>', f'<script type="module">{MODULE}</script></body>')
            body = html.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()


async def unobstructed(page, selector):
    return await page.locator(selector).evaluate('''e=>{
      const r=e.getBoundingClientRect();
      const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
      return {ok:e===hit||e.contains(hit),rect:r.toJSON(),hit:hit?.outerHTML.slice(0,180)};
    }''')


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'public')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report, errors = [], []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for width, height in [(390,844),(320,568),(844,390),(1280,860),(768,1024),(390,500)]:
                page = await browser.new_page(viewport=dict(width=width,height=height))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(f'http://127.0.0.1:{server.server_port}/layout?isometricdebug=1')
                await page.wait_for_function('window.ready===true')
                await page.wait_for_function("!!document.querySelector('link[data-lazy-css]').sheet")
                camera = '[data-action="isoCamera"]'
                toggle = '[data-social="toggle"]'
                await page.screenshot(path=str(OUT/f'{width}x{height}-closed.png'))
                hit = await unobstructed(page,camera)
                assert hit['ok'], (width,height,'Camera covered',hit)
                assert (await unobstructed(page,toggle))['ok']
                await page.locator(toggle).click()
                await page.screenshot(path=str(OUT/f'{width}x{height}-panel.png'))
                assert (await unobstructed(page,camera))['ok'], 'Open chat covers camera'
                await page.locator(camera).click()
                await page.screenshot(path=str(OUT/f'{width}x{height}-chat-and-zoom.png'))
                for action in ['isoZoomIn','isoZoomOut','isoRecenter','isoOverview']:
                    hit = await unobstructed(page,f'[data-action="{action}"]')
                    assert hit['ok'], (width,height,'Zoom covered',action,hit)
                    assert min(hit['rect']['width'],hit['rect']['height']) >= 44
                assert await page.evaluate('''()=>{
                  const social=[...document.querySelectorAll('.town-social-toggle,.town-social-panel')].map(e=>e.getBoundingClientRect());
                  const camera=[...document.querySelectorAll('.iso-camera-toggle,.iso-camera-options')].map(e=>e.getBoundingClientRect());
                  return social.every(a=>a.top>=0&&a.left>=0&&a.right<=innerWidth&&camera.every(b=>a.bottom<=b.top||a.top>=b.bottom||a.right<=b.left||a.left>=b.right));
                }'''), 'Nearby speech and camera rectangles overlap or escape viewport'
                before = await page.evaluate('fixture.world.debug().camera.zoom')
                await page.locator('[data-action="isoZoomIn"]').click()
                assert await page.evaluate('fixture.world.debug().camera.zoom') > before
                await page.locator('[data-action="isoZoomOut"]').click()
                await page.locator('[data-action="isoRecenter"]').click()
                before = await page.evaluate('fixture.world.getPresence()')
                await page.locator('[data-social="draft"]').fill('wasd Xin chào!')
                await page.locator('[data-social="draft"]').press('ArrowLeft')
                assert await page.evaluate('fixture.world.getPresence()') == before
                await page.locator('[data-social="send"]').click()
                assert await page.evaluate('fixture.sent.at(-1).t') == 'town_say'
                await page.locator('[data-social="emote-👋"]').click()
                assert await page.evaluate('fixture.sent.at(-1).t') == 'town_emote'
                await page.locator('[data-social="draft"]').press('Escape')
                assert await page.locator('[data-social="panel"]').is_hidden()
                await page.locator(camera).click()
                await page.evaluate("fixture.emit('town_said',{room:'layout',pid:'me',name:'Lan',id:1,ch:'iso-talk:layout',text:'Xin chào!'})")
                await page.locator('[data-social="reactions-me"] button').first.click()
                assert await page.evaluate('fixture.sent.at(-1).t') == 'react'
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                report.append(dict(width=width,height=height,zoom=True,chat=True,keyboard=True,reaction=True))
                await page.close()
            await browser.close()
        assert not errors, errors
        (OUT/'report.json').write_text(json.dumps(dict(checks=report,errors=errors),indent=2),encoding='utf8')
        print(json.dumps(report))
    finally:
        server.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
