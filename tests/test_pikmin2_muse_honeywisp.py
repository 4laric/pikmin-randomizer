"""Muse l65 tests: Honeywisp source-fact registry and runtime-log validator.

All fixtures are synthetic and hermetic, except the documented read-only
re-validation of preserved lane-15 logs, which runs outside pytest (see the
lane handoff) so this suite never depends on another lane's output directory.
"""
import unittest

from experimental.pikmin2_muse_honeywisp import (
    GATE2_SOURCE,
    GATE3_NA_CASE,
    GATE5_NA_CASE,
    SOURCE_ID,
    check_contact_drop,
    check_death,
    check_identity,
    check_movement,
    check_reward_chain,
    classify_reentry,
    gate_status,
    parse,
)

GOOD_LOG = """\
P2_QURIONE_BIND generator=203001 source_id=16 visual_only=0
P2_ENEMY_READY species=Qurione native_family=Qurione generator=203001 x=-104.0 y=30.0 z=1816.0 health=9999.0 max_health=9999.0 behavior=native source_FSM=implemented reward=P2_Egg
P2_QURIONE_EGG generator=203001 action=attach
P2_QURIONE_EGG_REAL generator=203001 born=1 drop_group=0
P2_QURIONE_STATE generator=203001 state=appear
P2_QURIONE_POS generator=203001 state=appear clip=appear1 phase=0.00 x=-103.86 y=29.95 z=1816.01
P2_QURIONE_STATE generator=203001 state=move
P2_QURIONE_POS generator=203001 state=move clip=waitl phase=0.00 x=-103.95 y=29.90 z=1816.06
P2_QURIONE_POS generator=203001 state=move clip=waitl phase=0.30 x=-103.95 y=73.04 z=1894.68
P2_QURIONE_POS generator=203001 state=move clip=waitl phase=0.61 x=-103.95 y=63.01 z=1977.28
P2_QURIONE_STATE generator=203001 state=drop
P2_QURIONE_EGG generator=203001 action=drop
P2_QURIONE_EGG_REAL generator=203001 released=1
P2_QURIONE_EGG_BOUNCE generator=203001 health_zeroed=1
P2_QURIONE_EGG_BREAK generator=203001 type=3 items=2 real=1
P2_QURIONE_EGG_ITEM generator=203001 index=0 kind=2 real=1 fallback=0 item=nectar x=-103.9 y=4.0 z=1818.7
P2_QURIONE_EGG_ITEM generator=203001 index=1 kind=2 real=1 fallback=0 item=nectar x=-103.9 y=4.0 z=1818.7
P2_QURIONE_STATE generator=203001 state=dead
P2_QURIONE_POS generator=203001 state=dead clip=run phase=1.00 x=-103.86 y=111.93 z=1818.68
P2_QURIONE_DEAD generator=203001 source_id=16
P2_QURIONE_POS generator=203001 state=dead clip=run phase=1.00 x=-103.86 y=213.28 z=1818.68
P2_QURIONE_FORGET generator=203001
"""


class SourceFactTests(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(SOURCE_ID, 16)

    def test_gate5_case_covers_no_carcass_no_haul_no_pellets(self):
        case = " ".join(GATE5_NA_CASE.values())
        for token in ("EB_LeaveCarcass", "EDG_None", "mForcedDropType",
                      "HONEY_Y", "EnemyID_Egg", "KEYEVENT_2"):
            self.assertIn(token, case, token)

    def test_gate5_case_forbids_pellet_claim(self):
        case = " ".join(GATE5_NA_CASE.values())
        self.assertIn("no pellet reward may be claimed", case)

    def test_gate3_case_covers_no_attack_and_contact_trigger(self):
        case = " ".join(GATE3_NA_CASE.values())
        for token in ("flyCollisionCallBack", "EB_Invulnerable", "QURIONE_Drop"):
            self.assertIn(token, case, token)

    def test_gate2_source_covers_retrigger(self):
        case = " ".join(GATE2_SOURCE.values())
        self.assertIn("isAppear", case)


class ValidatorTests(unittest.TestCase):
    def test_good_log_passes_all_log_level_gates(self):
        status = gate_status(GOOD_LOG)
        for gate in ("identity_spawn", "movement_animation", "attacks_receivers",
                     "death_corpse", "transport_reward", "cleanup_reentry"):
            self.assertEqual(status[gate][0], "PASS", (gate, status[gate][1]))
        self.assertTrue(status["no_nan"][0])

    def test_nan_positions_fail_movement(self):
        bad = GOOD_LOG.replace("z=1894.68", "z=nan")
        ok, _ = check_movement(parse(bad))
        self.assertFalse(ok)
        self.assertFalse(gate_status(bad)["no_nan"][0])

    def test_frozen_movement_fails(self):
        frozen = GOOD_LOG.replace("z=1894.68", "z=1816.06").replace("z=1977.28", "z=1816.06")
        ok, why = check_movement(parse(frozen))
        self.assertFalse(ok)
        self.assertTrue("distinct" in why or "displacement" in why, why)

    def test_drop_without_move_is_not_contact_trigger(self):
        no_move = "\n".join(
            line for line in GOOD_LOG.splitlines()
            if "state=move" not in line and "state=appear" not in line
        )
        ok, _ = check_contact_drop(parse(no_move))
        self.assertFalse(ok)

    def test_broken_reward_chain_fails_without_inventing_pellets(self):
        no_break = "\n".join(
            line for line in GOOD_LOG.splitlines() if "EGG_BREAK" not in line and "EGG_ITEM" not in line
        )
        ok, why = check_reward_chain(parse(no_break))
        self.assertFalse(ok)
        self.assertNotIn("pellet", why)

    def test_non_nectar_item_rejected(self):
        pellet = GOOD_LOG.replace("item=nectar", "item=pellet")
        ok, why = check_reward_chain(parse(pellet))
        self.assertFalse(ok)
        self.assertIn("non-nectar", why)

    def test_death_requires_dead_marker(self):
        alive = "\n".join(line for line in GOOD_LOG.splitlines() if "DEAD" not in line)
        ok, _ = check_death(parse(alive))
        self.assertFalse(ok)

    def test_second_bind_is_new_actor_not_same_wisp(self):
        rebound = GOOD_LOG + "P2_QURIONE_BIND generator=203002 source_id=16 visual_only=0\n"
        kind, _ = classify_reentry(parse(rebound))
        self.assertEqual(kind, "new-actor")

    def test_second_appear_single_bind_is_same_wisp(self):
        two_cycles = GOOD_LOG.replace(
            "P2_QURIONE_FORGET generator=203001",
            "P2_QURIONE_STATE generator=203001 state=appear\n"
            "P2_QURIONE_STATE generator=203001 state=move\n"
            "P2_QURIONE_FORGET generator=203001",
        )
        kind, why = classify_reentry(parse(two_cycles))
        self.assertEqual(kind, "same-wisp")
        self.assertIn("203001", why)

    def test_identity_requires_native_ready(self):
        no_ready = "\n".join(line for line in GOOD_LOG.splitlines() if "ENEMY_READY" not in line)
        ok, _ = check_identity(parse(no_ready))
        self.assertFalse(ok)

    def test_empty_log_is_untested_everywhere(self):
        status = gate_status("")
        for gate in ("identity_spawn", "movement_animation", "attacks_receivers",
                     "death_corpse", "transport_reward", "cleanup_reentry"):
            self.assertEqual(status[gate][0], "UNTESTED", gate)


if __name__ == "__main__":
    unittest.main()
