"""Lane 05 identity-to-runtime binding layer (``install_layout``).

Uses a synthetic ``content_root`` and a fake ``dwarf_orange`` installer: no real
bank/ISO assets are read. Proves the binding layer resolves P2 source ids and
enum names into a family, validates everything fail-closed before writing, then
installs through the registered installer and replays from the on-disk binding
receipt cache.
"""
import json
import shutil
import struct
from pathlib import Path

import pytest

from experimental import pikmin2_family_install as family_install
from experimental.pikmin2_dwarf_orange_bank import (
    BANK_JSON, BANK_TXT, HEADER, POSE_PREFIX, PROFILE, PROFILE_JSON, PROFILE_TXT)
from experimental.pikmin2_dwarf_orange_install import sha
from experimental.pikmin2_kochappy_bank import (
    HEADER as KOCHAPPY_HEADER, PROFILE as KOCHAPPY_PROFILE,
    parse_bank as kochappy_parse_bank)
from experimental.pikmin2_staging import StagingError


def binding(target="gen-001", source_id=44, enum_name="BlueKochappy"):
    return {"target": target, "source_id": source_id, "enum_name": enum_name}


def layout_with(*bindings):
    return {"bindings": list(bindings)}


def make_source_dir(content_root, enum_name):
    source = content_root / enum_name
    source.mkdir(parents=True)
    return source


@pytest.fixture(autouse=True)
def _isolate_overrides(monkeypatch):
    monkeypatch.setattr(family_install, "_OVERRIDES", {})


DWARF_ORANGE_CLIPS = {"wait1": 75, "move1": 55, "attack": 90, "dead": 90, "flick": 80}
SNOW_CLIPS = DWARF_ORANGE_CLIPS
MODEL_CHUNKS = ((32, b"material"), (34, b"texture"), (48, b"event"), (65535, b""))


def model_bytes():
    return b"".join(struct.pack(">II", tag, len(payload)) + payload
                    for tag, payload in MODEL_CHUNKS)


