import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_snagret_assets import (
    BASE_CLASSIFICATION, CLIPS, DISC_PARMS, EXPECTED_EVENTS, GENERAL_DEFAULTS,
    PROPER_PARM_DEFAULTS, SHARED_BASE, SPECIES, STATE_IDS, TEXT, animation_rows,
    extract, profile)


def blocks_for(species, override=None):
    general = dict(DISC_PARMS[species]['general'])
    proper = dict(DISC_PARMS[species]['proper'])
    blocks = [{'s000': 0.5}, general, proper]
    if override:
        override(blocks)
    return blocks


def rows_for(species):
    return [{'file': name + '.bca',
             'events': [list(event) for event in EXPECTED_EVENTS[species][name]]}
            for name in CLIPS[species]]


class SnagretAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        for species, identity in (('SnakeCrow', 34), ('SnakeWhole', 70),
                                  ('DangoMushi', 94)):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(len(result['anim_id_by_clip']), len(CLIPS[species]))
            self.assertEqual(result['proper_header_defaults'],
                             PROPER_PARM_DEFAULTS[species])
            self.assertEqual(result['role'], 'concrete spawnable boss')

    def test_retail_values_match_audit_contract(self):
        for species in SPECIES:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
            self.assertEqual(result['general_retail'], DISC_PARMS[species]['general'])

    def test_retail_and_header_defaults_stay_distinct(self):
        for species in SPECIES:
            result = profile(species, blocks_for(species), rows_for(species))
            for key, retail in DISC_PARMS[species]['general'].items():
                # general defaults are reported from the header, never flattened
                self.assertEqual(result['general_header_defaults'][key],
                                 GENERAL_DEFAULTS[key])
                self.assertEqual(result['general_retail'][key], retail)
            # known header/retail splits
            self.assertEqual(result['general_header_defaults']['fp00'], 100.0)
            self.assertEqual(result['general_header_defaults']['fp09'], 200.0)
            self.assertNotEqual(result['general_retail']['fp00'],
                                result['general_header_defaults']['fp00'])
        crow = profile('SnakeCrow', blocks_for('SnakeCrow'), rows_for('SnakeCrow'))
        self.assertEqual(crow['general_retail']['fp00'], 1500.0)
        self.assertEqual(crow['general_retail']['fp06'], 0.0)
        whole = profile('SnakeWhole', blocks_for('SnakeWhole'), rows_for('SnakeWhole'))
        self.assertEqual(whole['general_retail']['fp00'], 5000.0)
        self.assertEqual(whole['general_retail']['fp06'], 1000.0)
        dango = profile('DangoMushi', blocks_for('DangoMushi'), rows_for('DangoMushi'))
        self.assertEqual(dango['general_retail']['fp00'], 3000.0)
        self.assertEqual(dango['general_retail']['fp20'], 300.0)

    def test_keys_defaulted_from_header_recorded(self):
        for species in SPECIES:
            result = profile(species, blocks_for(species), rows_for(species))
            if species == 'DangoMushi':
                # the disc proper block stores fp01/fp02/fp03 only; fp10 is the
                # header mFlipTime default and is reported as defaulted.
                self.assertEqual(result['proper_keys_defaulted_from_header'],
                                 ['fp10'])
            else:
                self.assertEqual(result['proper_keys_defaulted_from_header'],
                                 [])
        # a declared-key omission that the disc actually carries is drift.
        def drop(bl):
            del bl[2]['fp31']
        with self.assertRaises(ValueError):
            profile('SnakeCrow', blocks_for('SnakeCrow', drop),
                    rows_for('SnakeCrow'))

        def drop_dango(bl):
            del bl[2]['fp02']
        with self.assertRaises(ValueError):
            profile('DangoMushi', blocks_for('DangoMushi', drop_dango),
                    rows_for('DangoMushi'))

    def test_shared_base_classification_is_explicit(self):
        self.assertEqual(SHARED_BASE,
                         {'SnakeCrow': 'SnakeJointMgr',
                          'SnakeWhole': 'SnakeJointMgr', 'DangoMushi': None})
        self.assertEqual(BASE_CLASSIFICATION['SnakeCrow']['base_class'],
                         'Game::SnakeJointMgr')
        self.assertEqual(BASE_CLASSIFICATION['SnakeWhole']['shared_with'],
                         ['SnakeCrow'])
        self.assertEqual(BASE_CLASSIFICATION['SnakeCrow']['shared_with'],
                         ['SnakeWhole'])
        self.assertIn('SnakeJointMgr',
                      BASE_CLASSIFICATION['SnakeWhole']['evidence'])
        dango = BASE_CLASSIFICATION['DangoMushi']
        self.assertIsNone(dango['base_class'])
        self.assertEqual(dango['shared_with'], [])
        self.assertIn('Segmented', dango['family'])
        self.assertIn('EnemyBlendAnimatorBase', dango['animator'])
        # profile exposes the same reclassification
        result = profile('DangoMushi', blocks_for('DangoMushi'),
                         rows_for('DangoMushi'))
        self.assertIsNone(result['base_class'])
        crow = profile('SnakeCrow', blocks_for('SnakeCrow'), rows_for('SnakeCrow'))
        self.assertEqual(crow['base_class'], 'Game::SnakeJointMgr')

    def test_reject_general_disc_parameter_drift(self):
        def tamper(blocks):
            blocks[1]['fp00'] = 999.0  # SnakeCrow retail life is 1500
        with self.assertRaises(ValueError):
            profile('SnakeCrow', blocks_for('SnakeCrow', tamper),
                    rows_for('SnakeCrow'))

        def tamper_dango(blocks):
            blocks[1]['fp20'] = 100.0  # DangoMushi retail ranged attack is 300
        with self.assertRaises(ValueError):
            profile('DangoMushi', blocks_for('DangoMushi', tamper_dango),
                    rows_for('DangoMushi'))

    def test_reject_unknown_general_and_proper_keys(self):
        def tamper_general(blocks):
            blocks[1]['fp07'] = 1.0  # fp07 is never declared
        with self.assertRaises(ValueError):
            profile('SnakeWhole', blocks_for('SnakeWhole', tamper_general),
                    rows_for('SnakeWhole'))

        def tamper_general_unknown(blocks):
            blocks[1]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('SnakeCrow', blocks_for('SnakeCrow', tamper_general_unknown),
                    rows_for('SnakeCrow'))

        def tamper_proper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('DangoMushi', blocks_for('DangoMushi', tamper_proper),
                    rows_for('DangoMushi'))

    def test_reject_proper_disc_parameter_drift(self):
        def tamper(blocks):
            blocks[2]['fp21'] = 100.0  # SnakeCrow disc poison damage is 200
        with self.assertRaises(ValueError):
            profile('SnakeCrow', blocks_for('SnakeCrow', tamper),
                    rows_for('SnakeCrow'))

        def tamper_dango(blocks):
            blocks[2]['fp03'] = 1.0  # DangoMushi disc max turn speed is 3.0
        with self.assertRaises(ValueError):
            profile('DangoMushi', blocks_for('DangoMushi', tamper_dango),
                    rows_for('DangoMushi'))

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('SnakeCrow')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('SnakeCrow', blocks_for('SnakeCrow'), rows)

        rows = rows_for('SnakeWhole')
        rows[CLIPS['SnakeWhole'].index('appear2')]['events'][3][1] = 9
        with self.assertRaises(ValueError):
            profile('SnakeWhole', blocks_for('SnakeWhole'), rows)

        rows = rows_for('DangoMushi')
        rows[CLIPS['DangoMushi'].index('type5' if 'type5' in CLIPS['DangoMushi']
                                       else 'carry')]['events'].append([7, 1000])
        with self.assertRaises(ValueError):
            profile('DangoMushi', blocks_for('DangoMushi'), rows)

    def test_event_contract_matches_source(self):
        self.assertEqual(EXPECTED_EVENTS['SnakeCrow']['dead'],
                         [[67, 2], [75, 2], [110, 5], [131, 3], [143, 4],
                          [149, 4]])
        self.assertEqual(EXPECTED_EVENTS['SnakeCrow']['wait1'],
                         [[0, 0], [49, 1]])
        self.assertEqual(EXPECTED_EVENTS['SnakeWhole']['run1'],
                         [[10, 0], [10, 2], [32, 3], [34, 1]])
        self.assertEqual(EXPECTED_EVENTS['DangoMushi']['attack'],
                         [[6, 2], [17, 3], [23, 4], [50, 0], [100, 1],
                          [118, 5]])
        self.assertEqual(EXPECTED_EVENTS['DangoMushi']['carry'],
                         [[10, 0], [29, 1]])
        # disc clip spellings, not the header enum aliases
        self.assertIn('hit_near', CLIPS['SnakeCrow'])
        self.assertIn('hit_far', CLIPS['SnakeCrow'])
        self.assertIn('attack_2', CLIPS['DangoMushi'])
        self.assertEqual(STATE_IDS['SnakeCrow']['struggle'], 8)
        self.assertEqual(STATE_IDS['SnakeWhole']['home'], 7)
        self.assertEqual(STATE_IDS['DangoMushi']['flick'], 8)
        self.assertEqual([len(CLIPS[s]) for s in CLIPS], [13, 14, 9])
        self.assertEqual(SPECIES, {'SnakeCrow': 34, 'SnakeWhole': 70,
                                   'DangoMushi': 94})

    def test_animation_rows_tolerates_missing_dango_brace(self):
        text = ('\t2 \t# number of animations\n'
                '# fly.bca\n{\n\tfly.bca \n\t13 2 \n\t30 3 \n\t-1 \n}\n'
                '# attack_2.bca\n\n\tattack_2.bca \n\t26 2 \n\t-1 \n}\n')
        rows = animation_rows(text)
        self.assertEqual([row['file'] for row in rows],
                         ['fly.bca', 'attack_2.bca'])
        self.assertEqual(rows[1]['events'], [[26, 2]])

    def test_profile_text_explicit_nonclaims(self):
        self.assertIn('native_ready false', TEXT)
        self.assertIn('gameplay_events_executed false', TEXT)
        self.assertIn('btk_playback false', TEXT)
        self.assertIn('shared_base SnakeCrow SnakeWhole SnakeJointMgr', TEXT)
        self.assertIn('dango_base EnemyBase EnemyBlendAnimatorBase standalone', TEXT)

    def test_refuse_overwrite_before_source_access(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'keep').write_text('unchanged')
            with self.assertRaises(ValueError):
                extract(root / 'absent.iso', root / 'absent-source', root)
            self.assertEqual((root / 'keep').read_text(), 'unchanged')

    def test_wrong_region_has_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            iso = root / 'source.iso'
            iso.write_bytes(b'GPVJ0100')
            with patch('experimental.pikmin2_snagret_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_snagret_assets.subprocess.check_output',
                       return_value='a' * 40):
                with self.assertRaises(ValueError):
                    extract(iso, root, root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_pose_limit_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for bad in (0, 1, 13, True, '6'):
                with self.assertRaises(ValueError):
                    extract(root / 'x.iso', root, root / f'out-{bad}', bad)


if __name__ == '__main__':
    unittest.main()
