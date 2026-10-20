"""🧰 Thợ phục chế for other players (game/restore_service.py, through 🛎️ Phố dịch vụ, owner 21/10).

Two real accounts on one store: the buyer brings a broken vehicle / a worn part of their home / a piece of furniture
(a ticket), orders the matching service (×3 the NPC price, escrow, 95 % paid, 5 % burned), the restorer works three
bench steps and delivers; the buyer's save is restored exactly once with a visible mark. Refusals: no ticket, bench not
finished, an order refunded (its ticket opens again), the kill switch MNL_RESTORE_OFF, a broken mark in a save."""
import copy
import json
import os
import unittest
from unittest.mock import patch

from game import marriage as mr
from game import reno as rn
from game import restore_service as rs
from game import rui
from game import service_market as sm
from game.engine import GameError, validate_state
from tests.test_bank import act
from tests.test_housing import buy
from tests.test_quay_hire import Base


def right(kind, i, style):
    return rs.BENCH[kind][i][2] or style


class RestoreBase(Base):
    """Helpers only (tests/test_restore_compat.py uses them too)."""
    def setUp(self):
        super().setUp()
        sm._swept[0] = 0.0
        rs.install()

    # ------------------------------------------------------------ people
    def restorer(self, name='rs_tho'):
        tok = self.user(name)
        self.cmd(tok, 'select_career', career='restore')
        self.cmd(tok, 'start_day', career='restore')
        for svc in rs.SERVICES:
            sm.post(self.store, tok, None, 'settings', dict(career='restore', service=svc, on=True, mode='fixed', mult=3))
        return tok

    def owner(self, name='rs_khach', car='xe_so', home='tap_the', piece='ban_tra'):
        tok = self.user(name, wallet=200_000)

        def fn(s):
            s2 = s
            if home:
                s2, _ = buy(s2, home)
            if piece:
                s2, _ = act(s2, 'jr_deco_buy', item=piece, confirm=True)
            if car:
                s2, _ = act(s2, 'jr_garage_buy', id=car, confirm=True)
                j = s2['journey']
                if not isinstance(j.get('rui'), dict):
                    j['rui'] = rui.initial(j['life_day'])
                j['rui']['broken']['xe'][car] = dict(c=26, d=j['life_day'])
            s.clear()
            s.update(s2)
        mr._mutate(self.store, {self.sid(tok): fn})
        return tok

    def pid(self, tok):
        from game import social
        return social.pid_of(self.sid(tok))

    def total(self, tok):
        from game import bank as bk
        s = self.state(tok)
        b = bk.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def mine(self, tok):
        return rs.get(self.store, tok, self.state(tok), 'mine', {})

    def ticket(self, tok, service, ref, style='giu'):
        return rs.post(self.store, tok, self.state(tok), 'ticket', dict(service=service, ref=ref, style=style))

    def order(self, buyer, seller, service):
        self.rid += 1
        return sm.post(self.store, buyer, None, 'order', dict(pid=self.pid(seller), career='restore', service=service, rid=f'rs-order-{self.rid:06d}'))['order']

    def work(self, tok, oid, pick):
        return rs.post(self.store, tok, None, 'work', dict(order=oid, pick=pick))

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message

    def finish_bench(self, tho, oid, kind, style, wrong=0):
        for i in range(3):
            if i == 0 and wrong:
                bad = next(a for a, _ in rs.BENCH[kind][0][1] if a != right(kind, 0, style))
                for _ in range(wrong):
                    self.assertFalse(self.work(tho, oid, bad)['ok'])
            self.assertTrue(self.work(tho, oid, right(kind, i, style))['ok'])


