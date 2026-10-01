"""🎓 Giấy chứng nhận: a browser walk-through of the diploma (dev tool, needs `pip install playwright` + chromium).

Runs the real app on a throwaway story-mode server (as scripts/browser_housing.py) and seeds one save straight in
its database: a named character in an áo dài with round glasses, a certificate passed before 1.3 (no real date
stored: the diploma prints the life day only) and a paid class whose exam is open now. Then, in the browser:
the profile badge opens the old diploma (zoom, "Tải ảnh" = a real PNG download, the souvenir photo, "Lưu vào Kỷ
niệm"), the exam is answered right through, and the reveal shows the new diploma. Also an iPhone pass (no Web
Share in headless Chromium: the long-press view) and the English diploma.

Screens at 390x844 and 1280x860; exit 1 on any console error or a missing step.

    python scripts/browser_cert_diploma.py [out_dir] [--lang vi|en|both]
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = Path(args[0]) if args else ROOT.parent / '_cert_shots'
LANGS = {'vi': ['vi'], 'en': ['en'], 'both': ['vi', 'en']}[next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--lang=')), 'both')]
OLD, NEW = 'work_safety', 'customer_service'
KEY = {}   # token → [(question, right option)] of the open exam


def seed(db: str, token: str, lang: str) -> None:
    from game import certificates as ct
    from game import marriage as mr
    from game import wardrobe as wd
    from game import whats_new as wn
    from game.storage import Store
    store = Store(db, story=True)

    def fn(s):
        j = s['journey']
        s['name'] = 'Nguyễn Minh Khuê'
        s['settings']['whatsNewSeen'] = wn.newer(s['settings'].get('whatsNewSeen', ''), wn.LATEST)
        s['settings']['lang'] = lang
        j.update(gender='female', intro=True, life_day=12, wallet=800)
        look = dict(wd.default_look('female'), top='ao_dai', acc='kinh_tron', hair='toc_dai', shoes='giay_do')
        s[wd.KEY] = dict(v=wd.VERSION, look=look, owned=[x for x in look.values() if isinstance(x, str) and x in wd.BUYABLE])
        # passed in 1.2: no `earned_on`
        j['certificates'][OLD] = dict(score=83, best=83, earned_day=5, attempts=2)
        ct.action(s, 'jr_cert_enrol', {'cert': NEW, 'mode': 'class'})
        paper = j['study']['paper']
        KEY[token] = [(q, ct.KEY[NEW][q]['answer']) for q in paper['qs']]
    mr._mutate(store, {store.key(token): fn})
    store.close_pool()


def album_of(db: str, token: str) -> list:
    """The photos kept in Kỷ niệm (any workplace): (title, data URL head, length)."""
    from game.storage import Store
    store = Store(db, story=True)
    try:
        state = store.read(token)[0]
    finally:
        store.close_pool()
    return [(p['title'], p['image'][:23], len(p['image'])) for c in state['careers'].values() for p in c.get('album') or []]


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors, report = [], []
    with server() as (base, db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            runs = [(390, 844, lang, False) for lang in LANGS] + [(1280, 860, lang, False) for lang in LANGS[:1]] + [(390, 844, LANGS[0], True)]
            for w, h, lang, iphone in runs:
                opts = dict(viewport=dict(width=w, height=h), accept_downloads=True)
                if iphone:
                    opts.update(user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                                has_touch=True, is_mobile=True, device_scale_factor=2)
                ctx = await browser.new_context(**opts)
                page = await ctx.new_page()
                page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.goto(base)
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                token = next(c['value'] for c in await ctx.cookies() if c['name'] == 'mnl_session')
                seed(db, token, lang)
                await page.reload()
                await page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await page.wait_for_timeout(1500)
                tag = f'{w}x{h}-{lang}' + ('-iphone' if iphone else '')

                async def popups():
                    for _ in range(4):
                        b = page.locator('[data-wn="close"]:visible, [data-action="jrSceneClose"]:visible')
                        if not await b.count():
                            break
                        await b.first.click()
                        await page.wait_for_timeout(400)
                    # a life card or a story scene that came up on its own (not what this walk is about)
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#dpDialog)').forEach(d=>d.close())")

                async def click(sel):
                    try:
                        await page.click(sel, timeout=4000)
                        return
                    except Exception:
                        pass
                    # A life card ("lfScene", v4/life.js) keeps coming back over the sheet after each state change
                    # in this seeded save: close it and press the control directly.
                    await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet):not(#dpDialog)').forEach(d=>d.close())")
                    try:
                        await page.click(sel, timeout=3000)
                    except Exception:
                        what = await page.evaluate("""s=>{const b=document.querySelector(s);if(!b)return 'missing';const r=b.getBoundingClientRect();
                          const e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                          return {box:[r.x,r.y,r.width,r.height],disabled:b.disabled,on:e&&e.outerHTML.slice(0,160),dialogs:[...document.querySelectorAll('dialog[open]')].map(d=>d.id)};}""", sel)
                        print('click failed', tag, sel, what)
                        await page.screenshot(path=str(OUT / f'{tag}-zz-failed.png'))
                        raise

                async def shot(name, wait=450):
                    await page.wait_for_timeout(wait)
                    await page.screenshot(path=str(OUT / f'{tag}-{name}.png'))

                await popups()
                await page.wait_for_selector('.jr-me', timeout=15000)

                # 1. The profile badge of the 1.2 pass opens its diploma.
                badge = page.locator(f'.ct-badge[data-cert="{OLD}"]')
                await badge.scroll_into_view_if_needed()
                await shot('1-profile')
                await badge.click()
                await page.wait_for_selector('#dpDialog[open] .dp-sheet svg', timeout=10000)
                await shot('2-old-diploma', 700)
                txt = await page.inner_text('#dpDialog')
                svg = await page.inner_html('#dpDialog .dp-sheet')
                report.append((tag, 'old diploma', 'PCC-WS-' in svg, 'Ngày sống thứ 5' in svg or 'life day 5' in svg))
                if iphone:
                    # "Tải ảnh" on an iPhone without Web Share: the image to long-press
                    await click('#dpDialog [data-action="jrCertDipSave"]')
                    await page.wait_for_selector('#dpDialog .dp-hold img', timeout=15000)
                    await shot('3-hold')
                    src = await page.get_attribute('#dpDialog .dp-hold img', 'src')
                    report.append((tag, 'hold view', src[:22]))
                    await click('#dpDialog [data-action="jrCertDipClose"]')
                    await ctx.close()
                    continue
                await click('#dpDialog [data-action="jrCertDipZoom"]')
                await shot('3-old-diploma-zoom')
                await click('#dpDialog [data-action="jrCertDipZoom"]')
                async with page.expect_download(timeout=20000) as dl:
                    await click('#dpDialog [data-action="jrCertDipSave"]')
                d = await dl.value
                path = OUT / f'{tag}-{d.suggested_filename}'
                await d.save_as(str(path))
                report.append((tag, 'download', d.suggested_filename, path.stat().st_size, path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'))
                # 2. The souvenir photo: download and keep in Kỷ niệm.
                await click('#dpDialog [data-action="jrCertDipView"][data-view="photo"]')
                await page.wait_for_selector('#dpDialog .dp-photo img', timeout=20000)
                await shot('4-photo', 600)
                async with page.expect_download(timeout=20000) as dl:
                    await click('#dpDialog [data-action="jrCertDipSave"][data-kind="photo"]')
                d = await dl.value
                path = OUT / f'{tag}-{d.suggested_filename}'
                await d.save_as(str(path))
                report.append((tag, 'photo download', d.suggested_filename, path.stat().st_size))
                await click('#dpDialog [data-action="jrCertDipKeep"]')
                await shot('4b-kept', 1500)
                await popups()   # a title earned on the way (the seeded wallet) opens over the diploma
                report.append((tag, 'album', album_of(db, token)))
                await popups()
                await click('#dpDialog [data-action="jrCertDipClose"]')
                await page.wait_for_timeout(300)
                # 3. The exam of the class: answer right through, the reveal opens.
                await click('[data-action="jrCerts"]:not(.ct-badge)')
                await page.wait_for_selector('.ct-exam', timeout=10000)
                await shot('5-exam')
                for q, opt in KEY[token]:
                    sel = f'.ct-opt[data-q="{q}"][data-option="{opt}"]'
                    await popups()
                    await page.wait_for_selector(sel, timeout=10000)
                    await click(sel)
                    await page.wait_for_timeout(250)
                await page.wait_for_selector('#dpDialog[open].reveal', timeout=15000)
                await page.wait_for_timeout(300)
                await popups()
                await shot('6-reveal', 650)
                await shot('7-reveal-settled', 2600)
                svg = await page.inner_html('#dpDialog .dp-sheet')
                report.append((tag, 'new diploma', 'PCC-CS-' in svg, any(x in svg for x in ('tháng', 'October', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'November', 'December'))))
                await click('#dpDialog [data-action="jrCertDipView"][data-view="photo"]')
                await page.wait_for_selector('#dpDialog .dp-photo img', timeout=20000)
                await shot('8-new-photo', 600)
                await click('#dpDialog [data-action="jrCertDipClose"]')
                await page.wait_for_timeout(500)
                await popups()
                await page.evaluate("document.querySelectorAll('dialog[open]:not(#sheet)').forEach(d=>d.close())")
                card = page.locator('.ct-result')
                if await card.count():
                    await card.first.scroll_into_view_if_needed()
                await shot('9-centre-after')
                if lang == 'en':
                    misses = await page.evaluate("[...(globalThis.__i18nMisses||[])].filter(s=>/chứng|Giấy|Kỷ niệm|ảnh|Tải|Chúc mừng|phóng|Nhấn/i.test(s))")
                    report.append((tag, 'i18n misses (diploma)', misses))
                await ctx.close()
            await browser.close()
    for r in report:
        print(*r)
    real = [e for e in errors if 'favicon' not in e]
    print('errors:', real or 'none')
    print('shots:', OUT)
    return 1 if real else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
