"""Chuyện bất ngờ trong ca: live happenings (theft, damage, compensation, break-ins)."""
import copy
import unittest

from game import happenings as hp
from game import journey as jr
from game.content import CAREERS
from game.engine import GameError, apply_action, public_state, validate_state, new_state, migrate_state
from game.happening_content import HAPPENINGS, INDEX, REACTIONS, KINDS, EMPLOYEE


def ledger_ok(c):
    f = c['ops']['finance']
    return f['opening_balance'] + sum(x['amount'] for x in f['ledger']) == c['money']


def quiet(c):
    ext = c.get('ext') or {}
    if 'situation' in ext:
        ext['situation'] = None
        ext['sit_day'] = c['day']
    d = ext.get('data') or {}
    if isinstance(d.get('desk'), dict):
        d['desk']['ev'] = None


def open_day(career, story=True, seed=4242, day=None):
    s = new_state()
    if story:
        jr.enable_story(s, seed)
        s['journey']['gender'] = 'male'
        s['journey']['intro'] = True
        if career not in s['journey']['unlocked']:
            s['journey']['unlocked'].append(career)
    from game.employment import hired_record, required
    if required(career):
        s['careers'][career]['job'] = hired_record(career)
    s, _ = apply_action(s, career, 'select_career', {})
    s, _ = apply_action(s, career, 'start_day', {})
    c = s['careers'][career]
    quiet(c)
    c['incidents']['plan'] = None
    c['incidents']['active'] = None
    c['happen']['plan'] = None
    c['happen']['live'] = None
    c['event'] = None
    if day:
        c['day'] = day
        quiet(c)
    return s


def fire(s, career, sid, roll=None, **kw):
    c = s['careers'][career]
    live = hp._fire(s, c, career, sid)
    if roll is not None:
        live['_roll'] = roll
    live.update(kw)
    validate_state(s)
    return live


def react(s, career, choice):
    return apply_action(s, career, 'hap_react', {'choice': choice})


def cats(c, ref):
    return [x['category'] for x in c['ops']['finance']['ledger'] if x['ref'] == ref]


class Content(unittest.TestCase):
    def test_integrity_and_coverage(self):
        self.assertGreaterEqual(len(HAPPENINGS), 45)
        for x in HAPPENINGS:
            self.assertIn(x['kind'], KINDS)
            self.assertIn(x['default'], x['reactions'], x['id'])
            for r in x['reactions']:
                self.assertIn(r, REACTIONS, x['id'])
            for cid in x['careers']:
                self.assertIn(cid, CAREERS, x['id'])
            self.assertTrue(x['loss'], x['id'])
            self.assertNotIn('camera', [x['default']])
        for cid in CAREERS:
            own = [x for x in HAPPENINGS if cid in x['careers']]
            self.assertGreaterEqual(len(own), 5, cid)
            self.assertGreaterEqual(len({x['kind'] for x in own}), 2, cid)

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'của game', 'người chơi', 'mô phỏng', 'giả lập')
        for x in HAPPENINGS:
            for text in (x['title'], x['text'], x['label']):
                for b in banned:
                    self.assertNotIn(b, text, x['id'])
        for r in REACTIONS.values():
            for text in (r['label'], r['hint'], r['win'], r['lose']):
                for b in banned:
                    self.assertNotIn(b, text)


