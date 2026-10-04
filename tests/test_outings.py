import copy
import json
import subprocess
import unittest
from game import outings, bank, wardrobe
from game.engine import GameError, new_state
from tests.test_wardrobe import story


class Outings(unittest.TestCase):
    def act(self, state, action, **payload):
        next_state = copy.deepcopy(state)
        result = outings.action(next_state, action, payload)
        outings.validate(next_state)
        wardrobe.validate(next_state)
        return next_state, result

    def test_optional_read_does_not_mutate_old_save(self):
        s=story();before=copy.deepcopy(s)
        outings.public(s);outings.validate(s)
        self.assertEqual(s,before)
        self.assertNotIn('outings',s['journey'])

    def test_salon_buys_then_equips_new_hair_and_repeat_is_free(self):
        s=story();start=s['journey']['wallet']
        s,_=self.act(s,'jr_out_salon',hair='toc_bui_doi')
        self.assertIn('toc_bui_doi',s['wardrobe']['owned'])
        self.assertEqual(s['wardrobe']['look']['hair'],'toc_bui_doi')
        self.assertEqual(start-s['journey']['wallet'],12+wardrobe.price(s,'toc_bui_doi'))
        again,r=self.act(s,'jr_out_salon',hair='toc_bui_doi')
        self.assertEqual(s,again)
        self.assertTrue(r['duplicate'])

    def test_owned_hair_only_charges_service(self):
        s=story();s['wardrobe']['owned'].append('toc_bob')
        s,_=self.act(s,'jr_out_salon',hair='toc_bob')
        self.assertEqual(s['journey']['wallet'],488)

    def test_nails_and_craft_keep_visible_choices_across_roundtrip(self):
        s=story()
        s,_=self.act(s,'jr_out_nails',color='rose',pattern='flower')
        s,_=self.act(s,'jr_out_craft',kind='pot',color='mint',pattern='waves')
        s=json.loads(json.dumps(s));outings.validate(s)
        saved=outings.public(s)
        self.assertEqual(saved['nails']['color'],'rose')
        self.assertEqual(saved['nails']['pattern'],'flower')
        self.assertEqual(saved['crafts'][0]['kind'],'pot')
        self.assertEqual(saved['crafts'][0]['pattern'],'waves')
        again,result=self.act(s,'jr_out_craft',kind='pot',color='mint',pattern='waves')
        self.assertEqual(s,again)
        self.assertTrue(result['duplicate'])

    def test_same_nails_do_not_charge_twice(self):
        s,_=self.act(story(),'jr_out_nails',color='rose',pattern='flower')
        again,result=self.act(s,'jr_out_nails',color='rose',pattern='flower')
        self.assertEqual(s,again)
        self.assertTrue(result['duplicate'])

    def test_craft_shelf_is_bounded_without_losing_old_items(self):
        s=story(wallet=2000)
        for color in outings.COLORS:
            for pattern in outings.PATTERNS:
                s,_=self.act(s,'jr_out_craft',kind='pot',color=color['id'],pattern=pattern['id'])
        before=copy.deepcopy(s)
        with self.assertRaises(GameError):self.act(s,'jr_out_craft',kind='card',color='rose',pattern='plain')
        self.assertEqual(s,before)
        self.assertEqual(len(s['journey']['outings']['crafts']),24)

    def test_personal_outings_need_story_but_no_open_workplace(self):
        with self.assertRaises(GameError):self.act(new_state(),'jr_out_nails',color='rose',pattern='plain')
        s=story()
        self.assertFalse(any(c['open'] for c in s['careers'].values()))
        s,_=self.act(s,'jr_out_nails',color='rose',pattern='plain')
        self.assertFalse(any(c['open'] for c in s['careers'].values()))

    def test_payment_preference_account_does_not_spend_wallet(self):
        s=story()
        bank.action(s,'jr_bk_open',{})
        bank.get(s)['balance']=100
        bank.get(s)['pref']='account'
        before=s['journey']['wallet']
        s,_=self.act(s,'jr_out_nails',color='rose',pattern='plain')
        self.assertEqual(s['journey']['wallet'],before)
        self.assertEqual(bank.get(s)['balance'],82)
        bank.get(s)['balance']=0
        with self.assertRaises(GameError):self.act(s,'jr_out_craft',kind='pot',color='mint',pattern='waves')

    def test_salon_requires_full_quote_in_selected_account(self):
        s=story()
        bank.action(s,'jr_bk_open',{})
        bank.get(s)['balance']=60
        bank.get(s)['pref']='account'
        with self.assertRaises(GameError):self.act(s,'jr_out_salon',hair='toc_bui_doi')
        self.assertEqual(bank.get(s)['balance'],60)
        self.assertNotIn('toc_bui_doi',s['wardrobe']['owned'])
        bank.get(s)['balance']=72
        s,_=self.act(s,'jr_out_salon',hair='toc_bui_doi')
        self.assertEqual(bank.get(s)['balance'],0)
        self.assertEqual(s['journey']['wallet'],500)

    def test_invalid_choices_and_insufficient_total_are_atomic(self):
        s=story(wallet=15)
        for name,p in [('jr_out_salon',{'hair':'toc_bui_doi'}),('jr_out_salon',{'hair':'ao_len'}),
                       ('jr_out_nails',{'color':[], 'pattern':'plain'}),
                       ('jr_out_craft',{'kind':'pot','color':'mint','pattern':'waves','price':0}),
                       ('jr_out_nails',{'color':'rose','pattern':'plain','pay':'bogus'})]:
            with self.subTest(name=name,p=p),self.assertRaises(GameError):self.act(s,name,**p)
        self.assertNotIn('outings',s['journey'])

    def test_strict_saved_data_validation(self):
        s,_=self.act(story(),'jr_out_craft',kind='pot',color='mint',pattern='waves')
        for mutate in [lambda d:d.update(v=2),lambda d:d.update(extra=True),
                       lambda d:d['crafts'][0].update(color='bogus'),
                       lambda d:d['crafts'].append(copy.deepcopy(d['crafts'][0])),
                       lambda d:d['crafts'][0].update(day=True)]:
            bad=copy.deepcopy(s);mutate(bad['journey']['outings'])
            with self.assertRaises(GameError):outings.validate(bad)

    def test_render_preview_and_saved_collectibles(self):
        s,_=self.act(story(),'jr_out_nails',color='rose',pattern='flower')
        s,_=self.act(s,'jr_out_craft',kind='pot',color='mint',pattern='waves')
        s['journey']['outings']=outings.public(s)
        payload={'state':s,'content':{'journey':{'outings':outings.content()}}}
        out=subprocess.run(['node','tests/outings.mjs'],input=json.dumps(payload),encoding='utf-8',capture_output=True)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)


if __name__=='__main__':unittest.main()
