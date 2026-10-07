"""Support station desk: first-reply tone, reply deadlines, the courier's slow
answer, account takeover, the viral post and Phúc's story."""
import unittest

from game import desk, desk_content as dc
from game.content import make_task
from game.engine import CS_SOL_LABEL, GameError, public_state, validate_state
from tests.desk_support import Journey, desk_journey, reports, review, roundtrip, secrets, solve_desk


def reply_id(t, grade):
    return next(k for k, v in desk.reply_grades(t).items() if v == grade)


def advance(j, n):
    effects = []
    for _ in range(n):
        effects += j.act('advance')['effects']
    return effects


class ReplyTests(unittest.TestCase):
    def test_tone_moves_patience_and_opens_the_file(self):
        for grade, delta in (('best', 10), ('bad', -15)):
            j = desk_journey('customer_care', 'cs_wrong')
            t = j.task
            before = t.get('patience', 100)
            r = j.act('desk_reply', task=t['id'], reply=reply_id(t, grade))
            self.assertEqual(j.task['patience'], max(25, min(100, before + delta)))
            self.assertTrue(j.task['known'])  # replying already opens the papers
            self.assertEqual([m['who'] for m in j.task['thread']], ['player', 'npc'])
            self.assertIn(dc.REACT[t['mood']][grade], r['message'])

    def test_only_one_first_reply(self):
        j = desk_journey('customer_care', 'cs_wrong')
        j.act('desk_reply', task=j.task['id'], reply='r0')
        with self.assertRaises(GameError):
            j.act('desk_reply', task=j.task['id'], reply='r1')
        with self.assertRaises(GameError):
            desk_journey('customer_care', 'cs_wrong').act('desk_reply', task=j.task['id'], reply='r9')

    def test_reply_order_is_shuffled_but_stable(self):
        orders = set()
        for day in range(3, 20):
            for slot in range(6):
                if dc.plan('customer_care', day, slot):
                    j = Journey('customer_care', slot=slot, day=day)
                    orders.add(tuple(desk.reply_grades(j.task).values()))
                    self.assertEqual(desk.reply_grades(j.task), desk.reply_grades(dict(j.task)))
        self.assertGreater(len(orders), 2)

    def test_a_curt_first_reply_caps_the_grade(self):
        j = desk_journey('customer_care', 'cs_wrong')
        j.act('desk_reply', task=j.task['id'], reply=reply_id(j.task, 'ok'))
        t = solve_desk(j)
        self.assertEqual(t['grade'], 'good')
        post = next(f for f in j.c['feed'] if (f.get('feedback') or {}).get('task') == t['id'])
        self.assertEqual(next(c['score'] for c in post['feedback']['criteria'] if c['key'] == 'attitude'), 4)


class DeadlineTests(unittest.TestCase):
    def test_no_timer_on_the_first_two_days(self):
        for day in (1, 2):
            for slot in range(12):
                if dc.plan('customer_care', day, slot):
                    self.assertIsNone(Journey('customer_care', slot=slot, day=day).task['due_turn'])
        self.assertIn('cs_reply', [r['id'] for r in dc.bulletin('customer_care', 3)['rules'] if r['new']])

    def test_nudge_then_breach(self):
        j = desk_journey('customer_care', 'cs_wrong', days=range(3, 60))
        t = j.task
        left = t['due_turn'] - j.c['turn']
        before = t.get('patience', 100)
        effects = advance(j, left - 3)
        self.assertEqual(sum('còn 3 nhịp' in x for x in effects), 1)
        effects = advance(j, 2)
        self.assertFalse(any('⏳' in x for x in effects))  # nudged once only
        self.assertFalse(j.task['breached'])
        effects = advance(j, 2)
        self.assertTrue(j.task['breached'])
        self.assertTrue(any('Quá hạn phản hồi' in x for x in effects))
        self.assertEqual(j.task['patience'], max(25, before - desk.BREACH_PATIENCE))
        t = solve_desk(j)
        self.assertEqual(t['grade'], 'good')
        self.assertTrue(t['result']['breached'])
        validate_state(j.state)

    def test_reply_in_time_stops_the_clock(self):
        j = desk_journey('customer_care', 'cs_wrong', days=range(3, 60))
        j.act('desk_reply', task=j.task['id'], reply=reply_id(j.task, 'best'))
        advance(j, 20)
        self.assertFalse(j.task['breached'])
        self.assertEqual(solve_desk(j)['grade'], 'perfect')

    def test_public_tickets_are_shortest_and_late_ones_spread(self):
        self.assertLess(dc.SLA['public'], dc.SLA['vip'])
        self.assertLess(dc.SLA['vip'], dc.SLA['normal'])
        j = desk_journey('customer_care', 'cs_viral')
        advance(j, j.task['due_turn'] - j.c['turn'] + 1)
        self.assertTrue(j.task['breached'])
        self.assertEqual(j.c['ext']['data']['desk']['viral'], 1)


