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
               schema=1, filename=None, notes="test", **extra):
    document = {"schema": schema, "source_id": source_id, "enum_name": enum_name,
                "host_teki": host_teki, "pose_limit": pose_limit, "notes": notes}
    document.update(extra)
    path = directory / (filename or f"{source_id}_{enum_name}.json")
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_load_rows_happy_path_real_dir():
    rows = load_rows()
    assert rows == sorted(rows, key=lambda row: row["source_id"])
    by_id = {row["source_id"]: row for row in rows}
    assert by_id[2]["enum_name"] == "Chappy"
    # inst-frogs #871: Frog (17) graduated to its own identity installer.
    assert 17 not in by_id
    assert by_id[18]["enum_name"] == "MaroFrog"
    assert len(rows) == len(list((ROOT / "randomizer" / "p2_proxy").glob("*.json")))


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
                        lambda: {2: "Chappy", 18: "Chappy"})
    write_decl(tmp_path, 2, "Chappy")
    write_decl(tmp_path, 18, "Chappy")
    with pytest.raises(ValueError, match="duplicate enum"):
        load_rows(tmp_path)


def test_load_rows_rejects_bad_pose_limit(tmp_path):
    write_decl(tmp_path, 2, "Chappy", pose_limit=9)
    with pytest.raises(ValueError, match="pose_limit"):
        load_rows(tmp_path)
    write_decl(tmp_path, 18, "MaroFrog", pose_limit=1)
    with pytest.raises(ValueError, match="pose_limit"):
        load_rows(tmp_path)


def test_load_rows_rejects_bad_host(tmp_path):
    # Host 27 is a placeholder type that crashes the game.
    write_decl(tmp_path, 2, "Chappy", host_teki=27)
    with pytest.raises(ValueError, match="host_teki"):
        load_rows(tmp_path)


def test_load_rows_accepts_full_overrides(tmp_path):
    write_decl(tmp_path, 2, "Chappy", asset_dir="Kogane", param_dir="kogane",
               clips={"wait1": "waitact1"},
               param_files={"enemyparm.txt": "bombotakara"})
    (rows,) = load_rows(tmp_path)
    assert rows["asset_dir"] == "Kogane"
    assert rows["param_dir"] == "kogane"
    assert rows["clips"] == {"wait1": "waitact1"}
    assert rows["param_files"] == {"enemyparm.txt": "bombotakara"}


def test_load_rows_defaults_overrides_to_empty(tmp_path):
    write_decl(tmp_path, 2, "Chappy")
    (rows,) = load_rows(tmp_path)
    assert rows["asset_dir"] is None
    assert rows["param_dir"] is None
    assert rows["clips"] == {}
    assert rows["param_files"] == {}


@pytest.mark.parametrize("field,value", [
    ("asset_dir", 7),
    ("asset_dir", ""),
    ("asset_dir", "../Kogane"),
    ("asset_dir", "kogane!"),
    ("param_dir", 7),
    ("param_dir", ""),
    ("param_dir", "Kogane"),
    ("param_dir", "kogane/.."),
    ("clips", []),
    ("clips", {}),
    ("clips", {"nap1": "move"}),
    ("clips", {"wait1": "wait1"}),
    ("clips", {"wait1": "not a stem!"}),
    ("clips", {"wait1": "move", "dead": "move"}),
    ("param_files", []),
    ("param_files", {}),
    ("param_files", {"enemyparm.bin": "kogane"}),
    ("param_files", {"enemyparm.txt": "Kogane"}),
])
def test_load_rows_rejects_bad_overrides(tmp_path, field, value):
    write_decl(tmp_path, 2, "Chappy", **{field: value})
    with pytest.raises(ValueError, match=field):
        load_rows(tmp_path)


