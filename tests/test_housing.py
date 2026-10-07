"""🏠 Nhà của bạn (game/housing.py) and the bank's yearly savings (game/bank.py): in-game time, term
deposits, renting, buying with and without a mortgage, gentle missed payments, selling, the couple's
home, validation and migration."""
import copy
import unittest

from game import bank as bk
from game import housing as hs
from game import journey as jr
from game import price_index as pi
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from tests.test_bank import B, act, opened, story


def H(s):
    return s['journey']['home']


def tick(s, n=1, salary=0):
    """Close `n` life days: salary lands, life_day moves, the bank and the home catch up."""
    notes = []
    for _ in range(n):
        j = s['journey']
        if salary:
            jr._wallet(j, salary, 'salary', 'Lương ngày')
        j['life_day'] += 1
        notes += bk.on_life_day(s)
        notes += hs.on_life_day(s)
    validate_state(s)
    return notes


def buy(s, kind, down=None, months=None, joint=0):
    price = hs.HOMES[kind]['price']
    down = price if down is None else down
    p = dict(kind=kind, down=down, confirm=True)
    if joint:
        p['joint'] = joint
    if down < price:
        months = months or 36
        q = hs.quote(price - down, hs.offer(s)['rate'], months, s['journey']['life_day'])
        p.update(months=months, total_interest=q['interest'])
    return act(s, 'jr_home_buy', **p)


def spirit(s):
    return s['journey']['life']['spirit']


