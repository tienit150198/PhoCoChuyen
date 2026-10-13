"""Four new careers through real controls at 390/1280px, on isolated synthetic saves.

Requires TEST_DATABASE_URL pointing to disposable PostgreSQL and installed
Playwright Chromium. Writes screenshots and a machine-readable report only.
"""
import asyncio
import argparse
import copy
import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server
from browser_v04 import OVERFLOW
from game import marriage, __version__
from game.engine import validate_state
from game.storage import Store
from tests.helpers import Journey
from tests.test_quay import owner

OUT = ROOT / 'output/playwright/creative-civic'
CAREERS = ('art_studio', 'lawyer', 'laundry', 'post_office')


def read(namespace, token):
    store = Store(namespace, story=True)
    try:
        return store.read(token)[0]
    finally:
        store.close_pool()


def seed(namespace, token, cid, day):
    fixture = Journey(cid, day=day, slot=1)
    state = owner(wallet=10000, trade=cid, chapter=4)
    state['careers'][cid] = copy.deepcopy(fixture.c)
    state.update(current=cid, focus=cid, name='Người kiểm thử')
    state['settings'].update(tutorialDone=True, whatsNewSeen=__version__)
    state['journey'].update(intro=True, gender='female', news=[])
    validate_state(state)
    store = Store(namespace, story=True)
    try:
        marriage._mutate(store, {store.key(token): lambda s: (s.clear(), s.update(copy.deepcopy(state)))})
    finally:
        store.close_pool()
    return fixture.task['id']


async def open_work(page, reload=False):
    if reload:
        await page.reload()
    await page.wait_for_selector('#app:not([hidden])', timeout=45000)
    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
    if await page.locator('.iso-mission summary').count():
        await page.locator('.iso-mission summary').click()
        await page.locator('[data-action="isoMission"]:visible').click(timeout=20000)
    else:
        await page.locator('[data-action="job"]:visible, [data-action="workbench"]:visible').first.click(timeout=20000)
    await page.wait_for_selector('.career-job', timeout=20000)


async def click_command(page, action, **fields):
    buttons = page.locator(f'.career-job [data-command="{action}"]')
    await buttons.first.wait_for(timeout=10000)
    payloads = await buttons.evaluate_all("bs=>bs.map(b=>JSON.parse(b.dataset.payload||'{}'))")
    index = next(i for i, p in enumerate(payloads) if all(p.get(k) == v for k, v in fields.items()))
    return await send_click(page, buttons.nth(index), action)


async def send_click(page, button, action):
    async with page.expect_response(lambda r: '/api/command' in r.url and r.request.method == 'POST'
                                   and r.request.post_data_json.get('action') == action, timeout=20000) as response:
        await button.click()
    reply = await response.value
    data = await reply.json()
    assert reply.status == 200, (action, reply.status, data.get('error'))
    await page.wait_for_selector('body:not(.busy)')
    return data


async def rendered_task(page, cid, t):
    if cid == 'laundry':
        await page.wait_for_selector(f'.ld-stage[data-stage="{t["stage"]}"]')
    elif cid in ('lawyer', 'post_office'):
        selector = '.lw-step' if cid == 'lawyer' else '.post-step-count'
        text = f'Bước {t["at"]+1}/{len(t["needs"]["steps"])}'
        await page.locator(selector).filter(has_text=re.compile('^' + re.escape(text) + '$')).wait_for()
    else:
        command = dict(plan='art_plan',paint='art_layer',proof='art_proof',deliver='art_deliver')[t['stage']]
        await page.wait_for_selector(f'.career-job [data-command="{command}"]')


