"""Focused tests for the Jigumo63 throughput run (#167).

Covers the observer verdicts on synthetic logs plus a strict MinGW
compile-and-smoke of the fixture TU shape (guard + marker contract only;
no engine boot here).
"""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

observer = importlib.import_module("experimental.pikmin2_jigumo63_throughput_run")


def good_log(*replacements):
    lines = [
        "P2_JIGUMO573_BASELINE red=20 blue=0 live=20",
        "P2_JIGUMO573_WINDOW width=960 height=540 centered_call=1",
        "P2_JIGUMO573_STAGE generator=374003 source_id=63 chain=family near=6 far=14 staged=1",
        "P2_JIGUMO_BIND generator=374003 source_id=63 visual_only=0",
        "P2_JIGUMO573_CENSUS actors=9",
        "P2_JIGUMO573_SCENARIO latch_first generator=374003",
        "P2_JIGUMO573_SQUAD red=20 blue=0 live=20",
        "P2_JIGUMO_BITE generator=374003 frame=26 pikmin=1",
        "P2_JIGUMO_EAT generator=374003 pikmin=1",
        "P2_JIGUMO_FLICK generator=374003 frame=100",
        "P2_JIGUMO573_RELATCH count=4 staged=1",
        "P2_JIGUMO573_HP health=320.5 live=19",
        "P2_JIGUMO_DEAD generator=374003 source_id=63 health=0",
        "P2_JIGUMO573_RESULT dead=1 carcass=1 lost=5 ratio=100.00 hp_drained=500.0",
    ]
    text = "\n".join(lines) + "\n"
    assert len(replacements) % 2 == 0
    for i in range(0, len(replacements), 2):
        text = text.replace(replacements[i], replacements[i + 1])
    return text


class TestObserver(unittest.TestCase):
    def test_good_log_passes(self):
        verdict = observer.validate(good_log())
        self.assertTrue(verdict["passed"], verdict["failures"])
        self.assertTrue(verdict["dead"])
        self.assertTrue(verdict["carcass"])
        self.assertEqual(verdict["lost"], 5)
        self.assertEqual(verdict["ratio"], 100.0)
        self.assertTrue(verdict["ratio_above_25"])
        self.assertEqual(verdict["bites"], 1)
        self.assertEqual(verdict["eats"], 1)
        self.assertEqual(verdict["flicks"], 1)
        self.assertFalse(verdict["captain_down"])
        self.assertEqual(verdict["injected"], [])

    def test_ratio_at_25_fails(self):
        verdict = observer.validate(good_log("ratio=100.00", "ratio=25.00"))
        self.assertFalse(verdict["passed"])
        self.assertIn("ratio-at-or-below-25", verdict["failures"])

    def test_ratio_below_fails(self):
        verdict = observer.validate(good_log("lost=5 ratio=100.00", "lost=20 ratio=17.10"))
        self.assertFalse(verdict["passed"])

    def test_missing_dead_fails(self):
        text = good_log().replace("P2_JIGUMO_DEAD generator=374003 source_id=63 health=0\n", "")
        text = text.replace("P2_JIGUMO573_RESULT dead=1", "P2_JIGUMO573_RESULT dead=0")
        verdict = observer.validate(text)
        self.assertFalse(verdict["passed"])

    def test_no_carcass_fails(self):
        verdict = observer.validate(good_log("carcass=1", "carcass=0"))
        self.assertFalse(verdict["passed"])
        self.assertIn("no-carcass", verdict["failures"])

    def test_captain_down_blocks(self):
        text = good_log() + "P2_FIXTURE_CAPTAIN_DOWN tick=9 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED\n"
        verdict = observer.validate(text)
        self.assertTrue(verdict["captain_down"])
        self.assertFalse(verdict["passed"])

    def test_injected_marker_fails(self):
        text = good_log() + "P2_BOMBOTAKARA_INJECT_1 75 30 contact\n"
        verdict = observer.validate(text)
        self.assertTrue(verdict["injected"])
        self.assertFalse(verdict["passed"])

    def test_blocked_without_result(self):
        text = "\n".join([
            "P2_JIGUMO573_BASELINE red=20 blue=0 live=20",
            "P2_JIGUMO573_STAGE generator=374003 source_id=63 chain=family near=6 far=14 staged=1",
            "P2_JIGUMO_BIND generator=374003 source_id=63 visual_only=0",
            "P2_JIGUMO573_BLOCKED reason=no-kill generator=374003 health=380.0 live=13",
        ]) + "\n"
        verdict = observer.validate(text)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["blocked_reason"], "no-kill")

    def test_no_bind_fails(self):
        text = good_log().replace("P2_JIGUMO_BIND generator=374003 source_id=63 visual_only=0\n", "")
        verdict = observer.validate(text)
        self.assertFalse(verdict["passed"])
        self.assertIn("no-bind", verdict["failures"])

    def test_cli_pass_and_fail(self):
        import subprocess
        fd, path = tempfile.mkstemp(suffix=".log")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(good_log())
            proc = subprocess.run(
                [sys.executable, "-m", "experimental.pikmin2_jigumo63_throughput_run",
                 "--log", path],
                capture_output=True, text=True, timeout=60, cwd=str(ROOT))
            self.assertEqual(proc.returncode, 0, proc.stdout[-1000:])
            self.assertIn("VERDICT EVIDENCE", proc.stdout)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
