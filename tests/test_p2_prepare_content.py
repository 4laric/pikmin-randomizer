"""Unit tests for scripts/p2_prepare_content.py (no ISO reads).

Covers the path/binding logic only: actor derivation from a seed manifest,
playable-first ordering, supported/unsupported splits, output-dir guards, CLI
pairing validation, and orchestration with stubbed extractors. Real ISO
extraction is proven by the staged run, not here.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import p2_prepare_content as prepare


def manifest_with(*targets):
    return {"p2_layout": {"bindings": [
        {"target": t, "source_id": 44 + i, "enum_name": "BlueKochappy"}
        for i, t in enumerate(targets)]}, }


def test_actor_bindings_derive_generator_from_uid():
    bindings = prepare.actor_bindings_for_manifest(manifest_with("5465461", "328297937"))
    assert bindings == {"5465461": 5465461, "328297937": 328297937}


def test_actor_bindings_require_p2_layout():
    with pytest.raises(ValueError):
        prepare.actor_bindings_for_manifest({"seed": "x"})
    with pytest.raises(ValueError):
        prepare.actor_bindings_for_manifest({"p2_layout": {"bindings": []}})


def test_actor_bindings_reject_bad_targets():
    with pytest.raises(ValueError):
        prepare.actor_bindings_for_manifest(manifest_with("not a uid!"))
    with pytest.raises(ValueError):
        prepare.actor_bindings_for_manifest(manifest_with("4294967296"))  # > uint32


def test_order_source_ids_playable_first():
    assert prepare.order_source_ids([23, 60, 9, 44, 54]) == [44, 54, 60, 9, 23]


def test_split_supported_reports_installerless_ids():
    # Which ids have a family installer moves as installers land (#442), so derive it.
    from experimental.pikmin2_family_install import IDENTITY_FAMILY
    ids = [44, 54, 59, 9, 23, 57, 78, 79]
    supported, unsupported = prepare.split_supported(ids)
    assert supported + unsupported == prepare.order_source_ids(ids)
    assert set(supported) == {i for i in ids if i in IDENTITY_FAMILY}
    assert set(unsupported) == {i for i in ids if i not in IDENTITY_FAMILY}
    assert 44 in supported


def test_content_dir_for_uses_enum_names(tmp_path):
    assert prepare.content_dir_for(tmp_path, 44) == tmp_path / "BlueKochappy"
    assert prepare.content_dir_for(tmp_path, 54) == tmp_path / "Miulin"
    with pytest.raises(ValueError):
        prepare.content_dir_for(tmp_path, 999)


def test_prepare_refuses_nonempty_out(tmp_path, monkeypatch):
    iso = tmp_path / "game.iso"
    iso.write_bytes(b"fake")
    out = tmp_path / "content"
    out.mkdir()
    (out / "stale.txt").write_text("stale")
    monkeypatch.setattr(prepare, "extract_miulin", lambda *a, **k: None)
    with pytest.raises(ValueError):
        prepare.prepare_content_root(iso, out, wanted=[54])


def test_prepare_missing_iso(tmp_path):
    with pytest.raises(ValueError):
        prepare.prepare_content_root(tmp_path / "missing.iso", tmp_path / "out",
                                     wanted=[54])


def test_prepare_orchestrates_playable_first_with_stubs(tmp_path, monkeypatch):
    iso = tmp_path / "game.iso"
    iso.write_bytes(b"fake")
    out = tmp_path / "content"
    calls = []

    def fake_blue(iso_arg, research, dest, pose_limit=3):
        calls.append(44)
        target = Path(dest) / "BlueKochappy"
        (target / "bank").mkdir(parents=True)
        (target / "profile").mkdir(parents=True)
        return target

    def fake_miulin(iso_arg, dest, pose_limit=3):
        calls.append(54)
        target = Path(dest) / "Miulin"
        target.mkdir(parents=True)
        return target

    def fake_dweevil(iso_arg, repo, dest, pose_limit=3):
        calls.append("dweevil")
        for enum in ("FireOtakara", "WaterOtakara", "GasOtakara", "ElecOtakara"):
            (Path(dest) / enum).mkdir(parents=True)
        return [Path(dest) / e for e in ("FireOtakara",)]

    def fake_sarai(iso_arg, dest):
        calls.append(23)
        target = Path(dest) / "Sarai"
        target.mkdir(parents=True)
        return target

    monkeypatch.setattr(prepare, "extract_bluekochappy", fake_blue)
    monkeypatch.setattr(prepare, "extract_miulin", fake_miulin)
    monkeypatch.setattr(prepare, "extract_dweevil", fake_dweevil)
    def fake_kogane(iso_arg, dest):
        calls.append(9)
        target = Path(dest) / "Kogane"
        target.mkdir(parents=True)
        return target

    monkeypatch.setattr(prepare, "extract_sarai", fake_sarai)
    monkeypatch.setattr(prepare, "extract_kogane", fake_kogane)
    monkeypatch.setattr(prepare, "extract_minihoudai", lambda iso_arg, dest, pose_limit=3: calls.append(78))

    summary = prepare.prepare_content_root(iso, out, wanted=[23, 60, 9, 44, 54, 78])
    # Playable first (44, 54, 60), then the supported admitted ids in order.
    assert calls[0] == 44 and calls[1] == 54 and calls[2] == "dweevil"
    assert set(calls[3:]) == {9, 23, 78}
    assert summary["extracted"] == [9, 23, 44, 54, 60, 78]
    assert summary["skipped"] == []
    assert (out / "prepared.json").is_file()
    assert (out / "BlueKochappy").is_dir() and (out / "Miulin").is_dir()


def test_actors_for_manifest_file_roundtrip(tmp_path):
    manifest = tmp_path / "seed.json"
    manifest.write_text(json.dumps(manifest_with("5465461")))
    actors_out = tmp_path / "actors.json"
    bindings = prepare.actors_for_manifest_file(manifest, actors_out)
    assert bindings == {"5465461": 5465461}
    assert json.loads(actors_out.read_text()) == {"5465461": 5465461}


def test_cli_requires_paired_actor_args():
    with pytest.raises(SystemExit):
        prepare.main(["--iso", "a.iso", "--out", "o",
                      "--seed-manifest", "m.json"])
    with pytest.raises(SystemExit):
        prepare.main(["--iso", "a.iso", "--out", "o",
                      "--actors-out", "a.json"])


def test_cli_rejects_bad_pose_limit():
    with pytest.raises(SystemExit):
        prepare.main(["--iso", "a.iso", "--out", "o", "--pose-limit", "99"])


def test_docstring_bullets_match_extractors():
    """The module docstring must document exactly the wired extractors.

    This docstring has gone stale twice, both times on the day a species landed
    (7a165697, then again when Sokkuri was wired), and both times it asserted
    the opposite of the truth: that a wired species had no extractor. A reader
    trusting it would go looking in the wrong file. The bullet list is the one
    part that has to be maintained by hand, so it is the part under test.
    """
    import re

    bullets = set()
    for line in prepare.__doc__.splitlines():
        match = re.match(r"\* (\d+(?:-\d+)?) ", line.strip())
        if not match:
            continue
        token = match.group(1)
        if "-" in token:
            first, last = (int(part) for part in token.split("-"))
            bullets.update(range(first, last + 1))
        else:
            bullets.add(int(token))

    wired = set(prepare.EXTRACTORS) - set(prepare.PROXY_SOURCE_IDS)
    assert bullets == wired, (
        f"docstring documents {sorted(bullets)} but non-proxy EXTRACTORS wires "
        f"{sorted(wired)}; undocumented={sorted(wired - bullets)}, "
        f"stale={sorted(bullets - wired)}"
    )
    assert "randomizer/p2_proxy" in prepare.__doc__


def test_every_wired_extractor_has_a_dispatch_arm(tmp_path):
    """EXTRACTORS and prepare_content_root's dispatch must not drift apart.

    A species can be listed in EXTRACTORS and still never run if nobody adds the
    matching branch -- it would then be reported as skipped with a reason that
    says an extractor is missing, which would be false.
    """
    import inspect

    dispatch = inspect.getsource(prepare.prepare_content_root)
    assert "source_id in PROXY_SOURCE_IDS" in dispatch
    missing = [
        source_id for source_id in prepare.EXTRACTORS
        if f"source_id == {source_id}" not in dispatch
        and source_id not in (59, 60, 61, 62)  # shared dweevil arm, matched as a set
        and source_id not in set(prepare.PROXY_SOURCE_IDS)  # shared proxy set arm
    ]
    assert not missing, f"wired in EXTRACTORS but never dispatched: {missing}"


def test_every_proxy_id_maps_to_extract_proxy():
    from randomizer.p2_proxy import load_rows

    declared = {row["source_id"] for row in load_rows()}
    assert set(prepare.PROXY_SOURCE_IDS) == declared
    for source_id in prepare.PROXY_SOURCE_IDS:
        assert prepare.EXTRACTORS[source_id] == "extract_proxy"


def test_proxy_ids_for_manifest(tmp_path, monkeypatch):
    # The "proven" refusal below needs a row WITHOUT evidence, whatever the committed rows say.
    import randomizer.p2_proxy as _proxy
    _real_rows = _proxy.load_rows
    monkeypatch.setattr(_proxy, "load_rows", lambda directory=None: [
        {key: value for key, value in row.items() if key != "evidence"}
        for row in _real_rows(directory=directory)])
    plain = tmp_path / "plain.json"
    plain.write_text(json.dumps(manifest_with("11")))
    assert prepare.proxy_ids_for_manifest(plain) == []
    no_layout = tmp_path / "no-layout.json"
    no_layout.write_text(json.dumps({"seed": "x"}))
    assert prepare.proxy_ids_for_manifest(no_layout) == []
    tiered = tmp_path / "tiered.json"
    tiered.write_text(json.dumps({
        "p2_proxy_tier": "declared",
        "p2_layout": {"bindings": [
            {"target": "11", "source_id": 17, "enum_name": "Frog"},
            {"target": "22", "source_id": 44, "enum_name": "BlueKochappy"},
            {"target": "33", "source_id": 18, "enum_name": "MaroFrog"},
        ]}}))
    assert prepare.proxy_ids_for_manifest(tiered) == [17, 18]
    untiered = tmp_path / "untiered.json"
    untiered.write_text(json.dumps({
        "p2_layout": {"bindings": [
            {"target": "11", "source_id": 17, "enum_name": "Frog"}]}}))
    with pytest.raises(ValueError, match="without a p2_proxy_tier"):
        prepare.proxy_ids_for_manifest(untiered)
    # Frog carries no probe evidence here (stripped above), so the proven tier does not cover it.
    proven = tmp_path / "proven.json"
    proven.write_text(json.dumps({
        "p2_proxy_tier": "proven",
        "p2_layout": {"bindings": [
            {"target": "11", "source_id": 17, "enum_name": "Frog"}]}}))
    with pytest.raises(ValueError, match="outside the 'proven' tier"):
        prepare.proxy_ids_for_manifest(proven)


def test_main_adds_manifest_proxy_ids_to_wanted(tmp_path, monkeypatch):
    iso = tmp_path / "game.iso"
    iso.write_bytes(b"fake")
    manifest = tmp_path / "seed.json"
    manifest.write_text(json.dumps({
        "p2_proxy_tier": "declared",
        "p2_layout": {"bindings": [
            {"target": "11", "source_id": 17, "enum_name": "Frog"},
            {"target": "22", "source_id": 44, "enum_name": "BlueKochappy"}]}}))
    seen = {}

    def fake_prepare(iso_arg, out, research=None, pose_limit=3, wanted=None,
                     proxy_pose_limit=None):
        seen["wanted"] = list(wanted)
        seen["pose_limit"] = pose_limit
        seen["proxy_pose_limit"] = proxy_pose_limit
        return {"iso": str(iso_arg), "out": str(out),
                "extracted": [], "skipped": []}

    monkeypatch.setattr(prepare, "prepare_content_root", fake_prepare)
    actors_out = tmp_path / "actors.json"
    prepare.main(["--iso", str(iso), "--out", str(tmp_path / "content"),
                  "--seed-manifest", str(manifest),
                  "--actors-out", str(actors_out),
                  "--species", "playable"])
    assert 17 in seen["wanted"]
    assert seen["wanted"][:6] == [44, 54, 59, 60, 61, 62]
    assert json.loads(actors_out.read_text()) == {"11": 11, "22": 22}
    # Row pose limits win unless --pose-limit is explicit.
    assert seen["proxy_pose_limit"] is None
    assert seen["pose_limit"] == 3


def test_main_explicit_pose_limit_overrides_proxy_rows(tmp_path, monkeypatch):
    iso = tmp_path / "game.iso"
    iso.write_bytes(b"fake")
    manifest = tmp_path / "seed.json"
    manifest.write_text(json.dumps({
        "p2_proxy_tier": "declared",
        "p2_layout": {"bindings": [
            {"target": "11", "source_id": 17, "enum_name": "Frog"}]}}))
    seen = {}

    def fake_prepare(iso_arg, out, research=None, pose_limit=3, wanted=None,
                     proxy_pose_limit=None):
        seen["pose_limit"] = pose_limit
        seen["proxy_pose_limit"] = proxy_pose_limit
        return {"iso": str(iso_arg), "out": str(out),
                "extracted": [], "skipped": []}

    monkeypatch.setattr(prepare, "prepare_content_root", fake_prepare)
    actors_out = tmp_path / "actors.json"
    prepare.main(["--iso", str(iso), "--out", str(tmp_path / "content"),
                  "--seed-manifest", str(manifest),
                  "--actors-out", str(actors_out),
                  "--species", "playable", "--pose-limit", "5"])
    assert seen["pose_limit"] == 5
    assert seen["proxy_pose_limit"] == 5


def test_prepare_proxy_arm_uses_row_limit_by_default(tmp_path, monkeypatch):
    iso = tmp_path / "game.iso"
    iso.write_bytes(b"fake")
    out = tmp_path / "content"
    calls = []

    def fake_proxy(iso_arg, dest, source_id, pose_limit=None, **kwargs):
        calls.append((source_id, pose_limit))
        (Path(dest) / "Frog").mkdir(parents=True)
        return Path(dest) / "Frog"

    monkeypatch.setattr(prepare, "extract_proxy", fake_proxy)
    prepare.prepare_content_root(iso, out, wanted=[17])
    assert calls == [(17, None)]
    out2 = tmp_path / "content2"
    calls.clear()
    prepare.prepare_content_root(iso, out2, wanted=[17], proxy_pose_limit=6)
    assert calls == [(17, 6)]


def test_extract_proxy_passes_declaration_row(tmp_path, monkeypatch):
    import sys as _sys

    iso = tmp_path / "game.iso"
    iso.write_bytes(b"fake")
    dest = tmp_path / "content"
    dest.mkdir()
    seen = {}

    import experimental.pikmin2_proxy_assets as proxy_mod

    def fake_extract(iso_arg, enum_name, source_id, tmp, pose_limit=None,
                     row=None):
        seen["row"] = row
        seen["pose_limit"] = pose_limit
        (Path(tmp)).mkdir(parents=True, exist_ok=True)
        (Path(tmp) / "proxy.json").write_text("{}")
        return Path(tmp)

    monkeypatch.setattr(proxy_mod, "extract", fake_extract)
    # Wealthy (10) needs asset_dir/param_dir/clips/param_files from its row;
    # without row= the product path extracts from the wrong disc paths.
    prepare.extract_proxy(iso, dest, 10)
    from randomizer.p2_proxy import load_rows

    declared = {row["source_id"]: row for row in load_rows()}
    assert seen["row"] == declared[10]
    assert seen["pose_limit"] == declared[10]["pose_limit"]
