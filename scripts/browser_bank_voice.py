"""Bank speaker browser check (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway server (scripts/browser_v04.py).

speechSynthesis is stubbed to record utterances. The real server answers every command;
for chosen commands the route adds result.bank (what grocery gr_verify etc. send; the server
side is covered by tests/test_bank_speaker.py) so the app's api.js -> v4/sounds.js path runs.
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_v04 import server  # noqa: E402

STUB = """
window.__spoken=[];
window.__voices=[{name:'Linh',lang:'vi-VN',localService:true,voiceURI:'Linh',default:false},
                 {name:'Samantha',lang:'en-US',localService:true,voiceURI:'Samantha',default:true}];
window.SpeechSynthesisUtterance=class{constructor(t){this.text=t;this.lang='';this.voice=null;this.rate=1;this.pitch=1;this.volume=1;}};
Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
  getVoices:()=>window.__voices,speaking:false,pending:false,cancel(){},pause(){},resume(){},
  addEventListener(){},removeEventListener(){},
  speak(u){window.__spoken.push({text:u.text,lang:u.lang,voice:u.voice&&u.voice.lang,rate:u.rate});}}});
"""

CMD = """async ([action,payload,career])=>{
  const st=await fetch('/api/state').then(r=>r.json());
  const csrf=window.__csrf||(window.__csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf);
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:career||st.state.current,action,payload})});
  return r.status;
}"""


async def main():
    from playwright.async_api import async_playwright
    results, errors = {}, []
    inject = {'amounts': None}

    async def route(r):
        resp = await r.fetch()
        body = await resp.json()
        if inject['amounts'] and r.request.headers.get('x-game-csrf') and resp.status == 200 and isinstance(body.get('result'), dict):
            body['result']['bank'] = list(inject['amounts'])
        await r.fulfill(response=resp, body=json.dumps(body))

    with server() as base:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            page = await browser.new_page(viewport=dict(width=390, height=844))
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.add_init_script(STUB)
            await page.goto(base)
            await page.wait_for_selector('#app:not([hidden])', timeout=20000)
            await page.evaluate(CMD, ['select_career', {}, 'grocery'])
            await page.evaluate(CMD, ['start_day', {}, 'grocery'])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=20000)
            await page.route('**/api/command', route)

            async def open_sound():
                await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
                await page.evaluate("document.querySelector('[data-action=\"settings\"]').click()")
                await page.wait_for_timeout(300)
                await page.evaluate("document.querySelector('[data-action=\"v4SetTab\"][data-tab=\"sound\"]').click()")
                await page.wait_for_timeout(300)

            async def flip(key, times=1, gap=0):
                for _ in range(times):
                    await page.click(f'label.switch-row:has(input[data-setting="{key}"])')
                    await page.wait_for_timeout(gap or 250)

            async def spoken():
                return [x for x in await page.evaluate('window.__spoken') if x['text'].strip()]

            async def reset():
                await page.evaluate('window.__spoken=[];document.querySelectorAll(".bank-chip").forEach(e=>e.remove())')

            await open_sound()
            labels = await page.eval_on_selector_all('#sheet .switch-row b', 'els=>els.map(e=>e.textContent)')
            results['toggles'] = labels
            # 1. one transfer -> "Đã nhận 42 xu" with the Vietnamese voice
            await reset()
            inject['amounts'] = [42]
            await flip('detailSfx')
            inject['amounts'] = None
            await page.wait_for_timeout(1500)
            one = await spoken()
            results['single'] = one
            assert len(one) == 1 and one[0]['text'] == 'Đã nhận 42 xu' and one[0]['lang'] == 'vi-VN' and one[0]['voice'] == 'vi-VN', one
            # 2. three payments within the window -> one coalesced announcement
            await reset()
            inject['amounts'] = [42]
            await flip('detailSfx', times=3, gap=120)
            inject['amounts'] = None
            await page.wait_for_timeout(1800)
            many = await spoken()
            results['coalesced'] = many
            assert len(many) == 1 and many[0]['text'] == 'Đã nhận 3 khoản, 126 xu', many
            # and two payments in one command (day close pickups) -> one announcement too
            await reset()
            inject['amounts'] = [30, 12]
            await flip('detailSfx')
            inject['amounts'] = None
            await page.wait_for_timeout(1500)
            results['one_command_two_payments'] = await spoken()
            assert [x['text'] for x in results['one_command_two_payments']] == ['Đã nhận 2 khoản, 42 xu']
            # 3. switch off -> nothing, no chip
            await flip('bankVoice')
            await page.wait_for_timeout(300)
            off = await page.evaluate("fetch('/api/state').then(r=>r.json()).then(d=>d.state.settings.bankVoice)")
            assert off is False, off
            await reset()
            inject['amounts'] = [42]
            await flip('detailSfx')
            inject['amounts'] = None
            await page.wait_for_timeout(1500)
            results['off'] = dict(spoken=await spoken(), chips=await page.eval_on_selector_all('.bank-chip', 'els=>els.length'))
            assert results['off'] == dict(spoken=[], chips=0), results['off']
            await flip('bankVoice')
            await page.wait_for_timeout(300)
            # 4. global sound off -> nothing
            await flip('sound')
            await page.wait_for_timeout(300)
            await reset()
            inject['amounts'] = [42]
            await flip('detailSfx')
            inject['amounts'] = None
            await page.wait_for_timeout(1500)
            results['muted'] = await spoken()
            assert results['muted'] == [], results['muted']
            await flip('sound')
            await page.wait_for_timeout(300)
            # 5. no Vietnamese voice -> no speech in another language, a chip instead
            await page.evaluate("window.__voices=window.__voices.filter(v=>!v.lang.startsWith('vi'))")
            await reset()
            inject['amounts'] = [42]
            await flip('detailSfx')
            inject['amounts'] = None
            await page.wait_for_timeout(1000)
            chips = await page.eval_on_selector_all('.bank-chip', 'els=>els.map(e=>e.textContent)')
            results['no_vi_voice'] = dict(spoken=await spoken(), chips=chips)
            assert results['no_vi_voice'] == dict(spoken=[], chips=['🔔 +42 xu']), results['no_vi_voice']
            # 6. English UI -> "Received 42 coins" in English
            await page.evaluate(CMD, ['settings', {'lang': 'en'}])
            await page.reload()
            await page.wait_for_selector('#app:not([hidden])', timeout=20000)
            await open_sound()
            await reset()
            inject['amounts'] = [42]
            await flip('detailSfx')
            inject['amounts'] = None
            await page.wait_for_timeout(1500)
            results['english'] = await spoken()
            assert len(results['english']) == 1 and results['english'][0]['text'] == 'Received 42 coins' and results['english'][0]['voice'] == 'en-US', results['english']
            results['english_toggles'] = await page.eval_on_selector_all('#sheet .switch-row b', 'els=>els.map(e=>e.textContent)')
            await page.evaluate(CMD, ['settings', {'lang': 'vi'}])
            # 7. character voice + detail cues: build the real audio graph (a tap has unlocked the context)
            results['babble'] = await page.evaluate('''async()=>{
              const {Sound}=await import('/js/audio.js');const {voiceOf,PLAYER_VOICE}=await import('/js/v4/sounds.js');
              const s=new Sound();s.unlock();await s.ctx.resume();
              const v=[voiceOf('x',{display_name:'Bé Na',role:'Học sinh'}),voiceOf('y',{display_name:'Ông Tư',role:'Khách quen'}),voiceOf('z',{display_name:'Chị Thảo',role:'Nhân viên văn phòng'})];
              s.babble('Chào cháu, hôm nay bán đắt hàng không?',v[1]);const first=s.talk;
              s.babble('Dạ, con chào cô ạ!',v[0]);const second=s.talk;
              s.babble('một hai ba bốn năm sáu bảy tám chín mười mười một mười hai mười ba mười bốn mười lăm mười sáu mười bảy mười tám mười chín hai mươi',PLAYER_VOICE);
              const long=s.talk.end-s.ctx.currentTime;
              s.ting();s.coins();s.register();s.pop();s.chime();s.doorbell();s.paper();
              return {state:s.ctx.state,newestWins:first!==second&&!!second,longCapped:long<1.35,bases:v.map(x=>Math.round(x.base))};
            }''')
            assert results['babble']['newestWins'] and results['babble']['longCapped'], results['babble']
            b = results['babble']['bases']
            assert b[0] > b[2] > b[1], b   # child > woman > old man
            await browser.close()
    results['console_errors'] = errors
    print(json.dumps(results, ensure_ascii=False, indent=1))
    assert not errors, errors
    print('BANK CHECK OK')


asyncio.run(main())
