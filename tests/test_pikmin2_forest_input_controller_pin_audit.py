"""Fail-closed tests for the forest input-controller pin registry."""

import json
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experimental",
                    "pikmin2_forest_input_controller_pin_audit.py")


def run(*args):
    proc = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout


def test_pins_schema_and_finding():
    code, out = run("pins")
    assert code == 0
    reg = json.loads(out)
    assert reg["schema"] == "p2-forest-input-controller-pins-1"
    assert reg["finding"]["verdict"] == "NO_MISSING_ACCESSOR"
    assert "#660" in reg["consumer"]
    assert "a2085549" in reg["recovery"]


def test_chain_covers_poll_and_accessor():
    code, out = run("pins")
    reg = json.loads(out)
    symbols = {s["symbol"] for s in reg["chain"]}
    for want in ("ogScrResultMgr::update", "Controller::keyClick", "Controller::update",
                 "Controller::updateCont", "BaseGameSection::mController"):
        assert want in symbols, want


def test_check_known_symbol():
    code, out = run("check", "--symbol", "Controller::keyClick")
    assert code == 0
    result = json.loads(out)
    assert result["file"] == "include/Controller.h"
    assert result["line"] == 65


def test_check_unknown_symbol_refused():
    code, out = run("check", "--symbol", "Nope::doesNotExist")
    assert code == 1
    assert json.loads(out)["problems"]


def test_owner_and_slice_recorded():
    code, out = run("pins")
    reg = json.loads(out)
    assert "#794" in reg["finding"]["owner_line_for_accessor_change"]["owner_lane"]
    assert reg["finding"]["first_bounded_staging_slice"]["consumer"] == "#660"


def test_malformed_input_refused():
    proc = subprocess.run([sys.executable, TOOL, "check"], capture_output=True, text=True)
    assert proc.returncode == 2