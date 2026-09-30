import unittest

from scripts.capacity_gate import LIMITS, Snapshot, admit


def snap(**kw):
    base = dict(free_gb=12.0, cpu_percent=40.0, games=0, compilers=0, logical_cpus=24)
    base.update(kw)
    return Snapshot(**base)


class CapacityGateTest(unittest.TestCase):
    def test_idle_machine_admits_both(self):
        self.assertTrue(admit("game", snap())[0])
        self.assertTrue(admit("build", snap())[0])

    def test_game_ceiling_is_a_backstop(self):
        ok, reason = admit("game", snap(games=LIMITS["max_games"]))
        self.assertFalse(ok)
        self.assertIn("max", reason)

    def test_low_ram_blocks_games_and_builds(self):
        self.assertFalse(admit("game", snap(free_gb=3.0))[0])
        self.assertFalse(admit("build", snap(free_gb=5.0))[0])

    def test_busy_cpu_blocks_builds_before_games(self):
        self.assertFalse(admit("build", snap(cpu_percent=75))[0])
        self.assertTrue(admit("game", snap(cpu_percent=75))[0])
        self.assertFalse(admit("game", snap(cpu_percent=90))[0])

    def test_build_counts_requested_jobs(self):
        self.assertTrue(admit("build", snap(compilers=LIMITS["max_compilers"] - 4), jobs=4)[0])
        self.assertFalse(admit("build", snap(compilers=LIMITS["max_compilers"] - 3), jobs=4)[0])

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            admit("render", snap())


if __name__ == "__main__":
    unittest.main()
