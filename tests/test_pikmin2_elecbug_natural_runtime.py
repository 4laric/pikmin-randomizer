"""Unit tests for the ElecBug (28) natural lethal-death validator.

No native build, disc assets, GL or player session are touched: the pure-log
`validate` is exercised against the natural `GOOD_LOG` and negative/regression
logs for each required gate.
"""
import unittest

from experimental.pikmin2_elecbug_natural_runtime import (
    APP, ELECBUG_GEN, ELECBUG_SOURCE_ID, GOOD_LOG, REQUIRED_CHECKS, validate)


class ElecBugNaturalRuntimeTests(unittest.TestCase):
    def test_app_drives_no_injection(self):
        assert 'mHealth=' not in APP
        assert 'P2_LIFECYCLE_INJECT' not in APP
        assert 'pc_p2_elecbug_pressed(' not in APP  # press via the landing probe, not a direct call
        # The fixture stages a descending Purple (resetPosition + downward velocity)
        # and lets the family-local landing probe flip the beetle naturally.
        assert '-100.0f,0.0f' in APP
        assert 'pc_p2_set_species' in APP  # Purple/Yellow designated via lane-11 storage

    def test_constants(self):
        self.assertEqual(ELECBUG_GEN, 346002)
        self.assertEqual(ELECBUG_SOURCE_ID, 28)

    def test_validate_passes_on_natural_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(all(result['checks'][name] for name in REQUIRED_CHECKS))
        self.assertEqual(len(result['hit_values']), 4)

    def test_removing_flip_fails_natural_flip(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_FLIP generator=346002 source_id=28\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['natural_flip'])
        self.assertFalse(result['passed'])

    def test_removing_state_reverse_fails_natural_flip(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_STATE generator=346002 state=reverse\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['natural_flip'])
        self.assertFalse(result['passed'])

    def test_removing_natural_press_fails_natural_flip(self):
        # FLIP + reverse without the natural-landing press = injected flip.
        bad = GOOD_LOG.replace(
            'P2_ELECBUG_NATURAL_PRESS generator=346002 purple=1 source_id=28 state=charge\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['natural_flip'])
        self.assertFalse(result['passed'])

    def test_removing_yellow_immunity_fails(self):
        bad = GOOD_LOG.replace(
            'P2_ELECBUG_IMMUNE generator=346010 source_id=28 pikmin=yellow species=2\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['yellow_immunity'])
        self.assertFalse(result['passed'])

    def test_removing_hit_fails_vulnerability_damage(self):
        bad = GOOD_LOG
        for health in ('380.0', '210.0', '95.0', '24.0'):
            bad = bad.replace(
                'P2_ELECBUG_HIT generator=346002 source_id=28 health=%s\n' % health, '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['vulnerability_damage'])
        self.assertFalse(result['passed'])

    def test_removing_reentry_fails(self):
        bad = GOOD_LOG.replace(
            'P2_ELECBUG_NATURAL_REENTRY old=0x1 new=0x2 stale=0 fresh=1 count=2\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['reentry'])
        self.assertFalse(result['passed'])

    def test_inject_marker_fails_no_inject(self):
        spoof = GOOD_LOG + '\nP2_LIFECYCLE_INJECT generator=346002 source_id=28 not_natural_combat=1'
        result = validate(spoof, code=0)
        self.assertFalse(result['checks']['no_inject'])
        self.assertFalse(result['passed'])

    def test_death_without_flip_fails(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_FLIP generator=346002 source_id=28\n', '')
        result = validate(bad, code=0)
        self.assertTrue(result['checks']['natural_death'])
        self.assertFalse(result['checks']['natural_flip'])
        self.assertFalse(result['passed'])

    def test_flip_natural_label_is_rejected(self):
        # The press is staged (P1-derived), not natural combat; a token that
        # overclaims `flip=natural` must fail the staged_press gate.
        bad = GOOD_LOG.replace('flip=staged-press', 'flip=natural')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['staged_press'])
        self.assertFalse(result['passed'])

    def test_health_floor_stall_names_blocking_reason(self):
        stalled = '\n'.join([
            'P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0',
            'Experimental preview window set to 960x540 windowed and centered',
            'P2_ELECBUG_NATURAL_READY squad=20 elecbug_gen=346002 pair_gen=346010 reg=2',
            'P2_ELECBUG_NATURAL_DEPLOY free_squad=20 purple=1 yellow=1',
            'P2_ELECBUG_NATURAL_OBSERVE tick=600 health=500.00 state=charge squad=20',
            'P2_ELECBUG_NATURAL_BLOCKED health=500.00 squad=20',
            'FAIL p2 room: natural death timeout (health stalled)',
        ])
        result = validate(stalled, code=1)
        self.assertIsNotNone(result['blocking_reason'])
        self.assertIn('health_floor=500.0', result['blocking_reason'])
        self.assertFalse(result['passed'])

    def test_non_text_fails(self):
        with self.assertRaises(ValueError):
            validate(b'not text')

    def test_extinction_fails_no_extinction(self):
        bad = GOOD_LOG + '\nGAMEEND_PikminExtinction'
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
