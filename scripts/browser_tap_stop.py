#!/usr/bin/env python3
"""Stop-on-tap meters on a slow phone (dev tool, needs `pip install playwright` + chromium).

Player feedback #100: "lúc tắm thú hoặc ép nắp trà sữa … mình bấm dừng rồi nó vẫn cứ chạy lố", and the tailor's
sewing machine: "canh tới mức xanh nhưng tới mức đỏ nó mới dừng". On a 390 px phone with the CPU throttled
(default 4×) and a slow network (default 300 ms each way), this presses "🔥 Ép nắp" at the milk-tea counter,
"🚿 Mở vòi xả" at the pet-care bath table and "🧵 Đạp máy may" at the clothes shop, taps stop with a touch, and
reports:

- seen: where the bar was drawn when the finger came down (what the player saw);
- drift: how far the bar went on after that, until the server answered (should be 0: frozen at the tap);
- judged: what the server graded (the sealer's seconds, the rinse seconds, the seconds sewn);
- cue: the bar's colour / words (in the green, past it) against where the bar is drawn, frame by frame until the
  tap: cue_stale_s is how far (meter seconds) the bar was past a line while its cue still said the old thing
  (a green needle already in the red);
- frames while the bar runs: mean / p95 / max frame time, frames over 50 ms, layouts, style passes and script time
  per second (--root DIR measures another tree, e.g. an older build from `git archive`).

A busy production server, in miniature:
- --stop-delay MS: the stop command waits MS before it reaches the server (a command ahead of it, a server lock);
- --start-delay MS: the start command waits MS on its way in (the page's estimate of the server clock taken from
  that answer leans: the bar is drawn ahead of the server's own);
- --skew S: the phone's clock is S seconds off (the page must read the server's clock, not its own);
- --tap S: stop at S meter seconds instead of the default point in the green.

    python scripts/browser_tap_stop.py [--throttle 4] [--latency 300] [--careers milk_tea,pet_care,clothing]
        [--stop-delay MS] [--start-delay MS] [--skew S] [--tap S] [--report FILE] [--loose]

Exits 1 when a frozen bar moves, seen ≠ judged (more than one frame + rounding) or a cue runs more than a frame
behind its bar; --loose only reports (for measuring an older build).
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if '--root' in sys.argv:   # measure another tree (an older build) with this script
    ROOT = Path(sys.argv[sys.argv.index('--root') + 1]).resolve()
sys.path.insert(0, str(ROOT))
TOL = 0.08          # seconds: seen at the touch vs judged: a frame or two at 4× CPU, the rinse's 0.1 s rounding
FROZEN_TOL = 0.06   # seconds: where the bar stands frozen vs judged (the rinse's 0.1 s rounding)
CUE_TOL = 0.08      # meter seconds a cue may trail its bar: about a frame at 4× CPU


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix='mnl-tap-')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1', MNL_DEV='1')
    for k in ('MNL_CAREERS', 'LLM_API_KEY', 'LLM_BASE_URL'):
        env.pop(k, None)
    db = os.path.join(tmp, 'g.sqlite3')
    log = open(os.path.join(tmp, 'server.log'), 'wb')
    p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--db', db], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    for _ in range(600):
        try:
            urllib.request.urlopen(base + '/api/health', timeout=1)
            break
        except Exception:
            if p.poll() is not None:
                break
            time.sleep(0.1)
    try:
        yield base, db
    finally:
        p.terminate()
        with contextlib.suppress(Exception):
            p.wait(5)
        log.close()


def mutate(db: str, token: str, fn) -> None:
    from game import marriage as mr
    from game.storage import Store
    store = Store(db)
    mr._mutate(store, {store.key(token): fn})


def act(s, career, action, **p):
    from game.engine import apply_action
    t, r = apply_action(s, career, action, p)
    s.clear()
    s.update(t)
    return r


def quiet(s, career):
    from game import whats_new as wn
    from game.employment import hired_record, required
    s['name'] = 'Lan'
    s['settings'].update(tutorialDone=True, whatsNewSeen=wn.LATEST)
    if required(career):
        s['careers'][career]['job'] = hired_record(career)


def seed_milk_tea(s):
    """A cup with tea, sugar and ice in it, ready for the sealer."""
    from game import boba
    quiet(s, 'milk_tea')
    act(s, 'milk_tea', 'select_career')
    act(s, 'milk_tea', 'start_day')
    c = s['careers']['milk_tea']
    tid = c['active_task'] or c['tasks'][0]['id']
    act(s, 'milk_tea', 'ask', task=tid)
    t = next(x for x in c['tasks'] if x['id'] == tid)
    for action, payload in boba.solution(t):
        if action in ('tea_seal', 'tea_serve'):
            break
        if action == 'tea_add' and boba.stock(s['careers']['milk_tea'])[payload['item']] == 0:
            act(s, 'milk_tea', 'tea_prepare', item=payload['item'], qty=5, confirm=True)
        act(s, 'milk_tea', action, **payload)


def seed_pet_care(s):
    """A groom with a bath: washed, the tap still off."""
    from game.careers import pet_care as P
    quiet(s, 'pet_care')
    act(s, 'pet_care', 'select_career')
    act(s, 'pet_care', 'start_day')
    c = s['careers']['pet_care']
    for slot in range(12):
        t = P.make_task(c['day'], slot, 1)
        n = t['needs']
        if t['job'] == 'groom' and 'bath' in n['services'] and not n.get('rx') and not t['_x'].get('case') and n['species'] == 'dog':
            break
    else:
        raise SystemExit('no groom with a bath today')
    c['tasks'] = [t]
    c['active_task'] = t['id']
    P.on_task(s, c, t)
    act(s, 'pet_care', 'ask', task=t['id'])
    for part in ('scale', 'coat', 'skin', 'ears', 'nails', 'body', 'gait', 'mood'):
        with contextlib.suppress(Exception):
            act(s, 'pet_care', 'pc_inspect', task=t['id'], part=part)
    if 'brush' in t['needs']['services']:
        act(s, 'pet_care', 'pc_brush', task=t['id'], tool='brush')
    act(s, 'pet_care', 'pc_bath', task=t['id'], shampoo='sensitive' if t['needs']['stage'] == 'young' else 'normal', temp=37)


def seed_clothing(s):
    """A hem / waist job, measured and chalked: the sewing machine is next (day 3+: the regular green line)."""
    from game.careers import PLUGINS
    A = PLUGINS['clothing']
    quiet(s, 'clothing')
    act(s, 'clothing', 'select_career')
    act(s, 'clothing', 'start_day')
    c = s['careers']['clothing']
    t = next(t for day in range(3, 40) for slot in range(12) if (day, slot) not in A.STORY
             for t in [A.make_task(day, slot, 1)] if t['kind'] == 'alter')
    c['day'] = t['day']
    c['tasks'] = [t]
    c['active_task'] = t['id']
    if hasattr(A, 'on_task'):
        A.on_task(s, c, t)
    act(s, 'clothing', 'ask', task=t['id'])
    act(s, 'clothing', 'ao_measure', task=t['id'])
    act(s, 'clothing', 'ao_alter_self', task=t['id'], cm=t['needs']['_cm'])


SEED = {'milk_tea': seed_milk_tea, 'pet_care': seed_pet_care, 'clothing': seed_clothing}

OPEN_JOB = """(id)=>{const b=document.createElement('button');b.type='button';b.dataset.action='job';if(id)b.dataset.task=id;
  b.hidden=true;document.body.append(b);b.click();b.remove();}"""

# Recorder: frame times while a meter runs, the bar's position against its cue on each frame, and the bar's
# position from the moment a finger comes down. Runs before the page's own frame callbacks: what was painted.
INIT = r"""
window.__tap={frames:[],cues:[],rec:false,down:null,after:[]};
(function loop(){requestAnimationFrame(t=>{const T=window.__tap;if(T.rec){if(T.last)T.frames.push(t-T.last);T.last=t;if(T.cue){const c=T.cue();if(c)T.cues.push(c);}}else T.last=0;
  if(T.down&&T.read){T.after.push([T.read(),t-T.down.at]);}loop();});})();
