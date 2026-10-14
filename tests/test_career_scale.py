"""Ownership, real-day progression and physical resource contracts."""
import copy
import json
import pytest

from game import engine as e
from game import career_scale as scale
from game import career_scale_resources as resources
from game import career_scale_finance as finance

NOW = 1791936000


def fixture_state(cid='grocery', tier=0):
    from game import employment
    s = e.new_state()
    c = s['careers'][cid]
    c.update(started=True, open=True, money=500_000_000)
    if employment.required(cid): c['job']=employment.hired_record(cid)
    r = scale.ensure(c, cid, NOW)
    if tier:
        r['tier'] = tier
        r['today']['requires_contract'] = True
        resources.ensure(c, cid)
    return s, c


def finish(c, n, mistakes=0, now=NOW):
    task = dict(id=f'grocery-{c["day"]:04d}-{n}', career='grocery', day=c['day'],
                status='completed', mistakes=mistakes)
    c['tasks'].append(task)
    c['completed_ids'].append(task['id'])
    return scale.completed(c, 'grocery', task, now)


def ready(c):
    c['scale'].update(clean=1200, qualified_days=240, start_day=c['scale']['today']['day']-240)


def act(s, c, name, **payload):
    payload['expected_revision'] = c['scale']['revision']
    return scale.action(s, c, 'grocery', name, payload, NOW)


def test_optional_sidecar_public_pure_preserves_legacy():
    s = e.new_state(); c = s['careers']['grocery']
    c['money'] = 900000000; c['day'] = 500
    before = copy.deepcopy(c)
    out = scale.public(s, c, 'grocery', NOW)
    assert out['tier'] == 0 and out['next']['can_buy'] is False
    assert c == before
    scale.validate(c, 'grocery')


def test_upgrade_exact_capital_once_and_stale():
    s, c = fixture_state(); ready(c)
    legacy = {k: copy.deepcopy(c[k]) for k in ('stock','tasks','upgrades','earnings','costs')}
    money = c['money']; revenue = c['ops']['finance']['period_revenue']
    scale.action(s, c, 'grocery', 'scale_upgrade', {'expected_tier': 0}, NOW)
    assert c['money'] == money - 50000
    assert c['ops']['finance']['period_revenue'] == revenue
    assert all(c[k] == v for k, v in legacy.items())
    assert len(c['scale']['resources']) == 2 and not c['scale']['crew']
    with pytest.raises(e.GameError):
        scale.action(s, c, 'grocery', 'scale_upgrade', {'expected_tier': 0}, NOW)
    assert c['money'] == money - 50000


def test_certificate_and_funds_guards():
    s, c = fixture_state(tier=1); ready(c)
    with pytest.raises(e.GameError):
        scale.action(s, c, 'grocery', 'scale_upgrade', {'expected_tier': 1}, NOW)
    s['journey']['certificates'] = {'business_advanced': {'earned_day': 1}}
    c['money'] = 249999
    with pytest.raises(e.GameError):
        scale.action(s, c, 'grocery', 'scale_upgrade', {'expected_tier': 1}, NOW)
    for invalid in (True, 250000.0):
        c['money'] = invalid
        with pytest.raises(e.GameError):
            scale.action(s, c, 'grocery', 'scale_upgrade', {'expected_tier': 1}, NOW)


def test_real_day_finalizes_only_after_errors_and_never_from_career_day():
    s, c = fixture_state()
    for n in range(3): assert finish(c, n)
    assert scale.public(s, c, 'grocery', NOW)['progress']['qualified_days'] == 0
    finish(c, 3, mistakes=1)
    c['day'] += 1
    finish(c, 4, now=NOW+86400)
    assert c['scale']['qualified_days'] == 0
    for n in range(5, 8): finish(c, n, now=NOW+86400)
    finish(c, 8, now=NOW+2*86400)
    assert c['scale']['qualified_days'] == 1
    assert len(c['scale']['today']['ids']) == 1


def test_contract_required_after_first_upgrade_and_clock_rollback():
    s, c = fixture_state(tier=1)
    for n in range(3): finish(c, n)
    finish(c, 3, now=NOW+86400)
    assert c['scale']['qualified_days'] == 0
    for n in range(4, 6): finish(c, n, now=NOW+86400)
    scale.accepted(c, 'grocery', NOW+86400)
    finish(c, 6, now=NOW+2*86400)
    assert c['scale']['qualified_days'] == 1
    assert scale.completed(c, 'grocery', c['tasks'][0], NOW) is False


