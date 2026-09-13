"""Breadbug lane (#213) tests: classification, nest linking, cargo contest,
defeat/cargo recovery reference rules, and real-extraction verification."""
import json
import math
import unittest
from pathlib import Path

from experimental.pikmin2_breadbug_lane import (
    ENTRIES, MAX_HELD_TREASURES, NEST_DEATH_FADE_FRAMES, PCS_IDLE, PCS_UNK2,
    PCS_CARRY, THROWUP_RING_SPEED, classify, spawnable, nest_house_type,
    contest_pullable, contest_pull, endcarry_outcome, throwup_velocities)
from experimental.pikmin2_breadbug_assets import target_allowed, carry_strength

LANE_IMPORT = Path('output/p2-lifecycle-batch/breadbug-lane-01')


class ClassificationTests(unittest.TestCase):
    def test_spawn_scope_matches_issue_213(self):
        self.assertEqual(sorted(ENTRIES), [38, 39, 40, 83])
        self.assertTrue(spawnable(38))
        self.assertTrue(spawnable(40))
        self.assertFalse(spawnable(39))
        self.assertFalse(spawnable(83))

    def test_helper_and_alias_roles_are_explicit(self):
        self.assertEqual(classify(39)['role'], 'helper_alias')
        self.assertEqual(classify(83)['role'], 'helper_nest')
        self.assertEqual(classify(40)['role'], 'source_boss')
        self.assertTrue(classify(40)['boss'])
        self.assertFalse(classify(38)['boss'])
        for bad in (0, 'PanModoki', 39.0, -1, None):
            with self.assertRaises(ValueError):
                classify(bad)

    def test_alias_39_has_no_independent_base(self):
        # enemyInfo.cpp has no EnemyInfo row for 39 and generalEnemyMgr.cpp has
        # no case 39; the module records this so a generator substitution can
        # never pick it as a creature.
        note = classify(39)['note']
        self.assertIn('no manager', note)
        self.assertIn('no defined base', note)


class NestLinkTests(unittest.TestCase):
    def test_house_type_follows_owner(self):
        self.assertEqual(nest_house_type(38), 1)  # NEST_Breadbug
        self.assertEqual(nest_house_type(40), 1)
        self.assertEqual(nest_house_type(64), 0)  # Jigumo crawmad nest model
        for bad in (39, 83, 0):
            with self.assertRaises(ValueError):
                nest_house_type(bad)

    def test_nest_death_fade_bound(self):
        # killNest sets mDeathTimer=1; the draw loop increments it and disables
        # collision after 80 frames (enemyNestMgr.cpp:143-152).
        self.assertEqual(NEST_DEATH_FADE_FRAMES, 80)


class ContestTests(unittest.TestCase):
    def test_pullable_contest_channels(self):
        self.assertTrue(contest_pullable(PCS_IDLE, 0.0, 1.0))
        self.assertTrue(contest_pullable(PCS_UNK2, 3.0, 0.5))  # same channel
        # Pikmin carry channel resists equal or weaker breadbug drag
        self.assertFalse(contest_pullable(PCS_CARRY, 2.0, 2.0))
        self.assertFalse(contest_pullable(PCS_CARRY, 5.0, 2.0))
        self.assertTrue(contest_pullable(PCS_CARRY, 1.5, 2.0))  # strictly greater wins
        with self.assertRaises(ValueError):
            contest_pullable(PCS_CARRY, float('nan'), 1.0)

    def test_pull_takeover_stalls_half_second(self):
        self.assertEqual(contest_pull(PCS_CARRY, 1.0, 3.0), (PCS_UNK2, 3.0, 0.5))
        self.assertEqual(contest_pull(PCS_CARRY, 3.0, 1.0), (PCS_CARRY, 3.0, 0.0))
        self.assertEqual(contest_pull(PCS_IDLE, 0.0, 2.5), (PCS_UNK2, 2.5, 0.0))

    def test_breadbug_strength_and_thresholds(self):
        # mCarryStrength = (min+max)*0.5 (panModoki.cpp:1314); a 1-pellet (1/2)
        # out-drags a single carrying Pikmin but loses to two.
        self.assertEqual(carry_strength(1, 2), 1.5)
        self.assertTrue(contest_pullable(PCS_CARRY, 1.0, carry_strength(1, 2)))
        self.assertFalse(contest_pullable(PCS_CARRY, 2.0, carry_strength(1, 2)))
        # Giant (weight 10/20 cargo) overpowers ordinary crews.
        self.assertEqual(carry_strength(10, 20), 15.0)
        self.assertTrue(contest_pullable(PCS_CARRY, 14, carry_strength(10, 20)))

    def test_target_thresholds_differ_by_variant(self):
        # Retail ip01 proper: small 11 (targets strictly lighter), giant 1
        # (targets at-or-above). PanModokiBase.h:203; panModoki/OoPanModoki.h:16.
        self.assertTrue(target_allowed('PanModoki', 10, 11))
        self.assertFalse(target_allowed('PanModoki', 11, 11))
        self.assertTrue(target_allowed('OoPanModoki', 1, 1))
        self.assertTrue(target_allowed('OoPanModoki', 20, 1))


