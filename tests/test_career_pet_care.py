import copy
import json
import re
import unittest
from unittest import mock

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import pet_care as P
from tests.helpers import Journey


class Clock:
    def __init__(self):
        self.t = 8000.0

    def __call__(self):
        return self.t


def find(job, name=None, days=range(1, 40), case=None, mod=None):
    """First task of this kind; classic rows (case None) on calm days unless a case/modifier is asked for."""
    calm = [d for d in days if P.today(d)['id'] == (mod or 'steady')]
    for day in calm + ([] if mod else [d for d in days if d not in calm]):
        for slot in range(12):
            t = P.make_task(day, slot, 1)
            if (t['job'] == job and (name is None or t['needs'].get('name', t['needs'].get('family')) == name)
                    and t['_x'].get('case') == case):
                return day, slot
    raise AssertionError(f'no {job} task for {name}')


class PetCareTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    # ------------------------------------------------------------ helpers
    def journey(self, job, name=None):
        day, slot = find(job, name)
        j = Journey('pet_care', slot=slot, day=day)
        j.act('ask', task=j.task['id'])
        return j

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def crit(self, j, tid, key):
        return next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == key)

    def stock(self, j, item):
        return kit.stock(j.c, item)

    def pens(self, j):
        return j.c['ext']['data']['pens']

    def wash(self, j, shampoo='normal', rinse=9, dry=None, heat='warm'):
        j.act('pc_bath', shampoo=shampoo, temp=37)
        j.act('pc_rinse', mode='start')
        self.clock.t += rinse
        j.act('pc_rinse', mode='stop')
        j.act('pc_dry', mode='start', heat=heat)
        self.clock.t += dry if dry is not None else P.DRY_NEED[j.task['needs']['coat']]
        j.act('pc_dry', mode='stop')

    def hand(self, j, say=('done',)):
        tid = j.task['id']
        j.act('pc_report', say=list(say))
        j.act('pc_handover', confirm=True)
        return j.get(tid)

    # ------------------------------------------------------------ grooming
    def test_groom_happy_path_money_stock_review(self):
        j = self.journey('groom', 'Bông')
        tid = j.task['id']
        for part in ('scale', 'coat', 'skin', 'ears', 'nails', 'mood'):
            j.act('pc_inspect', part=part)
        money, towels, shampoo, cotton = j.c['money'], self.stock(j, 'towel'), self.stock(j, 'sh_normal'), self.stock(j, 'cotton')
        j.act('pc_brush', tool='brush')
        self.wash(j)
        self.assertEqual(j.task['g']['dry_pct'], 100)
        j.act('pc_nails', cut='short')
        j.act('pc_ears', how='clean')
        t = self.hand(j)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        price = P.SPEC['prices']
        self.assertEqual(j.c['money'] - money, price['groom_s'] + price['nails'] + price['ears'] + P.SPEC['tip'])   # perfect job: tip
        self.assertEqual(self.stock(j, 'sh_normal'), shampoo - 1)
        self.assertEqual(self.stock(j, 'towel'), towels - 1)
        self.assertEqual(self.stock(j, 'cotton'), cotton - 2)
        self.assertLess(t['g']['peak'], 60)
        self.assertEqual(self.review(j, tid)['stars'], 5)
        self.assertEqual(self.crit(j, tid, 'wish')['score'], 5)
        validate_state(json.loads(json.dumps(j.state)))

    def test_hidden_until_ask_and_inspect(self):
        day, slot = find('groom', 'Bơ')
        j = Journey('pet_care', slot=slot, day=day)
        tid = j.task['id']
        pub = next(t for t in public_state(j.state)['careers']['pet_care']['tasks'] if t['id'] == tid)
        self.assertIsNone(pub['needs'])
        self.assertNotIn('_x', pub)
        self.assertNotIn('"sensitive"', json.dumps(pub))
        with self.assertRaises(GameError):
            j.act('pc_inspect', part='scale')
        j.act('ask', task=tid)
        pub = next(t for t in public_state(j.state)['careers']['pet_care']['tasks'] if t['id'] == tid)
        self.assertEqual(pub['needs']['kg_said'], 11)
        self.assertNotIn('kg', pub['facts'])
        self.assertNotIn('skin', pub['facts'])
        j.act('pc_inspect', part='scale')
        j.act('pc_inspect', part='skin')
        pub = next(t for t in public_state(j.state)['careers']['pet_care']['tasks'] if t['id'] == tid)
        self.assertEqual(pub['facts']['kg'], 13)
        self.assertEqual(pub['facts']['skin'], 'sensitive')
        self.assertIn('13 kg', pub['found']['scale'])
        with self.assertRaises(GameError):
            j.act('pc_inspect', part='scale')
        with self.assertRaises(GameError):
            j.act('pc_inspect', part='vaccine')      # not part of a grooming intake

    def test_shampoo_rules_and_prescription(self):
        j = self.journey('groom', 'Bơ')
        j.act('pc_brush', tool='brush')
        r = j.act('pc_bath', shampoo='medicated', temp=37)
        self.assertTrue(r.get('refused'))
        self.assertIsNone(j.task['g']['shampoo'])
        self.assertEqual(j.task['mistakes'], 1)
        j.act('pc_bath', shampoo='normal', temp=37)
        self.assertTrue(j.task['g']['shampoo_bad'])
        self.assertEqual(j.task['mistakes'], 2)
        # A vet prescription: the owner's medicated shampoo, no shop stock used.
        j = self.journey('groom', 'Xám')
        before = {k: self.stock(j, k) for k in ('sh_normal', 'sh_puppy', 'sh_sensitive')}
        j.act('pc_bath', shampoo='sensitive', temp=37)
        self.assertEqual(j.task['mistakes'], 2)      # skipped brushing a matted coat + ignored the prescription
        j = self.journey('groom', 'Xám')
        j.act('pc_brush', tool='brush')
        j.act('pc_bath', shampoo='medicated', temp=37)
        self.assertEqual(j.task['mistakes'], 0)
        self.assertEqual({k: self.stock(j, k) for k in before}, before)
        with self.assertRaises(GameError):
            j.act('pc_bath', shampoo='sensitive', temp=37)

    def test_water_temperature_window(self):
        j = self.journey('groom', 'Bông')
        j.act('pc_brush', tool='brush')
        r = j.act('pc_bath', shampoo='normal', temp=43)
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['mistakes'], 1)
        self.assertIsNone(j.task['g']['shampoo'])
        with self.assertRaises(GameError):
            j.act('pc_bath', shampoo='normal', temp=80)
        with self.assertRaises(GameError):
            j.act('pc_bath', shampoo='normal', temp='37')
        stress = j.task['g']['stress']
        j.act('pc_bath', shampoo='normal', temp=33)
        self.assertTrue(j.task['g']['temp_bad'])
        self.assertEqual(j.task['mistakes'], 2)
        self.assertGreater(j.task['g']['stress'] - stress, P._r(P.STEP_STRESS['bath'] * P.STRESS_MULT['calm']))

    def test_rinse_dry_timers_residue_damp_and_safety(self):
        j = self.journey('groom', 'Bông')
        j.act('pc_brush', tool='brush')
        j.act('pc_bath', shampoo='normal', temp=37)
        with self.assertRaises(GameError):
            j.act('pc_dry', mode='start', heat='warm')       # rinse first
        j.act('pc_rinse', mode='start')
        with self.assertRaises(GameError):
            j.act('pc_nails', cut='tip')                      # wet, water running
        self.clock.t += 3
        r = j.act('pc_rinse', mode='stop')
        self.assertIn('xả thêm', r['message'].lower())
        r = j.act('pc_dry', mode='start', heat='hot')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['mistakes'], 1)
        j.act('pc_dry', mode='start', heat='warm')
        self.assertTrue(j.task['g']['residue'])
        self.assertEqual(j.task['mistakes'], 2)
        self.clock.t += 3
        j.act('pc_dry', mode='stop')
        self.assertEqual(j.task['g']['dry_pct'], 25)
        with self.assertRaises(GameError):
            j.act('pc_nails', cut='tip')                      # still damp
        j.act('pc_stop', confirm=True)
        t = self.hand(j, ('done', 'stopped'))
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 3)                    # hot dryer, residue, handed back damp
        tid = t['id']
        self.assertLess(self.crit(j, tid, 'coat')['score'], 4)

    def test_dark_nail_quick_honesty(self):
        for honest in (True, False):
            j = self.journey('groom', 'Bơ')
            tid = j.task['id']
            j.act('pc_brush', tool='brush')
            self.wash(j, shampoo='sensitive')
            self.assertGreaterEqual(j.task['g']['stress'], P.STRESS_STOP)
            with self.assertRaises(GameError):
                j.act('pc_nails', cut='short')                # too stressed
            j.act('pc_calm', how='voice')
            money, styptic = j.c['money'], self.stock(j, 'styptic')
            j.act('pc_nails', cut='short')
            self.assertTrue(j.task['g']['nick'])
            self.assertEqual(j.task['mistakes'], 1)
            j.act('pc_report', say=['done', 'nick'] if honest else ['done'])
            with self.assertRaises(GameError):
                j.act('pc_handover', confirm=True)            # still bleeding
            j.act('pc_styptic')
            self.assertEqual(self.stock(j, 'styptic'), styptic - 1)
            j.act('pc_handover', confirm=True)
            t = j.get(tid)
            price = P.SPEC['prices']
            full = price['groom_m'] + price['nails']          # never weighed: declared 11 kg is still medium
            if honest:
                self.assertEqual(t['mistakes'], 1)
                # The waived nail fee is folded into the owner's reaction: never both.
                self.assertEqual([x['code'] for x in t['slips']], ['nick'])
                self.assertEqual(j.c['money'] - money, min(price['groom_m'], full - t['reaction']['cut']))
                self.assertEqual(self.crit(j, tid, 'honesty')['score'], 5)
                self.assertLessEqual(self.review(j, tid)['stars'], 3)
            else:
                self.assertEqual(t['mistakes'], 2)
                self.assertEqual(t['reaction']['kind'], 'refuse')            # hidden injury: the owner does not pay
                self.assertEqual(j.c['money'] - money, 0)
                self.assertEqual(self.crit(j, tid, 'honesty')['score'], 1)

    def test_stress_gate_calm_and_stop(self):
        j = self.journey('groom', 'Mochi')
        tid = j.task['id']
        j.act('pc_brush', tool='brush')
        self.wash(j, shampoo='puppy')
        g = j.task['g']
        self.assertGreaterEqual(g['stress'], P.STRESS_STOP)
        self.assertEqual(g['dry_pct'], 100)
        with self.assertRaises(GameError):
            j.act('pc_nails', cut='tip')
        r = j.act('pc_muzzle')
        self.assertTrue(r.get('refused'))                     # never muzzle a cat
        self.assertEqual(j.task['mistakes'], 1)
        money = j.c['money']
        j.act('pc_stop', confirm=True)
        with self.assertRaises(GameError):
            j.act('pc_nails', cut='tip')
        t = self.hand(j, ('done', 'stopped'))
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(j.c['money'] - money, P.SPEC['prices']['groom_cat'])   # nails not done, not charged
        self.assertEqual(self.crit(j, tid, 'calm')['score'], 4)
        self.assertEqual(t['mistakes'], 1)

    def test_stop_must_be_reported(self):
        j = self.journey('groom', 'Mochi')
        j.act('pc_brush', tool='brush')
        j.act('pc_stop', confirm=True)
        t = self.hand(j, ('done',))
        self.assertEqual(t['mistakes'], 1)

    def test_muzzle_consent_and_bite(self):
        j = self.journey('groom', 'Vện')
        j.act('pc_inspect', part='coat')
        j.act('pc_brush', tool='brush')
        j.act('pc_brush', tool='flea')
        self.assertTrue(j.task['g']['flea'])
        self.wash(j, shampoo='normal')
        with self.assertRaises(GameError):
            j.act('pc_muzzle')                                # owner consent first
        r = j.act('pc_nails', cut='tip')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['g']['bites'], 1)
        self.assertIsNone(j.task['g']['nails'])
        j.act('pc_consent')
        j.act('pc_muzzle')
        j.act('pc_calm', how='voice')
        j.act('pc_nails', cut='tip')
        self.assertEqual(j.task['g']['nails'], 'tip')
        t = self.hand(j, ('done', 'vet_fleas'))
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 1)                    # the bite
        # A calm dog is never muzzled.
        j = self.journey('groom', 'Bông')
        with self.assertRaises(GameError):
            j.act('pc_consent')
        with self.assertRaises(GameError):
            j.act('pc_muzzle')

    def test_cat_towel_wrap(self):
        j = self.journey('groom', 'Xám')
        r = j.act('pc_nails', cut='tip')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['mistakes'], 1)
        towels = self.stock(j, 'towel')
        j.act('pc_calm', how='wrap')
        self.assertEqual(self.stock(j, 'towel'), towels - 1)
        j.act('pc_nails', cut='tip')
        self.assertEqual(j.task['g']['nails'], 'tip')
        j = self.journey('groom', 'Bông')
        with self.assertRaises(GameError):
            j.act('pc_calm', how='wrap')                      # towel wrap is for cats

    def test_sore_ears_referral_diagnosis_and_treats(self):
        j = self.journey('groom', 'Lu')
        tid = j.task['id']
        j.act('pc_inspect', part='body')
        j.act('pc_brush', tool='brush')
        self.wash(j)
        j.act('pc_ears', how='clean')
        self.assertTrue(j.task['g']['ears_hurt'])
        self.assertEqual(j.task['mistakes'], 1)
        j.act('pc_calm', how='treat')
        self.assertEqual(j.task['mistakes'], 2)               # owner said no treats
        t = self.hand(j, ('done', 'vet_ears', 'vet_lump'))
        self.assertEqual(t['mistakes'], 2)
        self.assertEqual(self.crit(j, tid, 'rules')['score'], 2)
        # Skip sore ears, but diagnose and forget the lump.
        j = self.journey('groom', 'Lu')
        j.act('pc_inspect', part='ears')
        j.act('pc_inspect', part='body')
        j.act('pc_brush', tool='brush')
        self.wash(j)
        j.act('pc_ears', how='skip')
        t = self.hand(j, ('done', 'vet_ears', 'diagnose'))
        self.assertEqual(t['mistakes'], 2)
        with self.assertRaises(GameError):
            P.handle(j.state, j.c, 'pc_report', {'say': ['nick']})    # finished task

    def test_report_validation(self):
        j = self.journey('groom', 'Bông')
        with self.assertRaises(GameError):
            j.act('pc_report', say=['vet_appetite'])          # a feeding-round statement
        with self.assertRaises(GameError):
            j.act('pc_report', say='done')
        with self.assertRaises(GameError):
            j.act('pc_report', say=['done', 'done'])
        with self.assertRaises(GameError):
            j.act('pc_handover', confirm=True)                # nothing done yet

    # ------------------------------------------------------------ boarding
    def test_board_happy_path(self):
        j = self.journey('board', 'Lu')
        tid = j.task['id']
        self.pens(j)['d3'] = None
        for part in ('vaccine', 'scale', 'mood', 'body'):
            j.act('pc_inspect', part=part)
        money = j.c['money']
        j.act('pc_pen', pen='d3')
        j.act('pc_plan', food='own', meals=2, grams=203, solo=False)
        j.act('pc_admit', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(j.c['money'] - money, 2 * P.SPEC['prices']['board_dog'] + P.SPEC['tip'])
        pen = self.pens(j)['d3']
        self.assertEqual((pen['pet'], pen['until'], pen['grams']), ('Lu', j.c['day'] + 2, 203))
        post = self.review(j, tid)
        self.assertEqual(post['feedback']['fair'] if post['feedback'].get('unfair') else post['stars'], 5)   # 1 in 6 reviewers misremember
        validate_state(json.loads(json.dumps(j.state)))

    def test_board_pen_rules(self):
        j = self.journey('board', 'Lu')
        self.pens(j)['d3'] = P._pet('Ki', 'dog', 32, 84, 9, 'Chú Sơn', 'own', 2, 240)
        with self.assertRaises(GameError):
            j.act('pc_pen', pen='d3')                          # occupied
        with self.assertRaises(GameError):
            j.act('pc_pen', pen='c1')                          # cat floor
        with self.assertRaises(GameError):
            j.act('pc_pen', pen='c3')                          # locked at level 1
        j.act('pc_inspect', part='scale')
        with self.assertRaises(GameError):
            j.act('pc_pen', pen='d1')                          # 30 kg in a small pen
        j.act('pc_inspect', part='vaccine')
        j.act('pc_refuse', reason='full', confirm=True)
        done = next(x for x in j.c['tasks'] if x['job'] == 'board')
        self.assertEqual(done['status'], 'referred')
        self.assertEqual(done['mistakes'], 0)

    def test_board_vaccine_lie(self):
        j = self.journey('board', 'Bơ')
        tid = j.task['id']
        j.act('pc_pen', pen='d2')
        j.act('pc_plan', food='house', meals=2, grams=130, solo=False)
        with self.assertRaises(GameError):
            j.act('pc_admit', confirm=True)                    # must see the vaccine book
        with self.assertRaises(GameError):
            j.act('pc_plan', food='own', meals=2, grams=130)   # owner brought no food
        j.act('pc_inspect', part='vaccine')
        pub = next(t for t in public_state(j.state)['careers']['pet_care']['tasks'] if t['id'] == tid)
        self.assertEqual(pub['facts']['vax'], 'expired')
        r = j.act('pc_admit', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.get(tid)['mistakes'], 1)
        money = j.c['money']
        j.act('pc_refuse', reason='vaccine', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'referred')
        self.assertEqual(j.c['money'], money)
        self.assertEqual(self.crit(j, tid, 'honesty')['score'], 5)
        self.assertIsNone(self.pens(j)['d2'])

    def test_board_cough_refuse_or_admit(self):
        j = self.journey('board', 'Bông')
        tid = j.task['id']
        j.act('pc_inspect', part='vaccine')
        j.act('pc_inspect', part='body')
        j.act('pc_refuse', reason='full', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(self.crit(j, tid, 'honesty')['score'], 2)
        j = self.journey('board', 'Bông')
        tid = j.task['id']
        j.act('pc_inspect', part='vaccine')
        j.act('pc_inspect', part='body')
        j.act('pc_refuse', reason='sick', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        # Not examining the body lets a coughing dog into the kennel: capped review.
        j = self.journey('board', 'Bông')
        tid = j.task['id']
        j.act('pc_inspect', part='vaccine')
        j.act('pc_pen', pen='d1')
        j.act('pc_plan', food='house', meals=2, grams=75)
        j.act('pc_admit', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['flags'], ['cough'])
        self.assertLessEqual(self.review(j, tid)['stars'], 2)

    def test_board_size_solo_and_portion(self):
        j = self.journey('board', 'Vện')
        tid = j.task['id']
        j.act('pc_inspect', part='vaccine')
        j.act('pc_pen', pen='d1')                              # declared 9 kg, really 12
        j.act('pc_plan', food='house', meals=2, grams=100)
        j.act('pc_admit', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['flags'], ['cramped', 'portion', 'solo'])
        self.assertEqual(t['mistakes'], 3)
        j = self.journey('board', 'Vện')
        tid = j.task['id']
        self.pens(j)['d3'] = None
        for part in ('vaccine', 'scale', 'mood'):
            j.act('pc_inspect', part=part)
        with self.assertRaises(GameError):
            j.act('pc_pen', pen='d1')
        j.act('pc_pen', pen='d3')
        j.act('pc_plan', food='house', meals=2, grams=P._portion('dog', 12, 60, 2) + 10, solo=True)   # within 10%
        j.act('pc_admit', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_board_allergy_and_meals(self):
        j = self.journey('board', 'Mochi')
        tid = j.task['id']
        j.act('pc_inspect', part='vaccine')
        j.act('pc_pen', pen='c2')
        j.act('pc_plan', food='house', meals=2, grams=22)
        j.act('pc_admit', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['flags'], ['meals', 'allergy'])
        self.assertEqual(t['mistakes'], 2)
        with self.assertRaises(GameError):
            j.act('pc_plan', food='house', meals=9, grams=10)

    # ------------------------------------------------------------ feeding rounds
    def test_feed_happy_path_binds_pen(self):
        j = self.journey('feed', 'Ki')
        tid = j.task['id']
        j.act('pc_inspect', part='bowl')
        self.assertEqual(j.get(tid)['pen'], 'd3')
        self.assertEqual(self.pens(j)['d3']['task'], tid)
        for part in ('energy', 'gait'):
            j.act('pc_inspect', part=part)
        bags, money = self.stock(j, 'poop_bag'), j.c['money']
        j.act('pc_feed', food='own', grams=240)
        j.act('pc_walk')
        self.assertEqual(self.stock(j, 'poop_bag'), bags - 1)
        t = self.hand(j)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(j.c['money'] - money, P.SPEC['prices']['care'] + P.SPEC['tip'])
        self.assertIsNone(self.pens(j)['d3']['task'])
        self.assertEqual(self.review(j, tid)['stars'], 5)

    def test_feed_warning_sign_and_waste(self):
        j = self.journey('feed', 'Mun')
        tid = j.task['id']
        j.act('pc_inspect', part='bowl')
        food = self.stock(j, 'cat_food')
        with self.assertRaises(GameError):
            j.act('pc_feed', food='own', grams=27)             # no food from the owner
        j.act('pc_feed', food='house', grams=27)
        self.assertEqual(self.stock(j, 'cat_food'), food - 1)
        with self.assertRaises(GameError):
            j.act('pc_walk')
        j.act('pc_litter')
        t = self.hand(j, ('done', 'vet_appetite'))
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(self.crit(j, tid, 'notice')['score'], 5)
        self.assertTrue(any(w['item'] == 'cat_food' and 'bỏ ăn' in w['reason'] for w in j.c['life']['waste']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_feed_mistakes(self):
        j = self.journey('feed', 'Sữa')
        tid = j.task['id']
        j.act('pc_inspect', part='body')
        j.act('pc_feed', food='house', grams=160)
        j.act('pc_treat')
        t = self.hand(j, ('done', 'diagnose'))
        self.assertEqual(t['mistakes'], 5)      # portion, treat on a diet, no walk, lump not reported, diagnosis
        self.assertEqual(self.crit(j, tid, 'care')['score'], 2)
        self.assertEqual(self.crit(j, tid, 'rules')['score'], 2)

    def test_walk_reveals_limp(self):
        j = self.journey('feed', 'Mực')
        j.act('pc_feed', food='house', grams=120)
        r = j.act('pc_walk')
        self.assertIn('khập khiễng', r['message'])
        self.assertIn('gait', j.task['inspected'])
        t = self.hand(j, ('done',))
        self.assertEqual(t['mistakes'], 1)

    def test_departures_on_start(self):
        j = Journey('pet_care')
        d = j.c['ext']['data']
        d['pens']['c2'] = P._pet('Tôm', 'cat', 3, 30, j.c['day'], 'Khách lẻ', 'house', 2, 22)
        d['pens']['d1'] = P._pet('Tép', 'dog', 5, 30, j.c['day'], 'Khách lẻ', 'house', 2, 63, task='pet_care-0001-99')
        P.on_start(j.state, j.c)
        self.assertIsNone(d['pens']['c2'])
        self.assertIsNotNone(d['pens']['d1'])               # still being cared for by an open task
        self.assertGreaterEqual(d['departed'], 1)

    # ------------------------------------------------------------ generic
    def test_wrong_job_action_rejected(self):
        j = self.journey('board', 'Lu')
        with self.assertRaises(GameError):
            j.act('pc_bath', shampoo='normal', temp=37)
        with self.assertRaises(GameError):
            j.act('pc_fly')
        with self.assertRaises(GameError):
            j.act('pc_inspect', part='bowl')

    def test_tampered_fixed_and_data_rejected(self):
        j = Journey('pet_care')
        s = copy.deepcopy(j.state)
        s['careers']['pet_care']['tasks'][0]['_x']['signs'] = []
        s['careers']['pet_care']['tasks'][0]['needs']['name'] = 'Hack'
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['pet_care']['ext']['data']['pens']['c2'] = P._pet('Vện', 'dog', 12, 60, 3, 'x', 'own', 2, 120)
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        t = next(x for x in s['careers']['pet_care']['tasks'] if x['job'] == 'groom')
        t['g']['stress'] = 400
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        t = next(x for x in s['careers']['pet_care']['tasks'] if x['job'] == 'groom')
        t['g']['muzzle'] = True
        with self.assertRaises(GameError):
            validate_state(s)

    def test_days_generate_valid_tasks(self):
        seen = set()
        for day in range(1, 15):
            for slot in range(12):
                t = P.make_task(day, slot, 3)
                self.assertEqual(t, P.make_task(day, slot, 3))
                self.assertEqual(json.loads(json.dumps(t)), t)
                seen.add(t['job'])
                if t['job'] == 'feed':
                    self.assertEqual(t['needs']['meals'], P.MEALS[t['needs']['stage']])
        self.assertEqual(seen, {'groom', 'board', 'feed', 'adopt'})

    def test_staff_assist(self):
        j = self.journey('board', 'Lu')
        msg = P.assist(j.state, j.c, dict(role='front'), j.task)
        self.assertIn('Sổ tiêm', msg)
        self.assertIn('vaccine', j.task['inspected'])
        j = self.journey('groom', 'Bông')
        msg = P.assist(j.state, j.c, dict(role='bather'), j.task)
        self.assertTrue(j.task['g']['brush'])
        j = self.journey('feed', 'Ki')
        j.act('pc_inspect', part='bowl')
        msg = P.assist(j.state, j.c, dict(role='kennel'), j.task)
        self.assertTrue(j.task['walked'])
        self.assertIsNone(P.assist(j.state, j.c, dict(role='front'), j.task))
        validate_state(j.state)

    def test_all_situations_playable(self):
        j = Journey('pet_care')
        self.assertTrue(5 <= len(P.SPEC['situations']) <= 8)
        for x in P.SPEC['situations']:
            self.assertEqual(len(x['facts']), 3)
            for opt in x['options']:
                self.assertGreaterEqual(len(opt['perspectives']), 2)
                self.assertTrue(set(opt.get('requires', [])) <= {f['id'] for f in x['facts']})
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_full_day_with_real_situation(self):
        j = Journey('pet_care')
        board = next(t for t in j.c['tasks'] if t['job'] == 'board')
        j.act('task_select', task=board['id'])
        j.act('ask', task=board['id'])
        j.act('pc_inspect', part='vaccine')
        j.act('pc_inspect', part='body')
        t = j.get(board['id'])
        reason = 'vaccine' if t['_x']['vax'] != 'valid' else 'sick' if 'cough' in t['_x']['signs'] else 'full'
        j.act('pc_refuse', reason=reason, confirm=True)
        self.assertIsNotNone(j.c['ext']['situation'])
        j.act('end_day')
        self.assertIn('staying', j.c['shift_summary']['career'])
        validate_state(json.loads(json.dumps(j.state)))


def pick(pred, days=range(1, 40)):
    for day in days:
        for slot in range(12):
            t = P.make_task(day, slot, 1)
            if pred(t):
                return day, slot
    raise AssertionError('no matching task')


class PetCareV2Tests(unittest.TestCase):
    """v0.5: body language, escapes, short-nosed breeds, hidden fevers, vaccine dates, medicine, adoption day, counter surprises."""

    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def at(self, day, slot, ask=True):
        j = Journey('pet_care', slot=slot, day=day)
        if ask:
            j.act('ask', task=j.task['id'])
        return j

    def gen(self, job, name, case=None, mod=None):
        return self.at(*find(job, name, case=case, mod=mod))

    def view(self, j):
        return next(v for v in public_state(j.state)['careers']['pet_care']['tasks'] if v['id'] == j.task['id'])

    def data(self, j):
        return j.c['ext']['data']

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def crit(self, j, tid, key):
        return next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == key)

    def ok(self, j):
        validate_state(json.loads(json.dumps(j.state)))

    def tamper(self, j, tid, fn):
        s = copy.deepcopy(j.state)
        fn(next(x for x in s['careers']['pet_care']['tasks'] if x['id'] == tid))
        return s

    def ok_shampoo(self, t):
        return next(sid for sid in P.SHAMPOO_INDEX if P._shampoo_verdict(t['needs'], t['_x'], sid)[0] == 'ok')

    # ------------------------------------------------------------ day, difficulty, generator
    def test_daily_modifier_is_deterministic_and_never_repeats(self):
        self.assertEqual(P.today(1)['id'], 'steady')
        seen = set()
        for d in range(1, 60):
            self.assertEqual(P.today(d), P.today(d))
            self.assertNotEqual(P.today(d)['id'], P.today(d + 1)['id'])
            if P.today(d)['id'] == 'adopt':
                self.assertGreaterEqual(d, 3)
            seen.add(P.today(d)['id'])
        self.assertEqual(seen, {x['id'] for x in P.TODAY})

    def test_new_tasks_are_marked_and_old_serials_use_the_old_generator(self):
        t = P.make_task(3, 2, 7)
        self.assertEqual(t['gen'], P.GEN)
        old = P.make_task(3, 2, kit.LEGACY_TURN + 7)
        self.assertNotIn('gen', old)
        self.assertEqual(old, P._make_v1(3, 2, kit.LEGACY_TURN + 7))

    def test_same_pet_never_twice_in_one_day(self):
        for d in range(1, 30):
            names = [(t['job'], t['needs'].get('name') or t['needs'].get('family')) for t in (P.make_task(d, sl, 1) for sl in range(8))]
            self.assertEqual(len(names), len(set(names)), (d, names))

    def test_no_owner_twice_in_one_day(self):
        for d in range(1, 121):
            tasks = [P.make_task(d, sl, 1) for sl in range(5)]
            self.assertEqual(len({t['npc'] for t in tasks}), 5, (d, [t['title'] for t in tasks]))
            pets = [t['needs'].get('name') or t['needs'].get('family') for t in tasks]
            self.assertEqual(len(pets), len(set(pets)), d)
        self.assertEqual(P.make_task(9, 3, 1), P.make_task(9, 3, 1))
        self.assertEqual(P.make_task(9, 20, 1)['career'], 'pet_care')     # slots past the plan still work

    def test_difficulty_grows_with_the_day(self):
        tpl = P.GROOMS2[0]
        a = P._groom_task2(1, 1, 1, tpl, 'steady')['g']['stress']
        b = P._groom_task2(12, 1, 1, tpl, 'steady')['g']['stress']
        self.assertEqual(b, min(60, a + 9))
        j = self.at(*pick(lambda t: t['needs'].get('today') == 'steady', range(12, 40)), ask=False)
        self.assertEqual(j.task['patience'], 88)
        j = self.at(*pick(lambda t: t['needs'].get('today') == 'holiday', range(12, 40)), ask=False)
        self.assertEqual(j.task['patience'], 80)
        j = self.at(*pick(lambda t: t['needs'].get('today') == 'steady', range(1, 3)), ask=False)
        self.assertEqual(j.task['patience'], 100)
        specials = lambda days: sum(1 for d in days for sl in range(1, 6) if P.make_task(d, sl, 1)['_x'].get('case'))
        self.assertLess(specials(range(1, 3)), specials(range(10, 12)))

    # ------------------------------------------------------------ reading the pet
    def test_stress_number_is_hidden_behind_body_language(self):
        j = self.gen('groom', 'Tia', 'escape')
        v = self.view(j)
        self.assertIsNone(v['g']['stress'])
        self.assertIsNone(v['g']['peak'])
        self.assertNotIn('_x', v)
        self.assertNotIn('runner', json.dumps(v))
        self.assertEqual(v['needs']['case'], 'escape')
        band = P._band(j.task['g']['stress'])
        self.assertEqual(len(v['cues']), 2)
        for cue in v['cues']:
            self.assertIn(cue, P.CUES['dog'][band] + [P.RUNNER_CUE])
        j.task['g']['stress'] = 70
        cues = self.view(j)['cues']
        self.assertIn(P.RUNNER_CUE, cues)
        self.assertTrue(set(cues) - {P.RUNNER_CUE} <= set(P.CUES['dog']['stressed']))
        with self.assertRaises(GameError):
            validate_state(self.tamper(j, j.task['id'], lambda t: t['g'].update(loop='yes')))

    def test_classic_tickets_keep_the_stress_number(self):
        j = self.at(1, 0, ask=False)
        s = copy.deepcopy(j.state)
        c = s['careers']['pet_care']
        old = P._make_v1(1, 0, 5)
        c['tasks'] = [old]
        c['active_task'] = old['id']
        validate_state(s)
        j.state = s
        j.act('ask', task=old['id'])
        self.assertEqual(old['job'], 'groom')
        self.assertIsInstance(self.view(j)['g']['stress'], int)
        self.assertNotIn('cues', self.view(j))

    def test_heat_day_makes_every_step_harder(self):
        j = self.at(*pick(lambda t: t['job'] == 'groom' and t['needs']['today'] == 'heat' and 'brush' in t['needs']['services']
                          and t['_x']['mood'] != 'bitey'))
        g, x = j.task['g'], j.task['_x']
        before = g['stress']
        j.act('pc_brush', tool='brush')
        want = P._r((P.STEP_STRESS['brush'] + (15 if x['matted'] else 0) + 5) * P.STRESS_MULT[x['mood']])
        self.assertEqual(j.task['g']['stress'], min(100, before + want))

    # ------------------------------------------------------------ escape attempts
    def bolted(self):
        j = self.gen('groom', 'Tia', 'escape')
        j.task['g']['stress'] = 60
        with mock.patch.dict(P.BOLT_P, runner=1.0):
            r = j.act('pc_brush', tool='brush')
        self.assertIn('nhảy khỏi bàn', r['message'])
        self.assertTrue(j.task['g']['bolt'])
        return j

    def test_runner_bolts_and_blocks_work_until_brought_back(self):
        j = self.bolted()
        for cmd, pl in (('pc_bath', dict(shampoo='normal', temp=37)), ('pc_loop', {}), ('pc_stop', dict(confirm=True)),
                        ('pc_handover', dict(confirm=True))):
            with self.assertRaises(GameError):
                j.act(cmd, **pl)
        with self.assertRaises(GameError):
            j.act('pc_catch', how='jump')
        stress, patience = j.task['g']['stress'], j.task['patience']
        j.act('pc_catch', how='corner')
        self.assertEqual(j.task['patience'], max(25, patience - P.CORNER_WAIT))
        g = j.task['g']
        self.assertFalse(g['bolt'])
        self.assertEqual((g['bolts'], g['stress']), (1, stress - 10))
        self.assertEqual((self.data(j)['bolts'], self.data(j)['day_bolts']), (1, 1))
        self.assertEqual(j.task['mistakes'], 0)
        with self.assertRaises(GameError):
            j.act('pc_catch', how='corner')
        self.ok(j)

    def test_grabbing_a_runaway_is_a_mistake(self):
        j = self.bolted()
        j.act('pc_catch', how='grab')
        self.assertTrue(j.task['g']['grabbed'])
        self.assertEqual(j.task['mistakes'], 1)
        self.ok(j)

    def test_lure_uses_a_treat(self):
        j = self.bolted()
        treats = kit.stock(j.c, 'treat')
        j.act('pc_catch', how='lure')
        self.assertEqual(kit.stock(j.c, 'treat'), treats - 1)
        self.assertEqual(j.task['g']['treats'], 1)

    def test_table_loop_prevents_the_escape(self):
        j = self.gen('groom', 'Tia', 'escape')
        j.act('pc_loop')
        with self.assertRaises(GameError):
            j.act('pc_loop')
        j.task['g']['stress'] = 60
        with mock.patch.dict(P.BOLT_P, runner=1.0):
            j.act('pc_brush', tool='brush')
        self.assertFalse(j.task['g']['bolt'])
        self.assertNotIn(P.RUNNER_CUE, self.view(j)['cues'])

    def test_calm_pets_only_bolt_on_later_days(self):
        fit = lambda t: t['job'] == 'groom' and 'brush' in t['needs']['services'] and not t['_x']['case']
        for (day, slot), bolt in ((pick(fit, range(1, 6)), False), (pick(fit, range(6, 40)), True)):
            j = self.at(day, slot)
            j.task['g']['stress'] = 76
            with mock.patch.dict(P.BOLT_P, other=1.0):
                j.act('pc_brush', tool='brush')
            self.assertEqual(j.task['g']['bolt'], bolt, day)

    def test_timers_can_stop_while_the_pet_runs(self):
        j = self.gen('groom', 'Tia', 'escape')
        j.act('pc_loop')
        j.act('pc_brush', tool='brush')
        j.act('pc_bath', shampoo='normal', temp=37)
        j.act('pc_rinse', mode='start')
        j.task['g']['bolt'] = True
        self.clock.t += 9
        j.act('pc_rinse', mode='stop')
        self.assertIsNone(j.task['g']['rinse'])

    # ------------------------------------------------------------ short-nosed breeds, humid days
    def test_short_nosed_breed_only_takes_the_cool_dryer(self):
        j = self.gen('groom', 'Mập', 'flat')
        tid = j.task['id']
        self.assertTrue(j.task['needs']['flat'])
        j.act('pc_bath', shampoo='sensitive', temp=37)
        j.act('pc_rinse', mode='start')
        self.clock.t += 9
        j.act('pc_rinse', mode='stop')
        r = j.act('pc_dry', mode='start', heat='warm')
        self.assertTrue(r.get('refused'))
        self.assertIn('mặt ngắn', r['message'])
        self.assertTrue(j.task['g']['breath'])
        self.assertIsNone(j.task['g']['dry'])
        self.assertEqual(j.task['mistakes'], 1)
        j.act('pc_dry', mode='start', heat='cool')
        self.clock.t += P.DRY_NEED['short'] * 1.5
        j.act('pc_dry', mode='stop')
        self.assertEqual(j.task['g']['dry_pct'], 100)
        j.act('pc_nails', cut='tip')
        j.act('pc_report', say=['done'])
        j.act('pc_handover', confirm=True)
        self.assertIn('mặt ngắn', self.crit(j, tid, 'gentle')['note'])
        self.ok(j)

    def test_rain_day_needs_longer_drying(self):
        j = self.at(*pick(lambda t: t['job'] == 'groom' and t['needs']['today'] == 'rain' and 'bath' in t['needs']['services']
                          and t['_x']['mood'] == 'calm' and not t['needs']['flat']))
        self.assertTrue(j.task['needs']['humid'])
        if 'brush' in j.task['needs']['services']:
            j.act('pc_brush', tool='brush')
        j.act('pc_bath', shampoo=self.ok_shampoo(j.task), temp=37)
        j.act('pc_rinse', mode='start')
        self.clock.t += 9
        j.act('pc_rinse', mode='stop')
        j.act('pc_dry', mode='start', heat='warm')
        self.clock.t += P.DRY_NEED[j.task['needs']['coat']]
        r = j.act('pc_dry', mode='stop')
        self.assertEqual(j.task['g']['dry_pct'], 66)
        self.assertIn('66%', r['message'])

    # ------------------------------------------------------------ boarding: hidden fever, vaccine dates
    def board_ready(self, j, pen):
        n = j.task['needs']
        self.data(j)['pens'][pen] = None
        j.act('pc_pen', pen=pen)
        meals = P.MEALS[n['stage']]
        j.act('pc_plan', food='house', meals=meals, grams=P._portion(n['species'], j.task['_x']['kg'], n['months'], meals), solo=False)

    def test_hidden_fever_found_only_with_the_thermometer(self):
        j = self.gen('board', 'Bắp', 'hidden')
        tid = j.task['id']
        self.assertIsNone(j.task['needs']['case'])
        self.assertNotIn('fever', self.view(j)['facts']['signs'])
        j.act('pc_inspect', part='vaccine')
        self.board_ready(j, 'd1')
        j.act('pc_admit', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertIn('fever', t['flags'])
        self.assertLessEqual(self.review(j, tid)['stars'], 2)
        self.ok(j)

    def test_thermometer_then_refuse_as_sick(self):
        j = self.gen('board', 'Bắp', 'hidden')
        tid = j.task['id']
        r = j.act('pc_inspect', part='temp')
        self.assertIn('39,8', r['message'])
        self.assertIn('fever', self.view(j)['facts']['signs'])
        j.act('pc_inspect', part='vaccine')
        self.board_ready(j, 'd1')
        r = j.act('pc_admit', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertNotEqual(j.get(tid)['status'], 'completed')
        j.act('pc_refuse', reason='sick', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'referred')
        self.assertNotIn('wrong_reason', t['flags'])
        self.assertEqual(self.data(j)['fevers'], 1)
        self.ok(j)

    def test_vaccine_must_last_until_pickup(self):
        j = self.gen('board', 'Ổi', 'vax_short')
        tid = j.task['id']
        day = j.task['day']
        r = j.act('pc_inspect', part='vaccine')
        self.assertIn(f'ngày {day + 1}', r['message'])
        self.assertEqual(self.view(j)['facts']['vax_until'], day + 1)
        self.board_ready(j, 'd3')
        r = j.act('pc_admit', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['mistakes'], 1)
        base = copy.deepcopy(j.state)
        j.act('pc_refuse', reason='vaccine', confirm=True)
        self.assertNotIn('wrong_reason', j.get(tid)['flags'])
        j.state = base
        j.act('pc_refuse', reason='sick', confirm=True)
        self.assertIn('wrong_reason', j.get(tid)['flags'])

    # ------------------------------------------------------------ medicine by the label
    def med_round(self, dose):
        j = self.gen('feed', 'Lu', 'med')
        tid = j.task['id']
        n = j.task['needs']
        self.assertTrue(n['med'])
        self.assertNotIn('dose', json.dumps(self.view(j)))
        with self.assertRaises(GameError):
            j.act('pc_med', dose='half')                  # with food, per the label
        j.act('pc_feed', food='own', grams=P._portion(n['species'], n['kg'], n['months'], n['meals']))
        with self.assertRaises(GameError):
            j.act('pc_handover', confirm=True)            # the morning dose is still due
        j.act('pc_med', dose=dose)
        with self.assertRaises(GameError):
            j.act('pc_med', dose=dose)
        j.act('pc_walk')
        j.act('pc_report', say=['done'])
        j.act('pc_handover', confirm=True)
        self.ok(j)
        return j, tid

    def test_medicine_right_dose(self):
        j, tid = self.med_round('half')
        self.assertEqual(j.get(tid)['mistakes'], 0)
        self.assertEqual(self.data(j)['meds'], 1)
        self.assertEqual(self.crit(j, tid, 'med')['score'], 5)

    def test_medicine_owner_says_more_but_the_label_wins(self):
        j, tid = self.med_round('one')
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(self.crit(j, tid, 'med')['score'], 1)
        self.assertLessEqual(self.review(j, tid)['stars'], 3)
        with self.assertRaises(GameError):
            validate_state(self.tamper(j, tid, lambda t: t.update(med='three')))

    # ------------------------------------------------------------ adoption day
    def test_adoption_fit_rules(self):
        want = {'Gia đình anh Tín': ['may'], 'Chị Quyên': ['may'], 'Ông bà Sáu': ['dom', 'tom'], 'Nhà bé Na': []}
        for f in P.FAMILIES:
            t = dict(needs=dict(candidates=f['candidates']), _x=dict(profile=f['profile']))
            self.assertEqual(P._fit_list(t), want[f['family']], f['family'])

    def adopt(self, family):
        return self.gen('adopt', family, 'adopt')

    def test_adoption_interview_then_the_right_pet(self):
        j = self.adopt('Gia đình anh Tín')
        tid = j.task['id']
        text = json.dumps(self.view(j), ensure_ascii=False)
        self.assertNotIn('profile', text)
        self.assertNotIn('tầng 9', text)
        with self.assertRaises(GameError):
            j.act('pc_match', pet='may', confirm=True)    # ask first
        for part in P.JOB_PARTS['adopt']:
            j.act('pc_inspect', part=part)
        self.assertIn('tầng 9', self.view(j)['found']['home'])
        with self.assertRaises(GameError):
            j.act('pc_match', pet='rex', confirm=True)
        money = j.c['money']
        r = j.act('pc_match', pet='may', confirm=True)
        self.assertTrue(r.get('celebrate'))
        self.assertGreaterEqual(j.c['money'] - money, P.SPEC['prices']['adopt'])
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual((self.data(j)['adopted'], self.data(j)['day_adopted']), (1, 1))
        self.assertEqual(self.crit(j, tid, 'match')['score'], 5)
        self.assertEqual(self.crit(j, tid, 'interview')['score'], 5)
        self.ok(j)

    def test_adoption_mismatch_comes_back_as_a_surprise(self):
        j = self.adopt('Gia đình anh Tín')
        tid = j.task['id']
        j.act('pc_inspect', part='home')
        j.act('pc_match', pet='dom', confirm=True)
        self.assertEqual(j.get(tid)['flags'], ['mismatch'])
        self.assertLessEqual(self.review(j, tid)['stars'], 2)
        desk = self.data(j)['desk']
        self.assertIn('adopt_bad', desk['marks'])
        pool = [x['id'] for x in kit._desk_pool('pet_care', j.c, desk, P.DESK, 'between', 'steady')]
        self.assertIn('return', pool)
        desk['ev'] = dict(id='desk-99', script='return', day=j.c['day'], at='between')
        j.act('pc_desk', option='take')
        self.assertNotIn('adopt_bad', self.data(j)['desk']['marks'])
        self.assertEqual(self.data(j)['returned'], 1)
        self.ok(j)

    def test_adoption_no_pet_when_the_family_is_allergic(self):
        j = self.adopt('Nhà bé Na')
        tid = j.task['id']
        r = j.act('pc_inspect', part='allergy')
        self.assertIn('hắt hơi', r['message'])
        r = j.act('pc_match', pet='none', confirm=True)
        self.assertTrue(r.get('celebrate'))
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes']), ('referred', 0))
        j = self.adopt('Gia đình anh Tín')
        tid = j.task['id']
        j.act('pc_inspect', part='home')
        j.act('pc_match', pet='none', confirm=True)
        self.assertEqual(j.get(tid)['flags'], ['turned_away'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        with self.assertRaises(GameError):
            validate_state(self.tamper(j, tid, lambda t: t.update(match='rex')))

    # ------------------------------------------------------------ counter surprises
    def desk_day(self):
        day, slot = pick(lambda t: t['job'] == 'groom' and not t['_x']['case'] and t['needs']['today'] == 'steady', range(2, 4))
        self.assertEqual(kit.desk_plan('pet_care', day), [2])
        return self.at(day, slot)

    def test_desk_surprise_blocks_work_until_decided(self):
        self.assertEqual(kit.desk_plan('pet_care', 1), [])
        j = self.desk_day()
        j.c['day_completed'] = 2
        r = j.act('pc_inspect', part='scale')
        self.assertTrue(r.get('surprise'), r)
        desk = self.data(j)['desk']
        with self.assertRaises(GameError) as ctx:
            j.act('pc_inspect', part='coat')
        self.assertEqual(ctx.exception.code, 'surprise_open')
        with self.assertRaises(GameError):
            j.act('pc_sanitize')
        view = public_state(j.state)['careers']['pet_care']['data']['desk']
        self.assertEqual(view['ev']['script'], desk['ev']['script'])
        for leak in ('luck', 'effects', 'good', 'outcome'):
            self.assertNotIn(leak, json.dumps(view['ev']))
        with self.assertRaises(GameError):
            j.act('pc_desk', option='nope')
        turn = j.c['turn']
        j.act('pc_desk', option=P.DESK_INDEX[desk['ev']['script']]['default'])
        self.assertEqual(j.c['turn'], turn)
        self.assertIsNone(self.data(j)['desk']['ev'])
        j.act('pc_inspect', part='coat')
        self.ok(j)

    def test_desk_options_are_shown_in_a_shuffled_order(self):
        j = self.desk_day()
        spots = set()
        for x in P.DESK:
            j.c['ext']['data']['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
            shown = public_state(j.state)['careers']['pet_care']['data']['desk']['ev']['options']
            self.assertEqual(sorted(o['id'] for o in shown), sorted(o['id'] for o in x['options']), x['id'])
            again = public_state(j.state)['careers']['pet_care']['data']['desk']['ev']['options']
            self.assertEqual([o['id'] for o in shown], [o['id'] for o in again], x['id'])
            good = [o['id'] for o in x['options'] if o.get('good')]
            if good:
                spots.add([o['id'] for o in shown].index(good[0]))
        self.assertGreater(len(spots), 1, 'the careful answer always sits in the same place')
        j.c['ext']['data']['desk']['ev'] = None

    def test_every_desk_option_applies_cleanly(self):
        j = self.desk_day()
        base = j.state
        self.assertGreaterEqual(len(P.DESK), 8)
        for x in P.DESK:
            self.assertGreaterEqual(len(x['options']), 2, x['id'])
            self.assertIn(x['default'], [o['id'] for o in x['options']])
            self.assertTrue(any(o.get('good') or (o.get('luck') and o['luck']['win'].get('good')) for o in x['options']), x['id'])
            for o in x['options']:
                j.state = copy.deepcopy(base)
                self.data(j)['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
                validate_state(j.state)
                r = j.act('pc_desk', option=o['id'])
                self.assertTrue(r['message'], (x['id'], o['id']))
                self.ok(j)
        j.state = base

    def test_vet_inspection_reads_the_sanitation_log(self):
        j = self.desk_day()
        base = copy.deepcopy(j.state)
        ev = lambda: dict(id='desk-99', script='inspect', day=j.c['day'], at='between')
        self.data(j)['desk']['ev'] = ev()
        money = j.c['money']
        r = j.act('pc_desk', option='log')
        self.assertIn('phạt 15', r['message'])
        self.assertEqual(j.c['money'], money - 15)
        j.state = copy.deepcopy(base)
        j.act('pc_sanitize')
        with self.assertRaises(GameError):
            j.act('pc_sanitize')
        self.assertTrue(public_state(j.state)['careers']['pet_care']['data']['sanitized_today'])
        self.data(j)['desk']['ev'] = ev()
        xp, money = j.c['xp'], j.c['money']
        r = j.act('pc_desk', option='log')
        self.assertIn('đạt', r['message'])
        self.assertEqual((j.c['xp'] - xp, j.c['money']), (10, money))
        j.state = copy.deepcopy(base)
        self.data(j)['desk']['ev'] = ev()
        r = j.act('pc_desk', option='clean')
        self.assertIn('đạt', r['message'])
        self.assertEqual(self.data(j)['sanitize_day'], j.c['day'])

    def test_desk_choices_leave_marks_that_bring_follow_ups(self):
        j = self.desk_day()
        pool = lambda mod='steady': [x['id'] for x in kit._desk_pool('pet_care', j.c, self.data(j)['desk'], P.DESK, 'between', mod)]
        self.assertNotIn('sneeze', pool())
        self.assertNotIn('itch', pool())
        self.assertNotIn('heat', pool())
        self.assertIn('heat', pool('heat'))
        self.data(j)['desk']['ev'] = dict(id='desk-98', script='stray', day=j.c['day'], at='between')
        j.act('pc_desk', option='mix')
        self.assertIn('sneeze', pool())
        self.data(j)['desk']['ev'] = dict(id='desk-99', script='rep', day=j.c['day'], at='between')
        shampoo = kit.stock(j.c, 'sh_normal')
        j.act('pc_desk', option='buy')
        self.assertGreater(kit.stock(j.c, 'sh_normal'), shampoo)
        self.assertIn('itch', pool())
        self.assertNotIn('rep', pool())

    # ------------------------------------------------------------ saves, close, text
    def test_old_save_keeps_old_tickets_and_gains_new_fields(self):
        j = self.at(1, 0, ask=False)
        s = copy.deepcopy(j.state)
        c = s['careers']['pet_care']
        old = P._make_v1(1, 0, 5)
        c['tasks'] = [old]
        c['active_task'] = old['id']
        d = c['ext']['data']
        for k in list(P.DATA_V2) + ['desk']:
            d.pop(k)
        validate_state(s)
        t = c['tasks'][0]
        self.assertGreaterEqual(t['created_turn'], kit.LEGACY_TURN)
        self.assertNotIn('gen', t)
        self.assertEqual(P.make_task(1, 0, t['created_turn']), P._make_v1(1, 0, t['created_turn']))
        self.assertIn('desk', d)
        self.assertEqual(d['bolts'], 0)
        validate_state(json.loads(json.dumps(s)))
        j.state = s
        j.act('ask', task=old['id'])
        j.act('pc_inspect', part='mood')
        self.assertIn('desk', public_state(j.state)['careers']['pet_care']['data'])

    def test_close_summary_lists_the_day(self):
        j = Journey('pet_care')
        board = next(t for t in j.c['tasks'] if t['job'] == 'board')
        j.act('task_select', task=board['id'])
        j.act('ask', task=board['id'])
        j.act('pc_inspect', part='vaccine')
        j.act('pc_refuse', reason='full', confirm=True)
        j.act('end_day')
        lines = j.c['shift_summary']['career']['lines']
        self.assertIn('Hôm nay xong 1 việc.', lines)
        self.assertEqual(j.c['ext']['data']['day_done'], 0)
        nxt = P.today(j.c['day'])                                        # closing moved to the next day: its market is announced
        self.assertTrue(lines[-1].startswith('Dự báo ngày mai: ') and nxt['title'] in lines[-1], lines)

    def test_public_data_shows_the_day(self):
        j = self.desk_day()
        d = public_state(j.state)['careers']['pet_care']['data']
        self.assertEqual(d['mod']['id'], P.today(j.c['day'])['id'])
        self.assertEqual(d['tier'], kit.tier(j.c['day']))
        self.assertIn('ev', d['desk'])

    def test_text_never_assumes_the_groomers_gender(self):
        texts = json.dumps([P.GROOMS2, P.BOARDS2, P.FEEDS2, P.FAMILIES, P.ADOPTEES, P.DESK, P.RULES, P.CUES, P.CATCH, P.TODAY,
                            P.SPEC['situations'], P.CASES], ensure_ascii=False)
        for bad in ('Chị chủ', 'chị chủ', 'anh chủ', 'cô chủ', 'rồi anh', 'nha anh', 'anh tin em'):
            self.assertNotIn(bad, texts)
        self.assertFalse(re.search(r'trong game|của game|người chơi|NPC|mô phỏng|giả lập', texts))
        for d in range(1, 12):
            for sl in range(6):
                t = P.make_task(d, sl, 1)
                self.assertFalse(re.search(r'\b(anh|chị) ơi\b', t['opening']), t['opening'])


class PetCareConsequenceTests(unittest.TestCase):
    """Làm sai thì phải chịu: what the owner finds at pick-up costs stars and money, in proportion."""

    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def journey(self, job, name, case=None):
        day, slot = find(job, name, case=case)
        j = Journey('pet_care', slot=slot, day=day)
        j.act('ask', task=j.task['id'])
        return j

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def fair(self, j, tid):
        post = self.review(j, tid)
        return post['feedback'].get('fair') or post['stars']

    def calm(self, j):
        while j.task['g']['stress'] >= 50:
            j.act('pc_calm', how='break')

    def groom(self, j, shampoo=None, temp=37, scald=False, nails=None):
        """Brush → bath → rinse → dry → nails → ears, calming between steps, then an honest report."""
        t = j.task
        n, x = t['needs'], t['_x']
        for part in P.JOB_PARTS['groom']:
            j.act('pc_inspect', part=part)
        self.calm(j)
        j.act('pc_brush', tool='brush')
        self.calm(j)
        sid = shampoo or next(k for k in P.SHAMPOO_INDEX if P._shampoo_verdict(n, x, k)[0] == 'ok')
        if scald:
            j.act('pc_bath', shampoo=sid, temp=43)
        j.act('pc_bath', shampoo=sid, temp=temp)
        self.calm(j)
        j.act('pc_rinse', mode='start')
        self.clock.t += 9
        j.act('pc_rinse', mode='stop')
        self.calm(j)
        j.act('pc_dry', mode='start', heat='warm')
        self.clock.t += P.DRY_NEED[n['coat']] + 0.5
        j.act('pc_dry', mode='stop')
        if 'nails' in n['services']:
            self.calm(j)
            j.act('pc_nails', cut=nails or ('short' if n['short_nails'] and x['nails'] == 'clear' else 'tip'))
        if 'ears' in n['services']:
            self.calm(j)
            j.act('pc_ears', how='skip' if 'ears' in x['signs'] else 'clean')
        j.act('pc_report', say=['done'] + ['vet_' + s for s in x['signs'] if s != 'cough'])
        money = j.c['money']
        r = j.act('pc_handover', confirm=True)
        return j.get(t['id']), j.c['money'] - money, r

    def board(self, j, grams=None, pen=None, food=None, parts=('vaccine', 'scale', 'mood', 'body')):
        t = j.task
        n, x = t['needs'], t['_x']
        j.c['ext']['data']['pens']['d3'] = None
        for part in parts:
            j.act('pc_inspect', part=part)
        j.act('pc_pen', pen=pen or 'd3')
        meals = P.MEALS[n['stage']]
        j.act('pc_plan', food=food or ('own' if n['food_own'] else 'house'), meals=meals,
              grams=grams or P._portion(n['species'], x['kg'], n['months'], meals), solo=x['mood'] == 'dog_aggressive')
        money = j.c['money']
        r = j.act('pc_admit', confirm=True)
        return j.get(t['id']), j.c['money'] - money, r

    def test_right_work_pays_in_full_without_slips(self):
        j = self.journey('groom', 'Bông')
        t, paid, r = self.groom(j)
        price = P.SPEC['prices']
        self.assertEqual(t.get('slips') or [], [])
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertEqual(paid, price['groom_s'] + price['nails'] + price['ears'] + P.SPEC['tip'])
        self.assertGreaterEqual(self.review(j, t['id'])['stars'], 4)
        self.assertTrue(r.get('celebrate'))

    def test_wrong_shampoo_on_a_cat_costs_stars_and_money(self):
        j = self.journey('groom', 'Mochi')
        t, paid, r = self.groom(j, shampoo='normal')
        self.assertEqual([x['code'] for x in t['slips']], ['shampoo'])
        self.assertLessEqual(self.review(j, t['id'])['stars'], 3)
        self.assertIn('sữa tắm cho chó', self.review(j, t['id'])['text'])
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        self.assertEqual(paid, P.SPEC['prices']['groom_cat'] + P.SPEC['prices']['nails'] - t['reaction']['cut'])
        self.assertGreater(t['reaction']['cut'], 0)
        self.assertIn('sữa tắm cho chó', r['message'])
        self.assertFalse(r.get('celebrate'))
        validate_state(json.loads(json.dumps(j.state)))

    def test_wrong_pen_and_portion_on_boarding(self):
        j = self.journey('board', 'Vện')
        t, paid, r = self.board(j, pen='d1', grams=60, parts=('vaccine', 'mood'))   # never weighed: 12 kg in a 10 kg pen, half the chart
        self.assertEqual(sorted(x['code'] for x in t['slips']), ['cramped', 'portion'])
        self.assertLessEqual(self.fair(j, t['id']), 2)
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        self.assertEqual(paid, P.SPEC['prices']['board_dog'] - t['reaction']['cut'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_owner_food_ignored_is_a_small_slip(self):
        j = self.journey('board', 'Lu')
        t, paid, r = self.board(j, food='house')
        self.assertEqual(t['flags'], ['food'])
        self.assertEqual([(x['code'], x['sev']) for x in t['slips']], [('food', 1)])
        self.assertLessEqual(self.fair(j, t['id']), 4)
        self.assertIn('hạt quen', self.review(j, t['id'])['text'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_severity_scales_the_stars(self):
        stars = {}
        for label, kw in (('small', dict(temp=33)), ('clear', dict(shampoo='normal')), ('safety', dict(scald=True))):
            j = self.journey('groom', 'Bơ')
            t, paid, r = self.groom(j, **kw)
            stars[label] = self.fair(j, t['id'])
        self.assertEqual(stars['small'], 4)
        self.assertLessEqual(stars['clear'], 3)
        self.assertEqual(stars['safety'], 1)
        self.assertGreater(stars['small'], stars['clear'])
        self.assertGreater(stars['clear'], stars['safety'])

    def test_scald_is_safety_critical(self):
        j = self.journey('groom', 'Bông')
        t, paid, r = self.groom(j, scald=True)
        self.assertTrue(t['scald'])
        self.assertEqual([x['code'] for x in t['slips']], ['scald'])
        self.assertEqual(self.review(j, t['id'])['stars'], 1)
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(paid, 0)
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertTrue(j.c['incidents']['follow'])
        self.assertIn('bỏng', r['message'])
        validate_state(json.loads(json.dumps(j.state)))
        s = copy.deepcopy(j.state)
        next(x for x in s['careers']['pet_care']['tasks'] if x['id'] == t['id'])['scald'] = 'yes'
        with self.assertRaises(GameError):
            validate_state(s)

    def test_medicine_overdose_and_allergen_are_safety_critical(self):
        j = self.journey('feed', 'Lu', case='med')
        tid = j.task['id']
        n = j.task['needs']
        j.act('pc_feed', food='own', grams=P._portion(n['species'], n['kg'], n['months'], n['meals']))
        j.act('pc_med', dose='two')
        j.act('pc_walk')
        j.act('pc_report', say=['done'])
        money = j.c['money']
        j.act('pc_handover', confirm=True)
        t = j.get(tid)
        self.assertTrue(t['slips'][0]['safety'])
        self.assertEqual((t['reaction']['kind'], j.c['money'] - money), ('refuse', 0))
        self.assertEqual(self.review(j, tid)['stars'], 1)
        self.assertTrue(j.c['incidents']['follow'])
        j = self.journey('board', 'Mochi')
        t, paid, r = self.board(j, pen='c2', food='house')
        self.assertIn('allergy', t['flags'])
        self.assertEqual((t['reaction']['kind'], paid), ('refuse', 0))
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_no_double_charge(self):
        j = self.journey('feed', 'Ki')
        tid = j.task['id']
        j.act('pc_feed', food='house', grams=240)              # the owner sent Ki's own food
        j.act('pc_walk')
        j.act('pc_report', say=['done'])
        money = j.c['money']
        j.act('pc_handover', confirm=True)
        t = j.get(tid)
        price = P.SPEC['prices']['care']
        self.assertEqual(j.c['money'] - money, price - t['reaction']['cut'])
        after = j.c['money']
        from game import consequences as cq
        again = cq.react(j.state, j.c, t, price, who='x')
        self.assertEqual(again['kind'], t['reaction']['kind'])
        self.assertEqual(j.c['money'], after)
        with self.assertRaises(GameError):
            j.act('pc_handover', task=tid, confirm=True)
        self.assertEqual(j.c['money'], after)
        validate_state(json.loads(json.dumps(j.state)))

    def test_turning_away_a_healthy_pet_is_named_but_moves_no_money(self):
        j = self.journey('board', 'Lu')
        tid = j.task['id']
        j.c['ext']['data']['pens']['d3'] = None
        j.act('pc_inspect', part='vaccine')
        money = j.c['money']
        r = j.act('pc_refuse', reason='full', confirm=True)
        t = j.get(tid)
        self.assertEqual([x['code'] for x in t['slips']], ['turned_away'])
        self.assertEqual(j.c['money'], money)
        self.assertIn('khỏe mạnh', r['message'])
        self.assertLessEqual(self.fair(j, tid), 3)
        validate_state(json.loads(json.dumps(j.state)))

    def test_stopping_for_a_panicking_pet_is_not_a_skip(self):
        j = self.journey('groom', 'Mochi')
        tid = j.task['id']
        j.act('pc_brush', tool='brush')
        j.act('pc_bath', shampoo='puppy', temp=37)
        j.act('pc_rinse', mode='start')
        self.clock.t += 9
        j.act('pc_rinse', mode='stop')
        j.act('pc_dry', mode='start', heat='warm')
        self.clock.t += P.DRY_NEED['short']
        j.act('pc_dry', mode='stop')
        self.assertGreaterEqual(j.task['g']['peak'], 70)
        j.act('pc_stop', confirm=True)
        j.act('pc_report', say=['done', 'stopped'])
        j.act('pc_handover', confirm=True)
        self.assertEqual(j.get(tid).get('slips') or [], [])
        # Stopping a calm pet only to skip the paid services is a clear mistake.
        j = self.journey('groom', 'Bông')
        tid = j.task['id']
        j.act('pc_brush', tool='brush')
        j.act('pc_stop', confirm=True)
        j.act('pc_report', say=['done', 'stopped'])
        j.act('pc_handover', confirm=True)
        self.assertEqual([x['code'] for x in j.get(tid)['slips']], ['skipped'])
        self.assertLessEqual(self.fair(j, tid), 3)


if __name__ == '__main__':
    unittest.main()
