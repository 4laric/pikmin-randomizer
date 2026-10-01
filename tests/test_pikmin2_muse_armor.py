"""Focused tests for the muse Armor15 observer and run-log reader (#165)."""
import os
import re
import unittest
from pathlib import Path

from experimental.pikmin2_muse_armor import (
    FORBIDDEN_FIXTURE_PATTERNS,
    validate,
)

GOOD_LOG = """\
Experimental preview window set to 960x540 windowed and centered
P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0
P2_MUSE_ARMOR_WINDOW bittered=1 source=armor_module_input
P2_MUSE_ARMOR_READY squad=20 armor_gen=346001 health=300.00
P2_ARMOR_RECEIVER generator=346001 decision=accept reason=weakpoint part=none bittered=0 weakpoint=dm1
P2_ARMOR_RECEIVER generator=346001 decision=accept reason=weakpoint part=none bittered=0 weakpoint=dm1
P2_MUSE_ARMOR_HP health=100.00 squad=20 atk=20 events=5 tick=300
P2_MUSE_ARMOR_DRAIN events=8 min=25.00 start=300.00
P2_MUSE_ARMOR_NATURAL_DEATH armor=1 health=0.00 tick=420
P2_ARMOR_DEAD generator=346001 source_id=15 health=0
P2_MUSE_ARMOR_CORPSE pellet=1 generator=346001
P2_MUSE_ARMOR_CARRY state=0 alive=1 transport=6 pokos=0
P2_POD_RECEIPT id=corpse:346001 value=2 new=1 pokos=2 seeds=0
P2_MUSE_ARMOR_FORGET count=0 registered=0
P2_MUSE_ARMOR_REENTRY old=000001 new=000002 stale=0 fresh=1 count=1
P2_MUSE_ARMOR_SESSION navi=1 pikis=18
PASS P2_MUSE_ARMOR death=Armor corpse=1 receipt=1 reentry=1 injected=0
"""

PREFIX_RECEIPT_LOG = GOOD_LOG.replace(
    "id=corpse:346001", "id=corpse:armor:346001")


def fixture_source():
    """Locate the reserved native fixture source, or None if unresolvable."""
    env = os.environ.get("PIKMIN_MUSE_ARMOR_FIXTURE")
    if env and Path(env).is_file():
        return Path(env)
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "native" / "tools" / "p2_muse_armor_fixture.cpp",
        root.parent / "armor15-observer-native" / "tools" / "p2_muse_armor_fixture.cpp",
    ]
    native = os.environ.get("PIKMIN_NATIVE_ROOT")
    if native:
        candidates.insert(0, Path(native) / "tools" / "p2_muse_armor_fixture.cpp")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


class ArmorObserverTests(unittest.TestCase):
    def test_valid_log_passes(self):
        result = validate(GOOD_LOG)
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["gates"]["death_corpse"], "pass")
        self.assertEqual(result["gates"]["transport_reward"], "pass")
        self.assertEqual(result["gates"]["cleanup_reentry"], "pass")
        self.assertEqual(result["accepts"], 2)
        self.assertEqual(result["drain_events"], 8)

    def test_prefixed_receipt_also_parses(self):
        result = validate(PREFIX_RECEIPT_LOG)
        self.assertTrue(result["passed"])
        self.assertTrue(result["checks"]["natural_carry"])

    def test_injected_run_is_rejected(self):
        for marker in ("P2_MUSE_ARMOR_INJECT armor injected_health=0 not_natural_combat=1",
                       "P2_LIFECYCLE_INJECT species=Armor injected_health=0"):
            with self.subTest(marker=marker[:24]):
                result = validate(GOOD_LOG + marker + "\n")
                self.assertFalse(result["passed"])
                self.assertTrue(result["natural_vs_injected"]["inject_present"])
                self.assertEqual(result["gates"]["death_corpse"], "fail")

    def test_drain_without_events_fails(self):
        log = GOOD_LOG.replace("P2_MUSE_ARMOR_DRAIN events=8 min=25.00 start=300.00\n", "")
        result = validate(log)
        self.assertFalse(result["passed"])
        self.assertEqual(result["gates"]["death_corpse"], "fail")

    def test_health_written_to_zero_fails(self):
        # A single jump with no observed accepts is not natural drain.
        log = GOOD_LOG.replace(
            "P2_MUSE_ARMOR_DRAIN events=8 min=25.00 start=300.00",
            "P2_MUSE_ARMOR_DRAIN events=0 min=0.00 start=300.00").replace(
            "P2_ARMOR_RECEIVER generator=346001 decision=accept reason=weakpoint part=none bittered=0 weakpoint=dm1\n", "")
        result = validate(log)
        self.assertFalse(result["passed"])
        self.assertEqual(result["gates"]["death_corpse"], "fail")

    def test_missing_receipt_fails_transport(self):
        log = GOOD_LOG.replace(
            "P2_POD_RECEIPT id=corpse:346001 value=2 new=1 pokos=2 seeds=0\n", "")
        result = validate(log)
        self.assertFalse(result["passed"])
        self.assertEqual(result["gates"]["transport_reward"], "fail")

    def test_zero_transport_fails_transport(self):
        log = GOOD_LOG.replace("transport=6", "transport=0")
        result = validate(log)
        self.assertFalse(result["passed"])
        self.assertEqual(result["gates"]["transport_reward"], "fail")

    def test_missing_reentry_fails_cleanup(self):
        log = re.sub(r"P2_MUSE_ARMOR_REENTRY[^\n]*\n", "", GOOD_LOG)
        result = validate(log)
        self.assertFalse(result["passed"])
        self.assertEqual(result["gates"]["cleanup_reentry"], "fail")

    def test_failure_exit_code_fails(self):
        result = validate(GOOD_LOG, code=1)
        self.assertFalse(result["passed"])

    def test_reader_is_dependency_free(self):
        source = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_muse_armor.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", text)
        self.assertNotIn("import sqlite3", text)

    def test_fixture_source_has_no_health_or_transport_write(self):
        path = fixture_source()
        if path is None:
            self.skipTest("reserved native fixture source not resolvable in this checkout")
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_FIXTURE_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text),
                                  "fixture must not contain " + pattern)
        self.assertIn("P2_MUSE_ARMOR_READY", text)
        self.assertIn("P2_MUSE_ARMOR_REENTRY", text)


if __name__ == "__main__":
    unittest.main()