class CheckTests(unittest.TestCase):
    def test_courier_answer_takes_two_beats(self):
        j = desk_journey('customer_care', 'cs_lost')
        tid = j.task['id']
        j.act('ask')
        r = j.act('desk_check', task=tid, check='courier')
        self.assertIn('2 nhịp', r['message'])
        with self.assertRaises(GameError):
            j.act('desk_check', task=tid, check='courier')
        with self.assertRaises(GameError):
            j.act('desk_flag', task=tid, field='courier.point', rule='cs_place')
        effects = advance(j, 2)
        self.assertTrue(any('Hỏi Ngọc bên giao nhận có kết quả' in x for x in effects))
        self.assertIn('courier', j.task['verified'])
        self.assertEqual(j.act('desk_flag', task=tid, field='courier.point', rule='cs_place')['mark'], 'found')

    def test_stamping_before_the_courier_answers_is_only_good(self):
        j = desk_journey('customer_care', 'cs_lost')
        j.act('ask')
        j.act('desk_check', task=j.task['id'], check='courier')
        j.act('desk_decide', task=j.task['id'], verdict='trace', confirm=True)
        self.assertEqual(j.get(j.c['completed_ids'][-1])['grade'], 'good')

    def test_staff_chases_a_slow_answer(self):
        j = desk_journey('customer_care', 'cs_lost')
        j.act('ask')
        j.act('desk_check', task=j.task['id'], check='courier')
        self.assertIn('sắp tới', desk.assist(j.state, j.c, j.task, 'support'))
        advance(j, 1)
        self.assertIn('courier', j.task['verified'])

    def test_photo_metadata_catches_an_old_picture(self):
        fake = desk_journey('customer_care', 'cs_fraud', lambda c: bool(c['issues']))
        self.assertEqual(solve_desk(fake)['verdict'], 'deny')
        legit = desk_journey('customer_care', 'cs_fraud', lambda c: not c['issues'], slots=range(12))
        self.assertEqual(solve_desk(legit)['verdict'], 'refund')


class CaseTests(unittest.TestCase):
    def test_account_takeover(self):
        j = desk_journey('customer_care', 'cs_takeover')
        self.assertEqual(solve_desk(j)['verdict'], 'lock')
        k = desk_journey('customer_care', 'cs_takeover')
        self.assertEqual(solve_desk(k, verdict='refund')['grade'], 'wrong')
        self.assertEqual(k.c['ext']['data']['desk']['risk'], 3)

    def test_temporary_hold_refunds_itself(self):
        j = desk_journey('customer_care', 'cs_double')
        self.assertEqual(solve_desk(j)['verdict'], 'explain')
        k = desk_journey('customer_care', 'cs_double')
        self.assertEqual(solve_desk(k, verdict='refund')['grade'], 'wrong')

    def test_return_window_follows_the_policy_of_the_day(self):
        j = desk_journey('customer_care', 'cs_window')
        days = dc.window_days(j.task['day'])
        self.assertIn(f'{days} ngày', secrets(j)['issues'][0]['why'])
        self.assertEqual(solve_desk(j)['verdict'], 'explain')

    def test_threats_go_to_the_shift_lead(self):
        self.assertEqual(solve_desk(desk_journey('customer_care', 'cs_threat'))['verdict'], 'escalate')

    def test_viral_post(self):
        j = desk_journey('customer_care', 'cs_viral')
        t = solve_desk(j, verdict='hide')
        self.assertEqual(t['grade'], 'wrong')
        d = j.c['ext']['data']['desk']
        self.assertEqual(d['viral'], 2)
        self.assertIn('mức ồn', ' '.join(t['result']['lines']))
        d['viral'] = 3
        j.act('end_day', carry_event=True)
        j.act('start_day')
        d = j.c['ext']['data']['desk']
        self.assertEqual(d['viral'], 2)  # decays by one a day
        desk_today = [x for x in j.c['tasks'] if x.get('desk') and x['day'] == j.c['day']]
        self.assertTrue(all(x.get('patience', 100) <= 90 for x in desk_today))
        validate_state(j.state)

    def test_public_reply_is_right(self):
        t = solve_desk(desk_journey('customer_care', 'cs_viral'))
        self.assertEqual((t['verdict'], t['grade']), ('public', 'perfect'))

    def test_the_angry_regular_is_not_phuc_twice(self):
        day = next(d for d, ch in dc.STORY_DAYS['customer_care'].items() if ch == 1)
        self.assertNotIn('cs_angry', [dc.plan('customer_care', day, s) for s in range(12)])
        j = desk_journey('customer_care', 'cs_angry')
        self.assertNotEqual(secrets(j)['npc'], dc.STORY_NPC['customer_care'])
        self.assertEqual(solve_desk(j)['verdict'], 'reship')


