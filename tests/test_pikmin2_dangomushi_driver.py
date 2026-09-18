"""Tests for the DangoMushi fixture-side driver (issue #667). Hermetic
synthetic logs, except the real-observer integration (skipped when the
observer file is absent) and the canonical guard-hash check (repo file).
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "pikmin2_dangomushi_driver.py"
_spec = importlib.util.spec_from_file_location("pikmin2_dangomushi_driver", ADAPTER_PATH)
driver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(driver)

GEN = 41001
GOOD_LOG = f"""\
P2_DANGOMUSHI_BIND generator={GEN} source_id=94 visual_only=0
P2_DANGOMUSHI_DAMAGE_REJECTED generator={GEN} stickable=0 invulnerable=1 state=turn
P2_DANGOMUSHI_DAMAGE_ACCEPTED generator={GEN} stickable=1 state=turn
P2_DANGOMUSHI_DEAD generator={GEN} source_id=94 health=0
P2_BATCH3_DRAW corpse=1 key=DangoMushi clip=dead00
P2_DANGOMUSHI_BIND generator={GEN} source_id=94 visual_only=0
"""


class PlanTests(unittest.TestCase):
    def test_plan_five_ordered_steps(self):
        steps = driver.plan(GEN)
        self.assertEqual([s["step"] for s in steps],
                         ["bind", "damage", "death", "corpse", "reset"])
        self.assertIn(str(GEN), steps[0]["require"])

    def test_plan_rejects_bad_generator(self):
        for bad in (0, -3, "x", None):
            with self.assertRaises(driver.DriverError):
                driver.plan(bad)

    def test_plan_forbids_writes(self):
        damage = driver.plan(GEN)[1]
        self.assertIn("mHealth=", damage["forbid"])


class DriveTests(unittest.TestCase):
    def test_good_run_complete(self):
        result = driver.drive(driver.plan(GEN), GOOD_LOG)
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["generator"], GEN)
        self.assertTrue(all(s["met"] for s in result["steps"].values()))

    def test_missing_death_fails(self):
        log = "\n".join(l for l in GOOD_LOG.splitlines() if "DEAD" not in l)
        result = driver.drive(driver.plan(GEN), log)
        self.assertFalse(result["complete"])
        self.assertFalse(result["steps"]["death"]["met"])
        self.assertTrue(result["steps"]["damage"]["met"])

    def test_wrong_order_fails(self):
        lines = GOOD_LOG.splitlines()
        death = [l for l in lines if "DEAD" in l][0]
        rest = [l for l in lines if "DEAD" not in l]
        result = driver.drive(driver.plan(GEN), "\n".join([death] + rest))
        self.assertFalse(result["complete"])

    def test_rejections_only_never_proceed(self):
        log = (f"P2_DANGOMUSHI_BIND generator={GEN} source_id=94 visual_only=0\n"
               f"P2_DANGOMUSHI_DAMAGE_REJECTED generator={GEN} stickable=0 invulnerable=1\n")
        result = driver.drive(driver.plan(GEN), log)
        self.assertFalse(result["steps"]["damage"]["met"])
        self.assertFalse(result["complete"])

    def test_injected_rejected(self):
        result = driver.drive(driver.plan(GEN), GOOD_LOG + "P2_DANGOMUSHI_DEATH_INJECT\n")
        self.assertFalse(result["complete"])
        self.assertTrue(result["rejected"].startswith("injected:"))

    def test_health_write_rejected(self):
        result = driver.drive(driver.plan(GEN), GOOD_LOG + "mHealth=0\n")
        self.assertFalse(result["complete"])

    def test_captain_down_blocked(self):
        result = driver.drive(driver.plan(GEN), GOOD_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=9\n")
        self.assertFalse(result["complete"])
        self.assertTrue(result.get("blocked"))

    def test_rebind_other_generator_fails(self):
        log = GOOD_LOG.replace(f"BIND generator={GEN} source_id=94 visual_only=0",
                               "BIND generator=99999 source_id=94 visual_only=0", 1)
        result = driver.drive(driver.plan(GEN), log)
        self.assertFalse(result["complete"])

    def test_non_string_log_rejected(self):
        with self.assertRaises(driver.DriverError):
            driver.drive(driver.plan(GEN), None)


class ObserverIntegrationTests(unittest.TestCase):
    def test_real_observer_agrees(self):
        checked = driver.check_observer(GOOD_LOG)
        if checked.get("skipped"):
            self.skipTest(checked["skipped"])
        self.assertTrue(checked["verdict"]["gate_ok"], checked["verdict"])
        bad = driver.check_observer("P2_DANGOMUSHI_BIND generator=1 source_id=94\n")
        self.assertFalse(bad["verdict"]["gate_ok"])

    def test_guard_hash_matches_canonical(self):
        guard = Path("C:/Users/alari/pikmin-randomizer/scripts/p2_fixture_captain_guard.h")
        if not guard.is_file():
            self.skipTest("canonical guard absent")
        import hashlib
        self.assertEqual(hashlib.sha256(guard.read_bytes()).hexdigest(),
                         driver.GUARD_SHA256)
        record = driver.guard_record()
        self.assertEqual(record["sha256"], driver.GUARD_SHA256)


if __name__ == "__main__":
    unittest.main()
