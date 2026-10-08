"""🎨 Cho trang trí (game/home_coop.py, feedback #257): a friend decorates the owner's home, permission first."""
import concurrent.futures
import copy
import json
import uuid
from unittest.mock import patch

from game import deco as dc, home_coop as hc, home_guests as hg, marriage as mr, social
from tests.test_marriage import Base
from tests.test_housing import buy


def bag_items(s):
    return [x for x in s['journey']['reno']['items'] if x['id'] not in dc.layout(s)['pos']]


class HomeCoop(Base):
    def setUp(self):
        super().setUp()
        self.a, self.b, self.c = [self.user(n, 10000) for n in ('host', 'friend', 'stranger')]
        self.codes = {t: self.code(t) for t in (self.a, self.b, self.c)}
        self.befriend(self.sid(self.a), self.sid(self.b))
        self.befriend(self.sid(self.a), self.sid(self.c))

        def setup(s):
            s.update(buy(s, 'tap_the')[0])
            for k in ('ghe_may', 'cay_canh', 'sofa'):
                dc.apply(s, 'jr_deco_buy', dict(item=k, confirm=True))
        mr._mutate(self.store, {self.sid(self.a): setup})

    # ------------------------------------------------------------ helpers
    def post(self, token, sub, **data):
        return hg.post(self.store, token, self.state(token), 'deco/' + sub, data)

    def get(self, token, sub, **query):
        return hg.get(self.store, token, self.state(token), 'deco/' + sub, query)

    def grant(self, token=None, to=None, hours=0):
        return self.post(token or self.a, 'grant', code=self.codes[to or self.b], hours=hours)

    def hview(self, token=None):
        return self.get(token or self.b, 'view', code=self.codes[self.a])

    def spot(self, token=None):
        """A free floor spot in the owner's first room for the ghế mây (from the owner's bag)."""
        v = self.hview(token)
        uid = next(b['id'] for b in v['deco']['bag'] + v['deco']['items'] if b['k'] == 'ghe_may')
        room = next(r for r in v['deco']['rooms'] if r['type'] in dc.ITEMS['ghe_may']['rooms'])
        return uid, room['id']

    def put(self, token=None, **kw):
        uid, room = self.spot(token)
        body = dict(code=self.codes[self.a], action='put', uid=uid, r=room, x=kw.pop('x', 20), y=kw.pop('y', 20), f=0)
        body.update(kw)
        return hg.post(self.store, token or self.b, self.state(token or self.b), 'deco/act', body), uid

    # ------------------------------------------------------------ permission
    def test_only_owner_can_grant_to_a_current_friend(self):
        with self.assertRaises(mr.MarriageError):           # not a home they own
            self.post(self.b, 'grant', code=self.codes[self.a], hours=0)
        out = self.grant(hours=24)['deco']
        self.assertEqual(len(out['mine']), 1)
        self.assertEqual(out['mine'][0]['expires_at'], self.clock.t + 24 * 3600)
        with self.assertRaises(mr.MarriageError):           # one active grant a pair
            self.grant()
        with self.assertRaises(mr.MarriageError):
            self.post(self.a, 'grant', code=self.codes[self.b], hours=5)
        with self.store.connect() as db:
            db.execute('DELETE FROM friends WHERE sid=? AND friend=?', (self.sid(self.a), self.sid(self.c)))
        with self.assertRaises(mr.MarriageError):
            self.grant(to=self.c)
        listing = hg.get(self.store, self.b, self.state(self.b), '', {})
        self.assertEqual(listing['deco']['homes'][0]['name'], 'Host')

    def test_no_grant_no_view_no_change(self):
        with self.assertRaises(mr.MarriageError) as e:
            self.hview()
        self.assertEqual(e.exception.status, 403)
        self.grant()
        uid, room = self.spot()
        before = self.store.read(self.a)[:2]
        for token in (self.c, self.a):                        # a stranger (even a friend) and the owner's own token
            with self.assertRaises(mr.MarriageError):
                hg.post(self.store, token, self.state(token), 'deco/act',
                        dict(code=self.codes[self.a], action='put', uid=uid, r=room, x=20, y=20, f=0))
        self.assertEqual(self.store.read(self.a)[:2], before)

    def test_friend_places_from_the_owners_bag_and_the_change_is_logged(self):
        self.grant()
        wallet = (self.state(self.a)['journey']['wallet'], self.state(self.b)['journey']['wallet'])
        friend_before = self.store.read(self.b)[:2]
        items = copy.deepcopy(self.state(self.a)['journey']['reno']['items'])
        out, uid = self.put()
        self.assertFalse(out['duplicate'])
        self.assertIn(uid, {p['id'] for p in out['view']['deco']['items']})
        self.assertIn(uid, dc.layout(self.state(self.a))['pos'])
        # nothing changes hands: the same furniture list, both wallets, the friend's save untouched
        self.assertEqual(self.state(self.a)['journey']['reno']['items'], items)
        self.assertEqual((self.state(self.a)['journey']['wallet'], self.state(self.b)['journey']['wallet']), wallet)
        self.assertEqual(self.store.read(self.b)[:2], friend_before)
        log = self.get(self.a, 'log')['log']
        self.assertEqual(log[0]['name'], 'Friend')
        self.assertTrue(log[0]['text'].startswith('đã đặt Ghế mây'))
        self.assertTrue(log[0]['undo'])
        self.assertEqual(out['view']['coop']['log'][0]['text'], log[0]['text'])
        again, _ = self.put()                                  # the same spot twice: nothing written, nothing logged
        self.assertTrue(again['duplicate'])
        self.assertEqual(len(self.get(self.a, 'log')['log']), 1)

    def test_only_moves_no_buying_selling_or_paint(self):
        self.grant()
        uid, room = self.spot()
        for body in (dict(action='buy', item='sofa'), dict(action='sell', uid=uid), dict(action='skin', r=room),
                     dict(action='pick', uid='all'), dict(action='put', uid=uid, r=room, x=1, y=1, f=0, n='abcd1234'),
                     dict(action='put', uid=uid, r=room, x=1, y=1, f=0, confirm=True)):
            with self.subTest(body=body), self.assertRaises(mr.MarriageError):
                hg.post(self.store, self.b, self.state(self.b), 'deco/act', dict(code=self.codes[self.a], **body))
        with self.assertRaises(Exception):                     # a piece the owner does not have
            hg.post(self.store, self.b, self.state(self.b), 'deco/act',
                    dict(code=self.codes[self.a], action='put', uid='nope', r=room, x=1, y=1, f=0))

    def test_revoke_expiry_unfriend_block_and_moving_end_it(self):
        gid = self.grant()['deco']['mine'][0]['id']
        self.put()
        self.post(self.a, 'revoke', id=gid)
        with self.assertRaises(mr.MarriageError):
            self.put()
        # time limited
        self.grant(hours=2)
        self.clock.t += 2 * 3600 + 1
        with self.assertRaises(mr.MarriageError):
            self.hview()
        self.assertEqual(self.get(self.a, 'log')['mine'], [])
        # a block either way, unfriending
        owner, friend = self.sid(self.a), self.sid(self.b)
        for sql, args in (('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)', (friend, owner, self.clock.t)),
                          ('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)', (social.pid_of(owner), social.pid_of(friend), self.clock.t)),
                          ('DELETE FROM friends WHERE sid=? AND friend=?', (owner, friend))):
            self.grant()
            with self.store.connect() as db:
                db.execute(sql, args)
            with self.assertRaises(mr.MarriageError):
                self.put()
            with self.store.connect() as db:
                db.execute('DELETE FROM marriage_blocks')
                db.execute('DELETE FROM blocks')
            self.befriend(owner, friend)
            self.assertEqual(self.get(self.a, 'log')['mine'], [])
        # the friend stops
        gid = self.grant()['deco']['mine'][0]['id']
        with self.assertRaises(mr.MarriageError):
            self.post(self.a, 'leave', id=gid)
        self.post(self.b, 'leave', id=gid)
        self.assertEqual(self.get(self.b, 'log')['homes'], [])

    def command(self, token, action, **payload):
        return self.store.command(token, str(uuid.uuid4()), self.store.read(token)[1], None, action, payload)

    def test_import_and_moving_end_the_grant_in_both_store_paths(self):
        for tries in (4, 0):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                gid = self.grant()['deco']['mine'][0]['id']
                saved = copy.deepcopy(self.state(self.a))
                self.command(self.a, 'import_save', save={'format': 'mot-ngay-lam-nghe/save-v1', 'state': saved})
                with self.store.connect() as db:
                    self.assertIsNone(db.execute('SELECT id FROM home_deco_grants WHERE id=?', (gid,)).fetchone())
                with self.assertRaises(mr.MarriageError):
                    self.hview()
        self.fund(self.a, 20000)
        self.command(self.a, 'jr_home_buy', kind='can_ho_mini', down=dc.hs.HOMES['can_ho_mini']['price'], confirm=True, move_in=False)
        for tries in (4, 0):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                old = self.state(self.a)['journey']['home']['own']['id']
                new = self.state(self.a)['journey']['home']['props'][-1]['id']
                gid = self.grant()['deco']['mine'][0]['id']
                self.command(self.a, 'jr_home_move', id=new, confirm=True)
                with self.store.connect() as db:
                    self.assertEqual(db.execute('SELECT status FROM home_deco_grants WHERE id=?', (gid,)).fetchone()['status'], 'ended')
                self.command(self.a, 'jr_home_move', id=old, confirm=True)   # coming back does not revive it
                with self.assertRaises(mr.MarriageError):
                    self.hview()

    def test_owner_undo_puts_the_spot_back(self):
        self.grant()
        _, uid = self.put()
        self.assertIn(uid, dc.layout(self.state(self.a))['pos'])
        rev = self.store.read(self.a)[1]
        lid = self.get(self.a, 'log')['log'][0]['id']
        with self.assertRaises(mr.MarriageError):              # only the owner
            self.post(self.b, 'undo', id=lid)
        out = self.post(self.a, 'undo', id=lid)
        self.assertNotIn(uid, dc.layout(self.state(self.a))['pos'])
        self.assertGreater(self.store.read(self.a)[1], rev)
        self.assertTrue(out['deco']['log'][0]['undone'])
        with self.assertRaises(mr.MarriageError):
            self.post(self.a, 'undo', id=lid)

    def test_undo_newest_first_for_the_same_piece(self):
        self.grant()
        _, uid = self.put(x=20)
        self.put(x=40)
        log = self.get(self.a, 'log')['log']
        with self.assertRaises(mr.MarriageError) as e:
            self.post(self.a, 'undo', id=log[1]['id'])
        self.assertEqual(e.exception.code, 'newer')
        self.post(self.a, 'undo', id=log[0]['id'])
        self.post(self.a, 'undo', id=log[1]['id'])
        self.assertNotIn(uid, dc.layout(self.state(self.a))['pos'])

    def test_owner_edits_and_friend_edits_never_overwrite_each_other(self):
        """The owner's own deco command and the friend's change race: both land (revision guards, recomputed)."""
        self.grant()
        v = self.hview()
        room = v['deco']['rooms'][0]['id']
        bag = {b['k']: b['id'] for b in v['deco']['bag']}

        def friend():
            return hg.post(self.store, self.b, self.state(self.b), 'deco/act',
                           dict(code=self.codes[self.a], action='put', uid=bag['ghe_may'], r=room, x=20, y=20, f=0))

        def owner():
            for _ in range(5):
                try:
                    return self.command(self.a, 'jr_deco_put', uid=bag['cay_canh'], r=room, x=60, y=20, f=0)
                except Exception as e:  # noqa: BLE001 - a revision conflict: the page sends it again
                    if getattr(e, 'code', '') != 'revision_conflict':
                        raise
            raise AssertionError('owner never landed')

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda f: f(), (friend, owner)))
        pos = dc.layout(self.state(self.a))['pos']
        self.assertIn(bag['ghe_may'], pos)
        self.assertIn(bag['cay_canh'], pos)

    def test_revoke_racing_a_change(self):
        gid = self.grant()['deco']['mine'][0]['id']

        def change():
            try:
                self.put()
                return 'put'
            except mr.MarriageError:
                return 'refused'

        def revoke():
            self.post(self.a, 'revoke', id=gid)
            return 'revoked'

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda f: f(), (change, revoke)))
        with self.assertRaises(mr.MarriageError):
            self.put()
        with self.store.connect() as db:
            n = db.execute('SELECT count(*) AS n FROM home_deco_log').fetchone()['n']
        self.assertIn(n, (0, 1))

    def test_forget_removes_grants_and_log(self):
        self.grant()
        self.put()
        with self.store.connect() as db:
            hg.forget(db, self.sid(self.b))
            self.assertEqual(db.execute('SELECT count(*) AS n FROM home_deco_log').fetchone()['n'], 0)
        self.assertEqual(self.get(self.a, 'log')['mine'], [])

    def test_view_is_private_and_read_only(self):
        self.grant()
        before = [self.store.read(t)[:2] for t in (self.a, self.b)]
        v = self.hview()
        self.assertEqual(v['access']['kind'], 'deco')
        self.assertTrue(v['deco']['bag'])
        self.assertNotIn(self.sid(self.a), json.dumps(v))
        self.assertNotIn(self.sid(self.b), json.dumps(v))
        self.assertNotIn('wallet', json.dumps(v['deco']))
        self.assertEqual([self.store.read(t)[:2] for t in (self.a, self.b)], before)