class DefeatRecoveryTests(unittest.TestCase):
    def test_endcarry_fates(self):
        first = endcarry_outcome('treasure', 0)
        self.assertEqual(first['fate'], 'nest_capture')
        self.assertEqual(first['stored_slot'], 0)
        later = endcarry_outcome('treasure', 3)
        self.assertEqual(later['fate'], 'kill_and_record')
        self.assertEqual(later['stored_slot'], 3)
        self.assertEqual(endcarry_outcome('carcass', 0)['fate'], 'kill')
        self.assertEqual(endcarry_outcome('item', 0)['fate'], 'kill')
        self.assertTrue(endcarry_outcome('treasure', 1)['kills_carriers'])
        with self.assertRaises(ValueError):
            endcarry_outcome('treasure', MAX_HELD_TREASURES)  # cap enforced upstream
        with self.assertRaises(ValueError):
            endcarry_outcome('upgrade', 0)

    def test_throwup_ring_recovery(self):
        single = throwup_velocities(1, (0.0, 5.0, 0.0))
        self.assertEqual(single, [(0.0, 5.0, 0.0)])  # no radial offset for one
        four = throwup_velocities(4)
        self.assertEqual(len(four), 4)
        for vx, vy, vz in four:
            self.assertAlmostEqual(math.hypot(vx, vz), THROWUP_RING_SPEED)
            self.assertEqual(vy, 0.0)
        # Ring order matches TAU*i/n (panModoki.cpp:1683-1687).
        self.assertAlmostEqual(four[1][0], THROWUP_RING_SPEED)  # sin(pi/2)
        self.assertAlmostEqual(four[3][0], -THROWUP_RING_SPEED)
        with self.assertRaises(ValueError):
            throwup_velocities(0)
        with self.assertRaises(ValueError):
            throwup_velocities(MAX_HELD_TREASURES + 1)


@unittest.skipUnless((LANE_IMPORT / 'breadbug-lane.json').exists(),
                     'lane extraction output not present')
class ExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((LANE_IMPORT / 'breadbug-lane.json').read_text())

    def test_all_species_converted(self):
        small = self.data['species']['PanModoki']
        giant = self.data['species']['OoPanModoki']
        nest = self.data['species']['PanHouse']
        self.assertEqual(len(small['clips']), 9)
        self.assertEqual(len(giant['clips']), 9)
        self.assertTrue(all(c['status'] == 'sampled_poses_converted'
                            and c['poses'] for c in small['clips']))
        self.assertTrue(all(c['status'] == 'sampled_poses_converted'
                            and c['poses'] for c in giant['clips']))
        self.assertTrue(giant['weighted'])
        self.assertFalse(small['weighted'])
        self.assertEqual(nest['clips'], [])
        self.assertEqual(nest['static_pose']['file'], 'nest.mod')

    def test_retail_profile_values(self):
        small = self.data['species']['PanModoki']['profile']
        giant = self.data['species']['OoPanModoki']['profile']
        self.assertEqual((small['health'], giant['health']), (1100.0, 2000.0))
        self.assertEqual((small['proper']['max_carry_weight'],
                          giant['proper']['max_carry_weight']), (11, 1))
        self.assertEqual((small['proper']['carry_speed'],
                          giant['proper']['carry_speed']), (35.0, 45.0))
        self.assertEqual((small['proper']['press_damage'],
                          giant['proper']['press_damage']), (200.0, 100.0))

    def test_pose_files_match_recorded_hashes(self):
        from experimental.pikmin2_breadbug_assets import sha
        for species in ('PanModoki', 'OoPanModoki'):
            for clip in self.data['species'][species]['clips']:
                for pose in clip['poses']:
                    path = LANE_IMPORT / species / pose['file']
                    self.assertEqual(sha(path.read_bytes()), pose['sha256'])

    def test_classification_stored_with_extraction(self):
        self.assertFalse(self.data['classification']['39']['spawnable'])
        self.assertFalse(self.data['classification']['83']['spawnable'])
        self.assertFalse(self.data['native_ready'])


if __name__ == '__main__':
    unittest.main()
