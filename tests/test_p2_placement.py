import copy
import json
import tempfile
import unittest
from pathlib import Path

from randomizer.p2_placement import (
    SCHEMA, audit, evaluate, load_document, normalize_profile, normalize_slot,
    slot_from_spawn_row, validate_document,
)
from randomizer.spawn_data import ADULT_SLOTS


def slot(**overrides):
    base = {
        'uid': 1, 'label': 'hope_adult_01', 'stage': 1, 'terrain': 'ground', 'radius': 100,
        'water_depth': 0, 'flight_space': False, 'burrow_ground': True, 'home': False,
        'helper_capacity': 4, 'projectile_corridor': False, 'corpse_route': True,
        'protected': False, 'boss_slot': False, 'first_day': 2, 'respawn_days': 5,
        'evidence': {'xyz': True, 'terrain': True, 'route': True},
    }
    base.update(overrides)
    return base


def profile(**overrides):
    base = {
        'identity': 'YellowKochappy', 'terrains': ['ground'], 'family_lane': 13,
        'footprint_radius': 30, 'min_water_depth': 0, 'requires_flight_space': False,
        'requires_burrow_ground': False, 'requires_home': False, 'helper_budget': 0,
        'requires_projectile_corridor': False, 'requires_corpse_route': True,
        'is_boss': False, 'encounter_descriptor': None, 'accepted_gates': ['placement'],
        'allow_protected': False, 'requires_renewable_slot': False, 'min_first_day': 0,
    }
    base.update(overrides)
    return base


def document(slots, profiles):
    return {'schema': SCHEMA, 'slots': slots, 'profiles': profiles}


