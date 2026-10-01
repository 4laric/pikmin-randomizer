"""Focused adoption tests: log verdicts for the impact rerun (#786)."""
import unittest

import experimental.pikmin2_impact_spawn_repair_adoption as adoption


GOOD = ("[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)\n"
        "Experimental preview window set to 960x540 windowed and centered\n"
        "P2_CHALLENGE_PARK_ALIVE pikis=21\n"
        "P2_CHALLENGE_SQUAD pikis=40\n"
        "P2_CHALLENGE_BOOT level=0 slot=chal0\n"
        "PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive\n")


class VerdictTests(unittest.TestCase):
    def test_full_pass_verdict(self):
        verdict = adoption.verify_run_log(GOOD)
        self.assertTrue(verdict["window_960x540"])
        self.assertTrue(verdict["window_centered"])
        self.assertEqual(verdict["park_alive_counts"], [21])
        self.assertEqual(verdict["squad_counts"], [40])
        self.assertEqual(verdict["boots"], [{"level": 0, "slot": "chal0"}])
        self.assertFalse(verdict["captain_down"])
        self.assertTrue(verdict["passed"])
        self.assertTrue(verdict["overall_pass"])

    def test_missing_squad_fails(self):
        log = ("P2_CHALLENGE_PARK_ALIVE pikis=21\n"
               "PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive\n")
        verdict = adoption.verify_run_log(log)
        self.assertFalse(verdict["overall_pass"])

    def test_zero_squad_fails(self):
        log = GOOD.replace("pikis=40", "pikis=0")
        verdict = adoption.verify_run_log(log)
        self.assertFalse(verdict["overall_pass"])

    def test_missing_boot_fails(self):
        log = GOOD.replace("P2_CHALLENGE_BOOT level=0 slot=chal0\n", "")
        verdict = adoption.verify_run_log(log)
        self.assertFalse(verdict["overall_pass"])

    def test_missing_window_fails(self):
        log = GOOD.replace(
            "[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)\n",
            "")
        verdict = adoption.verify_run_log(log)
        self.assertFalse(verdict["overall_pass"])
        self.assertTrue(verdict["passed"])

    def test_captain_down_blocks(self):
        log = (GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=9 hp=0.500 orima_dead=0 "
               "dead_state=1 outcome=BLOCKED\n")
        verdict = adoption.verify_run_log(log)
        self.assertTrue(verdict["captain_down"])
        self.assertFalse(verdict["overall_pass"])

    def test_non_text_fails_closed(self):
        with self.assertRaises(adoption.AdoptionGapError):
            adoption.verify_run_log(None)

    def test_cli_verify(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "headed.log"
            log.write_text(GOOD, encoding="utf-8")
            self.assertEqual(adoption.main(["--verify-log", str(log)]), 0)

    def test_cli_missing_refuses(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                adoption.main(["--verify-log", str(Path(tmp) / "nope.log")]), 2)


if __name__ == "__main__":
    unittest.main()