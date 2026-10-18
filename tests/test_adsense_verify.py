"""📺 AdSense site check (owner 19/10): the page carries <meta name="google-adsense-account"> and /ads.txt answers the
publisher line, with NO ad script and no ad host in the CSP (nothing is shown before rewarded ads are built)."""
import os
import unittest
from unittest.mock import patch

from game import observability
from game.webassets import WebAssets
from server import CSP, PUBLIC


class AdsenseVerifyTests(unittest.TestCase):
    def test_meta_without_any_ad_script(self):
        with patch.dict(os.environ, {}, clear=True):
            snap = WebAssets(PUBLIC, CSP, release='test').snapshot()
        page = snap.html.decode() if isinstance(snap.html, bytes) else snap.html
        self.assertIn('<meta name="google-adsense-account" content="ca-pub-9603813200470438">', page)
        for word in ('adsbygoogle', 'googlesyndication', 'doubleclick'):
            self.assertNotIn(word, page)
            self.assertNotIn(word, snap.csp)

    def test_ads_txt_line(self):
        self.assertEqual(observability.ads_txt(), 'google.com, pub-9603813200470438, DIRECT, f08c47fec0942fa0\n')


if __name__ == '__main__':
    unittest.main()