class PlacementSchemaTests(unittest.TestCase):
    def test_defaults_and_roundtrip(self):
        normalized = validate_document(document([slot()], [profile()]))
        self.assertEqual(normalized['schema'], SCHEMA)
        self.assertEqual(normalized['slots'][0]['evidence'], {'xyz': True, 'terrain': True, 'route': True})
        self.assertEqual(normalized['profiles'][0]['accepted_gates'], ['placement'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'placement.json'
            path.write_text(json.dumps(normalized))
            self.assertEqual(load_document(path), normalized)

    def test_slot_defaults_deny_evidence(self):
        normalized = normalize_slot({'uid': 9, 'label': 'x', 'stage': 0, 'terrain': 'ground', 'radius': 10})
        self.assertEqual(normalized['evidence'], {'xyz': False, 'terrain': False, 'route': False})
        self.assertFalse(normalized['protected'])
        self.assertEqual(normalized['respawn_days'], 0)

    def test_malformed_documents_rejected(self):
        cases = [
            lambda x: x.update(schema='p2-placement-v0'),
            lambda x: x['slots'][0].pop('terrain'),
            lambda x: x['slots'][0].update(no_such_field=True),
            lambda x: x['profiles'][0].update(terrains=[]),
            lambda x: x['profiles'][0].update(family_lane=-1),
            lambda x: x['profiles'][0].update(accepted_gates=['ok', 3]),
            lambda x: x['slots'][0].update(radius=-1),
            lambda x: x['slots'][0].update(water_depth='deep'),
            lambda x: x['profiles'][0].update(requires_home='yes'),
        ]
        for mutate in cases:
            changed = copy.deepcopy(document([slot()], [profile()]))
            mutate(changed)
            with self.assertRaises(ValueError):
                validate_document(changed)

    def test_duplicate_identities_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate slot uids'):
            validate_document(document([slot(uid=1), slot(uid=1)], [profile()]))
        with self.assertRaisesRegex(ValueError, 'duplicate profile identities'):
            validate_document(document([slot()], [profile(), profile()]))

    def test_profile_requires_identity_and_terrain(self):
        with self.assertRaises(ValueError):
            normalize_profile({'terrains': ['ground']})
        with self.assertRaises(ValueError):
            normalize_profile({'identity': 'X', 'terrains': ['lava']})


class PlacementEvaluationTests(unittest.TestCase):
    def test_legal_pair_when_all_constraints_hold(self):
        result = evaluate(normalize_slot(slot()), normalize_profile(profile()))
        self.assertEqual(result, {'status': 'legal', 'reasons': []})

    def test_default_deny_without_accepted_gate(self):
        result = evaluate(normalize_slot(slot()), normalize_profile(profile(accepted_gates=[])))
        self.assertEqual(result['status'], 'denied')
        self.assertIn('no accepted placement evidence', result['reasons'])

    def test_default_deny_without_slot_evidence(self):
        result = evaluate(normalize_slot(slot(evidence={'xyz': True, 'terrain': True, 'route': False})),
                          normalize_profile(profile()))
        self.assertIn('slot lacks accepted native placement evidence', result['reasons'])

    def test_terrain_and_water_constraints(self):
        result = evaluate(normalize_slot(slot(terrain='ground')),
                          normalize_profile(profile(terrains=['water'], min_water_depth=2)))
        self.assertEqual(result['status'], 'denied')
        self.assertIn("terrain ground not in ['water']", result['reasons'])
        self.assertIn('water depth 0 below required 2', result['reasons'])

    def test_space_home_helper_and_footprint_constraints(self):
        result = evaluate(
            normalize_slot(slot(radius=20, helper_capacity=1, home=False, flight_space=False, burrow_ground=False)),
            normalize_profile(profile(footprint_radius=40, helper_budget=3, requires_home=True,
                                      requires_flight_space=True, requires_burrow_ground=True)))
        self.assertEqual(result['status'], 'denied')
        for reason in ('slot lacks flight space', 'slot lacks burrow ground', 'slot lacks a home/nest anchor',
                       'helper budget 3 exceeds slot capacity 1', 'footprint 40 exceeds slot radius 20'):
            self.assertIn(reason, result['reasons'])

    def test_projectile_corridor_and_corpse_route(self):
        result = evaluate(normalize_slot(slot(projectile_corridor=False, corpse_route=False)),
                          normalize_profile(profile(requires_projectile_corridor=True, requires_corpse_route=True)))
        self.assertIn('slot lacks a projectile corridor', result['reasons'])
        self.assertIn('slot lacks a corpse return route', result['reasons'])

    def test_protected_slot_denied_unless_allowed(self):
        denied = evaluate(normalize_slot(slot(protected=True)), normalize_profile(profile()))
        self.assertIn('slot drop is protected', denied['reasons'])
        allowed = evaluate(normalize_slot(slot(protected=True)), normalize_profile(profile(allow_protected=True)))
        self.assertEqual(allowed['status'], 'legal')

    def test_boss_requires_encounter_descriptor(self):
        boss = evaluate(normalize_slot(slot()), normalize_profile(profile(is_boss=True)))
        self.assertIn('boss requires an encounter descriptor', boss['reasons'])
        descriptor = evaluate(normalize_slot(slot()), normalize_profile(profile(is_boss=True, encounter_descriptor='empress_arena')))
        self.assertEqual(descriptor['status'], 'legal')
        boss_slot = evaluate(normalize_slot(slot(boss_slot=True)), normalize_profile(profile()))
        self.assertIn('boss slot requires an encounter descriptor', boss_slot['reasons'])

    def test_schedule_constraints(self):
        result = evaluate(normalize_slot(slot(respawn_days=0, first_day=2)),
                          normalize_profile(profile(requires_renewable_slot=True, min_first_day=5)))
        self.assertIn('slot is one-shot, not renewable', result['reasons'])
        self.assertIn('slot first day 2 before required 5', result['reasons'])


class PlacementAuditTests(unittest.TestCase):
    def test_audit_reports_admitted_and_unplaced(self):
        slots = [slot(uid=1, label='a'), slot(uid=2, label='b', terrain='water', water_depth=3)]
        profiles = [
            profile(identity='YellowKochappy', terrains=['ground']),
            profile(identity='Tadpole', terrains=['water'], min_water_depth=1),
            profile(identity='Unproven', terrains=['ground'], accepted_gates=[]),
        ]
        report = audit(document(slots, profiles))
        self.assertEqual(report['slots_evaluated'], 2)
        self.assertEqual(report['identities_evaluated'], 3)
        self.assertEqual(report['admitted']['YellowKochappy'], [1])
        self.assertEqual(report['admitted']['Tadpole'], [2])
        self.assertIn('Unproven', report['unplaced_identities'])
        self.assertIn('no accepted placement evidence', report['denied_reasons'])
        self.assertEqual(len(report['decisions']), 6)

    def test_audit_filters_and_is_deterministic(self):
        slots = [slot(uid=2, label='b'), slot(uid=1, label='a')]
        profiles = [profile(identity='B'), profile(identity='A')]
        report = audit(document(slots, profiles), slot_uids={1}, identities={'A'})
        self.assertEqual([(d['slot_uid'], d['identity']) for d in report['decisions']], [(1, 'A')])

    def test_boss_slots_listed(self):
        report = audit(document([slot(uid=7, boss_slot=True, evidence={})], [profile()]))
        self.assertEqual(report['boss_slots'], [7])

    def test_spawn_row_adapter_defaults_to_denied(self):
        adapted = slot_from_spawn_row(ADULT_SLOTS[0], evidence={'xyz': True, 'terrain': True, 'route': True})
        self.assertEqual(adapted['uid'], ADULT_SLOTS[0]['uid'])
        self.assertEqual(adapted['respawn_days'], ADULT_SLOTS[0]['respawn_days'])
        legal_profile = normalize_profile(profile(footprint_radius=0, requires_corpse_route=False))
        self.assertEqual(evaluate(adapted, legal_profile)['status'], 'legal')
        unproven = slot_from_spawn_row(ADULT_SLOTS[0], evidence={})
        self.assertEqual(evaluate(unproven, legal_profile)['status'], 'denied')


if __name__ == '__main__':
    unittest.main()
