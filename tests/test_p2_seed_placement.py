"""Lane-04 slice 3 tests: the placement catalog driving a real generated seed.

These tests prove, without a native root, the three slice-3 claims plus the
fold-in fixes, all via the real ``randomizer.seed.generate`` path:

1. the slot the native ``P2_PLACEMENT_SLOT`` marker joins to (through the
   generator->slot sidecar) equals the slot the seed's ``p2_layout`` bound to the
   admitted identity;
2. the audit's stage guard fires from the probe's ``arena_stage`` field without a
   manual ``--stage``;
3. two different seeds bind the admitted identity to different catalog slots, so
   consecutive runs emit different markers.

The Snow/Dwarf Orange cohort's acceptance is injected (the committed ledger and
catalog are deny-by-default); this is the bridge-shaping that lane 02/03 fixture
tests already use, labelled clearly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import experimental.pikmin2_seed_placement as placement
import randomizer.p2_placement_probe as probe
from randomizer import p2_placement_catalog
from scripts import audit_p2_placement_evidence as auditplugin
from scripts.run_p2_catalog_placement import choose_slot


def _marker(generator, slot_uid, xyz=1, terrain='ground', route=1):
    return (
        f'P2_PLACEMENT_SLOT generator={generator} slot={slot_uid} actor=3 xyz={xyz} '
        f'terrain={terrain} route={route} route_distance=61.2 '
        f'x=-150.0 y=30.0 z=1850.0 water_depth=0.00\n'
    )


def _document():
    return placement.placement_document()


def test_seed_slot_equals_binding_target():
    """(1) The marker's `slot` equals the slot the seed placed in its layout."""
    document = _document()
    manifest = placement.generate_admitted_seed('seed-slice3-proof1', document)
    uid = placement.seed_slot_uid(manifest, placement.BLUEKOCHAPPY_SOURCE)
    assert uid is not None
    document_uids = {slot['uid'] for slot in document['slots']}
    assert uid in document_uids

    # The runtime writes the generator -> seed-chosen-slot sidecar, whose value
    # the native probe reads back into the marker. Simulate that round trip.
    text = _marker(placement.ARENA_SOURCE_GENERATOR, uid)
    doc = probe.build_probe(text)
    assert doc['catalog_join'] is True
    assert doc['mapping'][0]['slot'] == uid
    assert doc['mapping'][0]['generator'] == placement.ARENA_SOURCE_GENERATOR
    assert doc['unmapped_generators'] == []


def test_stage_guard_passes_without_manual_stage(tmp_path):
    """(2) run_audit guards stage from the probe's arena_stage, no --stage."""
    document = _document()
    manifest = placement.generate_admitted_seed('seed-slice3-proof2', document)
    uid = placement.seed_slot_uid(manifest, placement.BLUEKOCHAPPY_SOURCE)

    probe_doc = probe.build_probe(_marker(placement.ARENA_SOURCE_GENERATOR, uid))
    probe_doc['arena_stage'] = placement.ARENA_STAGE
    catalog_doc = p2_placement_catalog.build_document()

    # No explicit arena_stage argument: the guard is satisfied from the probe.
    report = auditplugin.run_audit(probe_doc, catalog_doc=catalog_doc)
    assert report['catalog_join'] is True
    assert report['arena_stage'] == placement.ARENA_STAGE
    assert uid in report['matched_slot_uids']

    # A wrong recorded stage still hard-fails (the guard is live, not skipped).
    wrong = dict(probe_doc, arena_stage=3)
    with pytest.raises(SystemExit):
        auditplugin.run_audit(wrong, catalog_doc=catalog_doc)


def test_two_seeds_pick_different_slots():
    """(3) Consecutive seeds bind the identity to different catalog slots."""
    document = _document()
    uids = {}
    for seed_name in ('seed-slice3-a', 'seed-slice3-b', 'seed-slice3-c',
                      'seed-slice3-d', 'seed-slice3-e'):
        manifest = placement.generate_admitted_seed(seed_name, document)
        uids[seed_name] = placement.seed_slot_uid(manifest, placement.BLUEKOCHAPPY_SOURCE)
    distinct = {uids[name] for name in uids}
    assert len(distinct) >= 2
    # Two concrete seeds that demonstrably disagree.
    differing = [name for name in uids if uids[name] != uids['seed-slice3-a']]
    assert differing, uids


def test_slot_uid_is_deterministic_per_seed():
    """The same seed name always resolves BlueKochappy to the same slot."""
    document = _document()
    first = placement.seed_slot_uid(
        placement.generate_admitted_seed('seed-slice3-det', document), 44)
    second = placement.seed_slot_uid(
        placement.generate_admitted_seed('seed-slice3-det', document), 44)
    assert first == second


def test_malformed_markers_are_counted():
    """Fold-in: malformed P2_PLACEMENT_SLOT lines are counted, not silently dropped."""
    text = (
        _marker(placement.ARENA_SOURCE_GENERATOR, 513430982)
        + 'P2_PLACEMENT_SLOT generator=broken slot=1 actor=3 xyz=1 terrain=ground '
        'route=1 route_distance=1.0 water_depth=0.00\n'
        + 'P2_PLACEMENT_SLOT generator=1 xyz=1 terrain=ground route=1\n'
    )
    doc = probe.build_probe(text)
    assert doc['malformed_markers'] == 2
    assert doc['catalog_join'] is True
    assert doc['mapping'][0]['slot'] == 513430982


def test_choose_slot_picks_stage_matching_ground_cohort():
    """Fold-in: choose_slot selects a stage-matched ground-cohort ground slot."""
    catalog_doc = p2_placement_catalog.build_document()
    chosen = choose_slot(catalog_doc, stage=0)
    assert chosen['stage'] == 0
    assert chosen['terrain'] == 'ground'
    assert chosen['cohort'] == 'ground'
    assert chosen['uid'] in {slot['uid'] for slot in catalog_doc['slots']}


def test_zero_slots_chooses_nothing():
    """choose_slot raises when no slot matches the requested stage/terrain."""
    catalog_doc = p2_placement_catalog.build_document()
    with pytest.raises(SystemExit):
        choose_slot({'slots': []}, stage=0)
