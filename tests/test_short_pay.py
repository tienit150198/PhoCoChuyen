"""Khách đưa thiếu tiền (game/short_pay.py through the shared till): the roll, every kind of customer
through every choice, the gap nobody noticed, IOUs paid back later, determinism, idempotency,
the tip contract, the public view and save validation."""
import copy
import json
import os
import unittest
from unittest import mock

from tests.helpers import Journey
from game import short_pay as SP
from game import tips
from game.careers import PLUGINS, till
from game.engine import GameError, public_state, validate_state

A = PLUGINS.get('clothing')


def ledger(j, tid, category=None):
    return [r for r in j.c['ops']['finance']['ledger'] if r['ref'] == tid and (category is None or r['category'] == category)]


def codes(t):
    return [x['code'] for x in t.get('slips') or []]


def billed(kind, pred=None, start=3):
    """A plain fitting-room sale billed with a customer of `kind` who pays short (the roll is forced)."""
    for day in range(start, 60):
        for slot in range(12):
            if (day, slot) in A.STORY:
                continue
            t = A.make_task(day, slot, 1)
            if t['kind'] != 'fit' or t['needs']['haggle'] or not SP.customer(t):
                continue
            if pred and not pred(t):
                continue
            j = Journey('clothing', slot=slot, day=day)
            j.act('ask', task=t['id'])
            for ln in t['needs']['lines']:
                j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
            with mock.patch.object(SP, '_forced', return_value=kind):
                j.act('ao_bill', task=t['id'])
            t = j.get(t['id'])
            if bool(kind) != bool(t['cash'].get('sp')):
                continue
            return j, t
    raise AssertionError('no such sale')


def pay(j, tid):
    t = j.get(tid)
    return j.act('ao_pay', task=tid, change=till.greedy(max(0, till.due(t['cash']))), confirm=True)


def short(j, tid, choice):
    return j.act('ao_short', task=tid, choice=choice)


def revenue(j, tid):
    return sum(r['amount'] for r in ledger(j, tid) if r['category'] not in ('tip',))


def close(j, t):
    return j.c.get('relationships', {}).get(t['npc'], 0)


