"""🏠 Chuyện nhà thuê (game/tenancy.py, feedback #261): renting and letting moments on the life card."""
import copy
import unittest

from game import housing as hs
from game import life as lf
from game import tenancy as tn
from game.engine import GameError, public_state, validate_state
from game.tenancy_content import CHU, THUE
from tests.test_bank import act, story
from tests.test_housing_dorm import live
from tests.test_housing_multi import buy2, legacy_tenant
from tests.test_housing import buy


def T(s):
    return s['journey'].get('tenancy')


def until_card(s, limit=80):
    for _ in range(limit):
        live(s)
        if T(s) and T(s)['card']:
            return T(s)['card']
    raise AssertionError('no tenancy card in %d days' % limit)


def landlord_state():
    """Lives in the tập thể, lets the studio to a tenant."""
    s = story(wallet=20000)
    s, _ = buy(s, 'tap_the')
    s, r = buy2(s, 'can_ho_studio')
    x = s['journey']['home']['props'][0]
    s, _ = legacy_tenant(s, x['id'])
    return s


class Attic(unittest.TestCase):
    def test_cards_come_rarely_one_a_day_and_never_with_a_life_card(self):
        s = story(wallet=200)
        lf.migrate(s)
        days = []
        for _ in range(120):
            live(s)
            card = T(s)['card'] if T(s) else None
            if card and card['day'] == s['journey']['life_day']:
                days.append(card['day'])
                self.assertIsNone(s['journey']['life']['pending'])          # one card a day at most
                self.assertIn(card['ref'], {x['id'] for x in THUE})        # the attic: the renting side only
        self.assertGreaterEqual(len(days), 5)
        self.assertTrue(all(b - a >= tn.GAP for a, b in zip(days, days[1:])))
        self.assertGreaterEqual(min(days), tn.FIRST_DAY)

    def test_choose_moves_spirit_bond_and_a_few_xu(self):
        s = story(wallet=200)
        lf.migrate(s)
        card = until_card(s)
        view = public_state(s)['life']['pending']
        self.assertEqual((view['id'], view['kind'], view['stage']), (card['id'], 'home', 'dorm'))
        self.assertTrue(view['lines'] and len(view['choices']) == 2 and view['speaker'])
        self.assertNotIn('{', ' '.join(view['lines'] + [view['title']] + [c['label'] for c in view['choices']]))
        x = tn.INDEX[card['ref']]
        c = next(c for c in x['choices'] if c['money'] < 0) if any(c['money'] < 0 for c in x['choices']) else x['choices'][0]
        L0 = copy.deepcopy(s['journey']['life'])
        w0 = s['journey']['wallet']
        s2, r = act(s, 'lf_choose', id=card['id'], choice=c['id'])
        self.assertTrue(r['message'])
        self.assertEqual(s2['journey']['wallet'], w0 + c['money'])
        self.assertEqual(s2['journey']['life']['spirit'], min(100, L0['spirit'] + c['spirit']))
        done = public_state(s2)['life']['pending']
        self.assertEqual(done['stage'], 'done')
        self.assertEqual(done['trail'][0], r['message'])
        with self.assertRaises(GameError):
            act(s2, 'lf_choose', id=card['id'], choice=c['id'])                # once
        s3, _ = act(s2, 'lf_close', id=card['id'])
        self.assertIsNone(public_state(s3)['life']['pending'])
        self.assertIsNone(T(s3)['card'])

    def test_a_cost_needs_the_wallet_and_the_default_is_free(self):
        for x in THUE + CHU:
            defaults = [c for c in x['choices'] if c['default']]
            self.assertEqual(len(defaults), 1, x['id'])
            self.assertGreaterEqual(defaults[0]['money'], 0, x['id'])
            for c in x['choices']:
                self.assertLessEqual(abs(c['spirit']), 4)
                self.assertLessEqual(abs(c['money']), 4)
        s = story(wallet=200)
        lf.migrate(s)
        card = until_card(s)
        while not any(c['money'] < 0 for c in tn.INDEX[card['ref']]['choices']):
            card = until_card(s)
        s['journey']['wallet'] = 0
        paid = next(c for c in tn.INDEX[card['ref']]['choices'] if c['money'] < 0)
        view = public_state(s)['life']['pending']
        self.assertFalse(next(c for c in view['choices'] if c['id'] == paid['id'])['ok'])
        with self.assertRaises(GameError):
            act(s, 'lf_choose', id=card['id'], choice=paid['id'])

    def test_undecided_takes_the_default_next_day(self):
        s = story(wallet=200)
        lf.migrate(s)
        card = until_card(s)
        spirit = s['journey']['life']['spirit']
        live(s)
        self.assertNotEqual((T(s)['card'] or {}).get('id'), card['id'])
        row = T(s)['log'][-1]
        d = next(c for c in tn.INDEX[card['ref']]['choices'] if c['default'])
        self.assertEqual((row['ref'], row['choice']), (card['ref'], d['id']))
        self.assertGreaterEqual(row['money'], 0)
        validate_state(s)
        self.assertGreaterEqual(s['journey']['life']['spirit'], 0)
        del spirit

    def test_owners_and_the_dorm_get_no_renting_card(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'tap_the')
        lf.migrate(s)
        for _ in range(60):
            live(s)
            self.assertFalse(T(s) and T(s)['card'])
        s = story(wallet=100)
        lf.migrate(s)
        s, _ = act(s, 'jr_home_rent', kind='ky_tuc_xa', confirm=True)
        for _ in range(60):
            live(s)
            self.assertFalse(T(s) and T(s)['card'])

    def test_a_lease_from_a_player_never_names_the_landlord(self):
        s = story(wallet=200)
        lf.migrate(s)
        j = s['journey']
        j['rental'] = dict(id='rent-' + 'a' * 24, kind='tap_the', rent=50, start_day=j['life_day'], end_day=j['life_day'] + 500)
        refs = set()
        for _ in range(150):
            live(s)
            if T(s) and T(s)['card']:
                refs.add(T(s)['card']['ref'])
        self.assertTrue(refs)
        self.assertFalse({x['id'] for x in THUE if x.get('landlord')} & refs)


