"""Focused tests for the forest UI-stall pin audit (#751).

Unit checks run on synthetic logs (positive + malformed/missing inputs);
one integration check runs the adapter against the real staged-rerun
native.log and asserts the recorded verdict. No runtime, no build, no ADMIT.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experimental"))

from pikmin2_forest_ui_stall_pin_audit import AuditInputError, audit_native_log

REAL_LOG = Path(
    "C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
    "planning-shards/overworld-forest/prepared/"
    "forest-p1-staged-rerun-output/run-forest-p1/native.log"
)

SYNTHETIC_STALL = """\
[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)
[BBFT] Direct boot: Forest of Hope day 2, 20 reds
[PC Port] DVDOpen("dataDir/cinemas/demo40.cin") -> OK, size = 274
MoviePlayer: *--------------- 245052.50k free
[PC Port] DVDOpen("dataDir/cinemas/demo84.cin") -> OK, size = 523
MoviePlayer: clearing top heap!
[PC Port] DVDOpen("dataDir/screen/eng_blo/data1.blo") -> OK, size = 3104
System: Opened file dataDir/screen/eng_blo/data1.blo
[PC Port] DVDOpen("dataDir/screen/eng_blo/re_a_00.blo") -> OK, size = 480
[PC Port] FPS: 30.0, DeltaTime: 33.3333ms, clamp: 2, TEV programs: 59, matrices: 929/8192, shapes: 6/1000
[PC Port] Textures: 495 live, 61 MB (peak 61 MB), 568 made / 73 freed
[PC Port] FPS: 30.0, DeltaTime: 33.3333ms, clamp: 2, TEV programs: 59, matrices: 929/8192, shapes: 6/1000
"""


def test_positive_stall_signature(tmp_path):
    log = tmp_path / "synthetic.log"
    log.write_text(SYNTHETIC_STALL, encoding="utf-8")
    v = audit_native_log(log)
    assert v["last_cinema"] == {"demo": "demo84", "line": 5}
    assert v["terminal_ui_cluster"] == {"count": 3, "first_line": 7, "last_line": 9}
    assert v["boundary_markers"] == 0
    assert v["heartbeat_tail"]["heartbeat_only"] is True
    assert "RESULT_Active" in v["verdict"]["screen"]


def test_missing_log_raises():
    with pytest.raises(AuditInputError):
        audit_native_log("C:/nonexistent/definitely-not-here/native.log")


def test_empty_log_raises(tmp_path):
    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    with pytest.raises(AuditInputError):
        audit_native_log(log)


def test_no_cinema_raises(tmp_path):
    log = tmp_path / "nocine.log"
    log.write_text("[PC Port] FPS: 30.0\n[PC Port] Textures: 1 live\n", encoding="utf-8")
    with pytest.raises(AuditInputError):
        audit_native_log(log)


def test_malformed_binary_log_handled(tmp_path):
    log = tmp_path / "binary.log"
    log.write_bytes(
        b"\xff\xfe[PC Port] DVDOpen(\"dataDir/cinemas/demo40.cin\") -> OK\x00\n"
        b"[PC Port] FPS: 30.0\xff\xfe\n"
    )
    v = audit_native_log(log)
    assert v["cinema_chain"] == ["demo40"]


def test_real_staged_rerun_log_verdict():
    v = audit_native_log(REAL_LOG)
    assert v["log_lines"] == 1546
    assert v["last_cinema"] == {"demo": "demo84", "line": 826}
    assert v["terminal_ui_cluster"]["first_line"] == 837
    assert v["terminal_ui_cluster"]["last_line"] == 970
    assert v["heartbeat_tail"] == {
        "first_line": 971,
        "last_line": 1546,
        "heartbeat_only": True,
    }
    assert v["boundary_markers"] == 0
    assert v["cinema_chain"][:3] == ["demo40", "demo46", "demo47"]
    assert "demo36" in v["cinema_chain"] and "demo32" in v["cinema_chain"]
