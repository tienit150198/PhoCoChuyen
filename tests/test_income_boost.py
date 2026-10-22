"""📈 Thu nhập tăng thêm (game/income_boost.py, owner 22/10: "tăng 50% thu nhập tất cả mọi người", "tăng cả tiền quầy,..
mọi thứ luôn mn kiếm được nhé", "ưu tiên cho user thấp, cao thì sẽ giảm dần còn 20%"): every earning × pct / 100, once
(150 under 50 triệu of net worth, 140 / 130 / 120 past 50 triệu / 200 triệu / 1 tỷ); costs, refunds, transfers and money between
players unchanged. tests/__init__.py turns it off for the older tests; this file turns it on."""
import copy
import json
import os
import unittest
from unittest import mock

from game import engine as E
from game import income_boost as ib
from game import journey as jr
from game import quay_business as qb
from game import x3_week as x3
from game.engine import new_state, validate_state

ON = {'MNL_INCOME_BOOST_OFF': '0'}
OFF = {'MNL_INCOME_BOOST_OFF': '1'}


def story():
    s = new_state()
    jr.enable_story(s, 4242)
    s['journey'].update(gender='female', intro=True)
    validate_state(s)
    return s


def opened(cid='grocery'):
    s = story()
    s, _ = E.apply_action(s, cid, 'select_career', {'confirm': True})
    s, _ = E.apply_action(s, cid, 'start_day')
    return s, s['careers'][cid]


def rows(c):
    return [r for r in c['ops']['finance']['ledger'] if r.get('ref') == ib.REF]


class Arithmetic(unittest.TestCase):
    @mock.patch.dict(os.environ, ON)
    def test_half_again_rounded_fairly(self):
        self.assertEqual(ib.INCOME_PCT, 150)
        self.assertEqual((ib.part(100), ib.scale(100), ib.part(0), ib.part(-40)), (50, 150, 0, 0))
        self.assertIn(ib.part(3, 'a'), (1, 2))
        self.assertEqual(ib.part(3, 'a'), ib.part(3, 'a'))   # a retried command books the same
        got = sum(ib.part(1, f'k{i}') for i in range(2000))
        self.assertTrue(900 < got < 1100, got)               # 0.5 xu on average
        self.assertEqual((ib.take_percent(124), ib.take_percent(236), ib.take_percent(0)), (236, 404, 50))
        self.assertEqual(ib.LABEL, '📈 Thu nhập tăng thêm')

    @mock.patch.dict(os.environ, ON)
    def test_the_brackets_by_net_worth(self):
        self.assertEqual([ib.for_worth(n) for n in (None, -5, 0, 49_999_999, 50_000_000, 199_999_999, 200_000_000,
                                                    999_999_999, 10**9, 10**11)],
                         [150, 150, 150, 150, 140, 140, 130, 130, 120, 120])
        s = story()
        self.assertEqual(ib.pct(s), 150)
        s['journey']['wallet'] = 60_000_000
        self.assertEqual(ib.pct(s), 140)
        s['journey']['wallet'] = 2 * 10**9
        self.assertEqual(ib.pct(s), 120)
        self.assertEqual((ib.part(100, s=s), ib.scale(100, s=s), ib.take_percent(124, s)), (20, 120, 168))
        with ib.scope(s):   # held once for a loop: no save given reads it too
            s['journey']['wallet'] = 60_000_000
            self.assertEqual((ib.pct(), ib.pct(s), ib.pct(story())), (120, 120, 150))
        self.assertEqual((ib.pct(), ib.pct(s)), (150, 140))

    @mock.patch.dict(os.environ, OFF)
    def test_the_switch(self):
        self.assertEqual((ib.part(100), ib.scale(100), ib.take_percent(124)), (0, 100, 124))
        self.assertFalse(ib.on(story()))


