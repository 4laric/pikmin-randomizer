"""Muse placement slice (#492): candidate-only profiles for 41/57/58/78.

Pins the placement/native-bind contract without admitting anything:

- one default-deny profile per identity, each naming its single defensible
  generated slot, and that slot is constraint-compatible yet denied pending
  accepted native evidence (fail closed);
- unsupported terrain/routes, protected slots, unknown sources and empty
  cohorts are rejected, not silently accepted;
- the lane-04 default document is unchanged (pinned group keys, no muse
  identities leaking into lane-03 consumers);
- the native `MUSE_GENERATED_SLOT_*` constants match the catalog table;
- the log observer correlates resolve/bind markers and reports mismatches;
- no muse id enters the admission set or the ordinary candidate cohort.
"""
import re
import unittest
from pathlib import Path

from randomizer import p2_placement
from randomizer import p2_placement_catalog as catalog
from experimental import pikmin2_muse_placement as observer

ROOT = Path(__file__).resolve().parent.parent
NATIVE_HEADER = ROOT / 'native' / 'pc_port' / 'pc_p2_generated_placement.h'

MUSE = {
    41: ('Fuefuki', 1254096625),
    57: ('Kurage', 689702860),
    58: ('BombSarai', 1787125272),
    78: ('MiniHoudai', 328297937),
}


def muse_document():
    return catalog.build_muse_document()


def profiles_by_identity(document):
    return {p['identity']: p for p in document['profiles']}


def slots_by_uid(document):
    return {s['uid']: s for s in document['slots']}


class MuseProfileTests(unittest.TestCase):
    def test_one_profile_per_identity_with_single_accepted_slot(self):
        profiles = catalog.muse_candidate_profiles()
        self.assertEqual(len(profiles), 4)
        by_identity = {p['identity']: p for p in profiles}
        for source_id, (identity, slot_uid) in MUSE.items():
            profile = by_identity[identity]
            self.assertEqual(profile['accepted_slot_uids'], [slot_uid])
            self.assertEqual(profile['accepted_gates'], [])
            self.assertTrue(profile['requires_corpse_route'])
            self.assertIn(f'source_id {source_id}', profile['notes'])

    def test_source_id_mapping(self):
        self.assertEqual(catalog.muse_candidate_source_ids(),
                         {identity: sid for sid, (identity, _) in MUSE.items()})
        self.assertEqual(catalog.MUSE_GENERATED_SLOTS,
                         {sid: uid for sid, (_, uid) in MUSE.items()})

    def test_accepted_slot_is_compatible_but_denied_pending_evidence(self):
        document = muse_document()
        profiles = profiles_by_identity(document)
        slots = slots_by_uid(document)
        for source_id, (identity, slot_uid) in MUSE.items():
            profile = profiles[identity]
            slot = slots[slot_uid]
            self.assertTrue(slot['corpse_route'], identity)
            self.assertFalse(slot.get('protected', False), identity)
            self.assertEqual(p2_placement.compatibility(slot, profile), [],
                             identity)
            verdict = p2_placement.evaluate(slot, profile)
            self.assertEqual(verdict['status'], 'denied', identity)
            self.assertIn('no accepted placement evidence', verdict['reasons'])

    def test_fail_closed_on_unsupported_terrain_and_routes(self):
        document = muse_document()
        profiles = profiles_by_identity(document)
        water = next(s for s in document['slots'] if s['terrain'] == 'water')
        air = next(s for s in document['slots'] if s['terrain'] == 'air')
        for identity in ('Fuefuki', 'BombSarai', 'MiniHoudai'):
            profile = profiles[identity]
            for slot in (water, air):
                reasons = p2_placement.compatibility(slot, profile)
                self.assertTrue(reasons, identity)
        kurage = profiles['Kurage']
        self.assertTrue(p2_placement.compatibility(air, kurage))
        route_less = dict(water)
        route_less['corpse_route'] = False
        self.assertIn('slot lacks a corpse return route',
                      p2_placement.compatibility(route_less, kurage))

    def test_fail_closed_on_protected_slots(self):
        profile = profiles_by_identity(muse_document())['Fuefuki']
        slot = next(s for s in muse_document()['slots']
                    if s['terrain'] == 'ground' and s['corpse_route'])
        sheltered = dict(slot)
        sheltered['protected'] = True
        self.assertIn('slot drop is protected',
                      p2_placement.compatibility(sheltered, profile))

    def test_muse_binding_targets_resolve_and_reject(self):
        for source_id, (_, slot_uid) in MUSE.items():
            targets = catalog.binding_targets_for_muse_sources([source_id])
            self.assertIn(str(slot_uid), targets)
        with self.assertRaises(ValueError):
            catalog.binding_targets_for_muse_sources([23])
        with self.assertRaises(ValueError):
            catalog.binding_targets_for_muse_sources([99])
        with self.assertRaises(ValueError):
            catalog.binding_targets_for_muse_sources([])

    def test_default_document_unchanged(self):
        document = catalog.build_document()
        identities = {p['identity'] for p in document['profiles']}
        for _, (identity, _) in MUSE.items():
            self.assertNotIn(identity, identities)
        groups = catalog.binding_target_groups()
        self.assertEqual(sorted(groups['groups']),
                         ['aquatic', 'dwarf', 'frog', 'ground', 'grub', 'open'])

    def test_no_admission_pollution(self):
        from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate
        admitted = admitted_ids(load_and_validate())
        for source_id in MUSE:
            self.assertNotIn(source_id, admitted)


