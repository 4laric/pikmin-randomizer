import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_waterwraith_assets import (CLIPS, EXPECTED_EVENTS,
                                                     DISC_PARMS, PROPER_PARM_DEFAULTS,
                                                     STATE_IDS, TEXT, profile, extract)


def blocks_for(species, override=None):
    general = dict(DISC_PARMS[species]['general'])
    proper = dict(DISC_PARMS[species]['proper'])
    blocks = [{'s000': 0.5}, general, proper]
    if override:
        override(blocks)
    return blocks


def rows_for(species):
    return [{'file': name + '.bca', 'events': [list(e) for e in EXPECTED_EVENTS[species][name]]}
            for name in CLIPS[species]]


class WaterwraithAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        for species, identity in (('Tyre', 98), ('BlackMan', 99)):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(len(result['anim_id_by_clip']), len(CLIPS[species]))
            self.assertEqual(result['proper_header_defaults'], PROPER_PARM_DEFAULTS[species])

    def test_retail_values_match_audit_contract(self):
        for species in ('Tyre', 'BlackMan'):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
            # disc values stay distinct from header build-time defaults
            for key in DISC_PARMS[species]['proper']:
                self.assertIn(key, PROPER_PARM_DEFAULTS[species])
        self.assertNotEqual(PROPER_PARM_DEFAULTS['Tyre']['fp01'],
                            DISC_PARMS['Tyre']['proper']['fp01'])
        self.assertNotEqual(PROPER_PARM_DEFAULTS['BlackMan']['fp02'],
                            DISC_PARMS['BlackMan']['proper']['fp02'])

    def test_keys_defaulted_from_header_recorded(self):
        self.assertEqual(profile('Tyre', blocks_for('Tyre'),
                                 rows_for('Tyre'))['proper_keys_defaulted_from_header'], [])
        result = profile('BlackMan', blocks_for('BlackMan'), rows_for('BlackMan'))
        self.assertEqual(result['proper_keys_defaulted_from_header'],
                         ['ip03', 'ip04', 'ip05', 'ip06'])
        for key in result['proper_keys_defaulted_from_header']:
            self.assertEqual(PROPER_PARM_DEFAULTS['BlackMan'][key], 200)
            self.assertNotIn(key, result['proper_retail'])

    def test_reject_disc_parameter_drift(self):
        def tamper_general(blocks):
            blocks[1]['fp00'] = 999.0  # BlackMan health drift
        with self.assertRaises(ValueError):
            profile('BlackMan', blocks_for('BlackMan', tamper_general), rows_for('BlackMan'))

        def tamper_proper(blocks):
            blocks[2]['fp02'] = 10.0  # header escape speed instead of disc 250
        with self.assertRaises(ValueError):
            profile('BlackMan', blocks_for('BlackMan', tamper_proper), rows_for('BlackMan'))

        def tamper_tyre(blocks):
            blocks[2]['fp01'] = 0.5  # header rotation speed instead of disc 25
        with self.assertRaises(ValueError):
            profile('Tyre', blocks_for('Tyre', tamper_tyre), rows_for('Tyre'))

    def test_reject_unexpected_general_and_proper_keys(self):
        def tamper_general(blocks):
            blocks[1]['fp07'] = 1.0  # fp07 is not declared in EnemyParmsBase
        with self.assertRaises(ValueError):
            profile('Tyre', blocks_for('Tyre', tamper_general), rows_for('Tyre'))

        def tamper_proper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('BlackMan', blocks_for('BlackMan', tamper_proper), rows_for('BlackMan'))

        def tamper_general_unknown(blocks):
            blocks[1]['ip99'] = 1.0
        with self.assertRaises(ValueError):
            profile('BlackMan', blocks_for('BlackMan', tamper_general_unknown), rows_for('BlackMan'))

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('BlackMan')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('BlackMan', blocks_for('BlackMan'), rows)

        rows = rows_for('Tyre')
        rows[0]['events'] = [[1, 2]]
        with self.assertRaises(ValueError):
            profile('Tyre', blocks_for('Tyre'), rows)

        rows = rows_for('BlackMan')
        rows[8]['events'][2][1] = 9  # kagebozu_run third event drift
        with self.assertRaises(ValueError):
            profile('BlackMan', blocks_for('BlackMan'), rows)

    def test_event_contract_matches_audit(self):
        self.assertEqual(EXPECTED_EVENTS['BlackMan']['kagebozu_dead'],
                         [[14, 2], [65, 3], [102, 4], [125, 5]])
        self.assertEqual(EXPECTED_EVENTS['BlackMan']['kagebozu_run'],
                         [[0, 0], [1, 2], [5, 3], [11, 1]])
        self.assertEqual(EXPECTED_EVENTS['BlackMan']['kagebozu_land'],
                         [[0, 0], [0, 1], [4, 2]])
        self.assertEqual(EXPECTED_EVENTS['BlackMan']['kagebozu_through'], [[6, 0], [6, 1]])
        self.assertEqual(EXPECTED_EVENTS['BlackMan']['kagebozu_recover'],
                         [[14, 2], [41, 3], [43, 4], [50, 5]])
        self.assertEqual(EXPECTED_EVENTS['Tyre']['tyre_move'], [])
        self.assertEqual(STATE_IDS['Tyre']['dead'], 3)
        self.assertEqual(STATE_IDS['BlackMan']['tired'], 8)
        self.assertEqual(STATE_IDS['BlackMan']['recover'], 7)
        self.assertEqual(len(CLIPS['Tyre']), 2)
        self.assertEqual(len(CLIPS['BlackMan']), 14)

    def test_profile_text_explicit_nonclaims(self):
        self.assertIn('native_ready false', TEXT)
        self.assertIn('gameplay_events_executed false', TEXT)
        self.assertIn('btk_playback false', TEXT)

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
            with patch('experimental.pikmin2_waterwraith_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_waterwraith_assets.subprocess.check_output',
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
