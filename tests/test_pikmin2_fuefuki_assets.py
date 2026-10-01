import unittest
from unittest.mock import patch

import experimental.pikmin2_fuefuki_assets as assets
from experimental.pikmin2_fuefuki_assets import (CLIPS, ENEMY_ID, GENERAL_RETAIL, LOOPS,
                                                 MGR_ROWS, PROPER_RETAIL, SPECIES,
                                                 TOLERANCES, extract, material_probe,
                                                 profile)


def blocks_for(override=None):
    general = dict(GENERAL_RETAIL)
    proper = dict(PROPER_RETAIL)
    blocks = [{'s000': 0.5, 's001': 0.5}, general, proper]
    if override:
        override(blocks)
    return blocks


def rows_for():
    return [{'file': stem + '.bca', 'events': [list(e) for e in events]}
            for stem, events in MGR_ROWS]


class FuefukiAssetsTests(unittest.TestCase):
    def test_profile_validates_audited_contract(self):
        result = profile(blocks_for(), rows_for())
        self.assertEqual(result['enemy_id'], 41)
        self.assertEqual(result['proper_retail'], PROPER_RETAIL)
        self.assertEqual(result['general_retail'], GENERAL_RETAIL)
        self.assertEqual(len(result['parameter_blocks']), 3)

    def test_reject_general_parameter_drift(self):
        def tamper(blocks):
            blocks[1]['fp22'] = 999.0  # whistle radius base
        with self.assertRaises(ValueError):
            profile(blocks_for(tamper), rows_for())

    def test_reject_proper_parameter_drift(self):
        def tamper(blocks):
            blocks[2]['fp01'] = 1.0  # max ground time
        with self.assertRaises(ValueError):
            profile(blocks_for(tamper), rows_for())

    def test_reject_registration_drift(self):
        # The docs transcription gives carry (0,0); the raw disc has (10,0).
        rows = rows_for()
        rows[9]['events'] = [[0, 0], [29, 1]]
        with self.assertRaises(ValueError):
            profile(blocks_for(), rows)

    def test_reject_missing_parameter_block(self):
        with self.assertRaises(ValueError):
            profile([{'s000': 0.5}], rows_for())

    def test_constants(self):
        self.assertEqual(SPECIES, 'Fuefuki')
        self.assertEqual(ENEMY_ID, 41)
        self.assertEqual(len(CLIPS), 10)
        self.assertEqual(CLIPS[0], 'dead')
        self.assertEqual(CLIPS[-1], 'carry')
        self.assertEqual(TOLERANCES, {'billboard': 'static'})
        self.assertIn(2, LOOPS)  # repeat

    def test_material_probe_records_strict_rejection(self):
        rows = [{'file': 'dead.bca', 'events': []}]
        with patch.object(assets, 'bca_pose', return_value=(60, [])), \
             patch.object(assets, 'draw_matrices', return_value=[]), \
             patch.object(assets, 'decode',
                          side_effect=ValueError('Only single-stage materials supported')):
            probe = material_probe(b'model', {}, [], {'dead.bca': b'x' * 72}, rows)
        self.assertFalse(probe['strict_ok'])
        self.assertEqual(probe['clip'], 'dead')
        self.assertIn('single-stage', probe['reason'])

    def test_material_probe_accepts_strict(self):
        rows = [{'file': 'wait.bca', 'events': []}]
        with patch.object(assets, 'bca_pose', return_value=(30, [])), \
             patch.object(assets, 'draw_matrices', return_value=[]), \
             patch.object(assets, 'decode', return_value=(None, None, [None], [None])):
            probe = material_probe(b'model', {}, [], {'wait.bca': b'x' * 72}, rows)
        self.assertTrue(probe['strict_ok'])
        self.assertEqual(probe['clip'], 'wait')

    def test_reject_invalid_pose_limit(self):
        with self.assertRaises(ValueError):
            extract(None, None, 1)
        with self.assertRaises(ValueError):
            extract(None, None, 13)


if __name__ == '__main__':
    unittest.main()
