"""Lane 05 family-installer orchestration (generated-session path).

Uses a synthetic frog bank and a synthetic retail root: no retail assets are
read. Proves a family installer is consumed through a generated-session run with
a private model destination and untouched retail content still reachable.
"""
import hashlib
import json
import struct

import pytest

from experimental.pikmin2_family_install import (
    available,
    install_family,
    prepare_private_destination,
)
from experimental.pikmin2_frog_install import CLIPS, SPECIES


def seed_bank(root):
    bank = root / "bank"
    bank.mkdir()
    manifest = dict(schema=1, policy="P2_FROG_IMPORT_1", disc_id="GPVE01",
                    disc_revision=0, species={}, total_pose_bytes=0)
    raw = b"".join(struct.pack(">II", value, 1) + b"x" for value in (32, 34, 48)) + struct.pack(">II", 65535, 0)
    for species, source_id in SPECIES.items():
        (bank / species).mkdir()
        clips = []
        for name in CLIPS:
            poses = []
            for index in range(2):
                file = f"frog_{species}_{name}_{index:02}.mod"
                (bank / species / file).write_bytes(raw)
                poses.append(dict(frame=index, file=file, bytes=len(raw),
                                  sha256=hashlib.sha256(raw).hexdigest()))
                manifest["total_pose_bytes"] += len(raw)
            clips.append(dict(name=name, source_frames=2, status="converted", poses=poses))
        manifest["species"][species] = dict(enemy_id=source_id, clips=clips)
    (bank / "frogs.json").write_text(json.dumps(manifest))
    return bank


def make_retail(root):
    retail = root / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)
    (retail / "dataDir" / "stages" / "base.bin").write_bytes(b"retail")
    return retail


def test_install_family_frog_into_private_overlay(tmp_path):
    bank = seed_bank(tmp_path)
    retail = make_retail(tmp_path)
    run = tmp_path / "run"
    receipt = install_family("frog", bank, run, [(201001, "Frog"), (201002, "MaroFrog")],
                             retail_assets=retail)
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert room.is_dir() and (run / "p2-frog.txt").is_file()
    assert receipt["models"] == 44
    assert (run / "frog-family-install-receipt.json").is_file()
    # Untouched retail content stays reachable through the private assets tree.
    assert (run / "assets" / "dataDir" / "stages" / "base.bin").read_bytes() == b"retail"
    assert "frog" in available()


def test_prepare_private_destination_is_guarded(tmp_path):
    retail = make_retail(tmp_path)
    run = tmp_path / "run"
    prepare_private_destination(run, retail)
    with pytest.raises(ValueError):
        prepare_private_destination(run, retail)  # already prepared


def test_install_family_requires_private_destination(tmp_path):
    bank = seed_bank(tmp_path)
    with pytest.raises(ValueError):
        install_family("frog", bank, tmp_path / "run", [(1, "Frog")])


def test_install_family_unknown_name(tmp_path):
    with pytest.raises(ValueError):
        install_family("not_a_family", tmp_path, tmp_path / "run", [])


def test_launch_consumes_family_installer(tmp_path, monkeypatch):
    import randomizer.runner as runner
    from randomizer.seed import generate

    bank = seed_bank(tmp_path)
    retail = make_retail(tmp_path)
    called = []
    async def fake_serve(*args, **kwargs):
        called.append(True)

    monkeypatch.setattr(runner, "serve", fake_serve)
    runner.launch(generate("seed-a"), tmp_path / "sess", assets=retail,
                  family_install="frog", family_source=bank,
                  family_actors=[(201001, "Frog"), (201002, "MaroFrog")])
    assert called == [True]
    installed = list((tmp_path / "sess" / "runs").glob("*/p2-frog.txt"))
    assert len(installed) == 1 and installed[0].is_file()
    assert list((tmp_path / "sess" / "runs").glob("*/frog-family-install-receipt.json"))


def test_launch_rejects_family_and_content_together(tmp_path, monkeypatch):
    import randomizer.runner as runner
    from randomizer.seed import generate

    retail = make_retail(tmp_path)
    with pytest.raises(ValueError):
        runner.launch(generate("seed-a"), tmp_path / "sess", assets=retail,
                      content_manifest=tmp_path / "x.json", family_install="frog")