def test_registry_tolerances_unit():
    from experimental.pikmin2_sheargrub_assets import animation_rows
    upper = ("2 { Z:\\a\\K_wait.bca K_wait.bca -1 } "
             "{ Z:\\a\\wait.bca wait.bca -1 }")
    with pytest.raises(ValueError, match="Invalid animation registration"):
        animation_rows(upper)
    notes = []
    rows = animation_rows(upper, allow_uppercase=True, notes=notes)
    assert [row["file"] for row in rows] == ["K_wait.bca", "wait.bca"]
    assert any("K_wait.bca" in note for note in notes)
    dup = ("2 { Z:\\a\\wait1.bca wait1.bca -1 } "
           "{ Z:\\a\\wait1.bca wait1.bca -1 }")
    with pytest.raises(ValueError, match="count/identity"):
        animation_rows(dup)
    notes = []
    rows = animation_rows(dup, dedupe_duplicates=True, notes=notes)
    assert [row["file"] for row in rows] == ["wait1.bca"]
    assert any("wait1.bca" in note for note in notes)
    braceless = ("2 { Z:\\a\\wait.bca wait.bca -1 } "
                 "# attack_2.bca\r\n Z:\\a\\attack_2.bca attack_2.bca -1 }")
    with pytest.raises(ValueError, match="count/identity"):
        animation_rows(braceless)
    notes = []
    rows = animation_rows(braceless, allow_braceless=True, notes=notes)
    assert [row["file"] for row in rows] == ["wait.bca", "attack_2.bca"]
    assert any("attack_2.bca" in note for note in notes)
    # Strict behaviour without flags is unchanged.
    assert animation_rows("1 { a\\attack1.bca attack1.bca 15 2 -1 }")[0]["events"] == [[15, 2]]


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
    make_species_tree(content_root, "MaroFrog", 18)
    run = make_run(tmp_path / "run")
    receipt = content.stage_proxy(content_root, run,
                                  {111: "Chappy", 222: "MaroFrog", 333: "Chappy"})
    assert receipt["species"] == ["Chappy", "MaroFrog"]
    assert (run / "p2-proxy-campaign.txt").read_text(encoding="ascii") == \
        "P2_PROXY_CAMPAIGN_1\n2\n2 Chappy 4\n18 MaroFrog 33\n"
    assert (run / "p2-proxy-actors.txt").read_text(encoding="ascii") == \
        "P2_PROXY_ACTORS_1\n3\n111 Chappy\n222 MaroFrog\n333 Chappy\n"
    bank = (run / "p2-proxy-bank.txt").read_text(encoding="ascii")
    assert "species Chappy 2\n" in bank and "species MaroFrog 18\n" in bank
    assert bank.startswith("P2_PROXY_BANK_1\n")
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("px_Chappy_*.mod"))) == 6
    assert len(list(room.glob("px_MaroFrog_*.mod"))) == 6


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
    # NOTE: a dict literal cannot test duplicate generators (the key
    # collapses before the call); see
    # test_stage_rejects_duplicate_generators_list_input for the pairs form.


def test_stage_rejects_hash_mismatch(tmp_path):
    content_root = tmp_path / "content"
    root = make_species_tree(content_root, "Chappy", 2)
    (root / "px_Chappy_wait1_00.mod").write_bytes(b"tampered")
    run = make_run(tmp_path / "run")
    with pytest.raises(StagingError, match="hash mismatch"):
        content.stage_proxy(content_root, run, {111: "Chappy"})


@pytest.mark.parametrize("species,source_id", [("Chappy", 2), ("MaroFrog", 18)])
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


def test_extract_tank_alias_iso(tmp_path):
    if not ISO.is_file():
        pytest.skip("P2 ISO not present")
    from experimental import pikmin2_proxy_assets as assets
    result = assets.extract(ISO, "Tank", 24, tmp_path / "Tank", pose_limit=4,
                            row={"clips": {"wait1": "waitact1"}})
    stems = {Path(clip["file"]).stem
             for clip in result["clips"] if clip["status"] == "converted"}
    assert "wait1" in stems and "dead" in stems
    aliased = [clip for clip in result["clips"]
               if clip["file"] == "wait1.bca"]
    assert len(aliased) == 1 and aliased[0]["source_file"] == "waitact1.bca"
    assert not (tmp_path / "Tank" / "waitact1.bca").exists()
    assert (tmp_path / "Tank" / "wait1.bca").is_file()
    assert sorted((tmp_path / "Tank").glob("px_Tank_wait1_*.mod"))
    assert not list((tmp_path / "Tank").glob("px_Tank_waitact1_*.mod"))
    with pytest.raises(ValueError, match="not in the species"):
        assets.extract(ISO, "Tank", 24, tmp_path / "Tank-bad", pose_limit=4,
                       row={"clips": {"wait1": "nosuchclip"}})


