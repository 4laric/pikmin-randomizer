"""Dev-console session support (#942): dev target scheme, dev seed, launcher wiring."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randomizer import dev_console  # noqa: E402
from randomizer.seed import PLAYABLE_P2_SPECIES, validate  # noqa: E402


def test_dev_target_scheme_round_trips():
    assert dev_console.dev_target(41) == str(0xDE000000 + 41)
    assert dev_console.is_dev_target(dev_console.dev_target(78))
    assert dev_console.dev_target_source(dev_console.dev_target(78)) == 78
    assert not dev_console.is_dev_target("1254096625")  # a real FoH slot uid
    assert not dev_console.is_dev_target("0")
    assert not dev_console.is_dev_target(None)
    with pytest.raises(ValueError):
        dev_console.dev_target(0)
    with pytest.raises(ValueError):
        dev_console.dev_target_source("1254096625")


def test_dev_layout_binds_every_species_to_its_dev_target():
    from experimental.pikmin2_seed_bridge import bootstrap_for_manifest
    layout = dev_console.build_dev_layout([41, 78, 38, 32])
    assert [b["source_id"] for b in layout["bindings"]] == [41, 78, 38, 32]
    assert [b["target"] for b in layout["bindings"]] == [dev_console.dev_target(i) for i in (41, 78, 38, 32)]
    assert layout["bindings"][0]["enum_name"] == "Fuefuki"
    actors = dev_console.actor_bindings(layout)
    assert actors == {dev_console.dev_target(i): 0xDE000000 + i for i in (41, 78, 38, 32)}
    manifest = dev_console.build_dev_manifest([41, 78, 38, 32])
    line = bootstrap_for_manifest(manifest)
    assert line.startswith("ENEMY_P2 1 ") and f" 4 {dev_console.dev_target(41)} 41 " in line
    with pytest.raises(ValueError):
        dev_console.build_dev_layout([])
    with pytest.raises(ValueError):
        dev_console.build_dev_layout([41, 41])


def test_dev_manifest_is_a_valid_forest_seed_for_the_whole_pool():
    manifest = dev_console.build_dev_manifest(list(PLAYABLE_P2_SPECIES))
    validate(manifest)
    assert manifest["profile"] == "foh-day2"
    assert "p2-enemy-bridge-v1" in manifest["capabilities"]
    assert len(manifest["p2_layout"]["bindings"]) == len(PLAYABLE_P2_SPECIES) <= 64  # native ENEMY_P2 cap
    assert manifest["enemy_mask"] == 0 and "spawn_layout" not in manifest


def test_staged_species_reads_prepared_content(tmp_path):
    from scripts.p2_prepare_content import ENUM_FOR_SOURCE
    with pytest.raises(FileNotFoundError):
        dev_console.staged_species(tmp_path)
    (tmp_path / "prepared.json").write_text(json.dumps({"extracted": [41, 78, 99]}), encoding="utf-8")
    (tmp_path / ENUM_FOR_SOURCE[41]).mkdir()
    # 78 is extracted but its directory is missing; 99 is not playable.
    assert dev_console.staged_species(tmp_path) == [41]
    assert dev_console.staged_species(tmp_path, species=[78, 41]) == [41]


def test_native_environment_switches_console_on(tmp_path):
    env = dev_console.native_environment(tmp_path / "dev-console.txt")
    assert env["PIKMIN_DEV_CONSOLE"] == "1"
    assert env["PIKMIN_DEV_CONSOLE_SCRIPT"] == str((tmp_path / "dev-console.txt").resolve())


def test_run_cli_dev_console_flag_sets_environment(tmp_path, monkeypatch):
    from randomizer import __main__ as cli
    from randomizer import runner
    manifest = dev_console.build_dev_manifest([41])
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    seen = {}

    def fake_launch(*args, **kwargs):
        import os
        seen["env"] = dict(os.environ)

    monkeypatch.delenv("PIKMIN_DEV_CONSOLE", raising=False)
    monkeypatch.delenv("PIKMIN_DEV_CONSOLE_SCRIPT", raising=False)
    monkeypatch.setattr(cli, "launch", fake_launch)
    monkeypatch.setattr(sys, "argv", ["randomizer", "run", str(path), "--session-dir", str(tmp_path / "s"), "--dev-console"])
    cli.main()
    assert seen["env"]["PIKMIN_DEV_CONSOLE"] == "1"
    assert seen["env"]["PIKMIN_DEV_CONSOLE_SCRIPT"] == str((tmp_path / "s" / "dev-console.txt").resolve())


def test_launcher_script_reuses_prepared_content_and_writes_seed(tmp_path, monkeypatch):
    from scripts import p2_dev_console as launcher
    from scripts.p2_prepare_content import ENUM_FOR_SOURCE
    content = tmp_path / "content"
    content.mkdir()
    (content / "prepared.json").write_text(json.dumps({"extracted": [41, 38], "pose_limit": 24}), encoding="utf-8")
    (content / ENUM_FOR_SOURCE[41]).mkdir()
    (content / ENUM_FOR_SOURCE[38]).mkdir()
    calls = []
    monkeypatch.setattr(launcher.subprocess, "run", lambda *a, **k: calls.append(a))
    session = tmp_path / "session"
    assert launcher.main(["--content", str(content), "--session-dir", str(session), "--prepare-only"]) == 0
    assert calls == []  # content reused, no extraction
    manifest = json.loads((session / "dev-seed.json").read_text(encoding="utf-8"))
    assert [b["source_id"] for b in manifest["p2_layout"]["bindings"]] == [38, 41]
    actors = json.loads((session / "dev-actors.json").read_text(encoding="utf-8"))
    assert actors == {dev_console.dev_target(38): 0xDE000000 + 38, dev_console.dev_target(41): 0xDE000000 + 41}
    assert (session / "dev-console.txt").is_file()
    # First-time preparation runs the extractor once for the requested species.
    fresh = tmp_path / "fresh"
    with pytest.raises(SystemExit):
        launcher.ensure_content(None, fresh, [41])
    launcher.ensure_content(tmp_path / "p2.iso", fresh, [41], run=lambda cmd, check: calls.append(cmd) or
                            (fresh / "prepared.json").write_text(json.dumps({"extracted": [41]}), encoding="utf-8") or
                            (fresh / ENUM_FOR_SOURCE[41]).mkdir())
    assert len(calls) == 1 and "--species" in calls[0] and calls[0][calls[0].index("--species") + 1] == "41"
    with pytest.raises(SystemExit):
        launcher.parse_species("99")


def test_dev_console_refuses_sparse_prepared_content(tmp_path):
    from scripts import p2_dev_console as launcher
    from scripts.p2_prepare_content import ENUM_FOR_SOURCE
    for limit in (12, None):
        content = tmp_path / f"c{limit}"
        content.mkdir()
        summary = {"extracted": [41]}
        if limit is not None:
            summary["pose_limit"] = limit
        (content / "prepared.json").write_text(json.dumps(summary), encoding="utf-8")
        (content / ENUM_FOR_SOURCE[41]).mkdir()
        with pytest.raises(SystemExit, match="dense default"):
            launcher.ensure_content(None, content, [41])
        assert launcher.ensure_content(None, content, [41], allow_sparse=True) == [41]
    assert launcher.DEFAULT_CONTENT.name == "p2-content-dense"


def _native_parser():
    import os
    candidates = [ROOT / "engine" / "pc_port" / "pc_dev_console_parser.h",
                  Path(os.environ.get("PIKMIN_NATIVE_SRC", ROOT / "native")) / "pc_port" / "pc_dev_console_parser.h"]
    return next((p for p in candidates if p.is_file()), None)


@pytest.mark.skipif(_native_parser() is None, reason="native dev console source not exported yet")
def test_native_species_and_arena_tables_match_root():
    from randomizer.p2_boss_arenas import P1_BOSS_ARENAS
    text = _native_parser().read_text(encoding="utf-8")
    assert f"kDevTargetBase = 0x{dev_console.DEV_TARGET_BASE:08X}u" in text
    native_ids = [int(m) for m in re.findall(r"^\s*\{(\d+), \"\w+\", \"[^\"]+\"\},", text, re.M)]
    assert native_ids == list(PLAYABLE_P2_SPECIES)
    arenas = re.findall(r"\{\"(\w+)\", (\d), (-?[\d.]+)f, (-?[\d.]+)f, (-?[\d.]+)f\}", text)
    assert [(a[0], int(a[1]), [float(a[2]), float(a[3]), float(a[4])]) for a in arenas] == \
        [(row["id"], row["stage"], row["center"]) for row in P1_BOSS_ARENAS]
