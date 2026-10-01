"""Nội trợ nhà chị Thảo (plugin career homemaker): the morning (count the market money, plan the day),
the market (fresh goods, the list in your head, haggling, the market book to the coin), cooking for
each person's diet and allergy, laundry, cleaning, the grandmother's pills, the children, the fridge,
the plants, household incidents, Tết; chị Thảo paying later, the market book checked again,
surprises, determinism, save validation and old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, PLUGINS
from game import consequences as cq
from game.careers import street_folk as folk
from game.content import initial_career, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

HM = PLUGINS.get('homemaker')
if HM is not None:
    from game.careers import homemaker_content as hc


def find(pred, days=range(1, 160), slots=range(1, 12)):
    """(day, slot) of the first job the predicate likes."""
    for d in days:
        for s in slots:
            if pred(HM.make_task(d, s, 1)):
                return d, s
    raise AssertionError('no such job')


def of(vid):
    return lambda t: t['needs']['variant'] == vid


def earned(j, tid):
    """What one job moved in the house's books (pay, a pocketed difference, money put back), not a stray happening."""
    return sum(r['amount'] for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid)


class Base(unittest.TestCase):
    def setUp(self):
        if HM is None:
            raise unittest.SkipTest('homemaker is filtered out by MNL_CAREERS')
        self.j = Journey('homemaker')

    def d(self, j=None):
        return (j or self.j).c['ext']['data']

    def at(self, pred):
        day, slot = find(pred)
        return Journey('homemaker', slot=slot, day=day)

    def act(self, j, name, **p):
        """An action, then whatever happened in the house in between is settled the patient way."""
        r = j.act(name, **p)
        self.settle(j)
        return r

    def settle(self, j):
        d = self.d(j)
        ev = d['desk']['ev']
        if ev:
            j.act('nt_desk', option=kit.desk_script(HM.DESK, ev['script'])['default'])
        if d['trouble']['ev']:
            j.act('nt_trouble', choice='refund')

    def best(self, j, tid, late='ok', receipt=None, overrides=None):
        """Play a job the careful way, from its key; `overrides` = {step id: callable(j, tid, step, key)} plays a step another way."""
        overrides = overrides or {}
        if not j.get(tid)['known']:
            self.act(j, 'ask', task=tid)
        for _ in range(80):
            t = j.get(tid)
            if t['status'] in ('completed', 'cancelled') or t['stage'] != 'work':
                break
            if t['kind'] == 'market' and not t['out']:
                self.act(j, 'nt_out', task=tid)
                continue
            st = t['needs']['steps'][t['at']]
            key = t['_key'].get(st['id'], {})
            if st['id'] in overrides:
                overrides[st['id']](j, tid, st, key)
                continue
            typ = st['type']
            if typ == 'pick':
                for iid, k in key['items'].items():
                    if k['ok'] is True and iid not in t['work'].get(st['id'], []):
                        self.act(j, 'nt_pick', task=tid, item=iid)
                self.act(j, 'nt_close', task=tid)
            elif typ == 'sort':
                for iid, k in key['items'].items():
                    self.act(j, 'nt_put', task=tid, item=iid, bin=k['right'][0])
                self.act(j, 'nt_close', task=tid)
            elif typ == 'order':
                for x in self.order_of(st, key):
                    self.act(j, 'nt_seq', task=tid, item=x)
                self.act(j, 'nt_close', task=tid)
            elif typ == 'choose':
                self.act(j, 'nt_choose', task=tid, option=next(o for o, k in key['options'].items() if k['q'] == 'good'))
            elif typ == 'haggle':
                self.act(j, 'nt_offer', task=tid, price=key['fair'])
            elif typ == 'receipt':
                self.act(j, 'nt_receipt', task=tid, amount=t['spent'] if receipt is None else receipt(t))
        if j.get(tid)['stage'] == 'late' and late:
            self.act(j, 'nt_late', task=tid, choice=late)
        return j.get(tid)

    @staticmethod
    def order_of(st, key):
        left = [i['id'] for i in st['items'] if i['id'] not in key['bad']]
        rules = [(a, b) for a, b, *_ in key['rules']]
        out = []
        while left:
            x = next(x for x in left if not any(b == x and a in left for a, b in rules))
            out.append(x)
            left.remove(x)
        return out