def test_extract_fuefuki_skips_singular_clips_iso(tmp_path):
    if not ISO.is_file():
        pytest.skip("P2 ISO not present")
    from experimental import pikmin2_proxy_assets as assets
    result = assets.extract(ISO, "Fuefuki", 41, tmp_path / "Fuefuki",
                            pose_limit=4)
    skipped = {entry["file"] for entry in result["unsupported_clips"]}
    assert skipped == {"landing.bca", "landfail.bca"}
    assert all("Singular animation scale" in entry["error"]
               for entry in result["unsupported_clips"])
    stems = {Path(clip["file"]).stem
             for clip in result["clips"] if clip["status"] == "converted"}
    assert stems & WAIT and stems & DEAD


def test_extract_qurione_stone_optional_iso(tmp_path):
    if not ISO.is_file():
        pytest.skip("P2 ISO not present")
    from experimental import pikmin2_proxy_assets as assets
    result = assets.extract(
        ISO, "Qurione", 16, tmp_path / "Qurione", pose_limit=4,
        row={"clips": {"wait1": "waitl", "dead": "damage"}})
    assert result["missing_metadata"] == ["enemystoneinfo.txt"]
    stems = {Path(clip["file"]).stem
             for clip in result["clips"] if clip["status"] == "converted"}
    assert "wait1" in stems and "dead" in stems


def test_load_rows_rejects_unknown_roster_source(tmp_path):
    # Source 999 is absent from the roster; the filename matches its content.
    write_decl(tmp_path, 999, "Ghost")
    with pytest.raises(ValueError, match="unknown to the roster"):
        load_rows(tmp_path)


def test_load_rows_rejects_duplicate_source(tmp_path, monkeypatch):
    import randomizer.p2_proxy as proxy
    # Two files for the same source id: serve each file's own enum from the
    # stubbed roster so both pass the enum check and reach the duplicate
    # branch (unreachable with the real one-enum-per-source roster).
    seen = iter(["Chappy", "Frog"])

    class _TwoEnums(dict):
        def get(self, key, default=None):
            try:
                return next(seen)
            except StopIteration:
                return default

    monkeypatch.setattr(proxy, "_roster_enums", lambda: _TwoEnums())
    write_decl(tmp_path, 2, "Chappy")
    write_decl(tmp_path, 2, "Frog", filename="2_Frog.json")
    with pytest.raises(ValueError, match="duplicate source"):
        load_rows(tmp_path)


def test_load_rows_missing_normals_policy(tmp_path):
    write_decl(tmp_path, 2, "Chappy", missing_normals="compute")
    (row,) = load_rows(tmp_path)
    assert row["missing_normals"] == "compute"
    write_decl(tmp_path, 2, "Chappy", missing_normals="default")
    with pytest.raises(ValueError, match="missing_normals"):
        load_rows(tmp_path)
    write_decl(tmp_path, 2, "Chappy", missing_normals="bogus")
    with pytest.raises(ValueError, match="missing_normals"):
        load_rows(tmp_path)


def test_stage_rejects_duplicate_generators_list_input(tmp_path):
    # A dict literal cannot carry a duplicate key, so pass pairs directly.
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    run = make_run(tmp_path / "run")
    with pytest.raises(StagingError, match="not unique"):
        content.stage_proxy(content_root, run,
                            [(111, "Chappy"), (111, "Chappy")])


def test_stage_rejects_actor_rows_past_native_cap(tmp_path):
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    run = make_run(tmp_path / "run")
    actors = [(1000 + index, "Chappy") for index in range(101)]
    with pytest.raises(StagingError, match="100-row cap"):
        content.stage_proxy(content_root, run, actors)


