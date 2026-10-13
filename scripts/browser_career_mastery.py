"""Mastery passport/review controls in classic and new UI, with disposable saves."""
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server
from browser_v04 import OVERFLOW
from browser_creative_civic import read, send_click
from game import marriage, career_mastery as mastery, __version__
from game.engine import validate_state
from game.storage import Store
from tests.helpers import Journey
from tests.test_quay import owner

OUT = ROOT / 'output/playwright/career-mastery'


def seed(namespace, token, modern):
    state = owner(wallet=10000, trade='laundry', chapter=4)
    c = copy.deepcopy(Journey('laundry', day=100, slot=1).c)
    c['xp'] = 9000
    c['metrics']['served'] = 320
    c['mastery'] = mastery._initial(1)
    c['mastery'].update(clean=320, completed=320, qualified_days=80, last_closed=99,
                        today=dict(day=100, jobs=[]))
    state['careers']['laundry'] = c
    state.update(current='laundry', focus='laundry', name='Người kiểm thử')
    state['settings'].update(tutorialDone=True, whatsNewSeen=__version__)
    state['journey'].update(intro=True, gender='female', news=[])
    state['journey']['interface'] = dict(newInterface=modern, interfacePromptSeen=True)
    validate_state(state)
    store = Store(namespace, story=True)
    try:
        marriage._mutate(store, {store.key(token): lambda s: (s.clear(), s.update(copy.deepcopy(state)))})
    finally:
        store.close_pool()


async def open_mastery(page):
    await page.wait_for_selector('#app:not([hidden])', timeout=45000)
    # Close only incidental first-visit announcements on these synthetic saves.
    await page.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
    group = page.locator('[data-action="v4Group"][data-group="minh"]:visible')
    if not await group.count():
        await page.locator('[data-action="isoMore"]:visible,[data-action="v4Menu"]:visible').first.click()
    await group.click()
    await page.locator('[data-action="passport"]:visible').first.click()
    await page.locator('.lx-card[aria-label="Tay nghề lâu năm"] [data-action="promo"]').click()
    await page.locator('.cm-card').wait_for()


async def shot(page, tag, name, rows):
    await page.wait_for_timeout(450)  # app scroll guard (350ms) and sheet entry fade
    await page.evaluate("""async()=>{await Promise.all(document.querySelector('#sheet').getAnimations({subtree:true})
      .filter(a=>Number.isFinite(a.effect.getComputedTiming().endTime)).map(a=>a.finished.catch(()=>{})));}""")
    over = await page.evaluate(OVERFLOW)
    assert not (over['page'] or over['sheet'] or over['over']), over
    rows.append(dict(stage=name, overflow=over))
    await page.locator('.cm-card').screenshot(path=str(OUT / f'{tag}-{name}.png'))


async def assessment(page, namespace, token, good, tag, rows, reload=False):
    await send_click(page, page.locator('[data-command="mastery_start"]'), 'mastery_start')
    for index in range(4):
        await page.locator('.cm-review .eyebrow').filter(has_text=f'Câu {index+1}/4').wait_for()
        # A new question may reuse the prior button node while its pending mark clears.
        # Allow the shared 350ms scroll guard to settle before the next answer.
        await page.wait_for_timeout(450)
        c = read(namespace, token)['careers']['laundry']
        paper = mastery._paper('laundry', c['mastery']['exam'])
        option = next(o['id'] for o in paper[index]['options'] if o['score'] == (2 if good else 0))
        buttons = page.locator('[data-command="mastery_answer"]')
        payloads = await buttons.evaluate_all("bs=>bs.map(b=>JSON.parse(b.dataset.payload))")
        button = buttons.nth(next(i for i,p in enumerate(payloads) if p['option'] == option))
        await send_click(page, button, 'mastery_answer')
        if reload and index == 1:
            before = copy.deepcopy(read(namespace, token)['careers']['laundry']['mastery']['exam'])
            await page.reload()
            await open_mastery(page)
            after = read(namespace, token)['careers']['laundry']['mastery']['exam']
            assert before == after
            await shot(page, tag, 'review-reloaded', rows)
    await page.locator('[data-command="mastery_finish"]').wait_for()
    await send_click(page, page.locator('[data-command="mastery_finish"]'), 'mastery_finish')
    await page.locator('.cm-result').filter(has_text='8/8' if good else '0/8').wait_for()


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    cases, errors = [], []
    desktop_only = '--desktop-only' in sys.argv
    if desktop_only:
        old = json.loads((OUT/'report.json').read_text(encoding='utf-8'))
        assert old['version'] == __version__
        cases = [c for c in old['cases'] if c['case'].startswith('390-')]
        errors = old['browser_errors']
    with server() as (base, namespace):
        print('Mastery browser server: ' + base, flush=True)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for width in ((1280,) if desktop_only else (390, 1280)):
                for modern in (False, True):
                    tag = f'{width}-' + ('new' if modern else 'classic')
                    context = await browser.new_context(viewport=dict(width=width, height=860))
                    page = await context.new_page()
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    try:
                        await page.goto(base)
                        await page.wait_for_selector('#app:not([hidden])', timeout=45000)
                        token = next(c['value'] for c in await context.cookies() if c['name']=='mnl_session')
                        seed(namespace, token, modern)
                        await page.reload()
                        await open_mastery(page)
                        rows=[]
                        await shot(page, tag, 'ready', rows)
                        await assessment(page, namespace, token, False, tag, rows)
                        await page.locator('.cm-retry').filter(has_text='3 ngày').wait_for()
                        assert await page.locator('[data-command="mastery_start"]').count()==0
                        await shot(page, tag, 'retry', rows)
                        # A second isolated ready fixture exercises success without waiting on game days.
                        seed(namespace, token, modern)
                        await page.reload()
                        await open_mastery(page)
                        await assessment(page, namespace, token, True, tag, rows, reload=True)
                        assert read(namespace, token)['careers']['laundry']['mastery']['tier']==1
                        await shot(page, tag, 'earned', rows)
                        cases.append(dict(case=tag,passed=True,wrong_review_retry=True,correct_review=True,reload_preserved=True,checks=rows))
                        for extension in ('png','html'):
                            (OUT/f'{tag}-FAILED.{extension}').unlink(missing_ok=True)
                        print(tag + ': passed', flush=True)
                    except Exception:
                        await page.screenshot(path=str(OUT / f'{tag}-FAILED.png'))
                        (OUT/f'{tag}-FAILED.html').write_text(await page.content(),encoding='utf-8')
                        raise
                    finally:
                        await context.close()
                    (OUT/'report.json').write_text(json.dumps(dict(version=__version__,cases=cases,browser_errors=errors),ensure_ascii=False,indent=2),encoding='utf-8')
            await browser.close()
    assert len(cases)==4 and not errors, errors


if __name__ == '__main__':
    if sys.platform=='win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
