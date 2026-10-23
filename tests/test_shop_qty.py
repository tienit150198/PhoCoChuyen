"""🛍️ Cửa hàng, "mua thì cho mua nhiều cái 1 lần" (owner 23/10): one purchase of many, one price for all, all or none.

* jr_wd_buy `items` (game/wardrobe.py): several different pieces (each is owned once, so "many" is many pieces), one
  wallet row for the sum, worn at once or kept; a missing coin, a piece owned or not for sale refuses the whole list;
  a list all owned already (a retry) pays nothing; `item` alone is the command it was.
* jr_pet_buy `qty` (game/pets.py): toys and accessories of one kind, now up to pets_content.ITEM_QTY_MAX (was 3).
* jr_pet_wing_buy `qty` (game/wings.py): the wallet is checked for the whole before a wing is made.
* charm_buy `qty` (game/friend_charms.py): N pairs in the box, one effect row for the sum (its request id: a retry pays
  nothing), the box's room and the wallet for all of them.
A replayed command request id answers the first result and charges once (game/storage.py command), checked here on the
two engine commands that changed. The pets' qty (jr_pet_adopt, jr_pet_wbuy, jr_pet_gear_buy): tests/test_pet_buy_qty.py."""
import copy
import tempfile
import unittest
from pathlib import Path

from game import friend_charms as fc
from game import marriage as mr
from game import pets_content as C
from game import wardrobe as wd
from game import wings as W
from game.engine import GameError, validate_state
from tests.test_bank import story as bank_story
from tests.test_marriage import Base
from tests.test_wardrobe import act, story


def refused(test, s, name, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before, 'a refused purchase changes nothing')
    return str(cm.exception)


def owned(s):
    return set(wd._box_owned(s))


class WardrobeMany(unittest.TestCase):
    PIECES = ['ao_len', 'ao_hoodie', 'non_la']

    def test_many_pieces_one_price_worn_at_once(self):
        s = story(wallet=1000)
        cost = sum(wd.price(s, i) for i in self.PIECES)
        s, r = act(s, 'jr_wd_buy', items=self.PIECES)
        self.assertEqual(s['journey']['wallet'], 1000 - cost)
        self.assertTrue(set(self.PIECES) <= owned(s))
        self.assertEqual(r['bought'], self.PIECES)
        self.assertEqual(s['wardrobe']['look']['acc'], 'non_la')
        self.assertEqual(s['wardrobe']['look']['top'], 'ao_hoodie', 'two tops: the last one is worn')
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['label']), (-cost, f'{wd.LABEL} · 3 món'), 'one wallet row for the sum')
        validate_state(s)
        again, r2 = act(s, 'jr_wd_buy', items=self.PIECES)   # a retry: all owned, nothing paid
        self.assertEqual(again['journey']['wallet'], s['journey']['wallet'])
        self.assertEqual(r2['bought'], [])

    def test_all_or_none(self):
        s = story(wallet=150)                    # one piece fits, not the three
        self.assertIn('Ví chưa đủ', refused(self, s, 'jr_wd_buy', items=self.PIECES))
        s, _ = act(s, 'jr_wd_buy', item='ao_len')
        rich = copy.deepcopy(s)
        rich['journey']['wallet'] = 10_000
        self.assertIn('đã có Áo len', refused(self, rich, 'jr_wd_buy', items=['ao_hoodie', 'ao_len']))
        refused(self, rich, 'jr_wd_buy', items=['ao_hoodie', 'ao_cuoi'])        # not for sale: nothing bought
        for bad in ({'items': []}, {'items': ['ao_hoodie', 'ao_hoodie']}, {'items': 'ao_hoodie'},
                    {'items': ['ao_hoodie'], 'item': 'non_la'}, {}, {'items': ['ao_hoodie'] * (wd.BUY_MANY_MAX + 1)},
                    {'items': [1]}, {'items': ['ao_hoodie'], 'qty': 2}):
            refused(self, rich, 'jr_wd_buy', **bad)

    def test_kept_not_worn(self):
        s = story(wallet=1000)
        before = s['wardrobe']['look']
        s, r = act(s, 'jr_wd_buy', items=['ao_hoodie', 'non_la'], wear=False)
        self.assertEqual(s['wardrobe']['look'], before)
        self.assertIn('cất vào tủ', r['message'])

    def test_request_id_charges_once(self):
        store, token, rev = _store(self, 10_000)
        one = store.command(token, 'req-wd-many-1', rev, None, 'jr_wd_buy', dict(items=self.PIECES))
        again = store.command(token, 'req-wd-many-1', rev, None, 'jr_wd_buy', dict(items=self.PIECES))
        self.assertEqual(one['result'], again['result'])
        s = store.read(token)[0]
        self.assertEqual(s['journey']['wallet'], 10_000 - sum(wd.price(s, i) for i in self.PIECES))


