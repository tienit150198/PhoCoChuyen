import copy
import unittest
import tempfile
from pathlib import Path
from game import courier
from game.engine import GameError
from tests.test_bank import story


class CourierContracts(unittest.TestCase):
    def setUp(self):
        self.s = story(200)
        self.s['journey']['unlocked'].append('delivery')

    def deliver(self, seq, late=0, kind='parcel'):
        c = self.s['careers']['delivery']
        c['metrics']['deliveries_done'] = seq
        c['tasks'] = [dict(id='parcel', status='completed', needs=dict(kind=kind), run=dict(outcome='delivered', late=late), mistakes=0)]
        courier.on_action(self.s, 'delivery', 'dl_deliver', {'task': 'parcel'}, {})

    def test_contract_only_new_real_deliveries_and_collect_once(self):
        courier.action(self.s, 'jr_ship_accept', dict(kind='local', confirm=True, pay='cash'))
        for i in range(1, 4):
            self.deliver(i)
            self.deliver(i)
        self.assertEqual(courier.public(self.s)['active']['done'], 3)
        before = self.s['journey']['wallet']
        courier.action(self.s, 'jr_ship_collect', {})
        self.assertGreater(self.s['journey']['wallet'], before)
        with self.assertRaises(GameError):
            courier.action(self.s, 'jr_ship_collect', {})
        courier.validate(self.s)

    def test_wrong_category_and_failed_delivery_do_not_progress(self):
        courier.action(self.s, 'jr_ship_accept', dict(kind='food', confirm=True, pay='cash'))
        self.deliver(1, kind='parcel')
        self.assertEqual(courier.public(self.s)['active']['done'], 0)
        self.deliver(2, kind='food')
        self.assertEqual(courier.public(self.s)['active']['done'], 1)

    def test_late_deliveries_reduce_bonus_and_cancel_no_reward(self):
        courier.action(self.s, 'jr_ship_accept', dict(kind='local', confirm=True))
        for i in range(1, 4):
            self.deliver(i, late=20)
        self.assertGreater(courier.public(self.s)['active']['deduction'], 0)
        before = self.s['journey']['wallet']
        courier.action(self.s, 'jr_ship_cancel', dict(confirm=True))
        self.assertEqual(self.s['journey']['wallet'], before)
        self.assertIsNone(courier.public(self.s)['active'])

    def test_insufficient_funds_and_invalid_payload_leave_state(self):
        self.s['journey']['wallet'] = 0
        before = copy.deepcopy(self.s)
        with self.assertRaises(GameError):
            courier.action(self.s, 'jr_ship_accept', dict(kind='local', confirm=True, pay='cash'))
        self.assertEqual(self.s, before)
        with self.assertRaises(GameError):
            courier.action(self.s, 'jr_ship_accept', dict(kind=[], confirm=True))

    def test_save_validation_rejects_forged_progress_and_quotes(self):
        courier.action(self.s,'jr_ship_accept',dict(kind='local',confirm=True))
        for key,value in [('kind',[]),('done',True),('last',999),('seq',0)]:
            bad=copy.deepcopy(self.s);bad['journey']['courier']['active'][key]=value
            with self.subTest(key=key),self.assertRaises(GameError):courier.validate(bad)
        for i in range(1,4):self.deliver(i)
        courier.action(self.s,'jr_ship_collect',{})
        for key,value in [('fee',999),('cost',999),('bonus',999)]:
            bad=copy.deepcopy(self.s);bad['journey']['courier']['history'][0][key]=value
            if key=='fee':bad['journey']['courier']['history'][0]['bonus']=999
            with self.subTest(key=key),self.assertRaises(GameError):courier.validate(bad)
        bad=copy.deepcopy(self.s);bad['journey']['courier']['history']*=2
        with self.assertRaises(GameError):courier.validate(bad)

    def test_real_delivery_engine_and_store_retry_progress_once(self):
        from tests.test_career_delivery import journey,ride
        from game import journey as jr,marriage as mr
        from game.storage import Store
        j,tid=journey('P1')
        j.act('dl_check',task=tid);j.act('dl_pack',task=tid,item='bubble');j.act('dl_load',task=tid)
        ride(j,'villa')
        jr.enable_story(j.state)
        if 'delivery' not in j.state['journey']['unlocked']:j.state['journey']['unlocked'].append('delivery')
        j.state['journey']['wallet']=200;j.state['journey']['stats']['max_wallet']=200
        j.act('jr_ship_accept',kind='local',confirm=True,pay='cash')
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store=Store(Path(tmp)/'courier.db',story=True)
            try:
                token,_,_=store.session()
                mr._mutate(store,{store.key(token):lambda s:s.update(copy.deepcopy(j.state))})
                rev=store.read(token)[1];args=(token,'courier-delivery-0001',rev,'delivery','dl_deliver',dict(task=tid))
                first=store.command(*args);again=store.command(*args)
                self.assertTrue(again['replayed'])
                self.assertEqual(first['state'],again['state'])
                saved=store.read(token)[0]
                self.assertEqual(saved['journey']['courier']['active']['done'],1)
                self.assertEqual(saved['journey']['courier']['delivered'],1)
                with self.assertRaises(GameError):store.command(token,'courier-delivery-0002',store.read(token)[1],'delivery','dl_deliver',dict(task=tid))
                self.assertEqual(store.read(token)[0]['journey']['courier']['delivered'],1)
            finally:store.close_pool()

    def test_levels_three_and_ten_contracts_and_gear_deductions(self):
        for n in range(10):
            courier.action(self.s,'jr_ship_accept',dict(kind='local',confirm=True,pay='cash'))
            for i in range(1,4):self.deliver(n*3+i)
            courier.action(self.s,'jr_ship_collect',{})
            self.assertEqual(courier.public(self.s)['level'],1+(n+1>=3)+(n+1>=10))
            courier.validate(self.s)
        for item in ('bag','cover'):courier.action(self.s,'jr_ship_gear',dict(item=item,confirm=True,pay='cash'))
        before=copy.deepcopy(self.s)
        with self.assertRaises(GameError):courier.action(self.s,'jr_ship_gear',dict(item='bag',confirm=True))
        self.assertEqual(self.s,before)
        courier.action(self.s,'jr_ship_accept',dict(kind='local',confirm=True,pay='cash'))
        for i in range(31,34):self.deliver(i,late=20)
        quote=courier.public(self.s)['active']
        self.assertEqual((quote['deduction'],quote['bonus']),(5,19))
        wallet=self.s['journey']['wallet'];courier.action(self.s,'jr_ship_collect',{})
        self.assertEqual(self.s['journey']['wallet']-wallet,quote['bonus'])
        courier.validate(self.s)


if __name__ == '__main__':
    unittest.main()