class Landlord(unittest.TestCase):
    def test_letting_brings_tenant_moments_and_closeness(self):
        s = landlord_state()
        lf.migrate(s)
        x = s['journey']['home']['props'][0]
        name = hs.tenant(x['let'])[1]
        card = until_card(s)
        self.assertIn(card['ref'], {c['id'] for c in CHU})
        view = public_state(s)['life']['pending']
        self.assertEqual(view['speaker']['name'], name)
        self.assertEqual(view['cat'], 'chu')
        rent = copy.deepcopy(x['let'])
        s, r = act(s, 'lf_choose', id=card['id'], choice=next(c['id'] for c in tn.INDEX[card['ref']]['choices'] if c['default']))
        key = f'{x["id"]}:{x["let"]["since"]}'
        self.assertGreater(T(s)['close'][key], tn.CLOSE_START)
        self.assertEqual(tn.closeness(s, s['journey']['home']['props'][0]), T(s)['close'][key])
        self.assertIn('Thân thiết', public_state(s)['life']['pending']['trail'][-1])
        self.assertEqual(s['journey']['home']['props'][0]['let']['rent'], rent['rent'])  # the real rent is housing's
        validate_state(s)


class Saves(unittest.TestCase):
    def test_validation_and_older_saves(self):
        s = story(wallet=200)
        lf.migrate(s)
        validate_state(s)                       # no block at all: fine
        until_card(s)
        validate_state(s)
        bad = copy.deepcopy(s)
        T(bad)['card']['ref'] = 'nope'
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(s)
        T(bad)['extra'] = 1
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(s)
        T(bad)['card']['id'] = 'lf-1'
        with self.assertRaises(GameError):
            validate_state(bad)
        # an older build's journey check takes a save with the block: it only needs its own keys
        from game import journey as jr
        self.assertTrue(set(jr.initial()) <= set(s['journey']))

    def test_life_cards_roll_as_before_until_a_choice_changes_the_spirit(self):
        """Its own random stream: up to the first moment, the life layer's cards are exactly the ones without it."""
        a = story(wallet=200)
        lf.migrate(a)
        b = copy.deepcopy(a)
        seen_a, seen_b = [], []
        orig = tn.roll
        try:
            while not (T(a) and T(a)['card']):
                live(a)
                seen_a.append((a['journey']['life']['pending'] or {}).get('ref'))
            tn.roll = lambda *a_, **k: None
            for _ in seen_a:
                live(b)
                seen_b.append((b['journey']['life']['pending'] or {}).get('ref'))
        finally:
            tn.roll = orig
        self.assertEqual(seen_a, seen_b)
        self.assertGreaterEqual(len(seen_a), tn.FIRST_DAY)


if __name__ == '__main__':
    unittest.main()
