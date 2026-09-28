"""Bị quỵt tiền & cuộc gọi lừa đảo: the unpaid-bill and phone-scam chuyện đời (spec 2026-09-29-unpaid-scams)."""
import copy
import json
import unittest
from unittest import mock

from game import incidents as inc
from game.content import CAREERS
from game.engine import public_state, validate_state
from game.incident_content import INCIDENTS, INDEX
from tests.test_incidents import choose, fake_c, fire, ledger_ok, open_day, quiet, set_money

# id: (category, careers or None for everyone, min_day)
ROOTS = {
    'tab_regular': ('no', ('grocery', 'pharmacy', 'mother_baby', 'repair', 'salon', 'pet_care', 'florist'), 5),
    'atm_runaway': ('no', ('milk_tea', 'cafe_bakery', 'restaurant'), 5),
    'cod_bomb': ('no', ('delivery',), 5),
    'minibar_dawn': ('no', ('homestay',), 5),
    'class_fund': ('no', ('teacher',), 5),
    'late_invoice': ('no', ('accounting', 'tax_payroll'), 5),
    'otp_parcel': ('lua', None, 5),
    'bank_sms': ('lua', None, 6),
    'fake_prize': ('lua', None, 7),
    'wrong_transfer': ('lua', None, 9),
    'ceo_fraud': ('lua', ('corp_accounting', 'tax_payroll', 'group_accounting'), 6),
    'power_cut': ('lua', ('mother_baby', 'pharmacy', 'milk_tea', 'grocery', 'florist', 'cafe_bakery', 'restaurant', 'pet_care',
                          'salon', 'repair', 'homestay', 'farm', 'accounting'), 7),
}
CHAINS = ('tab_due', 'tab_gone', 'invoice_paid', 'invoice_gone', 'prize_more', 'loan_claim', 'scam_ring_bust')
LOSS_CATS = ('scam_loss', 'bad_debt')
# (root, option, follow-up it schedules)
FOLLOWS = (('tab_regular', 'write', 'tab_due'), ('tab_regular', 'nod', 'tab_gone'),
           ('late_invoice', 'reconcile', 'invoice_paid'), ('late_invoice', 'wait', 'invoice_gone'),
           ('fake_prize', 'pay', 'prize_more'), ('wrong_transfer', 'other', 'loan_claim'),
           ('otp_parcel', 'report', 'scam_ring_bust'), ('power_cut', 'check', 'scam_ring_bust'))
NEW = tuple(ROOTS) + CHAINS


def home_of(sid):
    x = INDEX[sid]
    if not x['chain']:
        return next(c for c in x['careers'] if c in CAREERS)
    root = next(r for r, _, f in FOLLOWS if f == sid)
    return home_of(root)


def branches(o):
    """(won, result) for each way an option can end: one for a plain option, two for a luck roll."""
    if o.get('luck'):
        return [(True, o['luck']['win']), (False, o['luck']['lose'])]
    return [(None, None)]


class Content(unittest.TestCase):
    def test_new_stories_exist_with_eligibility(self):
        for sid, (cat, careers, min_day) in ROOTS.items():
            x = INDEX[sid]
            self.assertEqual(x['cat'], cat, sid)
            self.assertFalse(x['chain'], sid)
            self.assertEqual(x['min_day'], min_day, sid)
            self.assertGreaterEqual(x['min_day'], 5, sid)   # never on a new player's first days
            self.assertEqual(set(x['careers']), set(careers or CAREERS), sid)
            self.assertTrue(2 <= len(x['options']) <= 3, sid)
        for sid in CHAINS:
            self.assertTrue(INDEX[sid]['chain'], sid)

    def test_careful_choice_exists_and_careless_one_costs_money(self):
        for sid in ROOTS:
            x = INDEX[sid]
            self.assertTrue(any(o['good'] is True for o in x['options']), sid)
            losses = []
            for o in x['options']:
                for _, res in branches(o):
                    lines = inc._lines(o, res)
                    good = res['good'] if res else o['good']
                    if good is not True:   # the careless or the "easy way out" answer
                        losses += [a for _, a, cat in lines if a < 0 and cat in LOSS_CATS]
            if sid != 'wrong_transfer':   # its loss comes with the "công ty tài chính" call two days later
                self.assertTrue(losses, sid)
            for _, amount, cat in (ln for o in x['options'] for _, res in branches(o) for ln in inc._lines(o, res)):
                self.assertLessEqual(abs(amount), 60, sid)   # tens of xu, like the rest of the street
        self.assertTrue(any(a < 0 for o in INDEX['loan_claim']['options'] for _, a, _ in o['pay']))

    def test_lessons_are_in_the_outcomes(self):
        dump = json.dumps([INDEX[s] for s in NEW], ensure_ascii=False)
        for lesson in ('không bao giờ hỏi OTP', 'không ai cần mã OTP', 'phải trả qua ngân hàng', 'không bao giờ bắt nộp tiền trước',
                       'gọi lại xác minh', 'không bao giờ bắt chuyển khoản vào tài khoản cá nhân', 'chữ ký'):
            self.assertIn(lesson, dump, lesson)

    def test_new_money_category_is_accepted_by_the_ledger(self):
        s = open_day('grocery')
        set_money(s['careers']['grocery'], 500)
        fire(s, 'grocery', 'tab_regular')
        s, _ = choose(s, 'grocery', 'nod')
        c = s['careers']['grocery']
        self.assertEqual(c['ops']['finance']['ledger'][-1]['category'], 'bad_debt')
        self.assertEqual(c['ops']['finance']['ledger'][-1]['amount'], -30)
        self.assertTrue(ledger_ok(c))
        validate_state(s)


