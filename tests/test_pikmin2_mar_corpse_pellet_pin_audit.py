"""Fail-closed tests for the Mar corpse-pellet pin audit (#799)."""
import os
import subprocess
import sys
import tempfile

import pytest

ADAPTER = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "experimental",
    "pikmin2_mar_corpse_pellet_pin_audit.py"))
PY = sys.executable


def run_audit(*args):
    return subprocess.run([PY, ADAPTER] + list(args), capture_output=True,
                          text=True, timeout=120)


def make_arena(entries):
    tmp = tempfile.mkdtemp(prefix="mar-pellet-")
    d = os.path.join(tmp, "assets", "dataDir", "archives")
    os.makedirs(d)
    blob = b"\x00\x00\x00\xa8" + b"".join(
        b"\x00\x00\x00\x84" + e.encode("ascii") for e in entries)
    with open(os.path.join(d, "pelletsbin.dir"), "wb") as fh:
        fh.write(blob)
    return tmp


def test_absence_verified_on_white_only():
    root = make_arena(["objects/pellets/white1.bin", "objects/pellets/white2.bin"])
    proc = run_audit(root)
    assert proc.returncode == 0, proc.stderr
    assert "P2_MAR_PELLET_ABSENT enemy-corpse" in proc.stdout
    assert "P2_MAR_PELLET_VERDICT absence-verified" in proc.stdout
    assert "P2_MAR_PELLET_ENTRY objects/pellets/white1.bin" in proc.stdout


def test_entries_present_when_enemy_entry_exists():
    root = make_arena(["objects/pellets/white1.bin", "objects/pellets/mar.bin"])
    proc = run_audit(root)
    assert proc.returncode == 0, proc.stderr
    assert "P2_MAR_PELLET_VERDICT entries-present" in proc.stdout
    assert "P2_MAR_PELLET_ABSENT" not in proc.stdout


def test_runlog_markers_reported():
    root = make_arena(["objects/pellets/white1.bin"])
    fd, log = tempfile.mkstemp(prefix="mar-run-", suffix=".log")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("P2_MAR_DEAD generator=375001 source_id=29 health=0\n")
        fh.write("P2_MAR_CORPSE_OBSERVED_DEAD\n")
        fh.write("P2_MAR_CORPSE_WAIT tick=3600 corpse=0\n")
    proc = run_audit(root, log)
    assert proc.returncode == 0, proc.stderr
    assert "P2_MAR_RUNLOG BIND" in proc.stdout
    assert "P2_MAR_RUNLOG DEAD" in proc.stdout
    assert "P2_MAR_RUNLOG CORPSE" not in proc.stdout


def test_missing_arena_dir_refused():
    proc = run_audit(os.path.join(tempfile.gettempdir(), "no-such-mar-arena-xyz"))
    assert proc.returncode == 2
    assert "P2_MAR_PELLET_REFUSED reason=missing-arena-dir" in proc.stdout


def test_missing_pelletsbin_refused():
    tmp = tempfile.mkdtemp(prefix="mar-empty-")
    proc = run_audit(tmp)
    assert proc.returncode == 2
    assert "P2_MAR_PELLET_REFUSED reason=missing-pelletsbin-dir" in proc.stdout


def test_malformed_pelletsbin_refused():
    tmp = tempfile.mkdtemp(prefix="mar-tiny-")
    d = os.path.join(tmp, "assets", "dataDir", "archives")
    os.makedirs(d)
    with open(os.path.join(d, "pelletsbin.dir"), "wb") as fh:
        fh.write(b"\x00\x01")
    proc = run_audit(tmp)
    assert proc.returncode == 2
    assert "P2_MAR_PELLET_REFUSED reason=malformed-pelletsbin-dir" in proc.stdout


def test_usage_refused():
    proc = subprocess.run([PY, ADAPTER], capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode == 2
    assert "P2_MAR_PELLET_REFUSED reason=usage" in proc.stdout
