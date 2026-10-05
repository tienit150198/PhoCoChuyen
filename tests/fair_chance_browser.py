"""Exercise real fair modules/CSS with real engine results and controlled network replies.

python -m tests.fair_chance_browser --engine chromium|webkit
No account, database, or external service is used.
"""
import argparse
import asyncio
import http.server
import json
from pathlib import Path
import random
import sys
import threading
from unittest import mock

from playwright.sync_api import expect, sync_playwright

from game import fair as fair_engine
from tests.job_application_browser import Assets
from tests.test_fair import FairBase, story
from tests.test_fair_scratch import Draws

ROOT = Path(__file__).resolve().parents[1]


def view(state, clock):
    fair = fair_engine.public(state)
    fair['now'] = clock.t
    if fair.get('cash'):
        fair['cash']['gift_ready'] = False  # exclude the independent welcome gift
    return dict(fair=fair, journey=state['journey'], settings=dict(sound=False, music=False))


def setup_page(browser, url, initial, tab, saved=None):
    page = browser.new_page(viewport=dict(width=390, height=844), has_touch=True)
    page.goto(url)
    page.evaluate("""async ({initial,tab,saved})=>{
      document.documentElement.dataset.layout='phone';
      if(saved)localStorage.setItem('mnl.fair.lt',JSON.stringify(saved));
      await new Promise(resolve=>{const l=document.createElement('link');l.rel='stylesheet';l.href='/css/app.css';l.onload=resolve;document.head.append(l);});
      const {openFair}=await import('/js/v4/fair.js');
      const api=new EventTarget();api.state=initial;api.content={};
      const h=window.h={api,requests:[],pending:[],open:()=>openFair({api,closeSheet(){}},{tab})};
      api.refresh=async()=>api.state;
      api.command=(action,payload)=>new Promise((resolve,reject)=>{h.requests.push({action,payload,at:performance.now()});h.pending.push({resolve,reject});});
      h.reply=({state,result,error})=>{const p=h.pending.shift();if(!p)throw Error('No pending command');
        if(error){p.reject(new Error(error));return;}
        api.state=state;api.dispatchEvent(new Event('state'));p.resolve(result);
      };
      await h.open();
    }""", dict(initial=initial, tab=tab, saved=saved))
    return page


def reply(page, case, state, **payload_override):
    page.wait_for_function('h.pending.length>0')
    req = page.evaluate('h.requests.at(-1)')
    state, result = case.act(state, req['action'], **(payload_override or req['payload']))
    page.evaluate('data=>h.reply(data)', dict(state=view(state, case.clock), result=result))
    return state, result


