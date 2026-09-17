"""Focused fail-closed tests for the ch_NARI_02tile stage-boot record contract (#711).

Hermetic: parses the exact pinned #537/#669 records, checks the pinned
allowlist, and verifies the engine table-row follow-on spec. No engine, no
build, no runtime.
"""

import hashlib
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_challenge_stage_boot_02tile_record.py"
spec = importlib.util.spec_from_file_location("p2_boot_02tile", MOD)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

def fixture_text():
    """Read the native stage-boot fixture without a lane-local path.

    Resolution order: explicit P2_CHALLENGE_STAGE_BOOT_FIXTURE file, the
    native repo at P2_NATIVE_REPO via `git show`, then the legacy private-lane
    sibling layout. Raises SkipTest cleanly when it cannot be found so the
    suite stays green on trees (like the integration line) that do not carry
    this lane's directory layout.
    """
    override = os.environ.get("P2_CHALLENGE_STAGE_BOOT_FIXTURE")
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8", errors="replace")
        raise unittest.SkipTest("P2_CHALLENGE_STAGE_BOOT_FIXTURE points nowhere: " + override)
    repo = os.environ.get("P2_NATIVE_REPO")
    if repo:
        proc = subprocess.run(["git", "-C", repo, "show",
                               "HEAD:tools/p2_challenge_stage_boot_fixture.cpp"],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    legacy = (Path(__file__).resolve().parents[2]
              / "challenge-stage-boot-02tile-record-native-native/tools/p2_challenge_stage_boot_fixture.cpp")
    if legacy.is_file():
        return legacy.read_text(encoding="utf-8", errors="replace")
    raise unittest.SkipTest(
        "native stage-boot fixture not resolvable here; set "
        "P2_CHALLENGE_STAGE_BOOT_FIXTURE or P2_NATIVE_REPO")

REC_02TILE = """P2_CHALLENGE_STAGE_SELECT_1
cave ch_NARI_02tile ui_index 4 table_order 19 floors 2
source user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6
timers 200.0 150.0 legacy 0.0
sprays bitter 0 spicy 5 treasure_field 0
roster 0 0 50
roster 0 0 0
roster 0 0 0
roster 0 0 0
roster 0 0 0
roster 0 0 0
roster 0 0 0
"""

REC_KUSACHI = """P2_CHALLENGE_STAGE_SELECT_1
cave ch_NARI_01kusachi ui_index 3 table_order 3 floors 1
source user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85
timers 180.0 legacy 0.0
sprays bitter 1 spicy 2 treasure_field 0
roster 0 0 50
roster 0 0 0
roster 0 0 0
roster 0 0 0
roster 0 0 0
roster 0 0 0
roster 0 0 0
"""


class RecordContractTests(unittest.TestCase):
    def test_parse_02tile_ok(self):
        rec = adapter.parse_record(REC_02TILE)
        self.assertEqual(rec["cave_id"], "ch_NARI_02tile")
        self.assertEqual(rec["ui_index"], 4)
        self.assertEqual(rec["table_order"], 19)
        self.assertEqual(rec["floors"], 2)
        self.assertEqual(rec["floor_seconds"], [200.0, 150.0])
        self.assertEqual(rec["spicy_sprays"], 5)
        self.assertEqual(rec["roster"][0], [0, 0, 50])

    def test_parse_kusachi_ok(self):
        rec = adapter.parse_record(REC_KUSACHI)
        self.assertEqual(rec["cave_id"], "ch_NARI_01kusachi")
        self.assertEqual(rec["ui_index"], 3)

    def test_bad_magic(self):
        with self.assertRaises(ValueError):
            adapter.parse_record(REC_02TILE.replace("SELECT_1", "SELECT_9"))

    def test_unpinned_source_refused(self):
        text = REC_02TILE.replace("ch_NARI_02tile.txt d047060c",
                                  "ch_NARI_99bogus.txt d047060c")
        with self.assertRaises(ValueError):
            adapter.parse_record(text)
        text2 = REC_02TILE.replace("d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6", "0" * 64)
        with self.assertRaises(ValueError):
            adapter.parse_record(text2)

    def test_pin_mismatch_refused(self):
        text = REC_02TILE.replace("ui_index 4", "ui_index 7")
        with self.assertRaises(ValueError):
            adapter.parse_record(text)

    def test_trailing_data_refused(self):
        with self.assertRaises(ValueError):
            adapter.parse_record(REC_02TILE + "EXTRA\n")

    def test_empty_refused(self):
        with self.assertRaises(ValueError):
            adapter.parse_record("")

    def test_pinned_source_fail_closed(self):
        r = adapter.PINNED_RECORDS["ch_NARI_02tile"]
        self.assertTrue(adapter.pinned_source(r["cave_id"], r["source_path"], r["source_sha256"]))
        self.assertFalse(adapter.pinned_source(r["cave_id"], r["source_path"], "0" * 64))
        self.assertFalse(adapter.pinned_source("nope", r["source_path"], r["source_sha256"]))

    def test_engine_row_followon_exact(self):
        f = adapter.engine_table_row_followon()
        self.assertEqual(f["file"], "native/pc_port/pc_bbft.cpp")
        self.assertEqual(f["table"], "kP2ChallengeStages")
        row = f["row"]
        self.assertEqual(row["caveId"], "ch_NARI_02tile")
        self.assertEqual(row["sourceSha256"], adapter.PINNED_RECORDS["ch_NARI_02tile"]["source_sha256"])
        self.assertEqual(row["floorSeconds"], [200.0, 150.0])
        self.assertEqual(row["spicySprays"], 5)
        self.assertEqual(adapter.PINNED_RECORDS["ch_NARI_02tile"]["engine_row"], "pending-710")

    def test_fixture_allowlist_both_pinned(self):
        text = fixture_text()
        self.assertTrue(adapter.fixture_allowlist_ok(text))
        self.assertIn(adapter.PINNED_RECORDS["ch_NARI_02tile"]["source_sha256"], text)

    def test_fixture_allowlist_rejects_kusachi_only(self):
        self.assertFalse(adapter.fixture_allowlist_ok(
            'if (out.sourcePath != "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt") return false;'))


if __name__ == "__main__":
    unittest.main()
