"""Tests for the canonical P2 enemy roster model and audit (lane 02, #438)."""
import json

import pytest

from experimental.pikmin2_enemy_roster import (
    CLASSIFICATIONS,
    GATE_IDS,
    ROSTER_PATH,
    RosterError,
    build_entries,
    by_id,
    classify,
    entries_from_payload,
    load_and_validate,
    parse_enum_header,
    parse_info_table,
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


def test_eligibility_defaults_denied():
    roster = load_and_validate()
    assert all(entry.eligibility == "denied" for entry in roster)


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

    full = {"0": {"eligibility": "admitted", "gates": {g: "PASS" for g in GATE_IDS}}}
    validate_roster(entries_from_payload(payload, full))


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