class PhucTests(unittest.TestCase):
    def test_new_phone_needs_the_callback(self):
        j = Journey('customer_care', slot=1, day=5)
        self.assertEqual(j.task['chapter'], 2)
        j.act('desk_reply', task=j.task['id'], reply=reply_id(j.task, 'best'))
        j.act('desk_flag', task=j.task['id'], field='ticket.phone', rule='cs_id')
        r = j.act('desk_decide', task=j.task['id'], verdict='change', confirm=True)['desk_result']
        self.assertEqual(r['grade'], 'wrong')
        self.assertIn('chưa xác minh', r['says'])
        k = Journey('customer_care', slot=1, day=5)
        t = solve_desk(k)
        self.assertEqual((t['verdict'], t['grade']), ('change', 'perfect'))

    def test_first_chapter_calms_phuc(self):
        j = Journey('customer_care', slot=1, day=2)
        solve_desk(j)
        self.assertEqual(j.c['ext']['data']['desk']['flags'], ['phuc_calm'])


class ConsequenceTests(unittest.TestCase):
    def test_right_fix_keeps_five_stars(self):
        j = desk_journey('customer_care', 'cs_wrong')
        t = solve_desk(j)
        self.assertFalse(t.get('slips'))
        self.assertEqual(review(j, t['id'])['stars'], 5)

    def test_refund_to_a_hijacked_account_is_reported(self):
        j = desk_journey('customer_care', 'cs_takeover')
        money = j.c['money']
        t = solve_desk(j, verdict='refund')
        post = review(j, t['id'])
        self.assertLessEqual(post['stars'], 2)
        self.assertIn('tài khoản lạ', post['text'])
        self.assertTrue(reports(j, t['id']))
        self.assertEqual(j.c['money'], money)
        roundtrip(j)

    def test_posting_order_details_is_a_privacy_slip(self):
        j = desk_journey('customer_care', 'cs_viral')
        t = solve_desk(j, verdict='detail')
        self.assertEqual(t['slips'][0]['sev'], 3)
        self.assertIn('lộ hết thông tin', review(j, t['id'])['text'])

    def test_late_first_reply_is_a_small_slip_without_a_second_cut(self):
        j = desk_journey('customer_care', 'cs_wrong', days=range(3, 60))
        advance(j, j.task['due_turn'] - j.c['turn'] + 1)
        t = solve_desk(j)
        self.assertEqual(t['grade'], 'good')
        self.assertEqual([x['code'] for x in t['slips']], ['late_reply'])
        paid = [e['amount'] for e in j.c['ops']['finance']['ledger'] if e['ref'] == t['id']]
        self.assertEqual(paid, [desk.pay_for(t, 'good')])  # the grade already took 40%, no second cut
        self.assertEqual(review(j, t['id'])['stars'], 4)
        self.assertIn('quá hạn', review(j, t['id'])['text'])
        roundtrip(j)

    def test_late_and_wrong_add_up(self):
        j = desk_journey('customer_care', 'cs_lost', days=range(3, 60))
        advance(j, j.task['due_turn'] - j.c['turn'] + 1)
        t = solve_desk(j, verdict='deny')
        self.assertEqual(sorted(x['sev'] for x in t['slips']), [1, 3])
        self.assertLessEqual(review(j, t['id'])['stars'], 2)
        self.assertTrue(reports(j, t['id']))



