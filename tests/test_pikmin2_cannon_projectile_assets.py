import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_cannon_projectile_assets import (
    CLIPS, EXPECTED_EVENTS, DISC_PARMS, PROPER_PARM_DEFAULTS, STATE_IDS, SPECIES,
    HELPER_ENTRIES, PROJECTILE_ENTRIES, SHIPPED_MOTION_ALIASES, TEXT,
    motion_member, profile, extract)


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


class CannonProjectileAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        for species, identity in (('Kabuto', 75), ('Rkabuto', 95), ('Fkabuto', 96),
                                  ('Rock', 19), ('Stone', 74), ('Bomb', 36),
                                  ('Egg', 37), ('FminiHoudai', 97)):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(len(result['anim_id_by_clip']), len(CLIPS[species]))
            self.assertEqual(result['proper_header_defaults'], PROPER_PARM_DEFAULTS[species])

    def test_retail_values_match_audit_contract(self):
        for species in ('Kabuto', 'Rkabuto', 'Fkabuto', 'Rock', 'Stone', 'Bomb',
                        'Egg', 'FminiHoudai'):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
            # disc values stay distinct from header build-time defaults
            for key, retail in DISC_PARMS[species]['proper'].items():
                header = PROPER_PARM_DEFAULTS[species].get(key)
                if header is not None:
                    self.assertEqual(result['proper_header_defaults'][key], header)

    def test_retail_vs_header_default_separation(self):
        self.assertEqual(PROPER_PARM_DEFAULTS['Bomb']['fp01'], 250.0)
        self.assertEqual(DISC_PARMS['Bomb']['proper']['fp01'], 500.0)
        self.assertNotEqual(PROPER_PARM_DEFAULTS['Bomb']['fp01'],
                            DISC_PARMS['Bomb']['proper']['fp01'])
        self.assertEqual(PROPER_PARM_DEFAULTS['Rock']['fp01'], 150.0)
        self.assertEqual(DISC_PARMS['Rock']['proper']['fp01'], 100.0)
        self.assertEqual(PROPER_PARM_DEFAULTS['FminiHoudai']['fp11'], 30.0)
        self.assertEqual(DISC_PARMS['FminiHoudai']['proper']['fp11'], 2.0)
        self.assertEqual(PROPER_PARM_DEFAULTS['Egg']['fp01'], 1.0)
        self.assertEqual(DISC_PARMS['Egg']['proper']['fp01'], 0.5)
        for species in ('Kabuto', 'Rkabuto', 'Fkabuto'):
            self.assertEqual(PROPER_PARM_DEFAULTS[species], {})
            self.assertEqual(DISC_PARMS[species]['proper'], {})

    def test_keys_defaulted_from_header_recorded(self):
        for species in ('Kabuto', 'Rkabuto', 'Fkabuto', 'Rock', 'Stone', 'Bomb',
                        'Egg', 'FminiHoudai'):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_keys_defaulted_from_header'], [])

    def test_reject_unexpected_general_keys(self):
        def tamper(blocks):
            blocks[1]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('Kabuto', blocks_for('Kabuto', tamper), rows_for('Kabuto'))
        with self.assertRaises(ValueError):
            profile('Bomb', blocks_for('Bomb', tamper), rows_for('Bomb'))

    def test_reject_unexpected_proper_keys(self):
        def tamper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('Bomb', blocks_for('Bomb', tamper), rows_for('Bomb'))

        def tamper_kabuto(blocks):
            blocks[2]['fp01'] = 1.0  # Kabuto family proper block is empty
        with self.assertRaises(ValueError):
            profile('Kabuto', blocks_for('Kabuto', tamper_kabuto), rows_for('Kabuto'))

    def test_reject_general_and_proper_disc_drift(self):
        def tamper_general(blocks):
            blocks[1]['fp00'] = 999.0  # Kabuto health drift
        with self.assertRaises(ValueError):
            profile('Kabuto', blocks_for('Kabuto', tamper_general), rows_for('Kabuto'))

        def tamper_fkabuto(blocks):
            blocks[1]['fp00'] = 850.0  # header-shared value, not Fkabuto disc 2000
        with self.assertRaises(ValueError):
            profile('Fkabuto', blocks_for('Fkabuto', tamper_fkabuto), rows_for('Fkabuto'))

        def tamper_proper(blocks):
            blocks[2]['fp01'] = 1.5  # disc 100.0 for the Rock rumble speed
        with self.assertRaises(ValueError):
            profile('Rock', blocks_for('Rock', tamper_proper), rows_for('Rock'))

        def tamper_bomb(blocks):
            blocks[2]['ip02'] = 50  # header default instead of disc 15
        with self.assertRaises(ValueError):
            profile('Bomb', blocks_for('Bomb', tamper_bomb), rows_for('Bomb'))

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('Kabuto')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('Kabuto', blocks_for('Kabuto'), rows)
        rows = rows_for('FminiHoudai')
        rows[3]['events'] = [[1, 2]]
        with self.assertRaises(ValueError):
            profile('FminiHoudai', blocks_for('FminiHoudai'), rows)
        rows = rows_for('Bomb')
        rows[1]['events'][1][1] = 9  # hit_loop loop-end drift
        with self.assertRaises(ValueError):
            profile('Bomb', blocks_for('Bomb'), rows)

    def test_event_contract_matches_audit(self):
        self.assertEqual(EXPECTED_EVENTS['Kabuto']['attack'], [[50, 2]])
        self.assertEqual(EXPECTED_EVENTS['Fkabuto']['K_attack'], [[55, 2]])
        self.assertEqual(EXPECTED_EVENTS['Rkabuto']['move'], [[15, 0], [44, 1]])
        self.assertEqual(EXPECTED_EVENTS['Rock']['run'], [[0, 0], [39, 1]])
        self.assertEqual(EXPECTED_EVENTS['Bomb']['hit_start'], [[10, 2]])
        self.assertEqual(EXPECTED_EVENTS['Bomb']['hit_loop'], [[0, 0], [7, 1]])
        self.assertEqual(EXPECTED_EVENTS['Egg']['damage1'], [])
        self.assertEqual(EXPECTED_EVENTS['FminiHoudai']['attack1'],
                         [[11, 2], [22, 3], [25, 4], [32, 5]])
        self.assertEqual(EXPECTED_EVENTS['FminiHoudai']['rebirth'], [[32, 2], [45, 3]])
        self.assertEqual(STATE_IDS['Kabuto']['fixhide'], 8)
        self.assertEqual(STATE_IDS['Rkabuto']['move'], 3)
        self.assertEqual(STATE_IDS['Rock']['dead'], 5)
        self.assertEqual(STATE_IDS['Bomb']['bomb'], 1)
        self.assertEqual(STATE_IDS['Egg']['wait'], 0)
        self.assertEqual(STATE_IDS['FminiHoudai']['walkpath'], 10)
        self.assertEqual([len(CLIPS[s]) for s in CLIPS], [14, 14, 14, 2, 2, 2, 1, 8])

    def test_shipped_motion_names_resolve(self):
        # enemyanimmgr.txt keeps the authored upper-case K_*.bca names, while
        # enemy/data/Kabuto/anim.szs packs the buried members lower-case.
        self.assertEqual(SHIPPED_MOTION_ALIASES['K_pivot.bca'], 'k_pivot.bca')
        self.assertEqual(SHIPPED_MOTION_ALIASES['K_hide.bca'], 'k_hide.bca')
        self.assertEqual(len(SHIPPED_MOTION_ALIASES), 7)
        motions = {name: b'x' for name in (
            'dead.bca', 'move.bca', 'flick.bca', 'attack.bca', 'pivot.bca',
            'wait.bca', 'k_pivot.bca', 'k_wait.bca', 'k_attack.bca',
            'k_flick.bca', 'k_dead.bca', 'k_appear.bca', 'k_hide.bca',
            'carry.bca')}
        self.assertEqual(motion_member(motions, 'K_pivot.bca'), 'k_pivot.bca')
        self.assertEqual(motion_member(motions, 'dead.bca'), 'dead.bca')
        with self.assertRaises(KeyError):
            motion_member(motions, 'K_missing.bca')
        with self.assertRaises(KeyError):
            motion_member({'foo.bca': b'x', 'FOO.BCA': b'x'}, 'FOO.bca')

    def test_helper_and_projectile_reclassification(self):
        self.assertEqual(HELPER_ENTRIES, ('Fkabuto', 'FminiHoudai'))
        self.assertEqual(PROJECTILE_ENTRIES, ('Rock', 'Stone', 'Bomb', 'Egg'))
        self.assertEqual(DISC_PARMS['Fkabuto']['general']['fp00'], 2000.0)
        self.assertEqual(DISC_PARMS['Kabuto']['general']['fp00'], 850.0)
        self.assertEqual(DISC_PARMS['Stone'], DISC_PARMS['Rock'])
        self.assertEqual(DISC_PARMS['FminiHoudai']['general']['fp00'], 700.0)
        self.assertEqual(DISC_PARMS['Bomb']['proper'],
                         {'fp01': 500.0, 'fp02': 50.0, 'ip01': 1, 'ip02': 15})
        self.assertEqual(DISC_PARMS['Egg']['proper']['fp03'], 0.05)

    def test_profile_text_explicit_nonclaims(self):
        self.assertIn('native_ready false', TEXT)
        self.assertIn('gameplay_events_executed false', TEXT)
        self.assertIn('btk_playback false', TEXT)
        self.assertIn('P2_CANNON_PROJECTILE_1', TEXT)

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
            with patch('experimental.pikmin2_cannon_projectile_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_cannon_projectile_assets.subprocess.check_output',
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
