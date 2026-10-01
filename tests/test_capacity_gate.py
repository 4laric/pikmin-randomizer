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

    def test_no_fixed_count_caps(self):
        # Owner ruling 2026-09-30: admission follows measured headroom, not counts.
        self.assertTrue(admit("game", snap(games=12))[0])
        self.assertTrue(admit("build", snap(free_gb=20.0, compilers=40), jobs=2)[0])

    def test_gpu_headroom_blocks_games(self):
        self.assertFalse(admit("game", snap(gpu_free_gb=1.0))[0])
        self.assertFalse(admit("game", snap(gpu_util=95.0))[0])
        self.assertTrue(admit("game", snap(gpu_free_gb=8.0, gpu_util=20.0))[0])

    def test_low_ram_blocks_games_and_builds(self):
        self.assertFalse(admit("game", snap(free_gb=3.0))[0])
        self.assertFalse(admit("build", snap(free_gb=5.0))[0])

    def test_busy_cpu_blocks_builds_before_games(self):
        self.assertFalse(admit("build", snap(cpu_percent=75))[0])
        self.assertTrue(admit("game", snap(cpu_percent=75))[0])
        self.assertFalse(admit("game", snap(cpu_percent=90))[0])

    def test_build_reserves_ram_per_job(self):
        need = LIMITS["build_min_free_gb"] + 4 * LIMITS["build_cost_gb_per_job"]
        self.assertTrue(admit("build", snap(free_gb=need), jobs=4)[0])
        self.assertFalse(admit("build", snap(free_gb=need - 0.5), jobs=4)[0])

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            admit("render", snap())


if __name__ == "__main__":
    unittest.main()
