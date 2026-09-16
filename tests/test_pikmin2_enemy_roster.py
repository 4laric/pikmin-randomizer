"""Tests for the canonical P2 enemy roster model and audit (lane 02, #438)."""
import json

import pytest

from experimental.pikmin2_enemy_roster import (
    CLASSIFICATIONS,
    GATE_IDS,
    ROLES,
    ROSTER_PATH,
    RosterError,
    admission_set,
    admitted_ids,
    build_entries,
    by_id,
    candidate_review,
    classify,
    entries_from_payload,
    identity_role,
    inventory_encounters,
    load_and_validate,
    opt_in_validation_cohort,
    parse_enum_header,
    parse_info_table,
    require_admitted,
    require_opt_in,
    resolve_alias,
    resolve_ids,
    snapshot_payload,
    validate_roster,
)
from scripts.audit_pikmin2_roster import categorize_inventory_tokens

SYNTHETIC_HEADER = """
struct EnemyTypeID {
enum EEnemyTypeID {
\tEnemyID_NULL     = -1, // ID not set
\tEnemyID_Pelplant = 0,\t  // Pellet Posy
\tEnemyID_Frog     = 17,  // Yellow Wollywog
\tEnemyID_Egg      = 37,  // Egg
\tEnemyID_COUNT,
};
};
"""

SYNTHETIC_TABLE = """
EnemyInfo gEnemyInfo[] = {
//  name   ID   parent   members flags   model anim animgr texture param collision stone childID childNum droptype
\t{"Pelplant", EnemyTypeID::EnemyID_Pelplant, -1, 1, (EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "Pelplant", "Pelplant", "Pelplant", "Pelplant", "Pelplant", "Pelplant", "Pelplant", -1, 0, BDT_Empty},
\t{"Frog", EnemyTypeID::EnemyID_Frog, -1, 1, (EFlag_DayEndMax4 | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", EnemyTypeID::EnemyID_Egg, 10, BDT_Strong},
\t{"Egg", EnemyTypeID::EnemyID_Egg, -1, 1, (EFlag_HasNoInfo | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", -1, 0, BDT_Empty},
};
"""


def synthetic_payload():
    enums = parse_enum_header(SYNTHETIC_HEADER)
    tables = parse_info_table(SYNTHETIC_TABLE)
    return snapshot_payload(resolve_ids(build_entries(enums, tables)), "synthetic")


def test_roster_loads_and_validates():
    roster = load_and_validate()
    assert len(roster) == 102
    assert sum(entry.is_randomizable_candidate for entry in roster) == 64
    assert all(entry.classification in CLASSIFICATIONS for entry in roster)


def test_known_identities_and_relationships():
    roster = by_id(load_and_validate())
    assert roster[79].enum_name == "Sokkuri"
    assert roster[79].classification == "enemy"
    assert roster[99].classification == "boss"
    assert roster[0].classification == "plant"
    assert roster[82].classification == "manager_base"
    assert roster[39].classification == "nest"
    assert roster[39].in_info_table is False
    assert roster[30].child_name == "Baby" and roster[30].child_count == 50
    assert roster[75].child_id == 74 and roster[75].child_count == 5


def test_eligibility_defaults_denied_except_reviewed_candidates():
    roster = load_and_validate()
    candidates = {entry.source_id for entry in roster if entry.eligibility == "candidate"}
    assert candidates == {2, 15, 17, 45, 79}
    admitted = {entry.source_id for entry in roster if entry.eligibility == "admitted"}
    assert admitted == {23, 44, 54, 57, 59, 60, 61, 62, 78}
    assert all(entry.eligibility == "denied" for entry in roster if entry.source_id not in candidates | admitted)


