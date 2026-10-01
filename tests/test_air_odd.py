"""Chuyện oái oăm of the air crew (game/careers/air_odd.py): the scripts, how the other side decides from hidden
traits and the player's own answer, the conduct ladder up to cách chức, harassment reports, bargains with the
office, fatigue and rest days, the pilot's rain and squalls, and saves (old data, mid-encounter, forged answers)."""
import copy
import json
import re
import unittest

from tests.helpers import Journey
from tests.test_career_pilot import best_answer, quiet, settle_odd, sky_answer
from game.careers import PLUGINS, air_odd as ao
from game.careers.air_odd_content import CABIN, PILOT
from game.engine import GameError, public_state, validate_state

PL = PLUGINS.get('pilot')
FA = PLUGINS.get('flight_attendant')
ROUGH = re.compile(r'\b(địt|đụ|đéo|lồn|cặc|buồi|đĩ)\b', re.I)   # rude banter is fine; the crude words are not


def journey(career, day=4):
    j = Journey(career, slot=0, day=day)
    j.act('pl_intro' if career == 'pilot' else 'fa_intro')
    quiet(j)
    return j


def open_ev(j, sid):
    odd = ao.ensure(j.c['ext']['data'])
    odd['seq'] += 1
    odd['ev'] = dict(id=f'odd-{odd["seq"]}', script=sid, day=j.c['day'], at='between', said=[])
    return odd


def cmd(j):
    return 'pl_odd' if j.career == 'pilot' else 'fa_odd'


class Scripts(unittest.TestCase):
    def test_every_script_is_well_formed(self):
        ids = [x['id'] for x in PILOT + CABIN]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(PILOT), 25)
        self.assertGreaterEqual(len(CABIN), 25)
        for scripts in (PILOT, CABIN):
            marks = {x['follow'] for x in scripts if x.get('follow')}
            for x in scripts:
                self.assertIn(x['kind'], ao.KINDS, x['id'])
                self.assertIn(x['rank'], ao.RANKS, x['id'])
                self.assertGreaterEqual(len(x['push']), 2, x['id'])
                self.assertTrue(x['text'] and x['title'] and x['emoji'] and x['who'], x['id'])
                self.assertLessEqual(set(x.get('words', {})), set(ao.WORDS[x['kind']]), x['id'])
                self.assertIn(x.get('at', 'between'), ('open', 'between', 'any'))
                if x.get('need_mark'):
                    self.assertIn(x['need_mark'], marks, x['id'])
                if x['kind'] == 'bargain':
                    self.assertTrue(0 <= x['limit'] < x['ask'] and x['unit'], x['id'])
                lines = [x.get(k) for k in ('text', 'back', 'give', 'report', 'stuck', 'lawful', 'penalty')] + list(x['push'])
                for line in lines:
                    self.assertFalse(line and ROUGH.search(line), (x['id'], line))

    def test_each_career_has_every_kind_of_trouble(self):
        self.assertLessEqual({'charm', 'harass', 'demand', 'corner', 'bargain'}, {x['kind'] for x in PILOT})
        self.assertLessEqual({'charm', 'harass', 'demand', 'corner', 'bargain'}, {x['kind'] for x in CABIN})
        self.assertGreaterEqual(sum(x['kind'] == 'harass' for x in CABIN), 6)
        self.assertGreaterEqual(sum(x['kind'] == 'charm' for x in PILOT), 5)
        self.assertLessEqual({'pax', 'crew', 'boss', 'kin'}, {x['rank'] for x in PILOT})
        self.assertLessEqual({'pax', 'crew', 'boss', 'kin'}, {x['rank'] for x in CABIN})

    def test_no_encounter_on_the_first_day_and_a_few_later(self):
        self.assertEqual(ao.plan('pilot', 1), [])
        self.assertEqual(ao.plan('pilot', 2), [1])
        for d in range(4, 30):
            self.assertTrue(1 <= len(ao.plan('flight_attendant', d)) <= 3)
            self.assertEqual(ao.plan('pilot', d), ao.plan('pilot', d))