def test_authoritative_task_and_duplicate_guards():
    s, c = fixture_state(); finish(c, 0)
    assert not scale.completed(c, 'grocery', copy.deepcopy(c['tasks'][0]), NOW)
    assert not scale.completed(c, 'grocery', c['tasks'][0], NOW)
    assert c['scale']['clean'] == 1
    assert not scale.completed(c, 'grocery', c['tasks'][0], NOW+86400)


def test_valid_mastery_clean_inherited_once_but_not_its_career_days():
    from game import career_mastery as mastery
    from tests.test_career_mastery import career, job
    c=career(); c['started']=True
    task=job(c,'grocery'); mastery.completed(c,'grocery',task)
    scale.completed(c,'grocery',task,NOW)
    assert c['scale']['clean']==1 and c['scale']['qualified_days']==0
    task2=job(c,'grocery'); mastery.completed(c,'grocery',task2)
    scale.completed(c,'grocery',task2,NOW)
    assert c['scale']['clean']==2
    assert c['scale']['inherited_clean']==0
    scale.validate(c,'grocery')


def test_rejected_resource_action_does_not_mutate_save():
    s,c=fixture_state(tier=1); c['money']=0
    before=copy.deepcopy(c)
    with pytest.raises(e.GameError): act(s,c,'scale_crew_hire',candidate=0)
    assert c==before


def test_daily_tracking_overflow_cannot_freeze_a_passing_ratio():
    s,c=fixture_state()
    today=c['scale']['today']
    today.update(ids=[f'grocery-0001-{n}' for n in range(scale.DAY_MAX)],total=scale.DAY_MAX,clean=scale.DAY_MAX)
    c['scale']['clean']=scale.DAY_MAX
    assert not finish(c,scale.DAY_MAX,mistakes=1)
    assert today['overflow']
    scale.ensure(c,'grocery',NOW+86400)
    assert c['scale']['qualified_days']==0


def test_maintenance_explicit_exact_cost_and_no_busy_reset():
    s,c=fixture_state(tier=1)
    act(s,c,'scale_crew_hire',candidate=0)
    act(s,c,'scale_resource_assign',resource='r1',crew=c['scale']['crew'][0]['id'],site='base')
    row=c['scale']['resources'][0]; row['condition']=70
    fee=resources.maintenance_fee(c,'grocery',row); before=c['money']
    resources.lock(c,'grocery','grocery-1',['r1'])
    with pytest.raises(e.GameError): act(s,c,'scale_resource_maintain',resource='r1',expected_condition=70)
    resources.release(c,'grocery','grocery-1')
    act(s,c,'scale_resource_maintain',resource='r1',expected_condition=70)
    assert c['money']==before-fee and c['scale']['resources'][0]['condition']==100
    scale.validate(c,'grocery')


def test_resources_need_crew_distinct_and_lock_prevents_mutations():
    s, c = fixture_state(tier=1)
    assert resources.available(c, 'grocery') == []
    act(s,c,'scale_crew_hire', candidate=0)
    crew = c['scale']['crew'][0]['id']
    act(s,c,'scale_resource_assign', resource='r1', crew=crew, site='base')
    assert len(resources.available(c, 'grocery')) == 1
    with pytest.raises(e.GameError):
        act(s,c,'scale_resource_assign', resource='r2', crew=crew, site='base')
    resources.lock(c,'grocery','grocery-1',['r1'])
    with pytest.raises(e.GameError): act(s,c,'scale_crew_fire', crew=crew)
    with pytest.raises(e.GameError): resources.lock(c,'grocery','grocery-2',['r1'])
    resources.release(c,'grocery','grocery-1')
    resources.validate(c,'grocery')


def test_repeated_skill_template_creates_fifty_distinct_recruits():
    from game import operations
    s,c=fixture_state(tier=8)
    legacy=copy.deepcopy(c['ops']['staff'])
    template_name=operations.PEOPLE['grocery'][0][0]
    for _ in range(50):
        act(s,c,'scale_crew_hire',candidate=0)
    crew=c['scale']['crew']
    assert len({x['name'] for x in crew})==50
    assert len({x['id'] for x in crew})==50
    assert all(x['name']!=template_name and 'tuyển mới' in x['name'] for x in crew)
    assert c['ops']['staff']==legacy
    resources.validate(c,'grocery')
    original_name=crew[0]['name']
    act(s,c,'scale_crew_fire',crew=crew[0]['id'])
    act(s,c,'scale_crew_hire',candidate=0)
    assert c['scale']['crew'][-1]['name']!=original_name
    assert '#51' in c['scale']['crew'][-1]['name']
    view=resources.public(c,'grocery')
    hire=next(x for x in view['actions'] if x['command']=='scale_crew_hire')
    assert 'mẫu kỹ năng' in hire['label'] and 'Tuyển người mới' in hire['label']
    resources.validate(c,'grocery')


