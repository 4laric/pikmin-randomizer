"""Source/config and model-only negatives; these are not route/gameplay proofs."""
import copy
import hashlib
import json

import pytest

from randomizer.seed import generate
from randomizer.population_supply import resolve, growth_bound as _growth_bound, can_reach_population as _can_reach_population
from randomizer.population_supply_data import INPUTS, INPUTS_SHA256
from scripts.audit_population_supply import loose_pellets, pellet_configs

HOPE_DWARFS = (312577052, 837882317, 1165161781, 1630257208,
               2146533423, 2271980013, 2893364421)


def growth_bound(*args, **state):
    # Explicit model fixture, not evidence that a newly unlocked Onion has
    # withdrawn its stored stock or delivered a living field squad.
    state.setdefault("usable_carriers", {color: 20 for color in ("red", "blue", "yellow")})
    return _growth_bound(*args, **state)


def can_reach_population(*args, **state):
    state.setdefault("usable_carriers", {color: 20 for color in ("red", "blue", "yellow")})
    return _can_reach_population(*args, **state)


def test_actual_usable_carriers_required_even_with_unlocked_onion(manifest):
    saved = resolve(manifest, {uid: model_branch() for uid in HOPE_DWARFS})
    inventory = {"Blue Onion": 1, "Pikmin Delivery (10)": 999}
    assert _growth_bound(saved, manifest, inventory, "blue") == 0
    assert _growth_bound(saved, manifest, inventory, "blue", usable_carriers={"blue": 2}) == 0
    assert _growth_bound(saved, manifest, inventory, "blue", usable_carriers={"blue": 3}) == 36
    assert _growth_bound(saved, manifest, inventory, "blue", usable_carriers={"red": 20}) == 0
    for value in (True, -1, 1.5):
        with pytest.raises(ValueError, match="usable carrier"):
            _growth_bound(saved, manifest, inventory, "blue", usable_carriers={"blue": value})
    with pytest.raises(ValueError, match="usable carrier"):
        _growth_bound(saved, manifest, inventory, "blue", usable_carriers={"purple": 20})


def test_production_proposal_refuses_missing_reviewed_registry(manifest):
    from randomizer.population_supply import resolve_static, validate_snapshot
    with pytest.raises(ValueError, match="reviewed renewable/bootstrap"):
        resolve_static(manifest)
    saved = resolve(manifest, {uid: model_branch() for uid in HOPE_DWARFS})
    with pytest.raises(ValueError, match="reviewed renewable/bootstrap"):
        validate_snapshot(saved, manifest)


def test_static_proposal_reconstructs_source_and_excludes_finite_food(manifest, monkeypatch):
    import randomizer.population_supply as supply
    posies = [row["uid"] for row in INPUTS["generators"] if row["stage"] == 1
              and row["kind"] == "teki" and row["species"] == 7
              and row["schedule"]["mode"] == "every-visit"]
    # These registries are synthetic for validator tests, not production proof.
    monkeypatch.setattr(supply, "STATIC_ROUTES", {uid: model_branch(allows_fully_grown_posy=True) for uid in posies})
    monkeypatch.setattr(supply, "STATIC_BOOTSTRAPS", {"red": dict(version="onion-retrieval-v1",
                          evidence="model fixture only", requires=[])})
    saved = supply.resolve_static(manifest)
    assert saved["bootstrap_proofs"] == supply.STATIC_BOOTSTRAPS
    assert saved["bootstrap_proofs"] is not supply.STATIC_BOOTSTRAPS
    assert supply.validate_snapshot(json.loads(json.dumps(saved)), manifest)
    assert supply.static_can_reach_population(saved, manifest, {}, 100, "red")
    assert not supply.static_can_reach_population(saved, manifest, {"Blue Onion": 1}, 25, "blue")
    for mutate in (lambda rows: rows.pop(), lambda rows: rows.append(copy.deepcopy(rows[0])),
                   lambda rows: rows[0].update(count=True), lambda rows: rows[0].update(file_sha256="0" * 64)):
        corrupt = copy.deepcopy(saved)
        mutate(corrupt["suppliers"])
        with pytest.raises(ValueError, match="reviewed source snapshot"):
            supply.validate_snapshot(corrupt, manifest)
    monkeypatch.setattr(supply, "STATIC_ROUTES", {uid: model_branch() for uid in HOPE_DWARFS})
    with pytest.raises(ValueError, match="renewable supplier"):
        supply.resolve_static(manifest)


