"""Lane-04 slice 4 tests: every binding (full set), not one, plus the audit guards.

Proves, without a native root, the slice-4 corrections over
``randomizer.seed.generate``:

1. the seed bridge binds a *set* of stage-0 ground slots per admitted source, the
   ``p2-placement-slots.txt`` sidecar carries that whole set, and the marker-slot
   set parsed back from the log equals the binding set (not membership of one);
2. the catalog-join stage rejection lives inside ``run_audit`` (no stage anywhere
   is a hard failure, even with no ``--stage``);
3. two different seeds bind the admitted source to different slot sets.

The Snow/Dwarf Orange cohort's acceptance is injected (the committed ledger and
catalog are deny-by-default); this is the bridge-shaping the lane 02/03 fixture
tests already use, labelled clearly here.
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


def _marker(generator, slot_uid):
    return (
        f'P2_PLACEMENT_SLOT generator={generator} slot={slot_uid} actor=3 xyz=1 '
        f'terrain=ground route=1 route_distance=61.2 '
        f'x=-150.0 y=30.0 z=1850.0 water_depth=0.00\n'
    )


def _document():
    return placement.placement_document()


def _seed_slots(seed_name):
    manifest = placement.generate_admitted_seed(seed_name, _document())
    return placement.seed_slots(manifest, placement.BLUEKOCHAPPY_SOURCE)


# --- (1) every binding, not one -------------------------------------------------

def test_seed_binding_set_is_a_distinct_set_of_catalog_slots():
    slots = _seed_slots('seed-slice4-a')
    assert slots
    doc_uids = {slot['uid'] for slot in _document()['slots']}
    assert set(slots) <= doc_uids
    assert len(slots) == len(set(slots))  # every slot appears once, not a re-pick


def test_seed_slot_uids_returns_full_set_per_source():
    manifest = placement.generate_admitted_seed('seed-slice4-a', _document())
    by_source = placement.seed_slot_uids(manifest)
    assert placement.BLUEKOCHAPPY_SOURCE in by_source
    assert placement.YELLOWKOCHAPPY_SOURCE in by_source
    # The two sources jointly bind the whole stage-0 ground slot set.
    combined = sorted(by_source[placement.BLUEKOCHAPPY_SOURCE]
                      + by_source[placement.YELLOWKOCHAPPY_SOURCE])
    assert combined == sorted({slot['uid'] for slot in _document()['slots']})


def test_full_set_sidecar_round_trips(tmp_path):
    slots = _seed_slots('seed-slice4-a')
    pairs = [(211000 + index, uid) for index, uid in enumerate(slots)]
    path = placement.write_sidecar(tmp_path, pairs)
    lines = path.read_text().splitlines()
    assert lines[0] == placement.SIDECAR_HEADER
    assert len(lines) - 1 == len(slots)
    assert {(int(line.split()[1])) for line in lines[1:]} == set(slots)


def test_marker_slot_set_equals_binding_set():
    """The set of marker slots equals the seed's binding set for the source."""
    slots = _seed_slots('seed-slice4-a')
    pairs = [(211000 + index, uid) for index, uid in enumerate(slots)]
    text = ''.join(_marker(generator, uid) for generator, uid in pairs)
    doc = probe.build_probe(text)
    assert doc['catalog_join'] is True
    assert {mapping['slot'] for mapping in doc['mapping']} == set(slots)
    assert doc['unmapped_generators'] == []


# --- (2) stage guard now lives in run_audit -------------------------------------

def test_run_audit_rejects_catalog_join_without_any_stage():
    slots = _seed_slots('seed-slice4-a')
    doc = probe.build_probe(_marker(211001, slots[0]))
    assert doc['catalog_join'] is True
    assert 'arena_stage' not in doc
    with pytest.raises(SystemExit):
        auditplugin.run_audit(doc, catalog_doc=p2_placement_catalog.build_document())


def test_run_audit_rejects_wrong_recorded_stage():
    slots = _seed_slots('seed-slice4-a')
    doc = probe.build_probe(_marker(211001, slots[0]))
    doc['arena_stage'] = 3  # not the arena's stage-0
    with pytest.raises(SystemExit):
        auditplugin.run_audit(doc, catalog_doc=p2_placement_catalog.build_document())


def test_run_audit_stage_guard_from_probe_passes():
    slots = _seed_slots('seed-slice4-a')
    doc = probe.build_probe(_marker(211001, slots[0]))
    doc['arena_stage'] = placement.ARENA_STAGE
    report = auditplugin.run_audit(doc, catalog_doc=p2_placement_catalog.build_document())
    assert report['catalog_join'] is True
    assert report['arena_stage'] == placement.ARENA_STAGE
    assert slots[0] in report['matched_slot_uids']


# --- (3) two seeds bind different sets ------------------------------------------

def test_two_seeds_bind_different_slot_sets():
    assert _seed_slots('seed-slice4-a') != _seed_slots('seed-slice4-b')


def test_slot_set_is_deterministic_per_seed():
    assert _seed_slots('seed-slice4-det') == _seed_slots('seed-slice4-det')


# --- fold-ins -------------------------------------------------------------------

def test_malformed_markers_are_counted():
    text = (
        _marker(211001, 513430982)
        + 'P2_PLACEMENT_SLOT generator=broken slot=1 actor=3 xyz=1 terrain=ground '
        'route=1 route_distance=1.0 water_depth=0.00\n'
        + 'P2_PLACEMENT_SLOT generator=1 xyz=1 terrain=ground route=1\n'
    )
    assert probe.build_probe(text)['malformed_markers'] == 2


def test_choose_slot_picks_stage_matching_ground_cohort():
    chosen = choose_slot(p2_placement_catalog.build_document(), stage=0)
    assert chosen['stage'] == 0
    assert chosen['terrain'] == 'ground'
    assert chosen['cohort'] == 'ground'


def test_zero_slots_chooses_nothing():
    with pytest.raises(SystemExit):
        choose_slot({'slots': []}, stage=0)