def test_plan_rejects_species_past_native_table_cap(tmp_path, monkeypatch):
    import randomizer.p2_proxy as proxy
    rows = [{"source_id": 1000 + index, "enum_name": f"Species{index}",
             "host_teki": 4}
            for index in range(65)]
    monkeypatch.setattr(proxy, "load_rows", lambda directory=None: rows)
    monkeypatch.setattr(content, "_proxy_rows",
                        lambda: {row["enum_name"]: (row["source_id"], 4)
                                 for row in rows})
    with pytest.raises(StagingError, match="64-species cap"):
        content.plan(tmp_path / "content",
                     [(2000 + index, f"Species{index}") for index in range(65)])


def test_stage_accepts_retail_event_shapes(tmp_path):
    # The native parseEvents grammar accepts end-frame events and kind 1
    # without a preceding kind 0, with no duration relation; the stager
    # must too (frames stay strictly increasing, the safe-direction check
    # the extractor output always satisfies).
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2,
                      clips=(("wait1", [[5, 1], [12, 7]]),
                             ("move1", []),
                             ("dead", [[30, 0]])))
    run = make_run(tmp_path / "run")
    receipt = content.stage_proxy(content_root, run, {111: "Chappy"})
    assert receipt["staged"] == "written"
    bank = (run / "p2-proxy-bank.txt").read_text(encoding="ascii")
    assert "clip Chappy wait1 30 5:1,12:7 poses 2 converted" in bank


def test_stage_refuses_non_file_target(tmp_path):
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    run = make_run(tmp_path / "run")
    (run / "p2-proxy-bank.txt").mkdir()
    with pytest.raises(StagingError, match="non-file targets"):
        content.stage_proxy(content_root, run, {111: "Chappy"})


def test_stage_accepts_retail_uppercase_clip_stems(tmp_path):
    # Real species ship uppercase registry stems (BigTreasure preattackF,
    # Kabuto K_wait); the native bank reader takes the clip name as an
    # unrestricted token, so the stager must carry the spelling through.
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2,
                      clips=(("wait1", []),
                             ("preattackF", []),
                             ("dead", [])))
    run = make_run(tmp_path / "run")
    receipt = content.stage_proxy(content_root, run, {111: "Chappy"})
    assert receipt["staged"] == "written"
    bank = (run / "p2-proxy-bank.txt").read_text(encoding="ascii")
    assert "clip Chappy preattackF 30 - poses 2 converted" in bank
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert sorted(p.name for p in room.glob("px_Chappy_preattackF_*.mod")) == [
        "px_Chappy_preattackF_00.mod", "px_Chappy_preattackF_01.mod"]


def test_stage_accepts_underscore_clip_stems(tmp_path):
    # Clip stems legitimately contain underscores (Tobi dead_p, Kabuto
    # hit_start); the stager compares the exact native pose filename
    # px_<species>_<stem>_<ii>.mod instead of regex-splitting the stem, so
    # these stage instead of failing the whole layout install.
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2,
                      clips=(("wait1", []),
                             ("dead_p", []),
                             ("dead", [])))
    run = make_run(tmp_path / "run")
    receipt = content.stage_proxy(content_root, run, {111: "Chappy"})
    assert receipt["staged"] == "written"
    bank = (run / "p2-proxy-bank.txt").read_text(encoding="ascii")
    assert "clip Chappy dead_p 30 - poses 2 converted" in bank
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert sorted(p.name for p in room.glob("px_Chappy_dead_p_*.mod")) == [
        "px_Chappy_dead_p_00.mod", "px_Chappy_dead_p_01.mod"]


def _stub_private_destination(monkeypatch):
    import experimental.pikmin2_family_install as family_install
    room = Path("assets") / "dataDir" / "courses" / "pikmin2room"

    def _stub(run, retail_assets):
        dest = Path(run) / room
        dest.mkdir(parents=True, exist_ok=True)
        return Path(run) / "assets"

    monkeypatch.setattr(family_install, "prepare_private_destination", _stub)
    return family_install


