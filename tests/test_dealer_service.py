"""🚗 Bảo dưỡng ô tô for other players (game/dealer_service.py) through 🛎️ Phố dịch vụ: two real accounts on one store.
The buyer orders (×3 the NPC price, escrow), the 🚗 Đại lý xe player takes it, works the three graded steps (dx_svc)
and taps Giao; the deliver hook reads the dealer's committed save and refuses until the job is in svc_ok. The buyer's
save changes once: a 🎲 "xe sắp hỏng" warning on the car cleared and calmer days for it; a motorbike's are kept.
Kill switch MNL_DEALER_SVC_OFF."""
import os
import unittest
from unittest.mock import patch

from game import dealer_service as ds
from game import marriage as mr
from game import moto_service as ms
from game import rui
from game import service_market as sm
from game.careers import PLUGINS
from game.engine import validate_state
from tests.test_bank import act
from tests import test_moto_vet_service as mv
from tests.test_quay_hire import Base


@unittest.skipIf('car_dealer' not in PLUGINS or 'moto' not in PLUGINS, 'filtered out by MNL_CAREERS')
class Services(Base):
    pid, total, order, refused = mv.Services.pid, mv.Services.total, mv.Services.order, mv.Services.refused

    def work(self, tok, oid, wrong=0):
        """dx_svc: take the job, then each step with the key (`wrong` wrong answers first on the km step)."""
        self.cmd(tok, 'dx_svc', career='car_dealer', order=oid, service=ds.SERVICE)
        steps, key = PLUGINS['car_dealer'].svc_job(oid, ds.SERVICE)
        for st in steps:
            for _ in range(wrong if st['type'] == 'number' else 0):
                self.cmd(tok, 'dx_svc', career='car_dealer', order=oid, service=ds.SERVICE, step=st['id'], value=key[st['id']] + 100)
            self.cmd(tok, 'dx_svc', career='car_dealer', order=oid, service=ds.SERVICE, step=st['id'], value=key[st['id']])

    def setUp(self):
        super().setUp()
        sm._swept[0] = 0.0
        ms.install()
        ds.install()

    def dealer(self, name):
        tok = self.user(name)

        def fn(s):
            s['journey']['chapter'] = max(int(s['journey'].get('chapter') or 1), 4)
            s['journey']['done'] = sorted(set(s['journey'].get('done') or []) | {1, 2, 3})
        mr._mutate(self.store, {self.sid(tok): fn})
        self.cmd(tok, 'select_career', career='car_dealer')
        self.cmd(tok, 'start_day', career='car_dealer')
        sm.post(self.store, tok, None, 'settings', dict(career='car_dealer', service=ds.SERVICE, on=True, mode='fixed', mult=3))
        return tok

    def owner(self, name, *vids, warn=None):
        tok = self.user(name, wallet=200_000)

        def fn(s):
            for vid in vids:
                s2, _ = act(s, 'jr_garage_buy', id=vid, confirm=True)
                s.clear()
                s.update(s2)
            if warn:
                j = s['journey']
                if not isinstance(j.get('rui'), dict):
                    j['rui'] = rui.initial(j['life_day'])
                j['rui']['warn'] = dict(kind='xe', sub='car', ref=warn, day=j['life_day'] + 2, at=j['life_day'], cost=60)
        if vids:
            mr._mutate(self.store, {self.sid(tok): fn})
        return tok

    def test_a_car_is_serviced_once_the_warning_goes_and_money_is_conserved(self):
        dl = self.dealer('dx_dl')
        nobody = self.owner('dx_none')
        self.refused('requirement', self.order, nobody, dl, 'car_dealer', ds.SERVICE)   # no car
        biker = self.owner('dx_biker', 'xe_so')
        self.refused('requirement', self.order, biker, dl, 'car_dealer', ds.SERVICE)    # a motorbike is not a car
        khach = self.owner('dx_khach', 'xe_so', 'o_to_mini', warn='o_to_mini')
        self.assertEqual(ds.cars(self.state(khach)), ['o_to_mini'])
        tb, ta = self.total(khach), self.total(dl)
        o = self.order(khach, dl, 'car_dealer', ds.SERVICE)
        self.assertEqual((o['status'], o['price']), ('held', 120 * 3))
        sm.post(self.store, dl, None, 'take', dict(order=o['id']))
        self.refused('dealer_bench', sm.post, self.store, dl, None, 'done', dict(order=o['id']))
        self.work(dl, o['id'], wrong=1)
        done = sm.post(self.store, dl, None, 'done', dict(order=o['id']))['order']
        self.assertEqual(done['status'], 'done')
        self.assertEqual(done['result']['grade'], 2)
        s = self.state(khach)
        day = s['journey']['life_day']
        self.assertIsNone(rui.get(s)['warn'], 'the pending breakdown warning is prevented')
        self.assertEqual(s['journey']['xe_care']['cars'], {'o_to_mini': day + ms.CARE_DAYS}, 'the car only, not the bike')
        validate_state(s)
        fee = sm.fee_of(360)
        self.assertEqual((self.total(khach), self.total(dl)), (tb - 360, ta + 360 - fee))
        sm.settle_for(self.store, None)
        self.assertEqual(self.total(dl), ta + 360 - fee, 'paid once')

    def test_a_made_up_delivery_and_the_kill_switch_are_refused(self):
        dl = self.dealer('dx_dl2')
        khach = self.owner('dx_khach2', 'o_to_mini')
        o = self.order(khach, dl, 'car_dealer', ds.SERVICE)
        sm.post(self.store, dl, None, 'take', dict(order=o['id']))
        self.refused('dealer_bench', sm.post, self.store, dl, None, 'done', dict(order=o['id'], result=dict(grade=3)))
        with patch.dict(os.environ, {'MNL_DEALER_SVC_OFF': '1'}):
            self.work(dl, o['id'])
            self.refused('dealer_off', sm.post, self.store, dl, None, 'done', dict(order=o['id']))
        self.assertEqual(sm.post(self.store, dl, None, 'done', dict(order=o['id']))['order']['status'], 'done')

    def test_only_a_started_dealer_is_listed_and_one_car_per_order(self):
        self.assertIn('Đại lý xe', ds._can_provide({'careers': {'car_dealer': {'started': False}}}))
        self.assertEqual(ds._can_provide({'careers': {'car_dealer': {'started': True}}}), '')
        self.assertEqual(sm.REGISTRY[('car_dealer', ds.SERVICE)]['qty_max'], 1)
        with patch.dict(os.environ, {'MNL_DEALER_SVC_OFF': '1'}):
            self.assertEqual(ds._can_provide({'careers': {'car_dealer': {'started': True}}}), ds.OFF_LINE)


if __name__ == '__main__':
    unittest.main()
