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


def test_roster_admission_equals_pool():
    # Roster-follows-admission (#888): admitted == pool, so a bare
    # ``--p2-enemies`` seed never sees an admitted identity with no slot.
    roster = load_and_validate()
    assert set(admitted_ids(roster)) == set(PLAYABLE_P2_SPECIES)


def test_placement_accepts_exactly_the_pool():
    document = _default_admitted_placement()
    pool_enums = {row["enum_name"] for row in P2_PLAYABLE_POOL}
    accepted = {p["identity"] for p in document["profiles"] if p["accepted_gates"]}
    assert accepted == pool_enums


def test_no_check_species_are_excluded_everywhere():
    # Owner decision (#888): unkillable enemies carry no Archipelago check.
    from randomizer.p2_proxy import NO_CHECK_SOURCE_IDS, tier_ids

    roster = by_id(load_and_validate())
    for source_id in NO_CHECK_SOURCE_IDS:
        assert roster[source_id].eligibility == "excluded", source_id
        assert source_id not in PLAYABLE_P2_SPECIES, source_id
    for tier in ("proven", "declared"):
        assert not NO_CHECK_SOURCE_IDS & set(tier_ids(tier)), tier


def test_bare_p2_enemies_seed_generates():
    from randomizer.seed import generate

    manifest = generate("sync-bare-p2", p2_enemies=True)
    bound = {b["source_id"] for b in manifest["p2_layout"]["bindings"]}
    assert bound <= set(PLAYABLE_P2_SPECIES)


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


def test_p1_duplicates_are_withdrawn_everywhere():
    # Owner ruling 2026-10-01: "i rule the duplicates are withdrawals".
    # 0 Pelplant, 1 Kochappy, 29 Mar and the red/yellow/blue Candypop Buds
    # (3/4/5) duplicate P1; purple/white/random buds (6/7/8) do not.
    from randomizer.p2_proxy import WITHDRAWN_SOURCE_IDS, tier_ids

    assert WITHDRAWN_SOURCE_IDS == {0, 1, 3, 4, 5, 29}
    roster = by_id(load_and_validate())
    for source_id in WITHDRAWN_SOURCE_IDS:
        assert roster[source_id].eligibility == "excluded", source_id
        assert source_id not in PLAYABLE_P2_SPECIES, source_id
    for source_id in (6, 7, 8):
        assert roster[source_id].eligibility != "excluded", source_id
    for tier in ("proven", "declared"):
        assert not WITHDRAWN_SOURCE_IDS & set(tier_ids(tier)), tier