class Answers(unittest.TestCase):
    def setUp(self):
        if PL is None or FA is None:
            raise unittest.SkipTest('air careers filtered out')

    def test_the_same_answers_end_the_same(self):
        outs = []
        for _ in range(2):
            j = journey('pilot')
            open_ev(j, 'pl-bar')
            r1 = j.act('pl_odd', tone='soft', say=['duty'], to='self')
            r2 = j.act('pl_odd', tone='soft', say=['joke'], to='self') if j.c['ext']['data']['odd']['ev'] else {}
            outs.append((r1['message'], r2.get('message'), j.c['ext']['data']['odd']['last']))
        self.assertEqual(outs[0], outs[1])

    def test_hidden_traits_decide_how_long_they_push(self):
        # The same soft answer: someone gives up at once, someone keeps pushing (rolled from the encounter id).
        seen = set()
        for seq in range(1, 40):
            j = journey('pilot')
            odd = ao.ensure(j.c['ext']['data'])
            odd['seq'] = seq
            open_ev(j, 'pl-note')
            j.act('pl_odd', tone='soft', say=['duty'], to='self')
            seen.add(j.c['ext']['data']['odd']['ev'] is None)
        self.assertEqual(seen, {True, False})

    def test_declining_is_rewarded_and_giving_in_never(self):
        j = journey('pilot')
        xp = j.c['xp']
        open_ev(j, 'pl-wife')
        j.act('pl_odd', tone='firm', say=['no', 'rule'], to='self')
        settle_odd(j, 'pl_odd', PL.ODD)
        last = j.c['ext']['data']['odd']['last']
        self.assertIn(last['how'], ('back', 'report'))
        self.assertTrue(last['good'])
        self.assertGreater(j.c['xp'], xp)
        for sid in [x['id'] for x in PILOT if x['kind'] in ('charm', 'corner')]:
            j = journey('pilot')
            xp = j.c['xp']
            open_ev(j, sid)
            r = j.act('pl_odd', tone='soft', say=['yes'], to='self')
            last = j.c['ext']['data']['odd']['last']
            self.assertEqual(last['how'], 'give')
            self.assertFalse(last['good'])
            self.assertFalse(r.get('celebrate'))
            self.assertEqual(j.c['xp'], xp)
            self.assertGreaterEqual(j.c['ext']['data']['odd']['conduct']['points'], 2)

    def test_later_keeps_the_door_ajar(self):
        j = journey('pilot')
        open_ev(j, 'pl-bar')
        for _ in range(3):
            if not j.c['ext']['data']['odd']['ev']:
                break
            j.act('pl_odd', tone='soft', say=['later'], to='self')
        self.assertEqual(j.c['ext']['data']['odd']['last']['how'], 'stuck')
        self.assertGreaterEqual(j.c['ext']['data']['odd']['conduct']['points'], 3)

    def test_reporting_harassment_always_works_and_the_victim_is_never_punished(self):
        for sid in [x['id'] for x in CABIN if x['kind'] == 'harass']:
            j = journey('flight_attendant')
            open_ev(j, sid)
            r = j.act('fa_odd', tone='soft', say=['no'], to='company')
            last = j.c['ext']['data']['odd']['last']
            self.assertEqual((last['how'], last['good']), ('report', True), sid)
            self.assertIn('🛡️', r['message'])
            j = journey('flight_attendant')
            open_ev(j, sid)
            j.act('fa_odd', tone='soft', say=['yes'], to='self')
            odd = j.c['ext']['data']['odd']
            self.assertEqual(odd['last']['how'], 'give')
            self.assertIsNone(odd['last']['good'])
            self.assertEqual(odd['conduct']['points'], 0)

    def test_an_unreported_harasser_comes_back_and_a_report_ends_it(self):
        j = journey('flight_attendant')
        open_ev(j, 'fa-3c')
        for _ in range(3):
            if j.c['ext']['data']['odd']['ev']:
                j.act('fa_odd', tone='soft', say=['joke'], to='self')
        odd = j.c['ext']['data']['odd']
        self.assertIn('fa-3c-back', odd['marks'])
        pool = ao._pool(j.c, odd, CABIN, 'between')
        self.assertIn('fa-3c-back', [x['id'] for x in pool])
        open_ev(j, 'fa-3c-back')
        j.act('fa_odd', tone='firm', say=['stop'], to='company')
        self.assertNotIn('fa-3c-back', j.c['ext']['data']['odd']['marks'])

    def test_bringing_in_the_crew_helps_with_passengers(self):
        wins = 0
        for seq in range(1, 20):
            j = journey('flight_attendant')
            ao.ensure(j.c['ext']['data'])['seq'] = seq
            open_ev(j, 'fa-drunk')
            j.act('fa_odd', tone='firm', say=['stop', 'rule'], to='crew')
            wins += j.c['ext']['data']['odd']['ev'] is None
        self.assertEqual(wins, 19)

    def test_snapping_at_a_polite_passenger_sours_it_and_at_an_angry_one_makes_it_worse(self):
        j = journey('flight_attendant')
        odd = open_ev(j, 'fa-window')                      # bà Chín: always polite
        j.act('fa_odd', tone='sharp', say=['rule', 'no'], to='self')
        settle_odd(j, 'fa_odd', FA.ODD)
        self.assertIsNone(j.c['ext']['data']['odd']['last']['good'])
        j = journey('flight_attendant')
        odd = open_ev(j, 'fa-rude')                        # always hot
        j.act('fa_odd', tone='sharp', say=['no'], to='self')
        self.assertIsNotNone(j.c['ext']['data']['odd']['ev'])
        out = ao._play('flight_attendant', ao.script(CABIN, 'fa-rude'), j.c['ext']['data']['odd']['ev'], 0)
        self.assertTrue(out['dig'])
        self.assertIsNotNone(odd)

    def test_family_can_only_be_handled_yourself(self):
        j = journey('pilot')
        open_ev(j, 'pl-mom')
        with self.assertRaises(GameError):
            j.act('pl_odd', tone='soft', say=['rule'], to='company')
        view = public_state(j.state)['careers']['pilot']['data']['odd']['ev']
        self.assertEqual([c['id'] for c in view['channels']], ['self'])

    def test_answers_are_checked(self):
        j = journey('pilot')
        open_ev(j, 'pl-vip')
        for bad in (dict(tone='loud', say=['no'], to='self'), dict(tone='firm', say=[], to='self'),
                    dict(tone='firm', say=['no', 'no'], to='self'), dict(tone='firm', say=['stop'], to='self'),
                    dict(tone='firm', say=['no', 'rule', 'alt'], to='self')):
            with self.assertRaises(GameError):
                j.act('pl_odd', **bad)
        with self.assertRaises(GameError):
            j.act('pl_fuel', task=j.c['active_task'], kg=100)     # the encounter holds everything else

    def test_the_public_view_never_shows_the_traits(self):
        j = journey('pilot')
        open_ev(j, 'pl-skip')
        view = public_state(j.state)['careers']['pilot']['data']['odd']['ev']
        json.dumps(view)
        self.assertNotIn('persist', json.dumps(view))
        self.assertEqual(view['round'], 1)
        self.assertEqual(len(view['words']), len(ao.WORDS['corner']))


