"""Scale catalogue contract and independent economic checks."""
import importlib
import importlib.util
import json
from collections import Counter
from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from game.content import CAREERS


def catalogue():
    assert importlib.util.find_spec('game.career_scale_content'), 'scale catalogue missing'
    return importlib.import_module('game.career_scale_content')


def test_catalogue_covers_all_58_careers_with_464_immutable_stages():
    c = catalogue()
    assert set(c.PROFILES) == set(CAREERS)
    assert Counter(p.kind for p in c.PROFILES.values()) == {'business': 34, 'agency': 23, 'community': 1}
    assert sum(len(p.stages) for p in c.PROFILES.values()) == 464   # + 📻 radio's eight
    for cid, p in c.PROFILES.items():
        assert c.profile(cid) is p
        assert [s.tier for s in p.stages] == list(range(1, 9))
        assert tuple(s.resources for s in p.stages) == (2, 4, 6, 10, 16, 24, 36, 50)
        assert tuple(s.sites for s in p.stages) == (1, 1, 1, 2, 3, 5, 8, 12)
        assert tuple(s.days for s in p.stages) == (2, 7, 14, 30, 60, 100, 160, 240)
        assert tuple(s.clean for s in p.stages) == (10, 30, 70, 140, 260, 450, 750, 1200)
        with pytest.raises(FrozenInstanceError):
            p.stages[0].fee = 1
        with pytest.raises(FrozenInstanceError):
            p.roles = ()
    with pytest.raises(TypeError):
        c.PROFILES['fake'] = c.profile('grocery')


