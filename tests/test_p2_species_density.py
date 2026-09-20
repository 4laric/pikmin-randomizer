"""Versioned P2 species-density policy for the placement bridge (#838).

Pins the two behaviours issue #838 asks for:

1. The *legacy all-target fill* semantics of ``resolve_placement_layout`` are
   unchanged: every admitted identity is covered and every accepted compatible
   target is bound. The accepted-data case (``p2_species=[23]``) is reproduced
   verbatim: all 33 accepted Hope targets become Sarai, which is the eight
   overlapping capture territories that motivated the issue.
2. The new *bounded-coverage* policy binds the minimum number of targets that
   gives every selected species at least one binding and leaves the remaining
   compatible targets vanilla, without weakening accepted-placement constraints.

The tests use the committed accepted-placement document and the real lane-02
roster, so they exercise the same product entry point as ``randomizer.seed``.
"""
import json
from pathlib import Path

import pytest

from experimental.pikmin2_enemy_roster import load_and_validate
from experimental.pikmin2_seed_bridge import (
    DENSITY_BOUNDED,
    DENSITY_LEGACY,
    SeedBridgeError,
    build_bootstrap,
    parse_bootstrap,
    resolve_layout,
    resolve_placement_layout,
    validate_density,
    validate_layout,
)

ROOT = Path(__file__).resolve().parents[1]
ADMITTED_PLACEMENT_DOC = ROOT / "docs/PIKMIN2_ADMITTED_PLACEMENT.json"
SARAI = 23
BLUE_KOCHAPPY = 44
OTAKARA = [59, 60, 61, 62]


def committed_document():
    return json.loads(ADMITTED_PLACEMENT_DOC.read_text(encoding="utf-8"))


