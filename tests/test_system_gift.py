"""🎁 Quà từ Phố Có Chuyện (game/system_gift.py, scripts/grant_gift.py, /api/bootstrap, /api/gift/seen):
a gift is paid into the right wallet exactly once, whatever the retries and tabs, only its save
ever sees the card, and the grant tool is idempotent."""
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import accounts, pg_schema
from game import system_gift as sg
from game.engine import GameError, migrate_state, validate_state
from game.storage import Store
from server import GameServer

ROOT = Path(__file__).resolve().parents[1]
TITLE = 'Quà xin lỗi từ Phố Có Chuyện'
TEXT = ('Tối qua sau khi cập nhật, game của bạn bị lỗi kết nối vài phút. Phố gửi bạn 100 xu thay lời xin lỗi, '
        'cảm ơn bạn đã kiên nhẫn 💛')


class Base(unittest.TestCase):
    story = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'g.db'
        self.store = Store(self.path, story=self.story)
        self.addCleanup(self.store.close_pool)
        for name, fn in (('hash_password', lambda pw: 'scrypt$test$' + pw), ('verify_password', lambda pw, stored: stored == 'scrypt$test$' + pw)):
            h = patch('game.accounts.' + name, fn)   # scrypt is slow on purpose
            h.start()
            self.addCleanup(h.stop)

    def guest(self):
        token, _, _ = self.store.session()
        return token

    def state(self, tok):
        return self.store.read(tok)[0]

    def wallet(self, tok):
        return self.state(tok)['journey']['wallet']

    def gift_rows(self, tok):
        return [r for r in self.state(tok)['journey']['history'] if r['label'] == sg.LABEL]

    def grant(self, tok, coins=100, gid='sorry-20261001-a', **kw):
        return sg.grant(self.store, self.store.key(tok), coins, kw.get('title', TITLE), kw.get('text', TEXT), gid)

    def load(self, tok):
        return sg.on_load(self.store, tok, self.state(tok))

    def row(self, gid):
        with self.store.connect() as db:
            r = db.execute('SELECT * FROM system_gifts WHERE id=?', (gid,)).fetchone()
        return dict(r) if r else None


