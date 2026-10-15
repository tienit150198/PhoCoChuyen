"""NPC competition through real commands, public projection and reward accounting."""
import copy
import json
from unittest.mock import patch

import pytest
from game import engine as E, journey as JR, x3_week
from tests.helpers import Journey
from tests.test_career_laundry import solve


def test_all_careers_publish_competition_without_mutating_old_save():
    s = E.new_state()
    before = copy.deepcopy(s)
    assert len(s['careers']) == 55
    for cid in s['careers']:
        view = E.public_state(s, full=cid)['careers'][cid]['competition']
        assert len(view['standings']) == 4
        assert view['period']['worked_days'] == 0
    assert s == before


def test_real_service_records_work_and_close_once():
    j = Journey('laundry')
    solve(j, j.task['id'])
    view = E.public_state(j.state)['careers']['laundry']['competition']
    assert view['today']['completed'] == 1
    assert view['today']['score'] > 0
    j.act('end_day', carry_event=True)
    assert E.public_state(j.state)['careers']['laundry']['competition']['period']['worked_days'] == 1
    before = copy.deepcopy(j.state)
    with pytest.raises(E.GameError):
        j.act('end_day', carry_event=True)
    assert j.state == before
    E.validate_state(json.loads(json.dumps(j.state)))
    assert 'competition' not in E.public_state(j.state, full='mother_baby')['careers']['laundry']


def test_case_commands_no_tick_hidden_answers_and_persistent_result():
    j = Journey('laundry')
    solve(j, j.task['id'])
    with patch('game.promotion.rank', return_value=3):
        turn = j.c['turn']
        j.act('competition_start')
        view = E.public_state(j.state)['careers']['laundry']['competition']['case']['active']
        assert all(set(o) == {'id', 'label'} for o in view['options'])
        j.act('competition_answer', option=view['options'][0]['id'])
        assert j.c['turn'] == turn
        before = copy.deepcopy(j.state)
        with pytest.raises(E.GameError):
            j.act('competition_answer', option=view['options'][1]['id'])
        assert j.state == before
        restored = E.migrate_state(json.loads(json.dumps(j.state)))
        assert E.public_state(restored)['careers']['laundry']['competition']['case']['result']


def test_completion_budget_only_base_income_on_paid_days():
    from game import career_competition as cc
    j = Journey('laundry')
    expected_base = j.task['needs']['net']
    with patch.object(cc, 'completed', wraps=cc.completed) as hook:
        solve(j, j.task['id'])
        assert hook.call_count == 1
        assert hook.call_args.kwargs['income'] == expected_base
    j = Journey('laundry')
    with patch('game.interest_clock.day_paid', return_value=False), patch.object(cc, 'completed', wraps=cc.completed) as hook:
        solve(j, j.task['id'])
        assert hook.call_args.kwargs['income'] == 0


def test_competition_award_is_not_multiplied_by_weekly_x3():
    s = E.new_state(); JR.enable_story(s, 4242)
    s['journey'].update(gender='female', intro=True)
    res = {'summary': {'net': 346, 'job': {}, 'mastery': {'bonus': 6}, 'competition': {'bonus': 300}}}
    with patch.object(x3_week, 'on', return_value=True):
        JR._end_of_day(s, 'grocery', res)
    rows = [r['amount'] for r in s['journey']['history'] if r['label'].startswith('🔥')]
    assert rows == [80]


def test_ten_real_shifts_pay_one_bounded_award_and_survive_reload():
    j = Journey('laundry')
    for day in range(10):
        for task in list(j.c['tasks']):
            if task['day'] == j.c['day'] and task['status'] not in ('completed', 'cancelled', 'referred'):
                solve(j, task['id'])
        result = j.act('end_day', carry_event=True)['summary']['competition']
        if day < 9:
            assert result['bonus'] == 0
            j.act('start_day')
    assert 0 < result['bonus'] <= 300
    rows = [r for r in j.c['ops']['finance']['ledger'] if str(r.get('ref', '')).startswith('competition-')]
    assert len(rows) == 1
    assert rows[0]['amount'] == result['bonus']
    restored = E.migrate_state(json.loads(json.dumps(j.state)))
    E.validate_state(restored)
    view = E.public_state(restored)['careers']['laundry']['competition']
    assert view['last_result']['bonus'] == result['bonus']
    assert view['period']['worked_days'] == 0


@pytest.mark.parametrize('spirit', [99, 100])
def test_pagoda_spirit_ceiling_matches_public_receipt(spirit):
    from tests.test_career_competition import career, shift
    from tests.test_career_pagoda import Base
    c = career()
    for _ in range(9):
        shift(c, cid='pagoda')
    j = Journey('pagoda', day=10, slot=1)
    j.c['competition'] = copy.deepcopy(c['competition'])
    j.c['metrics']['served'] = c['metrics']['served']
    Base().best(j, j.task['id'])
    j.state['journey']['life']['spirit'] = spirit
    result = j.act('end_day', carry_event=True)['summary']['competition']
    gained = j.state['journey']['life']['spirit'] - spirit
    assert gained == 100 - spirit
    assert result['bonus'] == 0
    assert result['spirit'] == result['period']['spirit'] == gained
    assert E.public_state(j.state)['careers']['pagoda']['competition']['last_result']['spirit'] == gained
    E.validate_state(json.loads(json.dumps(j.state)))


def test_unpaid_tenth_shift_has_no_award_ledger_or_later_replay():
    from tests.test_career_competition import career, shift
    c = career()
    for _ in range(9):
        shift(c, cid='laundry')
    j = Journey('laundry', day=10, slot=1)
    j.c['competition'] = copy.deepcopy(c['competition'])
    j.c['metrics']['served'] = c['metrics']['served']
    solve(j, j.task['id'])
    with patch('game.interest_clock.day_paid', return_value=False):
        result = j.act('end_day', carry_event=True)['summary']['competition']
    assert result['period']['good']
    assert result['bonus'] == 0
    j.act('start_day')
    assert j.act('end_day', carry_event=True)['summary']['competition']['bonus'] == 0
    assert not [r for r in j.c['ops']['finance']['ledger'] if str(r.get('ref', '')).startswith('competition-')]
