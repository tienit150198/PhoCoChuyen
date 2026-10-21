import copy
import pytest
from game import career_specialism as sp, career_specialism_jobs as jobs, career_specialism_stock as stock
from game import career_scale as scale, career_scale_quota as quota
from game import engine as e, employment
from game.career_specialism_content import pack

NOW=1791907200

def prepared(cid='grocery'):
 s=e.new_state();s['current']=cid;c=s['careers'][cid]
 c.update(started=True,xp=90000,money=800000000)
 c['ops']['finance']['opening_balance']=c['money']
 if employment.required(cid):c['job']=employment.hired_record(cid)
 r=scale.ensure(c,cid,NOW);r.update(clean=3000,qualified_days=280,start_day=r['today']['day']-280)
 return s,c

def act(s,c,cid,name,p=None):return sp.action(s,c,cid,name,p or {},NOW)

def learn(s,c,cid,tier):
 act(s,c,cid,'special_enrol',{'tier':tier})
 for step in range(5):
  question=sp.exercise(cid,tier,step,1)
  act(s,c,cid,'special_practice',{'tier':tier,'step':step,'answer':question['answer']})
 assert c[sp.KEY]['tier']==tier

def job(s,c,cid,tier,bad=False):
 act(s,c,cid,'special_offer',{'tier':tier});o=c[sp.KEY]['job']
 if jobs.kind(cid)=='business':
  for m in stock.materials(cid,tier):
   n=o['quantity']
   while n:
    qty=min(n,stock.limit(c,cid)['order'])
    result=act(s,c,cid,'special_stock_buy',{'code':m['code'],'quantity':qty})
    act(s,c,cid,'special_stock_receive',{'order':result['order'],'count':qty});n-=qty
 act(s,c,cid,'special_start',{'id':o['id']})
 for step in range(5):
  q=sp.exercise(cid,tier,step,o['quantity'],o['id'])
  answer=q['answer']
  if bad and step==4:answer=next(x['value'] for x in q['options'] if x['value']!=answer)
  act(s,c,cid,'special_work',{'id':o['id'],'step':step,'answer':answer})
 return act(s,c,cid,'special_settle',{'id':o['id']})['receipt']

def test_learning_fee_once_and_free_retry_without_rewards():
 s,c=prepared();before=c['money'];act(s,c,'grocery','special_enrol',{'tier':1})
 assert c['money']==before-3000
 with pytest.raises(e.GameError):act(s,c,'grocery','special_enrol',{'tier':1})
 for step in range(5):
  q=sp.exercise('grocery',1,step,1)
  wrong=99999 if q['type']=='number' else next(x['value'] for x in q['options'] if x['value']!=q['answer'])
  act(s,c,'grocery','special_practice',{'tier':1,'step':step,'answer':wrong})
 assert c[sp.KEY]['tier']==0 and c[sp.KEY]['study']['step']==0
 for step in range(5):act(s,c,'grocery','special_practice',{'tier':1,'step':step,'answer':sp.exercise('grocery',1,step,1)['answer']})
 assert c[sp.KEY]['tier']==1 and c['money']==before-3000 and c['xp']==90000

def test_job_exact_fifo_ledger_no_multipliers_and_one_payment():
 s,c=prepared();learn(s,c,'grocery',1);before=c['money']
 r=job(s,c,'grocery',1)
 assert c['money']-before==r['net']==jobs.NET[0]
 assert c['earnings']==c['costs']==0
 with pytest.raises(e.GameError):act(s,c,'grocery','special_settle',{'id':r['id']})
 sp.validate(c,'grocery');jobs.validate_account(s)

def test_cancel_keeps_customer_and_pack_and_shared_quota():
 s,c=prepared();learn(s,c,'grocery',1);act(s,c,'grocery','special_offer',{'tier':1});o=copy.deepcopy(c[sp.KEY]['job'])
 with pytest.raises(e.GameError):quota.reserve(s,'clothing-1',NOW)
 act(s,c,'grocery','special_cancel',{'id':o['id']});assert quota.public(s,NOW)['available']==1
 act(s,c,'grocery','special_offer',{'tier':1});assert c[sp.KEY]['job']==o