class InGameYear(unittest.TestCase):
    def test_calendar_and_rates(self):
        self.assertEqual((bk.MONTH_DAYS, bk.YEAR_DAYS), (5, 60))
        self.assertEqual(sorted(bk.TERM_RATE), [7, 15, 30, 60, 120, 180])   # 7 ngày, 3/6/12 tháng, 2/3 năm
        rates = [bk.TERM_RATE[t] for t in sorted(bk.TERM_RATE)]
        self.assertEqual(rates, sorted(rates))                               # longer terms pay more
        self.assertLess(bk.DEMAND_BP * bk.YEAR_DAYS, rates[0])
        self.assertLess(max(rates), min(r for _, r in hs.RATES))             # saving never beats borrowing
        from game import invest as iv
        self.assertGreater(iv.RATE_MILLI * 10 * bk.YEAR_DAYS, bk.TERM_RATE[7])  # invest.py savings (0,3 %/ngày) pays more than the bank's 7-day term
        self.assertEqual(bk.year_text(750), '7,5%/năm')

    def test_twelve_month_term_accrues_by_in_game_time(self):
        s = opened(wallet=2000, deposit=2000)
        s, r = act(s, 'jr_bk_save', amount=1000, term=60)
        self.assertIn('8%/năm', r['message'])
        self.assertIn('80 xu', r['message'])                                 # 1000 × 8 % over one in-game year
        tick(s, 30)
        t = bk.public(s)['savings']['terms'][0]
        self.assertEqual((t['accrued'], t['interest'], t['value'], t['days_left']), (40, 80, 1080, 30))
        tick(s, 29)
        self.assertEqual(B(s)['balance'], 1000)
        notes = tick(s, 1)
        self.assertEqual((B(s)['balance'], B(s)['terms']), (2080, []))
        self.assertTrue(any('đáo hạn' in n for n in notes))

    def test_renewal_rolls_interest_into_a_new_term(self):
        s = opened(wallet=1000, deposit=1000)
        s, _ = act(s, 'jr_bk_save', amount=1000, term=15, renew=True)
        tick(s, 15)
        t = B(s)['terms'][0]
        self.assertEqual((t['amount'], t['start'], t['due'], t['renew']), (1000 + 1000 * 700 * 15 // 600000, s['journey']['life_day'],
                                                                          s['journey']['life_day'] + 15, True))
        self.assertEqual(B(s)['balance'], 0)
        with self.assertRaises(GameError):
            act(s, 'jr_bk_save', amount=100, term=15, renew='yes')

    def test_early_withdrawal_keeps_only_the_demand_rate(self):
        s = opened(wallet=3000, deposit=3000)
        s, _ = act(s, 'jr_bk_save', amount=2000, term=180)
        tick(s, 40)
        t = bk.public(s)['savings']['terms'][0]
        self.assertEqual(t['early'], 2000 * bk.DEMAND_BP * 40 // 10000)      # 40 xu instead of 2000 × 9 % × 3 năm
        self.assertEqual(t['interest'], 528)
        s, r = act(s, 'jr_bk_unsave', id=t['id'], confirm=True)
        self.assertEqual(B(s)['balance'], 1000 + 2000 + 40)
        self.assertIn('bớt 488 xu', r['message'])

    def test_old_term_deposits_keep_their_rate(self):
        s = opened(wallet=3000, deposit=3000)
        s, _ = act(s, 'jr_bk_save', amount=2000, term=30)
        old = copy.deepcopy(s)
        t = B(old)['terms'][0]
        t.pop('renew')
        t['bp'] = 30 * 1 if t.pop('rate') else 0                             # a 0.9.4 sổ: 0,3 %/ngày
        old = migrate_state(old)
        t = B(old)['terms'][0]
        self.assertEqual((t['rate'], t['renew']), (1800, False))
        validate_state(old)
        tick(old, 30)
        self.assertEqual(B(old)['balance'], 1000 + 2000 + 2000 * 30 * 30 // 10000)   # the same 180 xu as before
        bad = copy.deepcopy(s)
        B(bad)['terms'][0]['rate'] = 999
        with self.assertRaises(GameError):
            validate_state(bad)


class Renting(unittest.TestCase):
    def test_rent_a_room_then_leave(self):
        s = story(wallet=100)
        attic = jr.living_cost(s['journey'])
        with self.assertRaises(GameError):
            act(s, 'jr_home_rent', kind='tro_moi')                          # no confirm
        s, r = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)
        self.assertEqual(s['journey']['wallet'], 40)
        cost = jr.living_cost(s['journey'])
        self.assertEqual((cost['rent'], cost['meals'], cost['where']), (hs.HOMES['tro_moi']['rent'], attic['meals'], 'rent'))
        self.assertIn('Tiền phòng trọ', cost['label'])
        sp = spirit(s)
        tick(s, 2)
        self.assertEqual(spirit(s), min(100, sp + 2))
        self.assertEqual(H(s)['stats']['rent_days'], 2)
        s, _ = act(s, 'jr_home_leave', confirm=True)
        self.assertEqual((s['journey']['wallet'], H(s)['rent']), (100, None))
        self.assertEqual(jr.living_cost(s['journey']), attic)
        with self.assertRaises(GameError) as e:
            act(story(wallet=10), 'jr_home_rent', kind='tro_moi', confirm=True)
        self.assertEqual(e.exception.code, 'not_enough')


class BuyingWithCash(unittest.TestCase):
    def test_buy_outright_stops_the_rent(self):
        s = story(wallet=2200)
        attic = jr.living_cost(s['journey'])
        s, r = buy(s, 'tap_the')
        self.assertTrue(r['approved'])
        self.assertEqual(s['journey']['wallet'], 2200 - 1800 - hs.buy_fee(1800) - hs.tax('tap_the'))   # 💹 07/10: + thuế trước bạ
        cost = jr.living_cost(s['journey'])
        self.assertEqual((cost['rent'], cost['where']), (hs.HOMES['tap_the']['upkeep'], 'own'))
        self.assertLess(cost['total'], attic['total'])
        self.assertIn('m_home', s['journey']['titles'])
        self.assertEqual(s['journey']['stats']['homes_bought'], 1)
        self.assertIsNone(H(s)['own']['loan'])
        view = public_state(s)['journey']['home']
        self.assertEqual((view['place']['where_id'], view['own']['name']), ('own', 'Căn tập thể cũ'))
        with self.assertRaises(GameError):
            buy(s, 'tap_the')                                               # one home at a time

    def test_buying_while_renting_returns_the_deposit(self):
        s = story(wallet=2200)
        s, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)
        s, r = buy(s, 'tap_the')
        self.assertIsNone(H(s)['rent'])
        self.assertEqual(s['journey']['wallet'], 2200 - 1836 - hs.tax('tap_the'))
        self.assertIn('tiền cọc', r['message'])

    def test_what_is_missing_is_shown_and_enforced(self):
        s = story(wallet=300)
        row = next(m for m in hs.public(s)['market'] if m['id'] == 'tap_the')
        cat = next(m for m in hs.catalogue()['homes'] if m['id'] == 'tap_the')
        self.assertEqual((cat['down_min'], cat['fee'], cat['need'], row['missing']), (540, 36 + 180, 756, 456))   # fee: 2 % + 💹 thuế 180
        with self.assertRaises(GameError) as e:
            buy(s, 'tap_the')
        self.assertEqual(e.exception.code, 'not_enough')
        with self.assertRaises(GameError):
            buy(story(wallet=5000), 'tap_the', down=500)                     # under 30 %

    def test_account_money_counts_and_goes_first(self):
        s = opened(wallet=2100, deposit=1000)
        s, _ = buy(s, 'tap_the')
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), (0, 1100 - 836 - hs.tax('tap_the')))

    def test_comfort_raises_spirit_every_day(self):
        s, _ = buy(story(wallet=17000), 'nha_san')
        s['journey']['life']['spirit'] = 50
        tick(s, 3)
        self.assertEqual(spirit(s), 50 + 3 * hs.HOMES['nha_san']['comfort'])
        self.assertEqual(H(s)['stats']['home_days'], 3)