class Discipline(unittest.TestCase):
    def setUp(self):
        if PL is None:
            raise unittest.SkipTest('pilot filtered out')

    def give(self, j, sid='pl-bar'):
        open_ev(j, sid)
        return j.act('pl_odd', tone='soft', say=['yes'], to='self')

    def test_the_ladder_up_to_cach_chuc(self):
        j = journey('pilot')
        r = self.give(j)
        self.assertIn('nhắc nhở', r['message'])
        self.give(j, 'pl-dm')
        self.assertEqual(ao.level(j.c['ext']['data']['odd']['conduct']['points'])[1], 'ground')
        tid = j.c['active_task']
        j.act('ask', task=tid)
        with self.assertRaises(GameError) as e:
            j.act('pl_fuel', task=tid, kg=j.get(tid)['needs']['fuel']['need'])
        self.assertEqual(e.exception.code, 'grounded')
        r = self.give(j, 'pl-note')
        self.assertIn('cách chức', r['message'])
        cd = j.c['ext']['data']['odd']['conduct']
        self.assertTrue(cd['demoted'])
        view = public_state(j.state)['careers']['pilot']['data']['odd']['conduct']
        self.assertEqual((view['level'], view['ground'], view['demoted']), ('demote', True, True))
        validate_state(json.loads(json.dumps(j.state)))

    def test_demoted_crew_fly_for_no_bonus_and_clean_work_restores_the_rank(self):
        j = journey('pilot')
        odd = ao.ensure(j.c['ext']['data'])
        odd['conduct'].update(points=5, demoted=True)
        self.assertEqual(ao.bonus(odd, PL.BONUS), 0)
        notes = [ao.flown(odd, True, PL.CFG) for _ in range(9)]
        self.assertFalse(odd['conduct']['demoted'])
        self.assertTrue(any('phục chức' in n for n in notes))
        self.assertEqual(ao.bonus(odd, PL.BONUS), PL.BONUS)

    def test_a_grounded_day_ends_with_the_day(self):
        j = journey('pilot')
        ao.ensure(j.c['ext']['data'])['conduct'].update(points=6, ground=j.c['day'])
        self.assertTrue(ao.grounded(j.c, j.c['ext']['data']['odd']))
        j.act('end_day')
        j.act('start_day')
        self.assertFalse(ao.grounded(j.c, j.c['ext']['data']['odd']))


