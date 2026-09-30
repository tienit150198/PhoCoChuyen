"""Bỏ dở việc: leaving a workplace mid-work to try another one (game/abandon.py)."""
import copy
import unittest

from game import abandon as ab
from game import journey as jr
from game.content import CAREERS
from game.employment import hired_record, required
from game.engine import GameError, apply_action, new_state, public_state, validate_state, migrate_state


def story(seed=7):
    s = new_state()
    jr.enable_story(s, seed)
    s['journey']['gender'] = 'female'
    s['journey']['intro'] = True
    return s


def open_place(s, cid):
    """Unlock, hire (employed jobs) and open the day at `cid`."""
    j = s['journey']
    if cid not in j['unlocked']:
        j['unlocked'].append(cid)
        s['careers'][cid]['started'] = True  # a place you already worked at may stay unlocked
    if required(cid) and s['careers'][cid]['job']['status'] != 'hired':
        s['careers'][cid]['job'] = hired_record(cid)
    s, _ = apply_action(s, cid, 'select_career', {'confirm': True})
    s, _ = apply_action(s, cid, 'start_day')
    return s


def start_first(s, cid):
    """One work step on the first job (what kit.start_work does)."""
    t = next(t for t in s['careers'][cid]['tasks'] if t['status'] not in ab.DONE)
    t['status'] = 'in_progress'
    return t


class NothingInProgress(unittest.TestCase):
    def test_closed_day_costs_nothing(self):
        s = story()
        s, _ = apply_action(s, 'grocery', 'select_career')
        s, r = apply_action(s, 'milk_tea', 'select_career')
        self.assertNotIn('abandon', r)
        self.assertIsNone(s['journey'].get('abandon'))

    def test_day_ended_properly_costs_nothing(self):
        s = open_place(story(), 'grocery')
        start_first(s, 'grocery')
        s, _ = apply_action(s, 'grocery', 'end_day', {'carry_event': True})
        money = s['careers']['grocery']['money']
        self.assertIsNone(public_state(s)['abandon']['preview'])
        s, r = apply_action(s, 'milk_tea', 'select_career')
        self.assertNotIn('abandon', r)
        self.assertEqual(s['careers']['grocery']['money'], money)

    def test_same_place_is_not_a_switch(self):
        s = open_place(story(), 'grocery')
        start_first(s, 'grocery')
        s, r = apply_action(s, 'grocery', 'select_career')
        self.assertNotIn('abandon', r)

    def test_looking_is_not_switching(self):
        s = open_place(story(), 'grocery')
        before = copy.deepcopy(s['careers']['grocery'])
        public_state(s, full='milk_tea')  # reading another place's info
        self.assertEqual(s['careers']['grocery'], before)


class StartedTask(unittest.TestCase):
    def setUp(self):
        self.s = open_place(story(), 'grocery')
        self.t = start_first(self.s, 'grocery')

    def test_refused_without_confirm(self):
        with self.assertRaises(GameError) as cm:
            apply_action(self.s, 'milk_tea', 'select_career')
        self.assertEqual(cm.exception.code, 'abandon_confirm')
        self.assertIn('Đang làm dở', str(cm.exception))
        self.assertEqual(self.s['current'], 'grocery')

    def test_other_commands_cannot_slip_away(self):
        with self.assertRaises(GameError) as cm:
            apply_action(self.s, 'milk_tea', 'start_day', {'confirm': True})
        self.assertEqual(cm.exception.code, 'abandon_confirm')

    def test_penalty_once(self):
        s = self.s
        preview = public_state(s)['abandon']['preview']
        self.assertEqual(preview['started'], 1)
        c0 = s['careers']['grocery']
        money, trust = c0['money'], c0['incidents']['trust']
        waiting = sum(1 for t in c0['tasks'] if t['status'] not in ab.DONE) - 1
        s, r = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        x = r['abandon']
        c = s['careers']['grocery']
        # The dialog showed exactly what was applied.
        self.assertEqual((x['fine'], x['trust']), (preview['fine'], preview['trust']))
        self.assertGreater(x['fine'], 0)
        self.assertEqual(c['money'], money - x['fine'])
        self.assertEqual(c['incidents']['trust'], trust - x['trust'])
        row = [e for e in c['ops']['finance']['ledger'] if e['category'] == 'abandon_fine']
        self.assertEqual(len(row), 1)
        self.assertTrue(row[0]['reason'].startswith('Bỏ dở việc'))
        t = next(t for t in c['tasks'] if t['id'] == self.t['id'])
        self.assertEqual(t['status'], 'cancelled')
        self.assertIn(t['id'], c['completed_ids'])
        self.assertEqual(x['walked'], waiting)
        self.assertTrue(all(t['status'] in ab.DONE for t in c['tasks']))
        review = next(p for p in c['feed'] if p['source'] == self.t['id'])
        self.assertIn(review['stars'], (1, 2))
        self.assertTrue(any(j['kind'] == 'abandon' and 'nhắn' in j['text'] for j in c['journal']))
        validate_state(s)
        # Once: going back and leaving again with nothing in progress costs nothing more.
        s, _ = apply_action(s, 'grocery', 'select_career')
        s, r = apply_action(s, 'milk_tea', 'select_career')
        self.assertNotIn('abandon', r)
        self.assertEqual(len([e for e in s['careers']['grocery']['ops']['finance']['ledger'] if e['category'] == 'abandon_fine']), 1)

    def test_day_summary_lists_it(self):
        s, r = apply_action(self.s, 'milk_tea', 'select_career', {'confirm': True})
        s, _ = apply_action(s, 'grocery', 'select_career')
        s, r = apply_action(s, 'grocery', 'end_day', {'carry_event': True})
        x = r['summary']['abandon']
        self.assertEqual(x['count'], 1)
        self.assertGreater(x['fine'], 0)
        validate_state(s)

    def test_deterministic(self):
        a = apply_action(self.s, 'milk_tea', 'select_career', {'confirm': True})
        b = apply_action(self.s, 'milk_tea', 'select_career', {'confirm': True})
        self.assertEqual(a[1]['abandon'], b[1]['abandon'])
        self.assertEqual(a[0]['careers']['grocery']['feed'], b[0]['careers']['grocery']['feed'])


