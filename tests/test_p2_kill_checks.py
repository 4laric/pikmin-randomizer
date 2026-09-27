"""P2 enemy kills are not AP locations (lane rd-p2ap-kill-checks, #134).

Decision (a): on a playable-pool P2 seed every campaign generator for the
five replaced P1 host species (4 Spotty Bulborb, 15 Fiery Blowhog, 17
Armored Cannon Beetle, 24 Mamuta, 32 Spotty Bulbear) is P2-bound, but the
binds keep the host Teki type (native modules fail closed on mismatch;
gameplay stays P1), so kills and Onion corpse deliveries arrive in
checks.txt as ordinary host-species indices. The location set and fill are
therefore identical to a non-P2 seed and the runner needs no P2 mapping.
"""
from collections import Counter

from randomizer.catalog import (
    ITEM_IDS,
    MODERN_LOCATION_IDS,
    active_names,
    bestiary_sources,
    can_reach_manifest,
    item_pool,
)
from randomizer.campaign_data import CAMPAIGN_SLOTS
from randomizer.runner import NativeRun
from randomizer.seed import (
    PLAYABLE_P2_SPECIES,
    _default_admitted_placement,
    generate,
    solo_rewards,
    spheres,
    validate,
)
from randomizer.session import Session

SEED = "12345"
# Delivery checks whose host species are fully P2-bound in a playable seed.
AFFECTED = {
    "Bestiary: Deliver Spotty Bulborb": 4,
    "Bestiary: Deliver Fiery Blowhog": 15,
    "Bestiary: Deliver Armored Cannon Beetle": 17,
    "Bestiary: Deliver Mamuta": 24,
    "Bestiary: Deliver Spotty Bulbear": 32,
}


def playable_manifest(mode="solo"):
    manifest = generate(SEED, mode, p2_enemies=True, p2_species="playable")
    validate(manifest)
    return manifest


def test_playable_pool_binds_all_playable_species():
    manifest = playable_manifest()
    assert {b["source_id"] for b in manifest["p2_layout"]["bindings"]} == set(PLAYABLE_P2_SPECIES)


def test_location_set_ignores_p2_kills():
    manifest = playable_manifest()
    plain = generate(SEED, collection_checks=True)
    validate(plain)
    # Same modern schema-9 catalog with or without P2: no P2 location ids.
    assert manifest["schema"] == plain["schema"] == 9
    assert manifest["locations"] == plain["locations"]
    assert set(manifest["locations"]) == set(active_names(manifest))
    assert all(MODERN_LOCATION_IDS[name] == code for name, code in manifest["locations"].items())
    assert "p2-enemy-bridge-v1" in manifest["capabilities"]


def test_every_location_reachable_on_playable_seed():
    manifest = playable_manifest()
    assert len(manifest["locations"]) == 62
    assert sum(map(len, spheres(solo_rewards(manifest), manifest))) == 62


def test_replaced_hosts_keep_all_delivery_checks_reachable():
    manifest = playable_manifest()
    bound = {b["target"] for b in manifest["p2_layout"]["bindings"]}
    by_uid = {str(row["uid"]): row for row in CAMPAIGN_SLOTS}
    assert bound and bound <= set(by_uid)
    totals = Counter((row["stage"], row["original"]) for row in CAMPAIGN_SLOTS)
    hits = Counter((row["stage"], row["original"]) for row in CAMPAIGN_SLOTS if str(row["uid"]) in bound)
    for name, species in AFFECTED.items():
        stages = {stage for (stage, original) in totals if original == species}
        assert stages, name
        assert all(hits[(stage, species)] == totals[(stage, species)] for stage in stages), name
        assert name in manifest["locations"], name
        assert bestiary_sources(name, manifest), name
    full = Counter({name: 99 for name in ITEM_IDS})
    for name in AFFECTED:
        assert can_reach_manifest(name, full, manifest), name
    # Every bound slot keeps a corpse route home, so deliveries stay physical.
    doc_slots = {str(slot["uid"]): slot for slot in _default_admitted_placement()["slots"]}
    assert bound <= set(doc_slots)
    assert all(doc_slots[target]["corpse_route"] for target in bound)


def test_fill_pool_unchanged_by_p2():
    manifest = playable_manifest()
    plain = generate(SEED, collection_checks=True)
    assert sorted(item_pool(manifest)) == sorted(item_pool(plain))
    assert len(item_pool(manifest)) == len(active_names(manifest))


def test_runner_maps_host_receipts_from_p2_replaced_slots(tmp_path):
    manifest = playable_manifest()
    session = Session(manifest, tmp_path / "session")
    run = NativeRun(session)
    (run.directory / "hello.txt").write_text(" ".join(
        ["PIKMIN_HELLO", str(manifest["schema"]), run.token, session.fingerprint,
         *manifest["capabilities"], "END"]), encoding="ascii")
    names = active_names(manifest)
    wanted = list(AFFECTED) + [names[0], names[-1]]
    (run.directory / "checks.txt").write_text(
        "".join(f"{names.index(name)}\n" for name in wanted), encoding="ascii")
    # P2 economy side-channels the runner never reads must not disturb polling.
    (run.directory / "treasure-receipt.txt").write_text("treasure=none count=1 pokos=0\n", encoding="ascii")
    (run.directory / "native.log").write_text("[Pikipelago] P2_POD_RECEIPT id=corpse:uji:1 value=2 new=1 pokos=2 seeds=0\n", encoding="ascii")
    run.poll()
    assert session.data["checked"] == wanted
    # Every collected receipt already maps to an AP location id.
    assert all(name in manifest["locations"] for name in session.data["checked"])
    reloaded = Session(manifest, tmp_path / "session")
    assert reloaded.data["checked"] == wanted
