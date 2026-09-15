import json
from pathlib import Path

import pytest

from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate
from randomizer.p2_placement import audit, normalize_profile
from randomizer.seed import generate, validate

PLACEMENT = Path(__file__).resolve().parents[1] / 'docs/PIKMIN2_ADMITTED_PLACEMENT.json'


def document():
    return json.loads(PLACEMENT.read_text(encoding='utf-8'))


def test_reviewed_pairs_only():
    assert audit(document())['admitted'] == {
        'BlueKochappy': [1849273021], 'YellowKochappy': [2049888785]}


@pytest.mark.parametrize('seed', ['cohort-a', 'cohort-b', 'cohort-c', 'cohort-d'])
def test_product_generation_fails_closed_without_accepted_placement(monkeypatch, seed):
    # Directive 008 canonical set is [23,44,59,60,61,62]; directive 009/010 residual:
    # there is no accepted placement evidence for 23/59-62 yet, so a real-ledger
    # product generate must fail closed (the honest state) rather than fabricate it.
    monkeypatch.delenv('PIKMIN_P2_CANDIDATE_SCOPE', raising=False)
    monkeypatch.setenv('PIKMIN_P2_ADMITTED_IDS', '79')
    assert admitted_ids(load_and_validate()) == [23, 44, 59, 60, 61, 62]
    with pytest.raises(Exception, match='placement catalog rejected|admitted cohort'):
        generate(seed, p2_enemies=True, p2_placement=document())
    assert 'p2_layout' not in generate(seed)


def test_lost_second_slot_still_fails_closed():
    doc = document()
    doc['slots'] = [s for s in doc['slots'] if s['uid'] == 1849273021]
    with pytest.raises(ValueError, match='placement catalog rejected|accepted placement'):
        generate('missing-slot', p2_enemies=True, p2_placement=doc)


def test_explicit_empty_pair_approval_denies_all():
    doc = document()
    doc['profiles'][0]['accepted_slot_uids'] = []
    assert audit(doc)['admitted'].get(doc['profiles'][0]['identity'], []) == []


@pytest.mark.parametrize('uids', [None, '1', [True], [1, 1], [1.5], [{}]])
def test_invalid_pair_approval_rejected(uids):
    with pytest.raises(ValueError, match='accepted_slot_uids'):
        normalize_profile({'identity': 'BlueKochappy', 'terrains': ['ground'],
                           'accepted_slot_uids': uids})
