"""🏡 F#307: a player living in a home they do not own decorates it freely with their own things, like their own home.

* A rented room: buy, place, move, turn, paint, sell, as in a home you own (no repairs).
* A friend living in your home by a "Mời ở chung" invite moves their furniture in (POST move, journey.decor_stay):
  they buy, place, move, turn, paint and sell their own pieces there; each resident sees the others' pieces read-only
  (GET /api/deco/mate) and never sells, moves or paints the host's.
* Leaving, a revoke, or a stay that no longer holds puts their pieces back in their bag (the layout kept in
  decor_away, back in place when they return).
* Rollback: a build that does not know journey.decor_stay treats the save as living at home again; this build reads
  what it left exactly.
"""
import copy
import itertools
import unittest

from game import deco as dc, deco_mate as dm, home_coop
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act
from tests.test_deco import D, bag, fp, renter
from tests.test_housing import buy
from tests.test_marriage import Base
from tests import test_rentals as _rentals


class Renter(unittest.TestCase):
    def test_a_renter_buys_places_moves_turns_paints_and_sells(self):
        s = renter('tro_moi', wallet=9000)
        self.assertEqual(D(s)['place']['where'], 'rent')
        s, r = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='tro', x=0, y=40))
        sofa = r['uid']
        s, r = act(s, 'jr_deco_buy', item='cay_canh', confirm=True, put=dict(r='tro', x=100, y=0))
        plant = r['uid']
        s, _ = act(s, 'jr_deco_put', uid=sofa, r='tro', x=20, y=40, face='back')       # move it and turn it round
        self.assertEqual(fp(s, sofa)[:3], ('tro', 20, 40))
        self.assertEqual(next(i for i in D(s)['items'] if i['id'] == sofa).get('face'), 'back')
        s, _ = act(s, 'jr_deco_skin', r='tro', part='wall', skin='kem')
        self.assertEqual(D(s)['rooms'][0]['skin'].get('w'), 'kem')
        wallet = s['journey']['wallet']
        s, r = act(s, 'jr_deco_sell', uid=plant, confirm=True)
        self.assertGreater(s['journey']['wallet'], wallet)
        self.assertNotIn(plant, {i['id'] for i in D(s)['items']} | {b['id'] for b in D(s)['bag']})
        self.assertFalse(D(s)['place']['repairs'])
        validate_state(s)

    def test_a_rented_room_given_back_puts_everything_in_the_bag(self):
        s = renter('tro_moi', wallet=9000)
        s, _ = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='tro', x=0, y=40))
        s, _ = act(s, 'jr_home_leave', confirm=True)
        self.assertEqual((D(s)['place']['where'], D(s)['items'], bag(s)), ('attic', [], ['sofa']))
        validate_state(s)


class PlayerLease(unittest.TestCase):
    """A home rented from another player (game/rentals.py): the tenant decorates it with their own things."""
    R = _rentals.Rentals
    setUp, user, state, cmd, act, prop, listing = R.setUp, R.user, R.state, R.cmd, R.act, R.prop, R.listing

    def test_a_tenant_decorates_and_takes_everything_when_leaving(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        v = dc.public(self.state(tenant))
        self.assertEqual(v['place']['where'], 'lease')
        room = v['rooms'][0]['id']
        sofa = self.cmd(tenant, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r=room, x=0, y=40))['result']['uid']
        plant = self.cmd(tenant, 'jr_deco_buy', item='cay_canh', confirm=True, put=dict(r=room, x=100, y=0))['result']['uid']
        self.cmd(tenant, 'jr_deco_put', uid=sofa, r=room, x=20, y=40, face='back')
        self.cmd(tenant, 'jr_deco_skin', r=room, part='wall', skin='kem')
        self.cmd(tenant, 'jr_deco_sell', uid=plant, confirm=True)
        self.assertEqual(fp(self.state(tenant), sofa)[:3], (room, 20, 40))
        self.assertEqual(dc.public(self.state(owner))['bag'], [])                     # nothing in the landlord's save
        self.act(tenant, 'leave', id=lid)
        self.cmd(tenant, 'settings', sound=False)
        s = self.state(tenant)
        self.assertEqual((D(s)['items'], bag(s)), ([], ['sofa']))
        validate_state(s)


