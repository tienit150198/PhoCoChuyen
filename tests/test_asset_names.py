"""Asset file names that ad blockers block (Cốc Cốc's built-in blocker, uBlock, AdGuard lists).

A generic rule such as `ads.js` matched public/js/scenes/reads.js ("re-ads.js"): the module graph of app.js failed
to load and the page stayed on the splash (owner, 03/10: "Cốc Cốc tới bước tải cuối thấy dừng luôn"). No file the
page loads may carry one of these fragments in its path. A module loaded late with its failure caught (telemetry,
the analytics preferences) may, since the game runs without it; it is listed below."""
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'public')
BLOCKED = re.compile(r'ads\.|ads/|/ads|[-_.]ad[-_.]|/ad[-_.]|advert|banner|pop-?up|popunder|sponsor|track|beacon|pixel\.|analytics|adsbygoogle|affiliat', re.I)
OPTIONAL = {'js/telemetry.js', 'js/analytics-preferences.js'}   # dynamic import(), .catch(): the game starts without them


class AssetNames(unittest.TestCase):
    def test_no_page_asset_has_a_name_ad_blockers_match(self):
        bad = []
        for top in ('js', 'css', 'icons', 'audio', 'music', 'i18n'):
            base = os.path.join(ROOT, top)
            for d, _, files in os.walk(base):
                for f in files:
                    rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')
                    if rel not in OPTIONAL and BLOCKED.search('/' + rel):
                        bad.append(rel)
        self.assertEqual(bad, [], 'rename these: an ad blocker would stop them loading')

    def test_the_pattern_catches_the_cases_that_bit(self):
        for name in ('/js/scenes/reads.js', '/js/v4/popup-gate.js', '/css/banner.css', '/js/ads/x.js'):
            self.assertTrue(BLOCKED.search(name), name)
        for name in ('/js/scenes/room-watch.js', '/js/v4/break-gate.js', '/js/v4/loads-later.js', '/js/headstart.js'):
            self.assertFalse(BLOCKED.search(name), name)


if __name__ == '__main__':
    unittest.main()
