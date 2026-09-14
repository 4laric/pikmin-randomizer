"""Unit tests for the lane-13 bulborb/dwarf/sheargrub family contract (#120)."""
import unittest

from experimental.pikmin2_bulborb_family import (
    BY_ID, BY_INTERNAL, GATES, IDENTITIES, SCHEMA, acceptance_contract, identity,
    special_rules, validate_acceptance, variant_differences, variant_matrix)


GOOD_FIRECHAPPY_LOG = '\n'.join([
    'P2_FIRECHAPPY_BIND generator=330001 source_id=33 visual_only=0',
    'P2_ENEMY_READY species=FireChappy native_family=Chappy generator=330001 x=0.0 '
    'y=30.0 z=0.0 behavior=native source_FSM=implemented attack=animation_event',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_FIRECHAPPY_STATE generator=330001 state=sleep',
    'P2_FIRECHAPPY_STATE generator=330001 state=attack',
    'P2_FIRECHAPPY_STATE generator=330001 state=dead',
])


class BulborbFamilyTests(unittest.TestCase):
    def test_schema(self):
        self.assertEqual(SCHEMA, 'p2-bulborb-family-v1')

    def test_lane13_ids(self):
        expected = {
            1: 'Kochappy', 2: 'Chappy', 33: 'FireChappy', 35: 'KumaChappy',
            42: 'BlueChappy', 43: 'YellowChappy', 44: 'BlueKochappy',
            45: 'YellowKochappy', 76: 'KumaKochappy', 12: 'Ujia', 13: 'Ujib',
        }
        self.assertEqual({i.source_id: i.internal for i in IDENTITIES}, expected)
        self.assertEqual(identity(45).english, 'Snow Bulborb')
        self.assertEqual(identity(33).english, 'Fiery Bulblax')
        self.assertEqual(identity(35).english, 'Spotty Bulbear')

    def test_variant_matrix_covers_all_gates(self):
        rows = variant_matrix()
        self.assertEqual(len(rows), len(IDENTITIES))
        for row in rows:
            self.assertEqual(set(row['gates']), set(GATES), row['internal'])
            self.assertTrue(row['fsm_states'], row['internal'])
            self.assertTrue(row['anims'], row['internal'])

    def test_adult_and_dwarf_branches(self):
        adults = {i.internal for i in IDENTITIES if i.branch == 'adult'}
        dwarfs = {i.internal for i in IDENTITIES if i.branch == 'dwarf'}
        self.assertIn('FireChappy', adults)
        self.assertIn('KumaChappy', adults)
        self.assertIn('YellowKochappy', dwarfs)
        self.assertIn('KumaKochappy', dwarfs)
        self.assertNotIn('press', BY_INTERNAL['Chappy'].fsm_states)
        self.assertNotIn('sleep', BY_INTERNAL['Kochappy'].fsm_states)

    def test_dwarf_kuma_follows_parent(self):
        self.assertIn('parent_following_walkpath', BY_INTERNAL['KumaKochappy'].special)
        rules = special_rules('KumaKochappy')
        self.assertIn('parent_following_walkpath', rules)
        self.assertIn('ChappyRelation', rules['chappy_relation_owner']['source']
                      if 'chappy_relation_owner' in rules else
                      special_rules('KumaChappy')['chappy_relation_owner']['source'])

    def test_firechappy_special_rules(self):
        rules = special_rules('FireChappy')
        for name in ('fire_body_state', 'water_extinguish', 'fire_touch_receiver',
                     'dead_smoke_vs_steam'):
            self.assertIn(name, rules)
        self.assertIn('InteractFire', rules['fire_touch_receiver']['rule'])

    def test_firechappy_blocked_on_elemental_contract(self):
        row = next(r for r in variant_matrix() if r['internal'] == 'FireChappy')
        self.assertEqual(row['status'], 'missing')
        self.assertIn('lane 10', row['gates']['attacks_receivers'])
        self.assertTrue(any('FireChappy' in b for b in row['blockers']))

    def test_kumachappy_revival_rules(self):
        rules = special_rules('KumaChappy')
        self.assertIn('revive_carcass', rules)
        self.assertIn('gauge_rebirth', rules)
        self.assertIn('respawn_rate=10', BY_INTERNAL['KumaChappy'].parms['fp12'])

    def test_female_sheargrub_has_no_pikmin_damage(self):
        rule = special_rules('Ujia')['no_pikmin_damage']
        self.assertIn('no Pikmin-damaging attack', rule['rule'])
        self.assertIn('no_mouth_slots', BY_INTERNAL['Ujia'].special)
        self.assertIn('bite_and_swallow', BY_INTERNAL['Ujib'].special)

    def test_variant_differences_keys(self):
        keys = {entry['key'] for entry in variant_differences()}
        self.assertEqual(keys, {'adult_vs_dwarf', 'elemental', 'revival', 'relation',
                                'sheargrub_sex', 'mimicry'})

    def test_acceptance_contract_marker_and_source_id(self):
        contract = acceptance_contract('FireChappy')
        self.assertIn('P2_FIRECHAPPY_BIND', contract['identity'])
        self.assertIn('source_id=33', contract['identity'])
        self.assertIn('attack', contract['required_states'])
        self.assertEqual(set(contract['gates']), set(GATES))

    def test_validate_acceptance_passes_on_source_log(self):
        result = validate_acceptance(GOOD_FIRECHAPPY_LOG)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['identity'], 'FireChappy')
        self.assertEqual(result['source_id'], 33)

    def test_validate_acceptance_rejects_wrong_id(self):
        bad = GOOD_FIRECHAPPY_LOG.replace('source_id=33', 'source_id=35')
        result = validate_acceptance(bad)
        self.assertEqual(result['identity'], 'KumaChappy')
        self.assertFalse(result['checks']['identity'])
        self.assertFalse(result['passed'])

    def test_validate_acceptance_rejects_unknown_source_id(self):
        bad = GOOD_FIRECHAPPY_LOG.replace('source_id=33', 'source_id=34')
        with self.assertRaises(ValueError):
            validate_acceptance(bad)

    def test_validate_acceptance_rejects_missing_source_state(self):
        bad = '\n'.join(line for line in GOOD_FIRECHAPPY_LOG.splitlines()
                        if '_STATE ' not in line)
        bad += '\nP2_FIRECHAPPY_STATE generator=330001 state=unknownstate'
        result = validate_acceptance(bad)
        self.assertFalse(result['checks']['has_source_states'])
        self.assertFalse(result['passed'])

    def test_validate_acceptance_rejects_extinction(self):
        bad = GOOD_FIRECHAPPY_LOG + '\nExtinction sequence started'
        self.assertFalse(validate_acceptance(bad)['checks']['no_extinction'])

    def test_validate_acceptance_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate_acceptance(b'not text')


if __name__ == '__main__':
    unittest.main()
