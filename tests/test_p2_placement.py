import copy
import json
import tempfile
import unittest
from pathlib import Path

from randomizer.p2_placement import (
    ENCOUNTER_SCHEMA, SCHEMA, audit, compatibility, compatibility_report,
    coverage_report, evaluate, load_document, normalize_encounter_descriptor,
    normalize_profile, normalize_slot, slot_from_spawn_row, validate_document,
    validate_encounter_descriptor,
)
from randomizer import p2_placement_catalog as catalog
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


def document(slots, profiles, encounters=None):
    record = {'schema': SCHEMA, 'slots': slots, 'profiles': profiles}
    if encounters is not None:
        record['encounters'] = encounters
    return record


def descriptor(**overrides):
    base = {
        'id': 'empress_arena', 'identity': 'EmpressBulblax', 'terrains': ['ground'],
        'footprint_radius': 30, 'helper_budget': 0, 'arena_slots': {'min': 1, 'max': 1},
        'phases': 2, 'protected_drops': [], 'required_gates': ['arena'],
    }
    base.update(overrides)
    return base


def boss(**overrides):
    base = profile(identity='EmpressBulblax', is_boss=True, encounter_descriptor='empress_arena')
    base.update(overrides)
    return base


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


class CompatibilityReportTests(unittest.TestCase):
    def test_cohort_mismatch_is_a_hard_incompatibility(self):
        result = compatibility(normalize_slot(slot(cohort='aquatic')),
                               normalize_profile(profile(terrains=['ground'], cohort='grub')))
        self.assertEqual(result, ['cohort grub not allowed in slot cohort aquatic'])

    def test_missing_evidence_is_not_an_incompatibility(self):
        # No accepted gate and no slot evidence still counts as compatible.
        result = compatibility(normalize_slot(slot(evidence={})),
                               normalize_profile(profile(accepted_gates=[])))
        self.assertEqual(result, [])

    def test_report_separates_compatible_from_incompatible(self):
        slots = [slot(uid=1, label='a', cohort='ground'),
                 slot(uid=2, label='b', terrain='water', cohort='aquatic')]
        profiles = [profile(identity='Ground', terrains=['ground'], cohort='ground'),
                    profile(identity='Water', terrains=['water'], cohort='aquatic')]
        report = compatibility_report(document(slots, profiles))
        self.assertEqual(report['identity_compatibility']['Ground']['compatible_slot_uids'], [1])
        self.assertEqual(report['identity_compatibility']['Ground']['incompatible_slots'], 1)
        self.assertEqual(report['identity_compatibility']['Water']['compatible_slot_uids'], [2])
        self.assertEqual(report['slot_compatibility'][1]['compatible_identity_list'], ['Ground'])
        self.assertEqual(report['unplaceable_identities'], [])

    def test_report_flags_unplaceable_identity(self):
        report = compatibility_report(document([slot(terrain='ground', cohort='ground')],
                                               [profile(identity='Fish', terrains=['water'])]))
        self.assertEqual(report['unplaceable_identities'], ['Fish'])


