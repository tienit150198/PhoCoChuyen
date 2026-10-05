"""Variable pilot rosters and bonuses, including saves made before the change."""
import copy
import json
import subprocess
from pathlib import Path

from game.engine import GameError, migrate_state, public_state, validate_state
from tests.helpers import Journey
from tests.test_career_pilot import Base, PL, quiet


class PilotVariation(Base):
    def test_board_renders_schedule_and_bonus(self):
        result = subprocess.run(['node', 'tests/pilot_variation.mjs'],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_days_have_a_stable_varied_roster(self):
        self.assertTrue(callable(getattr(PL, 'daily_task_count', None)))
        counts = set()
        for day in range(2, 22):
            j = Journey('pilot')
            j.c.update(day=day, open=False, tasks=[], active_task=None)
            j.act('start_day')
            counts.add(len(j.c['tasks']))
            self.assertEqual(len(j.c['tasks']), PL.daily_task_count(day))
            restored = migrate_state(json.loads(json.dumps(j.state)))
            self.assertEqual(restored['careers']['pilot']['tasks'], j.c['tasks'])
            validate_state(restored)
        self.assertEqual(counts, {2, 3, 4, 5})
        self.assertEqual(len(self.j.c['tasks']), 3)

    def test_each_flight_has_a_stable_quote_and_pays_that_quote(self):
        quotes = set()
        for day, slot in ((1, 0), (1, 1), (1, 2), (2, 0), (3, 0), (4, 0)):
            j = Journey('pilot', day=day, slot=slot)
            quiet(j)
            t = j.task
            quote = PL.public_task(t).get('expected_bonus')
            self.assertIsInstance(quote, int)
            self.assertTrue(8 <= quote <= 22)
            quotes.add(quote)
            restored = migrate_state(json.loads(json.dumps(j.state)))
            self.assertEqual(PL.public_task(restored['careers']['pilot']['tasks'][0])['expected_bonus'], quote)
            tid = t['id']
            self.fly(j, tid)
            paid = [r['amount'] for r in j.c['ops']['finance']['ledger']
                    if r.get('ref') == tid and r.get('category') == 'revenue']
            self.assertEqual(paid, [quote])
        self.assertGreater(len(quotes), 1)

    def test_legacy_flight_keeps_its_original_fixed_bonus(self):
        j = self.j
        t = j.task
        t.pop('flight_bonus', None)
        before = copy.deepcopy(t)
        j.state = migrate_state(json.loads(json.dumps(j.state)))
        self.assertEqual(j.task, before)
        self.assertEqual(PL.public_task(j.task).get('expected_bonus'), PL.BONUS)
        quiet(j)
        tid = j.task['id']
        self.fly(j, tid)
        paid = [r['amount'] for r in j.c['ops']['finance']['ledger']
                if r.get('ref') == tid and r.get('category') == 'revenue']
        self.assertEqual(paid, [PL.BONUS])

    def test_bonus_cannot_be_raised_in_a_save(self):
        j = self.j
        j.task['flight_bonus'] = 9999
        with self.assertRaises(GameError):
            validate_state(j.state)

    def test_safety_error_still_removes_the_whole_bonus(self):
        j = self.j
        quiet(j)
        tid = j.task['id']
        self.settle_desk(j)
        self.brief(j, tid)
        j.act('pl_check', task=tid, point='engine')
        # Ignore the tutorial flight's pitot cover, then finish the remaining checks.
        point = PL.DEFECTS[j.get(tid)['needs']['defect']]['point']
        j.act('pl_check', task=tid, point=point)
        j.act('pl_defect', task=tid, how='ignore')
        for point in PL.POINTS:
            if point['id'] not in j.get(tid)['checked']:
                j.act('pl_check', task=tid, point=point['id'])
        self.start(j, tid)
        self.land(j, tid)
        paid = [r['amount'] for r in j.c['ops']['finance']['ledger']
                if r.get('ref') == tid and r.get('category') == 'revenue']
        self.assertFalse(any(paid))

    def test_existing_quality_fatigue_and_demotion_reductions_still_apply(self):
        from game.careers import air_odd as ao
        for mode in ('quality', 'tired', 'demoted'):
            with self.subTest(mode=mode):
                j = Journey('pilot')
                quiet(j)
                self.settle_desk(j)
                tid = j.task['id']
                quote = PL.public_task(j.task)['expected_bonus']
                self.brief(j, tid)
                self.walk(j, tid)
                if mode == 'quality':
                    j.act('pl_switch', task=tid, id=PL.ORDER[1])
                    expected = max(0, quote - 3)
                elif mode == 'tired':
                    j.c['ext']['data']['odd']['fatigue'] = ao.TIRED
                    expected = quote // 2
                else:
                    j.c['ext']['data']['odd']['conduct']['demoted'] = True
                    expected = 0
                self.start(j, tid)
                self.land(j, tid)
                paid = sum(r['amount'] for r in j.c['ops']['finance']['ledger']
                           if r.get('ref') == tid and r.get('category') == 'revenue')
                self.assertEqual(paid, expected)

    def test_roster_keeps_unfinished_flights_and_exposes_day_progress(self):
        self.assertTrue(callable(getattr(PL, 'daily_task_count', None)))
        j = self.j
        original = copy.deepcopy(j.c['tasks'])
        j.c.update(day=7, open=False)
        j.act('start_day')
        for old in original:
            self.assertEqual(j.get(old['id'])['needs'], old['needs'])
            self.assertEqual(j.get(old['id']).get('flight_bonus'), old.get('flight_bonus'))
        self.assertEqual(len(j.c['tasks']), max(len(original), PL.daily_task_count(7)))
        schedule = public_state(j.state)['careers']['pilot']['data']['schedule']
        self.assertEqual(schedule['remaining'], len(j.c['tasks']))
        self.assertEqual(schedule['completed'], 0)
