import copy
import math
import unittest
import tempfile
from pathlib import Path
from game import outings
from game.engine import GameError
from tests.test_wardrobe import story
from tests.pg_support import pg_only

RECIPES={'teddy':['measure','cut','sew','stuff','decorate'],'pot':['shape','glaze','decorate'],'bracelet':['thread','beads','decorate'],'card':['fold','decorate']}
SIZES={'teddy':[24,30],'pot':[20,24],'bracelet':[18,1],'card':[15,20]}

def work(kind='teddy'):
    return dict(v=1,steps=RECIPES[kind],size=SIZES[kind],marks=[[.3,.4],[.6,.7]])

class Handmade(unittest.TestCase):
    def make(self,state=None,kind='teddy',**kw):
        s=copy.deepcopy(state or story())
        result=outings.action(s,'jr_out_craft',dict(kind=kind,color='mint',pattern='flower',work=work(kind),**kw))
        outings.validate(s)
        return s,result

    def test_completed_teddy_persists_custom_marks_and_charges_once(self):
        s,r=self.make()
        self.assertEqual(s['journey']['wallet'],478)
        self.assertEqual(s['journey']['outings']['crafts'][0]['work'],work())
        again,r=self.make(s)
        self.assertEqual(again,s)
        self.assertTrue(r['duplicate'])

    def test_all_recipes_validate_and_old_keepsakes_remain_valid(self):
        for kind in RECIPES:
            s,_=self.make(kind=kind)
            outings.validate(s)
        s=story()
        outings.action(s,'jr_out_craft',dict(kind='pot',color='mint',pattern='flower'))
        outings.validate(s)
        s,_=self.make(s,kind='pot')
        self.assertEqual(len(s['journey']['outings']['crafts']),2)

    def test_invalid_work_cannot_charge_or_save(self):
        bad=[None,{},dict(work(),steps=['decorate']),dict(work(),steps=list(reversed(RECIPES['teddy']))),
             dict(work(),size=[True,36]),dict(work(),size=[99,36]),dict(work(),marks=[]),
             dict(work(),marks=[[math.nan,.2]]),dict(work(),marks=[[10**400,.2]]),dict(work(),marks=[[True,.2]]),
             dict(work(),marks=[[1.1,.2]]),dict(work(),marks=[[.2,.3]]*13),
             dict(work(),extra='bad')]
        for item in bad:
            with self.subTest(item=item):
                s=story();before=copy.deepcopy(s)
                p=dict(kind='teddy',color='mint',pattern='flower')
                if item is not None:p['work']=item
                with self.assertRaises(GameError):outings.action(s,'jr_out_craft',p)
                self.assertEqual(s,before)

    def test_new_design_is_separate_but_exact_retry_is_duplicate(self):
        s,_=self.make()
        p=dict(kind='teddy',color='mint',pattern='flower',work=dict(work(),marks=[[.2,.2]]))
        outings.action(s,'jr_out_craft',p)
        self.assertEqual(len(s['journey']['outings']['crafts']),2)
        before=copy.deepcopy(s)
        self.assertTrue(outings.action(s,'jr_out_craft',p)['duplicate'])
        self.assertEqual(s,before)
        outings.validate(s)

    def test_finished_record_validation_rejects_invalid_work(self):
        s,_=self.make()
        s['journey']['outings']['crafts'][0]['work']['steps']=[]
        with self.assertRaises(GameError):outings.validate(s)

    def test_content_defines_steps_size_and_teddy(self):
        c=outings.content()
        self.assertIn('teddy',{x['id'] for x in c['crafts']})
        self.assertEqual(c['workshop']['teddy']['steps'],RECIPES['teddy'])
        self.assertEqual(c['workshop']['teddy']['size'],[24,30])


@pg_only
class HandmadeStorage(unittest.TestCase):
    def test_real_store_receipt_replay_and_export_keep_finished_work(self):
        from game.storage import Store
        from game import marriage
        with tempfile.TemporaryDirectory() as temp:
            store=Store(Path(temp)/'handmade',story=True)
            try:
                token,_,_=store.session()
                def fund(s):s['journey']['wallet']=500
                marriage._mutate(store,{store.key(token):fund})
                rev=store.read(token)[1]
                payload=dict(kind='teddy',color='mint',pattern='flower',work=work())
                first=store.command(token,'handmade-one-save',rev,None,'jr_out_craft',payload)
                again=store.command(token,'handmade-one-save',rev,None,'jr_out_craft',payload)
                self.assertFalse(first['replayed']);self.assertTrue(again['replayed'])
                saved=store.read(token)[0]
                self.assertEqual(saved['journey']['wallet'],478)
                self.assertEqual(saved['journey']['outings']['crafts'][0]['work'],work())
                self.assertEqual(len(saved['journey']['outings']['crafts']),1)
            finally:store.close_pool()