class Rates(unittest.TestCase):
    def test_rate_curve(self):
        self.assertEqual(hp.rate(1), 0)
        self.assertEqual(hp.rate(2), 0)
        self.assertLess(hp.rate(4), hp.rate(8))
        self.assertLess(hp.rate(8), hp.rate(20))
        self.assertLess(hp.rate(20, 'calm'), hp.rate(20))
        self.assertGreater(hp.rate(20, 'festival'), hp.rate(20))
        self.assertLessEqual(hp.rate(99, 'festival'), 0.5)

    def test_plan_is_deterministic_and_frequency_matches(self):
        s = open_day('grocery')
        c = s['careers']['grocery']
        a = hp.roll_plan(s, c, 'grocery')
        b = hp.roll_plan(copy.deepcopy(s), copy.deepcopy(c), 'grocery')
        self.assertEqual(a[1], b[1])
        self.assertEqual(a[0] and a[0]['id'], b[0] and b[0]['id'])
        early = late = 0
        for seed in range(1, 201):
            s['journey']['seed'] = seed
            c['day'] = 3 + seed % 3
            early += hp.roll_plan(s, c, 'grocery')[1] is not None
            c['day'] = 30 + seed % 20
            late += hp.roll_plan(s, c, 'grocery')[1] is not None
        self.assertLess(early, late)
        self.assertTrue(10 <= early <= 60, early)
        self.assertTrue(35 <= late <= 100, late)
        c['day'] = 2
        self.assertEqual(hp.roll_plan(s, c, 'grocery'), (None, None))

    def test_story_off_nothing_happens(self):
        s = open_day('grocery', story=False)
        c = s['careers']['grocery']
        for d in range(5, 40):
            c['day'] = d
            c['open'] = False
            s, _ = apply_action(s, 'grocery', 'start_day', {})
            c = s['careers']['grocery']
            self.assertIsNone(c['happen']['plan'])
            self.assertIsNone(c['happen']['live'])
        c['day_completed'] = 3
        s, _ = apply_action(s, 'grocery', 'advance', {})
        self.assertIsNone(s['careers']['grocery']['happen']['live'])

    def test_fires_after_finished_job_not_while_busy(self):
        s = open_day('grocery', day=10)
        c = s['careers']['grocery']
        c['happen']['plan'] = dict(day=10, at=1, script='grab_till', fired=False)
        s, r = apply_action(s, 'grocery', 'advance', {})
        self.assertIsNone(s['careers']['grocery']['happen']['live'])   # no job finished yet
        c = s['careers']['grocery']
        c['day_completed'] = 1
        c['incidents']['active'] = dict(id='inc-9', script=next(iter(__import__('game.incident_content', fromlist=['INDEX']).INDEX)),
                                        day=10, practice=False, follow=False)
        s, r = apply_action(s, 'grocery', 'advance', {})
        self.assertIsNone(s['careers']['grocery']['happen']['live'])   # an open decision card: wait
        c = s['careers']['grocery']
        c['incidents']['active'] = None
        s, r = apply_action(s, 'grocery', 'advance', {})
        live = s['careers']['grocery']['happen']['live']
        self.assertIsNotNone(live)
        self.assertEqual(r['happening'], live['id'])
        # the chuyện đời layer steps aside while the scene event is open
        from game import incidents as inc
        self.assertTrue(inc._busy(s['careers']['grocery']))
        # only one per day
        c = s['careers']['grocery']
        c['happen']['live'] = None
        c['happen']['plan'] = dict(day=10, at=1, script='grab_shelf', fired=False)
        s, r = apply_action(s, 'grocery', 'advance', {})
        self.assertIsNone(s['careers']['grocery']['happen']['live'])