def test_bootstrap_proofs_are_strict_and_saved_not_consumable(manifest, monkeypatch):
    import randomizer.population_supply as supply
    posies = [row["uid"] for row in INPUTS["generators"] if row["stage"] == 1
              and row["kind"] == "teki" and row["species"] == 7
              and row["schedule"]["mode"] == "every-visit"]
    monkeypatch.setattr(supply, "STATIC_ROUTES", {uid: model_branch(allows_fully_grown_posy=True) for uid in posies})
    proof = dict(version="onion-retrieval-v1", evidence="model-only retrieval fixture", requires=[])
    for change in (dict(requires=["Pikmin Delivery (10)"]), dict(evidence=True),
                   dict(evidence="  "), dict(count=999), dict(requires=[{}]),
                   dict(requires=["Blue Onion", "Blue Onion"])):
        monkeypatch.setattr(supply, "STATIC_BOOTSTRAPS", {"red": {**proof, **change}})
        with pytest.raises(ValueError, match="Onion retrieval"):
            supply.resolve_static(manifest)
    monkeypatch.setattr(supply, "STATIC_BOOTSTRAPS", {"red": proof})
    saved = supply.resolve_static(manifest)
    supply.STATIC_BOOTSTRAPS["red"]["requires"] = ["Blue Onion"]
    with pytest.raises(ValueError, match="reviewed source snapshot"):
        supply.validate_snapshot(saved, manifest)
    with pytest.raises(ValueError, match="reviewed source snapshot"):
        supply.static_can_reach_population(saved, manifest, {"Blue Onion": 1}, 50, "red")


def model_branch(**changes):
    return dict(version="source-backed-logic-v1", evidence="model-only branch fixture; no physical route acceptance",
                requires=[], carrier_colors=["red", "yellow", "blue"], **changes)


@pytest.fixture(scope="module")
def manifest():
    return generate("1153", campaign_enemies=True, p2_enemies=True, p2_checks=True,
                    p2_species="playable", starting_flarlic=1,
                    randomize_color_stats=True, progressive_color_stats=True,
                    initial_stat_bounds={stat: (25, 25) for stat in ("damage", "movement", "attack_rate")})


def test_input_metadata_pin():
    assert hashlib.sha256(json.dumps(INPUTS, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True).encode()).hexdigest() == INPUTS_SHA256
    assert len(INPUTS["generators"]) == 975
    assert len(INPUTS["configs"]) == 62


def test_final_full42_protected_counts_and_no_corpse_sources(manifest):
    saved = resolve(manifest)
    rows = {row["uid"]: row for row in saved["suppliers"]}
    assert len({row["source_id"] for row in manifest["p2_layout"]["bindings"]}) == 42
    assert sum(rows[uid]["count"] for uid in HOPE_DWARFS) == 9
    assert all(rows[uid]["yields"]["red"] == 4 for uid in HOPE_DWARFS)
    assert all(not rows[uid]["repeatable_at_cap"] for uid in HOPE_DWARFS)
    assert rows[40410547]["count"] == 0 and sum(rows[40410547]["yields"].values()) == 0
    assert all(sum(row["yields"].values()) == 0 for row in rows.values()
               if row["game"] == "p2")  # Unreviewed module yields are not host yields.
    assert {row["species"] for row in rows.values() if row["game"] == "p2"} >= {57, 72, 69}


def test_unreviewed_routes_do_not_invent_supply_or_change_initial20(manifest):
    saved = resolve(manifest)
    assert growth_bound(saved, manifest, {}, "red") == 0
    assert can_reach_population(saved, manifest, {}, 20, "red")
    assert not can_reach_population(saved, manifest, {}, 50, "red")
    assert not can_reach_population(saved, manifest, {"Pikmin Delivery (10)": 999}, 50, "red")


def test_finite_protected_food_counts_once_at_day_cap(manifest):
    saved = resolve(manifest, {uid: model_branch() for uid in HOPE_DWARFS})
    assert growth_bound(saved, manifest, {}, "red") == 36
    assert can_reach_population(saved, manifest, {}, 50, "red")
    assert not can_reach_population(saved, manifest, {}, 100, "red")
    consumed = {row["uid"]: row["count"] for row in saved["suppliers"]}
    assert growth_bound(saved, manifest, {}, "red", consumed=consumed) == 0
    assert growth_bound(json.loads(json.dumps(saved)), manifest, {}, "red", consumed=consumed) == 0


