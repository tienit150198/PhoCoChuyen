"""Personal investing: savings, Mây Coin and scam offers (game/invest.py)."""
import copy
import unittest

from game import invest as iv
from game import journey as jr
from game.engine import GameError, new_state, validate_state


def state(wallet=600, seed=12345, max_wallet=None):
    s = new_state()
    jr.enable_story(s, seed)
    s['journey']['gender'] = 'female'
    j = s['journey']
    j['wallet'] = wallet
    j['stats']['max_wallet'] = max(wallet, max_wallet or 0)
    iv.migrate(s)
    validate_state(s)
    iv.validate(s)
    return s


def act(s, name, **p):
    """Transactional like engine.apply_action: a failure leaves `s` untouched."""
    t = copy.deepcopy(s)
    t, r = iv.action(t, name, p)
    return t, r


def days(s, n=1):
    """Advance life days the way end_day does (journey bumps life_day, then invest catches up)."""
    notes = []
    for _ in range(n):
        s['journey']['life_day'] += 1
        notes += iv.on_life_day(s)
    iv.validate(s)
    validate_state(s)
    return notes


def inv(s):
    return s['journey']['invest']


class Unlock(unittest.TestCase):
    def test_locked_until_wallet_reached_500_once(self):
        s = state(wallet=300)
        self.assertFalse(iv.public(s)['unlocked'])
        with self.assertRaises(GameError) as cm:
            act(s, 'iv_save', amount=10)
        self.assertEqual(cm.exception.code, 'locked')
        # Reached 500 once, spent since: still open.
        s = state(wallet=100, max_wallet=520)
        self.assertTrue(iv.public(s)['unlocked'])
        s, _ = act(s, 'iv_save', amount=50)
        self.assertEqual(inv(s)['saving']['balance'], 50)

    def test_public_works_without_invest_state(self):
        s = new_state()
        pub = iv.public(s)
        self.assertFalse(pub['unlocked'])
        self.assertEqual(len(pub['coin']['prices']), iv.PREHISTORY)
        iv.validate(s)  # absent: nothing to check


class Market(unittest.TestCase):
    def test_price_path_is_deterministic_for_a_seed(self):
        a, b, c = state(seed=7), state(seed=7), state(seed=8)
        days(a, 15)
        days(b, 15)
        days(c, 15)
        self.assertEqual(inv(a)['prices'], inv(b)['prices'])
        self.assertNotEqual(inv(a)['prices'], inv(c)['prices'])
        self.assertEqual(len(inv(a)['prices']), iv.HISTORY)

    def test_catch_up_is_idempotent_and_equals_step_by_step(self):
        a, b = state(seed=3), state(seed=3)
        days(a, 6)
        b['journey']['life_day'] += 6
        iv.on_life_day(b)
        iv.on_life_day(b)  # nothing more happens
        self.assertEqual(inv(a)['prices'], inv(b)['prices'])
        self.assertEqual(inv(b)['day'], b['journey']['life_day'])

    def test_moves_include_rare_pumps_and_crashes_and_stay_bounded(self):
        import random
        kinds, price = {'pump': 0, 'crash': 0, '': 0}, iv.BASE
        for d in range(2000):
            price, kind = iv._step(price, random.Random(f'may|99|{d}'))
            kinds[kind] += 1
            self.assertTrue(iv.PRICE_MIN <= price <= iv.PRICE_MAX)
        self.assertTrue(40 < kinds['pump'] < 160 and 30 < kinds['crash'] < 130, kinds)


