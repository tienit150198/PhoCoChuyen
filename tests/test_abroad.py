"""✈️ Du học, 🌏 Làm việc ở nước ngoài (game/abroad.py) and the 🎖️ pay ladder they feed (#249, #254)."""
import copy
import unittest

from game import abroad as ab
from game import abroad_content as AC
from game import promotion as pm
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_promotion import day, employee, story


def jr(j, name, **p):
    j.state, r = apply_action(j.state, None, name, p)
    return r


def worker(cid='delivery', wallet=3000):
    """A hired, official employee in story mode, its first shift closed, a full wallet."""
    j = employee(cid)
    j.state['journey']['wallet'] = wallet
    day(j)
    return j


def graduate(j, program='han_quoc', right=True):
    jr(j, 'jr_abroad_enrol', program=program)
    for n, ls in enumerate(AC.PROGRAMS[program]['lessons']):
        if n:
            day(j)
        pick = ls['ok'] if right else (ls['ok'] + 1) % 3
        r = jr(j, 'jr_abroad_lesson', option=pick)
    return r


class Study(unittest.TestCase):
    def test_tuition_one_lesson_a_day_and_a_degree(self):
        j = worker()
        w0 = j.state['journey']['wallet']
        jr(j, 'jr_abroad_enrol', program='nhat_ban')
        fee = ab.tuition('nhat_ban')
        self.assertEqual(j.state['journey']['wallet'], w0 - fee)
        self.assertEqual(j.state['journey']['history'][-1]['kind'], 'study')
        v = public_state(j.state)['journey']['abroad']['study']
        self.assertEqual((v['n'], v['of']), (0, 4))
        self.assertNotIn('ok', v['lesson'])   # the answer stays on the server
        jr(j, 'jr_abroad_lesson', option=AC.PROGRAMS['nhat_ban']['lessons'][0]['ok'])
        with self.assertRaises(GameError):   # one lesson a life day
            jr(j, 'jr_abroad_lesson', option=0)
        self.assertNotIn('lesson', public_state(j.state)['journey']['abroad']['study'])
        for n, ls in enumerate(AC.PROGRAMS['nhat_ban']['lessons'][1:], 1):
            day(j)
            r = jr(j, 'jr_abroad_lesson', option=ls['ok'])
        self.assertTrue(r['celebrate'])
        b = j.state['journey']['abroad']
        self.assertIsNone(b['study'])
        self.assertEqual(b['deg']['nhat_ban']['g'], 'xuat_sac')
        self.assertEqual(j.state['journey']['history'][-1]['amount'], fee * ab.SCHOLAR_PCT // 100)   # học bổng
        with self.assertRaises(GameError):   # a degree is earned once
            jr(j, 'jr_abroad_enrol', program='nhat_ban')
        validate_state(j.state)

    def test_wrong_answers_teach_never_fail(self):
        j = worker()
        r = graduate(j, 'phap', right=False)
        self.assertIn('Chưa đúng', r['message'])
        self.assertEqual(j.state['journey']['abroad']['deg']['phap']['g'], 'kha')
        self.assertEqual(ab.degrees(j.state), 1)

    def test_degree_raises_hired_pay_and_shortens_the_ladder(self):
        j = worker()
        base = j.c['job']['salary']
        nxt = public_state(j.state)['careers']['delivery']['promo']['next']
        self.assertEqual(nxt['need'], pm.EMP_STEPS[1]['good'])
        graduate(j, 'han_quoc')
        r = day(j)
        self.assertEqual(r['summary']['job']['salary'], round(base * 1.10))
        self.assertEqual(r['summary']['job']['degree'], 10)
        pub = public_state(j.state)['careers']['delivery']
        self.assertEqual(pub['job']['salary'], round(base * 1.10))
        self.assertEqual(pub['promo']['next']['need'], 4)   # 5 good days, 20 % fewer
        graduate(j, 'uc')
        self.assertEqual(ab.degree_pct(j.state), 15)

    def test_degree_counts_as_the_third_steps_certificate(self):
        j = worker()
        j.c['metrics']['served'] = 0
        rec = pm.record(j.state, 'delivery', True)
        pm._sync(rec, j.c)
        rec['rank'] = 2
        self.assertFalse(next(r for r in pm._gates(j.state, j.c, 'delivery', rec) if r['id'] == 'certificate_or_served')['met'])
        graduate(j)
        self.assertTrue(next(r for r in pm._gates(j.state, j.c, 'delivery', rec) if r['id'] == 'certificate_or_served')['met'])

    def test_drop_gives_half_the_unused_lessons_back(self):
        j = worker()
        jr(j, 'jr_abroad_enrol', program='uc')
        fee = ab.tuition('uc')
        jr(j, 'jr_abroad_lesson', option=0)
        w = j.state['journey']['wallet']
        with self.assertRaises(GameError):
            jr(j, 'jr_abroad_drop')
        jr(j, 'jr_abroad_drop', confirm=True)
        self.assertEqual(j.state['journey']['wallet'], w + fee * 3 // 4 // 2)
        self.assertIsNone(j.state['journey']['abroad']['study'])

    def test_thin_wallet_is_refused_cleanly(self):
        j = worker()
        j.state['journey']['wallet'] = 5
        with self.assertRaises(GameError):
            jr(j, 'jr_abroad_enrol', program='uc')
        self.assertEqual(j.state['journey']['wallet'], 5)


class Work(unittest.TestCase):
    def test_contract_pays_more_shuts_other_places_and_brings_you_home(self):
        j = worker()
        base = j.c['job']['salary']
        w0 = j.state['journey']['wallet']
        fee = ab.work_fee('han_quoc')
        r = jr(j, 'jr_abroad_work', to='han_quoc', career='delivery', confirm=True)
        self.assertTrue(r['celebrate'])
        self.assertEqual(j.state['journey']['wallet'], w0 - fee)
        # the other workplaces stay shut
        other = 'pho'
        with self.assertRaises(GameError) as e:
            apply_action(j.state, other, 'start_day', {})
        self.assertEqual(e.exception.code, 'abroad')
        v = public_state(j.state)['careers']['delivery']['job']
        self.assertEqual((v['away'], v['salary'], v['ladder_pay'][0]), (50, round(base * 1.5), v['salary']))   # the ladder quotes today's pay
        good0 = pm.record(j.state, 'delivery')['good']
        pay = []
        for n in range(AC.WORK['han_quoc']['days']):
            r = day(j)
            pay.append(r['summary']['job']['salary'])
            self.assertTrue(any(x.startswith('🌏 Ngày') for x in r['effects']), r['effects'])
            self.assertTrue(any(x.startswith('✉️') for x in r['effects']))
        self.assertEqual(pay[0], round(base * 1.5))
        b = j.state['journey']['abroad']
        self.assertIsNone(b['work'])
        self.assertEqual(b['done'], {'han_quoc': 1})
        self.assertTrue(any('Hết hợp đồng' in x for x in r['effects']))
        refund = [h for h in j.state['journey']['history'] if h['label'].startswith('Hoàn tiền vé')]
        self.assertEqual([h['amount'] for h in refund], [fee])
        rec = pm.record(j.state, 'delivery')
        self.assertTrue(rec['good'] >= good0 + ab.LADDER_BONUS or rec['due'] or rec['rank'] > 0)
        # home again: other places open, the next contract after a rest
        apply_action(j.state, other, 'start_day', {})
        with self.assertRaises(GameError):
            jr(j, 'jr_abroad_work', to='uc', career='delivery', confirm=True)
        validate_state(j.state)

    def test_needs_closed_shifts_and_no_probation(self):
        j = employee()
        j.state['journey']['wallet'] = 3000
        with self.assertRaises(GameError) as e:   # the delivery shift is open
            jr(j, 'jr_abroad_work', to='uc', career='delivery', confirm=True)
        self.assertEqual(e.exception.code, 'shift_open')
        day(j)
        j.c['job']['probation'] = True
        with self.assertRaises(GameError):
            jr(j, 'jr_abroad_work', to='uc', career='delivery', confirm=True)
        with self.assertRaises(GameError):   # an owner's place does not send anyone
            jr(j, 'jr_abroad_work', to='uc', career='pho', confirm=True)
        v = public_state(j.state)['journey']['abroad']['jobs']
        self.assertEqual([(x['career'], bool(x['why'])) for x in v], [('delivery', True)])

    def test_coming_home_early_keeps_the_pay_no_refund(self):
        j = worker()
        jr(j, 'jr_abroad_work', to='nhat_ban', career='delivery', confirm=True)
        day(j)
        w = j.state['journey']['wallet']
        jr(j, 'jr_abroad_home', confirm=True)
        self.assertEqual(j.state['journey']['wallet'], w)
        self.assertIsNone(j.state['journey']['abroad']['work'])
        self.assertEqual(j.state['journey']['abroad']['done'], {})

    def test_quitting_the_job_ends_the_contract(self):
        j = worker()
        jr(j, 'jr_abroad_work', to='phap', career='delivery', confirm=True)
        j.act('job_quit', confirm=True)
        self.assertIsNone(j.state['journey']['abroad']['work'])
        self.assertIsNone(ab.contract(j.state))
        validate_state(j.state)


class Saves(unittest.TestCase):
    def test_old_saves_and_bad_blocks(self):
        j = worker()
        validate_state(j.state)   # no 'abroad' at all
        self.assertIn('abroad', public_state(j.state)['journey'])
        jr(j, 'jr_abroad_enrol', program='han_quoc')
        for path, value in ((('v',), 2), (('study', 'n'), 9), (('study', 'p'), 'mars'), (('back',), -1), (('deg',), [])):
            s = copy.deepcopy(j.state)
            x = s['journey']['abroad']
            for k in path[:-1]:
                x = x[k]
            x[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['journey']['abroad']['later'] = {'x': 1}   # a newer build's key is kept
        validate_state(s)

    def test_catalogue_is_fair(self):
        cat = ab.catalogue()
        self.assertEqual(sorted(cat['programs']), sorted(d['id'] for d in AC.DESTS))
        for k, v in AC.PROGRAMS.items():
            for ls in v['lessons']:
                self.assertEqual(len(ls['options']), 3)
                self.assertIn(ls['ok'], (0, 1, 2))
        for k, w in AC.WORK.items():
            self.assertLessEqual(w['pct'], 100)
            self.assertGreaterEqual(len(w['lines']), w['days'] - 1)


class PayLadder(unittest.TestCase):
    def test_steps_climb_and_stay_in_the_old_bounds(self):
        pcts = [st['pct'] for st in pm.EMP_STEPS[1:]]
        self.assertEqual(pcts, sorted(pcts))
        self.assertGreaterEqual(pm.EMP_STEPS[4]['pct'], 50)            # the top of a 4-step ladder pays clearly more
        self.assertLessEqual(pcts[-1] + pm.EXTRA_MAX, 100)            # log rows older builds validate at ≤ 100
        steps = [100] + [100 + x for x in pcts]
        self.assertTrue(all(b / a < 1.2 for a, b in zip(steps, steps[1:])))   # moderate raises, never ×5

    def test_job_card_gets_title_and_pay_ladder(self):
        j = worker()
        pub = public_state(j.state)['careers']['delivery']
        base = j.c['job']['salary']
        self.assertEqual(pub['job']['ladder_pay'][0], base)
        self.assertEqual(len(pub['job']['ladder_pay']), pm.top('delivery') + 1)
        self.assertEqual(pub['job']['ladder_pay'][4], round(base * (100 + pm.EMP_STEPS[4]['pct']) / 100))
        self.assertEqual(len(pub['promo']['ladder']), pm.top('delivery'))
        self.assertTrue(pub['promo']['base_title'])


if __name__ == '__main__':
    unittest.main()
