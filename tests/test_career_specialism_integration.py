"""Execute the actual reducer for every authored module, not just catalogue sums."""
import copy
import pytest
from game import engine as e, career_specialism as sp, career_specialism_jobs as jobs
from game import career_specialism_stock as stock, career_scale_quota as quota
from game import capacity_progression as cap, order_progression as ordering
from game.content import CAREERS
from tests.test_career_specialism import prepared


@pytest.mark.parametrize('cid',list(CAREERS))
@pytest.mark.parametrize('tier',range(1,11))
def test_every_pack_real_learning_stock_work_and_exact_money(cid,tier):
    s,c=prepared(cid)
    # Fixture supplies prior progress/paid rights; this tier's fee and work are real commands.
    c[sp.KEY]=dict(v=1,tier=tier-1,study=None,tuition=[dict(tier=t,fee=sp.fee(cid,t)) for t in range(1,tier)],seq=0,job=None,history=[])
    if jobs.kind(cid)=='business':
        c['upgrades'] += [cap.item_id(cid,i) for i in range(1,11)]
        c['upgrades'] += [ordering.item_id(cid,i) for i in range(1,11)]
    e.validate_state(s)
    def act(name,p):
        nonlocal s,c
        s,result=e.apply_action(s,cid,name,p,owned=True,scoped=True);c=s['careers'][cid]
        return result
    before=c['money'];xp=c['xp'];earnings=c['earnings']
    act('special_enrol',dict(tier=tier))
    assert before-c['money']==sp.fee(cid,tier)
    for step in range(5):act('special_practice',dict(tier=tier,step=step,answer=sp.exercise(cid,tier,step,1)['answer']))
    assert c[sp.KEY]['tier']==tier and c['xp']==xp
    start=c['money'];act('special_offer',dict(tier=tier));o=c[sp.KEY]['job']
    assert quota.public(s)['reserved']==(None if jobs.kind(cid)=='community' else o['id'])
    if jobs.kind(cid)=='business':
        for m in stock.materials(cid,tier):
            result=act('special_stock_buy',dict(code=m['code'],quantity=o['quantity']))
            act('special_stock_receive',dict(order=result['order'],count=o['quantity']))
    act('special_start',dict(id=o['id']))
    assert quota.public(s)['reserved'] is None
    for step in range(5):act('special_work',dict(id=o['id'],step=step,answer=sp.exercise(cid,tier,step,o['quantity'],o['id'])['answer']))
    result=act('special_settle',dict(id=o['id']))['receipt']
    assert c['money']-start==result['net']==(0 if jobs.kind(cid)=='community' else jobs.NET[tier-1])
    assert c['earnings']==earnings and c['ops']['finance']['period_revenue']==0
    assert not c.get(stock.KEY,{}).get('lots') and c[sp.KEY]['job'] is None
    assert c['money']==c['ops']['finance']['opening_balance']+sum(x['amount'] for x in c['ops']['finance']['ledger'])
    e.validate_state(s)


def test_joint_quota_rejects_orphans_and_reset_returns_only_reserved_start():
    s,c=prepared();c[sp.KEY]=dict(v=1,tier=1,study=None,tuition=[dict(tier=1,fee=3000)],seq=0,job=None,history=[])
    sp.action(s,c,'grocery','special_offer',dict(tier=1))
    bad=copy.deepcopy(s);bad['journey']['scale_quota']['reserved']='milk_tea-1'
    with pytest.raises(e.GameError):e.validate_state(bad)
    quota.carry_reset(s,s,'grocery');c.pop(sp.KEY)
    assert quota.public(s)['available']==1 and quota.public(s)['reserved'] is None


def test_engine_blocks_unemployed_new_work_but_keeps_training_receiving_and_cleanup():
    from game import employment
    s,c=prepared('post_office');posting=c['job']['employer'];c['job']=employment.initial()
    c['job']['history']=[dict(day=c['day'],event='quit',posting=posting)]
    for name,p in [('special_enrol',{'tier':1}),('special_offer',{'tier':1})]:
        with pytest.raises(e.GameError):e.apply_action(s,'post_office',name,p,owned=True,scoped=True)
    reason=sp.requirements(s,c,'post_office',1,None)[4]['reason']
    assert 'tuyển dụng' in reason


def test_summary_projection_never_leaks_other_career_sidecars():
    s,c=prepared();c[sp.KEY]=dict(v=1,tier=1,study=None,tuition=[dict(tier=1,fee=3000)],seq=0,job=None,history=[])
    v=e.public_state(s,full='milk_tea')
    assert 'specialism' not in v['careers']['grocery'] and 'special_stock' not in v['careers']['grocery']