class Effects(unittest.TestCase):
    """Every branch of every new story moves exactly the money it says, to the right place and category."""

    def test_every_branch_applies_its_money(self):
        bases = {}
        for sid in NEW:
            cid = home_of(sid)
            if cid not in bases:
                bases[cid] = open_day(cid)
                set_money(bases[cid]['careers'][cid], 5000)
            for o in INDEX[sid]['options']:
                for won, res in branches(o):
                    s = copy.deepcopy(bases[cid])
                    row = fire(s, cid, sid)
                    c0 = s['careers'][cid]
                    fund0, wallet0, n0, trust0 = c0['money'], s['journey']['wallet'], len(c0['ops']['finance']['ledger']), \
                        c0['incidents']['trust']
                    with mock.patch.object(inc, '_luck', return_value=won):
                        s, r = choose(s, cid, o['id'], row['id'])
                    c = s['careers'][cid]
                    lines = inc._lines(o, res)
                    fund = sum(a for w, a, _ in lines if w == 'fund')
                    wallet = sum(a for w, a, _ in lines if w == 'wallet')
                    key = (sid, o['id'], won)
                    self.assertEqual(c['money'] - fund0, fund, key)
                    self.assertEqual(s['journey']['wallet'] - wallet0, wallet, key)
                    got = sorted((e['amount'], e['category']) for e in c['ops']['finance']['ledger'][n0:] if e['ref'] == row['id'])
                    self.assertEqual(got, sorted((a, cat) for w, a, cat in lines if w == 'fund' and a), key)
                    self.assertTrue(ledger_ok(c), key)
                    trust = o.get('trust', 0) + (res.get('trust', 0) if res else 0)
                    self.assertEqual(c['incidents']['trust'], max(0, min(100, trust0 + trust)), key)
                    self.assertEqual(c['incidents']['last']['good'], res['good'] if res else o['good'], key)
                    self.assertTrue(r['message'], key)
                    validate_state(s)

    def test_voluntary_scam_payments_need_the_money(self):
        s = open_day('grocery')
        s['journey']['wallet'] = 10
        fire(s, 'grocery', 'fake_prize')
        pub = public_state(s)['careers']['grocery']['incidents']['active']
        self.assertFalse(next(o for o in pub['options'] if o['id'] == 'pay')['affordable'])
        self.assertTrue(next(o for o in pub['options'] if o['id'] == 'check')['affordable'])

    def test_careless_scam_loss_is_hidden_until_decided(self):
        s = open_day('pharmacy')
        fire(s, 'pharmacy', 'otp_parcel')
        pub = public_state(s)['careers']['pharmacy']['incidents']['active']
        self.assertEqual(next(o for o in pub['options'] if o['id'] == 'read')['stakes'], [])
        dump = json.dumps(pub, ensure_ascii=False)
        for k in ('"good"', '"outcome"', '"luck"', '"follow"', '"trust"'):
            self.assertNotIn(k, dump)

    def test_vigilance_pays_at_the_office(self):
        s = open_day('corp_accounting')
        fire(s, 'corp_accounting', 'ceo_fraud')
        w0 = s['journey']['wallet']
        s, r = choose(s, 'corp_accounting', 'call')
        self.assertEqual(s['journey']['wallet'], w0 + 15)
        self.assertTrue(r.get('celebrate'))


