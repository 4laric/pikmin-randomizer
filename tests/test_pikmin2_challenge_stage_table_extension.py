"""Focused tests for the challenge stage extension table (#730).

Covers pin identity (against docs/PIKMIN_CONTENT_IMPORT_LANES.json), the log
validator's good/bad paths, and the C++ policy compile. No runtime launched.
"""

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

observer = importlib.import_module("experimental.pikmin2_challenge_stage_table_extension")

LANES_JSON = ROOT / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json"
NATIVE = Path(r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\prerequisites\challenge-stage-table-extension-native-native")
MINGW_GXX = Path(r"C:\msys64\mingw64\bin\g++.exe")


def good_log(cave, **overrides):
    pin = dict(observer.ROWS[cave])
    pin.update(overrides)
    roster_total = sum(sum(row) for row in pin["roster"])
    lines = [
        "P2_CHALLENGE_STAGE_EXT_RESOLVED cave=%s ui_index=%d table_order=%d floors=%d "
        "roster_total=%d timers=%.1f,%.1f sprays=%d,%d legacy=%.1f treasure=%d sha=%s"
        % (cave, pin["ui_index"], pin["table_order"], pin["floors"], roster_total,
           pin["floor_seconds"][0], pin["floor_seconds"][1],
           pin["bitter"], pin["spicy"], pin["legacy"], pin["treasure"],
           pin["sha256"][:8]),
        "P2_CHALLENGE_STAGE_EXT_ENGINE_UNTOUCHED cave=ch_NARI_01kusachi ui_index=3",
        "P2_CHALLENGE_STAGE_EXT_ENGINE_REFUSES cave=ch_ABEM_LeafChappy",
        "P2_CHALLENGE_STAGE_EXT_ENGINE_REFUSES cave=ch_NARI_02tile",
        "P2_CHALLENGE_STAGE_EXT_WINDOW size=960x540 pos=100,100 display=1920x1080 centered=1",
        "P2_CHALLENGE_STAGE_EXT_READY observed=12",
        "P2_CHALLENGE_STAGE_EXT_GATES all=UNTESTED content_wired=0",
        "PASS CHALLENGE_STAGE_TABLE_EXT",
    ]
    return "\n".join(lines) + "\n"


class TestPins(unittest.TestCase):
    def test_pins_match_lane_plan(self):
        if not LANES_JSON.is_file():
            self.skipTest("lane plan absent")
        plan = json.loads(LANES_JSON.read_text(encoding="utf-8"))
        by_id = {lane.get("source_id"): lane for lane in plan["lanes"]}
        for cave, pin in observer.ROWS.items():
            entry = (by_id.get(cave) or {}).get("details", {})
            self.assertEqual(pin["cave_path"], "user/Mukki/mapunits/caveinfo/%s.txt" % cave)
            self.assertEqual(pin["ui_index"], entry["ui_index"], cave)
            self.assertEqual(pin["table_order"], entry["table_order"], cave)
            self.assertEqual(pin["floors"], entry["floors"], cave)
            self.assertEqual(pin["floor_seconds"], entry["floor_seconds"], cave)
            self.assertEqual(pin["roster"], entry["pikmin_by_native_color_and_maturity"], cave)
            self.assertEqual(pin["bitter"], entry["bitter_sprays"], cave)
            self.assertEqual(pin["spicy"], entry["spicy_sprays"], cave)
            self.assertEqual(pin["legacy"], entry["legacy_time"], cave)
            self.assertEqual(pin["treasure"], entry["treasure_count_field"], cave)
            lane = next(l for l in plan["lanes"] if l.get("source_id") == cave)
            self.assertEqual(pin["sha256"], lane["source_sha256"], cave)

    def test_kusachi_not_in_extension(self):
        self.assertNotIn("ch_NARI_01kusachi", observer.ROWS)
        self.assertEqual(len(observer.ROWS), 2)

    def test_roster_totals(self):
        self.assertEqual(sum(sum(r) for r in observer.ROWS["ch_ABEM_LeafChappy"]["roster"]), 30)
        self.assertEqual(sum(sum(r) for r in observer.ROWS["ch_NARI_02tile"]["roster"]), 50)


class TestValidator(unittest.TestCase):
    def test_good_logs_pass(self):
        for cave in observer.ROWS:
            verdict = observer.validate(good_log(cave), cave)
            self.assertTrue(verdict["passed"], (cave, verdict["failures"]))
            self.assertTrue(verdict["engine_untouched"])
            self.assertTrue(verdict["engine_refuses_new"])

    def test_wrong_pin_fails(self):
        verdict = observer.validate(good_log("ch_ABEM_LeafChappy", ui_index=99),
                                    "ch_ABEM_LeafChappy")
        self.assertFalse(verdict["passed"])
        self.assertTrue(any("pin-mismatch" in f for f in verdict["failures"]))

    def test_missing_resolved_fails(self):
        verdict = observer.validate("P2_CHALLENGE_STAGE_EXT_READY observed=3\n",
                                    "ch_NARI_02tile")
        self.assertFalse(verdict["passed"])
        self.assertIn("no-resolved-marker", verdict["failures"])

    def test_refusal_fails(self):
        text = good_log("ch_NARI_02tile") + "P2_CHALLENGE_STAGE_EXT_REFUSED reason=pin-mismatch\n"
        verdict = observer.validate(text, "ch_NARI_02tile")
        self.assertFalse(verdict["passed"])
        self.assertIn("refused:pin-mismatch", verdict["failures"])

    def test_captain_down_blocked(self):
        text = good_log("ch_ABEM_LeafChappy") + \
            "P2_FIXTURE_CAPTAIN_DOWN tick=4 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED\n"
        verdict = observer.validate(text, "ch_ABEM_LeafChappy")
        self.assertTrue(verdict["captain_down"])
        self.assertFalse(verdict["passed"])

    def test_unknown_cave(self):
        verdict = observer.validate(good_log("ch_ABEM_LeafChappy"), "ch_NARI_99bogus")
        self.assertFalse(verdict["passed"])
        self.assertIn("unknown-cave", verdict["failures"])

    def test_cli_exit_codes(self):
        fd, path = tempfile.mkstemp(suffix=".log")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(good_log("ch_NARI_02tile"))
            proc = subprocess.run(
                [sys.executable, "-m", "experimental.pikmin2_challenge_stage_table_extension",
                 "--log", path, "--cave", "ch_NARI_02tile"],
                capture_output=True, text=True, timeout=60, cwd=str(ROOT))
            self.assertEqual(proc.returncode, 0, proc.stdout[-1000:])
            self.assertIn("VERDICT PASS", proc.stdout)
        finally:
            os.unlink(path)


EXT_TU = r"""
#include "pc_p2_challenge_stages_ext.h"
#include <cassert>
#include <cstdio>
#include <cstring>
int main() {
    assert(pc_p2_challenge_stages_ext_count() == 2);
    const P2ChallengeStageExtRow* leaf =
        pc_p2_challenge_stages_ext_lookup("ch_ABEM_LeafChappy");
    assert(leaf && leaf->uiIndex == 17 && leaf->tableOrder == 4 && leaf->floors == 2);
    assert(leaf->floorSeconds[0] == 85.0f && leaf->floorSeconds[1] == 100.0f);
    assert(leaf->bitterSprays == 1 && leaf->spicySprays == 1);
    assert(leaf->legacyTime == 400.0f && leaf->treasureCountField == 11);
    assert(!std::strcmp(leaf->sourceSha256,
        "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf"));
    const P2ChallengeStageExtRow* tile =
        pc_p2_challenge_stages_ext_lookup("ch_NARI_02tile");
    assert(tile && tile->uiIndex == 4 && tile->tableOrder == 19 && tile->floors == 2);
    assert(tile->floorSeconds[0] == 200.0f && tile->floorSeconds[1] == 150.0f);
    assert(tile->bitterSprays == 0 && tile->spicySprays == 5);
    assert(tile->legacyTime == 0.0f && tile->treasureCountField == 0);
    assert(!std::strcmp(tile->sourceSha256,
        "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6"));
    // kusachi must never resolve here (engine table owns it).
    assert(pc_p2_challenge_stages_ext_lookup("ch_NARI_01kusachi") == nullptr);
    assert(pc_p2_challenge_stages_ext_lookup("ch_NARI_99bogus") == nullptr);
    assert(pc_p2_challenge_stages_ext_lookup(nullptr) == nullptr);
    std::printf("EXT_TABLE_OK\n");
    return 0;
}
"""


class TestNativeTable(unittest.TestCase):
    def test_ext_table_compiles_strict_and_resolves(self):
        header = NATIVE / "pc_port" / "pc_p2_challenge_stages_ext.h"
        source = NATIVE / "pc_port" / "pc_p2_challenge_stages_ext.cpp"
        if not MINGW_GXX.exists():
            self.skipTest("MinGW g++ unavailable")
        if not header.is_file() or not source.is_file():
            self.skipTest("extension table absent")
        tmp = Path(tempfile.mkdtemp())
        try:
            tu = tmp / "ext_check.cpp"
            tu.write_text(EXT_TU, encoding="utf-8")
            exe = tmp / "ext_check.exe"
            env = dict(os.environ)
            env["PATH"] = r"C:\msys64\mingw64\bin;" + env.get("PATH", "")
            build = subprocess.run(
                [str(MINGW_GXX), "-std=c++17", "-O1", "-Wall", "-Wextra",
                 "-Werror", "-I", str(NATIVE / "pc_port"), str(tu), str(source),
                 "-o", str(exe)],
                capture_output=True, text=True, timeout=180, env=env)
            self.assertEqual(build.returncode, 0, build.stderr[-2000:])
            run = subprocess.run([str(exe)], capture_output=True, text=True,
                                 timeout=60, env=env)
            self.assertEqual(run.returncode, 0, run.stdout[-1000:])
            self.assertIn("EXT_TABLE_OK", run.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