class PromisedOrder(unittest.TestCase):
    def test_promised_order_is_charged_once_and_kept(self):
        s = open_place(story(), 'grocery')
        c = s['careers']['grocery']
        for t in c['tasks']:
            t['day'] = c['day'] - 1 if c['day'] > 1 else t['day']
        t = c['tasks'][0]
        t['bulk'] = dict(stage='deliver', offers=[], price=90, deposit=30, delivered={})  # deposit taken, due today
        self.assertTrue(ab.started(t) and ab.kept(c, t))
        s, r = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        g = s['careers']['grocery']
        self.assertEqual(next(x for x in g['tasks'] if x['id'] == t['id'])['status'], t['status'])  # the order stays
        self.assertEqual(r['abandon']['jobs'], 0)
        s, _ = apply_action(s, 'grocery', 'select_career')
        s, r = apply_action(s, 'milk_tea', 'select_career')  # already charged: no second fine
        self.assertNotIn('abandon', r)


class Escalation(unittest.TestCase):
    def test_repeat_escalates_and_warns(self):
        s = open_place(story(), 'grocery')
        fines, warns = [], []
        for _ in range(3):
            start_first(s, 'grocery')
            s, r = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
            fines.append(r['abandon']['fine'])
            warns.append(r['abandon']['warn'])
            s, _ = apply_action(s, 'grocery', 'select_career')
            s, _ = apply_action(s, 'grocery', 'more_work')
        self.assertLess(fines[0], fines[1])
        self.assertEqual(warns, [False, True, True])
        self.assertIn('khách', r['abandon']['line'])  # a neighbour, not a boss, for a place you own
        validate_state(s)

    def test_boss_warns_before_anything_else(self):
        s = open_place(story(), 'delivery')
        lines = []
        for _ in range(3):
            start_first(s, 'delivery')
            s, r = apply_action(s, 'grocery', 'select_career', {'confirm': True})
            lines.append(r['abandon']['line'])
            s, _ = apply_action(s, 'delivery', 'select_career')
            s, _ = apply_action(s, 'delivery', 'more_work')
        self.assertNotIn('cho nghỉ', lines[0])
        self.assertIn('cho nghỉ', lines[1])
        self.assertIn('cho nghỉ', lines[2])
        self.assertEqual(s['careers']['delivery']['job']['status'], 'hired')  # warned, never fired
        validate_state(s)

    def test_new_day_resets_the_count(self):
        s = open_place(story(), 'grocery')
        start_first(s, 'grocery')
        s, r1 = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        s, _ = apply_action(s, 'grocery', 'select_career')
        s, _ = apply_action(s, 'grocery', 'end_day', {'carry_event': True})
        s, _ = apply_action(s, 'grocery', 'start_day')
        start_first(s, 'grocery')
        self.assertEqual(public_state(s)['abandon']['preview']['offence'], 1)