def test_install_layout_groups_two_proxy_species(tmp_path, monkeypatch):
    family_install = _stub_private_destination(monkeypatch)
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    make_species_tree(content_root, "MaroFrog", 18)
    run = tmp_path / "run"
    layout = {"bindings": [
        {"target": "1001", "source_id": 2, "enum_name": "Chappy"},
        {"target": "1002", "source_id": 18, "enum_name": "MaroFrog"},
        {"target": "1003", "source_id": 2, "enum_name": "Chappy"},
    ]}
    receipt = family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"1001": 1001, "1002": 1002, "1003": 1003},
        retail_assets=tmp_path / "retail")
    assert sorted(receipt["receipts"]) == ["1001", "1002", "1003"]
    assert (run / "p2-proxy-campaign.txt").read_text(encoding="ascii") == \
        "P2_PROXY_CAMPAIGN_1\n2\n2 Chappy 4\n18 MaroFrog 33\n"
    assert (run / "p2-proxy-actors.txt").read_text(encoding="ascii") == \
        "P2_PROXY_ACTORS_1\n3\n1001 Chappy\n1002 MaroFrog\n1003 Chappy\n"


def test_install_layout_mixes_proxy_and_other_families(tmp_path, monkeypatch):
    family_install = _stub_private_destination(monkeypatch)
    monkeypatch.setitem(family_install.IDENTITY_FAMILY, 900, "fakefam")
    monkeypatch.setitem(family_install.IDENTITY_FAMILY, "fakefam", "fakefam")

    def _fake_install(source, run, actors):
        assert Path(source).name == "Fakefam"
        assert sorted(species for _, species in actors) == ["Fakefam"] * 2
        (Path(run) / "p2-fakefam.txt").write_text(
            "P2_FAKEFAM_1\n", encoding="ascii")
        return {"family": "fakefam", "staged": "written"}

    monkeypatch.setitem(family_install._OVERRIDES, "fakefam", _fake_install)
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    (content_root / "Fakefam").mkdir(parents=True)
    run = tmp_path / "run"
    layout = {"bindings": [
        {"target": "1001", "source_id": 2, "enum_name": "Chappy"},
        {"target": "1002", "source_id": 900, "enum_name": "Fakefam"},
        {"target": "1003", "source_id": 900, "enum_name": "Fakefam"},
    ]}
    receipt = family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"1001": 1001, "1002": 1002, "1003": 1003},
        retail_assets=tmp_path / "retail")
    assert sorted(receipt["receipts"]) == ["1001", "1002", "1003"]
    assert (run / "p2-fakefam.txt").read_text(encoding="ascii") == "P2_FAKEFAM_1\n"
    assert (run / "p2-proxy-campaign.txt").read_text(encoding="ascii") == \
        "P2_PROXY_CAMPAIGN_1\n1\n2 Chappy 4\n"


def test_install_layout_second_call_replays_receipt(tmp_path, monkeypatch):
    family_install = _stub_private_destination(monkeypatch)
    content_root = tmp_path / "content"
    make_species_tree(content_root, "Chappy", 2)
    make_species_tree(content_root, "MaroFrog", 18)
    run = tmp_path / "run"
    layout = {"bindings": [
        {"target": "1001", "source_id": 2, "enum_name": "Chappy"},
        {"target": "1002", "source_id": 18, "enum_name": "MaroFrog"},
    ]}
    actors = {"1001": 1001, "1002": 1002}
    first = family_install.install_layout(
        run, layout, content_root, actor_bindings=actors,
        retail_assets=tmp_path / "retail")
    assert not first.get("cached")
    before = {name: (run / name).read_bytes() for name in (
        "p2-proxy-campaign.txt", "p2-proxy-actors.txt", "p2-proxy-bank.txt")}
    second = family_install.install_layout(
        run, layout, content_root, actor_bindings=actors,
        retail_assets=tmp_path / "retail")
    assert second.get("cached") is True
    assert second["plan_digest"] == first["plan_digest"]
    for name, payload in before.items():
        assert (run / name).read_bytes() == payload
