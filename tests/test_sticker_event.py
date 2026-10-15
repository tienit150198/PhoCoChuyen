"""🎨 Thi làm sticker (game/sticker_event.py, /sticker): who may submit (a signed-in account whose character lived
MIN_LIFE_DAYS days, while the event is open, at most MAX_ENTRIES), what the server accepts (PNG/WebP magic bytes,
exactly 512x512, one frame, at most 400 KB, not empty), the participation gift (once per account, through the system
gift path, revocable while pending), who sees an image (the author, the admins, the winners once the prizes are out)
and the operators' acts (reject / restore, ranks 1..10 unique and one per account, "Trao giải" once, after the end).
Runs on PostgreSQL with TEST_DATABASE_URL."""
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


def sticker(seed=1, size=se.SIZE, fmt='PNG', mime=None, **save):
    """A small drawing on a transparent 512x512 canvas, as the page sends it (a data URL)."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    for _ in range(6):
        x, y = rnd.randrange(size // 2), rnd.randrange(size // 2)
        d.ellipse((x, y, x + size // 3, y + size // 3), fill=(rnd.randrange(256), rnd.randrange(256), 90, 255))
    d.text((20, size - 40), f'@player {seed}', fill=(0, 0, 0, 255))
    out = io.BytesIO()
    im.save(out, fmt, **save)
    mime = mime or {'PNG': 'image/png', 'WEBP': 'image/webp', 'JPEG': 'image/jpeg'}[fmt]
    return f'data:{mime};base64,' + base64.b64encode(out.getvalue()).decode()


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

    def submit(self, dev, image=None, **kw):
        return self.req(dev, '/api/sticker/submit', 'POST', dict(image=image or sticker(), **kw))

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
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 49)
        with self.store.connect() as db:
            self.assertEqual(pg_schema.installed_version(db), pg_schema.SCHEMA_VERSION)
        self.assertEqual(pg_schema.TABLE['sticker_entries']['identity'], 'id')
        self.assertIn('sticker_rewards', pg_schema.TABLE)

    # ---- who may submit ---------------------------------------------------------------
    def test_guest_sees_the_rules_and_must_sign_in(self):
        status, out = self.req({}, '/api/sticker/me')
        self.assertEqual(status, 200)
        self.assertEqual((out['account'], out['can'], out['why']), (None, False, 'login'))
        self.assertEqual(out['rules']['join'], 200_000)
        self.assertEqual([p['coins'] for p in out['rules']['prizes']], [3_000_000, 1_500_000, 500_000])
        self.assertEqual((out['rules']['max'], out['rules']['size'], out['rules']['hashtag']), (3, 512, se.HASHTAG))
        self.assertNotIn('csrf', out)
        guest = {}
        self.req(guest, '/api/bootstrap?lite=1')
        status, out = self.req(guest, '/api/sticker/me')
        self.assertEqual((status, out['why'], out['account']), (200, 'login', None))
        status, out = self.submit(guest)
        self.assertEqual((status, out['code']), (401, 'login'))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_entries').fetchone()['n'], 0)

    def test_eligibility_life_days_and_window(self):
        dev = self.user('stk_new')
        with patch.object(se, 'MIN_LIFE_DAYS', 3):
            status, out = self.req(dev, '/api/sticker/me')
            self.assertEqual((status, out['can'], out['why'], out['life_day']), (200, False, 'days', 1))
            self.assertEqual(out['account']['username'], 'stk_new')
            self.assertTrue(out['csrf'])
            status, out = self.submit(dev)
            self.assertEqual((status, out['code']), (403, 'days'))
            self.assertIn('3 ngày', out['error'])
        with patch.object(se, 'END', time.time() - 1):
            status, out = self.req(dev, '/api/sticker/me')
            self.assertEqual((out['open'], out['can'], out['why']), (False, False, 'closed'))
            status, out = self.submit(dev)
            self.assertEqual((status, out['code']), (409, 'closed'))
        self.assertEqual(self.gifts('stk_new'), [])
        status, out = self.req(dev, '/api/sticker/me')
        self.assertEqual((out['open'], out['can'], out['why']), (True, True, ''))

    def test_csrf_and_body_limits(self):
        dev = self.user('stk_csrf')
        self.assertEqual(self.req(dev, '/api/sticker/submit', 'POST', dict(image=sticker()), csrf=False)[0], 403)
        self.assertEqual(self.req(dev, '/api/sticker/submit', 'POST', dict(image=sticker()), headers={'Origin': 'https://evil.example'})[0], 403)
        big = json.dumps(dict(image='data:image/png;base64,' + 'A' * (se.MAX_BODY + 10)))
        self.assertEqual(self.req(dev, '/api/sticker/submit', 'POST', big)[0], 413)
        self.assertEqual(self.gifts('stk_csrf'), [])

    # ---- what the server accepts ------------------------------------------------------
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
            (sticker(size=256), 'bad_size'), (sticker(size=1024), 'bad_size'),
            (raw_url('image/jpeg', jpeg.getvalue()), 'bad_type'),            # not a type we take
            (raw_url('image/png', jpeg.getvalue()), 'bad_type'),             # a JPEG called PNG: the magic bytes
            (raw_url('image/webp', base64.b64decode(sticker().split(',')[1])), 'bad_type'),   # a PNG called WebP
            (raw_url('image/png', out.getvalue()), 'too_large'),            # ~1 MB of noise
            (raw_url('image/webp', anim.getvalue()), 'bad_type'),           # animated
            (raw_url('image/png', empty.getvalue()), 'empty'),
            ('data:image/png;base64,@@@@', 'bad_sticker'), ('data:image/png;base64,', 'bad_type'), ('hello', 'bad_type'),
            (raw_url('image/png', b'\x89PNG\r\n\x1a\n' + b'0' * 200), 'bad_sticker'),   # the magic, then garbage
        ]
        for image, code in cases:
            self.server.limits.clear()   # 6 tries a minute
            status, res = self.submit(dev, image)
            self.assertEqual(res.get('code'), code, (code, status, res))
            self.assertIn(status, (400, 413), res)
        self.server.limits.clear()
        self.assertEqual(self.req(dev, '/api/sticker/submit', 'POST', dict(image=7))[1]['code'], 'bad_type')
        self.assertEqual(self.req(dev, '/api/sticker/submit', 'POST', dict(image=sticker(), extra=1))[1]['code'], 'bad_request')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) AS n FROM sticker_entries').fetchone()['n'], 0)
        self.assertEqual(self.gifts('stk_img'), [], 'no gift without an accepted sticker')
        # WebP is fine too; the stored image is the re-encoded one, 512x512, no metadata
        status, res = self.submit(dev, sticker(seed=9, fmt='WEBP', lossless=True))
        self.assertEqual(status, 200, res)
        st, h, body = self.req(dev, f'/api/sticker/img/{res["entry"]}', raw=True)
        self.assertEqual((st, h['Content-Type']), (200, 'image/webp'))
        with Image.open(io.BytesIO(body)) as im:
            self.assertEqual((im.format, im.size), ('WEBP', (512, 512)))
        st, h, body = self.req(dev, f'/api/sticker/img/{res["entry"]}?thumb=1', raw=True)
        self.assertEqual((st, h['Content-Type']), (200, 'image/webp'))
        with Image.open(io.BytesIO(body)) as im:
            self.assertEqual(im.size, (se.THUMB, se.THUMB))
        self.assertEqual(h['Cache-Control'], 'private, no-store')

    def test_three_per_account_and_no_duplicates(self):
        dev = self.user('stk_three')
        first = sticker(seed=11)
        status, out = self.submit(dev, first)
        self.assertEqual(status, 200, out)
        status, out = self.submit(dev, first)
        self.assertEqual((status, out['code']), (409, 'duplicate'))
        for seed in (12, 13):
            self.assertEqual(self.submit(dev, sticker(seed=seed))[0], 200)
        status, out = self.submit(dev, sticker(seed=14))
        self.assertEqual((status, out['code']), (409, 'full'))
        status, me = self.req(dev, '/api/sticker/me')
        self.assertEqual((len(me['entries']), me['can'], me['why']), (3, False, 'full'))
        self.assertEqual({e['status'] for e in me['entries']}, {'live'})
        # a rejected sticker still counts (no fourth try by getting one rejected)
        self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='reject', id=me['entries'][0]['id']))
        self.assertEqual(self.submit(dev, sticker(seed=15))[1]['code'], 'full')

    # ---- the participation gift -------------------------------------------------------
    def test_join_gift_once_and_paid_once(self):
        dev = self.user('stk_join')
        before = self.wallet(dev)
        status, out = self.submit(dev, sticker(seed=21))
        self.assertEqual((status, out['joined']), (200, dict(coins=200_000)), out)
        status, out = self.submit(dev, sticker(seed=22))
        self.assertEqual((status, out['joined']), (200, None))
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

    def test_join_gift_concurrent_submissions(self):
        dev = self.user('stk_race')
        results = []

        def go(seed):
            results.append(self.submit(dict(dev), sticker(seed=seed)))
        threads = [threading.Thread(target=go, args=(s,)) for s in (31, 32, 33)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        ok = [r for s, r in results if s == 200]
        self.assertTrue(ok, results)
        self.assertLessEqual(sum(1 for r in ok if r['joined']), 1)
        self.assertEqual(len(self.gifts('stk_race')), 1)

    def test_revoke_a_pending_join_gift(self):
        dev = self.user('stk_revoke')
        before = self.wallet(dev)
        self.assertEqual(self.submit(dev, sticker(seed=41))[0], 200)
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
        # and never given again by a later sticker
        status, out = self.submit(dev, sticker(seed=42))
        self.assertEqual((status, out['joined']), (200, None))
        self.assertEqual(len(self.gifts('stk_revoke')), 1)
        self.assertEqual(self.req(self.admin, '/api/admin/sticker', 'POST', dict(act='revoke', gift='g-other-gift'))[1]['code'], 'bad_admin')

    # ---- who sees an image ------------------------------------------------------------
    def test_only_the_author_and_admins_see_a_sticker(self):
        dev, other = self.user('stk_owner'), self.user('stk_other')
        status, out = self.submit(dev, sticker(seed=51))
        eid = out['entry']
        self.assertEqual(self.req(dev, f'/api/sticker/img/{eid}', raw=True)[0], 200)
        self.assertEqual(self.req(self.admin, f'/api/sticker/img/{eid}', raw=True)[0], 200)
        self.assertEqual(self.req(other, f'/api/sticker/img/{eid}', raw=True)[0], 404)
        self.assertEqual(self.req({}, f'/api/sticker/img/{eid}', raw=True)[0], 404)
        self.assertEqual(self.req({}, f'/api/sticker/img/{eid}?thumb=1', raw=True)[0], 404)
        for bad in ('abc', '-1', '1' * 20, '1;DROP'):
            self.assertEqual(self.req(dev, f'/api/sticker/img/{bad}', raw=True)[0], 404, bad)
        status, me = self.req(other, '/api/sticker/me')
        self.assertEqual(me['entries'], [])
        self.assertEqual(me['results'], [])
        # the operators' list is for the operators
        for d in (dev, other, {}):
            self.assertIn(self.req(d, '/api/admin/sticker')[0], (401, 403))
            self.assertIn(self.req(d, '/api/admin/sticker', 'POST', dict(act='award'))[0], (401, 403))
        self.assertEqual(self.req(self.admin, '/api/admin/sticker', csrf=False)[0], 403)

    # ---- the operators ----------------------------------------------------------------
    def test_admin_reject_rank_award(self):
        a, b, c = self.user('stk_a'), self.user('stk_b'), self.user('stk_c')
        ea = self.submit(a, sticker(seed=61))[1]['entry']
        ea2 = self.submit(a, sticker(seed=62))[1]['entry']
        eb = self.submit(b, sticker(seed=63))[1]['entry']
        ec = self.submit(c, sticker(seed=64))[1]['entry']
        act = lambda **d: self.req(self.admin, '/api/admin/sticker', 'POST', d)
        status, view = self.req(self.admin, '/api/admin/sticker')
        self.assertEqual((status, view['total'], view['people'], view['awarded']), (200, 4, 3, False))
        self.assertTrue(all(i['thumb'].endswith('?thumb=1') and i['username'] for i in view['items']))
        # reject / restore
        self.assertEqual(act(act='reject', id=ec, note='thiếu username')[1]['status'], 'rejected')
        self.assertEqual(act(act='rank', id=ec, rank=3)[1]['code'], 'rejected')
        self.assertEqual(act(act='restore', id=ec)[1]['status'], 'live')
        # ranks: 1..10, unique, one per account
        self.assertEqual(act(act='rank', id=ea, rank=1)[1]['rank'], 1)
        self.assertEqual(act(act='rank', id=eb, rank=1)[1]['code'], 'rank_taken')
        self.assertEqual(act(act='rank', id=ea2, rank=2)[1]['code'], 'one_rank')
        for bad in (0, 11, '2', 2.0, True):
            self.assertEqual(act(act='rank', id=eb, rank=bad)[1]['code'], 'bad_rank', bad)
        self.assertEqual(act(act='rank', id=eb, rank=2)[0], 200)
        self.assertEqual(act(act='rank', id=ec, rank=5)[0], 200)
        self.assertEqual(act(act='rank', id=99999999, rank=6)[1]['code'], 'not_found')
        # a rejected entry loses its rank
        act(act='reject', id=ec)
        act(act='restore', id=ec)
        self.assertEqual(act(act='rank', id=ec, rank=4)[0], 200)
        # "Trao giải": only after the end
        self.assertEqual(act(act='award')[1]['code'], 'not_yet')
        self.assertEqual(self.req({}, '/api/sticker/me')[1]['results'], [])
        before = {n: self.wallet(d) for n, d in (('a', a), ('b', b), ('c', c))}
        with patch.object(se, 'END', time.time() - 1):
            status, out = act(act='award')
            self.assertEqual(status, 200, out)
            self.assertEqual([(g['rank'], g['coins'], g['username']) for g in out['given']],
                             [(1, 3_000_000, 'stk_a'), (2, 1_500_000, 'stk_b'), (4, 500_000, 'stk_c')])
            self.assertEqual(act(act='award')[1]['given'], [], 'idempotent')
            self.assertEqual(act(act='rank', id=ea, rank=3)[1]['code'], 'locked')
            self.assertEqual(act(act='rank', id=ea, rank=None)[1]['code'], 'locked')
            self.assertEqual(act(act='reject', id=eb)[1]['code'], 'locked')
            # the results are public now, and so are the winners' images (only theirs)
            status, me = self.req({}, '/api/sticker/me')
            self.assertEqual([(r['rank'], r['username'], r['coins']) for r in me['results']],
                             [(1, 'stk_a', 3_000_000), (2, 'stk_b', 1_500_000), (4, 'stk_c', 500_000)])
            self.assertEqual(self.req({}, f'/api/sticker/img/{ea}', raw=True)[0], 200)
            self.assertEqual(self.req({}, f'/api/sticker/img/{ea2}', raw=True)[0], 404)
        after = {n: self.wallet(d) for n, d in (('a', a), ('b', b), ('c', c))}
        self.assertEqual(after, dict(a=before['a'] + 3_000_000, b=before['b'] + 1_500_000, c=before['c'] + 500_000))
        self.assertEqual(self.wallet(a), after['a'], 'paid once')
        status, view = self.req(self.admin, '/api/admin/sticker')
        self.assertTrue(view['awarded'])
        self.assertEqual(sorted((w['kind'], w['coins']) for w in view['rewards'] if w['kind'] == 'prize'),
                         [('prize', 500_000), ('prize', 1_500_000), ('prize', 3_000_000)])
        self.assertEqual(act(act='nope')[1]['code'], 'bad_admin')

    def test_account_deletion_takes_the_stickers(self):
        dev = self.user('stk_bye')
        self.assertEqual(self.submit(dev, sticker(seed=71))[0], 200)
        status, out = self.req(dev, '/api/account/delete', 'POST', dict(confirm='XOA'))
        self.assertEqual(status, 200, out)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM sticker_entries WHERE username='stk_bye'").fetchone()['n'], 0)
            self.assertEqual(db.execute("SELECT count(*) AS n FROM sticker_rewards WHERE username='stk_bye'").fetchone()['n'], 0)

    def test_in_game_hint_follows_the_window(self):
        from server import ui_config
        self.assertEqual(ui_config()['sticker'], dict(until=se.END))
        with patch.object(se, 'END', time.time() - 1):
            self.assertNotIn('sticker', ui_config())


if __name__ == '__main__':
    unittest.main()
