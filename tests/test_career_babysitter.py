"""Bảo mẫu trông trẻ (plugin career babysitter): one family's child for the day, block by block: the arrival
(hands, the note, the greeting, the bag), meals from the kitchen counter (allergy, age, preparation), play that
fits the mood (small parts, screens), the room sweep, the nap (routine, pats in time with the breath), small
moments on a calm meter (first aid in order), the honest day log and the day's pay (rate, care bonus, loyalty,
tip), cô Tâm's apprenticeship, the schedule clock, determinism, save validation, old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, PLUGINS
from game.content import initial_career, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from game.feedback import PERSONAS

BM = PLUGINS.get('babysitter')


class Clock:
    def __init__(self):
        self.t = 9000.0

    def __call__(self):
        return self.t


def find(kind, days=range(1, 60), pred=None):
    """(day, slot) of the first block of this kind (and matching pred)."""
    for day in days:
        for slot, (k, _) in enumerate(BM.plan_of(day)):
            if k == kind:
                t = make_task('babysitter', day, slot, 1)
                if pred is None or pred(t):
                    return day, slot
    raise AssertionError(f'no {kind}')


class Base(unittest.TestCase):
    def setUp(self):
        if BM is None:
            raise unittest.SkipTest('babysitter is filtered out by MNL_CAREERS')
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, learning=False):
        """One block on its own (the note already read)."""
        self.j = Journey('babysitter', slot=slot, day=day)
        d = BM._data(self.j.c)
        d['intro'] = True
        d['learn']['done'] = not learning
        if not learning:
            d['stats']['days'] = BM.APPRENTICE
        BM._today(self.j.c, d)['note'] = 1
        return self.j.task

    def fam(self, t):
        return BM.fam(t['needs']['fam'])

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}

    # ------------------------------------------------ doing a block well
    def good_plate(self, t):
        f, n = self.fam(t), t['needs']
        for g in n['groups']:
            ok = [x for x in n['menu'] if BM.FOODS[x]['group'] == g and f['allergy'] not in BM.FOODS[x]['al']
                  and not (BM.young(f) and BM.FOODS[x]['hard'])]
            if BM.mod_of(t['day'])['id'] == 'sniffle' and g == 'drink':
                ok = ['nuoc']
            self.j.act('bm_food', task=t['id'], food=ok[0])
            if BM._needs_prep(f, ok[0]):
                self.j.act('bm_prep', task=t['id'], food=ok[0])

    def pat_at(self, tid, phase):
        st = self.j.get(tid)['st']
        self.clock.t = st['pat'] + BM.CYCLE * 7 + BM.CYCLE * phase
        return self.j.act('bm_pat', task=tid, tap_at=self.clock.t)

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('bm_desk', option=kit.desk_script(BM.DESK, ev['script'])['default'])

    def block(self, t):
        """Do one block the careful way."""
        tid, n, f = t['id'], t['needs'], self.fam(t)
        self.settle_desk()
        k = t['kind']
        if k == 'arrive':
            self.j.act('bm_wash', task=tid)
            self.j.act('bm_note', task=tid)
            self.j.act('bm_greet', task=tid, greet=BM.TEMPERS[f['temper']][2])
            self.j.act('bm_bag', task=tid)
            self.j.act('bm_ask', task=tid, item=n['missing'])
            return self.j.act('bm_take', task=tid)
        if k in ('snack', 'meal'):
            self.good_plate(t)
            self.j.act('bm_kidwash', task=tid)
            self.j.act('bm_seat', task=tid)
            return self.j.act('bm_serve', task=tid)
        if k == 'play':
            a = next(x for x in n['acts'] if n['mood'] in BM.ACTS[x]['fits'] and not BM.ACTS[x]['screen']
                     and not (BM.ACTS[x]['small'] and BM.young(f)))
            self.j.act('bm_play', task=tid, act=a)
            for b in n['beats']:
                self.j.act('bm_beat', task=tid, opt=next(o[0] for o in BM.BEATS[b][1] if o[2] == 2))
            self.j.act('bm_tidy', task=tid)
            return self.j.act('bm_play_done', task=tid)
        if k == 'safety':
            for x in BM.hazards(t):
                self.j.act('bm_check', task=tid, item=x)
            return self.j.act('bm_safe_done', task=tid)
        if k == 'nap':
            self.j.act('bm_nap', task=tid, step='potty')
            self.j.act('bm_nap', task=tid, step='dark')
            self.j.act('bm_lovey', task=tid, item=f['lovey'])
            self.j.act('bm_nap', task=tid, step='song')
            for _ in range(BM.SLEEP_PATS):
                self.pat_at(tid, 0.7)
            return self.j.act('bm_nap_done', task=tid)
        if k == 'moment':
            mk = n['mk']
            moves = BM.SCRAPE_ORDER + ['hug'] if mk == 'scrape' else [m for m in n['moves'] if BM.MOVES[mk][m][3] is None]
            for m in moves:
                if self.j.get(tid)['st']['calm'] >= 100:
                    break
                self.j.act('bm_care', task=tid, move=m)
            return self.j.act('bm_moment_done', task=tid)
        for lid, _, true, _ in BM.log_lines(self.j.c):
            if true and lid != 'fine':
                self.j.act('bm_log', task=tid, line=lid)
        return self.j.act('bm_hand', task=tid)

    def play_day(self):
        for _ in range(20):
            t = next((t for t in self.j.c['tasks'] if t['day'] == self.j.c['day'] and t['status'] not in ('completed', 'cancelled')), None)
            if t is None:
                break
            self.block(t)
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        validate_state(self.j.state)
        return r


class Spec(Base):
    def test_spec_shape(self):
        s = BM.SPEC
        self.assertEqual(s['id'], 'babysitter')
        self.assertEqual(s['prefix'], 'bm_')
        self.assertTrue(s['wait'])
        for p in BM.PEOPLE:
            self.assertIn(p[3], PERSONAS)
        for name in list(BM.NO_TICK) + list(BM.PHYSICAL):
            self.assertTrue(name in BM.ACTIONS or name in ('bm_intro', 'bm_desk'), name)
        self.assertEqual(set(BM.ACTIONS), (set(BM.NO_TICK) | set(BM.PHYSICAL)) - {'bm_intro', 'bm_desk'})
        json.dumps(BM.content(), ensure_ascii=False)

    def test_families_and_content_agree(self):
        for fid, f in BM.FAMILIES.items():
            self.assertIn(f['band'], BM.BANDS)
            self.assertIn(f['temper'], BM.TEMPERS)
            self.assertIn(f['lovey'], BM.LOVEYS)
            self.assertIn(f['allergy'], list(BM.ALLERGENS) + [None])
            self.assertIn(f['likes'], BM.FOODS)
            self.assertIn(f['home'], BM.HOMES)
            self.assertIn(fid, BM.FAM_STORY)
        for k, x in BM.FOODS.items():
            self.assertIn(x['group'], BM.GROUPS, k)
            self.assertTrue(set(x['al']) <= set(BM.ALLERGENS), k)
            self.assertIn(x['prep'], [None, *BM.PREP], k)
        for mk, moves in BM.MOVES.items():
            self.assertGreaterEqual(sum(v[2] for v in moves.values() if v[2] > 0), 100, mk)
        self.assertEqual(set(BM.MOVES['scrape']) & set(BM.SCRAPE_ORDER), set(BM.SCRAPE_ORDER))

    def test_tasks_are_deterministic_and_the_day_is_a_schedule(self):
        for day in range(1, 50):
            plan = BM.plan_of(day)
            self.assertEqual(plan[0][0], 'arrive')
            self.assertEqual(plan[-1], ('handover', BM.CLOSE))
            self.assertLess(len(plan), 12)
            self.assertEqual([m for _, m in plan], sorted(m for _, m in plan), day)
            for slot in range(len(plan)):
                a, b = make_task('babysitter', day, slot, 1), make_task('babysitter', day, slot, 9)
                self.assertEqual({k: v for k, v in a.items() if k != 'created_turn'}, {k: v for k, v in b.items() if k != 'created_turn'})
                self.assertEqual(json.loads(json.dumps(a['needs'])), a['needs'])
                self.assertEqual(a['kind'], plan[slot][0])
        self.assertEqual(BM.family_of(1), 'bin')
        self.assertGreaterEqual(len({BM.family_of(d) for d in range(1, 30)}), 5)

    def test_every_meal_can_be_served_safely_and_has_a_trap(self):
        traps = 0
        for day in range(1, 60):
            for slot, (k, _) in enumerate(BM.plan_of(day)):
                if k not in ('snack', 'meal'):
                    continue
                t = make_task('babysitter', day, slot, 1)
                f = BM.fam(t['needs']['fam'])
                for g in t['needs']['groups']:
                    safe = [x for x in t['needs']['menu'] if BM.FOODS[x]['group'] == g and f['allergy'] not in BM.FOODS[x]['al']
                            and not (BM.young(f) and BM.FOODS[x]['hard'])]
                    self.assertTrue(safe, (day, slot, g))
                traps += any(f['allergy'] in BM.FOODS[x]['al'] or (BM.young(f) and BM.FOODS[x]['hard']) for x in t['needs']['menu'])
        self.assertGreater(traps, 10)

    def test_desk_scripts_and_situations_are_well_formed(self):
        for x in BM.DESK:
            self.assertIn(x['default'], [o['id'] for o in x['options']])
        for x in BM.SITUATIONS:
            self.assertEqual(len(x['options']), 3)
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng')
        text = json.dumps([BM.DESK, BM.SITUATIONS, BM.INTRO, BM.LESSONS, BM.CATCH, BM.FAM_STORY], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, text)


class Arrive(Base):
    def test_a_careful_arrival(self):
        t = self.at(1, 0)
        r = self.block(t)
        self.assertTrue(r.get('celebrate'))
        self.assertEqual(self.j.get(t['id'])['status'], 'completed')
        self.assertFalse(self.codes(t['id']))

    def test_the_note_comes_before_any_other_block(self):
        t = self.at(*find('play'))
        BM._today(self.j.c, self.d)['note'] = 0
        with self.assertRaises(GameError):
            self.j.act('bm_play', task=t['id'], act=t['needs']['acts'][0])

    def test_skipping_steps_is_named(self):
        t = self.at(1, 0)
        self.j.act('bm_note', task=t['id'])
        self.j.act('bm_greet', task=t['id'], greet='grab')
        self.j.act('bm_take', task=t['id'])
        self.assertEqual(self.codes(t['id']), {'wash', 'greet', 'bag'})

    def test_asking_for_what_is_in_the_bag(self):
        t = self.at(1, 0)
        with self.assertRaises(GameError):
            self.j.act('bm_ask', task=t['id'], item=t['needs']['missing'])
        self.j.act('bm_bag', task=t['id'])
        other = next(x for x in t['needs']['bag'] if x != t['needs']['missing'])
        r = self.j.act('bm_ask', task=t['id'], item=other)
        self.assertFalse(r['correct'])
        r = self.j.act('bm_ask', task=t['id'], item=t['needs']['missing'])
        self.assertTrue(r['correct'])


class Meals(Base):
    def test_a_safe_plate(self):
        t = self.at(*find('meal'))
        r = self.block(t)
        self.assertFalse(self.codes(t['id']))
        self.assertTrue(r['celebrate'])
        self.assertTrue(self.d['today']['food'])

    def test_the_allergy_is_on_the_label(self):
        t = self.at(*find('snack', pred=lambda t: any(BM.FAMILIES[t['needs']['fam']]['allergy'] in BM.FOODS[x]['al'] for x in t['needs']['menu'])))
        f = self.fam(t)
        bad = next(x for x in t['needs']['menu'] if f['allergy'] in BM.FOODS[x]['al'])
        self.good_plate(t)
        self.j.act('bm_food', task=t['id'], food=next(x for x in self.j.get(t['id'])['st']['plate'] if BM.FOODS[x]['group'] == BM.FOODS[bad]['group']))
        self.j.act('bm_food', task=t['id'], food=bad)
        self.j.act('bm_kidwash', task=t['id'])
        self.j.act('bm_seat', task=t['id'])
        self.j.act('bm_serve', task=t['id'])
        self.assertIn('allergy', self.codes(t['id']))
        self.assertTrue(BM.cq.safety(self.j.get(t['id'])))
        self.assertEqual(self.d['today']['oops'], f['allergy'])
        self.assertEqual(self.d['today']['safe_slip'], 1)

    def test_young_children_need_food_prepared(self):
        t = self.at(*find('meal', pred=lambda t: BM.FAMILIES[t['needs']['fam']]['band'] in BM.YOUNG))
        f = self.fam(t)
        for g in t['needs']['groups']:
            pick = next(x for x in t['needs']['menu'] if BM.FOODS[x]['group'] == g and f['allergy'] not in BM.FOODS[x]['al']
                        and not BM.FOODS[x]['hard'] and (BM.FOODS[x]['prep'] or g == 'drink'))
            self.j.act('bm_food', task=t['id'], food=pick)
        self.j.act('bm_kidwash', task=t['id'])
        self.j.act('bm_seat', task=t['id'])
        self.j.act('bm_serve', task=t['id'])
        self.assertIn('prep', self.codes(t['id']))

    def test_prep_only_what_needs_it(self):
        t = self.at(*find('snack'))
        plain = next(x for x in t['needs']['menu'] if not BM.FOODS[x]['prep'])
        self.j.act('bm_food', task=t['id'], food=plain)
        with self.assertRaises(GameError):
            self.j.act('bm_prep', task=t['id'], food=plain)


class Play(Base):
    def test_play_that_fits_the_mood(self):
        t = self.at(*find('play'))
        self.block(t)
        self.assertFalse(self.codes(t['id']))
        self.assertGreaterEqual(self.j.get(t['id'])['st']['joy'], 90)

    def test_small_parts_are_for_big_children(self):
        t = self.at(*find('play', pred=lambda t: BM.FAMILIES[t['needs']['fam']]['band'] in BM.YOUNG))
        small = next(x for x in t['needs']['acts'] if BM.ACTS[x]['small'])
        self.j.act('bm_play', task=t['id'], act=small)
        for b in t['needs']['beats']:
            self.j.act('bm_beat', task=t['id'], opt=BM.BEATS[b][1][0][0])
        self.j.act('bm_play_done', task=t['id'])
        self.assertIn('small', self.codes(t['id']))

    def test_screens_follow_the_note(self):
        t = self.at(*find('play', pred=lambda t: not t['needs']['screen_ok']))
        self.j.act('bm_play', task=t['id'], act='tv')
        self.j.act('bm_play_done', task=t['id'])
        self.assertIn('screen', self.codes(t['id']))
        t = self.at(*find('play', pred=lambda t: t['needs']['screen_ok']))
        self.j.act('bm_play', task=t['id'], act='tv')
        self.j.act('bm_play_done', task=t['id'])
        self.assertNotIn('screen', self.codes(t['id']))
        self.assertEqual(self.d['today']['tv'], 1)

    def test_a_curt_answer_dims_the_joy(self):
        t = self.at(*find('play'))
        a = next(x for x in t['needs']['acts'] if t['needs']['mood'] in BM.ACTS[x]['fits'] and not BM.ACTS[x]['screen'])
        self.j.act('bm_play', task=t['id'], act=a)
        before = self.j.get(t['id'])['st']['joy']
        self.j.act('bm_beat', task=t['id'], opt=next(o[0] for o in BM.BEATS[t['needs']['beats'][0]][1] if o[2] == 0))
        self.assertLess(self.j.get(t['id'])['st']['joy'], before)


class Safety(Base):
    def test_sweep_the_room(self):
        t = self.at(*find('safety'))
        harmless = next(x for x in t['needs']['items'] if not BM.HAZ[x][2])
        self.assertFalse(self.j.act('bm_check', task=t['id'], item=harmless)['correct'])
        self.block(t)
        self.assertFalse(self.codes(t['id']))
        self.assertEqual(self.d['today']['hazards'], len(BM.hazards(t)))

    def test_a_missed_hazard_is_named(self):
        t = self.at(*find('safety'))
        self.j.act('bm_check', task=t['id'], item=BM.hazards(t)[0])
        self.j.act('bm_safe_done', task=t['id'])
        self.assertIn('hazard', self.codes(t['id']))
        self.assertGreaterEqual(self.d['today']['missed'], 1)

    def test_rain_wets_the_floor(self):
        day, slot = find('safety', pred=lambda t: BM.mod_of(t['day'])['id'] == 'rain')
        self.assertIn('wet', make_task('babysitter', day, slot, 1)['needs']['items'])


class Nap(Base):
    def test_routine_then_pats_in_time(self):
        t = self.at(*find('nap'))
        f = self.fam(t)
        with self.assertRaises(GameError):
            self.j.act('bm_pat', task=t['id'])
        self.j.act('bm_nap', task=t['id'], step='potty')
        self.j.act('bm_nap', task=t['id'], step='dark')
        wrong = next(x for x in t['needs']['loveys'] if x != f['lovey'])
        self.assertFalse(self.j.act('bm_lovey', task=t['id'], item=wrong)['correct'])
        self.j.act('bm_lovey', task=t['id'], item=f['lovey'])
        self.assertIsNotNone(self.j.get(t['id'])['st']['pat'])
        self.assertFalse(self.pat_at(t['id'], 0.1)['correct'])
        with self.assertRaises(GameError):
            self.j.act('bm_nap_done', task=t['id'])
        for _ in range(BM.SLEEP_PATS):
            self.assertTrue(self.pat_at(t['id'], 0.7)['correct'])
        self.j.act('bm_nap_done', task=t['id'])
        self.assertEqual(self.codes(t['id']), {'routine'})     # no lullaby
        self.assertEqual(self.d['today']['nap'], 1)

    def test_a_late_tap_counts_when_the_finger_came_down(self):
        t = self.at(*find('nap', days=range(3, 60)))
        f = self.fam(t)
        self.j.act('bm_nap', task=t['id'], step='dark')
        self.j.act('bm_lovey', task=t['id'], item=f['lovey'])
        st = self.j.get(t['id'])['st']
        tap = st['pat'] + BM.CYCLE * 0.7
        self.clock.t = tap + 2.5                     # the command arrives later than the tap
        self.assertTrue(self.j.act('bm_pat', task=t['id'], tap_at=tap)['correct'])
        self.clock.t = tap + 2.5
        self.assertFalse(self.j.act('bm_pat', task=t['id'])['correct'])   # judged on arrival: off the breath


class Moments(Base):
    def test_first_aid_goes_in_order(self):
        t = self.at(*find('moment', pred=lambda t: t['needs']['mk'] == 'scrape'))
        r = self.j.act('bm_care', task=t['id'], move='plaster')
        self.assertFalse(r['correct'])
        for m in BM.SCRAPE_ORDER + ['hug']:
            self.j.act('bm_care', task=t['id'], move=m)
        self.assertEqual(self.j.get(t['id'])['st']['calm'], 100)
        self.j.act('bm_moment_done', task=t['id'])
        self.assertEqual(self.codes(t['id']), {'aid_order'})
        self.assertEqual(self.d['today']['moment'], 'scrape')

    def test_harsh_words_are_remembered(self):
        t = self.at(*find('moment', pred=lambda t: t['needs']['mk'] == 'tantrum'))
        self.j.act('bm_care', task=t['id'], move='shout')
        for m in ('breath', 'sit', 'name', 'choice'):
            if self.j.get(t['id'])['st']['calm'] < 100:
                self.j.act('bm_care', task=t['id'], move=m)
        if self.j.get(t['id'])['st']['calm'] < 100:
            with self.assertRaises(GameError):
                self.j.act('bm_moment_done', task=t['id'])
            return
        self.j.act('bm_moment_done', task=t['id'])
        self.assertIn('harsh', self.codes(t['id']))

    def test_tears_calm_down_with_care(self):
        t = self.at(*find('moment', pred=lambda t: t['needs']['mk'] == 'cry'))
        self.block(t)
        self.assertFalse(self.codes(t['id']))


class Handover(Base):
    def day_to_handover(self, day=None):
        self.j = Journey('babysitter')
        self.d['intro'] = True
        for _ in range(12):
            t = next(t for t in self.j.c['tasks'] if t['day'] == self.j.c['day'] and t['status'] not in ('completed', 'cancelled'))
            if t['kind'] == 'handover':
                return t
            self.block(t)
        raise AssertionError('no handover')

    def test_pay_tip_and_loyalty(self):
        t = self.day_to_handover()
        f = self.fam(t)
        money = self.j.c['money']
        pay = BM.pay_of(self.j.c, self.d, t['needs']['fam'])
        self.assertEqual(pay['total'], f['rate'] + BM.CARE_BONUS[0][1])
        self.block(t)
        done = self.j.get(t['id'])
        self.assertGreater(done['tip_given'], 0)
        self.assertGreaterEqual(self.j.c['money'] - money, pay['total'] + done['tip_given'])
        tips = [r for r in self.j.c.get('ledger', []) if r.get('category') == 'tip' and r.get('ref') == t['id']]
        if 'ledger' in self.j.c:
            self.assertEqual(sum(r['amount'] for r in tips), done['tip_given'])
        self.assertEqual(self.d['fams'][t['needs']['fam']], dict(visits=1, trust=1))
        self.assertEqual(self.d['today']['handed'], 1)

    def test_hiding_the_scrape_is_not_honest(self):
        t = self.day_to_handover()
        self.d['today']['moment'] = 'scrape'
        self.j.act('bm_log', task=t['id'], line='fine')
        for lid, _, true, must in BM.log_lines(self.j.c):
            if true and must and lid != 'moment':
                self.j.act('bm_log', task=t['id'], line=lid)
        self.j.act('bm_hand', task=t['id'])     # day 1: cô Tâm catches it once
        self.assertNotEqual(self.j.get(t['id'])['status'], 'completed')
        self.j.act('bm_hand', task=t['id'])
        self.assertIn('hide', self.codes(t['id']))
        self.assertNotIn('tip_given', self.j.get(t['id']))

    def test_log_lines_follow_the_day(self):
        t = self.day_to_handover()
        ids = [r[0] for r in BM.log_lines(self.j.c)]
        self.assertIn('food', ids)
        self.assertIn('nap', ids)
        self.assertIn('play', ids)
        self.assertNotIn('moment', ids)
        self.assertTrue(next(r for r in BM.log_lines(self.j.c) if r[0] == 'fine')[2])


class Schedule(Base):
    def test_blocks_go_in_order_and_the_clock_follows(self):
        self.j = Journey('babysitter')
        c = self.j.c
        plan = BM.plan_of(1)
        open_ = [t for t in c['tasks'] if t['status'] not in ('completed', 'cancelled')]
        self.assertEqual(open_[0]['kind'], 'arrive')
        self.assertEqual(c['active_task'], open_[0]['id'])
        self.assertEqual(BM.clock_minutes(c), BM.OPEN)
        later = open_[1]
        BM._today(c, BM._data(c))['note'] = 1
        with self.assertRaises(GameError):
            self.j.act('bm_play' if later['kind'] == 'play' else 'bm_kidwash', task=later['id'], act=later['needs'].get('acts', [None])[0])
        self.block(open_[0])
        self.assertEqual(BM.clock_minutes(self.j.c), plan[1][1])

    def test_the_handover_is_at_closing_and_takes_no_more_work(self):
        self.j = Journey('babysitter')
        for _ in range(12):
            t = next(t for t in self.j.c['tasks'] if t['day'] == self.j.c['day'] and t['status'] not in ('completed', 'cancelled'))
            if t['kind'] == 'handover':
                break
            self.block(t)
        self.assertEqual(BM.clock_minutes(self.j.c), BM.CLOSE)
        with self.assertRaises(GameError):
            self.j.act('more_work')
        self.block(t)
        self.assertFalse(BM._open_today(self.j.c))

    def test_closing_before_the_handover_pays_half(self):
        self.j = Journey('babysitter')
        t = self.j.task
        self.block(t)
        money = self.j.c['money']
        r = self.j.act('end_day', carry_event=True)
        car = r['summary']['career']
        self.assertEqual(car['half'], BM.FAMILIES['bin']['rate'] // 2)
        self.assertGreaterEqual(self.j.c['money'] - money, car['half'])
        self.j.act('start_day')
        validate_state(self.j.state)
        stale = [x for x in self.j.c['tasks'] if x['day'] == 1 and x['status'] not in ('completed', 'cancelled')]
        self.assertFalse(stale)
        self.assertEqual(self.j.task['kind'], 'arrive')
        self.assertEqual(self.j.task['day'], 2)


class Apprenticeship(Base):
    def test_co_tam_stops_an_allergy_once(self):
        t = self.at(*find('snack', pred=lambda t: any(BM.FAMILIES[t['needs']['fam']]['allergy'] in BM.FOODS[x]['al'] for x in t['needs']['menu'])),
                    learning=True)
        f = self.fam(t)
        bad = next(x for x in t['needs']['menu'] if f['allergy'] in BM.FOODS[x]['al'])
        self.j.act('bm_food', task=t['id'], food=bad)
        r = self.j.act('bm_serve', task=t['id'])
        self.assertEqual(r.get('lesson'), 'allergy')
        self.assertNotEqual(self.j.get(t['id'])['status'], 'completed')
        self.assertFalse(self.codes(t['id']))

    def test_two_days_and_she_lets_you_go(self):
        self.j = Journey('babysitter')
        self.j.act('bm_intro')
        self.play_day()
        self.assertTrue(BM.learning(self.d))
        self.play_day()
        self.assertFalse(BM.learning(self.d))
        self.assertTrue(self.d['learn']['done'])


class Days(Base):
    def test_ten_days_of_play_stay_valid(self):
        self.j = Journey('babysitter')
        self.j.act('bm_intro')
        for _ in range(10):
            r = self.play_day()
            car = r['summary']['career']
            self.assertIn('lines', car)
            self.assertIn('tomorrow', car)
            self.assertTrue(car['handed'])
            self.assertEqual(car['care'], 100)
        self.assertEqual(self.d['stats']['days'], 10)
        self.assertGreater(sum(v['trust'] for v in self.d['fams'].values()), 4)
        v = public_state(self.j.state)
        json.dumps(v['careers']['babysitter'])

    def test_public_data_shows_the_log_at_the_handover(self):
        self.j = Journey('babysitter')
        for _ in range(12):
            t = next(t for t in self.j.c['tasks'] if t['day'] == self.j.c['day'] and t['status'] not in ('completed', 'cancelled'))
            if t['kind'] == 'handover':
                break
            self.block(t)
        pd = BM.public_data(self.j.c)
        self.assertTrue(pd['log'])
        self.assertNotIn('true', pd['log'][0])
        self.assertEqual(pd['fam']['kid'], 'Bin')
        self.assertEqual(pd['pay']['care'], 100)

    def test_validator_rejects_tampering(self):
        t = self.at(*find('nap'))
        self.j.act('bm_nap', task=t['id'], step='dark')
        self.j.act('bm_lovey', task=t['id'], item=self.fam(t)['lovey'])
        validate_state(self.j.state)
        task = lambda s: next(x for x in s['careers']['babysitter']['tasks'] if x['id'] == t['id'])
        data = lambda s: s['careers']['babysitter']['ext']['data']
        for mutate in (lambda s: task(s)['st'].update(good=9),
                       lambda s: task(s)['st'].update(lovey='vit' if self.fam(t)['lovey'] != 'vit' else 'gau'),
                       lambda s: task(s)['st'].update(extra=1),
                       lambda s: task(s).update(stage='paid'),
                       lambda s: task(s)['needs'].update(loveys=['gau']),
                       lambda s: data(s)['today'].update(fam='zz'),
                       lambda s: data(s)['fams'].update(bin=dict(visits=1, trust=9)),
                       lambda s: data(s)['today'].update(food=['banh_mi_pate'])):
            bad = copy.deepcopy(self.j.state)
            mutate(bad)
            with self.assertRaises(GameError):
                validate_state(bad)


class OldSaves(Base):
    def story_save(self):
        s = new_state()
        jr.enable_story(s, 77)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        return s

    def test_a_save_without_the_career_gains_it_fresh_and_nothing_else_moves(self):
        s = self.story_save()
        s['careers'].pop('babysitter')
        s['journey']['chapter'] = 3
        s['journey']['unlocked'] = [cid for n in range(1, 4) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        s['journey']['done'] = [1, 2]
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['babysitter'], sort_keys=True), json.dumps(initial_career('babysitter'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)
        self.assertIn('babysitter', m['journey']['unlocked'])

    def test_data_from_an_older_build_fills_in(self):
        t = self.at(*find('play'))
        for k in ('learn', 'fams', 'stats'):
            self.d.pop(k)
        self.d['today'].pop('joy')
        self.j.act('bm_play', task=t['id'], act=t['needs']['acts'][0])
        validate_state(self.j.state)


if __name__ == '__main__':
    unittest.main()
