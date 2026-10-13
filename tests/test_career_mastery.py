"""Prospective manual-work mastery, persisted assessments and capped rewards."""
import copy
import importlib.util
import json
import unittest


class MasteryContract(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('game.career_mastery'))


def career(day=1):
    return dict(day=day, open=True, xp=0, metrics={'served': 0}, tasks=[], completed_ids=[])


def job(c, cid='post_office', mistakes=0, status='completed', day=None, slot=None):
    n = c['metrics']['served'] if slot is None else slot
    task_day = c['day'] if day is None else day
    t = dict(id=f'{cid}-{task_day:04d}-{n:02d}', career=cid, day=task_day,
             status=status, mistakes=mistakes, completed_turn=n + 1)
    c['tasks'].append(t)
    c['completed_ids'].append(t['id'])
    c['metrics']['served'] += 1
    c['xp'] += 30
    return t


@unittest.skipUnless(importlib.util.find_spec('game.career_mastery'), 'implementation pending')
class CareerMastery(unittest.TestCase):
    def setUp(self):
        from game import career_mastery
        self.m = career_mastery

    def finish_day(self, c, clean=4, dirty=0, cid='post_office', allowed=True):
        c['open'] = True
        for _ in range(clean):
            self.m.completed(c, cid, job(c, cid))
        for _ in range(dirty):
            self.m.completed(c, cid, job(c, cid, mistakes=1))
        note = self.m.close(c, cid, allowed)
        c['day'] += 1
        c['open'] = False
        self.m.validate(c, cid)
        return note

    def eligible(self, cid='post_office'):
        c = career()
        for _ in range(15):
            self.finish_day(c, cid=cid)
        return c

    def exam(self, c, cid='post_office', scores=(2, 2, 2, 2)):
        self.m.action(c, cid, 'mastery_start', {})
        for score in scores:
            raw = self.m._paper(cid, c['mastery']['exam'])
            i = len(c['mastery']['exam']['answers'])
            opt = next(o['id'] for o in raw[i]['options'] if o['score'] == score)
            self.m.action(c, cid, 'mastery_answer', {'option': opt})
        return self.m.action(c, cid, 'mastery_finish', {})

    def test_old_save_public_read_only_and_prospective_counts(self):
        c = career(day=150)
        c['metrics']['served'] = 2000
        c['xp'] = 60000
        before = copy.deepcopy(c)
        self.m.validate(c, 'post_office')
        view = self.m.public(c, 'post_office')
        self.assertEqual(c, before)
        self.assertEqual(view['tier'], 0)
        self.assertEqual(view['clean'], 0)
        self.assertFalse(view['ready'])
        self.m.completed(c, 'post_office', job(c))
        self.assertEqual(c['mastery']['clean'], 1)
        self.assertEqual(c['mastery']['qualified_days'], 0)

    def test_real_current_day_manual_completion_and_duplicate_guard(self):
        c = career(day=10)
        for kwargs in ({'status': 'referred'}, {'status': 'cancelled'}, {'day': 9}):
            self.m.completed(c, 'post_office', job(c, **kwargs))
        self.assertNotIn('mastery', c)
        t = job(c)
        self.m.completed(c, 'post_office', t)
        before = copy.deepcopy(c)
        self.m.completed(c, 'post_office', t)
        self.assertEqual(c, before)
        foreign = job(c, cid='lawyer')
        self.m.completed(c, 'post_office', foreign)
        self.assertEqual(c['mastery']['completed'], 1)
        self.m.validate(c, 'post_office')

    def test_quality_day_thresholds_and_no_empty_repeat_exploit(self):
        c = career()
        self.assertFalse(self.finish_day(c, clean=2)['qualified'])
        self.assertFalse(self.finish_day(c, clean=3, dirty=1)['qualified'])
        self.assertTrue(self.finish_day(c, clean=4, dirty=1)['qualified'])
        c['open'] = True
        self.assertFalse(self.m.close(c, 'post_office', True)['qualified'])
        before = copy.deepcopy(c)
        self.assertEqual(self.m.close(c, 'post_office', True)['bonus'], 0)
        self.assertEqual(c, before)
        self.assertEqual(c['mastery']['qualified_days'], 1)

    def test_assessment_save_reload_hidden_scores_and_pass_seven(self):
        c = self.eligible()
        self.assertTrue(self.m.public(c, 'post_office')['ready'])
        self.m.action(c, 'post_office', 'mastery_start', {})
        for i, score in enumerate((2, 2, 2, 1)):
            view = self.m.public(c, 'post_office')
            self.assertEqual(view['exam']['index'], i)
            self.assertNotIn('score', json.dumps(view['exam']))
            raw = self.m._paper('post_office', c['mastery']['exam'])
            opt = next(o['id'] for o in raw[i]['options'] if o['score'] == score)
            self.m.action(c, 'post_office', 'mastery_answer', {'option': opt})
            c = json.loads(json.dumps(c))
            self.m.validate(c, 'post_office')
        self.assertTrue(self.m.public(c, 'post_office')['exam']['complete'])
        self.m.action(c, 'post_office', 'mastery_finish', {})
        self.assertEqual(c['mastery']['tier'], 1)
        self.assertEqual(self.m.public(c, 'post_office')['last_result']['score'], 7)
        from game.engine import GameError
        with self.assertRaises(GameError):
            self.m.action(c, 'post_office', 'mastery_finish', {})

    def test_failed_assessment_requires_three_more_qualified_days(self):
        c = self.eligible()
        self.exam(c, scores=(2, 2, 1, 1))
        self.assertEqual(c['mastery']['tier'], 0)
        self.assertEqual(self.m.public(c, 'post_office')['retry_good_days'], 3)
        self.finish_day(c, clean=0)
        self.assertEqual(self.m.public(c, 'post_office')['retry_good_days'], 3)
        for remaining in (2, 1, 0):
            self.finish_day(c)
            self.assertEqual(self.m.public(c, 'post_office')['retry_good_days'], remaining)
        self.assertTrue(self.m.public(c, 'post_office')['ready'])
        self.exam(c)
        self.assertEqual(c['mastery']['tier'], 1)

    def test_retry_starts_at_submission_day_not_when_paper_opened(self):
        c = self.eligible()
        self.m.action(c, 'post_office', 'mastery_start', {})
        self.finish_day(c)
        self.finish_day(c)
        for i in range(4):
            raw = self.m._paper('post_office', c['mastery']['exam'])
            wrong = next(o['id'] for o in raw[i]['options'] if o['score'] == 0)
            self.m.action(c, 'post_office', 'mastery_answer', {'option': wrong})
        self.m.action(c, 'post_office', 'mastery_finish', {})
        self.assertEqual(self.m.public(c, 'post_office')['retry_good_days'], 3)
        self.m.validate(c, 'post_office')

    def test_no_backfill_from_old_saved_completions_or_unearned_xp(self):
        c = career(day=60)
        c['xp'] = 100000
        c['metrics']['served'] = 3000
        c['open'] = True
        self.assertEqual(self.m.close(c, 'post_office', True)['bonus'], 0)
        self.assertNotIn('mastery', c)
        for _ in range(15):
            self.finish_day(c, clean=0)
        self.assertFalse(self.m.public(c, 'post_office')['ready'])
        self.assertEqual(self.m.public(c, 'post_office')['qualified_days'], 0)

    def test_invalid_actions_are_atomic(self):
        from game.engine import GameError
        c = self.eligible()
        for name, payload in [('mastery_answer', {'option': 'a'}), ('mastery_finish', {}),
                              ('mastery_start', {'tier': 3})]:
            before = copy.deepcopy(c)
            with self.assertRaises(GameError):
                self.m.action(c, 'post_office', name, payload)
            self.assertEqual(c, before)
        self.m.action(c, 'post_office', 'mastery_start', {})
        for name, payload in [('mastery_start', {}), ('mastery_answer', {'option': True}),
                              ('mastery_answer', {'option': 'forged'}), ('mastery_finish', {})]:
            before = copy.deepcopy(c)
            with self.assertRaises(GameError):
                self.m.action(c, 'post_office', name, payload)
            self.assertEqual(c, before)

    def test_paid_day_bonus_once_and_no_bonus_for_low_quality(self):
        c = self.eligible()
        self.exam(c)
        self.assertEqual(self.finish_day(c)['bonus'], 6)
        self.assertEqual(self.finish_day(c, allowed=False)['bonus'], 0)
        self.assertEqual(self.finish_day(c, clean=3, dirty=1)['bonus'], 0)
        before = copy.deepcopy(c)
        self.assertEqual(self.m.close(c, 'post_office', True)['bonus'], 0)
        self.assertEqual(c, before)

    def test_forged_tier_paper_counters_and_money_rejected(self):
        from game.engine import GameError
        c = self.eligible()
        self.exam(c)
        for edit in (lambda r: r.update(tier=3), lambda r: r.update(clean=True),
                     lambda r: r.update(qualified_days=9999), lambda r: r.update(earned=99999),
                     lambda r: r['awards'][0]['questions'].__setitem__(0, 'fake'),
                     lambda r: r['awards'][0].update(score=9)):
            changed = copy.deepcopy(c)
            edit(changed['mastery'])
            with self.assertRaises(GameError):
                self.m.validate(changed, 'post_office')

    def test_all_careers_have_appropriate_papers_and_no_org_mutation(self):
        from game.content import CAREERS
        for cid in CAREERS:
            c = self.eligible(cid)
            c['job'] = {'status': 'hired', 'employer': 'original'}
            c['org'] = {'grade': 'original'}
            before = (copy.deepcopy(c['job']), copy.deepcopy(c['org']))
            self.exam(c, cid)
            self.m.validate(c, cid)
            self.assertEqual((c['job'], c['org']), before)
            self.assertEqual(self.m.public(c, cid)['bonus'], 6)

    def test_long_progression_has_three_tiers_and_flat_bonus(self):
        c = career()
        awards = []
        bonuses = []
        for _ in range(90):
            note = self.finish_day(c)
            bonuses.append(note['bonus'])
            if self.m.public(c, 'post_office')['ready']:
                self.exam(c)
                awards.append(c['day'] - 1)
        self.assertEqual(awards, [15, 40, 75])
        self.assertEqual(c['mastery']['tier'], 3)
        self.assertEqual(max(bonuses), 20)
        self.assertIsNone(self.m.public(c, 'post_office')['next'])


if __name__ == '__main__':
    unittest.main()
