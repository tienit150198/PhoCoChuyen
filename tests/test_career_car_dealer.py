"""🚗 Đại lý xe Phố Mây (game/careers/car_dealer.py): a motorbike and car showroom. The morning slip (frame number, the
five-step PDI, an honest price board) opens it; then each customer is a slip of server-graded steps: sell a vehicle (it
leaves the showroom, its cost kept; trước bạ and the plate are passed on, never income; trả góp goes through the NPC
bank), take a used vehicle in (sold to the yard the same day at 106 %), after-sales, an accessory. Option ids never say
which one is right; the answers and the loan verdict never reach the client; out of stock is referred; players' cars
are serviced as dx_svc jobs; strict saves; dormant until worked."""
import copy
import json
import unittest

from tests.helpers import Journey
from tests.test_career_moto import clear_desk, data, svc_finish, wrong_value
from game import journey as jr
from game.careers import ORDER, PLUGINS, kit, stepkit as sk
from game.engine import DORMANT, GameError, dormant_out, initial_career, public_state, validate_state

M = PLUGINS.get('car_dealer')
if M is not None:
    from game.careers import car_dealer_content as MC

ORDER_A = 'sv_' + 'd4' * 12
ORDER_B = 'sv_' + 'e5' * 12


def find(kind, day=8, pred=None):
    """The first (day, slot) from `day` on whose slip is of `kind` (and passes `pred`); a day has slots 1..11."""
    for d in range(day, day + 60):
        for slot in range(1, 12):
            k, needs, *_ = M.slip(d, slot)
            if k == kind and (pred is None or pred(needs)):
                return d, slot
    raise AssertionError(f'no {kind} slip from day {day}')


def showroom(kind, day=8, pred=None, opened=True):
    day, slot = find(kind, day, pred)
    j = Journey('car_dealer', day=day, slot=slot)
    if opened:
        data(j)['open_day'] = j.c['day']
    return j


def in_stock(n):
    return M.ITEM[n.get('model') or n.get('item')]['start'] > 0


def work(j, tid=None, wrong_at=None):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    out = None
    for _ in range(40):
        clear_desk(j, 'dx_', MC.DESK)
        t = j.get(tid)
        if t['status'] == 'completed':
            break
        st = t['needs']['steps'][t['at']]
        right = t['_key'][st['id']]
        if wrong_at is not None and t['at'] == wrong_at and not t['errors']:
            out = j.act('dx_step', task=tid, step=st['id'], value=wrong_value(st, right))
            continue
        out = j.act('dx_step', task=tid, step=st['id'], value=right)
    return out


