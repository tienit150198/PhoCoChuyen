"""🏘️ Several homes (game/housing.py VERSION 2): version 1 saves upgrade losslessly (a loan half paid, a late fee,
a spouse, repairs and decor), buying a second and a third home, the bank's 40 % limit over every home loan,
letting a home (rent at the month boundary, the tenant's light moments), moving between homes (comfort, upkeep,
repairs kept, decor to the bag), selling any home, paying per home, the wallet never below 0, the save checks."""
import copy
import unittest

from game import bank as bk
from game import deco as dc
from game import housing as hs
from game import journey as jr
from game import reno as rn
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import B, act, opened, story
from tests.test_deco import place_new
from tests.test_housing import H, buy


def tick(s, n=1, salary=0):
    """Close `n` life days like end_day: salary, the bank, the homes, the inside of the home, the decor."""
    notes = []
    for _ in range(n):
        j = s['journey']
        if salary:
            jr._wallet(j, salary, 'salary', 'Lương ngày')
        j['life_day'] += 1
        notes += bk.on_life_day(s) + hs.on_life_day(s) + rn.on_life_day(s) + dc.on_life_day(s)
        assert j['wallet'] >= 0 or not salary
    validate_state(s)
    return notes


def buy2(s, kind, down=None, months=36, **p):
    """Buy through the engine with the exact quote (as the page does); `p`: move_in, joint…"""
    price = hs.HOMES[kind]['price']
    down = price if down is None else down
    q = dict(kind=kind, down=down, confirm=True, **p)
    if down < price:
        quote = hs.quote(price - down, hs.offer(s, hs.need_score(kind))['rate'], months, s['journey']['life_day'])
        q.update(months=months, total_interest=quote['interest'])
    return act(s, 'jr_home_buy', **q)


def legacy_tenant(s, hid):
    """Existing NPC contracts keep their own fixed rent; new advert demand is tested in test_rentals."""
    s = copy.deepcopy(s)
    x = hs.find(H(s), hid)
    day = s['journey']['life_day']
    x['let'] = dict(who=0, since=day, rent=hs.rent_of(x['kind']), paid=day, ev=day, owed=0, od=0)
    validate_state(s)
    return s, dict(message=f"{x['let']['rent']} xu/tháng")


def to_v1(s):
    """The save as 1.4.5 wrote it: version 1, one home, no props, no mv/let/keep, eight stats."""
    s = copy.deepcopy(s)
    h = H(s)
    assert not h['props']
    h['v'] = 1
    del h['props']
    for k in ('moves', 'rent_in'):
        del h['stats'][k]
    if h['own']:
        for k in ('mv', 'let', 'keep'):
            del h['own'][k]
    return s


def rich(wallet=60000, salary=400, score=760):
    s = opened(wallet=wallet, deposit=1000, income_days=14, salary=salary)
    B(s)['score'] = score
    return s


def ready(s):
    return s['journey']['wallet'] + (B(s)['balance'] if s['journey'].get('bank') else 0)


