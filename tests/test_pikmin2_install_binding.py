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


def test_resolve_family_int_and_enum():
    assert family_install.resolve_family(44) == "dwarf_orange"
    assert family_install.resolve_family("BlueKochappy") == "dwarf_orange"
    assert family_install.resolve_family("bluekochappy") == "dwarf_orange"


def test_resolve_family_unknown_identity():
    for bad in (999, "Nope", "Kochappy", 1):
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
