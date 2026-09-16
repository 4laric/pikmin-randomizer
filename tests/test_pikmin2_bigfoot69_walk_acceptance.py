"""Unit tests for the BigFoot69 walk acceptance auditor (#574).

Synthetic logs only; no engine, actors or retail assets are touched. Covers
the natural-Walk pass, the separated net-displacement measure, teleport and
injection rejection, missing-Walk failure and Houdai preservation.
"""
import importlib.util
import unittest
from pathlib import Path


def _load():
    path = (Path(__file__).resolve().parents[1] / "experimental"
            / "pikmin2_bigfoot69_walk_acceptance.py")
    spec = importlib.util.spec_from_file_location("bigfoot69_acceptance", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ACC = _load()

READY = "P2_MUSE_WALK_READY squad=20 houdai_gen=312001 bigfoot_gen=312002"
BIND = ("P2_LONG_LEGS_BIND generator=312001 species=Houdai native_fsm=implemented\n"
        "P2_LONG_LEGS_BIND generator=312002 species=BigFoot native_fsm=implemented\n")
WINDOW = "Experimental preview window set to 960x540 windowed and centered"
SESSION = "P2_MUSE_WALK_SESSION navi=1 pikis=20"
WAKE = "P2_MUSE_WALK_WAKE_BIGFOOT captain=1"
STATE_WALK = "P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=Walk"
WALK = ("P2_LONG_LEGS_WALK species=BigFoot generator=312002 "
        "from=330.0,1900.0 to=200.0,1800.0 speed=70.0")
# 10 s Walk at 70 u/s toward a 161u target: 161 owned steps, net 161.
END = ("P2_LONG_LEGS_WALK_END species=BigFoot generator=312002 distance=161.0 "
       "seconds=10.00 start=330.0,1900.0 end=200.0,1800.0")
HOUDAI_END = ("P2_LONG_LEGS_WALK_END species=Houdai generator=312001 distance=38.5 "
              "seconds=0.16 start=149.8,1846.1 end=168.1,1813.3")
DEATH = "P2_MUSE_WALK_NATURAL_DEATH houdai=1 health=0.00 tick=1600"
HB = "P2_MUSE_WALK_HB frames=600 stage=1 observed=596 live=20 navimgr=1 naviobj=1 pikimgr=1"
PASS_LINE = "PASS P2_MUSE_LONGLEGS_WALK walk+Houdai-drain"

CARCASS_ROOT = "C:/Users/alari/pikmin-randomizer/native/pikmin2-research"


def good_log():
    return "\n".join([READY, BIND.strip(), WAKE, STATE_WALK, WALK, END,
                      HOUDAI_END, DEATH, SESSION, WINDOW, PASS_LINE, HB,
                      "disableEvent(0, EB_LeaveCarcass) present"]) + "\n"


class BigFootWalkTests(unittest.TestCase):
    def validate(self, text):
        return ACC.validate(text, retail_root=CARCASS_ROOT)

    def test_natural_walk_passes_with_net_measure(self):
        result = self.validate(good_log())
        self.assertTrue(result["passed"], result)
        self.assertAlmostEqual(result["walk"]["net"], 164.0, places=1)
        self.assertAlmostEqual(result["walk"]["drift"], 3.0, places=1)

    def test_missing_walk_fails(self):
        result = self.validate("\n".join([READY, WAKE, WINDOW]) + "\n")
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["bigfoot_walk"])

    def test_teleport_like_jump_rejected(self):
        log = good_log().replace(
            "distance=161.0 seconds=10.00", "distance=500.0 seconds=0.50")
        result = self.validate(log)
        self.assertFalse(result["checks"]["bigfoot_walk"])

    def test_short_net_displacement_rejected(self):
        log = good_log().replace("end=200.0,1800.0", "end=329.0,1899.0")
        result = self.validate(log)
        self.assertFalse(result["checks"]["bigfoot_walk"])

    def test_old_marker_without_net_positions_rejected(self):
        log = good_log().replace(" start=330.0,1900.0 end=200.0,1800.0", "")
        result = self.validate(log)
        self.assertFalse(result["checks"]["bigfoot_walk"])

    def test_injected_log_rejected(self):
        result = self.validate(good_log() + "P2_LL_INJECT Houdai health=0\n")
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["no_inject"])

    def test_wrong_generator_rejected(self):
        log = good_log().replace("generator=312002", "generator=999999")
        result = self.validate(log)
        self.assertFalse(result["checks"]["bigfoot_walk"])
        self.assertFalse(result["checks"]["bound"])

    def test_houdai_preserved(self):
        result = self.validate(good_log())
        self.assertTrue(result["checks"]["houdai_preserved"])

    def test_houdai_missing_fails_preserved(self):
        result = self.validate(good_log().replace(HOUDAI_END + "\n", ""))
        self.assertFalse(result["checks"]["houdai_preserved"])
        self.assertFalse(result["passed"])

    def test_no_carcass_audit(self):
        ok = ACC.check_no_carcass_source(CARCASS_ROOT)
        self.assertTrue(ok["passed"], ok)
        bad = ACC.check_no_carcass_source("C:/nonexistent-retail-root")
        self.assertFalse(bad["passed"])


if __name__ == "__main__":
    unittest.main()