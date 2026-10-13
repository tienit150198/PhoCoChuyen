"""Two authenticated browser contexts on disposable local game/live services."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_live_chat import servers, API, PW
from browser_business_licenses import mutate

OUT = ROOT / 'output/playwright/town-social'


async def run():
    from playwright.async_api import async_playwright
    os.environ['LIVE_TOWN'] = '1'
    OUT.mkdir(parents=True, exist_ok=True)
    errors, checks = [], []
    with tempfile.TemporaryDirectory(prefix='mnl-town-social-') as tmp, servers(tmp) as (base, namespace, log):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            pages = []
            try:
                for i, (name, width, height) in enumerate((('Lan', 1280, 860), ('Minh', 390, 844))):
                    # The installed Playwright's wait_for_function uses eval internally.
                    ctx = await browser.new_context(viewport=dict(width=width, height=height), bypass_csp=True)
                    page = await ctx.new_page()
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    pages.append(page)
                    await page.goto(base)
                    await page.wait_for_selector('#app:not([hidden])', timeout=60000)
                    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                    def seed(s):
                        s['name'] = name
                        s['journey'].update(intro=True, gender='female', news=[])
                        s['settings'].update(tutorialDone=True, whatsNewSeen='2.3.0')
                        s['journey']['interface'] = dict(newInterface=True, interfacePromptSeen=True)
                    mutate(namespace, token, seed)
                    result = await page.evaluate(API, ['/api/account/register', dict(username=f'town_social_{i}', password=PW, confirm=PW, display=name)])
                    assert result['status'] == 200, result
                    await page.goto(base + '/?isometricdebug=1')
                    await page.wait_for_function('!!window.__isoWorld', timeout=60000)
                    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                    if await page.evaluate('__isoWorld.mode') != 'town':
                        await page.locator('[data-action="isoTown"]').first.click()
                    await page.wait_for_selector('[data-social="dock"]:not([hidden])', timeout=30000)
                    print('ready', name, flush=True)
                a, b = pages
                # Transport is the real authenticated module loaded by the app's import map.
                for p in pages:
                    await p.evaluate("async()=>{const {live}=await import('/js/v4/live.js');window.__socialLive=live;}")
                pa, pb = await a.evaluate('__socialLive.me.pid'), await b.evaluate('__socialLive.me.pid')
                await a.locator('[data-social="toggle"]').click()
                await b.locator('[data-social="toggle"]').click()
                await a.wait_for_selector(f'[data-social="peer-{pb}"]')
                await b.wait_for_selector(f'[data-social="peer-{pa}"]')
                await b.locator('[data-social="close"]').click()
                await a.locator('[data-social="draft"]').fill('Chào Minh, cùng đi dạo nhé!')
                await a.locator('[data-social="send"]').click()
                await b.wait_for_selector(f'[data-social="bubble-{pa}"]:not([hidden])')
                assert 'Chào Minh' in await b.locator(f'[data-social="bubble-{pa}"]').inner_text()
                await b.locator(f'[data-social="reactions-{pa}"] button').first.click()
                await a.wait_for_function('(pid)=>document.querySelector(`[data-social="counts-${pid}"]`)?.textContent.includes("❤️ 1")', arg=pa)
                checks.append('Real nearby speech, self acknowledgement, peer reaction')
                await a.locator('[data-social="close"]').click()
                print('speech and reaction passed', flush=True)
                await b.screenshot(path=str(OUT / 'phone-speech.png'))
                await a.screenshot(path=str(OUT / 'desktop-speech.png'))
                # A real avatar tap opens its card (use its projected body point).
                at = await a.evaluate('(pid)=>__isoWorld.getSocialAnchor(pid)', pb)
                assert at, 'Peer is onscreen'
                zoom = await a.evaluate('__isoWorld.debug().camera.zoom')
                await a.mouse.click(at['x'], at['y'] + 65 * zoom)
                await a.wait_for_selector('[data-social="greet"]')
                await a.locator('[data-social="greet"]').click()
                await b.wait_for_function('(pid)=>document.querySelector(`[data-social="bubble-${pid}"]`)?.textContent.includes("👋")', arg=pa)
                checks.append('Avatar picking, nearby player card and targeted wave')
                await a.locator('[data-social="friend"]').click()
                await a.wait_for_function('document.querySelector("[data-social=status]")?.textContent.includes("lời mời")')
                check = await b.evaluate(API, ['/api/marriage', None])
                incoming = check['data']['friends']['incoming']
                assert incoming, check
                await b.evaluate(API, ['/api/marriage/friend_respond', dict(id=incoming[0]['id'], answer='accept')])
                await a.locator(f'[data-social="peer-{pb}"]').click()
                await a.wait_for_selector('[data-social="dm"]')
                await a.locator('[data-social="dm"]').click()
                await a.wait_for_selector('#townChat[open]')
                checks.append('Friend request through game API and private chat entry')
                await a.evaluate("document.querySelector('#townChat').close()")
                # Keyboard typing must not move the avatar.
                await a.locator('[data-social="toggle"]').click()
                before = await a.evaluate('__isoWorld.getPresence()')
                await a.locator('[data-social="draft"]').fill('wasd')
                await a.locator('[data-social="draft"]').press('ArrowLeft')
                await a.wait_for_timeout(150)
                assert await a.evaluate('__isoWorld.getPresence()') == before
                checks.append('Composer arrow keys do not drive the avatar')
                await b.locator('[data-social="toggle"]').click()
                await b.locator(f'[data-social="peer-{pa}"]').click()
                await b.wait_for_selector('[data-social="block"]')
                await b.locator('[data-social="block"]').click()
                await b.wait_for_function('(pid)=>!document.querySelector(`[data-social="peer-${pid}"]`)', arg=pa)
                checks.append('Block removes player interaction immediately')
                for p, name in ((a, 'desktop-panel'), (b, 'phone-panel')):
                    await p.screenshot(path=str(OUT / (name + '.png')))
                    assert await p.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'horizontal overflow'
                # A fresh page under the application's real CSP must also load the module.
                normal = await browser.new_context(storage_state=await a.context.storage_state())
                plain = await normal.new_page()
                plain.on('pageerror', lambda e: errors.append(str(e)))
                await plain.goto(base)
                await plain.wait_for_selector('[data-social="dock"]:not([hidden])', timeout=30000)
                checks.append('Fresh page loads social controls under normal CSP')
                await normal.close()
                assert not errors, errors
            except Exception:
                for i, p in enumerate(pages):
                    await p.screenshot(path=str(OUT / f'failure-{i}.png'))
                    (OUT / f'failure-{i}.txt').write_text(await p.locator('body').inner_text(), encoding='utf8')
                (OUT / 'live.log').write_text(Path(log).read_text(encoding='utf8', errors='replace'), encoding='utf8')
                raise
            finally:
                await browser.close()
                (OUT / 'report.json').write_text(json.dumps(dict(checks=checks, errors=errors), ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(checks=checks, errors=errors), ensure_ascii=False))


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run())