class PlacementCatalogTests(unittest.TestCase):
    def test_campaign_slots_are_default_deny_with_cohort_terrain(self):
        slots = catalog.slots_from_campaign()
        self.assertEqual(len(slots), len(catalog.CAMPAIGN_SLOTS))
        by_uid = {s['uid']: s for s in slots}
        sample = next(s for s in slots if s['cohort'] == 'aquatic')
        self.assertEqual(sample['terrain'], 'water')
        self.assertTrue(sample['evidence']['xyz'])
        self.assertFalse(sample['evidence']['terrain'])
        self.assertFalse(sample['evidence']['route'])
        self.assertEqual(by_uid[sample['uid']]['cohort'], 'aquatic')

    def test_generator_slots_mark_boss_and_deny_evidence(self):
        slots = catalog.slots_from_generators()
        self.assertTrue(any(s.get('boss_slot') for s in slots))
        self.assertTrue(all(not s['evidence']['xyz'] for s in slots))
        boss = next(s for s in slots if s.get('boss_slot'))
        self.assertEqual(boss['terrain'], 'mixed')

    def test_all_slots_excludes_terrain_unknown_generators_by_default(self):
        known = catalog.all_slots()
        self.assertEqual(len(known), len(catalog.CAMPAIGN_SLOTS))
        expanded = catalog.all_slots(include_generators=True)
        self.assertGreater(len(expanded), len(known))

    def test_candidate_profiles_are_valid_and_default_deny(self):
        profiles = catalog.candidate_profiles()
        identities = {p['identity'] for p in profiles}
        self.assertIn('Chappy', identities)
        self.assertIn('Miulin', identities)
        self.assertNotIn('UmiMushi', identities)  # boss not in the non-boss cohort
        for p in profiles:
            self.assertEqual(p['accepted_gates'], [])
            self.assertFalse(p['is_boss'])
        by_identity = {p['identity']: p for p in profiles}
        self.assertEqual(by_identity['Chappy']['cohort'], 'ground')
        self.assertEqual(by_identity['UjiA']['cohort'], 'grub')
        self.assertEqual(by_identity['Sokkuri']['cohort'], None)
        # Source-backed nest anchor: Hermit Crawmad references PanHouse.
        self.assertTrue(by_identity['Jigumo']['requires_home'])
        self.assertFalse(by_identity['Tadpole']['requires_home'])
        self.assertTrue(all(p['requires_corpse_route'] for p in profiles))

    def test_boss_descriptors_and_profiles_are_default_deny(self):
        descriptors = catalog.boss_encounters()
        self.assertEqual({d['id'] for d in descriptors},
                         {'umi_mushi_arena', 'umi_mushi_blind_arena'})
        self.assertTrue(all(d['arena_slots'] == {'min': 1, 'max': 1} for d in descriptors))
        profiles = catalog.boss_profiles()
        self.assertTrue(all(p['is_boss'] for p in profiles))
        self.assertTrue(all(p['accepted_gates'] == [] for p in profiles))

    def test_boss_document_needs_a_boss_arena_slot(self):
        # Default campaign document excludes bosses and their descriptors.
        plain = catalog.build_document()
        self.assertEqual(plain['encounters'], [])
        self.assertNotIn('UmiMushi', {p['identity'] for p in plain['profiles']})
        # A caller-supplied water boss arena validates and is constraint-compatible.
        water = normalize_slot(dict(
            next(s for s in catalog.slots_from_campaign() if s['terrain'] == 'water'), boss_slot=True))
        document = catalog.build_document(slots=[water], include_bosses=True)
        identities = {p['identity'] for p in document['profiles']}
        self.assertTrue({'UmiMushi', 'UmiMushiBlind'} <= identities)
        boss = normalize_profile(catalog.boss_profiles()[0])
        encounters = {e['id']: e for e in document['encounters']}
        self.assertEqual(compatibility(water, boss, encounters), [])
        # Still denied: no accepted gate and no native evidence.
        self.assertEqual(audit(document)['admitted'], {})
        # A ground slot cannot host a water boss.
        ground = normalize_slot(dict(
            next(s for s in catalog.slots_from_campaign() if s['terrain'] == 'ground'), boss_slot=True))
        blocked = compatibility(ground, boss, encounters)
        self.assertIn("terrain ground not in ['water']", blocked)

    def test_built_document_validates_and_rejects_foreign_cohorts(self):
        document = catalog.build_document()
        report = compatibility_report(document)
        compatibility_by_id = report['identity_compatibility']
        self.assertEqual(report['slots_evaluated'], len(catalog.CAMPAIGN_SLOTS))
        # Jigumo needs a nest anchor the campaign table does not expose.
        self.assertEqual(report['unplaceable_identities'], ['Jigumo'])
        jigumo_reasons = [row['reason'] for row in compatibility_by_id['Jigumo']['top_incompatible_reasons']]
        self.assertIn('slot lacks a home/nest anchor', jigumo_reasons)
        # A grub identity cannot land in the ground or aquatic cohorts.
        self.assertEqual(compatibility_by_id['UjiA']['compatible_slots'], 10)
        self.assertEqual(compatibility_by_id['Chappy']['compatible_slots'], 33)
        self.assertEqual(compatibility_by_id['Tadpole']['compatible_slots'], 10)
        self.assertEqual(compatibility_by_id['Frog']['compatible_slots'], 7)
        # Every pair is still denied for missing gates/evidence.
        audit_report = audit(document)
        self.assertEqual(audit_report['admitted'], {})
        self.assertTrue(all(d['status'] == 'denied' for d in audit_report['decisions']))


