"""Compiled production protocol/selection checks; no engine save or actor claim.

Set PIKMIN_CAPTAIN_PROBE to tools/test_p2_captain_bootstrap.cpp linked against
pc_randomizer.cpp, pc_p2_delivery_host.cpp and pc_p2_second_captain.cpp. The
NaviMgr link stub is used only to avoid engine actor dependencies.
"""
import os
from pathlib import Path
import subprocess

import pytest

from randomizer.runner import NativeRun
from randomizer.seed import generate
from randomizer.session import Session

PROBE = os.environ.get("PIKMIN_CAPTAIN_PROBE")
pytestmark = pytest.mark.skipif(not PROBE, reason="set PIKMIN_CAPTAIN_PROBE to compiled native consumer")


def run_probe(run=None, ambient=None):
    env = dict(os.environ)
    env.pop("PIKMIN_P2_SECOND_CAPTAIN", None)
    if ambient is not None:
        env["PIKMIN_P2_SECOND_CAPTAIN"] = ambient
    args = [PROBE]
    if run is not None:
        run.write_state(True)
        args += ["--randomizer-seed", str(run.bootstrap)]
    return subprocess.run(args, env=env, capture_output=True, text=True, timeout=15)


def make_run(tmp_path, second=False, p2=True, purple=False, checks=False):
    options = dict(p2_enemies=p2, p2_second_captain=second)
    if p2:
        options.update(p2_species=[2], p2_checks=checks)
    manifest = generate("captain-native-1080", **options)
    session = Session(manifest, tmp_path)
    return session, NativeRun(session, purple_campaign=purple)


@pytest.mark.parametrize("ambient", [None, "0", "1"])
@pytest.mark.parametrize("second,p2", [(True, True), (False, True), (False, False)])
def test_seed_choice_overrides_ambient_and_handshakes(tmp_path, ambient, second, p2):
    session, run = make_run(tmp_path, second=second, p2=p2)
    result = run_probe(run, ambient)
    assert result.returncode == 0, result.stdout + result.stderr
    expected = int(second)
    assert f"enabled=1 second={expected} requested={expected} capacity={1+expected}" in result.stdout
    run.poll()
    assert run.handshaken
    # A fresh run of this session has the same option without inherited opt-in.
    again = NativeRun(session)
    result = run_probe(again)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"requested={expected} capacity={1+expected}" in result.stdout
    again.poll()
    assert again.handshaken


@pytest.mark.parametrize("ambient,expected", [(None, 0), ("0", 0), ("1", 1)])
def test_standalone_experimental_optin_still_works(ambient, expected):
    result = run_probe(ambient=ambient)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"enabled=0 second=0 requested={expected} capacity={1+expected}" in result.stdout


@pytest.mark.parametrize("suffix", ["CAPTAINS 0", "CAPTAINS 1", "CAPTAINS 3", "CAPTAINS -2",
                                   "CAPTAINS 02", "CAPTAINS +2",
                                   "CAPTAINS x", "CAPTAINS 2 CAPTAINS 2"])
def test_native_rejects_invalid_count_or_duplicate(tmp_path, suffix):
    _, run = make_run(tmp_path, second=True)
    run.bootstrap.write_text(run.bootstrap.read_text().replace("CAPTAINS 2", suffix))
    result = run_probe(run)
    assert result.returncode != 0
    assert not (run.directory / "hello.txt").exists()


def test_native_rejects_captains_without_p2(tmp_path):
    _, run = make_run(tmp_path, p2=False)
    run.bootstrap.write_text(run.bootstrap.read_text().replace("END\n", "CAPTAINS 2\nEND\n"))
    result = run_probe(run)
    assert result.returncode != 0
    assert not (run.directory / "hello.txt").exists()


@pytest.mark.parametrize("purple,checks", [(True, False), (False, True), (True, True)])
def test_extension_composition(tmp_path, purple, checks):
    _, run = make_run(tmp_path, second=True, purple=purple, checks=checks)
    result = run_probe(run)
    assert result.returncode == 0, result.stdout + result.stderr
    run.poll()
    assert run.handshaken


def test_capability_detects_missing_native_directive(tmp_path):
    _, run = make_run(tmp_path, second=True)
    run.bootstrap.write_text(run.bootstrap.read_text().replace("CAPTAINS 2\n", ""))
    result = run_probe(run)
    assert result.returncode == 0, result.stdout + result.stderr
    with pytest.raises(ValueError, match="capability.*mismatch"):
        run.poll()