def make_dwarf_orange_source(content_root):
    source = content_root / "BlueKochappy"
    bank = source / "bank"
    profile = source / "profile"
    bank.mkdir(parents=True)
    profile.mkdir()

    profile_json_bytes = json.dumps(
        {"schema": 1, "species": "BlueKochappy", "source_id": 44},
        separators=(",", ":")).encode("ascii")
    (profile / PROFILE_JSON).write_bytes(profile_json_bytes)
    (bank / PROFILE_TXT).write_bytes(PROFILE.encode("ascii"))

    data = model_bytes()
    motions = {}
    rows = [HEADER]
    file_sha256 = {}
    for name, duration in DWARF_ORANGE_CLIPS.items():
        frames = [0, duration // 2, duration - 1]
        motions[name] = {
            "poses": 3,
            "source_frames": duration,
            "frames": frames,
            "event_frames": [duration // 2],
        }
        rows.append(f"{name} 3 {duration} " + " ".join(map(str, frames)))
        for index in range(3):
            model_name = f"{POSE_PREFIX}_{name}_{index:02}.mod"
            (bank / model_name).write_bytes(data)
            file_sha256[model_name] = sha(data)
    (bank / BANK_TXT).write_text("\n".join(rows) + "\n", encoding="ascii")
    metadata = {
        "schema": 1,
        "species": "BlueKochappy",
        "source_id": 44,
        "health": 250,
        "motions": motions,
        "reference_sha256": sha(profile_json_bytes),
        "file_sha256": file_sha256,
    }
    (bank / BANK_JSON).write_text(json.dumps(metadata), encoding="utf-8")
    return source


def make_snow_source(content_root):
    source = content_root / "YellowKochappy"
    source.mkdir(parents=True)

    data = model_bytes()
    motions = {}
    rows = ["P2_SNOW_2"]
    for name, duration in SNOW_CLIPS.items():
        frames = [0, duration // 2, duration - 1]
        motions[name] = {"poses": 3, "source_frames": duration, "frames": frames}
        rows.append(f"{name} 3 {duration} 0 {duration // 2} {duration - 1}")
        for index in range(3):
            (source / f"snow_{name}_{index:02}.mod").write_bytes(data)
    (source / "p2-snow.txt").write_text("\n".join(rows) + "\n", encoding="ascii")
    snow_json = {"schema": 1, "species": "YellowKochappy", "motions": motions}
    (source / "snow.json").write_text(json.dumps(snow_json), encoding="utf-8")
    return source


KOCHAPPY_CLIPS = DWARF_ORANGE_CLIPS


def make_kochappy_source(content_root):
    """Flat Dwarf Red (Kochappy) source accepted by the real bank installer.

    Mirrors ``pikmin2_kochappy_bank.build``'s output layout: a single flat
    ``<content_root>/Kochappy`` directory holding ``kochappy-bank.json``,
    the flat bank/profile text files, and 15 ``kochappy_<clip>_<nn>.mod`` poses.
    """
    source = content_root / "Kochappy"
    source.mkdir(parents=True)

    data = model_bytes()
    rows = [KOCHAPPY_HEADER]
    for name, duration in KOCHAPPY_CLIPS.items():
        frames = [0, duration // 2, duration - 1]
        rows.append(f"{name} 3 {duration} " + " ".join(map(str, frames)))
    bank_text = "\n".join(rows) + "\n"

    motions = kochappy_parse_bank(bank_text)
    file_sha256 = {}
    for name in motions:
        for index in range(3):
            model_name = f"kochappy_{name}_{index:02}.mod"
            (source / model_name).write_bytes(data)
            file_sha256[model_name] = sha(data)

    (source / "p2-kochappy-bank.txt").write_text(bank_text, encoding="ascii")
    (source / "p2-kochappy-profile.txt").write_text(KOCHAPPY_PROFILE, encoding="ascii")
    metadata = {
        "schema": 1,
        "species": "Kochappy",
        "source_id": 1,
        "health": 200,
        "motions": motions,
        "file_sha256": file_sha256,
    }
    (source / "kochappy-bank.json").write_text(json.dumps(metadata), encoding="utf-8")
    return source


def test_resolve_family_int_and_enum():
    assert family_install.resolve_family(44) == "dwarf_orange"
    assert family_install.resolve_family("BlueKochappy") == "dwarf_orange"
    assert family_install.resolve_family("bluekochappy") == "dwarf_orange"


def test_resolve_family_snow():
    assert family_install.resolve_family(45) == "snow"
    assert family_install.resolve_family("YellowKochappy") == "snow"
    assert family_install.resolve_family("yellowkochappy") == "snow"
    assert family_install.resolve_family("BlueKochappy") == "dwarf_orange"


def test_resolve_family_kochappy():
    assert family_install.resolve_family(1) == "kochappy"
    assert family_install.resolve_family("Kochappy") == "kochappy"
    assert family_install.resolve_family("kochappy") == "kochappy"
    assert family_install.resolve_family("BlueKochappy") == "dwarf_orange"
    assert family_install.resolve_family(45) == "snow"


def test_resolve_family_unknown_identity():
    for bad in (999, "Nope", 0):
        with pytest.raises(ValueError):
            family_install.resolve_family(bad)


def test_install_layout_happy_path(tmp_path):
    content_root = tmp_path / "content"
    source = make_source_dir(content_root, "BlueKochappy")
    run = tmp_path / "run"

    calls = []
    fake_receipt = {"models": 1, "actor": "BlueKochappy"}

    def fake_installer(source_arg, run_arg, actors):
        calls.append((source_arg, run_arg, actors))
        return fake_receipt

    family_install.register("dwarf_orange", fake_installer)

    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    receipt = family_install.install_layout(
        run, layout, content_root, actor_bindings={"gen-001": 211001})

    assert len(calls) == 1
    source_arg, run_arg, actors = calls[0]
    assert source_arg == source
    assert run_arg == run
    assert actors == [(211001, "BlueKochappy")]

    assert receipt["schema"] == 1
    assert receipt["mode"] == "identity-binding"
    assert receipt["bindings"] == layout["bindings"]
    assert receipt["receipts"] == {"gen-001": fake_receipt}

    receipt_file = run / "p2-binding-receipt.json"
    assert receipt_file.is_file()
    stored = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert stored["schema"] == 1
    assert stored["mode"] == "identity-binding"
    assert stored["receipts"]["gen-001"] == fake_receipt


def test_install_layout_rejects_missing_bindings(tmp_path):
    run = tmp_path / "run"
    with pytest.raises(ValueError):
        family_install.install_layout(run, {}, tmp_path / "content")
    assert not run.exists()


def test_install_layout_rejects_empty_bindings(tmp_path):
    run = tmp_path / "run"
    with pytest.raises(ValueError):
        family_install.install_layout(run, layout_with(), tmp_path / "content")
    assert not run.exists()


def test_install_layout_rejects_unknown_identity(tmp_path):
    run = tmp_path / "run"
    layout = layout_with(binding(source_id=999, enum_name="Nope"))
    with pytest.raises(ValueError):
        family_install.install_layout(
            run, layout, tmp_path / "content", actor_bindings={"gen-001": 999})
    assert not run.exists()


def test_install_layout_rejects_missing_source_dir(tmp_path):
    run = tmp_path / "run"
    content_root = tmp_path / "content"
    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(
            run, layout, content_root, actor_bindings={"gen-001": 44})
    assert not run.exists()


def test_install_layout_rejects_missing_actor_binding(tmp_path):
    run = tmp_path / "run"
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(run, layout, content_root)
    assert not run.exists()


def test_install_layout_cached_replay(tmp_path):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    run = tmp_path / "run"

    calls = []

    def fake_installer(source_arg, run_arg, actors):
        calls.append((source_arg, run_arg, actors))
        return {"ok": True}

    family_install.register("dwarf_orange", fake_installer)

    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    family_install.install_layout(
        run, layout, content_root, actor_bindings={"gen-001": 211001})
    assert len(calls) == 1

    shutil.rmtree(content_root)

    replay = family_install.install_layout(
        run, layout, content_root, actor_bindings={"gen-001": 211001})

    assert replay.get("cached") is True
    assert replay["schema"] == 1
    assert replay["mode"] == "identity-binding"
    assert len(calls) == 1


def test_install_layout_rejects_partial_assets(tmp_path):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    run = tmp_path / "run"
    (run / "assets").mkdir(parents=True)
    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(
            run, layout, content_root, actor_bindings={"gen-001": 44})


def test_install_layout_rejects_stale_receipt(tmp_path):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    run = tmp_path / "run"
    run.mkdir(parents=True)
    (run / "p2-binding-receipt.json").write_text(
        '{"schema": 999}\n', encoding="utf-8")
    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(
            run, layout, content_root, actor_bindings={"gen-001": 44})


def test_launch_binds_p2_layout_identity(tmp_path, monkeypatch):
    """End-to-end: a generated p2_layout seed auto-stages its identity's content
    through the launcher keyed by enum name, without per-family manual flags."""
    import experimental.pikmin2_seed_bridge as bridge
    from experimental.pikmin2_staging import StagingError as _SE  # noqa: F401
    from randomizer import runner
    from randomizer.seed import generate

    calls = []
    family_install.register("dwarf_orange",
                            lambda source, run, actors: calls.append((source, run, actors)) or {"ok": True})

    placeholder = dict(schema="p2-placement-v1",
                       slots=[dict(uid=401, label="bulborb-slot", stage=1, terrain="ground",
                                   radius=300.0, evidence=dict(xyz=True, terrain=True, route=True))],
                       profiles=[dict(identity="BlueKochappy", terrains=["ground"],
                                      accepted_gates=["xyz"])])
    original = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: [44]
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    async def fake_serve(*args, **kwargs):
        pass

    monkeypatch.setattr(runner, "serve", fake_serve)
    try:
        manifest = generate("p2-binding-seed", collection_checks=True,
                            p2_enemies=True, p2_placement=placeholder)
        # The admission set must stay patched through launch: Session validates the
        # manifest via fingerprint(), which re-checks the current admission set.
        target = manifest["p2_layout"]["bindings"][0]["target"]
        runner.launch(manifest, tmp_path / "sess", assets=retail,
                      p2_content=content_root, p2_actors={target: 201001})
    finally:
        bridge.admitted_ids = original

    assert len(calls) == 1
    _, run_arg, actors = calls[0]
    assert actors == [(201001, "BlueKochappy")]
    receipts = list((tmp_path / "sess").glob("runs/*/p2-binding-receipt.json"))
    assert len(receipts) == 1
    stored = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert stored["mode"] == "identity-binding" and stored["bindings"] == manifest["p2_layout"]["bindings"]


def test_launch_replays_from_session_cache(tmp_path, monkeypatch):
    import experimental.pikmin2_seed_bridge as bridge
    from randomizer import runner
    from randomizer.seed import generate

    def fake(source, run, actors):
        (run / "p2-dwarf-orange-actors.txt").write_text(
            "P2_DWARF_ORANGE_ACTORS_1 1\n" + str(actors[0][0]) + "\n")
        (run / "assets" / "dataDir" / "courses" / "pikmin2room" /
         "fake_model.mod").write_bytes(b"model")
        return {"ok": True}

    family_install.register("dwarf_orange", fake)

    placeholder = dict(schema="p2-placement-v1",
                       slots=[dict(uid=401, label="bulborb-slot", stage=1,
                                   terrain="ground", radius=300.0,
                                   evidence=dict(xyz=True, terrain=True, route=True))],
                       profiles=[dict(identity="BlueKochappy", terrains=["ground"],
                                      accepted_gates=["xyz"])])
    original = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: [44]
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    async def fake_serve(*args, **kwargs):
        pass

    monkeypatch.setattr(runner, "serve", fake_serve)
    session = tmp_path / "sess"
    try:
        manifest = generate("p2-binding-seed", collection_checks=True,
                            p2_enemies=True, p2_placement=placeholder)
        # The admission patch must stay active through both launches because Session
        # re-validates the manifest via fingerprint() on every launch.
        target = manifest["p2_layout"]["bindings"][0]["target"]
        runner.launch(manifest, session, assets=retail,
                      p2_content=content_root, p2_actors={target: 211001})
        shutil.rmtree(content_root)
        runner.launch(manifest, session, assets=retail,
                      p2_content=content_root, p2_actors={target: 211001})
    finally:
        bridge.admitted_ids = original

    run_dirs = sorted((session / "runs").iterdir())
    assert len(run_dirs) == 2

    receipts = [run / "p2-binding-receipt.json" for run in run_dirs]
    cached_flags = [bool(json.loads(p.read_text(encoding="utf-8")).get("cached"))
                    for p in receipts]
    assert sorted(cached_flags) == [False, True]

    for run in run_dirs:
        assert (run / "p2-dwarf-orange-actors.txt").is_file()
        assert (run / "assets" / "dataDir" / "courses" / "pikmin2room" /
                "fake_model.mod").is_file()
    actors_files = [run / "p2-dwarf-orange-actors.txt" for run in run_dirs]
    model_files = [run / "assets" / "dataDir" / "courses" / "pikmin2room" /
                   "fake_model.mod" for run in run_dirs]
    assert actors_files[0].read_bytes() == actors_files[1].read_bytes()
    assert model_files[0].read_bytes() == model_files[1].read_bytes()


def test_install_layout_source_id_mismatch_rejected(tmp_path):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    run = tmp_path / "run"
    layout = layout_with(binding(source_id=999, enum_name="BlueKochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(
            run, layout, content_root, actor_bindings={"gen-001": 211001})
    assert not run.exists()


def test_install_layout_real_dwarf_orange_adapter(tmp_path):
    content_root = tmp_path / "content"
    make_dwarf_orange_source(content_root)
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    receipt = family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"gen-001": 211001}, retail_assets=retail)

    assert receipt["receipts"]["gen-001"]["species"] == "BlueKochappy"
    actors_txt = run / "p2-dwarf-orange-actors.txt"
    assert actors_txt.is_file()
    assert "211001" in actors_txt.read_text(encoding="ascii")
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("dwarf_orange_*.mod"))) == 15


def test_install_layout_validate_hook_rejects_bad_source(tmp_path):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(
            run, layout, content_root,
            actor_bindings={"gen-001": 211001}, retail_assets=retail)
    assert not (run / "assets").exists()


def test_install_layout_session_cache_replay(tmp_path):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    cache = tmp_path / "cache"
    cache.mkdir()
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"

    calls = []

    def fake_installer(source_arg, run_arg, actors):
        (Path(run_arg) / "installed.txt").write_text("done")
        calls.append((source_arg, run_arg, actors))
        return {"ok": True}

    family_install.register("dwarf_orange", fake_installer)

    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    family_install.install_layout(
        run1, layout, content_root, actor_bindings={"gen-001": 211001},
        cache_dir=cache)
    assert len(calls) == 1

    shutil.rmtree(content_root)

    replay = family_install.install_layout(
        run2, layout, content_root, actor_bindings={"gen-001": 211001},
        cache_dir=cache)

    assert len(calls) == 1
    assert replay.get("cached") is True
    assert (run2 / "installed.txt").is_file()


def test_install_layout_real_snow_adapter(tmp_path):
    content_root = tmp_path / "content"
    make_snow_source(content_root)
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(binding(source_id=45, enum_name="YellowKochappy"))
    receipt = family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"gen-001": 211045}, retail_assets=retail)

    assert receipt["receipts"]["gen-001"]
    actors_txt = run / "p2-snow-actors.txt"
    assert actors_txt.is_file()
    assert "211045" in actors_txt.read_text(encoding="ascii")
    assert (run / "p2-snow.txt").is_file()
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("snow_*.mod"))) == 15


