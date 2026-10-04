"""#oldcost (owner, 04/10/2026): "người ta đổi nghề rồi mà vẫn trừ tiền ở nghề cũ".

A player who moved on from a workplace kept paying for it: every started place they were
not working at paid 4-11 xu "duy trì khi vắng chủ" each life day (fund first, then the
wallet), shown at the end of the day as one wallet chip "Nơi làm khác −56". Now:

* a place you are away from costs nothing: its fund, stock, staff and bills wait, frozen;
* the only leaving cost is the one-time "Bỏ dở việc" fine, shown with its exact amount in
  the confirm dialog and written "Phạt bỏ dở ca ở <nơi>" in the books;
* reopening a place paused under the old rules is free.
"""
import copy
import unittest

from game import abandon as ab
from game import journey as jr
from game.engine import GameError, apply_action, public_state, validate_state

A, B = 'grocery', 'milk_tea'


def story(seed=11):
    from game.engine import new_state
    s = new_state()
    jr.enable_story(s, seed)
    s['journey']['gender'] = 'female'
    s['journey']['intro'] = True
    return s


def act(s, where, action, **p):
    return apply_action(s, where, action, p)


def work_day(s, cid):
    s, _ = act(s, cid, 'select_career')
    s, _ = act(s, cid, 'start_day')
    s, r = act(s, cid, 'end_day', carry_event=True)
    return s, r


def career_a(days=3):
    """A few days at the grocery, with a hired helper (wages, bills) and its stock."""
    s = story()
    s, _ = work_day(s, A)
    s['careers'][A]['money'] += 200   # enough to hire (fixture: keep the ledger identity)
    s['careers'][A]['ops']['finance']['opening_balance'] += 200
    s, _ = act(s, A, 'ops_hire', candidate=f'{A}-staff-1', confirm=True)
    for _ in range(days - 1):
        s, _ = work_day(s, A)
    validate_state(s)
    return s


def frozen(c):
    """Everything of a workplace that money or time could touch while you are away."""
    return copy.deepcopy(dict(money=c['money'], ledger=c['ops']['finance']['ledger'], bills=c['ops']['finance']['bills'],
                              staff=c['ops']['staff'], inv=(c.get('ext') or {}).get('inv'), day=c['day'], open=c['open']))


def lines_for(s, cid, since):
    return [h for h in s['journey']['history'][since:] if h.get('career') == cid]


