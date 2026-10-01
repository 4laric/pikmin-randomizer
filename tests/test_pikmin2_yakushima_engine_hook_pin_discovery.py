"""Fail-closed tests for the yakushima engine-hook pin-discovery registry."""

import json
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experimental",
                    "pikmin2_yakushima_engine_hook_pin_discovery.py")


def run(*args):
    proc = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout


def test_pins_schema_and_four_boundaries():
    code, out = run("pins")
    assert code == 0
    reg = json.loads(out)
    assert reg["schema"] == "p2-yakushima-engine-hook-pins-1"
    assert set(reg["boundaries"]) == {"boot_yakushima_surface", "day_transition",
                                      "receipt_replay", "exit_reentry"}
    for name, entry in reg["boundaries"].items():
        assert entry["verdict"] == "ABSENT", name
        assert entry["owner"] and entry["nearest_foothold"]


def test_pins_records_downstream_and_destination():
    code, out = run("pins")
    reg = json.loads(out)
    assert "bd5aaf22" in str(reg["downstream"])
    assert reg["destination_pins"]["root"] == "f2803e423b9f30ee6fcaf79004be02b2770a5a98"
    assert "#186" in reg["decision_request"]


def test_check_each_boundary_absent():
    for name in ("boot_yakushima_surface", "day_transition", "receipt_replay",
                 "exit_reentry"):
        code, out = run("check", "--boundary", name)
        assert code == 0, (name, out)
        result = json.loads(out)
        assert result["verdict"] == "ABSENT"
        assert result["problems"] == []


def test_check_unknown_boundary_refused():
    code, out = run("check", "--boundary", "save_reload")
    assert code == 1
    assert json.loads(out)["verdict"] == "REFUSED"


def test_malformed_input_refused():
    proc = subprocess.run([sys.executable, TOOL, "check"], capture_output=True, text=True)
    assert proc.returncode == 2