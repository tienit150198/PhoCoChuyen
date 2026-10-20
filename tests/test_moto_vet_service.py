"""🏍️ Bảo dưỡng xe máy and 🩺 khám / tiêm thú cưng for other players (game/moto_service.py, game/vet_service.py) through
🛎️ Phố dịch vụ: two real accounts on one store. The buyer orders (×3 the NPC price, escrow), the provider takes it,
works the three graded steps in the career (xm_svc / ty_svc) and taps Giao; the market's deliver hook reads the
provider's committed save and refuses until the job is in the career's finished list. The buyer's save changes once:
a 🎲 "xe sắp hỏng" warning cleared and calmer days for the bike / the pets examined or vaccinated. Kill switches."""
import os
import unittest
from unittest.mock import patch

from game import marriage as mr
from game import moto_service as ms
from game import rui
from game import service_market as sm
from game import vet_service as vs
from game.careers import PLUGINS
from game.employment import hired_record
from game.engine import validate_state
from tests.test_bank import act
from tests.test_quay_hire import Base


@unittest.skipIf('moto' not in PLUGINS or 'vet' not in PLUGINS, 'filtered out by MNL_CAREERS')
class Services(Base):
    def setUp(self):
        super().setUp()
        sm._swept[0] = 0.0
        ms.install()
        vs.install()

    def provider(self, name, career):
        tok = self.user(name)

        def fn(s):
            s['journey']['chapter'] = max(int(s['journey'].get('chapter') or 1), 4)
            s['journey']['done'] = sorted(set(s['journey'].get('done') or []) | {1, 2, 3})
            if career == 'vet':
                s['careers']['vet']['job'] = hired_record('vet')
        mr._mutate(self.store, {self.sid(tok): fn})
        self.cmd(tok, 'select_career', career=career)
        self.cmd(tok, 'start_day', career=career)
        for svc in (('bao_duong',) if career == 'moto' else vs.SERVICES):
            sm.post(self.store, tok, None, 'settings', dict(career=career, service=svc, on=True, mode='fixed', mult=3))
        return tok

    def pid(self, tok):
        from game import social
        return social.pid_of(self.sid(tok))

    def total(self, tok):
        from game import bank as bk
        s = self.state(tok)
        b = bk.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def order(self, buyer, seller, career, service, qty=1):
        self.rid += 1
        return sm.post(self.store, buyer, None, 'order', dict(pid=self.pid(seller), career=career, service=service, qty=qty,
                                                               rid=f'mv-order-{self.rid:06d}'))['order']

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)

    def work(self, tok, career, prefix, job_of, oid, service, wrong=0):
        self.cmd(tok, prefix + 'svc', career=career, order=oid, service=service)
        steps, key = job_of(oid, service)
        for i, st in enumerate(steps):
            if i == 0 and wrong:
                bad = key[st['id']] + 1 if st['type'] == 'number' else None
                if bad is not None:
                    self.cmd(tok, prefix + 'svc', career=career, order=oid, service=service, step=st['id'], value=bad)
            self.cmd(tok, prefix + 'svc', career=career, order=oid, service=service, step=st['id'], value=key[st['id']])

    # ------------------------------------------------------------ 🏍️
    def test_a_bike_is_serviced_once_the_warning_goes_and_money_is_conserved(self):
        tho = self.provider('mv_tho', 'moto')
        khach = self.user('mv_khach', wallet=200_000)
        self.refused('requirement', self.order, khach, tho, 'moto', 'bao_duong')   # no motorbike yet

        def fn(s):
            s2, _ = act(s, 'jr_garage_buy', id='xe_so', confirm=True)
            j = s2['journey']
            if not isinstance(j.get('rui'), dict):
                j['rui'] = rui.initial(j['life_day'])
            j['rui']['warn'] = dict(kind='xe', sub='bike', ref='xe_so', day=j['life_day'] + 2, at=j['life_day'], cost=40)
            s.clear()
            s.update(s2)
        mr._mutate(self.store, {self.sid(khach): fn})
        tb, ta = self.total(khach), self.total(tho)
        o = self.order(khach, tho, 'moto', 'bao_duong')
        self.assertEqual((o['status'], o['price']), ('held', 150))
        sm.post(self.store, tho, None, 'take', dict(order=o['id']))
        self.refused('moto_bench', sm.post, self.store, tho, None, 'done', dict(order=o['id']))
        self.work(tho, 'moto', 'xm_', PLUGINS['moto'].svc_job, o['id'], 'bao_duong', wrong=1)
        done = sm.post(self.store, tho, None, 'done', dict(order=o['id']))['order']
        self.assertEqual(done['status'], 'done')
        self.assertEqual(done['result']['grade'], 2)
        s = self.state(khach)
        day = s['journey']['life_day']
        self.assertIsNone(rui.get(s)['warn'], 'the pending breakdown warning is prevented')
        self.assertEqual(s['journey']['xe_care'], dict(v=1, cars={'xe_so': day + ms.CARE_DAYS}))
        self.assertGreaterEqual(rui.care_until(s, 'xe_so'), day)
        validate_state(s)
        fee = sm.fee_of(150)
        self.assertEqual((self.total(khach), self.total(tho)), (tb - 150, ta + 150 - fee))
        sm.settle_for(self.store, None)
        self.assertEqual(self.total(tho), ta + 150 - fee, 'paid once')

    def test_a_made_up_delivery_and_the_kill_switch_are_refused(self):
        tho = self.provider('mv_tho2', 'moto')
        khach = self.user('mv_khach2', wallet=200_000)
        mr._mutate(self.store, {self.sid(khach): lambda s: s.update(act(s, 'jr_garage_buy', id='xe_so', confirm=True)[0])})
        o = self.order(khach, tho, 'moto', 'bao_duong')
        sm.post(self.store, tho, None, 'take', dict(order=o['id']))
        self.refused('moto_bench', sm.post, self.store, tho, None, 'done', dict(order=o['id'], result=dict(grade=3)))
        with patch.dict(os.environ, {'MNL_MOTO_SVC_OFF': '1'}):
            self.work(tho, 'moto', 'xm_', PLUGINS['moto'].svc_job, o['id'], 'bao_duong')
            self.refused('moto_off', sm.post, self.store, tho, None, 'done', dict(order=o['id']))
        self.assertEqual(sm.post(self.store, tho, None, 'done', dict(order=o['id']))['order']['status'], 'done')

    # ------------------------------------------------------------ 🩺
    def test_pets_are_examined_by_a_player_vet(self):
        bs = self.provider('mv_bs', 'vet')
        khach = self.user('mv_chu', wallet=200_000)
        self.refused('requirement', self.order, khach, bs, 'vet', 'kham')   # no pet

        def fn(s):
            s2, _ = act(s, 'jr_pet_adopt', **{'from': 'shelter'}, i=0, nick='Lu', confirm=True)
            s2['journey']['pets']['list'][0]['h'] = 30
            s.clear()
            s.update(s2)
        mr._mutate(self.store, {self.sid(khach): fn})
        o = self.order(khach, bs, 'vet', 'kham')
        self.assertEqual(o['price'], 150 * 3)
        sm.post(self.store, bs, None, 'take', dict(order=o['id']))
        self.refused('vet_bench', sm.post, self.store, bs, None, 'done', dict(order=o['id']))
        self.work(bs, 'vet', 'ty_', PLUGINS['vet'].svc_job, o['id'], 'kham')
        self.assertEqual(sm.post(self.store, bs, None, 'done', dict(order=o['id']))['order']['status'], 'done')
        s = self.state(khach)
        from game import pets_content as PC
        self.assertEqual(s['journey']['pets']['list'][0]['h'], PC.VET['h'])
        validate_state(s)

    def test_only_a_hired_vet_is_listed_and_one_pet_per_order(self):
        s = {'careers': {'vet': {'started': True, 'job': {'status': 'none'}}}}
        self.assertIn('Ứng tuyển', vs._can_provide(s))
        s['careers']['vet']['job'] = hired_record('vet')
        self.assertEqual(vs._can_provide(s), '')
        for key in (('moto', 'bao_duong'), ('vet', 'kham'), ('vet', 'tiem')):
            self.assertEqual(sm.REGISTRY[key]['qty_max'], 1, key)


if __name__ == '__main__':
    unittest.main()