class Coin(unittest.TestCase):
    def test_buy_charges_fee_and_moves_wallet(self):
        s = state(wallet=600)
        s, r = act(s, 'iv_buy', amount=100)
        c = inv(s)['coin']
        self.assertEqual(s['journey']['wallet'], 500)
        self.assertEqual(c['fees'], 2)
        self.assertEqual(c['basis'], 100)
        self.assertEqual(c['units'], 98 * iv.COIN * iv.CENT // inv(s)['price'])
        self.assertIn('first_coin', inv(s)['badges'])
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount']), ('invest', -100))

    def test_no_negative_wallet_and_bad_payloads(self):
        s = state(wallet=600)
        for p in ({'amount': 601}, {'amount': 5}, {'amount': 50.0}, {'amount': '50'}, {'amount': True},
                  {}, {'all': False}, {'amount': 50, 'all': True}, {'amount': 50, 'x': 1}):
            with self.assertRaises(GameError, msg=p):
                act(s, 'iv_buy', **p)
        s, _ = act(s, 'iv_buy', all=True)
        self.assertEqual(s['journey']['wallet'], 0)
        with self.assertRaises(GameError):
            act(s, 'iv_buy', amount=10)
        with self.assertRaises(GameError):
            act(s, 'iv_save', all=True)

    def test_sell_more_than_owned_is_rejected(self):
        s = state(wallet=600)
        with self.assertRaises(GameError):
            act(s, 'iv_sell', all=True)
        s, _ = act(s, 'iv_buy', amount=100)
        value = iv.public(s)['coin']['value']
        with self.assertRaises(GameError):
            act(s, 'iv_sell', amount=value + 1)
        s, r = act(s, 'iv_sell', amount=50)
        self.assertGreater(inv(s)['coin']['units'], 0)
        s, r = act(s, 'iv_sell', all=True)
        c = inv(s)['coin']
        self.assertEqual((c['units'], c['basis']), (0, 0))

    def test_round_trip_loses_the_fees(self):
        s = state(wallet=600)
        s, _ = act(s, 'iv_buy', amount=200)
        s, r = act(s, 'iv_sell', all=True)
        c = inv(s)['coin']
        self.assertLess(s['journey']['wallet'], 600)
        self.assertEqual(c['realised'], s['journey']['wallet'] - 600)
        self.assertGreaterEqual(c['fees'], 7)

    def test_profit_and_loss_follow_the_price(self):
        s = state(wallet=600)
        s, _ = act(s, 'iv_buy', amount=200)
        inv(s)['price'] *= 2
        inv(s)['prices'][-1] = inv(s)['price']
        pub = iv.public(s)['coin']
        self.assertGreater(pub['unrealised'], 150)
        s, _ = act(s, 'iv_sell', all=True)
        self.assertGreater(inv(s)['coin']['realised'], 150)
        self.assertGreater(s['journey']['stats']['max_wallet'], 750)


class Savings(unittest.TestCase):
    def test_interest_is_credited_each_term(self):
        s = state(wallet=1000)
        s, _ = act(s, 'iv_save', amount=1000)
        days(s, 6)
        self.assertEqual(inv(s)['saving']['balance'], 1000)
        self.assertEqual(iv.public(s)['saving']['pending'], 18)
        notes = days(s, 1)
        sv = inv(s)['saving']
        self.assertEqual(sv['balance'], 1021)
        self.assertEqual(sv['earned'], 21)
        self.assertTrue(any('lãi' in n for n in notes))
        self.assertIn('first_interest', inv(s)['badges'])

    def test_early_withdrawal_forfeits_the_term_interest_never_principal(self):
        s = state(wallet=1000)
        s, _ = act(s, 'iv_save', amount=500)
        days(s, 3)
        s, r = act(s, 'iv_withdraw', amount=200)
        self.assertIn('mất 4 xu', r['message'])
        self.assertEqual(inv(s)['saving']['balance'], 300)
        self.assertEqual(inv(s)['saving']['forfeited'], 4)
        self.assertEqual(s['journey']['wallet'], 700)
        with self.assertRaises(GameError):
            act(s, 'iv_withdraw', amount=301)
        s, _ = act(s, 'iv_withdraw', all=True)
        self.assertEqual(s['journey']['wallet'], 1000)
        with self.assertRaises(GameError):
            act(s, 'iv_withdraw', all=True)


def with_offer(s, kind='moon', pay_days=2):
    day = s['journey']['life_day']
    inv(s)['scam'] = dict(kind=kind, stage='offer', day=day, stake=0, paid=0, pay_days=pay_days, paid_days=0)
    iv.validate(s)
    return s


class Scam(unittest.TestCase):
    def test_offers_appear_rarely_and_deterministically(self):
        seen = []
        for seed in range(6):
            s = state(seed=seed)
            for _ in range(60):
                days(s)
                sc = inv(s)['scam']
                if sc and sc['stage'] == 'offer' and sc['day'] == s['journey']['life_day']:
                    seen.append((seed, s['journey']['life_day']))
                if sc and sc['stage'] == 'offer' and seed % 2:
                    s, _ = act(s, 'iv_scam_decline')
        self.assertTrue(4 <= len(seen) <= 40, seen)
        a, b = state(seed=4), state(seed=4)
        days(a, 60)
        days(b, 60)
        self.assertEqual(inv(a)['log'], inv(b)['log'])

    def test_no_offers_while_locked(self):
        s = state(wallet=100)
        days(s, 120)
        self.assertIsNone(inv(s)['scam'])
        self.assertFalse(any(r['kind'].startswith('scam') for r in inv(s)['log']))

    def test_join_pays_a_little_then_rug_pulls(self):
        s = with_offer(state(wallet=600), pay_days=2)
        with self.assertRaises(GameError):
            act(s, 'iv_scam_join', amount=10)
        with self.assertRaises(GameError):
            act(s, 'iv_scam_join', amount=601)
        s, _ = act(s, 'iv_scam_join', amount=200)
        self.assertEqual(s['journey']['wallet'], 400)
        days(s)
        self.assertEqual(s['journey']['wallet'], 408)
        days(s)
        self.assertEqual(s['journey']['wallet'], 416)
        notes = days(s)
        self.assertIsNone(inv(s)['scam'])
        self.assertEqual(s['journey']['wallet'], 416)
        self.assertEqual(inv(s)['stats']['lost'], 184)
        self.assertIn('rug_lesson', inv(s)['badges'])
        self.assertTrue(any('biến mất' in n for n in notes))
        self.assertEqual(inv(s)['log'][-1]['kind'], 'scam_gone')
        # Cooldown: no new offer right away.
        self.assertGreater(inv(s)['stats']['next_scam'], s['journey']['life_day'])

    def test_one_payout_variant(self):
        s = with_offer(state(wallet=600), pay_days=1)
        s, _ = act(s, 'iv_scam_join', amount=100)
        days(s, 2)
        self.assertIsNone(inv(s)['scam'])
        self.assertEqual(s['journey']['wallet'], 504)

    def test_decline_gives_badge_and_later_news(self):
        s = with_offer(state(wallet=600))
        s, r = act(s, 'iv_scam_decline')
        self.assertIn('scam_spotter', inv(s)['badges'])
        self.assertEqual(inv(s)['stats']['declined'], 1)
        self.assertEqual(r['effects'][0][:2], '🛡️')
        with self.assertRaises(GameError):
            act(s, 'iv_scam_join', amount=50)
        with self.assertRaises(GameError):
            act(s, 'iv_scam_decline')
        days(s, iv.SCAM_ECHO)
        self.assertIsNone(inv(s)['scam'])
        self.assertEqual(inv(s)['log'][-1]['kind'], 'scam_news')
        self.assertEqual(s['journey']['wallet'], 600)

    def test_ignored_offer_expires(self):
        s = with_offer(state(wallet=600))
        days(s, iv.SCAM_OPEN)
        self.assertEqual(inv(s)['scam']['stage'], 'expired')
        with self.assertRaises(GameError):
            act(s, 'iv_scam_join', amount=50)
        self.assertEqual(iv.public(s)['scam']['stage'], 'expired')


class SaveFile(unittest.TestCase):
    def test_migrate_adds_defaults_to_an_old_journey(self):
        s = new_state()
        jr.enable_story(s, 99)
        s['journey']['life_day'] = 17
        self.assertNotIn('invest', s['journey'])
        iv.migrate(s)
        v = inv(s)
        self.assertEqual(v['day'], 17)
        self.assertEqual(v['saving']['term_day'], 17)
        iv.validate(s)
        # A partial older invest dict gets the missing keys, keeps its data.
        del v['badges'], v['coin']['trades']
        v['saving']['balance'] = 40
        iv.migrate(s)
        self.assertEqual(inv(s)['badges'], [])
        self.assertEqual(inv(s)['coin']['trades'], 0)
        self.assertEqual(inv(s)['saving']['balance'], 40)
        iv.validate(s)
        again = copy.deepcopy(s)
        iv.migrate(again)
        self.assertEqual(again, s)

    def test_validate_rejects_corrupt_state(self):
        base = state(wallet=600)
        base, _ = act(base, 'iv_buy', amount=100)
        corrupt = [
            lambda v: v.__setitem__('price', 0),
            lambda v: v.__setitem__('price', 12.5),
            lambda v: v['prices'].append(123),
            lambda v: v.__setitem__('prices', []),
            lambda v: v['coin'].__setitem__('units', -1),
            lambda v: v['coin'].__setitem__('units', '5'),
            lambda v: v['coin'].__setitem__('hack', 1),
            lambda v: v['saving'].__setitem__('balance', -5),
            lambda v: v['saving'].__setitem__('term_day', 10**6),
            lambda v: v.__setitem__('scam', dict(kind='ponzi', stage='offer', day=1, stake=0, paid=0, pay_days=1, paid_days=0)),
            lambda v: v.__setitem__('scam', dict(kind='moon', stage='joined', day=1, stake=0, paid=0, pay_days=1, paid_days=0)),
            lambda v: v.__setitem__('scam', dict(kind='moon', stage='offer', day=1, stake=0, paid=0, pay_days=3, paid_days=0)),
            lambda v: v['log'].append(dict(day=1, kind='hack', text='x')),
            lambda v: v['log'].append(dict(day=1, kind='buy', text='x' * 500)),
            lambda v: v.__setitem__('log', [dict(day=1, kind='buy', text='x')] * 21),
            lambda v: v['badges'].append('millionaire'),
            lambda v: v['badges'].append('first_coin'),
            lambda v: v['stats'].__setitem__('lost', -1),
            lambda v: v.__setitem__('extra', 1),
            lambda v: v.__setitem__('version', 2),
            lambda v: v.__setitem__('day', 10**5),
        ]
        for i, fn in enumerate(corrupt):
            s = copy.deepcopy(base)
            fn(inv(s))
            with self.assertRaises(GameError, msg=f'corruption #{i}'):
                iv.validate(s)
        s = copy.deepcopy(base)
        s['journey']['invest'] = []
        with self.assertRaises(GameError):
            iv.validate(s)

    def test_public_view_shape(self):
        s = with_offer(state(wallet=600))
        pub = iv.public(s)
        self.assertEqual(pub['scam']['days_left'], iv.SCAM_OPEN)
        self.assertEqual(len(pub['scam']['flags']), 4)
        self.assertEqual(pub['rules']['fee_pct'], 2)
        for k in ('balance', 'pending', 'term_left', 'daily'):
            self.assertIn(k, pub['saving'])
        for k in ('price', 'prices', 'change', 'units', 'value', 'unrealised', 'realised'):
            self.assertIn(k, pub['coin'])

    def test_unknown_command(self):
        s = state()
        with self.assertRaises(GameError):
            act(s, 'iv_moon', amount=1)


if __name__ == '__main__':
    unittest.main()