@mock.patch.dict(os.environ, ON)
class Fund(unittest.TestCase):
    def test_earnings_get_one_row_a_day(self):
        s, c = opened()
        m0, e0 = c['money'], c['earnings']
        E.money(s, c, 100, 'Hoàn thành: một giỏ hàng', 't-1')
        E.money(s, c, 40, 'Khách để lại tiền lẻ', 't-1', 'tip')
        E.money(s, c, 30, 'Lương ngày 1', 'salary-1', 'salary')
        self.assertEqual(c['money'] - m0, 170 + 85)
        self.assertEqual(c['earnings'] - e0, 255)
        self.assertEqual([(r['amount'], r['reason'], r['category']) for r in rows(c)], [(85, ib.LABEL, 'other_income')])
        self.assertEqual(ib.day_total(c, c['day']), 85)
        validate_state(s)   # opening balance + rows == the fund
        json.loads(json.dumps(s))

    def test_costs_refunds_transfers_gifts_and_players_money_are_not_earnings(self):
        s, c = opened()
        m0 = c['money']
        E.money(s, c, 20, 'Hoàn tiền lô lỗi', 'r-1', 'refund')
        E.money(s, c, 20, 'Bảo hiểm tài sản chi trả', 'r-2', 'insurance_recovery')
        E.money(s, c, 20, 'Quà từ bạn (Phố nghề)', None, 'gift')
        E.money(s, c, 80, 'Gói hỗ trợ khởi đầu của khu phố', None, 'grant')
        E.money(s, c, -10, 'Đặt nhập 1 thùng', None, 'stock')
        jr._transfer(s, c, 50, 'Góp vốn từ ví của bạn', 'owner_capital')
        with ib.skip():
            E.money(s, c, 60, 'Thanh toán đơn khách thật', 'p-1', 'revenue')
        self.assertEqual(c['money'] - m0, 20 + 20 + 20 + 80 - 10 + 50 + 60)
        self.assertEqual(rows(c), [])
        validate_state(s)

    def test_a_save_outside_the_story_and_the_switch(self):
        s = new_state()
        c = s['careers']['grocery']
        m0 = c['money']
        E.money(s, c, 100, 'Hoàn thành: x', 't')
        self.assertEqual(c['money'] - m0, 100)
        s, c = opened()
        m0 = c['money']
        with mock.patch.dict(os.environ, OFF):
            E.money(s, c, 100, 'Hoàn thành: x', 't')
        self.assertEqual(c['money'] - m0, 100)

    def test_a_new_day_starts_a_new_row(self):
        s, c = opened()
        E.money(s, c, 10, 'Hoàn thành: a', 'a')
        c['day'] += 1
        E.money(s, c, 10, 'Hoàn thành: b', 'b')
        self.assertEqual([r['amount'] for r in rows(c)], [5, 5])
        self.assertEqual(ib.day_total(c, c['day']), 5)

    def test_a_rich_save_gets_less(self):
        s, c = opened()
        s['journey']['wallet'] = 300_000_000   # 200 triệu – 1 tỷ: +30 %
        E.money(s, c, 100, 'Hoàn thành: a', 'a')
        s['journey']['wallet'] = 2 * 10**9     # from 1 tỷ: +20 %, same day's row
        E.money(s, c, 100, 'Hoàn thành: b', 'b')
        self.assertEqual([r['amount'] for r in rows(c)], [50])


@mock.patch.dict(os.environ, ON)
class Shift(unittest.TestCase):
    def close(self, cid, earn, x3_day=False):
        s, c = opened(cid)
        E.money(s, c, earn, 'khách mua')
        with mock.patch.object(x3, 'on', lambda career, t=None: x3_day and career == cid):
            s, r = E.apply_action(s, cid, 'end_day', {'carry_event': True})
        validate_state(s)
        return r['summary'], [h['amount'] for h in s['journey']['history'] if h['label'].startswith('🔥')]

    def test_the_summary_counts_the_boost_and_x3_pays_on_the_boosted_base(self):
        summary, fire = self.close('grocery', 40, x3_day=True)
        self.assertEqual(summary['incomeboost'], 20)
        self.assertEqual((summary['income'], summary['net']), (60, 60))
        self.assertEqual(fire, [2 * 60])                  # x3 × 1.5: (3 − 1) × 40 × 1.5
        self.assertEqual(summary['journey']['x3'], 120)
        with mock.patch.dict(os.environ, OFF):
            summary, fire = self.close('grocery', 40, x3_day=True)
        self.assertNotIn('incomeboost', summary)
        self.assertEqual(fire, [80])

    def test_the_x3_cap_still_holds(self):
        summary, fire = self.close('grocery', 5000, x3_day=True)
        self.assertEqual(fire, [x3.CAP])


