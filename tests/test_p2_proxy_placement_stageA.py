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
    assert sorted(s["uid"] for s in validated["slots"]) == [1849273021, 2049888785]
    for slot in validated["slots"]:
        assert slot["proxy_only"] is True
        assert slot["evidence_level"] == placement.PROXY_EVIDENCE_LEVEL
        assert slot["evidence"] == {"xyz": True, "terrain": False, "route": False}
        assert slot["terrain"] == "ground"
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
    assert not (SINGLETONS & union_before)

    ground_rows = _proxy_rows_for([10, 11])
    accepted = _proxy_accepted_targets(document, ground_rows, roster,
                                       proxy_document=sibling)
    for source_id, tokens in accepted.items():
        assert SINGLETONS <= set(tokens)
        assert not (RESERVED & set(tokens))

    water_row = dict(_proxy_rows_for([2])[0])
    water_row["terrains"] = ["water"]
    accepted_water = _proxy_accepted_targets(document, [water_row], roster,
                                             proxy_document=sibling)
    assert accepted_water[2] == set()

    # The audit-derived union is unchanged: without the sibling the singletons
    # never appear.
    accepted_plain = _proxy_accepted_targets(document, ground_rows, roster)
    for tokens in accepted_plain.values():
        assert not (SINGLETONS & set(tokens))
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
    # Six-gate accepted sets never contain the proxy-only singletons.
    for uids in report["admitted"].values():
        assert not (SINGLETONS & {str(uid) for uid in uids})

    first = resolve_placement_layout("stageA-invariance", "Player1", document,
                                     roster, species=list(PLAYABLE_P2_SPECIES))
    second = resolve_placement_layout("stageA-invariance", "Player1", document,
                                      roster, species=list(PLAYABLE_P2_SPECIES),
                                      proxy_document=sibling)
    assert first == second
    assert all(b["target"] not in SINGLETONS for b in first["bindings"])

    manifest = generate("stageA-parity", p2_enemies=True, p2_species="playable")
    manifest_none = generate("stageA-parity", p2_enemies=True,
                             p2_species="playable", p2_proxy_tier=None)
    assert manifest == manifest_none
    assert "p2_proxy_tier" not in manifest
    assert manifest["p2_layout"].get("density", "all-targets-v1") == "all-targets-v1"
    assert all(b["target"] not in SINGLETONS for b in manifest["p2_layout"]["bindings"])
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

    # Six-gate identities are never placed on the new singleton slots.
    for binding in layout["bindings"]:
        if binding["target"] in SINGLETONS:
            assert binding["source_id"] not in set(PLAYABLE_P2_SPECIES)

    grown = _synthetic_65_document()
    with pytest.raises(SeedBridgeError):
        resolve_placement_layout("stageA-65", "Player1", grown, roster,
                                 species=[44, 2],
                                 proxy_rows=_proxy_rows_for([2]))


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
    """With more species than targets every target carries a distinct species."""
    from collections import Counter
    from randomizer.seed import generate
    for seed in ("distinct-a", "distinct-b", "distinct-c"):
        layout = generate(seed, "solo", "Player1", p2_enemies=True, p2_species="full",
                          p2_proxy_tier="declared")["p2_layout"]
        counts = Counter(binding["source_id"] for binding in layout["bindings"])
        pool = len(counts) + len(layout.get("unplaced", []))
        assert pool > len(layout["bindings"]), "test needs a pool larger than the target set"
        assert len(counts) == len(layout["bindings"]), {k: v for k, v in counts.items() if v > 1}
