import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_ground_inverts_assets import (CLIPS, EXPECTED_EVENTS,
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


class GroundInvertAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        for species, identity in (('Armor', 15), ('ElecBug', 28), ('Imomushi', 65),
                                  ('TamagoMushi', 68), ('Sokkuri', 79), ('Hana', 84)):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(len(result['anim_id_by_clip']), len(CLIPS[species]))
            self.assertEqual(result['proper_header_defaults'], PROPER_PARM_DEFAULTS[species])

    def test_retail_values_match_audit_contract(self):
        for species in ('Armor', 'ElecBug', 'Imomushi', 'TamagoMushi', 'Sokkuri', 'Hana'):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
            # disc values stay distinct from header build-time defaults
            for key, retail in DISC_PARMS[species]['proper'].items():
                header = PROPER_PARM_DEFAULTS[species].get(key)
                if header is not None:
                    self.assertEqual(result['proper_header_defaults'][key], header)

    def test_keys_defaulted_from_header_recorded(self):
        result = profile('Armor', blocks_for('Armor'), rows_for('Armor'))
        self.assertEqual(result['proper_keys_defaulted_from_header'], ['fp12'])
        self.assertEqual(PROPER_PARM_DEFAULTS['Armor']['fp12'], 100.0)
        result = profile('Hana', blocks_for('Hana'), rows_for('Hana'))
        self.assertEqual(result['proper_keys_defaulted_from_header'], ['fp03'])
        self.assertEqual(PROPER_PARM_DEFAULTS['Hana']['fp03'], 400.0)
        for species in ('ElecBug', 'Imomushi', 'TamagoMushi', 'Sokkuri'):
            self.assertEqual(profile(species, blocks_for(species),
                                     rows_for(species))['proper_keys_defaulted_from_header'], [])

    def test_reject_disc_parameter_drift(self):
        def tamper(blocks):
            blocks[1]['fp00'] = 999.0  # Armor health drift
        with self.assertRaises(ValueError):
            profile('Armor', blocks_for('Armor', tamper), rows_for('Armor'))

        def tamper_proper(blocks):
            blocks[2]['fp11'] = 1.5  # disc 1.0 for Armor attack loop
        with self.assertRaises(ValueError):
            profile('Armor', blocks_for('Armor', tamper_proper), rows_for('Armor'))

        def tamper_hana(blocks):
            blocks[2]['fp02'] = 300.0  # header poison default instead of disc 2500
        with self.assertRaises(ValueError):
            profile('Hana', blocks_for('Hana', tamper_hana), rows_for('Hana'))

    def test_reject_unexpected_proper_keys(self):
        def tamper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('Imomushi', blocks_for('Imomushi', tamper), rows_for('Imomushi'))

        def tamper_disc_wide(blocks):
            blocks[1]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('Sokkuri', blocks_for('Sokkuri', tamper_disc_wide), rows_for('Sokkuri'))

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('ElecBug')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('ElecBug', blocks_for('ElecBug'), rows)
        rows = rows_for('Sokkuri')
        rows[0]['events'] = [[1, 2]]
        with self.assertRaises(ValueError):
            profile('Sokkuri', blocks_for('Sokkuri'), rows)
        rows = rows_for('Hana')
        rows[8]['events'][1][1] = 9  # type1 second event drift
        with self.assertRaises(ValueError):
            profile('Hana', blocks_for('Hana'), rows)

    def test_event_contract_matches_audit(self):
        self.assertEqual(EXPECTED_EVENTS['Armor']['attack2'], [[12, 0], [14, 1], [18, 2], [22, 3]])
        self.assertEqual(EXPECTED_EVENTS['ElecBug']['discharge'], [[8, 2], [10, 0], [17, 1]])
        self.assertEqual(EXPECTED_EVENTS['TamagoMushi']['set'], [[2, 2]])
        self.assertEqual(EXPECTED_EVENTS['Sokkuri']['flick1'], [[14, 2], [18, 3], [40, 4]])
        self.assertEqual(EXPECTED_EVENTS['Hana']['type1'],
                         [[27, 2], [30, 0], [100, 1], [103, 3], [120, 4]])
        self.assertEqual(STATE_IDS['Armor']['attack2'], 10)
        self.assertEqual(STATE_IDS['ElecBug']['reverse'], 8)
        self.assertEqual(STATE_IDS['Imomushi']['climb'], 10)
        self.assertEqual(STATE_IDS['TamagoMushi']['hide'], 3)
        self.assertEqual(STATE_IDS['Sokkuri']['movewater'], 7)
        self.assertEqual(STATE_IDS['Hana']['sleep'], 7)
        self.assertEqual([len(CLIPS[s]) for s in CLIPS], [10, 8, 9, 6, 9, 9])

    def test_disc_parms_cover_tamagomushi_grouping(self):
        self.assertEqual(len(DISC_PARMS['TamagoMushi']['proper']), 7)
        self.assertEqual(DISC_PARMS['TamagoMushi']['proper']['ip04'], 90)
        self.assertEqual(DISC_PARMS['Hana']['proper'], {'fp01': 30.0, 'fp02': 2500.0})

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
            with patch('experimental.pikmin2_ground_inverts_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_ground_inverts_assets.subprocess.check_output',
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