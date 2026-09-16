"""Admission-gated seed pool wiring tests (lane 02, #438, slice 4).

Proves the lane 02 admission contract actually gates the seedable P2 identity
pool that lane 03's seed bridge reads: an identity reaches a generated P2 seed
only when ``admission_requirements(entry)`` is empty on the ledger â€” natural
PASS on gates 1-4 + 6 plus a cited delivery receipt for gate 5. A partially
passed sibling stays blocked, and stripping the receipt drops the identity back
out (fail closed). Synthetic rosters are built purely through
``parse_enum_header``/``parse_info_table``/``build_entries``/``resolve_ids``/
``snapshot_payload``/``entries_from_payload``; the committed roster, evidence
JSON and native sources are never touched, so these tests need no native root.
"""
import pytest

from experimental.pikmin2_enemy_roster import (
    ADMISSION_GATES,
    admission_contract,
    admitted_ids,
    build_entries,
    entries_from_payload,
    load_and_validate,
    parse_enum_header,
    parse_info_table,
    resolve_ids,
    snapshot_payload,
)
from experimental.pikmin2_seed_bridge import SeedBridgeError, resolve_placement_layout
from randomizer.seed import generate

# Two distinct "source" identities: Frog=17 (fully passed) and Snek=41 (one
# open gate). Exactly one may satisfy the contract, so exactly one may seed.
SYNTHETIC_HEADER = """
struct EnemyTypeID {
enum EEnemyTypeID {
\tEnemyID_NULL     = -1, // ID not set
\tEnemyID_Frog     = 17,  // Yellow Wollywog
\tEnemyID_Snek     = 41,  // Synthetic source enemy
\tEnemyID_COUNT,
};
};
"""

SYNTHETIC_TABLE = """
EnemyInfo gEnemyInfo[] = {
//  name   ID   parent   members flags   model anim animgr texture param collision stone childID childNum droptype
\t{"Frog", EnemyTypeID::EnemyID_Frog, -1, 1, (EFlag_DayEndMax4 | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", -1, 0, BDT_Strong},
\t{"Snek", EnemyTypeID::EnemyID_Snek, -1, 1, (EFlag_DayEndMax4 | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", -1, 0, BDT_Strong},
};
"""


def _roster(overlays):
    enums = parse_enum_header(SYNTHETIC_HEADER)
    tables = parse_info_table(SYNTHETIC_TABLE)
    payload = snapshot_payload(resolve_ids(build_entries(enums, tables)), "synthetic")
    return entries_from_payload(payload, overlays)


def _pass_gates():
    return {gate: "PASS" for gate in ADMISSION_GATES}


def _full_frog():
    return {
        "gates": _pass_gates(),
        "delivery_receipt": "corpse:frog:1 goal=1",
        "eligibility": "candidate",
    }


def _partial_snek():
    gates = _pass_gates()
    gates["death_corpse"] = "UNTESTED"
    return {
        "gates": gates,
        "delivery_receipt": "corpse:snek:1 goal=1",
        "eligibility": "candidate",
    }


def _two_identity_roster():
    return _roster({"17": _full_frog(), "41": _partial_snek()})


def placement_document_accepting_frog():
    """Minimal lane 04 document granting Frog one legal, accepted ground slot."""
    return {
        "schema": "p2-placement-v1",
        "slots": [{"uid": 401, "label": "frog-slot", "stage": 1, "terrain": "ground",
                   "radius": 300.0, "evidence": {"xyz": True, "terrain": True, "route": True}}],
        "profiles": [{"identity": "Frog", "terrains": ["ground"], "accepted_gates": ["xyz"]}],
    }


def test_fully_passed_identity_is_the_whole_seed_pool():
    roster = _two_identity_roster()
    # Frog has natural PASS on gates 1-4 + 6 and a cited receipt for gate 5.
    contract = admission_contract(roster)
    assert contract["admitted"] == [17]
    assert 41 in contract["blocking"]
    # The real seed path (randomizer.seed.generate -> resolve_placement_layout)
    # reads that exact pool.
    layout = resolve_placement_layout("seed-l02", "Player1", placement_document_accepting_frog(), roster)
    assert {binding["source_id"] for binding in layout["bindings"]} == {17}
    assert all(binding["enum_name"] == "Frog" for binding in layout["bindings"])


def test_partial_sibling_never_reaches_the_seed_pool():
    roster = _two_identity_roster()
    assert admitted_ids(roster) == [17]
    assert 41 not in admitted_ids(roster)
    assert "death_corpse" in admission_contract(roster)["blocking"][41]


def test_stripping_receipt_drops_identity_from_seed_pool():
    frog = _full_frog()
    frog["delivery_receipt"] = None
    roster = _roster({"17": frog, "41": _partial_snek()})
    # With the transport/reward receipt gone, the contract no longer passes, the
    # admitted pool is empty and the product entry point refuses to seed.
    assert admitted_ids(roster) == []
    assert "transport_reward" in admission_contract(roster)["blocking"][17]
    with pytest.raises(SeedBridgeError):
        resolve_placement_layout("seed-l02", "Player1", placement_document_accepting_frog(), roster)


def test_real_ledger_seed_pool_is_deny_by_default():
    roster = load_and_validate()
    assert admitted_ids(roster) == [23, 44, 59, 60, 61, 62]  # 44/45 Kochappy cohort; 59-62 Otakara elemental Dweevils (2026-09-15)
    # The product generator still fails closed when the placement document accepts only
    # identities outside the admitted set.
    with pytest.raises(SeedBridgeError):
        generate("seed", p2_enemies=True, p2_placement=placement_document_accepting_frog())