@mock.patch.dict(os.environ, ON)
class Jobs(unittest.TestCase):
    def test_a_finished_job_earns_half_again_in_all(self):
        from tests.test_pay_boost import Run
        got = {}
        for name, env in (('off', OFF), ('on', ON)):
            with mock.patch.dict(os.environ, env):
                r = Run()
                m0 = r.c['money']
                r.solve(r.c['active_task'])
                got[name] = (r.c['money'] - m0, ib.day_total(r.c, r.c['day']))
                validate_state(json.loads(json.dumps(r.state)))
        (off, none), (on, boost) = got['off'], got['on']
        self.assertEqual(none, 0)
        self.assertGreater(off, 0)
        self.assertEqual(on, off + boost)
        self.assertLessEqual(abs(boost - off / 2), 3)     # one fraction per earning row at most

    def test_a_shop_job_counts_its_margin_and_its_pay_row_once(self):
        s, c = opened('grocery')   # any career: task_done's bonus_base is a shop's margin (clothing passes it)
        t = E.make_task('grocery', c['day'], 0, c['turn'])
        c['tasks'].append(t)
        with mock.patch.object(ib, 'on_job', wraps=ib.on_job) as job, mock.patch.object(ib, 'book', wraps=ib.book) as book:
            E.task_done(s, c, t, 100, 'Đã bán.', bonus_base=40)
        self.assertEqual(job.call_args.args[2:], (40, t['id']))   # the margin, as the gear counts it
        self.assertEqual(book.call_args_list[0].args[1], 20)      # 50 % of 40, and nothing on the 100-xu pay row itself
        self.assertNotIn(50, [x.args[1] for x in book.call_args_list])


@mock.patch.dict(os.environ, ON)
class Quay(unittest.TestCase):
    def test_the_owner_take_is_half_again_and_the_page_shows_it(self):
        from tests.test_quay_business import fixture

        def sale(env):
            with mock.patch.dict(os.environ, env):
                s, st = fixture(staff=False)
                qb.settle(s, now=1000)
                st['business']['stock']['hong_tra'] = 50
                st['menu'] = dict(on=['hong_tra'], p={'hong_tra': 1000})
                before = st['till'] + st['fund']
                qb.sale(st, ['hong_tra'], 1000000)
                return st['till'] + st['fund'] - before, qb.unit_cost(st, 'hong_tra'), qb.public(st)
        (off, cost, view_off), (on, cost2, view_on) = sale(OFF), sale(ON)
        self.assertEqual(cost, cost2)
        self.assertLessEqual(abs((on - cost) - (off - cost) * 3 / 2), 1)   # the take: what the sale left above the goods' cost
        self.assertEqual((view_off['bonus_percent'], view_on['bonus_percent']), (124, 236))
        self.assertEqual((view_off['staff_bonus_percent'], view_on['staff_bonus_percent']), (236, 404))

    def test_a_rich_owner_takes_plus_20(self):
        from tests.test_quay_business import fixture
        s, st = fixture(staff=False)
        qb.settle(s, now=1000)
        s['journey']['wallet'] = 2 * 10**9
        with qb.chain_scope(s):
            self.assertEqual((qb.take(124), qb.public(st)['bonus_percent']), (168, 168))
        self.assertEqual(qb.take(124, s), 168)


@mock.patch.dict(os.environ, ON)
class Wallet(unittest.TestCase):
    def test_rent_contracts_and_chests(self):
        from game import housing, town_treasure
        s = story()
        self.assertEqual(housing._earned(s, 300, 'k'), 450)
        self.assertEqual(housing._earned(new_state(), 300, 'k'), 300)
        self.assertEqual((town_treasure.reward(), town_treasure.reward(s)), (15000, 15000))
        s['journey']['wallet'] = 2 * 10**9
        self.assertEqual((housing._earned(s, 300, 'k'), town_treasure.reward(s)), (360, 12000))
        s['journey']['wallet'] = 0
        with mock.patch.dict(os.environ, OFF):
            self.assertEqual((housing._earned(s, 300, 'k'), town_treasure.reward()), (300, 10000))


if __name__ == '__main__':
    unittest.main()
