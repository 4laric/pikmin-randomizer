"""Admission-gated P2 seed generation wiring (lane 03, #439).

The real lane 02 roster admits nothing yet, so these tests inject a minimal
admitted cohort (Sokkuri=79) to exercise the product path and separately prove
the default docile/fail-closed behavior.
"""
import pytest

import experimental.pikmin2_seed_bridge as bridge
from experimental.pikmin2_enemy_roster import load_and_validate
from randomizer.seed import generate, validate
from randomizer.enemy_slots import bootstrap_slots

SOKKURI = 79
TARGETS = ["gen-001", "gen-002"]


@pytest.fixture
def one_admitted(monkeypatch):
    monkeypatch.setattr(bridge, "admitted_ids", lambda roster: [SOKKURI])


def test_p2_generation_fails_closed_while_nothing_admitted():
    assert load_and_validate()  # real roster loads, nothing admitted
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True, p2_targets=TARGETS)


def test_p2_generation_requires_targets(one_admitted):
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True)


def test_p2_generation_emits_versioned_layout(one_admitted):
    manifest = generate("seed-a", p2_enemies=True, p2_targets=TARGETS)
    assert manifest["p2_layout"]["version"] == "p2-enemy-layout-v1"
    assert "p2-enemy-bridge-v1" in manifest["capabilities"]
    assert manifest["enemy_mask"] == 0
    assert {b["target"] for b in manifest["p2_layout"]["bindings"]} == set(TARGETS)
    validate(manifest)


def test_p2_generation_is_deterministic_across_restart(one_admitted):
    first = generate("seed-a", p2_enemies=True, p2_targets=TARGETS)
    second = generate("seed-a", p2_enemies=True, p2_targets=TARGETS)
    assert first["p2_layout"] == second["p2_layout"]
    assert first == second


def test_p2_bootstrap_line_is_real_and_parseable(one_admitted):
    manifest = generate("seed-a", p2_enemies=True, p2_targets=TARGETS)
    line = bootstrap_slots(manifest)
    assert line.startswith("ENEMY_P2 1 ")
    assert bridge.parse_bootstrap(line) == manifest["p2_layout"]


def test_legacy_seed_has_no_p2_line():
    manifest = generate("seed-a")
    assert "p2_layout" not in manifest
    assert bootstrap_slots(manifest) == ""


def test_p2_rejects_mixing_p1_layouts(one_admitted):
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True, p2_targets=TARGETS, enemy_shuffle=True)
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True, p2_targets=TARGETS, campaign_enemies=True)


def test_p2_targets_must_be_strings(one_admitted):
    with pytest.raises(ValueError):
        generate("seed-a", p2_enemies=True, p2_targets=[1, 2])