async def snapshot(page, tag, suffix, checks):
    # The app deliberately defers workbench redraws for 350ms after a scroll.
    # Settle that guard before awaiting the finite opening animation.
    await page.wait_for_timeout(450)
    await page.evaluate("""async()=>{const sheet=document.querySelector('#sheet');
      await Promise.all(sheet.getAnimations({subtree:true})
        .filter(a=>Number.isFinite(a.effect.getComputedTiming().endTime))
        .map(a=>a.finished.catch(()=>{})));}""")
    styles = await page.evaluate("""()=>['#sheet','.career-job'].map(selector=>{
      const el=document.querySelector(selector),s=getComputedStyle(el);
      return {selector,opacity:s.opacity,background:s.backgroundColor,animation:s.animationName};})""")
    overflow = await page.evaluate(OVERFLOW)
    checks.append(dict(stage=suffix, overflow=overflow, styles=styles))
    assert styles[0]['opacity'] == '1', (tag, suffix, styles)
    assert not (overflow['page'] or overflow['sheet'] or overflow['over']), (tag, suffix, overflow)
    await page.screenshot(path=str(OUT / f'{tag}-{suffix}.png'))


async def laundry_step(page, t, wrong=False):
    stage = t['stage']
    if stage in ('inspect', 'check'):
        for box in await page.locator('.ld-stage input[type="checkbox"]').all():
            await box.check()
    elif stage == 'deliver':
        await page.locator(f'.ld-stage input[value="{t["needs"]["tag"]}"]').check()
    else:
        values = dict(t['_key'][stage])
        if wrong:
            from game.careers.laundry import step_options
            key = next(iter(values))
            values[key] = next(o['id'] for o in step_options(stage) if o['id'] != values[key])
        for key, value in values.items():
            await page.locator(f'.ld-stage select[data-ld-field="{key}"]').select_option(value)
    await send_click(page, page.locator('.ld-submit'), 'ld_' + stage)


async def lawyer_step(page, t, wrong=False):
    st = t['needs']['steps'][t['at']]
    value = t['_key'][st['id']]
    if st['type'] in ('multi', 'order'):
        await page.locator('.lw-work [data-action="car:reset"]').click()
        values = ['signed', 'claim'] if wrong else value
        for item in values:
            await page.locator(f'.lw-work [data-action="car:select"][data-item="{item}"]').click()
        await send_click(page, page.locator('.lw-work [data-action="car:submit"]'), 'lw_submit')
    elif st['type'] == 'amount':
        await page.locator('.lw-work input[data-sk-amt]').fill(str(value))
        await send_click(page, page.locator('.lw-work [data-action="car:lawAmount"]'), 'lw_submit')
    else:
        await click_command(page, 'lw_submit', step=st['id'], value=value)


async def post_step(page, t, wrong=False):
    st = t['needs']['steps'][t['at']]
    value = t['_key'][st['id']]
    if st.get('options'):
        if wrong:
            value = next(o['id'] for o in st['options'] if o['id'] != value)
        await click_command(page, 'post_step', step=st['id'], value=value)
    else:
        await page.locator('.post-step input[data-sk-amt]').fill(str(value))
        await send_click(page, page.locator('.post-step [data-action="car:amtSend"]'), 'post_step')


async def art_step(page, t, wrong=False):
    stage = t['stage']
    if stage == 'plan':
        for field in ('layout', 'palette', 'medium'):
            await click_command(page, 'art_plan', field=field, value=t['_key'][field])
        await click_command(page, 'art_begin')
    elif stage == 'paint':
        remaining = [l for l in t['_key']['layers'] if l not in t['painted']]
        await click_command(page, 'art_layer', layer=remaining[1 if wrong and len(remaining) > 1 else 0])
    elif stage == 'proof':
        for key in ('brief', 'surface', 'signature'):
            await page.locator(f'[data-action="car:artCheck"][data-key="{key}"]').click()
        await click_command(page, 'art_proof')
    else:
        await click_command(page, 'art_deliver', recipient=t['needs']['recipient'])