class OldSaves(unittest.TestCase):
    """A 1.4.5 save with one home loads as version 2 with nothing lost."""

    def old_save(self):
        s = opened(wallet=1500, deposit=1000, income_days=14, salary=60)
        s, _ = buy(s, 'can_ho_mini', down=1080, months=36)
        s['journey']['wallet'] = 3000
        p = rn.public(s)['parts'][0]
        s, _ = act(s, 'jr_reno_up', part=p['id'], lv=1, cost=p['up']['cost'], confirm=True)   # an upgrade
        s, _ = place_new(s, 'cay_canh', 'living')                            # a piece of decor
        tick(s, 5, salary=60)                                                # kỳ 1 paid on time
        j = s['journey']
        keep_wallet, keep_bal = j['wallet'], B(s)['balance']
        j['wallet'], B(s)['balance'] = 0, 0
        tick(s, 5 + hs.GRACE)                                                # kỳ 2 missed: grace, then the late fee
        j['wallet'], B(s)['balance'] = keep_wallet, keep_bal
        tick(s, 1)                                                           # kỳ 2 taken late
        rows = H(s)['own']['loan']['rows']
        self.assertTrue(rows[1]['late'] and rows[1]['fee'] and rows[1]['paid'] == rows[1]['amount'])
        s['marriage'] = dict(v=1, applied=[], spouse=dict(name='Bình', status='married', since=1, wed=1, date=None, couple=7, side='a'),
                             sticker=True, weddings=1)
        return to_v1(s)

    def test_version_1_is_valid_and_upgrades_losslessly(self):
        old = self.old_save()
        validate_state(old)                                                  # the old shape is still accepted
        h1 = copy.deepcopy(H(old))
        reno1, deco1, decor1 = (copy.deepcopy(old['journey'].get(k)) for k in ('reno', 'deco', 'decor'))
        new = migrate_state(old)
        validate_state(new)
        h2 = H(new)
        self.assertEqual((h2['v'], h2['props']), (2, []))
        self.assertEqual({k: v for k, v in h2['own'].items() if k not in ('mv', 'let', 'keep')}, h1['own'])   # loan, schedule, fees
        self.assertEqual((h2['own']['mv'], h2['own']['let'], h2['own']['keep']), (0, None, None))
        for k in ('seq', 'day', 'rent', 'shared', 'past', 'log'):
            self.assertEqual(h2[k], h1[k], k)
        self.assertEqual({k: v for k, v in h2['stats'].items() if k in h1['stats']}, h1['stats'])
        self.assertEqual((h2['stats']['moves'], h2['stats']['rent_in']), (0, 0))
        self.assertEqual([new['journey'].get(k) for k in ('reno', 'deco', 'decor')], [reno1, deco1, decor1])
        view = public_state(new)['journey']
        self.assertEqual(view['home']['own']['loan']['paid_rows'], 2)
        self.assertEqual(view['reno']['parts'][0]['lv'], 1)                 # the upgrade is still there
        self.assertEqual(len(view['deco']['items']), 1)                     # the decor still stands
        from game import marriage as mr
        ids = [e['id'] for e in hs.partner_effects(new, 7, 'a', 'sid-b', mr._effect)]
        self.assertEqual(ids, [])                                        # upgrading never creates new sharing without consent
        tick(new, 5, salary=60)                                              # the schedule goes on
        self.assertEqual(H(new)['own']['loan']['rows'][2]['paid'], H(new)['own']['loan']['rows'][2]['amount'])

    def test_upgrade_is_idempotent_and_never_touches_absent_homes(self):
        new = migrate_state(self.old_save())
        again = copy.deepcopy(new)
        jr.upgrade(again['journey'])
        self.assertEqual(H(again), H(new))
        s = story()
        jr.upgrade(s['journey'])
        self.assertNotIn('home', s['journey'])

    def test_a_version_1_room_or_shared_home(self):
        s = story(wallet=200)
        s, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)
        old = to_v1(s)
        validate_state(old)
        new = migrate_state(old)
        self.assertEqual((H(new)['v'], H(new)['rent']['kind'], H(new)['own']), (2, 'tro_moi', None))
        validate_state(new)


