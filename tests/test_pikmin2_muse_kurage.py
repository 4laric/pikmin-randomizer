"""Tests for the muse l58 Kurage57 generated-birth observer (#498)."""
import unittest

from experimental.pikmin2_muse_kurage import (
    ACCEPTED_SLOT,
    SOURCE_ID,
    is_generated_identity,
    validate_generated_birth,
)

# Reviewed contract (muse-placement l52): accepted slot 689702860, placement
# marker carries the engine generator.
CORRELATED_LOG = """\
:100 P2_SEED_RESOLVE source_id=57 target=689702860 original_type=0 x=120.0 z=-40.0
:101 P2_GENERATED_PLACEMENT source_id=57 target=689702860 generator=689702860 bound=1
:102 P2_KURAGE_TEKI_READY generator=689702860 type=0 binding=private_adapter
:103 P2_KURAGE_CORPSE_READY generator=689702860 drop=BDT_Normal ledger=onion receipt=corpse:kurage:689702860
"""

LEGACY_FORMAT_LOG = """\
P2_SEED_RESOLVE source_id=57 target=689702860 original_type=0 x=1.0 z=2.0
P2_GENERATED_PLACEMENT source_id=57 target=689702860 bound=1
P2_KURAGE_TEKI_READY generator=689702860 type=0 binding=private_adapter
P2_KURAGE_CORPSE_READY generator=689702860 drop=BDT_Normal ledger=onion receipt=corpse:kurage:689702860
"""


class GeneratedBirthObserverTests(unittest.TestCase):
    def test_source_id_is_kurage57(self):
        self.assertEqual(SOURCE_ID, 57)
        self.assertEqual(ACCEPTED_SLOT, '689702860')

    def test_correlated_birth_passes(self):
        verdict, detail = validate_generated_birth(CORRELATED_LOG)
        self.assertEqual(verdict, 'PASS')
        self.assertIn('689702860', detail)
        self.assertTrue(is_generated_identity(CORRELATED_LOG))

    def test_legacy_format_birth_passes(self):
        # Pre-contract markers without the generator field fall back to the
        # strict slot==generator check on the accepted slot.
        verdict, _ = validate_generated_birth(LEGACY_FORMAT_LOG)
        self.assertEqual(verdict, 'PASS')
        self.assertTrue(is_generated_identity(LEGACY_FORMAT_LOG))

    def test_chain_passes_with_distinct_generator(self):
        # Triple-chain: placement ties the accepted slot to a differing
        # engine generator, and the Kurage binding names that generator.
        log = ("P2_SEED_RESOLVE source_id=57 target=689702860 original_type=0 x=1.0 z=2.0\n"
               "P2_GENERATED_PLACEMENT source_id=57 target=689702860 generator=775001 bound=1\n"
               "P2_KURAGE_TEKI_READY generator=775001 type=0 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=775001 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:775001\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'PASS')
        self.assertIn('689702860', detail)
        self.assertIn('775001', detail)

    def test_legacy_auto_bind_is_not_generated(self):
        # The historical l29 sidecar path: TEKI_READY for 201001 with no
        # resolve/placement markers. Must fail, never pass as generated.
        log = ("P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=201001 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:201001\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('auto-bind', detail)
        self.assertFalse(is_generated_identity(log))

    def test_missing_placement_fails(self):
        # Resolve + binding but no generated-placement claim.
        log = ("P2_SEED_RESOLVE source_id=57 target=689702860 original_type=0 x=1.0 z=2.0\n"
               "P2_KURAGE_TEKI_READY generator=689702860 type=0 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=689702860 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:689702860\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('P2_GENERATED_PLACEMENT', detail)
        self.assertFalse(is_generated_identity(log))

    def test_missing_resolve_fails(self):
        log = ("P2_GENERATED_PLACEMENT source_id=57 target=689702860 generator=689702860 bound=1\n"
               "P2_KURAGE_TEKI_READY generator=689702860 type=0 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=689702860 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:689702860\n")
        verdict, _ = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')

    def test_slot_disagreement_fails(self):
        log = ("P2_SEED_RESOLVE source_id=57 target=689702860 original_type=0 x=1.0 z=2.0\n"
               "P2_GENERATED_PLACEMENT source_id=57 target=349002 generator=349002 bound=1\n"
               "P2_KURAGE_TEKI_READY generator=689702860 type=0 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=689702860 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:689702860\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('disagreement', detail)

    def test_slot_not_accepted_fails(self):
        # All markers agree, but on a slot that is not the reviewed one.
        log = CORRELATED_LOG.replace('689702860', '349001')
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('slot-not-accepted', detail)
        self.assertFalse(is_generated_identity(log))

    def test_generator_disagreement_fails(self):
        log = ("P2_SEED_RESOLVE source_id=57 target=689702860 original_type=0 x=1.0 z=2.0\n"
               "P2_GENERATED_PLACEMENT source_id=57 target=689702860 generator=689702860 bound=1\n"
               "P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=201001 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:201001\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('disagreement', detail)

    def test_legacy_format_generator_disagreement_fails(self):
        # Pre-contract marker (no generator field): teki generator must equal
        # the slot.
        log = LEGACY_FORMAT_LOG.replace('generator=689702860',
                                        'generator=201001').replace(
            'receipt=corpse:kurage:689702860', 'receipt=corpse:kurage:201001')
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('disagreement', detail)

    def test_bound_zero_fails(self):
        log = ("P2_SEED_RESOLVE source_id=57 target=689702860 original_type=0 x=1.0 z=2.0\n"
               "P2_GENERATED_PLACEMENT source_id=57 target=689702860 generator=689702860 bound=0 reason=slot-rejected\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('bound=0', detail)

    def test_wrong_source_id_fails(self):
        log = CORRELATED_LOG.replace('source_id=57', 'source_id=72')
        verdict, _ = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertFalse(is_generated_identity(log))

    def test_injected_birth_taint_fails(self):
        log = CORRELATED_LOG + "P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=689702860 injected=health_zero\n"
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('injected', detail.lower())
        self.assertFalse(is_generated_identity(log))

    def test_corpse_receipt_mismatch_fails(self):
        log = CORRELATED_LOG.replace('receipt=corpse:kurage:689702860',
                                     'receipt=corpse:kurage:201001')
        verdict, _ = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')

    def test_empty_log_fails(self):
        verdict, _ = validate_generated_birth('')
        self.assertEqual(verdict, 'FAIL')
        self.assertFalse(is_generated_identity(''))


if __name__ == '__main__':
    unittest.main()
