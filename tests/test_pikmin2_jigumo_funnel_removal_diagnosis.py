"""Focused tests for the Jigumo63 post-DEAD diagnosis (#823).

No runtime: synthetic marker chains exercise attribution (anim-end with no
removal), the unattributable branch (anim never completes), and fail-closed
malformed and missing-input refusal. The real gen-3 log is asserted to
yield the documented ATTRIBUTED verdict with family-then-engine routing,
never an invented provider.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experimental.pikmin2_jigumo_funnel_removal_diagnosis import (
    ATTRIBUTED,
    FILES,
    UNATTRIBUTABLE,
    Refused,
    analyze,
    attribute,
    trace_death,
)

REAL_LOG = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
            "planning-shards/enemies-4/prepared/"
            "shard-enemies-4-jigumo63-observer/out/jigumo-run2/pass1/"
            "c386be146feb4b5cac32abae073616a8/native.log")


ATTRIBUTED_LOG = """P2_JIGUMO_BIND generator=374003 source_id=63 visual_only=0
P2_JIGUMO_DEAD generator=374003 source_id=63 health=0
P2_JIGUMO_NATURAL_DEATH tick=186 throws=16 jigumo_alive=0
P2_JIGUMO_FUNNEL_DROVE engine=dieSoon
P2_JIGUMO_POS generator=0 state=dead clip=dead1 phase=0.21 x=1.0 y=2.0 z=3.0
P2_JIGUMO_POS generator=0 state=dead clip=dead1 phase=1.00 x=1.0 y=2.0 z=3.0
P2_JIGUMO_POS generator=0 state=dead clip=dead1 phase=1.00 x=2.0 y=1.0 z=4.0
P2_JIGUMO_REMOVAL_STALLED no_removal_no_corpse
FAIL p2 room: death produced neither removal nor corpse
"""

INCOMPLETE_LOG = """P2_JIGUMO_BIND generator=374003 source_id=63 visual_only=0
P2_JIGUMO_DEAD generator=374003 source_id=63 health=0
P2_JIGUMO_POS generator=0 state=dead clip=dead1 phase=0.21 x=1.0 y=2.0 z=3.0
P2_JIGUMO_POS generator=0 state=dead clip=dead1 phase=0.50 x=1.0 y=2.0 z=3.0
"""


class TraceTests(unittest.TestCase):
    def test_attributed_shape(self):
        t = trace_death(ATTRIBUTED_LOG.splitlines())
        self.assertTrue(t["dead_observed"])
        self.assertTrue(t["natural_death"])
        self.assertTrue(t["dead_anim_reached_end"])
        self.assertFalse(t["removal_observed"])
        self.assertTrue(t["corpse_fail_logged"])
        verdict, _, owner = attribute(t)
        self.assertEqual(verdict, ATTRIBUTED)
        self.assertIn("167", owner)

    def test_incomplete_unattributable(self):
        t = trace_death(INCOMPLETE_LOG.splitlines())
        self.assertFalse(t["dead_anim_reached_end"])
        verdict, _, _ = attribute(t)
        self.assertEqual(verdict, UNATTRIBUTABLE)

    def test_no_death_refused(self):
        with self.assertRaises(Refused):
            trace_death(["nothing here", "no markers"])


class RefusalTests(unittest.TestCase):
    def test_missing_log_refused(self):
        with self.assertRaises(Refused):
            analyze(os.path.join("no-such-dir-xyz", "native.log"))

    def test_empty_log_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "native.log")
            open(p, "w").write("  \n")
            with self.assertRaises(Refused):
                analyze(p)

    def test_files_pinned(self):
        self.assertEqual(len(FILES), 3)
        for blob in FILES.values():
            self.assertRegex(blob, r"^[0-9a-f]{64}$")


@unittest.skipUnless(os.path.exists(REAL_LOG), "gen-3 log unavailable")
class RealLogTests(unittest.TestCase):
    def test_real_log_attributed(self):
        r = analyze(REAL_LOG)
        self.assertEqual(r["verdict"], ATTRIBUTED)
        self.assertIn("167", r["owner"])
        self.assertTrue(r["trace"]["dead_anim_reached_end"])

    def test_real_log_has_death_chain(self):
        r = analyze(REAL_LOG)
        self.assertTrue(r["trace"]["natural_death"])
        self.assertIsNotNone(r["trace"]["funnel_drove"])


if __name__ == "__main__":
    unittest.main()
