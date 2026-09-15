"""Lane-04 admitted-cohort placement: catalog recognition and accepted binding.

Regression guard for the gap exposed by the Sarai (23) / Otakara (59-62)
admissions: `binding_targets_for_sources` used to reject any admitted source
absent from `CANDIDATE_SPECS` ("source id N is not a non-boss lane-04
candidate"), so a real-ledger product seed failed before placement was even
evaluated. These tests pin:

- every admitted source is now a recognised lane-04 candidate,
- the default-deny catalog still fails closed, but with the honest placement
  reason (not a catalog membership error),
- a document carrying accepted evidence + accepted slot ids seeds the whole
  admitted cohort through the real ledger (`generate`, no admission injection).
"""
import json
import os
from pathlib import Path

import pytest

from randomizer import p2_placement
from randomizer import p2_placement_catalog as catalog
from randomizer.seed import generate
from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate
from experimental.pikmin2_seed_bridge import SeedBridgeError, resolve_placement_layout

ADMITTED_PLACEMENT_DOC = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "docs/PIKMIN2_ADMITTED_PLACEMENT.json"

IDENTITY_BY_SOURCE = {
    23: 'Sarai',
    44: 'BlueKochappy',
    59: 'FireOtakara',
    60: 'WaterOtakara',
    61: 'GasOtakara',
    62: 'ElecOtakara',
}


def admitted_set():
    roster = load_and_validate()
    admitted = admitted_ids(roster)
    assert admitted == [23, 44, 59, 60, 61, 62]
    return roster, admitted


def accepted_document():
    """The real catalog with accepted evidence stamped for the admitted cohort.

    Labelled test-fixture acceptance: it does not claim a native run accepted the
    slots, only that the accepted-placement mechanism binds the admitted cohort.
    """
    document = json.loads(json.dumps(catalog.build_document()))
    ground = [slot for slot in document['slots'] if slot['terrain'] == 'ground']
    assert ground
    uids = sorted(slot['uid'] for slot in ground)
    for slot in ground:
        slot.setdefault('evidence', {})
        for key in p2_placement.EVIDENCE_KEYS:
            slot['evidence'][key] = True
    names = set(IDENTITY_BY_SOURCE.values())
    for profile in document['profiles']:
        if profile['identity'] in names:
            profile['accepted_gates'] = ['test-fixture']
            profile['accepted_slot_uids'] = list(uids)
    return p2_placement.validate_document(document)


def test_catalog_recognizes_every_admitted_source():
    _, admitted = admitted_set()
    # No "not a non-boss lane-04 candidate" membership error any more.
    targets = catalog.binding_targets_for_sources(admitted)
    assert targets


def test_default_deny_document_fails_closed_with_honest_reason():
    roster, _ = admitted_set()
    with pytest.raises(SeedBridgeError) as exc:
        resolve_placement_layout('lane04-deny', 'Player1', catalog.build_document(), roster)
    message = str(exc.value)
    assert 'accepted placement evidence' in message
    assert 'not a non-boss lane-04 candidate' not in message


def test_accepted_slot_uids_restrict_a_profile():
    document = accepted_document()
    profile = next(p for p in document['profiles'] if p['identity'] == 'Sarai')
    inside = next(s for s in document['slots'] if s['terrain'] == 'ground')
    assert p2_placement.evaluate(inside, profile)['status'] == 'legal'
    outside = dict(inside)
    outside['uid'] = 999_999_999
    verdict = p2_placement.evaluate(outside, profile)
    assert verdict['status'] == 'denied'
    assert any('accepted placement evidence for this identity' in r for r in verdict['reasons'])


def test_accepted_document_seeds_the_whole_admitted_cohort():
    _, admitted = admitted_set()
    document = accepted_document()
    result = generate('lane04-admitted', p2_enemies=True, p2_placement=document)
    bound = {binding['source_id'] for binding in result['p2_layout']['bindings']}
    assert set(admitted) <= bound


def test_committed_admitted_placement_seeds_the_whole_cohort():
    _, admitted = admitted_set()
    document = json.loads(ADMITTED_PLACEMENT_DOC.read_text(encoding="utf-8"))
    assert document["schema"] == p2_placement.SCHEMA
    result = generate('lane04-committed', p2_enemies=True, p2_placement=document)
    bound = {binding['source_id'] for binding in result['p2_layout']['bindings']}
    assert bound == set(admitted)
