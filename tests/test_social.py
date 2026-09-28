import json
import tempfile
import unittest
from pathlib import Path

from game import social, push
from game.engine import apply_action, new_state, GameError
from game.social import SocialError
from game.storage import Store


class Player:
    def __init__(self, store, name=None):
        self.store = store
        self.token, self.csrf, _ = store.session(None)
        self.n = 0
        self.cmd('select_career', career='restaurant')
        if name:
            self.post('profile', name=name, bio='Quán nhỏ vui vẻ')

    @property
    def state(self):
        return self.store.read(self.token)[0]

    @property
    def c(self):
        return self.state['careers']['restaurant']

    @property
    def pid(self):
        return social.pid_of(self.store.key(self.token))

    def cmd(self, action, career='restaurant', **payload):
        self.n += 1
        rev = self.store.read(self.token)[1]
        return self.store.command(self.token, f'test-{self.n:06d}-{id(self)}', rev, career, action, payload)['result']

    def get(self, route, **q):
        return social.get(self.store, self.token, self.state, route, q)

    def post(self, route, **d):
        return social.post(self.store, self.token, self.state, route, d)


class SocialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.sqlite3')
        social.ensure(self.store)
        push.ensure(self.store)
        self.a = Player(self.store, 'Mây Bếp')
        self.b = Player(self.store, 'Gió Hoa')

    def tearDown(self):
        self.tmp.cleanup()

    def test_profile_rules(self):
        with self.assertRaises(SocialError):
            Player(self.store, 'mây bếp')  # names are unique ignoring case
        p = Player(self.store)
        for bad in ('x', 'ghé www.abc.com', '0912345678', 'a@b.com'):
            with self.assertRaises(SocialError):
                p.post('profile', name=bad)
        with self.assertRaises(SocialError):
            p.post('review', pid=self.a.pid, stars=5, text='ngon quá')  # needs a name first
        names = [x['name'] for x in self.b.get('directory')['players']]
        self.assertIn('Mây Bếp', names)
        self.assertNotIn('sid', json.dumps(self.b.get('directory')))

    def test_visit_review_reply_and_inbox(self):
        with self.assertRaises(SocialError):
            self.b.post('review', pid=self.a.pid, stars=4, text='Chưa ghé mà chấm')
        shop = self.b.get('shop', pid=self.a.pid)
        self.assertTrue(shop['can_review'])
        self.b.post('review', pid=self.a.pid, stars=4, text='Mì dai, nước dùng đậm!')
        with self.assertRaises(SocialError):
            self.b.post('review', pid=self.a.pid, stars=5, text='Chấm lần hai')
        inbox = self.a.get('inbox')
        kinds = [x['kind'] for x in inbox['items']]
        self.assertIn('visit', kinds)
        self.assertIn('review', kinds)
        rid = self.a.get('shop', pid=self.a.pid)['reviews'][0]['id']
        self.a.post('reply', id=rid, text='Cảm ơn bạn nhé!')
        with self.assertRaises(SocialError):
            self.a.post('reply', id=rid, text='Trả lời lần hai')
        self.assertEqual(self.b.get('shop', pid=self.a.pid)['reviews'][0]['reply'], 'Cảm ơn bạn nhé!')
        with self.assertRaises(SocialError):
            self.a.post('review', pid=self.a.pid, stars=5, text='Tự khen')

    def test_gift_moves_coins_once(self):
        before_a, before_b = self.a.c['money'], self.b.c['money']
        self.a.post('gift', pid=self.b.pid, sticker='🍜', coins=10, note='Chúc buôn may bán đắt')
        self.assertEqual(self.a.c['money'], before_a - 10)
        with self.assertRaises(SocialError):
            self.a.post('gift', pid=self.b.pid, sticker='🌸', coins=0)
        with self.assertRaises(SocialError):
            self.a.post('gift', pid=self.b.pid, sticker='💣', coins=0)
        self.b.get('inbox')
        self.b.get('inbox')  # settling twice must not pay twice
        self.assertEqual(self.b.c['money'], before_b + 10)
        self.assertTrue(any(x['category'] == 'gift' for x in self.b.c['ops']['finance']['ledger']))

    def test_market_escrow_buy_payout_and_unlist(self):
        stock = lambda p, item: sum(l['qty'] for l in p.c['ext']['inv']['lots'] if l['item'] == item)
        item = next(l['item'] for l in self.a.c['ext']['inv']['lots'] if l['qty'] >= 3)
        a0, b0 = stock(self.a, item), stock(self.b, item)
        with self.assertRaises(SocialError):
            self.a.post('list', career='restaurant', item=item, qty=2, price=10 ** 6)
        self.a.post('list', career='restaurant', item=item, qty=2, price=self._price(item))
        self.assertEqual(stock(self.a, item), a0 - 2)
        listing = self.b.get('market', career='restaurant')['listings'][0]
        with self.assertRaises(SocialError):
            self.a.post('buy', id=listing['id'])
        money_a, money_b = self.a.c['money'], self.b.c['money']
        self.b.post('buy', id=listing['id'])
        self.assertEqual(stock(self.b, item), b0 + 2)
        self.assertEqual(self.b.c['money'], money_b - listing['total'])
        with self.assertRaises(SocialError):
            Player(self.store, 'Người Thứ Ba').post('buy', id=listing['id'])
        self.a.get('market')
        self.a.get('market')
        self.assertEqual(self.a.c['money'], money_a + listing['total'])
        self.a.post('list', career='restaurant', item=item, qty=1, price=self._price(item))
        mine = self.a.get('market')['mine'][0]
        self.a.post('unlist', id=mine['id'])
        self.assertEqual(stock(self.a, item), a0 - 2)

    def test_buy_without_money_releases_listing(self):
        item = next(l['item'] for l in self.a.c['ext']['inv']['lots'] if l['qty'] >= 3)
        self.a.post('list', career='restaurant', item=item, qty=3, price=self._price(item) * 3 // 1)
        broke = Player(self.store, 'Hết Tiền')
        # Drain the wallet through a gift chain is slow; set money through a real
        # command path instead: spend on stock orders until short.
        st, rev, _ = self.store.read(broke.token)
        st['careers']['restaurant']['money'] = 0
        st['careers']['restaurant']['ops']['finance']['opening_balance'] -= self.store.read(broke.token)[0]['careers']['restaurant']['money']
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(st, ensure_ascii=False), self.store.key(broke.token)))
        lid = broke.get('market')['listings'][0]['id']
        with self.assertRaises(SocialError):
            broke.post('buy', id=lid)
        self.assertEqual(self.b.get('market')['listings'][0]['status'], 'active')

    def test_board_comments_reactions_reports(self):
        self.a.post('board', career='restaurant', kind='tip', text='Mì nên trụng 13 giây là vừa.')
        post = self.b.get('board', career='restaurant')['posts'][0]
        self.b.post('react', post=post['id'], emoji='👏')
        self.b.post('comment', post=post['id'], text='Hay quá, cảm ơn!')
        post = self.a.get('board')['posts'][0]
        self.assertEqual(post['reactions']['👏']['n'], 1)
        self.assertEqual(len(post['comments']), 1)
        self.b.post('react', post=post['id'], emoji='👏')
        self.assertNotIn('👏', self.a.get('board')['posts'][0]['reactions'])
        for i in range(3):
            Player(self.store, f'Người Báo {i}').post('report', kind='board', id=post['id'], reason='spam')
        self.assertEqual(self.a.get('board')['posts'], [])

    def test_block_and_forget(self):
        self.a.post('block', pid=self.b.pid)
        with self.assertRaises(SocialError):
            self.b.get('shop', pid=self.a.pid)
        with self.assertRaises(SocialError):
            self.b.post('gift', pid=self.a.pid, sticker='🌸', coins=0)
        self.assertNotIn(self.b.pid, [x['pid'] for x in self.a.get('directory')['players']])
        social.forget(self.store, self.b.token)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM profiles WHERE pid=?', (self.b.pid,)).fetchone())

    def test_internal_actions_not_public(self):
        s = apply_action(new_state(), 'restaurant', 'select_career')[0]
        with self.assertRaises(GameError):
            apply_action(s, 'restaurant', 'soc_gift_in', dict(coins=100))
        with self.assertRaises(GameError):
            apply_action(s, 'restaurant', 'fb_resolve', dict(post='x'))

    def test_community_goal_counts_week(self):
        data = self.a.get('community')
        self.assertEqual(data['community']['goal'], social.WEEK_GOAL)

    def _price(self, item):
        from game.careers import PLUGINS
        spec = next(x for x in PLUGINS['restaurant'].SPEC['inventory']['items'] if x['id'] == item)
        return max(1, spec['cost'])


class PushTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.sqlite3')
        social.ensure(self.store)
        push.ensure(self.store)
        push._keys.clear()

    def tearDown(self):
        push._keys.clear()
        self.tmp.cleanup()

    def test_vapid_signature_verifies(self):
        k = push.keys()
        header = push.vapid_header(k['d'], 'https://fcm.googleapis.com/fcm/send/abc', push.subject())
        jwt = header.split('t=')[1].split(',')[0]
        h, c, sig = jwt.split('.')
        self.assertTrue(push.verify(push.unb64u(k['public']), f'{h}.{c}'.encode(), push.unb64u(sig)))
        self.assertEqual(json.loads(push.unb64u(c))['aud'], 'https://fcm.googleapis.com')

    def test_subscribe_whitelist_queue_and_pending(self):
        a = Player(self.store, 'Mây Bếp')
        b = Player(self.store, 'Gió Hoa')
        with self.assertRaises(SocialError):
            push.subscribe(self.store, a.token, dict(subscription=dict(endpoint='https://evil.example/steal')))
        with self.assertRaises(SocialError):
            push.subscribe(self.store, a.token, dict(subscription=dict(endpoint='http://fcm.googleapis.com/x')))
        push.subscribe(self.store, a.token, dict(subscription=dict(endpoint='https://fcm.googleapis.com/fcm/send/abc'), prefs=dict(social=True)))
        b.get('shop', pid=a.pid)
        items = push.pending(self.store, a.token)['items']
        self.assertEqual(items[0]['tag'], 'visit')
        self.assertEqual(push.pending(self.store, a.token)['items'], [])
        push.forget(self.store, a.token)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM push_subs').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
