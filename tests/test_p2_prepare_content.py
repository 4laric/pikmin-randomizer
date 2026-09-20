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

    # 78 MiniHoudai is the supported-but-unextractable case now: it has a family
    # installer and no EXTRACTORS entry. 9 Kogane used to play that role and no
    # longer can, because it is wired.
    summary = prepare.prepare_content_root(iso, out, wanted=[23, 60, 9, 44, 54, 78])
    # Playable first (44, 54, 60), then the supported admitted ids in order.
    assert calls[0] == 44 and calls[1] == 54 and calls[2] == "dweevil"
    assert set(calls[3:]) == {9, 23}
    assert summary["extracted"] == [9, 23, 44, 54, 60]
    assert [s["source_id"] for s in summary["skipped"]] == [78]
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

    wired = set(prepare.EXTRACTORS)
    assert bullets == wired, (
        f"docstring documents {sorted(bullets)} but EXTRACTORS wires "
        f"{sorted(wired)}; undocumented={sorted(wired - bullets)}, "
        f"stale={sorted(bullets - wired)}"
    )


def test_every_wired_extractor_has_a_dispatch_arm(tmp_path):
    """EXTRACTORS and prepare_content_root's dispatch must not drift apart.

    A species can be listed in EXTRACTORS and still never run if nobody adds the
    matching branch -- it would then be reported as skipped with a reason that
    says an extractor is missing, which would be false.
    """
    import inspect

    dispatch = inspect.getsource(prepare.prepare_content_root)
    missing = [
        source_id for source_id in prepare.EXTRACTORS
        if f"source_id == {source_id}" not in dispatch
        and source_id not in (59, 60, 61, 62)  # shared dweevil arm, matched as a set
    ]
    assert not missing, f"wired in EXTRACTORS but never dispatched: {missing}"