def test_pure_projection_hides_answers_and_unknown_fields_rejected():
 s,c=prepared();learn(s,c,'grocery',1);act(s,c,'grocery','special_offer',{'tier':1});before=copy.deepcopy(s)
 dto=sp.public(s,c,'grocery',NOW);assert s==before
 assert 'answer' not in str(dto) and 'unit_cost' in str(dto)
 with pytest.raises(e.GameError):act(s,c,'grocery','special_start',{'id':c[sp.KEY]['job']['id'],'quantity':1})

def test_free_pagoda_and_organizational_allowance():
 for cid in ('pagoda','police','post_office'):
  s,c=prepared(cid);before=c['money'];learn(s,c,cid,1)
  assert c['money']==before-(0 if cid=='pagoda' else 3000)
  before=c['money'];r=job(s,c,cid,1)
  assert c['money']-before==(0 if cid=='pagoda' else 200)
  assert r['materials']==r['tax']==0


@pytest.mark.parametrize('change',[{'money':2999},{'xp':0},{'started':False}])
def test_learning_gates_do_not_charge(change):
 s,c=prepared();c.update(change);before=copy.deepcopy(c)
 with pytest.raises(e.GameError):act(s,c,'grocery','special_enrol',{'tier':1})
 assert c==before


@pytest.mark.parametrize('tier',[True,0,2,11,'1'])
def test_learning_rejects_invalid_or_skipped_tiers(tier):
 s,c=prepared();before=copy.deepcopy(s)
 with pytest.raises(e.GameError):act(s,c,'grocery','special_enrol',{'tier':tier})
 assert s==before


def test_stock_transit_and_held_use_capacity_missing_inputs_do_not_spend():
 s,c=prepared();learn(s,c,'grocery',1);act(s,c,'grocery','special_offer',{'tier':1});oid=c[sp.KEY]['job']['id']
 with pytest.raises(e.GameError):act(s,c,'grocery','special_stock_buy',dict(code='sp1_0',quantity=81))
 order=act(s,c,'grocery','special_stock_buy',dict(code='sp1_0',quantity=80))['order']
 before=copy.deepcopy(s)
 with pytest.raises(e.GameError):act(s,c,'grocery','special_stock_buy',dict(code='sp1_0',quantity=1))
 with pytest.raises(e.GameError):act(s,c,'grocery','special_stock_receive',dict(order=order,count=79))
 with pytest.raises(e.GameError):act(s,c,'grocery','special_start',dict(id=oid))
 assert s==before
 act(s,c,'grocery','special_stock_receive',dict(order=order,count=80))
 before=copy.deepcopy(s)
 with pytest.raises(e.GameError):act(s,c,'grocery','special_start',dict(id=oid))
 assert s==before # second input absent: first input remains free
 order=act(s,c,'grocery','special_stock_buy',dict(code='sp1_1',quantity=1))['order']
 act(s,c,'grocery','special_stock_receive',dict(order=order,count=1))
 act(s,c,'grocery','special_start',dict(id=oid))
 assert stock.units(c,'sp1_0')==79 and stock.occupied(c,'sp1_0')==80
 with pytest.raises(e.GameError):act(s,c,'grocery','special_stock_buy',dict(code='sp1_0',quantity=1))
 assert quota.public(s,NOW)['available']==0
 quota.carry_reset(s,s,'grocery');assert quota.public(s,NOW)['available']==0


def test_failed_acceptance_consumes_inputs_pays_labor_and_refunds_tax():
 s,c=prepared();learn(s,c,'grocery',1);before=c['money'];r=job(s,c,'grocery',1,bad=True)
 assert r['quality']==r['revenue']==r['tax']==0
 assert c['money']-before==r['net']==-r['materials']-r['wages']
 assert r['refund']>0 and not c[stock.KEY]['lots']
 assert r['evidence'][-1].startswith('Sai. ') and '0%' in r['message']
 e.validate_state(s)


