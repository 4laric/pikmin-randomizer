"""Unit tests for the SnakeCrow slice-2 natural-kill validator (#174)."""
import unittest

from experimental.pikmin2_snakejoint_slice2 import validate

GOOD_LOG = '\n'.join([
    'P2_SNAKEJOINT_BIND generator=376001 species=SnakeCrow source_id=34 visual_only=0',
    'P2_SNAKEJOINT_JOINTS generator=376001 species=SnakeCrow source_joints=6 host_joints=1 '
    'pose=clip_override',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_SNAKEJOINT_STATE generator=376001 state=stay',
    'P2_SNAKEJOINT_DAMAGE_REJECTED generator=376001 state=stay',
    'P2_SNAKEJOINT_STATE generator=376001 state=appear1',
    'P2_SNAKEJOINT_DAMAGE_ACCEPTED generator=376001 state=appear1',
    'P2_SNAKEJOINT_BITE generator=376001 frame=34 pikmin=1',
    'P2_SNAKEJOINT_DEAD generator=376001 source_id=34 health=0',
    'P2_BATCH3_DRAW corpse=1 key=snagret|SnakeCrow clip=dead',
])


class SnakeJointSlice2Tests(unittest.TestCase):
    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['rejected_buried'])
        self.assertTrue(result['checks']['accepted_emerged'])
        self.assertTrue(result['checks']['joints'])
        self.assertTrue(result['checks']['natural_death'])
        self.assertTrue(result['checks']['corpse'])
        # Cleanup forget is informational in the single-floor fixture.
        self.assertFalse(result['checks']['cleanup'])

    def test_missing_corpse_fails(self):
        stripped = GOOD_LOG.replace(
            'P2_BATCH3_DRAW corpse=1 key=snagret|SnakeCrow clip=dead', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['checks']['corpse'])
        self.assertFalse(result['passed'])

    def test_missing_joints_fails(self):
        stripped = GOOD_LOG.replace(
            'P2_SNAKEJOINT_JOINTS generator=376001 species=SnakeCrow source_joints=6 '
            'host_joints=1 pose=clip_override\n', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['checks']['joints'])
        self.assertFalse(result['passed'])

    def test_missing_rejected_fails(self):
        stripped = GOOD_LOG.replace(
            'P2_SNAKEJOINT_DAMAGE_REJECTED generator=376001 state=stay\n', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['checks']['rejected_buried'])
        self.assertFalse(result['passed'])

    def test_accept_outside_emerged_fails(self):
        outside = GOOD_LOG.replace(
            'P2_SNAKEJOINT_DAMAGE_ACCEPTED generator=376001 state=appear1',
            'P2_SNAKEJOINT_DAMAGE_ACCEPTED generator=376001 state=stay')
        result = validate(outside, code=0)
        self.assertFalse(result['checks']['accepted_emerged'])

    def test_rejected_outside_buried_fails(self):
        bad = GOOD_LOG.replace(
            'P2_SNAKEJOINT_DAMAGE_REJECTED generator=376001 state=stay',
            'P2_SNAKEJOINT_DAMAGE_REJECTED generator=376001 state=attack')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['rejected_buried'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