def test_install_layout_two_families_staged_together(tmp_path):
    content_root = tmp_path / "content"
    make_dwarf_orange_source(content_root)
    make_snow_source(content_root)
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(
        binding(target="gen-001", source_id=44, enum_name="BlueKochappy"),
        binding(target="gen-002", source_id=45, enum_name="YellowKochappy"),
    )
    family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"gen-001": 211001, "gen-002": 211045},
        retail_assets=retail)

    assert (run / "p2-dwarf-orange-actors.txt").is_file()
    assert (run / "p2-snow-actors.txt").is_file()
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("dwarf_orange_*.mod"))) == 15
    assert len(list(room.glob("snow_*.mod"))) == 15
    assert len(list(room.glob("*.mod"))) == 30


def test_install_layout_rejects_wrong_source_hash_before_tree(tmp_path):
    content_root = tmp_path / "content"
    make_dwarf_orange_source(content_root)
    bank_json = content_root / "BlueKochappy" / "bank" / BANK_JSON
    metadata = json.loads(bank_json.read_text(encoding="utf-8"))
    metadata["reference_sha256"] = "0" * 64
    bank_json.write_text(json.dumps(metadata), encoding="utf-8")
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(
            run, layout, content_root,
            actor_bindings={"gen-001": 211001}, retail_assets=retail)
    assert not (run / "assets").exists()