def test_synthetic_pipeline_round_trips():
    payload = synthetic_payload()
    assert [entry["enum_name"] for entry in payload["entries"]] == ["Pelplant", "Frog", "Egg"]
    roster = by_id(entries_from_payload(payload))
    assert roster[0].classification == "plant"
    assert roster[17].classification == "enemy"
    assert roster[37].classification == "projectile"
    assert roster[17].child_id == 37 and roster[17].child_count == 10
    assert roster[17].drop_type == "BDT_Strong"
    # NULL sentinel is excluded.
    assert -1 not in roster


def test_parser_extracts_common_names():
    enums = parse_enum_header(SYNTHETIC_HEADER)
    assert enums["Frog"]["common_name"] == "Yellow Wollywog"
    assert enums["Pelplant"]["source_id"] == 0


def test_validate_rejects_duplicate_ids():
    payload = synthetic_payload()
    payload["entries"].append(dict(payload["entries"][0]))
    roster = entries_from_payload(payload)
    with pytest.raises(RosterError):
        validate_roster(roster)


def test_admitted_requires_complete_gates():
    payload = synthetic_payload()
    admitted_without_gates = {"0": {"eligibility": "admitted", "gates": {}}}
    roster = entries_from_payload(payload, admitted_without_gates)
    with pytest.raises(RosterError):
        validate_roster(roster)

    # A seedable identity (Frog=17) with a satisfied admission contract validates.
    full = {"17": {"eligibility": "admitted", "gates": {g: "PASS" for g in GATE_IDS},
                   "delivery_receipt": "corpse:frog:1 goal=1"}}
    validate_roster(entries_from_payload(payload, full))

    # An admitted identity whose contract is missing the delivery receipt fails.
    no_receipt = {"17": {"eligibility": "admitted", "gates": {g: "PASS" for g in GATE_IDS}}}
    with pytest.raises(RosterError):
        validate_roster(entries_from_payload(payload, no_receipt))


def test_classify_uses_boss_and_flags():
    assert classify("Pom", {"spawnable": False}) == "manager_base"
    assert classify("Queen", {"spawnable": True, "drop_type": "BDT_Boss"}) == "boss"
    assert classify("Hiba", {"spawnable": True}) == "hazard"
    assert classify("Rock", {"spawnable": True}) == "projectile"
    assert classify("Baby", {"spawnable": True}) == "boss_helper"


def test_inventory_tokens_are_categorized():
    enum_names = {"Chappy", "Rkabuto", "Bomb", "Wealthy"}
    tokens = {"Chappy", "$1Rkabuto", "Chappy_donutsichigo_s", "Wealthy_j_block_green", "NotAThing"}
    result = categorize_inventory_tokens(tokens, enum_names)
    assert result["exact"] == ["Chappy"]
    assert result["generator_variants"] == ["Rkabuto"]
    assert result["carrier_bases"]["Chappy"] == ["Chappy_donutsichigo_s"]
    assert result["carrier_bases"]["Wealthy"] == ["Wealthy_j_block_green"]
    assert result["unknown"] == ["NotAThing"]


def test_committed_snapshot_is_valid_json():
    payload = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    assert payload["schema"] == "p2-enemy-roster-1"
    assert payload["entry_count"] == 102


def test_identity_roles_real_roster():
    roster = by_id(load_and_validate())
    assert identity_role(roster[79]) == "source"          # Sokkuri
    assert identity_role(roster[99]) == "source"          # BlackMan boss
    assert identity_role(roster[71]) == "variant"         # UmiMushi shares UmiMushiBase
    assert identity_role(roster[101]) == "variant"        # UmiMushiBlind
    assert identity_role(roster[31]) == "helper"          # Baby boss_helper
    assert identity_role(roster[0]) == "plant"
    assert identity_role(roster[82]) == "manager_base"
    assert all(identity_role(entry) in ROLES for entry in roster.values())


