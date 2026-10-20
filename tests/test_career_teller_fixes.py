"""🏦 Review fixes of the teller career (game/careers/teller.py): watching chị Hạnh is not a worked day, one promotion
review a day whatever the branch, no handover bonus for an empty shift, every withdrawal case comes up, Bà Lựu's book
holds what the slip says, the short-float surprise only on a short day, amounts bằng chữ in words, grown-up faces, and
the withdrawal's case never in the public brief."""
import re
import unittest

from tests.helpers import Journey
from tests.test_career_teller import T, TC, at_job, data, handover, learn, open_float, roundtrip, solve, teller, wrong
from game.engine import GameError, public_state


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Fixes(unittest.TestCase):
    def test_watching_the_mentor_is_not_a_worked_day(self):
        j = Journey('teller', day=1, slot=0)
        learn(j)
        before = (j.c['day_completed'], j.c['metrics'].get('served', 0), len(j.c['feed']), j.c['xp'])
        r = j.act('tl_shadow', task=j.task['id'])
        t = j.c['tasks'][0]
        self.assertEqual((t['status'], t['paid'], t['shadow']), ('referred', 0, True))
        self.assertIn('Chị Hạnh', r['message'])
        self.assertEqual(j.c['day_completed'], before[0])            # the contract's salary needs a served customer
        self.assertEqual(j.c['metrics'].get('served', 0), before[1])
        self.assertEqual(len(j.c['feed']), before[2])                 # no review, no stars
        self.assertEqual(j.c['xp'], before[3] + 1)
        self.assertIn(t['id'], j.c['completed_ids'])
        roundtrip(j)
        with self.assertRaises(GameError):
            j.act('tl_shadow', task=t['id'])

    def test_one_promotion_review_a_day_whatever_the_branch(self):
        j = at_job('withdraw')
        d = data(j)
        d['ranks'].update(giao_dich=1, tu_van=1)
        d['prog'].update(giao_dich=99, tu_van=99)
        j.act('tl_review', start=True)
        rv = data(j)['review']
        parts, key = T.review_parts(rv['branch'], rv['to'], rv['day'], data(j)['record'])
        for st in parts[rv['at']:]:
            if data(j)['review']['done']:
                break
            j.act('tl_review', step=st['id'], value=wrong(st, key[st['id']]))
        self.assertFalse(data(j)['review']['passed'])
        j.act('tl_branch', branch='tu_van')
        with self.assertRaises(GameError) as e:
            j.act('tl_review', start=True)
        self.assertEqual(e.exception.code, 'teller_retry')
        j.c['day'] += 1
        data(j)['today'] = T._today(j.c['day'])
        j.act('tl_review', start=True)
        self.assertEqual(data(j)['review']['branch'], 'tu_van')

    def test_no_handover_bonus_for_a_shift_without_a_customer(self):
        j = at_job('withdraw')
        money, prog = j.c['money'], data(j)['prog']['quan_ly']
        handover(j)
        self.assertEqual(j.c['money'], money)
        self.assertEqual(data(j)['prog']['quan_ly'], prog)
        self.assertEqual(data(j)['today']['handover'], 1)
        roundtrip(j)

    def test_the_handover_bonus_comes_after_a_served_customer(self):
        j = at_job('withdraw')
        solve(j)
        money = j.c['money']
        handover(j)
        self.assertEqual(j.c['money'], money + TC.HANDOVER_BONUS)

    def test_every_withdrawal_case_comes_up(self):
        seen = set()
        for day in range(2, 40):
            for slot in range(10):
                if T.job_of(day, slot) != 'withdraw':
                    continue
                b, steps, key, *_ = T.brief(day, slot, 'withdraw')
                seen.add(b['variant'])
                self.assertEqual(key['withdraw.check'], b['variant'])
        self.assertEqual(seen, {'ok', 'clarify', 'sign', 'refuse'})

    def test_amounts_in_words_are_words(self):
        self.assertEqual(T.money_words(2350), 'Hai triệu ba trăm năm mươi nghìn đồng')
        self.assertEqual(T.money_words(1050), 'Một triệu không trăm năm mươi nghìn đồng')
        self.assertEqual(T.money_words(1005), 'Một triệu không trăm linh năm nghìn đồng')
        self.assertEqual(T.money_words(2015), 'Hai triệu không trăm mười lăm nghìn đồng')
        self.assertEqual(T.money_words(21), 'Hai mươi mốt nghìn đồng')
        self.assertEqual(T.money_words(400), 'Bốn trăm nghìn đồng')
        n = 0
        for day in range(2, 60):
            for slot in range(10):
                if T.job_of(day, slot) == 'withdraw':
                    b = T.brief(day, slot, 'withdraw')[0]
                    if b['slip'].get('words'):
                        n += 1
                        self.assertFalse(re.search(r'\d', b['slip']['words']), b['slip']['words'])
        self.assertGreater(n, 0)

    def test_grown_up_faces_that_fit_the_customer(self):
        kids = {'👦🏻', '👧🏻'}
        self.assertFalse(kids & set(TC.FACES))
        self.assertEqual(len(TC.NPC_FACE), len(TC.PEOPLE))
        for day in range(2, 30):
            for slot in range(10):
                job = T.job_of(day, slot)
                if job == 'withdraw':
                    b = T.brief(day, slot, job)[0]
                    npc = T.npc_of(day, slot, job)
                    self.assertEqual(b['slip']['face'], TC.NPC_FACE[npc])
                if job == 'transfer':
                    b = T.brief(day, slot, job)[0]
                    self.assertFalse(kids & {c['face'] for c in b['steps'][0]['options']})

    def test_ba_luu_book_holds_the_goal_once_paid_in(self):
        self.assertEqual(T.arc_saved_before(4), TC.ARC_GOAL)
        self.assertEqual(T.arc_saved_before(5), TC.ARC_GOAL)
        day = next(d for d in range(2, 60) if any(T.luu_slot(d, s) for s in range(10)))
        slot = next(s for s in range(10) if T.luu_slot(day, s))
        b3 = T.brief(day, slot, 'savings', 3)[0]
        left = T.brief(day, slot, 'savings', 3)[2]['savings.left']
        self.assertEqual(b3['saved'] + left, TC.ARC_GOAL)
        b4 = T.brief(day, slot, 'savings', 4)[0]
        self.assertEqual(b4['saved'], TC.ARC_GOAL)
        self.assertIn(T.money_text(TC.ARC_GOAL), b4['steps'][0]['evidence'])

    def test_the_short_float_surprise_only_on_a_short_day(self):
        for day in range(1, 40):
            ids = {x['id'] for x in T.desk_scripts(day)}
            self.assertEqual('short_float' in ids, T.short_day(day), day)

    def test_the_withdrawal_case_is_not_in_the_public_brief(self):
        j = at_job('withdraw')
        j.act('ask', task=j.task['id'])
        pub = next(t for t in public_state(j.state)['careers']['teller']['tasks'] if t['id'] == j.task['id'])
        self.assertNotIn('variant', pub['needs'])
        self.assertIn('slip', pub['needs'])
        self.assertIn('variant', T._active(j.task)[0])   # the server still has it


if __name__ == '__main__':
    unittest.main()
