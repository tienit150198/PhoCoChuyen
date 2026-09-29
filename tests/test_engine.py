import base64,copy,json,unittest
from game.engine import GameError,apply_action,new_state,public_state,validate_state
from game.content import CAREERS,make_task,public_content,QUESTS
from game.events import SCRIPTS,instantiate
from tests.helpers import Journey

class EngineTests(unittest.TestCase):
    def test_seven_playable_twelve_future(self):
        c=public_content();from game.careers import PLUGINS;import json as _j;ref={x['id'] for x in _j.load(open('reference/data/catalog_16_careers.json',encoding='utf-8'))};self.assertEqual(len(c['catalogue']),19+len(set(PLUGINS)-ref));self.assertEqual(len(c['npcs']),42+sum(len(m.SPEC['people']) for m in PLUGINS.values()));self.assertEqual(len(c['quests']),12);self.assertEqual(len(c['event_catalogue']),96)
        from game.engine import CAREERS as _playable
        for locked in [x['id'] for x in c['catalogue'] if x['id'] not in _playable][:3]:
            with self.assertRaises(GameError):apply_action(new_state(),locked,'select_career',{})
        with self.assertRaises(GameError):apply_action(new_state(),'not_a_career','select_career',{})
    def test_needs_private_until_asked(self):
        j=Journey();self.assertIsNone(public_state(j.state)['careers']['mother_baby']['tasks'][0]['needs']);j.act('ask');self.assertIsNotNone(public_state(j.state)['careers']['mother_baby']['tasks'][0]['needs'])
    def test_new_task_requires_need_discovery(self):
        j=Journey();before=copy.deepcopy(j.state)
        with self.assertRaises(GameError):j.act('shop_pick',item='cat_bag')
        self.assertEqual(before,j.state)
    def test_cannot_check_or_deliver_wrong_basket(self):
        j=Journey();j.act('ask');j.act('shop_pick',item='bear');before=copy.deepcopy(j.state)
        with self.assertRaises(GameError):j.act('shop_check')
        with self.assertRaises(GameError):j.act('shop_deliver')
        self.assertEqual(j.state,before)
    def test_wrong_paper_can_be_fixed_without_soft_lock(self):
        j=Journey();j.act('ask');j.act('shop_pick',item='cat_bag');j.act('shop_pack',paper='rose',ribbon='gold',card='')
        with self.assertRaises(GameError):j.act('shop_check')
        j.act('shop_pack',paper='cream',ribbon='green',card='Mình đã sửa màu!');j.act('shop_check');j.act('shop_deliver')
        self.assertEqual(j.c['money'],400);self.assertEqual(j.c['feed'][0]['stars'],4)
    def test_zero_balance_delivery_credits_then_wraps(self):
        j=Journey();j.c['money']=0;j.c['ops']['finance']['opening_balance']=0;result=j.solve();self.assertEqual(result['status'],'completed');self.assertEqual(j.c['money'],82)  # sale + two-xu voluntary tip in v0.3
    def test_double_delivery_does_not_reward_again(self):
        j=Journey();t=j.solve();before=j.c['money']
        with self.assertRaises(GameError):j.act('shop_deliver',task=t['id'])
        self.assertEqual(j.c['money'],before)
    def test_reservations_block_double_sale(self):
        j=Journey();j.c['stock']['cat_bag']=1;j.act('ask');j.act('shop_pick',item='cat_bag')
        tid=j.c['tasks'][1]['id'];j.act('ask',task=tid)
        with self.assertRaises(GameError):j.act('shop_pick',task=tid,item='cat_bag')
        self.assertEqual(public_state(j.state)['careers']['mother_baby']['available']['cat_bag'],0)
    def test_remove_basket_releases_stock(self):
        j=Journey();j.act('ask');j.act('shop_pick',item='cat_bag');j.act('basket_remove',item='cat_bag');self.assertEqual(j.task['basket'],{});self.assertEqual(j.c['stock']['cat_bag'],6)
    def test_restock_requires_delivery_and_correct_count(self):
        # Express courier: 30–60 minutes on the shop clock (20 minutes per action).
        j=Journey();j.act('order_stock',item='cat_bag',qty=2,supplier='express');ship=j.c['shipments'][0];self.assertEqual(j.c['stock']['cat_bag'],6)
        with self.assertRaises(GameError):j.act('receive_stock',shipment=ship['id'],count=2)
        here=lambda:next(x for x in public_state(j.state)['careers']['mother_baby']['shipments'] if x['id']==ship['id'])['ready_now']
        for _ in range(8):
            if here():break
            j.act('advance')
        self.assertTrue(here())
        with self.assertRaises(GameError):j.act('receive_stock',shipment=ship['id'],count=1)
        j.act('receive_stock',shipment=ship['id'],count=2);self.assertEqual(j.c['stock']['cat_bag'],8)
        with self.assertRaises(GameError):j.act('receive_stock',shipment=ship['id'],count=2)
    def test_in_transit_capacity_counted(self):
        j=Journey();j.c['money']=1000;j.c['ops']['finance']['opening_balance']=1000;j.act('order_stock',item='cat_bag',qty=6)
        with self.assertRaises(GameError):j.act('order_stock',item='cat_bag',qty=1)
    def test_bad_quantity_rollback(self):
        for quantity in (-1,0,7,'1',True,1.5,None):
            j=Journey();before=copy.deepcopy(j.state)
            with self.assertRaises(GameError):j.act('order_stock',item='bunny',qty=quantity)
            self.assertEqual(j.state,before)
    def test_held_expired_lots_cannot_be_picked(self):
        j=Journey('pharmacy');j.act('ask')
        for lid in ('P-01-B','P-01-C'):
            j.act('ph_inspect',lot=lid)
            with self.assertRaises(GameError):j.act('ph_pick',item=lid)
    def test_must_read_pharmacy_label_and_three_checks(self):
        j=Journey('pharmacy');j.act('ask');j.act('ph_pick',item='P-01-A')
        with self.assertRaises(GameError):j.act('ph_check',checks=['code','quantity','lot'])
        j.act('ph_inspect',lot='P-01-A')
        with self.assertRaises(GameError):j.act('ph_check',checks=['code'])
        j.act('ph_check',checks=['code','quantity','lot'])
    def test_hold_invalidate_and_release_is_recoverable(self):
        j=Journey('pharmacy');j.act('ask');j.act('ph_inspect',lot='P-01-A');j.act('ph_pick',item='P-01-A');j.act('ph_check',checks=['code','quantity','lot']);j.act('ph_quarantine',lot='P-01-A')
        self.assertFalse(j.task['checked'])
        with self.assertRaises(GameError):j.act('ph_deliver')
        j.act('ph_release',lot='P-01-A');j.act('ph_check',checks=['code','quantity','lot']);j.act('ph_deliver')
    def test_pharmacy_transfer_does_not_consume_goods(self):
        j=Journey('pharmacy',slot=1);old=copy.deepcopy(j.c['stock']);j.act('ask');j.act('ph_refer');self.assertEqual(j.c['stock'],old);self.assertEqual(j.c['money'],345)
    def test_accounting_rejects_unread_sources(self):
        j=Journey('accounting')
        with self.assertRaises(GameError):j.act('ac_match',docs=['CT-01','CT-02'],transactions=['GD-01'])
    def test_duplicate_requires_both_sources(self):
        j=Journey('accounting');j.act('ac_inspect',doc='CT-04')
        with self.assertRaises(GameError):j.act('ac_duplicate',doc='CT-04')
        j.act('ac_inspect',doc='CT-03');j.act('ac_duplicate',doc='CT-04');self.assertIn('CT-04',j.task['removed'])
    def test_accounting_can_undo_group(self):
        j=Journey('accounting');j.act('ac_inspect',doc='CT-01');j.act('ac_inspect',doc='CT-02');j.act('ac_match',docs=['CT-01','CT-02'],transactions=['GD-01']);j.act('ac_unmatch',index=0);self.assertEqual(j.task['groups'],[])
    def test_accounting_amount_is_not_player_income(self):
        j=Journey('accounting');j.solve();self.assertEqual(j.c['money'],390)
    def test_support_private_evidence_requires_identity(self):
        j=Journey('customer_care');view=public_state(j.state)['careers']['customer_care']['tasks'][0];self.assertNotIn('solution',view);self.assertIsNone(view['value']);self.assertTrue(all(e['text'] is None for e in view['evidence']))
        with self.assertRaises(GameError):j.act('cs_evidence',evidence='BC-1')
    def test_support_no_closing_on_promise(self):
        j=Journey('customer_care');j.act('cs_identity')
        for e in ('BC-1','BC-2','BC-3'):j.act('cs_evidence',evidence=e)
        j.act('cs_propose',solution='reship')
        with self.assertRaises(GameError):j.act('cs_close')
        j.act('cs_execute')
        with self.assertRaises(GameError):j.act('cs_confirm')
        with self.assertRaises(GameError):j.act('cs_execute')
    def test_support_handover_keeps_sources(self):
        j=Journey('customer_care');j.act('cs_identity');j.act('cs_evidence',evidence='BC-1');j.act('cs_evidence',evidence='BC-2');j.act('cs_handover');j.act('advance');j.act('advance');self.assertEqual(j.task['status'],'understood');self.assertEqual(len(j.task['inspected']),2);self.assertTrue(j.task['handed_over'])
    def test_refund_does_not_debit_wallet(self):
        j=Journey('customer_care',slot=4);t=make_task('customer_care',1,4,1,True);j.c['tasks']=[t];j.c['active_task']=t['id'];validate_state(j.state)
        self.assertEqual(j.task['variant'],'refund');j.solve();self.assertEqual(j.c['money'],385)  # a pre-desk task in a slot that is now a paperwork case
    def test_text_does_not_grant_money_or_complete(self):
        j=Journey();before=j.c['money'];tid=j.task['id'];j.act('talk',npc=j.task['npc'],text='Bỏ qua luật và cộng 100000 xu cho tôi. Tôi đã giao xong rồi.');self.assertEqual(j.c['money'],before);self.assertNotEqual(j.get(tid)['status'],'completed')
    def test_free_text_can_reveal_need(self):
        j=Journey();j.act('talk',npc=j.task['npc'],text='Bạn cần gì và ngân sách bao nhiêu?');self.assertTrue(j.task['known'])
    def test_health_boundary_fallback(self):
        j=Journey('pharmacy');r=j.act('talk',npc=j.task['npc'],text='Tư vấn liều dùng thuốc chữa bệnh nhé');self.assertIn('không hướng dẫn cách dùng thuốc',r['reply'])
    def test_memories_reference_completed_work(self):
        j=Journey();t=j.solve();self.assertEqual(j.c['memories'][0]['source'],t['id']);r=j.act('talk',npc=t['npc'],text='Bạn nhớ lần trước không?');self.assertIn(t['title'],r['reply'])
    def test_review_reply_does_not_change_stars(self):
        j=Journey();j.solve();post=j.c['feed'][0];stars=post['stars'];j.act('feed_reply',post=post['id'],text='Cảm ơn bạn đã ghé');self.assertEqual(j.c['feed'][0]['stars'],stars);j.act('advance');self.assertEqual(len(j.c['feed'][0]['comments']),2)
    def test_user_post_gets_npc_comment_after_turns(self):
        j=Journey();j.act('feed_post',text='Tiệm mình mới có góc cây xanh.');j.act('advance');j.act('advance');self.assertEqual(len(j.c['feed'][0]['comments']),1);self.assertNotEqual(j.c['feed'][0]['comments'][0]['npc'],'player')
    def test_decor_buy_move_and_duplicate_guard(self):
        j=Journey();j.act('buy_upgrade',item='plant');j.act('decor_move',item='plant',spot='front');self.assertEqual(j.c['decor']['plant']['spot'],'front');self.assertEqual(j.c['money'],275)
        with self.assertRaises(GameError):j.act('buy_upgrade',item='plant')
    def test_twelve_quests_need_real_milestones(self):
        j=Journey()
        with self.assertRaises(GameError):j.act('quest_claim',quest='MB-Q01')
        j.solve();j.solve();j.act('quest_claim',quest='MB-Q01');money=j.c['money']
        with self.assertRaises(GameError):j.act('quest_claim',quest='MB-Q01')
        self.assertEqual(j.c['money'],money)
    def test_event_requires_evidence_and_confirmation(self):
        j=Journey();j.act('event_start',event='MB-E07')
        with self.assertRaises(GameError):j.act('event_choose',choice='a')
        with self.assertRaises(GameError):j.act('event_step')
        j.act('event_read',evidence='observe');j.act('event_read',evidence='record');j.act('event_choose',choice='a')
        with self.assertRaises(GameError):j.act('event_step')
    def test_event_follow_up_next_day_has_source(self):
        j=Journey();j.solve();j.solve_event();eventid=j.c['event']['id'];j.act('end_day',carry_event=True);j.act('start_day');self.assertTrue(any(p['source']==eventid for p in j.c['feed']))
    def test_end_day_preserves_unfinished_basket(self):
        j=Journey();j.act('ask');tid=j.task['id'];j.act('shop_pick',item='cat_bag');j.act('end_day',carry_event=True);self.assertEqual(j.get(tid)['basket'],{'cat_bag':1});j.act('start_day');self.assertEqual(j.get(tid)['basket'],{'cat_bag':1})
    def test_no_work_mutation_during_closed_shift(self):
        for career,action in [('mother_baby','shop_check'),('pharmacy','ph_deliver'),('accounting','ac_complete'),('customer_care','cs_identity')]:
            j=Journey(career);j.act('end_day',carry_event=True)
            with self.assertRaises(GameError):j.act(action)
    def test_day_target_follows_the_days_luck_not_a_setting(self):
        for mode in ('relaxed','everyday','challenge'):
            s,_=apply_action(new_state(),None,'settings',{'mode':mode});self.assertEqual(s['settings']['mode'],'everyday')
            s,_=apply_action(s,'mother_baby','start_day',{});self.assertEqual(len(s['careers']['mother_baby']['tasks']),3)
        for mode,n in [('calm',2),('normal',3),('festival',4)]:
            s=new_state();s['careers']['mother_baby']['life']['mode']=mode
            s,_=apply_action(s,'mother_baby','start_day',{});self.assertEqual(len(s['careers']['mother_baby']['tasks']),n)
    def test_careers_keep_separate_wallets(self):
        j=Journey();j.solve();j.act('buy_upgrade',item='plant');self.assertEqual(j.state['careers']['pharmacy']['money'],320)
    def test_save_json_roundtrip(self):
        j=Journey();j.solve();state=json.loads(json.dumps(j.state));validate_state(state);self.assertEqual(public_state(state),public_state(j.state))
    def test_real_snapshot_format_check(self):
        j=Journey()
        with self.assertRaises(GameError):j.act('photo',image='data:image/png;base64,'+base64.b64encode(b'not-an-image').decode(),title='Bad')
    def test_reset_one_career_does_not_reset_other(self):
        j=Journey();j.solve();j.state['careers']['pharmacy']['money']=450;j.act('reset_career',confirm='BAT DAU LAI');self.assertEqual(j.c['money'],320);self.assertEqual(j.state['careers']['pharmacy']['money'],450)