def test_interrupted_cache_staging_fails_safe(tmp_path, monkeypatch):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    cache = tmp_path / "cache"
    cache.mkdir()
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"

    def fake_installer(source_arg, run_arg, actors):
        for name in ("a.txt", "b.txt", "c.txt"):
            (Path(run_arg) / name).write_text(name)
        return {"ok": True}

    family_install.register("dwarf_orange", fake_installer)

    real_copyfile = family_install.shutil.copyfile
    calls = {"n": 0}

    def flaky_copyfile(src, dst, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated interrupt")
        return real_copyfile(src, dst, *args, **kwargs)

    monkeypatch.setattr(family_install.shutil, "copyfile", flaky_copyfile)

    layout = layout_with(binding(source_id=44, enum_name="BlueKochappy"))
    with pytest.raises(RuntimeError):
        family_install.install_layout(
            run1, layout, content_root,
            actor_bindings={"gen-001": 211001}, cache_dir=cache)

    assert not list(cache.glob("p2bind-*"))

    monkeypatch.setattr(family_install.shutil, "copyfile", real_copyfile)
    receipt = family_install.install_layout(
        run2, layout, content_root,
        actor_bindings={"gen-001": 211001}, cache_dir=cache)

    assert receipt.get("cached") is not True
    assert (run2 / "a.txt").is_file()
    assert (run2 / "b.txt").is_file()
    assert (run2 / "c.txt").is_file()


def test_real_adapter_mid_install_failure_cleans_assets(tmp_path, monkeypatch):
    """Inject a crash mid-copy inside the REAL Snow adapter and assert no partial
    asset tree is left, then a re-run performs a fresh install."""
    content_root = tmp_path / "content"
    make_snow_source(content_root)
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    real_copyfile = family_install.shutil.copyfile
    calls = {"n": 0}

    def flaky(source_arg, destination, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("mid-copy interrupt")
        return real_copyfile(source_arg, destination, *args, **kwargs)

    monkeypatch.setattr(family_install.shutil, "copyfile", flaky)
    layout = layout_with(binding(source_id=45, enum_name="YellowKochappy"))
    with pytest.raises(RuntimeError):
        family_install.install_layout(
            run, layout, content_root,
            actor_bindings={"gen-001": 211045}, retail_assets=retail)
    assert not (run / "assets").exists()

    monkeypatch.setattr(family_install.shutil, "copyfile", real_copyfile)
    family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"gen-001": 211045}, retail_assets=retail)
    assert (run / "p2-snow-actors.txt").is_file()
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("snow_*.mod"))) == 15


