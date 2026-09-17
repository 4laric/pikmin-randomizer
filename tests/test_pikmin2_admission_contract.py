"""Admission-contract tests for ``experimental.pikmin2_enemy_roster`` (lane 02).

Pins the five-gate admission contract on top of the eligibility ledger:
``admission_requirements`` (natural-PASS + delivery-receipt enforcement),
``admission_contract``, ``admitted_ids`` and ``write_admission``. Synthetic tests
build rosters purely through ``parse_enum_header``/``parse_info_table``/
``build_entries``/``resolve_ids``/``snapshot_payload``/``entries_from_payload``
(Pelplant=0, Frog=17, Egg=37), so they never mutate the committed roster or
evidence.
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
        "delivery_receipt": "corpse:frog:1 goal=1",
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
        "delivery_receipt": "corpse:frog:1 goal=1",
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


def test_admission_requirements_rejects_blank_or_garbage_receipt():
    # A whitespace-only receipt is treated as absent.
    assert admission_requirements(_req_entry(delivery_receipt=" ")) == ["transport_reward"]
    # An arbitrary string that is neither a lane-06 key nor a doc/log citation.
    assert admission_requirements(_req_entry(delivery_receipt="x")) == ["transport_reward:invalid_receipt"]


def test_admission_requirements_accepts_receipt_keys_and_citations():
    assert admission_requirements(_req_entry(delivery_receipt="corpse:frog:1 goal=1")) == []
    assert admission_requirements(_req_entry(delivery_receipt="onion:frog:1")) == []
    assert admission_requirements(_req_entry(delivery_receipt="receipt:frog:1")) == []
    assert admission_requirements(_req_entry(delivery_receipt="PIKMIN2_FROG_DELIVERY.md")) == []
    assert admission_requirements(_req_entry(delivery_receipt="output/p2-frog/native.log")) == []


def test_admission_requirements_flags_non_natural_pass():
    entry = _req_entry(
        notes=("PASS via injected health write", "proxy fixture-only registration"),
        eligibility_reason="forced vehicle/visual display host",
    )
    assert admission_requirements(entry) == [f"{gate}:injected" for gate in ADMISSION_GATES]


def test_admission_contract_rejects_injected_evidence_even_with_all_pass():
    roster = _roster({"17": _frog_overlay(
        notes=["PASS via injected health write", "proxy fixture-only registration"],
        delivery_receipt="proxy: forced Onion suck (injected)",
    )})
    contract = admission_contract(roster)
    assert contract["admitted"] == []
    assert 17 in contract["blocking"]


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
        "delivery_receipt": "onion:pelplant:1",
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
    assert admitted_ids(load_and_validate()) == [9, 23, 44, 54, 57, 59, 60, 61, 62, 78, 79]  # 23 Sarai; 44 Dwarf Orange; 59-62 Otakara elemental Dweevils (lane 22 fix 4, natural six gates, admitted 2026-09-15)


# ---------------------------------------------------------------------------
# write_admission
# ---------------------------------------------------------------------------

def test_write_admission_round_trip(tmp_path):
    real = load_and_validate()
    path = tmp_path / "ev.json"
    result = write_admission(real, path=path)
    assert result["admitted"] == [9, 23, 44, 54, 57, 59, 60, 61, 62, 78, 79]  # 23 Sarai; 44 Dwarf Orange; 59-62 Otakara elemental Dweevils (lane 22 fix 4, natural six gates, admitted 2026-09-15)

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
        "delivery_receipt": "corpse:snek:1 goal=1",
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


def test_write_admission_fresh_path_keeps_fields(tmp_path):
    real = load_and_validate()
    path = tmp_path / "fresh.json"
    write_admission(real, path=path)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(written.get("fields"), dict)
    assert "delivery_receipt" in written["fields"]


def test_admit_check_cli_exit_codes(capsys):
    import scripts.audit_pikmin2_roster as audit
    # Sokkuri (79) and Kogane (9) are admitted (user-approved 2026-09-17): all
    # six gates clear and admit-check reports PASS for both.
    assert audit.main(["--admit-check", "79"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert audit.main(["--admit-check", "9"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    # A plant identity is refused for its role.
    assert audit.main(["--admit-check", "0"]) == 1
    # An unknown id fails closed.
    assert audit.main(["--admit-check", "99999"]) == 1
    # Repeatable across ids still fails closed when any id in the batch fails.
    assert audit.main(["--admit-check", "79", "--admit-check", "0"]) == 1
