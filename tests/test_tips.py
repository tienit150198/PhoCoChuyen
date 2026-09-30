"""Tip hên xui (game/tips.py): luck, weighted; rolled once per task; the right pocket."""
import copy
import unittest

from game import engine as e
from game import experiences as life
from game import journey as jr
from game import tip_content as tc
from game import tips
from game.content import CAREERS, make_task
from game.employment import hired_record, required
from game.engine import GameError, new_state, validate_state
from game.feedback import persona_for
from tests.helpers import Journey

HIGH = ('tour_guide', 'salon', 'delivery', 'homestay', 'restaurant', 'cafe_bakery', 'pet_care')
MEDIUM = ('milk_tea', 'florist', 'mother_baby', 'grocery')
NO_CASH = ('pharmacy', 'teacher', 'customer_care', 'corp_accounting', 'tax_payroll', 'group_accounting')


def finished(s, cid, day, slot, stars=5, bill=None, served=10):
    """A synthetic job just handed over: paid through engine.money, reviewed, marked done."""
    c = s['careers'][cid]
    c['day'] = day
    c['metrics']['served'] = served
    t = make_task(cid, day, slot, 1)
    t['status'] = 'completed'
    c['tasks'] = [t]
    pay = tc.NORMS.get(cid, tc.DEFAULT_NORM)['bill'] if bill is None else bill
    if pay:
        e.money(s, c, pay, 'Hoàn thành: ' + t['title'], t['id'])
    c['feed'] = [dict(id='post-x', npc=t['npc'], author='Khách', text='Ổn áp.', day=day, source=t['id'], stars=stars,
                      kind='review', comments=[], liked=False,
                      feedback=dict(fair=stars, persona=persona_for(cid, t['npc'])))]
    return c, t


