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
from randomizer.seed import generate, PLAYABLE_P2_SPECIES
from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate
from experimental.pikmin2_seed_bridge import SeedBridgeError, resolve_placement_layout

ADMITTED_PLACEMENT_DOC = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "docs/PIKMIN2_ADMITTED_PLACEMENT.json"

def admitted_set():
    roster = load_and_validate()
    admitted = admitted_ids(roster)
    assert admitted == sorted(PLAYABLE_P2_SPECIES)
    return roster, admitted


def accepted_document():
    """Current generated constraint profiles, including bosses and water species."""
    from randomizer.p2_admitted_placement import build_admitted_document
    return build_admitted_document()



def test_catalog_recognizes_every_admitted_source():
    _, admitted = admitted_set()
    # No "not a non-boss lane-04 candidate" membership error any more.
    identities = catalog.identities_for_sources(admitted, accepted_document())
    assert len(identities) == len(admitted)


def test_default_deny_document_fails_closed_with_honest_reason():
    roster, _ = admitted_set()
    document = accepted_document()
    for profile in document['profiles']:
        profile['accepted_gates'] = []
        profile['accepted_slot_uids'] = []
    with pytest.raises(SeedBridgeError) as exc:
        resolve_placement_layout('lane04-deny', 'Player1', document, roster)
    message = str(exc.value)
    assert 'accepted placement evidence' in message
    assert 'not a non-boss lane-04 candidate' not in message


def test_accepted_slot_uids_restrict_a_profile():
    document = accepted_document()
    profile = next(p for p in document['profiles'] if p['identity'] == 'Chappy')
    inside = next(s for s in document['slots'] if s['uid'] in profile['accepted_slot_uids'])
    assert p2_placement.evaluate(inside, profile)['status'] == 'legal'
    outside = dict(inside)
    outside['uid'] = 999_999_999
    verdict = p2_placement.evaluate(outside, profile)
    assert verdict['status'] == 'denied'
    assert any('not in the accepted slot list' in r for r in verdict['reasons'])


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
