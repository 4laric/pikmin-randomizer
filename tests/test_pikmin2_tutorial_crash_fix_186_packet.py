"""Focused tests for the tutorial crash-fix #186 packet (#785)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_tutorial_crash_fix_186_packet as pkt  # noqa: E402


def test_packet_pins_and_scope():
    p = pkt.build_packet(pkt.PRODUCER_ROOT, pkt.PRODUCER_NATIVE)
    assert p["schema"] == pkt.SCHEMA
    assert p["producer"]["lane"] == "tutorial-p1-font-settexture-crash-fix"
    assert p["guard"]["callsite"]["symbol"] == "Font::setTexture"
    assert "UNTESTED" in p["gates"]


def test_wrong_pins_refused(tmp_path):
    with pytest.raises(pkt.PacketRejected):
        pkt.build_packet("0" * 40, pkt.PRODUCER_NATIVE, tmp_path)
    with pytest.raises(pkt.PacketRejected):
        pkt.build_packet(pkt.PRODUCER_ROOT, "0" * 40, tmp_path)


def test_malformed_pin_refused():
    with pytest.raises(pkt.PacketRejected):
        pkt.build_packet("short", pkt.PRODUCER_NATIVE)


def test_no_overwrite(tmp_path):
    pkt.build_packet(pkt.PRODUCER_ROOT, pkt.PRODUCER_NATIVE, tmp_path)
    with pytest.raises(pkt.PacketRejected):
        pkt.build_packet(pkt.PRODUCER_ROOT, pkt.PRODUCER_NATIVE, tmp_path)


def test_emit_packet(tmp_path):
    r = pkt.build_packet(pkt.PRODUCER_ROOT, pkt.PRODUCER_NATIVE, tmp_path)
    assert Path(r["packet_path"]).is_file()
    assert len(r["packet_sha256"]) == 64
    assert json.loads(Path(r["packet_path"]).read_text())["schema"] == pkt.SCHEMA


def test_consumer_names_downstream():
    p = pkt.build_packet(pkt.PRODUCER_ROOT, pkt.PRODUCER_NATIVE)
    assert p["consumer"]["downstream_issues"] == [148]
    assert "0xC0000005" in p["consumer"]["expected"]


def test_module_is_stdlib_only():
    src = (ROOT / "experimental" / "pikmin2_tutorial_crash_fix_186_packet.py").read_text()
    assert "import numpy" not in src and "import requests" not in src