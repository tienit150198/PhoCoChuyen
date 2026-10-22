"""💍 Tiệm vàng Ngọc Mây (game/careers/jewelry.py): a gold, silver and diamond shop. The morning slip (count the safe,
check the scale, post the board) opens the shop; then each customer is a slip of server-graded steps: sell a piece off
the shelf (it leaves the stock, its cost kept), buy old gold back (passed to the company the same day at its middle
price: the margin is the spread and the deduction; no gold is kept), appraise a diamond. The board is pure per day and
always sells above what it buys; option ids never say which one is right; the answers never reach the client; out of
stock is referred; strict saves; dormant until worked."""
import copy
import json
import unittest

from tests.helpers import Journey
from tests.test_career_moto import clear_desk, data, wrong_value
from game import journey as jr
from game.careers import ORDER, PLUGINS, kit, stepkit as sk
from game.engine import DORMANT, GameError, dormant_out, initial_career, public_state, validate_state

M = PLUGINS.get('jewelry')
if M is not None:
    from game.careers import jewelry_content as MC


def find(kind, day=8, pred=None):
    """The first (day, slot) from `day` on whose slip is of `kind` (and passes `pred`); a day has slots 1..11."""
    for d in range(day, day + 60):
        for slot in range(1, 12):
            k, needs, *_ = M.slip(d, slot)
            if k == kind and (pred is None or pred(needs)):
                return d, slot
    raise AssertionError(f'no {kind} slip from day {day}')


def shop(kind, day=8, pred=None, opened=True):
    day, slot = find(kind, day, pred)
    j = Journey('jewelry', day=day, slot=slot)
    if opened:
        data(j)['open_day'] = j.c['day']
    return j


def work(j, tid=None, wrong_at=None):
    """Ask, then answer every step with the server's key (one wrong answer first at step `wrong_at`)."""
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    out = None
    for _ in range(40):
        clear_desk(j, 'vg_', MC.DESK)
        t = j.get(tid)
        if t['status'] == 'completed':
            break
        st = t['needs']['steps'][t['at']]
        right = t['_key'][st['id']]
        if wrong_at is not None and t['at'] == wrong_at and not t['errors']:
            out = j.act('vg_step', task=tid, step=st['id'], value=wrong_value(st, right))
            continue
        out = j.act('vg_step', task=tid, step=st['id'], value=right)
    return out


