"""Focused fail-closed tests for the forest PAD sink contract (#794).

Hermetic: validates the marker-log contract, the sink decl/def presence
rules, and the production-clean rule. No engine, no build, no runtime.

Native sources resolve without a lane-local path: from P2_NATIVE_REPO (git
show), the legacy sibling layout, or skipped cleanly.
"""

import importlib.util
import os
import subprocess
import unittest
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_forest_pad_sink.py"
spec = importlib.util.spec_from_file_location("p2_forest_pad_sink", MOD)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def native_text(relpath):
    repo = os.environ.get("P2_NATIVE_REPO")
    if repo:
        proc = subprocess.run(["git", "-C", repo, "show", "HEAD:" + relpath],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    legacy = (Path(__file__).resolve().parents[2]
              / "forest-controller-pad-sink-native-native" / relpath)
    if legacy.is_file():
        return legacy.read_text(encoding="utf-8", errors="replace")
    raise unittest.SkipTest("native file not resolvable here: " + relpath)


def sample_log():
    return ("P2_FOREST_PAD_SINK_BASELINE_CLEAR\n"
            "P2_FOREST_PAD_SINK_OBSERVED button=A\n"
            "P2_FOREST_PAD_SINK_OBSERVED button=START\n"
            "P2_FOREST_PAD_SINK_GATES all=UNTESTED content_wired=0\n"
            "PASS P2_FOREST_PAD_SINK_RUN markers=3\n")


class PadSinkContractTests(unittest.TestCase):
    def test_marker_log_ok(self):
        ok, detail = adapter.check_run_log(sample_log())
        self.assertTrue(ok, detail)

    def test_marker_log_missing(self):
        text = sample_log().replace("P2_FOREST_PAD_SINK_OBSERVED button=START\n", "")
        ok, detail = adapter.check_run_log(text)
        self.assertFalse(ok)

    def test_marker_log_captain_down_rejected(self):
        ok, _ = adapter.check_run_log(sample_log() + "P2_FIXTURE_CAPTAIN_DOWN tick=0\n")
        self.assertFalse(ok)

    def test_marker_log_no_pass_rejected(self):
        ok, _ = adapter.check_run_log("P2_FOREST_PAD_SINK_BASELINE_CLEAR\n")
        self.assertFalse(ok)

    def test_marker_log_fail_rejected(self):
        ok, _ = adapter.check_run_log(sample_log() + "FAIL P2_FOREST_PAD_SINK injected-A-unobserved\n")
        self.assertFalse(ok)

    def test_sink_declared(self):
        header = native_text("include/Controller.h")
        impl = native_text("src/sysDolphin/controllerMgr.cpp")
        self.assertTrue(adapter.sink_declared(header, impl))

    def test_sink_missing_rejected(self):
        self.assertFalse(adapter.sink_declared("no decl here", "no def here"))

    def test_production_clean(self):
        tree = {"src/sysDolphin/controllerMgr.cpp": "x testSinkPadButtons y",
                "include/Controller.h": "x testSinkPadButtons y",
                "tools/p2_forest_pad_sink_fixture.cpp": "x testSinkPadButtons y"}
        self.assertTrue(adapter.production_clean(tree))
        dirty = dict(tree)
        dirty["pc_port/pc_main.cpp"] = "x testSinkPadButtons y"
        self.assertFalse(adapter.production_clean(dirty))

    def test_button_constants(self):
        self.assertEqual(adapter.BUTTON_A, 0x0100)
        self.assertEqual(adapter.BUTTON_START, 0x1000)

    def test_consumer_is_660(self):
        self.assertEqual(adapter.CONSUMER["issue"], 660)


if __name__ == "__main__":
    unittest.main()
