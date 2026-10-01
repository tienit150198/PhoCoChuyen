"""Money sounds browser check (dev tool, needs `pip install playwright` + chromium): feedback #13.

Runs the real app on a throwaway server (scripts/browser_v04.py). speechSynthesis is stubbed to record utterances;
AudioBufferSourceNode.start is recorded (the recorded "ting" bell: public/audio/sfx/ting.mp3) and lowpass filters
are counted (each character-voice babble makes one). The real server answers every command; the route adds money
to the answer's journey (a wallet row, newest first, as game/journey.py public() sends it) or result.bank, so the
app's api.js -> v4/sounds.js path runs exactly as for a real payday, gift or transfer.

    python scripts/browser_money_sounds.py [--shots DIR]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_v04 import server  # noqa: E402

CMD = """async ([action,payload,career])=>{
  const st=await fetch('/api/state').then(r=>r.json());
  const csrf=window.__csrf||(window.__csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf);
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:career===null?null:(career||st.state.current),action,payload})});
  return r.status;
}"""

STUB = """
window.__spoken=[];window.__plays=[];window.__filters=[];
window.__voices=[{name:'Linh',lang:'vi-VN',localService:true,voiceURI:'Linh',default:false},
                 {name:'Samantha',lang:'en-US',localService:true,voiceURI:'Samantha',default:true}];
window.SpeechSynthesisUtterance=class{constructor(t){this.text=t;this.lang='';this.voice=null;this.rate=1;this.pitch=1;this.volume=1;}};
Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
  getVoices:()=>window.__voices,speaking:false,pending:false,cancel(){},pause(){},resume(){},
  addEventListener(){},removeEventListener(){},
  speak(u){window.__spoken.push({text:u.text,lang:u.lang,voice:u.voice&&u.voice.lang});}}});
