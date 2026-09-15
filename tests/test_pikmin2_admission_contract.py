"""Admission-contract tests for ``experimental.pikmin2_enemy_roster`` (lane 02).

Pins the five-gate admission contract another worker is adding on top of the
eligibility ledger: what counting a ``delivery_receipt`` and five PASS gates
means for ``admission_requirements``, ``admission_contract`` and
``admitted_ids``, and how ``write_admission`` commits/demotes eligibility in
the evidence JSON.

The API under test (``ADMISSION_GATES``, ``RosterEntry.delivery_receipt``,
``admission_requirements``, ``admission_contract``, ``write_admission`` and the
new ``admitted_ids`` semantics) does not exist yet: this module will fail to
import until it lands. Synthetic tests build rosters purely through the existing
``parse_enum_header`` / ``parse_info_table`` / ``build_entries`` / ``resolve_ids``
/ ``snapshot_payload`` / ``entries_from_payload`` helpers (Pelplant=0, Frog=17,
Egg=37), so they never mutate the committed roster or evidence.
"""
import json

from experimental.pikmin2_enemy_roster import (
    ADMISSION_GATES,
    RosterEntry,
    admitted_ids,
    admission_contract,
    admission_requirements,
    build_entries,
    entries_from_payload,
    load_and_validate,
    parse_enum_header,
    parse_info_table,
    resolve_ids,
    snapshot_payload,
    write_admission,
)

# ---------------------------------------------------------------------------
# Synthetic roster (Pelplant=0, Frog=17, Egg=37), mirroring
# tests/test_pikmin2_roster_coverage.py.
# ---------------------------------------------------------------------------

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

# A second two-source identity roster used only by the write_admission test so
# a stale "admitted" sibling can regress while a sibling is promoted.
WRITE_HEADER = """
struct EnemyTypeID {
enum EEnemyTypeID {
\tEnemyID_NULL     = -1, // ID not set
\tEnemyID_Frog     = 17,  // Yellow Wollywog
\tEnemyID_Snek     = 41,  // Synthetic source enemy
\tEnemyID_COUNT,
};
};
"""

WRITE_TABLE = """
EnemyInfo gEnemyInfo[] = {
//  name   ID   parent   members flags   model anim animgr texture param collision stone childID childNum droptype
\t{"Frog", EnemyTypeID::EnemyID_Frog, -1, 1, (EFlag_DayEndMax4 | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", -1, 0, BDT_Strong},
\t{"Snek", EnemyTypeID::EnemyID_Snek, -1, 1, (EFlag_DayEndMax4 | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", -1, 0, BDT_Strong},
};
"""


def _payload_from(header, table):
    enums = parse_enum_header(header)
    tables = parse_info_table(table)
    return snapshot_payload(resolve_ids(build_entries(enums, tables)), "synthetic")


def _roster(overlays):
    return entries_from_payload(_payload_from(SYNTHETIC_HEADER, SYNTHETIC_TABLE), overlays)


def _pass_gates():
    return {gate: "PASS" for gate in ADMISSION_GATES}


def _frog_overlay(**overrides):
    overlay = {
        "gates": _pass_gates(),
        "delivery_receipt": "SEED-17",
        "eligibility": "candidate",
    }
    overlay.update(overrides)
    return overlay


def _req_entry(**overrides):
    kw = {
        "source_id": 17,
        "enum_name": "Frog",
        "source_name": "Frog",
        "common_name": "Yellow Wollywog",
        "classification": "enemy",
        "gates": _pass_gates(),
        "delivery_receipt": "SEED-17",
    }
    kw.update(overrides)
    return RosterEntry(**kw)


# ---------------------------------------------------------------------------
# admission_requirements
# ---------------------------------------------------------------------------

def test_admission_requirements_empty_when_full():
    assert admission_requirements(_req_entry()) == []


def test_admission_requirements_reports_exact_gate():
    gates = _pass_gates()
    gates["death_corpse"] = "UNTESTED"
    assert admission_requirements(_req_entry(gates=gates)) == ["death_corpse"]


def test_admission_requirements_reports_transport_reward():
    assert admission_requirements(_req_entry(delivery_receipt=None)) == ["transport_reward"]


# ---------------------------------------------------------------------------
# admission_contract
# ---------------------------------------------------------------------------

def test_admission_contract_admits_full_row():
    roster = _roster({"17": _frog_overlay()})
    contract = admission_contract(roster)
    assert contract["admitted"] == [17]
    assert 17 not in contract["blocking"]


def test_admission_contract_blocks_partial_and_lists_gates():
    gates = _pass_gates()
    gates["attacks_receivers"] = "UNTESTED"
    roster = _roster({"17": _frog_overlay(gates=gates)})
    contract = admission_contract(roster)
    assert contract["admitted"] == []
    assert contract["blocking"][17] == ["attacks_receivers"]


def test_admission_contract_ignores_non_seedable_roles():
    overlay = {
        "gates": _pass_gates(),
        "delivery_receipt": "SEED-0",
        "eligibility": "candidate",
    }
    roster = _roster({"0": overlay})
    contract = admission_contract(roster)
    assert contract["admitted"] == []
    assert 0 not in contract["blocking"]


def test_admission_contract_respects_excluded():
    roster = _roster({"17": _frog_overlay(eligibility="excluded")})
    contract = admission_contract(roster)
    assert contract["admitted"] == []
    assert contract["blocking"][17] == ["excluded"]


# ---------------------------------------------------------------------------
# admitted_ids
# ---------------------------------------------------------------------------

def test_admitted_ids_from_contract():
    roster = _roster({"17": _frog_overlay()})
    assert admitted_ids(roster) == [17]
    assert admitted_ids(load_and_validate()) == []


# ---------------------------------------------------------------------------
# write_admission
# ---------------------------------------------------------------------------

def test_write_admission_round_trip(tmp_path):
    real = load_and_validate()
    path = tmp_path / "ev.json"
    result = write_admission(real, path=path)
    assert result["admitted"] == []

    written = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(written.get("entries"), dict)
    roster_elig = {str(entry.source_id): entry.eligibility for entry in real}
    for key, value in written["entries"].items():
        assert value.get("eligibility") == roster_elig[key]

    frog = _frog_overlay()
    snek_gates = _pass_gates()
    snek_gates["death_corpse"] = "UNTESTED"
    snek = {
        "gates": snek_gates,
        "delivery_receipt": "SEED-41",
        "eligibility": "admitted",
    }
    roster = entries_from_payload(
        _payload_from(WRITE_HEADER, WRITE_TABLE), {"17": frog, "41": snek}
    )
    path2 = tmp_path / "write.json"
    write_admission(roster, path=path2)
    written2 = json.loads(path2.read_text(encoding="utf-8"))
    assert written2["entries"]["17"]["eligibility"] == "admitted"
    assert written2["entries"]["41"]["eligibility"] == "candidate"
