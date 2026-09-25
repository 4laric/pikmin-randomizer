"""Own-identity installers for the legs lane: 56 Damagumo, 63 Jigumo, 69 BigFoot (#871).

Proves the inst-legs root contract, one species at a time in brief order:

- IDENTITY_FAMILY rows resolve 56/69 to long_legs and 63 to aquatic, and no
  proxy row coexists for them (import fails closed on collision).
- EXTRACTORS wires all three with dispatch arms in prepare_content_root.
- install_layout stages each species' family sidecars from synthetic sources:
  Damagumo/BigFoot via the long_legs adapter (configs + native bind shapes),
  Jigumo via the shared aquatic installer (actors/bank/poses).
Synthetic sources only; no retail assets or ISO reads.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_family_install as family_install
from scripts import p2_prepare_content as prepare


def test_identity_rows_and_no_proxy_coexistence():
    assert family_install.resolve_family(56) == "long_legs"
    assert family_install.resolve_family("Damagumo") == "long_legs"
    assert family_install.resolve_family(69) == "long_legs"
    assert family_install.resolve_family("BigFoot") == "long_legs"
    assert family_install.resolve_family(63) == "aquatic"
    assert family_install.resolve_family("Jigumo") == "aquatic"
    from randomizer.p2_proxy import load_rows
    declared = {row["source_id"] for row in load_rows()}
    assert 56 not in declared and 63 not in declared and 69 not in declared


def test_extractors_wired_with_dispatch():
    import inspect
    assert prepare.EXTRACTORS[56] == "extract_damagumo"
    assert prepare.EXTRACTORS[63] == "extract_jigumo"
    assert prepare.EXTRACTORS[69] == "extract_bigfoot"
    dispatch = inspect.getsource(prepare.prepare_content_root)
    assert "source_id == 56" in dispatch
    assert "source_id == 63" in dispatch
    assert "source_id == 69" in dispatch


def _long_legs_source(root, damagumo=False, bigfoot=True):
    """Synthetic long-legs import dir (mirrors test_pikmin2_long_legs_install)."""
    from tests.test_pikmin2_long_legs_install import fake_imported
    fake_imported(root, damagumo=damagumo)
    return root


def _aquatic_source(root):
    from tests.test_pikmin2_aquatic_install import fake_imported
    fake_imported(root)
    return root


def _run_dir(parent):
    run = parent / "run"
    return run


def _retail(parent):
    retail = parent / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)
    return retail


def _patch_bind_conversion(monkeypatch):
    """Synthetic meshes are not J3D2bmd3; stub the bind bake (bytes preserved)."""
    from experimental import pikmin2_long_legs_visual as visual

    def _fake(model_bytes):
        return b"BIND:" + model_bytes[:16], {
            "vertices": 1, "triangles": 1, "shapes": 1, "textures": 0,
            "envelopes": 0, "bind_draw_matrices": 0,
        }
    monkeypatch.setattr(visual, "_conversion", _fake)
    # Damagumo branch uses joint_matrices + decode/write_model directly.
    import experimental.pikmin2_rigid as rigid
    import experimental.pikmin2_convert as convert

    monkeypatch.setattr(rigid, "joint_matrices", lambda blocks, arg=None: [])
    def _fake_decode(model, *args, **kwargs):
        return object()
    def _fake_write(decoded, target, *args, **kwargs):
        from pathlib import Path as _P
        _P(target).write_bytes(b"BIND:Damagumo")
        return {"vertices": 1, "triangles": 1}
    def _fake_blocks(model):
        return {}
    monkeypatch.setattr(convert, "decode", _fake_decode)
    monkeypatch.setattr(convert, "write_model", _fake_write)
    monkeypatch.setattr(convert, "blocks", _fake_blocks)


def test_install_damagumo_identity(tmp_path, monkeypatch):
    _patch_bind_conversion(monkeypatch)
    content = tmp_path / "content"
    _long_legs_source(content / "Damagumo", damagumo=True)
    run = _run_dir(tmp_path)
    layout = {"bindings": [{"target": "560001", "source_id": 56, "enum_name": "Damagumo"}]}
    receipt = family_install.install_layout(
        run, layout, content, actor_bindings={"560001": 560001},
        retail_assets=_retail(tmp_path))
    assert (run / "p2-long-legs-actors.txt").is_file()
    assert (run / "assets/dataDir/courses/pikmin2room/longlegs_Damagumo_bind_00.mod").is_file()
    assert receipt["receipts"]["560001"]["generators"] == [560001]


def test_install_bigfoot_identity(tmp_path, monkeypatch):
    _patch_bind_conversion(monkeypatch)
    content = tmp_path / "content"
    _long_legs_source(content / "BigFoot", damagumo=False)
    run = _run_dir(tmp_path)
    layout = {"bindings": [{"target": "690001", "source_id": 69, "enum_name": "BigFoot"}]}
    receipt = family_install.install_layout(
        run, layout, content, actor_bindings={"690001": 690001},
        retail_assets=_retail(tmp_path))
    assert (run / "p2-long-legs-actors.txt").is_file()
    assert (run / "assets/dataDir/courses/pikmin2room/longlegs_BigFoot_bind_00.mod").is_file()
    assert receipt["receipts"]["690001"]["generators"] == [690001]


def test_install_jigumo_identity(tmp_path):
    content = tmp_path / "content"
    _aquatic_source(content / "Jigumo")
    run = _run_dir(tmp_path)
    layout = {"bindings": [{"target": "630001", "source_id": 63, "enum_name": "Jigumo"}]}
    receipt = family_install.install_layout(
        run, layout, content, actor_bindings={"630001": 630001},
        retail_assets=_retail(tmp_path))
    assert (run / "p2-aquatic-actors.txt").is_file()
    assert (run / "p2-aquatic-bank.txt").is_file()
    assert (run / "assets/dataDir/courses/pikmin2room").is_dir()
    assert "630001" in receipt["receipts"]