class EncounterDescriptorTests(unittest.TestCase):
    def test_normalizes_required_fields_and_optional_notes(self):
        normalized = normalize_encounter_descriptor(descriptor())
        self.assertEqual(normalized['notes'], '')
        self.assertEqual(normalized['arena_slots'], {'min': 1, 'max': 1})
        self.assertEqual(normalized['phases'], 2)
        with self.assertRaises(ValueError):
            normalize_encounter_descriptor({'id': 'x'})

    def test_malformed_descriptors_rejected(self):
        cases = [
            {'id': ''},
            {'identity': ''},
            {'terrains': []},
            {'terrains': ['lava']},
            {'footprint_radius': -1},
            {'helper_budget': -1},
            {'helper_budget': 1.5},
            {'phases': 0},
            {'phases': 1.5},
            {'protected_drops': [1]},
            {'required_gates': 'arena'},
            {'arena_slots': {'min': 2, 'max': 1}},
            {'arena_slots': {'min': -1, 'max': 1}},
            {'arena_slots': {'min': 1, 'max': 1, 'extra': 0}},
            {'arena_slots': {'min': 1}},
            {'arena_slots': 'wide'},
            {'notes': 7},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    normalize_encounter_descriptor(descriptor(**overrides))
                malformed = normalize_encounter_descriptor(descriptor())
                malformed.update(overrides)
                with self.assertRaises(ValueError):
                    validate_encounter_descriptor(malformed)

    def test_document_validates_encounters(self):
        normalized = validate_document(document([slot()], [profile()], [descriptor()]))
        self.assertEqual(normalized['encounters'][0]['id'], 'empress_arena')

    def test_duplicate_descriptor_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate encounter descriptor ids'):
            validate_document(document([slot()], [profile()], [descriptor(), descriptor()]))

    def test_unknown_descriptor_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unknown field'):
            validate_document(document([slot()], [profile()], [descriptor(no_such_field=1)]))

    def test_boss_profile_requires_existing_descriptor(self):
        with self.assertRaisesRegex(ValueError, 'requires an encounter_descriptor'):
            validate_document(document([slot()], [boss(encounter_descriptor=None)], []))
        with self.assertRaisesRegex(ValueError, 'references unknown encounter descriptor'):
            validate_document(document([slot()], [boss(encounter_descriptor='missing')], [descriptor()]))


class BossDescriptorEvaluationTests(unittest.TestCase):
    def descriptors(self, *records):
        return {record['id']: normalize_encounter_descriptor(record) for record in records}

    def test_boss_with_matching_descriptor_is_legal(self):
        result = evaluate(normalize_slot(slot()), normalize_profile(boss()), self.descriptors(descriptor()))
        self.assertEqual(result, {'status': 'legal', 'reasons': []})

    def test_boss_without_descriptor_context_is_denied(self):
        result = evaluate(normalize_slot(slot()), normalize_profile(boss()), self.descriptors())
        self.assertIn("no encounter descriptor 'empress_arena' defined", result['reasons'])

    def test_boss_identity_mismatch_denied(self):
        result = evaluate(normalize_slot(slot()), normalize_profile(boss()),
                          self.descriptors(descriptor(identity='OtherBoss')))
        self.assertEqual(result['status'], 'denied')
        self.assertIn('encounter identity OtherBoss does not match profile identity EmpressBulblax', result['reasons'])

    def test_boss_constraint_mismatch_denied(self):
        result = evaluate(
            normalize_slot(slot(radius=20, helper_capacity=1)),
            normalize_profile(boss()),
            self.descriptors(descriptor(terrains=['water'], footprint_radius=40, helper_budget=3,
                                        arena_slots={'min': 2, 'max': 3})))
        self.assertEqual(result['status'], 'denied')
        for reason in ('terrain ground not in encounter terrains [\'water\']',
                       'encounter footprint 40 exceeds slot radius 20',
                       'encounter helper budget 3 exceeds slot capacity 1',
                       'slot cannot host exactly one boss arena'):
            self.assertIn(reason, result['reasons'])

    def test_non_boss_evaluation_ignores_descriptor_context(self):
        result = evaluate(normalize_slot(slot()), normalize_profile(profile()), self.descriptors(descriptor()))
        self.assertEqual(result['status'], 'legal')


class CoverageReportTests(unittest.TestCase):
    def test_counts_and_top_denials(self):
        slots = [slot(uid=1, label='a'), slot(uid=2, label='b', terrain='water', water_depth=3)]
        profiles = [
            profile(identity='YellowKochappy', terrains=['ground']),
            profile(identity='Tadpole', terrains=['water'], min_water_depth=1),
            profile(identity='Unproven', terrains=['ground'], accepted_gates=[]),
        ]
        report = coverage_report(document(slots, profiles))
        self.assertEqual(report['encounter_schema'], ENCOUNTER_SCHEMA)
        self.assertEqual(report['identity_coverage']['YellowKochappy']['admitted_slots'], 1)
        self.assertEqual(report['identity_coverage']['YellowKochappy']['admitted_slot_uids'], [1])
        self.assertEqual(report['identity_coverage']['Tadpole']['admitted_slot_uids'], [2])
        self.assertEqual(report['identity_coverage']['Unproven']['admitted_slots'], 0)
        unproven_reasons = [row['reason'] for row in report['identity_coverage']['Unproven']['top_denial_reasons']]
        self.assertIn('no accepted placement evidence', unproven_reasons)
        self.assertEqual(report['slot_coverage'][1]['admitted_identities'], 1)
        self.assertEqual(report['slot_coverage'][1]['admitted_identity_list'], ['YellowKochappy'])
        self.assertEqual(report['slot_coverage'][2]['admitted_identities'], 1)
        self.assertEqual(report['unresolved_bosses'], [])

    def test_coverage_is_deterministic(self):
        slots = [slot(uid=2, label='b'), slot(uid=1, label='a')]
        profiles = [profile(identity='B'), profile(identity='A')]
        report = coverage_report(document(slots, profiles))
        self.assertEqual(list(report['identity_coverage']), ['A', 'B'])
        self.assertEqual(list(report['slot_coverage']), [1, 2])

    def test_unresolved_boss_identity_mismatch(self):
        report = coverage_report(document([slot()], [boss()], [descriptor(identity='OtherBoss')]))
        self.assertEqual(report['unresolved_bosses'], ['EmpressBulblax'])
        self.assertFalse(report['identity_coverage']['EmpressBulblax']['has_valid_descriptor'])

    def test_resolved_boss_admitted(self):
        report = coverage_report(document([slot()], [boss()], [descriptor()]))
        self.assertEqual(report['unresolved_bosses'], [])
        self.assertEqual(report['identity_coverage']['EmpressBulblax']['admitted_slots'], 1)


class BindingTargetTests(unittest.TestCase):
    def test_targets_by_identity_match_compatibility(self):
        document = catalog.build_document()
        targets = catalog.targets_by_identity(document)
        self.assertEqual(len(targets['Catfish']), 10)
        self.assertEqual(len(targets['Chappy']), 33)
        self.assertEqual(targets['Jigumo'], [])
        campaign_uids = {str(s['uid']) for s in document['slots']}
        self.assertTrue(set(targets['Catfish']) <= campaign_uids)

    def test_binding_targets_are_the_cohort_intersection(self):
        # Sokkuri (open ground) accepts every ground slot Chappy accepts.
        self.assertEqual(catalog.binding_targets(['Chappy', 'Sokkuri']),
                         catalog.binding_targets(['Chappy']))
        self.assertEqual(len(catalog.binding_targets(['Catfish', 'Tadpole'])), 10)
        # A ground and an aquatic identity share no legal flat target.
        self.assertEqual(catalog.binding_targets(['Chappy', 'Catfish']), [])
        with self.assertRaises(ValueError):
            catalog.binding_targets([])
        with self.assertRaises(ValueError):
            catalog.binding_targets(['NoSuchIdentity'])

    def test_binding_targets_for_sources_maps_and_rejects_bosses(self):
        self.assertEqual(catalog.binding_targets_for_sources([26, 27]),
                         catalog.binding_targets(['Catfish', 'Tadpole']))
        with self.assertRaises(ValueError):
            catalog.binding_targets_for_sources([71])  # UmiMushi is a boss cohort entry

    def test_targets_compose_with_lane03_seed_bridge(self):
        from experimental.pikmin2_seed_bridge import (
            resolve_layout, validate_layout, validate_targets,
        )
        targets = catalog.binding_targets_for_sources([26, 27])
        self.assertEqual(validate_targets(targets), targets)
        layout = resolve_layout('placement-contract', 'Player1', targets, [26, 27])
        validate_layout(layout)
        bound = {b['enum_name'] for b in layout['bindings']}
        self.assertTrue(bound <= {'Catfish', 'Tadpole'})
        self.assertTrue({b['target'] for b in layout['bindings']} <= set(targets))

    def test_target_groups_are_deterministic(self):
        groups = catalog.binding_target_groups()
        self.assertEqual(sorted(groups['groups']),
                         ['aquatic', 'dwarf', 'frog', 'ground', 'grub', 'open'])
        self.assertEqual(groups['source_ids']['Catfish'], 26)
        self.assertEqual(groups['groups']['aquatic']['targets'],
                         catalog.binding_targets(['Catfish', 'Tadpole']))


if __name__ == '__main__':
    unittest.main()