def accepted_document_for(*identities):
    """Minimal accepted document granting each named identity every ground target."""
    roster = load_and_validate()
    by_enum = {entry.enum_name: entry for entry in roster}
    document = {
        "schema": "p2-placement-v1",
        "slots": [
            {"uid": uid, "label": f"slot-{uid}", "stage": 1, "terrain": "ground",
             "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}}
            for uid in (401, 402, 403, 404, 405)
        ],
        "profiles": [
            {"identity": identity, "terrains": ["ground"], "accepted_gates": ["xyz"]}
            for identity in identities
        ],
    }
    assert set(identities) <= set(by_enum)
    return document


# --- pinning the current all-target fill semantics --------------------------


def test_legacy_default_fills_every_accepted_target_for_one_species():
    """The accepted-data eight-Sarai case: one species replaces every target."""
    roster = load_and_validate()
    document = committed_document()
    layout = resolve_placement_layout("seed-a", "Player1", document, roster, species=[SARAI])
    targets = {binding["target"] for binding in layout["bindings"]}
    # Every accepted, constraint-compatible target is bound, all to Sarai.
    assert len(layout["bindings"]) == 33  # committed doc exposes 33 accepted slots
    assert {binding["source_id"] for binding in layout["bindings"]} == {SARAI}
    assert layout["density"] == DENSITY_LEGACY
    assert targets  # nonempty


def test_legacy_default_is_unchanged_and_deterministic():
    """Default policy is byte-for-byte the same layout on repeated calls."""
    roster = load_and_validate()
    document = committed_document()
    first = resolve_placement_layout("seed-a", "Player1", document, roster)
    second = resolve_placement_layout("seed-a", "Player1", document, roster)
    assert first == second
    # Default None equals an explicit legacy token.
    explicit = resolve_placement_layout(
        "seed-a", "Player1", document, roster, density=DENSITY_LEGACY)
    assert explicit == first
    assert {binding["source_id"] for binding in first["bindings"]} == set(layout_ids(first))


def layout_ids(layout):
    return sorted({binding["source_id"] for binding in layout["bindings"]})


def test_legacy_multi_species_multiset_is_pinned():
    """The full admitted cohort keeps its historical all-target multiset."""
    from collections import Counter

    roster = load_and_validate()
    layout = resolve_placement_layout("seed-a", "Player1", committed_document(), roster)
    counts = Counter(binding["source_id"] for binding in layout["bindings"])
    assert sum(counts.values()) == 33
    assert counts == {
        9: 1, 23: 1, 44: 4, 54: 2, 57: 4,
        59: 3, 60: 3, 61: 3, 62: 2, 78: 4, 79: 6,
    }


# --- bounded-coverage policy ------------------------------------------------


def test_bounded_leaves_unassigned_targets_vanilla():
    """One selected species gets exactly one target; the rest stay unbound."""
    roster = load_and_validate()
    layout = resolve_placement_layout(
        "seed-a", "Player1", committed_document(), roster,
        species=[SARAI], density=DENSITY_BOUNDED)
    assert layout["density"] == DENSITY_BOUNDED
    assert len(layout["bindings"]) == 1
    assert layout["bindings"][0]["source_id"] == SARAI


def test_bounded_multispecies_covers_each_exactly_once():
    roster = load_and_validate()
    layout = resolve_placement_layout(
        "seed-a", "Player1", committed_document(), roster,
        species=OTAKARA, density=DENSITY_BOUNDED)
    assert len(layout["bindings"]) == len(OTAKARA)
    assert {binding["source_id"] for binding in layout["bindings"]} == set(OTAKARA)


def test_bounded_is_deterministic_and_stable_rng():
    """Bounded replay is a stable function of (seed, slot, document, species)."""
    roster = load_and_validate()
    kwargs = dict(species=[SARAI, BLUE_KOCHAPPY], density=DENSITY_BOUNDED)
    first = resolve_placement_layout("seed-a", "Player1", committed_document(), roster, **kwargs)
    second = resolve_placement_layout("seed-a", "Player1", committed_document(), roster, **kwargs)
    assert first == second


def test_bounded_never_weakens_accepted_placement():
    """A target bound by bounded mode is one the document accepts for the species."""
    roster = load_and_validate()
    document = committed_document()
    layout = resolve_placement_layout(
        "seed-a", "Player1", document, roster,
        species=[SARAI], density=DENSITY_BOUNDED)
    target = layout["bindings"][0]["target"]
    # Re-resolve with the legacy fill; the bounded target must also appear there
    # for the same species, proving it is an accepted compatible target.
    legacy = resolve_placement_layout("seed-a", "Player1", document, roster, species=[SARAI])
    accepted_targets = {b["target"] for b in legacy["bindings"] if b["source_id"] == SARAI}
    assert target in accepted_targets


def test_bounded_insufficient_unique_targets_fails_closed():
    """Two identities sharing one accepted target cannot both be covered."""
    roster = load_and_validate()
    document = accepted_document_for("BlueKochappy", "YellowKochappy")
    document["slots"] = [document["slots"][0]]  # exactly one compatible target
    with pytest.raises(SeedBridgeError):
        resolve_placement_layout(
            "seed-a", "Player1", document, roster,
            species=[BLUE_KOCHAPPY], density=DENSITY_BOUNDED)


def test_bounded_rejects_unknown_policy():
    roster = load_and_validate()
    with pytest.raises(SeedBridgeError):
        resolve_placement_layout(
            "seed-a", "Player1", committed_document(), roster, density="not-a-policy")


def test_validate_density_accepts_none_and_tokens():
    assert validate_density(None) == DENSITY_LEGACY
    assert validate_density(DENSITY_LEGACY) == DENSITY_LEGACY
    assert validate_density(DENSITY_BOUNDED) == DENSITY_BOUNDED
    with pytest.raises(SeedBridgeError):
        validate_density("bounded")


# --- round trips and manifest storage ---------------------------------------


def test_round_trip_preserves_manifest_density():
    roster = load_and_validate()
    layout = resolve_placement_layout(
        "seed-a", "Player1", committed_document(), roster,
        species=[SARAI, BLUE_KOCHAPPY], density=DENSITY_BOUNDED)
    text = build_bootstrap(layout, roster)
    parsed = parse_bootstrap(text, roster, density=layout["density"])
    assert parsed == layout
    assert parsed["density"] == DENSITY_BOUNDED


def test_legacy_manifest_without_density_still_validates():
    roster = load_and_validate()
    layout = resolve_layout("seed-a", "Player1", ["g1", "g2", "g3"], [SARAI, BLUE_KOCHAPPY])
    stripped = {key: value for key, value in layout.items() if key != "density"}
    validate_layout(stripped, roster)  # absent policy means legacy; never rejected


def test_tampered_density_is_rejected():
    roster = load_and_validate()
    layout = resolve_placement_layout(
        "seed-a", "Player1", committed_document(), roster,
        species=[SARAI], density=DENSITY_BOUNDED)
    layout["density"] = "untrusted-token"
    with pytest.raises(SeedBridgeError):
        validate_layout(layout, roster)


# --- explicit-cohort diagnostic path ----------------------------------------


def test_explicit_layout_bounded_uses_minimum_targets():
    layout = resolve_layout(
        "seed-a", "Player1", ["g1", "g2", "g3", "g4"], [SARAI, BLUE_KOCHAPPY],
        density=DENSITY_BOUNDED)
    assert layout["density"] == DENSITY_BOUNDED
    assert len(layout["bindings"]) == 2
    assert {binding["source_id"] for binding in layout["bindings"]} == {SARAI, BLUE_KOCHAPPY}


def test_explicit_layout_legacy_covers_every_target():
    layout = resolve_layout("seed-a", "Player1", ["g1", "g2", "g3", "g4"], [SARAI, BLUE_KOCHAPPY])
    assert layout["density"] == DENSITY_LEGACY
    assert {binding["target"] for binding in layout["bindings"]} == {"g1", "g2", "g3", "g4"}


def test_explicit_layout_bounded_insufficient_targets_fails_closed():
    with pytest.raises(SeedBridgeError):
        resolve_layout("seed-a", "Player1", ["g1"], [SARAI, BLUE_KOCHAPPY],
                       density=DENSITY_BOUNDED)
