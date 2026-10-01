"""Focused fail-closed tests for the #807 floor-9 descend evidence (no runtime here).

Verifies the floor-9 POLICY/admission marker grammar, the pinned constants,
and that malformed logs, wrong floors, captain-down interruptions and missing
PASS markers are all refused. The headed proof lives in the hashed boot log.
"""
import re
import unittest

ENTRY_VERSION = "P2_CAVE_ENTRY_4"
FLOOR = 9
EXPECTED_DESCEND = "1"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
FORBIDDEN = ("P2_FIXTURE_CAPTAIN_DOWN", "FAIL TUTORIAL2_FLOOR9")

POLICY_RE = re.compile(r"P2_TUTORIAL2_DESCEND_POLICY floor=(\d+) descend=([01])")
READY_RE = re.compile(r"P2_CAVE_READY floor=(\d+) survivors=(\d+)")
PASS_RE = re.compile(r"^PASS TUTORIAL2_FLOOR9", re.MULTILINE)


def check_floor9_log(text):
    """Fail-closed verdict for one floor-9 boot log. Returns the descend flag."""
    for bad in FORBIDDEN:
        if bad in text:
            raise ValueError("forbidden marker present: " + bad)
    ready = READY_RE.search(text)
    if not ready or int(ready.group(1)) != FLOOR or int(ready.group(2)) < 1:
        raise ValueError("floor-9 READY with live squad absent")
    match = POLICY_RE.search(text)
    if not match or int(match.group(1)) != FLOOR:
        raise ValueError("floor-9 POLICY marker absent")
    if match.group(2) != EXPECTED_DESCEND:
        raise ValueError("floor 9 descend=%s, expected %s" % (match.group(2), EXPECTED_DESCEND))
    if not PASS_RE.search(text):
        raise ValueError("floor-9 PASS marker absent")
    return match.group(2)


GOOD = (
    "P2_TUTORIAL2_DESCEND_POLICY floor=9 descend=1\n"
    "P2_CAVE_READY floor=9 survivors=20 health=1\n"
    "P2_TUTORIAL2_FLOOR9_ENTRY_READY floor=9 observed=1\n"
    "P2_TUTORIAL2_FLOOR9_PASS floor=9 squad_alive=20 observed=2\n"
    "PASS TUTORIAL2_FLOOR9\n"
)


class Floor9PolicyTests(unittest.TestCase):
    def test_pins_are_hashes(self):
        self.assertRegex(GUARD_SHA256, r"^[0-9a-f]{64}$")
        self.assertEqual(ENTRY_VERSION, "P2_CAVE_ENTRY_4")
        self.assertEqual(FLOOR, 9)

    def test_good_log_passes(self):
        self.assertEqual(check_floor9_log(GOOD), "1")

    def test_captain_down_refused(self):
        with self.assertRaisesRegex(ValueError, "forbidden"):
            check_floor9_log(GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=0 outcome=BLOCKED\n")

    def test_missing_ready_refused(self):
        with self.assertRaisesRegex(ValueError, "READY"):
            check_floor9_log("P2_TUTORIAL2_DESCEND_POLICY floor=9 descend=1\nPASS TUTORIAL2_FLOOR9\n")

    def test_wrong_floor_policy_refused(self):
        with self.assertRaisesRegex(ValueError, "POLICY"):
            check_floor9_log(GOOD.replace("floor=9 descend=1", "floor=8 descend=1"))

    def test_descend_zero_refused(self):
        with self.assertRaisesRegex(ValueError, "descend=0"):
            check_floor9_log(GOOD.replace("floor=9 descend=1", "floor=9 descend=0"))

    def test_missing_pass_refused(self):
        with self.assertRaisesRegex(ValueError, "PASS"):
            check_floor9_log(GOOD.replace("PASS TUTORIAL2_FLOOR9\n", ""))

    def test_empty_log_refused(self):
        with self.assertRaises(ValueError):
            check_floor9_log("")


if __name__ == "__main__":
    unittest.main()
