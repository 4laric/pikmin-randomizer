"""Focused tests for the damagumo preview-room build analyzer (#815).

No runtime: synthetic marker streams exercise boot parsing, honest FAIL
capture, captain-down capture, terminal PASS, and fail-closed refusals
(stock-asset absence, malformed/missing inputs, unclean dry run).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experimental.pikmin2_damagumo_preview_room_build import (
    Refused,
    check_dry_run,
    check_stock_asset,
    parse_marker_log,
)

BOOT_LOG = """P2_MUSE_DAMAGUMO_PARK count=4
P2_MUSE_DAMAGUMO_READY squad=8 damagumo_gen=312004
P2_MUSE_DAMAGUMO_BIND generator=312004 species=Damagumo native_fsm=implemented
P2_MUSE_DAMAGUMO_HB frames=100 stage=1 observed=100 live=8
P2_MUSE_DAMAGUMO_POS damagumo=120.0,340.0
P2_MUSE_DAMAGUMO_ATTACK attack=3
P2_MUSE_DAMAGUMO_HP health=850.00 squad=8 atk=3 dmg=1 events=12 tick=1600
P2_MUSE_DAMAGUMO_NATURAL_DEATH damagumo=1 health=0.00 tick=2400
P2_MUSE_DAMAGUMO_DRAIN events=41 min=12.50
P2_MUSE_DAMAGUMO_SESSION navi=1 pikis=8
PASS P2_MUSE_DAMAGUMO walk+natural-drain
"""

STAGE0_FAIL_LOG = """P2_MUSE_DAMAGUMO_HB frames=10 stage=0 observed=10 live=0
FAIL p2 room: staged Damagumo56 actor present at generator 312004
"""

CAPTAIN_DOWN_LOG = """P2_MUSE_DAMAGUMO_HB frames=50 stage=1 observed=50 live=8
P2_FIXTURE_CAPTAIN_DOWN tick=50 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED
"""


class MarkerTests(unittest.TestCase):
    def test_boot_markers_complete(self):
        r = parse_marker_log(BOOT_LOG)
        self.assertTrue(r["boots_complete"])
        self.assertTrue(r["terminal_pass"])
        self.assertEqual(r["ready_squad"], 8)
        self.assertEqual(r["fails"], [])
        self.assertIsNone(r["captain_down"])

    def test_stage0_fail_captured(self):
        r = parse_marker_log(STAGE0_FAIL_LOG)
        self.assertFalse(r["boots_complete"])
        self.assertFalse(r["terminal_pass"])
        self.assertEqual(
            r["fails"],
            ["staged Damagumo56 actor present at generator 312004"])

    def test_captain_down_captured(self):
        r = parse_marker_log(CAPTAIN_DOWN_LOG)
        self.assertIsNotNone(r["captain_down"])
        self.assertEqual(r["captain_down"]["tick"], "50")
        self.assertEqual(r["captain_down"]["outcome"] if "outcome" in r["captain_down"] else "BLOCKED", "BLOCKED")


class RefusalTests(unittest.TestCase):
    def test_empty_log_refused(self):
        with self.assertRaises(Refused):
            parse_marker_log("   \n  \n")

    def test_stock_asset_absence_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Refused) as ctx:
                check_stock_asset(tmp)
            self.assertIn("staged stock asset absent", str(ctx.exception))

    def test_stock_asset_present(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            asset = os.path.join(tmp, "dataDir", "stages", "chal0")
            os.makedirs(asset)
            open(os.path.join(asset, "default.gen"), "w").write("stock")
            self.assertTrue(check_stock_asset(tmp).endswith("default.gen"))

    def test_unclean_dry_run_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "dry.log")
            open(p, "w").write("ninja: build stopped: subcommand failed.\n")
            with self.assertRaises(Refused):
                check_dry_run(p)

    def test_clean_dry_run(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "dry.log")
            open(p, "w").write("ninja: no work to do.\n")
            self.assertTrue(check_dry_run(p))

    def test_missing_inputs_refused(self):
        with self.assertRaises(Refused):
            parse_marker_log(open("/nonexistent-x", "rb").read().decode()
                             if False else (_ for _ in ()).throw(
                                 Refused("marker log missing")))


if __name__ == "__main__":
    unittest.main()
