"""Pharmacy counter desk: clinic stamps, recalls, the cold chain, look-alike
names, the tip temptation, supplier checks and the inspection."""
import unittest

from game import desk, desk_content as dc
from game.content import LOT_INDEX
from game.engine import GameError, public_state, validate_state
from tests.desk_support import Journey, desk_journey, find_case, flag_all, reports, review, roundtrip, secrets, solve_desk

DAYS = range(1, 60)


def field(case, ref):
    did, fid = ref.split('.')
    doc = next(d for d in case['docs'] if d['id'] == did)
    return next(f for f in doc['fields'] if f['id'] == fid)


class StampRegistryTests(unittest.TestCase):
    def test_stamps_change_every_four_days_and_never_collide(self):
        seen = set()
        for day in range(1, 40):
            reg = dc.stamps(day)
            self.assertEqual(len(set(reg.values())), 3, day)  # three clinics, three different stamps
            seen.add(tuple(sorted(reg.items())))
        self.assertGreaterEqual(len(seen), 8)
        self.assertEqual([when for when, *_ in dc.stamp_changes(15)], [3, 7, 11, 15])

    def test_the_bulletin_announces_the_new_stamp_and_retires_the_old(self):
        when, clinic, old, new = dc.stamp_changes(3)[0]
        b = dc.bulletin('pharmacy', when)
        self.assertEqual(b['stamps'][clinic], new)
        text = ' '.join(b['notices'])
        self.assertIn(dc.stamp_text(new), text)
        self.assertIn('hết dùng', text)
        self.assertIn('ph_stamp', [r['id'] for r in b['rules'] if r['new']])

    def test_every_valid_slip_carries_todays_stamp(self):
        for day in range(1, 30):
            for slot in range(6):
                v = dc.plan('pharmacy', day, slot)
                if not v:
                    continue
                case, b, _ = dc.build('pharmacy', v, day, slot)
                slip = next((d for d in case['docs'] if d['id'] == 'slip'), None)
                if not slip or v == 'ph_stamp':
                    continue
                clinic = next(k for k, name in dc.CLINICS.items() if name == field(case, 'slip.clinic')['value'])
                self.assertEqual(field(case, 'slip.stamp')['mark'], b['stamps'][clinic], (day, slot, v))

    def test_forged_stamp_is_caught_and_referred(self):
        j = desk_journey('pharmacy', 'ph_stamp')
        case = secrets(j)
        clinic = next(k for k, name in dc.CLINICS.items() if name == field(case, 'slip.clinic')['value'])
        self.assertNotEqual(field(case, 'slip.stamp')['mark'], dc.stamps(j.task['day'])[clinic])
        t = solve_desk(j)
        self.assertEqual((t['verdict'], t['grade']), ('refer', 'perfect'))

    def test_late_game_forgeries_use_the_retired_stamp(self):
        day, slot = find_case('pharmacy', 'ph_stamp', lambda c: 'mẫu cũ' in c['issues'][0]['why'], days=range(9, 80), slots=range(12))
        case, b, _ = dc.build('pharmacy', 'ph_stamp', day, slot)
        mark = field(case, 'slip.stamp')['mark']
        self.assertIn(mark, [old for _, _, old, _ in dc.stamp_changes(day)])
        self.assertNotIn(mark, b['stamps'].values())

    def test_giving_on_a_forged_slip_is_risky(self):
        j = desk_journey('pharmacy', 'ph_stamp')
        t = solve_desk(j, verdict='give')
        self.assertEqual(t['grade'], 'wrong')
        self.assertEqual(j.c['ext']['data']['desk']['risk'], 3)


