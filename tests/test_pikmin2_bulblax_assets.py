import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_bulblax_assets import (CLIPS, EXPECTED_EVENTS, DISC_PARMS,
                                                 PROPER_PARM_DEFAULTS, CARCASS,
                                                 STATE_IDS, TEXT, corpse, profile, extract)


def blocks_for(species, override=None):
    general = dict(DISC_PARMS[species]['general'])
    proper = dict(PROPER_PARM_DEFAULTS[species])
    proper.update(DISC_PARMS[species]['proper'])
    blocks = [{'s000': 0.5}, general, proper]
    if override:
        override(blocks)
    return blocks


def rows_for(species):
    return [{'file': name + '.bca', 'events': [list(e) for e in EXPECTED_EVENTS[species][name]]}
            for name in CLIPS[species]]


CORPSE_ENTRY = {'Queen': {'name': 'Queen', 'money': '15', 'min': '20', 'max': '30'},
                'KingChappy': {'name': 'KingChappy', 'money': '15', 'min': '20', 'max': '30'},
                'Baby': None}


class BulblaxAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        for species in ('Queen', 'Baby', 'KingChappy'):
            result = profile(species, blocks_for(species), rows_for(species), CORPSE_ENTRY[species])
            self.assertEqual(result['enemy_id'], {'Queen': 30, 'Baby': 31, 'KingChappy': 53}[species])
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(len(result['anim_id_by_clip']), len(CLIPS[species]))
            self.assertEqual(result['proper_header_defaults'], PROPER_PARM_DEFAULTS[species])
            if species == 'Baby':
                self.assertIsNone(result['corpse'])
            else:
                self.assertEqual(result['corpse'], {'money': 15, 'min': 20, 'max': 30})

    def test_retail_values_match_audit_contract(self):
        queen = profile('Queen', blocks_for('Queen'), rows_for('Queen'), CORPSE_ENTRY['Queen'])
        self.assertEqual(queen['proper_retail'], {'fp01': 3.5, 'fp02': 2.0, 'fp11': 3300.0, 'ip01': 50, 'ip02': 25})
        self.assertEqual(queen['proper_header_defaults']['fp01'], 10.0)  # kept distinct from disc
        baby = profile('Baby', blocks_for('Baby'), rows_for('Baby'), None)
        self.assertEqual(baby['proper_retail'], {'fp01': 300.0, 'fp11': 0.2})
        king = profile('KingChappy', blocks_for('KingChappy'), rows_for('KingChappy'), CORPSE_ENTRY['KingChappy'])
        self.assertEqual(king['proper_retail']['fp05'], 200.0)   # bomb damage
        self.assertEqual(king['proper_retail']['ip03'], 180)     # stun frames
        self.assertEqual(king['proper_retail']['fp15'], 1.5)     # big scale
        self.assertEqual(king['proper_header_defaults']['ip03'], 10)

    def test_reject_disc_parameter_drift(self):
        def tamper(blocks):
            blocks[1]['fp00'] = 4999.0  # Queen health drift
        with self.assertRaises(ValueError):
            profile('Queen', blocks_for('Queen', tamper), rows_for('Queen'), CORPSE_ENTRY['Queen'])

        def tamper_proper(blocks):
            blocks[2]['fp11'] = 2500.0  # header default instead of disc 3300
        with self.assertRaises(ValueError):
            profile('Queen', blocks_for('Queen', tamper_proper), rows_for('Queen'), CORPSE_ENTRY['Queen'])

    def test_reject_unexpected_proper_keys(self):
        def tamper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('Baby', blocks_for('Baby', tamper), rows_for('Baby'), None)

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('Queen')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('Queen', blocks_for('Queen'), rows, CORPSE_ENTRY['Queen'])
        rows = rows_for('KingChappy')
        rows[0]['events'] = [[25, 2], [40, 3]]
        with self.assertRaises(ValueError):
            profile('KingChappy', blocks_for('KingChappy'), rows, CORPSE_ENTRY['KingChappy'])
        rows = rows_for('Baby')
        rows[3]['events'][1][1] = 9  # attack swallow event type drift
        with self.assertRaises(ValueError):
            profile('Baby', blocks_for('Baby'), rows, None)

    def test_carcass_contract(self):
        with self.assertRaises(ValueError):
            profile('Baby', blocks_for('Baby'), rows_for('Baby'), {'name': 'Baby', 'money': '1', 'min': '1', 'max': '1'})
        with self.assertRaises(ValueError):
            profile('Queen', blocks_for('Queen'), rows_for('Queen'), None)
        with self.assertRaises(ValueError):
            profile('Queen', blocks_for('Queen'), rows_for('Queen'),
                    {'name': 'Queen', 'money': '10', 'min': '20', 'max': '30'})

    def test_corpse_bounds(self):
        self.assertEqual(corpse({'money': '15', 'min': '20', 'max': '30'}), {'money': 15, 'min': 20, 'max': 30})
        for fields in ({'money': '-1', 'min': '20', 'max': '30'},
                       {'money': '15', 'min': '0', 'max': '30'},
                       {'money': '15', 'min': '31', 'max': '30'}):
            with self.assertRaises(ValueError):
                corpse(fields)

    def test_event_contract_matches_audit(self):
        self.assertEqual(EXPECTED_EVENTS['Queen']['sleep'], [[59, 0], [118, 1], [120, 2]])
        self.assertEqual(EXPECTED_EVENTS['Queen']['rolling_l'], [[20, 0], [67, 2], [69, 1]])
        self.assertEqual(EXPECTED_EVENTS['Queen']['born'], [[24, 2]])
        self.assertEqual(EXPECTED_EVENTS['KingChappy']['attack'],
                         [[25, 2], [40, 3], [70, 4], [86, 5], [92, 6]])
        self.assertEqual(EXPECTED_EVENTS['Baby']['attack'], [[10, 2], [30, 3]])
        self.assertEqual(EXPECTED_EVENTS['Baby']['move'], [[0, 0], [11, 1]])
        self.assertEqual(STATE_IDS['Queen'], {'dead': 0, 'sleep': 1, 'wait': 2, 'damage': 3,
                                              'flick': 4, 'rolling': 5, 'born': 6})
        self.assertEqual(STATE_IDS['KingChappy']['swallow'], 12)
        self.assertEqual(len(CLIPS['Queen']), 9)
        self.assertEqual(len(CLIPS['Baby']), 6)
        self.assertEqual(len(CLIPS['KingChappy']), 14)

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
            with patch('experimental.pikmin2_bulblax_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_bulblax_assets.subprocess.check_output', return_value='a' * 40):
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