def test_prices_and_group_counts_match_approved_design():
    c = catalogue()
    factors = {'retail': (8, 10), 'food': (8, 8), 'service': (8, 7),
               'technical': (2, 12), 'farm': (1, 12), 'hospitality': (1, 15),
               'professional': (3, 6), 'arts': (2, 8), 'logistics': (1, 12),
               'agency': (23, 0), 'community': (1, 0)}
    fees = (50_000, 250_000, 1_000_000, 4_000_000, 12_000_000, 35_000_000, 100_000_000, 250_000_000)
    targets = (1000, 3500, 12000, 35000, 90000, 200000, 420000, 800000)
    for group, (count, tenths) in factors.items():
        profiles = [p for p in c.PROFILES.values() if p.group == group]
        assert len(profiles) == count
        for p in profiles:
            assert tuple(s.fee for s in p.stages) == tuple(v * tenths // 10 for v in fees)
            assert tuple(s.net for s in p.stages) == tuple(v // 4 if group == 'agency' else v * tenths // 10 for v in targets)
    assert c.stage('grocery', 8).title == 'Hệ thống bán lẻ'
    assert sum(s.fee for s in c.profile('grocery').stages) == 402_300_000


def test_cost_ledger_matches_independent_model_at_three_demands():
    c = catalogue()
    rates = {'retail': (70, 8, 4, 2, 4), 'food': (55, 18, 8, 3, 4),
             'service': (35, 25, 12, 3, 4), 'technical': (50, 20, 10, 3, 4),
             'farm': (50, 18, 12, 4, 4), 'hospitality': (25, 30, 20, 3, 4),
             'professional': (20, 35, 12, 2, 4), 'arts': (40, 25, 12, 3, 4),
             'logistics': (55, 20, 10, 3, 4)}
    for p in c.PROFILES.values():
        for s in p.stages:
            for demand in (100, 80, 60):
                q = c.quote(p.cid, s.tier, demand)
                costs = sum(q[k] for k in ('materials', 'wages', 'premises', 'loss', 'tax'))
                assert q['revenue'] - costs == q['net']
                assert q['cost_total'] == costs
                assert q['wages'] == q['wage_variable'] + q['wage_fixed']
                assert all(type(q[k]) is int for k in ('revenue', 'materials', 'wages', 'premises', 'loss', 'tax', 'net'))
                if p.kind == 'business':
                    goods, wage, rent, loss, tax = rates[p.group]
                    full = Fraction(s.net * 100, 100 - sum(rates[p.group]))
                    d = Fraction(demand, 100)
                    expected = full * (d * (1 - Fraction(goods + loss + tax, 100) - Fraction(wage * 3, 500)) - Fraction(rent, 100) - Fraction(wage * 2, 500))
                    assert abs(q['net'] - expected) <= Fraction(1, 2)
                    assert abs(q['premises'] - full * rent / 100) < 2
                    assert abs(q['wage_fixed'] - full * wage * Fraction(2, 500)) < 2
                else:
                    assert costs == 0
                    assert q['net'] == s.net * demand // 100
                if demand == 100:
                    assert q['net'] == s.net
    assert [c.quote('grocery', 3, d)['net'] for d in (100, 80, 60)] == [12000, 8160, 4320]
    assert c.quote('grocery', 3)['cost_total'] == 88000


def test_authored_materials_roles_choices_and_evidence_are_career_specific():
    c = catalogue()
    scenarios = set()
    for p in c.PROFILES.values():
        assert len(p.roles) >= 2
        assert p.resource_name
        assert p.materials
        for m in p.materials:
            assert all((m.code, m.name, m.unit, m.bundle, m.quality))
            assert len(m.bundle) > 20
            assert len(m.quality) > 15
        case = p.scenario
        assert case.title not in scenarios
        scenarios.add(case.title)
        assert len(case.evidence) >= 4
        for phase in ('planning', 'allocation', 'exception', 'acceptance'):
            choices = getattr(case, phase)
            assert len(choices) >= 2
            assert len({o.id for o in choices}) == len(choices)
            assert len({o.label for o in choices}) == len(choices)
            assert all(o.evidence and o.label for o in choices)
    assert 'COD' in str(c.profile('delivery').scenario)
    assert 'chu kỳ' in str(c.profile('laundry').scenario)
    assert 'xung đột' in str(c.profile('lawyer').scenario)
    assert 'riêng tư' in str(c.profile('pagoda').scenario)


def test_json_helpers_are_detached_and_validate_inputs():
    c = catalogue()
    dto = c.profile_dict('grocery')
    assert json.loads(json.dumps(dto, ensure_ascii=False))['stages'][0]['fee'] == 50000
    dto['stages'][0]['fee'] = 0
    assert c.stage('grocery', 1).fee == 50000
    assert c.stage_dict('grocery', 3)['resources'] == 6
    for tier in (0, 9, -1, True, 1.5, '1'):
        with pytest.raises(ValueError):
            c.stage('grocery', tier)
    for demand in (-1, 101, True, 60.5, '80'):
        with pytest.raises(ValueError):
            c.quote('grocery', 1, demand)
    with pytest.raises(KeyError):
        c.profile('missing')
    assert c.quote('pagoda', 8)['net'] == 0
    assert c.quote('grocery', 1, 0)['net'] < 0


def test_public_dto_hides_scores_and_evidence_until_resolution():
    c = catalogue()
    for cid in c.PROFILES:
        public = c.profile_dict(cid)
        assert 'evidence' not in public['scenario']
        for phase in ('planning', 'allocation', 'exception', 'acceptance'):
            for choice in public['scenario'][phase]:
                assert set(choice) == {'id', 'label'}


def test_procurement_keeps_fixed_unit_prices_and_physical_leftovers():
    c = catalogue()
    for p in c.PROFILES.values():
        m = p.materials[0]
        assert m.unit_cost > 0
        assert m.batch_units > 0
        for tier in (1, 8):
            q = c.quote(p.cid, tier)
            line = q['material_plan'][0]
            assert line['unit_cost'] == m.unit_cost
            assert line['purchased_units'] == line['quantity'] * m.batch_units
            assert line['purchased_units'] == line['consumed_units'] + line['remaining_units']
            assert line['purchase_cost'] == line['purchased_units'] * m.unit_cost
            assert line['consumed_cost'] == line['consumed_units'] * m.unit_cost
            assert line['carry_value'] == line['remaining_units'] * m.unit_cost
            assert line['purchase_cost'] == line['consumed_cost'] + line['carry_value']
            if p.kind == 'business':
                assert line['consumed_cost'] == q['materials']
                assert line['funded_by'] == 'business'
            else:
                assert q['materials'] == 0
                assert line['funded_by'] in ('organization', 'community')