class Mortgage(unittest.TestCase):
    def mortgaged(self, kind='can_ho_mini', down=None, months=36, wallet=1500, deposit=1000):
        s = opened(wallet=wallet, deposit=deposit, income_days=14, salary=60)
        price = hs.HOMES[kind]['price']
        s, r = buy(s, kind, down=down or hs.down_min(price), months=months)
        self.assertTrue(r.get('approved'), r['message'])
        return s

    def test_buy_with_a_mortgage(self):
        s = opened(wallet=1500, deposit=1000, income_days=14, salary=60)
        o = hs.offer(s)
        self.assertTrue(o['ok'], o['text'])
        before = (B(s)['balance'], s['journey']['wallet'])
        s, r = buy(s, 'can_ho_mini', down=1080, months=36)
        ln = H(s)['own']['loan']
        self.assertEqual((ln['principal'], ln['months'], len(ln['rows'])), (2520, 36, 36))
        self.assertEqual([x['due'] for x in ln['rows'][:2]], [ln['start'] + 5, ln['start'] + 10])
        self.assertEqual(sum(x['principal'] for x in ln['rows']), 2520)
        self.assertEqual(sum(before) - B(s)['balance'] - s['journey']['wallet'], 1080 + hs.buy_fee(3600) + hs.tax('can_ho_mini'))
        self.assertEqual(B(s)['inq'][-1], s['journey']['life_day'])          # the bank looked at the file
        self.assertIn('36 kỳ', r['message'])
        self.assertEqual(jr.living_cost(s['journey'])['rent'], hs.HOMES['can_ho_mini']['upkeep'])

    def test_installments_are_taken_every_in_game_month(self):
        s = self.mortgaged()
        row = H(s)['own']['loan']['rows'][0]
        score = B(s)['score']
        tick(s, 4, salary=60)
        self.assertEqual(row['paid'], 0)
        tick(s, 1, salary=60)
        row = H(s)['own']['loan']['rows'][0]
        self.assertEqual(row['paid'], row['amount'])
        self.assertGreater(B(s)['score'], score - 1)
        self.assertEqual(H(s)['stats']['ontime'], 1)

    def test_paying_it_all_off_gives_the_title(self):
        s = self.mortgaged('tap_the', months=12, wallet=3000, deposit=1000)
        tick(s, 60, salary=60)
        self.assertIsNone(H(s)['own']['loan'])
        self.assertEqual(s['journey']['stats']['home_paid'], 1)
        s, _ = act(s, 'jr_bk_read')                                          # any command: titles are evaluated
        self.assertIn('m_home_free', s['journey']['titles'])
        self.assertIn('home_done', [x['why'] for x in B(s)['score_log']])

    def test_missed_payments_are_gentle(self):
        s = self.mortgaged()
        s['journey']['wallet'] = 0
        B(s)['balance'] = 0
        s['journey']['life']['spirit'] = 50
        score, misses = B(s)['score'], B(s)['misses']
        notes = tick(s, 4)
        self.assertTrue(any('Ngày mai' in n for n in notes))                 # a reminder the day before
        notes = tick(s, 1)                                                   # due day: a message, no fee
        row = H(s)['own']['loan']['rows'][0]
        self.assertEqual((row['late'], row['fee']), (False, 0))
        self.assertTrue(any('ân hạn' in n for n in notes))
        self.assertEqual(B(s)['score'], score)
        tick(s, hs.GRACE - 1)
        self.assertFalse(H(s)['own']['loan']['rows'][0]['late'])
        tick(s, 1)                                                           # grace over: small fee, score drops
        row = H(s)['own']['loan']['rows'][0]
        self.assertTrue(row['late'])
        self.assertEqual(row['fee'], max(hs.LATE_MIN, -(-(row['amount'] - row['fee']) * hs.LATE_PCT // 100)))
        self.assertLess(B(s)['score'], score)
        self.assertEqual(B(s)['misses'], misses + 1)
        sp = spirit(s)
        tick(s, 1)
        self.assertLessEqual(spirit(s), sp + 4)                             # no comfort bonus while late (life recovery aside)
        self.assertIsNotNone(H(s)['own'])                                    # the home is never taken
        # paying catches it up
        B(s)['balance'] = 500
        s, r = act(s, 'jr_home_pay')
        self.assertTrue(all(x['paid'] >= x['amount'] for x in H(s)['own']['loan']['rows'] if x['due'] <= s['journey']['life_day']))

    def test_declines_move_no_money(self):
        s = opened(wallet=1600, deposit=1000)                                # no income yet
        before = (B(s)['balance'], s['journey']['wallet'])
        s, r = buy(s, 'can_ho_mini', down=1080, months=36)
        self.assertFalse(r['approved'])
        self.assertIsNone((H(s) if 'home' in s['journey'] else {}).get('own'))
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), before)
        self.assertEqual(len(B(s)['inq']), 1)                                # the inquiry stays on record
        # too big an installment for the income
        s = opened(wallet=1500, deposit=1000, income_days=14, salary=20)
        s, r = buy(s, 'can_ho_mini', down=1080, months=12)
        self.assertFalse(r['approved'])
        self.assertIn('40%', r['message'])
        # no bank account: a clear sentence, nothing changes
        with self.assertRaises(GameError) as e:
            buy(story(wallet=2000), 'tap_the', down=540, months=12)
        self.assertEqual(e.exception.code, 'no_account')

    def test_stale_quote_is_refused(self):
        s = opened(wallet=1500, deposit=1000, income_days=14, salary=60)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_home_buy', kind='can_ho_mini', down=1080, months=36, total_interest=1, confirm=True)
        self.assertEqual(e.exception.code, 'stale_quote')

    def test_early_payoff(self):
        s = self.mortgaged('tap_the', months=12, wallet=3000, deposit=1000)
        tick(s, 7, salary=60)
        off = hs._payoff(H(s)['own']['loan'], s['journey']['life_day'])
        B(s)['balance'] += off['total']
        s, r = act(s, 'jr_home_payoff', confirm=True)
        self.assertIsNone(H(s)['own']['loan'])
        self.assertIn('m_home_free', s['journey']['titles'])
        self.assertIn('không còn nợ', r['message'])


class Selling(unittest.TestCase):
    def test_sell_with_a_mortgage_pays_the_bank_first(self):
        s = opened(wallet=1500, deposit=1000, income_days=14, salary=60)
        s, _ = buy(s, 'can_ho_mini', down=1080, months=36)
        tick(s, 60, salary=60)                                               # one in-game year
        own = hs.public(s)['own']
        self.assertEqual(own['value'], 3600 * 103 // 100 // 10 * 10)         # +3 %/năm, rounded down to 10 xu
        sell = own['sell']
        bal = B(s)['balance']
        with self.assertRaises(GameError) as e:
            act(s, 'jr_home_sell', confirm=True, value=1)
        self.assertEqual(e.exception.code, 'stale_quote')
        s, r = act(s, 'jr_home_sell', confirm=True, value=sell['value'])
        self.assertIsNone(H(s)['own'])
        self.assertEqual(B(s)['balance'], bal + sell['get'])
        self.assertEqual(sell['get'], sell['value'] - sell['fee'] - sell['payoff'])
        self.assertEqual(H(s)['past'][-1]['got'], sell['get'])
        self.assertEqual(jr.living_cost(s['journey'])['where'], 'attic')
        self.assertIn('m_home', s['journey']['titles'])                      # a title stays earned

    def test_value_growth_is_capped(self):
        own = dict(price=1000, day=1, kind='tap_the')
        self.assertEqual(hs.value_of(own, 1), 1000)
        self.assertEqual(hs.value_of(own, 1 + 60 * 50), 1300)


class SaveData(unittest.TestCase):
    def test_absent_home_is_valid_and_public(self):
        s = story()
        self.assertNotIn('home', s['journey'])
        view = public_state(s)['journey']['home']
        self.assertEqual(view['place']['where_id'], 'attic')
        self.assertEqual(len(view['market']), len(hs.HOMES))
        self.assertEqual(hs.on_life_day(s), [])

    def test_tampered_homes_are_refused(self):
        s = opened(wallet=1500, deposit=1000, income_days=14, salary=60)
        s, _ = buy(s, 'can_ho_mini', down=1080, months=36)
        validate_state(s)
        breaks = [
            lambda h: h['own'].__setitem__('price', 10),
            lambda h: h['own'].__setitem__('kind', 'tro_moi'),
            lambda h: h.__setitem__('rent', dict(kind='tro_moi', since=1, deposit=60)),
            lambda h: h['own']['loan']['rows'][0].__setitem__('amount', 1),
            lambda h: h['own']['loan']['rows'].pop(),
            lambda h: h['own']['loan'].__setitem__('rate', 1),
            lambda h: h.__setitem__('day', 10**6),
            lambda h: h.__setitem__('extra', 1),
            lambda h: h['stats'].__setitem__('bought', -1),
            lambda h: h.__setitem__('shared', dict(couple=1, id='h1', kind='castle', name='A', since=1)),
        ]
        for i, f in enumerate(breaks):
            bad = copy.deepcopy(s)
            f(H(bad))
            with self.subTest(i=i), self.assertRaises(GameError):
                validate_state(bad)
        bad = copy.deepcopy(s)
        del bad['journey']['bank']
        with self.assertRaises(GameError):
            validate_state(bad)                                              # a mortgage needs its bank

    def test_ticks_are_idempotent_and_migrate_keeps_it(self):
        s = opened(wallet=1500, deposit=1000, income_days=14, salary=60)
        s, _ = buy(s, 'can_ho_mini', down=1080, months=36)
        s['journey']['life_day'] += 12
        bk.on_life_day(s)
        hs.on_life_day(s)
        once = copy.deepcopy(s['journey']['home'])
        hs.on_life_day(s)
        self.assertEqual(H(s), once)
        again = migrate_state(copy.deepcopy(s))
        self.assertEqual(H(again), once)
        validate_state(again)

    def test_free_mode_has_no_homes(self):
        from game.engine import new_state
        s = new_state()
        with self.assertRaises(GameError):
            apply_action(s, None, 'jr_home_buy', dict(kind='tap_the', down=1500, confirm=True))


class SpouseEffects(unittest.TestCase):
    """The inbox side of the couple's home (the database side: tests/test_couple.py HomeTests)."""

    def married(self, couple=7):
        s = story(wallet=100)
        s['marriage'] = dict(v=1, applied=[], spouse=dict(name='Bình', status='married', since=1, wed=1, date=None, couple=couple, side='b'),
                             sticker=True, weddings=1)
        return s

    def test_move_in_and_out(self):
        s = self.married()
        attic = jr.living_cost(s['journey'])
        hs.apply_effect(s, dict(set='in', couple=7, id='h1', kind='nha_pho', name='An'))
        validate_state(s)
        cost = jr.living_cost(s['journey'])
        self.assertEqual((cost['where'], cost['rent']), ('shared', hs.HOMES['nha_pho']['upkeep']))
        self.assertLess(cost['total'], attic['total'])
        self.assertEqual(hs.public(s)['place']['with'], 'An')
        hs.apply_effect(s, dict(set='out', couple=7, id='h9'))              # another home: nothing
        self.assertIsNotNone(H(s)['shared'])
        hs.apply_effect(s, dict(set='out', couple=7, id='h1'))
        self.assertIsNone(H(s)['shared'])
        hs.apply_effect(s, dict(set='in', couple='x', id='h1', kind='nha_pho'))   # malformed: ignored
        self.assertIsNone(H(s)['shared'])

    def test_divorce_ends_the_shared_home(self):
        s = self.married()
        hs.apply_effect(s, dict(set='in', couple=7, id='h1', kind='nha_pho', name='An'))
        s['marriage']['spouse'] = None
        notes = hs.on_life_day(s)
        self.assertIsNone(H(s)['shared'])
        self.assertEqual(jr.living_cost(s['journey'])['where'], 'attic')
        self.assertTrue(notes)

    def test_partner_effects(self):
        from game import marriage as mr
        s = story(wallet=2200)
        s['name'] = 'An'
        s, _ = buy(s, 'tap_the')
        effects = hs.partner_effects(s, 7, 'a', 'sid-b', mr._effect)
        self.assertEqual(effects, [])  # purchasing requires an explicit family invitation
        s, _ = act(s, 'jr_home_sell', confirm=True, value=hs.value_of(H(s)['own'], s['journey']['life_day']))
        self.assertEqual([e['id'] for e in hs.partner_effects(s, 7, 'a', 'sid-b', mr._effect)], ['homeoff:7:a:h1'])


NEW_APARTMENTS = ('can_ho_studio', 'can_ho_1pn', 'can_ho_2pn', 'penthouse')
VILLAS = ('biet_thu_vuon', 'biet_thu_song')


def rich(salary, score=None, wallet=0, deposit=1000):
    """A bank customer with two weeks of `salary` a day (the mortgage's income check) and `score`."""
    s = opened(wallet=wallet + deposit, deposit=deposit, income_days=14, salary=salary)
    if score is not None:
        B(s)['score'] = score
    return s


class Prices097(unittest.TestCase):
    """0.9.13: list prices +20 %, more kinds of homes, grouped as Phòng thuê / Căn hộ / Nhà phố / Biệt thự."""

    def test_list_prices_are_twenty_percent_up_and_round(self):
        for kind, old in hs.OLD_PRICES.items():
            with self.subTest(kind=kind):
                self.assertEqual(hs.HOMES[kind]['price'], old[0] * 120 // 100)
                self.assertEqual(hs.prices(kind), (hs.HOMES[kind]['price'],) + old + (pi.price(hs.HOMES[kind]['price']),))   # 💹 accepted ahead
        self.assertEqual({k: hs.HOMES[k]['price'] for k in hs.OLD_PRICES},
                         dict(tap_the=1800, can_ho_mini=3600, nha_pho=7800, nha_san=14400))
        for kind in hs.OWN:
            with self.subTest(kind=kind):
                self.assertEqual(hs.HOMES[kind]['price'] % 50, 0)
                self.assertEqual(hs.down_min(hs.HOMES[kind]['price']) % 10, 0)
        # the rented room is a daily living cost, not a house price: unchanged then; 💹 07/10 indexed (the deposit stays)
        self.assertEqual((hs.HOMES['tro_moi']['rent'], hs.HOMES['tro_moi']['deposit']), (15, 60))

    def test_groups_and_the_ladder(self):
        self.assertEqual(hs.GROUP_IDS, ('rent', 'apartment', 'townhouse', 'villa'))
        for kind, H in hs.HOMES.items():
            with self.subTest(kind=kind):
                self.assertIn(H['group'], hs.GROUP_IDS)
                self.assertEqual(H['group'] == 'rent', H['kind'] == 'rent')
                self.assertTrue(H['emoji'] and H['name'] and H['where'] and 20 <= len(H['desc']) <= 140)
                self.assertLessEqual(len(hs.lname(H['name'])), 24)
        for kind in NEW_APARTMENTS:
            self.assertEqual(hs.HOMES[kind]['group'], 'apartment')
        for kind in VILLAS:
            self.assertEqual(hs.HOMES[kind]['group'], 'villa')
            self.assertTrue(hs.HOMES[kind]['perk'])
        own = sorted(hs.OWN, key=lambda k: hs.HOMES[k]['price'])
        comfort = [hs.HOMES[k]['comfort'] for k in own]
        self.assertEqual(comfort, sorted(comfort))                           # dearer is never less comfortable
        self.assertEqual(own[-2:], list(VILLAS))                             # the villas top the market
        self.assertGreater(min(hs.HOMES[k]['upkeep'] for k in VILLAS), max(hs.HOMES[k]['upkeep'] for k in hs.OWN if k not in VILLAS))
        # an apartment costs more to run than the house with the same comfort (phí quản lý)
        self.assertGreater(hs.HOMES['can_ho_1pn']['upkeep'], hs.HOMES['nha_pho']['upkeep'])
        self.assertGreater(hs.HOMES['can_ho_2pn']['upkeep'], hs.HOMES['nha_san']['upkeep'])
        self.assertEqual([hs.need_score(k) for k in ('tap_the', 'penthouse', *VILLAS)], [hs.HOME_SCORE, 670, 700, 740])
        cat = jr.content()['homes']                                          # static, sent once at bootstrap
        self.assertEqual([g['id'] for g in cat['groups']], list(hs.GROUP_IDS))
        self.assertEqual([m['id'] for m in cat['homes']], [m['id'] for m in hs.public(story(wallet=40000))['market']])
        row = next(m for m in cat['homes'] if m['id'] == 'biet_thu_song')
        self.assertEqual((row['group'], row['score'], row['perk']), ('villa', 740, hs.HOMES['biet_thu_song']['perk']))
        live = next(m for m in hs.public(story(wallet=40000))['market'] if m['id'] == 'biet_thu_song')
        self.assertEqual(live, dict(id='biet_thu_song', missing=0, missing_all=60000 + hs.buy_fee(60000) + hs.tax('biet_thu_song') - 40000))

    def test_names_inside_sentences_keep_proper_nouns(self):
        self.assertEqual(hs.lname('Biệt thự Sông Hồng'), 'biệt thự Sông Hồng')
        self.assertEqual(hs.lname('Căn tập thể cũ'), 'căn tập thể cũ')

    def test_new_apartments_are_bought_with_a_mortgage(self):
        for kind in NEW_APARTMENTS:
            with self.subTest(kind=kind):
                price = hs.HOMES[kind]['price']
                s = rich(salary=400, score=700, wallet=hs.down_min(price) + hs.buy_fee(price) + hs.tax(kind))
                s, r = buy(s, kind, down=hs.down_min(price), months=36)
                self.assertTrue(r['approved'], r['message'])
                own = H(s)['own']
                self.assertEqual((own['kind'], own['price'], own['loan']['principal']), (kind, price, price - hs.down_min(price)))
                self.assertEqual(jr.living_cost(s['journey'])['rent'], hs.HOMES[kind]['upkeep'])
                validate_state(s)
                sp = s['journey']['life']['spirit'] = 40
                tick(s, 1, salary=400)
                self.assertGreaterEqual(spirit(s), sp + hs.HOMES[kind]['comfort'])

    def test_penthouse_needs_score_670(self):
        price = hs.HOMES['penthouse']['price']
        s = rich(salary=400, score=660, wallet=hs.down_min(price) + hs.buy_fee(price) + hs.tax('penthouse'))
        before = (B(s)['balance'], s['journey']['wallet'])
        s, r = buy(s, 'penthouse', down=hs.down_min(price))
        self.assertFalse(r['approved'])
        self.assertIn('cần từ 670', r['message'])
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), before)
        # the same score buys a cheaper home
        s2 = rich(salary=400, score=660, wallet=5000)
        s2, r = buy(s2, 'can_ho_2pn', down=hs.down_min(hs.HOMES['can_ho_2pn']['price']))
        self.assertTrue(r['approved'], r['message'])


class VillaLoans(unittest.TestCase):
    """Villas: the score each one needs, the same 40 % installment limit, and cash is always fine."""

    def villa(self, kind, salary, score, months=36, down=None):
        price = hs.HOMES[kind]['price']
        s = rich(salary=salary, score=score, wallet=price + hs.buy_fee(price) + hs.tax(kind))
        before = (B(s)['balance'], s['journey']['wallet'])
        s, r = buy(s, kind, down=down or hs.down_min(price), months=months)
        return s, r, before

    def test_score_gate(self):
        s, r, before = self.villa('biet_thu_vuon', salary=600, score=690)
        self.assertFalse(r['approved'])
        self.assertIn('690, cần từ 700', r['message'])
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), before)  # nothing moved
        self.assertIsNone(H(s)['own'] if 'home' in s['journey'] else None)
        s, r, _ = self.villa('biet_thu_song', salary=900, score=720)
        self.assertFalse(r['approved'])
        self.assertIn('cần từ 740', r['message'])

    def test_installment_limit(self):
        s, r, before = self.villa('biet_thu_vuon', salary=200, score=760)   # room 400 xu a month
        self.assertFalse(r['approved'])
        self.assertIn('40%', r['message'])
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), before)
        s, r, _ = self.villa('biet_thu_vuon', salary=200, score=760, down=30000)   # a bigger down payment fits
        self.assertTrue(r['approved'], r['message'])
        self.assertEqual(H(s)['own']['loan']['principal'], 6000)

    def test_approved_villa(self):
        s, r, _ = self.villa('biet_thu_vuon', salary=500, score=720)
        self.assertTrue(r['approved'], r['message'])
        own = H(s)['own']
        self.assertEqual((own['price'], own['down'], own['loan']['principal'], own['loan']['rate']), (36000, 10800, 25200, 1020))
        self.assertLessEqual(own['loan']['rows'][0]['amount'], 500 * hs.MONTH_DAYS * hs.DTI_PCT // 100)
        self.assertIn('Mua biệt thự Vườn Cau giá 36.000 xu', H(s)['log'][-1]['text'])
        s, r, _ = self.villa('biet_thu_song', salary=800, score=760)
        self.assertTrue(r['approved'], r['message'])
        self.assertEqual((H(s)['own']['loan']['principal'], H(s)['own']['loan']['rate']), (42000, 900))
        view = hs.public(s)
        self.assertEqual((view['own']['group'], view['place']['group'], view['place']['comfort']), ('villa', 'villa', 7))
        validate_state(s)

    def test_cash_needs_no_score(self):
        price = hs.HOMES['biet_thu_song']['price']
        s, r = buy(story(wallet=price + hs.buy_fee(price) + hs.tax('biet_thu_song')), 'biet_thu_song')
        self.assertTrue(r['approved'])
        self.assertEqual(s['journey']['wallet'], 0)


class OldSaves097(unittest.TestCase):
    """Homes bought before 0.9.13 keep the price paid, the loan and its schedule; resale follows the price paid."""

    def old_mini(self):
        from unittest import mock
        with mock.patch.dict(hs.HOMES['can_ho_mini'], price=3000):          # the 0.9.5/0.9.6 list price
            s = opened(wallet=1500, deposit=1000, income_days=14, salary=60)
            s, r = buy(s, 'can_ho_mini', down=900, months=36)
        self.assertTrue(r['approved'], r['message'])
        return s

    def test_old_home_and_loan_load_unchanged(self):
        s = self.old_mini()
        own = copy.deepcopy(H(s)['own'])
        self.assertEqual((own['price'], own['down'], own['fee'], own['loan']['principal']), (3000, 900, hs.buy_fee(3000), 2100))
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(H(s)['own'], own)                                   # price, loan, schedule: untouched
        view = hs.public(s)['own']
        self.assertEqual((view['price'], view['list_price'], view['value']), (3000, 3600, 3000))   # no windfall
        tick(s, 5, salary=60)                                                # installments go on as scheduled
        self.assertEqual(H(s)['own']['loan']['rows'][0]['paid'], own['loan']['rows'][0]['amount'])
        self.assertEqual([r['amount'] for r in H(s)['own']['loan']['rows']], [r['amount'] for r in own['loan']['rows']])
        tick(s, 55, salary=60)                                               # a year: +3 % on the price paid
        self.assertEqual(hs.public(s)['own']['value'], 3090)
        s, r = act(s, 'jr_home_sell', confirm=True, value=3090)
        self.assertEqual(H(s)['past'][-1]['price'], 3000)
        validate_state(s)

    def test_only_known_prices_are_valid(self):
        s = self.old_mini()
        for price in (3300, 1500, 3000 * 2):
            bad = copy.deepcopy(s)
            H(bad)['own'].update(price=price, fee=hs.buy_fee(price))
            with self.subTest(price=price), self.assertRaises(GameError):
                validate_state(bad)
        s = opened(wallet=2000)
        s, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)         # a rented room: the same deposit as before
        validate_state(migrate_state(s))


