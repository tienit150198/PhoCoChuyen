"""Tiệm Áo Chỉ Mây (career `clothing`): every job kind done right and wrong, the till,
consequences, tips, restock, determinism, saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.engine import GameError, validate_state, migrate_state, new_state, apply_action
from game.careers import PLUGINS, kit, till
from game import consequences as cq

A = PLUGINS.get('clothing')


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


def find(kind, pred=None, days=range(1, 40)):
    for day in days:
        for slot in range(12):
            if (day, slot) in A.STORY:
                continue
            t = A.make_task(day, slot, 1)
            if t['kind'] == kind and (pred is None or pred(t)):
                return day, slot
    raise AssertionError('no task of kind ' + kind)


def job(kind, pred=None, days=range(1, 40)):
    day, slot = find(kind, pred, days)
    j = Journey('clothing', slot=slot, day=day)
    j.act('ask', task=j.task['id'])
    return j


def empty(j, item, size):
    """Someone else sold every piece of this size (stock and grid move together)."""
    g = j.c['ext']['data']['grid'][item]
    kit.take(j.c, item, g[size])
    g[size] = 0


def slip_codes(t):
    return [x['code'] for x in cq.slips(t)]


def pay_exact(j, tid):
    t = j.get(tid)
    return j.act('ao_pay', task=tid, change=till.greedy(till.due(t['cash'])), confirm=True)


def bill_and_pay(j, tid):
    t = j.get(tid)
    if t['stage'] != 'pay':
        j.act('ao_bill', task=tid)
    if j.get(tid)['haggle'] == 'ask':
        j.act('ao_haggle', task=tid, answer='small')
    return pay_exact(j, tid)


def good_outfit(t):
    """A correct outfit for the task (right sizes, right colours, the needed accessory)."""
    n = t['needs']
    occ = n['occasion']
    top, waist = n['top'], n['waist']
    one = top if top in ('S', 'M', 'L') else 'L'
    return {
        'wedding': [('dress', one, 'xanh mint'), ('belt', 'F', 'nâu')],
        'interview': [('shirt', top, 'trắng'), ('jeans', waist, 'xanh đậm'), ('belt', 'F', 'đen')],
        'beach': [('dress', one, 'hoa nhí'), ('hat', 'F', 'cói')],
        'tet': [('aodai', one, 'đỏ'), ('hat', 'F', 'cói')],
    }[occ]


def solve(j, tid):
    """The careful way through any job."""
    t = j.get(tid)
    if not t['known']:
        j.act('ask', task=tid)
        t = j.get(tid)
    k = t['kind']
    if k == 'fit':
        for ln in t['needs']['lines']:
            j.act('ao_pick', task=tid, item=ln['item'], size=ln['_size'], colour=ln['colour'])
        return bill_and_pay(j, tid)
    if k == 'outfit':
        pieces = good_outfit(t)
        total = sum(A._price(j.c, i) for i, _, _ in pieces)
        if total > t['needs']['budget']:
            pieces = pieces[:-1] if t['needs']['occasion'] != 'beach' else pieces
        for item, size, colour in pieces:
            j.act('ao_pick', task=tid, item=item, size=size, colour=colour)
        return bill_and_pay(j, tid)
    if k == 'alter':
        if t['stage'] == 'measure':
            if not t['alt']['measured']:
                j.act('ao_measure', task=tid)
            j.act('ao_alter_send', task=tid)
        for _ in range(A.TAILOR_TURNS + 1):
            if j.c['turn'] >= j.get(tid)['alt']['sent'] + A.TAILOR_TURNS:
                break
            j.act('ao_intro')      # free; does not tick
            j.act('advance')
        j.act('ao_alter_collect', task=tid)
        return bill_and_pay(j, tid)
    if k == 'room':
        q = t['needs']['queue']
        for i, x in enumerate(q):
            j.act('ao_room_tag', task=tid, count=x['items'])
            j.act('ao_room_out', task=tid)
            if x['_out'] == 'left':
                j.act('ao_room_check', task=tid)
            elif x['_out'] == 'hidden':
                j.act('ao_room_check', task=tid)
                j.act('ao_room_ask', task=tid)
        b = t['needs']['buy']
        j.act('ao_pick', task=tid, item=b['item'], size=b['size'], colour=b['colour'])
        return bill_and_pay(j, tid)
    if k == 'return':
        for w in A.FACTS:
            j.act('ao_inspect', task=tid, what=w)
        best = {'good': 3, 'ok': 2, 'bad': 0}
        ok = A._return_ok(t['needs'])
        choice = max(ok, key=lambda x: (best[ok[x]], x == 'exchange'))
        return j.act('ao_return_do', task=tid, choice=choice, tone='calm', new_size=t['needs']['new_size'], confirm=True)
    if k == 'sale':
        for i, ln in enumerate(t['needs']['lines']):
            j.act('ao_tag', task=tid, line=i, price=t['sale']['base'][ln['item']] * (100 - ln['pct']) // 100)
        return j.act('ao_sale_done', task=tid, confirm=True)
    if k == 'online':
        for x in t['needs']['lines']:
            j.act('ao_pack', task=tid, **x)
        j.act('ao_label', task=tid)
        j.act('ao_seal', task=tid)
        return j.act('ao_ship', task=tid, confirm=True)
    for item, size, colour in good_outfit(dict(needs=dict(occasion=t['needs']['theme'], top='M', waist='29'))):
        j.act('ao_dress', task=tid, item=item, colour=colour)
    for i in range(len(j.get(tid)['disp']['pieces'])):
        j.act('ao_steam', task=tid, index=i)
    return j.act('ao_display_done', task=tid, confirm=True)


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingBasicsTests(unittest.TestCase):
    def test_registered_and_spec(self):
        s = A.SPEC
        self.assertEqual(s['id'], 'clothing')
        self.assertEqual(s['prefix'], 'ao_')
        self.assertTrue(5 <= len(s['people']) <= 8)
        self.assertTrue(all(p[3] in ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet') for p in s['people']))
        self.assertEqual(len(s['staff']), 4)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        self.assertEqual(len(s['stories']), 3)
        self.assertEqual(len(s['review_asides']), 4)
        for it in A.ITEMS:
            self.assertIn(it['id'], A.PRICES)
            self.assertGreater(A.PRICES[it['id']], it['cost'])
            self.assertTrue(A.SIZES[it['id']] and A.COLOURS[it['id']])
            for col in A.COLOURS[it['id']]:
                self.assertIn(col, A.SWATCH)
        self.assertEqual(set(A.JEANS_WAIST), set(A.SIZES['jeans']))

    def test_every_kind_is_dealt(self):
        seen = {A.make_task(d, s, 1)['kind'] for d in range(1, 20) for s in range(12)}
        self.assertEqual(seen, set(A.KINDS))

    def test_first_day_is_gentle(self):
        kinds = [A.make_task(1, s, 1)['kind'] for s in range(12)]
        self.assertNotIn('return', kinds)
        self.assertNotIn('sale', kinds)
        self.assertNotIn('display', kinds)
        for s in range(12):
            t = A.make_task(1, s, 1)
            if t['kind'] == 'fit':
                self.assertTrue(all(ln['clue'] in ('label', 'waist', 'age', 'free') for ln in t['needs']['lines']))

    def test_determinism_and_hidden_answers(self):
        for d in range(1, 31):
            for s in range(12):
                a, b = A.make_task(d, s, 3), A.make_task(d, s, 3)
                self.assertEqual(a, b)
                pub = json.dumps(A.public_task(dict(a, known=True)), ensure_ascii=False)
                self.assertNotIn('"_', pub)
                self.assertIsNone(A.public_task(a)['needs'])

    def test_story_days_continue(self):
        self.assertEqual(A.make_task(2, 0, 1)['title'], 'Buổi phỏng vấn đầu tiên')
        self.assertEqual(A.make_task(5, 0, 1)['npc'], 'clothing_npc_03')
        self.assertEqual(A.make_task(7, 0, 1)['kind'], 'alter')
        self.assertEqual(A.make_task(9, 0, 1)['needs']['occasion'], 'wedding')

    def test_intro_is_free_and_remembered(self):
        j = Journey('clothing')
        turn = j.c['turn']
        self.assertFalse(j.c['ext']['data']['intro'])
        j.act('ao_intro')
        self.assertTrue(j.c['ext']['data']['intro'])
        self.assertEqual(j.c['turn'], turn)
        intro = A.content()['intro']
        self.assertTrue(intro['does'] and intro['meets'] and intro['stars'])

    def test_grid_matches_stock(self):
        j = Journey('clothing')
        g = j.c['ext']['data']['grid']
        for it in A.ITEMS:
            self.assertEqual(sum(g[it['id']].values()), kit.stock(j.c, it['id']))
        self.assertGreater(g['tee']['M'], g['tee']['XL'])

    def test_a_full_first_week(self):
        j = Journey('clothing')
        for day in range(7):
            for _ in range(4):
                open_ = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]
                if not open_:
                    j.act('more_work')
                    open_ = [j.task]
                t = open_[0]
                for it in A.ITEMS:        # the player keeps the racks full (restock is tested below)
                    if min(j.c['ext']['data']['grid'][it['id']].values()) < 2 and kit.stock(j.c, it['id']) < A.CAPACITY - 8:
                        kit.add_lot(j.c, it['id'], 8, it['cost'], 999, 'test')
                A._sync(j.c)
                solve(j, t['id'])
                self.assertEqual(j.get(t['id'])['status'], 'completed', t['kind'])
            roundtrip(j)
            r = j.act('end_day', carry_event=True)
            self.assertIn('lines', r['summary']['career'])
            j.act('start_day')
        self.assertGreaterEqual(j.c['ext']['data']['look'] if 'look' in j.c['ext']['data'] else A._look(j.c), 1)


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingFitTests(unittest.TestCase):
    def test_right_size_right_colour(self):
        j = job('fit')
        t = j.task
        money = j.c['money']
        stock = {ln['item']: kit.stock(j.c, ln['item']) for ln in t['needs']['lines']}
        r = solve(j, t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(slip_codes(t), [])
        self.assertEqual(t['bill']['sub'], sum(x['amount'] for x in t['bill']['lines']))
        self.assertGreaterEqual(j.c['money'] - money, t['bill']['total'])
        for item, n in stock.items():
            self.assertLess(kit.stock(j.c, item), n)
        self.assertTrue(r.get('celebrate'))
        roundtrip(j)

    def test_brand_clue_means_one_size_up(self):
        j = job('fit', lambda t: any(ln['clue'] == 'brand' for ln in t['needs']['lines']))
        ln = next(ln for ln in j.task['needs']['lines'] if ln['clue'] == 'brand')
        said = ln['say'].rsplit('size ', 1)[1].rstrip('.')
        self.assertEqual(A.LETTERS.index(ln['_size']), A.LETTERS.index(said) + 1)

    def test_wrong_size_comes_back_to_swap(self):
        j = job('fit', lambda t: t['needs']['lines'][0]['item'] in ('tee', 'shirt', 'dress', 'jeans') and len(t['needs']['lines']) == 1)
        t = j.task
        ln = t['needs']['lines'][0]
        sizes = A.SIZES[ln['item']]
        wrong = sizes[(sizes.index(ln['_size']) + 1) % len(sizes)]
        j.act('ao_pick', task=t['id'], item=ln['item'], size=wrong, colour=ln['colour'])
        bill_and_pay(j, t['id'])
        t = j.get(t['id'])
        self.assertIn('wrong_size', slip_codes(t))
        self.assertEqual(next(x for x in cq.slips(t) if x['code'] == 'wrong_size')['sev'], 2)
        swaps = j.c['ext']['data']['swaps']
        self.assertEqual(len(swaps), 1)
        self.assertEqual(swaps[0]['right'], ln['_size'])
        roundtrip(j)
        with self.assertRaises(GameError):
            j.act('ao_swap', id=swaps[0]['id'])        # tomorrow, not today
        j.act('end_day', carry_event=True)
        j.act('start_day')
        before = j.c['ext']['data']['grid'][ln['item']][wrong]
        j.act('ao_swap', id=swaps[0]['id'], mode='swap')
        self.assertEqual(j.c['ext']['data']['swaps'], [])
        self.assertEqual(j.c['ext']['data']['grid'][ln['item']][wrong], before + 1)
        roundtrip(j)

    def test_ignored_swap_costs_a_review(self):
        j = job('fit', lambda t: t['needs']['lines'][0]['item'] in ('tee', 'shirt') and len(t['needs']['lines']) == 1)
        t = j.task
        ln = t['needs']['lines'][0]
        sizes = A.SIZES[ln['item']]
        j.act('ao_pick', task=t['id'], item=ln['item'], size=sizes[(sizes.index(ln['_size']) + 1) % len(sizes)], colour=ln['colour'])
        bill_and_pay(j, t['id'])
        j.act('end_day', carry_event=True)
        j.act('start_day')
        r = j.act('end_day', carry_event=True)
        self.assertTrue(any('1★' in x for x in r['summary']['career']['lines']))
        self.assertEqual(j.c['ext']['data']['swaps'], [])

    def test_fitting_room_reveals_the_size(self):
        j = job('fit', lambda t: t['needs']['lines'][0]['item'] in ('tee', 'shirt') and len(t['needs']['lines']) == 1)
        t = j.task
        ln = t['needs']['lines'][0]
        sizes = A.SIZES[ln['item']]
        small = sizes[sizes.index(ln['_size']) - 1] if sizes.index(ln['_size']) else None
        if small is None:
            self.skipTest('smallest size')
        j.act('ao_pick', task=t['id'], item=ln['item'], size=small, colour=ln['colour'])
        r = j.act('ao_try', task=t['id'], index=0)
        self.assertIn('Chật', r['message'])
        self.assertEqual(j.get(t['id'])['tried'], ['small'])
        with self.assertRaises(GameError):
            j.act('ao_bill', task=t['id'])
        j.act('ao_unpick', task=t['id'], index=0)
        j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        j.act('ao_try', task=t['id'], index=0)
        bill_and_pay(j, t['id'])
        self.assertEqual(slip_codes(j.get(t['id'])), [])

    def test_wrong_colour_is_refused_at_the_bill(self):
        j = job('fit', lambda t: len(t['needs']['lines']) == 1 and t['needs']['lines'][0]['item'] not in ('hat', 'belt', 'socks'))
        t = j.task
        ln = t['needs']['lines'][0]
        other = next(c for c in A.COLOURS[ln['item']] if c != ln['colour'])
        j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=other)
        r = j.act('ao_bill', task=t['id'])
        self.assertTrue(r.get('refused'))
        self.assertIn('wrong_colour', slip_codes(j.get(t['id'])))
        j.act('ao_unpick', task=t['id'], index=0)
        j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        bill_and_pay(j, t['id'])
        self.assertEqual(j.get(t['id'])['status'], 'completed')

    def test_extra_item_is_refused(self):
        j = job('fit', lambda t: len(t['needs']['lines']) == 1)
        t = j.task
        ln = t['needs']['lines'][0]
        j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        j.act('ao_pick', task=t['id'], item='socks', size='F', colour='đen')
        self.assertTrue(j.act('ao_bill', task=t['id']).get('refused'))
        self.assertIn('extra', slip_codes(j.get(t['id'])))

    def test_out_of_size_cannot_be_picked(self):
        j = job('fit')
        t = j.task
        ln = t['needs']['lines'][0]
        empty(j, ln['item'], ln['_size'])
        with self.assertRaises(GameError):
            j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingTillTests(unittest.TestCase):
    def _billed(self, pred=None):
        for day in range(1, 60):
            for slot in range(12):
                if (day, slot) in A.STORY:
                    continue
                t = A.make_task(day, slot, 1)
                if t['kind'] != 'fit' or t['needs']['haggle']:
                    continue
                price = sum(A.PRICES[ln['item']] for ln in t['needs']['lines'])
                rec = till.new(price, t['id'])
                if pred is None or pred(t, rec):
                    j = Journey('clothing', slot=slot, day=day)
                    j.act('ask', task=t['id'])
                    for ln in t['needs']['lines']:
                        j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
                    j.act('ao_bill', task=t['id'])
                    return j, j.get(t['id'])
        raise AssertionError('no such bill')

    def test_bill_total_is_traceable(self):
        j, t = self._billed()
        b = t['bill']
        self.assertEqual(b['total'], sum(A._price(j.c, ln['item']) for ln in t['needs']['lines']))
        self.assertEqual(t['cash']['price'], b['total'])
        self.assertGreaterEqual(sum(t['cash']['tender']), b['total'])
        pub = A.public_task(t)
        self.assertEqual(pub['cash']['due'], sum(t['cash']['tender']) - b['total'])

    def test_exact_change(self):
        j, t = self._billed(lambda t, r: till.due(r) > 0)
        pay_exact(j, t['id'])
        t = j.get(t['id'])
        self.assertIn(t['cash']['outcome'], ('exact', 'keep'))
        self.assertEqual(t['status'], 'completed')

    def test_short_change_is_caught_or_found_at_home(self):
        j, t = self._billed(lambda t, r: till.due(r) >= 10)
        due = till.due(t['cash'])
        r = j.act('ao_pay', task=t['id'], change=till.greedy(due - 10), confirm=True)
        t = j.get(t['id'])
        if r.get('refused'):
            self.assertEqual(t['status'], 'in_progress')
            self.assertEqual(t['cash']['asked'], 1)
            pay_exact(j, t['id'])
            self.assertIn('change_short', slip_codes(j.get(t['id'])))
        else:
            self.assertEqual(t['cash']['outcome'], 'missed')
            self.assertIn('change_home', slip_codes(t))

    def test_excess_change_is_returned_or_lost(self):
        j, t = self._billed(lambda t, r: till.due(r) >= 0)
        money = j.c['money']
        due = till.due(t['cash'])
        j.act('ao_pay', task=t['id'], change=till.greedy(due + 20), confirm=True)
        t = j.get(t['id'])
        self.assertIn(t['cash']['outcome'], ('returned', 'kept'))
        gain = j.c['money'] - money
        if t['cash']['outcome'] == 'kept':
            self.assertEqual(t['cash']['loss'], 20)
            self.assertLessEqual(gain, t['bill']['total'] - 20)
        roundtrip(j)

    def test_tip_contract(self):
        found = None
        probe = Journey('clothing')
        for day in range(1, 120):
            for slot in range(12):
                t = A.make_task(day, slot, 1)
                if t['kind'] != 'fit' or t['needs']['haggle'] or (day, slot) in A.STORY:
                    continue
                price = sum(A.PRICES[ln['item']] for ln in t['needs']['lines'])
                rec = till.new(price, t['id'])
                if till.waves_off(probe.c, t, till.due(rec)):
                    found = (Journey('clothing', slot=slot, day=day), t)
                    break
            if found:
                break
        self.assertIsNotNone(found)
        j, t = found
        solve(j, t['id'])
        t = j.get(t['id'])
        if t.get('reaction', {}).get('kind') != 'accept':
            self.skipTest('customer grumbled')
        self.assertEqual(t['tip_given'], till.due(t['cash']))
        tips = [e for e in j.c['ops']['finance']['ledger'] if e['ref'] == t['id'] and e['category'] == 'tip']
        self.assertEqual(len(tips), 1)
        self.assertEqual(tips[0]['amount'], t['tip_given'])
        roundtrip(j)

    def test_haggle(self):
        j = job('fit', lambda t: t['needs']['haggle'])
        t = j.task
        for ln in t['needs']['lines']:
            j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        j.act('ao_bill', task=t['id'])
        self.assertEqual(j.get(t['id'])['haggle'], 'ask')
        self.assertIsNone(j.get(t['id'])['cash'])
        with self.assertRaises(GameError):
            j.act('ao_pay', task=t['id'], change=[], confirm=True)
        j.act('ao_haggle', task=t['id'], answer='big')
        t = j.get(t['id'])
        self.assertEqual(t['bill']['off'], t['bill']['sub'] * A.HAGGLE_BIG // 100)
        self.assertEqual(t['cash']['price'], t['bill']['total'])
        self.assertTrue(j.c['ext']['data']['notes'])
        pay_exact(j, t['id'])
        roundtrip(j)

    def test_a_happening_takes_the_last_piece(self):
        j, t = self._billed()
        ln = t['needs']['lines'][0]
        empty(j, ln['item'], ln['_size'])
        r = pay_exact(j, t['id'])
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.get(t['id'])['stage'], 'pick')


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingOutfitTests(unittest.TestCase):
    def test_right_outfit(self):
        for occ in A.OCCASIONS:
            j = job('outfit', lambda t, o=occ: t['needs']['occasion'] == o)
            solve(j, j.task['id'])
            t = j.get(j.task['id']) if j.c['active_task'] else next(x for x in j.c['tasks'] if x['kind'] == 'outfit')
            self.assertEqual(t['status'], 'completed', occ)
            self.assertEqual(slip_codes(t), [], occ)

    def test_taboo_colour(self):
        j = job('outfit', lambda t: t['needs']['occasion'] == 'wedding')
        t = j.task
        j.act('ao_pick', task=t['id'], item='dress', size=t['needs']['top'] if t['needs']['top'] in A.SIZES['dress'] else 'L', colour='trắng')
        bill_and_pay(j, t['id'])
        t = j.get(t['id'])
        self.assertIn('colour_taboo', slip_codes(t))
        self.assertLess(A.feedback(j.c, t)['criteria'][-2 if t.get('cash') else -1]['score'], 5)

    def test_occasion_miss_and_odd_piece(self):
        rows = A._judge(A.OCCASIONS['interview'], [('tee', 'đen'), ('jeans', 'đen'), ('hat', 'cói')])
        codes = [r[0] for r in rows]
        self.assertIn('occasion_miss', codes)
        self.assertIn('odd_piece', codes)
        rows = A._judge(A.OCCASIONS['beach'], [('dress', 'hoa nhí')])
        self.assertEqual([r[0] for r in rows], ['missing_acc'])
        self.assertEqual(A._judge(A.OCCASIONS['tet'], [('aodai', 'đỏ')]), [])

    def test_not_a_set_and_over_budget(self):
        j = job('outfit')
        t = j.task
        j.act('ao_pick', task=t['id'], item='hat', size='F', colour='cói')
        with self.assertRaises(GameError):
            j.act('ao_bill', task=t['id'])
        j.act('ao_unpick', task=t['id'], index=0)
        for item in ('aodai', 'hat', 'belt'):
            j.act('ao_pick', task=t['id'], item=item, size='F' if item != 'aodai' else 'M', colour=A.COLOURS[item][0])
        j.act('ao_pick', task=t['id'], item='shirt', size='M', colour='trắng')
        j.act('ao_pick', task=t['id'], item='jeans', size='29', colour='đen')
        r = j.act('ao_bill', task=t['id'])
        self.assertTrue(r.get('refused'))
        self.assertIn('over_budget', slip_codes(j.get(t['id'])))


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingAlterTests(unittest.TestCase):
    def setUp(self):
        self.clock = kit.clock
        self.now = [1000.0]
        kit.clock = lambda: self.now[0]

    def tearDown(self):
        kit.clock = self.clock

    def _sew(self, j, tid, cm, seconds):
        j.act('ao_measure', task=tid)
        j.act('ao_alter_self', task=tid, cm=cm)
        j.act('ao_sew_start', task=tid)
        self.now[0] += seconds
        return j.act('ao_sew_stop', task=tid)

    def test_sew_it_yourself_on_the_mark(self):
        j = job('alter', days=range(3, 40))
        tid = j.task['id']
        r = self._sew(j, tid, j.task['needs']['_cm'], A.SEW_SECONDS * 0.8)
        self.assertIn('Dừng ngay vạch', r['message'])
        bill_and_pay(j, tid)
        t = j.get(tid)
        self.assertEqual(slip_codes(t), [])
        self.assertEqual(t['bill']['total'], t['needs']['fee'])

    def test_too_early_then_crooked(self):
        j = job('alter', days=range(3, 40))
        tid = j.task['id']
        j.act('ao_measure', task=tid)
        j.act('ao_alter_self', task=tid, cm=j.task['needs']['_cm'])
        j.act('ao_sew_start', task=tid)
        self.now[0] += 0.5
        self.assertTrue(j.act('ao_sew_stop', task=tid).get('refused'))
        self.now[0] += A.SEW_SECONDS
        j.act('ao_sew_stop', task=tid)
        bill_and_pay(j, tid)
        self.assertEqual(slip_codes(j.get(tid)), ['seam'])

    def test_cut_too_much(self):
        j = job('alter', days=range(3, 40))
        tid = j.task['id']
        self._sew(j, tid, j.task['needs']['_cm'] + 3, A.SEW_SECONDS * 0.8)
        bill_and_pay(j, tid)
        t = j.get(tid)
        sl = next(x for x in cq.slips(t) if x['code'] == 'cut_short')
        self.assertEqual(sl['sev'], 3)
        self.assertNotEqual(t['reaction']['kind'], 'accept')

    def test_send_to_ba_tu(self):
        j = job('alter')
        tid = j.task['id']
        j.act('ao_measure', task=tid)
        j.act('ao_alter_send', task=tid)
        with self.assertRaises(GameError):
            j.act('ao_alter_collect', task=tid)
        money = j.c['money']
        solve(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(slip_codes(t), [])
        share = t['needs']['fee'] * A.TAILOR_SHARE // 100
        rows = [e for e in j.c['ops']['finance']['ledger'] if e['ref'] == tid and e['category'] == 'service']
        self.assertEqual(rows[0]['amount'], -share)
        self.assertLess(j.c['money'] - money, t['needs']['fee'] + 10)


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingRoomTests(unittest.TestCase):
    def test_careful_watch(self):
        j = job('room', lambda t: any(q['_out'] == 'hidden' for q in t['needs']['queue']))
        tid = j.task['id']
        solve(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(slip_codes(t), [])
        self.assertIn('returned', t['room']['res'].values())
        self.assertGreaterEqual(j.c['ext']['data']['stats']['room_saved'], 1)

    def test_letting_a_hidden_piece_walk(self):
        j = job('room', lambda t: any(q['_out'] == 'hidden' for q in t['needs']['queue']))
        tid = j.task['id']
        waste = j.c['life']['day_waste']
        for x in j.task['needs']['queue']:
            j.act('ao_room_tag', task=tid, count=x['items'])
            j.act('ao_room_out', task=tid)
            if x['_out'] != 'ok':
                j.act('ao_room_let', task=tid)
        t = j.get(tid)
        self.assertIn('room_loss', slip_codes(t))
        self.assertGreater(j.c['life']['day_waste'], waste)
        self.assertEqual(t['stage'], 'pick')
        roundtrip(j)

    def test_accusing_an_innocent_customer(self):
        j = job('room', lambda t: any(q['_out'] == 'left' for q in t['needs']['queue']))
        tid = j.task['id']
        for x in j.task['needs']['queue']:
            j.act('ao_room_tag', task=tid, count=x['items'])
            j.act('ao_room_out', task=tid)
            if x['_out'] == 'left':
                r = j.act('ao_room_ask', task=tid)
                self.assertTrue(r.get('refused'))
            elif x['_out'] == 'hidden':
                j.act('ao_room_ask', task=tid)
        t = j.get(tid)
        sl = next(x for x in cq.slips(t) if x['code'] == 'accuse')
        self.assertEqual(sl['sev'], 2)

    def test_no_tag_means_no_count(self):
        j = job('room', lambda t: t['needs']['queue'][0]['_out'] == 'hidden', days=range(3, 60))
        tid = j.task['id']
        j.act('ao_room_out', task=tid)
        self.assertEqual(j.get(tid)['room']['res']['0'], 'lost')


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingReturnTests(unittest.TestCase):
    def test_each_case_by_the_book(self):
        for case in ('size_swap', 'defect', 'worn', 'sale', 'late', 'no_receipt'):
            j = job('return', lambda t, c=case: t['needs']['_case'] == c, days=range(3, 80))
            tid = j.task['id']
            solve(j, tid)
            t = j.get(tid)
            self.assertEqual(t['status'], 'completed', case)
            self.assertNotEqual(t['result']['grade'], 'bad', case)
            self.assertEqual(slip_codes(t), [], case)
            roundtrip(j)

    def test_worn_dress_accepted_is_fraud(self):
        j = job('return', lambda t: t['needs']['_case'] == 'worn', days=range(3, 80))
        tid = j.task['id']
        money = j.c['money']
        j.act('ao_inspect', task=tid, what='wear')
        j.act('ao_return_do', task=tid, choice='refund', confirm=True)
        t = j.get(tid)
        self.assertIn('fraud_ok', slip_codes(t))
        self.assertEqual(j.c['money'], money - t['needs']['price'])
        self.assertEqual(j.c['ext']['data']['stats']['frauds'], 1)

    def test_refusing_a_defect_and_being_blunt(self):
        j = job('return', lambda t: t['needs']['_case'] == 'defect', days=range(3, 80))
        tid = j.task['id']
        j.act('ao_return_do', task=tid, choice='refuse', tone='blunt', confirm=True)
        t = j.get(tid)
        codes = slip_codes(t)
        self.assertIn('refuse_defect', codes)
        self.assertIn('rude', codes)
        self.assertEqual(next(x for x in cq.slips(t) if x['code'] == 'refuse_defect')['sev'], 3)

    def test_exchange_puts_the_old_piece_back(self):
        j = job('return', lambda t: t['needs']['_case'] == 'size_swap', days=range(3, 80))
        n = j.task['needs']
        g = j.c['ext']['data']['grid'][n['item']]
        old, new = g[n['size']], g[n['new_size']]
        solve(j, j.task['id'])
        g = j.c['ext']['data']['grid'][n['item']]
        self.assertEqual(g[n['size']], old + 1)
        self.assertEqual(g[n['new_size']], new - 1)
        self.assertEqual(sum(g.values()), kit.stock(j.c, n['item']))


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingSaleTests(unittest.TestCase):
    def test_right_tags_set_todays_prices(self):
        j = job('sale')
        t = j.task
        solve(j, t['id'])
        t = j.get(t['id'])
        self.assertEqual(slip_codes(t), [])
        sale = j.c['ext']['data']['sale']
        for ln in t['needs']['lines']:
            self.assertEqual(A._price(j.c, ln['item']), A.PRICES[ln['item']] * (100 - ln['pct']) // 100)
            self.assertEqual(sale['tags'][ln['item']], A._price(j.c, ln['item']))
        j.act('end_day', carry_event=True)
        self.assertIsNone(j.c['ext']['data']['sale'])

    def test_too_low_loses_money_too_high_complains(self):
        j = job('sale')
        t = j.task
        opts = t['sale']['options']
        for i, ln in enumerate(t['needs']['lines']):
            right = t['sale']['base'][ln['item']] * (100 - ln['pct']) // 100
            pick = min(opts[i]) if i == 0 else max(opts[i]) if i == 1 else right
            j.act('ao_tag', task=t['id'], line=i, price=pick)
        money = j.c['money']
        j.act('ao_sale_done', task=t['id'], confirm=True)
        t = j.get(t['id'])
        codes = slip_codes(t)
        self.assertIn('sale_low', codes)
        self.assertIn('sale_high', codes)
        self.assertGreater(t['result']['loss'], 0)
        rows = [e for e in j.c['ops']['finance']['ledger'] if e['ref'] == t['id'] and e['category'] == 'loss']
        self.assertEqual(-rows[0]['amount'], t['result']['loss'])

    def test_price_not_offered_is_refused(self):
        j = job('sale')
        with self.assertRaises(GameError):
            j.act('ao_tag', task=j.task['id'], line=0, price=1)


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingOnlineTests(unittest.TestCase):
    def test_right_parcel(self):
        j = job('online')
        tid = j.task['id']
        money = j.c['money']
        solve(j, tid)
        t = j.get(tid)
        self.assertEqual(slip_codes(t), [])
        self.assertEqual(t['result']['net'], t['parcel']['label']['total'] - A.SHIP_FEE)
        self.assertEqual(j.c['money'] - money, t['result']['net'])

    def test_wrong_size_and_unsealed(self):
        j = job('online', lambda t: t['needs']['lines'][0]['item'] not in ('hat', 'belt', 'socks'))
        t = j.task
        x = dict(t['needs']['lines'][0])
        sizes = A.SIZES[x['item']]
        x['size'] = sizes[(sizes.index(x['size']) + 1) % len(sizes)]
        j.act('ao_pack', task=t['id'], **x)
        for y in t['needs']['lines'][1:]:
            j.act('ao_pack', task=t['id'], **y)
        j.act('ao_label', task=t['id'])
        j.act('ao_ship', task=t['id'], confirm=True)
        t = j.get(t['id'])
        codes = slip_codes(t)
        self.assertIn('wrong_parcel', codes)
        self.assertIn('unsealed', codes)
        self.assertEqual(t['result']['loss'], A.SHIP_FEE * 2)

    def test_label_before_seal(self):
        j = job('online')
        with self.assertRaises(GameError):
            j.act('ao_seal', task=j.task['id'])


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingDisplayTests(unittest.TestCase):
    def test_good_window_brings_walk_ins(self):
        j = job('display')
        solve(j, j.task['id'])
        disp = j.c['ext']['data']['display']
        self.assertGreaterEqual(disp['score'], 4)
        money = j.c['money']
        r = j.act('end_day', carry_event=True)
        self.assertGreater(j.c['ext']['data']['stats']['walkins'], 0)
        self.assertGreater(j.c['money'], money - 1000)
        self.assertTrue(any('ma-nơ-canh' in x for x in r['summary']['career']['lines']))

    def test_wrinkled_and_off_theme(self):
        j = job('display', lambda t: t['needs']['theme'] == 'interview')
        tid = j.task['id']
        j.act('ao_dress', task=tid, item='pajama', colour='hồng')
        j.act('ao_display_done', task=tid, confirm=True)
        t = j.get(tid)
        codes = slip_codes(t)
        self.assertIn('occasion_miss', codes)
        self.assertIn('wrinkled', codes)
        self.assertLessEqual(j.c['ext']['data']['display']['score'], 2)


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingStockAndSaveTests(unittest.TestCase):
    def test_restock_fills_the_grid(self):
        from tests.test_inventory_flow import wait_until_ready
        j = Journey('clothing')
        kit.take(j.c, 'tee', kit.stock(j.c, 'tee'))
        A._sync(j.c)
        self.assertEqual(sum(j.c['ext']['data']['grid']['tee'].values()), 0)
        j.act('inv_order', item='tee', qty=4, supplier='market', confirm=True)
        o = j.c['ext']['inv']['orders'][-1]
        wait_until_ready(j, o['id'])
        j.act('inv_receive', order=o['id'], count=o['actual'])
        g = j.c['ext']['data']['grid']['tee']
        self.assertEqual(sum(g.values()), kit.stock(j.c, 'tee'))
        self.assertGreaterEqual(g['M'], g['XL'])
        roundtrip(j)

    def test_tampered_fixed_needs_is_rejected(self):
        j = job('fit')
        j.task['needs']['lines'][0]['_size'] = 'XL' if j.task['needs']['lines'][0]['_size'] != 'XL' else 'S'
        with self.assertRaises(GameError):
            validate_state(j.state)

    def test_tampered_grid_and_bill_rejected(self):
        j = job('fit')
        t = j.task
        ln = t['needs']['lines'][0]
        j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        j.act('ao_bill', task=t['id'])
        bad = copy.deepcopy(j.state)
        bad['careers']['clothing']['tasks'][-1]['bill']['total'] -= 10
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(j.state)
        bad['careers']['clothing']['ext']['data']['grid']['tee']['XXL'] = 3
        validate_state(bad)          # unknown sizes are dropped by the sync
        self.assertNotIn('XXL', bad['careers']['clothing']['ext']['data']['grid']['tee'])

    def test_old_save_without_this_career(self):
        s = new_state()
        s['careers'].pop('clothing')
        s = migrate_state(s)
        self.assertIn('clothing', s['careers'])
        validate_state(s)
        s, _ = apply_action(s, 'clothing', 'select_career', {})
        s, _ = apply_action(s, 'clothing', 'start_day', {})
        validate_state(s)

    def test_old_data_without_new_fields(self):
        j = Journey('clothing')
        d = j.c['ext']['data']
        for k in ('swaps', 'book', 'sale', 'display', 'intro', 'notes', 'seq', 'day_sales', 'stats'):
            d.pop(k)
        validate_state(j.state)
        self.assertIn('stats', d)
        self.assertFalse(d['intro'])

    def test_public_data_does_not_change_the_save(self):
        from game.engine import public_state
        j = job('fit')
        before = json.dumps(j.state, sort_keys=True)
        pub = public_state(j.state)
        self.assertEqual(before, json.dumps(j.state, sort_keys=True))
        data = pub['careers']['clothing']['data'] if 'careers' in pub else None
        if data:
            self.assertIn('look_view', data)
            self.assertIn('today', data)

    def test_feedback_criteria(self):
        j = job('fit')
        solve(j, j.task['id']) if j.c['active_task'] else None
        t = next(x for x in j.c['tasks'] if x['kind'] == 'fit')
        crit = A.feedback(j.c, t)['criteria']
        self.assertTrue(all(1 <= r['score'] <= 5 for r in crit))
        self.assertIn('accuracy', [r['key'] for r in crit])

    def test_assist_and_hint(self):
        j = job('room')
        e = dict(role='ao_floor')
        msg = A.assist(j.state, j.c, e, j.task)
        self.assertIn('thẻ số', msg)
        for k in A.KINDS:
            self.assertTrue(A.hint(j.c, dict(kind=k)))
        roundtrip(j)


if __name__ == '__main__':
    unittest.main()
