"""🧾 Hóa đơn tháng (game/upkeep.py) and the other xu sinks of 03/10 (docs/ECONOMY_SINKS.md): the rates (free for a
bicycle and a small flat), the daily accrual and the bill every tháng, pro rata for what is bought or sold in between,
never below 0 (cash, then the bank account, the rest waived), nothing billed before the block existed, the views,
the save checks; the savings tier of game/invest.py (old terms keep the flat rate); the fair's new numbers."""
import copy
import json
import unittest

from game import bank as bk
from game import fair_knife as kn
from game import fair_scratch as xs
from game import garage as gr
from game import housing as hs
from game import invest as iv
from game import journey as jr
from game import upkeep as up
from game.engine import GameError, public_state, validate_state
from tests.test_bank import act, opened, story


def U(s):
    return s['journey']['upk']


def days(s, n=1):
    """Close `n` life days the way the engine does after end_day: the bank, the homes, then the bills."""
    notes = []
    for _ in range(n):
        s['journey']['life_day'] += 1
        notes += bk.on_life_day(s) + hs.on_life_day(s) + up.on_life_day(s)
    validate_state(s)
    return notes


def to_bill_day(s):
    """Up to the next bill day (a multiple of MONTH_DAYS), the bill included."""
    notes = []
    while True:
        notes += days(s)
        if s['journey']['life_day'] % up.MONTH_DAYS == 0:
            return notes


def own_car(s, vid, day=None):
    g = s['journey'].setdefault('garage', gr.initial())
    g['cars'][vid] = dict(c=gr.VEHICLES[vid]['paint'], n='', d=day or s['journey']['life_day'], p=gr.VEHICLES[vid]['price'])


def rows(s, kind='upkeep'):
    return [r for r in s['journey']['history'] if r['kind'] == kind]


class Rates(unittest.TestCase):
    def test_vehicles(self):
        self.assertEqual(up.car_month('xe_dap', 120), 0)            # bicycles are free
        self.assertEqual(up.car_month('xe_dap_dien', 300), 0)
        self.assertEqual(up.car_month('xe_so', 600), 3)             # 0,5 % a tháng
        self.assertEqual(up.car_month('o_to_mini', 3000), 23)       # 0,75 %
        self.assertEqual(up.car_month('du_thuyen', 45000), 450)     # 1 %
        self.assertEqual(up.car_month('phan_luc', 90000), 1125)     # 1,25 %
        self.assertEqual(up.car_month('khong_co', 5000), 0)         # an id a newer build wrote: nothing
        for vid, V in gr.VEHICLES.items():                          # dearer groups cost more a tháng, never above 1,5 %
            self.assertLessEqual(up.car_month(vid, V['price']) * 10000, V['price'] * 150, vid)

    def test_homes(self):
        for k in ('tap_the', 'can_ho_studio', 'can_ho_mini', 'can_ho_1pn'):
            self.assertEqual(up.home_month(k, hs.HOMES[k]['price']), 0, k)   # the small flats: only their điện nước
        self.assertEqual(up.home_month('nha_pho', 7800), 16)        # 0,2 %
        self.assertEqual(up.home_month('penthouse', 21600), 65)     # 0,3 %
        self.assertEqual(up.home_month('biet_thu_song', 60000), 210)   # 0,35 %
        self.assertEqual(up.home_bp('tro_moi'), 0)                  # a rented room
        for k in hs.OWN:                                            # letting a home still pays more than its upkeep
            self.assertLess(up.home_month(k, hs.HOMES[k]['price']), hs.rent_of(k), k)

    def test_the_new_models_and_the_catalogue(self):
        for vid in ('sieu_xe', 'truc_thang', 'sieu_du_thuyen'):
            self.assertIn(vid, gr.VEHICLES)
        cat = {v['id']: v for v in gr.catalogue()['vehicles']}
        self.assertEqual(cat['phan_luc']['upkeep'], 1125)
        self.assertEqual(cat['xe_dap']['upkeep'], 0)
        homes = {h['id']: h for h in hs.catalogue()['homes']}
        self.assertEqual(homes['biet_thu_song']['care'], 210)
        self.assertNotIn('care', homes['tro_moi'])