class LivingWithAFriend(Base):
    seq = itertools.count()

    def setUp(self):   # as tests/test_home_guests.py: a host who owns Căn tập thể cũ, a friend, a stranger
        super().setUp()
        from game import home_guests, marriage as mr
        self.hg = home_guests
        self.a, self.b, self.c = [self.user(n, 10000) for n in ('host', 'guest', 'stranger')]
        self.codes = {t: self.code(t) for t in (self.a, self.b, self.c)}
        self.befriend(self.sid(self.a), self.sid(self.b))
        mr._mutate(self.store, {self.sid(self.a): lambda s: s.update(buy(s, 'tap_the')[0])})

    def post(self, token, sub, **data):
        return self.hg.post(self.store, token, self.state(token), sub, data)

    def listing(self, token):
        return self.hg.get(self.store, token, self.state(token), '', {})

    def invite(self, kind='stay'):
        return self.post(self.a, 'invite', code=self.codes[self.b], kind=kind)['outgoing'][0]['id']

    def accept(self, kind='stay'):
        ident = self.invite(kind)
        self.post(self.b, 'answer', id=ident, answer='accept')
        return ident

    def cmd(self, tok, action, **data):
        return self.store.command(tok, f'sd-{next(self.seq):06d}', self.store.read(tok)[1], None, action, data)

    def move(self, ident, on=True, tok=None):
        return self.post(tok or self.b, 'move', id=ident, on=on)

    def moved_in(self):
        ident = self.accept()
        self.move(ident)
        return ident

    def mine(self, tok):
        return public_state(self.state(tok))['journey']['deco']

    def mate(self, tok):
        return dm.view(self.store, tok, self.state(tok))

    def host_piece(self):
        out = self.cmd(self.a, 'jr_deco_buy', item='den_long', confirm=True, put=dict(r='living', x=0, y=0))
        return out['result']['uid']

    def test_a_friend_moves_in_and_decorates_with_their_own_things(self):
        lamp = self.host_piece()
        ident = self.moved_in()
        v = self.mine(self.b)
        host = self.mine(self.a)
        self.assertEqual(v['place']['where'], 'stay')
        self.assertEqual([r['id'] for r in v['rooms']], [r['id'] for r in host['rooms']])   # the host's rooms
        self.assertFalse(v['place']['repairs'])
        self.assertEqual(self.listing(self.b)['homes'][0]['here'], True)
        a_rev = self.store.read(self.a)[1]
        b_wallet = self.wallet(self.b)
        sofa = self.cmd(self.b, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=0, y=40))['result']['uid']
        plant = self.cmd(self.b, 'jr_deco_buy', item='cay_canh', confirm=True, put=dict(r='living', x=100, y=0))['result']['uid']
        self.assertLess(self.wallet(self.b), b_wallet)                                     # their own wallet
        self.cmd(self.b, 'jr_deco_put', uid=sofa, r='living', x=20, y=40, face='back')       # move, turn
        self.assertEqual(fp(self.state(self.b), sofa)[:3], ('living', 20, 40))
        self.cmd(self.b, 'jr_deco_skin', r='living', part='wall', skin='kem')               # their wall, their view
        self.cmd(self.b, 'jr_deco_sell', uid=plant, confirm=True)
        self.assertEqual({i['id'] for i in self.mine(self.b)['items']}, {sofa})
        self.assertEqual(self.store.read(self.a)[1], a_rev)                                 # the host's save never moved
        self.assertNotIn('living', dc.layout(self.state(self.a))['skins'])
        # each sees the other's pieces, read-only
        va, vb = self.mate(self.a), self.mate(self.b)
        self.assertEqual([(p['id'], p['n']) for p in va['items']], [('g0:' + sofa, 'Guest')])
        self.assertEqual(va['at'], host['place']['key'])
        self.assertEqual([p['id'] for p in vb['items']], ['p:' + lamp])
        self.assertEqual(vb['skins']['living']['w'], 'kem')
        self.assertTrue(vb['stay'] and not vb['owner'])
        self.assertEqual(self.store.read(self.a)[1], a_rev)
        for tok in (self.a, self.b):
            s = self.state(tok)
            validate_state(s)
            validate_state(migrate_state(copy.deepcopy(s)))
        self.assertTrue(ident)

    def test_a_refresh_parses_only_the_saves_that_changed(self):
        """Load: residents' saves are read by revision; nothing changed, nothing parsed; one change, one parse."""
        self.host_piece()
        self.moved_in()
        sofa = self.cmd(self.b, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=0, y=40))['result']['uid']
        self.mate(self.a), self.mate(self.b)                                                # warm
        dm.PARSED[0] = 0
        for _ in range(3):
            va, vb = self.mate(self.a), self.mate(self.b)
        self.assertEqual(dm.PARSED[0], 0)
        self.assertEqual([p['id'] for p in va['items']], ['g0:' + sofa])
        self.cmd(self.b, 'jr_deco_put', uid=sofa, r='living', x=20, y=40)                  # the friend moves their sofa
        va2, _vb = self.mate(self.a), self.mate(self.b)
        self.assertEqual(dm.PARSED[0], 1)                                                    # only the friend's save
        self.assertEqual(va2['items'][0]['fx'], 20)
        self.cmd(self.a, 'jr_deco_buy', item='cay_canh', confirm=True, put=dict(r='living', x=100, y=0))
        self.assertEqual(len(self.mate(self.b)['items']), 2)
        self.assertEqual(dm.PARSED[0], 2)                                                    # then only the host's
        self.mate(self.a), self.mate(self.b)
        self.assertEqual(dm.PARSED[0], 2)

    def test_the_cache_is_bounded(self):
        with self.subTest('rows'):
            saved = dm.CACHE_ROWS
            dm.CACHE_ROWS = 3
            try:
                for i in range(6):
                    dm._cache_put((f's{i}', 1), dict(pieces=[]))
                self.assertLessEqual(len(dm._CACHE), 3)
                dm._cache_put(('s5', 2), dict(pieces=[]))                                   # a newer revision replaces
                self.assertEqual([k for k in dm._CACHE if k[0] == 's5'], [('s5', 2)])
            finally:
                dm.CACHE_ROWS = saved

    def test_nobody_sells_or_moves_another_residents_piece(self):
        """Commands only ever reach the actor's own save and its own pieces (piece ids are per save: the same 'd1' in
        two saves are two different things). The others' pieces come with a prefix and are found nowhere."""
        lamp = self.host_piece()
        table = self.cmd(self.a, 'jr_deco_buy', item='ban_tra', confirm=True)['result']['uid']   # the host's, in their bag
        self.moved_in()
        sofa = self.cmd(self.b, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=0, y=40))['result']['uid']
        mine = self.mine(self.b)
        self.assertNotIn(table, {i['id'] for i in mine['items']} | {i['id'] for i in mine['bag']})
        before = [self.store.read(t)[:2] for t in (self.a, self.b)]
        for tok, uid in ((self.a, 'g0:' + sofa), (self.b, 'p:' + lamp), (self.b, table)):
            for action, extra in (('jr_deco_sell', dict(confirm=True)), ('jr_deco_pick', {}),
                                  ('jr_deco_put', dict(r='living', x=40, y=40))):
                with self.assertRaises(GameError, msg=(tok == self.a, uid, action)):
                    self.cmd(tok, action, uid=uid, **extra)
        self.assertEqual([self.store.read(t)[:2] for t in (self.a, self.b)], before)
        self.cmd(self.a, 'jr_deco_sell', uid=lamp, confirm=True)       # the host sells their own 'd1'...
        self.assertEqual(self.store.read(self.b)[:2], before[1])       # ...the friend's sofa never moved
        self.assertEqual([p['id'] for p in self.mate(self.a)['items']], ['g0:' + sofa])
        # 🎨 Cho trang trí moves the host's pieces only: the friend's sofa is not in the host's save
        with self.assertRaises(GameError):
            dc.apply(copy.deepcopy(self.state(self.a)), home_coop.ACTS['pick'], dict(uid='g0:' + sofa))

    def test_leaving_puts_the_pieces_back_in_the_bag_and_coming_back_restores_them(self):
        ident = self.moved_in()
        sofa = self.cmd(self.b, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=0, y=40))['result']['uid']
        self.cmd(self.b, 'jr_deco_buy', item='cay_canh', confirm=True, put=dict(r='living', x=100, y=0))
        self.cmd(self.b, 'jr_deco_put', uid=sofa, r='living', x=0, y=40, face='back')
        self.move(ident, on=False)                                                         # 📦 Dọn đồ về
        v = self.mine(self.b)
        self.assertEqual((v['place']['where'], v['items'], sorted(bag(self.state(self.b)))), ('attic', [], ['cay_canh', 'sofa']))
        self.assertNotIn('decor_stay', self.state(self.b)['journey'])
        self.assertEqual(self.mate(self.a), {})
        self.move(ident)                                                                   # back: as it was, turned round too
        self.assertEqual(fp(self.state(self.b), sofa)[:3], ('living', 0, 40))
        self.assertEqual(next(i for i in self.mine(self.b)['items'] if i['id'] == sofa).get('face'), 'back')
        self.post(self.b, 'leave', id=ident)                                               # leaving the home
        s = self.state(self.b)
        self.assertNotIn('decor_stay', s['journey'])
        self.assertEqual((D(s)['place']['where'], sorted(bag(s))), ('attic', ['cay_canh', 'sofa']))
        with self.assertRaises(Exception):                                                 # no stay, no moving in
            self.move(ident)
        validate_state(s)

    def test_a_revoke_or_an_ended_friendship_sends_the_pieces_home(self):
        ident = self.moved_in()
        self.cmd(self.b, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=0, y=40))
        self.post(self.a, 'revoke', id=ident)
        self.assertEqual(bag(self.state(self.b)), ['sofa'])
        self.assertNotIn('decor_stay', self.state(self.b)['journey'])
        # an unfriend ends it without touching the guest's save: the next look puts the pieces back
        ident = self.moved_in()
        self.cmd(self.b, 'jr_deco_put', uid=self.mine(self.b)['bag'][0]['id'], r='living', x=0, y=40)

        def unfriend(db):
            db.execute('DELETE FROM friends WHERE sid=? OR friend=?', (self.sid(self.a), self.sid(self.a)))
        self.store.transaction(unfriend)
        self.assertEqual(self.mate(self.b), {'moved': True})
        self.assertEqual(bag(self.state(self.b)), ['sofa'])
        self.assertEqual(self.mine(self.b)['place']['where'], 'attic')
        self.assertEqual(self.mate(self.a), {})

    def test_only_an_accepted_stay_of_your_own_lets_you_move_in(self):
        ident = self.invite()
        with self.assertRaises(Exception):
            self.move(ident)                                   # not accepted yet
        self.post(self.b, 'answer', id=ident, answer='accept')
        with self.assertRaises(Exception):
            self.move(ident, tok=self.c)                       # someone else's invite
        self.post(self.b, 'leave', id=ident)
        visit = self.accept('visit')
        with self.assertRaises(Exception):
            self.move(visit)                                   # a visit is not living there
        self.assertNotIn('decor_stay', self.state(self.b)['journey'])

    def test_a_forged_stay_in_a_save_shows_nothing_and_is_cleared(self):
        self.accept()
        from game import marriage as mr
        def forge(s):
            s['journey']['decor_stay'] = dict(v=1, id='0' * 16, home=self.state(self.a)['journey']['home']['own']['id'], kind='tap_the')
        mr._mutate(self.store, {self.sid(self.b): forge})
        self.assertEqual(self.mine(self.b)['place']['where'], 'stay')
        self.assertEqual(self.mate(self.b), {'moved': True})
        self.assertNotIn('decor_stay', self.state(self.b)['journey'])
        self.assertEqual(self.mate(self.a), {})

    def test_rollback_an_older_build_reads_the_save_as_living_at_home(self):
        """What 1.9.37 does with a save that lives in a friend's home: journey.decor_stay is an extra journey key it
        keeps and ignores, so its place() is the player's own room; its first command packs the stay layout into
        decor_away. Back on this build the layout is where it was. (The real 1.9.37 tree: see the release notes.)"""
        self.moved_in()
        sofa = self.cmd(self.b, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=0, y=40))['result']['uid']
        s = copy.deepcopy(self.state(self.b))
        stay = s['journey'].pop('decor_stay')                  # the older build's place(): the attic
        validate_state(s)
        s, _ = act(s, 'jr_deco_buy', item='cay_canh', confirm=True)
        self.assertEqual((D(s)['place']['where'], D(s)['items']), ('attic', []))
        self.assertEqual(sorted(bag(s)), ['cay_canh', 'sofa'])
        self.assertTrue(any(x['at'].startswith('stay:') for x in s['journey']['decor_away']['places']))
        s['journey']['decor_stay'] = stay                      # it kept the key; this build again
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(D(s)['place']['where'], 'stay')
        s2, _ = act(s, 'jr_deco_buy', item='den_long', confirm=True)   # the next command follows the player back
        self.assertEqual(fp(s2, sofa)[:3], ('living', 0, 40))
        validate_state(s2)
