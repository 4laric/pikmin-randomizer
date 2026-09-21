"""Unit tests for the data-driven campaign-proxy family (issue #871).

Covers ``randomizer/p2_proxy`` declarations, the ``pikmin2_proxy_content``
sidecar writers (with fabricated manifests, no ISO reads), and the real
``pikmin2_proxy_assets`` extractor behind an ISO gate (skipped cleanly when
the retail ISO path does not exist).
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randomizer.p2_proxy import load_rows
from experimental.pikmin2_staging import StagingError
from experimental import pikmin2_proxy_content as content

ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")

WAIT = {"wait1", "wait", "wait2"}
MOVE = {"move1", "move", "move2", "run1", "walk"}
DEAD = {"dead", "dead1", "pdead1"}


def write_decl(directory, source_id, enum_name, host_teki=4, pose_limit=4,
               schema=1, filename=None, notes="test"):
    document = {"schema": schema, "source_id": source_id, "enum_name": enum_name,
                "host_teki": host_teki, "pose_limit": pose_limit, "notes": notes}
    path = directory / (filename or f"{source_id}_{enum_name}.json")
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_load_rows_happy_path_real_dir():
    rows = load_rows()
    assert [(row["source_id"], row["enum_name"], row["host_teki"])
            for row in rows] == [(2, "Chappy", 4), (17, "Frog", 0)]
    assert rows == sorted(rows, key=lambda row: row["source_id"])


def test_load_rows_rejects_bad_schema(tmp_path):
    write_decl(tmp_path, 2, "Chappy", schema=2)
    with pytest.raises(ValueError, match="schema"):
        load_rows(tmp_path)


def test_load_rows_rejects_filename_mismatch(tmp_path):
    write_decl(tmp_path, 2, "Chappy", filename="2_Frog.json")
    with pytest.raises(ValueError, match="filename"):
        load_rows(tmp_path)


def test_load_rows_rejects_roster_mismatch(tmp_path):
    # Filename matches its content, but source 2 is Chappy in the roster.
    write_decl(tmp_path, 2, "KumaChappy")
    with pytest.raises(ValueError, match="roster"):
        load_rows(tmp_path)


def test_load_rows_rejects_non_proxy_path(tmp_path):
    # Source 44 already stages through dwarf_orange, not the proxy family.
    write_decl(tmp_path, 44, "BlueKochappy", host_teki=3)
    with pytest.raises(ValueError, match="non-proxy"):
        load_rows(tmp_path)


def test_load_rows_rejects_duplicate_enum(tmp_path, monkeypatch):
    import randomizer.p2_proxy as proxy
    monkeypatch.setattr(proxy, "_roster_enums",
                        lambda: {2: "Chappy", 17: "Chappy"})
    write_decl(tmp_path, 2, "Chappy")
    write_decl(tmp_path, 17, "Chappy")
    with pytest.raises(ValueError, match="duplicate enum"):
        load_rows(tmp_path)


def test_load_rows_rejects_bad_pose_limit(tmp_path):
    write_decl(tmp_path, 2, "Chappy", pose_limit=9)
    with pytest.raises(ValueError, match="pose_limit"):
        load_rows(tmp_path)
    write_decl(tmp_path, 17, "Frog", pose_limit=1)
    with pytest.raises(ValueError, match="pose_limit"):
        load_rows(tmp_path)


def test_load_rows_rejects_bad_host(tmp_path):
    # Host 27 is a placeholder type that crashes the game.
    write_decl(tmp_path, 2, "Chappy", host_teki=27)
    with pytest.raises(ValueError, match="host_teki"):
        load_rows(tmp_path)


def make_species_tree(content_root, species, source_id, clips=(("wait1", []),
                                                               ("move1", [[5, 0], [10, 1]]),
                                                               ("dead", []))):
    """Fabricate one ``<content_root>/<species>/`` tree with hash-bound poses."""
    root = content_root / species
    root.mkdir(parents=True)
    manifest_clips = []
    for name, events in clips:
        poses = []
        for index in range(2):
            data = f"{species}/{name}/{index}".encode() * 64
            filename = f"px_{species}_{name}_{index:02}.mod"
            (root / filename).write_bytes(data)
            poses.append({"file": filename, "frame": index * 7,
                          "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest()})
        manifest_clips.append({"file": f"{name}.bca", "events": events,
                               "source_frames": 30,
                               "sha256": hashlib.sha256(name.encode()).hexdigest(),
                               "status": "converted", "poses": poses,
                               "unsupported_frames": []})
    (root / "proxy.json").write_text(json.dumps(
        {"schema": 1, "species": species, "enemy_id": source_id,
         "clips": manifest_clips}), encoding="utf-8")
    return root


def make_run(run):
    run.mkdir(parents=True)
    (run / "assets" / "dataDir" / "courses" / "pikmin2room").mkdir(parents=True)
    return run


def test_sidecar_grammar_single_species(tmp_path):
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    run = make_run(tmp_path / "run")
    receipt = content.stage_proxy(content_root, run, {111: "Chappy"})
    assert receipt["staged"] == "written"
    assert (run / "p2-proxy-campaign.txt").read_text(encoding="ascii") == \
        "P2_PROXY_CAMPAIGN_1\n1\n2 Chappy 4\n"
    assert (run / "p2-proxy-actors.txt").read_text(encoding="ascii") == \
        "P2_PROXY_ACTORS_1\n1\n111 Chappy\n"
    bank = (run / "p2-proxy-bank.txt").read_text(encoding="ascii").splitlines()
    assert bank[0] == "P2_PROXY_BANK_1"
    assert bank[1] == "species Chappy 2"
    assert bank[2] == "clip Chappy wait1 30 - poses 2 converted"
    assert bank[3] == "clip Chappy move1 30 5:0,10:1 poses 2 converted"
    assert bank[4] == "clip Chappy dead 30 - poses 2 converted"
    assert len(bank) == 5
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert sorted(p.name for p in room.glob("*.mod")) == [
        "px_Chappy_dead_00.mod", "px_Chappy_dead_01.mod",
        "px_Chappy_move1_00.mod", "px_Chappy_move1_01.mod",
        "px_Chappy_wait1_00.mod", "px_Chappy_wait1_01.mod",
    ]


def test_two_species_share_sidecars(tmp_path):
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    make_species_tree(content_root, "Frog", 17)
    run = make_run(tmp_path / "run")
    receipt = content.stage_proxy(content_root, run,
                                  {111: "Chappy", 222: "Frog", 333: "Chappy"})
    assert receipt["species"] == ["Chappy", "Frog"]
    assert (run / "p2-proxy-campaign.txt").read_text(encoding="ascii") == \
        "P2_PROXY_CAMPAIGN_1\n2\n2 Chappy 4\n17 Frog 0\n"
    assert (run / "p2-proxy-actors.txt").read_text(encoding="ascii") == \
        "P2_PROXY_ACTORS_1\n3\n111 Chappy\n222 Frog\n333 Chappy\n"
    bank = (run / "p2-proxy-bank.txt").read_text(encoding="ascii")
    assert "species Chappy 2\n" in bank and "species Frog 17\n" in bank
    assert bank.startswith("P2_PROXY_BANK_1\n")
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("px_Chappy_*.mod"))) == 6
    assert len(list(room.glob("px_Frog_*.mod"))) == 6


def test_reapplication_conflict_rejected(tmp_path):
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    run = make_run(tmp_path / "run")
    first = content.stage_proxy(content_root, run, {111: "Chappy"})
    assert first["staged"] == "written"
    second = content.stage_proxy(content_root, run, {111: "Chappy"})
    assert second["staged"] == "existing_identical"
    with pytest.raises(StagingError, match="conflicting"):
        content.stage_proxy(content_root, run, {999: "Chappy"})


def test_stage_rejects_unknown_species_and_bad_generators(tmp_path):
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    run = make_run(tmp_path / "run")
    with pytest.raises(StagingError):
        content.stage_proxy(content_root, run, {111: "Kogane"})
    with pytest.raises(StagingError):
        content.stage_proxy(content_root, run, {0: "Chappy"})
    with pytest.raises(StagingError):
        content.stage_proxy(content_root, run, {111: "Chappy", 111: "Frog"})


def test_stage_rejects_hash_mismatch(tmp_path):
    content_root = tmp_path / "content"
    root = make_species_tree(content_root, "Chappy", 2)
    (root / "px_Chappy_wait1_00.mod").write_bytes(b"tampered")
    run = make_run(tmp_path / "run")
    with pytest.raises(StagingError, match="hash mismatch"):
        content.stage_proxy(content_root, run, {111: "Chappy"})


@pytest.mark.parametrize("species,source_id", [("Chappy", 2), ("Frog", 17)])
def test_extract_real_species(tmp_path, species, source_id):
    if not ISO.is_file():
        pytest.skip("P2 ISO not present")
    from experimental import pikmin2_proxy_assets as assets
    result = assets.extract(ISO, species, source_id, tmp_path / species,
                            pose_limit=4)
    assert result["species"] == species and result["enemy_id"] == source_id
    converted = [clip for clip in result["clips"] if clip["status"] == "converted"]
    stems = {Path(clip["file"]).stem for clip in converted}
    assert stems & WAIT, f"{species} converted wait clips: {sorted(stems)}"
    assert stems & MOVE, f"{species} converted move clips: {sorted(stems)}"
    assert stems & DEAD, f"{species} converted dead clips: {sorted(stems)}"
    total = 0
    for clip in converted:
        indices = [int(Path(pose["file"]).stem.rsplit("_", 1)[1])
                   for pose in clip["poses"]]
        assert indices == list(range(len(indices))), clip["file"]
        clip_bytes = sum(pose["bytes"] for pose in clip["poses"])
        assert 0 < clip_bytes <= 512 * 1024, (clip["file"], clip_bytes)
        total += clip_bytes
    assert 0 < total <= 8 * 1024 * 1024
    assert result["total_pose_bytes"] == total
    assert (tmp_path / species / "proxy.json").is_file()
