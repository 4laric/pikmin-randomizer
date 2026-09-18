"""Fail-closed tests for the save durable-payload pin-discovery registry."""

import json
import os
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experimental",
                    "pikmin2_save_durable_payload_pin_discovery.py")


def run(*args):
    proc = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout


def test_pins_schema_and_verdict():
    code, out = run("pins")
    assert code == 0
    reg = json.loads(out)
    assert reg["schema"] == "p2-save-durable-payload-pins-1"
    assert reg["verdict"] == "ABSENT"
    assert reg["stage"]["cave_id"] == "ch_NARI_01kusachi"
    assert "kusachi-persistence-obs (#781)" in reg["owner_contract"]["consumers"]


def test_pins_names_owner_contract():
    code, out = run("pins")
    reg = json.loads(out)
    contract = reg["owner_contract"]
    assert "#186" in contract["shared_review"]
    assert "p2_challenge_save_<caveId>" in contract["producer"]


def test_verify_run_empty_card_is_absent():
    with tempfile.TemporaryDirectory() as tmp:
        card = os.path.join(tmp, "save", "bbft_sessions", "123", "card0")
        os.makedirs(card)
        with open(os.path.join(tmp, "native.log"), "w") as f:
            f.write("P2_CHALLENGE_SAVE_KEY stage=ch_NARI_01kusachi\n")
        code, out = run("verify-run", "--dir", tmp)
        assert code == 0, out
        result = json.loads(out)
        assert result["verdict"] == "ABSENT"
        assert result["payloads"] == []


def test_verify_run_payload_is_unexpected():
    with tempfile.TemporaryDirectory() as tmp:
        card = os.path.join(tmp, "save", "bbft_sessions", "123", "card0")
        os.makedirs(card)
        with open(os.path.join(card, "payload.bin"), "wb") as f:
            f.write(b"\x00" * 16)
        code, out = run("verify-run", "--dir", tmp)
        assert code == 1, out
        result = json.loads(out)
        assert result["verdict"] == "UNEXPECTED"
        assert any("payload.bin" in p for p in result["payloads"])


def test_verify_run_missing_dir_refused():
    code, out = run("verify-run", "--dir", os.path.join(tempfile.gettempdir(), "no-such-dir-xyz"))
    assert code == 1
    assert json.loads(out)["verdict"] == "REFUSED"


def test_malformed_input_refused():
    proc = subprocess.run([sys.executable, TOOL, "verify-run"],
                          capture_output=True, text=True)
    assert proc.returncode == 2