"""Tests for the muse l58 Kurage57 generated-birth observer (#498)."""
import unittest

from experimental.pikmin2_muse_kurage import (
    SOURCE_ID,
    is_generated_identity,
    validate_generated_birth,
)

CORRELATED_LOG = """\
:100 P2_SEED_RESOLVE source_id=57 target=349001 original_type=4 x=120.0 z=-40.0
:101 P2_GENERATED_PLACEMENT source_id=57 target=349001 bound=1
:102 P2_KURAGE_TEKI_READY generator=349001 type=4 binding=private_adapter
:103 P2_KURAGE_CORPSE_READY generator=349001 drop=BDT_Normal ledger=onion receipt=corpse:kurage:349001
"""


class GeneratedBirthObserverTests(unittest.TestCase):
    def test_source_id_is_kurage57(self):
        self.assertEqual(SOURCE_ID, 57)

    def test_correlated_birth_passes(self):
        verdict, detail = validate_generated_birth(CORRELATED_LOG)
        self.assertEqual(verdict, 'PASS')
        self.assertIn('349001', detail)
        self.assertTrue(is_generated_identity(CORRELATED_LOG))

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
        # Resolve + binding but no generated-placement claim (current state:
        # l52 has not landed case 57). This is the live gap, not a pass.
        log = ("P2_SEED_RESOLVE source_id=57 target=349001 original_type=4 x=1.0 z=2.0\n"
               "P2_KURAGE_TEKI_READY generator=349001 type=4 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=349001 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:349001\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('P2_GENERATED_PLACEMENT', detail)
        self.assertFalse(is_generated_identity(log))

    def test_missing_resolve_fails(self):
        log = ("P2_GENERATED_PLACEMENT source_id=57 target=349001 bound=1\n"
               "P2_KURAGE_TEKI_READY generator=349001 type=4 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=349001 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:349001\n")
        verdict, _ = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')

    def test_slot_disagreement_fails(self):
        log = ("P2_SEED_RESOLVE source_id=57 target=349001 original_type=4 x=1.0 z=2.0\n"
               "P2_GENERATED_PLACEMENT source_id=57 target=349002 bound=1\n"
               "P2_KURAGE_TEKI_READY generator=349001 type=4 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=349001 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:349001\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('disagreement', detail)

    def test_generator_disagreement_fails(self):
        log = ("P2_SEED_RESOLVE source_id=57 target=349001 original_type=4 x=1.0 z=2.0\n"
               "P2_GENERATED_PLACEMENT source_id=57 target=349001 bound=1\n"
               "P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter\n"
               "P2_KURAGE_CORPSE_READY generator=201001 drop=BDT_Normal ledger=onion "
               "receipt=corpse:kurage:201001\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('disagreement', detail)

    def test_bound_zero_fails(self):
        log = ("P2_SEED_RESOLVE source_id=57 target=349001 original_type=4 x=1.0 z=2.0\n"
               "P2_GENERATED_PLACEMENT source_id=57 target=349001 bound=0 reason=host\n")
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('bound=0', detail)

    def test_wrong_source_id_fails(self):
        log = CORRELATED_LOG.replace('source_id=57', 'source_id=72')
        verdict, _ = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertFalse(is_generated_identity(log))

    def test_injected_birth_taint_fails(self):
        log = CORRELATED_LOG + "P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=349001 injected=health_zero\n"
        verdict, detail = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('injected', detail.lower())
        self.assertFalse(is_generated_identity(log))

    def test_corpse_receipt_mismatch_fails(self):
        log = CORRELATED_LOG.replace('receipt=corpse:kurage:349001',
                                     'receipt=corpse:kurage:201001')
        verdict, _ = validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')

    def test_empty_log_fails(self):
        verdict, _ = validate_generated_birth('')
        self.assertEqual(verdict, 'FAIL')
        self.assertFalse(is_generated_identity(''))


if __name__ == '__main__':
    unittest.main()
