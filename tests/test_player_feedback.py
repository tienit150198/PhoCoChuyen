"""Player feedback ("Góp ý"): module rules and the HTTP routes through a real server.
Spec: docs/superpowers/specs/2026-09-29-player-feedback-design.md"""
import http.client, json, os, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch

from tests.pg_support import columns
from game import accounts, player_feedback as pfb, social
from game.storage import Store
from server import GameServer

REG = dict(password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Người Thử')


class FeedbackModuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')
        social.ensure(self.store)
        self.token, _, _ = self.store.session()

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, token=None):
        return self.store.read(token or self.token)[0]

    def send(self, text='Nút gửi bị che mất trên điện thoại', kind='bug', token=None, context=None, ua='', version='0.5'):
        token = token or self.token
        return pfb.submit(self.store, token, self.state(token), dict(kind=kind, text=text, context=context or {}), ua, version)

    def test_table_exists_in_a_fresh_store(self):
        with self.store.connect() as db:
            cols = columns(db, 'player_feedback')
        self.assertTrue({'id', 'sid', 'account', 'kind', 'text', 'context', 'status', 'reply', 'created_at', 'updated_at'} <= cols)

    def test_submit_and_mine(self):
        out = self.send()
        self.assertEqual(out, dict(ok=True, id=out['id'], message='Đã ghi nhận, cảm ơn bạn!'))
        mine = pfb.list_mine(self.store, self.token)
        self.assertEqual(len(mine), 1)
        self.assertEqual((mine[0]['kind'], mine[0]['status'], mine[0]['reply']), ('bug', 'new', None))
        self.assertNotIn('context', mine[0])  # the player's own list stays small
        self.assertNotIn('sid', json.dumps(mine))

    def test_validation(self):
        st = self.state()
        bad = [dict(kind='rant', text='Không có loại này'), dict(kind=None, text='abcdef'), dict(kind='bug', text=''),
               dict(kind='bug', text='  a '), dict(kind='bug', text='x' * 10001), dict(kind='bug', text=123), dict(kind='bug'),
               dict(kind='idea', text='đm đm')]
        for d in bad:
            with self.subTest(d=d), self.assertRaises(pfb.FeedbackError):
                pfb.submit(self.store, self.token, st, d)
        self.assertEqual(len(pfb.list_mine(self.store, self.token)), 0)
        self.send('x' * 10000)  # the limit itself is fine (owner 06/10: 10,000)
        for kind in pfb.KINDS:
            self.send('Một góp ý nhỏ thôi', kind)

    def test_redaction_and_banned_words(self):
        self.send('Gọi mình 0901 234 567 hoặc mail an.nguyen@example.com, xem https://evil.example/x nhé. Đm lỗi này fuck')
        text = pfb.list_mine(self.store, self.token)[0]['text']
        for leaked in ('0901', 'example.com', 'https://', 'evil', 'Đm', 'fuck'):
            self.assertNotIn(leaked, text)
        self.assertIn('[đã ẩn]', text)
        self.assertIn('•••', text)
        self.assertIn('lỗi này', text)

    def test_text_is_normalised(self):
        self.send('  Dòng một​\x07  \n\n\n\n  Dòng   hai  ')
        self.assertEqual(pfb.list_mine(self.store, self.token)[0]['text'], 'Dòng một\n\nDòng hai')

    def test_context_is_whitelisted_and_server_derived(self):
        rev = self.store.read(self.token)[1]
        self.store.command(self.token, 'fb-test-select', rev, 'restaurant', 'select_career', {})
        self.send(context=dict(view='prepare', layout='phone', screen='390x844', career='pharmacy', day=99, evil='<script>',
                               ua='fake'), ua='Mozilla/5.0 ' + 'x' * 400, version='0.5.1')
        ctx = pfb.list_admin(self.store)['items'][0]['context']
        self.assertEqual(ctx['career'], 'restaurant')  # from the save, not the client
        self.assertEqual(ctx['day'], self.state()['careers']['restaurant']['day'])
        self.assertEqual((ctx['view'], ctx['layout'], ctx['screen'], ctx['lang'], ctx['version']), ('prepare', 'phone', '390x844', 'vi', '0.5.1'))
        self.assertEqual(len(ctx['ua']), 200)
        self.assertNotIn('evil', ctx)
        self.assertIn('life_day', ctx)
        bad = pfb.clean_context(dict(view='a b<c>', layout='watch', screen='9999999x1'), self.state())
        self.assertFalse({'view', 'layout', 'screen'} & set(bad))

    def test_mine_is_isolated_between_saves(self):
        other, _, _ = self.store.session()
        self.send('Góp ý của người thứ nhất')
        self.send('Góp ý của người thứ hai', token=other)
        self.assertEqual([x['text'] for x in pfb.list_mine(self.store, self.token)], ['Góp ý của người thứ nhất'])
        self.assertEqual([x['text'] for x in pfb.list_mine(self.store, other)], ['Góp ý của người thứ hai'])

    def test_mine_keeps_the_last_twenty(self):
        for i in range(23):
            self.send(f'Góp ý số {i}')
        mine = pfb.list_mine(self.store, self.token)
        self.assertEqual(len(mine), 20)
        self.assertEqual(mine[0]['text'], 'Góp ý số 22')

    def test_account_linkage_follows_the_player_to_another_device(self):
        self.send('Trước khi đăng ký')
        out = accounts.register(self.store, self.token, dict(REG, username='chu_quan'))
        signed = out['token']
        self.send('Sau khi đăng ký', token=signed)
        rows = {x['text']: x for x in pfb.list_admin(self.store)['items']}
        self.assertIsNone(rows['Trước khi đăng ký']['account'])
        self.assertEqual(rows['Sau khi đăng ký']['account'], 'chu_quan')
        other, _, _ = self.store.session()
        dev2 = accounts.login(self.store, other, dict(username='chu_quan', password=REG['password']))['token']
        self.assertEqual({x['text'] for x in pfb.list_mine(self.store, dev2)}, {'Trước khi đăng ký', 'Sau khi đăng ký'})

    def test_admin_users_and_is_admin(self):
        out = accounts.register(self.store, self.token, dict(REG, username='boss'))
        signed = out['token']
        with patch.dict(os.environ, {'ADMIN_USERS': ''}):
            self.assertEqual(pfb.admin_users(), set())
            self.assertFalse(pfb.is_admin(self.store, signed))
        with patch.dict(os.environ, {'ADMIN_USERS': ' Boss , other '}):
            self.assertEqual(pfb.admin_users(), {'boss', 'other'})
            self.assertTrue(pfb.is_admin(self.store, signed))
            anon, _, _ = self.store.session()
            self.assertFalse(pfb.is_admin(self.store, anon))
            self.assertFalse(pfb.is_admin(self.store, None))

    def test_admin_list_filters_and_pages(self):
        for i in range(7):
            self.send(f'Góp ý {i}', kind='idea' if i % 2 else 'bug')
        page = pfb.list_admin(self.store, limit=3)
        self.assertEqual([x['text'] for x in page['items']], ['Góp ý 6', 'Góp ý 5', 'Góp ý 4'])
        self.assertEqual(page['counts'], dict(new=7, seen=0, done=0))
        page2 = pfb.list_admin(self.store, before=page['next'], limit=3)
        self.assertEqual([x['text'] for x in page2['items']], ['Góp ý 3', 'Góp ý 2', 'Góp ý 1'])
        last = pfb.list_admin(self.store, before=page2['next'], limit=3)
        self.assertEqual(([x['text'] for x in last['items']], last['next']), (['Góp ý 0'], None))
        self.assertEqual(len(pfb.list_admin(self.store, kind='idea')['items']), 3)
        first = page['items'][0]['id']
        pfb.update(self.store, first, 'done')
        self.assertEqual([x['id'] for x in pfb.list_admin(self.store, status='done')['items']], [first])
        self.assertEqual(pfb.list_admin(self.store)['counts'], dict(new=6, seen=0, done=1))
        for bad in (dict(status='open'), dict(kind='rant'), dict(before='abc'), dict(before=-3)):
            with self.subTest(bad=bad), self.assertRaises(pfb.FeedbackError):
                pfb.list_admin(self.store, **bad)
        self.assertTrue(page['items'][0]['player'])
        self.assertNotIn(self.store.key(self.token), json.dumps(page))

    def test_update_reply_and_status(self):
        fid = self.send()['id']
        item = pfb.update(self.store, fid, reply='  Cảm ơn bạn, đã sửa!  ')
        self.assertEqual((item['reply'], item['status']), ('Cảm ơn bạn, đã sửa!', 'new'))
        self.assertIsNotNone(item['replied_at'])
        item = pfb.update(self.store, fid, status='done')
        self.assertEqual((item['reply'], item['status']), ('Cảm ơn bạn, đã sửa!', 'done'))
        mine = pfb.list_mine(self.store, self.token)[0]
        self.assertEqual((mine['reply'], mine['status']), ('Cảm ơn bạn, đã sửa!', 'done'))
        item = pfb.update(self.store, fid, reply='')
        self.assertIsNone(item['reply'])
        self.assertIsNone(item['replied_at'])
        self.assertIn('[đã ẩn]', pfb.update(self.store, fid, reply='Gọi 0901234567 nhé')['reply'])
        for bad in (dict(fid=fid), dict(fid=fid, status='open'), dict(fid=fid, reply='x' * 301), dict(fid='x', status='seen'),
                    dict(fid=None, status='seen')):
            with self.subTest(bad=bad), self.assertRaises(pfb.FeedbackError):
                pfb.update(self.store, **bad)
        with self.assertRaises(pfb.FeedbackError) as e:
            pfb.update(self.store, fid + 99, status='seen')
        self.assertEqual(e.exception.status, 404)

    def test_edit_own_note_until_it_has_a_reply(self):
        """F#295: "nên có nút sửa lại góp ý": the owner edits a note with no reply; the edit goes back to "new"."""
        fid = self.send('Nút gửi bị che')['id']
        pfb.update(self.store, fid, status='seen')
        out = pfb.edit(self.store, self.token, dict(id=fid, text='  Nút gửi bị che trên iPhone SE, gọi 0901234567  ', kind='hard'))
        self.assertEqual((out['ok'], out['message']), (True, 'Đã lưu góp ý.'))
        self.assertEqual((out['item']['text'], out['item']['kind'], out['item']['status']),
                         ('Nút gửi bị che trên iPhone SE, gọi [đã ẩn]', 'hard', 'new'))
        self.assertNotIn('context', out['item'])
        mine = pfb.list_mine(self.store, self.token)[0]
        self.assertEqual(mine['text'], 'Nút gửi bị che trên iPhone SE, gọi [đã ẩn]')
        out = pfb.edit(self.store, self.token, dict(id=fid, text='Chỉ đổi chữ'))   # no kind: the kind stays
        self.assertEqual(out['item']['kind'], 'hard')
        # someone else's note: refused, nothing changes
        other, _, _ = self.store.session()
        with self.assertRaises(pfb.FeedbackError) as e:
            pfb.edit(self.store, other, dict(id=fid, text='Tôi sửa của người khác'))
        self.assertEqual((e.exception.status, e.exception.code), (409, 'not_editable'))
        self.assertEqual(pfb.list_mine(self.store, self.token)[0]['text'], 'Chỉ đổi chữ')
        # replied: no more edits
        pfb.update(self.store, fid, reply='Cảm ơn bạn!')
        with self.assertRaises(pfb.FeedbackError) as e:
            pfb.edit(self.store, self.token, dict(id=fid, text='Sửa sau khi đã có lời đáp'))
        self.assertEqual(e.exception.status, 409)
        self.assertEqual(pfb.list_mine(self.store, self.token)[0]['text'], 'Chỉ đổi chữ')
        for bad in (dict(id=fid, text=''), dict(id=fid, text='x' * 10001), dict(id='abc', text='Một góp ý'), dict(text='Một góp ý'),
                    dict(id=fid, text='Một góp ý', kind='rant'), dict(id=fid, text='đm đm'), 'x'):
            with self.subTest(bad=bad), self.assertRaises(pfb.FeedbackError):
                pfb.edit(self.store, self.token, bad)

    def test_edit_follows_the_account(self):
        self.send('Trước khi đăng ký')
        signed = accounts.register(self.store, self.token, dict(REG, username='sua_gop_y'))['token']
        fid = self.send('Ghi bằng tài khoản', token=signed)['id']
        other, _, _ = self.store.session()
        dev2 = accounts.login(self.store, other, dict(username='sua_gop_y', password=REG['password']))['token']
        self.assertEqual(pfb.edit(self.store, dev2, dict(id=fid, text='Sửa từ máy khác'))['item']['text'], 'Sửa từ máy khác')

    def test_forget_and_prune(self):
        other, _, _ = self.store.session()
        self.send('Của tôi')
        self.send('Của người khác', token=other)
        self.assertEqual(pfb.forget(self.store, self.token), 1)
        self.assertEqual(pfb.list_mine(self.store, self.token), [])
        self.assertEqual(len(pfb.list_mine(self.store, other)), 1)
        with self.store.connect() as db:
            db.execute('UPDATE player_feedback SET created_at=created_at-800*86400')
        self.assertEqual(pfb.prune(self.store), 1)


class FeedbackHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'op_admin'})
        cls.env.start()
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup(); cls.env.stop()

    def setUp(self):
        self.server.limits.clear()

    def req(self, dev, path, method='GET', body=None, headers=None, csrf=True):
        h = {'Host': f'127.0.0.1:{self.port}', 'User-Agent': 'FeedbackTest/1.0'}
        if dev.get('cookie'): h['Cookie'] = dev['cookie']
        if csrf and dev.get('csrf'): h['X-Game-CSRF'] = dev['csrf']
        if body is not None: h['Content-Type'] = 'application/json'; body = json.dumps(body)
        h.update(headers or {})
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse(); data = json.loads(res.read() or b'{}'); hdrs = dict(res.getheaders()); con.close()
        if 'Set-Cookie' in hdrs: dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(data, dict) and data.get('csrf'): dev['csrf'] = data['csrf']
        return res.status, data

    def device(self):
        dev = {}
        status, data = self.req(dev, '/api/bootstrap')
        self.assertEqual(status, 200)
        self.assertIs(data['admin'], False)
        return dev

    def signed(self, name):
        dev = self.device()
        status, data = self.req(dev, '/api/account/register', 'POST', dict(REG, username=name))
        self.assertEqual(status, 200, data)
        self.req(dev, '/api/bootstrap')
        return dev

    def admin(self):
        cls = type(self)
        if not getattr(cls, 'admin_dev', None):
            cls.admin_dev = self.signed('op_admin')
        return cls.admin_dev

    def send(self, dev, text='Màn hình chuẩn bị bị tràn chữ', kind='bug', **kw):
        return self.req(dev, '/api/feedback', 'POST', dict(kind=kind, text=text, context=dict(view='prepare', layout='phone', screen='390x844')), **kw)

    def test_submit_mine_and_isolation(self):
        a, b = self.device(), self.device()
        status, data = self.send(a)
        self.assertEqual(status, 200, data)
        self.assertEqual((data['ok'], data['message']), (True, 'Đã ghi nhận, cảm ơn bạn!'))
        self.assertIsInstance(data['id'], int)
        self.assertEqual(self.send(b, 'Ý tưởng của người B', 'idea')[0], 200)
        status, mine = self.req(a, '/api/feedback/mine')
        self.assertEqual(status, 200)
        self.assertEqual([x['text'] for x in mine['items']], ['Màn hình chuẩn bị bị tràn chữ'])
        self.assertIs(mine['admin'], False)
        self.assertEqual([x['text'] for x in self.req(b, '/api/feedback/mine')[1]['items']], ['Ý tưởng của người B'])
        with self.server.store.connect() as db:
            ctx = json.loads(db.execute('SELECT context FROM player_feedback WHERE id=?', (data['id'],)).fetchone()['context'])
        self.assertEqual((ctx['ua'], ctx['layout'], ctx['view']), ('FeedbackTest/1.0', 'phone', 'prepare'))

    def test_post_needs_csrf_session_and_json(self):
        a = self.device()
        self.assertEqual(self.send(a, csrf=False)[0], 403)
        self.assertEqual(self.send(a, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.req({}, '/api/feedback', 'POST', dict(kind='bug', text='Không có phiên'))[0], 401)
        self.assertEqual(self.req({}, '/api/feedback/mine')[0], 401)
        self.assertEqual(self.req(a, '/api/feedback', 'POST', dict(kind='bug', text='x' * 10001))[0], 400)
        self.assertEqual(self.req(a, '/api/feedback', 'POST', dict(kind='nope', text='Loại không có'))[0], 400)
        self.assertEqual(self.req(a, '/api/feedback/mine')[1]['items'], [])

    def test_rate_limits_per_ten_minutes_and_per_day(self):
        a = self.device()
        with patch.dict(os.environ, {'FEEDBACK_PER_10MIN': '2', 'FEEDBACK_PER_DAY': '30'}):
            self.assertEqual([self.send(a, f'Góp ý số {i}')[0] for i in range(3)], [200, 200, 429])
        self.server.limits.clear()
        with patch.dict(os.environ, {'FEEDBACK_PER_10MIN': '50', 'FEEDBACK_PER_DAY': '3'}):
            self.assertEqual([self.send(a, f'Góp ý ngày {i}')[0] for i in range(4)], [200, 200, 200, 429])
        self.server.limits.clear()
        with patch.dict(os.environ, {'FEEDBACK_PER_10MIN': '1'}):
            # Fresh sessions from one IP cannot multiply the budget (4 × the 10-minute limit per IP).
            codes = [self.send(self.device(), f'Phiên mới {i}')[0] for i in range(5)]
        self.assertEqual(codes, [200, 200, 200, 200, 429])
        self.assertEqual(len(self.req(a, '/api/feedback/mine')[1]['items']), 5)

    def test_edit_route(self):
        a, b = self.device(), self.device()
        fid = self.send(a, 'Chữ cũ của góp ý')[1]['id']
        status, data = self.req(a, '/api/feedback/edit', 'POST', dict(id=fid, text='Chữ mới của góp ý'))
        self.assertEqual(status, 200, data)
        self.assertEqual((data['item']['text'], data['message']), ('Chữ mới của góp ý', 'Đã lưu góp ý.'))
        self.assertEqual(self.req(b, '/api/feedback/edit', 'POST', dict(id=fid, text='Người khác sửa'))[0], 409)
        self.assertEqual(self.req(a, '/api/feedback/edit', 'POST', dict(id=fid, text='Không CSRF'), csrf=False)[0], 403)
        self.assertEqual(self.req(a, '/api/feedback/edit', 'POST', dict(id=fid, text='x'))[0], 400)
        self.assertEqual(self.req(a, '/api/feedback/mine')[1]['items'][0]['text'], 'Chữ mới của góp ý')
        with patch.dict(os.environ, {'FEEDBACK_EDITS_PER_10MIN': '1'}):
            self.server.limits.clear()
            codes = [self.req(a, '/api/feedback/edit', 'POST', dict(id=fid, text=f'Sửa lần {i}'))[0] for i in range(2)]
        self.assertEqual(codes, [200, 429])

    def test_admin_routes_are_gated(self):
        anon = self.device()
        self.send(anon, 'Chỗ này khó dùng quá', 'hard')
        player = self.signed('regular_joe')
        for dev in (anon, player):
            self.assertEqual(self.req(dev, '/api/admin/feedback')[0], 403)
            self.assertEqual(self.req(dev, '/api/admin/feedback', 'POST', dict(id=1, status='done'))[0], 403)
            self.assertIs(self.req(dev, '/api/bootstrap')[1]['admin'], False)
        admin = self.admin()
        _, boot = self.req(admin, '/api/bootstrap')
        self.assertIs(boot['admin'], True)
        self.assertNotIn('op_admin', json.dumps(self.req(anon, '/api/bootstrap')[1]))
        # A cookie alone (no CSRF header) does not open the inbox.
        self.assertEqual(self.req(admin, '/api/admin/feedback', csrf=False)[0], 403)
        status, page = self.req(admin, '/api/admin/feedback?status=new&kind=hard')
        self.assertEqual(status, 200, page)
        item = next(x for x in page['items'] if x['text'] == 'Chỗ này khó dùng quá')
        self.assertIn('context', item)
        self.assertEqual(item['context']['layout'], 'phone')
        self.assertEqual(self.req(admin, '/api/admin/feedback?status=bogus')[0], 400)
        # Reply + status; the author sees both.
        status, out = self.req(admin, '/api/admin/feedback', 'POST', dict(id=item['id'], status='done', reply='Cảm ơn, bản sau sẽ gọn hơn!'))
        self.assertEqual(status, 200, out)
        self.assertEqual((out['item']['status'], out['item']['reply']), ('done', 'Cảm ơn, bản sau sẽ gọn hơn!'))
        mine = self.req(anon, '/api/feedback/mine')[1]['items'][0]
        self.assertEqual((mine['status'], mine['reply']), ('done', 'Cảm ơn, bản sau sẽ gọn hơn!'))
        self.assertEqual(self.req(admin, '/api/admin/feedback', 'POST', dict(id=10 ** 9, status='seen'))[0], 404)
        self.assertEqual(self.req(admin, '/api/admin/feedback', 'POST', dict(id=item['id'], reply='x' * 301))[0], 400)
        self.assertIs(self.req(admin, '/api/feedback/mine')[1]['admin'], True)
        # Removing the account from ADMIN_USERS closes the inbox at once.
        with patch.dict(os.environ, {'ADMIN_USERS': ''}):
            self.assertEqual(self.req(admin, '/api/admin/feedback')[0], 403)

    def test_admin_paging(self):
        admin = self.admin()
        a = self.device()
        with patch.dict(os.environ, {'FEEDBACK_PER_10MIN': '100', 'FEEDBACK_PER_DAY': '100'}):
            for i in range(55):
                self.assertEqual(self.send(a, f'Trang {i:02d}', 'idea')[0], 200)
        _, p1 = self.req(admin, '/api/admin/feedback?kind=idea')
        self.assertEqual(len(p1['items']), 50)
        self.assertIsNotNone(p1['next'])
        _, p2 = self.req(admin, f'/api/admin/feedback?kind=idea&before={p1["next"]}')
        self.assertGreaterEqual(len(p2['items']), 5)
        self.assertLess(max(x['id'] for x in p2['items']), min(x['id'] for x in p1['items']))

    def test_delete_my_data_removes_feedback(self):
        a = self.device()
        self.send(a, 'Xóa tôi đi nhé')
        with self.server.store.connect() as db:
            before = db.execute("SELECT COUNT(*) FROM player_feedback WHERE text='Xóa tôi đi nhé'").fetchone()[0]
        self.assertEqual(before, 1)
        self.assertEqual(self.req(a, '/api/account/delete', 'POST', dict(confirm='XOA'))[0], 200)
        with self.server.store.connect() as db:
            after = db.execute("SELECT COUNT(*) FROM player_feedback WHERE text='Xóa tôi đi nhé'").fetchone()[0]
        self.assertEqual(after, 0)


if __name__ == '__main__':
    unittest.main()
