"""Opt-in proxy tier for seeds: schema, generate, bridge, CLI (issue #871).

A proxy species is a P2 model + animations over a real Pikmin 1 host enemy
(P1 behaviour and combat); it is honestly NOT a six-gate P2 identity and must
never be recorded as one. This tier is strictly opt-in and data-driven off
``randomizer/p2_proxy``.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randomizer.p2_proxy import load_rows, tier_ids
from randomizer.seed import PLAYABLE_P2_SPECIES, generate, validate


def _unproven(monkeypatch):
    """Pretend no row carries probe evidence yet, whatever the committed rows say."""
    import randomizer.p2_proxy as proxy
    real = proxy.load_rows
    monkeypatch.setattr(proxy, "load_rows", lambda directory=None: [
        {key: value for key, value in row.items() if key != "evidence"}
        for row in real(directory=directory)])


def _proxy_rows_for(ids):
    by_id = {row["source_id"]: row for row in load_rows()}
    return [by_id[source_id] for source_id in ids]


def test_tier_ids_declared_vs_proven():
    rows = load_rows()
    declared = tier_ids("declared")
    assert declared == sorted(row["source_id"] for row in rows)
    assert {2} <= set(declared)
    # inst-frogs #871: Frog (17) graduated to its own identity installer.
    assert 17 not in set(declared)
    # Proven is exactly the rows that carry a probe evidence block.
    assert tier_ids("proven") == sorted(row["source_id"] for row in rows if "evidence" in row)
    assert set(tier_ids("proven")) <= set(declared)
    with pytest.raises(ValueError):
        tier_ids("bogus")


def test_row_schema_defaults_and_validation(tmp_path):
    rows = load_rows()
    by_id = {row["source_id"]: row for row in rows}
    # Catfish/Tadpole hosts are land-capable, so they accept water too.
    assert by_id[26]["terrains"] == ["ground", "water"]
    assert by_id[27]["terrains"] == ["ground", "water"]
    assert all(row["terrains"] == ["ground"] for row in rows
               if row["source_id"] not in (26, 27))
    # A row is either only declared or carries a complete, all-true evidence block.
    for row in rows:
        if "evidence" in row:
            assert row["evidence"]["markers"] == {"table": True, "bind": True, "draw": True}
    # Bad terrains fail closed.
    bad = tmp_path / "2_Chappy.json"
    bad.write_text(json.dumps({"schema": 1, "source_id": 2, "enum_name": "Chappy",
                               "host_teki": 4, "pose_limit": 4,
                               "terrains": ["lava"]}))
    with pytest.raises(ValueError, match="terrain"):
        load_rows(tmp_path)
    # Present-but-invalid evidence fails closed instead of silently declared.
    bad.write_text(json.dumps({"schema": 1, "source_id": 2, "enum_name": "Chappy",
                               "host_teki": 4, "pose_limit": 4,
                               "evidence": {"run": "", "log": "x"}}))
    with pytest.raises(ValueError, match="evidence"):
        load_rows(tmp_path)


def test_row_evidence_proven(tmp_path, monkeypatch):
    import randomizer.p2_proxy as proxy
    monkeypatch.setattr(proxy, "_roster_enums", lambda: {2: "Chappy"})
    evidence = {"run": "probe run", "log": "logs/probe.md",
                "log_sha256": "ab" * 32, "native_commit": "abc1234",
                "recorded": "2026-09-20",
                "markers": {"table": True, "bind": True, "draw": True}}
    (tmp_path / "2_Chappy.json").write_text(json.dumps(
        {"schema": 1, "source_id": 2, "enum_name": "Chappy",
         "host_teki": 4, "pose_limit": 4, "evidence": evidence}))
    rows = load_rows(tmp_path)
    assert rows[0]["evidence"]["log_sha256"] == "ab" * 32
    assert tier_ids("proven", tmp_path) == [2]
    assert tier_ids("declared", tmp_path) == [2]
    # A false marker is not proven: it fails closed at load.
    bad = dict(evidence)
    bad["markers"] = {"table": True, "bind": False, "draw": True}
    (tmp_path / "2_Chappy.json").write_text(json.dumps(
        {"schema": 1, "source_id": 2, "enum_name": "Chappy",
         "host_teki": 4, "pose_limit": 4, "evidence": bad}))
    with pytest.raises(ValueError, match="markers"):
        load_rows(tmp_path)


def test_default_path_unchanged():
    first = generate("tier-default-seed", p2_enemies=True, p2_species="playable")
    second = generate("tier-default-seed", p2_enemies=True, p2_species="playable",
                      p2_proxy_tier=None)
    assert first == second
    assert "p2_proxy_tier" not in first
    assert "p2-proxy-tier-v1" not in first["capabilities"]
    assert first["p2_layout"].get("density", "all-targets-v1") == "all-targets-v1"
    validate(first)


def test_proxy_tier_requires_p2_enemies():
    with pytest.raises(ValueError):
        generate("x", p2_proxy_tier="declared")
    with pytest.raises(ValueError):
        generate("x", p2_enemies=True, p2_proxy_tier="bogus")


def test_full_requires_a_tier():
    with pytest.raises(ValueError):
        generate("x", p2_enemies=True, p2_species="full")


def test_full_plus_proven_is_playable_plus_every_proven_row():
    manifest = generate("tier-full-proven-live", p2_enemies=True,
                        p2_proxy_tier="proven", p2_species="full")
    layout = manifest["p2_layout"]
    bound = {b["source_id"] for b in layout["bindings"]}
    assert bound | set(layout.get("unplaced", [])) == set(PLAYABLE_P2_SPECIES) | set(tier_ids("proven"))
    assert set(PLAYABLE_P2_SPECIES) <= bound
    validate(manifest)


def test_full_plus_proven_equals_playable_six(monkeypatch):
    _unproven(monkeypatch)
    manifest = generate("tier-full-proven", p2_enemies=True,
                        p2_proxy_tier="proven", p2_species="full")
    assert manifest["p2_proxy_tier"] == "proven"
    assert "p2-proxy-tier-v1" in manifest["capabilities"]
    assert {b["source_id"] for b in manifest["p2_layout"]["bindings"]} == set(PLAYABLE_P2_SPECIES)
    validate(manifest)


def test_declared_admits_chappy_frog():
    manifest = generate("tier-declared", p2_enemies=True,
                        p2_proxy_tier="declared", p2_species="full")
    bound = {b["source_id"] for b in manifest["p2_layout"]["bindings"]}
    # The declared pool overflows the ground slots, so some species land in
    # `unplaced`; the pool as a whole still covers Chappy/Tank (Frog 17 and
    # MaroFrog 18 are now their own identity via inst-frogs #871).
    # The sampler must still bind something: an empty binding list with
    # everything unplaced would pass the pool check while placement is broken.
    assert bound
    pool = bound | set(manifest["p2_layout"].get("unplaced", []))
    assert {2, 24} <= pool
    assert manifest["p2_layout"]["density"] == "sampled-v1"
    assert manifest["p2_proxy_tier"] == "declared"
    validate(manifest)


def test_explicit_proxy_ids_need_covering_tier(monkeypatch):
    _unproven(monkeypatch)
    with pytest.raises(ValueError):
        generate("x", p2_enemies=True, p2_species=[44, 2])
    with pytest.raises(ValueError):
        generate("x", p2_enemies=True, p2_proxy_tier="proven",
                 p2_species=[44, 2])
    manifest = generate("x", p2_enemies=True, p2_proxy_tier="declared",
                        p2_species=[44, 2])
    assert {b["source_id"] for b in manifest["p2_layout"]["bindings"]} == {44, 2}
    validate(manifest)


def test_manifest_round_trip_with_tier():
    manifest = generate("tier-roundtrip", p2_enemies=True,
                        p2_proxy_tier="declared",
                        p2_species=[44, 54, 59, 60, 61, 62, 2, 24])
    validate(manifest)
    loaded = json.loads(json.dumps(manifest))
    validate(loaded)
    assert loaded["p2_proxy_tier"] == "declared"
    assert loaded["p2_layout"]["density"] == "sampled-v1"


def test_proxy_binding_without_tier_key_rejected():
    manifest = generate("tier-strip", p2_enemies=True,
                        p2_proxy_tier="declared",
                        p2_species=[44, 54, 59, 60, 61, 62, 2, 24])
    stripped = json.loads(json.dumps(manifest))
    del stripped["p2_proxy_tier"]
    stripped["capabilities"] = [c for c in stripped["capabilities"]
                                if c != "p2-proxy-tier-v1"]
    with pytest.raises(ValueError):
        validate(stripped)


def test_sampled_layout_pool_larger_than_targets_reports_unplaced():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import resolve_placement_layout
    from randomizer.seed import _default_admitted_placement

    roster = load_and_validate()
    document = _default_admitted_placement()
    pool = [44, 54, 59, 60, 61, 62, 2, 24, 9, 23, 57, 78, 79]
    tiny = {"schema": document["schema"],
            "slots": document["slots"][:3],
            "profiles": document["profiles"]}
    proxy_rows = _proxy_rows_for([2, 24])
    layout = resolve_placement_layout("seed-unplaced", "Player1", tiny, roster,
                                      species=pool, proxy_rows=proxy_rows)
    assert layout["density"] == "sampled-v1"
    assert len(layout["bindings"]) == 3
    assert layout["unplaced"] == sorted(set(pool) - {b["source_id"] for b in layout["bindings"]})
    assert layout["unplaced"]


def test_sampled_assigns_playable_first():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import resolve_placement_layout, validate_layout
    from randomizer.seed import _default_admitted_placement

    roster = load_and_validate()
    document = _default_admitted_placement()
    proxy_rows = _proxy_rows_for([2, 24])
    layout = resolve_placement_layout("seed-playable-first", "Player1", document, roster,
                                      species=[*PLAYABLE_P2_SPECIES, 2, 24],
                                      proxy_rows=proxy_rows)
    bound = {b["source_id"] for b in layout["bindings"]}
    assert set(PLAYABLE_P2_SPECIES) <= bound
    validate_layout(layout, roster)


def test_sampled_uses_same_stream_without_proxy_change():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import resolve_placement_layout
    from randomizer.seed import _default_admitted_placement

    roster = load_and_validate()
    document = _default_admitted_placement()
    legacy = resolve_placement_layout("seed-stream", "Player1", document, roster,
                                      species=[44, 54])
    assert legacy["density"] == "all-targets-v1"
    assert "unplaced" not in legacy


def test_proxy_row_accepted_only_on_matching_terrain():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import _proxy_accepted_targets
    from randomizer.seed import _default_admitted_placement

    roster = load_and_validate()
    document = _default_admitted_placement()
    water_row = dict(_proxy_rows_for([2])[0])
    water_row["terrains"] = ["water"]
    accepted = _proxy_accepted_targets(document, [water_row], roster)
    assert accepted[2] == set()


def test_validate_layout_accepts_sampled_and_unplaced():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import (
        SeedBridgeError, resolve_placement_layout, validate_layout)
    from randomizer.seed import _default_admitted_placement

    roster = load_and_validate()
    document = _default_admitted_placement()
    layout = resolve_placement_layout("seed-validate", "Player1", document, roster,
                                      species=[44, 2], proxy_rows=_proxy_rows_for([2]))
    validate_layout(layout, roster)
    bad = dict(layout)
    bad["unplaced"] = [44]
    with pytest.raises(SeedBridgeError):
        validate_layout(bad, roster)


def test_bootstrap_carries_sampled_proxy_bindings():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import (
        bootstrap_for_manifest, build_bootstrap, parse_bootstrap)
    from randomizer.seed import _default_admitted_placement
    from experimental.pikmin2_seed_bridge import resolve_placement_layout

    roster = load_and_validate()
    document = _default_admitted_placement()
    layout = resolve_placement_layout("seed-boot", "Player1", document, roster,
                                      species=[44, 2], proxy_rows=_proxy_rows_for([2]))
    line = build_bootstrap(layout, roster)
    assert line.startswith("ENEMY_P2 1 ")
    assert " 2 " in f" {line} " or line.strip().endswith(" 2")
    parsed = parse_bootstrap(line, roster, density="sampled-v1")
    assert parsed["density"] == "sampled-v1"
    assert {b["source_id"] for b in parsed["bindings"]} == {44, 2}
    assert bootstrap_for_manifest({"p2_layout": layout}, roster) == line


def test_bootstrap_tier_pair_round_trip():
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import (
        SeedBridgeError, bootstrap_for_manifest, build_bootstrap,
        parse_bootstrap)
    from randomizer.seed import _default_admitted_placement
    from experimental.pikmin2_seed_bridge import resolve_placement_layout

    import pytest

    roster = load_and_validate()
    document = _default_admitted_placement()
    layout = resolve_placement_layout("seed-boot-tier", "Player1", document,
                                      roster, species=[44, 2],
                                      proxy_rows=_proxy_rows_for([2]))
    legacy = build_bootstrap(layout, roster)
    assert "P2_PROXY_TIER" not in legacy
    parsed_legacy = parse_bootstrap(legacy, roster, density="sampled-v1")
    assert "p2_proxy_tier" not in parsed_legacy
    assert {b["source_id"] for b in parsed_legacy["bindings"]} == {44, 2}
    tiered = build_bootstrap(layout, roster, proxy_tier="declared")
    assert tiered.startswith(legacy)
    assert tiered.endswith("P2_PROXY_TIER 1\n")
    parsed = parse_bootstrap(tiered, roster, density="sampled-v1")
    assert parsed["p2_proxy_tier"] is True
    assert {b["source_id"] for b in parsed["bindings"]} == {44, 2}
    assert build_bootstrap(parsed, roster) == tiered
    assert bootstrap_for_manifest(
        {"p2_layout": layout, "p2_proxy_tier": "declared"},
        roster) == tiered
    assert bootstrap_for_manifest({"p2_layout": layout}, roster) == legacy
    for bad in (legacy + "P2_PROXY_TIER 2\n",
                legacy + "P2_PROXY_TIER\n",
                legacy + "P2_PROXY_TIER 1 EXTRA\n"):
        with pytest.raises(SeedBridgeError):
            parse_bootstrap(bad, roster)


def test_cli_proxy_tier_and_full(tmp_path):
    import subprocess
    out = tmp_path / "seed.json"
    subprocess.run(
        [sys.executable, "-m", "randomizer", "generate", "--seed", "cli-tier",
         "--p2-enemies", "--p2-proxy-tier", "declared", "--p2-species", "full",
         "--output", str(out)],
        cwd=str(ROOT), check=True, capture_output=True, text=True)
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["p2_proxy_tier"] == "declared"
    validate(manifest)