def test_shared_slots_count_business_only_and_chain_cert():
    s, c = fixture_state(tier=5)
    act(s,c,'scale_crew_hire',candidate=0)
    crew=c['scale']['crew'][0]['id']
    s['journey']['quay']={'stalls':[{'id':'q1'}]}
    with pytest.raises(e.GameError): act(s,c,'scale_site_open',resource='r7',crew=crew)
    s['journey']['quay']['paid_tier']={'slots':2}
    act(s,c,'scale_site_open',resource='r7',crew=crew)
    assert scale.external_slots(s)==1
    act(s,c,'scale_crew_hire',candidate=1)
    crew=c['scale']['crew'][1]['id']
    with pytest.raises(e.GameError): act(s,c,'scale_site_open',resource='r8',crew=crew)
    s['journey']['certificates']={'business_chain':{'earned_day':1}}
    act(s,c,'scale_site_open',resource='r8',crew=crew)
    assert scale.external_slots(s)==2


def test_agency_community_sites_do_not_use_business_rights():
    for cid in ('teacher','pagoda'):
        s,c=fixture_state(cid,tier=4)
        s['journey']['quay']={'stalls':[{'id':'q1'}]}
        scale.action(s,c,cid,'scale_crew_hire',dict(candidate=0,expected_revision=0),NOW)
        scale.action(s,c,cid,'scale_site_open',dict(resource='r6',crew=c['scale']['crew'][0]['id'],expected_revision=1),NOW)
        assert len(c['scale']['sites'])==2 and scale.external_slots(s)==0
        scale.validate(c,cid)


def test_public_rollover_does_not_commit_progress_and_current_day_is_pending():
    s,c=fixture_state()
    for n in range(3): finish(c,n)
    before=copy.deepcopy(c)
    view=scale.public(s,c,'grocery',NOW+86400)
    assert view['progress']['qualified_days']==1 and c==before
    assert view['progress']['today']['pending'] is True


def test_lock_rejects_foreign_career_and_duplicates_atomically():
    s,c=fixture_state(tier=1)
    act(s,c,'scale_crew_hire',candidate=0)
    act(s,c,'scale_resource_assign',resource='r1',crew=c['scale']['crew'][0]['id'],site='base')
    before=copy.deepcopy(c)
    for job,ids in (('teacher-1',['r1']),('grocery-1',['r1','r1']),('grocery-1',['r1','r2'])):
        with pytest.raises(e.GameError): resources.lock(c,'grocery',job,ids)
        assert c==before


@pytest.mark.parametrize('cid',['teacher','pagoda'])
def test_agency_community_no_fee_or_rank_change(cid):
    s,c=fixture_state(cid); ready(c); old=copy.deepcopy(c.get('job')); money=c['money']
    scale.action(s,c,cid,'scale_upgrade',{'expected_tier':0},NOW)
    assert c['money']==money and c.get('job')==old


def test_existing_employment_required_but_no_paid_authority_rank():
    s,c=fixture_state('teacher'); ready(c); c['job']['status']='none'
    with pytest.raises(e.GameError): scale.action(s,c,'teacher','scale_upgrade',{'expected_tier':0},NOW)


def test_all_career_stages_allocate_whole_network_only_and_preserve_legacy():
    from game import career_scale_content as content
    for cid in content.PROFILES:
        s,c=fixture_state(cid)
        legacy=copy.deepcopy(c['ops'])
        for tier in range(1,9):
            c['scale']['tier']=tier; c['scale']['today']['requires_contract']=True
            resources.ensure(c,cid)
            scale.validate(c,cid)
            view=scale.public(s,c,cid,NOW)
            assert len(view['resources'])==content.stage(cid,tier).resources
            assert len(view['sites'])==1 and view['crew']==[]
            assert c['ops']==legacy


def test_upgrade_preserves_positions_when_new_site_density_falls():
    s,c=fixture_state(tier=3); ready(c)
    assert sum(x['site']=='base' for x in c['scale']['resources'])==6
    s['journey']['certificates']={'business_advanced':{'earned_day':1}}
    scale.action(s,c,'grocery','scale_upgrade',{'expected_tier':3},NOW)
    assert sum(x['site']=='base' for x in c['scale']['resources'])==6
    scale.validate(c,'grocery')


