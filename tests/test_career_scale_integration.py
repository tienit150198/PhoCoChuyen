"""Real engine commands across all careers, independent ledger reconciliation."""
import copy
import pytest

from game import engine as e, employment, career_scale as scale
from game import career_scale_resources as resources, career_scale_contracts as contracts
from game import career_scale_inventory as stock, capacity_progression as capacity
from game import order_progression as ordering
from game.career_scale_content import PROFILES, profile, stage


def prepared(cid, tier):
    s=e.new_state();s['current']=cid;c=s['careers'][cid]
    c.update(started=True, money=800_000_000)
    c['ops']['finance']['opening_balance']=c['money']
    if employment.required(cid):c['job']=employment.hired_record(cid)
    s['journey']['certificates']={x:dict(score=100,best=100,earned_day=1,attempts=1)
                                 for x in ('business_advanced','business_chain')}
    r=scale.ensure(c,cid)
    r.update(clean=1200,qualified_days=240,start_day=r['today']['day']-240)
    # The test provides eligibility; purchases and workflows use engine commands.
    for n in range(tier):s,_=e.apply_action(s,cid,'scale_upgrade',dict(expected_tier=n),owned=True,scoped=True)
    c=s['careers'][cid];r=c['scale']
    for i in range(len(r['resources'])):
        s,_=e.apply_action(s,cid,'scale_crew_hire',dict(candidate=i%len(resources.candidates(c,cid)),expected_revision=r['revision']),owned=True,scoped=True)
        c=s['careers'][cid];r=c['scale']
    # Layout fixture: opening and shared paid-slot action guards have dedicated tests.
    r['sites']=[dict(id='base' if i==0 else f'branch-{i}',name=f'Điểm {i+1}',public=False)
                for i in range(stage(cid,tier).sites)]
    for i,x in enumerate(r['resources']):x.update(site=r['sites'][i%len(r['sites'])]['id'],crew=r['crew'][i]['id'])
    if profile(cid).kind=='business':
        c['upgrades'] += [capacity.item_id(cid,i) for i in range(1,11)]
        c['upgrades'] += [ordering.item_id(cid,i) for i in range(1,11)]
    e.validate_state(s)
    return s


def run_contract(cid,tier,demand=100,bad=False):
    s=prepared(cid,tier)
    def act(name,p=None):
        nonlocal s
        s,result=e.apply_action(s,cid,name,p or {},owned=True,scoped=True)
        e.validate_career(s['careers'][cid],cid)
        return result
    start=s['careers'][cid]['money'];turn=s['careers'][cid]['turn']
    act('scale_offer');c=s['careers'][cid];o=c[contracts.KEY]['offer']
    o['demand']=demand
    o['quote']=contracts.project_quote(cid,tier,demand,len(o['resources']),len({x['site'] for x in o['resources']}))
    chosen=lambda phase:sorted(getattr(profile(cid).scenario,phase),key=lambda x:x.score,reverse=not bad)[0].id
    act('scale_plan',dict(id=o['id'],option=chosen('planning')))
    for line in contracts.requirements(c,cid,o):
        if profile(cid).kind=='business':
            room=stock.space(c,cid,line['code'])
            qty=(line['units']+room['carton_units']-1)//room['carton_units']
            while qty:
                count=min(qty,room['order'])
                order=act('scale_stock_buy',dict(site=line['site'],code=line['code'],quantity=count))
                act('scale_stock_receive',dict(order=order['order'],count=count));qty-=count
        act('scale_allocate',dict(id=o['id'],site=line['site'],code=line['code'],units=line['units']))
    for row in o['resources']:act('scale_schedule',dict(id=o['id'],resource=row['id'],role=row['role']))
    act('scale_start',dict(id=o['id'],option=chosen('allocation')))
    for site in sorted({x['site'] for x in o['resources']}):
        act('scale_resolve',dict(id=o['id'],site=site,option=chosen('exception')))
        act('scale_accept',dict(id=o['id'],site=site,option=chosen('acceptance')))
    receipt=act('scale_settle',dict(id=o['id']))['receipt']
    c=s['careers'][cid]
    remaining=sum(x['units']*x['unit_cost'] for x in c.get(stock.KEY,{}).get('lots',[]))
    assert c['money']+remaining-start==receipt['net']
    assert c['turn']==turn and c['earnings']==0 and c['costs']==0
    assert c['ops']['finance']['period_revenue']==0
    assert not any(x['busy'] for x in c['scale']['resources'])
    if not bad and demand==100:assert receipt['net']==stage(cid,tier).net
    e.validate_state(s)
    before=copy.deepcopy(s)
    with pytest.raises(e.GameError):e.apply_action(s,cid,'scale_settle',dict(id=o['id']))
    assert s==before
    return s,receipt