@unittest.skipIf(M is None, 'car_dealer filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_late_unlock_owner_shop(self):
        self.assertEqual(ORDER[ORDER.index('jewelry') + 1], 'car_dealer')
        self.assertIn('car_dealer', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['car_dealer'], 2)
        self.assertEqual((M.SPEC['category'], M.SPEC['prefix']), ('shop', 'dx_'))
        self.assertNotIn('employment', M.SPEC)

    def test_content_has_many_awkward_turns_and_real_garage_models(self):
        from game import garage
        self.assertGreaterEqual(len(MC.DEMANDS), 10)
        self.assertGreaterEqual(len(MC.DESK), 10)
        self.assertEqual(len({x['id'] for x in MC.DESK}), len(MC.DESK))
        ids = {v['id'] for v in garage.VEHICLES} if isinstance(garage.VEHICLES, (list, tuple)) else set(garage.VEHICLES)
        for k, m in MC.MODELS.items():
            self.assertIn(m['vid'], ids, k)
            self.assertLess(M.ITEM[k]['cost'], m['price'], k)


@unittest.skipIf(M is None, 'car_dealer filtered out by MNL_CAREERS')
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
                if kind == 'ban':
                    self.assertLessEqual(MC.MODELS[needs['model']]['day'], day)
                    self.assertEqual(key['tien.tong'], needs['price'] + needs['tax'] + needs['plate'])
                    if needs['loan']:
                        self.assertLessEqual(needs['loan']['principal'], 5000)
        self.assertEqual(kinds, set(M.KINDS))

    def test_the_client_never_sees_the_answers_the_model_or_the_loan_verdict(self):
        j = showroom('ban', day=12, pred=lambda n: n['loan'] and in_stock(n))
        tid = j.task['id']
        v = public_state(j.state)['careers']['car_dealer']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertIsNone(v['needs'])
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['car_dealer']['tasks'][0]
        for k in ('model', 'model_name', 'price', 'loan'):
            self.assertNotIn(k, v['needs'])
        self.assertNotIn(j.task['needs']['model_name'], v['title'], 'the title never names the vehicle')
        st = j.task['needs']['steps'][0]
        j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        v = public_state(j.state)['careers']['car_dealer']['tasks'][0]
        self.assertEqual(v['needs']['model'], j.task['needs']['model'])
        self.assertNotIn('ok', v['needs']['loan'], 'the bank verdict is the step answer')
        self.assertNotIn('_key', v)


@unittest.skipIf(M is None, 'car_dealer filtered out by MNL_CAREERS')
class Morning(unittest.TestCase):
    def test_the_showroom_opens_with_the_morning_slip_first(self):
        j = Journey('car_dealer')
        t = j.task
        self.assertEqual((t['kind'], t['id'][-3:]), ('open', '-00'))
        work(j, t['id'])
        self.assertEqual((j.get(t['id'])['status'], j.get(t['id'])['paid']), ('completed', 0))
        self.assertTrue(public_state(j.state)['careers']['car_dealer']['data']['opened'])
        validate_state(j.state)

    def test_no_customer_before_the_showroom_is_open(self):
        j = showroom('pk', opened=False)
        tid = j.task['id']
        with self.assertRaises(GameError) as cm:
            j.act('ask', task=tid)
            st = j.task['needs']['steps'][0]
            j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        self.assertEqual(cm.exception.code, 'shop_closed')


@unittest.skipIf(M is None, 'car_dealer filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_sale_bills_the_price_and_fee_and_passes_the_taxes_on(self):
        j = showroom('ban', pred=in_stock)
        tid = j.task['id']
        n = j.task['needs']
        stock = kit.stock(j.c, n['model'])
        before = j.c['money']
        out = work(j)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['held']), ('completed', 100, True))
        self.assertEqual(t['paid'], n['price'] + t['fee'], 'trước bạ and the plate are never the dealer\'s')
        self.assertEqual(kit.stock(j.c, n['model']), stock - 1)
        self.assertEqual(data(j)['today']['earned'], t['paid'] - t['cogs'])
        self.assertGreater(t['paid'], M.ITEM[n['model']]['cost'])
        self.assertGreaterEqual(j.c['money'] - before, t['paid'])
        self.assertTrue(out['celebrate'])
        self.assertIn(str(n['tax']), out['message'])
        validate_state(j.state)

    def test_a_trade_in_keeps_nothing_and_earns_the_yard_margin(self):
        j = showroom('thu_cu', pred=lambda n: not n['refused'])
        tid = j.task['id']
        lots = copy.deepcopy(j.c['ext'].get('inv'))
        before = j.c['money']
        work(j)
        t = j.get(tid)
        price = t['_key']['gia.thu']
        self.assertEqual(t['paid'], M.yard(t) - price)
        self.assertEqual(M.yard(t), price * MC.YARD_PCT // 100)
        self.assertGreaterEqual(j.c['money'] - before, t['paid'])
        self.assertEqual(j.c['ext'].get('inv'), lots)
        self.assertEqual(data(j)['stats']['traded'], 1)
        validate_state(j.state)

    def test_a_doubtful_seller_is_refused_without_money(self):
        j = showroom('thu_cu', day=10, pred=lambda n: n['refused'])
        tid = j.task['id']
        before = j.c['money']
        work(j)
        t = j.get(tid)
        self.assertEqual((t['paid'], j.c['money'], data(j)['stats']['refused']), (0, before, 1))
        validate_state(j.state)

    def test_after_sales_pays_its_fee_and_the_certificate_two_more(self):
        got = []
        for cert in (False, True):
            j = showroom('hau_mai')
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
        self.assertEqual((g['hire'], g['careers']), (False, ('car_dealer',)))

    def test_an_accessory_sale_with_a_wrong_step(self):
        j = showroom('pk', pred=in_stock)
        tid = j.task['id']
        item = j.task['needs']['item']
        stock = kit.stock(j.c, item)
        work(j, wrong_at=0)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality']), ('completed', 100 - MC.WRONG_COST))
        self.assertEqual(t['paid'], max(1, t['fee'] * (100 - MC.WRONG_COST) // 100))
        self.assertEqual(kit.stock(j.c, item), stock - 1)
        validate_state(j.state)

    def test_out_of_stock_is_referred_before_the_vehicle_is_picked(self):
        j = showroom('ban', pred=in_stock)
        tid = j.task['id']
        model = j.task['needs']['model']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('dx_out', task=tid)
        kit.take(j.c, model, kit.stock(j.c, model))
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError) as cm:
            j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        self.assertEqual(cm.exception.code, 'out_of_stock')
        j.act('dx_out', task=tid)
        self.assertEqual(j.get(tid)['status'], 'referred')
        validate_state(j.state)

    def test_a_tampered_save_is_refused(self):
        j = showroom('ban', pred=in_stock)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)
        for field, value in (('quality', 50), ('at', 4), ('paid', 9), ('fee', 999), ('cogs', 10**6), ('held', False)):
            s = copy.deepcopy(j.state)
            s['careers']['car_dealer']['tasks'][0][field] = value
            with self.assertRaises(GameError, msg=field):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['car_dealer']['tasks'][0]['needs']['price'] = 1
        with self.assertRaises(GameError):
            validate_state(s)


@unittest.skipIf(M is None, 'car_dealer filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_a_surprise_blocks_work_until_decided(self):
        j = showroom('hau_mai')
        x = MC.DESK[0]
        data(j)['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script=x['id'], day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError):
            j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        j.act('dx_desk', option=next(o['id'] for o in x['options'] if o.get('good')))
        j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)


@unittest.skipIf(M is None, 'car_dealer filtered out by MNL_CAREERS')
class PlayerJobs(unittest.TestCase):
    def test_a_player_car_service_is_three_graded_steps_and_lands_in_svc_ok(self):
        j = showroom('hau_mai')
        with self.assertRaises(GameError):
            j.act('dx_svc', order='sv_nope', service='bao_duong_oto')
        with self.assertRaises(GameError):
            j.act('dx_svc', order=ORDER_A, service='bao_duong')
        out = svc_finish(j, 'dx_', M.svc_job, ORDER_A, 'bao_duong_oto', wrong=1)
        self.assertEqual(out['svc_ready'], ORDER_A)
        d = data(j)
        self.assertEqual((d['svc'], d['svc_ok']), ([], [dict(o=ORDER_A, s='bao_duong_oto', q=2)]))
        validate_state(j.state)
        self.assertEqual(public_state(j.state)['careers']['car_dealer']['data']['svc_ok'], [ORDER_A])
        j.act('dx_svc', order=ORDER_B, service='bao_duong_oto')
        s = copy.deepcopy(j.state)
        s['careers']['car_dealer']['ext']['data']['svc_ok'].append(dict(o=ORDER_B, s='bao_duong_oto', q=3))
        with self.assertRaises(GameError):
            validate_state(s)

    def test_the_job_is_pure_per_order(self):
        self.assertEqual(M.svc_job(ORDER_A, 'bao_duong_oto'), M.svc_job(ORDER_A, 'bao_duong_oto'))
        steps, key = M.svc_job(ORDER_A, 'bao_duong_oto')
        self.assertEqual(len(steps), 3)
        self.assertEqual(set(key), {st['id'] for st in steps})


@unittest.skipIf(M is None, 'car_dealer filtered out by MNL_CAREERS')
class Days(unittest.TestCase):
    def test_a_few_days_play_through(self):
        j = Journey('car_dealer')
        for _ in range(3):
            work(j, j.task['id'])
            for t in [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')][:2]:
                item = M._stock_item(t)
                if item and not kit.stock(j.c, item):
                    j.act('ask', task=t['id'])
                    j.act('dx_out', task=t['id'])
                else:
                    work(j, t['id'])
            j.act('end_day', carry_event=True)
            validate_state(j.state)
            j.act('start_day')
            self.assertEqual(j.task['kind'], 'open')
            validate_state(j.state)
        self.assertGreaterEqual(data(j)['stats']['jobs'], 3)

    def test_an_untouched_showroom_is_left_out_of_the_stored_text(self):
        j = Journey('milk_tea')
        self.assertEqual(j.state['careers']['car_dealer'], initial_career('car_dealer'))
        self.assertNotIn('car_dealer', dormant_out(j.state)['careers'])


if __name__ == '__main__':
    unittest.main()