class Restore(RestoreBase):
    # ------------------------------------------------------------ the whole flow
    def test_a_broken_vehicle_is_restored_once_with_a_mark_and_money_is_conserved(self):
        tho, khach = self.restorer(), self.owner()
        view = self.mine(khach)
        xe = next(s for s in view['services'] if s['id'] == 'xe')
        self.assertEqual([x['ref'] for x in xe['items']], ['xe_so'])
        self.assertTrue(rui.is_broken(self.state(khach), 'xe', 'xe_so'))
        # no ticket: the order is refused before any money moves
        self.refused('requirement', self.order, khach, tho, 'xe')
        self.ticket(khach, 'xe', 'xe_so', 'moi')
        self.assertEqual(self.ticket(khach, 'xe', 'xe_so')['ticket'], self.mine(khach)['tickets'][0]['id'], 'a second tap: the same ticket')
        tb, ta = self.total(khach), self.total(tho)
        o = self.order(khach, tho, 'xe')
        self.assertEqual((o['status'], o['price']), ('held', 40 * 3))
        self.assertEqual(self.total(khach), tb - 120)
        # the bench needs the order taken
        self.refused('not_working', self.work, tho, o['id'], 'check')
        sm.post(self.store, tho, None, 'take', dict(order=o['id']))
        b = rs.get(self.store, tho, None, 'bench', {})
        row = b['orders'][0]
        self.assertEqual((row['ticket']['label'], row['ticket']['style'], row['at']), ('🏍️ Xe số Cub', 'moi', 0))
        self.assertEqual(sorted(x['id'] for x in row['step']['options']), sorted(a for a, _ in rs.BENCH['xe'][0][1]))
        # delivering before the bench is finished is refused, the order stays open
        self.refused('restore_bench', sm.post, self.store, tho, None, 'done', dict(order=o['id']))
        self.finish_bench(tho, o['id'], 'xe', 'moi', wrong=1)
        self.refused('bench_done', self.work, tho, o['id'], 'check')
        done = sm.post(self.store, tho, None, 'done', dict(order=o['id']))['order']
        self.assertEqual(done['status'], 'done')
        s = self.state(khach)
        self.assertFalse(rui.is_broken(s, 'xe', 'xe_so'), 'the vehicle rides again')
        mark = s['journey']['restored']['items']['xe:xe_so']
        self.assertEqual((mark['by'], mark['s'], mark['g'], mark['o']), ('Rs_Tho', 'xe', 2, o['id']))
        fee = sm.fee_of(120)
        self.assertEqual(self.total(tho), ta + 120 - fee)
        self.assertEqual(self.total(khach), tb - 120)
        validate_state(s)
        # exactly once: settling again, delivering again, the hook again change nothing
        before = json.dumps(self.state(khach), sort_keys=True)
        sm.settle_for(self.store, None)
        sm.deliver(self.store, self.sid(tho), o['id'])
        self.assertEqual(json.dumps(self.state(khach), sort_keys=True), before)
        self.assertEqual(self.total(tho), ta + 120 - fee)
        s2 = copy.deepcopy(self.state(khach))
        with self.store.connect() as db:
            result = sm.order_of(db, o['id'])['result']
        self.assertFalse(rs.apply(s2, result, o['id']), 'the mark carries the order: applied once')
        # the public state carries the mark (the client draws "đã phục chế bởi …")
        from game.engine import public_state
        self.assertEqual(public_state(self.state(khach))['journey']['restored']['xe:xe_so']['by'], 'Rs_Tho')
        # the restorer's bench count, the buyer's list
        self.assertEqual(rs.get(self.store, tho, None, 'bench', {})['done'], 1)
        self.assertEqual(self.mine(khach)['marks'][0]['key'], 'xe:xe_so')

    def test_a_worn_home_part_goes_back_to_100_and_furniture_turns_classic(self):
        tho, khach = self.restorer('rs_tho2'), self.owner('rs_khach2', car=None)
        s = self.state(khach)
        r = rn.get(s)
        part = next(p for p, x in r['parts'].items() if x['c'] < 100)
        ref = f'{r["hid"]}:{part}'
        nha = next(x for x in self.mine(khach)['services'] if x['id'] == 'nha')
        self.assertIn(ref, [x['ref'] for x in nha['items']])
        uid = next(it['id'] for it in r['items'] if it['k'] == 'ban_tra')
        self.ticket(khach, 'nha', ref)
        self.ticket(khach, 'co_dien', uid)
        for svc, kind in (('nha', 'nha'), ('co_dien', 'decor')):
            o = self.order(khach, tho, svc)
            sm.post(self.store, tho, None, 'take', dict(order=o['id']))
            self.finish_bench(tho, o['id'], kind, 'giu')
            self.assertEqual(sm.post(self.store, tho, None, 'done', dict(order=o['id']))['order']['status'], 'done')
        s = self.state(khach)
        self.assertEqual(rn.get(s)['parts'][part]['c'], 100)
        self.assertEqual(rn.get(s)['items'], r['items'], 'furniture: nothing but the look changes')
        self.assertEqual(set(s['journey']['restored']['items']), {f'nha:{ref}', f'decor:{uid}'})
        self.assertNotIn(uid, [x['ref'] for x in next(x for x in self.mine(khach)['services'] if x['id'] == 'co_dien')['items']])
        validate_state(s)

    def test_a_refunded_order_opens_its_ticket_again(self):
        tho, khach = self.restorer('rs_tho3'), self.owner('rs_khach3', home=None, piece=None)
        self.ticket(khach, 'xe', 'xe_so')
        o = self.order(khach, tho, 'xe')
        sm.post(self.store, tho, None, 'take', dict(order=o['id']))
        self.work(tho, o['id'], right('xe', 0, 'giu'))
        self.assertEqual(self.mine(khach)['tickets'][0]['status'], 'bound')
        tb = self.total(khach)
        sm.post(self.store, tho, None, 'decline', dict(order=o['id']))
        self.assertEqual(self.total(khach), tb + 120, 'the whole price back')
        t = self.mine(khach)['tickets'][0]
        self.assertEqual((t['status'], t['order']), ('open', ''))
        self.assertTrue(rui.is_broken(self.state(khach), 'xe', 'xe_so'))
        # withdraw it; a bound one cannot be withdrawn
        rs.post(self.store, khach, None, 'drop', dict(ticket=t['id']))
        self.assertEqual(self.mine(khach)['tickets'], [])
        self.refused('requirement', self.order, khach, tho, 'xe')

    def test_kill_switch_stops_new_work_but_lets_a_settling_delivery_land(self):
        tho, khach = self.restorer('rs_tho4'), self.owner('rs_khach4', home=None, piece=None)
        self.ticket(khach, 'xe', 'xe_so')
        o = self.order(khach, tho, 'xe')
        sm.post(self.store, tho, None, 'take', dict(order=o['id']))
        self.finish_bench(tho, o['id'], 'xe', 'giu')
        with patch.dict(os.environ, {'MNL_RESTORE_OFF': '1'}):
            self.refused('restore_off', self.ticket, khach, 'oto', 'xe_so')
            self.refused('restore_off', sm.post, self.store, tho, None, 'done', dict(order=o['id']))
            self.assertTrue(self.mine(khach)['off'])
            why = next(x for x in sm.mine(self.store, self.sid(tho), self.state(tho))['services'] if x['career'] == 'restore')['why']
            self.assertIn('tạm nghỉ', why)
        self.assertEqual(sm.post(self.store, tho, None, 'done', dict(order=o['id']))['order']['status'], 'done')
        self.assertFalse(rui.is_broken(self.state(khach), 'xe', 'xe_so'))

    def test_only_what_can_break_is_offered_and_tickets_are_bounded(self):
        khach = self.owner('rs_khach5', car='xe_dap', home=None, piece=None)
        view = {x['id']: x for x in self.mine(khach)['services']}
        self.assertEqual([x['ref'] for x in view['xe']['items']], ['xe_dap'])
        self.assertEqual(view['oto']['items'], [])
        self.assertEqual(view['nha']['items'], [], 'no home of your own: nothing to restore')
        self.refused('not_eligible', self.ticket, khach, 'oto', 'xe_dap')
        self.refused('not_eligible', self.ticket, khach, 'xe', 'sieu_xe')
        self.refused('restore_error', self.ticket, khach, 'xe', 'xe_dap', 'bong')


