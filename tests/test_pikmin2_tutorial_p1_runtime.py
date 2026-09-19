"""Focused tests for experimental/pikmin2_tutorial_p1_runtime.py.

Covers staging, layout validation (including tamper detection), integrated
contract/locator pin consumption, and run-log verification (PASS only on full
evidence; UNSUPPORTED/UNOBSERVED otherwise). No engine, assets, or display.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_tutorial_p1_runtime import (
    contract_schema,
    pin_hashes,
    stage_run_layout,
    validate_run_layout,
    verify_run_log,
)

P1_RUN = os.path.join(
    "C:/Users/alari/pikmin-randomizer/output/workflow/autofill/planning-shards",
    "overworld-tutorial/prepared/tutorial-p1-surface-session-output/p1-run/run")

MANIFEST = os.path.join(P1_RUN, "manifest.json")
SEED = os.path.join(P1_RUN, "session-seed.json")
PINS = {"root": "c86e4029", "native": "b805d9c6"}
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")


class TutorialP1RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tutorial-p1-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def staged(self):
        outdir = os.path.join(self.tmp, "run")
        record = stage_run_layout(MANIFEST, SEED, outdir, PINS)
        return outdir, record

    def test_real_source_inputs_exist(self):
        self.assertTrue(os.path.isfile(MANIFEST), MANIFEST)
        self.assertTrue(os.path.isfile(SEED), SEED)
        seed = json.load(open(SEED, encoding="utf-8"))
        self.assertEqual(seed["schema"], contract_schema(REPO_ROOT))
        self.assertEqual(seed["course"], "tutorial")

    def test_stage_happy(self):
        outdir, record = self.staged()
        self.assertEqual(record["schema"], "p2-tutorial-p1-run-1")
        self.assertEqual(record["course"], "tutorial")
        self.assertEqual(record["source_pins"], PINS)
        self.assertEqual(validate_run_layout(outdir), [])
        self.assertTrue(os.path.isfile(os.path.join(outdir, "tutorial-p1", "manifest.json")))

    def test_stage_records_integrated_pins(self):
        _outdir, record = self.staged()
        integrated = record["integrated_pins"]
        self.assertIsNotNone(integrated["contract"])
        self.assertIsNotNone(integrated["source_locator"])
        self.assertRegex(integrated["contract"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(integrated["source_locator"]["sha256"], r"^[0-9a-f]{64}$")

    def test_pin_hashes_match_live_files(self):
        pins = pin_hashes(REPO_ROOT)
        for key in ("contract", "source_locator"):
            path = os.path.join(REPO_ROOT, pins[key]["path"])
            self.assertTrue(os.path.isfile(path), path)

    def test_stage_rejects_bad_seed_schema(self):
        bad = os.path.join(self.tmp, "seed.json")
        seed = json.load(open(SEED, encoding="utf-8"))
        seed["schema"] = "something-else"
        json.dump(seed, open(bad, "w", encoding="utf-8"))
        with self.assertRaises(ValueError):
            stage_run_layout(MANIFEST, bad, os.path.join(self.tmp, "run"), PINS)

    def test_stage_rejects_wrong_course(self):
        bad = os.path.join(self.tmp, "seed.json")
        seed = json.load(open(SEED, encoding="utf-8"))
        seed["course"] = "forest"
        json.dump(seed, open(bad, "w", encoding="utf-8"))
        with self.assertRaises(ValueError):
            stage_run_layout(MANIFEST, bad, os.path.join(self.tmp, "run"), PINS)

    def test_stage_rejects_bad_pins_json(self):
        from experimental.pikmin2_tutorial_p1_runtime import main
        code = main(["stage", "--manifest", MANIFEST, "--seed", SEED,
                     "--out", os.path.join(self.tmp, "run"), "--pins", "{bad"])
        self.assertEqual(code, 2)

    def test_validate_missing_layout(self):
        self.assertEqual(validate_run_layout(os.path.join(self.tmp, "absent")),
                         ["missing-or-bad-run-metadata"])

    def test_validate_detects_tamper(self):
        outdir, _record = self.staged()
        with open(os.path.join(outdir, "tutorial-p1", "manifest.json"), "a",
                  encoding="utf-8") as f:
            f.write("# tampered\n")
        problems = validate_run_layout(outdir)
        self.assertIn("hash-mismatch-manifest.json", problems)

    def test_validate_rejects_bad_schema(self):
        outdir, _record = self.staged()
        meta = os.path.join(outdir, "tutorial-p1", "run-metadata.json")
        record = json.load(open(meta, encoding="utf-8"))
        record["schema"] = "wrong"
        json.dump(record, open(meta, "w", encoding="utf-8"))
        self.assertIn("bad-run-schema", validate_run_layout(outdir))

    def test_verify_full_pass(self):
        log = ("P2_TUTORIAL_P1_WINDOW size=960x540\n"
               "P2_TUTORIAL_P1_ENGINE_FACT observed=120 squad_alive=20 diagnostic_only=1\n"
               "P2_TUTORIAL_P1_BOOT_PASS\nP2_TUTORIAL_P1_DAY_PASS\nP2_TUTORIAL_P1_SAVE_PASS\n"
               "P2_TUTORIAL_P1_RECEIPT_PASS\nP2_TUTORIAL_P1_REENTRY_PASS\n"
               "PASS TUTORIAL_P1_RUNTIME\n")
        result = verify_run_log(log)
        self.assertTrue(result["engine_boot"])
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["failure_markers"], [])
        self.assertTrue(all(v == "observed" for v in result["boundaries"].values()))

    def test_verify_unsupported_boundaries(self):
        log = ("P2_TUTORIAL_P1_WINDOW size=960x540\n"
               "P2_TUTORIAL_P1_ENGINE_FACT observed=120 squad_alive=20 diagnostic_only=1\n"
               "P2_TUTORIAL_P1_UNSUPPORTED boundary=day_transition reason=no-day-advance-api-in-port\n"
               "FAIL TUTORIAL_P1_RUNTIME boundaries_unobservable=5 observed=120\n")
        result = verify_run_log(log)
        self.assertTrue(result["engine_boot"])
        self.assertFalse(result["overall_pass"])
        self.assertEqual(result["boundaries"]["day_transition"], "unsupported")
        self.assertEqual(result["boundaries"]["boot_tutorial_surface"], "unobserved")
        self.assertIn("FAIL TUTORIAL_P1_RUNTIME", result["failure_markers"])

    def test_verify_captain_down_blocks_pass(self):
        log = ("P2_TUTORIAL_P1_WINDOW size=960x540\n"
               "P2_TUTORIAL_P1_ENGINE_FACT observed=5 squad_alive=20 diagnostic_only=1\n"
               "P2_TUTORIAL_P1_BOOT_PASS\nP2_TUTORIAL_P1_DAY_PASS\nP2_TUTORIAL_P1_SAVE_PASS\n"
               "P2_TUTORIAL_P1_RECEIPT_PASS\nP2_TUTORIAL_P1_REENTRY_PASS\n"
               "P2_FIXTURE_CAPTAIN_DOWN tick=9 outcome=BLOCKED\n")
        result = verify_run_log(log)
        self.assertFalse(result["overall_pass"])
        self.assertIn("P2_FIXTURE_CAPTAIN_DOWN", result["failure_markers"])

    def test_verify_empty_log(self):
        result = verify_run_log("")
        self.assertFalse(result["engine_boot"])
        self.assertFalse(result["overall_pass"])
        self.assertTrue(all(v == "unobserved" for v in result["boundaries"].values()))

    def test_main_validate_cli(self):
        from experimental.pikmin2_tutorial_p1_runtime import main
        outdir, _record = self.staged()
        self.assertEqual(main(["validate", "--dir", outdir]), 0)
        self.assertEqual(main(["validate", "--dir", os.path.join(self.tmp, "absent")]), 1)


if __name__ == "__main__":
    unittest.main()
