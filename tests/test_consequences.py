"""Làm sai thì phải chịu (game/consequences.py + game/mistake_lines.py): stars by severity,
the reaction at the counter, reports, inspections, money moved once, saves."""
import copy
import json
import unittest

from game import consequences as cq
from game import feedback
from game.engine import GameError, validate_state
from tests.helpers import Journey


def fresh_task(j):
    return next(t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled'))


def ledger_ok(c):
    f = c['ops']['finance']
    return f['opening_balance'] + sum(x['amount'] for x in f['ledger']) == c['money']


class Stars(unittest.TestCase):
    def test_cap_scales_with_severity(self):
        t = dict(id='x-0001-00')
        self.assertEqual(cq.star_cap(t), 5)
        cq.slip(t, 'a', 1, 'Hơi ngọt.')
        self.assertEqual(cq.star_cap(t), 4)
        cq.slip(t, 'b', 1, 'Hơi ít đá.')
        self.assertEqual(cq.star_cap(t), 3)
        cq.slip(t, 'c', 2, 'Sai size.')
        self.assertEqual(cq.star_cap(t), 2)
        cq.slip(t, 'd', 1, 'Nắp cháy.')
        self.assertEqual(cq.star_cap(t), 1)
        t2 = dict(id='x-0001-01')
        cq.slip(t2, 'dose', 3, 'Sai liều thuốc.', safety=True)
        self.assertEqual(cq.star_cap(t2), 1)

    def test_same_code_once_and_bounded(self):
        t = dict(id='x-0001-00')
        for i in range(20):
            cq.slip(t, 'a' if i < 5 else f'k{i}', 1, 'x')
        self.assertEqual(len(t['slips']), cq.MAX_SLIPS)
        self.assertEqual(sum(1 for r in t['slips'] if r['code'] == 'a'), 1)

    def test_evaluate_pulls_criteria_and_names_the_mistake(self):
        j = Journey('milk_tea')
        t = fresh_task(j)
        t['known'] = True
        good = feedback.evaluate(j.c, t, 'completed')
        cq.slip(t, 'ice', 2, 'Dặn ít đá mà đưa nhiều đá, uống toàn nước đá.', 'dặn ít đá mà đưa nhiều đá')
        bad = feedback.evaluate(j.c, t, 'completed')
        self.assertEqual(good['stars'], 5)
        self.assertEqual(bad['stars'], 3)
        acc = next(x for x in bad['criteria'] if x['key'] == 'accuracy')
        self.assertEqual((acc['score'], acc['note']), (3, 'dặn ít đá mà đưa nhiều đá'))
        made = feedback.make_review(j.state, j.c, t, 'completed')
        self.assertIn('Dặn ít đá mà đưa nhiều đá', made['text'])
        self.assertLessEqual(made['stars'], 3)
        self.assertFalse(made['aside'])


class Counter(unittest.TestCase):
    def test_no_slips_accepts_and_pays_in_full(self):
        j = Journey('milk_tea')
        t = fresh_task(j)
        r = cq.react(j.state, j.c, t, 40)
        self.assertEqual((r['kind'], r['pay'], r['cut'], r['message']), ('accept', 40, 0, ''))

    def test_reaction_grows_with_severity(self):
        order = ['accept', 'grumble', 'discount', 'refund', 'walkout']
        seen = []
        for sevs in ([1], [2], [2, 1], [2, 2], [3, 2]):
            j = Journey('milk_tea')
            t = fresh_task(j)
            for i, sv in enumerate(sevs):
                cq.slip(t, f'k{i}', sv, 'Sai rồi.')
            seen.append(order.index(cq.decide(j.c, t)))
        self.assertEqual(seen, sorted(seen))
        self.assertGreaterEqual(seen[-1], order.index('refund'))

    def test_prepaid_refund_moves_money_once_with_category(self):
        j = Journey('milk_tea')
        t = fresh_task(j)
        cq.slip(t, 'a', 2, 'Sai size.')
        cq.slip(t, 'b', 2, 'Sai vị.')
        cash = j.c['money']
        r = cq.react(j.state, j.c, t, 40, prepaid=True)
        self.assertEqual(r['pay'], 0)
        self.assertEqual(j.c['money'], cash - r['cut'])
        self.assertGreater(r['cut'], 0)
        self.assertEqual(j.c['ops']['finance']['ledger'][-1]['category'], 'refund')
        again = cq.react(j.state, j.c, t, 40, prepaid=True)
        self.assertEqual(j.c['money'], cash - r['cut'])
        self.assertEqual(again['kind'], r['kind'])
        self.assertTrue(ledger_ok(j.c))

    def test_remake_is_offered_once(self):
        j = Journey('milk_tea')
        t = j.c['tasks'][1]                 # a picky customer hands a wrong size back
        cq.slip(t, 'a', 2, 'Sai size.')
        cash = j.c['money']
        r = cq.react(j.state, j.c, t, 40, remake=True)
        self.assertEqual((r['kind'], r['pay'], j.c['money']), ('remake', 0, cash))
        self.assertEqual(j.c.get('slipbook', {}).get('total', 0), 0)   # nothing is settled yet
        cq.downgrade(t, 'returned', 'Sai size. Phải làm lại.')
        r = cq.react(j.state, j.c, t, 40, remake=True)
        # After one redo the hand-off settles, mildly: no endless remakes, no big refund.
        self.assertIn(r['kind'], ('accept', 'grumble'))
        self.assertEqual(r['pay'], 40)
        self.assertEqual([x['code'] for x in t['slips']], ['returned'])


class Escalation(unittest.TestCase):
    def test_safety_refuses_reports_and_brings_an_inspection(self):
        j = Journey('milk_tea')
        t = fresh_task(j)
        trust = j.c['incidents']['trust']
        cq.slip(t, 'spoiled', 3, 'Trân châu có mùi chua, uống xong đau bụng.', safety=True)
        r = cq.react(j.state, j.c, t, 40)
        self.assertEqual((r['kind'], r['pay'], r['cut']), ('refuse', 0, 40))
        self.assertTrue(any(p.get('report') and p['source'] == t['id'] for p in j.c['feed']))
        self.assertEqual(j.c['incidents']['trust'], trust - 4)
        self.assertEqual([f['script'] for f in j.c['incidents']['follow']], ['slip_food_inspect'])
        self.assertEqual(j.c['incidents']['follow'][0]['day'], j.c['day'] + 1)
        validate_state(json.loads(json.dumps(j.state)))

    def test_small_slips_do_not_report_until_they_repeat(self):
        j = Journey('milk_tea')
        tasks = [x for x in j.c['tasks']][:3]
        for i, t in enumerate(tasks):
            cq.slip(t, 'a', 2, 'Sai size.')
            cq.react(j.state, j.c, t, 30)
            reports = [p for p in j.c['feed'] if p.get('report')]
            self.assertEqual(len(reports), 0 if i < 2 else 1)
        self.assertEqual(j.c['slipbook']['total'], 3)

    def test_reports_are_capped_per_day(self):
        j = Journey('milk_tea')
        for t in j.c['tasks'][:3]:
            cq.slip(t, 'a', 3, 'Sai hẳn món.')
            cq.react(j.state, j.c, t, 30)
        self.assertEqual(sum(1 for p in j.c['feed'] if p.get('report')), cq.REPORTS_PER_DAY)

    def test_office_boss_trust_drops(self):
        j = Journey('corp_accounting')
        t = fresh_task(j)
        from game.careers import office
        o = office.ensure(j.c['ext']['data'])
        before = o['trust']
        cq.slip(t, 'wrong', 3, 'Hồ sơ nộp lên sai số tổng.')
        r = cq.react(j.state, j.c, t, 20)
        self.assertLess(o['trust'], before)
        self.assertIn('Sếp', r['message'])


class Saves(unittest.TestCase):
    def test_old_save_without_book_or_slips_is_valid(self):
        j = Journey('milk_tea')
        s = copy.deepcopy(j.state)
        for c in s['careers'].values():
            c.pop('slipbook', None)
        validate_state(s)

    def test_tampered_slips_are_rejected(self):
        j = Journey('milk_tea')
        t = fresh_task(j)
        cq.slip(t, 'a', 2, 'Sai size.')
        cq.react(j.state, j.c, t, 30)
        validate_state(j.state)
        for mutate in (lambda s, t: t['slips'][0].update(sev=9), lambda s, t: t['slips'].append('x'),
                       lambda s, t: t['reaction'].update(kind='free'), lambda s, t: s['careers']['milk_tea']['slipbook'].update(v=2),
                       lambda s, t: t.update(remade='yes')):
            bad = copy.deepcopy(j.state)
            bt = next(x for x in bad['careers']['milk_tea']['tasks'] if x['id'] == t['id'])
            mutate(bad, bt)
            with self.assertRaises(GameError):
                validate_state(bad)


if __name__ == '__main__':
    unittest.main()
