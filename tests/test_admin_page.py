"""Operator site (/admin): the page itself (HTML, CSP, noindex, assets) and the flow it
uses against the existing endpoints: bootstrap -> account login -> admin-only APIs.
The page adds no privileges: every admin endpoint still answers 401/403 to others."""
import http.client, json, os, re, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch

from game import admin_stats as st
from game.storage import Store
from server import GameServer, PAGES

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
ADMIN_JS = PUBLIC / 'js' / 'admin'
PW = 'matkhau-rat-dai'
REG = dict(password=PW, confirm=PW, display='Người Thử')


class AdminPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'op_admin'})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.server.store.close_pool(); cls.temp.cleanup(); cls.env.stop()
        st.clear_cache()

    def setUp(self):
        self.server.limits.clear()
        st.clear_cache()

    # ---- helpers ------------------------------------------------------------------
    def raw(self, path, method='GET', headers=None, body=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        h.update(headers or {})
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=15)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse(); data = res.read(); hdrs = dict(res.getheaders()); con.close()
        return res.status, hdrs, data

    def req(self, dev, path, method='GET', body=None, csrf=True):
        h = {}
        if dev.get('cookie'): h['Cookie'] = dev['cookie']
        if csrf and dev.get('csrf'): h['X-Game-CSRF'] = dev['csrf']
        if body is not None: h['Content-Type'] = 'application/json'; body = json.dumps(body)
        status, hdrs, raw = self.raw(path, method, h, body)
        data = json.loads(raw or b'{}')
        if 'Set-Cookie' in hdrs: dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(data, dict) and data.get('csrf'): dev['csrf'] = data['csrf']
        return status, data

    def device(self):
        dev = {}
        self.assertEqual(self.req(dev, '/api/bootstrap')[0], 200)
        return dev

    def registered(self, name):
        """An account whose save lives on a device the page never sees."""
        dev = self.device()
        status, data = self.req(dev, '/api/account/register', 'POST', dict(REG, username=name))
        self.assertIn(status, (200, 409), data)   # 409: already made by an earlier test
        return dev

    def page_login(self, name, password=PW):
        """What public/js/admin/api.js does: bootstrap, POST login with that CSRF, then /api/feedback/mine."""
        dev = self.device()
        status, out = self.req(dev, '/api/account/login', 'POST', dict(username=name, password=password))
        return dev, status, out

    # ---- the page ---------------------------------------------------------------------
    def test_admin_route_serves_its_own_page(self):
        self.assertEqual(PAGES['/admin'], 'admin.html')
        status, h, body = self.raw('/admin')
        self.assertEqual(status, 200)
        self.assertTrue(h['Content-Type'].startswith('text/html'))
        html = body.decode()
        csp = h['Content-Security-Policy']
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn('noindex', h.get('X-Robots-Tag', ''))
        self.assertRegex(html, r'<meta name="robots" content="noindex[^"]*">')
        self.assertIn('<script type="module" src="/js/admin/main.js"></script>', html)
        self.assertIn('/css/admin/admin.css', html)
        # Its own shell, not the game's; no inline script (CSP would block it anyway).
        self.assertNotIn('/js/boot.js', html)
        self.assertNotIn('/css/app.css', html)
        self.assertFalse(re.search(r'<script(?![^>]*\bsrc=)[^>]*>', html), 'inline <script> in admin.html')
        self.assertNotIn('Set-Cookie', h)   # opening the page creates no session by itself
        self.assertEqual(self.raw('/admin', 'HEAD')[0], 200)
        # The game's pages stay indexable.
        self.assertNotIn('X-Robots-Tag', self.raw('/')[1])

    def test_admin_assets_resolve(self):
        html = (PUBLIC / 'admin.html').read_text(encoding='utf-8')
        for ref in re.findall(r'(?:src|href)="(/[^"]+)"', html):
            status, h, _ = self.raw(ref)
            self.assertEqual(status, 200, ref)
        for ref, ctype in (('/js/admin/main.js', 'text/javascript'), ('/css/admin/admin.css', 'text/css')):
            self.assertTrue(self.raw(ref)[1]['Content-Type'].startswith(ctype), ref)
        css = (PUBLIC / 'css' / 'admin' / 'admin.css').read_text(encoding='utf-8')
        for font in set(re.findall(r'url\((/fonts/[^)]+)\)', css)):
            self.assertTrue((PUBLIC / font.lstrip('/')).is_file(), font)
        self.assertFalse(re.search(r'@import|url\((?!/fonts/)', css), 'admin.css must stay self-contained')
        for js in ADMIN_JS.glob('*.js'):
            for ref in re.findall(r"""from\s+'(\.[^']+)'""", js.read_text(encoding='utf-8')):
                self.assertTrue((js.parent / ref).resolve().is_file(), f'{js.name}: {ref}')

    def test_admin_js_keeps_secrets_out_of_storage(self):
        src = '\n'.join(p.read_text(encoding='utf-8') for p in ADMIN_JS.glob('*.js'))
        self.assertNotIn('sessionStorage', src)
        self.assertNotIn('document.cookie', src)
        # Only display preferences are remembered.
        keys = set(re.findall(r"store\.set\('([a-z]+)'", src))
        self.assertEqual(keys, {'theme', 'range', 'auto'})

    # ---- the flow it uses -----------------------------------------------------------------
    def test_admin_flow_through_existing_endpoints(self):
        self.registered('op_admin')
        dev, status, out = self.page_login('op_admin')
        self.assertEqual(status, 200, out)
        for secret in ('token', 'pw'):
            self.assertNotIn(secret, out)
        self.assertIs(self.req(dev, '/api/feedback/mine')[1]['admin'], True)
        status, stats = self.req(dev, '/api/admin/stats?range=7')
        self.assertEqual(status, 200, stats)
        self.assertIn('server', stats)
        self.assertEqual(self.req(dev, '/api/admin/feedback?status=new')[0], 200)
        # Logging out on the page drops the rights at once.
        self.assertEqual(self.req(dev, '/api/account/logout', 'POST', {})[0], 200)
        _, boot = self.req(dev, '/api/bootstrap')
        self.assertIs(boot['admin'], False)
        self.assertEqual(self.req(dev, '/api/admin/stats')[0], 403)

    def test_admin_endpoints_still_refuse_others(self):
        anon = self.device()
        self.registered('regular_joe')
        player, status, _ = self.page_login('regular_joe')
        self.assertEqual(status, 200)
        self.assertIs(self.req(player, '/api/feedback/mine')[1]['admin'], False)
        for dev in (anon, player):
            self.assertEqual(self.req(dev, '/api/admin/stats')[0], 403)
            self.assertEqual(self.req(dev, '/api/admin/feedback')[0], 403)
            self.assertEqual(self.req(dev, '/api/admin/feedback', 'POST', dict(id=1, status='done'))[0], 403)
        self.assertEqual(self.req({}, '/api/admin/stats')[0], 401)
        self.assertEqual(self.req({}, '/api/admin/feedback')[0], 401)
        # An admin cookie without the CSRF header is refused too.
        self.registered('op_admin')
        admin, _, _ = self.page_login('op_admin')
        self.assertEqual(self.req(admin, '/api/admin/stats', csrf=False)[0], 403)

    def test_login_does_not_reveal_accounts(self):
        self.registered('op_admin')
        _, s1, wrong = self.page_login('op_admin', 'khong-dung-mat-khau')
        _, s2, nobody = self.page_login('khong_co_ai', 'khong-dung-mat-khau')
        self.assertEqual((s1, s2), (401, 401))
        strip = lambda d: {k: v for k, v in d.items() if k not in ('server_time', 'server_recv')}
        self.assertEqual(strip(wrong), strip(nobody))


if __name__ == '__main__':
    unittest.main()