def _store(test, wallet):
    from game.storage import Store
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    test.addCleanup(tmp.cleanup)
    store = Store(Path(tmp.name) / 's.db', story=True)
    test.addCleanup(store.close_pool)
    token, _, _ = store.session()
    store.read(token)

    def fn(s):
        s['journey']['wallet'] = wallet
        s['journey']['gender'] = 'female'
        wd.migrate(s)
    mr._mutate(store, {store.key(token): fn})
    return store, token, store.read(token)[1]


class PetItemsMany(unittest.TestCase):
    def test_toys_up_to_the_new_cap_all_or_none(self):
        s = bank_story(wallet=1_000_000)
        price = C.TOY['bong']['price']
        s, r = act(s, 'jr_pet_buy', id='bong', qty=C.ITEM_QTY_MAX, confirm=True)
        self.assertEqual(s['journey']['wallet'], 1_000_000 - price * C.ITEM_QTY_MAX)
        self.assertEqual(s['journey']['pets']['own']['bong'], C.TOY['bong']['uses'] * C.ITEM_QTY_MAX)
        self.assertIn(f'×{C.ITEM_QTY_MAX}', r['message'])
        refused(self, s, 'jr_pet_buy', id='bong', qty=C.ITEM_QTY_MAX + 1, confirm=True)
        poor = bank_story(wallet=price * 2)
        refused(self, poor, 'jr_pet_buy', id='bong', qty=3, confirm=True)

    def test_request_id_charges_once(self):
        store, token, rev = _store(self, 100_000)
        p = dict(id='bong', qty=5, confirm=True)
        one = store.command(token, 'req-toy-many-1', rev, None, 'jr_pet_buy', p)
        again = store.command(token, 'req-toy-many-1', rev, None, 'jr_pet_buy', p)
        self.assertEqual(one['result'], again['result'])
        s = store.read(token)[0]
        self.assertEqual(s['journey']['wallet'], 100_000 - 5 * C.TOY['bong']['price'])


class WingsMany(unittest.TestCase):
    def test_the_wallet_for_the_whole(self):
        st = W.INDEX['buom']
        s = bank_story(wallet=st['price'] * 2)
        refused(self, s, 'jr_pet_wing_buy', style='buom', qty=3, confirm=True)
        s, r = act(s, 'jr_pet_wing_buy', style='buom', qty=2, rid='req-wing-many-1', confirm=True)
        self.assertEqual((len(r['wings']), s['journey']['wallet']), (2, 0))
        again, r2 = act(s, 'jr_pet_wing_buy', style='buom', qty=2, rid='req-wing-many-1', confirm=True)
        self.assertEqual((again['journey']['wallet'], [x['id'] for x in r2['wings']]), (0, [x['id'] for x in r['wings']]))


class PairsMany(Base):
    def mine(self, tok):
        return self.act(tok, 'charm_view')['charms']

    def test_qty_pairs_one_price_and_a_retry_pays_nothing(self):
        a = self.user('fc_many', wallet=10_000)
        price = fc.INDEX['tri_ki']['price']
        out = self.act(a, 'charm_buy', kind='tri_ki', qty=4, rid='same-rid-many-01')
        self.assertEqual(self.wallet(a), 10_000 - 4 * price)
        self.assertEqual([x['kind'] for x in out['charms']['box']], ['tri_ki'] * 4)
        again = self.act(a, 'charm_buy', kind='tri_ki', qty=4, rid='same-rid-many-01')
        self.assertIn('đã mua rồi', again['message'])
        self.assertEqual((self.wallet(a), len(self.mine(a)['box'])), (10_000 - 4 * price, 4))

    def test_all_or_none_room_wallet_and_bad_numbers(self):
        a = self.user('fc_many_poor', wallet=fc.INDEX['tri_ki']['price'] * 2)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'charm_buy', kind='tri_ki', qty=3)
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(self.mine(a)['box'], [])
        self.fund(a, 1_000_000)
        self.act(a, 'charm_buy', kind='tri_ki', qty=fc.BOX_MAX - 2)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'charm_buy', kind='tri_ki', qty=3)
        self.assertEqual(e.exception.code, 'box_full')
        self.assertEqual(len(self.mine(a)['box']), fc.BOX_MAX - 2, 'none of the three')
        for bad in (0, -1, fc.BOX_MAX + 1, 2.0, '2', True, None):
            with self.assertRaises(mr.MarriageError):
                self.act(a, 'charm_buy', kind='tri_ki', qty=bad)

    def test_with_a_friend_the_first_goes_the_rest_wait(self):
        a, b = self.user('fc_many_a', wallet=10_000), self.user('fc_many_b')
        self.befriend(self.sid(a), self.sid(b))
        self.act(a, 'charm_buy', kind='ban_than', qty=3, code=self.code(b))
        v = self.mine(a)
        self.assertEqual((len(v['sent']), len(v['box'])), (1, 2))


if __name__ == '__main__':
    unittest.main()
