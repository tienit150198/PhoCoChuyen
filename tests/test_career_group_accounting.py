import copy
import json
import unittest

from game import employment
from game.careers import group_accounting as GA
from game.careers import kit, office
from game.engine import GameError, apply_action, new_state, public_state, validate_state
from tests.helpers import Journey

CAR = 'group_accounting'
GENDERED = ('anh/chị', 'chị/anh', 'Anh/chị', 'Chị/anh', 'anh ơi', 'chị ơi', 'Anh ơi', 'Chị ơi', 'cô ấy', 'anh ấy')


def answer(st):
    if st['kind'] == 'entry':
        return [dict(debit=d, credit=c, amount=a) for d, c, a in st['_key']]
    return copy.deepcopy(st['_key'])


def slot_for(kind, pred=None):
    for d in range(1, 41):
        for s in range(8):
            if GA._kind(d, s) == kind and (pred is None or pred(GA.make_task(d, s, 1))):
                return d, s
    raise AssertionError('no slot for ' + kind)


def board_for(pred):
    for d in range(1, 41):
        for s in range(8):
            if GA._kind(d, s) == 'match':
                t = GA.make_task(d, s, 1)
                if pred(t):
                    return d, s
    raise AssertionError('no board')


def moves(t):
    """The right moves for a board, straight from the hidden truth."""
    out = []
    by = {x['id']: x for x in t['lines']}
    for x in t['lines']:
        tr = x['_truth']
        if tr['k'] == 'pair' and x['side'] == 'a':
            p = dict(a=x['id'], b=tr['mate'])
            if x['amount'] != by[tr['mate']]['amount']:
                p['cause'] = tr['cause']
            out.append(('ga_pair', p))
        elif tr['k'] == 'single':
            out.append(('ga_tag', dict(line=x['id'], tag=tr['tag'])))
    return out


def kinds(t):
    return [x['_truth'].get('tag') for x in t['lines'] if x['_truth']['k'] == 'single']


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


class GroupAccountingTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey(CAR)

    def open_all(self, tid):
        for d in self.j.get(tid)['docs']:
            self.j.act('ga_open', task=tid, doc=d['id'])

    def play_board(self, tid):
        j = self.j
        for action, p in moves(j.get(tid)):
            r = j.act(action, task=tid, **p)
            self.assertTrue(r['correct'], (action, p, r))

    def solve(self, tid=None, note='specific'):
        j = self.j
        tid = tid or j.task['id']
        j.act('ask', task=tid)
        if j.get(tid)['variant'] == 'match':
            self.play_board(tid)
            return j.act('ga_submit', task=tid, confirm=True)
        self.open_all(tid)
        for st in j.get(tid)['proc']:
            r = j.act('ga_step', task=tid, step=st['id'], answer=answer(st))
            self.assertTrue(r['correct'], (st['id'], r))
        return j.act('ga_submit', task=tid, note=note, confirm=True)

    def use(self, kind, pred=None):
        day, slot = slot_for(kind, pred)
        self.j = Journey(CAR, slot=slot, day=day)
        self.assertEqual(self.j.task['variant'], kind)
        return self.j.task['id']

    def test_first_board_coach_pairs_every_line(self):
        tid = self.board(day=1)
        t = self.j.get(tid)
        coach = public_state(self.j.state)['careers'][CAR]['data']['coach'][tid]['lines']
        self.assertEqual(set(coach), {x['id'] for x in t['lines']})
        for lid, k in coach.items():
            if 'tag' in k:
                r = self.j.act('ga_tag', task=tid, line=lid, tag=k['tag'])
            elif lid.startswith('a'):
                r = self.j.act('ga_pair', task=tid, a=lid, b=k['mate'], **({'cause': k['cause']} if k['cause'] else {}))
            else:
                continue
            self.assertTrue(r['correct'], r)
        self.assertTrue(self.j.act('ga_submit', task=tid, confirm=True)['message'])
        self.assertEqual(public_state(self.j.state)['careers'][CAR]['data']['coach'], {})

    def board(self, day=None, pred=None, chase=True):
        if day is not None:
            day, slot = day, GA._match_slot(day)
        else:
            day, slot = board_for(pred)
        self.j = Journey(CAR, slot=slot, day=day)
        self.assertEqual(self.j.task['variant'], 'match')
        tid = self.j.task['id']
        self.j.act('ask', task=tid)
        if chase and self.j.task.get('wait'):
            self.j.act('ga_chase', task=tid)
        return tid

    def paid(self, category, amount):
        return any(e['category'] == category and e['amount'] == amount for e in self.j.c['ops']['finance']['ledger'])

    @property
    def o(self):
        return self.j.c['ext']['data']['office']

    # ------------------------------------------------------------ the matching board
    def test_day_one_opens_with_the_board(self):
        t = self.j.task
        self.assertEqual(t['variant'], 'match')
        self.assertEqual(t['gen'], GA.GEN)
        self.assertEqual(t['due'], office.DUE[0])
        roundtrip(self.j)

    def test_board_generation_balances_every_day(self):
        for day in range(1, 41):
            for slot in range(8):
                if GA._kind(day, slot) != 'match':
                    continue
                with self.subTest(day=day, slot=slot):
                    t = GA.make_task(day, slot, 1)
                    self.assertEqual(json.loads(json.dumps(t)), t)
                    m = GA._solved_meter(t['lines'])
                    self.assertEqual(m['gap'], 0)
                    self.assertGreater(m['ra2'], 0)
                    self.assertEqual(m['ra2'], t['_value'])
                    by = {x['id']: x for x in t['lines']}
                    self.assertEqual(len(by), len(t['lines']))
                    for x in t['lines']:
                        tr = x['_truth']
                        if tr['k'] == 'pair':
                            mate = by[tr['mate']]
                            self.assertEqual(mate['_truth']['mate'], x['id'])
                            self.assertNotEqual(mate['side'], x['side'])
                            self.assertEqual(x['amount'] != mate['amount'], tr['cause'] is not None)
                        elif tr['tag'] == 'dup':
                            root = by[tr['of']]
                            self.assertEqual((root['ref'], root['amount'], root['side']), (x['ref'], x['amount'], x['side']))
                        else:
                            self.assertLessEqual(GA.TAG_MIN_DAY[tr['tag']], day)
                    self.assertGreaterEqual(len(kinds(t)), 1)
                    if day >= 4:
                        self.assertTrue(all(x['ref'].startswith(('PN-', 'UNC-')) for x in t['lines'] if x['side'] == 'b'))

    def test_difficulty_grows_and_each_twist_shows_up_early(self):
        size = lambda d: len(GA.make_task(d, GA._match_slot(d), 1)['lines'])
        self.assertLess(size(1), max(size(d) for d in range(10, 16)))
        self.assertEqual(len(kinds(GA.make_task(1, 0, 1))), 1)
        self.assertIn('dup', kinds(GA.make_task(2, GA._match_slot(2), 1)))
        self.assertIn('outside', kinds(GA.make_task(3, GA._match_slot(3), 1)))
        self.assertEqual([x['id'] for x in GA.tags_for(1)], ['transit', 'invoice', 'cash'])
        self.assertEqual(len(GA.tags_for(3)), 5)
        typo = [d for d in range(2, 20) if any(x['_truth'].get('cause') == 'typo' for x in GA.make_task(d, GA._match_slot(d), 1)['lines'])]
        self.assertIn(2, typo)

    def test_board_happy_path_eliminates_and_pays(self):
        j = self.j
        tid = j.task['id']
        money = j.c['money']
        agreed = j.task['_value']
        r = self.solve(tid)
        self.assertIn('331', r['message'])
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t['late'])
        d = j.c['ext']['data']
        self.assertEqual(d['elim'], {'331': agreed, '131': -agreed})
        self.assertIn('ic', d['milestones'])
        self.assertEqual(j.c['money'], money + 30)
        self.assertEqual(d['boards'], 1)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertEqual(post['stars'], 5)
        self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'accuracy', 'independence', 'speed', 'handover'})
        roundtrip(j)

    def test_wrong_pair_costs_time_and_trust_and_is_not_recorded(self):
        tid = self.board(pred=lambda t: True)
        j = self.j
        t = j.get(tid)
        by = {x['id']: x for x in t['lines']}
        a = next(x for x in t['lines'] if x['side'] == 'a' and x['_truth']['k'] == 'pair')
        good = GA._group(t, a['_truth']['mate'])
        b = next(x for x in t['lines'] if x['side'] == 'b' and x['id'] not in good)
        p = dict(a=a['id'], b=b['id'])
        if a['amount'] != b['amount']:
            p['cause'] = 'typo'
        clock, trust = self.o['clock'], self.o['trust']
        r = j.act('ga_pair', task=tid, **p)
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(j.get(tid)['board'], {})
        self.assertEqual(self.o['clock'], clock + 20)
        self.assertEqual(self.o['trust'], trust - 1)
        with self.assertRaises(GameError):
            j.act('ga_pair', task=tid, a=b['id'], b=a['id'])
        self.assertEqual(by[a['id']]['side'], 'a')
        roundtrip(j)

    def test_amount_gap_needs_the_right_cause(self):
        tid = self.board(pred=lambda t: any(x['_truth'].get('cause') == 'typo' for x in t['lines']))
        j = self.j
        a = next(x for x in j.get(tid)['lines'] if x['_truth'].get('cause') == 'typo' and x['side'] == 'a')
        with self.assertRaises(GameError):
            j.act('ga_pair', task=tid, a=a['id'], b=a['_truth']['mate'])
        self.assertEqual(j.get(tid)['mistakes'], 0)
        r = j.act('ga_pair', task=tid, a=a['id'], b=a['_truth']['mate'], cause='fx')
        self.assertFalse(r['correct'])
        self.assertIn('nguyên nhân', r['message'])
        r = j.act('ga_pair', task=tid, a=a['id'], b=a['_truth']['mate'], cause='typo')
        self.assertTrue(r['correct'])
        self.assertEqual(j.get(tid)['board'][a['id']], dict(k='pair', mate=a['_truth']['mate'], cause='typo'))
        roundtrip(j)

    def test_fx_board_on_swing_day(self):
        self.assertEqual(GA._mod(3)['id'], 'fx_swing')
        rates = GA.fx_rates(3)
        self.assertNotEqual(rates['delta'], 0)
        tid = self.board(day=3)
        t = self.j.get(tid)
        self.assertTrue(t['ic']['fx'])
        inv = [x for x in t['lines'] if x['side'] == 'a' and x['kind'] == 'inv' and x['_truth']['k'] == 'pair']
        self.assertTrue(inv and all(x['_truth']['cause'] == 'fx' for x in inv))
        self.assertTrue(all('NM' in x['text'] for x in inv))
        self.assertTrue(any(f'× {rates["closing"]}' in x['text'] for x in t['lines'] if x['side'] == 'b'))
        self.play_board(tid)
        self.j.act('ga_submit', task=tid, confirm=True)
        self.assertEqual(self.j.get(tid)['status'], 'completed')
        roundtrip(self.j)

    def test_singles_need_the_right_reason(self):
        tid = self.board(pred=lambda t: 'cash' in kinds(t))
        j = self.j
        t = j.get(tid)
        pair = next(x for x in t['lines'] if x['_truth']['k'] == 'pair' and len(GA._group(t, x['id'])) == 1)
        r = j.act('ga_tag', task=tid, line=pair['id'], tag='cash')
        self.assertFalse(r['correct'])
        self.assertIn('đối ứng', r['message'])
        cash = next(x for x in t['lines'] if x['_truth'].get('tag') == 'cash')
        r = j.act('ga_tag', task=tid, line=cash['id'], tag='invoice')
        self.assertFalse(r['correct'])
        with self.assertRaises(GameError):
            j.act('ga_tag', task=tid, line=cash['id'], tag='moon')
        r = j.act('ga_tag', task=tid, line=cash['id'], tag='cash')
        self.assertTrue(r['correct'])
        self.assertEqual(j.get(tid)['mistakes'], 2)
        with self.assertRaises(GameError):
            j.act('ga_tag', task=tid, line=cash['id'], tag='cash')
        roundtrip(j)

    def test_duplicate_either_copy_may_be_the_one_paired(self):
        for order in ('copy_first', 'root_first'):
            with self.subTest(order=order):
                tid = self.board(pred=lambda t: 'dup' in kinds(t))
                j = self.j
                t = j.get(tid)
                copy_ = next(x for x in t['lines'] if x['_truth'].get('tag') == 'dup')
                root = next(x for x in t['lines'] if x['id'] == copy_['_truth']['of'])
                tagged, paired = (root, copy_) if order == 'copy_first' else (copy_, root)
                r = j.act('ga_tag', task=tid, line=tagged['id'], tag='dup')
                self.assertTrue(r['correct'])
                a, b = (paired['id'], root['_truth']['mate']) if paired['side'] == 'a' else (root['_truth']['mate'], paired['id'])
                r = j.act('ga_pair', task=tid, a=a, b=b)
                self.assertTrue(r['correct'], r)
                roundtrip(j)
                other = next(x for x in j.get(tid)['lines'] if x['side'] == paired['side'] and x['id'] not in j.get(tid)['board'] and x['_truth']['k'] == 'pair')
                r = j.act('ga_tag', task=tid, line=other['id'], tag='dup')
                self.assertFalse(r['correct'])

    def test_meter_closes_the_gap(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        view = lambda: next(x for x in public_state(j.state)['careers'][CAR]['tasks'] if x['id'] == tid)
        m = view()['meter']
        self.assertFalse(m['ready'])
        self.assertIsNone(m['agreed'])
        self.play_board(tid)
        m = view()['meter']
        self.assertTrue(m['ready'])
        self.assertEqual(m['gap'], 0)
        self.assertEqual(m['agreed'], j.task['_value'])
        self.assertEqual(m['resolved'], m['total'])

    def test_submit_needs_every_line_and_confirm(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('ga_submit', task=tid, confirm=True)
        self.play_board(tid)
        with self.assertRaises(GameError):
            j.act('ga_submit', task=tid)
        j.act('ga_submit', task=tid, confirm=True)
        with self.assertRaises(GameError):
            j.act('ga_submit', task=tid, confirm=True)
        with self.assertRaises(GameError):
            j.act('ga_step', task=tid, step='x', answer=1)

    def test_board_hint_costs_time_and_is_recorded(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        line = j.task['lines'][0]
        clock = self.o['clock']
        r = j.act('ga_hint', task=tid, line=line['id'])
        self.assertIn('Chị Mai Anh', r['message'])
        self.assertEqual(self.o['clock'], clock + office.COST['hint'])
        self.assertEqual(j.get(tid)['tips'], [line['id']])
        row = next(x for x in public_state(j.state)['careers'][CAR]['tasks'][0]['lines'] if x['id'] == line['id'])
        self.assertTrue(row['hinted'] and row['tip'])
        roundtrip(j)

    def test_board_meeting_makes_hints_slow_and_rewards_a_clean_day(self):
        day = next(d for d in range(1, 40) if GA._mod(d)['id'] == 'board_meeting')
        tid = self.board(day=day)
        j = self.j
        clock = self.o['clock']
        j.act('ga_hint', task=tid, line=j.get(tid)['lines'][0]['id'])
        self.assertEqual(self.o['clock'], clock + 15)
        self.play_board(tid)
        j.act('ga_submit', task=tid, confirm=True)
        trust = self.o['trust']
        r = j.act('end_day', carry_event=True)
        self.assertTrue(r['summary']['career']['board']['ok'])
        self.assertTrue(self.paid('board_bonus', 12))
        self.assertEqual(r['summary']['career']['office']['trust'], min(100, trust + 3))

    def test_hidden_truth_in_public_view(self):
        j = self.j
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertIsNone(view['lines'])
        self.assertIsNone(view['docs'])
        tid = j.task['id']
        j.act('ask', task=tid)
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        blob = json.dumps(view, ensure_ascii=False)
        for secret in ('_truth', '"mate"', '"of"', '_handover', '"board"', '"why"'):
            self.assertNotIn(secret, blob)
        self.assertTrue(all(set(x) >= {'id', 'side', 'ref', 'date', 'text', 'amount', 'kind'} for x in view['lines']))
        self.play_board(tid)
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertTrue(all(x['state'] and x['why'] for x in view['lines']))
        self.assertNotIn('_truth', json.dumps(view, ensure_ascii=False))

    def test_tampered_board_rejected(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.task
        a = next(x for x in t['lines'] if x['side'] == 'a' and x['_truth']['k'] == 'pair')
        wrong_b = next(x for x in t['lines'] if x['side'] == 'b' and x['id'] not in GA._group(t, a['_truth']['mate']))
        single = next(x for x in t['lines'] if x['_truth']['k'] == 'single' and x['_truth']['tag'] != 'dup')
        for mutate in (
            lambda t: t['board'].update({a['id']: dict(k='pair', mate=wrong_b['id'], cause=None), wrong_b['id']: dict(k='pair', mate=a['id'], cause=None)}),
            lambda t: t['board'].update({single['id']: dict(k='tag', tag='dup')}),
            lambda t: t['board'].update({a['id']: dict(k='tag', tag='cash')}),
            lambda t: t['lines'][0].__setitem__('amount', t['lines'][0]['amount'] + 10),
            lambda t: t['lines'][0]['_truth'].__setitem__('k', 'single'),
            lambda t: t.__setitem__('status', 'completed'),
            lambda t: t.__setitem__('wait', 5),
            lambda t: t.__setitem__('tips', ['zz']),
        ):
            s = copy.deepcopy(j.state)
            mutate(s['careers'][CAR]['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(s)

    # ------------------------------------------------------------ the office day
    def test_luck_of_the_day_intro_and_forced_close(self):
        self.assertEqual([GA._mod(d)['id'] for d in range(1, 6)], ['normal', 'late_package', 'fx_swing', 'audit_visit', 'crunch'])
        self.assertEqual(GA._mod(10)['id'], 'crunch')
        later = {GA._mod(d)['id'] for d in range(6, 40)}
        self.assertTrue({'late_package', 'fx_swing', 'audit_visit', 'board_meeting', 'normal'} <= later)
        self.assertEqual([GA._mod(d)['id'] for d in range(1, 30)], [GA._mod(d)['id'] for d in range(1, 30)])

    def test_late_package_waits_then_chase(self):
        tid = self.board(day=2, chase=False)
        j = self.j
        t = j.get(tid)
        self.assertEqual(t['wait'], GA.WAIT_AT)
        self.assertGreaterEqual(t['due'], GA.WAIT_AT + 90)
        self.assertIn('SH Logistics', t['title'])
        move = moves(t)[0]
        with self.assertRaises(GameError):
            j.act(move[0], task=tid, **move[1])
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertEqual(view['wait'], GA.WAIT_AT)
        clock = self.o['clock']
        j.act('ga_chase', task=tid)
        self.assertIsNone(j.get(tid)['wait'])
        self.assertEqual(self.o['clock'], clock + GA.CHASE_MIN)
        with self.assertRaises(GameError):
            j.act('ga_chase', task=tid)
        self.assertTrue(j.act(move[0], task=tid, **move[1])['correct'])
        roundtrip(j)

    def test_late_package_arrives_by_itself_and_overnight(self):
        tid = self.board(day=2, chase=False)
        j = self.j
        self.o['clock'] = GA.WAIT_AT
        move = moves(j.get(tid))[0]
        self.assertTrue(j.act(move[0], task=tid, **move[1])['correct'])
        tid = self.board(day=2, chase=False)
        j = self.j
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertIsNone(j.get(tid)['wait'])
        self.assertEqual(j.get(tid)['due'], office.CARRY_DUE)

    def test_rates_board_shifts_daily_and_feeds_fx_translation(self):
        closes = [GA.fx_rates(d)['closing'] for d in range(1, 31)]
        self.assertTrue(all(19 <= c <= 29 for c in closes))
        self.assertGreater(len(set(closes)), 3)
        for d in range(2, 30):
            r = GA.fx_rates(d)
            self.assertEqual(r['prev'], GA.fx_rates(d - 1)['closing'])
            if GA._mod(d)['id'] == 'fx_swing':
                self.assertEqual(abs(r['delta']), 3)
        data = public_state(self.j.state)['careers'][CAR]['data']
        self.assertEqual(data['today']['fx'], GA.fx_rates(1))
        day, slot = slot_for('fx_translate')
        t = GA.make_task(day, slot, 1)
        rates = next(x for x in t['docs'] if x['id'] == 'rates')
        r = GA.fx_rates(day)
        self.assertEqual(rates['rows'][0][1], str(r['closing']))
        self.assertEqual(rates['rows'][2][1], str(GA.FX_HIST))

    def test_rule_cards_shift_with_new_badges(self):
        new = lambda d: {x['id'] for x in GA.rules(d) if x['new']}
        self.assertEqual(new(1), set())
        self.assertIn('single', new(2))
        self.assertTrue({'single', 'ic'} <= new(3))
        self.assertIn('refs', new(4))
        self.assertIn('cutoff', new(6))
        self.assertEqual(new(7), set())
        data = public_state(self.j.state)['careers'][CAR]['data']
        self.assertEqual(data['today']['mod']['id'], 'normal')
        self.assertTrue(data['today']['rules'])
        self.assertEqual(data['office']['time'], '08:00')

    def test_crunch_due_earlier_and_overtime_pays_more(self):
        tid = self.board(day=5)
        j = self.j
        self.assertEqual(j.get(tid)['due'], office.DUE[0] - 30)
        self.o['clock'] = office.CLOSE
        move = moves(j.get(tid))[0]
        with self.assertRaises(GameError) as cm:
            j.act(move[0], task=tid, **move[1])
        self.assertEqual(cm.exception.code, 'office_closed')
        money, trust = j.c['money'], self.o['trust']
        with self.assertRaises(GameError):
            j.act('ga_overtime')
        j.act('ga_overtime', confirm=True)
        self.assertEqual(j.c['money'], money + 18)
        self.assertEqual(self.o['trust'], trust + 3)
        self.assertTrue(j.act(move[0], task=tid, **move[1])['correct'])
        roundtrip(j)

    def test_lunch_break_on_the_clock(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        self.o['clock'] = office.LUNCH - 2
        move = moves(j.get(tid))[0]
        r = j.act(move[0], task=tid, **move[1])
        self.assertIn('Nghỉ trưa', r['message'])
        self.assertEqual(self.o['clock'], office.LUNCH - 2 + office.COST['pair'] + office.LUNCH_MIN)

    def test_late_board_cuts_bonus_and_trust(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        self.play_board(tid)
        self.o['clock'] = j.task['due'] + 5
        money, trust = j.c['money'], self.o['trust']
        r = j.act('ga_submit', task=tid, confirm=True)
        self.assertIn('Trễ hạn', r['message'])
        self.assertTrue(j.get(tid)['late'])
        self.assertEqual(j.c['money'], money + 30 - office.LATE_CUT)
        self.assertEqual(self.o['trust'], trust - 3)

    def test_audit_visit_rewards_clean_or_writes_a_letter(self):
        self.assertEqual(GA._mod(4)['id'], 'audit_visit')
        tid = self.board(day=4)
        self.play_board(tid)
        self.j.act('ga_submit', task=tid, confirm=True)
        r = self.j.act('end_day', carry_event=True)
        self.assertTrue(r['summary']['career']['audit']['ok'])
        self.assertTrue(self.paid('audit_bonus', 10))
        self.assertTrue(any(p['kind'] == 'review' and p['npc'] == kit.npc_id(CAR, 5) for p in self.j.c['feed']))
        tid = self.board(day=4)
        j = self.j
        t = j.get(tid)
        a = next(x for x in t['lines'] if x['side'] == 'a' and x['_truth']['k'] == 'pair')
        good = GA._group(t, a['_truth']['mate'])
        b = next(x for x in t['lines'] if x['side'] == 'b' and x['id'] not in good)
        for _ in range(3):
            j.act('ga_pair', task=tid, a=a['id'], b=b['id'], cause='typo')
        self.play_board(tid)
        j.act('ga_submit', task=tid, confirm=True)
        r = j.act('end_day', carry_event=True)
        audit = r['summary']['career']['audit']
        self.assertFalse(audit['ok'])
        self.assertEqual(audit['amount'], 10)
        self.assertTrue(self.paid('penalty', -10))
        self.assertEqual(r['summary']['career']['slips'], 3)

    def test_day_summary_names_milestones(self):
        self.solve()
        r = self.j.act('end_day', carry_event=True)
        car = r['summary']['career']
        self.assertEqual(car['milestones'], ['Đối chiếu nội bộ'])
        self.assertEqual(car['boards'], 1)
        self.assertIn('office', car)
        self.assertEqual(car['mod']['name'], 'Ngày bình thường')

    # ------------------------------------------------------------ dossiers with steps
    def test_every_kind_solvable_and_saves(self):
        for kind in GA.KINDS:
            with self.subTest(kind=kind):
                tid = self.use(kind)
                self.solve(tid)
                self.assertEqual(self.j.get(tid)['status'], 'completed')
                self.assertEqual(sum(self.j.c['ext']['data']['elim'].values()), 0)
                roundtrip(self.j)

    def test_generation_deterministic_and_valid(self):
        for day in range(1, 41):
            for slot in range(8):
                a, b = GA.make_task(day, slot, 1), GA.make_task(day, slot, 9)
                self.assertEqual(a['proc'], b['proc'])
                self.assertEqual(a.get('lines'), b.get('lines'))
                self.assertEqual(json.loads(json.dumps(a)), a)
                ids = {d['id'] for d in a['docs']}
                for st in a['proc']:
                    self.assertTrue(set(st.get('docs', [])) <= ids)
                    if st['kind'] == 'choice':
                        self.assertIn(st['_key'], [o['id'] for o in st['options']])
                    if st['kind'] == 'entry':
                        for d, c, amt in st['_key']:
                            self.assertNotEqual(d, c)
                            self.assertGreater(amt, 0)

    def test_brief_docs_and_answers_hidden(self):
        tid = self.use('calendar')
        j = self.j
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertIsNone(view['docs'])
        self.assertIsNone(view['proc'])
        j.act('ask', task=tid)
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        blob = json.dumps(view, ensure_ascii=False)
        self.assertNotIn('_key', blob)
        self.assertNotIn('_handover', blob)
        self.assertTrue(all(set(d) == {'id', 'type', 'title', 'source', 'closed'} for d in view['docs']))
        for st in view['proc']:
            if st['state'] == 'locked':
                self.assertEqual(set(st), {'id', 'kind', 'title', 'state'})
            if st['state'] == 'current':
                self.assertNotIn('explain', st)

    def test_docs_needed_and_order_enforced(self):
        tid = self.use('ic_rec')
        j = self.j
        j.act('ask', task=tid)
        first, second = j.get(tid)['proc'][:2]
        with self.assertRaises(GameError):
            j.act('ga_step', task=tid, step=first['id'], answer=answer(first))
        self.open_all(tid)
        with self.assertRaises(GameError):
            j.act('ga_step', task=tid, step=second['id'], answer=answer(second))
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_ic_rec_wrong_cause_is_a_mistake(self):
        tid = self.use('ic_rec')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        diff, cause = j.get(tid)['proc'][:2]
        j.act('ga_step', task=tid, step=diff['id'], answer=answer(diff))
        wrong = next(o['id'] for o in cause['options'] if o['id'] != cause['_key'])
        clock = self.o['clock']
        r = j.act('ga_step', task=tid, step=cause['id'], answer=wrong)
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(self.o['clock'], clock + office.COST['step'] + office.COST['wrong'])
        fix = j.get(tid)['proc'][2]
        self.assertNotIn(fix['_key'], ('split', 'plug'))

    def test_elimination_entries_unbalanced_or_malformed_rejected(self):
        tid = self.use('elim_sales')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        pick = j.get(tid)['proc'][0]
        j.act('ga_step', task=tid, step=pick['id'], answer=answer(pick))
        st = j.get(tid)['proc'][1]
        d, c, a = st['_key'][0]
        for ans in (dict(debit=[dict(account=d, amount=a)], credit=[dict(account=c, amount=a - 10)]),
                    [dict(debit=d, credit='000', amount=a)], [dict(debit=d, credit=c, amount=-a)], {'debit': 'x'}):
            with self.subTest(ans=ans), self.assertRaises(GameError):
                j.act('ga_step', task=tid, step=st['id'], answer=ans)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        r = j.act('ga_step', task=tid, step=st['id'], answer=[dict(debit=c, credit=d, amount=a)])
        self.assertFalse(r['correct'])
        self.assertIn('Tổng số tiền đúng', r['message'])
        self.assertEqual(j.c['ext']['data']['elim'], {})
        r = j.act('ga_step', task=tid, step=st['id'], answer=answer(st))
        self.assertTrue(r['correct'])
        self.assertEqual(j.c['ext']['data']['elim'], {'511': a, '632': -a})

    def test_dividend_from_70_percent_subsidiary_splits_nci(self):
        tid = self.use('elim_div', lambda t: 'Logistics' in t['title'])
        j = self.j
        entry = next(s for s in j.task['proc'] if s['kind'] == 'entry')
        accounts = {d for d, _, _ in entry['_key']}
        self.assertEqual(accounts, {'515', '429'})
        parent = next(s for s in j.task['proc'] if s['id'] == 'parent')['_key']
        nci = next(s for s in j.task['proc'] if s['id'] == 'nci')['_key']
        self.assertEqual(parent * 30, nci * 70)
        self.solve(tid)
        roundtrip(j)

    def test_fx_translation_accepts_negative_difference(self):
        tid = self.use('fx_translate')
        j = self.j
        st = next(s for s in j.task['proc'] if s['id'] == 'diff')
        self.assertIsInstance(st['_key'], int)
        rates = next(s for s in j.task['proc'] if s['id'] == 'rates')['_key']
        self.assertEqual(rates, dict(ta='closing', tl='closing', rev='average', exp='average', cap='historical'))
        self.solve(tid)

    def test_worksheet_consolidated_balance_ties(self):
        seen = 0
        for day in range(1, 41):
            for slot in range(8):
                if GA._kind(day, slot) != 'worksheet':
                    continue
                seen += 1
                t = GA.make_task(day, slot, 1)
                ws = next(d for d in t['docs'] if d['id'] == 'ws')
                self.assertEqual(ws['cols'][-1], 'Loại trừ')
                self.assertGreater(next(s for s in t['proc'] if s['id'] == 'ta')['_key'], 0)
        self.assertGreater(seen, 0)

    def test_submit_requires_done_note_and_confirm(self):
        tid = self.use('calendar')
        j = self.j
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('ga_submit', task=tid, note='specific', confirm=True)
        self.open_all(tid)
        for st in j.get(tid)['proc']:
            j.act('ga_step', task=tid, step=st['id'], answer=answer(st))
        with self.assertRaises(GameError):
            j.act('ga_submit', task=tid, note='specific')
        with self.assertRaises(GameError):
            j.act('ga_submit', task=tid, note='x', confirm=True)
        j.act('ga_submit', task=tid, note='short', confirm=True)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertEqual(next(x for x in post['feedback']['criteria'] if x['key'] == 'handover')['score'], 3)
        self.assertEqual(next(x for x in post['feedback']['criteria'] if x['key'] == 'speed')['score'], 5)

    def test_hint_recorded(self):
        tid = self.use('calendar')
        j = self.j
        j.act('ask', task=tid)
        j.act('ga_hint', task=tid)
        self.assertEqual(len(j.get(tid)['tips']), 1)
        j.act('ga_hint', task=tid)
        self.assertEqual(len(j.get(tid)['tips']), 1)
        roundtrip(j)

    def test_board_has_no_documents_to_open(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        doc = j.task['docs'][0]['id'] if j.task['docs'] else 'e1'
        with self.assertRaises(GameError):
            j.act('ga_open', task=tid, doc=doc)

    # ------------------------------------------------------------ save integrity
    def test_tampered_fixed_fields_rejected(self):
        tid = self.use('calendar')
        j = self.j
        j.act('ask', task=tid)
        for mutate in (
            lambda t: t['proc'][-1].__setitem__('_key', 'x'),
            lambda t: t['docs'][0].__setitem__('source', 'Giả'),
            lambda t: t.__setitem__('_value', t['_value'] + 1),
            lambda t: t.__setitem__('brief', 'khác'),
            lambda t: t.__setitem__('tips', ['nope']),
            lambda t: t.__setitem__('gen', 1),
            lambda t: t.__setitem__('due', 5),
        ):
            s = copy.deepcopy(j.state)
            mutate(s['careers'][CAR]['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_elimination_journal_must_balance(self):
        s = copy.deepcopy(self.j.state)
        s['careers'][CAR]['ext']['data']['elim'] = {'511': 100, '632': -50}
        with self.assertRaises(GameError):
            validate_state(s)
        s['careers'][CAR]['ext']['data']['milestones'] = ['moon']
        s['careers'][CAR]['ext']['data']['elim'] = {}
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(self.j.state)
        s['careers'][CAR]['ext']['data']['day_work'] = [dict(task='x', board='yes', mistakes=0, late=False)]
        with self.assertRaises(GameError):
            validate_state(s)

    def test_consolidation_journal_resets_each_quarter(self):
        tid = self.use('elim_upi')
        j = self.j
        self.solve(tid)
        self.assertTrue(j.c['ext']['data']['elim'])
        j.c['day'] = 5
        j.act('end_day', carry_event=True)
        d = j.c['ext']['data']
        self.assertEqual(d['elim'], {})
        self.assertEqual(d['milestones'], [])
        self.assertEqual(d['quarters'], 1)
        self.assertEqual(d['posted'], 2)
        roundtrip(j)

    def test_old_save_keeps_its_dossiers(self):
        s = copy.deepcopy(self.j.state)
        c = s['careers'][CAR]
        old = GA.make_task(1, 0, kit.LEGACY_TURN + 1)
        old['created_turn'] = 1
        self.assertEqual(old['variant'], 'calendar')
        self.assertNotIn('gen', old)
        c['tasks'] = [old]
        c['active_task'] = old['id']
        c['ext']['data'] = dict(elim={}, entries=[], milestones=[], posted=0, quarters=0, done=0, day_posted=0, day_done=0)
        validate_state(s)
        self.assertEqual(c['tasks'][0]['created_turn'], kit.LEGACY_TURN + 1)
        self.assertIn('office', c['ext']['data'])
        self.j.state = s
        money = self.j.c['money']
        self.solve(old['id'])
        self.assertEqual(self.j.get(old['id'])['status'], 'completed')
        self.assertEqual(self.j.c['money'], money + 30)
        roundtrip(self.j)

    def test_public_data_and_content(self):
        data = public_state(self.j.state)['careers'][CAR]['data']
        self.assertEqual(data['period']['quarter'], 1)
        self.assertTrue(data['balanced'])
        self.assertNotIn('day_work', data)
        self.assertEqual(set(data['today']), {'mod', 'rules', 'fx'})
        content = GA.content()
        self.assertEqual(len(content['entities']), 5)
        self.assertTrue(any(e['own'] == 70 for e in content['entities']))
        self.assertTrue(any(e['cur'] != 'xu' for e in content['entities']))
        self.assertEqual([x['id'] for x in content['tags']], GA.TAG_IDS)
        self.assertEqual(content['boss']['name'], 'Chị Mai Anh')

    # ------------------------------------------------------------ situations & employment
    def test_all_situations_playable(self):
        j = self.j
        self.assertTrue(10 <= len(GA.SPEC['situations']) <= 14)
        for x in GA.SPEC['situations']:
            for opt in x['options']:
                self.assertTrue(2 <= len(opt['perspectives']) <= 3 or opt.get('quality') != 'good')
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_texts_never_assume_the_players_gender(self):
        blobs = [json.dumps(GA.SPEC['situations'], ensure_ascii=False), json.dumps(GA.MODS, ensure_ascii=False),
                 json.dumps(GA.SPEC['meta'], ensure_ascii=False), GA.SPEC['guide']]
        for d in range(1, 11):
            blobs.append(json.dumps(GA.rules(d), ensure_ascii=False))
            for s in range(6):
                blobs.append(json.dumps(GA.make_task(d, s, 1), ensure_ascii=False))
        text = '\n'.join(blobs)
        for w in GENDERED:
            self.assertNotIn(w, text)

    def test_start_day_blocked_until_hired_then_full_hiring_flow(self):
        state = new_state()
        state, _ = apply_action(state, CAR, 'select_career', {})
        with self.assertRaises(GameError) as cm:
            apply_action(state, CAR, 'start_day', {})
        self.assertEqual(cm.exception.code, 'not_hired')
        post = GA.SPEC['employment']['postings'][1]

        def act(name, **p):
            nonlocal state
            state, r = apply_action(state, CAR, name, p)
            return r
        act('job_apply', posting=post['id'])
        act('job_cv', strengths=post['wants'][:3], claims=['fresh'])
        act('job_letter', parts=dict(why='specific', example='story', close='available'))
        for qid in post['questions']:
            q = employment.question(CAR, qid)
            r = act('job_answer', question=qid, option=max(q['options'], key=lambda o: o['score'])['id'])
        self.assertEqual(state['careers'][CAR]['job']['status'], 'offer')
        act('job_negotiate')
        act('job_accept', confirm=True)
        self.assertEqual(state['careers'][CAR]['job']['status'], 'hired')
        act('start_day')
        self.assertEqual(state['careers'][CAR]['tasks'][0]['variant'], 'match')
        validate_state(json.loads(json.dumps(state)))

    def test_poor_interview_is_rejected(self):
        state = new_state()
        state, _ = apply_action(state, CAR, 'select_career', {})
        post = GA.SPEC['employment']['postings'][0]
        state, _ = apply_action(state, CAR, 'job_apply', dict(posting=post['id']))
        state, _ = apply_action(state, CAR, 'job_cv', dict(strengths=['creative'], claims=['served15']))
        state, _ = apply_action(state, CAR, 'job_letter', dict(parts=dict(why='wrong', example='salary', close='demand')))
        for qid in post['questions']:
            q = employment.question(CAR, qid)
            state, r = apply_action(state, CAR, 'job_answer', dict(question=qid, option=min(q['options'], key=lambda o: o['score'])['id']))
        self.assertEqual(state['careers'][CAR]['job']['status'], 'rejected')

    def test_staff_roles_are_unique_to_this_career(self):
        roles = {r for _, r, *_ in GA.SPEC['staff']}
        self.assertTrue(all(r.startswith('ga_') for r in roles))
        self.assertEqual(roles, set(GA.SPEC['roles']))
        tid = self.use('calendar')
        j = self.j
        j.act('ask', task=tid)
        self.assertTrue(GA.assist(j.state, j.c, dict(role='ga_collect'), j.get(tid)))
        self.assertEqual(len(j.get(tid)['inspected']), 1)
        validate_state(j.state)
        self.assertIn('xu/NM', GA.assist(j.state, j.c, dict(role='ga_fx'), None))
        self.j = Journey(CAR)
        tid = self.j.task['id']
        self.j.act('ask', task=tid)
        self.assertIn('còn lệch', GA.assist(self.j.state, self.j.c, dict(role='ga_analyst'), self.j.get(tid)))


class ConsequenceTests(unittest.TestCase):
    """The consolidation desk never lets a wrong answer into the file: it is blocked, counted
    (time, bonus, trust) and the dossier that goes out is right, so there is nothing to react to."""

    def test_wrong_pair_is_blocked_and_the_dossier_goes_out_right(self):
        day = 1
        j = Journey(CAR, slot=GA._match_slot(day), day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        if j.task.get('wait'):
            j.act('ga_chase', task=tid)
        t = j.get(tid)
        a = next(x for x in t['lines'] if x['side'] == 'a' and x['_truth']['k'] == 'pair')
        b = next(x for x in t['lines'] if x['side'] == 'b' and x['id'] not in GA._group(t, a['_truth']['mate']))
        p = dict(a=a['id'], b=b['id'])
        if a['amount'] != b['amount']:
            p['cause'] = 'typo'
        self.assertFalse(j.act('ga_pair', task=tid, **p)['correct'])
        for action, q in moves(j.get(tid)):
            j.act(action, task=tid, **q)
        money = j.c['money']
        r = j.act('ga_submit', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['mistakes'], 1)
        self.assertFalse(t.get('slips'))
        self.assertEqual(j.c['money'], money + 26)
        self.assertNotIn('uy tín', r['message'])
        validate_state(json.loads(json.dumps(j.state)))



# ---------------------------------------------------------------- office care: reporting packs, audit questions, colleagues
def solve_task(j, tid):
    j.act('ask', task=tid)
    t = j.get(tid)
    if t['variant'] == 'match':
        if t.get('wait') and j.c['ext']['data']['office']['clock'] < t['wait']:
            j.act('ga_chase', task=tid)
        for action, p in moves(j.get(tid)):
            j.act(action, task=tid, **p)
        return j.act('ga_submit', task=tid, confirm=True)
    for d in t['docs']:
        j.act('ga_open', task=tid, doc=d['id'])
    for st in j.get(tid)['proc']:
        j.act('ga_step', task=tid, step=st['id'], answer=answer(st))
    return j.act('ga_submit', task=tid, note='specific', confirm=True)


class OfficeCareTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey(CAR)

    @property
    def care(self):
        return self.j.c['ext']['data']['care']

    @property
    def o(self):
        return self.j.c['ext']['data']['office']

    def st(self, sub):
        return self.care['packs']['st'][sub]

    def view(self):
        return public_state(self.j.state)['careers'][CAR]['data']['care']

    def roll(self, n=1):
        for _ in range(n):
            self.j.act('end_day', carry_event=True)
            self.j.act('start_day')

    def test_pack_seed_is_deterministic_and_fair(self):
        for qi in range(12):
            arrive, issue = GA._pack_seed(qi)
            self.assertEqual((arrive, issue), GA._pack_seed(qi))
            self.assertEqual(set(arrive), set(GA.SUBS))
            late = [s for s, a in arrive.items() if a > GA.PACK_DUE]
            self.assertEqual(len(late), 1 if qi < 2 else 2, qi)
            self.assertTrue(all(a <= GA.PACK_DUE + 2 for a in arrive.values()))
            self.assertIn(issue, GA.SUBS)

    def test_view_has_packs_mates_and_calendar(self):
        v = self.view()
        self.assertEqual([m['id'] for m in v['mates']], ['ngoc', 'phong', 'linh', 'kien'])
        self.assertEqual(v['plan']['kind'], 'packs')
        self.assertEqual([x['sub'] for x in v['plan']['items']], GA.SUBS)
        arrive, _ = GA._pack_seed(0)
        for x in v['plan']['items']:
            self.assertEqual(x['state'], 'in' if arrive[x['sub']] == 0 else 'wait')
            self.assertFalse(x['can_nudge'])                                             # not due yet
        self.assertTrue(any(i['text'].startswith('Hạn gói') for i in v['calendar'][1]['items']))

    def test_review_catches_the_mistake_and_it_comes_back(self):
        j = self.j
        arrive, issue = GA._pack_seed(0)
        clean = next(s for s in GA.SUBS if s != issue and arrive[s] == 0) if any(arrive[s] == 0 and s != issue for s in GA.SUBS) else None
        if clean:
            clock = self.o['clock']
            r = j.act('ga_review', sub=clean)
            self.assertIn('sạch', r['message'])
            self.assertEqual(self.st(clean)['s'], 'ok')
            self.assertEqual(self.o['clock'], clock + GA.REVIEW_MIN)
            with self.assertRaises(GameError):
                j.act('ga_review', sub=clean)
        while self.st(issue)['s'] != 'in':
            self.roll()
        trust = self.o['trust']
        r = j.act('ga_review', sub=issue)
        self.assertIn(GA.PACK_ISSUES[issue], r['message'])
        self.assertEqual(self.st(issue)['s'], 'fixing')
        self.assertEqual(self.o['trust'], trust + 1)
        self.roll()
        self.assertEqual(self.st(issue)['s'], 'in')
        j.act('ga_review', sub=issue)
        self.assertEqual(self.st(issue)['s'], 'ok')
        validate_state(json.loads(json.dumps(j.state)))

    def test_chasing_a_late_pack(self):
        j = self.j
        arrive, _ = GA._pack_seed(0)
        late = next(s for s, a in arrive.items() if a > GA.PACK_DUE)
        with self.assertRaises(GameError) as cm:
            j.act('ga_nudge', sub=late)                                                   # day 1: not due yet
        self.assertIn('Chưa tới hạn', str(cm.exception))
        self.roll()                                                                       # day 2: due today
        self.assertEqual(self.st(late)['s'], 'wait')
        self.assertTrue(next(x for x in self.view()['plan']['items'] if x['sub'] == late)['can_nudge'])
        clock = self.o['clock']
        r = j.act('ga_nudge', sub=late)
        self.assertIn('sáng mai', r['message'])
        self.assertEqual(self.o['clock'], clock + GA.NUDGE_MIN)
        with self.assertRaises(GameError):
            j.act('ga_nudge', sub=late)                                                   # once a day
        self.roll()
        self.assertEqual(self.st(late)['s'], 'in')
        validate_state(json.loads(json.dumps(j.state)))

    def test_a_friend_sends_at_once_and_a_close_friend_is_never_late(self):
        j = self.j
        arrive, _ = GA._pack_seed(0)
        late = next(s for s, a in arrive.items() if a > GA.PACK_DUE)
        mate = GA.SUB_MATE[late]
        self.roll()
        self.care['mates'][mate]['bond'] = 2
        r = j.act('ga_nudge', sub=late)
        self.assertIn('trong buổi chiều', r['message'])
        self.assertEqual(self.st(late)['s'], 'in')
        # next quarter: with bond 3 the pack is on time
        self.j = Journey(CAR)
        for m in self.care['mates'].values():
            m.update(bond=3)
        for _ in range(5):
            self.roll()
        due = self.care['packs']['q'] * 5 + 1 + GA.PACK_DUE
        self.assertTrue(all(st['at'] <= due for st in self.care['packs']['st'].values()))

    def test_audit_questions_and_answers(self):
        j = self.j
        self.roll(2)                                                                      # day 3: phase 2, chị Thảo starts asking
        qs = [q for q in self.care['queries'] if q['s'] == 'open']
        self.assertGreaterEqual(len(qs), 1)
        self.assertEqual(qs[0]['due'], 3 + GA.QUERY_DAYS)
        q = qs[0]
        view = next(x for x in self.view()['plan']['queries'] if x['id'] == q['id'])
        ready = self.st(q['sub'])['s'] == 'ok'
        self.assertEqual(view['minutes'], GA.QUERY_READY if ready else GA.QUERY_DIG)
        clock, trust = self.o['clock'], self.o['trust']
        j.act('ga_answer', query=q['id'])
        self.assertEqual(self.o['clock'], clock + view['minutes'])
        self.assertEqual(self.o['trust'], trust + 1)
        with self.assertRaises(GameError):
            j.act('ga_answer', query=q['id'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_a_reviewed_pack_makes_the_answer_quick(self):
        j = self.j
        self.roll(2)
        q = next(q for q in self.care['queries'] if q['s'] == 'open')
        st = self.st(q['sub'])
        st.update(s='in', issue=False, at=min(st['at'], j.c['day']))
        j.act('ga_review', sub=q['sub'])
        clock = self.o['clock']
        j.act('ga_answer', query=q['id'])
        self.assertEqual(self.o['clock'], clock + GA.QUERY_READY)

    def test_an_unanswered_question_becomes_a_management_letter(self):
        j = self.j
        self.roll(2)
        q = next(q for q in self.care['queries'] if q['s'] == 'open')
        self.roll(q['due'] - j.c['day'])
        self.assertEqual(j.c['day'], q['due'])
        r = j.act('end_day', carry_event=True)                                           # the due day closes unanswered
        self.assertGreaterEqual(r['summary']['career']['queries_late'], 1)
        self.assertEqual(next(x for x in self.care['queries'] if x['id'] == q['id'])['s'], 'late')
        self.assertTrue(any('Thư quản lý' in n['text'] for n in self.o['notes']))

    def test_quarter_close_rewards_reviewed_packs(self):
        j = self.j
        self.roll(3)                                                                      # day 4
        for st in self.care['packs']['st'].values():
            st.update(s='ok', issue=False)
        j.act('end_day', carry_event=True)
        j.act('start_day')                                                                # day 5: the quarter close
        money = j.c['money']
        r = j.act('end_day', carry_event=True)
        packs = r['summary']['career']['packs']
        self.assertEqual((packs['ok'], packs['bonus']), (4, GA.PACK_BONUS))
        self.assertGreaterEqual(j.c['money'], money + GA.PACK_BONUS)
        j.act('start_day')
        self.assertEqual(self.care['packs']['q'], 1)

    def test_a_late_pack_never_chased_costs_trust(self):
        j = self.j
        arrive, _ = GA._pack_seed(0)
        late = next(s for s, a in arrive.items() if a > GA.PACK_DUE)
        self.roll(4)                                                                      # day 5, without chasing
        self.st(late).update(s='wait', at=6, nudged=0)
        r = j.act('end_day', carry_event=True)
        self.assertIn(ENT_SHORT[late], r['summary']['career']['packs']['silent'])

    def test_old_save_mid_quarter_counts_packs_as_handled(self):
        j = self.j = Journey(CAR, slot=GA._match_slot(3), day=3)
        j.c['ext']['data'].pop('care')
        validate_state(j.state)
        self.assertTrue(all(st['s'] == 'ok' for st in self.care['packs']['st'].values()))
        self.assertEqual(self.care['queries'], [])

    def test_tampered_packs_rejected(self):
        for f in (lambda cr: cr['packs']['st']['food'].update(s='lost'), lambda cr: cr['packs']['st'].pop('nami'),
                  lambda cr: cr['packs']['st']['food'].update(at=99), lambda cr: cr['packs']['st']['food'].update(issue='yes'),
                  lambda cr: cr['queries'].append(dict(id='q1a', day=1, due=9, sub='food', topic=0, s='open', ready=False)),
                  lambda cr: cr['queries'].append(dict(id='q1a', day=1, due=3, sub='mars', topic=0, s='open', ready=False))):
            j = Journey(CAR)
            f(j.c['ext']['data']['care'])
            with self.assertRaises(GameError):
                validate_state(json.loads(json.dumps(j.state)))

    def test_a_quarter_of_days(self):
        j = self.j
        for day in range(1, 7):
            if day > 1:
                j.act('start_day')
            v = self.view()
            for m in v['mates']:
                if m['ask']:
                    j.act('ga_help', mate=m['id'], answer='yes')
            for x in v['plan']['items']:
                if x['can_nudge']:
                    j.act('ga_nudge', sub=x['sub'])
            for x in self.view()['plan']['items']:
                if x['can_review']:
                    j.act('ga_review', sub=x['sub'])
            for q in self.view()['plan']['queries']:
                j.act('ga_answer', query=q['id'])
            for t in [t for t in j.c['tasks'] if t['status'] != 'completed']:
                solve_task(j, t['id'])
            validate_state(json.loads(json.dumps(j.state)))
            r = j.act('end_day', carry_event=True)
            self.assertNotIn('queries_late', r['summary']['career'])
            if day == 5:
                self.assertEqual(r['summary']['career']['packs']['silent'], [])
        self.assertGreaterEqual(self.care['reliable'], 3)


ENT_SHORT = {e['id']: e['short'] for e in GA.ENTITIES}


if __name__ == '__main__':
    unittest.main()
