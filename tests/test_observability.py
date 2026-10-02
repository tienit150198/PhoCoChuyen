"""Public configuration, CSP and Search Console integration (no real Google calls)."""
import html
import json
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from game.webassets import WebAssets
from server import CSP, PUBLIC

CONFIG = {
    'SITE_URL': 'https://phocochuyen.io.vn',
    'FIREBASE_API_KEY': 'web-public-key',
    'FIREBASE_PROJECT_ID': 'pho-co-chuyen',
    'FIREBASE_APP_ID': '1:123:web:abc',
    'FIREBASE_MESSAGING_SENDER_ID': '123',
    'FIREBASE_MEASUREMENT_ID': 'G-ABC123',
}


class ObservabilityTests(unittest.TestCase):
    def snapshot(self, env):
        with patch.dict(os.environ, env, clear=True):
            return WebAssets(PUBLIC, CSP, release='test').snapshot()

    def test_no_config_means_no_third_party_sdk_or_csp(self):
        snap = self.snapshot({})
        self.assertNotIn('google-analytics.com', snap.csp)
        self.assertNotIn('mnl-observability', snap.html.decode())

    def test_config_has_only_public_whitelisted_fields(self):
        snap = self.snapshot(dict(CONFIG, LLM_API_KEY='never-expose', DATABASE_URL='private-db'))
        page = snap.html.decode()
        found = re.search(r'<meta name="mnl-observability" content="([^"]+)">', page)
        self.assertIsNotNone(found, 'Firebase configuration must be injected in the rendered page')
        cfg = json.loads(html.unescape(found.group(1)))
        self.assertEqual(cfg['firebase']['measurementId'], 'G-ABC123')
        self.assertEqual(cfg['origin'], 'https://phocochuyen.io.vn')
        self.assertNotIn('never-expose', page)
        self.assertNotIn('private-db', page)
        self.assertIn('https://www.gstatic.com', snap.csp)
        self.assertIn('https://*.google-analytics.com', snap.csp)
        self.assertIn('https://firebase.googleapis.com', snap.csp.split('connect-src')[1].split(';')[0])
        self.assertNotIn("'unsafe-inline'", snap.csp.split('style-src')[0])

    def test_incomplete_config_does_not_enable_google(self):
        env = dict(CONFIG)
        del env['FIREBASE_APP_ID']
        snap = self.snapshot(env)
        self.assertNotIn('mnl-observability', snap.html.decode())
        self.assertNotIn('google-analytics.com', snap.csp)

    def test_verification_is_in_head_and_canonical_is_public(self):
        page = self.snapshot(dict(SITE_URL='https://phocochuyen.io.vn/', GOOGLE_SITE_VERIFICATION='verify-123')).html.decode()
        self.assertIn('<meta name="google-site-verification" content="verify-123">', page.split('</head>')[0])
        self.assertIn('<link rel="canonical" href="https://phocochuyen.io.vn/">', page)

    def test_verification_cannot_inject_markup(self):
        page = self.snapshot({'GOOGLE_SITE_VERIFICATION': '\"><script src="https://evil.example"></script>'}).html.decode()
        self.assertNotIn('<script src="https://evil.example">', page)

    def test_sitemap_and_robots_only_advertise_public_pages(self):
        from xml.etree import ElementTree
        root = ElementTree.fromstring((PUBLIC / 'sitemap.xml').read_text())
        locs = [node.text for node in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        self.assertEqual(locs, ['https://phocochuyen.io.vn/'])
        robots = (PUBLIC / 'robots.txt').read_text()
        self.assertIn('Sitemap: https://phocochuyen.io.vn/sitemap.xml', robots)
        self.assertIn('Disallow: /admin', robots)
        self.assertIn('Disallow: /api/', robots)
        self.assertNotIn('Disallow: /js/', robots)


if __name__ == '__main__':
    unittest.main()