def test_last_supplier_suppression_and_filler_cannot_rescue(manifest):
    saved = resolve(manifest, {uid: model_branch() for uid in HOPE_DWARFS})
    for row in saved["suppliers"]:
        if row["uid"] in HOPE_DWARFS:
            row["suppressed"] = True  # Derived logic negative, not a generated layout.
    assert not can_reach_population(saved, manifest, {"Pikmin Delivery (10)": 99}, 50, "red")


def test_locked_onion_combat_and_carry_branch(manifest):
    saved = resolve(manifest, {uid: model_branch() for uid in HOPE_DWARFS})
    assert growth_bound(saved, manifest, {}, "blue") == 0
    assert growth_bound(saved, manifest, {"Blue Onion": 1}, "blue") == 36
    for row in saved["suppliers"]:
        if row["uid"] in HOPE_DWARFS:
            row["logic_route"]["requires"] = ["Yellow Onion"]
    assert growth_bound(saved, manifest, {}, "red") == 0
    assert growth_bound(saved, manifest, {"Yellow Onion": 1}, "red") == 36
    for row in saved["suppliers"]:
        if row["uid"] in HOPE_DWARFS:
            row["carrier_slots"] = 2  # One fewer carrier than loaded minimum3.
    assert growth_bound(saved, manifest, {"Yellow Onion": 1}, "red") == 0


def test_expired_delayed_and_late_missed_activation(manifest):
    saved = resolve(manifest, {uid: model_branch() for uid in HOPE_DWARFS})
    for row in saved["suppliers"]:
        if row["uid"] in HOPE_DWARFS:
            row["schedule"]["expires_after_day"] = 28
    assert growth_bound(saved, manifest, {}, "red") == 0
    for row in saved["suppliers"]:
        if row["uid"] in HOPE_DWARFS:
            row["schedule"]["expires_after_day"] = 30
            row["schedule"]["first_day"] = 10
    assert growth_bound(saved, manifest, {}, "red", day=2) == 0
    for row in saved["suppliers"]:
        if row["uid"] in HOPE_DWARFS:
            row["schedule"]["last_activation_day"] = 10
    assert growth_bound(saved, manifest, {}, "red") == 0
    assert growth_bound(saved, manifest, {}, "red", activated=HOPE_DWARFS) == 36


def test_repeatable_fully_grown_default_posy_is_separate_witness(manifest):
    posies = [row["uid"] for row in INPUTS["generators"] if row["stage"] == 1
              and row["kind"] == "teki" and row["species"] == 7
              and row["schedule"]["mode"] == "every-visit"]
    assert len(posies) == 5
    saved = resolve(manifest, {uid: model_branch() for uid in posies})
    assert growth_bound(saved, manifest, {}, "red") == 0  # Premature cutting has no guaranteed drop.
    for row in saved["suppliers"]:
        if row["uid"] in posies:
            row["logic_route"]["allows_fully_grown_posy"] = True
    assert growth_bound(saved, manifest, {}, "red") == float("inf")
    assert can_reach_population(saved, manifest, {}, 100, "red")


def test_consumable_requirement_and_invalid_state_refused(manifest):
    branch = model_branch()
    branch["requires"] = ["Pikmin Delivery (10)"]
    with pytest.raises(ValueError, match="reviewed"):
        resolve(manifest, {HOPE_DWARFS[0]: branch})
    saved = resolve(manifest, {uid: model_branch() for uid in HOPE_DWARFS})
    with pytest.raises(ValueError, match="consumption"):
        growth_bound(saved, manifest, {}, "red", consumed={HOPE_DWARFS[0]: -1})
    with pytest.raises(ValueError, match="color/day"):
        growth_bound(saved, manifest, {}, "red", day=30)


@pytest.mark.parametrize("parser", [pellet_configs, lambda b: loose_pellets(b, 1, "default.gen")])
def test_malformed_source_frames_refused(parser):
    with pytest.raises(ValueError):
        parser(b"\x00\x00\x00\x01tlep")
