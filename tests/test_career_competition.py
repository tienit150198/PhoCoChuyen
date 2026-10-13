"""Competition is prospective, deterministic, earned and never directly pays funds."""
import copy
from unittest.mock import patch

import pytest

from game import career_competition as cc


def career(day=1):
    return dict(day=day, open=True, xp=0, metrics={'served': 0}, tasks=[], completed_ids=[])


def job(c, cid='post_office', **values):
    t = dict(id=f'{cid}-{c["day"]:04d}-{len(c["tasks"]):02d}', career=cid,
             day=c['day'], status='completed', mistakes=0, known=True)
    t.update(values)
    c['tasks'].append(t)
    c['completed_ids'].append(t['id'])
    c['metrics']['served'] += 1
    return t


def feedback(fair=5, **extra):
    return dict(fair=fair, criteria=[dict(key='judgment', label='Judgment', score=fair, note='Evidence')], **extra)


def shift(c, cid='post_office', fair=5, income=1000, allowed=True, abandoned=False):
    c['open'] = True
    assert cc.completed(c, cid, job(c, cid), feedback(fair), income)
    s = {'journey': {'life': {'spirit': 0}}} if cid == 'pagoda' else {}
    result = cc.close(s, c, cid, allowed, abandoned)
    c['day'] += 1
    cc.validate(c, cid)
    return result


def test_old_save_public_is_pure():
    c = career(99)
    original = copy.deepcopy(c)
    assert cc.public({}, c, 'post_office')['period']['worked_days'] == 0
    cc.validate(c, 'post_office')
    assert c == original


def test_only_real_current_manual_work_and_once():
    c = career()
    for kwargs in ({'status': 'cancelled'}, {'status': 'referred'}, {'day': 0},
                   {'player_order': True}, {'kind': 'brief'}, {'job': 'setup'}):
        assert not cc.completed(c, 'post_office', job(c, **kwargs), feedback(), 999)
    assert 'competition' not in c
    t = job(c)
    assert not cc.completed(c, 'post_office', copy.deepcopy(t), feedback(), 1)
    assert cc.completed(c, 'post_office', t, feedback(), 1)
    assert not cc.completed(c, 'post_office', t, feedback(), 1)
    assert not cc.completed(c, 'post_office', job(c, 'lawyer'), feedback(), 1)
    assert cc.public({}, c, 'post_office')['today']['completed'] == 1


def test_fair_not_display_stars_mistakes_and_missing_judgment():
    c = career()
    cc.completed(c, 'post_office', job(c), feedback(stars_original=1), 0)
    assert cc.public({}, c, 'post_office')['today']['score'] == 100
    d = career()
    cc.completed(d, 'post_office', job(d, mistakes=3), dict(fair=3, criteria=[]), 0)
    v = cc.public({}, d, 'post_office')['today']
    assert v['score'] < 70
    assert 'judgment' not in {x['id'] for x in v['components']}


def test_empty_and_setup_days_do_not_advance():
    c = career()
    assert cc.close({}, c, 'post_office')['bonus'] == 0
    assert 'competition' not in c
    shift(c)
    before = cc.public({}, c, 'post_office')['period']['worked_days']
    cc.close({}, c, 'post_office')
    assert cc.public({}, c, 'post_office')['period']['worked_days'] == before


def test_ten_shifts_cap_idempotence_and_no_funds_mutation():
    c = career()
    for _ in range(9):
        assert shift(c)['bonus'] == 0
    out = shift(c)
    assert out['bonus'] == 300
    assert out['period']['score'] == 100
    assert cc.close({}, c, 'post_office')['bonus'] == 0
    assert 'money' not in c
    assert cc.public({}, c, 'post_office')['period']['worked_days'] == 0


def test_no_reward_day_never_replays_and_budget_is_only_supplied_income():
    c = career()
    for _ in range(9):
        shift(c, income=10)
    assert shift(c, income=0, allowed=False)['bonus'] == 0
    c['earnings'] = 1000000000
    for _ in range(10):
        out = shift(c, income=0)
    assert out['bonus'] == 0
    d = career()
    for _ in range(10):
        out = shift(d, income=7)
    assert out['bonus'] == 7


