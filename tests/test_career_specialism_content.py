"""Contract and editorial regression checks for the authored specialism catalogue."""
import re
from pathlib import Path

import pytest

from game import career_specialism_content as content


def approved_titles():
    text = (Path(__file__).parents[1] / 'docs/superpowers/specs/2026-10-13-career-content-catalog.md').read_text(encoding='utf-8')
    return {cid: re.findall(r'^\d+\. (.+)$', body, re.M)
            for cid, body in re.findall(r'^## \d+\..+?\(`([^`]+)`\)\n(.*?)(?=^## |\Z)', text, re.M | re.S)}


def test_exact_approved_540_titles_and_real_procedure_diversity():
    expected = approved_titles()
    assert len(expected) == 54
    assert set(content.CAREER_IDS) == set(expected)
    all_procedures, all_checks = set(), set()
    for cid, titles in expected.items():
        items = content.packs(cid)
        assert [p['title'] for p in items] == titles
        assert [p['tier'] for p in items] == list(range(1, 11))
        for p in items:
            assert set(p) == {'tier', 'title', 'output_unit', 'inputs', 'procedure', 'check'}
            assert 1 <= len(p['inputs']) <= 2
            for material in p['inputs']:
                assert set(material) == {'name', 'unit', 'quantity', 'unit_cost'}
                assert type(material['quantity']) is int and material['quantity'] > 0
                assert type(material['unit_cost']) is int and material['unit_cost'] > 0
            assert len(p['procedure']) == len(set(p['procedure'])) == 3
            assert all(len(s) >= 15 for s in p['procedure'])
            assert p['check']['good'] != p['check']['bad']
            assert p['title'] not in ' '.join(p['procedure'])
            all_procedures.add(tuple(p['procedure']))
            all_checks.add((p['check']['good'], p['check']['bad']))
    assert len(all_procedures) == len(all_checks) == 540


def test_callers_cannot_mutate_catalogue():
    original = content.pack('clothing', 1)
    listing = content.packs('clothing')
    listing[0]['inputs'][0]['quantity'] = 999
    listing[0]['procedure'].append('changed')
    listing[0]['check']['good'] = 'changed'
    other = content.pack('clothing', 1)
    other['inputs'].clear()
    assert content.pack('clothing', 1) == original


@pytest.mark.parametrize('tier', [True, False, 0, 11, -1, 1.0, '1', None])
def test_invalid_tier_is_rejected(tier):
    with pytest.raises((ValueError, TypeError)):
        content.pack('clothing', tier)


def test_unknown_career_is_rejected():
    with pytest.raises(KeyError):
        content.packs('unknown')


@pytest.mark.parametrize('mutation', [
    lambda p: p['inputs'][0].update(quantity=True),
    lambda p: p['inputs'][0].update(unit_cost=0),
    lambda p: p.update(procedure=['a'] * 3),
    lambda p: p['check'].update(bad=p['check']['good']),
    lambda p: p.update(extra='not permitted'),
    lambda p: p.update(title='Changed approved title'),
    lambda p: p['inputs'][0].update(quantity=100000, unit_cost=100000),
])
def test_strict_validation_rejects_corrupt_packs(mutation):
    catalogue = {cid: content.packs(cid) for cid in content.CAREER_IDS}
    mutation(catalogue['clothing'][0])
    with pytest.raises(ValueError):
        content.validate_catalogue(catalogue)


def test_apparel_and_food_have_physical_inputs():
    assert 'lụa' in content.pack('clothing', 1)['inputs'][0]['name'].lower()
    assert 'số đo' in ' '.join(content.pack('clothing', 1)['procedure'])
    for cid in ('milk_tea', 'restaurant', 'cafe_bakery', 'tra_da', 'ice_cream', 'pho', 'com', 'naucom'):
        assert all(len(p['inputs']) == 2 for p in content.packs(cid))
        assert all('hồ sơ' not in m['name'].lower() for p in content.packs(cid) for m in p['inputs'])


def test_registry_must_be_complete_and_no_extra_careers():
    catalogue = {cid: content.packs(cid) for cid in content.CAREER_IDS}
    del catalogue['clothing']
    with pytest.raises(ValueError):
        content.validate_catalogue(catalogue)
    catalogue['not_a_career'] = content.packs('clothing')
    with pytest.raises(ValueError):
        content.validate_catalogue(catalogue)


def test_private_storage_is_recursively_frozen():
    with pytest.raises(TypeError):
        content._CATALOGUE['clothing'][0]['inputs'][0]['quantity'] = 2


def test_runtime_rejects_missing_packaged_shard(monkeypatch):
    monkeypatch.setattr(content, '_FILES', content._FILES + ('missing-required-shard.json',))
    with pytest.raises(FileNotFoundError):
        content._load()


def test_json_duplicate_keys_are_not_silently_overwritten():
    with pytest.raises(ValueError):
        content._unique_object([('tier', 1), ('tier', 2)])