@unittest.skipIf(A is None, 'clothing filtered out')
class RollTests(unittest.TestCase):
    def test_never_on_the_first_day_rare_later_and_pure(self):
        c = dict(day=5, shortpay=None)
        hits = {1: 0, 2: 0, 5: 0}
        n = {1: 0, 2: 0, 5: 0}
        with mock.patch.dict(os.environ, {'MNL_DEV': ''}):
            for day in (1, 2, 5):
                for slot in range(12):
                    for serial in range(1, 40):
                        t = dict(A.make_task(day, slot, serial), id=f'clothing-{day:04d}-{slot:02d}-{serial}')
                        if not SP.customer(t):
                            continue
                        r = SP.roll(c, t, 200)
                        self.assertEqual(r, SP.roll(c, t, 200))        # pure: the same task rolls the same
                        n[day] += 1
                        hits[day] += bool(r)
        self.assertEqual(hits[1], 0)
        self.assertLess(hits[2] / n[2], 0.08)
        self.assertTrue(0.02 < hits[5] / n[5] < 0.12)

    def test_amount_is_below_half_the_bill_and_the_notes_show_it(self):
        t = A.make_task(5, 1, 1)
        for kind in SP.KINDS:
            for price in (6, 9, 13, 40, 199, 850):
                with mock.patch.object(SP, '_forced', return_value=kind):
                    r = SP.roll(dict(day=5), dict(t, npc='clothing_npc_03'), price)
                if r is None:
                    self.assertTrue(all(x > price // 2 for x in SP.AMOUNTS[kind]))
                    continue
                self.assertEqual(r['kind'], kind)
                self.assertTrue(1 <= r['short'] <= price // 2)
                self.assertEqual(sum(SP.tender(price, r)), price - r['short'])

    def test_kind_follows_the_person(self):
        from game.content import NPC_INDEX
        kid = next(k for k, v in NPC_INDEX.items() if v['display_name'].startswith('Bé ') and v['career_id'] == 'pet_shop')
        elder = next(k for k, v in NPC_INDEX.items() if v['display_name'].startswith('Bà ') and v['career_id'] == 'clothing')
        with mock.patch.object(SP, '_forced', return_value='on'):
            self.assertEqual(SP.roll(dict(day=5), dict(id='pet_shop-0005-01', npc=kid, day=5), 100)['kind'], 'kid')
            self.assertEqual(SP.roll(dict(day=5), dict(id='clothing-0005-01', npc=elder, day=5), 100)['kind'], 'elder')
        owner = dict(id='clothing-0005-01', npc='clothing_npc_01', day=5)   # Chị Vy runs the shop: never a customer
        with mock.patch.object(SP, '_forced', return_value='on'):
            self.assertIsNone(SP.roll(dict(day=5), owner, 100))

    def test_dev_switch_needs_mnl_dev(self):
        with mock.patch.dict(os.environ, {'MNL_DEV': '', 'MNL_SHORTPAY': 'cheat'}):
            self.assertIsNone(SP._forced())
        with mock.patch.dict(os.environ, {'MNL_DEV': '1', 'MNL_SHORTPAY': 'cheat'}):
            self.assertEqual(SP._forced(), 'cheat')
        with mock.patch.dict(os.environ, {'MNL_DEV': '1', 'MNL_SHORTPAY': 'bogus'}):
            self.assertIsNone(SP._forced())


@unittest.skipIf(A is None, 'clothing filtered out')
class NoticeTests(unittest.TestCase):
    def test_the_gap_is_hidden_until_counted(self):
        j, t = billed('honest')
        v = A.public_task(t)['cash']
        self.assertIsNone(v['gap'])
        self.assertEqual(sum(v['tender']), t['cash']['price'] - t['cash']['sp']['short'])
        self.assertLess(v['due'], 0)
        blob = json.dumps(public_state(j.state), ensure_ascii=False)
        self.assertNotIn('"honest"', blob)
        r = short(j, t['id'], 'count')
        self.assertIn(f'còn thiếu {t["cash"]["sp"]["short"]} xu', r['message'])
        g = A.public_task(j.get(t['id']))['cash']['gap']
        self.assertEqual((g['stage'], g['choices'], g['kind']), ('open', ['ask', 'police', 'let'], None))
        with self.assertRaises(GameError):
            pay(j, t['id'])                         # decide first

    def test_counting_a_full_payment_is_harmless(self):
        j, t = billed(None, lambda t: True)
        self.assertNotIn('sp', t['cash'])
        money = j.c['money']
        r = short(j, t['id'], 'count')
        self.assertIn('Đủ rồi', r['message'])
        self.assertTrue(j.get(t['id'])['cash']['counted'])
        self.assertEqual(j.c['money'], money)
        with self.assertRaises(GameError):
            short(j, t['id'], 'ask')
        pay(j, t['id'])
        self.assertEqual(j.get(t['id'])['status'], 'completed')

    def test_nobody_noticed_every_kind(self):
        for kind in SP.KINDS:
            with self.subTest(kind=kind):
                j, t = billed(kind)
                gap, price = t['cash']['sp']['short'], t['cash']['price']
                r = pay(j, t['id'])
                t = j.get(t['id'])
                self.assertEqual(t['status'], 'completed')
                self.assertEqual(t['cash']['sp']['outcome'], 'missed')
                self.assertIn(f'Tối kiểm két thiếu {gap} xu', r['message'])
                self.assertEqual(revenue(j, t['id']), price - gap)
                self.assertEqual(j.c['shortpay']['cheats'].get(t['npc'], 0), 1 if kind == 'cheat' else 0)
                self.assertNotIn('police_overreact', codes(t))
                validate_state(json.loads(json.dumps(j.state)))


@unittest.skipIf(A is None, 'clothing filtered out')
class ChoiceTests(unittest.TestCase):
    def run_path(self, kind, *choices):
        j, t = billed(kind)
        tid = t['id']
        gap, price = t['cash']['sp']['short'], t['cash']['price']
        before = close(j, t)
        short(j, tid, 'count')
        out = [short(j, tid, c)['message'] for c in choices]
        r = pay(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        validate_state(json.loads(json.dumps(j.state)))
        return j, t, gap, price, before, out, r

    def test_ask_honest_and_elder_pay_the_rest(self):
        for kind, gain in (('honest', 1), ('elder', 2)):
            with self.subTest(kind=kind):
                j, t, gap, price, before, out, r = self.run_path(kind, 'ask')
                self.assertEqual(t['cash']['sp']['outcome'], 'paid')
                self.assertEqual(revenue(j, t['id']), price)
                self.assertEqual(sum(t['cash']['tender']), price)
                self.assertNotIn('police_overreact', codes(t))
                self.assertGreaterEqual(close(j, t), before)       # +closeness (then the job's own +4)

    def test_ask_kid_then_owe_less_give(self):
        for choice in ('owe', 'less', 'give'):
            with self.subTest(choice=choice):
                j, t, gap, price, before, out, r = self.run_path('kid', 'ask', choice)
                self.assertIn(out[0][:2], ('🙏 ',))
                self.assertEqual(t['cash']['sp']['outcome'], choice)
                self.assertEqual(revenue(j, t['id']), price - gap)
                owed = [x for x in j.c['shortpay']['owed'] if x['task'] == t['id']]
                self.assertEqual(len(owed), 1 if choice in ('owe', 'give') else 0)

    def test_ask_cheat_denies_then_let_or_police(self):
        j, t, gap, price, before, out, r = self.run_path('cheat', 'ask', 'let')
        self.assertEqual((t['cash']['sp']['outcome'], revenue(j, t['id'])), ('let', price - gap))
        self.assertEqual(j.c['shortpay']['cheats'][t['npc']], 1)
        j, t, gap, price, before, out, r = self.run_path('cheat', 'ask', 'police')
        self.assertEqual((t['cash']['sp']['outcome'], revenue(j, t['id'])), ('police', price))
        self.assertNotIn('police_overreact', codes(t))
        self.assertIn('công an khu vực', out[1])

    def test_police_on_a_cheat(self):
        j, t = billed('cheat')
        tid = t['id']
        trust, turn = j.c['incidents']['trust'], j.c['turn']
        posts = len(j.c['feed'])
        short(j, tid, 'count')
        r = short(j, tid, 'police')
        self.assertIn('Chờ gần hai mươi phút', r['message'])
        self.assertEqual(j.c['turn'], turn + SP.POLICE_TURNS)
        self.assertEqual(j.c['incidents']['trust'], min(100, trust + SP.TRUST['police_cheat']))
        self.assertGreater(len(j.c['feed']), posts)
        pay(j, tid)
        self.assertEqual(revenue(j, tid), j.get(tid)['cash']['price'])

    def test_police_on_an_honest_customer_is_an_overreaction(self):
        for kind in ('honest', 'elder', 'kid'):
            with self.subTest(kind=kind):
                j, t = billed(kind)
                tid = t['id']
                trust = j.c['incidents']['trust']
                short(j, tid, 'count')
                r = short(j, tid, 'police')
                self.assertIn('Anh công an', r['message'])
                t = j.get(tid)
                self.assertIn('police_overreact', codes(t))
                self.assertEqual(j.c['incidents']['trust'], max(0, trust + SP.TRUST['police_wrong']))
                pay(j, tid)
                t = j.get(tid)
                post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
                self.assertLessEqual(post['stars'], 3)
                self.assertEqual(t['cash']['sp']['got'], t['cash']['sp']['short'])

    def test_let_it_go(self):
        for kind in SP.KINDS:
            with self.subTest(kind=kind):
                j, t, gap, price, before, out, r = self.run_path(kind, 'let')
                self.assertEqual((t['cash']['sp']['outcome'], revenue(j, t['id'])), ('let', price - gap))
                self.assertIn(f'Két bớt {gap} xu', r['message'])

    def test_wrong_choice_for_the_stage_and_no_second_decision(self):
        j, t = billed('kid')
        tid = t['id']
        with self.assertRaises(GameError):
            short(j, tid, 'ask')                   # count first
        short(j, tid, 'count')
        with self.assertRaises(GameError):
            short(j, tid, 'owe')                   # not yet: remind first
        short(j, tid, 'ask')
        with self.assertRaises(GameError):
            short(j, tid, 'police')                # a kid: owe / less / give
        short(j, tid, 'give')
        money = j.c['money']
        with self.assertRaises(GameError):
            short(j, tid, 'give')
        self.assertEqual(j.c['money'], money)
        with self.assertRaises(GameError):
            short(j, tid, 'fly')


@unittest.skipIf(A is None, 'clothing filtered out')
class LaterTests(unittest.TestCase):
    def test_owed_money_comes_back_once_on_a_later_sale(self):
        for choice in ('owe', 'give'):
            with self.subTest(choice=choice):
                j, t = billed('kid')
                tid = t['id']
                short(j, tid, 'count')
                short(j, tid, 'ask')
                short(j, tid, choice)
                pay(j, tid)
                row = j.c['shortpay']['owed'][0]
                # the next day: another sale at the same till settles the IOU
                j.c['day'] += 1
                c, s = j.c, j.state
                msgs = SP.due(s, c)
                self.assertEqual(c['shortpay']['owed'], [])
                back = [r for r in ledger(j, tid, 'revenue')]
                if row['back']:
                    self.assertTrue(msgs and '💌' in msgs[0])
                    self.assertEqual(sum(r['amount'] for r in back), t['cash']['price'])
                else:
                    self.assertEqual(sum(r['amount'] for r in back), t['cash']['price'] - row['amount'])
                self.assertEqual(SP.due(s, c), [])       # once

    def test_back_roll_is_seeded(self):
        seen = {SP._hash('sp-back', f'clothing-0005-{i:02d}') % 100 < SP.BACK_P['owe'] for i in range(12)}
        self.assertEqual(seen, {True, False})


@unittest.skipIf(A is None, 'clothing filtered out')
class ContractTests(unittest.TestCase):
    def test_honest_reminder_tip_follows_the_tip_contract(self):
        found = False
        for start in range(3, 40):
            j, t = billed('honest', start=start)
            if SP._hash('sp-tip', t['id']) % 100 >= SP.TIP_P:
                continue
            short(j, t['id'], 'count')
            r = short(j, t['id'], 'ask')
            t = j.get(t['id'])
            self.assertIn('tip', r['message'])
            self.assertGreater(t['tip_given'], 0)
            self.assertEqual(sum(x['amount'] for x in ledger(j, t['id'], 'tip')), t['tip_given'])
            pay(j, t['id'])
            t = j.get(t['id'])
            self.assertEqual(tips.decide(j.state, j.c, t)['why'], 'given')
            self.assertEqual(sum(x['amount'] for x in ledger(j, t['id'], 'tip')), t['tip_given'])   # no second tip
            found = True
            break
        self.assertTrue(found)

    def test_rebilling_keeps_a_settled_story(self):
        j, t = billed('honest')
        tid, price = t['id'], t['cash']['price']
        short(j, tid, 'count')
        short(j, tid, 'ask')
        j.act('ao_unbill', task=tid)
        j.act('ao_bill', task=tid)
        t = j.get(tid)
        self.assertEqual((t['cash']['sp']['stage'], sum(t['cash']['tender'])), ('done', price))
        pay(j, tid)
        self.assertEqual(revenue(j, tid), price)

    def test_same_choices_same_result(self):
        outs = []
        for _ in range(2):
            j, t = billed('cheat')
            short(j, t['id'], 'count')
            outs.append((short(j, t['id'], 'ask')['message'], short(j, t['id'], 'police')['message'], j.get(t['id'])['cash']))
        self.assertEqual(outs[0], outs[1])


@unittest.skipIf(A is None, 'clothing filtered out')
class SaveTests(unittest.TestCase):
    def test_old_saves_load(self):
        j, t = billed('cheat')
        short(j, t['id'], 'count')
        short(j, t['id'], 'ask')
        short(j, t['id'], 'let')
        pay(j, t['id'])
        old = json.loads(json.dumps(j.state))
        old['careers']['clothing'].pop('shortpay')
        for x in old['careers']['clothing']['tasks']:
            if isinstance(x.get('cash'), dict):
                x['cash'].pop('sp', None)
                x['cash'].pop('counted', None)
                x['cash']['tender'] = till.tender(x['cash']['price'], x['id'])
        validate_state(old)

    def test_bad_fields_are_rejected(self):
        j, t = billed('kid')
        short(j, t['id'], 'count')
        short(j, t['id'], 'ask')
        short(j, t['id'], 'owe')
        validate_state(json.loads(json.dumps(j.state)))

        def broken(fn):
            bad = json.loads(json.dumps(j.state))
            c = bad['careers']['clothing']
            fn(c, next(x for x in c['tasks'] if x['id'] == t['id']))
            with self.assertRaises(GameError):
                validate_state(bad)
        broken(lambda c, x: x['cash']['sp'].update(kind='ghost'))
        broken(lambda c, x: x['cash']['sp'].update(short=x['cash']['price']))
        broken(lambda c, x: x['cash']['sp'].update(stage='done', outcome=None))
        broken(lambda c, x: x['cash']['sp'].update(got=3))
        broken(lambda c, x: x['cash'].update(counted='yes'))
        broken(lambda c, x: x['cash'].update(tender=[1]))
        broken(lambda c, x: x['cash']['sp'].update(path=['dance']))
        broken(lambda c, x: c['shortpay'].update(v=9))
        broken(lambda c, x: c['shortpay']['owed'][0].update(kind='steal'))
        broken(lambda c, x: c['shortpay']['owed'][0].update(amount=0))
        broken(lambda c, x: c['shortpay']['cheats'].update(x=0))
        broken(lambda c, x: c['shortpay']['log'].append(dict(task='a', day=1, kind='kid', outcome=None, short=2)))


if __name__ == '__main__':
    unittest.main()
