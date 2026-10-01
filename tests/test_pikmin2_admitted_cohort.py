"""Canonical admitted-cohort placement (merged line).

Reconciled 2026-09-15 after the wave's lane-04 accepted-placement document and
the generated-placement bridge landed: the admitted cohort (23,44,59-62) now has
a committed accepted placement document, so the product seeds the whole cohort
instead of failing closed. The fail-closed guarantee is retained below as the
no-acceptance case.
"""
import json
from pathlib import Path

import pytest

from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate
from randomizer.p2_placement import audit, normalize_profile
from randomizer.seed import generate

PLACEMENT = Path(__file__).resolve().parents[1] / 'docs/PIKMIN2_ADMITTED_PLACEMENT.json'
IDENTITIES = {'Sarai', 'BlueKochappy', 'Miulin', 'Kurage', 'FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara', 'MiniHoudai', 'Kogane', 'Sokkuri'}


def document():
    return json.loads(PLACEMENT.read_text(encoding='utf-8'))


def test_reviewed_pairs_only():
    admitted = audit(document())['admitted']
    assert set(admitted) == IDENTITIES
    assert all(admitted[name] for name in admitted)


@pytest.mark.parametrize('seed', ['cohort-a', 'cohort-b', 'cohort-c', 'cohort-d'])
def test_product_generation_seeds_the_admitted_cohort(seed):
    assert admitted_ids(load_and_validate()) == [9, 23, 44, 54, 57, 59, 60, 61, 62, 78, 79]
    manifest = generate(seed, p2_enemies=True, p2_placement=document())
    bound = {binding['source_id'] for binding in manifest['p2_layout']['bindings']}
    assert bound == {9, 23, 44, 54, 57, 59, 60, 61, 62, 78, 79}


def test_p2_enemies_defaults_to_the_committed_document():
    """The p2_enemies option places the admitted cohort with no explicit document."""
    default = generate('admitted-default', p2_enemies=True)
    explicit = generate('admitted-default', p2_enemies=True, p2_placement=document())
    assert default['p2_layout'] == explicit['p2_layout']
    bound = {binding['source_id'] for binding in default['p2_layout']['bindings']}
    assert bound == {9, 23, 44, 54, 57, 59, 60, 61, 62, 78, 79}


def test_lost_accepted_slot_fails_closed():
    doc = document()
    for profile in doc['profiles']:
        if profile['identity'] in IDENTITIES:
            profile['accepted_slot_uids'] = []
    with pytest.raises(ValueError):
        generate('missing-slot', p2_enemies=True, p2_placement=doc)


def test_explicit_empty_approval_denies_identity():
    doc = document()
    target = next(profile for profile in doc['profiles'] if profile['identity'] == 'Sarai')
    target['accepted_slot_uids'] = []
    assert audit(doc)['admitted'].get('Sarai', []) == []


@pytest.mark.parametrize('uids', [None, '1', [True], [1, 1], [1.5], [{}]])
def test_invalid_pair_approval_rejected(uids):
    with pytest.raises(ValueError, match='accepted_slot_uids'):
        normalize_profile({'identity': 'BlueKochappy', 'terrains': ['ground'],
                           'accepted_slot_uids': uids})

