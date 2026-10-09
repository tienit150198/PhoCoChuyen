"""🎙️ Phòng hát mic trực tiếp, the pure parts and the game server (game/karaoke_mic.py, live/sfu.py, live/config.py,
server.py headers): the age rule, the birth year stored once on the account (account_birth), the tokens (what each
side may do, signed, expiring), the switch (off: headers and routes exactly as before), the admin tools, and that the
browser module pins the same SDK the CSP allows. The rooms themselves: tests/test_live_karaoke_mic.py."""
import base64
import hashlib
import os
import re
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import karaoke as kg
from game import karaoke_mic as km
from live import config as lc
from live.sfu import Sfu, room_name, sign, verify
from tests.test_karaoke import Base

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'x' * 40


def server_module():
    import server
    return server


class AgeRule(unittest.TestCase):
    def test_youngest_possible_age(self):
        t = time.mktime((2026, 10, 7, 12, 0, 0, 0, 0, -1))
        self.assertEqual(km.vn_year(t), 2026)
        self.assertTrue(km.age_ok(2009, t))      # 16 or 17 this year: at least 16
        self.assertFalse(km.age_ok(2010, t))     # 15 or 16: maybe 15, listening only
        self.assertFalse(km.age_ok(2020, t))
        self.assertTrue(km.age_ok(1950, t))
        for bad in (None, '2000', 2000.0, 1800, True):
            self.assertFalse(km.age_ok(bad, t), bad)
        self.assertTrue(km.age_ok(2010, time.mktime((2027, 1, 2, 12, 0, 0, 0, 0, -1))))

    def test_account_age(self):
        t = time.time()
        old = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - 2 * 86400))
        new = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - 3600))
        self.assertTrue(km.account_old_enough(old, t))
        self.assertFalse(km.account_old_enough(new, t))
        self.assertFalse(km.account_old_enough(None, t))


class Tokens(unittest.TestCase):
    def setUp(self):
        self.sfu = Sfu('wss://phocochuyen.io.vn/sfu', 'http://127.0.0.1:7880', 'APIkey', SECRET)

    def test_singer_token(self):
        t = time.time()
        c = verify(self.sfu.token('a' * 16, 'Lan', 'kara-tre.x.1', publish=True, ttl=120, now=t), SECRET, t)
        v = c['video']
        self.assertEqual((c['iss'], c['sub'], c['name']), ('APIkey', 'a' * 16, 'Lan'))
        self.assertEqual(v, dict(room='kara-tre.x.1', roomJoin=True, canPublish=True, canPublishSources=['microphone'], canSubscribe=False,
                                 canPublishData=False, canUpdateOwnMetadata=False))
        self.assertAlmostEqual(c['exp'] - t, 120, delta=1)

    def test_listener_token(self):
        c = verify(self.sfu.token('b' * 16, 'Minh', 'kara-tre.x.1', publish=False, ttl=km.LISTEN_TTL), SECRET)
        v = c['video']
        self.assertEqual((v['canPublish'], v['canPublishSources'], v['canSubscribe'], v['canPublishData'], v['hidden']), (False, [], True, False, True))
        for grant in ('recorder', 'roomRecord', 'roomAdmin', 'roomCreate', 'roomList', 'ingressAdmin'):
            self.assertNotIn(grant, v)

    def test_signature_and_expiry(self):
        tok = self.sfu.token('a' * 16, 'Lan', 'r', publish=True, ttl=30)
        self.assertIsNone(verify(tok, 'another-secret-another-secret-another'))
        head, body, mac = tok.split('.')
        forged = sign(dict(verify(tok, SECRET), video=dict(room='r', roomJoin=True, roomAdmin=True)), 'wrong')
        self.assertIsNone(verify(forged, SECRET))
        self.assertIsNone(verify(f'{head}.{body}x.{mac}', SECRET))
        self.assertIsNone(verify(tok, SECRET, time.time() + 3600))   # expired
        self.assertIsNone(verify('garbage', SECRET))

    def test_room_names_never_repeat(self):
        names = {room_name('kara:tre-2', e, n) for e in ('kf-a', 'kf-b', 'r-1') for n in (1, 2)}
        self.assertEqual(len(names), 6)
        self.assertTrue(all(re.fullmatch(r'kara-tre-2\.[0-9a-f]{10}\.\d', x) for x in names))

    def test_unconfigured_sfu_calls_nothing(self):
        import asyncio
        s = Sfu('', '', '', '')
        self.assertFalse(s.configured)
        self.assertFalse(asyncio.run(s.create_room('x', 10)))
        self.assertEqual(s.calls, 0)


