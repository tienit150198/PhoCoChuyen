"""Thông cống chú Hai (plugin career drain): the morning packing (the appointment book, five tools
on the bike, gloves), a callout (clues, diagnosis, the quote before the work, the right tool or a
stopgap, testing, cleaning, advice, the cash), the manhole safety drill paid by transfer, night
emergencies, warranty calls, a trip back for a tool, surprises, determinism, save validation and
old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.careers import kit, till, PLUGINS
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

DR = PLUGINS.get('drain')
ALL_TOOLS = [t['id'] for t in DR.TOOLS] if DR else []


def ledger(c, ref):
    return [r for r in c['ops']['finance']['ledger'] if r.get('ref') == ref]


class Base(unittest.TestCase):
    def setUp(self):
        if DR is None:
            raise unittest.SkipTest('drain is filtered out by MNL_CAREERS')
        self.j = Journey('drain')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def kind(self, kind, j=None):
        j = j or self.j
        return next(t for t in j.c['tasks'] if t['kind'] == kind and t['status'] not in ('completed', 'cancelled'))

    def settle_desk(self, j=None):
        j = j or self.j
        ev = j.c['ext']['data']['desk']['ev']
        if ev:
            j.act('cg_desk', option=kit.desk_script(DR.DESK, ev['script'])['default'])

    def set_out(self, tools=('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'camera'), gear=('gang_tay', 'kinh'), j=None):
        j = j or self.j
        self.settle_desk(j)
        t = self.kind('setup', j)
        for tool in list(j.c['ext']['data']['bike']):   # yesterday's tools are still on the bike
            j.act('cg_pack', tool=tool)
        for tool in tools:
            j.act('cg_pack', tool=tool)
        for g in gear:
            j.act('cg_gear', item=g)
        j.act('cg_setout', task=t['id'])
        return j.get(t['id'])

    def out(self, j, bike=None, gear=('gang_tay', 'kinh', 'ung', 'khau_trang')):
        """A journey started on a given day and slot has no packing job: the bike is already loaded."""
        j.c['ext']['data'].update(out=True, bike=list(bike or ('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'moc')), gear=list(gear))

    def at(self, pick, bike=None):
        day, slot = next((d, s) for d in range(2, 300) for s in range(1, 6) if pick(DR.make_task(d, s, 1)))
        j = Journey('drain', slot=slot, day=day)
        self.out(j, bike)
        return j

    def do_job(self, tid, j=None, level='list', finish=True):
        """The careful way: clues, the right diagnosis, the list price, the right tool, test, clean, advise, bill, pay."""
        j = j or self.j
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        t = j.get(tid)
        for how in ('hoi', 'nhin'):
            j.act('cg_check', task=tid, how=how)
        j.act('cg_diag', task=tid, cause=t['_cause'])
        j.act('cg_quote', task=tid, level=level)
        if t['kind'] == 'manhole':
            for step in DR.SAFETY:
                j.act('cg_safety', task=tid, step=step)
        cause = DR.CAUSES[t['_cause']]
        if cause.get('part'):
            j.act('cg_part', task=tid)
        else:
            tool = next(x for x in cause['fix'] if x in j.c['ext']['data']['bike'])
            j.act('cg_work', task=tid, tool=tool)
        if not finish:
            return j.get(tid)
        for a in ('cg_test', 'cg_clean', 'cg_advise'):
            j.act(a, task=tid)
        r = j.act('cg_bill', task=tid)
        t = j.get(tid)
        if t['stage'] == 'pay':
            r = j.act('cg_pay', task=tid, change=till.greedy(till.due(t['cash'])))
        return r


class Spec(Base):
    def test_spec_shape(self):
        s = DR.SPEC
        self.assertEqual((s['id'], s['prefix']), ('drain', 'cg_'))
        self.assertTrue(6 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        for k in s['no_tick'] + s['free_actions'] + tuple(DR.ACTIONS):
            self.assertTrue(k.startswith('cg_'), k)
        for k, v in DR.CAUSES.items():
            self.assertTrue(v['fix'] or v.get('part'), k)
            self.assertIn(k, DR.ADVICE)

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng', 'giả lập', 'nhiệm vụ', 'anh/chị')
        blob = json.dumps([DR.CALLS, DR.RECALLS, DR.DESK, DR.SITUATIONS, DR.REG_STORY, DR.INTRO, DR.SPEC['meta'], DR.CAUSES], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_price_list(self):
        self.assertEqual(DR.list_price('bon_rua', 'mo'), 25)
        self.assertEqual(DR.list_price('lavabo', 'xi_phong'), 16)
        self.assertEqual(DR.list_price('bon_rua', 'thong_hoi'), 18)
        self.assertEqual(DR.list_price('bon_cau', 'giay', 'emergency'), 30)
        self.assertEqual(DR.quote_for('high', 'bon_cau', 'giay', 'call'), 36)
        self.assertEqual(DR.quote_for('warranty', 'bon_cau', 'giay', 'recall'), 0)


class Determinism(Base):
    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 25):
            for slot in range(0, 8):
                a, b = DR.make_task(day, slot, 1), DR.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(make_task('drain', day, slot, 1)['id'], f'drain-{day:04d}-{slot:02d}')

    def test_first_day_and_the_book(self):
        self.assertEqual([DR.make_task(1, s, 1)['kind'] for s in range(3)], ['setup', 'call', 'call'])
        book = DR.make_task(1, 0, 1)['needs']['book']
        self.assertEqual([b['place'] for b in book], [DR.make_task(1, s, 1)['needs']['place'] for s in (1, 2, 3)])
        kinds = {DR.make_task(d, s, 1)['kind'] for d in range(2, 40) for s in range(1, 5)}
        self.assertTrue({'call', 'manhole', 'emergency', 'recall'} <= kinds, kinds)


class Packing(Base):
    def test_packing_right(self):
        t = self.set_out()
        self.assertFalse(t.get('slips'))
        self.assertTrue(self.d['out'])
        self.assertEqual(len(self.d['bike']), 5)

    def test_the_bike_holds_five(self):
        j = self.j
        for tool in ALL_TOOLS[:5]:
            j.act('cg_pack', tool=tool)
        with self.assertRaises(GameError):
            j.act('cg_pack', tool=ALL_TOOLS[5])
        j.act('cg_pack', tool=ALL_TOOLS[0])      # take one off again
        self.assertEqual(len(self.d['bike']), 4)

    def test_packing_wrong(self):
        t = self.set_out(tools=('gau', 'do_khi', 'moc'), gear=())
        codes = {x['code'] for x in t['slips']}
        self.assertTrue({'pack', 'no_gloves'} <= codes, codes)

    def test_fetching_a_tool_costs_the_waiting_customers(self):
        j = self.j
        self.set_out(tools=('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'camera'))
        t = self.kind('call')
        before = j.get(t['id'])['patience']
        with self.assertRaises(GameError):
            j.act('cg_fetch', tool='moc')      # the bike is full: say what stays behind
        j.act('cg_fetch', tool='moc', drop='camera')
        self.assertIn('moc', self.d['bike'])
        self.assertNotIn('camera', self.d['bike'])
        self.assertLess(j.get(t['id'])['patience'], before)


class Callout(Base):
    def test_the_careful_callout_pays_the_list_price(self):
        j = self.j
        self.set_out()
        t = self.kind('call')
        money = j.c['money']
        r = self.do_job(t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'), r)
        fair = DR.list_price(t['needs']['place'], t['_cause'])
        self.assertEqual(t['quote'], fair)
        self.assertEqual(sum(x['amount'] for x in ledger(j.c, t['id']) if x.get('category') != 'tip'), fair)
        self.assertGreaterEqual(j.c['money'] - money, fair)
        validate_state(json.loads(json.dumps(j.state)))

    def test_quote_and_diagnosis_come_first(self):
        j = self.j
        self.set_out()
        t = self.kind('call')
        j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            j.act('cg_diag', task=t['id'], cause='toc')     # look before guessing
        j.act('cg_check', task=t['id'], how='hoi')
        with self.assertRaises(GameError):
            j.act('cg_work', task=t['id'], tool='lo_xo')    # quote before the hands go in
        with self.assertRaises(GameError):
            j.act('cg_check', task=t['id'], how='hoi')

    def test_the_camera_tells_the_cause(self):
        j = self.j
        self.set_out()
        t = self.kind('call')
        j.act('ask', task=t['id'])
        r = j.act('cg_check', task=t['id'], how='camera')
        self.assertIn(DR.CAUSES[t['_cause']]['camera'], r['message'])
        view = next(x for x in public_state(j.state)['careers']['drain']['tasks'] if x['id'] == t['id'])
        self.assertEqual(view['camera'], DR.CAUSES[t['_cause']]['camera'])
        self.assertNotIn('_cause', view)

    def test_the_wrong_tool_fails_and_a_stopgap_must_be_said(self):
        j = self.at(lambda t: t['kind'] == 'call' and t['_cause'] == 'mo')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cg_check', task=tid, how='hoi')
        j.act('cg_diag', task=tid, cause='toc')
        j.act('cg_quote', task=tid, level='list')
        r = j.act('cg_work', task=tid, tool='pit_tong')
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['cleared'], 'fail')
        r = j.act('cg_work', task=tid, tool='lo_xo')
        self.assertEqual(j.get(tid)['cleared'], 'temp')
        j.act('cg_test', task=tid)
        j.act('cg_clean', task=tid)
        j.act('cg_bill', task=tid)
        t = j.get(tid)
        codes = {x['code'] for x in t['slips']}
        self.assertIn('recur', codes)
        self.assertEqual(t['cash']['price'], DR.list_price('bon_rua', 'toc'))   # the quote for the wrong cause: the shop's loss

    def test_a_quote_for_the_wrong_cause_is_noticed(self):
        j = self.at(lambda t: t['kind'] == 'call' and t['_cause'] == 'toc')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cg_check', task=tid, how='hoi')
        j.act('cg_diag', task=tid, cause='mo')
        j.act('cg_quote', task=tid, level='list')
        j.act('cg_work', task=tid, tool='lo_xo')
        for a in ('cg_test', 'cg_clean', 'cg_advise'):
            j.act(a, task=tid)
        j.act('cg_bill', task=tid)
        t = j.get(tid)
        self.assertIn('misquote', {x['code'] for x in t['slips']})
        self.assertEqual(t['cash']['price'], DR.list_price(t['needs']['place'], 'mo'))

    def test_a_high_quote(self):
        refused = kept = 0
        for d in range(2, 80):
            for s in range(1, 5):
                t = DR.make_task(d, s, 1)
                if t['kind'] != 'call':
                    continue
                j = Journey('drain', slot=s, day=d)
                self.out(j)
                tid = j.task['id']
                j.act('ask', task=tid)
                j.act('cg_check', task=tid, how='hoi')
                j.act('cg_diag', task=tid, cause=t['_cause'])
                j.act('cg_quote', task=tid, level='high')
                t = j.get(tid)
                if t['status'] == 'completed':
                    refused += 1
                    self.assertIn('greedy', {x['code'] for x in t['slips']})
                    self.assertFalse(ledger(j.c, tid))
                else:
                    kept += 1
                    self.assertEqual(t['quote'], DR.quote_for('high', t['needs']['place'], t['_cause'], 'call'))
                if refused and kept:
                    return
        self.fail('both a refusal and an accepted high quote were expected')

    def test_overcharging_shows_in_the_review_and_at_night(self):
        j = self.at(lambda t: t['kind'] == 'call' and DR._hash('cg-refuse', t['id']) % 100 >= 60)
        tid = j.task['id']
        self.do_job(tid, j, level='high')
        t = j.get(tid)
        self.assertIn('overcharge', {x['code'] for x in t['slips']})
        lines = j.act('end_day')['summary']['career']['lines']
        self.assertTrue(any('nói thách' in x for x in lines), lines)

    def test_chemicals_on_an_old_pipe(self):
        j = self.at(lambda t: t['kind'] == 'call' and t['needs']['old'], bike=('pit_tong', 'lo_xo', 'may_lo_xo', 'camera', 'moc'))
        j.c['ext']['data']['gear'] = ['gang_tay']
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cg_check', task=tid, how='nhin')
        j.act('cg_diag', task=tid, cause='toc')
        j.act('cg_quote', task=tid, level='list')
        j.act('cg_chem', task=tid)
        codes = {x['code'] for x in j.get(tid)['slips']}
        self.assertTrue({'chem_burn', 'chem_pipe'} <= codes, codes)

    def test_a_cracked_trap_needs_the_part(self):
        j = self.at(lambda t: t['kind'] == 'call' and t['_cause'] == 'xi_phong')
        tid = j.task['id']
        parts = kit.stock(j.c, 'xi_phong')
        self.do_job(tid, j)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertEqual(kit.stock(j.c, 'xi_phong'), parts - 1)

    def test_giving_up_honestly(self):
        j = self.j
        self.set_out()
        t = self.kind('call')
        j.act('ask', task=t['id'])
        j.act('cg_giveup', task=t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(ledger(j.c, t['id']))


class Kinds(Base):
    def test_a_manhole_done_safely_is_paid_by_transfer(self):
        j = self.at(lambda t: t['kind'] == 'manhole', bike=('gau', 'do_khi', 'may_phun', 'lo_xo', 'camera'))
        tid = j.task['id']
        money = j.c['money']
        self.do_job(tid, j)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertIsNone(t['cash'])
        self.assertEqual(j.c['money'] - money, DR.list_price('ho_ga', 'bun'))
        self.assertEqual(j.c['ext']['data']['stats']['safety_ok'], 1)

    def test_a_manhole_without_the_gas_check(self):
        j = self.at(lambda t: t['kind'] == 'manhole', bike=('gau', 'do_khi', 'may_phun', 'lo_xo', 'camera'))
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cg_check', task=tid, how='nhin')
        j.act('cg_diag', task=tid, cause='bun')
        j.act('cg_quote', task=tid, level='list')
        with self.assertRaises(GameError):
            j.act('cg_safety', task=tid, step='quat')     # measure first
        j.act('cg_work', task=tid, tool='gau')
        t = j.get(tid)
        self.assertTrue(any(x['code'] == 'gas' and x['safety'] for x in t['slips']))

    def test_warranty_calls(self):
        for fault in ('shop', 'new'):
            j = self.at(lambda t, f=fault: t['kind'] == 'recall' and t['_fault'] == f, bike=('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'camera'))
            tid = j.task['id']
            self.do_job(tid, j, level='warranty' if fault == 'shop' else 'list')
            t = j.get(tid)
            self.assertEqual(t['status'], 'completed')
            self.assertFalse(t.get('slips'), fault)
            j = self.at(lambda t, f=fault: t['kind'] == 'recall' and t['_fault'] == f, bike=('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'camera'))
            tid = j.task['id']
            self.do_job(tid, j, level='list')
            self.assertEqual('warranty' in {x['code'] for x in j.get(tid).get('slips', [])}, fault == 'shop')

    def test_night_emergency_surcharge_is_fair_when_said(self):
        j = self.at(lambda t: t['kind'] == 'emergency', bike=('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'camera'))
        tid = j.task['id']
        self.do_job(tid, j)
        t = j.get(tid)
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['quote'], DR.list_price(t['needs']['place'], t['_cause']) * DR.NIGHT // 100)


class Days(Base):
    def test_a_week_of_play_keeps_the_save_valid(self):
        j = self.j
        for day in range(1, 8):
            self.assertEqual(j.c['day'], day)
            if kit.stock(j.c, 'gang_tay') < 2:
                kit.add_lot(j.c, 'gang_tay', 6, 2, 90, 'test')
            if kit.stock(j.c, 'xi_phong') < 2:
                kit.add_lot(j.c, 'xi_phong', 3, 6, 365, 'test')
            book = {b['place'] for b in self.kind('setup')['needs']['book']}
            tools = ('gau', 'do_khi', 'may_phun', 'may_lo_xo', 'moc') if 'ho_ga' in book else ('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'moc')
            self.set_out(tools=tools, gear=('gang_tay', 'kinh', 'ung', 'khau_trang'))
            for t in [x for x in j.c['tasks'] if x['kind'] != 'setup' and x['status'] not in ('completed', 'cancelled')]:
                self.settle_desk()
                need = DR.CAUSES[t['_cause']]['fix']
                if need and not set(need) & set(self.d['bike']):
                    j.act('cg_fetch', tool=need[0], drop=next(x for x in self.d['bike'] if x not in need))
                self.do_job(t['id'], level='warranty' if t['kind'] == 'recall' and t['_fault'] == 'shop' else 'list')
                self.assertFalse(j.get(t['id']).get('slips'), t['title'])
            validate_state(json.loads(json.dumps(j.state)))
            self.settle_desk()
            j.act('end_day')
            j.act('start_day')
            self.assertEqual(j.task['kind'], 'setup')
        self.assertGreater(self.d['stats']['jobs'], 10)


class Surprises(Base):
    def test_every_surprise_option_is_playable(self):
        for x in DR.DESK:
            for o in x['options']:
                j = Journey('drain')
                self.set_out(j=j)
                j.c['money'] += 100
                j.c['ops']['finance']['opening_balance'] += 100
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('cg_fetch', tool='moc', drop='camera')
                self.assertTrue(j.act('cg_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_situations_are_playable(self):
        j = self.j
        for x in DR.SPEC['situations']:
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
        for path, value in ((('bike',), ALL_TOOLS[:6]), (('gear',), ['cape']), (('out',), 'yes'), (('temp_fixes',), [dict(day=1, task='x', cause='ghost')])):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['drain']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        for key, value in (('_cause', 'toc' if DR.make_task(1, 1, 1)['_cause'] != 'toc' else 'mo'), ('cleared', 'magic'), ('level', 'free')):
            s = copy.deepcopy(self.j.state)
            t = next(x for x in s['careers']['drain']['tasks'] if x['kind'] == 'call')
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_old_save_without_the_shop_loads(self):
        s = new_state()
        s['careers'].pop('drain', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIn('drain', s['careers'])

    def test_hidden_facts_stay_hidden(self):
        self.set_out()
        t = self.kind('call')
        self.j.act('ask', task=t['id'])
        view = public_state(self.j.state)['careers']['drain']
        raw = json.dumps(view, ensure_ascii=False)
        self.assertNotIn('_cause', raw)
        tv = next(x for x in view['tasks'] if x['id'] == t['id'])
        self.assertEqual(set(tv['needs']['clues'].values()), {None})
        self.assertIsNone(tv['prices'])


if __name__ == '__main__':
    unittest.main()
