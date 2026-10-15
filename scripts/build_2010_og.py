"""💐 Thiệp 20/10: the share pictures (og:image, 1200×630) for every theme → public/icons/2010/og-<theme>.png.

game/event2010.py head_tags points a card's link preview (Zalo, Facebook, Messenger) at its theme's picture. Each one
is /2010?og=<theme> (public/js/event2010.js ogView: the theme's own art, the copy "Bạn có một tấm thiệp 💌")
photographed by chromium on a throwaway server, then reduced to a 256-colour PNG. Rerun after changing a theme's art.

    python scripts/build_2010_og.py          (needs playwright + chromium, TEST_DATABASE_URL)
"""
import asyncio
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from browser_housing import server  # noqa: E402
from game.event2010 import THEMES  # noqa: E402

OUT = ROOT / 'public' / 'icons' / '2010'


async def main() -> int:
    from PIL import Image
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with server() as (base, _db):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport=dict(width=1200, height=630), device_scale_factor=1, reduced_motion='reduce')
            page.on('pageerror', lambda e: errors.append(str(e)))
            for theme in THEMES:
                await page.goto(f'{base}/2010?og={theme}')
                await page.wait_for_selector('.ev-og-wrap', timeout=20000)
                await page.evaluate('document.fonts.ready')
                await page.wait_for_timeout(300)
                png = await page.screenshot(clip=dict(x=0, y=0, width=1200, height=630))
                img = Image.open(io.BytesIO(png)).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
                img.save(OUT / f'og-{theme}.png', optimize=True)
                print(theme, (OUT / f'og-{theme}.png').stat().st_size)
            await browser.close()
    print('errors:', errors)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