@unittest.skipIf(M is None, 'jewelry filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_after_the_vet_dormant_late_unlock_owner_shop(self):
        self.assertEqual(tuple(ORDER[ORDER.index('tuning'):ORDER.index('tuning') + 3]), ('tuning', 'jewelry', 'car_dealer'))
        self.assertIn('jewelry', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['jewelry'], 2)
        self.assertEqual((M.SPEC['category'], M.SPEC['prefix']), ('shop', 'vg_'))
        self.assertNotIn('employment', M.SPEC)

    def test_content_has_many_awkward_turns(self):
        self.assertGreaterEqual(len(MC.DEMANDS), 10)
        self.assertGreaterEqual(len(MC.DESK), 10)
        self.assertEqual(len({x['id'] for x in MC.DESK}), len(MC.DESK))
        self.assertGreaterEqual(len(MC.PIECES), 8)


@unittest.skipIf(M is None, 'jewelry filtered out by MNL_CAREERS')
class Board(unittest.TestCase):
    def test_the_board_is_pure_and_always_sells_above_what_it_buys(self):
        for day in range(1, 400):
            b = M.board(day)
            self.assertEqual(b, M.board(day))
            self.assertLess(abs(b['mid'] - MC.REF), MC.REF * 0.04)
            for k, row in b['rows'].items():
                self.assertLess(row['buy'], row['mid'], (day, k))
                self.assertLess(row['mid'], row['sell'], (day, k))

    def test_a_piece_sells_above_its_cost_and_its_buy_back_below_the_sale(self):
        for k, x in MC.PIECES.items():
            item = M.ITEM[k]
            self.assertGreater(item['price'], item['cost'], k)
            if x['tuoi'] == 'bac':
                continue
            for day in (1, 9, 40):
                sell = M._row(day, x['tuoi'])['sell'] * x['phan'] // 10
                back = M._row(day, x['tuoi'])['buy'] * x['phan'] // 10
                self.assertLess(back, sell, (k, day))


@unittest.skipIf(M is None, 'jewelry filtered out by MNL_CAREERS')
class Slips(unittest.TestCase):
    def test_a_slip_is_pure_and_every_answer_fits_its_step(self):
        kinds = set()
        for day in range(1, 60, 3):
            for slot in range(8):
                one = M.slip(day, slot)
                self.assertEqual(json.dumps(one, sort_keys=True), json.dumps(M.slip(day, slot), sort_keys=True))
                kind, needs, key = one[:3]
                kinds.add(kind)
                self.assertEqual(kind == 'open', slot == 0)
                ids = [st['id'] for st in needs['steps']]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(set(ids), set(key))
                for st in needs['steps']:
                    self.assertTrue(sk.same(sk.value(st, key[st['id']]), key[st['id']]))
                    for o in st.get('options') or ():
                        self.assertRegex(o['id'], r'^[a-j]$', 'neutral ids only')
                if kind == 'kc':
                    self.assertGreaterEqual(day, MC.MILESTONES[0])
        self.assertEqual(kinds, set(M.KINDS))

    def test_the_client_never_sees_the_answers_nor_the_piece_before_it_is_picked(self):
        j = shop('ban')
        tid = j.task['id']
        v = public_state(j.state)['careers']['jewelry']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertIsNone(v['needs'])
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['jewelry']['tasks'][0]
        self.assertNotIn('_key', v)
        for k in ('piece', 'piece_name', 'tuoi', 'sell'):
            self.assertNotIn(k, v['needs'])
        self.assertNotIn(j.task['needs']['piece_name'].lower(), v['title'].lower(), 'the title never names the piece')
        st = j.task['needs']['steps'][0]
        j.act('vg_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        v = public_state(j.state)['careers']['jewelry']['tasks'][0]
        self.assertEqual(v['needs']['piece'], j.task['needs']['piece'], 'named once picked')

    def test_a_buy_back_hides_the_purity(self):
        j = shop('mua', pred=lambda n: 'tuoi_key' in n)
        j.act('ask', task=j.task['id'])
        v = public_state(j.state)['careers']['jewelry']['tasks'][0]
        self.assertNotIn('tuoi_key', v['needs'])
        self.assertNotIn('_key', v)


@unittest.skipIf(M is None, 'jewelry filtered out by MNL_CAREERS')
class Morning(unittest.TestCase):
    def test_the_shop_opens_with_the_morning_slip_first(self):
        j = Journey('jewelry')
        t = j.task
        self.assertEqual((t['kind'], t['id'][-3:], t['known']), ('open', '-00', True))
        self.assertFalse(public_state(j.state)['careers']['jewelry']['data']['opened'])
        out = work(j, t['id'])
        self.assertEqual(j.get(t['id'])['status'], 'completed')
        self.assertEqual(j.get(t['id'])['paid'], 0)
        self.assertIn('mở cửa', out['message'])
        self.assertEqual(data(j)['open_day'], j.c['day'])
        pub = public_state(j.state)['careers']['jewelry']['data']
        self.assertTrue(pub['opened'])
        self.assertEqual(pub['board'], M.board(j.c['day']))
        validate_state(j.state)

    def test_no_customer_before_the_shop_is_open(self):
        j = shop('ban', opened=False)
        tid = j.task['id']
        with self.assertRaises(GameError) as cm:
            j.act('ask', task=tid)
            st = j.task['needs']['steps'][0]
            j.act('vg_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        self.assertEqual(cm.exception.code, 'shop_closed')


@unittest.skipIf(M is None, 'jewelry filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_sale_takes_the_piece_off_the_shelf_and_bills_gold_stone_and_labour(self):
        j = shop('ban')
        tid = j.task['id']
        n = j.task['needs']
        stock = kit.stock(j.c, n['piece'])
        self.assertGreater(stock, 0, 'the opening shelf has it')
        before = j.c['money']
        out = work(j)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['held']), ('completed', 100, True))
        self.assertEqual(t['paid'], t['_key']['tien.vang'] + n['stone'] + t['fee'])
        self.assertEqual(kit.stock(j.c, n['piece']), stock - 1)
        self.assertGreaterEqual(t['cogs'], 0)   # the opening shelf is free, like every shop's; bought stock carries its cost
        self.assertEqual(data(j)['today']['earned'], t['paid'] - t['cogs'])
        self.assertGreater(t['paid'], M.ITEM[n['piece']]['cost'], 'a clean sale beats what the piece costs from the company')
        self.assertGreaterEqual(j.c['money'] - before, t['paid'])
        self.assertTrue(out['celebrate'])
        self.assertEqual(data(j)['stats']['sold'], 1)
        validate_state(j.state)

    def test_a_buy_back_keeps_no_gold_and_earns_the_spread(self):
        j = shop('mua', pred=lambda n: 'tuoi_key' in n)
        tid = j.task['id']
        lots = copy.deepcopy(j.c['ext'].get('inv'))
        before = j.c['money']
        work(j)
        t = j.get(tid)
        payout = t['_key']['tien.tra']
        self.assertEqual(t['paid'], M.refinery(t) - payout)
        self.assertGreater(t['paid'], 0)
        self.assertLess(t['paid'], M.refinery(t) * 0.06, 'spread + deduction only')
        self.assertGreaterEqual(j.c['money'] - before, t['paid'])
        self.assertEqual(j.c['ext'].get('inv'), lots, 'the old gold goes to the company the same day')
        self.assertEqual(data(j)['stats']['bought'], 1)
        validate_state(j.state)

    def test_a_fake_or_doubtful_seller_is_refused_without_money(self):
        j = shop('mua', day=10, pred=lambda n: 'tuoi_key' not in n)
        before = j.c['money']
        tid = j.task['id']
        work(j)
        t = j.get(tid)
        self.assertTrue(M.refused(t))
        self.assertEqual(t['paid'], 0)
        self.assertEqual(j.c['money'], before)
        self.assertEqual(data(j)['stats']['refused'], 1)
        validate_state(j.state)

    def test_an_appraisal_pays_its_fee_and_the_certificate_two_more(self):
        got = []
        for cert in (False, True):
            j = shop('kc')
            if cert:
                j.state['journey'].setdefault('certificates', {})[M.CERT_ID] = dict(score=90, best=90, earned_day=1, attempts=1)
            before, tid = j.c['money'], j.task['id']
            work(j)
            self.assertEqual(j.get(tid)['paid'], j.get(tid)['fee'])
            got.append(j.c['money'] - before)
            validate_state(j.state)
        self.assertEqual(got[1] - got[0], 2)
        from game import certificate_content as cc
        g = next(x for x in cc.GROUPS if x['id'] == M.CERT_ID)
        self.assertEqual((g['hire'], g['careers']), (False, ('jewelry',)))

    def test_a_wrong_step_stays_open_and_costs_quality(self):
        j = shop('kc')
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        out = j.act('vg_step', task=tid, step=st['id'], value=wrong_value(st, j.task['_key'][st['id']]))
        self.assertFalse(out['correct'])
        t = j.get(tid)
        self.assertEqual((t['at'], t['wrong'], t['quality']), (0, 1, 100 - MC.WRONG_COST))
        validate_state(j.state)
        work(j, tid)
        t = j.get(tid)
        self.assertEqual(t['paid'], max(5, t['fee'] * (100 - MC.WRONG_COST) // 100))
        validate_state(j.state)

    def test_out_of_stock_is_referred_before_the_piece_is_picked(self):
        j = shop('ban')
        tid = j.task['id']
        piece = j.task['needs']['piece']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('vg_out', task=tid)   # still on the shelf
        kit.take(j.c, piece, kit.stock(j.c, piece))
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError) as cm:
            j.act('vg_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        self.assertEqual(cm.exception.code, 'out_of_stock')
        before = j.c['money']
        j.act('vg_out', task=tid)
        t = j.get(tid)
        self.assertEqual((t['status'], t['paid']), ('referred', 0))
        self.assertEqual(j.c['money'], before)
        validate_state(j.state)

    def test_a_tampered_save_is_refused(self):
        j = shop('ban')
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        j.act('vg_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)
        for field, value in (('quality', 50), ('at', 4), ('paid', 9), ('fee', 999), ('cogs', 10**6), ('held', False)):
            s = copy.deepcopy(j.state)
            s['careers']['jewelry']['tasks'][0][field] = value
            with self.assertRaises(GameError, msg=field):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['jewelry']['tasks'][0]['needs']['stone'] = 999
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['jewelry']['ext']['data']['stats']['good'] = 10**6
        with self.assertRaises(GameError):
            validate_state(s)


@unittest.skipIf(M is None, 'jewelry filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_a_surprise_blocks_work_until_decided(self):
        j = shop('kc')
        d = data(j)
        x = MC.DESK[0]
        d['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script=x['id'], day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError):
            j.act('vg_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        j.act('vg_desk', option=next(o['id'] for o in x['options'] if o.get('good')))
        j.act('vg_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)


@unittest.skipIf(M is None, 'jewelry filtered out by MNL_CAREERS')
class Days(unittest.TestCase):
    def test_a_few_days_play_through_and_the_old_morning_slip_is_put_away(self):
        j = Journey('jewelry')
        for _ in range(3):
            work(j, j.task['id'])
            self.assertTrue(data(j)['open_day'] == j.c['day'])
            for t in [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')][:2]:
                piece = t['needs'].get('piece') if t['kind'] == 'ban' else None
                if piece and not kit.stock(j.c, piece):
                    j.act('ask', task=t['id'])
                    j.act('vg_out', task=t['id'])
                else:
                    work(j, t['id'])
            j.act('end_day', carry_event=True)
            validate_state(j.state)
            j.act('start_day')
            self.assertEqual(j.task['kind'], 'open')
            validate_state(j.state)
        self.assertGreaterEqual(data(j)['stats']['jobs'], 3)

    def test_an_untouched_shop_is_left_out_of_the_stored_text(self):
        j = Journey('milk_tea')
        self.assertEqual(j.state['careers']['jewelry'], initial_career('jewelry'))
        self.assertNotIn('jewelry', dormant_out(j.state)['careers'])


if __name__ == '__main__':
    unittest.main()