class RecallTests(unittest.TestCase):
    def test_recall_list_grows_with_the_tier_and_is_in_the_rulebook(self):
        self.assertEqual(dc.recall_lots(1), [])
        self.assertEqual(len(dc.recall_lots(3)), 1)
        self.assertEqual(len(dc.recall_lots(8)), 2)
        rule = next(r for r in dc.bulletin('pharmacy', 8)['rules'] if r['id'] == 'ph_recall')
        for lot in dc.recall_lots(8):
            self.assertIn(lot, rule['text'])

    def test_only_the_recall_case_puts_a_recalled_lot_on_the_tray(self):
        for day in range(2, 30):
            recall = set(dc.recall_lots(day))
            for slot in range(6):
                v = dc.plan('pharmacy', day, slot)
                if not v:
                    continue
                case, _, _ = dc.build('pharmacy', v, day, slot)
                tray = next((d for d in case['docs'] if d['id'] == 'tray'), None)
                if tray:
                    self.assertEqual(field(case, 'tray.lot')['value'] in recall, v == 'ph_recall', (day, slot, v))

    def test_swap_the_recalled_box(self):
        j = desk_journey('pharmacy', 'ph_recall')
        self.assertIn(field(secrets(j), 'tray.lot')['value'], dc.recall_lots(j.task['day']))
        self.assertEqual(solve_desk(j)['verdict'], 'fix')
        k = desk_journey('pharmacy', 'ph_recall')
        self.assertEqual(solve_desk(k, verdict='give')['grade'], 'wrong')


class ColdChainTests(unittest.TestCase):
    def test_warm_fridge_blocks_the_cold_item(self):
        j = desk_journey('pharmacy', 'ph_cold')
        t = solve_desk(j)
        self.assertEqual((t['verdict'], t['grade']), ('refer', 'perfect'))

    def test_skipping_the_fridge_log_is_only_good(self):
        j = desk_journey('pharmacy', 'ph_cold')
        j.act('ask')
        j.act('desk_decide', task=j.task['id'], verdict='refer', confirm=True)
        self.assertEqual(j.get(j.c['completed_ids'][-1])['grade'], 'good')

    def test_even_a_clean_cold_order_needs_the_fridge_log(self):
        j = desk_journey('pharmacy', 'ph_clean', lambda c: bool(c['needs']), days=range(3, 80))
        self.assertIn('fridge', secrets(j)['needs'])
        j.act('ask')
        j.act('desk_decide', task=j.task['id'], verdict='give', confirm=True)
        self.assertEqual(j.get(j.c['completed_ids'][-1])['grade'], 'good')
        k = desk_journey('pharmacy', 'ph_clean', lambda c: bool(c['needs']), days=range(3, 80))
        self.assertEqual(solve_desk(k)['grade'], 'perfect')


