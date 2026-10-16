"""🏝️ Đảo riêng (game/island.py, game/island_content.py; owner 16/10 "cho phép mua đảo riêng giá cao, mời bạn ra chơi bằng
du thuyền hoặc phi cơ, có dung lượng người dùng"): the catalogue and the seats of every vehicle, buying and selling
(wallet then bank, never into debt, wallet rows a build can validate), the monthly fee, the save block's shape, the
views and the 💰 board."""
import copy
import unittest
import unittest.mock

from game import bank as bk
from game import garage
from game import island as isl
from game import island_content as C
from game import journey as jr
from game import lux
from game import wealth
from game.engine import GameError, public_state, validate_state
from tests.test_bank import act, story

ROW = 10_000_000


def I(s):
    return s['journey']['island']


def money(s):
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def refused(test, s, name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


def rich(wallet=50_000_000, bank=0):
    s = story(wallet + bank)
    if bank:
        s, _ = act(s, 'jr_bk_open')
        while s['journey']['bank']['balance'] < bank:
            s, _ = act(s, 'jr_bk_deposit', amount=min(bk.AMOUNT_MAX, bank - s['journey']['bank']['balance']))
    return s


def next_day(s, n=1):
    for _ in range(n):
        s['journey']['life_day'] += 1
        s, _ = act(s, 'jr_seen', ids=['x'])
    return s


def buy(s, iid='dao_dua'):
    return act(s, 'jr_island_buy', id=iid, confirm=True)


class Catalogue(unittest.TestCase):
    def test_four_islands_priced_for_the_richest(self):
        prices = [i['price'] for i in C.ISLANDS]
        self.assertEqual(prices, sorted(prices))
        self.assertEqual(len(C.ISLANDS), 4)
        self.assertGreaterEqual(prices[0], 13_000_000)      # the top 10 hold ≥ 13M
        self.assertLessEqual(prices[-1], 10**8)
        self.assertEqual(len({i['id'] for i in C.ISLANDS}), 4)
        self.assertEqual(len({i['look'] for i in C.ISLANDS}), 4)   # each its own map
        for i in C.ISLANDS:
            self.assertTrue(isl._id(i['id']) and 10 <= i['bp'] <= 60, i)
        self.assertTrue(50 <= C.SELL_PCT <= 65)

    def test_seats_are_keyed_by_existing_vehicle_ids(self):
        for vid, (n, kind) in C.SEATS.items():
            self.assertTrue(vid in garage.VEHICLES or vid in lux.ASSET, vid)
            self.assertIn(kind, ('boat', 'heli', 'plane'))
            self.assertTrue(2 <= n <= C.SEATS_MAX, vid)
        boats = [vid for vid, v in garage.VEHICLES.items() if v['group'] in ('boat', 'plane')]
        self.assertTrue(set(boats) <= set(C.SEATS))   # every yacht and plane of today has its seats
        self.assertEqual(C.SEATS['may_bay_nho'][0], 2)      # "Hai chỗ ngồi"
        self.assertEqual(C.SEATS['truc_thang'][0], 4)       # "Bốn ghế"
        self.assertEqual(C.SEATS['phan_luc'][0], 8)         # "Tám ghế da"
        self.assertGreaterEqual(C.SEATS['du_thuyen_hg'][0], 20)
        self.assertGreater(C.SEATS['sieu_du_thuyen'][0], C.SEATS['du_thuyen'][0])
        self.assertIsNone(isl.seats_of('xe_dap'))            # a bicycle takes nobody to an island
        with unittest.mock.patch.dict(garage.VEHICLES, {'tau_moi': dict(garage.VEHICLES['du_thuyen'], id='tau_moi')}):
            self.assertEqual(isl.seats_of('tau_moi'), C.GROUP_SEATS['boat'])   # a newer garage model: its group's seats

    def test_content_and_catalogue(self):
        cat = isl.catalogue()
        self.assertEqual([i['id'] for i in cat['islands']], [i['id'] for i in C.ISLANDS])
        self.assertEqual(cat['seats']['chuyen_co'], dict(seats=16, arrive='plane'))
        self.assertEqual(cat['islands'][0]['month'], 15_000_000 * 30 // 10000)
        self.assertEqual(jr.content()['island']['islands'][0]['id'], 'dao_dua')


class Buying(unittest.TestCase):
    def test_buy_pays_wallet_then_bank_in_rows_a_build_can_read(self):
        s = rich(8_000_000, bank=30_000_000)
        before = money(s)
        s, r = buy(s, 'dao_san_ho')
        self.assertEqual(before - money(s), 30_000_000)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 8_000_000)
        self.assertIn('dao_san_ho', I(s)['own'])
        self.assertEqual(I(s)['own']['dao_san_ho']['p'], 30_000_000)
        self.assertIn('tiền mặt', r['message'])
        validate_state(s)

    def test_a_big_cash_purchase_is_split_into_rows_of_at_most_ten_million(self):
        s = rich(120_000_000)
        s, _ = buy(s, 'dao_hoang_hon')
        rows = [h for h in s['journey']['history'] if h['label'].startswith('Mua đảo')]
        self.assertEqual(sum(h['amount'] for h in rows), -100_000_000)
        self.assertTrue(all(-ROW <= h['amount'] < 0 and h['kind'] == 'life' for h in rows))
        self.assertEqual(len(rows), 10)
        self.assertEqual(s['journey']['wallet'], 20_000_000)
        validate_state(s)
        s, r = act(s, 'jr_island_sell', id='dao_hoang_hon', confirm=True)
        back = [h for h in s['journey']['history'] if h['label'].startswith('Bán lại')]
        self.assertEqual(sum(h['amount'] for h in back), 60_000_000)
        self.assertTrue(all(0 < h['amount'] <= ROW for h in back))
        self.assertEqual(s['journey']['wallet'], 80_000_000)
        self.assertNotIn('dao_hoang_hon', I(s)['own'])
        validate_state(s)

    def test_refusals_change_nothing(self):
        s = rich(10_000_000, bank=4_000_000)
        refused(self, s, 'jr_island_buy', 'not_enough', id='dao_dua', confirm=True)
        refused(self, s, 'jr_island_buy', id='dao_dua')                 # no confirm
        refused(self, s, 'jr_island_buy', id='dao_khong_co', confirm=True)
        refused(self, s, 'jr_island_sell', 'not_owned', id='dao_dua', confirm=True)
        refused(self, s, 'jr_island_buy', id='dao_dua', confirm=True, extra=1)
        bk_ok = rich(0, bank=30_000_000)
        bk_ok['journey']['wallet'] = -5
        why = refused(self, bk_ok, 'jr_island_buy', 'not_enough', id='dao_dua', confirm=True)
        self.assertIn('nợ', why)

    def test_second_tap_pays_nothing_and_several_islands_are_owned(self):
        s = rich(60_000_000)
        s, _ = buy(s, 'dao_dua')
        w = s['journey']['wallet']
        s, r = buy(s, 'dao_dua')
        self.assertTrue(r.get('duplicate'))
        self.assertEqual(s['journey']['wallet'], w)
        s, _ = buy(s, 'dao_san_ho')
        self.assertEqual(sorted(isl.owned(s)), ['dao_dua', 'dao_san_ho'])
        self.assertEqual(I(s)['stats']['bought'], 2)

    def test_free_play_cannot_buy(self):
        s = rich(20_000_000)
        s['journey']['story'] = False
        with self.assertRaises(GameError):
            isl.action(s, 'jr_island_buy', dict(id='dao_dua', confirm=True))


class Upkeep(unittest.TestCase):
    def test_monthly_fee_is_billed_with_the_month_like_a_villa(self):
        s = rich(16_000_000)
        s, _ = buy(s, 'dao_dua')
        month = isl.monthly(s)
        self.assertEqual(month, 15_000_000 * 30 // 10000)
        start = s['journey']['life_day']
        w = s['journey']['wallet']
        s = next_day(s, bk.MONTH_DAYS)
        rows = [h for h in s['journey']['history'] if h['label'].startswith(isl.UPKEEP_LABEL)]
        self.assertTrue(rows)
        self.assertLessEqual(w - s['journey']['wallet'], month)
        self.assertGreater(w - s['journey']['wallet'], 0)
        self.assertEqual(I(s)['upk']['paid'], w - s['journey']['wallet'])
        validate_state(s)

    def test_bank_then_waived_never_a_debt(self):
        s = rich(15_000_000, bank=100_000)
        s, _ = buy(s, 'dao_dua')
        self.assertEqual(s['journey']['wallet'], 0)
        s = next_day(s, bk.MONTH_DAYS * 2)
        self.assertGreaterEqual(s['journey']['wallet'], 0)
        self.assertGreaterEqual(s['journey']['bank']['balance'], 0)
        self.assertLess(s['journey']['bank']['balance'], 100_000)
        s = next_day(s, bk.MONTH_DAYS * 3)
        self.assertGreaterEqual(s['journey']['bank']['balance'], 0)
        self.assertGreaterEqual(s['journey']['wallet'], 0)
        validate_state(s)

    def test_idempotent_and_nothing_before_the_block(self):
        s = rich(16_000_000)
        s = next_day(s, 7)
        s, _ = buy(s, 'dao_dua')
        u = copy.deepcopy(I(s)['upk'])
        self.assertEqual(u['since'], s['journey']['life_day'])
        isl.on_life_day(s)
        self.assertEqual(I(s)['upk'], u)


class SaveBlock(unittest.TestCase):
    def owned(self):
        s = rich(40_000_000)
        s, _ = buy(s, 'dao_dua')
        return s

    def test_absent_block_and_strict_shape(self):
        s = rich(1000)
        validate_state(s)
        self.assertNotIn('island', s['journey'])
        self.assertNotIn('island', public_state(s)['journey'])
        for bad in ({'v': 2}, {'own': {'dao_dua': {'d': 1}}}, {'own': {'Dao': {'d': 1, 'p': 5}}}, {'stats': {'x': 1}},
                    {'upk': {'since': 1}}, {'extra': 1}):
            t = self.owned()
            I(t).update(bad)
            with self.assertRaises(GameError):
                validate_state(t)

    def test_a_newer_builds_block_is_kept_by_shape(self):
        s = self.owned()
        I(s)['own']['dao_moi'] = dict(d=3, p=200_000_000)       # an island of a newer build
        I(s)['zz'] = {'later': True}
        jr.upgrade(s['journey'])
        self.assertNotIn('zz', I(s))
        self.assertIn('dao_moi', I(s)['own'])
        validate_state(s)
        self.assertNotIn('dao_moi', public_state(s)['journey']['island']['own'])
        self.assertEqual(isl.worth(s['journey']), isl.sell_price(15_000_000))
        self.assertEqual(isl.monthly(s), isl.month_of('dao_dua', 15_000_000))   # it pays nothing here

    def test_public_and_wealth(self):
        s = self.owned()
        pub = public_state(s)['journey']['island']
        self.assertEqual(pub['own']['dao_dua']['sell'], 9_000_000)
        self.assertEqual(pub['month'], 45_000)
        w = wealth.worth(s)
        self.assertIsNotNone(w)
        s2 = copy.deepcopy(s)
        del s2['journey']['island']
        self.assertEqual(wealth.worth(s)[0] - wealth.worth(s2)[0], 9_000_000)

    def test_vehicles_that_take_friends(self):
        s = rich(40_000_000)
        s, _ = act(s, 'jr_garage_buy', id='du_thuyen', color='navy', confirm=True)
        s, _ = act(s, 'jr_garage_buy', id='xe_dap', color='do', confirm=True)
        s, _ = act(s, 'jr_lux_buy', id='chuyen_co', confirm=True)
        got = isl.vehicles(s)
        self.assertEqual([(v['id'], v['seats'], v['arrive']) for v in got], [('chuyen_co', 16, 'plane'), ('du_thuyen', 8, 'boat')])
        s, _ = act(s, 'jr_island_buy', id='dao_dua', confirm=True)
        self.assertEqual([v['id'] for v in public_state(s)['journey']['island']['rides']], ['chuyen_co', 'du_thuyen'])


if __name__ == '__main__':
    unittest.main()