class SecondHome(unittest.TestCase):
    def test_buy_a_second_and_third_home_kept_empty(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'tap_the')
        first = H(s)['own']['id']
        s, r = buy2(s, 'can_ho_studio')                                      # a page with several homes: stays empty by default
        self.assertIn('để trống', r['message'])
        self.assertEqual((H(s)['own']['id'], [x['kind'] for x in H(s)['props']]), (first, ['can_ho_studio']))
        self.assertEqual(jr.living_cost(s['journey'])['rent'], hs.HOMES['tap_the']['upkeep'])   # an empty home costs nothing
        s, r = buy2(s, 'can_ho_mini', move_in=True)                          # …or move into the new one
        self.assertEqual(H(s)['own']['kind'], 'can_ho_mini')
        self.assertEqual(sorted(x['kind'] for x in H(s)['props']), ['can_ho_studio', 'tap_the'])
        self.assertIn(hs.MOVE_LINES['move'], r['message'])
        self.assertIn('Căn tập thể cũ giờ để trống', r['message'])
        self.assertEqual(s['journey']['stats']['homes_bought'], 3)
        view = hs.public(s)
        self.assertEqual((view['count'], view['can_buy']['ok'], len(view['props'])), (3, True, 2))
        self.assertEqual(sorted(view['owned']), ['can_ho_mini', 'can_ho_studio', 'tap_the'])
        with self.assertRaises(GameError) as e:
            buy2(s, 'tap_the')                                               # the same listing twice
        self.assertEqual(e.exception.code, 'owned')
        s['journey']['wallet'] = 20000
        s, _ = buy2(s, 'nha_pho')
        view = hs.public(s)
        self.assertEqual((view['count'], view['can_buy']['ok']), (hs.OWNED_MAX, False))
        self.assertTrue(view['can_buy']['why'])
        with self.assertRaises(GameError) as e:
            buy2(s, 'can_ho_1pn')
        self.assertEqual(e.exception.code, 'too_many')
        validate_state(s)

    def test_buying_never_takes_the_wallet_below_zero(self):
        s = story(wallet=2200)
        s, _ = buy(s, 'tap_the')
        before = copy.deepcopy(s)
        with self.assertRaises(GameError) as e:
            buy2(s, 'can_ho_studio')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(s, before)
        self.assertGreaterEqual(s['journey']['wallet'], 0)

    def test_the_joint_fund_only_pays_for_a_home_you_move_into(self):
        s = story(wallet=6000)
        s, _ = buy(s, 'tap_the')
        with self.assertRaises(GameError) as e:
            buy2(s, 'can_ho_studio', joint=100, move_in=False)
        self.assertEqual(e.exception.code, 'no_joint')
        with self.assertRaises(GameError):
            buy2(s, 'can_ho_studio', move_in='yes')


class DebtLimit(unittest.TestCase):
    """The bank's 40 % limit counts the installments of every home loan."""

    def test_second_mortgage_counts_the_first(self):
        s = rich(salary=100, score=760)
        o = hs.offer(s)
        self.assertEqual(o['others'], 0)
        room = o['room']
        price = hs.HOMES['nha_pho']['price']
        s['journey']['wallet'] = 20000
        s, r = buy2(s, 'nha_pho', down=hs.down_min(price), months=36)
        self.assertTrue(r['approved'], r['message'])
        first = H(s)['own']['loan']['rows'][0]['amount']
        o = hs.offer(s)
        self.assertEqual((o['others'], o['room']), (first, max(0, room - first)))
        # the same loan on another home would fit alone, not on top of the first
        price2 = hs.HOMES['can_ho_1pn']['price']
        q = hs.quote(price2 - hs.down_min(price2), o['rate'], 36, 0)
        self.assertLessEqual(q['installment'], room)
        self.assertGreater(q['installment'], o['room'])
        s, r = buy2(s, 'can_ho_1pn', down=hs.down_min(price2), months=36)
        self.assertFalse(r['approved'])
        self.assertEqual(r['why'], 'dti')
        self.assertIn('vượt 40% thu nhập', r['message'])
        self.assertIn('đã trừ', r['message'])
        self.assertEqual(len(hs.homes(H(s))), 1)
        s, r = buy2(s, 'can_ho_1pn', down=price2 - 600, months=36)           # a bigger down payment fits
        self.assertTrue(r['approved'], r['message'])
        self.assertEqual(hs.offer(s)['others'], first + H(s)['props'][0]['loan']['rows'][0]['amount'])
        validate_state(s)


