import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_dweevil_assets import (CLIPS, EXPECTED_EVENTS,
                                                 GAMEPLAY_EVENT_TYPES,
                                                 DISC_PARMS, PROPER_PARM_DEFAULTS,
                                                 STATE_IDS, SPECIES, HAZARDS,
                                                 SHARED_MODEL, SHARED_PARM,
                                                 HAZARD_CLASSIFICATION,
                                                 HAZARD_PROPER_PARM_DEFAULTS,
                                                 TEXT, profile, extract)


def blocks_for(species, override=None):
    general = dict(DISC_PARMS[species]['general'])
    proper = dict(DISC_PARMS[species]['proper'])
    blocks = [{'s000': 0.5}, general, proper]
    if override:
        override(blocks)
    return blocks


def rows_for(species):
    return [{'file': name + '.bca',
             'events': [[i, t] for i, t in enumerate(EXPECTED_EVENTS[name])]}
            for name in CLIPS]


class DweevilAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        for species, identity in (('FireOtakara', 59), ('WaterOtakara', 60),
                                  ('GasOtakara', 61), ('ElecOtakara', 62),
                                  ('BombOtakara', 93)):
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['state_ids'], STATE_IDS)
            self.assertEqual(result['shared_base'], 'OtakaraBase')
            self.assertEqual(len(result['anim_id_by_clip']), len(CLIPS))
            self.assertEqual(result['proper_header_defaults'], PROPER_PARM_DEFAULTS)

    def test_retail_values_match_audit_contract(self):
        for species in SPECIES:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
            # disc values stay distinct from header build-time defaults
            for key, retail in DISC_PARMS[species]['proper'].items():
                self.assertEqual(result['proper_header_defaults'][key],
                                 PROPER_PARM_DEFAULTS[key])
                self.assertEqual(result['proper_retail'][key], retail)

    def test_retail_and_header_defaults_stay_distinct(self):
        result = profile('FireOtakara', blocks_for('FireOtakara'),
                         rows_for('FireOtakara'))
        self.assertEqual(result['proper_retail']['fp01'], 80.0)
        self.assertEqual(result['proper_header_defaults']['fp01'], 100.0)
        self.assertNotEqual(result['proper_retail']['fp01'],
                            result['proper_header_defaults']['fp01'])
        # Gas is the one species whose retail fp01 equals the header default,
        # but it is still reported from the disc block, not the header.
        gas = profile('GasOtakara', blocks_for('GasOtakara'), rows_for('GasOtakara'))
        self.assertEqual(gas['proper_retail']['fp01'], 100.0)
        self.assertEqual(DISC_PARMS['GasOtakara']['proper']['fp01'], 100.0)

    def test_keys_defaulted_from_header_recorded(self):
        for species in SPECIES:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_keys_defaulted_from_header'], [])

    def test_reject_general_disc_parameter_drift(self):
        def tamper(blocks):
            blocks[1]['fp00'] = 999.0  # FireOtakara life drift
        with self.assertRaises(ValueError):
            profile('FireOtakara', blocks_for('FireOtakara', tamper),
                    rows_for('FireOtakara'))

        def tamper_elec(blocks):
            blocks[1]['fp24'] = 10.0  # WaterOtakara retail attack is 0
        with self.assertRaises(ValueError):
            profile('WaterOtakara', blocks_for('WaterOtakara', tamper_elec),
                    rows_for('WaterOtakara'))

    def test_reject_unknown_general_and_proper_keys(self):
        def tamper_general(blocks):
            blocks[1]['fp07'] = 1.0  # fp07 is never declared
        with self.assertRaises(ValueError):
            profile('ElecOtakara', blocks_for('ElecOtakara', tamper_general),
                    rows_for('ElecOtakara'))

        def tamper_proper(blocks):
            blocks[1]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('GasOtakara', blocks_for('GasOtakara', tamper_proper),
                    rows_for('GasOtakara'))

        def tamper_species_proper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('BombOtakara', blocks_for('BombOtakara', tamper_species_proper),
                    rows_for('BombOtakara'))

    def test_reject_proper_disc_parameter_drift(self):
        def tamper(blocks):
            blocks[2]['fp01'] = 100.0  # FireOtakara retail otakara life is 80
        with self.assertRaises(ValueError):
            profile('FireOtakara', blocks_for('FireOtakara', tamper),
                    rows_for('FireOtakara'))

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('FireOtakara')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('FireOtakara', blocks_for('FireOtakara'), rows)

        rows = rows_for('ElecOtakara')
        rows[CLIPS.index('attack1')]['events'][1][1] = 9
        with self.assertRaises(ValueError):
            profile('ElecOtakara', blocks_for('ElecOtakara'), rows)

        rows = rows_for('BombOtakara')
        rows[CLIPS.index('dropitem2')]['events'].append([7, 3])
        with self.assertRaises(ValueError):
            profile('BombOtakara', blocks_for('BombOtakara'), rows)

    def test_event_contract_matches_source(self):
        self.assertEqual(EXPECTED_EVENTS['attack1'], (2, 3))
        self.assertEqual(EXPECTED_EVENTS['attack2'], (2, 3))
        self.assertEqual(EXPECTED_EVENTS['takeitem'], (2,))
        self.assertEqual(EXPECTED_EVENTS['dropitem2'], (2,))
        self.assertEqual(EXPECTED_EVENTS['wait1'], ())
        self.assertEqual(STATE_IDS['flick'], 1)
        self.assertEqual(STATE_IDS['bomb_wait'], 11)
        self.assertEqual(STATE_IDS['bomb_turn'], 13)
        self.assertEqual(len(CLIPS), 12)
        # The on-disc AnimID slot 4 stem is `takeitem`, not `take1`.
        self.assertEqual(CLIPS[4], 'takeitem')

    def test_clip_and_resource_aliasing_match_disc(self):
        # Disc otakara/enemyanimmgr.txt registers these 12 stems in AnimID order;
        # all five species alias the FireOtakara model/anim bank while the
        # anim/collision/stone metadata live under the shared `otakara/` folder.
        self.assertEqual(CLIPS, ('wait1', 'move1', 'pivot1', 'attack1',
                                 'takeitem', 'wait2', 'move2', 'pivot2',
                                 'attack2', 'dropitem2', 'dead', 'carry'))
        self.assertEqual(SHARED_MODEL, 'FireOtakara')
        self.assertEqual(SHARED_PARM, 'otakara')
        self.assertEqual(GAMEPLAY_EVENT_TYPES, (2, 3))

    def test_hazard_classification_is_explicit(self):
        self.assertEqual(HAZARDS, {'Hiba': 20, 'GasHiba': 21, 'ElecHiba': 22})
        for name in HAZARDS:
            self.assertTrue(HAZARD_CLASSIFICATION[name]['registered'])
            self.assertIn('fixed scenery-adjacent',
                          HAZARD_CLASSIFICATION[name]['classification'])
            self.assertIn('HasNoInfo', HAZARD_CLASSIFICATION[name]['evidence'])
        self.assertEqual(HAZARD_PROPER_PARM_DEFAULTS['Hiba'],
                         {'fp02': 2.5, 'fp01': 2.5, 'fp03': 10.0,
                          'fp90': 0.085, 'fp91': 0.05})
        self.assertEqual(HAZARD_PROPER_PARM_DEFAULTS['ElecHiba']['fp03'], 2.5)

    def test_profile_text_explicit_nonclaims(self):
        self.assertIn('native_ready false', TEXT)
        self.assertIn('gameplay_events_executed false', TEXT)
        self.assertIn('btk_playback false', TEXT)
        self.assertIn('hazards Hiba GasHiba ElecHiba', TEXT)
        self.assertIn('shared_base Otakara model FireOtakara', TEXT)

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
            with patch('experimental.pikmin2_dweevil_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_dweevil_assets.subprocess.check_output',
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
