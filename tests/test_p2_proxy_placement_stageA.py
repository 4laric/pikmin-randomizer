"""Stage-A proxy-tier-only placement expansion (issue #871).

Covers the sibling document, the proxy-union extension, six-gate invariance,
the 64-binding fail-closed guard, reserved-vanilla exclusion and generate parity.
No game, no ISO, no native build.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randomizer import p2_placement as placement
from randomizer.seed import (
    PLAYABLE_P2_SPECIES,
    _default_admitted_placement,
    generate,
    validate,
)

SINGLETONS = {"1849273021", "2049888785"}
PACKS = {"3768801221", "2637843033", "517610653", "2380387682", "3679976242",
         "1102975523", "3417529495", "1428724902", "648204418", "3157218646",
         "843459898", "1340027046", "2158371058", "4096115722"}
PROXY_ONLY = SINGLETONS | PACKS
# Placement-cap (#871): the 2 former proxy singletons above are now SHARED
# admitted slots (all 49 ground slots covered: 33 admitted-exclusive + 14
# proxy-exclusive + 2 shared), so six-gate sets legitimately contain them.
# PROXY_EXCLUSIVE is the still-exclusive remainder.
SHARED = {"1849273021", "2049888785"}
PROXY_EXCLUSIVE = PROXY_ONLY - SHARED
PACK_HOSTS = [0, 3, 18, 19, 20, 25, 31, 33]
RESERVED = set()  # no committed slot is reserved from proxies (see PROXY_RESERVED_VANILLA)


def _sibling():
    path = ROOT / "docs" / "PIKMIN2_PROXY_PLACEMENT.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _proxy_rows_for(ids):
    from randomizer.p2_proxy import load_rows

    by_id = {row["source_id"]: row for row in load_rows()}
    return [by_id[source_id] for source_id in ids]


def test_validate_proxy_document_accepts_sibling():
    doc = _sibling()
    validated = placement.validate_proxy_document(doc)
    assert validated["schema"] == placement.PROXY_SCHEMA
    assert sorted(s["uid"] for s in validated["slots"]) == sorted(
        int(uid) for uid in PROXY_ONLY)
    assert sorted(validated["pack_hosts"]) == sorted(placement.PACK_HOSTS)
    for slot in validated["slots"]:
        assert slot["terrain"] == "ground"
        if str(slot["uid"]) in SHARED:
            # Shared with the admitted doc and native-probed (doc-reconcile #871).
            assert slot["proxy_only"] is False
            assert slot["evidence"] == {"xyz": True, "terrain": True, "route": True}
        else:
            assert slot["proxy_only"] is True
            assert slot["evidence"] == {"xyz": True, "terrain": False, "route": False}
        if str(slot["uid"]) in PACKS:
            assert slot["pack"] is True
            assert slot["evidence_level"] == placement.PROXY_PACK_EVIDENCE_LEVEL
            expected = placement.PACK_TARGETS[slot["uid"]]
            assert slot["count"] == expected[3]
            assert slot["original_teki"] == expected[2]
            assert slot["first_day"] == expected[4]
        else:
            assert slot["pack"] is False
            assert slot["evidence_level"] == placement.PROXY_SHARED_EVIDENCE_LEVEL
            assert "count" not in slot
            assert "original_teki" not in slot
    assert sorted(validated["reserved_vanilla"]) == sorted(
        list(placement.PROXY_RESERVED_VANILLA))


def test_validate_proxy_document_rejects_bad_docs():
    good = _sibling()
    # A p2-placement-v1 doc is never a proxy doc.
    committed = _default_admitted_placement()
    with pytest.raises(ValueError):
        placement.validate_proxy_document(committed)
    # Slot with probed terrain/route is dishonest.
    bad = copy.deepcopy(good)
    bad["slots"][0]["evidence"]["terrain"] = True
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    bad = copy.deepcopy(good)
    bad["slots"][1]["evidence"]["route"] = True
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # A third uid is rejected.
    bad = copy.deepcopy(good)
    extra = copy.deepcopy(bad["slots"][0])
    extra["uid"] = 12345
    bad["slots"].append(extra)
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # Missing pack_hosts is rejected.
    bad = copy.deepcopy(good)
    del bad["pack_hosts"]
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # Altered pack_hosts is rejected.
    bad = copy.deepcopy(good)
    bad["pack_hosts"] = [3]
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # Pack slot with singleton evidence_level is rejected.
    bad = copy.deepcopy(good)
    for slot in bad["slots"]:
        if slot.get("pack") is True:
            slot["evidence_level"] = placement.PROXY_SHARED_EVIDENCE_LEVEL
            break
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # Pack slot with wrong count is rejected.
    bad = copy.deepcopy(good)
    for slot in bad["slots"]:
        if slot.get("pack") is True:
            slot["count"] += 1
            break
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # Singleton carrying count is rejected.
    bad = copy.deepcopy(good)
    for slot in bad["slots"]:
        if slot.get("pack") is False:
            slot["count"] = 1
            break
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # Missing proxy_only is rejected.
    bad = copy.deepcopy(good)
    del bad["slots"][0]["proxy_only"]
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)
    # Altered evidence_level is rejected.
    bad = copy.deepcopy(good)
    bad["slots"][0]["evidence_level"] = "probed"
    with pytest.raises(ValueError):
        placement.validate_proxy_document(bad)


def test_proxy_accepted_targets_extends_only_ground_proxies():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import (
        _accepted_placement_targets,
        _proxy_accepted_targets,
    )

    roster = load_and_validate()
    document = _default_admitted_placement()
    sibling = _sibling()
    union_before = set()
    for tokens in _accepted_placement_targets(document, roster).values():
        union_before.update(tokens)
    # Placement-cap shares the 2 singletons (see SHARED); no other singleton
    # may appear in six-gate admission.
    assert not ((SINGLETONS - SHARED) & union_before)
    assert SHARED <= union_before

    ground_rows = _proxy_rows_for([10, 11])
    accepted = _proxy_accepted_targets(document, ground_rows, roster,
                                       proxy_document=sibling)
    for source_id, tokens in accepted.items():
        assert SINGLETONS <= set(tokens)
        assert PACKS <= set(tokens)
        assert not (RESERVED & set(tokens))

    # Pack targets admit only small-host rows: a large-host ground row (id 42,
    # host_teki 4 BlueChappy) sees the singletons but none of the packs.
    # (SnakeCrow id 34 used to serve here; it is now own-identity, inst-worms.
    # Chappy id 2 served before that; also own-identity now, inst-chappy.)
    large_rows = _proxy_rows_for([42])
    assert large_rows[0]["host_teki"] not in PACK_HOSTS
    accepted_large = _proxy_accepted_targets(document, large_rows, roster,
                                             proxy_document=sibling)
    assert SINGLETONS <= set(accepted_large[42])
    assert not (PACKS & set(accepted_large[42]))

    water_row = dict(_proxy_rows_for([42])[0])
    water_row["terrains"] = ["water"]
    accepted_water = _proxy_accepted_targets(document, [water_row], roster,
                                             proxy_document=sibling)
    assert accepted_water[42] == set()

    # The audit-derived union is extended only by the shared singletons:
    # without the sibling the exclusive singletons never appear (there are
    # none left; both singletons are shared), and reserved behaviour is old.
    accepted_plain = _proxy_accepted_targets(document, ground_rows, roster)
    for tokens in accepted_plain.values():
        assert not ((SINGLETONS - SHARED) & set(tokens))
        assert SHARED <= set(tokens)
        # Reserved slots are still available without the sibling (old behaviour).
        assert RESERVED <= set(tokens)


def test_six_gate_invariance_and_no_tier_byte_identical():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import resolve_placement_layout

    roster = load_and_validate()
    document = _default_admitted_placement()
    sibling = _sibling()
    report = placement.audit(document)
    assert set(report["admitted"]) >= {"BlueKochappy", "Miulin"}
    # Six-gate accepted sets never contain any proxy-EXCLUSIVE slot (the 2
    # shared singletons are legitimately admitted; see SHARED above).
    for uids in report["admitted"].values():
        assert not (PROXY_EXCLUSIVE & {str(uid) for uid in uids})

    first = resolve_placement_layout("stageA-invariance", "Player1", document,
                                     roster, species=list(PLAYABLE_P2_SPECIES))
    second = resolve_placement_layout("stageA-invariance", "Player1", document,
                                      roster, species=list(PLAYABLE_P2_SPECIES),
                                      proxy_document=sibling)
    assert first == second
    assert all(b["target"] not in PROXY_EXCLUSIVE for b in first["bindings"])

    manifest = generate("stageA-parity", p2_enemies=True, p2_species="playable")
    manifest_none = generate("stageA-parity", p2_enemies=True,
                             p2_species="playable", p2_proxy_tier=None)
    assert manifest == manifest_none
    assert "p2_proxy_tier" not in manifest
    # #893: a no-tier pool that outgrows the slots is sampled (sampled-v1);
    # either way it never reaches the proxy-only slots (checked below).
    assert manifest["p2_layout"].get("density", "all-targets-v1") in ("all-targets-v1", "sampled-v1")
    assert all(b["target"] not in PROXY_EXCLUSIVE for b in manifest["p2_layout"]["bindings"])
    validate(manifest)


def _synthetic_65_document():
    slots = []
    for index in range(65):
        uid = 1000 + index
        slots.append({
            "uid": uid,
            "label": f"synth_{index}",
            "stage": 1,
            "terrain": "ground",
            "radius": 100.0,
            "corpse_route": True,
            "burrow_ground": True,
            "evidence": {"xyz": True, "terrain": True, "route": True},
        })
    profiles = []
    for identity in ("BlueKochappy", "Chappy"):
        profiles.append({
            "identity": identity,
            "terrains": ["ground"],
            "accepted_gates": ["placement.xyz"],
            "accepted_slot_uids": [slot["uid"] for slot in slots],
        })
    return placement.validate_document(
        {"schema": placement.SCHEMA, "slots": slots, "profiles": profiles})


def test_sampler_cap_and_reserved_and_sorted():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import (
        SeedBridgeError,
        resolve_placement_layout,
    )

    roster = load_and_validate()
    document = _default_admitted_placement()
    sibling = _sibling()
    proxy_rows = _proxy_rows_for([10, 11])
    layout = resolve_placement_layout("stageA-sampled", "Player1", document,
                                      roster, species=[44, 54, 10, 11],
                                      proxy_rows=proxy_rows,
                                      proxy_document=sibling)
    assert layout["density"] == "sampled-v1"
    assert len(layout["bindings"]) <= 64
    targets = [b["target"] for b in layout["bindings"]]
    assert len(targets) == len(set(targets))
    assert targets == sorted(targets, key=lambda item: (len(item), item))
    if "unplaced" in layout:
        assert layout["unplaced"] == sorted(layout["unplaced"])
        bound_ids = {b["source_id"] for b in layout["bindings"]}
        assert not (set(layout["unplaced"]) & bound_ids)
    by_target = {b["target"]: b["source_id"] for b in layout["bindings"]}
    for reserved_target in RESERVED:
        if reserved_target in by_target:
            assert by_target[reserved_target] in set(PLAYABLE_P2_SPECIES)

    # Six-gate identities are never placed on the proxy-EXCLUSIVE slots (the
    # 2 shared singletons are legitimately admitted; see SHARED above).
    for binding in layout["bindings"]:
        if binding["target"] in PROXY_EXCLUSIVE:
            assert binding["source_id"] not in set(PLAYABLE_P2_SPECIES)

    grown = _synthetic_65_document()
    with pytest.raises(SeedBridgeError):
        resolve_placement_layout("stageA-65", "Player1", grown, roster,
                                 species=[44, 10],
                                 proxy_rows=_proxy_rows_for([10]))


def test_pack_targets_only_bind_small_hosts():
    """Guarantee: pack uids never bind a large/dangerous-host proxy species.

    The sampler places as many distinct eligible species as the pack-host rule
    allows; a pack target whose small-host pool is exhausted stays a repeat of
    an already-placed small-host species, never a large-host species. What is
    NOT guaranteed: 49 distinct species on every seed (only 20 declared proxy
    rows are small-host eligible on packs, so wide pools still leave species
    in `unplaced`).
    """
    from randomizer.seed import generate
    from randomizer.p2_proxy import load_rows

    host_by_id = {row["source_id"]: row["host_teki"] for row in load_rows()}
    for seed in ("pack-host-a", "pack-host-b"):
        layout = generate(seed, "solo", "Player1", p2_enemies=True, p2_species="full",
                          p2_proxy_tier="proven")["p2_layout"]
        by_target = {b["target"]: b["source_id"] for b in layout["bindings"]}
        assert PACKS & set(by_target), f"seed {seed} bound no pack targets"
        for uid in PACKS & set(by_target):
            assert host_by_id[by_target[uid]] in PACK_HOSTS


def test_sampled_fill_prefers_unplaced_eligible_over_repeats():
    """Guarantee: every binding's species is eligible for its target, and
    pack targets only ever bind small-host species.

    Pool (8 playable + 10 pool identities + all 17 declared proxies) fits
    the 35-slot base document exactly: placement-cap admitted 2 more slots,
    so the exact-fit pool is 8 playable + 10 more pool identities
    (Chappy/Uji/Sarai/Sokkuri) + 2 small-host + 15 large-host proxies = 35.
    The sibling layout (49 targets) still needs repeats, and which species
    the sampler repeats there is pool-sensitive (not an invariant), so this
    pins the real guarantees instead: eligibility soundness on every
    binding, the pack small-host rule, the exact-fit boundary on both
    layouts, and distinctness plus pool conservation on the base layout.
    """
    from collections import Counter
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import (
        _accepted_placement_targets,
        _proxy_accepted_targets,
        resolve_placement_layout,
    )
    from randomizer.p2_proxy import load_rows
    from randomizer.seed import _default_admitted_placement

    roster = load_and_validate()
    document = _default_admitted_placement()
    sibling = _sibling()
    rows = load_rows()
    small_ids = [row["source_id"] for row in rows if row["host_teki"] in PACK_HOSTS]
    large_ids = [row["source_id"] for row in rows if row["host_teki"] not in PACK_HOSTS]
    # All 38 own-identity species left the proxy tier for their own
    # installers (integ #871), so this pins the declared shape, not a
    # universal constant: 2 small-host proxies (10 Wealthy, 11 Fart) + 15
    # large-host proxies remain.
    assert len(small_ids) == 2 and len(large_ids) == 15
    assert sorted(small_ids) == [10, 11]
    for finished in (2, 33, 35, 43, 53, 67, 76,
                     12, 13, 14, 28, 68, 94,
                     17, 18, 24, 25, 15, 75,
                     56, 63, 69,
                     34, 70, 65, 71, 101,
                     26, 27, 66, 84, 93, 97):
        assert finished not in small_ids + large_ids
    pool = [44, 54, 59, 60, 61, 62, 10, 11] + large_ids
    # Twelve more pool identities (admitted, non-proxy) bring the pool to the
    # exact 35-slot fit: 8 playable + 10 pool + 17 proxies = 35.
    pool = pool + [2, 33, 35, 43, 53, 67, 76, 12, 13, 14, 23, 79]
    assert len(pool) == 35 and len(set(pool)) == 35
    proxy_rows = [row for row in rows if row["source_id"] in set(pool)]
    for seed in ("norepeat-a", "norepeat-b", "norepeat-c"):
        layout = resolve_placement_layout(
            seed, "Player1", document, roster, species=pool,
            proxy_rows=proxy_rows, proxy_document=sibling)
        counts = Counter(b["source_id"] for b in layout["bindings"])
        repeats = {source_id for source_id, count in counts.items() if count > 1}
        assert repeats, "the 35-species pool cannot fill 49 targets distinctly"
        # The declared pool fits the sibling layout's non-pack slots exactly
        # now (see docstring): nothing is unplaced here.
        assert not layout.get("unplaced", []), (seed, layout.get("unplaced"))
        accepted = _accepted_placement_targets(document, roster)
        proxy_accepted = _proxy_accepted_targets(document, proxy_rows, roster,
                                                 proxy_document=sibling)
        eligible = {}
        for target in {b["target"] for b in layout["bindings"]}:
            ids = {source_id for source_id, tokens in accepted.items()
                   if source_id in set(pool) and target in tokens}
            ids |= {source_id for source_id, tokens in proxy_accepted.items()
                    if source_id in set(pool) and target in tokens}
            eligible[target] = ids
        for binding in layout["bindings"]:
            assert binding["source_id"] in eligible[binding["target"]], (
                seed, binding["target"], binding["source_id"])
            if binding["target"] in PACKS:
                assert binding["source_id"] in small_ids, (
                    seed, binding["target"], binding["source_id"])
        # The same pool fits the 35-slot base document exactly (8 playable
        # + 10 pool + 17 proxies = 35): nothing is unplaced, every
        # binding is distinct (no repeat steals a slot), and nothing in
        # the pool is lost.
        base = resolve_placement_layout(
            seed, "Player1", document, roster, species=pool,
            proxy_rows=proxy_rows)
        base_unplaced = set(base.get("unplaced", []))
        assert not base_unplaced, (seed, base_unplaced)
        # The #901 held-part layer binds holder slots from its own stream
        # after the ordinary fill; count the ordinary fill only.
        held = {row["target"] for row in base.get("held_parts", {}).get("placed", [])}
        base_ordinary = [b for b in base["bindings"] if b["target"] not in held]
        base_counts = Counter(b["source_id"] for b in base_ordinary)
        assert all(count == 1 for count in base_counts.values()), (
            seed, base_counts)
        assert {b["source_id"] for b in base_ordinary} == set(pool), (
            seed, base_unplaced)


def test_generate_parity_with_declared_dwarf_hosts():
    manifest_plain = generate("stageA-gen", p2_enemies=True, p2_species="playable")
    assert "p2_proxy_tier" not in manifest_plain
    manifest = generate("stageA-gen", p2_enemies=True,
                        p2_proxy_tier="declared", p2_species=[10, 11])
    assert manifest["p2_proxy_tier"] == "declared"
    assert "p2-proxy-tier-v1" in manifest["capabilities"]
    assert manifest["p2_layout"]["density"] == "sampled-v1"
    assert {10, 11} <= {b["source_id"] for b in manifest["p2_layout"]["bindings"]}
    validate(manifest)


def test_sampled_layout_never_wastes_a_slot_on_a_repeat():
    """With more species than targets every target carries a distinct species,
    except where the pack rule forces small-host repeats.

    The 14 pack targets only accept the 2 small-host proxies (10/11), so
    repeats there are required, not wasted. Non-pack targets must still be
    pairwise distinct.
    """
    from collections import Counter
    from randomizer.p2_proxy import load_rows
    from randomizer.seed import generate
    host_by_id = {row["source_id"]: row["host_teki"] for row in load_rows()}
    for seed in ("distinct-a", "distinct-b", "distinct-c"):
        layout = generate(seed, "solo", "Player1", p2_enemies=True, p2_species="full",
                          p2_proxy_tier="declared")["p2_layout"]
        counts = Counter(binding["source_id"] for binding in layout["bindings"])
        pool = len(counts) + len(layout.get("unplaced", []))
        assert pool > len(layout["bindings"]), "test needs a pool larger than the target set"
        pack_counts = Counter()
        plain_counts = Counter()
        # #901: a held-part holder slot draws from the roster-admitted pool
        # only; the unplaced species here are proxies it cannot host, so a
        # repeat there is not a wasted slot.
        held = {row["target"] for row in layout.get("held_parts", {}).get("placed", [])}
        for binding in layout["bindings"]:
            if binding["target"] in held:
                continue
            (pack_counts if binding["target"] in PACKS else plain_counts)[binding["source_id"]] += 1
        assert len(plain_counts) == sum(plain_counts.values()), (
            {k: v for k, v in plain_counts.items() if v > 1})
        assert set(pack_counts) <= {10, 11}, dict(pack_counts)
        for source_id in pack_counts:
            assert host_by_id[source_id] in PACK_HOSTS, source_id