class CounterTests(unittest.TestCase):
    def test_tip_temptation(self):
        j = desk_journey('pharmacy', 'ph_norx')
        money = j.c['money']
        t = solve_desk(j, verdict='give')
        self.assertEqual(t['grade'], 'wrong')
        # The customer offers 10 xu, but after a wrong hand-off cô Thu hands it back: nothing is earned.
        self.assertEqual(j.c['money'], money)
        self.assertFalse(any(x['category'] == 'tip' for x in j.c['ops']['finance']['ledger']))
        k = desk_journey('pharmacy', 'ph_norx')
        t = solve_desk(k)
        self.assertEqual((t['verdict'], t['grade']), ('refuse', 'perfect'))
        self.assertEqual(k.last['desk_result']['tip'], 0)
        validate_state(j.state)

    def test_no_slip_is_fine_for_everyday_items(self):
        t = solve_desk(desk_journey('pharmacy', 'ph_otc'))
        self.assertEqual((t['verdict'], t['grade']), ('give', 'perfect'))

    def test_lookalike_and_strength(self):
        j = desk_journey('pharmacy', 'ph_lookalike')
        j.act('ask')
        r = j.act('desk_flag', task=j.task['id'], field='tray.name', rule='ph_name')
        self.assertEqual(r['mark'], 'found')
        j.act('desk_decide', task=j.task['id'], verdict='fix', confirm=True)
        self.assertEqual(j.get(j.c['completed_ids'][-1])['grade'], 'perfect')
        # a different strength cannot be "fixed" at the counter when the shelf is empty
        k = desk_journey('pharmacy', 'ph_strength')
        self.assertEqual(solve_desk(k, verdict='fix')['grade'], 'wrong')

    def test_quantity_is_trimmed_to_the_slip(self):
        t = solve_desk(desk_journey('pharmacy', 'ph_qty'))
        self.assertEqual((t['verdict'], t['grade']), ('fix', 'perfect'))

    def test_pickup_line_decides_who_may_collect(self):
        ok = desk_journey('pharmacy', 'ph_proxy', lambda c: not c['issues'])
        self.assertEqual(solve_desk(ok)['verdict'], 'give')
        bad = desk_journey('pharmacy', 'ph_proxy', lambda c: bool(c['issues']))
        self.assertEqual(solve_desk(bad)['verdict'], 'refer')
        bad2 = desk_journey('pharmacy', 'ph_proxy', lambda c: bool(c['issues']))
        self.assertEqual(solve_desk(bad2, verdict='give')['grade'], 'wrong')

    def test_cheap_supplier_lot_without_silver_thread(self):
        fake = desk_journey('pharmacy', 'ph_supplier', lambda c: bool(c['issues']))
        self.assertEqual(len(secrets(fake)['issues']), 2)
        t = solve_desk(fake, verdict='accept')
        self.assertEqual(t['grade'], 'wrong')
        self.assertEqual(fake.c['ext']['data']['desk']['risk'], 4)
        legit = desk_journey('pharmacy', 'ph_supplier', lambda c: not c['issues'], days=range(4, 200), slots=range(12))
        self.assertEqual(solve_desk(legit)['verdict'], 'accept')

    def test_supplier_rule_arrives_on_day_four(self):
        self.assertNotIn('ph_supply', [r['id'] for r in dc.bulletin('pharmacy', 3)['rules']])
        self.assertIn('ph_supply', [r['id'] for r in dc.bulletin('pharmacy', 4)['rules'] if r['new']])
        self.assertTrue(all(d >= 4 for d in range(1, 30) for s in range(6) if dc.plan('pharmacy', d, s) == 'ph_supplier'))

    def test_inspection_asks_to_own_the_gaps(self):
        j = Journey('pharmacy', slot=0, day=8)
        self.assertEqual(j.task['variant'], 'ph_inspect')
        self.assertIn('ph_log', [r['id'] for r in dc.bulletin('pharmacy', 8)['rules']])
        self.assertEqual(len(secrets(j)['issues']), 2)  # the fridge gap shows up from tier 2
        t = solve_desk(j)
        self.assertEqual((t['verdict'], t['grade']), ('own', 'perfect'))
        k = Journey('pharmacy', slot=0, day=8)
        self.assertEqual(solve_desk(k, verdict='excuse')['grade'], 'wrong')


class RestockTests(unittest.TestCase):
    def test_parcel_is_received_only_once_it_shows_as_arrived(self):
        j = Journey('pharmacy')
        lot = next(k for k, v in LOT_INDEX.items() if v['status'] == 'available')
        before = j.c['stock'].get(lot, 0)
        j.act('order_stock', item=lot, qty=1)  # the distributor's midday run (order before 11:00)
        sid = j.c['shipments'][-1]['id']

        def shown():
            return next(x for x in public_state(j.state)['careers']['pharmacy']['shipments'] if x['id'] == sid)['ready_now']

        waited = 0
        while not shown():
            with self.assertRaises(GameError) as err:  # not a moment earlier than the parcel card says
                j.act('receive_stock', shipment=sid, count=1)
            self.assertNotIn('nhịp', err.exception.message)
            j.act('advance')
            waited += 1
            self.assertLess(waited, 40)
        self.assertGreaterEqual(waited, 12)  # 13:00 at the earliest, four hours and more after opening
        j.act('receive_stock', shipment=sid, count=1)
        self.assertEqual(j.c['stock'][lot], before + 1)
        validate_state(j.state)


