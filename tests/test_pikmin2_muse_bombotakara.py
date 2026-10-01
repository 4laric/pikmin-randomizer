"""Unit tests for the Muse l61 BombOtakara93 natural observer (#501).

Exercises ``experimental.pikmin2_muse_bombotakara.validate`` against synthetic
captures only. No GL, assets, saves, or runtime are touched.
"""
import unittest

from experimental import pikmin2_muse_bombotakara as observer

GOOD_LINES = [
    "[PC Port] Experimental preview window set to 960x540 windowed and centered",
    "P2_OTAKARA_BIND generator=349001 source_id=93 stimulus=None visual_only=0",
    "P2_ENEMY_READY species=BombOtakara native_family=Chappy generator=349001 "
    "x=0.0000000 y=30.0000000 z=1850.0000000 health=150.0 max_health=150.0 "
    "behavior=native source_FSM=implemented attack=payload_delegated",
    "P2_OTAKARA_STATE generator=349001 state=flick",
    "P2_OTAKARA_DISCHARGE_NONE generator=349001 source_id=93 payload_delegated=1",
    "P2_BOMBOTAKARA_ATTACH generator=349001 payload=349002 joint=otakara natural=1",
    "P2_BOMBOTAKARA_BLAST generator=349001 payload=349002 center=10.000,30.000,20.000 "
    "radius=90.0 receivers=3 hits=2 pikmin_hits=1 teki_damage=500.0 "
    "navi_piki_damage=10.0 shared_primitive=1",
    "P2_BOMBOTAKARA_BOMB_HIT generator=349001 payload=349002 pikmin=0 accepted=1 "
    "target_state=22 interaction=InteractBomb natural=1",
]

GOOD = "\n".join(GOOD_LINES)
ATTACH_LINE = GOOD_LINES[5]
BLAST_LINE = GOOD_LINES[6]
BOMB_HIT_LINE = GOOD_LINES[7]
BIND_LINE = GOOD_LINES[1]


def _without(target):
    return "\n".join(line for line in GOOD_LINES if line != target)


class MuseBombotakaraTests(unittest.TestCase):
    def test_good_natural_log_passes(self):
        result = observer.validate(GOOD, code=0)
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["gates"]["identity_spawn"], "pass_natural")
        self.assertEqual(result["gates"]["attacks_receivers"], "pass_natural")
        self.assertFalse(result["injected"])

    def test_missing_attach_blocks_identity(self):
        result = observer.validate(_without(ATTACH_LINE), code=0)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["identity_spawn"])
        self.assertEqual(result["gates"]["identity_spawn"], "blocked")

    def test_missing_blast_blocks_receivers(self):
        result = observer.validate(_without(BLAST_LINE), code=0)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["attacks_receivers"])
        self.assertEqual(result["gates"]["attacks_receivers"], "blocked")

    def test_missing_bomb_hit_blocks_receivers(self):
        result = observer.validate(_without(BOMB_HIT_LINE), code=0)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["bomb_hit"])

    def test_zero_hit_blast_does_not_count(self):
        text = GOOD.replace("receivers=3 hits=2 pikmin_hits=1",
                            "receivers=0 hits=0 pikmin_hits=0")
        result = observer.validate(text, code=0)
        self.assertFalse(result["checks"]["blast_routed"])
        self.assertFalse(result["passed"])

    def test_injected_trigger_fails_natural(self):
        text = GOOD + "\nP2_BOMBOTAKARA_INJECT_1 75 349001 contact"
        result = observer.validate(text, code=0)
        self.assertTrue(result["injected"])
        self.assertFalse(result["checks"]["no_injection"])
        self.assertFalse(result["passed"])

    def test_guard_pikmin_counts_as_injected(self):
        text = GOOD + "\nP2_BOMBOTAKARA_FIXTURE_GUARD_PIKMIN injection=1"
        result = observer.validate(text, code=0)
        self.assertTrue(result["injected"])
        self.assertFalse(result["passed"])

    def test_nonzero_exit_fails(self):
        self.assertFalse(observer.validate(GOOD, code=1)["passed"])

    def test_zero_generator_bind_does_not_count(self):
        text = GOOD.replace("generator=349001 source_id=93", "generator=0 source_id=93")
        result = observer.validate(text, code=0)
        self.assertFalse(result["checks"]["identity_bind"])
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