class NativeContractSyncTests(unittest.TestCase):
    HEADER_SLOTS = {
        'FUEFUKI41': 41,
        'KURAGE57': 57,
        'BOMBSARAI58': 58,
        'MINIHOUDAI78': 78,
    }

    def test_header_slot_constants_match_catalog(self):
        text = NATIVE_HEADER.read_text(encoding='utf-8')
        for suffix, source_id in self.HEADER_SLOTS.items():
            match = re.search(
                rf'MUSE_GENERATED_SLOT_{suffix}\s*=\s*(\d+)u', text)
            self.assertIsNotNone(match, suffix)
            self.assertEqual(int(match.group(1)),
                             catalog.MUSE_GENERATED_SLOTS[source_id], suffix)

    def test_header_declares_registry_queries(self):
        text = NATIVE_HEADER.read_text(encoding='utf-8')
        for symbol in ('pc_p2_generated_placement_is_bound',
                       'pc_p2_generated_placement_bound_count',
                       'pc_p2_generated_placement_forget',
                       'pc_p2_generated_placement_reset'):
            self.assertIn(symbol, text)


def synthetic_log(entries):
    lines = []
    for source_id, uid, bound, reason in entries:
        lines.append(f'P2_SEED_RESOLVE source_id={source_id} target={uid} '
                     f'original_type=11 x=1.0 z=2.0')
        marker = (f'P2_GENERATED_PLACEMENT source_id={source_id} target={uid} '
                  f'generator=7 bound={bound}')
        if reason:
            marker += f' reason={reason}'
        lines.append(marker)
    return '\n'.join(lines) + '\n'


class ObserverTests(unittest.TestCase):
    def test_correlated_cohort(self):
        text = synthetic_log([(sid, uid, 1, None) for sid, (_, uid) in MUSE.items()])
        rows = observer.observe_cohort(text)
        for source_id, (_, uid) in MUSE.items():
            row = rows[source_id]
            self.assertTrue(row['correlated'], source_id)
            self.assertEqual(row['resolved_uid'], uid)
            self.assertEqual(row['bound_uid'], uid)
            self.assertIsNone(row['refusal_reason'])
        self.assertTrue(observer.summary(rows)['all_correlated'])

    def test_missing_bind_is_not_correlated(self):
        text = '\n'.join(
            f'P2_SEED_RESOLVE source_id={sid} target={uid} original_type=11 x=1.0 z=2.0'
            for sid, (_, uid) in MUSE.items()) + '\n'
        rows = observer.observe_cohort(text)
        rolled = observer.summary(rows)
        self.assertFalse(rolled['all_correlated'])
        self.assertEqual(rolled['missing'], [41, 57, 58, 78])

    def test_refused_bind_reports_reason(self):
        text = synthetic_log([(41, 1254096625, 0, 'slot-rejected')])
        row = observer.observe_identity(text, 41)
        self.assertFalse(row['correlated'])
        self.assertFalse(row['bound'])
        self.assertEqual(row['refusal_reason'], 'slot-rejected')

    def test_resolve_bind_mismatch_is_not_correlated(self):
        text = ('P2_SEED_RESOLVE source_id=57 target=689702860 '
                'original_type=0 x=1.0 z=2.0\n'
                'P2_GENERATED_PLACEMENT source_id=57 target=999 '
                'generator=7 bound=1\n')
        row = observer.observe_identity(text, 57)
        self.assertTrue(row['bound'])
        self.assertFalse(row['correlated'])
        self.assertEqual(row['refusal_reason'], 'resolve-bind-uid-mismatch')

    def test_bound_wrong_slot_is_not_correlated(self):
        text = synthetic_log([(57, 999, 1, None)])
        row = observer.observe_identity(text, 57)
        self.assertTrue(row['bound'])
        self.assertFalse(row['correlated'])
        self.assertEqual(row['refusal_reason'], 'slot-not-accepted')

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            observer.observe_identity('P2_SEED_RESOLVE source_id=23 target=1', 23)


if __name__ == '__main__':
    unittest.main()
