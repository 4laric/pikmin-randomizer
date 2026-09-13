"""Unit tests for the Sokkuri source-behavior validator (#407).

No native build, disc assets or player sessions are touched: the validator is
exercised against a synthetic native log and the private behavior-fixture
coordinate is checked against the source sight radius.
"""
import unittest

from experimental.pikmin2_sokkuri_behavior import (
    BEHAVIOR_POSITION, SOKKURI_ID, SOKKURI_INDEX, SPECIES, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0',
    'P2_ENEMY_READY species=Sokkuri native_family=Chappy generator=346005 x=180.0 y=30.0 '
    'z=1850.0 health=120.0 max_health=120.0 behavior=native source_FSM=implemented disguise=native',
    'P2_SOKKURI_DISGUISE generator=346005 hidden=1',
    'P2_SOKKURI_DISGUISE generator=346005 hidden=0',
    'P2_SOKKURI_STATE generator=346005 state=appear',
    'P2_SOKKURI_STATE generator=346005 state=moveground',
    'P2_BATCH2_DRAW corpse=0 key=ground|Sokkuri clip=appear1',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_SOKKURI_POS generator=346005 state=appear clip=appear1 phase=0.50 x=-100.00 z=1850.00',
    'P2_SOKKURI_POS generator=346005 state=moveground clip=run1 phase=0.10 x=-100.00 z=1850.00',
    'P2_SOKKURI_POS generator=346005 state=moveground clip=run1 phase=0.55 x=-90.00 z=1848.00',
    'P2_SOKKURI_POS generator=346005 state=moveground clip=run1 phase=0.90 x=-78.00 z=1845.00',
])


class SokkuriBehaviorTests(unittest.TestCase):
    def test_species_index_and_identity(self):
        self.assertEqual(SPECIES[SOKKURI_INDEX], 'Sokkuri')
        self.assertEqual(SOKKURI_ID, 346005)

    def test_behavior_fixture_position_is_within_sight(self):
        distance = min((BEHAVIOR_POSITION[0] - x) ** 2 + (BEHAVIOR_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, 150.0, 'Sokkuri must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(all(result['checks'].values()))
        self.assertGreater(result['motion_spread'], 5.0)

    def test_validate_rejects_static_or_unbound_log(self):
        stale = GOOD_LOG.replace('P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0', '')
        stale = stale.replace('P2_SOKKURI_POS generator=346005 state=moveground clip=run1 phase=0.55 '
                              'x=-90.00 z=1848.00', '')
        stale = stale.replace('P2_SOKKURI_POS generator=346005 state=moveground clip=run1 phase=0.90 '
                              'x=-78.00 z=1845.00', '')
        result = validate(stale, code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['identity'])
        self.assertFalse(result['checks']['autonomous_motion'])
        self.assertFalse(result['checks']['animation'])

    def test_validate_flags_extinction(self):
        result = validate(GOOD_LOG + '\nGAMEEND_PikminExtinction', code=0)
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
