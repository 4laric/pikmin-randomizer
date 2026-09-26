"""Pool/roster/placement sync: every P2_PLAYABLE_POOL id must be admittable.

Future admissions add one row to P2_PLAYABLE_POOL; this test fails until the
same identity is also admitted in the roster evidence overlay and accepted in
the committed placement document, so the three stay in sync.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_enemy_roster import (
    admission_requirements,
    admitted_ids,
    by_id,
    load_and_validate,
)
from randomizer.seed import (
    PLAYABLE_P2_SPECIES,
    P2_PLAYABLE_POOL,
    _default_admitted_placement,
)


def test_pool_table_derives_playable_tuple_once():
    assert PLAYABLE_P2_SPECIES == tuple(row["source_id"] for row in P2_PLAYABLE_POOL)


def test_every_pool_id_is_roster_admitted_with_natural_gates():
    roster = load_and_validate()
    admitted = set(admitted_ids(roster))
    missing = [row["source_id"] for row in P2_PLAYABLE_POOL
               if row["source_id"] not in admitted]
    assert not missing, f"pool ids missing from roster admission: {missing}"
    for row in P2_PLAYABLE_POOL:
        entry = by_id(roster)[row["source_id"]]
        assert entry.eligibility == "admitted", row["source_id"]
        assert admission_requirements(entry) == [], row["source_id"]
        assert (entry.delivery_receipt or "").strip(), row["source_id"]


def test_every_pool_id_has_accepted_placement():
    from randomizer.p2_placement import audit

    document = _default_admitted_placement()
    slot_uids = {slot["uid"] for slot in document["slots"]}
    by_identity = {p["identity"]: p for p in document["profiles"]}
    admitted = audit(document)["admitted"]
    for row in P2_PLAYABLE_POOL:
        enum_name = row["enum_name"]
        assert enum_name in by_identity, enum_name
        profile = by_identity[enum_name]
        assert profile["accepted_gates"], enum_name
        assert profile.get("accepted_slot_uids"), enum_name
        assert set(profile["accepted_slot_uids"]) <= slot_uids, enum_name
        assert admitted.get(enum_name), enum_name


def test_bridge_playable_priority_mirrors_pool():
    from experimental.pikmin2_seed_bridge import PLAYABLE_IDS

    assert tuple(PLAYABLE_IDS) == tuple(PLAYABLE_P2_SPECIES)


def test_every_pool_id_maps_in_the_placement_catalog():
    from randomizer import p2_placement_catalog as catalog

    document = _default_admitted_placement()
    for row in P2_PLAYABLE_POOL:
        targets = catalog.binding_targets_for_sources(
            [row["source_id"]], document=document)
        assert targets, row["source_id"]
