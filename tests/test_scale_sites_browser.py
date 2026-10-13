"""Optional real Chromium + authenticated live sockets, desktop and phone.
Run: RUN_SCALE_SITE_BROWSER=1 TEST_DATABASE_URL=... python -m pytest tests/test_scale_sites_browser.py -q
"""
import asyncio
import sys
import os
import unittest
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tests.live_support import LiveCase
from tests import test_live_scale_sites as site_tests


@unittest.skipUnless(os.environ.get('RUN_SCALE_SITE_BROWSER') == '1', 'opt-in real Chromium: RUN_SCALE_SITE_BROWSER=1')
class ScaleSitesBrowser(LiveCase):
    cfg_extra = dict(town=True)
    save_site = site_tests.ScaleSiteSockets.save_site

    async def test_desktop_phone_walk_social_private_and_reconnect(self):
        from playwright.async_api import async_playwright
        public = Path(__file__).resolve().parents[1] / 'public'
        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(public)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        self.cfg.origins = frozenset({base})
        owner_token, sid = self.account('Lan')
        guest_token, _ = self.account('Khách')
        self.save_site(sid, False)
        code = f'{self.pid(sid)}:grocery:base'
        errors=[]
        fixture='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><body><div id="stage"></div><dialog id="sheet"><button id="sheet-close" onclick="this.parentElement.close()">Đóng bảng</button></dialog><script type="module">
          import {live,liveBoot} from '/js/v4/live.js';
          import {openScaleSiteGuest} from '/js/v4/scale-site.js';
          import {createTownPresence} from '/js/isometric-town.js';
          const state={name:'Lan',current:'grocery',journey:{gender:'female'},careers:{grocery:{scale:{sites:[{id:'base',name:'Tiệm Lan'}]}}}};
          const api=new EventTarget();Object.assign(api,{state,live:{url:'WS_URL'}});
          window.toasts=[];window.env={api,ui:{},toast:t=>toasts.push(t),closeSheet:()=>document.querySelector('#sheet').close(),openSheet:()=>document.querySelector('#sheet').showModal(),world:{mode:'town',getPresence:()=>({x:6,y:6,direction:'ne'}),setRemotePlayers:()=>{},setSocialEnabled:()=>{}}};
          window.live=live;window.frames=[];live.on('*',f=>frames.push(f));liveBoot(env);window.bridge=createTownPresence(env).start();
          window.enter=async()=>window.visit=await openScaleSiteGuest(env,'SITE_CODE');
        </script>'''.replace('WS_URL',f'ws://127.0.0.1:{self.port}/live').replace('SITE_CODE',code)
        main_loop=asyncio.get_running_loop()
        async def on_main(coro):
            return await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro,main_loop))
        async def browser_test():
          async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True)
            async def page_for(token,width,height):
                context=await browser.new_context(viewport=dict(width=width,height=height),has_touch=width<600)
                await context.add_cookies([dict(name='mnl_session',value=token,url=base)])
                page=await context.new_page();page.set_default_timeout(8000);page.on('pageerror',lambda e:errors.append(str(e)))
                await page.route(base+'/fixture',lambda r:r.fulfill(status=200,content_type='text/html',body=fixture))
                await page.goto(base+'/fixture');await page.wait_for_function("live.state==='open'")
                await page.wait_for_function("frames.some(f=>f.t==='town_room'&&f.map==='iso-town-v1')")
                return page
            owner=await page_for(owner_token,1280,900)
            guest=await page_for(guest_token,390,844)
            await asyncio.wait_for(owner.evaluate('enter()'),15);await owner.locator('.venue-visit[open]').wait_for()
            await asyncio.wait_for(guest.evaluate('enter()'),15);self.assertEqual(await guest.locator('.venue-visit').count(),0)
            self.assertTrue(await guest.evaluate('toasts.some(t=>t.includes("đón khách"))'))
            self.save_site(sid,True)
            await asyncio.wait_for(guest.evaluate('enter()'),15);await guest.locator('.venue-visit[open]').wait_for()
            await owner.wait_for_function("document.querySelector('.scale-site-social select').options.length===2")
            self.assertTrue(await guest.locator('.scale-site-social').evaluate('(e)=>e.scrollWidth<=e.clientWidth'))
            await guest.get_by_label('Người ở gần').select_option(self.pid(sid))
            await guest.get_by_role('button',name='Xem bạn',exact=True).click()
            await guest.wait_for_function("frames.some(f=>f.t==='town_card')")
            # Typing letters used by walking must remain typing, not movement.
            before=await owner.evaluate('({x:visit.scene.state.x,y:visit.scene.state.y})')
            await owner.get_by_label('Lời nhắn trong cơ sở').fill('wasd xin chào')
            await owner.get_by_role('button',name='Gửi',exact=True).click()
            await guest.get_by_role('log').filter(has_text='wasd xin chào').wait_for()
            self.assertEqual(before,await owner.evaluate('({x:visit.scene.state.x,y:visit.scene.state.y})'))
            await guest.get_by_role('button',name='Thả biểu cảm 👋',exact=True).click()
            await owner.get_by_role('log').filter(has_text='👋').wait_for()
            # Desktop keyboard movement is real and collision bounded.
            await owner.locator('canvas').focus();await owner.keyboard.down('ArrowRight');await asyncio.sleep(.4);await owner.keyboard.up('ArrowRight')
            after=await owner.evaluate('({x:visit.scene.state.x,y:visit.scene.state.y})')
            self.assertNotEqual(before,after)
            # Phone tap on floor moves within the actual modal canvas.
            canvas=guest.locator('canvas');await canvas.scroll_into_view_if_needed();box=await canvas.bounding_box()
            x,y=320+(260-310)*.67,76+(260+310)*.38
            await guest.touchscreen.tap(box['x']+x/640*box['width'],box['y']+y/470*box['height'])
            await guest.wait_for_function('visit.scene.state.x>245')
            # Room reconnect after a real socket close restores the same authorized site.
            guest_pid=await guest.evaluate('live.me.pid')
            conn=next(c for c in self.app.hub.conns if c.player.pid==guest_pid)
            await on_main(conn.ws.close(code=1012))
            await guest.wait_for_function("frames.filter(f=>f.t==='town_room'&&f.map==='scale-site-v1').length>=2",timeout=15000)
            self.assertEqual(await guest.locator('.venue-visit[open]').count(),1)
            # Owner walks to management; the panel returns to the same walkable room.
            await owner.locator('[data-station=management]').click()
            await owner.locator('#sheet[open]').wait_for(timeout=10000)
            await owner.locator('#sheet-close').click();await owner.locator('.venue-visit[open]').wait_for()
            out=Path(__file__).resolve().parents[1]/'output'/'playwright'/'scale-sites';out.mkdir(parents=True,exist_ok=True)
            await owner.screenshot(path=str(out/'desktop.png'))
            await guest.get_by_label('Lời nhắn trong cơ sở').scroll_into_view_if_needed()
            await guest.screenshot(path=str(out/'phone-social.png'))
            # Idle visitor is evicted, local modal closes, outdoor presence returns.
            self.save_site(sid,False);self.app.by_name['town']._sites_at=0
            await on_main(self.app.by_name['town'].tick(__import__('time').monotonic()))
            await guest.wait_for_function("!document.querySelector('.venue-visit')")
            await guest.wait_for_function("frames.filter(f=>f.t==='town_room'&&f.map==='iso-town-v1').length>=2")
            self.assertEqual(errors,[])
            await browser.close()
        def run_browser():
            loop=asyncio.ProactorEventLoop() if sys.platform=='win32' else asyncio.new_event_loop()
            try: loop.run_until_complete(browser_test())
            finally: loop.close()
        try:
            await asyncio.wait_for(asyncio.to_thread(run_browser),90)
        finally:
            server.shutdown();server.server_close()
