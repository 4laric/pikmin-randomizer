"""Focused fail-closed tests for the P1 Challenge Forest acceptance driver."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "p1_forest_accept",
    ROOT / "scripts" / "p1_challenge_forest_runtime_acceptance.py")
driver = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(driver)

FULL_LOG = """[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)
Experimental preview window set to 960x540 windowed and centered
[Pikipelago] CHALLENGE_LAYOUT_READY id=challenge-1 stage_index=17 file=stages/chal1.ini story=1
[PC Generator] default: initialised 79 recognised generators, spawned 126 creatures
[PC Generator] plant: initialised 30 recognised generators, spawned 30 creatures
P2_CHALLENGE_PARK nx=325.259 ny=-37.722 nz=1996.714
P2_CHALLENGE_SQUAD pikis=20
P2_CHALLENGE_BOOT level=1 slot=chal1
PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive
"""


def _package(tmp, **overrides):
    stage = {"slot": "chal1", "area_id": "forest", "name": "Forest",
             "ini": "stages/chal1.ini", "ini_sha256": "0" * 64,
             "challenge_level": 1,
             "argv": ["nectar.exe", "--experimental-challenge-level", "1"],
             "env": {}}
    stage.update(overrides)
    obj = {"schema": 1, "stages": [stage]}
    path = os.path.join(tmp, "challenge-runtime-inputs.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return path
class ParseTests(unittest.TestCase):
    def test_full_log_facts(self):
        facts = driver.parse_run_log(FULL_LOG)
        self.assertTrue(facts["window_960x540"])
        self.assertTrue(facts["window_centered"])
        self.assertEqual(facts["layout_id"], "challenge-1")
        self.assertEqual(facts["spawned_total"], 156)
        self.assertEqual(facts["squad_pikis"], 20)
        self.assertEqual((facts["boot_level"], facts["boot_slot"]), (1, "chal1"))
        self.assertEqual(facts["park"], [325.259, -37.722, 1996.714])
        self.assertTrue(facts["fixture_pass_marker"])
        self.assertFalse(facts["captain_down"])

    def test_empty_log_unobserved(self):
        facts = driver.parse_run_log("nothing here\n")
        self.assertFalse(facts["window_960x540"])
        self.assertIsNone(facts["layout_id"])
        self.assertEqual(facts["spawned_total"], 0)
        self.assertIsNone(facts["squad_pikis"])
        self.assertFalse(facts["fixture_pass_marker"])
        self.assertFalse(facts["captain_down"])

    def test_captain_down_detected(self):
        facts = driver.parse_run_log(FULL_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=9\n")
        self.assertTrue(facts["captain_down"])


class AcceptTests(unittest.TestCase):
    def test_full_log_passes_identity_only(self):
        facts = driver.parse_run_log(FULL_LOG)
        record = driver.accept_facts(facts, "guardsha")
        self.assertEqual(record["schema"], "p2-challenge-forest-acceptance-1")
        self.assertEqual(record["gates"]["identity_spawn"]["status"], "PASS")
        self.assertEqual(record["gates"]["identity_spawn"]["method"], "natural")
        for gate in ("movement_animation", "attacks_receivers", "death_corpse",
                     "transport_reward", "cleanup_reentry"):
            self.assertEqual(record["gates"][gate]["status"], "UNTESTED")
        self.assertFalse(record["runtime_claim"])

    def test_captain_down_blocks_identity(self):
        facts = driver.parse_run_log(FULL_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=9\n")
        record = driver.accept_facts(facts, "guardsha")
        self.assertEqual(record["gates"]["identity_spawn"]["status"], "UNTESTED")
        self.assertEqual(record["gates"]["identity_spawn"]["method"], "unobserved")

    def test_missing_pass_marker_blocks(self):
        facts = driver.parse_run_log(FULL_LOG.replace(
            "PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive\n", ""))
        record = driver.accept_facts(facts, "guardsha")
        self.assertEqual(record["gates"]["identity_spawn"]["status"], "UNTESTED")

    def test_zero_squad_blocks(self):
        facts = driver.parse_run_log(FULL_LOG.replace("pikis=20", "pikis=0"))
        record = driver.accept_facts(facts, "guardsha")
        self.assertEqual(record["gates"]["identity_spawn"]["status"], "UNTESTED")

    def test_wrong_slot_blocks(self):
        facts = driver.parse_run_log(FULL_LOG.replace("slot=chal1", "slot=chal2"))
        record = driver.accept_facts(facts, "guardsha")
        self.assertEqual(record["gates"]["identity_spawn"]["status"], "UNTESTED")


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="chal1-acc-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_valid_package(self):
        path = _package(self.tmp)
        stage, problem = driver.check_stage_package(path)
        self.assertIsNone(problem)
        self.assertEqual(stage["slot"], "chal1")

    def test_missing_file(self):
        _stage, problem = driver.check_stage_package(
            os.path.join(self.tmp, "absent.json"))
        self.assertIn("unreadable-input-package", problem)

    def test_bad_schema(self):
        path = _package(self.tmp)
        obj = json.load(open(path, encoding="utf-8"))
        obj["schema"] = 999
        json.dump(obj, open(path, "w", encoding="utf-8"))
        _stage, problem = driver.check_stage_package(path)
        self.assertIn("bad-input-package-schema", problem)

    def test_level_mismatch(self):
        path = _package(self.tmp, challenge_level=2)
        _stage, problem = driver.check_stage_package(path)
        self.assertIn("chal1-level-mismatch", problem)

    def test_argv_mismatch(self):
        path = _package(self.tmp, argv=["nectar.exe", "--experimental-challenge-level", "3"])
        _stage, problem = driver.check_stage_package(path)
        self.assertIn("chal1-argv-mismatch", problem)

    def test_chal1_missing(self):
        path = _package(self.tmp, slot="chal2", challenge_level=2,
                        argv=["nectar.exe", "--experimental-challenge-level", "2"])
        _stage, problem = driver.check_stage_package(path)
        self.assertIn("chal1-stage-missing", problem)


if __name__ == "__main__":
    unittest.main()