def test_admission_defaults_deny_except_reviewed_pair():
    roster = load_and_validate()
    admission = admission_set(roster)
    assert admission.admitted == (23, 44, 54, 57, 59, 60, 61, 62, 78)
    assert admitted_ids(roster) == [23, 44, 54, 57, 59, 60, 61, 62, 78]  # 23 Sarai; 44 Dwarf Orange; 59-62 Otakara elemental Dweevils (admitted 2026-09-15); 54 Miulin, 57 Kurage, 78 MiniHoudai (admitted 2026-09-16)
    assert set(admission.candidates) == {2, 15, 17, 45, 79}
    assert sum(admission.by_role.values()) == len(roster)
    with pytest.raises(RosterError):
        require_admitted(roster, 79)


def test_admitted_ids_env_has_no_override(monkeypatch):
    # Directive 008: the stale PIKMIN_P2_CANDIDATE_SCOPE/PIKMIN_P2_ADMITTED_IDS
    # override was removed; the strict contract is canonical and env-inert.
    roster = load_and_validate()
    monkeypatch.setenv("PIKMIN_P2_ADMITTED_IDS", "79")
    assert admitted_ids(roster) == [23, 44, 54, 57, 59, 60, 61, 62, 78]
    monkeypatch.setenv("PIKMIN_P2_CANDIDATE_SCOPE", "private-snow-candidate-v1")
    assert admitted_ids(roster) == [23, 44, 54, 57, 59, 60, 61, 62, 78]


def test_admission_set_admits_only_seedable_randomizable():
    payload = synthetic_payload()
    full = {g: "PASS" for g in GATE_IDS}
    adopted = entries_from_payload(payload, {"17": {
        "eligibility": "admitted", "gates": full,
        "delivery_receipt": "corpse:frog:1 goal=1"}})
    assert admitted_ids(adopted) == [17]
    assert require_admitted(adopted, 17).enum_name == "Frog"

    # A plant cannot be admitted as a seedable identity even with a full contract.
    plant = entries_from_payload(payload, {"0": {
        "eligibility": "admitted", "gates": full,
        "delivery_receipt": "corpse:pelplant:1"}})
    with pytest.raises(RosterError):
        admission_set(plant)


def test_resolve_alias_distinguishes_tokens():
    roster = load_and_validate()
    assert resolve_alias("Chappy", roster)[0] == "exact"
    assert resolve_alias("$1Rkabuto", roster)[0] == "generator_variant"
    assert resolve_alias("Chappy_donutsichigo_s", roster)[0] == "treasure_carrier"
    assert resolve_alias("NotAThing", roster) == ("unknown", None)


def synthetic_inventory():
    return {"story_caves": [{"id": "cave-a", "floors": [
        {"first": 1, "last": 2, "enemy_ids": ["Frog", "$1Egg"]},
        {"first": 3, "last": 3, "enemy_ids": ["Egg", "NotAThing"]},
    ]}]}


def test_inventory_encounters_maps_aliases():
    roster = entries_from_payload(synthetic_payload())
    encounters = inventory_encounters(synthetic_inventory(), roster)
    assert encounters["Frog"] == [{"cave": "cave-a", "first": 1, "last": 2}]
    assert len(encounters["Egg"]) == 2
    assert "NotAThing" not in encounters


def test_candidate_review_reports_role_and_missing_gates():
    full = {g: "PASS" for g in GATE_IDS}
    roster = entries_from_payload(synthetic_payload(), {"17": {
        "eligibility": "candidate", "gates": full,
        "native_module": "pc_p2_frog", "owner_lane": "16"}})
    rows = candidate_review(roster, inventory_encounters(synthetic_inventory(), roster))
    frog = next(row for row in rows if row["source_id"] == 17)
    assert frog["role"] == "source" and frog["owner_lane"] == "16"
    assert frog["missing_gates"] == [] and frog["encounters"]
    assert {row["source_id"] for row in rows} == {17}