class Letting(unittest.TestCase):
    def owner2(self, loan=False):
        """Lives in the tập thể, owns the studio (empty)."""
        s = rich() if loan else story(wallet=20000)
        s['journey']['wallet'] = 20000
        s, _ = buy(s, 'tap_the')
        price = hs.HOMES['can_ho_studio']['price']
        s, r = buy2(s, 'can_ho_studio', down=hs.down_min(price) if loan else None, months=12)
        self.assertTrue(r['approved'], r['message'])
        return s

    def test_rent_at_the_month_boundary(self):
        s = self.owner2()
        x = H(s)['props'][0]
        self.assertEqual(hs.rent_of('can_ho_studio'), 20)                   # 2.400 × 10 % / 12
        tick(s, 2)
        s, r = legacy_tenant(s, x['id'])
        x = H(s)['props'][0]
        L = x['let']
        self.assertEqual((L['rent'], L['since'], L['paid']), (20, x['day'] + 2, x['day'] + 2))
        self.assertIn('20 xu/tháng', r['message'])
        w = s['journey']['wallet']
        tick(s, 2)
        self.assertEqual(s['journey']['wallet'], w)                          # nothing before the boundary
        notes = tick(s, 1)                                                   # the boundary: 3 days of 5
        self.assertEqual(s['journey']['wallet'], w + 12)
        self.assertTrue(any('tiền thuê' in n for n in notes))
        tick(s, 5)
        self.assertEqual(H(s)['stats']['rent_in'], 12 + 20 - (H(s)['props'][0]['let']['owed']))
        self.assertEqual(jr.living_cost(s['journey'])['rent'], hs.HOMES['tap_the']['upkeep'])   # tenants pay their own bills
        view = hs.public(s)['props'][0]
        self.assertEqual((view['let']['rent'], view['live'], view['move']['ok']), (20, False, False))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_home_move', id=x['id'], confirm=True)
        self.assertEqual(e.exception.code, 'let')
        with self.assertRaises(GameError) as e:
            act(s, 'jr_home_let', id=H(s)['own']['id'], on=True, confirm=True)   # not the home you live in
        self.assertEqual(e.exception.code, 'here')
        tick(s, 2)
        w = s['journey']['wallet'] + H(s)['props'][0]['let']['owed']
        s, r = act(s, 'jr_home_let', id=x['id'], on=False, confirm=True)     # 2 days of rent, and anything owed
        self.assertEqual(s['journey']['wallet'], w + 8)
        self.assertIsNone(H(s)['props'][0]['let'])
        validate_state(s)

    def test_rent_lands_before_the_installment_of_the_same_home(self):
        s = self.owner2(loan=True)
        x = H(s)['props'][0]
        s, _ = legacy_tenant(s, x['id'])
        B(s)['balance'] = 0
        due = x['loan']['rows'][0]
        s['journey']['wallet'] = due['amount'] - 20                         # short by exactly one month's rent
        tick(s, hs.MONTH_DAYS)                                               # no tenant moment in the first TENANT_GAP days
        row = H(s)['props'][0]['loan']['rows'][0]
        self.assertEqual((row['paid'], row['late'], H(s)['props'][0]['let']['owed']), (row['amount'], False, 0))
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertGreaterEqual(s['journey']['wallet'], 0)

    def test_tenant_moments_are_light_and_capped(self):
        s = self.owner2()
        x = H(s)['props'][0]
        s, _ = legacy_tenant(s, x['id'])
        start = s['journey']['wallet']
        days = 60 * hs.MONTH_DAYS
        notes = tick(s, days)
        moments = [n for n in notes if 'khất' in n and 'gửi đủ' not in n or n.startswith('🔧')]
        self.assertTrue(moments)                                             # some happen over five years…
        self.assertLessEqual(len(moments), days // hs.TENANT_GAP + 1)         # …never often
        got = s['journey']['wallet'] - start
        self.assertEqual(got, H(s)['stats']['rent_in'])
        self.assertLessEqual(got, 60 * 20)
        self.assertGreaterEqual(got, 60 * 20 * 8 // 10)                      # repairs only ever take a little
        validate_state(s)


class Moving(unittest.TestCase):
    def test_move_between_homes_keeps_repairs_and_decor(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'tap_the')
        a = H(s)['own']['id']
        p = rn.public(s)['parts'][0]
        s, _ = act(s, 'jr_reno_up', part=p['id'], lv=1, cost=p['up']['cost'], confirm=True)
        s, _ = place_new(s, 'cay_canh', 'living')
        s, _ = buy2(s, 'nha_pho')
        b = H(s)['props'][0]['id']
        tick(s, 3)
        w = s['journey']['wallet']
        s, r = act(s, 'jr_home_move', id=b, confirm=True)
        self.assertIn(hs.MOVE_LINES['move'], r['message'])
        self.assertEqual(s['journey']['wallet'], w - hs.MOVE_FEE)
        self.assertEqual((H(s)['own']['id'], H(s)['own']['mv'], H(s)['props'][0]['id']), (b, 1, a))
        self.assertEqual(H(s)['props'][0]['keep']['parts'][p['id']]['lv'], 1)   # the upgrade waits in the old home
        self.assertEqual(jr.living_cost(s['journey'])['rent'], hs.HOMES['nha_pho']['upkeep'])
        self.assertEqual(public_state(s)['journey']['deco']['bag'][0]['k'], 'cay_canh')   # decor into the bag, not lost
        self.assertEqual(rn.public(s)['home']['kind'], 'nha_pho')
        self.assertEqual(max(x['lv'] for x in rn.public(s)['parts']), 0)
        s['journey']['life']['spirit'] = 50
        tick(s, 1)
        self.assertEqual(s['journey']['life']['spirit'], 50 + hs.HOMES['nha_pho']['comfort'])   # the comfort of the home you live in
        tick(s, 20)
        s, _ = act(s, 'jr_home_move', id=a, confirm=True)                    # back home: the upgrade is back
        self.assertEqual(rn.public(s)['parts'][0]['lv'], 1)
        self.assertLess(rn.public(s)['parts'][1]['c'], 100)                   # worn by the days away
        self.assertEqual(H(s)['own']['keep'], None)
        self.assertEqual(H(s)['stats']['moves'], 2)
        validate_state(s)

    def test_moving_needs_the_truck_money_and_an_empty_home(self):
        s = story(wallet=1836 + hs.tax('tap_the') + 2400 + hs.buy_fee(2400) + hs.tax('can_ho_studio'))   # 💹 07/10: + thuế trước bạ
        s, _ = buy(s, 'tap_the')
        s, _ = buy2(s, 'can_ho_studio')
        x = H(s)['props'][0]
        self.assertEqual(s['journey']['wallet'], 0)
        view = hs.public(s)['props'][0]
        self.assertEqual((view['move']['ok'], view['move']['why']), (False, f'Thiếu {hs.MOVE_FEE} xu thuê xe'))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_home_move', id=x['id'], confirm=True)
        self.assertEqual(e.exception.code, 'not_enough')
        with self.assertRaises(GameError) as e:
            act(s, 'jr_home_move', id=H(s)['own']['id'], confirm=True)
        self.assertEqual(e.exception.code, 'here')
        with self.assertRaises(GameError):
            act(s, 'jr_home_move', id=x['id'])                               # no confirm

    def test_from_a_rented_room_into_a_home_you_own(self):
        s = story(wallet=3000)
        s, _ = buy2(s, 'tap_the', move_in=False)                             # bought to let, living in the attic
        self.assertEqual((H(s)['own'], jr.living_cost(s['journey'])['where']), (None, 'attic'))
        s, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)
        w = s['journey']['wallet']
        s, r = act(s, 'jr_home_move', id=H(s)['props'][0]['id'], confirm=True)
        self.assertEqual(s['journey']['wallet'], w + 60 - hs.MOVE_FEE)      # the deposit back, the truck paid
        self.assertEqual((H(s)['rent'], H(s)['own']['kind']), (None, 'tap_the'))
        validate_state(s)

    def test_moving_never_creates_automatic_spouse_invitations(self):
        from game import marriage as mr
        s = story(wallet=20000)
        s['name'] = 'An'
        s, _ = buy(s, 'tap_the')
        s, _ = buy2(s, 'nha_pho')
        a, b = H(s)['own']['id'], H(s)['props'][0]['id']
        ids = lambda: [e['id'] for e in hs.partner_effects(s, 7, 'a', 'sid-b', mr._effect) if e['id'].startswith('home:')]
        self.assertEqual(ids(), [])
        s, _ = act(s, 'jr_home_move', id=b, confirm=True)
        self.assertEqual(ids(), [])
        s, _ = act(s, 'jr_home_move', id=a, confirm=True)
        self.assertEqual(ids(), [])
        s, _ = act(s, 'jr_home_move', id=b, confirm=True)
        self.assertEqual(ids(), [])                                      # returning still needs a new explicit invitation


class SellingAndPaying(unittest.TestCase):
    def test_sell_a_let_home_and_the_home_you_live_in(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'tap_the')
        s, _ = buy2(s, 'nha_pho')
        x = H(s)['props'][0]
        s, _ = legacy_tenant(s, x['id'])
        tick(s, 3)
        w = s['journey']['wallet']
        value = hs.value_of(x, s['journey']['life_day'])
        s, r = act(s, 'jr_home_sell', id=x['id'], confirm=True, value=value)
        rent = 3 * hs.rent_of('nha_pho') // hs.MONTH_DAYS
        self.assertEqual(s['journey']['wallet'], w + value - hs.sell_fee(value) + rent)
        self.assertIn('dọn đi', r['message'])
        self.assertEqual((H(s)['props'], H(s)['own']['kind']), ([], 'tap_the'))
        s, _ = buy2(s, 'nha_pho')
        own = H(s)['own']
        s, r = act(s, 'jr_home_sell', confirm=True, value=hs.value_of(own, s['journey']['life_day']))   # no id: the home you live in
        self.assertIn(hs.MOVE_LINES['back'], r['message'])
        self.assertEqual((H(s)['own'], len(H(s)['props'])), (None, 1))
        self.assertEqual(jr.living_cost(s['journey'])['where'], 'attic')
        self.assertEqual([p['kind'] for p in H(s)['past']], ['nha_pho', 'tap_the'])
        validate_state(s)

    def test_pay_and_payoff_per_home(self):
        s = rich()
        s, _ = buy(s, 'tap_the')
        price = hs.HOMES['can_ho_studio']['price']
        s, r = buy2(s, 'can_ho_studio', down=hs.down_min(price), months=12)
        self.assertTrue(r['approved'], r['message'])
        x = H(s)['props'][0]
        with self.assertRaises(GameError):
            act(s, 'jr_home_pay')                                            # no id: the home you live in has no loan
        s, r = act(s, 'jr_home_pay', id=x['id'])
        self.assertEqual(H(s)['props'][0]['loan']['rows'][0]['paid'], x['loan']['rows'][0]['amount'])
        self.assertIn('vay mua studio Nắng Mai', r['message'])
        s, r = act(s, 'jr_home_payoff', id=x['id'], confirm=True)
        self.assertIsNone(H(s)['props'][0]['loan'])
        self.assertIn('m_home_free', s['journey']['titles'])
        with self.assertRaises(GameError):
            act(s, 'jr_home_pay', id='nope')
        validate_state(s)


class SaveChecks(unittest.TestCase):
    def test_tampered_homes_are_refused(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'tap_the')
        s, _ = buy2(s, 'nha_pho')
        s, _ = legacy_tenant(s, H(s)['props'][0]['id'])
        validate_state(s)
        let = copy.deepcopy(H(s)['props'][0]['let'])
        breaks = [
            lambda h: h['own'].__setitem__('let', let),                                # the home you live in is not let
            lambda h: h['own'].__setitem__('keep', dict(day=1, parts={})),
            lambda h: h['props'][0].__setitem__('kind', 'tap_the'),                    # the same home twice
            lambda h: h['props'][0].__setitem__('id', h['own']['id']),
            lambda h: h['props'].extend(copy.deepcopy([h['props'][0]] * 3)),            # more than OWNED_MAX
            lambda h: h['props'][0]['let'].__setitem__('paid', 10**5),
            lambda h: h['props'][0]['let'].__setitem__('extra', 1),
            lambda h: h['props'][0].pop('mv'),
            lambda h: h.__setitem__('v', 3),
            lambda h: h.pop('props'),                                                   # version 2 without its list
            lambda h: h['stats'].pop('moves'),
        ]
        for i, f in enumerate(breaks):
            bad = copy.deepcopy(s)
            f(H(bad))
            with self.subTest(i=i), self.assertRaises(GameError):
                validate_state(bad)

    def test_round_trip(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'tap_the')
        s, _ = buy2(s, 'nha_pho')
        s, _ = legacy_tenant(s, H(s)['props'][0]['id'])
        tick(s, 12)
        again = migrate_state(copy.deepcopy(s))
        self.assertEqual(H(again), H(s))
        validate_state(again)
        import json
        validate_state(json.loads(json.dumps(s)))

    def test_new_commands_story_only_and_old_pages(self):
        from game.engine import apply_action, new_state
        with self.assertRaises(GameError):
            apply_action(new_state(), None, 'jr_home_move', dict(id='h1', confirm=True))
        s = story(wallet=100)
        with self.assertRaises(GameError):
            act(s, 'jr_home_let', id='h1', on=True, confirm=True)
        view = public_state(s)['journey']['home']                            # a page from before still finds its fields
        for k in ('place', 'own', 'rent', 'shared', 'market', 'offer', 'rules', 'have'):
            self.assertIn(k, view)
        self.assertEqual((view['props'], view['count']), ([], 0))


from tests.test_couple import CoupleBase   # noqa: E402  (the database side of a couple)


class CoupleMoves(CoupleBase):
    """The spouse accepts each new home explicitly; ownership stays personal."""

    def cmd(self, tok, action, rid, **p):
        return self.store.command(tok, rid, self.store.read(tok)[1], None, action, p)

    def load(self):
        from game import marriage as mr
        self.clock.t += 3600
        for _ in range(2):
            mr.on_load(self.store, self.a, self.state(self.a))
            mr.on_load(self.store, self.b, self.state(self.b))

    def share(self):
        self.act(self.a, 'family_home_request', rid='move-home-invite-' + str(int(self.clock.t)))
        request = self.view(self.b)['family']['requests'][0]
        self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='move-home-accept-' + str(request['id']))

    def shared(self):
        sh = self.state(self.b)['journey']['home']['shared']
        return sh and sh['kind']

    def test_spouse_accepts_each_lived_in_home(self):
        self.fund(self.a, 20000)
        self.cmd(self.a, 'jr_home_buy', 'multi-buy-0001', kind='tap_the', down=1800, confirm=True)
        self.load()
        self.share()
        self.assertEqual(self.shared(), 'tap_the')
        out = self.cmd(self.a, 'jr_home_buy', 'multi-buy-0002', kind='nha_pho', down=7800, move_in=False, confirm=True)
        self.assertTrue(out['result']['approved'])
        self.load()
        self.assertEqual(self.shared(), 'tap_the')                         # an empty home does not move the spouse
        hid = self.state(self.a)['journey']['home']['props'][0]['id']
        self.cmd(self.a, 'jr_home_move', 'multi-move-0001', id=hid, confirm=True)
        self.load()
        self.share()
        self.assertEqual(self.shared(), 'nha_pho')
        old = self.state(self.a)['journey']['home']['props'][0]['id']
        self.cmd(self.a, 'jr_home_move', 'multi-move-0002', id=old, confirm=True)
        self.load()
        self.share()
        self.assertEqual(self.shared(), 'tap_the')                         # explicitly accepted again
        sa = self.state(self.a)
        x = sa['journey']['home']['props'][0]
        self.cmd(self.a, 'jr_home_sell', 'multi-sell-0001', id=x['id'], confirm=True, value=hs.value_of(x, sa['journey']['life_day']))
        self.load()
        self.assertEqual(self.shared(), 'tap_the')                         # selling another home changes nothing for the spouse
        validate_state(self.state(self.b))

    def test_living_in_the_spouses_home_a_new_one_stays_empty_and_the_way_back(self):
        """Feedback #137: "đang ở biệt thự, mua căn hộ xong ở luôn căn hộ, không về biệt thự được"."""
        self.fund(self.a, 20000)
        self.cmd(self.a, 'jr_home_buy', 'sh-buy-0001', kind='nha_pho', down=7800, confirm=True)
        self.load()
        self.share()
        self.assertEqual(self.shared(), 'nha_pho')
        self.fund(self.b, 20000)
        out = self.cmd(self.b, 'jr_home_buy', 'sh-buy-0002', kind='tap_the', down=1800, confirm=True)   # no move_in: stays empty
        self.assertIn('để trống', out['result']['message'])
        h = self.state(self.b)['journey']['home']
        self.assertEqual((h['own'], [x['kind'] for x in h['props']], hs.where(h)[0]), (None, ['tap_the'], 'shared'))
        hid = h['props'][0]['id']
        self.cmd(self.b, 'jr_home_move', 'sh-move-0001', id=hid, confirm=True)   # moves into it on purpose
        self.assertEqual(hs.where(self.state(self.b)['journey']['home']), ('own', 'tap_the'))
        view = public_state(self.state(self.b))['journey']['home']
        self.assertEqual((view['shared']['home'], view['own']['kind']), (hs.HOMES['nha_pho']['name'], 'tap_the'))
        w = self.state(self.b)['journey']['wallet']
        out = self.cmd(self.b, 'jr_home_move', 'sh-move-0002', to='shared', confirm=True)   # and back to the spouse's home
        self.assertIn('ở chung', out['result']['message'])
        sb = self.state(self.b)
        h = sb['journey']['home']
        self.assertEqual((hs.where(h), h['own'], [x['kind'] for x in h['props']]), (('shared', 'nha_pho'), None, ['tap_the']))
        self.assertEqual(sb['journey']['wallet'], w - hs.MOVE_FEE)
        self.assertEqual(jr.living_cost(sb['journey'])['where'], 'shared')
        with self.assertRaises(GameError) as e:
            act(sb, 'jr_home_move', to='shared', confirm=True)                    # already there
        self.assertEqual(e.exception.code, 'here')
        validate_state(sb)


class MoveBackSolo(unittest.TestCase):
    def test_without_a_spouse_there_is_no_shared_home_to_go_back_to(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'tap_the')
        with self.assertRaises(GameError) as e:
            act(s, 'jr_home_move', to='shared', confirm=True)
        self.assertEqual(e.exception.code, 'no_shared')
        s, r = buy2(s, 'biet_thu' if 'biet_thu' in hs.HOMES else 'nha_pho')   # owning a home: the new one stays empty
        self.assertEqual(H(s)['own']['kind'], 'tap_the')
        s, r = act(s, 'jr_home_move', id=H(s)['props'][0]['id'], confirm=True)  # "Dọn về ở" either way, both kept
        s, r = act(s, 'jr_home_move', id=H(s)['props'][0]['id'], confirm=True)
        self.assertEqual((H(s)['own']['kind'], len(H(s)['props'])), ('tap_the', 1))
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