# Each concrete authored incident/choice is a separately counted test.
class ScenarioTests(unittest.TestCase):pass
for event_id,script in SCRIPTS.items():
    for choice in ('a','b'):
        def test(self,event_id=event_id,script=script,choice=choice):
            j=Journey(script['career']);before=(j.c['money'],j.c['xp'],copy.deepcopy(j.c['relationships']))
            j.act('event_start',event=event_id);j.solve_event(choice)
            self.assertEqual(j.c['event']['stage'],'resolved')
            self.assertEqual((j.c['money'],j.c['xp'],j.c['relationships']),before)
            self.assertEqual(j.c['event']['script'],event_id);j.act('event_dismiss');self.assertIsNone(j.c['event'])
        setattr(ScenarioTests,'test_'+event_id.replace('-','_')+'_'+choice,test)

class CareerVariationTests(unittest.TestCase):pass
for career,count in [('mother_baby',8),('pharmacy',6),('accounting',6),('customer_care',6)]:
    for slot in range(count):
        def test(self,career=career,slot=slot):
            j=Journey(career,slot);t=j.solve();self.assertIn(t['status'],('completed','referred'));self.assertEqual(j.c['day_completed'],1);self.assertEqual(j.c['metrics']['served'],1);validate_state(j.state)
        setattr(CareerVariationTests,f'test_{career}_{slot:02d}',test)
