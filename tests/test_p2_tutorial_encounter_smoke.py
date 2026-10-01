import json
from pathlib import Path
import subprocess
import sys
import pytest
from scripts.run_pikmin2_tutorial_encounter import arguments, environment, fresh_attempt, next_attempt


def test_actual_human_cli_wiring_without_launch():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "scripts/play_pikmin2_tutorial_encounter_smoke.py"), "--plan"],
                            cwd=root, text=True, capture_output=True, check=True)
    plan = json.loads(result.stdout)
    assert plan["seconds_per_child"] == 60
    assert plan["environment"]["PIKMIN_RANDOMIZER_TEST_BACKGROUND"] == "2"
    assert plan["environment"]["P2_TUTORIAL_HUMAN"] == "1"
    assert not plan["human_launched"]


def test_scrub_inherited_automatic_and_negative_flags(monkeypatch, tmp_path):
    for key in ("PIKMIN_RANDOMIZER_AUTOPLAY", "P2_TUTORIAL_FORCE_CAPTAIN_DOWN", "P2_TUTORIAL_READY_ONLY", "COOP_ONION_HUMAN", "COOP_X"):
        monkeypatch.setenv(key, "1")
    env = environment("human", tmp_path, tmp_path / "save", tmp_path / "fixture.exe")
    assert env["PIKMIN_RANDOMIZER_AUTOPLAY"] == "0"
    assert not any(key in env for key in ("P2_TUTORIAL_FORCE_CAPTAIN_DOWN", "P2_TUTORIAL_READY_ONLY", "COOP_ONION_HUMAN", "COOP_X"))
    assert env["NECTAR_SAVE_DIR"] == str(tmp_path / "save")


def test_reset_regenerates_private_arena_save_and_only_expected_exit(tmp_path):
    args = arguments(["--workspace", str(tmp_path)])
    first, one = fresh_attempt(args, 0)
    second, two = fresh_attempt(args, 1)
    assert first != second and one["NECTAR_SAVE_DIR"] != two["NECTAR_SAVE_DIR"]
    assert next_attempt("human", 90, 0, 2)
    assert not next_attempt("human", 86, 0, 2)
    assert not next_attempt("human", 90, 2, 2)
    assert not next_attempt("reset", 90, 0, 2)


def test_hidden_readiness_uses_physical_input_path(tmp_path):
    env = environment("ready", tmp_path, tmp_path / "save", tmp_path / "fixture.exe")
    assert env["P2_TUTORIAL_HUMAN"] == "1"
    assert env["P2_TUTORIAL_READY_ONLY"] == "1"
    assert env["PIKMIN_RANDOMIZER_TEST_BACKGROUND"] == "1"


@pytest.mark.parametrize("values", [["--seconds", "61"], ["--seconds", "0"], ["--max-resets", "3"]])
def test_refuse_unbounded_runtime_or_reset_count(values):
    with pytest.raises(SystemExit): arguments(values)


def test_human_wrapper_refuses_automatic_mode():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "scripts/play_pikmin2_tutorial_encounter_smoke.py"),
                             "--mode", "positive", "--plan"], cwd=root, text=True, capture_output=True)
    assert result.returncode != 0
    assert "explicit automated modes" in result.stderr