def test_committed_overlay_reviewed_cohort_and_native_modules():
    roster = by_id(load_and_validate())
    assert roster[79].eligibility == "candidate" and roster[79].native_module == "pc_p2_sokkuri"
    assert roster[54].owner_lane == "19" and roster[45].owner_lane == "13"
    assert roster[44].eligibility == "admitted" and roster[44].native_module == "pc_p2_dwarf_orange"
    assert roster[44].owner_lane == "13"
    assert admitted_ids(load_and_validate()) == [23, 44, 54, 57, 59, 60, 61, 62, 78]  # 23 Sarai; 44 Dwarf Orange; 59-62 Otakara elemental Dweevils (admitted 2026-09-15); 54 Miulin, 57 Kurage, 78 MiniHoudai (admitted 2026-09-16)


def test_opt_in_requires_reviewed_seedable_identity():
    roster = load_and_validate()
    # Snow (45) and Dwarf Orange (44) are reviewed candidates with a source role.
    assert require_opt_in(roster, 45).enum_name == "YellowKochappy"
    assert require_opt_in(roster, 44).enum_name == "BlueKochappy"
    # Denied (un-reviewed) identity cannot be opted in.
    with pytest.raises(RosterError):
        require_opt_in(roster, 1)  # Kochappy: denied
    # Non-seedable roles are rejected even though their classification is enemy/boss.
    with pytest.raises(RosterError):
        require_opt_in(roster, 82)  # manager_base
    with pytest.raises(RosterError):
        require_opt_in(roster, 0)  # plant
    # Unknown ids are rejected.
    with pytest.raises(RosterError):
        require_opt_in(roster, 999)


def test_opt_in_validation_cohort_validates_and_does_not_admit():
    roster = load_and_validate()
    cohort = opt_in_validation_cohort(roster, [44, 45])
    assert cohort == [44, 45]
    # The private validation path never mutates the global admission set.
    assert admitted_ids(roster) == [23, 44, 54, 57, 59, 60, 61, 62, 78]  # 23 Sarai; 44 Dwarf Orange; 59-62 Otakara elemental Dweevils (admitted 2026-09-15); 54 Miulin, 57 Kurage, 78 MiniHoudai (admitted 2026-09-16)
    with pytest.raises(RosterError):
        require_admitted(roster, 45)


def test_opt_in_validation_cohort_rejects_invalid_input():
    roster = load_and_validate()
    with pytest.raises(RosterError):
        opt_in_validation_cohort(roster, [])
    with pytest.raises(RosterError):
        opt_in_validation_cohort(roster, [44, 44])
    with pytest.raises(RosterError):
        opt_in_validation_cohort(roster, [1])  # denied
    with pytest.raises(RosterError):
        opt_in_validation_cohort(roster, [44, 1])  # one denied member
    with pytest.raises(RosterError):
        opt_in_validation_cohort(roster, [999])
    for coerced in ([True], ["44"], [44.5]):
        with pytest.raises(RosterError):
            opt_in_validation_cohort(roster, coerced)


def test_opt_in_cohort_feeds_private_validation_path_only():
    from experimental.pikmin2_seed_bridge import SeedBridgeError, resolve_admitted_layout, resolve_layout
    roster = load_and_validate()
    snow_dwarf = opt_in_validation_cohort(roster, [44, 45])
    # A consumer may run the Snow/Dwarf Orange cohort through a private binding
    # layout (ordinary generated-session validation) without admission.
    layout = resolve_layout("seed-l02", "Player1", ("gen-a", "gen-b", "gen-c"),
                            snow_dwarf, roster, admitted=snow_dwarf)
    assert {binding["source_id"] for binding in layout["bindings"]} == {44, 45}
    # Normal generation stays deny-by-default: the product entry point seeds only the
    # admitted set (Sarai 23, Dwarf Orange 44 + Otakara 59-62 since 2026-09-15), never the private cohort's Snow 45.
    assert admitted_ids(roster) == [23, 44, 54, 57, 59, 60, 61, 62, 78]
    admitted_layout = resolve_admitted_layout("seed-l02", "Player1", tuple(f"gen-{c}" for c in "abcdefghi"), roster)
    assert {binding["source_id"] for binding in admitted_layout["bindings"]} == {23, 44, 54, 57, 59, 60, 61, 62, 78}


