"""Unit tests for the Tadpole source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_tadpole_behavior import (
    SIGHT, SQUAD_X, SQUAD_Z, TADPOLE_ID, TADPOLE_POS, normalize_pose_names, validate)

GOOD_LOG = '\n'.join([
    'P2_TADPOLE_BIND generator=374002 source_id=27 visual_only=0',
    'P2_BATCH3_BIND generator=374002 key=aquatic|Tadpole visual_only=0 native_fsm=implemented',
    'P2_ENEMY_READY species=Tadpole native_family=Otama generator=374002 x=-120.0 y=30.0 '
    'z=1850.0 health=200.0 max_health=200.0 behavior=native source_FSM=implemented '
    'water=absent attack=none',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_TADPOLE_STATE generator=374002 state=wait',
    'P2_TADPOLE_STATE generator=374002 state=amaze',
    'P2_TADPOLE_STATE generator=374002 state=escape',
    'P2_TADPOLE_STATE generator=374002 state=leap',
    'P2_TADPOLE_LEAP generator=374002 state=leap frame=14',
    'P2_TADPOLE_POS generator=374002 state=wait clip=wait1 phase=0.50 x=-120.00 y=30.00 z=1850.00',
    'P2_TADPOLE_POS generator=374002 state=leap clip=piti1 phase=0.40 x=-120.00 y=45.00 z=1830.00',
])


class TadpoleBehaviorTests(unittest.TestCase):
    def test_identity_and_squad_distance(self):
        self.assertEqual(TADPOLE_ID, 374002)
        self.assertEqual(TADPOLE_POS, (-120.0, 30.0, 1850.0))
        distance = min((TADPOLE_POS[0] - x) ** 2 + (TADPOLE_POS[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, SIGHT, 'Tadpole must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['leap'])
        self.assertTrue(result['checks']['idle_or_move'])
        self.assertTrue(result['checks']['batch3_bind'])
        self.assertGreater(result['motion_spread'], 5.0)

    def test_missing_leap_fails(self):
        no_leap = GOOD_LOG.replace('P2_TADPOLE_STATE generator=374002 state=leap', '')
        no_leap = no_leap.replace('P2_TADPOLE_POS generator=374002 state=leap clip=piti1 '
                                  'phase=0.40 x=-120.00 y=45.00 z=1830.00', '')
        result = validate(no_leap, code=0)
        self.assertFalse(result['checks']['leap'])
        self.assertFalse(result['checks']['autonomous_motion'])
        self.assertFalse(result['passed'])

    def test_pose_name_normalization_copies_misindexed_pose(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            room = run / 'assets/dataDir/courses/pikmin2room'
            room.mkdir(parents=True)
            (run / 'p2-aquatic-bank.txt').write_text(
                'P2_AQUATIC_BANK_1\n'
                'species Tadpole 27\n'
                'clip Tadpole wait1 30 5:0,24:1 poses 2 converted\n')
            (room / 'aquatic_Tadpole_wait1_01.mod').write_bytes(b'pose')
            copied = normalize_pose_names(run)
            self.assertTrue((room / 'aquatic_Tadpole_wait1_00.mod').is_file())
            self.assertEqual(len(copied), 1)
            self.assertEqual(copied[0]['source'], 'aquatic_Tadpole_wait1_01.mod')

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
