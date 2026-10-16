"""🎨 Thi làm sticker (game/sticker_event.py, /sticker): a PACK per account (one picture of the whole set, or 12–24
stickers of 512x512), who may send it (a signed-in account whose character lived MIN_LIFE_DAYS days, while the event
is open), what the server accepts (PNG/WebP magic bytes, sizes, one frame, the byte limits, not empty, at least 12
stickers, `ai` said), replacing the pack, the participation gift (once per account, through the system gift path,
revocable while pending; nothing more for an account paid under the first rules), who sees an image (the author, the
admins, the winners once the prizes are out) and the operators' acts (reject / restore, ranks 1..10 unique, "Trao
giải" once, after the end). Runs on PostgreSQL with TEST_DATABASE_URL."""
import base64
import http.client
import io
import json
import os
import random
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from game import pg_schema
from game import sticker_event as se
from game.storage import Store
from server import GameServer, PAGES

PW = 'matkhau-rat-dai'
REG = dict(password=PW, confirm=PW, display='Người Thử')
PUBLIC = Path(__file__).resolve().parents[1] / 'public'


def picture(seed=1, w=se.SIZE, h=None, fmt='PNG', mime=None, **save):
    """A small drawing on a transparent canvas, as the page sends it (a data URL)."""
    h = h or w
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    for _ in range(6):
        x, y = rnd.randrange(max(1, w // 2)), rnd.randrange(max(1, h // 2))
        d.ellipse((x, y, x + w // 3, y + h // 3), fill=(rnd.randrange(256), rnd.randrange(256), 90, 255))
    d.text((20, h - 40), f'@player {seed}', fill=(0, 0, 0, 255))
    out = io.BytesIO()
    im.save(out, fmt, **save)
    mime = mime or {'PNG': 'image/png', 'WEBP': 'image/webp', 'JPEG': 'image/jpeg'}[fmt]
    return f'data:{mime};base64,' + base64.b64encode(out.getvalue()).decode()


def a_set(seed=1, n=12, **kw):
    return [picture(seed * 100 + i, **kw) for i in range(n)]


def raw_url(mime, data: bytes):
    return f'data:{mime};base64,' + base64.b64encode(data).decode()


class StickerHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.store = Store(Path(cls.temp.name) / 'state.db', story=True)
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'op_admin'})
        cls.env.start()
        cls.fast = [patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw),
                    patch('game.accounts.verify_password', lambda pw, stored: stored == 'scrypt$test$' + pw)]
        for p in cls.fast:
            p.start()
        cls.admin = cls.signed_up(cls, 'op_admin')

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.store.close_pool()
        for p in cls.fast:
            p.stop()
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.server.limits.clear()
        self.store.transaction(lambda db: (db.execute('DELETE FROM sticker_entries'), db.execute('DELETE FROM sticker_rewards'),
                                           db.execute('DELETE FROM sticker_pack_images'), db.execute('DELETE FROM sticker_packs'),
                                           db.execute("DELETE FROM system_gifts WHERE id LIKE 'stk-%'")))
        self.days = patch.object(se, 'MIN_LIFE_DAYS', 1)   # a fresh save is on day 1; test_eligibility checks the bound
        self.days.start()
        self.addCleanup(self.days.stop)

    # ---- helpers ----------------------------------------------------------------------
    def req(self, dev, path, method='GET', body=None, csrf=True, headers=None, raw=False):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'):
            h['Cookie'] = dev['cookie']
        if csrf and dev.get('csrf'):
            h['X-Game-CSRF'] = dev['csrf']
        h.update(headers or {})
        if body is not None and not isinstance(body, (bytes, str)):
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        elif body is not None:
            h.setdefault('Content-Type', 'application/json')
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        data, hdrs = res.read(), dict(res.getheaders())
        con.close()
        if raw:
            return res.status, hdrs, data
        out = json.loads(data or b'{}')
        if 'Set-Cookie' in hdrs:
            dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(out, dict) and out.get('csrf'):
            dev['csrf'] = out['csrf']
        return res.status, out

    def signed_up(self, name):
        dev = {}
        status, _ = StickerHTTP.req(self, dev, '/api/bootstrap?lite=1')
        assert status == 200
        status, data = StickerHTTP.req(self, dev, '/api/account/register', 'POST', dict(REG, username=name))
        assert status == 200, data
        return dev

    def user(self, name):
        try:
            return self.signed_up(name)
        except AssertionError:   # registered by an earlier test: sign in on a new device
            dev = {}
            self.req(dev, '/api/bootstrap?lite=1')
            status, out = self.req(dev, '/api/account/login', 'POST', dict(username=name, password=PW, replace=True))
            assert status == 200, out
            return dev

    def send(self, dev, images=None, kind='set', ai=False, **kw):
        body = dict(kind=kind, ai=ai, images=a_set() if images is None else images, **kw)
        return self.req(dev, '/api/sticker/pack', 'POST', body)

    def sid(self, name):
        with self.store.connect() as db:
            return db.execute('SELECT sid FROM accounts WHERE username=?', (name,)).fetchone()['sid']

    def wallet(self, dev):
        status, data = self.req(dev, '/api/bootstrap?lite=1')
        self.assertEqual(status, 200, data)
        return data['state']['journey']['wallet']

    def gifts(self, name):
        with self.store.connect() as db:
            sid = db.execute('SELECT sid FROM accounts WHERE username=?', (name,)).fetchone()['sid']
            return [dict(r) for r in db.execute("SELECT id,coins,status FROM system_gifts WHERE sid=? AND id LIKE 'stk-%' ORDER BY created", (sid,))]

    # ---- the page and the schema ------------------------------------------------------
    def test_page_is_served_without_inline_scripts(self):
        self.assertEqual(PAGES['/sticker'], 'sticker.html')
        status, h, body = self.req({}, '/sticker', raw=True)
        self.assertEqual(status, 200)
        self.assertTrue(h['Content-Type'].startswith('text/html'))
        html = body.decode()
        self.assertIn('<script type="module" src="/js/sticker/main.js"></script>', html)
        self.assertNotRegex(html, r'<script(?![^>]*\bsrc=)[^>]*>')
        self.assertNotIn('unsafe-inline', h['Content-Security-Policy'].split('script-src', 1)[1].split(';', 1)[0])
        for ref in __import__('re').findall(r'(?:src|href)="(/[^"]+)"', html):
            self.assertEqual(self.req({}, ref, raw=True)[0], 200, ref)
        for js in (PUBLIC / 'js' / 'sticker').glob('*.js'):
            for ref in __import__('re').findall(r"""from\s*'(\.[^']+)'""", js.read_text(encoding='utf-8')):
                self.assertTrue((js.parent / ref).resolve().is_file(), f'{js.name}: {ref}')
        # not in the game page's import map (like the operator site)
        self.assertNotIn('/js/sticker/', self.server.assets.snapshot().importmap)

    def test_schema(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 50)
        with self.store.connect() as db:
            self.assertEqual(pg_schema.installed_version(db), pg_schema.SCHEMA_VERSION)
        self.assertEqual(pg_schema.TABLE['sticker_packs']['identity'], 'id')
        for t in ('sticker_entries', 'sticker_rewards', 'sticker_pack_images'):
            self.assertIn(t, pg_schema.TABLE)

    # ---- who may send -----------------------------------------------------------------
    def test_guest_sees_the_rules_and_must_sign_in(self):
        status, out = self.req({}, '/api/sticker/me')
        self.assertEqual(status, 200)
        self.assertEqual((out['account'], out['can'], out['why'], out['pack']), (None, False, 'login', None))
        r = out['rules']
        self.assertEqual(r['join'], 200_000)
        self.assertEqual([p['coins'] for p in r['prizes']], [5_000_000, 2_500_000, 1_000_000])
        self.assertEqual((r['min'], r['max_set'], r['size'], r['hashtag']), (12, 24, 512, '#PhoCoChuyen'))
        self.assertTrue(r['fb'].startswith('https://www.facebook.com/groups/'))
        self.assertNotIn('csrf', out)
        guest = {}
        self.req(guest, '/api/bootstrap?lite=1')
        status, out = self.req(guest, '/api/sticker/me')
        self.assertEqual((status, out['why'], out['account']), (200, 'login', None))
        status, out = self.send(guest)
        self.assertEqual((status, out['code']), (401, 'login'))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_packs').fetchone()['n'], 0)

    def test_eligibility_life_days_and_window(self):
        dev = self.user('stk_new')
        with patch.object(se, 'MIN_LIFE_DAYS', 3):
            status, out = self.req(dev, '/api/sticker/me')
            self.assertEqual((status, out['can'], out['why'], out['life_day']), (200, False, 'days', 1))
            self.assertEqual(out['account']['username'], 'stk_new')
            self.assertTrue(out['csrf'])
            status, out = self.send(dev)
            self.assertEqual((status, out['code']), (403, 'days'))
            self.assertIn('3 ngày', out['error'])
        with patch.object(se, 'END', time.time() - 1):
            status, out = self.req(dev, '/api/sticker/me')
            self.assertEqual((out['open'], out['can'], out['why']), (False, False, 'closed'))
            status, out = self.send(dev)
            self.assertEqual((status, out['code']), (409, 'closed'))
        self.assertEqual(self.gifts('stk_new'), [])
        status, out = self.req(dev, '/api/sticker/me')
        self.assertEqual((out['open'], out['can'], out['why']), (True, True, ''))

    def test_csrf_body_limits_and_the_old_route(self):
        dev = self.user('stk_csrf')
        body = dict(kind='set', ai=False, images=a_set())
        self.assertEqual(self.req(dev, '/api/sticker/pack', 'POST', body, csrf=False)[0], 403)
        self.assertEqual(self.req(dev, '/api/sticker/pack', 'POST', body, headers={'Origin': 'https://evil.example'})[0], 403)
        big = json.dumps(dict(kind='sheet', ai=False, count=12, images=['data:image/png;base64,' + 'A' * (se.MAX_BODY + 10)]))
        self.assertEqual(self.req(dev, '/api/sticker/pack', 'POST', big)[0], 413)
        # an open tab of the first page (one sticker): told to reload
        status, out = self.req(dev, '/api/sticker/submit', 'POST', dict(image=picture()))
        self.assertEqual((status, out['code']), (410, 'pack_now'))
        self.assertEqual(self.gifts('stk_csrf'), [])

    # ---- what the server accepts ------------------------------------------------------
    def test_pack_shape(self):
        dev = self.user('stk_shape')
        one = picture(seed=3)
        cases = [
            (dict(kind='set', ai=False, images=a_set(n=11)), 'too_few'),
            (dict(kind='set', ai=False, images=a_set(n=25)), 'too_few'),
            (dict(kind='set', ai=False, images=[one] * 12), 'duplicate'),
            (dict(kind='sheet', ai=False, count=11, images=[picture(w=900)]), 'too_few'),
            (dict(kind='sheet', ai=False, count=12.0, images=[picture(w=900)]), 'too_few'),
            (dict(kind='sheet', ai=False, count=101, images=[picture(w=900)]), 'too_few'),
            (dict(kind='sheet', ai=False, count=12, images=[picture(w=900), picture(w=900, seed=2)]), 'bad_count'),
            (dict(kind='sheet', ai=False, count=12, images=[picture(w=200)]), 'bad_size'),
            (dict(kind='sheet', ai=False, count=12, images=[picture(w=4200, h=400)]), 'bad_size'),
            (dict(kind='album', ai=False, images=a_set()), 'bad_kind'),
            (dict(kind='set', images=a_set()), 'bad_ai'),
            (dict(kind='set', ai='yes', images=a_set()), 'bad_ai'),
            (dict(kind='set', ai=False, images=[]), 'empty'),
            (dict(kind='set', ai=False, images=a_set(), extra=1), 'bad_request'),
        ]
        for body, code in cases:
            self.server.limits.clear()   # 6 tries a minute
            status, res = self.req(dev, '/api/sticker/pack', 'POST', body)
            self.assertEqual(res.get('code'), code, (code, status, res))
            self.assertIn(status, (400, 413), res)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_packs').fetchone()['n'], 0)
        self.assertEqual(self.gifts('stk_shape'), [], 'no gift without an accepted pack')

    def test_image_validation(self):
        dev = self.user('stk_img')
        noise = Image.frombytes('RGBA', (512, 512), random.Random(5).randbytes(512 * 512 * 4))
        out = io.BytesIO()
        noise.save(out, 'PNG')
        anim = io.BytesIO()
        frames = [Image.new('RGBA', (512, 512), (255, 0, 0, 255)), Image.new('RGBA', (512, 512), (0, 0, 255, 255))]
        frames[0].save(anim, 'WEBP', save_all=True, append_images=frames[1:], duration=100)
        jpeg = io.BytesIO()
        Image.new('RGB', (512, 512), (200, 10, 10)).save(jpeg, 'JPEG')
        empty = io.BytesIO()
        Image.new('RGBA', (512, 512), (0, 0, 0, 0)).save(empty, 'PNG')
        cases = [
            (picture(w=256), 'bad_size'), (picture(w=1024), 'bad_size'),
            (raw_url('image/jpeg', jpeg.getvalue()), 'bad_type'),            # not a type we take
            (raw_url('image/png', jpeg.getvalue()), 'bad_type'),             # a JPEG called PNG: the magic bytes
            (raw_url('image/webp', base64.b64decode(picture().split(',')[1])), 'bad_type'),   # a PNG called WebP
            (raw_url('image/png', out.getvalue()), 'too_large'),            # ~1 MB of noise
            (raw_url('image/webp', anim.getvalue()), 'bad_type'),           # animated
            (raw_url('image/png', empty.getvalue()), 'empty'),
            ('data:image/png;base64,@@@@', 'bad_sticker'), ('data:image/png;base64,', 'bad_type'), ('hello', 'bad_type'), (7, 'bad_type'),
            (raw_url('image/png', b'\x89PNG\r\n\x1a\n' + b'0' * 200), 'bad_sticker'),   # the magic, then garbage
        ]
        good = a_set(seed=4, n=11)
        for image, code in cases:
            self.server.limits.clear()
            status, res = self.send(dev, good[:5] + [image] + good[5:])
            self.assertEqual(res.get('code'), code, (code, status, res))
            self.assertIn(status, (400, 413), res)
            if code != 'bad_type':
                self.assertIn('Sticker 6', res['error'])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_packs').fetchone()['n'], 0)
        # WebP is fine too; the stored images are the re-encoded ones, 512x512, no metadata
        self.server.limits.clear()
        status, res = self.send(dev, a_set(seed=9, fmt='WEBP', lossless=True), ai=True)
        self.assertEqual(status, 200, res)
        pack = res['pack']
        self.assertEqual((pack['kind'], pack['count'], pack['ai'], pack['status'], len(pack['images'])), ('set', 12, True, 'live', 12))
        st, h, body = self.req(dev, pack['images'][0]['img'], raw=True)
        self.assertEqual((st, h['Content-Type']), (200, 'image/webp'))
        with Image.open(io.BytesIO(body)) as im:
            self.assertEqual((im.format, im.size), ('WEBP', (512, 512)))
        st, h, body = self.req(dev, pack['images'][11]['thumb'], raw=True)
        self.assertEqual((st, h['Content-Type']), (200, 'image/webp'))
        with Image.open(io.BytesIO(body)) as im:
            self.assertEqual(im.size, (se.THUMB, se.THUMB))
        self.assertEqual(h['Cache-Control'], 'private, no-store')
        self.assertEqual(self.req(dev, pack['images'][0]['img'].replace('/0?', '/12?'), raw=True)[0], 404)

    def test_one_picture_of_the_whole_set(self):
        dev = self.user('stk_sheet')
        status, res = self.send(dev, [picture(seed=5, w=1254, h=1254)], kind='sheet', count=16)
        self.assertEqual(status, 200, res)
        pack = res['pack']
        self.assertEqual((pack['kind'], pack['count'], pack['ai'], len(pack['images'])), ('sheet', 16, False, 1))
        st, h, body = self.req(dev, pack['images'][0]['img'], raw=True)
        with Image.open(io.BytesIO(body)) as im:
            self.assertEqual((h['Content-Type'], im.size), ('image/png', (1254, 1254)))
        with Image.open(io.BytesIO(self.req(dev, pack['images'][0]['thumb'], raw=True)[2])) as im:
            self.assertEqual(im.size, (se.SHEET_THUMB, se.SHEET_THUMB))

    # ---- one pack, replaced -----------------------------------------------------------
    def test_one_pack_replaced_in_place(self):
        dev = self.user('stk_again')
        first = a_set(seed=11)
        status, out = self.send(dev, first)
        self.assertEqual((status, out['replaced'], out['joined']), (200, False, dict(coins=200_000)), out)
        pid = out['pack']['id']
        status, out = self.send(dev, first)
        self.assertEqual((status, out['code']), (409, 'duplicate'))
        status, out = self.send(dev, a_set(seed=12, n=14), ai=True)
        self.assertEqual((status, out['replaced'], out['joined']), (200, True, None), out)
        self.assertEqual((out['pack']['id'], out['pack']['count'], out['pack']['ai'], len(out['pack']['images'])), (pid, 14, True, 14))
        self.assertIn('v=2', out['pack']['images'][0]['img'])
        status, out = self.send(dev, [picture(seed=13, w=800, h=600)], kind='sheet', count=20)
        self.assertEqual((status, out['pack']['kind'], len(out['pack']['images'])), (200, 'sheet', 1))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_packs').fetchone()['n'], 1)
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_pack_images').fetchone()['n'], 1)
        self.assertEqual(len(self.gifts('stk_again')), 1)
        # a rejected pack: the author reads why, sends a new one, which is live again
        self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='reject', id=pid, note='thiếu tên tài khoản'))
        status, me = self.req(dev, '/api/sticker/me')
        self.assertEqual((me['pack']['status'], me['pack']['note'], me['can']), ('rejected', 'thiếu tên tài khoản', True))
        status, out = self.send(dev, a_set(seed=14))
        self.assertEqual((status, out['pack']['status'], out['pack']['note']), (200, 'live', ''))
        # a ranked pack is locked
        self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='rank', id=pid, rank=1))
        status, out = self.send(dev, a_set(seed=15))
        self.assertEqual((status, out['code']), (409, 'locked'))

    # ---- the participation gift -------------------------------------------------------
    def test_join_gift_once_and_paid_once(self):
        dev = self.user('stk_join')
        before = self.wallet(dev)
        status, out = self.send(dev, a_set(seed=21))
        self.assertEqual((status, out['joined']), (200, dict(coins=200_000)), out)
        gifts = self.gifts('stk_join')
        self.assertEqual([(g['coins'], g['status']) for g in gifts], [(200_000, 'pending')])
        self.assertEqual(self.wallet(dev), before + 200_000, 'paid at the next load')
        self.assertEqual(self.wallet(dev), before + 200_000, 'only once')
        self.assertEqual(self.gifts('stk_join')[0]['status'], 'applied')
        status, me = self.req(dev, '/api/sticker/me')
        self.assertEqual(me['joined'], dict(coins=200_000, status='granted', paid=True))
        # a paid gift cannot be revoked
        status, out = self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='revoke', gift=gifts[0]['id']))
        self.assertEqual((status, out['code']), (409, 'paid'))
        with self.store.connect() as db:
            rows = db.execute("SELECT kind,coins,status,username,life_day FROM sticker_rewards").fetchall()
        self.assertEqual([dict(r) for r in rows], [dict(kind='join', coins=200_000, status='granted', username='stk_join', life_day=1)])

    def test_paid_under_the_first_rules_gets_nothing_more(self):
        dev = self.user('stk_old')
        sid = self.sid('stk_old')
        png = base64.b64decode(picture(seed=1).split(',')[1])
        self.store.transaction(lambda db: (
            db.execute("INSERT INTO sticker_entries(sid,username,mime,width,height,byte_size,data,thumb,sha,created) "
                       "VALUES(?,?,'image/png',512,512,?,?,?,'x',?)", (sid, 'stk_old', len(png), png, png, time.time())),
            db.execute("INSERT INTO sticker_rewards(gift_id,sid,kind,coins,username,status,created) VALUES(?,?,'join',200000,'stk_old','granted',?)",
                       (se.join_id(sid), sid, time.time()))))
        status, me = self.req(dev, '/api/sticker/me')
        self.assertEqual((me['legacy'], me['pack'], me['can']), (1, None, True))
        status, out = self.send(dev, a_set(seed=81))
        self.assertEqual((status, out['joined']), (200, None), out)
        status, view = self.req(self.admin, '/api/admin/sticker')
        self.assertEqual([e['username'] for e in view['legacy']], ['stk_old'])
        self.assertEqual(self.req(dev, view['legacy'][0]['img'], raw=True)[0], 200)
        self.assertEqual(self.req({}, view['legacy'][0]['img'], raw=True)[0], 404)

    def test_join_gift_concurrent_packs(self):
        dev = self.user('stk_race')
        results = []

        def go(seed):
            results.append(self.send(dict(dev), a_set(seed=seed)))
        threads = [threading.Thread(target=go, args=(s,)) for s in (31, 32, 33)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        ok = [r for s, r in results if s == 200]
        self.assertTrue(ok, results)
        self.assertLessEqual(sum(1 for r in ok if r['joined']), 1)
        self.assertEqual(len(self.gifts('stk_race')), 1)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_packs').fetchone()['n'], 1)

    def test_revoke_a_pending_join_gift(self):
        dev = self.user('stk_revoke')
        before = self.wallet(dev)
        self.assertEqual(self.send(dev, a_set(seed=41))[0], 200)
        gid = self.gifts('stk_revoke')[0]['id']
        status, view = self.req(self.admin, '/api/admin/sticker')
        self.assertEqual(status, 200)
        item = next(i for i in view['items'] if i['username'] == 'stk_revoke')
        self.assertEqual((item['join']['id'], item['join']['gift'], item['join']['status']), (gid, 'pending', 'granted'))
        self.assertEqual(self.req(dev, '/api/admin/sticker', 'POST', dict(act='revoke', gift=gid))[0], 403)
        status, out = self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='revoke', gift=gid))
        self.assertEqual((status, out['status']), (200, 'revoked'), out)
        self.assertEqual(self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='revoke', gift=gid))[1]['code'], 'revoked')
        self.assertEqual(self.wallet(dev), before, 'a revoked gift is never paid')
        self.assertEqual(self.gifts('stk_revoke')[0]['status'], 'revoked')
        # and never given again by a later pack
        status, out = self.send(dev, a_set(seed=42))
        self.assertEqual((status, out['joined']), (200, None))
        self.assertEqual(len(self.gifts('stk_revoke')), 1)
        self.assertEqual(self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='revoke', gift='g-other-gift'))[1]['code'], 'bad_admin')

    # ---- who sees an image ------------------------------------------------------------
    def test_only_the_author_and_admins_see_a_pack(self):
        dev, other = self.user('stk_owner'), self.user('stk_other')
        status, out = self.send(dev, a_set(seed=51))
        url = out['pack']['images'][3]['img']
        self.assertEqual(self.req(dev, url, raw=True)[0], 200)
        self.assertEqual(self.req(self.admin, url, raw=True)[0], 200)
        self.assertEqual(self.req(other, url, raw=True)[0], 404)
        self.assertEqual(self.req({}, url, raw=True)[0], 404)
        self.assertEqual(self.req({}, url + '&thumb=1', raw=True)[0], 404)
        for bad in ('abc/0', '-1/0', '1' * 20 + '/0', '1/1;DROP', '1/9999'):
            self.assertIn(self.req(dev, f'/api/sticker/pack/{bad}', raw=True)[0], (404,), bad)
        status, me = self.req(other, '/api/sticker/me')
        self.assertEqual((me['pack'], me['results']), (None, []))
        # the operators' list is for the operators
        for d in (dev, other, {}):
            self.assertIn(self.req(d, '/api/admin/sticker')[0], (401, 403))
            self.assertIn(self.req(d, '/api/admin/sticker', 'POST', dict(act='award'))[0], (401, 403))
        self.assertEqual(self.req(self.admin, '/api/admin/sticker', csrf=False)[0], 403)

    # ---- the operators ----------------------------------------------------------------
    def test_admin_reject_rank_award(self):
        a, b, c, d = self.user('stk_a'), self.user('stk_b'), self.user('stk_c'), self.user('stk_d')
        pa = self.send(a, a_set(seed=61))[1]['pack']
        pb = self.send(b, [picture(seed=62, w=1000)], kind='sheet', count=16, ai=True)[1]['pack']
        pc = self.send(c, a_set(seed=63))[1]['pack']
        pd = self.send(d, a_set(seed=64))[1]['pack']
        act = lambda **x: self.req(self.admin, '/api/admin/sticker', 'POST', x)
        status, view = self.req(self.admin, '/api/admin/sticker')
        self.assertEqual((status, view['total'], view['awarded']), (200, 4, False))
        item = next(i for i in view['items'] if i['username'] == 'stk_b')
        self.assertEqual((item['kind'], item['count'], item['ai'], len(item['images'])), ('sheet', 16, True, 1))
        # reject / restore
        self.assertEqual(act(act='reject', id=pc['id'], note='chép mạng')[1]['status'], 'rejected')
        self.assertEqual(act(act='rank', id=pc['id'], rank=3)[1]['code'], 'rejected')
        self.assertEqual(act(act='restore', id=pc['id'])[1]['status'], 'live')
        # ranks: 1..10, unique
        self.assertEqual(act(act='rank', id=pa['id'], rank=1)[1]['rank'], 1)
        self.assertEqual(act(act='rank', id=pb['id'], rank=1)[1]['code'], 'rank_taken')
        for bad in (0, 11, '2', 2.0, True):
            self.assertEqual(act(act='rank', id=pb['id'], rank=bad)[1]['code'], 'bad_rank', bad)
        self.assertEqual(act(act='rank', id=pb['id'], rank=2)[0], 200)
        self.assertEqual(act(act='rank', id=pc['id'], rank=5)[0], 200)
        self.assertEqual(act(act='rank', id=99999999, rank=6)[1]['code'], 'not_found')
        # a rejected pack loses its rank
        act(act='reject', id=pc['id'])
        act(act='restore', id=pc['id'])
        self.assertEqual(act(act='rank', id=pc['id'], rank=4)[0], 200)
        # "Trao giải": only after the end
        self.assertEqual(act(act='award')[1]['code'], 'not_yet')
        self.assertEqual(self.req({}, '/api/sticker/me')[1]['results'], [])
        before = {n: self.wallet(x) for n, x in (('a', a), ('b', b), ('c', c))}
        with patch.object(se, 'END', time.time() - 1):
            status, out = act(act='award')
            self.assertEqual(status, 200, out)
            self.assertEqual([(g['rank'], g['coins'], g['username']) for g in out['given']],
                             [(1, 5_000_000, 'stk_a'), (2, 2_500_000, 'stk_b'), (4, 1_000_000, 'stk_c')])
            self.assertEqual(act(act='award')[1]['given'], [], 'idempotent')
            self.assertEqual(act(act='rank', id=pa['id'], rank=3)[1]['code'], 'locked')
            self.assertEqual(act(act='rank', id=pa['id'], rank=None)[1]['code'], 'locked')
            self.assertEqual(act(act='reject', id=pb['id'])[1]['code'], 'locked')
            # the results are public now, and so are the winners' images (only theirs)
            status, me = self.req({}, '/api/sticker/me')
            self.assertEqual([(r['rank'], r['username'], r['coins'], r['ai'], len(r['images'])) for r in me['results']],
                             [(1, 'stk_a', 5_000_000, False, 12), (2, 'stk_b', 2_500_000, True, 1), (4, 'stk_c', 1_000_000, False, 12)])
            self.assertEqual(self.req({}, pa['images'][0]['img'], raw=True)[0], 200)
            self.assertEqual(self.req({}, pd['images'][0]['img'], raw=True)[0], 404)
        after = {n: self.wallet(x) for n, x in (('a', a), ('b', b), ('c', c))}
        self.assertEqual(after, dict(a=before['a'] + 5_000_000, b=before['b'] + 2_500_000, c=before['c'] + 1_000_000))
        self.assertEqual(self.wallet(a), after['a'], 'paid once')
        status, view = self.req(self.admin, '/api/admin/sticker')
        self.assertTrue(view['awarded'])
        self.assertEqual(sorted((w['kind'], w['coins']) for w in view['rewards'] if w['kind'] == 'prize'),
                         [('prize', 1_000_000), ('prize', 2_500_000), ('prize', 5_000_000)])
        self.assertEqual(act(act='nope')[1]['code'], 'bad_admin')

    def test_account_deletion_takes_the_pack(self):
        dev = self.user('stk_bye')
        self.assertEqual(self.send(dev, a_set(seed=71))[0], 200)
        status, out = self.req(dev, '/api/account/delete', 'POST', dict(confirm='XOA'))
        self.assertEqual(status, 200, out)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM sticker_packs WHERE username='stk_bye'").fetchone()['n'], 0)
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_pack_images').fetchone()['n'], 0)
            self.assertEqual(db.execute("SELECT count(*) AS n FROM sticker_rewards WHERE username='stk_bye'").fetchone()['n'], 0)

    def test_in_game_hint_follows_the_window(self):
        from server import ui_config
        self.assertEqual(ui_config()['sticker'], dict(until=se.END))
        with patch.object(se, 'END', time.time() - 1):
            self.assertNotIn('sticker', ui_config())


if __name__ == '__main__':
    unittest.main()
