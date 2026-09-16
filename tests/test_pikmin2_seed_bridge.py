"""Tests for the versioned P2 seed/native binding bridge (lane 03, #439)."""
import pytest

from experimental.pikmin2_seed_bridge import (
    LAYOUT_VERSION,
    PROTOCOL_HEADER,
    SeedBridgeError,
    bootstrap_for_manifest,
    build_bootstrap,
    parse_bootstrap,
    resolve_layout,
    roster_revision,
    validate_layout,
)

# Source IDs from the lane 02 roster (#438).
SOKKURI = 79
FROG = 17
QUEEN = 30
BLACKMAN = 99
PELPLANT = 0
POM = 82

TARGETS = ("gen-001", "gen-002", "gen-003", "gen-004")


def test_resolve_is_deterministic():
    first = resolve_layout("seed-a", "Player1", TARGETS, [SOKKURI, FROG])
    second = resolve_layout("seed-a", "Player1", TARGETS, [SOKKURI, FROG])
    assert first == second
    assert first["version"] == LAYOUT_VERSION
    assert {binding["target"] for binding in first["bindings"]} == set(TARGETS)


def test_slot_and_seed_change_the_roll():
    cohort = [SOKKURI, FROG, QUEEN]
    rolls = {
        tuple((binding["target"], binding["source_id"])
              for binding in resolve_layout("seed-a", f"Player{index}", TARGETS, cohort)["bindings"])
        for index in range(1, 9)
    }
    assert len(rolls) > 1
    seed_rolls = {
        tuple((binding["target"], binding["source_id"])
              for binding in resolve_layout(f"seed-{index}", "Player1", TARGETS, cohort)["bindings"])
        for index in range(8)
    }
    assert len(seed_rolls) > 1


def test_cohort_coverage_when_targets_allow():
    layout = resolve_layout("seed-c", "Player1", TARGETS, [SOKKURI, FROG, QUEEN])
    chosen = [binding["source_id"] for binding in layout["bindings"]]
    assert set(chosen) == {SOKKURI, FROG, QUEEN}


def test_only_enemy_and_boss_are_bindable():
    with pytest.raises(SeedBridgeError):
        resolve_layout("seed", "Player1", TARGETS, [PELPLANT])
    with pytest.raises(SeedBridgeError):
        resolve_layout("seed", "Player1", TARGETS, [POM])
    with pytest.raises(SeedBridgeError):
        resolve_layout("seed", "Player1", TARGETS, [999])
    with pytest.raises(SeedBridgeError):
        resolve_layout("seed", "Player1", TARGETS, [SOKKURI, SOKKURI])
    with pytest.raises(SeedBridgeError):
        resolve_layout("seed", "Player1", TARGETS, [])


def test_validate_layout_rejects_stale_revision():
    layout = resolve_layout("seed", "Player1", TARGETS, [SOKKURI, FROG])
    layout["roster_revision"] = "0" * 64
    with pytest.raises(SeedBridgeError):
        validate_layout(layout)


def test_validate_layout_rejects_duplicate_targets():
    layout = resolve_layout("seed", "Player1", TARGETS, [SOKKURI, FROG])
    layout["bindings"][1]["target"] = layout["bindings"][0]["target"]
    with pytest.raises(SeedBridgeError):
        validate_layout(layout)


def test_bootstrap_round_trip():
    layout = resolve_layout("seed-b", "Player1", TARGETS, [SOKKURI, QUEEN])
    text = build_bootstrap(layout)
    assert text.startswith(f"{PROTOCOL_HEADER} 1 ")
    parsed = parse_bootstrap(text)
    assert parsed == layout


def test_parse_rejects_malformed():
    with pytest.raises(SeedBridgeError):
        parse_bootstrap("ENEMY_SLOTS hash 15 1 3\n")
    with pytest.raises(SeedBridgeError):
        parse_bootstrap(f"{PROTOCOL_HEADER} 1 rev 2 gen-001 79\n")
    with pytest.raises(SeedBridgeError):
        parse_bootstrap(f"{PROTOCOL_HEADER} 2 rev 1 gen-001 79\n")
    with pytest.raises(SeedBridgeError):
        parse_bootstrap(f"{PROTOCOL_HEADER} 1 rev 1 gen-001 999\n")
    with pytest.raises(SeedBridgeError):
        parse_bootstrap(f"{PROTOCOL_HEADER} 1 rev 0\n")


def test_legacy_manifest_has_no_p2_line():
    assert bootstrap_for_manifest({}) == ""
    layout = resolve_layout("seed", "Player1", TARGETS, [SOKKURI])
    assert bootstrap_for_manifest({"p2_layout": layout}).startswith(PROTOCOL_HEADER)


def test_roster_revision_is_stable():
    assert roster_revision() == roster_revision()
    assert len(roster_revision()) == 64

@pytest.mark.parametrize('cohort', [[True], ['79'], [79.5]])
def test_rejects_coerced_source_ids(cohort):
    with pytest.raises(SeedBridgeError):
        resolve_layout('seed', 'slot', TARGETS, cohort)


@pytest.mark.parametrize('target', ['', 'has space', 'line\nbreak', None, 7])
def test_rejects_invalid_protocol_targets(target):
    with pytest.raises(SeedBridgeError):
        resolve_layout('seed', 'slot', [target], [SOKKURI])


def test_cohort_coverage_cannot_silently_drop_species():
    with pytest.raises(SeedBridgeError):
        resolve_layout('seed', 'slot', ['one'], [SOKKURI, FROG])