class Spec(Base):
    def test_spec_shape(self):
        s = HM.SPEC
        self.assertEqual((s['id'], s['prefix']), ('homemaker', 'nt_'))
        self.assertTrue(6 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        for k in s['no_tick'] + s['free_actions'] + tuple(HM.ACTIONS):
            self.assertTrue(k.startswith('nt_'), k)

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng', 'giả lập', 'nhiệm vụ', 'anh/chị')
        blob = json.dumps([hc.VARIANTS, HM.DESK, HM.SITUATIONS, HM.REG_STORY, HM.INTRO, HM.SPEC['meta'], hc.NOTEBOOK, hc.LATE_LINES,
                           hc.CHASE_LINES, hc.MODS, HM.REACT], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_every_job_is_well_formed(self):
        kinds = {v['kind'] for v in hc.VARIANTS}
        self.assertEqual(kinds, set(HM.KINDS) - {'setup'})
        for v in hc.VARIANTS:
            with self.subTest(job=v['id']):
                self.assertTrue(0 <= v['npc'] < len(hc.PEOPLE))
                steps = [hc._rice('thuong') if s == 'RICE' else s for s in v['steps']]
                ids = [s['id'] for s in steps]
                self.assertEqual(len(ids), len(set(ids)))
                for i, s in enumerate(steps):
                    self.assertIn(s['type'], HM.STEP_TYPES)
                    if s.get('when'):
                        self.assertIn(s['when'][0], ids[:i], 'a step can only wait on an earlier one')
                    if s['type'] == 'pick':
                        self.assertTrue(any(x['ok'] is not False for x in s['items']))
                    elif s['type'] == 'choose':
                        self.assertTrue(any(o['q'] == 'good' for o in s['options']))
                        for o in s['options']:
                            if o['q'] == 'good':
                                self.assertEqual(o['sev'], 0, o['id'])
                            elif o['q'] == 'bad':
                                self.assertGreater(o['sev'], 0, o['id'])
                    elif s['type'] == 'sort':
                        bins = {b['id'] for b in s['bins']}
                        for x in s['items']:
                            self.assertTrue(set(x['right']) <= bins and set(x['wrong']) <= bins, x['id'])
                    elif s['type'] == 'order':
                        bad = {x['id'] for x in s['items'] if x['bad']}
                        for a, b, *_ in s['rules']:
                            self.assertFalse({a, b} & bad, (a, b))
                    elif s['type'] == 'haggle':
                        self.assertGreater(s['quote'], s['fair'])
                if v['kind'] == 'market':
                    self.assertEqual(steps[-1]['type'], 'receipt')
                    self.assertTrue(v['budget'] > 0 and v['shop'])

    def test_pay_is_balanced(self):
        self.assertEqual(HM.PAY['setup'], 0)
        self.assertEqual(HM.PAY['tet'], max(HM.PAY.values()))
        for k, v in HM.PAY.items():
            if k != 'setup':
                self.assertTrue(10 <= v <= 30, k)
        # Every job's market budget covers the dearest honest shopping it can need.
        for v in hc.VARIANTS:
            if v['kind'] != 'market':
                continue
            dear = sum(x['price'] for s in v['steps'] if s['type'] == 'pick' for x in s['items'] if x['ok'] is True)
            dear += sum(s['quote'] for s in v['steps'] if s['type'] == 'haggle')
            self.assertLessEqual(dear, v['budget'], v['id'])


class Determinism(Base):
    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 25):
            for slot in range(0, 12):
                a, b = HM.make_task(day, slot, 1), HM.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(make_task('homemaker', day, slot, 1)['id'], f'homemaker-{day:04d}-{slot:02d}')

    def test_first_day_and_the_mix(self):
        self.assertEqual(HM.make_task(1, 0, 1)['kind'], 'setup')
        self.assertEqual([HM.make_task(1, s, 1)['needs']['variant'] for s in range(1, 10)], list(HM.DAY1))
        seen = {HM.make_task(d, s, 1)['needs']['variant'] for d in range(1, 80) for s in range(1, 12)}
        self.assertEqual(seen, {v['id'] for v in hc.VARIANTS}, 'every job turns up')
        for d in range(2, 30):
            self.assertEqual(HM.make_task(d, 1, 1)['kind'], 'market', d)
            self.assertEqual(HM.make_task(d, 2, 1)['kind'], 'cook', d)
            plan = HM._day_plan(d)
            self.assertEqual(len(plan), 11)
            self.assertTrue(len({k for k, _ in plan}) >= 5, d)

    def test_tet_comes_late(self):
        for d in range(1, 6):
            self.assertNotIn('tet', {k for k, _ in HM._day_plan(d)}, d)


class Careful(Base):
    def test_the_first_day_done_carefully(self):
        j = self.j
        self.assertEqual(j.task['kind'], 'setup')
        for t in list(j.c['tasks']):
            if t['status'] in ('completed', 'cancelled'):
                continue
            t = self.best(j, t['id'])
            self.assertEqual(t['status'], 'completed', t['title'])
            self.assertFalse(cq.slips(t), (t['title'], cq.slips(t)))
            self.assertEqual(earned(j, t['id']), HM.PAY[t['kind']])
        validate_state(json.loads(json.dumps(j.state)))

    def test_every_job_can_be_done_cleanly_for_full_pay(self):
        for v in hc.VARIANTS:
            with self.subTest(job=v['id']):
                j = self.at(of(v['id']))
                tid = j.task['id']
                t = self.best(j, tid)
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(cq.slips(t), cq.slips(t))
                if not t.get('twist'):
                    self.assertEqual(earned(j, tid), HM.PAY[v['kind']])
                validate_state(json.loads(json.dumps(j.state)))


class Mistakes(Base):
    def test_shrimp_for_the_allergic_child_is_a_safety_slip(self):
        j = self.at(of('c_tom'))
        tid = j.task['id']

        def wrong(j, tid, st, key):
            for iid, k in key['items'].items():
                self.act(j, 'nt_put', task=tid, item=iid, bin='thuong' if iid == 'su' else k['right'][0])
            self.act(j, 'nt_close', task=tid)
        t = self.best(j, tid, overrides={'chia': wrong})
        self.assertTrue(cq.safety(t))
        self.assertTrue(any(r['sev'] >= 3 for r in cq.slips(t)))
        self.assertLess(earned(j, tid), HM.PAY['cook'])

    def test_the_sleeping_pill_in_the_morning(self):
        j = self.at(of('e_thuoc'))
        tid = j.task['id']
        step = next(s for s in j.task['needs']['steps'] if s['type'] == 'pick')

        def wrong(j, tid, st, key):
            for iid, k in key['items'].items():
                if k['ok'] is True or iid == 'hong':
                    self.act(j, 'nt_pick', task=tid, item=iid)
            self.act(j, 'nt_close', task=tid)
        t = self.best(j, tid, overrides={step['id']: wrong})
        self.assertTrue(cq.safety(t))

    def test_wilted_greens_and_a_forgotten_item(self):
        j = self.at(of('m_canh'))
        tid = j.task['id']

        def wrong(j, tid, st, key):
            for iid in ('rm_b', 'ct_a', 'dua'):           # the sprayed greens, no good ones
                self.act(j, 'nt_pick', task=tid, item=iid)
            self.act(j, 'nt_close', task=tid)
        t = self.best(j, tid, overrides={'rau': wrong})
        codes = [r['code'] for r in cq.slips(t)]
        self.assertTrue(any('rau.rm_b' in c for c in codes), codes)
        self.assertTrue(any('rau.rm_a' in c for c in codes), codes)

    def test_buying_at_the_first_price_is_overpaying(self):
        j = self.at(of('m_canh'))
        tid = j.task['id']
        t = self.best(j, tid, overrides={'gia': lambda j, tid, st, key: self.act(j, 'nt_buy', task=tid)})
        self.assertTrue(any(r['code'].endswith('gia.dat') for r in cq.slips(t)))
        self.assertEqual(t['work']['gia'], 16)
        self.assertEqual(self.d(j)['stats']['overpaid'], 1)

    def test_a_rude_lowball_ends_the_haggling(self):
        j = self.at(of('m_canh'))
        tid = j.task['id']

        def lowball(j, tid, st, key):
            self.act(j, 'nt_offer', task=tid, price=5)
            self.assertTrue(j.get(tid)['bid']['firm'])
            with self.assertRaises(GameError):
                j.act('nt_offer', task=tid, price=12)
            self.act(j, 'nt_buy', task=tid)
        t = self.best(j, tid, overrides={'gia': lowball})
        self.assertEqual(t['status'], 'completed')
        self.assertIsNone(t['bid'])

    def test_the_market_book_written_low_comes_from_your_own_pocket(self):
        j = self.at(of('m_canh'))
        t = self.best(j, j.task['id'], receipt=lambda t: t['spent'] - 2)
        self.assertTrue(any(r['code'].endswith('so.thieu') for r in cq.slips(t)))
        self.assertLess(earned(j, t['id']), HM.PAY['market'])

    def _padded(self, savvy_low):
        def pred(t):
            return t['kind'] == 'market' and (folk.traits(f'{t["id"]}-so', 'picky')['savvy'] < 60) == savvy_low and not HM.twist_of(t)
        return self.at(pred)

    def test_a_padded_market_book_is_caught_by_a_sharp_eye(self):
        j = self._padded(False)
        t = self.best(j, j.task['id'], receipt=lambda t: t['spent'] + 1)
        self.assertTrue(any(r['code'].startswith('hn:') and r['sev'] == 3 for r in cq.slips(t)))
        self.assertEqual(self.d(j)['stats']['caught'], 1)
        self.assertEqual(self.d(j)['audits'], [])

    def test_a_padded_market_book_comes_up_again_days_later(self):
        j = self._padded(True)
        t = self.best(j, j.task['id'], receipt=lambda t: t['spent'] + 1)
        self.assertFalse(cq.slips(t))
        self.assertEqual(earned(j, t['id']), HM.PAY['market'] + 1)
        au = self.d(j)['audits'][0]
        self.assertEqual((au['diff'], au['state']), (1, 'wait'))
        validate_state(json.loads(json.dumps(j.state)))
        for _ in range(4):
            if self.d(j)['trouble']['ev']:
                break
            j.act('end_day', carry_event=True)
            j.act('start_day')
            ev = self.d(j)['desk']['ev']
            if ev:
                j.act('nt_desk', option=kit.desk_script(HM.DESK, ev['script'])['default'])
            setup = j.task
            if setup['kind'] == 'setup' and setup['status'] not in ('completed', 'cancelled'):
                j.act('nt_choose', task=setup['id'], option='count')
        ev = self.d(j)['trouble']['ev']
        self.assertTrue(ev and ev['kind'] == 'audit')
        with self.assertRaises(GameError):              # chị Thảo is waiting for an answer first
            j.act('nt_out', task=setup['id'])
        validate_state(json.loads(json.dumps(j.state)))
        before = j.c['money']
        j.act('nt_trouble', choice='refund')
        self.assertEqual(j.c['money'], before - 1)
        self.assertEqual(self.d(j)['audits'][0]['state'], 'done')
        self.assertIsNone(self.d(j)['trouble']['ev'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_calling_for_the_list_shows_it_and_costs_a_little_patience(self):
        j = self.at(of('m_canh'))
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('nt_out', task=tid)
        view = lambda: next(x for x in public_state(j.state)['careers']['homemaker']['tasks'] if x['id'] == tid)
        self.assertIsNone(view()['needs']['shop'])
        self.assertEqual(view()['needs']['note'], '')         # the note repeats the list
        p = j.get(tid)['patience']
        j.act('nt_call', task=tid)
        self.assertEqual(view()['needs']['shop'], hc.VARIANTS[0]['shop'])
        self.assertLess(j.get(tid)['patience'], p)
        with self.assertRaises(GameError):
            j.act('nt_call', task=tid)

    def test_the_market_list_must_be_read_before_buying(self):
        j = self.at(of('m_canh'))
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('nt_pick', task=tid, item='rm_a')

    def test_tapping_the_last_task_again_takes_it_back(self):
        j = self.at(of('c_trua'))
        tid = j.task['id']
        j.act('ask', task=tid)
        while j.get(tid)['needs']['steps'][j.get(tid)['at']]['type'] != 'order':
            st = j.get(tid)['needs']['steps'][j.get(tid)['at']]
            key = j.get(tid)['_key'][st['id']]
            if st['type'] == 'choose':
                j.act('nt_choose', task=tid, option=next(o for o, k in key['options'].items() if k['q'] == 'good'))
            elif st['type'] == 'pick':
                for iid, k in key['items'].items():
                    if k['ok'] is True:
                        j.act('nt_pick', task=tid, item=iid)
                j.act('nt_close', task=tid)
            else:
                for iid, k in key['items'].items():
                    j.act('nt_put', task=tid, item=iid, bin=k['right'][0])
                j.act('nt_close', task=tid)
        j.act('nt_seq', task=tid, item='com')
        j.act('nt_seq', task=tid, item='canh')
        j.act('nt_seq', task=tid, item='canh')
        self.assertEqual(j.get(tid)['work']['nau'], ['com'])


class Late(Base):
    def _late_job(self):
        return self.at(lambda t: t['day'] >= 3 and HM.twist_of(t) is not None and t['kind'] != 'market')

    def test_saying_it_is_fine_writes_the_debt_book(self):
        j = self._late_job()
        tid = j.task['id']
        t = self.best(j, tid, late=None)
        self.assertEqual(t['stage'], 'late')
        view = next(x for x in public_state(j.state)['careers']['homemaker']['tasks'] if x['id'] == tid)
        self.assertEqual(view['twist']['state'], 'on')
        validate_state(json.loads(json.dumps(j.state)))
        j.act('nt_late', task=tid, choice='ok')
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(earned(j, tid), 0)
        debt = self.d(j)['debts'][0]
        self.assertEqual(debt['owed'], HM.PAY[t['kind']])
        r = j.act('nt_chase', debt=debt['id'], tone='soft')
        self.assertTrue(r['message'])
        with self.assertRaises(GameError):                 # once a day
            j.act('nt_chase', debt=debt['id'], tone='soft')
        validate_state(json.loads(json.dumps(j.state)))

    def test_asking_politely_gets_something_today(self):
        j = self._late_job()
        tid = j.task['id']
        t = self.best(j, tid, late='ask')
        self.assertEqual(t['status'], 'completed')
        self.assertGreaterEqual(earned(j, tid), HM.PAY[t['kind']] // 2)


class Days(Base):
    def test_a_week_of_play_keeps_the_save_valid(self):
        j = self.j
        for day in range(1, 8):
            self.assertEqual(j.c['day'], day)
            self.assertEqual(j.task['kind'], 'setup')
            for t in [x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled')]:
                if j.get(t['id'])['status'] in ('completed', 'cancelled'):
                    continue
                self.settle(j)
                t = self.best(j, t['id'])
                self.assertFalse(cq.slips(t), (day, t['title'], cq.slips(t)))
            validate_state(json.loads(json.dumps(j.state)))
            self.settle(j)
            j.act('end_day', carry_event=True)
            j.act('start_day')
        self.assertGreater(self.d()['stats']['jobs'], 10)
        self.assertEqual(self.d()['stats']['slips'], 0)


class Surprises(Base):
    def test_every_surprise_option_is_playable(self):
        for x in HM.DESK:
            for o in x['options']:
                j = Journey('homemaker')
                j.c['money'] += 100
                j.c['ops']['finance']['opening_balance'] += 100
                self.d(j)['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('nt_choose', task=j.task['id'], option='count')
                self.assertTrue(j.act('nt_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_situations_are_playable(self):
        j = self.j
        for x in HM.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


class Saves(Base):
    def test_validate_rejects_broken_data(self):
        for path, value in ((('intro',), 'yes'), (('regulars',), {'9': {'visits': 1}}), (('audits',), [dict(id='x')]),
                            (('stats', 'jobs'), -1), (('debts',), 'junk'), (('trouble',), None)):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['homemaker']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        def budget(t):
            t['needs']['budget'] = 999

        def key(t):
            t['_key'] = {}

        def at(t):
            t['at'] = 99

        def work(t):
            t['work'] = {'ghost': 1}

        def twist(t):
            t['twist'], t['tw'] = dict(kind='late', n=0), dict(state='on', choice=None)

        def stage(t):
            t['stage'] = 'late'

        def bid(t):
            t['bid'] = dict(tries=1, ask=0, firm=False)
        for forge in (budget, key, at, work, twist, stage, bid):
            s = copy.deepcopy(self.j.state)
            t = next(x for x in s['careers']['homemaker']['tasks'] if x['kind'] == 'market')
            forge(t)
            with self.assertRaises(GameError, msg=forge.__name__):
                validate_state(s)

    def test_old_save_without_the_house_loads(self):
        s = new_state()
        s['careers'].pop('homemaker', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIn('homemaker', s['careers'])

    def test_data_from_an_older_build_fills_in(self):
        s = copy.deepcopy(self.j.state)
        d = s['careers']['homemaker']['ext']['data']
        for k in ('audits', 'trouble', 'debts'):
            d.pop(k)
        d['stats'].pop('haggled')
        validate_state(s)

    def test_hidden_facts_stay_hidden(self):
        j = self.at(of('m_canh'))
        tid = j.task['id']
        raw = json.dumps(public_state(j.state)['careers']['homemaker'], ensure_ascii=False)
        self.assertNotIn('_key', raw)
        self.assertIsNone(next(x for x in public_state(j.state)['careers']['homemaker']['tasks'] if x['id'] == tid)['needs'])
        j.act('ask', task=tid)
        view = next(x for x in public_state(j.state)['careers']['homemaker']['tasks'] if x['id'] == tid)
        self.assertEqual(view['needs']['shop'], hc.VARIANTS[0]['shop'])
        raw = json.dumps(view, ensure_ascii=False)
        for word in ('"ok"', '"fair"', '"right"', '"rules"', '"q"'):
            self.assertNotIn(word, raw)


@unittest.skipUnless(PLUGINS.get('homemaker'), 'homemaker is filtered out by MNL_CAREERS')
class OldStorySaves(unittest.TestCase):
    def old_save(self, chapter):
        s = new_state()
        jr.enable_story(s, 4242)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s['careers'].pop('homemaker')
        j = s['journey']
        j['chapter'] = chapter
        j['unlocked'] = [cid for n in range(1, min(chapter, jr.LAST) + 1) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        j['done'] = list(range(1, chapter))
        return s

    def test_the_house_joins_fresh_and_nothing_else_moves(self):
        s = self.old_save(3)
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['homemaker'], sort_keys=True), json.dumps(initial_career('homemaker'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)

    def test_chapter_two_opens_the_house(self):
        m = migrate_state(json.loads(json.dumps(self.old_save(3))))
        self.assertTrue(jr.is_unlocked(m, 'homemaker'))
        m = migrate_state(json.loads(json.dumps(self.old_save(1))))
        self.assertFalse(jr.is_unlocked(m, 'homemaker'))


if __name__ == '__main__':
    unittest.main()
