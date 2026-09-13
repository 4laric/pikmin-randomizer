import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import experimental.pikmin2_aquatic_assets as aquatic
from experimental.pikmin2_aquatic_assets import (ANIM_IDS, CLIPS, DISC_PARMS,
                                                 EXPECTED_EVENTS, LIMITATIONS,
                                                 MGR_ROWS, PROPER_PARM_DEFAULTS,
                                                 SPECIES, STATE_IDS, TEXT,
                                                 UNREGISTERED, anim_mgr_rows,
                                                 extract, profile)


def blocks_for(species, override=None):
    general = dict(DISC_PARMS[species]['general'])
    proper = dict(PROPER_PARM_DEFAULTS[species])
    proper.update(DISC_PARMS[species]['proper'])
    blocks = [{'s000': 0.5}, general, proper]
    if override:
        override(blocks)
    return blocks


def rows_for(species, override=None):
    rows = [{'file': stem + '.bca', 'events': [list(e) for e in events]}
            for stem, events in MGR_ROWS[species]]
    if override:
        override(rows)
    return rows


def mgr_text(species):
    blocks = []
    for stem, events in MGR_ROWS[species]:
        tokens = [stem, stem + '.bca'] + [str(x) for pair in events for x in pair] + ['-1']
        blocks.append('{ ' + ' '.join(tokens) + ' }')
    return str(len(blocks)) + '\n' + '\n'.join(blocks)