def scratch_case(browser, url, case, out, engine):
    state = story(1000)
    page = setup_page(browser, url, view(state, case.clock), 'xs')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.locator('[data-fh=xsbuy]').click()
    page.evaluate("h.reply({error:'Mạng tạm ngắt, thử lại nha.'})")
    expect(page.locator('[data-fh=xsbuy]')).to_be_enabled()
    assert page.evaluate('__fairScratch.state().ticket') is None
    page.locator('[data-fh=xsbuy]').click()
    page.locator('[data-fh=close]').click()
    expect(page.locator('.fh-sheet')).not_to_be_visible()
    state, result = reply(page, case, state)
    page.wait_for_function('__fairScratch.state().ticket!==null')
    hidden = page.locator('.fh-xs-cv').evaluate('(c)=>({width:c.width,height:c.height,w:c._w,h:c._h,mounted:!!c._xs})')
    page.evaluate('h.open()')
    canvas = page.locator('.fh-xs-cv')
    canvas.scroll_into_view_if_needed()
    canvas.wait_for(state='visible')
    size = canvas.evaluate('(c)=>({width:c.width,height:c.height,w:c._w,h:c._h,box:c.getBoundingClientRect().toJSON()})')
    before = page.evaluate('__fairScratch.state()')
    page.screenshot(path=str(out / f'{engine}-scratch-reopen.png'))
    b = canvas.bounding_box()
    page.mouse.click(b['x'] + b['width']/2, b['y'] + b['height']/2)
    after = page.evaluate('__fairScratch.state()')
    evidence = dict(case='scratch late purchase then reopen', hidden=hidden, reopened=size,
                    before=before, after_one_tap=after, result=result['fair'], requests=page.evaluate('h.requests'), errors=errors)
    (out / f'{engine}-scratch.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    assert size['w'] > 100 and size['h'] > 50, f'Canvas mounted while hidden and never resized: {size}'
    assert after['pct'] < .2 and not after['done'], 'One scratch tap must not reveal the whole ticket'
    assert len(evidence['requests']) == 2, 'Exactly one failed request and one paid purchase'
    page.locator('[data-fh=close]').click()
    page.evaluate('h.open()')
    assert page.evaluate('__fairScratch.state().pct') == after['pct'], 'Reopening must preserve partial scratches'
    assert page.evaluate('__fairScratch.state().ticket.id') == result['fair']['id']
    page.locator('[data-fh=xsall]').click()
    page.wait_for_function('__fairScratch.state().done')
    expect(page.locator('.fh-xs .fh-result')).to_be_visible()
    assert page.evaluate('h.api.state.fair.wallet') == state['journey']['wallet']
    assert not errors, errors
    page.close()
    return evidence


def bowl_cases(browser, url, case, out, engine):
    records = []
    for tab, action, draws in [('bc', 'roll', [.01]), ('xd', 'shakexd', [.9, .01]),
                                ('xd', 'shakexd', [.9, .99]), ('xd', 'shakexd', [.0])]:
        state = story(1000)
        page = setup_page(browser, url, view(state, case.clock), tab)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        if tab == 'bc':
            page.locator('[data-fh=chip][data-v="5"]').click()
            page.locator('[data-fh=bet][data-face=cua]').click()
        else:
            page.locator('[data-fh=side][data-v=le]').click()
            page.locator('[data-fh=stake][data-v="20"]').click()
        page.evaluate('h.started=performance.now()')
        page.locator(f'[data-fh={action}]').click()
        # Repeated activation and a slow response cannot start a second wager.
        page.locator(f'[data-fh={action}]').evaluate('(b)=>b.click()')
        expect(page.locator(f'[data-fh={action}]')).to_be_disabled()
        page.wait_for_function('h.pending.length===1')
        page.wait_for_timeout(650)
        page.locator('[data-fh=close]').click()
        with mock.patch.object(fair_engine, '_rng', Draws(draws, seed=19)):
            state, result = reply(page, case, state)
        page.evaluate('h.open()')
        raid = result['fair'].get('raid')
        target = page.locator('.fh-raid' if raid else f'.fh-{tab} .fh-result')
        expect(target).to_be_visible(timeout=7000)
        elapsed = page.evaluate('performance.now()-h.started')
        assert len(page.evaluate('h.requests')) == 1, 'One click sequence must settle one wager'
        assert state['journey']['wallet'] == 1000 + result['fair']['net']
        expect(page.locator('.fh-strip > span').first).to_contain_text(f"{state['journey']['wallet']:,}".replace(',', '.'))
        if raid:
            expect(target).to_contain_text(str(result['fair']['fine']))
            page.locator('[data-fh=raidok][data-tab=bc]').click()
            page.evaluate('h.open()')
            expect(page.locator('[data-fh=shakexd]')).to_be_disabled()
            expect(page.locator('.fh-swept')).to_be_visible()
        else:
            expect(target).to_contain_text(str(abs(result['fair']['net'])))
            if tab == 'bc':
                assert elapsed >= 4500, 'The configured five-second bowl reveal must be retained'
            else:
                expect(target).to_contain_text('Bạn chọn LẺ')
        records.append(dict(tab=tab, elapsed_ms=elapsed, result=result['fair'], requests=page.evaluate('h.requests'), errors=errors))
        assert not errors, errors
        page.screenshot(path=str(out / f'{engine}-{tab}-{len(records)}.png'))
        page.close()
    return records


def loto_case(browser, url, case, out, engine):
    state = story(1000)
    page = setup_page(browser, url, view(state, case.clock), 'lt')
    page.locator('[data-fh=buy]').click()
    page.evaluate("h.reply({error:'Mạng tạm ngắt'})")
    expect(page.locator('[data-fh=buy]')).to_be_enabled()
    page.locator('[data-fh=buy]').click()
    page.locator('[data-fh=buy]').evaluate('(b)=>b.click()')
    expect(page.locator('[data-fh=buy]')).to_be_disabled()
    page.locator('[data-fh=close]').click()
    with mock.patch.object(fair_engine, '_rng', Draws([.01], seed=7)):
        state, bought = reply(page, case, state)
    page.wait_for_timeout(1100)
    assert page.evaluate("JSON.parse(localStorage.getItem('mnl.fair.lt')||'null')") is None, 'Closed loto must not call numbers'
    page.evaluate('h.open()')
    page.wait_for_function("JSON.parse(localStorage.getItem('mnl.fair.lt')||'{}').shown===1")
    first = page.evaluate("JSON.parse(localStorage.getItem('mnl.fair.lt'))")
    page.locator('[data-fh=close]').click()
    page.wait_for_timeout(2500)
    assert page.evaluate("JSON.parse(localStorage.getItem('mnl.fair.lt')).shown") == 1, 'Closing pauses the caller'
    assert len(page.evaluate('h.requests')) == 2, 'Retry buys exactly one ticket'
    page.close()
    public = view(state, case.clock)
    v = public['fair']['loto']
    cards = v.get('cards') or [v['card']]
    need = v.get('need', 1)
    finish = min((sorted(max(v['seq'].index(n)+1 for n in row) for row in card)[need-1], ci)
                 for ci, card in enumerate(cards))
    at, ci = finish
    assert at <= v['npc_done'], 'Seed must create a winnable real round'
    called = set(v['seq'][:at-1])
    saved = dict(id=v['id'], shown=at-1, marks=[[n for row in c for n in row if n in called] for c in cards])
    page = setup_page(browser, url, public, 'lt', saved)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.locator('[data-fh=ltspeed][data-v="2"]').click()
    page.wait_for_function('at=>JSON.parse(localStorage.getItem("mnl.fair.lt")).shown>=at', arg=at)
    last = v['seq'][at-1]
    page.locator(f'[data-fh=mark][data-c="{ci}"][data-n="{last}"]').click()
    expect(page.locator(f'[data-fh=mark][data-c="{ci}"][data-n="{last}"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('[data-fh=kinh]').click()
    page.locator('[data-fh=kinh]').evaluate('(b)=>b.click()')
    expect(page.locator('[data-fh=kinh]')).to_be_disabled()
    page.locator('[data-fh=close]').click()
    state, claim = reply(page, case, state)
    assert claim['fair'].get('won'), claim
    page.evaluate('h.open()')
    expect(page.locator('.fh-kinhcard')).to_contain_text(str(claim['fair']['prize']))
    assert len(page.evaluate('h.requests')) == 1, 'Claim must not duplicate after reopening'
    assert not errors, errors
    record = dict(case='loto buy error/retry, closed reply, paused calls, persisted marks, winning claim after close',
                  first=first, resumed=saved, bought=bought['fair'], claim=claim['fair'], requests=page.evaluate('h.requests'), errors=errors)
    page.screenshot(path=str(out / f'{engine}-loto-win.png'))
    page.close()
    return record


def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('chromium', 'webkit'), default='chromium')
    args = parser.parse_args()
    out = ROOT / 'output/playwright/fair-all-local'
    out.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    case = FairBase()
    case.setUp()
    try:
        with mock.patch.object(fair_engine, '_rng', random.Random(712)), sync_playwright() as pw:
            browser = getattr(pw, args.engine).launch()
            url = f'http://127.0.0.1:{server.server_port}/'
            report = [scratch_case(browser, url, case, out, args.engine)]
            report.extend(bowl_cases(browser, url, case, out, args.engine))
            report.append(loto_case(browser, url, case, out, args.engine))
            (out / f'{args.engine}-chance-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            browser.close()
        print(f'{args.engine}: scratch, bau cua, xoc dia win/loss/raid, loto lifecycle passed')
    finally:
        case.doCleanups()
        server.shutdown()


if __name__ == '__main__':
    main()