def test_launch_wrong_source_leaves_no_run_dir(tmp_path, monkeypatch):
    """A wrong-source seed leaves NO runs/<token> tree at the launcher level."""
    import experimental.pikmin2_seed_bridge as bridge
    from randomizer import runner
    from randomizer.seed import generate

    content_root = tmp_path / "content"
    make_dwarf_orange_source(content_root)
    bank_json = content_root / "BlueKochappy" / "bank" / BANK_JSON
    metadata = json.loads(bank_json.read_text(encoding="utf-8"))
    metadata["reference_sha256"] = "0" * 64
    bank_json.write_text(json.dumps(metadata), encoding="utf-8")
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    placeholder = dict(schema="p2-placement-v1",
                       slots=[dict(uid=401, label="bulborb-slot", stage=1, terrain="ground",
                                   radius=300.0, evidence=dict(xyz=True, terrain=True, route=True))],
                       profiles=[dict(identity="BlueKochappy", terrains=["ground"],
                                      accepted_gates=["xyz"])])
    original = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: [44]

    async def fake_serve(*args, **kwargs):
        pass

    monkeypatch.setattr(runner, "serve", fake_serve)
    session = tmp_path / "sess"
    try:
        manifest = generate("p2-binding-seed", collection_checks=True,
                            p2_enemies=True, p2_placement=placeholder)
        target = manifest["p2_layout"]["bindings"][0]["target"]
        with pytest.raises(StagingError):
            runner.launch(manifest, session, assets=retail,
                          p2_content=content_root, p2_actors={target: 211001})
    finally:
        bridge.admitted_ids = original

    assert list((session / "runs").iterdir()) == []


