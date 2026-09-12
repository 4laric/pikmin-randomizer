import importlib.util
import json
import sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from randomizer.seed import generate, fingerprint

spec = importlib.util.spec_from_file_location("pik_launcher", REPO / "launcher" / "launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    return tmp_path / "Roaming"


def test_config_round_trip(appdata):
    assert launcher.load_config() == {}
    launcher.save_config({"assets": "X:\\assets", "server": "archipelago.gg:38281"})
    assert launcher.config_path() == appdata / "PikminRandomizer" / "config.json"
    assert launcher.load_config() == {"assets": "X:\\assets", "server": "archipelago.gg:38281"}


def test_assets_validation(tmp_path):
    assert "not a directory" in launcher.assets_problem(tmp_path / "missing")
    assert "dataDir" in launcher.assets_problem(tmp_path)
    (tmp_path / "dataDir").mkdir()
    assert "stages" in launcher.assets_problem(tmp_path)
    (tmp_path / "dataDir" / "stages").mkdir()
    assert launcher.assets_problem(tmp_path) is None


def test_ask_assets_retries_then_fails(tmp_path, appdata):
    answers = iter([str(tmp_path / "a"), str(tmp_path / "b"), str(tmp_path / "c")])
    with pytest.raises(launcher.LaunchError, match="three attempts"):
        launcher.ask_assets(ask=lambda prompt: next(answers), dialog=lambda: None)
    good = tmp_path / "good"
    (good / "dataDir" / "stages").mkdir(parents=True)
    answers = iter([str(tmp_path / "bad"), '"' + str(good) + '"'])
    config = {}
    assert launcher.resolve_assets(config, ask=lambda prompt: next(answers), dialog=lambda: None) == str(good.resolve())
    assert launcher.load_config()["assets"] == str(good.resolve())


def test_session_dir(tmp_path, appdata):
    manifest = generate("t")
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps(manifest))
    expected = appdata / "PikminRandomizer" / "sessions" / fingerprint(manifest)[:16]
    assert launcher.session_dir(manifest, seed) == expected
    (tmp_path / "session").mkdir()
    assert launcher.session_dir(manifest, seed) == (tmp_path / "session").resolve()


def test_seed_card(tmp_path):
    manifest = generate("t", slot="Olimar")
    (tmp_path / "VERSION").write_text("1.2.3\n")
    card = launcher.seed_card(manifest, tmp_path / "seed.json", root=tmp_path)
    assert "Olimar" in card and fingerprint(manifest)[:16] in card and "1.2.3" in card
    assert manifest["profile"] in card and "solo" in card


def test_build_command(tmp_path):
    command = launcher.build_command(tmp_path / "seed.json", tmp_path / "s", tmp_path / "bin" / "nectar.exe",
                                     "X:\\assets", server="host:1", python="py.exe")
    assert command[:4] == ["py.exe", "-m", "randomizer", "run"]
    assert command[4] == str((tmp_path / "seed.json").resolve())
    assert command[command.index("--assets") + 1] == "X:\\assets"
    assert command[-2:] == ["--server", "host:1"]
    assert "--server" not in launcher.build_command("s.json", "d", "e", "a")


def test_explain_failure(tmp_path):
    session = tmp_path / "session"
    run = session / "runs" / "abc"
    run.mkdir(parents=True)
    (run / "native.log").write_text("boom")
    assert "Another launcher is already running" in launcher.explain_failure(1, "ValueError: another runner owns this session directory", session)
    assert "Choose your disc image" in launcher.explain_failure(1, "--assets must point to the extracted assets directory containing dataDir/stages/", session)
    assert "complete Windows release ZIP" in launcher.explain_failure(1, "ModuleNotFoundError: No module named 'websockets'", session)
    native = launcher.explain_failure(1, "RuntimeError: native process exited 3; see x", session)
    assert "game exited" in native and str(run / "native.log") in native
    assert "refused" in launcher.explain_failure(1, "ValueError: AP connection refused: ['InvalidSlot']", session)
    assert "exited with code 7" in launcher.explain_failure(7, "mystery", session)


def test_choose_seed(tmp_path):
    with pytest.raises(launcher.LaunchError, match="No seed given"):
        launcher.choose_seed(None, root=tmp_path)
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    (seeds / "b.json").write_text("{}")
    (seeds / "a.json").write_text("{}")
    assert launcher.choose_seed(None, root=tmp_path, ask=lambda p: "2") == seeds / "b.json"
    (seeds / "seed.json").write_text("{}")
    assert launcher.choose_seed(None, root=tmp_path) == seeds / "seed.json"


def test_password_prompt_only_when_room_has_one():
    assert launcher.ask_password(ask=lambda p: "n", secret=lambda p: "x") is None
    assert launcher.ask_password(ask=lambda p: "y", secret=lambda p: "hunter2") == "hunter2"

def test_solo_creation_is_local_unique_and_valid(appdata):
    first = launcher.create_solo_seed()
    second = launcher.create_solo_seed()
    a = launcher.load_manifest(first)
    b = launcher.load_manifest(second)
    assert first != second and first.parent == launcher.app_dir() / "seeds"
    assert a["mode"] == "solo" and a["goal_mode"] == "emperor_bulblax"
    assert launcher.short_fingerprint(a) != launcher.short_fingerprint(b)
    assert a["permanent_checks"]
    original = first.read_bytes()
    launcher.create_solo_seed("named run")
    assert first.read_bytes() == original


@pytest.mark.parametrize("address", ["archipelago.gg:38281", " wss://example.org:443 ", "ws://127.0.0.1:1234", "[::1]:1234"])
def test_server_address_accepts_game_endpoint(address):
    assert launcher.validate_server(address) == address.strip()


@pytest.mark.parametrize("address", ["", "https://archipelago.gg/room/abc", "example.org", "example.org:0", "example.org:99999", "ws://user:secret@example.org:1234", "example.org:1234/path", "bad host:1234"])
def test_server_address_rejects_web_pages_and_invalid_input(address):
    with pytest.raises(launcher.LaunchError):
        launcher.validate_server(address)

def test_diagnostics_do_not_copy_secrets_or_raw_paths(appdata):
    manifest = generate("secret seed name", "ap", slot="private player")
    report = launcher.diagnostic_report(manifest, "C:/private/assets", "password=secret\nC:/Users/Private\nwss://secret@private.server:1234\nAP connection handshake failed\ninstaller exit 7")
    for value in ("secret", "Private", "private", "password=", "wss://", "C:/"):
        assert value not in report
    assert "handshake_failed" in report and '"7"' in report


def test_run_summary_does_not_create_or_reset_session(appdata, tmp_path):
    manifest = generate("continue")
    seed = tmp_path / "seed.json"
    folder = launcher.session_dir(manifest, seed)
    assert launcher.run_summary(manifest, seed).startswith("New run")
    assert not folder.exists()
    folder.mkdir(parents=True)
    (folder / "session.json").write_text(json.dumps({"fingerprint": fingerprint(manifest), "checked": ["a"]}))
    assert "1 checks recorded" in launcher.run_summary(manifest, seed)