class Marks(unittest.TestCase):
    def test_marks_are_validated_and_bounded(self):
        s = {'journey': {'life_day': 3}}
        for i in range(rs.MARK_MAX + 5):
            rs._mark(s, f'decor:d{i}', 'Thợ', 'co_dien', 3, f'sv_{i:024x}')
        its = s['journey'][rs.KEY]['items']
        self.assertEqual(len(its), rs.MARK_MAX)
        self.assertNotIn('decor:d0', its)
        rs.validate(s)
        for bad in ({'v': 2, 'items': {}}, {'v': 1, 'items': {'x:1': dict(by='a', d=1, s='xe', g=1, o='o')}},
                    {'v': 1, 'items': {'xe:a': dict(by='a', d=1, s='xe', g=4, o='o')}}, {'v': 1, 'items': {'xe:a': dict(by='a')}}):
            s['journey'][rs.KEY] = bad
            with self.assertRaises(GameError):
                rs.validate(s)


class Floors(unittest.TestCase):
    def test_prices_never_undercut_the_games_own_repair(self):
        """Review 22/10: 🚗 500 vs a 1 440 repair, ⛵ 2 500 vs 7 800: a pair could dodge the repair sink. The lowest unit
        price of each service is now the dearest in-game repair of its class."""
        from game import garage as gr
        rs.install()
        for sid, sp in rs.SERVICES.items():
            spec = sm.get_spec(rs.CAREER, sid)
            lo = sm.bounds(spec, sm.base_of(spec, None, ''), 1)[0]
            if sp['kind'] == 'xe':
                worst = max(v['price'] * rui.XE_PCT // 10000 for v in gr.VEHICLES.values() if v['group'] in sp['groups'])
                self.assertGreaterEqual(lo, worst, sid)
            elif sp['kind'] == 'nha':
                worst = max(rn.fix_cost(k, part, 0) for k in rn.HOUSES for part in rn.PARTS)
                self.assertGreaterEqual(lo, worst, sid)
        self.assertEqual((rs.repair_floor('oto'), rs.repair_floor('tau')), (1440, 7800), 'at today\'s price index')

    def test_a_broken_home_entry_dearer_than_the_order_stays(self):
        s = {'journey': {'life_day': 5}}
        with patch.object(rn, 'get', return_value=dict(hid='h1', parts=dict(wall=dict(c=40)))), \
                patch.object(rui, 'get', return_value=dict(broken=dict(nha=dict(h1=dict(p='wall', c=1800, d=3)), xe={}))) as g:
            self.assertTrue(rs.apply(s, dict(svc='nha', ref='h1:wall', by='Thợ', grade=3), 'sv_' + 'a' * 24, price=600))
            self.assertIn('h1', g.return_value['broken']['nha'], 'a 1 800 xu repair bill is not paid by a 600 xu order')
        s = {'journey': {'life_day': 5}}
        with patch.object(rn, 'get', return_value=dict(hid='h1', parts=dict(wall=dict(c=40)))), \
                patch.object(rui, 'get', return_value=dict(broken=dict(nha=dict(h1=dict(p='wall', c=500, d=3)), xe={}))) as g:
            self.assertTrue(rs.apply(s, dict(svc='nha', ref='h1:wall', by='Thợ', grade=3), 'sv_' + 'b' * 24, price=600))
            self.assertNotIn('h1', g.return_value['broken']['nha'])