class ClassicCaseChoiceTests(unittest.TestCase):
    """The multi-day case: the 📌 source line that names the fix, and a wrong pick that says why."""
    FIX = {'missing': {'reship', 'refund'}, 'delivered': {'trace'}, 'delay': {'trace'}, 'wrong': {'exchange'},
           'refund': {'refund'}, 'guide': {'guide'}}

    def case(self, slot):
        j = Journey('customer_care', slot=slot)
        t = make_task('customer_care', 1, slot, 1, True)  # a classic (pre-desk) case in this slot
        j.c['tasks'] = [t]
        j.c['active_task'] = t['id']
        validate_state(j.state)
        return j

    def view(self, j):
        return public_state(j.state)['careers']['customer_care']['tasks'][0]

    def read_all(self, j):
        j.act('cs_identity')
        for e in j.task['evidence']:
            self.assertIsNone(self.view(j)['basis'])  # only once every source is read
            j.act('cs_evidence', evidence=e['id'])

    def test_every_case_flags_its_basis_and_explains_a_wrong_pick(self):
        for slot in range(6):
            j = self.case(slot)
            variant = j.task['variant']
            self.assertIsNone(self.view(j)['basis'])
            self.read_all(j)
            v = self.view(j)
            self.assertNotIn('solution', v)
            line = next(e for e in v['evidence'] if e['id'] == v['basis'])
            self.assertTrue(line['text'])
            before = j.task['status']
            for wrong in sorted({'reship', 'trace', 'exchange', 'refund', 'guide'} - self.FIX[variant]):
                with self.assertRaises(GameError) as err:
                    j.act('cs_propose', solution=wrong)
                msg = str(err.exception)
                self.assertIn(line['title'], msg, variant)
                self.assertIn(line['text'], msg, variant)
                self.assertIn(CS_SOL_LABEL[wrong], msg)
                self.assertEqual(j.task['status'], before)
                self.assertIsNone(j.task['proposal'])
            j.act('cs_propose', solution=j.task['solution'])
            self.assertEqual(j.task['proposal'], j.task['solution'])
            validate_state(j.state)

    def test_basis_names_the_fix(self):
        """The flagged line carries the words of the fix it points to."""
        words = {'missing': 'gửi bù', 'delivered': 'đầu mối giao nhận', 'delay': 'kiểm tra chặng', 'wrong': 'đổi đúng mã',
                 'refund': 'yêu cầu hoàn', 'guide': 'Đơn của tôi'}
        for slot in range(6):
            j = self.case(slot)
            self.read_all(j)
            v = self.view(j)
            line = next(e for e in v['evidence'] if e['id'] == v['basis'])
            self.assertIn(words[j.task['variant']].lower(), line['text'].lower())

    def test_missing_policy_reads_as_shortage(self):
        """07/10: "Chính sách đổi trả" on the missing-item case read as "đổi đúng món". On screen it is "Chính sách thiếu
        hàng"; the stored title stays (1.9.10 and the task-compat gate regenerate the case and compare it), and a wrong
        pick quotes the 📌 line first."""
        j = next(x for x in (self.case(s) for s in range(6)) if x.task['variant'] == 'missing')
        self.read_all(j)
        stored = [e['title'] for e in j.task['evidence']]
        self.assertIn('Chính sách đổi trả', stored)
        shown = [e['title'] for e in self.view(j)['evidence']]
        self.assertIn('Chính sách thiếu hàng', shown)
        self.assertNotIn('Chính sách đổi trả', shown)
        with self.assertRaises(GameError) as err:
            j.act('cs_propose', solution='exchange')
        msg = str(err.exception)
        self.assertTrue(msg.startswith('📌 '), msg)
        self.assertIn('không phải thiếu món', msg)
        self.assertNotIn('đổi trả', msg)
        self.assertEqual([e['title'] for e in j.task['evidence']], stored)   # never written back
        validate_state(j.state)

    def test_missing_item_still_takes_a_refund(self):
        j = self.case(0)
        self.read_all(j)
        j.act('cs_propose', solution='refund')
        self.assertEqual(j.task['proposal'], 'refund')

    def test_odd_choice_keeps_the_plain_message(self):
        j = self.case(0)
        self.read_all(j)
        with self.assertRaises(GameError) as err:
            j.act('cs_propose', solution='nonsense')
        self.assertIn('Phương án chưa phù hợp', str(err.exception))


if __name__ == '__main__':
    unittest.main()
