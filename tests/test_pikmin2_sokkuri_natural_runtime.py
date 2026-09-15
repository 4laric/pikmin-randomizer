"""Unit tests for the Sokkuri natural lethal-death validator (#165/#407 slice 2).

No native build, disc assets, GL or player session are touched: the validator is
exercised against synthetic native logs for the natural pass, the injected
regression and the blocking mechanism.
"""
import unittest

from experimental.pikmin2_sokkuri_natural_runtime import (
    APP, PRIOR_HEALTH_MAX, SOKKURI_GEN, validate)

GOOD_LOG = '\n'.join([
    'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_SOKKURI_NATURAL_READY squad=20 sokkuri_gen=346005 reg=1',
    'P2_SOKKURI_NATURAL_DEPLOY free_squad=20 x=-100.00 z=1850.00',
    'P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=104.0',
    'P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=86.0',
    'P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=51.0',
    'P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=23.0',
    'P2_SOKKURI_NATURAL_OBSERVE tick=600 health=23.00 state=6 squad=20',
    'P2_SOKKURI_DEAD generator=346005 source_id=79 health=0 prior_health=23.0',
    'P2_SOKKURI_NATURAL_DIED tick=640 health=0.00',
    'P2_SOKKURI_NATURAL_CORPSE pellet=1 tick=700',
    'P2_SOKKURI_NATURAL_FORGET count=0',
    'P2_SOKKURI_NATURAL_REENTRY old=0x1 new=0x2 stale=0 fresh=1 count=1',
    'PASS P2_SOKKURI_NATURAL_RUNTIME death=natural corpse=1 cleanup=1 reentry=1 injected=0',
])


class SokkuriNaturalTests(unittest.TestCase):
    def test_empty_app_is_not_injected(self):
        assert 'mHealth=0.0f' not in APP
        assert 'P2_LIFECYCLE_INJECT' not in APP

    def test_validate_passes_on_natural_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['prior_health'], 23.0)
        self.assertEqual(len(result['damage']), 4)

    def test_injected_death_has_large_prior_health_and_fails_small_prior(self):
        injected = GOOD_LOG.replace('prior_health=23.0', 'prior_health=105.0')
        result = validate(injected, code=0)
        self.assertFalse(result['checks']['small_prior_health'])
        self.assertFalse(result['passed'])

    def test_inject_marker_fails_no_inject(self):
        spoof = GOOD_LOG + '\nP2_LIFECYCLE_INJECT injected_health=0 not_natural_combat=1'
        result = validate(spoof, code=0)
        self.assertFalse(result['checks']['no_inject'])
        self.assertFalse(result['passed'])

    def test_no_damage_but_death_fails(self):
        no_damage = GOOD_LOG.replace('P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=104.0\n', '')
        no_damage = no_damage.replace('P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=86.0\n', '')
        no_damage = no_damage.replace('P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=51.0\n', '')
        no_damage = no_damage.replace('P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=23.0\n', '')
        result = validate(no_damage, code=0)
        self.assertFalse(result['checks']['natural_damage'])
        self.assertFalse(result['passed'])

    def test_blocking_timeout_names_the_mechanism(self):
        blocked = '\n'.join([
            'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0',
            'Experimental preview window set to 960x540 windowed and centered',
            'P2_SOKKURI_NATURAL_READY squad=20 sokkuri_gen=346005 reg=1',
            'P2_SOKKURI_NATURAL_DEPLOY free_squad=20 x=-100.00 z=1850.00',
            'P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=118.0',
            'P2_SOKKURI_NATURAL_OBSERVE tick=4000 health=118.00 state=6 squad=12',
            'FAIL p2 room: natural death timeout (health stalled)',
        ])
        result = validate(blocked, code=1)
        self.assertIsNotNone(result['blocking_reason'])
        self.assertIn('min_health=118.0', result['blocking_reason'])
        self.assertIn('P2_SOKKURI_DAMAGE hits=1', result['blocking_reason'])
        self.assertFalse(result['passed'])

    def test_non_text_fails(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
