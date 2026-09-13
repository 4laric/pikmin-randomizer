import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_flora_assets import (CLIPS, COMMON_NAME, DISC_PARMS,
                                               ENEMY_FLORA, EXPECTED_EVENTS,
                                               POM_BASE_ID, POM_SPECIES,
                                               POSE_TOLERANCES,
                                               PROPER_PARM_DEFAULTS,
                                               PROPER_RETAIL_ONLY, PROP_FLORA,
                                               SHARED_BASE, SPECIES, STATE_IDS,
                                               TEXT, TOLERANCES, VARIANT_GROUPS,
                                               extract, flora_animation_rows,
                                               profile, reference_conversion,
                                               resource_id)


def blocks_for(species, override=None):
    general = dict(DISC_PARMS[species]['general'])
    if species in ENEMY_FLORA:
        proper = dict(DISC_PARMS[species]['proper'])
        blocks = [{'s000': 0.5}, general, proper]
    else:
        blocks = [{'s000': 0.5}, general]
        if 'extra' in DISC_PARMS[species]:
            blocks.append(dict(DISC_PARMS[species]['extra']))
    if override:
        override(blocks)
    return blocks


def rows_for(species):
    return [{'file': name + '.bca', 'events': [list(e) for e in EXPECTED_EVENTS[species][name]]}
            for name in CLIPS[species]]


