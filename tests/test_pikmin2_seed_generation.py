"""Admission-gated P2 seed generation wiring (lane 03, #439).

The real lane 02 roster admits Orange and Snow; these tests also inject a minimal
admitted cohort (Sokkuri=79) and a minimal lane 04 placement document to exercise
the product path, and separately prove the default docile/fail-closed behavior.
"""
import pytest

import experimental.pikmin2_seed_bridge as bridge
from experimental.pikmin2_enemy_roster import load_and_validate
from randomizer.seed import generate, validate
from randomizer.enemy_slots import bootstrap_slots

SOKKURI = 79


def placement_document():
    """Minimal lane 04 document granting Sokkuri one legal ground slot."""
    return {
        "schema": "p2-placement-v1",
        "slots": [{"uid": 401, "label": "sokkuri-slot", "stage": 1, "terrain": "ground",
                   "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}}],
        "profiles": [{"identity": "Sokkuri", "terrains": ["ground"], "accepted_gates": ["xyz"]}],
    }


@pytest.fixture
def one_admitted(monkeypatch):
    monkeypatch.setattr(bridge, "admitted_ids", lambda roster: [SOKKURI])


def test_p2_generation_fails_closed_for_unadmitted_placement():
    assert load_and_validate()  # real roster loads; Sokkuri remains unadmitted
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True, p2_placement=placement_document())


def test_p2_generation_requires_a_placement_document(one_admitted):
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True)


def test_p2_generation_emits_versioned_layout(one_admitted):
    manifest = generate("seed-a", p2_enemies=True, p2_placement=placement_document())
    assert manifest["p2_layout"]["version"] == "p2-enemy-layout-v1"
    assert "p2-enemy-bridge-v1" in manifest["capabilities"]
    assert manifest["enemy_mask"] == 0
    assert manifest["p2_layout"]["bindings"] == [
        {"target": "401", "source_id": SOKKURI, "enum_name": "Sokkuri"}]
    validate(manifest)


def test_p2_generation_is_deterministic_across_restart(one_admitted):
    first = generate("seed-a", p2_enemies=True, p2_placement=placement_document())
    second = generate("seed-a", p2_enemies=True, p2_placement=placement_document())
    assert first["p2_layout"] == second["p2_layout"]
    assert first == second


def test_p2_bootstrap_line_is_real_and_parseable(one_admitted):
    manifest = generate("seed-a", p2_enemies=True, p2_placement=placement_document())
    line = bootstrap_slots(manifest)
    assert line.startswith("ENEMY_P2 1 ")
    assert bridge.parse_bootstrap(line) == manifest["p2_layout"]


def test_legacy_seed_has_no_p2_line():
    manifest = generate("seed-a")
    assert "p2_layout" not in manifest
    assert bootstrap_slots(manifest) == ""


def test_p2_rejects_mixing_p1_layouts(one_admitted):
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True, p2_placement=placement_document(), enemy_shuffle=True)
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True, p2_placement=placement_document(), campaign_enemies=True)


def test_placement_layout_is_deterministic(one_admitted):
    first = generate("seed-p", p2_enemies=True, p2_placement=placement_document())
    second = generate("seed-p", p2_enemies=True, p2_placement=placement_document())
    assert first["p2_layout"] == second["p2_layout"]


def test_placement_defaults_denied_and_gated_by_admission():
    empty = {"schema": "p2-placement-v1", "slots": [], "profiles": []}
    with pytest.raises(ValueError):
        bridge.binding_targets_from_placement(empty)  # nothing admitted
    # A legal placement is still rejected while lane 02 admits nothing.
    with pytest.raises(ValueError):
        generate("seed-p", p2_enemies=True, p2_placement=placement_document())


def test_manifest_validate_enforces_current_admission(one_admitted):
    """A manually supplied layout binds a candidate identity only while admitted."""
    manifest = generate("seed-a", p2_enemies=True, p2_placement=placement_document())
    # Drop the test-only admission injection: the real roster has Sokkuri as a
    # candidate, so the loaded product manifest must now be rejected.
    bridge.admitted_ids, saved = (lambda roster: []), bridge.admitted_ids
    try:
        with pytest.raises(ValueError):
            validate(manifest)
    finally:
        bridge.admitted_ids = saved


def test_diagnostic_explicit_cohort_stays_available():
    """Explicit-cohort binding is a bridge diagnostic, independent of product admission."""
    layout = bridge.resolve_layout("seed", "Player1", ["gen-001"], [SOKKURI])
    assert layout["bindings"] == [{"target": "gen-001", "source_id": SOKKURI, "enum_name": "Sokkuri"}]


def test_shared_host_slot_must_not_silently_drop_an_admitted_identity(monkeypatch):
    """A slot contract must fail closed when two admitted identities share only
    one accepted host slot. Snow (45) and Dwarf Orange (44) reuse the same P1
    Dwarf-Bulborb host slot, so a single accepted slot cannot cover both: the
    resolver must raise rather than emit a binding set missing an admitted
    identity.
    """
    doc = {
        "schema": "p2-placement-v1",
        "slots": [{"uid": 401, "label": "shared-host-slot", "stage": 1, "terrain": "ground",
                   "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}}],
        "profiles": [
            {"identity": "YellowKochappy", "terrains": ["ground"], "accepted_gates": ["xyz"]},
            {"identity": "BlueKochappy", "terrains": ["ground"], "accepted_gates": ["xyz"]},
        ],
    }
    monkeypatch.setattr(bridge, "admitted_ids", lambda roster: [45, 44])
    with pytest.raises(ValueError, match="accepted placement target|binding"):
        bridge.resolve_placement_layout("seed-a", "Player1", doc)


@pytest.mark.parametrize("seed", ["seed-a", "seed-b", "seed-c"])
def test_shared_host_slots_cover_both_identities_when_capacity_exists(monkeypatch, seed):
    doc = {
        "schema": "p2-placement-v1",
        "slots": [{"uid": uid, "label": "shared-host-slot", "stage": 1, "terrain": "ground",
                   "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}}
                  for uid in [401, 402]],
        "profiles": [{"identity": identity, "terrains": ["ground"], "accepted_gates": ["xyz"]}
                     for identity in ["YellowKochappy", "BlueKochappy"]],
    }
    monkeypatch.setattr(bridge, "admitted_ids", lambda roster: [45, 44])
    result = bridge.resolve_placement_layout(seed, "Player1", doc)
    assert {row["source_id"] for row in result["bindings"]} == {44, 45}
    assert len({row["target"] for row in result["bindings"]}) == 2
    assert bridge.resolve_placement_layout(seed, "Player1", doc) == result
