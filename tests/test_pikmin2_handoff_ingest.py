"""Tests for scripts.ingest_p2_handoff_gates (lane 02, #438, slice 5).

Covers the handoff six-gate ingestion contract on two synthetic handoffs (one
clean, one carrying an injected PASS and an uncited PASS), the parser helpers and
the merge-only ``--apply`` path. Synthetic rosters are built purely through the
``experimental.pikmin2_enemy_roster`` source helpers; no committed evidence JSON
or native sources are touched.
"""
import json

from experimental.pikmin2_enemy_roster import (
    ADMISSION_GATES,
    build_entries,
    entries_from_payload,
    parse_enum_header,
    parse_info_table,
    resolve_ids,
    snapshot_payload,
)
from scripts.ingest_p2_handoff_gates import (
    apply_ingested_gates,
    ingest,
    parse_gate_table,
    parse_identities,
)

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


def _roster():
    enums = parse_enum_header(SYNTHETIC_HEADER)
    tables = parse_info_table(SYNTHETIC_TABLE)
    payload = snapshot_payload(resolve_ids(build_entries(enums, tables)), "synthetic")
    return entries_from_payload(payload)


CLEAN_HANDOFF = """# Lane 99 handoff (clean synthetic)

## Concrete source ID
- Source enemy ID: 17 `Frog`.

## Six arena gates (natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md spawn binding observed |
| 2. Autonomous movement and animation | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md leap animation |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md crush receiver |
| 4. Death and corpse | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md corpse drop |
| 5. Actual transport and reward | PASS (natural) | corpse:frog:1 goal=1 |
| 6. Cleanup and re-entry | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md re-entry |
"""

INJECTED_HANDOFF = """# Lane 99 handoff (injected synthetic)

## Concrete source ID
- Source enemy ID: 17 `Frog`.

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md spawn binding observed |
| 2. Autonomous movement and animation | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md leap animation |
| 3. Attacks and receivers | PASS (injected) | docs/PIKMIN2_FROG_IMPORT.md forced health write |
| 4. Death and corpse | PASS (natural) | docs/PIKMIN2_FROG_IMPORT.md corpse drop |
| 5. Actual transport and reward | PASS (natural) | corpse:frog:1 goal=1 |
| 6. Cleanup and re-entry | PASS | observed reset at runtime (no citation) |
"""


def test_clean_handoff_advances_every_gate():
    (row,) = ingest(CLEAN_HANDOFF, _roster())
    assert row["source_id"] == 17 and row["enum_name"] == "Frog" and row["role"] == "source"
    assert set(row["advances"]) == set(ADMISSION_GATES) | {"transport_reward"}
    assert row["refused"] == {}
    assert row["blocking"] == []


def test_injected_and_uncited_pass_are_refused():
    (row,) = ingest(INJECTED_HANDOFF, _roster())
    assert row["refused"]["attacks_receivers"] == "injected"
    assert row["refused"]["cleanup_reentry"] == "uncited"
    assert "attacks_receivers" not in row["advances"]
    assert "cleanup_reentry" not in row["advances"]
    assert "attacks_receivers" in row["blocking"]
    assert "cleanup_reentry" in row["blocking"]
    # Refusing the two bad PASSes keeps the identity out of the admitted set.
    assert row["blocking"]  # non-empty; the contract is not satisfied


def test_gate_table_maps_numbers_to_gate_ids():
    table = parse_gate_table(CLEAN_HANDOFF)
    assert set(table) == {1, 2, 3, 4, 5, 6}
    assert table[5]["evidence"] == "corpse:frog:1 goal=1"
    assert table[1]["evidence"].startswith("docs/PIKMIN2_FROG_IMPORT.md")


def test_identities_are_roster_verified():
    assert parse_identities(CLEAN_HANDOFF, _roster()) == [(17, "Frog")]
    # A helper (Egg=37 is a projectile here) is still parsed by id.
    text = "# x\nSource enemy ID: 37 `Egg`.\n"
    assert parse_identities(text, _roster()) == [(37, "Egg")]


def test_non_seedable_identity_is_skipped():
    text = "# x\nSource enemy ID: 0 `Pelplant`.\n\n## Six arena gates\n\n"
    text += "| Gate | Result | Evidence |\n|---|---|---|\n"
    text += "| 1. Exact identity and spawn | PASS | docs/PIKMIN2_FLORA_NATIVE.md |\n"
    (row,) = ingest(text, _roster())
    assert row.get("skipped") is True
    assert row["role"] == "plant"
    assert row["advances"] == []


def test_apply_merges_gates_only_into_existing_rows(tmp_path):
    (row,) = ingest(CLEAN_HANDOFF, _roster())
    ledger = tmp_path / "ev.json"
    ledger.write_text(json.dumps({
        "entries": {
            "17": {"gates": {gate: "UNTESTED" for gate in ADMISSION_GATES},
                   "eligibility": "candidate"},
        },
    }), encoding="utf-8")
    changed = apply_ingested_gates([row], ledger)
    assert changed[0][0] == "17"
    doc = json.loads(ledger.read_text(encoding="utf-8"))
    assert doc["entries"]["17"]["gates"]["identity_spawn"] == "PASS"
    # transport_reward is a manual lane-06 receipt, never persisted here.
    assert "transport_reward" not in doc["entries"]["17"]["gates"]
    # eligibility never changes (deny-by-default preserved).
    assert doc["entries"]["17"]["eligibility"] == "candidate"


def test_apply_never_fabricates_a_missing_row(tmp_path):
    (row,) = ingest(CLEAN_HANDOFF, _roster())
    ledger = tmp_path / "ev.json"
    ledger.write_text(json.dumps({"entries": {}}), encoding="utf-8")
    assert apply_ingested_gates([row], ledger) == []
    assert json.loads(ledger.read_text(encoding="utf-8"))["entries"] == {}