class FloraAssetsTests(unittest.TestCase):
    def test_species_profiles_validate(self):
        identities = {'Pelplant': 0, 'BluePom': 3, 'RedPom': 4, 'YellowPom': 5,
                      'BlackPom': 6, 'WhitePom': 7, 'RandPom': 8, 'Tanpopo': 46,
                      'Clover': 47, 'HikariKinoko': 48, 'Ooinu_s': 49,
                      'Ooinu_l': 50, 'Wakame_s': 51, 'Wakame_l': 52}
        self.assertEqual(SPECIES, identities)
        for species, identity in identities.items():
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['enemy_id'], identity)
            self.assertEqual(result['common_name'], COMMON_NAME[species])
            self.assertEqual(result['state_ids'], STATE_IDS[species])
            self.assertEqual(result['anim_id_by_clip'],
                             {name: i for i, name in enumerate(CLIPS[species])})
            self.assertEqual(result['proper_header_defaults'],
                             PROPER_PARM_DEFAULTS[species])

    def test_classification_separation(self):
        self.assertEqual(set(ENEMY_FLORA) | set(PROP_FLORA), set(SPECIES))
        for species in ENEMY_FLORA:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['classification'], 'enemy_flora')
        for species in PROP_FLORA:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['classification'], 'prop_flora')
            self.assertEqual(result['proper_header_defaults'], {})
            self.assertEqual(result['proper_retail'], {})
            self.assertEqual(result['proper_keys_defaulted_from_header'], [])

    def test_enemy_flora_require_proper_prop_flora_reject_it(self):
        for species in ENEMY_FLORA:
            with self.assertRaises(ValueError):
                profile(species, blocks_for(species)[:2], rows_for(species))
        for species in PROP_FLORA:
            general = dict(DISC_PARMS[species]['general'])
            with self.assertRaises(ValueError):
                profile(species, [{'s000': 0.5}, general, {'fp01': 1.0}],
                        rows_for(species))

    def test_retail_values_match_audit_contract(self):
        for species in ENEMY_FLORA:
            result = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(result['proper_retail'], DISC_PARMS[species]['proper'])
        # disc values stay distinct from header build-time defaults
        self.assertEqual(PROPER_PARM_DEFAULTS['Pelplant']['fp01'], 120.0)
        self.assertEqual(PROPER_PARM_DEFAULTS['Pelplant']['fp02'], 120.0)
        self.assertEqual(DISC_PARMS['Pelplant']['proper']['fp01'], 90.0)
        self.assertEqual(DISC_PARMS['Pelplant']['proper']['fp02'], 60.0)
        self.assertNotEqual(DISC_PARMS['Pelplant']['proper']['fp01'],
                            PROPER_PARM_DEFAULTS['Pelplant']['fp01'])
        self.assertEqual(PROPER_PARM_DEFAULTS['BluePom']['ip13'], 5)
        self.assertEqual(DISC_PARMS['BluePom']['proper']['ip13'], 9)
        self.assertEqual(DISC_PARMS['BluePom']['proper']['fp01'], 1.0)
        self.assertEqual(PROPER_PARM_DEFAULTS['BluePom']['fp01'], 30.0)
        self.assertEqual(DISC_PARMS['BluePom']['proper']['fp02'], 2.6)
        self.assertEqual(PROPER_PARM_DEFAULTS['BluePom']['fp02'], 1.25)
        # fp03 is serialized on disc (0.0) even though the header default is
        # 0.15; Pelplant's fp03 is serialized too, so nothing is defaulted.
        self.assertEqual(DISC_PARMS['Pelplant']['proper']['fp03'], 1.5)
        self.assertEqual(DISC_PARMS['BluePom']['proper']['fp03'], 0.0)
        self.assertEqual(PROPER_PARM_DEFAULTS['BluePom']['fp03'], 0.15)
        # ip02/ip12 are disc-only proper keys absent from the decomp Parms.
        self.assertEqual(DISC_PARMS['BluePom']['proper']['ip02'], 1)
        self.assertEqual(DISC_PARMS['BluePom']['proper']['ip12'], 1)
        self.assertNotIn('ip02', PROPER_PARM_DEFAULTS['BluePom'])
        self.assertEqual(PROPER_RETAIL_ONLY['BluePom'], ('ip02', 'ip12'))
        # Clover's floor-offset-looking 25 is an unreferenced trailing block,
        # not the general block value (which is 1100/40).
        self.assertEqual(DISC_PARMS['Clover']['general'], {'fp00': 1100.0})
        self.assertEqual(DISC_PARMS['Clover']['extra'], {'fp01': 25.0})

    def test_serialized_proper_keys_are_not_defaulted(self):
        result = profile('Pelplant', blocks_for('Pelplant'), rows_for('Pelplant'))
        self.assertEqual(result['proper_keys_defaulted_from_header'], [])
        self.assertEqual(result['proper_retail']['fp03'], 1.5)
        self.assertEqual(PROPER_PARM_DEFAULTS['Pelplant']['fp03'], 1.5)
        for species in POM_SPECIES:
            pom = profile(species, blocks_for(species), rows_for(species))
            self.assertEqual(pom['proper_keys_defaulted_from_header'], [])
            self.assertEqual(pom['proper_retail_only'], ['ip02', 'ip12'])
            self.assertEqual(pom['proper_retail']['fp03'], 0.0)

    def test_prop_flora_extra_block_and_metadata_absence(self):
        result = profile('Clover', blocks_for('Clover'), rows_for('Clover'),
                         metadata_absent=['enemystoneinfo.txt'])
        self.assertEqual(result['proper_retail'], {})
        self.assertEqual(result['unused_disc_blocks'], [{'fp01': 25.0}])
        self.assertEqual(result['metadata_absent'], ['enemystoneinfo.txt'])
        self.assertEqual(profile('Tanpopo', blocks_for('Tanpopo'),
                                 rows_for('Tanpopo'))['unused_disc_blocks'], [])

        def tamper_extra(blocks):
            blocks[2]['fp01'] = 1.0
        with self.assertRaises(ValueError):
            profile('Clover', blocks_for('Clover', tamper_extra),
                    rows_for('Clover'))

    def test_large_variant_registration_uses_capital_l(self):
        text = (
            '#\r\n#\tAnimMgr\r\n#\r\n\t1 \t# number of animations\r\n'
            '# ooinu_L.bca\r\n{\r\n\tZ:\\x\\ooinu_L.bca \r\n\tooinu_L.bca \r\n\t-1 \r\n}\r\n'
        )
        rows = flora_animation_rows(text)
        self.assertEqual(rows, [{'file': 'ooinu_L.bca', 'events': []}])
        # profile accepts the registered capital stem and normalises it.
        self.assertEqual(profile('Ooinu_l', blocks_for('Ooinu_l'),
                                 rows)['anim_id_by_clip'], {'ooinu_l': 0})
        with self.assertRaises(ValueError):
            flora_animation_rows(
                '#\r\n\t2 \t# number of animations\r\n{\r\n\tA \r\n\tbad \r\n\t-1 \r\n}')

    def test_reject_disc_parameter_drift(self):
        def tamper_pelplant(blocks):
            blocks[1]['fp00'] = 999.0
        with self.assertRaises(ValueError):
            profile('Pelplant', blocks_for('Pelplant', tamper_pelplant),
                    rows_for('Pelplant'))

        def tamper_pelplant_proper(blocks):
            blocks[2]['fp01'] = 120.0  # header default instead of disc 90
        with self.assertRaises(ValueError):
            profile('Pelplant', blocks_for('Pelplant', tamper_pelplant_proper),
                    rows_for('Pelplant'))

        def tamper_pom(blocks):
            blocks[2]['ip13'] = 5  # header multiplier instead of disc 9
        with self.assertRaises(ValueError):
            profile('BluePom', blocks_for('BluePom', tamper_pom),
                    rows_for('BluePom'))

        def tamper_plant(blocks):
            blocks[1]['fp00'] = 100.0  # header health instead of disc 1100
        with self.assertRaises(ValueError):
            profile('Clover', blocks_for('Clover', tamper_plant),
                    rows_for('Clover'))

        def tamper_clover_extra(blocks):
            blocks[2]['fp01'] = 40.0  # wrong unused trailing block value
        with self.assertRaises(ValueError):
            profile('Clover', blocks_for('Clover', tamper_clover_extra),
                    rows_for('Clover'))

    def test_reject_general_and_proper_key_drift(self):
        def tamper_general(blocks):
            blocks[1]['fp07'] = 1.0  # fp07 is not declared in EnemyParmsBase
        with self.assertRaises(ValueError):
            profile('Pelplant', blocks_for('Pelplant', tamper_general),
                    rows_for('Pelplant'))

        def tamper_general_plant(blocks):
            blocks[1]['fp07'] = 1.0
        with self.assertRaises(ValueError):
            profile('Tanpopo', blocks_for('Tanpopo', tamper_general_plant),
                    rows_for('Tanpopo'))

        def tamper_proper(blocks):
            blocks[2]['fp99'] = 1.0
        with self.assertRaises(ValueError):
            profile('Pelplant', blocks_for('Pelplant', tamper_proper),
                    rows_for('Pelplant'))

        def tamper_proper_pom(blocks):
            blocks[2]['ip99'] = 1
        with self.assertRaises(ValueError):
            profile('RandPom', blocks_for('RandPom', tamper_proper_pom),
                    rows_for('RandPom'))

    def test_reject_clip_and_event_mismatch(self):
        rows = rows_for('Pelplant')
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            profile('Pelplant', blocks_for('Pelplant'), rows)
        rows = rows_for('BluePom')
        rows[2]['events'] = [[24, 2]]
        with self.assertRaises(ValueError):
            profile('BluePom', blocks_for('BluePom'), rows)
        rows = rows_for('Tanpopo')
        rows[0]['file'] = 'wrong.bca'
        with self.assertRaises(ValueError):
            profile('Tanpopo', blocks_for('Tanpopo'), rows)

    def test_identity_event_and_state_contract(self):
        self.assertEqual(POM_BASE_ID, 82)
        self.assertEqual([len(CLIPS[s]) for s in ENEMY_FLORA],
                         [10, 6, 6, 6, 6, 6, 6])
        self.assertEqual([len(CLIPS[s]) for s in PROP_FLORA], [1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(EXPECTED_EVENTS['Pelplant']['wait1'], [[0, 0], [29, 1]])
        self.assertEqual(EXPECTED_EVENTS['Pelplant']['grow1'], [])
        self.assertEqual(EXPECTED_EVENTS['RandPom']['type1'], [[25, 2]])
        self.assertEqual(EXPECTED_EVENTS['RandPom']['type3'], [[20, 2]])
        self.assertEqual(STATE_IDS['Pelplant']['dead'], 6)
        self.assertEqual(STATE_IDS['Pelplant']['withersmall'], 9)
        self.assertEqual(STATE_IDS['RandPom']['swing'], 5)
        self.assertEqual(STATE_IDS['Tanpopo'], {})

    def test_two_identity_variant_groups(self):
        self.assertEqual(VARIANT_GROUPS['Ooinu'], ('Ooinu_s', 'Ooinu_l'))
        self.assertEqual(VARIANT_GROUPS['Wakame'], ('Wakame_s', 'Wakame_l'))
        for small, large in tuple(VARIANT_GROUPS.values()):
            self.assertIn(small, SPECIES)
            self.assertIn(large, SPECIES)
            self.assertEqual(SPECIES[small] + 1, SPECIES[large])

    def test_shared_base_and_resource_resolution(self):
        self.assertEqual(SHARED_BASE, {p: 'Pom' for p in POM_SPECIES})
        for species in POM_SPECIES:
            self.assertEqual(resource_id(species), 'Pom')
            self.assertEqual(profile(species, blocks_for(species),
                                     rows_for(species))['shared_base'], 'Pom')
        self.assertEqual(resource_id('Pelplant'), 'Pelplant')
        self.assertEqual(resource_id('Clover'), 'Clover')
        for species in ('Pelplant',) + PROP_FLORA:
            self.assertIsNone(profile(species, blocks_for(species),
                                      rows_for(species))['shared_base'])

    def test_pellet_to_pom_reference_predicate(self):
        self.assertEqual(reference_conversion('Pelplant', 1)['output'], 1)
        self.assertEqual(reference_conversion('Pelplant', 20)['output'], 20)
        self.assertTrue(reference_conversion('Pelplant', 5)['reference_only'])
        blue = reference_conversion('BluePom', 3)
        self.assertEqual((blue['output'], blue['multiplier'], blue['refund']),
                         (3, 1, False))
        refund = reference_conversion('BluePom', 2, own_colour=True)
        self.assertEqual((refund['output'], refund['refund']), (2, True))
        queen = reference_conversion('RandPom', 1)
        self.assertEqual((queen['output'], queen['multiplier'], queen['refund']),
                         (9, 9, False))
        self.assertFalse(reference_conversion('RandPom', 1,
                                              own_colour=True)['refund'])
        for bad in (('Pelplant', 3), ('Pelplant', -1), ('BluePom', 6),
                    ('BluePom', True), ('Tanpopo', 1), ('Nope', 1)):
            with self.assertRaises(ValueError):
                reference_conversion(*bad)

    def test_profile_text_explicit_nonclaims(self):
        self.assertIn('native_ready false', TEXT)
        self.assertIn('gameplay_events_executed false', TEXT)
        self.assertIn('btk_playback false', TEXT)
        self.assertIn('candypop_shared_base Pom', TEXT)

    def test_converter_tolerances_are_scoped(self):
        # #405/#429: Pelplant is the only flora with an opt-in singular
        # scale/normal policy and HikariKinoko the only one with the billboard
        # static fallback; every other identity keeps strict converter defaults.
        self.assertEqual(POSE_TOLERANCES,
                         {'Pelplant': {'singular_scale': 'allow'}})
        self.assertEqual(TOLERANCES, {
            'Pelplant': {'singular_normal': 'transpose-adjugate-zero'},
            'HikariKinoko': {'billboard': 'static', 'missing_normals': 'compute'},
        })
        self.assertEqual(set(POSE_TOLERANCES), {'Pelplant'})
        for strict in PROP_FLORA:
            if strict == 'HikariKinoko':
                continue
            self.assertNotIn(strict, POSE_TOLERANCES)
            self.assertNotIn(strict, TOLERANCES)

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
            with patch('experimental.pikmin2_flora_assets.disc_files', return_value={}), \
                 patch('experimental.pikmin2_flora_assets.subprocess.check_output',
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