class ApplyOnce(Base):
    def test_paid_once_with_history_row_and_a_valid_save(self):
        tok = self.guest()
        w0, rev0 = self.wallet(tok), self.store.read(tok)[1]
        self.assertEqual(self.grant(tok)['status'], 'created')
        self.assertEqual(self.wallet(tok), w0, 'granting never touches the save')
        self.assertEqual(self.store.read(tok)[1], rev0)
        changed, shown = self.load(tok)
        self.assertTrue(changed)
        self.assertEqual(shown, [dict(id='sorry-20261001-a', coins=100, title=TITLE, text=TEXT)])
        self.assertEqual(self.wallet(tok), w0 + 100)
        rows = self.gift_rows(tok)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['amount'], rows[0]['kind'], rows[0]['career']), (100, 'life', None))
        self.assertEqual(self.row('sorry-20261001-a')['status'], 'applied')
        # a second bootstrap: still listed (not acknowledged yet), never paid again
        changed, shown = self.load(tok)
        self.assertFalse(changed)
        self.assertEqual([g['id'] for g in shown], ['sorry-20261001-a'])
        self.assertEqual(self.wallet(tok), w0 + 100)
        self.assertEqual(len(self.gift_rows(tok)), 1)
        # the stored save passes every check, fresh from the database
        s = self.state(tok)
        validate_state(migrate_state(s))
        self.assertEqual(s['journey']['gifts'], ['sorry-20261001-a'])

    def test_a_retried_request_replays_its_receipt(self):
        tok = self.guest()
        w0 = self.wallet(tok)
        self.grant(tok)
        self.load(tok)
        again = self.store.command(tok, 'sysgift-sorry-20261001-a', None, None, sg.ACTION,
                                   dict(id='sorry-20261001-a', coins=100), internal=True)
        self.assertTrue(again['replayed'])
        self.assertEqual(self.wallet(tok), w0 + 100)
        self.assertEqual(len(self.gift_rows(tok)), 1)

    def test_crash_between_the_two_writes_and_pruned_receipts_never_pay_twice(self):
        tok = self.guest()
        w0 = self.wallet(tok)
        self.grant(tok)
        self.load(tok)
        sid = self.store.key(tok)
        # the row never got its 'applied' mark, and the receipt is gone (RECEIPT_DAYS later)
        self.store.transaction(lambda db: db.execute("UPDATE system_gifts SET status='pending',applied_at=NULL WHERE id=?", ('sorry-20261001-a',)))
        self.store.transaction(lambda db: db.execute('DELETE FROM receipts WHERE sid=?', (sid,)))
        changed, shown = self.load(tok)
        self.assertTrue(changed)   # the no-op command still went through
        self.assertEqual([g['id'] for g in shown], ['sorry-20261001-a'])
        self.assertEqual(self.wallet(tok), w0 + 100)
        self.assertEqual(len(self.gift_rows(tok)), 1)
        self.assertEqual(self.row('sorry-20261001-a')['status'], 'applied')

    def test_two_tabs_at_once(self):
        tok = self.guest()
        w0 = self.wallet(tok)
        self.grant(tok)
        state = self.state(tok)
        errors = []

        def tab():
            try:
                sg.on_load(self.store, tok, state)
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=tab) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(self.wallet(tok), w0 + 100)
        self.assertEqual(len(self.gift_rows(tok)), 1)

    def test_several_gifts_in_order_and_debt(self):
        tok = self.guest()
        sid = self.store.key(tok)
        # a wallet in debt goes up by exactly the coins too
        from game import marriage as mr
        mr._mutate(self.store, {sid: lambda s: s['journey'].update(wallet=-40, in_debt=True)})
        self.grant(tok, gid='g-one', coins=100)
        self.grant(tok, gid='g-two', coins=30, title='Cảm ơn', text='Cảm ơn bạn 💛')
        _, shown = self.load(tok)
        self.assertEqual([(g['id'], g['coins']) for g in shown], [('g-one', 100), ('g-two', 30)])
        s = self.state(tok)
        self.assertEqual(s['journey']['wallet'], 90)
        self.assertFalse(s['journey']['in_debt'])

    def test_a_client_cannot_send_the_gift_action(self):
        tok = self.guest()
        rev = self.store.read(tok)[1]
        with self.assertRaises(GameError) as e:
            self.store.command(tok, 'client-req-0001', rev, None, sg.ACTION, dict(id='free-money', coins=1000))
        self.assertEqual(e.exception.code, 'forbidden')
        with self.assertRaises(GameError):   # and the server path checks the amount
            self.store.command(tok, 'sysgift-too-much', None, None, sg.ACTION, dict(id='too-much', coins=sg.MAX_COINS + 1), internal=True)

    def test_bad_gift_ids_in_a_save_are_refused(self):
        s = migrate_state(self.state(self.guest()))
        for bad in ('x', ['a'], ['ok-id', 'ok-id'], ['bad id!'], ['g-%d' % i for i in range(sg.KEPT + 1)]):
            s['journey']['gifts'] = bad
            with self.assertRaises(GameError):
                validate_state(s)
        s['journey']['gifts'] = ['sorry-20261001-a']
        validate_state(s)


class Privacy(Base):
    def test_ack_hides_it_and_another_player_never_sees_it(self):
        a, b = self.guest(), self.guest()
        wb = self.wallet(b)
        self.grant(a)
        self.assertEqual(self.load(b), (False, []))
        self.assertEqual(self.wallet(b), wb)
        self.load(a)
        self.assertFalse(sg.seen(self.store, b, 'sorry-20261001-a'), 'someone else cannot acknowledge it')
        self.assertEqual(self.row('sorry-20261001-a')['status'], 'applied')
        self.assertTrue(sg.seen(self.store, a, 'sorry-20261001-a'))
        self.assertEqual(self.row('sorry-20261001-a')['status'], 'seen')
        self.assertIsNotNone(self.row('sorry-20261001-a')['seen_at'])
        self.assertEqual(self.load(a), (False, []))
        self.assertFalse(sg.seen(self.store, a, 'sorry-20261001-a'))
        self.assertFalse(sg.seen(self.store, a, 'bad id'))

    def test_an_account_gets_it_on_every_device_and_sees_it_once(self):
        token = self.guest()
        out = accounts.register(self.store, token, dict(username='minh_test', password='matkhau-dai-lam', confirm='matkhau-dai-lam', display='Minh'))
        phone = out['token']
        laptop = accounts.login(self.store, self.guest(), dict(username='minh_test', password='matkhau-dai-lam'))['token']
        self.assertEqual(self.store.key(phone), self.store.key(laptop))
        w0 = self.wallet(phone)
        self.grant(phone)
        self.assertEqual(len(self.load(laptop)[1]), 1)
        self.assertEqual(len(self.load(phone)[1]), 1)
        self.assertEqual(self.wallet(phone), w0 + 100)
        self.assertTrue(sg.seen(self.store, laptop, 'sorry-20261001-a'))
        self.assertEqual(self.load(phone), (False, []))
        # the pre-registration cookie no longer reaches the save, nor its gifts
        self.assertEqual(self.store.key(token)[:8], 'revoked:')

    def test_account_deletion_takes_its_gifts(self):
        tok = self.guest()
        self.grant(tok)
        sg.forget(self.store, tok)
        self.assertIsNone(self.row('sorry-20261001-a'))


