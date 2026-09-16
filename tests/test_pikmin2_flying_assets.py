import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_flying_assets import (CLIPS, DISC_PARMS, EXPECTED_EVENTS,
                                                HELPER_SPECIES, PROPER_PARM_DEFAULTS,
                                                SHIJIMICHOU_GROUP_COUNT, SPECIES,
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


class FlyingRemainderAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        for species, identity, common in (('Mar', 29, 'Puffy Blowhog'),
                                          ('Hanachirashi', 55, 'Withering Blowhog'),
                                          ('ShijimiChou', 77, 'Unmarked Spectralids')):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['common_name'], common)
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(len(result['anim_id_by_clip']), len(CLIPS[species]))
            self.assertEqual(result['proper_header_defaults'], PROPER_PARM_DEFAULTS[species])

    def test_retail_values_match_audit_contract(self):
        for species in SPECIES:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
            # disc values stay distinct from header build-time defaults
            for key, retail in DISC_PARMS[species]['proper'].items():
                header = PROPER_PARM_DEFAULTS[species].get(key)
                if header is not None:
                    self.assertEqual(result['proper_header_defaults'][key], header)
        # header defaults remain reported even where disc differs
        result = profile('Mar', blocks_for('Mar'), rows_for('Mar'))
        self.assertEqual(result['proper_header_defaults']['fp01'], 90.0)
        self.assertEqual(result['proper_retail']['fp01'], 80.0)
        result = profile('ShijimiChou', blocks_for('ShijimiChou'), rows_for('ShijimiChou'))
        self.assertEqual(result['proper_header_defaults']['fp01'], 300.0)
        self.assertEqual(result['proper_retail']['fp01'], 250.0)

    def test_reject_general_key_drift(self):
        def tamper(blocks):
            blocks[1]['fp07'] = 1.0  # fp07 is not declared in EnemyParmsBase
        with self.assertRaises(ValueError):
            profile('Mar', blocks_for('Mar', tamper), rows_for('Mar'))

        def tamper_unknown(blocks):
            blocks[1]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('ShijimiChou', blocks_for('ShijimiChou', tamper_unknown),
                    rows_for('ShijimiChou'))

    def test_reject_proper_key_drift(self):
        def tamper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('Hanachirashi', blocks_for('Hanachirashi', tamper),
                    rows_for('Hanachirashi'))

    def test_reject_disc_parameter_drift(self):
        def tamper_general(blocks):
            blocks[1]['fp00'] = 999.0  # Mar health drift
        with self.assertRaises(ValueError):
            profile('Mar', blocks_for('Mar', tamper_general), rows_for('Mar'))

        def tamper_proper(blocks):
            blocks[2]['fp01'] = 90.0  # header default instead of disc 80
        with self.assertRaises(ValueError):
            profile('Mar', blocks_for('Mar', tamper_proper), rows_for('Mar'))

        def tamper_shijimi(blocks):
            blocks[2]['fp02'] = 1.0  # header nectar rate instead of disc 0.2
        with self.assertRaises(ValueError):
            profile('ShijimiChou', blocks_for('ShijimiChou', tamper_shijimi),
                    rows_for('ShijimiChou'))

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('Mar')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('Mar', blocks_for('Mar'), rows)
        rows = rows_for('ShijimiChou')
        rows[1]['events'] = [[3, 2]]
        with self.assertRaises(ValueError):
            profile('ShijimiChou', blocks_for('ShijimiChou'), rows)
        rows = rows_for('Hanachirashi')
        rows[3]['events'][0][0] = 30  # Hanachirashi flick frame drift from 25
        with self.assertRaises(ValueError):
            profile('Hanachirashi', blocks_for('Hanachirashi'), rows)

    def test_event_contract_matches_audit(self):
        self.assertEqual(EXPECTED_EVENTS['Mar']['damage'], [[15, 2]])
        self.assertEqual(EXPECTED_EVENTS['Mar']['wait2'], [[0, 0], [39, 1]])
        self.assertEqual(EXPECTED_EVENTS['Mar']['type2'], [[5, 0], [19, 1]])
        self.assertEqual(EXPECTED_EVENTS['Mar']['attack'], [[50, 2]])
        self.assertEqual(EXPECTED_EVENTS['Hanachirashi']['flick'], [[25, 2]])
        self.assertEqual(EXPECTED_EVENTS['Hanachirashi']['laugh'], [])
        self.assertEqual(EXPECTED_EVENTS['ShijimiChou']['carry'], [[10, 0], [29, 1]])
        self.assertEqual(EXPECTED_EVENTS['ShijimiChou']['move'], [[0, 0], [7, 1]])
        self.assertEqual(STATE_IDS['Mar']['groundflick'], 11)
        self.assertEqual(STATE_IDS['Hanachirashi']['laugh'], 12)
        self.assertEqual(STATE_IDS['ShijimiChou']['rest'], 5)
        self.assertEqual([len(CLIPS[s]) for s in CLIPS], [10, 11, 3])

    def test_shijimi_helper_classification(self):
        self.assertEqual(HELPER_SPECIES, ('ShijimiChou',))
        self.assertEqual(SHIJIMICHOU_GROUP_COUNT, 25)
        self.assertTrue(profile('ShijimiChou', blocks_for('ShijimiChou'),
                                rows_for('ShijimiChou'))['helper_only'])
        self.assertFalse(profile('Mar', blocks_for('Mar'), rows_for('Mar'))['helper_only'])
        self.assertFalse(profile('Hanachirashi', blocks_for('Hanachirashi'),
                                 rows_for('Hanachirashi'))['helper_only'])

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
            with patch('experimental.pikmin2_flying_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_flying_assets.subprocess.check_output',
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