from tests.test_couple import CoupleBase   # noqa: E402  (the database side of a couple)


class CoupleHome(CoupleBase):
    def cmd(self, tok, action, rid, **p):
        return self.store.command(tok, rid, self.store.read(tok)[1], None, action, p)

    def share(self):
        self.act(self.a, 'family_home_request', rid='home-consent-' + str(int(self.clock.t)))
        request = self.view(self.b)['family']['requests'][0]
        self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='home-accept-' + str(request['id']))

    def test_buy_together_from_the_joint_fund_and_move_in(self):
        from game import couple as cp
        from game import marriage as mr
        self.act(self.a, 'fund_deposit', amount=800, rid='deposit-home-1')
        self.fund(self.a, 1300)
        out = self.cmd(self.a, 'jr_home_buy', 'home-buy-0001', kind='tap_the', down=1800, joint=800, confirm=True)
        self.assertTrue(out['result']['approved'])
        self.assertIn('quỹ chung', out['result']['message'])
        self.assertEqual(self.wallet(self.a), 1300 - (1836 + hs.tax('tap_the') - 800))           # 800 > the daily card cap: a home is not capped
        self.assertEqual(cp.joint_account(self.state(self.a))['balance'], 0)
        self.assertEqual(self.row("SELECT amount FROM joint_ledger WHERE kind='home'")['amount'], 800)
        # the next loads: the hold is confirmed, the spouse moves in once
        self.clock.t += cp.HOLD_S + 1
        for _ in range(2):
            mr.on_load(self.store, self.a, self.state(self.a))
            mr.on_load(self.store, self.b, self.state(self.b))
        self.assertFalse((self.state(self.b)['journey'].get('home') or {}).get('shared'))
        self.share()
        sb = self.state(self.b)
        self.assertEqual(sb['journey']['home']['shared']['kind'], 'tap_the')
        self.assertEqual(jr.living_cost(sb['journey'])['where'], 'shared')
        self.assertEqual(self.row("SELECT COUNT(*) AS n FROM marriage_effects WHERE id LIKE 'home:%'")['n'], 0)
        self.assertEqual(self.row("SELECT status FROM joint_ledger WHERE kind='home'")['status'], 'done')
        # selling the home moves the spouse back out
        sa = self.state(self.a)
        value = hs.value_of(sa['journey']['home']['own'], sa['journey']['life_day'])
        self.cmd(self.a, 'jr_home_sell', 'home-sell-0001', confirm=True, value=value)
        mr.on_load(self.store, self.a, self.state(self.a))
        mr.on_load(self.store, self.b, self.state(self.b))
        self.assertIsNone(self.state(self.b)['journey']['home']['shared'])

    def test_a_couple_buys_a_villa_with_the_fund_and_a_mortgage(self):
        from game import marriage as mr
        self.act(self.a, 'fund_deposit', amount=800, rid='deposit-villa-1')

        def ready(s):
            j = s['journey']
            start = j['life_day']
            for d in range(start, start + 14):
                j['life_day'] = d
                jr._wallet(j, 500, 'salary', f'Lương ngày {d}')
            j['life_day'] = start + 14
            j['wallet'] = 18200
            bk.apply(s, 'jr_bk_open', {})
            s['journey']['bank']['score'] = 720
        mr._mutate(self.store, {self.sid(self.a): ready})
        sa = self.state(self.a)
        price, day = hs.HOMES['biet_thu_vuon']['price'], sa['journey']['life_day']
        q = hs.quote(price - hs.down_min(price), hs.offer(sa, 700)['rate'], 36, day)
        out = self.cmd(self.a, 'jr_home_buy', 'home-villa-0001', kind='biet_thu_vuon', down=hs.down_min(price), joint=800,
                       months=36, total_interest=q['interest'], confirm=True)
        self.assertTrue(out['result']['approved'], out['result']['message'])
        own = self.state(self.a)['journey']['home']['own']
        self.assertEqual((own['kind'], own['joint'], own['loan']['principal']), ('biet_thu_vuon', 800, 25200))
        self.assertEqual(self.wallet(self.a), 18200 - (hs.down_min(price) + hs.buy_fee(price) + hs.tax('biet_thu_vuon') - 800))
        self.clock.t += 3600
        for _ in range(2):
            mr.on_load(self.store, self.a, self.state(self.a))
            mr.on_load(self.store, self.b, self.state(self.b))
        self.share()
        self.assertEqual(self.state(self.b)['journey']['home']['shared']['kind'], 'biet_thu_vuon')

    def row(self, sql):
        with self.store.connect() as db:
            r = db.execute(sql).fetchone()
        return dict(r) if r else None


if __name__ == '__main__':
    unittest.main()