async def main():
    from playwright.async_api import async_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--career', choices=CAREERS)
    parser.add_argument('--reuse-report', action='store_true', help='Keep evidence for careers not selected in this run')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    reports, errors, failures = [], [], []
    selected = (args.career,) if args.career else CAREERS[:1] if args.quick else CAREERS
    if args.reuse_report and (OUT / 'report.json').exists():
        previous = json.loads((OUT / 'report.json').read_text(encoding='utf-8'))
        assert previous['version'] == __version__, 'Do not combine evidence across releases'
        keep = lambda entry: not any(f'-{cid}-' in entry['case'] for cid in selected)
        reports = [entry for entry in previous['cases'] if keep(entry)]
        errors = [entry for entry in previous['browser_errors'] if keep(entry)]
        failures = [entry for entry in previous['failures'] if keep(entry)]
    with server() as (base, namespace):
        print('Browser server ready: ' + base, flush=True)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            quick = args.quick
            for width, height in (((390, 844),) if quick else ((390, 844), (1280, 860))):
                for cid in selected:
                    for day in ((1,) if quick else (1, 40)):
                        tag = f'{width}-{cid}-day{day}'
                        context = await browser.new_context(viewport=dict(width=width, height=height))
                        page = await context.new_page()
                        page.on('pageerror', lambda e, tag=tag: errors.append(dict(case=tag, error=str(e))))
                        try:
                            await page.goto(base)
                            await page.wait_for_selector('#app:not([hidden])', timeout=45000)
                            token = next(c['value'] for c in await context.cookies() if c['name'] == 'mnl_session')
                            tid = seed(namespace, token, cid, day)
                            await open_work(page, reload=True)
                            checks = []
                            if cid == 'post_office':
                                await click_command(page, 'post_intro')
                            await click_command(page, 'ask')
                            await snapshot(page, tag, 'received', checks)
                            wrong_done = reloaded = False
                            steps = 0
                            while steps < 100:
                                state = read(namespace, token)
                                t = next(t for t in state['careers'][cid]['tasks'] if t['id'] == tid)
                                if t['status'] == 'completed':
                                    break
                                await rendered_task(page, cid, t)
                                wrong = not wrong_done and (cid in ('lawyer', 'post_office') or
                                        cid == 'laundry' and t['stage'] == 'sort' or cid == 'art_studio' and t['stage'] == 'paint')
                                await {'laundry': laundry_step, 'lawyer': lawyer_step, 'post_office': post_step,
                                       'art_studio': art_step}[cid](page, t, wrong=wrong)
                                steps += 1
                                if wrong:
                                    wrong_done = True
                                    after = next(t for t in read(namespace, token)['careers'][cid]['tasks'] if t['id'] == tid)
                                    assert after['mistakes'] > 0, (tag, 'wrong input was not recorded')
                                    await snapshot(page, tag, 'wrong-input', checks)
                                if steps >= 3 and not reloaded:
                                    before = next(t for t in read(namespace, token)['careers'][cid]['tasks'] if t['id'] == tid)
                                    await open_work(page, reload=True)
                                    after = next(t for t in read(namespace, token)['careers'][cid]['tasks'] if t['id'] == tid)
                                    assert before == after, (tag, 'reload changed task')
                                    reloaded = True
                                    await snapshot(page, tag, 'reloaded', checks)
                            done = next(t for t in read(namespace, token)['careers'][cid]['tasks'] if t['id'] == tid)
                            assert done['status'] == 'completed', tag
                            assert wrong_done and reloaded, tag
                            await snapshot(page, tag, 'completed', checks)
                            for extension in ('png','html'):
                                (OUT / f'{tag}-FAILED.{extension}').unlink(missing_ok=True)
                            reports.append(dict(case=tag, viewport=[width,height],career=cid, day=day, completed=True,
                                                wrong_input=True,reload_preserved=True,mistakes=done['mistakes'],steps=steps,checks=checks))
                            print(tag + ': passed', flush=True)
                        except Exception as error:
                            failures.append(dict(case=tag,error=str(error)))
                            await page.screenshot(path=str(OUT / f'{tag}-FAILED.png'))
                            (OUT / f'{tag}-FAILED.html').write_text(await page.content(), encoding='utf-8')
                            print(traceback.format_exc(), flush=True)
                            print(tag + ': FAILED ' + str(error), flush=True)
                        finally:
                            await context.close()
                        (OUT / 'report.json').write_text(json.dumps(dict(version=__version__,cases=reports, failures=failures, browser_errors=errors),ensure_ascii=False,indent=2),encoding='utf-8')
            await browser.close()
    assert not failures and not errors, (failures,errors)


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