def find(cid, kind='cash', start=2, story=False, s=None):
    """The first synthetic job (by day/slot) whose seeded roll gives `kind`."""
    for i in range(3000):
        st = copy.deepcopy(s) if s is not None else new_state()
        if story and s is None:
            jr.enable_story(st, 11)
        c, t = finished(st, cid, start + i // 12, i % 12)
        if tips.decide(st, c, t)['kind'] == kind:
            return st, c, t
    raise AssertionError(f'no {kind} tip found for {cid}')


def rate(cid, stars=5, n=240):
    s = new_state()
    hit = cash = 0
    for i in range(n):
        c, t = finished(s, cid, 2 + i // 12, i % 12, stars)
        r = tips.decide(s, c, t)
        hit += r['kind'] in ('cash', 'gift')
        cash += r['kind'] == 'cash'
    return hit / n, cash / n


class Luck(unittest.TestCase):
    def test_same_task_same_roll(self):
        s, c, t = find('salon')
        a = tips.decide(s, c, t)
        b = tips.decide(copy.deepcopy(s), copy.deepcopy(c), copy.deepcopy(t))
        self.assertEqual(a, b)
        s1, s2 = copy.deepcopy(s), copy.deepcopy(s)
        for st in (s1, s2):
            cc = st['careers']['salon']
            tips.after_task(st, cc, cc['tasks'][0])
        self.assertEqual(s1['careers']['salon']['tasks'][0]['tip_roll'], s2['careers']['salon']['tasks'][0]['tip_roll'])
        self.assertEqual(s1['careers']['salon']['money'], s2['careers']['salon']['money'])

    def test_rough_frequency_per_career(self):
        for cid in CAREERS:
            with self.subTest(career=cid):
                p, cash = rate(cid)
                if cid in HIGH:
                    self.assertTrue(.18 <= p <= .6, p)
                elif cid in MEDIUM:
                    self.assertTrue(.08 <= p <= .4, p)
                elif cid in NO_CASH:
                    self.assertTrue(p <= .16, p)
                    self.assertEqual(cash, 0)   # a gift or a note, never money
                else:
                    self.assertTrue(.03 <= p <= .4, p)
                self.assertGreater(p, 0)

    def test_stars_pull_the_chance_down(self):
        high, _ = rate('salon', 5)
        mid, _ = rate('salon', 4)
        low, _ = rate('salon', 3)
        self.assertGreater(high, mid)
        self.assertGreater(mid, low)
        self.assertLessEqual(low, .1)   # mediocre can still tip, rarely
        for stars in (1, 2):
            self.assertEqual(rate('salon', stars, 120), (0, 0))

    def test_amounts_are_nice_and_small(self):
        s = new_state()
        seen = []
        for i in range(600):
            c, t = finished(s, 'salon', 2 + i // 12, i % 12)
            r = tips.decide(s, c, t)
            if r['kind'] == 'cash':
                seen.append(r)
                self.assertIn(r['amount'], tc.NICE)
                n = tc.NORMS['salon']
                if r['big']:
                    self.assertTrue(tc.BIG_LO <= r['amount'] <= tc.BIG_HI)
                    self.assertGreater(r['amount'], n['hi'])
                else:
                    self.assertTrue(n['lo'] <= r['amount'] <= n['hi'], r)
                self.assertTrue(r['line'] and r['who'])
        self.assertGreater(len(seen), 50)
        self.assertLess(sum(r['big'] for r in seen), len(seen) * .1)

    def test_festival_day_tips_more(self):
        s = new_state()
        base = fest = 0
        for i in range(400):
            c, t = finished(s, 'tour_guide', 2 + i // 12, i % 12)
            c['life']['mode'] = 'normal'
            base += tips.decide(s, c, t)['kind'] != 'none'
            c['life']['mode'] = 'festival'
            fest += tips.decide(s, c, t)['kind'] != 'none'
        self.assertGreater(fest, base)

    def test_generosity_is_a_stable_trait_of_each_person(self):
        a = tips.generosity('salon', 'salon_npc_03', 'salon_npc_03')
        self.assertEqual(a, tips.generosity('salon', 'salon_npc_03', 'salon_npc_03'))
        traits = {round(tips.generosity('salon', f'salon_npc_{i:02d}', f'salon_npc_{i:02d}'), 2) for i in range(1, 18)}
        self.assertGreater(len(traits), 3)   # tight, ordinary, open-handed…

    def test_closeness_bonus_is_optional(self):
        self.assertEqual(tips.closeness(new_state(), 'salon_npc_01') > 0, True)


class NeverTips(unittest.TestCase):
    def setUp(self):
        self.s, self.c, self.t = find('salon')

    def check(self, why):
        r = tips.decide(self.s, self.c, self.t)
        self.assertEqual((r['kind'], r['why']), ('skip', why))
        money = self.c['money']
        tips.after_task(self.s, self.c, self.t)
        self.assertEqual(self.c['money'], money)
        self.assertEqual(self.t['tip_roll']['kind'], 'skip')

    def test_refuse_walkout_and_money_back(self):
        for kind in ('refuse', 'walkout', 'refund', 'discount'):
            with self.subTest(kind=kind):
                self.setUp()
                self.t['reaction'] = dict(kind=kind, cut=10, line='…', day=self.c['day'])
                self.check('reaction')

    def test_safety_slip(self):
        from game import consequences as cq
        cq.slip(self.t, 'allergy', 1, 'Tôi đã dặn dị ứng rồi mà.', safety=True)
        self.check('safety')

    def test_one_star(self):
        self.c['feed'][0]['feedback']['fair'] = 1
        self.check('stars')

    def test_referred_or_cancelled(self):
        self.t['status'] = 'referred'
        self.check('status')

    def test_keep_the_change_already_paid(self):
        self.t['tip_given'] = 5
        self.check('given')

    def test_career_tip_already_booked(self):
        e.money(self.s, self.c, 3, 'Khách quen gửi thêm', self.t['id'], category='tip')
        self.check('given')

    def test_first_job_at_a_place(self):
        self.c['metrics']['served'] = 1
        self.check('first')

    def test_grumble_rarely(self):
        s = new_state()
        hit = 0
        for i in range(240):
            c, t = finished(s, 'salon', 2 + i // 12, i % 12)
            t['reaction'] = dict(kind='grumble', cut=0, line='…', day=c['day'])
            hit += tips.decide(s, c, t)['kind'] != 'none' and tips.decide(s, c, t)['kind'] != 'skip'
        self.assertLess(hit / 240, .2)


class Pockets(unittest.TestCase):
    def test_till(self):
        s, c, t = find('salon')
        money, tips0 = c['money'], c['life']['tips']
        row = tips.after_task(s, c, t)
        amount = t['tip_roll']['amount']
        self.assertEqual((row['to'], t['tip_roll']['to']), ('till', 'till'))
        self.assertEqual(c['money'], money + amount)
        self.assertEqual(c['life']['tips'], tips0 + amount)
        rows = [x for x in c['ops']['finance']['ledger'] if x['ref'] == t['id'] and x['category'] == 'tip']
        self.assertEqual([x['amount'] for x in rows], [amount])
        self.assertTrue(rows[0]['reason'].startswith('Tip của khách'))
        self.assertEqual(c['life']['tip_day'][-1]['id'], t['id'])
        self.assertIn('xu tip', row['head'])

    def test_staff_on_shift_take_it_as_a_team(self):
        s, c, t = find('salon')
        c['ops']['staff'] = [dict(id='x', status='hired', on_shift=True, jobs=2)]
        money = c['money']
        row = tips.after_task(s, c, t)
        self.assertEqual(row['to'], 'team')
        self.assertEqual(c['money'], money)
        self.assertEqual(c['life']['staff_tips'], t['tip_roll']['amount'])
        self.assertIn('cả đội', row['head'])

    def test_employee_in_the_story_keeps_the_tip_in_the_wallet(self):
        self.assertTrue(required('salon'))
        base = new_state()
        jr.enable_story(base, 11)
        base['careers']['salon']['job'] = hired_record('salon')
        s, c, t = find('salon', s=base)
        j = s['journey']
        wallet, money, earned = j['wallet'], c['money'], c['earnings']
        row = tips.after_task(s, c, t)
        amount = t['tip_roll']['amount']
        self.assertEqual(row['to'], 'wallet')
        self.assertEqual(j['wallet'], wallet + amount)
        self.assertEqual(c['money'], money)                 # through the cash book, straight to you
        self.assertEqual(c['earnings'], earned + amount)    # still the day's income
        cats = [(x['category'], x['amount']) for x in c['ops']['finance']['ledger'] if x['ref'] in (t['id'], None)][-2:]
        self.assertEqual(cats, [('tip', amount), ('owner_draw', -amount)])
        self.assertEqual(j['history'][-1]['amount'], amount)
        self.assertIn('Tip của khách', j['history'][-1]['label'])
        jr.validate(s)

    def test_own_shop_in_the_story_keeps_it_in_the_till(self):
        self.assertFalse(required('restaurant'))
        base = new_state()
        jr.enable_story(base, 11)
        s, c, t = find('restaurant', s=base)
        wallet = s['journey']['wallet']
        row = tips.after_task(s, c, t)
        self.assertEqual(row['to'], 'till')
        self.assertEqual(s['journey']['wallet'], wallet)

    def test_gift_carries_no_money(self):
        s, c, t = find('teacher', 'gift')
        money = c['money']
        row = tips.after_task(s, c, t)
        self.assertEqual((row['kind'], row['amount'], row['to']), ('gift', 0, None))
        self.assertEqual(c['money'], money)
        self.assertTrue(row['gift'])
        self.assertNotIn('{', row['line'])

    def test_paid_once(self):
        s, c, t = find('pet_care')
        tips.after_task(s, c, t)
        money, rows = c['money'], len(c['ops']['finance']['ledger'])
        self.assertIsNone(tips.after_task(s, c, t))
        self.assertEqual((c['money'], len(c['ops']['finance']['ledger'])), (money, rows))
        self.assertEqual(len(c['life']['tip_day']), 1)

    def test_review_mentions_the_tip(self):
        s, c, t = find('salon')
        tips.after_task(s, c, t)
        post = c['feed'][0]
        self.assertIn('💝' if t['tip_roll']['kind'] == 'cash' else '🎁', post['text'])
        self.assertEqual(post['tip']['amount'], t['tip_roll']['amount'])


class RealPlay(unittest.TestCase):
    def play_day(self, j):
        """Every job of one day (up to 12), then close the shift."""
        done = []
        for _ in range(40):
            open_ = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
            if open_:
                done.append(j.solve(open_[0]['id'])['id'])
                continue
            try:
                j.act('more_work')
            except GameError:
                break
        return done

    def test_counter_jobs_tip_now_and_then_and_the_books_agree(self):
        j = Journey('mother_baby')
        got = []
        for day in range(3):
            done = self.play_day(j)
            rolls = {tid: j.get(tid).get('tip_roll') for tid in done}
            self.assertTrue(all(isinstance(r, dict) for r in rolls.values()), rolls)
            if day == 0:
                self.assertEqual(rolls[done[0]]['why'], 'first')   # the guided first job stays calm
            ledger = j.c['ops']['finance']['ledger']
            for tid, r in rolls.items():
                paid = sum(x['amount'] for x in ledger if x['ref'] == tid and x['category'] == 'tip')
                self.assertEqual(paid, r['amount'] if r['kind'] == 'cash' else 0, tid)
            till = sum(r['amount'] for r in rolls.values() if r['to'] == 'till')
            self.assertEqual(j.c['life']['tips'], till)
            validate_state(j.state)
            count = len(j.c['life'].get('tip_day') or [])
            # The day closes: "Tip hôm nay" goes into the recap and the list starts over.
            x = j.act('end_day', carry_event=True)['summary']['experiences']['tip_day']
            self.assertEqual((x['count'], x['till']), (count, till))
            self.assertEqual(j.c['life']['tip_day'], [])
            validate_state(j.state)
            got += [r for r in rolls.values() if r['kind'] in ('cash', 'gift')]
            j.act('start_day')
        self.assertTrue(got)   # over three real days somebody tipped


class Saves(unittest.TestCase):
    def played(self):
        s, c, t = find('salon')
        c['tasks'] = []   # keep the synthetic task out of the fixed-facts check
        return s

    def test_validate_catches_a_bad_roll_or_row(self):
        j = Journey('mother_baby')
        for _ in range(12):
            open_ = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
            if not open_:
                j.act('more_work')
                continue
            j.solve(open_[0]['id'])
            if j.c['life'].get('tip_day'):
                break
        self.assertTrue(j.c['life'].get('tip_day'))
        validate_state(j.state)
        done = next(t for t in j.c['tasks'] if isinstance(t.get('tip_roll'), dict))
        for bad in (dict(kind='cash', amount=0), dict(kind='jackpot'), dict(to='pocket'), dict(p=300), dict(v=9)):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['mother_baby']['tasks'] if x['id'] == done['id'])
            t['tip_roll'].update(bad)
            with self.subTest(bad=bad), self.assertRaises(GameError):
                validate_state(s)
        for bad in (dict(kind='cash', to=None), dict(amount=-1), dict(line=''), dict(big='yes')):
            s = copy.deepcopy(j.state)
            s['careers']['mother_baby']['life']['tip_day'][0].update(bad)
            with self.subTest(bad=bad), self.assertRaises(GameError):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['mother_baby']['life']['tip_day'] = [j.c['life']['tip_day'][0]] * (tips.DAY_KEEP + 1)
        with self.assertRaises(GameError):
            validate_state(s)

    def test_older_save_without_tip_fields(self):
        j = Journey('mother_baby')
        j.solve()
        old = copy.deepcopy(j.state)
        c = old['careers']['mother_baby']
        c['life'].pop('tip_day', None)
        for t in c['tasks']:
            t.pop('tip_roll', None)
        m = e.migrate_state(old)
        validate_state(m)
        s, r = e.apply_action(m, 'mother_baby', 'end_day', {'carry_event': True})
        self.assertEqual(r['summary']['experiences']['tip_day']['count'], 0)
        validate_state(s)
        # A job finished before this release is never rolled again.
        again = copy.deepcopy(s)
        cc = again['careers']['mother_baby']
        done = next(t for t in cc['tasks'] if t['status'] == 'completed')
        life.after_task(again, cc, done)
        self.assertNotIn('tip_roll', done)

    def test_day_summary_shape(self):
        x = dict(tip_day=[dict(id='a', day=2, kind='cash', amount=5, to='till', big=False, emoji='💝', who='Chị Lan',
                               head='Chị Lan để lại 5 xu tip', line='Em làm khéo ghê!', where='Tip vào két tiệm.', gift=''),
                          dict(id='b', day=2, kind='cash', amount=10, to='wallet', big=False, emoji='💝', who='Anh Tú',
                               head='Anh Tú để lại 10 xu tip', line='Cảm ơn nha.', where='…', gift=''),
                          dict(id='c', day=2, kind='gift', amount=0, to=None, big=False, emoji='🍊', who='Bà Sáu',
                               head='Bà Sáu gửi mấy trái quýt', line='Cháu cầm lấy.', where='…', gift='mấy trái quýt')])
        d = tips.day_summary(x)
        self.assertEqual((d['count'], d['cash'], d['till'], d['wallet'], d['team'], d['tips'], d['gifts']), (3, 15, 5, 10, 0, 2, 1))
        self.assertEqual(d['best']['head'], 'Anh Tú để lại 10 xu tip')
        self.assertEqual(tips.day_summary({})['count'], 0)


class Content(unittest.TestCase):
    def test_every_career_has_norms_lines_and_gifts(self):
        for cid in CAREERS:
            with self.subTest(career=cid):
                self.assertIn(cid, tc.NORMS)
                self.assertTrue(tc.GIFTS.get(cid))
                self.assertTrue(tc.CAREER_LINES.get(cid))
        for pool in (*tc.VOICE_LINES.values(), *tc.GIFT_LINES.values(), tc.BIG_LINES, *tc.CAREER_LINES.values()):
            for line in pool:
                line.format(self='bà', ac='chị', gv='cô')   # placeholders all known
                self.assertLessEqual(len(line), 120)

    def test_teacher_pharmacy_and_office_never_take_money(self):
        for cid in NO_CASH:
            self.assertEqual(tc.NORMS[cid]['cash'], 0, cid)


if __name__ == '__main__':
    unittest.main()