@pytest.mark.parametrize("failure", [ValueError, RuntimeError])
def test_launch_install_error_leaves_no_run_dir(tmp_path, monkeypatch, failure):
    """A launcher-stage install failure (non-StagingError) must leave NO
    runs/<token> tree: NativeRun has already seeded bootstrap.txt/state.txt."""
    import experimental.pikmin2_seed_bridge as bridge
    from randomizer import runner
    from randomizer.seed import generate

    placeholder = dict(schema="p2-placement-v1",
                       slots=[dict(uid=401, label="bulborb-slot", stage=1, terrain="ground",
                                   radius=300.0, evidence=dict(xyz=True, terrain=True, route=True))],
                       profiles=[dict(identity="BlueKochappy", terrains=["ground"],
                                      accepted_gates=["xyz"])])
    original = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: [44]

    def boom(*args, **kwargs):
        raise failure("adapter crash")

    monkeypatch.setattr(family_install, "install_layout", boom)

    async def fake_serve(*args, **kwargs):
        pass

    monkeypatch.setattr(runner, "serve", fake_serve)

    content_root = tmp_path / "content"
    make_source_dir(content_root, "BlueKochappy")
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)
    session = tmp_path / "sess"
    try:
        manifest = generate("p2-binding-seed", collection_checks=True,
                            p2_enemies=True, p2_placement=placeholder)
        target = manifest["p2_layout"]["bindings"][0]["target"]
        with pytest.raises(failure):
            runner.launch(manifest, session, assets=retail,
                          p2_content=content_root, p2_actors={target: 211001})
    finally:
        bridge.admitted_ids = original

    assert list((session / "runs").iterdir()) == []


