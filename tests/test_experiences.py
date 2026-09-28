"""v0.3 playable paths, corrections, imports, repeat safety and content variation."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from game.engine import new_state,apply_action,validate_state,migrate_state,public_state,GameError
from game.content import CAREERS,make_task,public_content
from game.extra_content import ACTIVITIES,STORIES,PLACE_INDEX,INGREDIENTS,NEW_CAREERS
from game import experiences as life
from game.storage import Store
from tests.helpers import Journey,solve_activity

class ExperiencesTests(unittest.TestCase):
 def test_content_catalogue(self):
  c=public_content()
  from game.careers import PLUGINS;import json as _j;ref={x['id'] for x in _j.load(open('reference/data/catalog_16_careers.json',encoding='utf-8'))}
  self.assertEqual((len(CAREERS),len(c['catalogue']),len(c['npcs'])),(7+len(PLUGINS),19+len(set(PLUGINS)-ref),42+sum(len(m.SPEC['people']) for m in PLUGINS.values())))
  self.assertEqual(len(ACTIVITIES),28+4*sum(bool(m.SPEC.get('activity')) for m in PLUGINS.values()));self.assertEqual(len(STORIES),21+3*sum(bool(m.SPEC.get('stories')) for m in PLUGINS.values()))
  self.assertEqual(len({s['beats'][0]['text'] for s in STORIES}),len(STORIES))
 def test_teacher_answer_hidden_until_source(self):
  j=Journey('teacher');t=public_state(j.state)['careers']['teacher']['tasks'][0]
  self.assertNotIn('answer',t['lesson']);self.assertIsNone(t['students'][0]['submission']);self.assertNotIn('method',t['students'][0])
 def test_teacher_incomplete_cannot_finish(self):
  j=Journey('teacher');old=copy.deepcopy(j.state)
  with self.assertRaises(GameError):j.act('lesson_complete',confirm=True)
  self.assertEqual(j.state,old)
 def test_teacher_wrong_attendance_is_recoverable(self):
  j=Journey('teacher',slot=0,day=3);t=j.task
  j.act('lesson_plan',steps=['demo','practice','reflect'])
  st=t['students'][-1];j.act('lesson_attendance',student=st['id'],present=not st['present'])
  self.assertEqual(j.task['mistakes'],1);self.assertNotIn(st['id'],j.task['attendance'])
  j.act('lesson_attendance',student=st['id'],present=st['present']);self.assertIn(st['id'],j.task['attendance'])
 def test_teacher_wrong_method_then_correct(self):
  j=Journey('teacher');t=j.task;j.act('lesson_plan',steps=['demo','practice','reflect'])
  for st in t['students']:j.act('lesson_attendance',student=st['id'],present=st['present'])
  st=t['students'][0];wrong=next(x for x in ['visual','hands','story'] if x!=st['method'])
  j.act('lesson_teach',student=st['id'],method=wrong);self.assertNotIn(st['id'],j.task['taught'])
  j.act('lesson_teach',student=st['id'],method=st['method']);self.assertEqual(j.task['taught'][st['id']],st['method'])
 def test_teacher_wrong_grade_not_done(self):
  j=Journey('teacher');t=j.task;j.act('lesson_plan',steps=['demo','practice','reflect'])
  for st in t['students']:j.act('lesson_attendance',student=st['id'],present=st['present'])
  for st in t['students']:j.act('lesson_teach',student=st['id'],method=st['method'])
  st=t['students'][0];ok=st['submission']==t['lesson']['answer'];j.act('lesson_grade',student=st['id'],correct=not ok,feedback='specific')
  self.assertNotIn(st['id'],j.task['grades']);self.assertEqual(j.task['stage'],'grade')
 def test_tour_cannot_leave_people(self):
  j=Journey('tour_guide');t=j.task;j.act('tour_plan',route=t['required']+['cafe']);before=copy.deepcopy(j.state)
  with self.assertRaises(GameError):j.act('tour_depart',confirm=True)
  self.assertEqual(j.state,before)
 def test_tour_ticket_debits_once(self):
  j=Journey('tour_guide');t=j.task;j.act('tour_plan',route=t['required']+['cafe'])
  for v in t['visitors']:j.act('tour_count',visitor=v['id'])
  old=j.c['money'];j.act('tour_depart',confirm=True);self.assertEqual(j.c['money'],old-j.task['plan_cost']);after=copy.deepcopy(j.state)
  with self.assertRaises(GameError):j.act('tour_depart',confirm=True)
  self.assertEqual(j.state,after)
 def test_tour_rain_blocks_river(self):
  j=Journey('tour_guide',slot=0,day=2)
  with self.assertRaises(GameError):j.act('tour_plan',route=['museum','river','cafe'])
 def test_tour_duplicate_route_rejected(self):
  j=Journey('tour_guide')
  with self.assertRaises(GameError):j.act('tour_plan',route=['museum','museum','cafe'])
 def test_tour_wrong_photo_recoverable(self):
  j=Journey('tour_guide');t=j.task;j.act('tour_plan',route=t['required']+['cafe'])
  for v in t['visitors']:j.act('tour_count',visitor=v['id'])
  j.act('tour_depart',confirm=True);j.act('tour_photo',object='not-a-place')
  self.assertFalse(j.task['photo_done']);self.assertEqual(j.task['mistakes'],1)
  j.act('tour_photo',object=PLACE_INDEX[j.task['route'][0]]['target']);self.assertTrue(j.task['photo_done'])
 def test_tea_order_hidden_before_asking(self):
  j=Journey('milk_tea');self.assertIsNone(public_state(j.state)['careers']['milk_tea']['tasks'][0]['needs'])
  with self.assertRaises(GameError):j.act('tea_add',item='milk')
  j.act('ask');self.assertIsNotNone(public_state(j.state)['careers']['milk_tea']['tasks'][0]['needs'])
 def test_tea_cannot_give_unchecked(self):
  j=Journey('milk_tea');j.act('ask')
  with self.assertRaises(GameError):j.act('tea_serve',confirm=True)
  with self.assertRaises(GameError):j.act('tea_seal')
 def test_tea_repeated_item_does_not_consume_twice(self):
  j=Journey('milk_tea');j.act('ask');j.act('tea_cup',size='M');j.act('tea_add',item='milk');before=life.stock(j.c)['milk']
  with self.assertRaises(GameError):j.act('tea_add',item='milk')
  self.assertEqual(life.stock(j.c)['milk'],before)
 def test_tea_prepare_confirmation_and_money(self):
  j=Journey('milk_tea');before=copy.deepcopy(j.state)
  with self.assertRaises(GameError):j.act('tea_prepare',item='foam',qty=5)
  self.assertEqual(j.state,before);j.act('tea_prepare',item='foam',qty=5,confirm=True)
  self.assertEqual(j.c['money'],305);self.assertEqual(life.stock(j.c)['foam'],13)
 def test_tea_fifo_uses_earliest_lot(self):
  j=Journey('milk_tea');j.act('tea_prepare',item='milk',qty=3,confirm=True);j.act('ask');j.act('tea_cup',size='M');j.act('tea_add',item='milk')
  lots=[l for l in j.c['life']['pantry'] if l['item']=='milk'];self.assertEqual([l['qty'] for l in lots],[7,3])
 def test_tea_expiry_does_not_charge_again(self):
  j=Journey('milk_tea');j.act('tea_prepare',item='foam',qty=5,confirm=True);balance=j.c['money'];j.act('end_day',carry_event=True)
  self.assertEqual(j.c['money'],balance);self.assertEqual(life.stock(j.c)['foam'],0)
  self.assertEqual(j.c['shift_summary']['experiences']['waste_value'],15)
 def test_tea_discard_consumes_not_refunds(self):
  j=Journey('milk_tea');j.act('ask');j.act('tea_cup',size='M');j.act('tea_add',item='milk');q=life.stock(j.c)['milk'];cash=j.c['money']
  j.act('tea_discard',confirm=True);self.assertEqual(life.stock(j.c)['milk'],q);self.assertEqual(j.c['money'],cash);self.assertEqual(j.task['cup']['items'],[])
 def test_tea_size_validated(self):
  j=Journey('milk_tea');j.act('ask')
  for args in [dict(size='XL',sugar=50,ice='none'),dict(size='M',sugar=True,ice='none'),dict(size='M',sugar=30,ice='frozen')]:
   with self.subTest(args=args),self.assertRaises(GameError):j.act('tea_config',**args)
 def test_tea_quote_survives_next_day_price(self):
  j=Journey('milk_tea');tid=j.task['id'];quoted=j.task['quoted_price'];j.act('end_day',carry_event=True)
  j.act('life_price',item='milk',price=33);j.act('start_day');self.assertEqual(j.get(tid)['quoted_price'],quoted)
 def test_rename_roundtrip_plain_text(self):
  j=Journey();j.act('life_rename',name='<b>Tiệm Mây</b>');self.assertEqual(j.c['life']['shop_name'],'<b>Tiệm Mây</b>');validate_state(j.state)
 def test_day_mode_is_luck_not_a_picker(self):
  # The server rolls each day's pace at close (see tests/test_journey.py); players cannot pick it.
  j=Journey()
  with self.assertRaises(GameError):j.act('life_mode',mode='festival')
  j.act('end_day',carry_event=True)
  with self.assertRaises(GameError):j.act('life_mode',mode='festival')
  j.c['life']['mode']='festival';j.act('start_day');self.assertTrue(j.c['life']['festival']);self.assertEqual(len([t for t in j.c['tasks'] if t['status']=='new']),4)
 def test_goals_claim_once(self):
  j=Journey();solve_activity(j,'mother_baby-sort');j.act('life_goal',goal='play');cash=j.c['money']
  with self.assertRaises(GameError):j.act('life_goal',goal='play')
  self.assertEqual(j.c['money'],cash)
 def test_activity_reward_once_per_day(self):
  j=Journey();solve_activity(j,'mother_baby-sort');cash=j.c['money'];solve_activity(j,'mother_baby-sort');self.assertEqual(j.c['money'],cash)
 def test_practice_no_cash_or_day_goal(self):
  j=Journey();cash=j.c['money'];solve_activity(j,'mother_baby-pairs',True);self.assertEqual(j.c['money'],cash);self.assertEqual(j.c['life']['day_metrics'].get('activities',0),0)
 def test_wrong_sort_can_recover(self):
  j=Journey();j.act('life_activity_start',spec='mother_baby-sort');a=j.c['life']['activity'];card=a['cards'][0];wrong=next(x for x in a['bins'] if x!=card['bin'])
  j.act('life_activity_assign',card=card['id'],target=wrong);self.assertNotIn(card['id'],j.c['life']['activity']['assignments']);j.act('life_activity_assign',card=card['id'],target=card['bin']);self.assertIn(card['id'],j.c['life']['activity']['assignments'])
 def test_memory_public_conceals_cards(self):
  j=Journey();j.act('life_activity_start',spec='mother_baby-pairs');a=public_state(j.state)['careers']['mother_baby']['life']['activity'];self.assertTrue(all(c['value'] is None for c in a['cards']))
 def test_chapter_needs_actual_new_work(self):
  j=Journey('teacher');j.solve();j.solve();j.act('life_chapter',story='teacher-chapter-1',choice='listen')
  with self.assertRaises(GameError):j.act('life_chapter',story='teacher-chapter-1',choice='show')
  j.solve();j.act('life_chapter',story='teacher-chapter-1',choice='show');j.act('life_chapter',story='teacher-chapter-1',choice='share');cash=j.c['money']
  with self.assertRaises(GameError):j.act('life_chapter',story='teacher-chapter-1',choice='share')
  self.assertEqual(cash,j.c['money']);self.assertTrue(j.c['life']['chapters']['teacher-chapter-1']['completed'])
 def test_town_repeat_no_duplicate_sticker(self):
  j=Journey();j.act('life_town',place='garden');x=copy.deepcopy(j.c['life']['stickers']);j.act('life_town',place='garden');self.assertEqual(j.c['life']['stickers'],x)
 def test_owner_edit_review_not_stars(self):
  j=Journey();j.solve();post=next(p for p in j.c['feed'] if p['kind']=='review');j.act('feed_reply',post=post['id'],text='Cảm ơn bạn!')
  post=next(p for p in j.c['feed'] if p['id']==post['id']);i=next(i for i,c in enumerate(post['comments']) if c['npc']=='player');stars=post['stars'];j.act('life_reply_edit',post=post['id'],index=i,text='Cảm ơn bạn đã ghé!')
  now=next(p for p in j.c['feed'] if p['id']==post['id']);self.assertEqual(now['stars'],stars);self.assertTrue(now['comments'][i]['edited'])
 def test_player_cannot_edit_npc(self):
  j=Journey();j.solve();post=next(p for p in j.c['feed'] if p['kind']=='review');j.act('feed_reply',post=post['id'],text='Cảm ơn');j.act('advance');now=next(p for p in j.c['feed'] if p['id']==post['id']);i=next(i for i,c in enumerate(now['comments']) if c['npc']!='player')
  with self.assertRaises(GameError):j.act('life_reply_edit',post=post['id'],index=i,text='5 sao đi')
 def test_patience_reading_and_chat_no_penalty(self):
  j=Journey();j.act('ask');j.act('talk',npc=j.task['npc'],text='Chào bạn');self.assertTrue(all(t.get('patience',100)==100 for t in j.c['tasks']))
  j.act('shop_pick',item=j.task['needs']['product']);other=j.c['tasks'][1];self.assertEqual(other['patience'],99)
 def test_calm_patience_never_falls(self):
  j=Journey();j.c['life']['mode']='calm';j.act('ask');j.act('shop_pick',item=j.task['needs']['product']);self.assertTrue(all(t.get('patience',100)==100 for t in j.c['tasks']))
 def test_schema2_migrate_keeps_balance_no_backtax(self):
  j=Journey();j.solve();old=copy.deepcopy(j.state);old['schema']=2
  for cid in NEW_CAREERS:old['careers'].pop(cid)
  for c in old['careers'].values():c.pop('life')
  before=copy.deepcopy(old['careers']['mother_baby']['ops']);m=migrate_state(old);validate_state(m)
  self.assertEqual(m['schema'],4);self.assertEqual(m['careers']['mother_baby']['money'],402);self.assertEqual(m['careers']['mother_baby']['ops'],before)
 def test_store_schema2_on_read(self):
  with tempfile.TemporaryDirectory() as td:
   store=Store(Path(td)/'test.db');token,csrf,_=store.session();old=new_state();old['schema']=2
   for cid in NEW_CAREERS:old['careers'].pop(cid)
   for c in old['careers'].values():c.pop('life')
   with store.connect() as db:db.execute('UPDATE sessions SET state=? WHERE sid=?',(json.dumps(old),store.key(token)))
   state,rev,_=store.read(token);self.assertEqual(state['schema'],4);self.assertEqual(rev,1)
   _,rev,_=store.read(token);self.assertEqual(rev,1)
 def test_store_repeat_preparation_idempotent(self):
  with tempfile.TemporaryDirectory() as td:
   st=Store(Path(td)/'test.db');tok,_,_=st.session()
   args=(tok,'tea-batch-001',0,'milk_tea','tea_prepare',dict(item='milk',qty=5,confirm=True))
   a=st.command(*args);b=st.command(*args);self.assertTrue(b['replayed']);self.assertEqual(a['state']['careers']['milk_tea']['money'],b['state']['careers']['milk_tea']['money'])
 def test_bad_pantry_restore_rejected(self):
  s=new_state();s['careers']['milk_tea']['life']['pantry'][0]['qty']=-1
  with self.assertRaises(GameError):validate_state(s)
 def test_bad_fixed_lesson_rejected(self):
  j=Journey('teacher');j.task['lesson']['answer']='pretend'
  with self.assertRaises(GameError):validate_state(j.state)
 def test_duplicate_activity_cards_rejected(self):
  j=Journey();j.act('life_activity_start',spec='mother_baby-sort');j.c['life']['activity']['cards'][0]['label']='Thẻ tự sửa'
  with self.assertRaises(GameError):validate_state(j.state)

# Full deterministic content variants. Each instance executes and validates every step.
def career_case(cid,day,slot):
 def run(self):
  j=Journey(cid,slot=slot,day=day)
  if cid=='milk_tea':
   # Generated fixtures at future days need inventory corresponding to that day.
   for lot in j.c['life']['pantry']:lot['received']=day;lot['expires']=day+2
  t=j.solve();self.assertEqual(t['status'],'completed');self.assertEqual(j.c['day_completed'],1);self.assertTrue(any(p['kind']=='review' for p in j.c['feed']));validate_state(j.state)
  before=copy.deepcopy(j.state)
  with self.assertRaises(GameError):j.act({'teacher':'lesson_complete','tour_guide':'tour_complete','milk_tea':'tea_serve'}[cid],task=t['id'],confirm=True)
  self.assertEqual(j.state,before)
 return run
for _cid in NEW_CAREERS:
 for _day in (1,2,3):
  for _slot in (0,1,2,3):setattr(ExperiencesTests,f'test_job_{_cid}_day{_day}_slot{_slot}',career_case(_cid,_day,_slot))
def activity_case(spec):
 def run(self):
  j=Journey(spec['career']);cash=j.c['money'];a=solve_activity(j,spec['id']);self.assertEqual(a['status'],'completed');self.assertEqual(j.c['money'],cash+12);self.assertEqual(a['score'],100);validate_state(j.state)
 return run
for _sp in ACTIVITIES:setattr(ExperiencesTests,'test_puzzle_'+_sp['id'].replace('-','_'),activity_case(_sp))
if __name__=='__main__':unittest.main()

# New review lines must be attached to real completions, never menu visits.
def humour_case(cid):
 def run(self):
  from game.extra_content import REVIEW_ASIDES
  j=Journey(cid);t=j.solve();post=next(v for v in j.c['feed'] if v['kind']=='review')
  self.assertEqual(post['source'],t['id']);self.assertIn(post['source'],j.c['completed_ids'])
  self.assertTrue(any(txt in post['text'] for txt in REVIEW_ASIDES[cid]))
 return run
for _cid in ('mother_baby','pharmacy','accounting','customer_care','teacher','tour_guide','milk_tea'):
 setattr(ExperiencesTests,'test_contextual_review_'+_cid,humour_case(_cid))
