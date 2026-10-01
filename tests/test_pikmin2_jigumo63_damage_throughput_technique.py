"""Focused technique tests: break-even math, gates, boundaries (#729)."""
import json
import unittest
from pathlib import Path

import experimental.pikmin2_jigumo63_damage_throughput_technique as tech


class RatioTests(unittest.TestCase):
    def test_break_even_constant(self):
        self.assertEqual(tech.BREAK_EVEN, 25.0)
        self.assertEqual(tech.HP_TOTAL, 500.0)
        self.assertEqual(tech.SQUAD_SIZE, 20)

    def test_pass1_ratio_below_break_even(self):
        ratio = tech.pass1_ratio()
        self.assertAlmostEqual(ratio, 120.0 / 7, places=4)
        self.assertLess(ratio, tech.BREAK_EVEN)
        self.assertFalse(tech.meets_break_even(120.0, 7))

    def test_strict_boundary(self):
        self.assertFalse(tech.meets_break_even(25.0, 1))
        self.assertTrue(tech.meets_break_even(25.1, 1))
        self.assertTrue(tech.meets_break_even(500.0, 19))

    def test_malformed_inputs_fail_closed(self):
        for bad in (("x", 1), (10.0, 0), (10.0, -2), (-5.0, 2), (10.0, 1.5)):
            with self.assertRaises(tech.TechniqueGapError):
                tech.throughput_ratio(*bad)


class GateTests(unittest.TestCase):
    def test_clean_run_has_no_problems(self):
        run = {"hp_drained": 500.0, "pikmin_lost": 12, "latched_attackers": True,
               "captain_down": False, "injected": False}
        self.assertEqual(tech.check_preconditions(run), [])

    def test_captain_down_taints(self):
        run = {"hp_drained": 500.0, "pikmin_lost": 12, "latched_attackers": True,
               "captain_down": True, "injected": False}
        self.assertTrue(any("captain-down" in p for p in tech.check_preconditions(run)))

    def test_no_latch_fails(self):
        run = {"hp_drained": 120.0, "pikmin_lost": 7, "latched_attackers": False,
               "captain_down": False, "injected": False}
        problems = tech.check_preconditions(run)
        self.assertTrue(any("latched" in p for p in problems))
        self.assertTrue(any("break-even" in p for p in problems))

    def test_missing_stats_listed(self):
        self.assertTrue(any("missing run stat" in p
                            for p in tech.check_preconditions({})))

    def test_packet_shape(self):
        packet = tech.packet()
        self.assertEqual(packet["downstream_issue"], 374)
        self.assertEqual(packet["family_change"][:4], "none")
        self.assertEqual(len(packet["validation_plan"]), 5)
        self.assertIn("25", json.dumps(packet))


class BoundaryTests(unittest.TestCase):
    def test_cli_report_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "packet.json"
            self.assertEqual(tech.main(["--out", str(target)]), 0)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["issue"], 729)
            self.assertEqual(len(payload["anchors"]), len(tech.ANCHORS))


if __name__ == "__main__":
    unittest.main()