class Switch(unittest.TestCase):
    ENV = ('LIVE_KARAOKE', 'LIVE_KARAOKE_MIC', 'LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'LIVEKIT_API_URL', 'DATABASE_URL')

    def cfg(self, **env):
        base = {k: '' for k in self.ENV}
        base.update(DATABASE_URL='postgresql://x@127.0.0.1/x', **env)
        with patch.dict(os.environ, base):
            return lc.from_env([])

    def test_live_service_switch(self):
        full = dict(LIVE_KARAOKE='1', LIVE_KARAOKE_MIC='1', LIVEKIT_URL='wss://h/sfu', LIVEKIT_API_KEY='k', LIVEKIT_API_SECRET=SECRET)
        self.assertTrue(self.cfg(**full).flags()['kara_mic'])
        self.assertFalse(self.cfg(**dict(full, LIVE_KARAOKE_MIC='0')).flags()['kara_mic'])     # default off
        self.assertFalse(self.cfg(**dict(full, LIVE_KARAOKE='0')).flags()['kara_mic'])         # needs the rooms
        self.assertFalse(self.cfg(**dict(full, LIVEKIT_API_SECRET='')).flags()['kara_mic'])    # needs the SFU
        self.assertEqual(self.cfg(**full).sfu_api, 'http://127.0.0.1:7880')
        self.assertFalse(lc.Config().flags()['kara_mic'])

    def test_headers_off_are_unchanged(self):
        srv = server_module()
        csp = srv.CSP if not km.enabled() else None
        base_perm = 'camera=(), microphone=(), geolocation=(), payment=()'
        self.assertEqual(srv.mic_headers('CSP-X', base_perm, False, 'wss://h'), ('CSP-X', base_perm))
        if csp is not None:   # this process runs with the switch off: the module's headers are today's
            self.assertEqual(srv.PERMISSIONS, base_perm)
            self.assertNotIn('jsdelivr', srv.CSP)
            self.assertIn("connect-src 'self';", srv.CSP)

    def test_headers_on(self):
        srv = server_module()
        perm = 'camera=(), microphone=(), geolocation=(), payment=()'
        csp, p = srv.mic_headers(srv.CSP, perm, True, 'wss://phocochuyen.io.vn/sfu')
        self.assertEqual(p, 'camera=(), microphone=(self), geolocation=(), payment=()')
        d = {x.split()[0]: x.split()[1:] for x in csp.split(';') if x.strip()}
        self.assertEqual(d['script-src'], ["'self'", srv.KARA_MIC_SDK, 'https://www.youtube.com', 'https://s.ytimg.com'])
        self.assertEqual(d['connect-src'], ["'self'", 'wss://phocochuyen.io.vn', 'https://phocochuyen.io.vn'])
        for k in ('default-src', 'object-src', 'frame-ancestors', 'base-uri', 'form-action', 'frame-src', 'img-src', 'media-src', 'worker-src'):
            self.assertEqual(d[k], {x.split()[0]: x.split()[1:] for x in srv.CSP.split(';') if x.strip()}[k], k)   # the rest as strict as before
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertNotIn('https://cdn.jsdelivr.net ', csp + ' ')   # the one file, never the whole CDN
        for bad in ('javascript:alert(1)', 'wss://evil host', 'ftp://x', ''):
            self.assertIn("connect-src 'self';", srv.mic_headers(srv.CSP, perm, True, bad)[0], bad)
        self.assertIn("connect-src 'self' ws://127.0.0.1:7880 http://127.0.0.1:7880;", srv.mic_headers(srv.CSP, perm, True, 'ws://127.0.0.1:7880')[0])

    def test_browser_module_pins_the_same_sdk(self):
        js = (ROOT / 'public/js/v4/karaoke-mic.js').read_text(encoding='utf-8')
        self.assertIn(f"urls:['/js/vendor/livekit-client-2.22.3.umd.js','{server_module().KARA_MIC_SDK}']", js)   # our copy first, then the CDN
        self.assertRegex(js, r"sri:'sha384-[A-Za-z0-9+/]{64}'")
        # our copy is the very file jsDelivr serves: the same SRI checks both (and the release never minifies vendor/)
        own = (ROOT / 'public/js/vendor/livekit-client-2.22.3.umd.js').read_bytes()
        sri = 'sha384-' + base64.b64encode(hashlib.sha384(own).digest()).decode()
        self.assertIn(f"sri:'{sri}'", js)
        self.assertTrue((ROOT / 'public/js/vendor/livekit-client.LICENSE').is_file())
        import importlib.util
        spec = importlib.util.spec_from_file_location('build_static', ROOT / 'scripts/build_static.py')
        bs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bs)
        self.assertNotIn(ROOT / 'public/js/vendor/livekit-client-2.22.3.umd.js', bs.sources(ROOT, '.js'))
        self.assertIn('s.integrity=SDK.sri', js)
        self.assertIn("s.crossOrigin='anonymous'", js)
        self.assertIn('echoCancellation:true,noiseSuppression:true', js)
        code = re.sub(r'/\*.*?\*/|//[^\n]*', '', js, flags=re.S)
        for never in ('MediaRecorder', 'canPublish', 'recorder', 'captureStream'):   # nothing records; a page never grants itself anything
            self.assertNotIn(never, code)