class Theft(unittest.TestCase):
    def test_till_theft_let_costs_cash_with_category(self):
        s = open_day('grocery', day=8)
        c = s['careers']['grocery']
        live = fire(s, 'grocery', 'grab_till', roll=99)
        before = c['money']
        s, r = react(s, 'grocery', 'let')
        c = s['careers']['grocery']
        cash = live['facts']['cash']
        self.assertEqual(c['money'], before - min(cash, before))
        self.assertIn('theft_loss', cats(c, live['id']))
        self.assertTrue(ledger_ok(c))
        last = c['happen']['last']
        self.assertEqual(sum(x['amount'] for x in last['lines']), -min(cash, before))
        pub = public_state(s)['careers']['grocery']['happen']
        self.assertEqual(pub['last']['label'], INDEX['grab_till']['label'])
        self.assertNotIn('_roll', str(pub))

    def test_stock_theft_takes_inventory(self):
        from game import inventory
        s = open_day('grocery', day=8)
        c = s['careers']['grocery']
        live = fire(s, 'grocery', 'grab_shelf', roll=99)
        counts = {i: inventory.count(c, i) for i, q, u in live['facts']['stock']}
        s, _ = react(s, 'grocery', 'let')
        c = s['careers']['grocery']
        for item, qty, unit in live['facts']['stock']:
            self.assertEqual(inventory.count(c, item), counts[item] - qty)
        self.assertTrue(c['happen']['last']['items'])

    def test_stopped_theft_loses_nothing(self):
        s = open_day('grocery', day=8)
        c = s['careers']['grocery']
        fire(s, 'grocery', 'grab_till', roll=0)
        before, wallet = c['money'], s['journey']['wallet']
        s, r = react(s, 'grocery', 'shout')
        c = s['careers']['grocery']
        self.assertEqual(c['money'], before)
        self.assertEqual(s['journey']['wallet'], wallet)
        self.assertTrue(c['happen']['last']['won'])
        self.assertTrue(r['celebrate'])

    def test_other_stock_kinds(self):
        from game import boba
        for career in ('mother_baby', 'pharmacy', 'milk_tea'):
            s = open_day(career, day=None if career == 'milk_tea' else 8)
            c = s['careers'][career]
            live = fire(s, career, 'grab_shelf' if career != 'milk_tea' else 'grab_shelf', roll=99)
            self.assertTrue(live['facts']['stock'], career)
            item, qty, _ = live['facts']['stock'][0]
            have = boba.stock(c)[item] if career == 'milk_tea' else c['stock'][item]
            s, _ = react(s, career, 'let')
            c = s['careers'][career]
            now = boba.stock(c)[item] if career == 'milk_tea' else c['stock'][item]
            self.assertEqual(now, have - qty, career)
            validate_state(s)

    def test_chase_can_hurt_wallet(self):
        s = open_day('grocery', day=8)
        live = fire(s, 'grocery', 'grab_till', roll=99, _hurt=0)
        wallet = s['journey']['wallet']
        s, _ = react(s, 'grocery', 'chase')
        last = s['careers']['grocery']['happen']['last']
        self.assertTrue(last['hurt'])
        self.assertEqual(s['journey']['wallet'], wallet - live['_hurt_cost'])
        self.assertIn('medical', [x['cat'] for x in last['lines']])

    def test_camera_needs_camera(self):
        s = open_day('grocery', day=8)
        fire(s, 'grocery', 'grab_till', roll=99)
        with self.assertRaises(GameError):
            react(s, 'grocery', 'camera')
        pub = public_state(s)['careers']['grocery']['happen']['live']
        cam = next(r for r in pub['reactions'] if r['id'] == 'camera')
        self.assertFalse(cam['enabled'])

    def test_no_double_charge(self):
        s = open_day('grocery', day=8)
        fire(s, 'grocery', 'grab_till', roll=99)
        s, _ = react(s, 'grocery', 'let')
        money = s['careers']['grocery']['money']
        with self.assertRaises(GameError):
            react(s, 'grocery', 'let')
        s, _ = apply_action(s, 'grocery', 'end_day', {})
        self.assertLessEqual(s['careers']['grocery']['money'], money)   # closing bills, no second theft
        ledger = s['careers']['grocery']['ops']['finance']['ledger']
        self.assertEqual(sum(1 for x in ledger if x['category'] == 'theft_loss'), 1)

    def test_moment_passes_when_you_keep_working(self):
        s = open_day('grocery', day=8)
        live = fire(s, 'grocery', 'grab_till', roll=0)
        s, r = apply_action(s, 'grocery', 'advance', {})
        c = s['careers']['grocery']
        self.assertIsNone(c['happen']['live'])
        self.assertTrue(c['happen']['last']['auto'])
        self.assertEqual(c['happen']['last']['choice'], 'let')
        self.assertEqual(r['happen_auto'], live['id'])

    def test_employee_pays_half_of_till_shortage(self):
        s = open_day('teacher', day=8)
        c = s['careers']['teacher']
        live = fire(s, 'teacher', 'class_fund', roll=99)
        cash = live['facts']['cash']
        lines = c['happen']['live']['applied']
        wallet_part = sum(x['amount'] for x in lines if x['where'] == 'wallet')
        self.assertEqual(wallet_part, -(cash // 2))
        self.assertTrue(ledger_ok(c))
        s, _ = react(s, 'teacher', 'let')
        validate_state(s)


class Damage(unittest.TestCase):
    def test_parents_pay_or_you_do(self):
        s = open_day('florist', day=8)
        c = s['careers']['florist']
        fire(s, 'florist', 'ball_window', roll=0)
        money = c['money']
        s2, _ = react(copy.deepcopy(s), 'florist', 'parents')
        self.assertEqual(s2['careers']['florist']['money'], money)
        live = fire(s, 'florist', 'ball_window', roll=99) if False else c['happen']['live']
        live['_roll'] = 99
        s3, _ = react(s, 'florist', 'parents')
        c3 = s3['careers']['florist']
        self.assertLess(c3['money'], money)
        self.assertIn('damage', cats(c3, live['id']))
        self.assertTrue(ledger_ok(c3))

    def test_insurance_pays_part_of_damage(self):
        s = open_day('florist', day=8)
        c = s['careers']['florist']
        c['ops']['security']['insurance'] = True
        live = fire(s, 'florist', 'ball_window', roll=99)
        self.assertTrue(live['insured'])
        money = c['money']
        s, _ = react(s, 'florist', 'forgive')
        c = s['careers']['florist']
        dmg = live['facts']['damage']
        self.assertEqual(c['money'], money - dmg + dmg * hp.INSURANCE_PERCENT // 100)
        self.assertIn('insurance_recovery', cats(c, live['id']))

    def test_compensation_choices(self):
        s = open_day('restaurant', day=8)
        live = fire(s, 'restaurant', 'spill_phone', roll=0)
        comp = live['facts']['comp']
        money = s['careers']['restaurant']['money']
        a, _ = react(copy.deepcopy(s), 'restaurant', 'pay')
        self.assertEqual(a['careers']['restaurant']['money'], money - comp)
        self.assertIn('compensation', cats(a['careers']['restaurant'], live['id']))
        self.assertTrue(a['careers']['restaurant']['happen']['last']['good'])
        b, _ = react(copy.deepcopy(s), 'restaurant', 'half')
        self.assertEqual(b['careers']['restaurant']['money'], money - comp // 2)
        s['careers']['restaurant']['happen']['live']['_roll'] = 99
        trust = s['careers']['restaurant']['incidents']['trust']
        d, _ = react(s, 'restaurant', 'refuse')
        cd = d['careers']['restaurant']
        self.assertEqual(cd['money'], money - comp * 120 // 100)
        self.assertLess(cd['incidents']['trust'], trust)
        self.assertTrue(any(p.get('happen') == live['id'] and p['stars'] == 1 for p in cd['feed']))

    def test_wallet_compensation_for_office(self):
        s = open_day('accounting', day=8)
        live = fire(s, 'accounting', 'coffee_laptop')
        wallet = s['journey']['wallet']
        s, _ = react(s, 'accounting', 'pay')
        self.assertEqual(s['journey']['wallet'], wallet - live['facts']['wallet'])


class NightAndPolice(unittest.TestCase):
    def test_break_in_found_at_opening(self):
        s = open_day('grocery', day=9)
        c = s['careers']['grocery']
        money = c['money']
        live = fire(s, 'grocery', 'night_shop')
        self.assertTrue(live['morning'])
        self.assertTrue(live['before'])
        self.assertLess(c['money'], money)            # already gone before you react
        pub = public_state(s)['careers']['grocery']['happen']['live']
        self.assertTrue(pub['before'] and pub['lines'])
        s, _ = react(s, 'grocery', 'report')
        c = s['careers']['grocery']
        self.assertEqual(len(c['happen']['cases']), 1)
        self.assertTrue(ledger_ok(c))

    def _case(self, solve, insured=False, camera=False):
        s = open_day('grocery', day=9)
        c = s['careers']['grocery']
        c['ops']['security']['insurance'] = insured
        if camera:
            c['ops']['security']['items'].append('camera')
        live = fire(s, 'grocery', 'grab_till', roll=99, _solve=solve)
        s, _ = react(s, 'grocery', 'camera' if camera else 'call')
        case = s['careers']['grocery']['happen']['cases'][0]
        return s, case

    def _next_day(self, s, days):
        for _ in range(days):
            s, _ = apply_action(s, 'grocery', 'end_day', {})
            c = s['careers']['grocery']
            c['happen']['plan'] = None
            s, r = apply_action(s, 'grocery', 'start_day', {})
            if s['careers']['grocery']['happen']['live']:
                s['careers']['grocery']['happen']['live'] = None
                s['careers']['grocery']['happen']['count'] = dict(day=0, n=0)
        return s

    def test_police_recover_the_money(self):
        s, case = self._case(0)
        self.assertGreater(case['fund'], 0)
        s = self._next_day(s, case['due'] - case['day'])
        c = s['careers']['grocery']
        self.assertFalse(c['happen']['cases'])
        news = c['happen']['news'][-1]
        self.assertEqual(news['outcome'], 'solved')
        self.assertIn('recovery', cats(c, case['id']))
        self.assertEqual(sum(x['amount'] for x in news['lines']), case['fund'])
        pub = public_state(s)['careers']['grocery']['happen']
        self.assertEqual(pub['news'][0]['title'], 'Công an phá án')
        s, _ = apply_action(s, 'grocery', 'hap_ack', {'id': case['id']})
        self.assertFalse(public_state(s)['careers']['grocery']['happen']['news'])
        self.assertTrue(ledger_ok(s['careers']['grocery']))

    def test_cold_case_with_insurance(self):
        s, case = self._case(99, insured=True)
        s = self._next_day(s, case['due'] - case['day'])
        c = s['careers']['grocery']
        news = c['happen']['news'][-1]
        self.assertEqual(news['outcome'], 'cold')
        self.assertEqual(news['insurance'], case['fund'] * hp.INSURANCE_PERCENT // 100)
        self.assertIn('insurance_recovery', cats(c, case['id']))
        self.assertNotIn('recovery', cats(c, case['id']))

    def test_cold_case_without_insurance_pays_nothing(self):
        s, case = self._case(99)
        s = self._next_day(s, case['due'] - case['day'])
        c = s['careers']['grocery']
        self.assertEqual(c['happen']['news'][-1]['outcome'], 'cold')
        self.assertFalse(cats(c, case['id']))

    def test_camera_helps_police(self):
        s, case = self._case(40, camera=True)
        self.assertTrue(case['camera'])
        s = self._next_day(s, case['due'] - case['day'])
        self.assertNotEqual(s['careers']['grocery']['happen']['news'][-1]['outcome'], 'cold')
        s2, case2 = self._case(40)
        s2 = self._next_day(s2, case2['due'] - case2['day'])
        self.assertEqual(s2['careers']['grocery']['happen']['news'][-1]['outcome'], 'cold')

    def test_recovered_stock_goes_back(self):
        from game import inventory
        s = open_day('grocery', day=9)
        live = fire(s, 'grocery', 'grab_shelf', roll=99, _solve=0)
        item, qty, _ = live['facts']['stock'][0]
        s, _ = react(s, 'grocery', 'call')
        after = inventory.count(s['careers']['grocery'], item)
        case = s['careers']['grocery']['happen']['cases'][0]
        s = self._next_day(s, case['due'] - case['day'])
        self.assertGreaterEqual(inventory.count(s['careers']['grocery'], item), min(after + qty, 60) - 20)
        self.assertTrue(s['careers']['grocery']['happen']['news'][-1]['items'])


class Saves(unittest.TestCase):
    def test_old_save_gains_book(self):
        s = open_day('grocery')
        old = copy.deepcopy(s)
        for c in old['careers'].values():
            c.pop('happen', None)
        m = migrate_state(old)
        validate_state(m)
        self.assertEqual(m['careers']['grocery']['happen'], hp.initial())

    def test_every_script_every_reaction_keeps_state_valid(self):
        for x in HAPPENINGS:
            career = x['careers'][0]
            s = open_day(career, day=12)
            s['careers'][career]['ops']['security']['items'].append('camera')
            fire(s, career, x['id'])
            for rid in x['reactions']:
                for roll in (0, 99):
                    t = copy.deepcopy(s)
                    t['careers'][career]['happen']['live']['_roll'] = roll
                    t, _ = react(t, career, rid)
                    validate_state(t)
                    self.assertTrue(ledger_ok(t['careers'][career]), (x['id'], rid))
                    pub = public_state(t)['careers'][career]['happen']
                    self.assertIsNotNone(pub['last'])

    def test_invalid_state_rejected(self):
        s = open_day('grocery', day=8)
        fire(s, 'grocery', 'grab_till')
        bad = copy.deepcopy(s)
        bad['careers']['grocery']['happen']['live']['_roll'] = 500
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(s)
        bad['careers']['grocery']['happen']['live']['script'] = 'nope'
        with self.assertRaises(GameError):
            validate_state(bad)


if __name__ == '__main__':
    unittest.main()
