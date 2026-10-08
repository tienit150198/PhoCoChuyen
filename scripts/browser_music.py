"""🎵 Background music smoke (owner report 08/10/2026 "nhạc lúc nghe được lúc không"): a browser check of the real app
(dev tool, needs `pip install playwright` + chromium/webkit).

Runs the app on a throwaway story-mode server, turns the save's "Nhạc nền" on in its database, then in Chromium:
nothing is fetched before the first tap; the first tap starts the page's AudioContext and the career's song (a
looping buffer source); hidden → suspended, shown → running again with the same single song, no new download; an
iPhone without navigator.audioSession (platform faked: iOS 15–16.3) also plays the silent <audio> keeper.
Playwright's WebKit on Windows has no Web Audio: there the page must load and take taps with music on without an
error; the keeper's silent WAV (audio.js silence()) is tried in WebKit's media element (Playwright's Windows build
plays no blob: media at all, so it is only reported there).

    python scripts/browser_music.py [--engine chromium|webkit]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

ENGINES = [sys.argv[sys.argv.index('--engine') + 1]] if '--engine' in sys.argv else ['chromium', 'webkit']

# Counts the songs started (buffer sources longer than 5 s) and keeps the page's AudioContext.
PROBE = """(()=>{
  const C=window.AudioContext||window.webkitAudioContext;if(!C)return;
  const P=window.__probe={ctx:null,songs:[],music:[]};
  const make=C.prototype.createBufferSource;
  C.prototype.createBufferSource=function(){P.ctx=this;const s=make.call(this),start=s.start;
    s.start=function(...a){if(this.buffer&&this.buffer.duration>5)P.songs.push({loop:this.loop,dur:this.buffer.duration,on:true,src:this});return start.apply(this,a);};
    const stop=s.stop;s.stop=function(...a){for(const x of P.songs)if(x.src===this)x.on=false;return stop.apply(this,a);};return s;};
  const f=window.fetch;window.fetch=function(u,...r){if(String(u).includes('/music/'))P.music.push(String(u));return f.call(this,u,...r);};
  if(window.__fakeIphone){Object.defineProperty(Navigator.prototype,'platform',{get:()=>'iPhone'});Object.defineProperty(Navigator.prototype,'maxTouchPoints',{get:()=>5});
    try{delete Navigator.prototype.audioSession;}catch{}
    const play=HTMLMediaElement.prototype.play;P.keeper=[];HTMLMediaElement.prototype.play=function(){P.keeper.push(this);return play.call(this);};}
})();"""
STATE = """()=>{const P=window.__probe;return {state:P.ctx?.state||'none',songs:P.songs.filter(s=>s.on).map(s=>({loop:s.loop,dur:Math.round(s.dur)})),
  music:P.music.length,keeper:(P.keeper||[]).map(a=>({paused:a.paused,err:a.error?.code||0,src:String(a.src).slice(0,22)}))}}"""


def music_on(db: str, token: str) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        s['settings']['music'] = True
        s['settings']['musicVolume'] = 45
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


async def run(pw, engine, base, db, iphone=False):
    browser = await getattr(pw, engine).launch()
    ctx = await browser.new_context(viewport=dict(width=390, height=844))
    if iphone:
        await ctx.add_init_script('window.__fakeIphone=1')
    await ctx.add_init_script(PROBE)
    page = await ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    await page.goto(base)
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
    music_on(db, token)
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_timeout(1500)
    before = await page.evaluate(STATE)
    assert before['music'] == 0, f'{engine}: music fetched before a tap: {before}'
    await page.mouse.click(5, 420)   # a tap on the page
    await page.wait_for_timeout(300)
    await page.mouse.click(5, 420)
    for _ in range(40):
        st = await page.evaluate(STATE)
        if st['songs'] and any(s['loop'] for s in st['songs']):
            break
        await page.wait_for_timeout(250)
    st = await page.evaluate(STATE)
    print(engine, 'iphone' if iphone else '', 'after tap:', st)
    assert st['state'] == 'running', st
    assert len([s for s in st['songs'] if s['loop']]) == 1, st
    if iphone:
        assert st['keeper'] and not st['keeper'][-1]['paused'] and st['keeper'][-1]['src'].startswith('blob:') and not st['keeper'][-1]['err'], st
    await page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
    await page.wait_for_timeout(500)
    hid = await page.evaluate(STATE)
    print(engine, 'hidden:', hid)
    assert hid['state'] == 'suspended', hid
    await page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))")
    await page.wait_for_timeout(800)
    back = await page.evaluate(STATE)
    print(engine, 'shown:', back)
    assert back['state'] == 'running', back
    assert len([s for s in back['songs'] if s['loop']]) == 1, back
    assert back['music'] == st['music'], 'no new download on return'
    assert not errors, errors
    await browser.close()


KEEPER_WAV = """async()=>{const a=document.createElement('audio');a.loop=true;a.src=(%s)();
  try{await a.play();}catch(e){return {err:String(e)};}await new Promise(r=>setTimeout(r,1500));
  const out={paused:a.paused,t:a.currentTime,dur:a.duration,err:a.error?.code||0};a.pause();return out;}"""


async def webkit_media(pw, base, db):
    import re
    src = (ROOT / 'public' / 'js' / 'audio.js').read_text(encoding='utf-8')
    fn = re.search(r'function silence\(\)\{.*?\r?\n\}', src, re.S).group(0)
    browser = await pw.webkit.launch()
    ctx = await browser.new_context(viewport=dict(width=390, height=844))
    page = await ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    await page.goto(base, wait_until='domcontentloaded')
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
    music_on(db, token)
    await page.goto(base, wait_until='domcontentloaded')
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    for _ in range(3):
        await page.mouse.click(5, 420)
        await page.wait_for_timeout(300)
    played = await page.evaluate(KEEPER_WAV % fn)
    print('webkit keeper wav:', played)
    assert not errors, errors
    if 'NotSupported' in str(played.get('err')):
        # Playwright's WebKit for Windows plays no blob: media at all (an MP3 blob fails the same way); Chromium
        # played the keeper above, and iPhone Safari plays blob: audio.
        print('webkit: this build plays no blob: media; keeper not checked here')
        return await browser.close()
    assert not played.get('err') and not played['paused'] and played['t'] > 0.3 and abs(played['dur'] - 1) < .05, played
    await browser.close()


async def main():
    from playwright.async_api import async_playwright
    with server() as (base, db):
        async with async_playwright() as pw:
            if 'chromium' in ENGINES:
                await run(pw, 'chromium', base, db)
                await run(pw, 'chromium', base, db, iphone=True)
            if 'webkit' in ENGINES:
                await webkit_media(pw, base, db)
    print('music smoke OK')


if __name__ == '__main__':
    asyncio.run(main())