class BacNamTests(unittest.TestCase):
    def test_chapter_one_needs_the_big_label(self):
        j = Journey('pharmacy', slot=1, day=2)
        j.act('ask')
        with self.assertRaises(GameError):  # the label row is locked until it is made
            j.act('desk_flag', task=j.task['id'], field='home.label', rule='ph_name')
        j.act('desk_decide', task=j.task['id'], verdict='give', confirm=True)
        self.assertEqual(j.get(j.c['completed_ids'][-1])['grade'], 'good')
        self.assertIn('nam_label', j.c['ext']['data']['desk']['flags'])

    def test_bac_nam_stays_out_of_the_shady_cases(self):
        for day in range(1, 40):
            for slot in range(6):
                v = dc.plan('pharmacy', day, slot)
                if v in ('ph_norx', 'ph_stamp'):
                    self.assertNotEqual(dc.build('pharmacy', v, day, slot)[0]['npc'], dc.STORY_NPC['pharmacy'])

    def test_story_days(self):
        self.assertEqual({d: dc.plan('pharmacy', d, 1) for d in dc.STORY_DAYS['pharmacy']}, {d: 'ph_story' for d in dc.STORY_DAYS['pharmacy']})


class ConsequenceTests(unittest.TestCase):
    """Doing the counter wrong costs stars, words in the review, a report, an inspection."""

    def test_right_hand_off_keeps_five_stars_and_full_pay(self):
        j = desk_journey('pharmacy', 'ph_clean')
        money = j.c['money']
        t = solve_desk(j)
        self.assertEqual(t['grade'], 'perfect')
        self.assertFalse(t.get('slips'))
        self.assertEqual(j.c['money'], money + desk.pay_for(t, 'perfect'))
        self.assertGreaterEqual(review(j, t['id'])['stars'], 4)
        self.assertEqual(t['reaction']['kind'], 'accept')

    def test_too_many_boxes_is_a_serious_mistake_named_in_the_review(self):
        j = desk_journey('pharmacy', 'ph_qty')
        money = j.c['money']
        t = solve_desk(j, verdict='give')
        self.assertEqual([x['code'] for x in t['slips']], ['give_ph_qty'])
        self.assertEqual(t['slips'][0]['sev'], 3)
        post = review(j, t['id'])
        self.assertLessEqual(post['stars'], 2)
        self.assertIn('Phiếu ghi 1 hộp mà quầy cứ thế đưa 3 hộp', post['text'])
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        self.assertEqual(j.c['money'], money)  # a wrong stamp earns nothing, and nothing is taken twice
        self.assertTrue(reports(j, t['id']))
        roundtrip(j)

    def test_wrong_medicine_is_refused_reported_and_inspected(self):
        for variant in ('ph_lookalike', 'ph_strength', 'ph_recall', 'ph_expired', 'ph_norx', 'ph_cold'):
            with self.subTest(variant=variant):
                j = desk_journey('pharmacy', variant)
                t = solve_desk(j, verdict='give')
                self.assertTrue(t['slips'][0]['safety'])
                self.assertEqual(review(j, t['id'])['stars'], 1)
                self.assertEqual(t['reaction']['kind'], 'refuse')
                self.assertTrue(reports(j, t['id']))
                self.assertIn('slip_drug_inspect', [f['script'] for f in j.c['incidents']['follow']])
                self.assertIn('kiểm tra', j.last['message'])
                roundtrip(j)

    def test_severity_scales_the_stars(self):
        small = desk_journey('pharmacy', 'ph_clean')
        t1 = solve_desk(small, verdict='refer')      # sev 1: an unneeded referral
        clear = desk_journey('pharmacy', 'ph_otc')
        t2 = solve_desk(clear, verdict='refuse')     # sev 2: a valid request refused
        bad = desk_journey('pharmacy', 'ph_lookalike')
        t3 = solve_desk(bad, verdict='give')         # safety: the wrong medicine
        s1, s2, s3 = review(small, t1['id'])['stars'], review(clear, t2['id'])['stars'], review(bad, t3['id'])['stars']
        self.assertGreater(s1, s2)
        self.assertGreater(s2, s3)
        self.assertEqual(s1, 4)

    def test_reaction_is_settled_once(self):
        from game import consequences as cq
        j = desk_journey('pharmacy', 'ph_norx')
        t = solve_desk(j, verdict='give')
        money = j.c['money']
        again = cq.react(j.state, j.c, t, 0)
        self.assertEqual((again['kind'], again['pay']), ('refuse', 0))
        self.assertEqual(j.c['money'], money)
        with self.assertRaises(GameError):
            j.act('desk_decide', task=t['id'], verdict='refuse', confirm=True)


if __name__ == '__main__':
    unittest.main()
