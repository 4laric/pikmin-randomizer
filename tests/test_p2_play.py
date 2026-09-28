"""Unit tests for scripts/p2_play.py (no ISO extraction, no launch).

Covers path-length refusal, per-ISO content-cache reuse, solo/AP command wiring
and the dry-run step report. A real staged run is proven by the handoff, not
here; nothing in these tests launches Archipelago, the game or the runner.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import p2_play


def fake_iso(tmp_path, data=b"fake-iso-bytes"):
    iso = tmp_path / "game.iso"
    iso.write_bytes(data)
    return iso


def cached_content(tmp_path, iso):
    cache = tmp_path / "cache"
    content = p2_play.content_cache_dir(cache, iso)
    content.mkdir(parents=True)
    (content / "prepared.json").write_text("{}\n")
    return cache, content


def dry_args(tmp_path, *extra):
    return ["--iso", str(fake_iso(tmp_path)),
            "--cache-dir", str(tmp_path / "cache"),
            "--work-dir", str(tmp_path / "work"),
            "--session-dir", str(tmp_path / "session"),
            "--dry-run", *extra]


def test_ensure_run_path_refuses_long_path():
    with pytest.raises(p2_play.PlayPathError):
        p2_play.ensure_run_path("C:/" + "a" * 220)
    assert p2_play.ensure_run_path("C:/short") == Path("C:/short")


def test_next_session_dir_increments_past_existing(tmp_path):
    (tmp_path / "demo-1").mkdir()
    assert p2_play.next_session_dir(tmp_path, "demo") == tmp_path / "demo-2"


def test_next_session_dir_sanitizes_seed(tmp_path):
    assert p2_play.next_session_dir(tmp_path, "a b/c") == tmp_path / "a_b_c-1"


def test_next_session_dir_refuses_long_base():
    with pytest.raises(p2_play.PlayPathError):
        p2_play.next_session_dir("C:/" + "b" * 220, "demo")


def test_content_cache_keyed_per_iso(tmp_path):
    iso = fake_iso(tmp_path)
    one = p2_play.content_cache_dir(tmp_path / "c", iso)
    two = p2_play.content_cache_dir(tmp_path / "c", iso)
    assert one == two
    assert one.parent.name == "p2-content"
    other = fake_iso(tmp_path, data=b"other-iso")
    assert p2_play.content_cache_dir(tmp_path / "c", other) != one


def test_content_is_cached_uses_prepared_marker(tmp_path):
    assert not p2_play.content_is_cached(tmp_path)
    (tmp_path / "prepared.json").write_text("{}")
    assert p2_play.content_is_cached(tmp_path)


def test_ensure_content_extracts_once_then_reuses(tmp_path, monkeypatch):
    iso = fake_iso(tmp_path)
    content = tmp_path / "cache" / "p2-content" / "hash"
    calls = []

    def fake_prepare(iso_arg, out, research=None, pose_limit=3, wanted=None):
        calls.append(Path(out))
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "prepared.json").write_text("{}\n")

    monkeypatch.setattr(p2_play.prepare, "prepare_content_root", fake_prepare)

    assert p2_play.ensure_content(iso, content, "playable", 3, None) is True
    assert len(calls) == 1
    assert p2_play.content_is_cached(content)
    assert not (content.parent / (content.name + ".partial")).exists()

    assert p2_play.ensure_content(iso, content, "playable", 3, None) is False
    assert len(calls) == 1


def test_wanted_source_ids_pools(tmp_path, monkeypatch):
    assert p2_play.wanted_source_ids("playable") == list(p2_play.prepare.PLAYABLE_SOURCE_IDS)
    monkeypatch.setattr(p2_play.prepare, "admitted_source_ids", lambda: [9, 44, 54])
    assert p2_play.wanted_source_ids("all") == [9, 44, 54]


def test_solo_generate_command_wiring():
    command = p2_play.solo_generate_command("demo", Path("m.json"), "playable",
                                            python="py")
    assert command[:3] == ["py", "-m", "randomizer"]
    assert ["--seed", "demo"] == command[4:6]
    assert "--p2-enemies" in command
    assert command[command.index("--p2-species") + 1] == "playable"
    assert "--output" in command
    all_pool = p2_play.solo_generate_command("demo", Path("m.json"), "all", python="py")
    assert "--p2-species" not in all_pool


def test_run_command_wiring(tmp_path):
    base = p2_play.run_command(tmp_path / "m.json", tmp_path / "s",
                               tmp_path / "assets", p2_content=tmp_path / "content",
                               p2_actors=tmp_path / "actors.json", python="py")
    assert base[:4] == ["py", "-m", "randomizer", "run"]
    assert "--session-dir" in base and "--assets" in base
    assert base[base.index("--p2-content") + 1] == str(tmp_path / "content")
    assert base[base.index("--p2-actors") + 1] == str(tmp_path / "actors.json")
    assert "--exe" not in base and "--server" not in base
    full = p2_play.run_command(tmp_path / "m.json", tmp_path / "s",
                               tmp_path / "assets", exe=tmp_path / "nectar.exe",
                               server="localhost:38281", python="py")
    assert full[full.index("--exe") + 1] == str(tmp_path / "nectar.exe")
    assert full[full.index("--server") + 1] == "localhost:38281"


def test_ap_command_wiring(tmp_path):
    archive = tmp_path / "pikmin_randomizer.apworld"
    build = p2_play.apworld_command(archive, python="py")
    assert build[1].endswith("build_apworld.py")
    assert build[build.index("--output") + 1] == str(archive)
    generate = p2_play.ap_generate_command(Path("C:/AP"), tmp_path / "players",
                                           tmp_path / "out", python="py")
    assert generate[1].replace("\\", "/").endswith("C:/AP/Generate.py")
    assert generate[generate.index("--player_files_path") + 1] == str(tmp_path / "players")
    assert generate[generate.index("--outputpath") + 1] == str(tmp_path / "out")
    assert p2_play.apworld_install_path("C:/AP").name == "pikmin_randomizer.apworld"


def test_dry_run_prints_every_step(tmp_path, capsys):
    iso = fake_iso(tmp_path)
    cache, _ = cached_content(tmp_path, iso)
    rc = p2_play.main(["--iso", str(iso), "--seed", "demo", "--dry-run",
                       "--cache-dir", str(cache),
                       "--session-dir", str(tmp_path / "session")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "generate:" in out
    assert "content (cached):" in out
    assert "actors:" in out
    assert "session dir:" in out
    assert "run command:" in out
    assert "randomizer run" in out
    assert not (tmp_path / "session").exists()


def test_dry_run_reports_extract_when_uncached(tmp_path, capsys):
    iso = fake_iso(tmp_path)
    rc = p2_play.main(["--iso", str(iso), "--seed", "demo", "--dry-run",
                       "--cache-dir", str(tmp_path / "cache"),
                       "--session-dir", str(tmp_path / "session")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "content (extract)" in out
    assert not (tmp_path / "cache").exists()


def test_dry_run_ap_wires_generation_and_server(tmp_path, capsys):
    iso = fake_iso(tmp_path)
    cache, _ = cached_content(tmp_path, iso)
    yaml = tmp_path / "player.yaml"
    yaml.write_text("name: Alari\n")
    rc = p2_play.main(["--iso", str(iso), "--apworld-yaml", str(yaml),
                       "--server", "localhost:38281", "--dry-run",
                       "--cache-dir", str(cache),
                       "--session-dir", str(tmp_path / "session")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "build_apworld.py" in out
    assert "Generate.py" in out
    assert "--player_files_path" in out
    assert "localhost:38281" in out
    assert "--server" in out


def test_rejects_both_modes(tmp_path):
    with pytest.raises(ValueError):
        p2_play.main(["--iso", str(fake_iso(tmp_path)), "--seed", "demo",
                      "--apworld-yaml", str(tmp_path / "x.yaml"),
                      "--server", "host:1", "--dry-run"])


def test_ap_requires_server(tmp_path):
    with pytest.raises(ValueError):
        p2_play.main(["--iso", str(fake_iso(tmp_path)),
                      "--apworld-yaml", str(tmp_path / "x.yaml"), "--dry-run"])


def test_dry_run_refuses_long_session_dir(tmp_path):
    with pytest.raises(p2_play.PlayPathError):
        p2_play.main(["--iso", str(fake_iso(tmp_path)), "--seed", "demo",
                      "--dry-run", "--cache-dir", str(tmp_path / "cache"),
                      "--session-dir", "C:/" + "z" * 220])