class FollowUps(unittest.TestCase):
    def test_follow_ups_are_scheduled_and_fire_days_later(self):
        for root, option, follow in FOLLOWS:
            cid = home_of(root)
            s = open_day(cid)
            set_money(s['careers'][cid], 5000)
            fire(s, cid, root)
            s, _ = choose(s, cid, option)
            c = s['careers'][cid]
            box = c['incidents']
            due = next(f for f in box['follow'] if f['script'] == follow)
            self.assertGreater(due['day'], c['day'], (root, option))
            # Not before its day …
            quiet(c)
            c['day_completed'] = 1
            box['count'] = dict(day=c['day'], n=0)
            inc.after(s, c, cid, 'task_select', {})
            self.assertIsNone(box['active'], (root, option))
            # … then it comes up by itself on the day it is due.
            c['day'] = due['day']
            box['count'] = dict(day=c['day'], n=0)
            box['plan'] = None
            result = {}
            inc.after(s, c, cid, 'task_select', result)
            self.assertEqual(box['active']['script'], follow, (root, option))
            self.assertTrue(box['active']['follow'])
            self.assertEqual(result['incident'], box['active']['id'])
            validate_state(s)

    def test_careful_choices_schedule_no_bad_follow_up(self):
        for root, option in (('tab_regular', 'decline'), ('late_invoice', 'pause'), ('fake_prize', 'check'),
                             ('wrong_transfer', 'bank'), ('otp_parcel', 'ask'), ('bank_sms', 'app'), ('ceo_fraud', 'process')):
            cid = home_of(root)
            s = open_day(cid)
            fire(s, cid, root)
            s, _ = choose(s, cid, option)
            self.assertEqual(s['careers'][cid]['incidents']['follow'], [], (root, option))

    def test_scam_story_stops_after_the_second_payment(self):
        s = open_day('grocery')
        fire(s, 'grocery', 'fake_prize')
        w0 = s['journey']['wallet'] = 200
        s, _ = choose(s, 'grocery', 'pay')
        box = s['careers']['grocery']['incidents']
        self.assertEqual([f['script'] for f in box['follow']], ['prize_more'])
        box['follow'] = []
        fire(s, 'grocery', 'prize_more')
        s, _ = choose(s, 'grocery', 'pay')
        self.assertEqual(s['journey']['wallet'], w0 - 70)
        self.assertEqual(s['careers']['grocery']['incidents']['follow'], [])   # no third call: the chain ends


class Eligibility(unittest.TestCase):
    def test_plans_respect_careers_and_min_day(self):
        seen = set()
        for cid in CAREERS:
            for day in (3, 4, 5, 6, 7, 8, 9, 12):
                for seed in range(60):
                    p = inc.roll_plan(dict(journey=dict(seed=seed)), fake_c(day), cid)
                    if not p or p['script'] not in ROOTS:
                        continue
                    x = INDEX[p['script']]
                    self.assertIn(cid, x['careers'], (cid, p['script']))
                    self.assertLessEqual(x['min_day'], day, (cid, p['script'], day))
                    seen.add(p['script'])
        self.assertEqual(seen, set(ROOTS))   # every new story can really come up somewhere

    def test_chains_never_planned_directly(self):
        for cid in CAREERS:
            for seed in range(40):
                p = inc.roll_plan(dict(journey=dict(seed=seed)), fake_c(20), cid)
                self.assertTrue(p is None or p['script'] not in CHAINS)

    def test_calm_days_skip_the_tense_ones(self):
        tense = {sid for sid in NEW if INDEX[sid]['tone'] == 'tense'}
        self.assertEqual(tense, {'ceo_fraud', 'loan_claim'})
        for cid in ('corp_accounting', 'tax_payroll', 'group_accounting'):
            for seed in range(120):
                p = inc.roll_plan(dict(journey=dict(seed=seed)), fake_c(12, 'calm'), cid)
                self.assertTrue(p is None or p['script'] != 'ceo_fraud')

    def test_offices_and_teachers_only_meet_their_own_unpaid_story(self):
        for sid in ('tab_regular', 'atm_runaway', 'cod_bomb', 'minibar_dawn', 'late_invoice', 'power_cut'):
            self.assertNotIn('teacher', INDEX[sid]['careers'], sid)
        for sid in ('ceo_fraud',):
            self.assertFalse(set(INDEX[sid]['careers']) - {'corp_accounting', 'tax_payroll', 'group_accounting'})
        self.assertEqual(INDEX['class_fund']['careers'], ('teacher',))

    def test_everyone_meets_a_phone_scam(self):
        for cid in CAREERS:
            own = [x for x in INCIDENTS if not x['chain'] and cid in x['careers'] and x['id'] in ROOTS]
            self.assertGreaterEqual(len(own), 4, cid)


if __name__ == '__main__':
    unittest.main()