@pytest.mark.parametrize('cid',list(PROFILES))
@pytest.mark.parametrize('tier',range(1,9))
def test_every_career_stage_actual_commands_reconcile(cid,tier):
    run_contract(cid,tier)


@pytest.mark.parametrize('demand',[60,80])
@pytest.mark.parametrize('bad',[False,True])
def test_low_demand_and_failed_ca(demand,bad):
    run_contract('grocery',8,demand,bad)


def test_partial_sites_quote_cannot_reach_full_chain_reward():
    full=contracts.project_quote('grocery',8,100,50,12)
    partial=contracts.project_quote('grocery',8,100,50,10)
    assert partial['revenue']<full['revenue'] and partial['net']<full['net']


def test_cancel_change_crew_rebook_same_customer_without_softlock():
    s=prepared('grocery',1);cid='grocery'
    s,_=e.apply_action(s,cid,'scale_offer');old=copy.deepcopy(s['careers'][cid][contracts.KEY]['offer'])
    s,_=e.apply_action(s,cid,'scale_cancel',dict(id=old['id']))
    c=s['careers'][cid];c['scale']['resources'][0]['condition']=0
    s,_=e.apply_action(s,cid,'scale_offer')
    offer=s['careers'][cid][contracts.KEY]['offer']
    assert offer['id']==old['id'] and offer['demand']==old['demand']
    assert len(offer['resources'])==1


def test_public_is_pure_and_never_exposes_private_contract_state():
    s=prepared('grocery',1);s,_=e.apply_action(s,'grocery','scale_offer')
    before=copy.deepcopy(s);view=e.public_state(s,migrated=True)
    assert s==before
    c=view['careers']['grocery']
    assert 'scale_contracts' not in c and 'scale_stock' not in c
    assert 'choices' not in c['scale']['contract']
    assert all(a['command']!='scale_upgrade' for a in c['scale']['actions'])


def test_quitting_or_suspension_blocks_new_commitments_but_allows_cancel():
    s=prepared('police',1)
    s,_=e.apply_action(s,'police','scale_offer')
    oid=s['careers']['police'][contracts.KEY]['offer']['id']
    s,_=e.apply_action(s,'police','job_quit',dict(confirm=True))
    s,_=e.apply_action(s,'police','scale_cancel',dict(id=oid))
    with pytest.raises(e.GameError):e.apply_action(s,'police','scale_offer')
    from game import promotion
    s=prepared('police',1);s['journey'][promotion.BAN_KEY]={}
    with pytest.raises(e.GameError):e.apply_action(s,'police','scale_offer')


def test_offer_held_by_another_career_is_named_and_cancelled_from_here():
    """F#469: the one shared allowance holds another career's offer: this card names it (no button that can only
    answer "Đang giữ…"), the error says what and where, and Hủy here frees it for this career."""
    s=prepared('grocery',1);s['careers']['clothing']=prepared('clothing',1)['careers']['clothing']
    s,_=e.apply_action(s,'grocery','scale_offer');held=s['careers']['grocery'][contracts.KEY]['offer']['id']
    s['current']='clothing';e.validate_state(s)
    view=e.public_state(s,migrated=True)['careers']['clothing']['scale']
    assert view['held']['id']==held and view['held']['career']=='grocery' and not view['held']['here']
    offer=next(a for a in view['actions'] if a['command']=='scale_offer')
    assert offer['disabled'] and offer['reason']
    with pytest.raises(e.GameError,match='Đang giữ hợp đồng điều phối ở'):e.apply_action(s,'clothing','scale_offer')
    with pytest.raises(e.GameError):e.apply_action(s,'clothing','scale_release',dict(id='grocery-9'))
    s,_=e.apply_action(s,'clothing','scale_release',dict(id=held))
    assert not s['careers']['grocery'][contracts.KEY]['offer']['reserved']
    view=e.public_state(s,migrated=True)['careers']['clothing']['scale']
    assert 'held' not in view and not next(a for a in view['actions'] if a['command']=='scale_offer').get('disabled')
    s,_=e.apply_action(s,'clothing','scale_offer')
    assert s['careers']['clothing'][contracts.KEY]['offer']['reserved']
    e.validate_state(s)