def test_abandoned_and_accepted_unfinished_penalized_but_waiting_queue_not():
    c = career()
    cc.completed(c, 'post_office', job(c), feedback(), 100)
    job(c, status='new', known=False)
    assert cc.close({}, c, 'post_office')['score'] == 100
    d = career()
    cc.completed(d, 'post_office', job(d), feedback(), 100)
    job(d, status='in_progress')
    assert cc.close({}, d, 'post_office')['score'] < 70
    e = career()
    assert shift(e, abandoned=True)['score'] == 0


def test_npcs_deterministic_and_ties_share_rank():
    c, d = career(), career()
    shift(c, fair=5)
    shift(d, fair=1)
    a = [x for x in cc.public({}, c, 'post_office')['standings'] if not x['is_player']]
    b = [x for x in cc.public({}, d, 'post_office')['standings'] if not x['is_player']]
    assert [(x['id'], x['score']) for x in sorted(a, key=lambda x: x['id'])] == [(x['id'], x['score']) for x in sorted(b, key=lambda x: x['id'])]
    zero = cc.public({}, career(), 'post_office')['standings']
    assert {x['rank'] for x in zero} == {1}


def test_pagoda_never_cash_capped_spirit_once():
    c = career()
    for _ in range(10):
        result = shift(c, cid='pagoda', income=99999)
    assert result['bonus'] == 0
    assert 0 < result['spirit'] <= cc.public({}, c, 'pagoda')['reward']['spirit_cap']
    assert cc.close({}, c, 'pagoda')['spirit'] == 0


@pytest.mark.parametrize('spirit,expected', [(99, 1), (100, 0), (None, 0)])
def test_pagoda_actual_spirit_headroom_is_saved_and_validated(spirit, expected):
    c = career()
    for _ in range(9):
        shift(c, cid='pagoda')
    cc.completed(c, 'pagoda', job(c, 'pagoda'), feedback(), 0)
    s = {'journey': {'life': {'spirit': spirit}}}
    result = cc.close(s, c, 'pagoda')
    assert result['spirit'] == expected
    assert cc.public(s, c, 'pagoda')['last_result']['spirit'] == expected
    assert s['journey']['life']['spirit'] == spirit
    cc.validate(c, 'pagoda')


def test_case_requires_rank_and_work_is_immutable_and_sanitized():
    c = career()
    with patch('game.promotion.rank', return_value=3):
        with pytest.raises(Exception):
            cc.action({}, c, 'post_office', 'competition_start', {})
        cc.completed(c, 'post_office', job(c), feedback(), 10)
        cc.action({}, c, 'post_office', 'competition_start', {})
        public = cc.public({}, c, 'post_office')['case']['active']
        assert all(set(x) == {'id', 'label'} for x in public['options'])
        cc.action({}, c, 'post_office', 'competition_answer', {'option': public['options'][0]['id']})
        old = copy.deepcopy(c)
        with pytest.raises(Exception):
            cc.action({}, c, 'post_office', 'competition_answer', {'option': public['options'][1]['id']})
        with pytest.raises(Exception):
            cc.action({}, c, 'post_office', 'competition_start', {})
        assert c == old
        cc.validate(c, 'post_office')


def test_progression_requires_good_periods_and_real_rank_without_changing_police_ladder():
    c = career()
    s = {'journey': {'promo': {'police': {'rank': 0}}}}
    before = copy.deepcopy(s)
    with patch('game.promotion.rank', return_value=4):
        for requirement in (2, 3, 4, 6):
            old = cc.public(s, c, 'police')['league']
            for _ in range(requirement * 10):
                shift(c, 'police')
            assert cc.public(s, c, 'police')['league'] == old + 1
    assert s == before
    assert cc.public({}, c, 'police')['next'] is None
    d = career()
    with patch('game.promotion.rank', return_value=0):
        for _ in range(20):
            shift(d)
    assert cc.public({}, d, 'post_office')['league'] == 0