const AC=window.AudioContext;window.AudioContext=class extends AC{constructor(...a){super(...a);window.__ctx=this;}};
const start=AudioBufferSourceNode.prototype.start;
AudioBufferSourceNode.prototype.start=function(...a){window.__plays.push({dur:Math.round((this.buffer?.duration||0)*100)/100});return start.apply(this,a);};
const filt=BaseAudioContext.prototype.createBiquadFilter;
BaseAudioContext.prototype.createBiquadFilter=function(){const f=filt.call(this);window.__filters.push(f);return f;};
"""

BABBLES = "window.__filters.filter(f=>f.type==='lowpass'&&Math.abs(f.Q.value-4)<.01).length"
TINGS = "window.__plays.filter(p=>p.dur>0.9).length"   # the bell is 1.1 s; the noise buffer of the paper rustle is 0.25 s


async def main(shots):
    from playwright.async_api import async_playwright
    results, errors = {}, []
    fake = {'rows': [], 'bank': None, 'answered': 0}

    async def route(r):
        resp = await r.fetch()
        body = await resp.json()
        if resp.status == 200 and r.request.headers.get('x-game-csrf'):
            j = (body.get('state') or {}).get('journey')
            if fake['rows'] and isinstance(j, dict):
                j['wallet'] += sum(x['amount'] for x in fake['rows'])
                j['history'] = [dict(x) for x in reversed(fake['rows'])] + j['history']
            if fake['bank'] and isinstance(body.get('result'), dict):
                body['result']['bank'] = list(fake['bank'])
                fake['bank'] = None                   # one command carries the transfer
            fake['answered'] += 1
        await r.fulfill(response=resp, body=json.dumps(body))

    with server() as base:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            page = await browser.new_page(viewport=dict(width=390, height=844))
            # 409: two quick taps raced on the save; api.js adopts the server's state and sends the tap again
            page.on('console', lambda m: m.type == 'error' and '409 (Conflict)' not in m.text and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.add_init_script(STUB)
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=20000)
            await page.evaluate(CMD, ['select_career', {}, 'grocery'])
            await page.evaluate(CMD, ['start_day', {}, 'grocery'])
            await page.evaluate(CMD, ['settings', {'whatsNewSeen': '99.0.0'}, None])   # no "Có gì mới" over the sheet
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=20000)
            await page.route('**/api/command', route)
            day = await page.evaluate("fetch('/api/state').then(r=>r.json()).then(d=>d.state.journey.life_day)")

            async def open_sound():
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate("document.querySelector('[data-action=\"settings\"]').click()")
                await page.wait_for_timeout(300)
                await page.evaluate("document.querySelector('[data-action=\"v4SetTab\"][data-tab=\"sound\"]').click()")
                await page.wait_for_timeout(300)

            async def flip(key, gap=250):
                try:
                    await page.click(f'label.switch-row:has(input[data-setting="{key}"])', timeout=8000)
                except Exception:
                    await page.screenshot(path=str(ROOT / 'browser-money-sounds-failure.png'))
                    print('errors so far:', errors, file=sys.stderr)
                    raise
                await page.wait_for_timeout(gap)

            async def reset():
                await page.evaluate('window.__spoken=[];window.__plays=[];window.__filters=[];document.querySelectorAll(".bank-chip").forEach(e=>e.remove())')

            async def heard():
                return dict(spoken=[x['text'] for x in await page.evaluate('window.__spoken') if x['text'].strip()],
                            tings=await page.evaluate(TINGS))

            async def answered(n):
                """Wait until n more commands were answered (a busy machine may send a tap late)."""
                for _ in range(80):
                    if fake['answered'] >= n:
                        return
                    await page.wait_for_timeout(100)

            async def money(*rows, wait=1700, trigger='detailSfx'):
                """One command per row (the trigger switch, flipped), each answer carrying that much more money."""
                await reset()
                start = fake['answered']
                for amount, kind in rows:
                    fake['rows'].append(dict(day=day, amount=amount, kind=kind, label=f'thử {kind} {len(fake["rows"])}', career=None))
                    await flip(trigger, gap=150)
                await answered(start + len(rows))
                await page.wait_for_timeout(wait)
                return await heard()

            await open_sound()
            # first tap: the bell is fetched (and decoded) once
            await flip('detailSfx')
            await flip('detailSfx')
            await page.wait_for_timeout(600)
            results['toggles'] = await page.eval_on_selector_all(
                '#sheet .switch-row', 'els=>els.map(e=>[e.querySelector("input").dataset.setting,e.querySelector("b").textContent,e.querySelector("input").checked])')
            keys = [k for k, _l, _c in results['toggles']]
            assert {'moneyTing', 'bankVoice', 'npcVoices', 'detailSfx'} <= set(keys), keys
            assert all(c for k, _l, c in results['toggles'] if k in ('moneyTing', 'bankVoice', 'npcVoices', 'detailSfx')), results['toggles']
            if shots:
                Path(shots).mkdir(parents=True, exist_ok=True)
                block = page.locator('#sheet .settings-block:has(input[data-setting="moneyTing"])')
                await block.screenshot(path=str(Path(shots) / 'sound-settings-vi.png'))
                await page.screenshot(path=str(Path(shots) / 'sound-tab-vi.png'))
            results['bell_loaded'] = await page.evaluate("performance.getEntriesByType('resource').filter(e=>e.name.includes('/audio/sfx/ting.mp3')).map(e=>e.name.split('/').pop())")
            assert len(results['bell_loaded']) == 1 and '?v=' in results['bell_loaded'][0], results['bell_loaded']

            # 1. a gift of 50 into the wallet: one "ting ting" (the bell twice) and the amount read in Vietnamese
            results['gift'] = await money((50, 'life'))
            assert results['gift'] == dict(spoken=['Ví vừa nhận thêm 50 xu'], tings=2), results['gift']
            # 2. pay day: salary told apart
            results['salary'] = await money((120, 'salary'))
            assert results['salary'] == dict(spoken=['Đã nhận lương 120 xu'], tings=2), results['salary']
            # 3. a small sum: the bell, no voice
            results['small'] = await money((3, 'life'))
            assert results['small'] == dict(spoken=[], tings=2), results['small']
            # 4. three sums within the window: one ting ting, one line
            results['rush'] = await money((5, 'life'), (5, 'draw'), (5, 'life'))
            assert results['rush'] == dict(spoken=['Ví vừa nhận thêm 15 xu'], tings=2), results['rush']
            # 5. a customer's transfer into the shop (result.bank): as before, now with the recorded bell
            await reset()
            fake['bank'] = [42]
            start = fake['answered']
            await flip('detailSfx')
            await answered(start + 1)
            await page.wait_for_timeout(1700)
            results['shop'] = await heard()
            assert results['shop'] == dict(spoken=['Đã nhận 42 xu'], tings=2), results['shop']
            # 6. "Tiếng ting ting" off: the voice alone
            await flip('moneyTing')
            results['ting_off'] = await money((60, 'life'))
            assert results['ting_off'] == dict(spoken=['Ví vừa nhận thêm 60 xu'], tings=0), results['ting_off']
            await flip('moneyTing')
            # 7. "Giọng đọc số tiền" off: the bell alone
            await flip('bankVoice')
            results['voice_off'] = await money((60, 'life'))
            assert results['voice_off'] == dict(spoken=[], tings=2), results['voice_off']
            await flip('bankVoice')
            # 8. spending: nothing
            fake['rows'].append(dict(day=day, amount=-30, kind='life', label='thử mua', career=None))
            await reset()
            start = fake['answered']
            await flip('detailSfx')
            await answered(start + 1)
            await page.wait_for_timeout(1700)
            results['spend'] = await heard()
            assert results['spend'] == dict(spoken=[], tings=0), results['spend']
            # 9. global sound off: nothing at all
            await flip('sound')
            results['muted'] = await money((80, 'life'))
            assert results['muted'] == dict(spoken=[], tings=0), results['muted']
            await flip('sound')

            # 10. a story scene: the first NPC line babbles once; the same line again does not; a new line does
            scene = """([name,text])=>{let d=document.getElementById('sfxScene');if(!d){d=document.createElement('dialog');d.id='sfxScene';document.body.append(d);}
              d.innerHTML=`<div class="jr-lines"><div class="jr-line"><span class="jr-face">👵</span><div class="jr-bubble"><b>${name}</b><p>${text}</p></div></div></div>`;if(!d.open)d.show();}"""
            await page.click('#sheet h3')                # a tap: the context runs again after "sound" came back on
            for _ in range(30):
                if await page.evaluate("window.__ctx&&window.__ctx.state") == 'running':
                    break
                await page.wait_for_timeout(100)
            await reset()
            await page.evaluate(scene, ['Bà Tám', 'Con về rồi đó hả?'])
            await page.wait_for_timeout(300)
            first = await page.evaluate(BABBLES)
            await page.evaluate(scene, ['Bà Tám', 'Con về rồi đó hả?'])
            await page.wait_for_timeout(300)
            same = await page.evaluate(BABBLES)
            await page.evaluate(scene, ['Bà Tám', 'Ăn cơm chưa con?'])
            await page.wait_for_timeout(300)
            new = await page.evaluate(BABBLES)
            results['scene_babble'] = [first, same, new]
            assert results['scene_babble'] == [1, 1, 2], results['scene_babble']
            await page.evaluate("document.getElementById('sfxScene').close()")
            await page.wait_for_timeout(200)
            await flip('npcVoices')
            await reset()
            await page.evaluate(scene, ['Chú Ba', 'Chào cháu!'])
            await page.wait_for_timeout(300)
            results['scene_babble_off'] = await page.evaluate(BABBLES)
            assert results['scene_babble_off'] == 0, results['scene_babble_off']
            await page.evaluate("document.getElementById('sfxScene').close()")
            await flip('npcVoices')

            # 11. English UI: English text, English voice
            fake['rows'].clear()
            await page.unroute('**/api/command')
            await page.evaluate(CMD, ['settings', {'lang': 'en'}, None])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=20000)
            await page.route('**/api/command', route)
            await open_sound()
            await flip('detailSfx')
            await flip('detailSfx')
            if not await page.is_checked('input[data-setting="detailSfx"]'):
                await flip('detailSfx')                  # the triggers above left it off: back to the default
            await page.wait_for_timeout(500)
            if shots:
                block = page.locator('#sheet .settings-block:has(input[data-setting="moneyTing"])')
                await block.screenshot(path=str(Path(shots) / 'sound-settings-en.png'))
            results['english'] = await money((50, 'life'))
            spoken = await page.evaluate('window.__spoken')
            assert results['english'] == dict(spoken=['Your wallet just received 50 coins'], tings=2), results['english']
            assert spoken[-1]['voice'] == 'en-US', spoken
            await browser.close()
    results['console_errors'] = errors
    print(json.dumps(results, ensure_ascii=False, indent=1))
    assert not errors, errors
    print('MONEY SOUNDS OK')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default='')
    asyncio.run(main(ap.parse_args().shots))
