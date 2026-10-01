"""Tests for the kusachi persistence observation adapter (#781).

Synthetic receipts only (no runtime). Verifies the fail-closed contract: a
sequence is OBSERVED only with its exact single kusachi-bound marker in a
guard-clean wired run; retry/re-entry need two identical fresh-process runs;
any foreign stage or refusal is leakage.
"""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[2] / 'experimental' / 'content_lanes' / \
    'p2-challenge-ch_nari_01kusachi_persistence.py'
spec = importlib.util.spec_from_file_location('kusachi_persistence', MODULE)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

STAGE = 'P2_CHALLENGE_STAGE_FLAG cave=ch_NARI_01kusachi\n'
PROBES = ''.join('P2_CHALLENGE_%s stage=ch_NARI_01kusachi\n' % p for p in adapter.PROBES)
BOOT = 'P2_KUSACHI_PERSIST_BOOT tick=1 total=20 blue=20 wired=20\n'
PASS = 'PASS KUSACHI_PERSIST wired=1 total=20\n'
CAPDOWN = 'P2_FIXTURE_CAPTAIN_DOWN tick=0 hp=0.000 orima_dead=1 dead_state=0 outcome=BLOCKED\n'
GOOD = STAGE + PROBES + BOOT + PASS


class PersistenceTests(unittest.TestCase):
    def test_probe_set_is_complete(self):
        self.assertEqual(set(adapter.PROBES),
                         {'SAVE_KEY', 'LOAD_KEY', 'CLEAR', 'HIGHSCORE', 'UNLOCK',
                          'RECEIPT_DEDUP', 'REENTRY'})

    def test_clean_run_observes_probes(self):
        seq, leakage, dedup = adapter.classify_sequences(GOOD)
        self.assertEqual(seq['save']['status'], 'OBSERVED')
        self.assertEqual(seq['reload']['status'], 'OBSERVED')
        self.assertEqual(seq['re-entry']['status'], 'OBSERVED')
        self.assertEqual(seq['retry']['status'], 'UNTESTED')
        self.assertEqual(leakage['status'], 'CLEAN')
        self.assertEqual(dedup['status'], 'SINGLE')

    def test_captain_down_unproves_everything(self):
        seq, leakage, dedup = adapter.classify_sequences(GOOD + CAPDOWN)
        for name, gate in seq.items():
            self.assertEqual(gate['status'], 'UNTESTED', name)
        self.assertEqual(dedup['status'], 'UNPROVEN')

    def test_foreign_stage_is_leakage(self):
        bad = GOOD + 'P2_CHALLENGE_SAVE_KEY stage=ch_MUKI_metal\n'
        _seq, leakage, _dedup = adapter.classify_sequences(bad)
        self.assertEqual(leakage['status'], 'LEAKED')

    def test_double_receipt_breaks_dedup(self):
        bad = GOOD + 'P2_CHALLENGE_SAVE_KEY stage=ch_NARI_01kusachi\n'
        seq, _leakage, dedup = adapter.classify_sequences(bad)
        self.assertEqual(seq['save']['status'], 'UNTESTED')
        self.assertEqual(dedup['status'], 'UNPROVEN')

    def test_identical_passes_replay(self):
        verdict = adapter.compare_runs(GOOD, GOOD)
        self.assertEqual(verdict['status'], 'REPLAYED')

    def test_divergent_passes_are_untested(self):
        other = GOOD.replace('P2_CHALLENGE_REENTRY stage=ch_NARI_01kusachi\n', '')
        verdict = adapter.compare_runs(GOOD, other)
        self.assertEqual(verdict['status'], 'UNTESTED')


if __name__ == '__main__':
    unittest.main()