class Pockets(unittest.TestCase):
    def test_owner_pays_from_the_fund(self):
        s = open_place(story(), 'grocery')
        start_first(s, 'grocery')
        wallet = s['journey']['wallet']
        s, r = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        self.assertEqual(r['abandon']['pocket'], 'fund')
        self.assertEqual(r['abandon']['fund'], r['abandon']['fine'])
        self.assertEqual(s['journey']['wallet'], wallet)

    def test_employee_pay_is_docked_and_boss_trust_drops(self):
        s = open_place(story(), 'delivery')
        start_first(s, 'delivery')
        wallet, fund = s['journey']['wallet'], s['careers']['delivery']['money']
        preview = public_state(s)['abandon']['preview']
        self.assertEqual(preview['trust_kind'], 'employer')
        s, r = apply_action(s, 'grocery', 'select_career', {'confirm': True})
        x = r['abandon']
        self.assertEqual(x['pocket'], 'wallet')
        self.assertEqual(s['journey']['wallet'], wallet - x['fine'])
        self.assertEqual(s['careers']['delivery']['money'], fund)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'incident')
        self.assertEqual(ab.trust_value(s, 'delivery'), ab.TRUST_START - x['trust'])
        self.assertEqual(public_state(s)['abandon']['trust']['delivery'], ab.TRUST_START - x['trust'])
        validate_state(s)

    def test_employee_short_wallet_falls_back_to_pay(self):
        s = open_place(story(), 'delivery')
        start_first(s, 'delivery')
        s['journey']['wallet'] = 2
        fund = s['careers']['delivery']['money']
        s, r = apply_action(s, 'grocery', 'select_career', {'confirm': True})
        x = r['abandon']
        self.assertEqual(x['wallet'], 2)
        self.assertEqual(s['careers']['delivery']['money'], fund - (x['fine'] - 2))

    def test_office_boss_trust(self):
        s = open_place(story(), 'corp_accounting')
        start_first(s, 'corp_accounting')
        o = s['careers']['corp_accounting']['ext']['data']['office']
        before = o['trust']
        s, r = apply_action(s, 'grocery', 'select_career', {'confirm': True})
        o = s['careers']['corp_accounting']['ext']['data']['office']
        self.assertEqual(r['abandon']['trust_kind'], 'office')
        self.assertEqual(o['trust'], before - r['abandon']['trust'])
        self.assertEqual(o['day_trust'], -r['abandon']['trust'])  # shows in the office day summary
        validate_state(s)


class SandboxAndDev(unittest.TestCase):
    def test_story_off_only_warns(self):
        s = new_state()  # the free sandbox (also every MNL_DEV sweep: the server runs without the story)
        s, _ = apply_action(s, 'grocery', 'select_career')
        s, _ = apply_action(s, 'grocery', 'start_day')
        start_first(s, 'grocery')
        money = s['careers']['grocery']['money']
        preview = public_state(s)['abandon']['preview']
        self.assertTrue(preview['soft'])
        self.assertEqual(preview['fine'], 0)
        s, r = apply_action(s, 'milk_tea', 'select_career')  # no confirm needed
        self.assertTrue(r['abandon']['soft'])
        self.assertEqual(s['careers']['grocery']['money'], money)
        self.assertTrue(any(t['status'] == 'in_progress' for t in s['careers']['grocery']['tasks']))
        self.assertIsNone(s['journey'].get('abandon'))

    def test_harness_sweep_switches_freely(self):
        """browser_v04's path: select → start_day → next career, over and over, story off."""
        s = new_state()
        for cid in ('grocery', 'milk_tea', 'florist', 'teacher', 'corp_accounting', 'grocery'):
            if required(cid):
                s['careers'][cid]['job'] = hired_record(cid)
            s, _ = apply_action(s, cid, 'select_career')
            if not s['careers'][cid]['open']:
                s, _ = apply_action(s, cid, 'start_day')
            start_first(s, cid)
        validate_state(s)

    def test_internal_commands_are_not_switches(self):
        s = open_place(story(), 'grocery')
        start_first(s, 'grocery')
        s2 = copy.deepcopy(s)
        self.assertIsNone(ab.check(s2, 'milk_tea', {}, internal=True))


class Saves(unittest.TestCase):
    def test_validate_rejects_bad_book(self):
        s = open_place(story(), 'grocery')
        start_first(s, 'grocery')
        s, _ = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        validate_state(s)
        for bad in (lambda b: b.update(v=2), lambda b: b['places']['grocery'].update(trust=101),
                    lambda b: b['places'].update(nowhere=b['places']['grocery']),
                    lambda b: b['places']['grocery']['log'].append(dict(day=1)),
                    lambda b: b['places']['grocery'].update(today=5)):
            x = copy.deepcopy(s)
            bad(x['journey']['abandon'])
            with self.assertRaises(GameError):
                validate_state(x)

    def test_old_save_without_book_loads_and_plays(self):
        s = open_place(story(), 'grocery')
        start_first(s, 'grocery')
        s['journey'].pop('abandon', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIsNotNone(public_state(s)['abandon']['preview'])
        s, r = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        self.assertIn('abandon', r)
        validate_state(s)


class EveryWorkplace(unittest.TestCase):
    def test_abandon_then_keep_playing(self):
        """Every career: walk off a started job, validate, come back, close and reopen the day."""
        for cid in CAREERS:
            with self.subTest(cid=cid):
                other = 'milk_tea' if cid != 'milk_tea' else 'grocery'
                s = open_place(story(), cid)
                start_first(s, cid)
                s, r = apply_action(s, other, 'select_career', {'confirm': True})
                self.assertIn('abandon', r)
                validate_state(s)
                s, _ = apply_action(s, cid, 'select_career')
                s, _ = apply_action(s, cid, 'end_day', {'carry_event': True})
                s, _ = apply_action(s, cid, 'start_day')
                validate_state(s)
                public_state(s)


if __name__ == '__main__':
    unittest.main()