class Bargains(unittest.TestCase):
    def setUp(self):
        if FA is None:
            raise unittest.SkipTest('flight_attendant filtered out')

    def test_the_rule_and_the_union_hold_the_line(self):
        j = journey('flight_attendant')
        money = j.c['money']
        open_ev(j, 'fa-kpi')
        x = ao.script(CABIN, 'fa-kpi')
        j.act('fa_odd', tone='firm', say=['rule'], to='company', n=x['limit'])
        odd = j.c['ext']['data']['odd']
        self.assertEqual((odd['last']['how'], odd['last']['good']), ('deal', True))
        self.assertEqual(j.c['money'], money + x['limit'] * x['pay'])
        self.assertEqual(odd['fatigue'], x['limit'] * x['tire'])

    def test_taking_everything_pays_and_tires(self):
        j = journey('flight_attendant')
        open_ev(j, 'fa-kpi')
        j.act('fa_odd', tone='soft', say=['yes'], to='self', n=0)
        odd = j.c['ext']['data']['odd']
        self.assertEqual(odd['last']['how'], 'give')
        self.assertFalse(odd['last']['good'])
        self.assertEqual(odd['fatigue'], 4)
        self.assertEqual(ao.bonus(odd, FA.BONUS), FA.BONUS // 2)

    def test_refusing_everything_without_a_reason_can_cost_the_bonus(self):
        outs = set()
        for seq in range(1, 16):
            j = journey('flight_attendant', day=8)
            ao.ensure(j.c['ext']['data'])['seq'] = seq
            money = j.c['money']
            open_ev(j, 'fa-gym')
            for _ in range(3):
                if j.c['ext']['data']['odd']['ev']:
                    j.act('fa_odd', tone='sharp', say=['alt'], to='self', n=0)
            last = j.c['ext']['data']['odd']['last']
            outs.add(last['how'])
            if last['how'] == 'penalty':
                self.assertLess(j.c['money'], money)
                self.assertIn('strained', j.c['ext']['data']['odd']['marks'])
        self.assertIn('penalty', outs)

    def test_a_penalty_never_takes_more_than_the_wallet(self):
        j = journey('flight_attendant')
        j.c['money'] = 3
        odd = ao.ensure(j.c['ext']['data'])
        ao._money({}, j.c, 0, {'title': 'x'}, 'r')          # no-op
        open_ev(j, 'fa-sales')
        x = ao.script(CABIN, 'fa-sales')
        out = dict(how='penalty', n=0, sour=False, dig=False, later=0, sharp_boss=False)
        ao._resolve(j.state, j.c, 'flight_attendant', odd, x, out, FA.CFG)
        self.assertEqual(j.c['money'], 0)


class Rest(unittest.TestCase):
    def setUp(self):
        if PL is None:
            raise unittest.SkipTest('pilot filtered out')

    def test_rest_is_asked_once_a_day_even_before_the_shift(self):
        j = journey('pilot')
        j.act('end_day')
        odd = ao.ensure(j.c['ext']['data'])
        odd['fatigue'] = 5
        r = j.act('pl_rest', n=2, say=['rule'], to='company')
        self.assertIn('duyệt', r['message'])
        self.assertLessEqual(j.c['ext']['data']['odd']['fatigue'], 3)
        with self.assertRaises(GameError):
            j.act('pl_rest', n=1, say=['health'], to='self')

    def test_the_legal_minimum_rest_cannot_be_refused(self):
        j = journey('pilot')
        odd = ao.ensure(j.c['ext']['data'])
        odd['fatigue'] = 4
        odd['marks']['strained'] = 1
        j.act('pl_rest', n=1, say=['rule'], to='self')
        self.assertEqual(j.c['ext']['data']['odd']['fatigue'], 2)

    def test_a_fresh_crew_asking_for_family_on_a_busy_day_hears_no(self):
        j = journey('pilot')
        r = j.act('pl_rest', n=2, say=['family'], to='self')
        self.assertIn('Đơn bị trả về', r['message']) if PL._pressure(j.c, j.c['ext']['data']) else self.assertTrue(r['message'])


class Sky(unittest.TestCase):
    def setUp(self):
        if PL is None:
            raise unittest.SkipTest('pilot filtered out')

    def to_sky(self, pick=lambda sk: True):
        from tests.test_career_pilot import Base
        b = Base()
        b.j = None
        for day in range(2, 60):
            for slot in range(0, 5):
                t = PL.make_task(day, slot, 1)
                if t['kind'] not in ('flight', 'tech') or t['needs']['wx'] in ('storm', 'fog') or t['needs']['event']:
                    continue
                j = Journey('pilot', slot=slot, day=day)
                j.act('pl_intro')
                quiet(j)
                tid = j.c['active_task']
                if j.get(tid)['kind'] != t['kind']:
                    continue
                b.brief(j, tid)
                b.walk(j, tid)
                b.start(j, tid)
                sk = j.c['ext']['data']['sky']
                if sk and pick(sk):
                    return j, tid, sk
        self.fail('no hop with that weather')

    def test_rain_waits_for_the_approach_setup(self):
        j, tid, sk = self.to_sky()
        with self.assertRaises(GameError):
            j.act('pl_gate', task=tid)
        view = public_state(j.state)['careers']['pilot']['data']['sky']
        self.assertIn(view['braking'], PL.BRAKING.values())
        r = j.act('pl_sky', task=tid, **sky_answer(sk))
        self.assertTrue(r.get('celebrate'))
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_landing_on_a_poor_runway_is_a_safety_slip(self):
        j, tid, sk = self.to_sky(lambda sk: sk['brake'] == 'poor')
        conf = dict(sky_answer(sk), go='land')
        j.act('pl_sky', task=tid, **conf)
        self.assertTrue(j.get(tid)['slips'][-1]['safety'])
        self.assertEqual(j.get(tid)['slips'][-1]['code'], 'sky_poor')

    def test_poor_braking_goes_to_the_alternate(self):
        j, tid, sk = self.to_sky(lambda sk: sk['brake'] == 'poor')
        j.act('pl_sky', task=tid, **sky_answer(sk))
        t = j.get(tid)
        self.assertEqual(t['at'], t['needs']['leg']['alt'])
        self.assertEqual(t['mistakes'], 0)

    def test_turning_into_the_cell_is_unsafe(self):
        j, tid, sk = self.to_sky(lambda sk: sk['cell'])
        j.act('pl_sky', task=tid, **dict(sky_answer(sk), dodge=sk['cell']))
        self.assertIn('sky_cell', [x['code'] for x in j.get(tid)['slips']])

    def test_no_wipers_and_no_gust_margin_are_small_slips(self):
        j, tid, sk = self.to_sky(lambda sk: sk['gust'] >= 10 and sk['brake'] != 'poor')
        j.act('pl_sky', task=tid, **dict(sky_answer(sk), wipers=False, add=0))
        codes = [x['code'] for x in j.get(tid)['slips']]
        self.assertIn('wipers', codes)
        self.assertIn('vref', codes)
        validate_state(json.loads(json.dumps(j.state)))


class Saves(unittest.TestCase):
    def setUp(self):
        if PL is None or FA is None:
            raise unittest.SkipTest('air careers filtered out')

    def test_data_from_before_gains_a_clean_record(self):
        for career in ('pilot', 'flight_attendant'):
            j = Journey(career, day=3)
            d = j.c['ext']['data']
            d.pop('odd', None)
            d.pop('sky', None)
            st = json.loads(json.dumps(j.state))
            validate_state(st)
            odd = st['careers'][career]['ext']['data']['odd']
            self.assertEqual(odd['conduct'], ao.initial()['conduct'])

    def test_a_save_in_the_middle_of_an_encounter_round_trips(self):
        j = journey('flight_attendant')
        open_ev(j, 'fa-vip')
        j.act('fa_odd', tone='soft', say=['duty'], to='self')
        if j.c['ext']['data']['odd']['ev']:
            st = json.loads(json.dumps(j.state))
            validate_state(st)
            forged = copy.deepcopy(st)
            forged['careers']['flight_attendant']['ext']['data']['odd']['ev']['said'][0]['say'] = ['yes', 'hack']
            with self.assertRaises(GameError):
                validate_state(forged)

    def test_a_week_with_encounters_stays_valid(self):
        for career, cmd_ in (('pilot', 'pl_odd'), ('flight_attendant', 'fa_odd')):
            j = Journey(career)
            j.act('pl_intro' if career == 'pilot' else 'fa_intro')
            seen = 0
            for _ in range(6):
                j.act('end_day')
                j.act('start_day')
                odd = j.c['ext']['data']['odd']
                seen += odd['ev'] is not None or bool(odd['plan'])
                settle_odd(j, cmd_, PL.ODD if career == 'pilot' else FA.ODD)
                validate_state(json.loads(json.dumps(j.state)))
            self.assertGreater(seen, 0)


if __name__ == '__main__':
    unittest.main()
