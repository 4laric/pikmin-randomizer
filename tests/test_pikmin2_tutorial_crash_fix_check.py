"""Focused fail-closed tests for the Font::setTexture guard probe checker (#750)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "crash_fix_check",
    ROOT / "experimental" / "pikmin2_tutorial_crash_fix_check.py")
check = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(check)

PASS_LOG = """P2_FONT_PROBE_WINDOW size=960x540 pos=1,2 display=3x4 centered=1
P2_FONT_PROBE_SPLASH_PASS observed=3 squad_alive=0
P2_FONT_PROBE_SQUAD pikis=5
PASS P2_FONT_PROBE_GUARDED_BOOT observed=180 squad_alive=5
"""

CRASH_LOG = """P2_FONT_PROBE_WINDOW size=960x540 pos=1,2 display=3x4 centered=1
"""

GUARDED_LOG = """P2_FONT_SETTEXTURE_GUARDED rows=21 cols=36
P2_FONT_PROBE_WINDOW size=960x540 pos=1,2 display=3x4 centered=1
P2_FONT_PROBE_SPLASH_PASS observed=9 squad_alive=0
"""

DOWN_LOG = """P2_FIXTURE_CAPTAIN_DOWN tick=4 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED
"""


class VerdictTests(unittest.TestCase):
    def test_full_pass(self):
        verdict = check.check_log(PASS_LOG, 0)
        self.assertEqual(verdict["outcome"], "PASS")
        self.assertTrue(verdict["passed"])
        self.assertTrue(verdict["window_ok"])
        self.assertTrue(verdict["splash_passed"])
        self.assertEqual(verdict["squad"], 5)
        self.assertFalse(verdict["crashed"])

    def test_crash_exit_fails(self):
        for code in (3221225477, -1073741515):
            verdict = check.check_log(CRASH_LOG, code)
            self.assertEqual(verdict["outcome"], "FAIL")
            self.assertTrue(verdict["crashed"])
            self.assertFalse(verdict["passed"])

    def test_missing_pass_markers_fails(self):
        verdict = check.check_log(CRASH_LOG, 0)
        self.assertEqual(verdict["outcome"], "FAIL")
        self.assertFalse(verdict["passed"])

    def test_guarded_marker_recorded_not_pass(self):
        verdict = check.check_log(GUARDED_LOG, 0)
        self.assertTrue(verdict["guard_tripped"])
        self.assertEqual(verdict["outcome"], "FAIL")

    def test_captain_down_blocks(self):
        verdict = check.check_log(DOWN_LOG + PASS_LOG, 86)
        self.assertTrue(verdict["captain_down"])
        self.assertEqual(verdict["outcome"], "BLOCKED")
        self.assertFalse(verdict["passed"])

    def test_malformed_input_fails_closed(self):
        verdict = check.check_log("", 0)
        self.assertEqual(verdict["outcome"], "FAIL")
        verdict = check.check_log("garbage\n" * 50, 3)
        self.assertEqual(verdict["outcome"], "FAIL")

    def test_wrong_window_fails(self):
        log = PASS_LOG.replace("centered=1", "centered=0")
        verdict = check.check_log(log, 0)
        self.assertFalse(verdict["window_ok"])
        self.assertEqual(verdict["outcome"], "FAIL")


class CliTests(unittest.TestCase):
    def test_bad_exit_code_refused(self):
        self.assertEqual(check.main(["--log", "x", "--exit-code", "abc"]), 2)

    def test_missing_log_raises(self):
        with self.assertRaises(FileNotFoundError):
            check.main(["--log", "C:\\no\\such.log", "--exit-code", "0"])

    def test_schema_constant(self):
        self.assertEqual(check.SCHEMA, "p2-tutorial-crash-fix-check-1")


if __name__ == "__main__":
    unittest.main()