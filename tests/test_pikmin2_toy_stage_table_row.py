"""Focused fail-closed tests for the 03toy stage-table row contract (#752).

Hermetic: pins the row facts, validates the marker-log contract, and checks
the serialized-integration follow-on spec. No engine, no build, no runtime.

The native row/fixture sources are resolved without a lane-local path: from
P2_NATIVE_REPO (git show), the legacy sibling layout, or skipped cleanly.
"""

import importlib.util
import os
import subprocess
import unittest
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_toy_stage_table_row.py"
spec = importlib.util.spec_from_file_location("p2_toy_row", MOD)
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
              / "toy-stage-table-row-native-native" / relpath)
    if legacy.is_file():
        return legacy.read_text(encoding="utf-8", errors="replace")
    raise unittest.SkipTest("native file not resolvable here: " + relpath)


def sample_log():
    return ("P2_TOY_STAGE_TABLE stage=ch_NARI_03toy ui_index=5 floors=2\n"
            "P2_TOY_STAGE_RESOLVED stage=ch_NARI_03toy ui_index=5 floors=2 roster_total=100\n"
            "P2_TOY_STAGE_TABLE_GATES all=UNTESTED content_wired=0\n"
            "PASS P2_TOY_STAGE_TABLE_RUN markers=3\n")


class ToyRowContractTests(unittest.TestCase):
    def test_row_valid(self):
        self.assertTrue(adapter.row_valid())
        self.assertEqual(adapter.roster_total(), 100)

    def test_row_rejects_drift(self):
        bad = dict(adapter.ROW, ui_index=6)
        self.assertFalse(adapter.row_valid(bad))
        bad2 = dict(adapter.ROW, source_sha256="0" * 64)
        self.assertFalse(adapter.row_valid(bad2))
        self.assertFalse(adapter.row_valid("not-a-dict"))

    def test_marker_log_ok(self):
        ok, detail = adapter.check_marker_log(sample_log())
        self.assertTrue(ok, detail)

    def test_marker_log_missing(self):
        text = sample_log().replace(
            "P2_TOY_STAGE_RESOLVED stage=ch_NARI_03toy ui_index=5 floors=2 roster_total=100\n", "")
        ok, detail = adapter.check_marker_log(text)
        self.assertFalse(ok)

    def test_marker_log_captain_down_rejected(self):
        ok, _ = adapter.check_marker_log(sample_log() + "P2_FIXTURE_CAPTAIN_DOWN tick=0\n")
        self.assertFalse(ok)

    def test_marker_log_no_pass_rejected(self):
        ok, _ = adapter.check_marker_log("P2_TOY_STAGE_TABLE stage=ch_NARI_03toy ui_index=5 floors=2\n")
        self.assertFalse(ok)

    def test_native_row_carries_pins(self):
        text = native_text("pc_port/pc_p2_challenge_toy_stage.cpp")
        for pin in (adapter.ROW["cave_id"], adapter.ROW["cave_path"],
                    adapter.ROW["source_sha256"]):
            self.assertIn(pin, text)

    def test_native_fixture_guarded_no_local_engine(self):
        text = native_text("tools/p2_toy_stage_table_fixture.cpp")
        self.assertIn("p2_fixture_captain_down", text)
        self.assertNotIn("pc_bbft_init", text)

    def test_followon_names_owner_files(self):
        f = adapter.integration_followon()
        self.assertIn("pc_bbft.cpp", " ".join(f["edits"]))
        self.assertIn("CMakeLists", " ".join(f["edits"]))
        self.assertEqual(f["row"]["ui_index"], 5)


if __name__ == "__main__":
    unittest.main()
