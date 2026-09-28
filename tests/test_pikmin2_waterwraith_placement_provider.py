"""Provider tests for Waterwraith99 generated placement (lane #575).

Covers: root/native slot sync, the preserved #492 muse contract, the
candidate-only Waterwraith profile, negative unsupported/mismatched/stale
behavior, and the real generation-to-seed source99-to-bind correlation API.
No ADMIT: accepted_gates stays empty and `evaluate` must keep denying.
"""
import os
import re
import unittest
from pathlib import Path

from randomizer import p2_placement_catalog as catalog
from randomizer.p2_placement import compatibility, evaluate

ROOT = Path(__file__).resolve().parents[1]

WATERWRAITH_SLOT = 568677317
MUSE_SLOTS = {41: 1254096625, 57: 689702860, 58: 1787125272, 78: 328297937}


def native_header():
    """Locate the private/maintained native header for slot-sync proof."""
    candidates = []
    env = os.environ.get('PIKMIN_NATIVE_ROOT')
    if env:
        candidates.append(Path(env) / 'pc_port' / 'pc_p2_generated_placement.h')
    candidates.append(ROOT / 'native' / 'pc_port' / 'pc_p2_generated_placement.h')
    candidates.append(ROOT.parent / 'autofill-native-575'
                      / 'pc_port' / 'pc_p2_generated_placement.h')
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding='utf-8')
    raise unittest.SkipTest('native header not available for slot-sync proof')


def synthetic_log(resolve_uid, bound_uid, generator=245001, bound=1, source=99,
                  reason=None):
    lines = [
        f'P2_SEED_RESOLVE source_id={source} target={resolve_uid} '
        f'original_type=3 x=1.0 z=2.0',
        f'P2_GENERATED_PLACEMENT source_id={source} target={bound_uid} '
        f'generator={generator} bound={bound}'
        + (f' reason={reason}' if reason else ''),
    ]
    return '\n'.join(lines)


class NativeSlotSyncTests(unittest.TestCase):
    def test_waterwraith_slot_constant_matches_catalog(self):
        text = native_header()
        match = re.search(
            r'WATERWRAITH_GENERATED_SLOT_BLACKMAN99\s*=\s*(\d+)u', text)
        self.assertIsNotNone(match, 'waterwraith slot constant missing')
        self.assertEqual(int(match.group(1)),
                         catalog.WATERWRAITH_GENERATED_SLOTS[99])
        self.assertEqual(int(match.group(1)), WATERWRAITH_SLOT)

    def test_muse_slot_constants_unchanged(self):
        text = native_header()
        for suffix, source_id in (('FUEFUKI41', 41), ('KURAGE57', 57),
                                  ('BOMBSARAI58', 58), ('MINIHOUDAI78', 78)):
            match = re.search(
                rf'MUSE_GENERATED_SLOT_{suffix}\s*=\s*(\d+)u', text)
            self.assertIsNotNone(match, suffix)
            self.assertEqual(int(match.group(1)), MUSE_SLOTS[source_id])
            self.assertEqual(int(match.group(1)),
                             catalog.MUSE_GENERATED_SLOTS[source_id])

    def test_native_declares_waterwraith_predicate_and_slot(self):
        text = native_header()
        for symbol in ('pc_p2_generated_placement_is_waterwraith_candidate',
                       'pc_p2_generated_placement_waterwraith_slot'):
            self.assertIn(symbol, text)


class PreservedMuseContractTests(unittest.TestCase):
    def test_muse_slots_exact(self):
        self.assertEqual(dict(catalog.MUSE_GENERATED_SLOTS), MUSE_SLOTS)
        self.assertEqual(catalog.MUSE_CANDIDATE_IDS, frozenset(MUSE_SLOTS))

    def test_waterwraith_not_in_muse_or_ordinary_pools(self):
        self.assertNotIn(99, catalog.MUSE_CANDIDATE_IDS)
        self.assertNotIn(99, catalog.WATERWRAITH_HELPER_IDS)
        self.assertNotEqual(catalog.WATERWRAITH_CANDIDATE_IDS,
                            catalog.MUSE_CANDIDATE_IDS)
        ordinary = {profile['identity'] for profile in catalog.candidate_profiles()}
        self.assertNotIn('BlackMan', ordinary)
        self.assertNotIn('Tyre', ordinary)

    def test_helper_tyre_never_seeded(self):
        self.assertEqual(catalog.WATERWRAITH_HELPER_IDS, frozenset({98}))
        self.assertNotIn(98, catalog.WATERWRAITH_CANDIDATE_IDS)
        self.assertNotIn(98, catalog.MUSE_CANDIDATE_IDS)


class WaterwraithProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = catalog.waterwraith_candidate_profile()

    def test_candidate_only(self):
        self.assertEqual(self.profile['identity'], 'BlackMan')
        self.assertEqual(self.profile['family_lane'], 31)
        self.assertEqual(self.profile['terrains'], ['ground'])
        self.assertTrue(self.profile['requires_corpse_route'])
        self.assertFalse(self.profile['is_boss'])
        self.assertEqual(self.profile['helper_budget'], 0)
        self.assertEqual(self.profile['accepted_gates'], [])
        self.assertEqual(self.profile['accepted_slot_uids'], [WATERWRAITH_SLOT])

    def test_source_id_and_slot_helpers(self):
        self.assertEqual(catalog.waterwraith_candidate_source_ids(),
                         {'BlackMan': 99})
        self.assertEqual(catalog.waterwraith_accepted_slot(99), WATERWRAITH_SLOT)
        self.assertIsNone(catalog.waterwraith_accepted_slot(41))

    def test_accepted_slot_is_constraint_compatible(self):
        document = catalog.build_waterwraith_document()
        slot = next(s for s in document['slots'] if s['uid'] == WATERWRAITH_SLOT)
        self.assertEqual(compatibility(slot, self.profile), [])
        self.assertIn(str(WATERWRAITH_SLOT),
                      catalog.binding_targets_for_waterwraith())

    def test_default_deny_still_denies(self):
        document = catalog.build_waterwraith_document()
        slot = next(s for s in document['slots'] if s['uid'] == WATERWRAITH_SLOT)
        result = evaluate(slot, self.profile)
        self.assertEqual(result['status'], 'denied')
        self.assertIn('no accepted placement evidence', result['reasons'])

    def test_mismatched_slot_is_denied(self):
        document = catalog.build_waterwraith_document()
        other = next(s for s in document['slots']
                     if s['uid'] != WATERWRAITH_SLOT and s['terrain'] == 'ground')
        result = evaluate(other, self.profile)
        self.assertEqual(result['status'], 'denied')
        self.assertIn('slot has no accepted placement evidence for this identity',
                      result['reasons'])

    def test_unsupported_source_id_raises(self):
        with self.assertRaises(ValueError):
            catalog.binding_targets_for_waterwraith(source_id=41)
        with self.assertRaises(ValueError):
            catalog.binding_targets_for_waterwraith(source_id=98)

    def test_waterwraith_document_keeps_muse_profiles(self):
        document = catalog.build_waterwraith_document()
        identities = {p['identity'] for p in document['profiles']}
        for identity in ('Fuefuki', 'Kurage', 'BombSarai', 'MiniHoudai',
                         'BlackMan'):
            self.assertIn(identity, identities)
        self.assertNotIn(99, [
            uid for profile in document['profiles']
            for uid in profile.get('accepted_slot_uids', [])
            if profile['identity'] != 'BlackMan'
        ])


class CorrelationApiTests(unittest.TestCase):
    def test_correlated_triple(self):
        result = catalog.waterwraith_generated_triple(
            synthetic_log(WATERWRAITH_SLOT, WATERWRAITH_SLOT))
        self.assertTrue(result['correlated'], result['reason'])
        self.assertEqual(result['resolved_uid'], WATERWRAITH_SLOT)
        self.assertEqual(result['bound_uid'], WATERWRAITH_SLOT)
        self.assertEqual(result['generator'], 245001)
        self.assertIsNone(result['reason'])

    def test_missing_seed_resolve(self):
        text = synthetic_log(WATERWRAITH_SLOT, WATERWRAITH_SLOT).splitlines()[1]
        result = catalog.waterwraith_generated_triple(text)
        self.assertFalse(result['correlated'])
        self.assertEqual(result['reason'], 'missing-seed-resolve')

    def test_missing_bind(self):
        text = synthetic_log(WATERWRAITH_SLOT, WATERWRAITH_SLOT).splitlines()[0]
        result = catalog.waterwraith_generated_triple(text)
        self.assertFalse(result['correlated'])
        self.assertEqual(result['reason'], 'missing-generated-placement')

    def test_uid_mismatch(self):
        result = catalog.waterwraith_generated_triple(
            synthetic_log(WATERWRAITH_SLOT, 111222))
        self.assertFalse(result['correlated'])
        self.assertEqual(result['reason'], 'resolve-bind-uid-mismatch')

    def test_slot_rejected_refusal(self):
        result = catalog.waterwraith_generated_triple(
            synthetic_log(WATERWRAITH_SLOT, WATERWRAITH_SLOT, bound=0,
                          reason='slot-rejected'))
        self.assertFalse(result['correlated'])
        self.assertEqual(result['reason'], 'bind-refused:slot-rejected')

    def test_other_source_id_ignored(self):
        result = catalog.waterwraith_generated_triple(
            synthetic_log(WATERWRAITH_SLOT, WATERWRAITH_SLOT, source=41))
        self.assertFalse(result['correlated'])
        self.assertEqual(result['reason'], 'no-source99-legs')

    def test_empty_log(self):
        result = catalog.waterwraith_generated_triple('')
        self.assertFalse(result['correlated'])
        self.assertEqual(result['reason'], 'no-source99-legs')


if __name__ == '__main__':
    unittest.main()