class BirthYear(Base):
    def test_set_once_and_the_gate(self):
        a = self.user('lan')
        with patch.dict(os.environ, LIVE_KARAOKE_MIC='1'):
            young = km.vn_year() - 15
            out = km.birth(self.store, a, dict(year=young))
            self.assertEqual((out['year'], out['mic'], out['fixed']), (young, False, False))
            again = km.birth(self.store, a, dict(year=1990))   # a second try with another year does not change it
            self.assertEqual((again['year'], again['mic'], again['fixed']), (young, False, True))
            b = self.user('minh')
            self.assertTrue(km.birth(self.store, b, dict(year=2000))['mic'])
            self.assertEqual(km.birth_of(self.store, self.store.key(b)), 2000)
            for bad in (None, '2000', 1900, km.vn_year() + 1, 2000.5, True):
                with self.assertRaises(kg.KaraError, msg=bad):
                    km.birth(self.store, b, dict(year=bad))
            g, _, _ = self.store.session()
            with self.assertRaises(kg.KaraError) as e:
                km.birth(self.store, g, dict(year=2000))
            self.assertEqual(e.exception.status, 403)     # guests: an account first
            # an admin clears a mistyped year; deleting one's data deletes it
            pid = kg.pid_of(self.store.key(a))
            self.assertEqual(kg.admin_act(self.store, 'boss', dict(act='birth_clear', pid=pid))['n'], 1)
            self.assertIsNone(km.birth_of(self.store, self.store.key(a)))
            km.forget(self.store, b)
            self.assertIsNone(km.birth_of(self.store, self.store.key(b)))
        with patch.dict(os.environ, LIVE_KARAOKE_MIC='0', LIVE_DOG_BARK='0'):
            with self.assertRaises(kg.KaraError) as e:
                km.birth(self.store, a, dict(year=2000))
            self.assertEqual(e.exception.status, 404)     # switched off: as if the route did not exist (🐕 kéo co off too)

    def test_no_save_key(self):
        a = self.user('hoa')
        before = self.store.read(a)[0]
        with patch.dict(os.environ, LIVE_KARAOKE_MIC='1'):
            km.birth(self.store, a, dict(year=1999))
        self.assertEqual(self.store.read(a)[0], before)


class AdminTools(Base):
    def test_live_voice_reports_and_the_mic_cut(self):
        bad = 'abcdefabcdef0123'
        t = time.time()
        self.store.transaction(lambda db: db.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES('aaaaaaaaaaaaaaa1', 'kara', ?, 'minor', ?)", ('m:' + bad, t)))
        it = kg.admin_view(self.store)['items'][0]
        self.assertEqual((it['kind'], it['ref'], it['safety']), ('m', bad, True))
        self.assertEqual(kg.admin_act(self.store, 'boss', dict(act='mic', room='kara:tre'))['act'], 'mic')
        kg.admin_act(self.store, 'boss', dict(act='mute', pid=bad, minutes=60))
        self.assertEqual(kg.admin_view(self.store)['items'], [])   # muting reviews the voice reports too
        kg.admin_act(self.store, 'boss', dict(act='keep', target='m:' + bad))
        with self.assertRaises(kg.KaraError):
            kg.admin_act(self.store, 'boss', dict(act='birth_clear', pid='nope'))


class VoiceSync(unittest.TestCase):
    """🎙️ Voice and music together (07/10 "bị delay xíu"): the target math in node, and the page's rollback guards."""

    def test_target_math(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'karaoke_sync.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_page_works_with_an_older_live_service(self):
        js = (ROOT / 'public/js/v4/karaoke.js').read_text(encoding='utf-8')
        quiet = re.search(r"\[('kara_dur'[^\]]*)\]\.includes\(f\.ref\)", js).group(1)
        self.assertIn("'kara_vt'", quiet)                                   # its refusals never toast
        self.assertIn("f.ref==='kara_vt'&&(f.code==='unknown'||f.code==='off'))K.vtOff=true", js)   # 'unknown': stop sending
        self.assertIn("on('welcome',()=>{K.vtOff=false;", js)              # a new service may know it
        self.assertIn('if(K.vtOff||', js)
        self.assertIn('none={t:clock,voice:false,hearing:false,margin:0}', js)   # no voice heard: the clock
        self.assertIn("const r=ok?M.followTarget(", js)                           # no video time of this song: no target …
        self.assertIn("lead.push(id)", js)
        # 🎤 hát cùng against an older live service: 'unknown' hides the button, its refusals never toast twice
        self.assertIn("'kara_join','kara_let'].includes(f.ref)", js)
        self.assertIn("if(f.ref==='kara_join'&&f.code==='unknown'){K.coOff=true;", js)
        self.assertIn("K.coOff=false;", re.search(r"on\('welcome',.*", js).group(0))
        # a co-singer's voice only from a reply for that pid; the stage singer's only from one without
        self.assertIn("f=>f.pid===pid", js)
        self.assertIn("'kara_listen',6000,f=>!f.pid", js)


if __name__ == '__main__':
    unittest.main()
