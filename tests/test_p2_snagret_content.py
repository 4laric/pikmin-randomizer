"""Tests for experimental.pikmin2_snagret_content (snagret-pair bank staging).

Hermetic: every test synthesizes its own extracted ``<content>/SnakeCrow/``
tree (``snagret.json`` plus deterministic
``snake_<Species>_<clip>_%02d.mod`` bytes) under ``tmp_path``, so no retail
disc image or cross-lane staging area is required. Clip/event fixtures reuse
the audited source values
(``experimental.pikmin2_snagret_assets.EXPECTED_EVENTS``). The native grammar
mirrors below are transcribed from the loader sources:

* ``engine/pc_port/pc_p2_batch3.cpp`` ``parseActors``/``parseBank`` (same
  shapes as the DangoMushi tests) and ``loadPose`` (``snake`` prefix).
* ``engine/pc_port/pc_p2_batch2_clock.h:102-136`` (``parseEvents``).
* ``engine/pc_port/pc_p2_snakejoint.cpp`` ``pc_p2_snakejoint_setup`` (bank
  header ``P2_SNAGRET_BANK_1``, ``species`` rows with numeric id or
  ``clips <count>``, ``clip`` rows with the ``status`` keyword tolerated;
  actors filtered to SnakeCrow/SnakeWhole; bridge ids from the seed).
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_snagret_content import (  # noqa: E402
    ACTORS_TXT,
    BANK_TXT,
    REQUIRED_CLIPS,
    ROOM,
    SPECIES_IDS,
    StagingError,
    plan,
    stage_snagret,
    validate_source,
)

# Audited snagret key events (snagret_assets.EXPECTED_EVENTS), two anchors per
# species; wait1 exercises the loop-pair (0/1) event path.
CLIPS = {
    "SnakeCrow": {
        "dead": dict(duration=150, events=[[67, 2], [75, 2], [110, 5]]),
        "appear1": dict(duration=30, events=[[14, 2]]),
        "wait1": dict(duration=50, events=[[0, 0], [49, 1]]),
    },
    "SnakeWhole": {
        "dead": dict(duration=140, events=[[65, 5], [89, 2]]),
        "appear1": dict(duration=35, events=[[13, 2], [17, 3]]),
        "wait1": dict(duration=50, events=[[0, 0], [49, 1]]),
    },
}


def make_source(root, species=("SnakeCrow", "SnakeWhole"), tag=b"SNAKE-POSE"):
    """Write a synthetic extracted snagret tree with pose meshes per species."""
    root = Path(root)
    manifest_species = {}
    for name in species:
        subdir = root / name
        subdir.mkdir(parents=True, exist_ok=True)
        manifest_clips = []
        for clip, spec in CLIPS[name].items():
            poses = []
            for index, frame in enumerate((0, spec["duration"] // 2)):
                filename = f"snake_{name}_{clip}_{index:02}.mod"
                data = tag + b" %s %s %d\n" % (name.encode(), clip.encode(), frame)
                (subdir / filename).write_bytes(data)
                poses.append({
                    "frame": frame,
                    "file": filename,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                })
            manifest_clips.append({
                "name": clip,
                "source_frames": spec["duration"],
                "events": [list(event) for event in spec["events"]],
                "status": "converted",
                "poses": poses,
            })
        manifest_species[name] = {"enemy_id": SPECIES_IDS[name], "clips": manifest_clips}
    document = {"schema": 1, "policy": "P2_SNAGRET_1",
                "disc_id": "GPVE01", "species": manifest_species}
    (root / "snagret.json").write_text(json.dumps(document, indent=2) + "\n",
                                       encoding="utf-8")
    return root


def make_dango_source(root):
    """Write a minimal synthetic DangoMushi tree for co-install tests."""
    from test_p2_dangomushi_content import make_source as make_dango

    return make_dango(root)


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


def _parse_bank_species_order(text):
    order = []
    for line in text.splitlines():
        if line.startswith("species "):
            order.append(line.split()[1])
    return order


def test_stage_snagret_34_only():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    source = make_source(tmp / "content")
    run = make_run(tmp / "run")
    receipt = stage_snagret(source, run, [(219094, "SnakeCrow")])
    assert receipt["species"] == ["SnakeCrow"]
    assert receipt["generators"] == [219094]

    actors = (run / ACTORS_TXT).read_text(encoding="ascii")
    assert actors.split() == ["P2_SNAGRET_ACTORS_1", "1", "219094", "SnakeCrow"]

    bank = (run / BANK_TXT).read_text(encoding="ascii")
    assert bank.startswith("P2_SNAGRET_BANK_1\n")
    assert _parse_bank_species_order(bank) == ["SnakeCrow"]
    for required in REQUIRED_CLIPS:
        assert f"clip SnakeCrow {required} " in bank

    room_files = sorted(p.name for p in (run / ROOM).glob("*.mod"))
    assert room_files and all(n.startswith("snake_SnakeCrow_") for n in room_files)

    # Idempotent: a second call over the same run is a no-op success.
    again = stage_snagret(source, run, [(219094, "SnakeCrow")])
    assert again["staged"] == "existing_identical"
    assert (run / BANK_TXT).read_text(encoding="ascii") == bank


def test_stage_snagret_grouped_pair_canonical_order():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    source = make_source(tmp / "content")
    run = make_run(tmp / "run")
    receipt = stage_snagret(source, run, [(2, "SnakeWhole"), (1, "SnakeCrow")])
    assert receipt["species"] == ["SnakeCrow", "SnakeWhole"]
    bank = (run / BANK_TXT).read_text(encoding="ascii")
    # Canonical family order regardless of actor order.
    assert _parse_bank_species_order(bank) == ["SnakeCrow", "SnakeWhole"]
    room_files = sorted(p.name for p in (run / ROOM).glob("*.mod"))
    assert any(n.startswith("snake_SnakeCrow_") for n in room_files)
    assert any(n.startswith("snake_SnakeWhole_") for n in room_files)


def test_snagret_co_install_with_dangomushi_is_order_independent():
    import tempfile
    from experimental.pikmin2_dangomushi_content import stage_dangomushi

    def parse_actors(data):
        tokens = data.decode("ascii").split()
        assert tokens[0] == "P2_SNAGRET_ACTORS_1"
        count = int(tokens[1])
        assert len(tokens) == 2 + 2 * count
        return {(int(tokens[i]), tokens[i + 1]) for i in range(2, len(tokens), 2)}

    def build(first):
        tmp = Path(tempfile.mkdtemp())
        source = make_source(tmp / "content")
        dango = make_dango_source(tmp / "dango")
        run = make_run(tmp / "run")
        calls = {
            "snagret": lambda: stage_snagret(source, run, [(7, "SnakeCrow")]),
            "dango": lambda: stage_dangomushi(dango, run, [(8, "DangoMushi")]),
        }
        for name in first:
            staged = calls[name]()
            assert staged["staged"] == "written"
        # Idempotent within the order.
        for name in first:
            again = calls[name]()
            assert again["staged"] == "existing_identical"
        return ((run / ACTORS_TXT).read_bytes(), (run / BANK_TXT).read_bytes())

    left = build(("snagret", "dango"))
    right = build(("dango", "snagret"))
    # Both orders succeed with the same row sets; bank bytes are canonical.
    assert parse_actors(left[0]) == parse_actors(right[0]) == {
        (7, "SnakeCrow"), (8, "DangoMushi")}
    assert left[1] == right[1]
    assert _parse_bank_species_order(left[1].decode("ascii")) == [
        "SnakeCrow", "DangoMushi"]


def test_snagret_skips_unconverted_sampled_poses(tmp_path):
    """Retail extractions record unconvertible sampled frames without `file`.

    The bank counts converted poses only and mesh indices keep the
    full-sample positions (the extractor numbers every sampled frame).
    """
    source = make_source(tmp_path / "content")
    manifest_path = source / "snagret.json"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    dead = next(c for c in document["species"]["SnakeCrow"]["clips"]
                if c["name"] == "dead")
    # Interleave an unconverted frame between the two converted poses.
    dead["poses"] = [dead["poses"][0],
                     {"frame": 75, "unsupported_reason": "ValueError: probe"},
                     dead["poses"][1]]
    # The extractor numbers every sampled frame, so the surviving converted
    # pose keeps full-sample position 02.
    subdir = source / "SnakeCrow"
    (subdir / "snake_SnakeCrow_dead_01.mod").rename(
        subdir / "snake_SnakeCrow_dead_02.mod")
    dead["poses"][2]["file"] = "snake_SnakeCrow_dead_02.mod"
    manifest_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    assert validate_source(source)
    run = make_run(tmp_path / "run")
    receipt = stage_snagret(source, run, [(5, "SnakeCrow")])
    assert receipt["staged"] == "written"
    bank = (run / BANK_TXT).read_text(encoding="ascii")
    assert "clip SnakeCrow dead 150 67:2,75:2,110:5 poses 2 status converted" in bank
    room_files = sorted(p.name for p in (run / ROOM).glob("snake_SnakeCrow_dead_*.mod"))
    assert len(room_files) == 2


def test_snagret_conflicting_restage_refuses():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    source = make_source(tmp / "content")
    run = make_run(tmp / "run")
    stage_snagret(source, run, [(219094, "SnakeCrow")])
    before = (run / BANK_TXT).read_bytes()
    (source / "SnakeCrow" / "snake_SnakeCrow_dead_00.mod").write_bytes(b"changed")
    with pytest.raises(StagingError):
        stage_snagret(source, run, [(219094, "SnakeCrow")])
    assert (run / BANK_TXT).read_bytes() == before


def test_snagret_bad_source_refuses(tmp_path):
    run = make_run(tmp_path / "run")
    with pytest.raises(StagingError):
        validate_source(tmp_path / "empty")
    with pytest.raises(StagingError):
        stage_snagret(tmp_path / "empty", run, [(1, "SnakeCrow")])
    with pytest.raises(StagingError):
        stage_snagret(make_source(tmp_path / "content"), run, [(1, "Nope")])


def test_family_adapter_snagret_end_to_end(tmp_path):
    from experimental import pikmin2_family_install as install

    assert install.resolve_family(34) == "snagret"
    assert install.resolve_family("SnakeWhole") == "snagret"
    content_root = tmp_path / "content"
    make_source(content_root / "SnakeCrow")
    make_source(content_root / "SnakeWhole")
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)
    run = tmp_path / "run"
    layout = {"bindings": [
        {"target": "t1", "source_id": 34, "enum_name": "SnakeCrow"},
        {"target": "t2", "source_id": 70, "enum_name": "SnakeWhole"},
    ]}
    receipt = install.install_layout(
        run, layout, content_root, actor_bindings={"t1": 101, "t2": 102},
        retail_assets=retail)
    assert set(receipt["receipts"]) == {"t1", "t2"}
    bank = (run / BANK_TXT).read_text(encoding="ascii")
    assert _parse_bank_species_order(bank) == ["SnakeCrow", "SnakeWhole"]