def test_bool_corruption_rejected_and_receipts_bounded():
    s,c=fixture_state(); c['scale']['tier']=True
    with pytest.raises(e.GameError): scale.validate(c,'grocery')
    c['scale']['tier']=0
    for n in range(85): finance.move(s,c,-1,'Test',str(n))
    assert len(c['scale']['capital_history']) <= 80
    before=c['money']
    with pytest.raises(e.GameError): finance.move(s,c,True,'Test','bool')
    assert c['money']==before


def test_f382_kept_job_finished_today_counts_but_future_day_does_not():
    """F#383 (chippoo, clothing): jobs kept at day close ("việc được giữ lại") and finished on a later career day
    are real manual work for the real-day track."""
    s, c = fixture_state()
    c['day'] = 10
    kept = dict(id='grocery-0009-00', career='grocery', day=9, status='completed', mistakes=0)
    c['tasks'].append(kept); c['completed_ids'].append(kept['id'])
    assert scale.completed(c, 'grocery', kept, NOW)
    assert c['scale']['today']['clean'] == 1 and c['scale']['clean'] == 1
    future = dict(id='grocery-0011-00', career='grocery', day=11, status='completed', mistakes=0)
    c['tasks'].append(future); c['completed_ids'].append(future['id'])
    assert not scale.completed(c, 'grocery', future, NOW)
    for bad in ('9', None, True):
        t = dict(kept, id=f'grocery-x-{bad}', day=bad); c['tasks'].append(t); c['completed_ids'].append(t['id'])
        assert not scale.completed(c, 'grocery', t, NOW)
    scale.validate(c, 'grocery')


def test_f382_requirement_explains_rule_and_today_live():
    """F#382 (yenmy1808_, 16/18 clean today): the row says today counts at 0h and the button says what is missing."""
    s, c = fixture_state()
    for n in range(18): finish(c, n, mistakes=int(n < 2))
    nxt = scale.public(s, c, 'grocery', NOW)['next']
    row = nxt['requirements'][0]
    assert row['id'] == 'real_days' and row['label'] == 'Ngày thực đạt chuẩn'
    assert (row['got'], row['need'], row['met']) == (0, 3, False)
    assert row['hint'] == 'Hôm nay: 16/18 việc sạch · đạt, cộng lúc 0h'
    assert '≥' not in row['rule'] and '80%' in row['rule'] and '0h' in row['rule']
    assert nxt['reason'] == 'Cần thêm 3 ngày thực đạt chuẩn.'
    assert 'đã kết thúc' not in nxt['reason']
    # Tomorrow the day is in, and the live line starts again.
    nxt = scale.public(s, c, 'grocery', NOW + 86400)['next']
    assert nxt['requirements'][0]['got'] == 1
    assert nxt['requirements'][0]['hint'] == 'Hôm nay: 0/0 việc sạch · cần ≥3 việc sạch, ≥80%'
    assert nxt['reason'] == 'Cần thêm 2 ngày thực đạt chuẩn.'


def test_f382_weak_ratio_and_missing_contract_are_named():
    s, c = fixture_state()
    for n in range(4): finish(c, n, mistakes=int(n == 0))
    assert scale.public(s, c, 'grocery', NOW)['next']['requirements'][0]['hint'].endswith('cần ≥3 việc sạch, ≥80%')
    s, c = fixture_state(tier=1)
    for n in range(3): finish(c, n)
    row = scale.public(s, c, 'grocery', NOW)['next']['requirements'][0]
    assert row['hint'] == 'Hôm nay: 3/3 việc sạch · thiếu ca quản lý nghiệm thu'
    assert 'ca quản lý được nghiệm thu' in row['rule']
    scale.accepted(c, 'grocery', NOW)
    assert scale.public(s, c, 'grocery', NOW)['next']['requirements'][0]['hint'].endswith('đạt, cộng lúc 0h')


def test_f382_other_missing_rows_read_as_sentences():
    s, c = fixture_state(); ready(c); c['money'] = 0
    assert scale.public(s, c, 'grocery', NOW)['next']['reason'] == 'Chưa đủ: Quỹ nghề (Góp vốn).'


def test_f383_engine_counts_a_kept_clothing_job_for_the_real_day_only():
    """Through the real engine: a clothing job kept past the day close and finished next career day."""
    from tests.test_career_clothing import job as clothing_job, solve
    j = clothing_job('fit'); tid = j.task['id']
    j.c['day'] += 1
    e.validate_state(j.state)
    solve(j, tid)
    assert j.get(tid)['status'] == 'completed' and j.get(tid)['day'] == j.c['day'] - 1
    assert j.c['scale']['clean'] == 1 and j.c['scale']['today']['ids'] == [tid]
    assert 'mastery' not in j.c, 'Tay nghề keeps its same-career-day rule'
    e.validate_state(json.loads(json.dumps(j.state)))