class Bills(unittest.TestCase):
    def test_the_block_starts_on_the_first_morning_and_bills_nothing_before(self):
        s = story(5000)
        s['journey']['life_day'] = 12
        own_car(s, 'o_to_suv', day=2)                                # owned long before this build
        self.assertNotIn('upk', s['journey'])
        validate_state(s)                                            # an older save: no block, valid
        s, r = act(s, 'jr_seen', ids=['x'])
        self.assertEqual(U(s), dict(v=1, since=12, day=12, acc=dict(car=0, home=0), paid=dict(car=0, home=0)))
        self.assertTrue(any('Ban quản lý' in x and '50 xu mỗi tháng' in x for x in r['effects']), r['effects'])
        self.assertEqual(s['journey']['wallet'], 5000)               # nothing for the ten days before
        to_bill_day(s)                                               # day 15: days 13, 14, 15
        self.assertEqual(s['journey']['wallet'], 5000 - 6600 * 75 * 3 // 50000)
        self.assertEqual(rows(s)[-1]['label'], 'Phí giữ xe & bảo dưỡng · 1 xe')

    def test_a_month_bills_once_whatever_the_retries(self):
        s = story(20000)
        up.on_life_day(s)
        own_car(s, 'phan_luc')
        own_car(s, 'xe_dap')
        s['journey']['life_day'] = 5 * 4 - 1
        U(s).update(since=19, day=19)
        notes = days(s)                                             # day 20: one day of the jet
        self.assertEqual(s['journey']['wallet'], 20000 - 225)                # 90 000 × 1,25 % / 5 days
        before = copy.deepcopy(s)
        self.assertEqual(up.on_life_day(s), [])                      # again: nothing
        self.assertEqual(s, before)
        for _ in range(5):                                           # a whole tháng: 1 125 xu
            days(s)
        self.assertEqual(before['journey']['wallet'] - s['journey']['wallet'], 1125)
        self.assertTrue(any(n.startswith('🧾 Hóa đơn tháng: phí giữ xe & bảo dưỡng') for n in notes))

    def test_pro_rata_for_a_vehicle_bought_or_sold_in_the_month(self):
        s = story(50000)
        up.on_life_day(s)
        to_bill_day(s)
        w = s['journey']['wallet']
        days(s, 2)
        own_car(s, 'du_thuyen')                                     # owned for the last 3 mornings of this tháng
        to_bill_day(s)
        self.assertEqual(w - s['journey']['wallet'], 45000 * 100 * 3 // 50000)
        w = s['journey']['wallet']
        days(s)
        s['journey']['garage']['cars'].pop('du_thuyen')             # sold after one more morning
        to_bill_day(s)
        self.assertEqual(w - s['journey']['wallet'], 45000 * 100 // 50000)

    def test_never_below_zero_the_bank_account_then_waived(self):
        s = opened(wallet=500, deposit=300)
        up.on_life_day(s)
        to_bill_day(s)
        own_car(s, 'phan_luc')                                       # 1 125 a tháng
        s['journey']['wallet'] = 100
        notes = []
        for _ in range(up.MONTH_DAYS):
            notes += days(s)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 0)
        self.assertFalse(s['journey']['in_debt'])
        line = next(n for n in notes if n.startswith('🧾'))
        self.assertIn('725 xu còn thiếu được miễn, không tính nợ', line)
        self.assertEqual(U(s)['paid']['car'], 400)
        s['journey']['wallet'] = -30                                 # a wallet in debt: never deeper
        for _ in range(up.MONTH_DAYS):
            days(s)
        self.assertEqual(s['journey']['wallet'], -30)

    def test_homes_lived_in_empty_or_let(self):
        s = story(100)
        h = s['journey']['home'] = hs.initial(1)
        home = lambda hid, kind: dict(id=hid, kind=kind, price=hs.HOMES[kind]['price'], day=1, down=hs.HOMES[kind]['price'],
                                      fee=hs.buy_fee(hs.HOMES[kind]['price']), joint=0, loan=None, mv=0, let=None, keep=None)
        h['own'] = home('h1', 'biet_thu_song')
        h['props'] = [home('h2', 'nha_pho'), home('h3', 'tap_the')]
        validate_state(s)
        up.on_life_day(s)
        to_bill_day(s)
        s['journey']['wallet'] = 10**6
        w = s['journey']['wallet']
        for _ in range(up.MONTH_DAYS):
            days(s)
        self.assertIn(w - s['journey']['wallet'], (225, 226))        # villa 210 + nhà phố 15,6 (the fraction carries over)
        self.assertEqual(rows(s)[-1]['label'], 'Phí bảo trì nhà · 2 căn')
        v = public_state(s)['journey']
        self.assertEqual(v['home']['care']['month'], 226)
        self.assertEqual(v['home']['own']['care'], 210)
        self.assertEqual([p['care'] for p in v['home']['props']], [16, 0])

    def test_non_story_and_the_views(self):
        s = story(500)
        s['journey']['story'] = False
        self.assertEqual(up.on_life_day(s), [])
        self.assertNotIn('upk', s['journey'])
        s = story(5000)
        s, _ = act(s, 'jr_garage_buy', id='o_to_mini', confirm=True)
        g = public_state(s)['journey']['garage']
        self.assertEqual(g['cars'][0]['upkeep'], 23)
        self.assertEqual(g['upkeep']['month'], 23)
        self.assertEqual(g['upkeep']['next'] % up.MONTH_DAYS, 0)
        s2 = story(5000)
        s2, _ = act(s2, 'jr_garage_buy', id='xe_dap', confirm=True)
        self.assertNotIn('upkeep', public_state(s2)['journey']['garage'])   # a bicycle: nothing to show

    def test_save_checks(self):
        s = story(500)
        up.on_life_day(s)
        validate_state(s)
        good = json.loads(json.dumps(s))
        for change in (lambda u: u.update(v=2), lambda u: u.update(extra=1), lambda u: u['acc'].update(car=-1),
                       lambda u: u['paid'].pop('home'), lambda u: u.update(day=10**5), lambda u: u.update(since=u['day'] + 1),
                       lambda u: u.update(acc=[])):
            bad = copy.deepcopy(good)
            change(bad['journey']['upk'])
            with self.assertRaises(GameError):
                validate_state(bad)
        older = copy.deepcopy(good)
        del older['journey']['upk']
        validate_state(older)


class SavingsTier(unittest.TestCase):
    def test_the_rate(self):
        self.assertEqual(iv.accrual(10000), 30000)                         # 0,3 %/ngày
        self.assertEqual(iv.accrual(50000), 20000 * 3 + 30000 * 1)          # 0,1 %/ngày above 20 000
        self.assertEqual(iv.accrual(50000, flat=True), 150000)

    def _saver(self, balance, term_day, since):
        s = story(1000)
        s['journey']['stats']['max_wallet'] = 1000
        iv.migrate(s)
        s['journey']['life_day'] = 10
        sv = s['journey']['invest']['saving']
        sv.update(balance=balance, term_day=term_day, pending=0)
        s['journey']['invest']['day'] = 10
        s['journey']['upk'] = up.initial(since)
        return s, sv

    def test_a_term_begun_before_keeps_the_flat_rate_until_it_ends(self):
        s, sv = self._saver(100000, term_day=8, since=10)
        self.assertTrue(iv.flat_term(s, sv))
        notes = []
        for _ in range(5):                                                  # days 10..14: the term ends on day 14
            iv._tick(s, s['journey']['invest'], s['journey']['invest']['day'], notes)
            s['journey']['invest']['day'] += 1
        self.assertEqual(sv['earned'], 100000 * 3 * 5 // 1000)                # the old flat 0,3 % for its days 10..14
        self.assertEqual(sv['term_day'], 15)
        self.assertFalse(iv.flat_term(s, sv))
        v = iv.public(s)['saving']
        self.assertEqual(v['daily_milli'], iv.accrual(sv['balance']))
        self.assertFalse(v['flat'])
        self.assertEqual(iv.public(s)['rules']['save_tier'], iv.SAVE_TIER)

    def test_a_new_deposit_says_the_tier(self):
        s = story(30000)
        s['journey']['stats']['max_wallet'] = 30000
        up.on_life_day(s)
        s, r = act(s, 'iv_save', amount=25000)
        self.assertIn('cho 20.000 xu đầu, phần trên lãi 0,1%/ngày', r['message'])
        s2 = story(5000)
        s2['journey']['stats']['max_wallet'] = 5000
        s2, r2 = act(s2, 'iv_save', amount=1000)
        self.assertNotIn('phần trên', r2['message'])


class Fair(unittest.TestCase):
    def test_the_scratch_card_keeps_a_small_edge(self):
        ev = lambda p: p * sum(m * w for m, w in xs.PRIZES) / sum(w for _, w in xs.PRIZES)
        self.assertTrue(.95 <= ev(xs.P_LO) <= ev(xs.P_HI) < 1.0)

    def test_the_knife_ladder_top(self):
        self.assertEqual(kn.LADDER[:5], (11, 12, 16, 21, 28))              # the sensible play pays as before
        self.assertLessEqual(kn.LADDER[-1], 100)


if __name__ == '__main__':
    unittest.main()