def test_install_layout_mid_failure_removes_run_root_sidecars(tmp_path):
    """A later family's failure must remove the run-root sidecars an earlier
    fully-installed family already copied (e.g. p2-snow.txt), not just run/assets."""
    content_root = tmp_path / "content"
    make_snow_source(content_root)
    make_source_dir(content_root, "BlueKochappy")
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    def failing(source, run_arg, actors):
        raise RuntimeError("second family crash")

    family_install.register("dwarf_orange", failing)

    layout = layout_with(
        binding(target="gen-001", source_id=45, enum_name="YellowKochappy"),
        binding(target="gen-002", source_id=44, enum_name="BlueKochappy"),
    )
    with pytest.raises(RuntimeError):
        family_install.install_layout(
            run, layout, content_root,
            actor_bindings={"gen-001": 211045, "gen-002": 211001},
            retail_assets=retail)

    assert not (run / "assets").exists()
    assert not (run / "p2-snow.txt").exists()
    assert not (run / "p2-snow-actors.txt").exists()


def test_install_layout_real_kochappy_adapter(tmp_path):
    content_root = tmp_path / "content"
    make_kochappy_source(content_root)
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(binding(source_id=1, enum_name="Kochappy"))
    family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"gen-001": 211100}, retail_assets=retail)

    actors_txt = run / "p2-kochappy-actors.txt"
    assert actors_txt.is_file()
    assert "211100" in actors_txt.read_text(encoding="ascii")
    assert (run / "p2-kochappy-bank.txt").is_file()
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("kochappy_*.mod"))) == 15


def test_install_layout_three_families_staged_together(tmp_path):
    content_root = tmp_path / "content"
    make_dwarf_orange_source(content_root)
    make_snow_source(content_root)
    make_kochappy_source(content_root)
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(
        binding(target="gen-001", source_id=44, enum_name="BlueKochappy"),
        binding(target="gen-002", source_id=45, enum_name="YellowKochappy"),
        binding(target="gen-003", source_id=1, enum_name="Kochappy"),
    )
    family_install.install_layout(
        run, layout, content_root,
        actor_bindings={"gen-001": 211001, "gen-002": 211045, "gen-003": 211100},
        retail_assets=retail)

    assert (run / "p2-dwarf-orange-actors.txt").is_file()
    assert (run / "p2-snow-actors.txt").is_file()
    assert (run / "p2-kochappy-actors.txt").is_file()
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("dwarf_orange_*.mod"))) == 15
    assert len(list(room.glob("snow_*.mod"))) == 15
    assert len(list(room.glob("kochappy_*.mod"))) == 15


def test_install_layout_kochappy_validate_rejects_bad_source(tmp_path):
    content_root = tmp_path / "content"
    make_source_dir(content_root, "Kochappy")
    run = tmp_path / "run"
    retail = tmp_path / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)

    layout = layout_with(binding(source_id=1, enum_name="Kochappy"))
    with pytest.raises(StagingError):
        family_install.install_layout(
            run, layout, content_root,
            actor_bindings={"gen-001": 211100}, retail_assets=retail)
    assert not (run / "assets").exists()
