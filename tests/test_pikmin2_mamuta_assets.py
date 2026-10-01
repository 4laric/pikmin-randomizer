"""Mamuta (Miulin, ID 54) source-contract tests; issue #214, parent #168.

Covers spawn registry facts, the plant attack (Pikmin planted -> flower sprout),
idle/aggression state transitions and the floor/save lifecycle flags, all as
source-backed reference semantics from native/pikmin2-research. Native hook
wiring is out of scope for this lane.
"""
import math
import unittest
from pathlib import Path

from experimental.pikmin2_mamuta_assets import (
    BURIED_PIKMIN_CAP_US, EXPECTED_CLIPS, NAVI_BURY_DAMAGE, PIKI_BURY_DAMAGE,
    PROPER_PARM_DEFAULTS, PROPER_PARM_KEYS, STATE_IDS, TEXT,
    attack_band_hit, attack_start_eligible, bury_outcome, extract,
    lifecycle_flags, profile, wait_transition)


def _events(names=EXPECTED_CLIPS):
    return {name: [] for name in names}


def _parameters(proper=None):
    proper = dict(PROPER_PARM_DEFAULTS) if proper is None else proper
    return [{'ip01': 100.0}, {'fp00': 500.0, 'fp22': 40.0, 'fp24': 10.0}, proper]


class SpawnContractTests(unittest.TestCase):
    """Spawn/registry facts: generalEnemyMgr.cpp:394-395, enemyInfo.cpp:88, genEnemy.cpp:554."""

    def test_expected_clip_set_matches_source_anim_ids(self):
        self.assertEqual(len(EXPECTED_CLIPS), 9)
        self.assertEqual(len(set(EXPECTED_CLIPS)), 9)

    def test_profile_accepts_retail_shape(self):
        result = profile(_parameters(), _events())
        self.assertEqual(result['enemy_id'], 54)
        self.assertEqual(result['species'], 'Miulin')
        self.assertEqual(result['general']['health'], 500.0)
        self.assertEqual(result['proper_retail']['fp08'], 25.0)

    def test_profile_rejects_changed_clip_set(self):
        for names in [EXPECTED_CLIPS[:-1], EXPECTED_CLIPS + ('extra.bca',)]:
            with self.subTest(names=names), self.assertRaises(ValueError):
                profile(_parameters(), _events(names))

    def test_profile_rejects_unknown_or_missing_proper_key(self):
        with self.assertRaises(ValueError):
            profile(_parameters(proper=dict(PROPER_PARM_DEFAULTS, fp99=1.0)), _events())
        broken = dict(PROPER_PARM_DEFAULTS)
        del broken['ip01']
        with self.assertRaises(ValueError):
            profile(_parameters(proper=broken), _events())

    def test_budget_rejected_before_io(self):
        for count in [1, 9, True]:
            with self.subTest(count=count), self.assertRaises(ValueError):
                extract(Path('missing'), Path('unused'), count)