class AquaticAssetsTests(unittest.TestCase):
    def test_species_identity(self):
        self.assertEqual(SPECIES, {'Catfish': 26, 'Tadpole': 27,
                                   'Jigumo': 63, 'UmiMushi': 71})

    def test_species_profiles_validate(self):
        for species, identity in SPECIES.items():
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(result['anim_id_by_clip'], ANIM_IDS[species])
            self.assertEqual(result['proper_header_defaults'], PROPER_PARM_DEFAULTS[species])
            self.assertEqual(len(result['anim_id_by_clip']), len(ANIM_IDS[species]))

    def test_retail_values_match_audit_contract(self):
        for species in SPECIES:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
            self.assertEqual(result['proper_retail'], result['parameter_blocks'][2])

    def test_disc_parms_cover_audit_facts(self):
        self.assertEqual(DISC_PARMS['Catfish']['general']['fp00'], 200.0)
        self.assertEqual(DISC_PARMS['Catfish']['general']['fp09'], 280.0)
        self.assertEqual(DISC_PARMS['Catfish']['proper']['fp02'], 300.0)
        self.assertEqual(DISC_PARMS['Tadpole']['general']['fp06'], 180.0)
        self.assertEqual(DISC_PARMS['Tadpole']['general']['fp24'], 0.0)
        self.assertEqual(DISC_PARMS['Jigumo']['general']['fp00'], 500.0)
        self.assertEqual(DISC_PARMS['Jigumo']['proper']['fp01'], 75.0)
        self.assertEqual(DISC_PARMS['Jigumo']['proper']['fp02'], 30.0)
        self.assertEqual(DISC_PARMS['UmiMushi']['general']['fp00'], 1500.0)
        self.assertEqual(DISC_PARMS['UmiMushi']['general']['fp12'], 700.0)
        self.assertEqual(DISC_PARMS['UmiMushi']['general']['fp22'], 170.0)
        self.assertEqual(DISC_PARMS['UmiMushi']['proper']['fp01'], 0.03)
        self.assertEqual(DISC_PARMS['UmiMushi']['proper']['fp12'], 800.0)

    def test_reject_unknown_species_and_block_count(self):
        with self.assertRaises(ValueError):
            profile('Namazu', blocks_for('Catfish'), rows_for('Catfish'))
        with self.assertRaises(ValueError):
            profile('Catfish', blocks_for('Catfish')[:2], rows_for('Catfish'))

    def test_reject_proper_key_drift(self):
        def add(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('UmiMushi', blocks_for('UmiMushi', add), rows_for('UmiMushi'))

        def remove(blocks):
            blocks[2].pop('fp03')
        with self.assertRaises(ValueError):
            profile('Catfish', blocks_for('Catfish', remove), rows_for('Catfish'))

    def test_reject_disc_parameter_drift(self):
        def tamper_general(blocks):
            blocks[1]['fp00'] = 999.0  # Catfish health drift
        with self.assertRaises(ValueError):
            profile('Catfish', blocks_for('Catfish', tamper_general), rows_for('Catfish'))

        def tamper_proper(blocks):
            blocks[2]['fp02'] = 30.0  # header default instead of disc 300
        with self.assertRaises(ValueError):
            profile('Catfish', blocks_for('Catfish', tamper_proper), rows_for('Catfish'))

        def tamper_umimushi(blocks):
            blocks[2]['fp12'] = 1000.0  # header blind health instead of disc 800
        with self.assertRaises(ValueError):
            profile('UmiMushi', blocks_for('UmiMushi', tamper_umimushi), rows_for('UmiMushi'))

    def test_reject_registration_drift(self):
        def swap(rows):
            rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('Tadpole', blocks_for('Tadpole'), rows_for('Tadpole', swap))

        def drift_event(rows):
            rows[3]['events'][0][1] = 9  # Jigumo backwait1 loop event drift
        with self.assertRaises(ValueError):
            profile('Jigumo', blocks_for('Jigumo'), rows_for('Jigumo', drift_event))

        def drop_duplicate(rows):
            rows.pop(6)  # Catfish wait1 is registered three times
        with self.assertRaises(ValueError):
            profile('Catfish', blocks_for('Catfish'), rows_for('Catfish', drop_duplicate))

    def test_anim_mgr_rows_preserves_duplicates(self):
        parsed = anim_mgr_rows(mgr_text('Catfish'))
        self.assertEqual(len(parsed), len(MGR_ROWS['Catfish']))
        registration = tuple((Path(r['file']).stem, [list(e) for e in r['events']]) for r in parsed)
        self.assertEqual(registration, MGR_ROWS['Catfish'])
        self.assertEqual(sum(1 for stem, _ in registration if stem == 'wait1'), 3)

    def test_anim_mgr_rows_matches_first_registration(self):
        for species in SPECIES:
            parsed = anim_mgr_rows(mgr_text(species))
            expected = {}
            for row in parsed:
                expected.setdefault(Path(row['file']).stem, row['events'])
            self.assertEqual(expected, EXPECTED_EVENTS[species])

    def test_anim_mgr_rows_rejects_malformed(self):
        with self.assertRaises(ValueError):
            anim_mgr_rows('2\n{ a a.bca 1 2 -1 }')  # count mismatch
        with self.assertRaises(ValueError):
            anim_mgr_rows('1\n{ a a.bca 1 -1 }')  # odd event pair count
        with self.assertRaises(ValueError):
            anim_mgr_rows('1\n{ a a.bca 1 2 }')  # missing -1 terminator
        with self.assertRaises(ValueError):
            anim_mgr_rows('1\n{ a a.txt 1 2 -1 }')  # not a .bca registration

    def test_event_contract_matches_audit(self):
        self.assertEqual(EXPECTED_EVENTS['Catfish']['attack'], [[17, 2], [75, 3]])
        self.assertEqual(EXPECTED_EVENTS['Tadpole']['piti1'],
                         [[14, 2], [15, 0], [29, 3], [30, 4], [44, 1]])
        self.assertEqual(EXPECTED_EVENTS['Jigumo']['sattack1'],
                         [[15, 2], [26, 3], [56, 4], [61, 5], [66, 6], [71, 7],
                          [76, 8], [91, 9], [115, 10]])
        self.assertEqual(EXPECTED_EVENTS['UmiMushi']['attack1'],
                         [[25, 2], [39, 3], [40, 4], [50, 5], [66, 6]])

    def test_state_and_anim_ids_match_headers(self):
        self.assertEqual(STATE_IDS['Catfish']['press'], 8)
        self.assertEqual(STATE_IDS['Tadpole']['leap'], 5)
        self.assertEqual(STATE_IDS['Jigumo']['smiss'], 12)
        self.assertEqual(STATE_IDS['UmiMushi']['lost'], 9)
        self.assertEqual(ANIM_IDS['Catfish']['waitact2'], 8)
        self.assertEqual(ANIM_IDS['Tadpole']['type5'], 5)
        self.assertEqual(ANIM_IDS['Jigumo']['dive1'], 5)  # AnimID Eat
        self.assertEqual(ANIM_IDS['Jigumo']['to_runaway1'], 16)
        self.assertEqual(ANIM_IDS['UmiMushi']['fsearch1'], 10)
        self.assertEqual([len(STATE_IDS[s]) for s in SPECIES], [9, 6, 13, 10])

    def test_clip_and_registry_counts(self):
        self.assertEqual([len(CLIPS[s]) for s in SPECIES], [7, 6, 17, 12])
        self.assertEqual([len(MGR_ROWS[s]) for s in SPECIES], [9, 6, 17, 11])
        for species in SPECIES:
            shipped = set(CLIPS[species])
            registered = set(stem for stem, _ in MGR_ROWS[species])
            unregistered = set(UNREGISTERED.get(species, ()))
            self.assertTrue(shipped <= registered | unregistered)

    def test_unregistered_clip_handling(self):
        self.assertEqual(UNREGISTERED, {'UmiMushi': ('wait1',)})
        self.assertIn('wait1', CLIPS['UmiMushi'])
        self.assertNotIn('wait1', EXPECTED_EVENTS['UmiMushi'])
        self.assertNotIn('wait1', ANIM_IDS['UmiMushi'])
        self.assertEqual(len(CLIPS['UmiMushi']),
                         len(ANIM_IDS['UmiMushi']) + len(UNREGISTERED['UmiMushi']))
        result = profile('UmiMushi', blocks_for('UmiMushi'), rows_for('UmiMushi'))
        self.assertEqual(result['anim_id_by_clip'], ANIM_IDS['UmiMushi'])

    def test_unregistered_clip_required_when_not_declared(self):
        with patch.object(aquatic, 'UNREGISTERED', {}):
            with self.assertRaises(ValueError):
                profile('UmiMushi', blocks_for('UmiMushi'), rows_for('UmiMushi'))

    def test_text_and_limitations_nonclaims(self):
        self.assertIn('species Catfish Tadpole Jigumo UmiMushi', TEXT)
        self.assertIn('native_ready false', TEXT)
        self.assertIn('gameplay_events_executed false', TEXT)
        self.assertIn('btk_playback false', TEXT)
        self.assertIsInstance(LIMITATIONS, list)
        self.assertEqual(len(LIMITATIONS), 7)
        joined = ' '.join(LIMITATIONS)
        self.assertIn('umimusi_model1.btk', joined)
        self.assertIn('wait1.bca ships in anim.szs', joined)
        self.assertIn('no native runtime', joined.lower())

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
            with patch('experimental.pikmin2_aquatic_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_aquatic_assets.subprocess.check_output',
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