class NotStory(Base):
    """A save without the story (dev and tests; production runs the story for every save) keeps its
    gift pending: never paid elsewhere, never shown."""
    story = False

    def test_stays_pending(self):
        tok = self.guest()
        s = self.state(tok)
        self.assertFalse(s['journey']['story'])
        w0, funds = s['journey']['wallet'], {cid: c['money'] for cid, c in s['careers'].items()}
        self.grant(tok)
        self.assertEqual(self.load(tok), (False, []))
        s = self.state(tok)
        self.assertEqual(s['journey']['wallet'], w0)
        self.assertEqual({cid: c['money'] for cid, c in s['careers'].items()}, funds)
        self.assertEqual(self.row('sorry-20261001-a')['status'], 'pending')
        with self.assertRaises(GameError) as e:
            self.store.command(tok, 'sysgift-sorry-20261001-a', None, None, sg.ACTION, dict(id='sorry-20261001-a', coins=100), internal=True)
        self.assertEqual(e.exception.code, 'not_story')


class Grant(Base):
    def test_idempotent_by_id(self):
        tok = self.guest()
        first = self.grant(tok)
        self.assertEqual(first['status'], 'created')
        again = self.grant(tok)
        self.assertEqual(again['status'], 'exists')
        self.assertEqual(again['gift']['created'], first['gift']['created'])
        for change in (dict(coins=99), dict(text=TEXT + '!'), dict(title='Khác')):
            with self.assertRaises(sg.GiftError):
                sg.grant(self.store, self.store.key(tok), change.get('coins', 100), change.get('title', TITLE), change.get('text', TEXT), 'sorry-20261001-a')
        with self.assertRaises(sg.GiftError):   # the same id for another save
            self.grant(self.guest())
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM system_gifts').fetchone()[0], 1)
        # after it was paid, a repeat is still "exists" and pays nothing
        self.load(tok)
        w = self.wallet(tok)
        self.assertEqual(self.grant(tok)['status'], 'exists')
        self.load(tok)
        self.assertEqual(self.wallet(tok), w)

    def test_default_id_dry_run_and_checks(self):
        tok = self.guest()
        sid = self.store.key(tok)
        dry = sg.grant(self.store, sid, 100, TITLE, TEXT, dry_run=True)
        self.assertEqual(dry['status'], 'would_create')
        self.assertEqual(dry['gift']['id'], sg.default_id(sid, 100, TITLE, TEXT))
        self.assertIsNone(self.row(dry['gift']['id']))
        self.assertEqual(sg.grant(self.store, sid, 100, TITLE, TEXT)['status'], 'created')
        self.assertEqual(sg.grant(self.store, sid, 100, TITLE, TEXT)['status'], 'exists')
        for args in ((sid, 0, TITLE, TEXT), (sid, sg.MAX_COINS + 1, TITLE, TEXT), (sid, 100, '', TEXT), (sid, 100, TITLE, 'x' * 301),
                     ('no-such-sid', 100, TITLE, TEXT), (sid, 100, TITLE, TEXT, 'bad id')):
            with self.assertRaises(sg.GiftError, msg=args):
                sg.grant(self.store, *args)

    def run_script(self, *args):
        env = {k: v for k, v in os.environ.items() if k != 'DATABASE_URL'}
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / 'grant_gift.py'), '--db', str(self.path), *args],
                              capture_output=True, text=True, env=env, timeout=60)

    def test_script(self):
        tok = self.guest()
        sid = self.store.key(tok)
        base = ['--sid', sid, '--coins', '100', '--title', TITLE, '--text', TEXT, '--id', 'sorry-20261001-x']
        dry = self.run_script(*base, '--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn('Thử (không ghi)', dry.stdout)
        self.assertIsNone(self.row('sorry-20261001-x'))
        first = self.run_script(*base)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn('Đã tạo quà sorry-20261001-x', first.stdout)
        self.assertIn('khách', first.stdout)
        second = self.run_script(*base)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('đã có', second.stdout)
        clash = self.run_script('--sid', sid, '--coins', '200', '--title', TITLE, '--text', TEXT, '--id', 'sorry-20261001-x')
        self.assertEqual(clash.returncode, 2)
        self.assertIn('Không ghi gì', clash.stderr)
        self.assertEqual(self.row('sorry-20261001-x')['coins'], 100)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM system_gifts').fetchone()[0], 1)
        missing = self.run_script('--user', 'nobody_here', '--coins', '100', '--title', TITLE, '--text', TEXT)
        self.assertNotEqual(missing.returncode, 0)


class Schema(unittest.TestCase):
    def test_postgres_table_matches(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 4)
        t = pg_schema.TABLE['system_gifts']
        self.assertEqual([c for c, _ in t['columns']], ['id', 'sid', 'coins', 'title', 'text', 'status', 'created', 'applied_at', 'seen_at'])
        self.assertEqual(t['key'], ('id',))
        self.assertIn('CREATE TABLE IF NOT EXISTS system_gifts', pg_schema.TABLES_DDL)
        self.assertIn('system_gifts (sid, status)', pg_schema.INDEX_DDL)


class HTTP(unittest.TestCase):
    """Through the server: bootstrap pays and lists, the ack needs the session's CSRF, another
    player never sees the card, the client cannot send the gift action."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.store = Store(Path(cls.temp.name) / 'state.db', story=True)
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.quiet = patch.dict(os.environ, {'QUIET': '1'})
        cls.quiet.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.store.close_pool()
        cls.temp.cleanup()
        cls.quiet.stop()

    def req(self, who, path, method='GET', body=None, csrf=True):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if who.get('cookie'):
            h['Cookie'] = who['cookie']
        if csrf and who.get('csrf'):
            h['X-Game-CSRF'] = who['csrf']
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        out = (res.status, dict(res.getheaders()), res.read())
        con.close()
        return out

    def boot(self, who):
        status, headers, body = self.req(who, '/api/bootstrap?lite=1')
        self.assertEqual(status, 200)
        if 'Set-Cookie' in headers:
            who['cookie'] = headers['Set-Cookie'].split(';')[0]
        data = json.loads(body)
        who['csrf'] = data['csrf']
        return data

    def test_flow(self):
        me, other = {}, {}
        first = self.boot(me)
        self.assertEqual(first['gifts'], [])
        self.boot(other)
        token = me['cookie'].split('=', 1)[1]
        w0 = first['state']['journey']['wallet']
        sg.grant(self.store, self.store.key(token), 100, TITLE, TEXT, 'sorry-http-1')
        self.assertEqual(self.boot(other)['gifts'], [])
        data = self.boot(me)
        self.assertEqual(data['gifts'], [dict(id='sorry-http-1', coins=100, title=TITLE, text=TEXT)])
        self.assertEqual(data['state']['journey']['wallet'], w0 + 100)
        self.assertEqual(data['state']['journey']['history'][0]['label'], sg.LABEL)
        self.assertNotIn('gifts', data['state']['journey'])   # the paid ids stay private
        again = self.boot(me)   # a reload before pressing the button: same card, same wallet
        self.assertEqual([g['id'] for g in again['gifts']], ['sorry-http-1'])
        self.assertEqual(again['state']['journey']['wallet'], w0 + 100)
        # the ack follows the POST rules: CSRF of the session, JSON
        status, _, _ = self.req(me, '/api/gift/seen', 'POST', dict(id='sorry-http-1'), csrf=False)
        self.assertEqual(status, 403)
        status, _, body = self.req(other, '/api/gift/seen', 'POST', dict(id='sorry-http-1'))
        self.assertEqual((status, json.loads(body)['seen']), (200, False))
        status, _, body = self.req(me, '/api/gift/seen', 'POST', dict(id='sorry-http-1'))
        self.assertEqual((status, json.loads(body)['ok'], json.loads(body)['seen']), (200, True, True))
        after = self.boot(me)
        self.assertEqual(after['gifts'], [])
        self.assertEqual(after['state']['journey']['wallet'], w0 + 100)
        # the gift action is the server's own
        status, _, body = self.req(me, '/api/command', 'POST', dict(request_id='client-gift-1', expected_revision=after['revision'],
                                                                   career=None, action=sg.ACTION, payload=dict(id='free', coins=500)))
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)['code'], 'forbidden')

    def test_a_failing_gift_never_blocks_loading(self):
        me = {}
        self.boot(me)
        with patch('game.system_gift.on_load', side_effect=RuntimeError('boom')):
            data = self.boot(me)
        self.assertEqual(data['gifts'], [])
        self.assertIn('state', data)


if __name__ == '__main__':
    unittest.main()
