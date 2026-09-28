"""Tests for experimental.pikmin2_chappy_content (inst-chappy, #871).

Hermetic: every test synthesizes its own extracted ``<content>/Chappy/``
tree (``proxy.json`` plus deterministic ``px_Chappy_<clip>_%02d.mod`` bytes)
under ``tmp_path``, so no retail disc image or cross-lane staging area is
required. The native grammar mirrors below are transcribed from the loader
contract the ``pc_p2_chappy`` module implements:

* ``p2-chappy-actors.txt``: ``P2_CHAPPY_ACTORS_1 <count>`` + ``<generator>
  <species>`` rows (count 1..100).
* ``p2-chappy-bank.txt``: ``P2_CHAPPY_BANK_1`` header, ``species <Species>
  <id>`` rows before ``clip <Species> <name> <frames> <events> poses
  <poses> converted`` rows, poses in 0..64.
* Room meshes ``ch_<Species>_<clip>_%02d.mod`` staged from the extracted
  ``px_<Species>_<clip>_%02d.mod`` bytes.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_chappy_content import (  # noqa: E402
    ACTORS_TXT,
    BANK_TXT,
    ROOM,
    StagingError,
    plan,
    stage_chappy,
    validate_source,
)

CLIPS = {
    "wait1.bca": dict(frames=[0, 5, 9], duration=10, events=[]),
    "move1.bca": dict(frames=[0, 10, 19], duration=20, events=[[4, 0]]),
    "attack.bca": dict(frames=[0, 20, 40], duration=50,
                       events=[[10, 2], [33, 3], [40, 4]]),
    "dead.bca": dict(frames=[0], duration=25, events=[[14, 2]]),
}

ACTORS = [(219002, "Chappy"), (219003, "Chappy")]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def make_source(root, species="Chappy", source_id=2, clips=None, corrupt=None):
    """Write a synthetic extracted Chappy-family tree."""
    clips = clips if clips is not None else CLIPS
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_clips = []
    for clip, spec in clips.items():
        stem = Path(clip).stem
        poses = []
        for index, frame in enumerate(spec["frames"]):
            name = f"px_{species}_{stem}_{index:02}.mod"
            data = b"CHAPPY-POSE %s %s %d\n" % (species.encode(), clip.encode(), frame)
            (root / name).write_bytes(data)
            poses.append({
                "frame": frame,
                "file": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
        manifest_clips.append({
            "file": clip,
            "events": [list(event) for event in spec["events"]],
            "source_frames": spec["duration"],
            "sha256": hashlib.sha256(b"CHAPPY-BCA %s" % clip.encode()).hexdigest(),
            "status": "converted",
            "poses": poses,
        })
    document = {
        "schema": 1,
        "species": species,
        "enemy_id": source_id,
        "clips": manifest_clips,
    }
    if corrupt is not None:
        corrupt(document)
    (root / "proxy.json").write_text(json.dumps(document, indent=2) + "\n",
                                     encoding="utf-8")
    return root


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


def test_validate_source_accepts_chappy_tree(tmp_path):
    source = make_source(tmp_path / "content" / "Chappy")
    assert validate_source(source) is True


def test_validate_source_rejects_unknown_dir(tmp_path):
    source = make_source(tmp_path / "content" / "Chappy")
    with pytest.raises(StagingError):
        validate_source(tmp_path / "content" / "Frog")


def test_plan_payloads_match_native_grammar(tmp_path):
    content = tmp_path / "content"
    make_source(content / "Chappy")
    actors_payload, bank_payload, mesh_files, digests = plan(content, ACTORS)
    assert actors_payload == b"P2_CHAPPY_ACTORS_1\n2\n219002 Chappy\n219003 Chappy\n"
    bank_text = bank_payload.decode("ascii")
    assert bank_text.splitlines()[0] == "P2_CHAPPY_BANK_1"
    assert "species Chappy 2" in bank_text.splitlines()
    for stem in ("wait1", "move1", "attack", "dead"):
        assert any(line.startswith(f"clip Chappy {stem} ") and line.endswith(" converted")
                   for line in bank_text.splitlines())
    assert set(mesh_files) == {
        f"ch_Chappy_{stem}_{index:02}.mod"
        for stem, spec in (("wait1", CLIPS["wait1.bca"]), ("move1", CLIPS["move1.bca"]),
                           ("attack", CLIPS["attack.bca"]), ("dead", CLIPS["dead.bca"]))
        for index in range(len(spec["frames"]))
    }
    assert set(digests) == {"Chappy"} and HEX64.match(digests["Chappy"])


def test_stage_is_idempotent_and_refuses_conflicts(tmp_path):
    content = tmp_path / "content"
    make_source(content / "Chappy")
    run = make_run(tmp_path / "run")
    first = stage_chappy(content, run, ACTORS)
    assert first["staged"] == "written"
    assert first["species"] == ["Chappy"]
    assert (run / ACTORS_TXT).is_file() and (run / BANK_TXT).is_file()
    second = stage_chappy(content, run, ACTORS)
    assert second["staged"] == "existing_identical"
    assert second["files"] == first["files"]
    (run / ACTORS_TXT).write_bytes(b"tampered\n")
    with pytest.raises(StagingError, match="conflicting"):
        stage_chappy(content, run, ACTORS)


def test_stage_rejects_non_chappy_species(tmp_path):
    content = tmp_path / "content"
    make_source(content / "Chappy")
    run = make_run(tmp_path / "run")
    with pytest.raises(StagingError):
        stage_chappy(content, run, [(7, "Frog")])


def test_stage_requires_wait_and_dead_anchors(tmp_path):
    content = tmp_path / "content"
    clips = {key: value for key, value in CLIPS.items() if key != "dead.bca"}
    make_source(content / "Chappy", clips=clips)
    run = make_run(tmp_path / "run")
    with pytest.raises(StagingError, match="dead"):
        stage_chappy(content, run, ACTORS)