def test_history_compacts_without_losing_progress_or_blocking_close():
    c = career()
    with patch('game.promotion.rank', return_value=7):
        for _ in range(270):
            shift(c)
    assert len(c['competition']['history']) == cc.HISTORY_MAX
    assert c['competition']['archive']['periods'] == 3
    assert cc.public({}, c, 'post_office')['period']['number'] == 28
    assert cc.public({}, c, 'post_office')['league'] == 4
    cc.validate(c, 'post_office')


def test_all_reward_caps_and_rank_requirements():
    c = career()
    with patch('game.promotion.rank', return_value=7):
        for league, periods in enumerate((2, 3, 4, 6, 1)):
            assert cc.public({}, c, 'post_office')['league'] == league
            for _ in range(periods):
                for _ in range(10):
                    result = shift(c, income=100000)
                assert result['bonus'] == cc.CAPS[league]


def test_accepted_unfinished_counts_zero_referral_neutral_and_no_case_unlock():
    c = career()
    job(c, status='in_progress')
    assert cc.close({}, c, 'post_office')['score'] == 0
    assert cc.public({}, c, 'post_office')['period']['worked_days'] == 1
    cc.validate(c, 'post_office')
    d = career()
    job(d, status='referred')
    assert cc.close({}, d, 'post_office')['period'] is None
    assert 'competition' not in d
    with patch('game.promotion.rank', return_value=3):
        with pytest.raises(Exception):
            cc.action({}, c, 'post_office', 'competition_start', {})


def test_case_answer_affects_teamwork_seed_is_validated_and_cannot_restart():
    scores = []
    for value in (0, 100):
        c = career()
        cc.completed(c, 'post_office', job(c), feedback(), 0)
        with patch('game.promotion.rank', return_value=0):
            with pytest.raises(Exception):
                cc.action({}, c, 'post_office', 'competition_start', {})
        with patch('game.promotion.rank', return_value=3):
            cc.action({}, c, 'post_office', 'competition_start', {})
            case = c['competition']['today']['case']
            raw = cc._scenario('post_office', c['day'], case['period'])
            opt = next(o['id'] for o in raw['options'] if o['score'] == value)
            cc.action({}, c, 'post_office', 'competition_answer', {'option': opt})
            scores.append(cc.close({}, c, 'post_office')['score'])
        cc.validate(c, 'post_office')
        bad = copy.deepcopy(c)
        bad['competition']['today']['case']['id'] = 'unknown'
        with pytest.raises(Exception):
            cc.validate(bad, 'post_office')
        c['day'] += 1
        with patch('game.promotion.rank', return_value=3):
            assert not cc.public({}, c, 'post_office')['case']['ready']
            with pytest.raises(Exception):
                cc.action({}, c, 'post_office', 'competition_start', {})
    assert scores[0] < scores[1]


@pytest.mark.parametrize('mutate', [
    lambda r: r.update(league=True),
    lambda r: r['days'][0].update(score=101),
    lambda r: r['days'][0]['npc'].__setitem__(0, 100),
    lambda r: r['today']['jobs'][0].update(income=-1),
    lambda r: r['today']['jobs'][0].update(id='foreign-0001-00'),
])
def test_validation_rejects_forged_current_and_period_data(mutate):
    c = career()
    shift(c)
    mutate(c['competition'])
    with pytest.raises(Exception):
        cc.validate(c, 'post_office')


def test_validation_rejects_forged_award_and_aggregate():
    c = career()
    for _ in range(10):
        shift(c)
    for field, value in (('bonus', 301), ('score', 99), ('authorized', False), ('rank', 4)):
        d = copy.deepcopy(c)
        d['competition']['history'][0][field] = value
        with pytest.raises(Exception):
            cc.validate(d, 'post_office')