class SwitchThenPlayElsewhere(unittest.TestCase):
    def assert_left_alone(self, s, days=4):
        """Play B for `days` life days: A must not move, the wallet only pays rent & meals."""
        a0, hist = frozen(s['careers'][A]), len(s['journey']['history'])
        for _ in range(days):
            wallet = s['journey']['wallet']
            s, r = work_day(s, B)
            jr_line = r['summary']['journey']
            self.assertEqual(jr_line['upkeep'], 0)   # no "Nơi làm khác −X" chip
            self.assertFalse(any('vắng chủ' in e for e in r['effects']))
            gained = jr_line['salary'] + jr_line.get('x3', 0) + jr_line.get('gift', 0)
            self.assertGreaterEqual(s['journey']['wallet'], wallet - jr_line['living'] + gained - 0)
        self.assertEqual(frozen(s['careers'][A]), a0)
        self.assertEqual(lines_for(s, A, hist), [])
        self.assertFalse(any(h['kind'] == 'upkeep' for h in s['journey']['history'][hist:]))
        validate_state(s)
        return s

    def test_switch_after_closing_the_shift(self):
        # 📋 Danh sách / the town map / Hành trình all send select_career.
        s = career_a()
        self.assertTrue(s['careers'][A]['ops']['staff'])
        s, r = act(s, B, 'select_career')
        self.assertNotIn('abandon', r)
        self.assert_left_alone(s)

    def test_switch_past_closing_time_with_the_shift_left_open(self):
        # 1.6.2 (#140): past closing time you walk over for free, work in hand waits.
        from game import dayclock as dc
        s = career_a()
        s, _ = act(s, A, 'select_career')
        s, _ = act(s, A, 'start_day')
        t = next(t for t in s['careers'][A]['tasks'] if t['status'] not in ab.DONE)
        t['status'] = 'in_progress'
        s['careers'][A]['turn'] += 60
        self.assertTrue(dc.past_close(s['careers'][A], A))
        s, r = act(s, B, 'select_career')
        self.assertTrue(r['abandon']['soft'])
        self.assertTrue(s['careers'][A]['open'])   # the shift waits for you
        s = self.assert_left_alone(s)
        s, _ = act(s, A, 'select_career')       # back: close it, nothing was taken meanwhile
        act(s, A, 'end_day', carry_event=True)

    def test_bo_do_viec_is_one_fine_shown_before_and_labelled(self):
        s = career_a()
        s, _ = act(s, A, 'select_career')
        s, _ = act(s, A, 'start_day')
        t = next(t for t in s['careers'][A]['tasks'] if t['status'] not in ab.DONE)
        t['status'] = 'in_progress'
        preview = public_state(s)['abandon']['preview']
        self.assertGreater(preview['fine'], 0)
        # The refusal (and the dialog built from the same preview) names the exact amount.
        with self.assertRaises(GameError) as err:
            act(s, B, 'select_career')
        self.assertEqual(err.exception.code, 'abandon_confirm')
        self.assertIn(f'phạt {preview["fine"]} xu', str(err.exception))
        money = s['careers'][A]['money']
        s, r = act(s, B, 'select_career', confirm=True)
        x = r['abandon']
        self.assertEqual(x['fine'], preview['fine'])
        self.assertEqual(x['label'], 'Phạt bỏ dở ca')
        self.assertEqual(s['careers'][A]['money'], money - x['fine'])
        row = s['careers'][A]['ops']['finance']['ledger'][-1]
        self.assertEqual(row['category'], 'abandon_fine')
        self.assertTrue(row['reason'].startswith(f'Phạt bỏ dở ca ở {ab._place(A)}'))
        # ... and nothing after it.
        self.assert_left_alone(s)

    def test_owner_fine_short_fund_is_labelled_in_the_wallet(self):
        s = career_a()
        s, _ = act(s, A, 'select_career')
        s, _ = act(s, A, 'start_day')
        t = next(t for t in s['careers'][A]['tasks'] if t['status'] not in ab.DONE)
        t['status'] = 'in_progress'
        c = s['careers'][A]
        c['ops']['finance']['opening_balance'] -= c['money'] - 1
        c['money'] = 1
        s['journey']['wallet'] = 500
        s, r = act(s, B, 'select_career', confirm=True)
        x = r['abandon']
        self.assertEqual((x['fund'], x['wallet']), (1, x['fine'] - 1))
        h = s['journey']['history'][-1]
        self.assertEqual((h['kind'], h['amount'], h['career']), ('incident', -(x['fine'] - 1), A))
        self.assertEqual(h['label'], f'Phạt bỏ dở ca ở {ab._place(A)} · quỹ thiếu, trừ ví')
        self.assertNotIn('trừ lương', h['label'])   # a shop you own pays no "lương"
        validate_state(s)

    def test_employee_fine_says_pay_docked(self):
        from game.employment import hired_record
        s = story()
        s['journey']['unlocked'].append('delivery') if 'delivery' not in s['journey']['unlocked'] else None
        s['careers']['delivery']['job'] = hired_record('delivery')
        s, _ = act(s, 'delivery', 'select_career', confirm=True)
        s, _ = act(s, 'delivery', 'start_day')
        t = next(t for t in s['careers']['delivery']['tasks'] if t['status'] not in ab.DONE)
        t['status'] = 'in_progress'
        s, r = act(s, B, 'select_career', confirm=True)
        h = s['journey']['history'][-1]
        self.assertEqual(h['label'], f'Phạt bỏ dở ca ở {ab._place("delivery")} · trừ lương')
        self.assertEqual(h['amount'], -r['abandon']['wallet'])

    def test_photobooth_report_many_old_places_cost_nothing(self):
        # "làm photobooth cuối ngày khép ca, chỗ ví còn 'nơi làm khác -56'": many started places.
        s = story()
        places = [cid for cid in jr.CH_UNLOCKS[1] if cid in s['careers'] and not jr._employed(cid)][:6]
        for cid in places:
            s, _ = work_day(s, cid)
        here, others = places[-1], places[:-1]
        before = {cid: frozen(s['careers'][cid]) for cid in others}
        wallet = s['journey']['wallet']
        s, r = work_day(s, here)
        jr_line = r['summary']['journey']
        self.assertEqual(jr_line['upkeep'], 0)
        self.assertEqual(s['journey']['wallet'], wallet - jr_line['living'] + jr_line['salary'] + jr_line.get('x3', 0))
        for cid in others:
            self.assertEqual(frozen(s['careers'][cid]), before[cid], cid)

    def test_journey_view_says_away_costs_nothing(self):
        s = career_a()
        s, _ = act(s, B, 'select_career')
        places = public_state(s)['journey']['places']
        self.assertEqual(places[A]['upkeep'], 0)
        self.assertEqual(jr.REOPEN_FEE, 0)


class OldPausedPlace(unittest.TestCase):
    def test_paused_under_old_rules_reopens_free(self):
        s = career_a()
        s, _ = act(s, B, 'select_career')
        s['journey']['paused'][A] = s['journey']['life_day']   # paused by 1.6.2 to dodge the old fee
        validate_state(s)
        a0, wallet = frozen(s['careers'][A]), s['journey']['wallet']
        s, r = act(s, None, 'jr_reopen', career=A, confirm=True)
        self.assertNotIn(A, s['journey']['paused'])
        self.assertEqual(frozen(s['careers'][A]), a0)
        self.assertEqual(s['journey']['wallet'], wallet)
        self.assertIn('không tốn phí', r['message'])
        s, _ = act(s, A, 'select_career')
        act(s, A, 'start_day')


class PastFeesRefund(unittest.TestCase):
    """Owner 04/10/2026 "làm hoàn phí đi": every old idle fee comes back to the wallet once, on load."""

    def test_the_old_fees_come_back_once(self):
        from game.engine import migrate_state
        s = story()
        s['journey']['stats']['upkeep_paid'] = 56
        wallet = s['journey']['wallet']
        s = migrate_state(copy.deepcopy(s))
        validate_state(s)
        j = s['journey']
        self.assertEqual(j['wallet'], wallet + 56)
        self.assertEqual(j['stats']['upkeep_paid'], 0)
        self.assertEqual((j['history'][-1]['amount'], j['history'][-1]['label']), (56, jr.REFUND_LABEL))
        again = migrate_state(copy.deepcopy(s))
        self.assertEqual(again['journey']['wallet'], wallet + 56)
        self.assertEqual(len(again['journey']['history']), len(j['history']))

    def test_a_wallet_in_debt_is_refunded_too(self):
        s = story()
        j = s['journey']
        j['wallet'], j['in_debt'], j['stats']['upkeep_paid'] = -20, True, 33
        jr.upgrade(j)
        self.assertEqual(j['wallet'], 13)
        self.assertFalse(j['in_debt'])

    def test_nothing_paid_nothing_written(self):
        s = story()
        n = len(s['journey']['history'])
        jr.upgrade(s['journey'])
        self.assertEqual(len(s['journey']['history']), n)


if __name__ == '__main__':
    unittest.main()