def test_historical_fifo_costs_used_for_profit():
 s,c=prepared();learn(s,c,'grocery',1)
 # Two previously purchased lots have distinct historical costs.
 c[stock.KEY]=dict(v=1,seq=3,lots=[dict(id='special-supply-1',code='sp1_0',quantity=1,unit_cost=100),
  dict(id='special-supply-2',code='sp1_0',quantity=1,unit_cost=200),dict(id='special-supply-3',code='sp1_1',quantity=1,unit_cost=7)],orders=[])
 act(s,c,'grocery','special_offer',dict(tier=1));o=c[sp.KEY]['job'];act(s,c,'grocery','special_start',dict(id=o['id']))
 assert sum(x['quantity']*x['unit_cost'] for x in o['held'])==107
 assert c[stock.KEY]['lots'][0]['unit_cost']==200
 for step in range(5):act(s,c,'grocery','special_work',dict(id=o['id'],step=step,answer=sp.exercise('grocery',1,step,1,o['id'])['answer']))
 receipt=act(s,c,'grocery','special_settle',dict(id=o['id']))['receipt']
 assert receipt['materials']==107 and receipt['net']==receipt['revenue']-107-receipt['wages']-receipt['tax']
 e.validate_state(s)


def test_explanation_only_after_answer_and_no_answer_key_in_question():
 s,c=prepared();act(s,c,'grocery','special_enrol',dict(tier=1))
 dto=sp.public(s,c,'grocery',NOW)
 assert pack('grocery',1)['check']['why'] not in dto['study']['instructions']
 assert 'answer' not in dto['study']['actions'][0]['fields'][0]
 assert dto['study']['feedback']==''


@pytest.mark.parametrize('lots,transit',[(4000,0),(60,21),(0,81)])
def test_import_rejects_stock_over_paid_capacity(lots,transit):
 s,c=prepared();learn(s,c,'grocery',1)
 c[stock.KEY]=dict(v=1,seq=2,lots=[],orders=[])
 for key,n,index in [('lots',lots,1),('orders',transit,2)]:
  if n:c[stock.KEY][key].append(dict(id=f'special-supply-{index}',code='sp1_0',quantity=n,unit_cost=100))
 with pytest.raises(e.GameError):e.validate_state(s)


def test_f382_specialism_shows_real_day_rule_today_and_reason():
 s=e.new_state();s['current']='clothing';c=s['careers']['clothing']
 c.update(started=True,open=True,xp=90000,money=800000000)
 rows=sp.requirements(s,c,'clothing',1,NOW)
 assert [r.get('id') for r in rows][2]=='real_days' and rows[2]['label']=='Ngày thực đạt chuẩn'
 assert rows[2]['got']==0 and rows[2]['need']==2 and rows[2]['hint'].startswith('Hôm nay: 0/0 việc sạch')
 assert 'tuyển dụng' not in rows[4].get('reason','')
 nxt=sp.public(s,c,'clothing',NOW)['next']
 assert nxt['can_enrol'] is False and nxt['reason']=='Chưa đủ: Việc tự làm không lỗi.'
 assert 'scale' not in c,'reading requirements never writes the sidecar'
 scale.ensure(c,'clothing',NOW)['clean']=13
 nxt=sp.public(s,c,'clothing',NOW)['next']
 assert nxt['can_enrol'] is False and nxt['reason']=='Cần thêm 2 ngày thực đạt chuẩn.'
def test_offer_held_elsewhere_disables_the_order_and_names_it():
 """F#469: a contract of another career holds the shared allowance: the order button waits and the card says which."""
 s,c=prepared();learn(s,c,'grocery',1);quota.reserve(s,'clothing-1',NOW)
 view=sp.public(s,c,'grocery',NOW)
 assert view['held']['id']=='clothing-1' and view['held']['kind']=='scale' and not view['held']['here']
 assert all(a['disabled'] for a in view['actions'] if a['command']=='special_offer')
 with pytest.raises(e.GameError,match='Đang giữ hợp đồng điều phối ở Shop quần áo'):act(s,c,'grocery','special_offer',{'tier':1})
 quota.cancel(s,'clothing-1',NOW)
 view=sp.public(s,c,'grocery',NOW)
 assert 'held' not in view and not any(a.get('disabled') for a in view['actions'] if a['command']=='special_offer')