// Capture on window: runs before the page's own document listeners (what the player saw = what is painted now).
addEventListener('pointerdown',e=>{const T=window.__tap;if(!T.read||!T.armed)return;T.armed=false;T.down={seen:T.read(),at:performance.now()};},true);
"""

READERS = {
    # Seconds shown by the sealer needle: its drawn x on the gauge × the scale (data-s: …,max).
    'milk_tea': r"""()=>{const g=document.querySelector('#sheet[open] [data-seal-start]');if(!g)return null;
      const n=g.querySelector('.mt-needle'),r=g.getBoundingClientRect(),q=n.getBoundingClientRect(),max=Number(g.dataset.s.split(',')[4]);
      const x=q.width>12?q.left:q.left+q.width/2;return (x-r.left)/r.width*max;}""",
    # Seconds shown by the rinse bar: its drawn fill × the scale (need×2 = data-over).
    'pet_care': r"""()=>{const g=document.querySelector('#sheet[open] [data-pc-timer="rinse"]');if(!g)return null;
      const tr=g.querySelector('.pc-track').getBoundingClientRect(),f=g.querySelector('.fill').getBoundingClientRect(),over=Number(g.dataset.over);
      return (Math.min(f.right,tr.right)-tr.left)/tr.width*over;}""",
}
START = {'milk_tea': '#sheet[open] .mt-sealer [data-op="tea_seal_start"]:not([disabled])',
         'pet_care': '#sheet[open] .btn[data-command="pc_rinse"][data-payload*="start"]:not([disabled])'}
STOP = {'milk_tea': '#sheet[open] .mt-sealer [data-op="tea_seal"]',
        'pet_care': '#sheet[open] .btn[data-command="pc_rinse"][data-payload*="stop"]'}
# The clothes shop: the needle's drawn x on the seam × the seconds of a pass (data-sec).
READERS['clothing'] = r"""()=>{const g=document.querySelector('#sheet[open] [data-ao-sew]');if(!g)return null;
  const box=g.querySelector('.ao-needle').getBoundingClientRect(),b=g.querySelector('.ao-needle>b').getBoundingClientRect();
  return (b.left-box.left)/box.width*Number(g.dataset.sec);}"""
# Cues: [bar value, cue shown ('ready' / 'over' / ''), cue due at that value, distance to the nearest line].
CUES = {
    'milk_tea': r"""()=>{const g=document.querySelector('#sheet[open] [data-seal-start]');if(!g)return null;const v=window.__tap.read();if(v==null)return null;
      const [loose,lo,hi,burn]=g.dataset.s.split(',').map(Number),cue=g.classList.contains('over')?'over':g.classList.contains('ready')?'ready':'';
      const want=v>burn?'over':v>=lo&&v<=hi?'ready':'';return [v,cue,want,Math.min(...[lo,hi,burn].map(e=>Math.abs(v-e)))];}""",
    'pet_care': r"""()=>{const g=document.querySelector('#sheet[open] [data-pc-timer="rinse"]');if(!g)return null;const v=window.__tap.read();if(v==null)return null;
      const need=Number(g.dataset.need),over=Number(g.dataset.over),cue=g.classList.contains('over')?'over':g.classList.contains('ready')?'ready':'';
      const want=v>=over?'over':v>=need?'ready':'';return [v,cue,want,Math.min(Math.abs(v-need),Math.abs(v-over))];}""",
    'clothing': r"""()=>{const g=document.querySelector('#sheet[open] [data-ao-sew]');if(!g)return null;const v=window.__tap.read();if(v==null)return null;
      const sec=Number(g.dataset.sec),lo=Number(g.dataset.lo)*sec,hi=Number(g.dataset.hi)*sec,cue=g.classList.contains('over')?'over':g.classList.contains('ready')?'ready':'';
      const want=v>hi?'over':v>=lo?'ready':'';return [v,cue,want,Math.min(Math.abs(v-lo),Math.abs(v-hi))];}""",
}
START['clothing'] = '#sheet[open] .ao-alter .btn[data-command="ao_sew_start"]:not([disabled])'
STOP['clothing'] = '#sheet[open] .ao-alter .btn[data-command="ao_sew_stop"]'
TARGET = {'milk_tea': 1.9, 'pet_care': 8.6, 'clothing': 3.3}   # stop here (the green zone / just past the 8 s line)
# The phone's clock `skew` seconds off (Date.now and new Date(); performance.now is the phone's own and stays).
SKEW = r"""(()=>{const k=__SKEW__*1000;if(!k)return;const N=Date.now.bind(Date),D=Date;
  globalThis.Date=class extends D{constructor(...a){super(...(a.length?a:[N()+k]));}static now(){return N()+k;}};}
)();"""


async def run(pw, base, db, cid, throttle, latency, stop_delay=0, start_delay=0, skew=0.0, target=None):
    browser = await pw.chromium.launch()
    ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2, bypass_csp=True)
    await ctx.add_init_script("try{localStorage.setItem('mnl.wn.seen','99.0.0')}catch(e){}")
    if skew:
        await ctx.add_init_script(SKEW.replace('__SKEW__', repr(float(skew))))
    await ctx.add_init_script(INIT)
    page = await ctx.new_page()
    target = target or TARGET[cid]
    start_op = 'tea_seal_start' if cid == 'milk_tea' else 'ao_sew_start' if cid == 'clothing' else 'pc_rinse'
    stop_op = 'tea_seal' if cid == 'milk_tea' else 'ao_sew_stop' if cid == 'clothing' else 'pc_rinse'
    delays = {'on': False}

    async def hold_back(route):
        """--start-delay / --stop-delay: the command waits before it reaches the server."""
        wait = 0
        with contextlib.suppress(Exception):
            b = json.loads(route.request.post_data or '{}')
            mode = (b.get('payload') or {}).get('mode')
            if delays['on'] and b.get('action') == start_op and mode in (None, 'start'):
                wait = start_delay
            elif delays['on'] and b.get('action') == stop_op and mode in (None, 'stop'):
                wait = stop_delay
        if wait:
            await asyncio.sleep(wait / 1000)
        await route.continue_()
    if stop_delay or start_delay:
        await page.route('**/api/command', hold_back)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)[:200]))
    answers = []

    async def on_response(r):
        if r.url.endswith('/api/command') and r.request.method == 'POST':
            with contextlib.suppress(Exception):
                answers.append(dict(body=json.loads(r.request.post_data or '{}'), data=await r.json(), at=time.time()))
    page.on('response', lambda r: asyncio.ensure_future(on_response(r)))
    await page.goto(base)
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
    mutate(db, token, SEED[cid])
    await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    await page.wait_for_timeout(800)
    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
    await page.evaluate(OPEN_JOB, None)
    await page.wait_for_selector('#sheet[open] .career-job', timeout=10000)
    await page.wait_for_timeout(600)
    cdp = await ctx.new_cdp_session(page)
    await cdp.send('Performance.enable')
    await cdp.send('Network.enable')
    await cdp.send('Network.emulateNetworkConditions', dict(offline=False, latency=latency, downloadThroughput=-1, uploadThroughput=-1))
    await cdp.send('Emulation.setCPUThrottlingRate', dict(rate=throttle))
    start = page.locator(START[cid]).first
    await start.scroll_into_view_if_needed()
    await page.evaluate(f"window.__tap.read={READERS[cid]};window.__tap.cue={CUES[cid]}")
    delays['on'] = True
    await start.tap()
    await page.wait_for_function(f"(()=>{{const v=window.__tap.read();return v!=null&&v>0.2;}})()", timeout=15000)
    m0 = {m['name']: m['value'] for m in (await cdp.send('Performance.getMetrics'))['metrics']}
    t0 = time.time()
    await page.evaluate("window.__tap.rec=true")
    await page.wait_for_function(f"(()=>{{const v=window.__tap.read();return v!=null&&v>={target};}})()", polling='raf', timeout=30000)
    m1 = {m['name']: m['value'] for m in (await cdp.send('Performance.getMetrics'))['metrics']}
    secs = time.time() - t0
    await page.evaluate("window.__tap.rec=false;window.__tap.armed=true")
    stop = page.locator(STOP[cid]).first
    n = len(answers)
    await stop.tap()
    for _ in range(400):
        if len(answers) > n:
            break
        await page.wait_for_timeout(50)
    await page.wait_for_timeout(300)
    tap = await page.evaluate("({down:window.__tap.down,after:window.__tap.after.filter(v=>v[0]!=null),frames:window.__tap.frames,cues:window.__tap.cues})")
    await cdp.send('Emulation.setCPUThrottlingRate', dict(rate=1))
    last = answers[-1] if len(answers) > n else None
    judged = None
    if last:
        res = last['data'].get('result') or {}
        if cid in ('milk_tea', 'clothing'):
            judged = res.get('held')
        else:
            tasks = last['data']['state']['careers']['pet_care']['tasks']
            judged = tasks[0]['g']['rinse_s']
    res = (last or {}).get('data', {}).get('result') or {}
    msg = res.get('message') or ''
    outcome = (res.get('seal') if cid == 'milk_tea' else None if cid != 'clothing' else 'refused' if res.get('refused')
               else 'good' if 'Dừng ngay vạch' in msg else 'crooked' if msg else None)
    # Cue frames: the bar's colour / words against where it is drawn (a frame right on a line does not count).
    stale = [c for c in tap['cues'] if c[1] != c[2] and c[3] > 0.005]
    frames = sorted(tap['frames'])
    seen = tap['down']['seen'] if tap['down'] else None
    after = [v for v, _ in tap['after']]
    drift = (max(after) - seen) if after and seen is not None else None
    # Where the bar stands a little after the touch, before the answer can be back (the latency is ≥ 150 ms).
    early = [v for v, dt in tap['after'] if dt < min(150, latency * .6)]
    frozen = early[-1] if early else None
    out = dict(career=cid, throttle=throttle, latency_ms=latency, stop_delay_ms=stop_delay, start_delay_ms=start_delay, skew_s=skew,
               seen=seen, judged=judged, outcome=outcome, message=msg[:90],
               judged_minus_seen=None if judged is None or seen is None else round(judged - seen, 3),
               drift_after_tap=None if drift is None else round(drift, 3),
               frozen=frozen, frozen_minus_judged=None if frozen is None or judged is None else round(frozen - judged, 3),
               sent_tap_at=(last or {}).get('body', {}).get('payload', {}).get('tap_at'),
               cue_frames=len(tap['cues']), cue_stale_frames=len(stale), cue_stale_s=round(max((c[3] for c in stale), default=0), 3),
               cue_stale_example=max(stale, key=lambda c: c[3]) if stale else None,
               frames=len(frames), frame_mean_ms=round(sum(frames) / len(frames), 1) if frames else None,
               frame_p95_ms=round(frames[int(len(frames) * .95) - 1], 1) if frames else None,
               frame_max_ms=round(frames[-1], 1) if frames else None, frames_over_50ms=sum(1 for f in frames if f > 50),
               layout_ms_per_s=round((m1['LayoutDuration'] - m0['LayoutDuration']) * 1000 / secs, 1),
               layouts_per_s=round((m1['LayoutCount'] - m0['LayoutCount']) / secs, 1),
               styles_per_s=round((m1['RecalcStyleCount'] - m0['RecalcStyleCount']) / secs, 1),
               style_ms_per_s=round((m1['RecalcStyleDuration'] - m0['RecalcStyleDuration']) * 1000 / secs, 1),
               script_ms_per_s=round((m1['ScriptDuration'] - m0['ScriptDuration']) * 1000 / secs, 1),
               task_ms_per_s=round((m1['TaskDuration'] - m0['TaskDuration']) * 1000 / secs, 1),
               errors=errors)
    await browser.close()
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--throttle', type=float, default=4)
    ap.add_argument('--latency', type=int, default=300)
    ap.add_argument('--careers', default='milk_tea,pet_care,clothing')
    ap.add_argument('--stop-delay', type=int, default=0, help='ms the stop command waits before it reaches the server')
    ap.add_argument('--start-delay', type=int, default=0, help='ms the start command waits on its way in')
    ap.add_argument('--skew', type=float, default=0.0, help="seconds the phone's clock is off")
    ap.add_argument('--tap', type=float, help='stop at this many meter seconds')
    ap.add_argument('--report')
    ap.add_argument('--loose', action='store_true')
    ap.add_argument('--root', help='the game tree to serve (default: this one)')
    a = ap.parse_args()
    from playwright.async_api import async_playwright
    results, bad = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            for cid in a.careers.split(','):
                r = await run(pw, base, db, cid, a.throttle, a.latency, a.stop_delay, a.start_delay, a.skew, a.tap)
                results.append(r)
                print(json.dumps(r, ensure_ascii=False))
                if r['errors']:
                    bad.append(f'{cid}: page errors {r["errors"]}')
                if r['judged'] is None or r['seen'] is None:
                    bad.append(f'{cid}: no stop measured')
                elif abs(r['judged_minus_seen']) > TOL:
                    bad.append(f'{cid}: judged {r["judged"]} but the bar showed {r["seen"]:.3f} at the tap')
                if r['frozen_minus_judged'] is None or abs(r['frozen_minus_judged']) > FROZEN_TOL:
                    bad.append(f'{cid}: the bar stopped at {r["frozen"]} but the server judged {r["judged"]}')
                if r['drift_after_tap'] is not None and r['drift_after_tap'] > 0.02:
                    bad.append(f'{cid}: the bar ran on {r["drift_after_tap"]:.3f} s after the tap')
                if r['cue_stale_s'] > CUE_TOL:
                    bad.append(f'{cid}: the cue trailed the bar by {r["cue_stale_s"]:.3f} s ({r["cue_stale_example"]})')
    if a.report:
        Path(a.report).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    for b in bad:
        print('FAIL', b)
    if bad and not a.loose:
        sys.exit(1)
    print('OK' if not bad else 'reported (--loose)')


if __name__ == '__main__':
    asyncio.run(main())