class PlantAttackTests(unittest.TestCase):
    """Bury attack: miulinState.cpp:264-330, interactPiki.cpp:377-442, interactNavi.cpp:218-226."""

    def test_attack_band_geometry(self):
        # inside vertical band and inside attack radius
        self.assertTrue(attack_band_hit(0.0, 100.0, 40.0))
        self.assertTrue(attack_band_hit(19.9, 1500.0, 40.0))
        # outside vertical band (miulinState.cpp:273-274, +/-20 around attack point)
        self.assertFalse(attack_band_hit(20.0, 100.0, 40.0))
        self.assertFalse(attack_band_hit(-25.0, 100.0, 40.0))
        # outside attack radius
        self.assertFalse(attack_band_hit(0.0, 1600.0, 40.0))
        for bad in [(float('nan'), 1.0, 40.0), (0.0, -1.0, 40.0), (0.0, 1.0, 0.0)]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                attack_band_hit(*bad)

    def test_attack_start_window(self):
        # retail: min range 25 (fp08), press angle 20 (fp03), attack radius 40
        self.assertTrue(attack_start_eligible(625.0, 0.0, 40.0, 25.0, 20.0))
        # outside the squared-distance band (miulin.cpp:186)
        self.assertFalse(attack_start_eligible(2300.0, 0.0, 40.0, 25.0, 20.0))
        # below the band only when the radius cannot swallow min range (10: band 525..725)
        self.assertFalse(attack_start_eligible(0.0, 0.0, 10.0, 25.0, 20.0))
        self.assertFalse(attack_start_eligible(800.0, 0.0, 10.0, 25.0, 20.0))
        # retail radius 40 swallows min range 25, so point-blank is eligible in source
        self.assertTrue(attack_start_eligible(0.0, 0.0, 40.0, 25.0, 20.0))
        # outside the continuous-press cone
        self.assertFalse(attack_start_eligible(625.0, math.radians(30.0), 40.0, 25.0, 20.0))
        with self.assertRaises(ValueError):
            attack_start_eligible(float('inf'), 0.0, 40.0, 25.0, 20.0)

    def test_bury_converts_to_flower_sprout(self):
        outcome = bury_outcome(invincible=False, buried_pikis=0, bald_triangle=False,
                               might_bury=True, sprout_mgr_available=True, sprout_birth_ok=True)
        self.assertEqual(outcome, 'convert')

    def test_bury_rejections_and_fallbacks(self):
        cases = [
            (dict(invincible=True), 'reject'),
            (dict(buried_pikis=BURIED_PIKMIN_CAP_US), 'reject'),
            (dict(buried_pikis=BURIED_PIKMIN_CAP_US + 5), 'reject'),
            (dict(bald_triangle=True), 'walk'),
            (dict(might_bury=False), 'walk'),
            (dict(sprout_mgr_available=False), 'walk'),
            (dict(sprout_birth_ok=False), 'walk'),
        ]
        base = dict(invincible=False, buried_pikis=98, bald_triangle=False, might_bury=True,
                    sprout_mgr_available=True, sprout_birth_ok=True)
        for override, expected in cases:
            with self.subTest(override=override):
                self.assertEqual(bury_outcome(**{**base, **override}), expected)

    def test_bury_inputs_validated(self):
        with self.assertRaises(ValueError):
            bury_outcome(False, '99', False, True, True, True)
        with self.assertRaises(ValueError):
            bury_outcome(False, 0, False, True, True, True, region='JP')

    def test_bury_damage_profile_is_nonlethal(self):
        result = profile(_parameters(), _events())
        contract = result['attack_contract']
        self.assertEqual(contract['kind'], 'bury')
        self.assertEqual(contract['piki_damage'], PIKI_BURY_DAMAGE)
        self.assertEqual(contract['piki_damage'], 0.0)
        self.assertEqual(contract['navi_damage'], NAVI_BURY_DAMAGE)
        self.assertEqual(contract['navi_damage'], 5.0)
        self.assertEqual(contract['vertical_band'], 20.0)


class StateTransitionTests(unittest.TestCase):
    """Idle/aggression transitions: miulinState.cpp:42-556, Miulin.h:20-31."""

    def test_state_ids_match_header(self):
        self.assertEqual(STATE_IDS, {'wait': 0, 'walk': 1, 'attackstart': 2, 'attacking': 3,
                                     'attackend': 4, 'turn': 5, 'flick': 6, 'dead': 7})

    def test_wait_remains_idle_without_target(self):
        self.assertIsNone(wait_transition(health=500.0, is_start_walk=False,
                                          attack_start=True, needs_turn=True))

    def test_wait_dead_checked_first(self):
        self.assertEqual(wait_transition(health=0.0, is_start_walk=True,
                                         attack_start=True, needs_turn=True), 'dead')

    def test_wait_aggression_order(self):
        # attack beats turn, turn beats walk (miulinState.cpp:65-73)
        self.assertEqual(wait_transition(500.0, True, True, True), 'attackstart')
        self.assertEqual(wait_transition(500.0, True, False, True), 'turn')
        self.assertEqual(wait_transition(500.0, True, False, False), 'walk')


class LifecycleTests(unittest.TestCase):
    """Floor/save lifecycle flags: enemyInfo.cpp:88, enemyInfo.h:29-40,
    generalEnemyMgr.cpp:923-941, zukan2D.cpp:179,2173-2183."""

    def test_registry_flags(self):
        flags = lifecycle_flags()
        self.assertTrue(flags['can_be_spawned'])
        self.assertTrue(flags['uses_own_id'])
        self.assertFalse(flags['can_appear_day_end'])
        self.assertFalse(flags['prepare_dayend_clears'])
        self.assertTrue(flags['piklopedia_tracks_stats'])
        self.assertTrue(flags['zukan_blinds_pikmin_lost'])

    def test_policy_marker(self):
        self.assertEqual(TEXT.split(),
                         ['P2_MAMUTA_1', 'nonlethal', 'bury_attack',
                          'piki_damage', '0', 'navi_damage', '5', 'vertical_band', '20'])


if __name__ == '__main__':
    unittest.main()
