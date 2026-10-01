"""Focused tests for the kusachi boot-stall diagnosis analyzer (#822).

No runtime: synthetic boot logs exercise the stall-window location (healthy
JAUDIO sequence, stalled shape), asset inventory, and fail-closed malformed
and missing-input refusal. The real run5 log is asserted to yield the
documented NEEDS-RUNTIME-PROBE verdict, never a guessed pin.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experimental.pikmin2_kusachi_boot_stall_diagnosis import (
    NEEDS_PROBE,
    PINNED,
    Refused,
    analyze,
    check_assets,
    locate_window,
    read_log_text,
)

REAL_LOG = ("C:/Users/alari/pikmin-randomizer/output/"
            "kusachi-gate-observation-run5/native.log")
REAL_RUN = ("C:/Users/alari/pikmin-randomizer/output/"
            "kusachi-gate-observation-run5")

STALLED = """P2_CHALLENGE_STAGE_FLAG cave=ch_NARI_01kusachi
P2_KUSACHI_CONTENT_WIRING_STAGE cave=ch_NARI_01kusachi ui_index=3 floors=1
[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)
[PC Port] OSInit() - System initialized
[PC Port] CARDInit() - persistent filesystem card: somewhere/card0
[PC Port] DVDInit() - DVD subsystem initialized
[PC Port] OpenGL context: 3.3.0
[jaudio] NextOS DSP, SDL2 S16 stereo 32000 Hz
"""

HEALTHY = STALLED + """[PC Port] JAudio wave catalog loaded: 22 WSYS, 882 waves
[PC Port] JAudio instrument catalog loaded: 19/22 IBNK
[PC Port] JAudio sequence catalog loaded: 22 sequences
[PC Port] DVDOpen("/dataDir/SndData/Seqs/pikiseq.arc") -> OK, size = 219392
[PC Port] PADInit() - SDL2 window & input initialized
[PC Port] DVDOpen("dataDir/consFont.bti") -> OK, size = 32800
P2_CHALLENGE_CONTENT_WIRED wired=8 total=8 target_color=0 cave=ch_NARI_01kusachi
"""


def write_tmp(tmp, name, content, binary=False):
    path = os.path.join(tmp, name)
    with open(path, "wb" if binary else "w", encoding=None if binary else "utf-8") as fh:
        fh.write(content)
    return path


class WindowTests(unittest.TestCase):
    def test_stalled_shape(self):
        w = locate_window(STALLED)
        self.assertEqual(w["last_observed"], "[jaudio] NextOS DSP")
        self.assertEqual(w["first_absent"], "JAudio wave catalog loaded")
        self.assertFalse(w["complete"])

    def test_healthy_shape(self):
        w = locate_window(HEALTHY)
        self.assertTrue(w["complete"])
        self.assertIsNone(w["first_absent"])

    def test_non_wiring_log_refused(self):
        with self.assertRaises(Refused):
            locate_window("hello world\nnothing here\n")


class AssetTests(unittest.TestCase):
    def test_missing_run_dir_refused(self):
        with self.assertRaises(Refused):
            check_assets(os.path.join("no-such-dir-xyz", "sub"))

    def test_asset_inventory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dd = os.path.join(tmp, "assets", "dataDir")
            os.makedirs(dd)
            open(os.path.join(dd, "consFont.bti"), "w").write("x" * 64)
            open(os.path.join(dd, "bigFont.bti"), "w").write("y" * 64)
            inv = check_assets(tmp)
            self.assertTrue(inv["consFont.bti"])
            self.assertTrue(inv["bigFont.bti"])
            self.assertFalse(inv["SndData_tree"])
            self.assertFalse(inv["stages/chal0/default.gen"])


class AnalyzeTests(unittest.TestCase):
    def test_synthetic_stalled_needs_probe(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "assets", "dataDir"))
            log = write_tmp(tmp, "native.log", STALLED)
            result = analyze(log, tmp)
            self.assertEqual(result["verdict"], NEEDS_PROBE)
            self.assertIn("SndData", result["detail"])

    def test_synthetic_healthy_pinned(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "assets", "dataDir"))
            log = write_tmp(tmp, "native.log", HEALTHY)
            result = analyze(log, tmp)
            self.assertEqual(result["verdict"], PINNED)

    def test_empty_log_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            log = write_tmp(tmp, "native.log", "   \n")
            with self.assertRaises(Refused):
                analyze(log, tmp)

    def test_missing_log_refused(self):
        with self.assertRaises(Refused):
            analyze(os.path.join("no-such-dir-xyz", "native.log"))


@unittest.skipUnless(os.path.exists(REAL_LOG), "landed run5 log unavailable")
class RealLogTests(unittest.TestCase):
    def test_real_log_needs_probe(self):
        result = analyze(REAL_LOG, REAL_RUN)
        self.assertEqual(result["verdict"], NEEDS_PROBE)
        self.assertEqual(result["window"]["last_observed"],
                         "[jaudio] NextOS DSP")
        self.assertFalse(result["assets"]["SndData_tree"])

    def test_real_log_deterministic_shape(self):
        text = read_log_text(REAL_LOG)
        self.assertEqual(len(text.splitlines()), 24)


if __name__ == "__main__":
    unittest.main()
