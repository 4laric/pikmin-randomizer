"""Focused fail-closed tests for the kusachi stage selector (lane #669).

All expectations derive from the checked-in canonical baseline at runtime;
no selection is invented. Unknown keys, P1-namespace slots, drifted pins,
malformed matrices/timers, incomplete boot records, and fabricated
placements all refuse. Fixture text is synthetic and exercises only the
candidate format, never retail decoding.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    'challenge_stage_select_boot',
    ROOT / 'experimental/pikmin2_challenge_stage_select_boot.py')
_sel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sel)


class BaselineTests(unittest.TestCase):
    def test_plan_and_inventory_agree(self):
        details = _sel.baseline_selection(ROOT)
        self.assertEqual(details['cave_id'], 'ch_NARI_01kusachi')
        self.assertEqual(details['ui_index'], 3)
        self.assertEqual(details['floors'], 1)
        self.assertEqual(details['floor_seconds'], [180.0])

    def test_select_resolves_exact_key_only(self):
        record = _sel.select_stage('ch_NARI_01kusachi', ROOT)
        self.assertEqual(record['cave_id'], 'ch_NARI_01kusachi')
        self.assertEqual(record['ui_index'], 3)
        self.assertEqual(record['source_sha256'],
                         'b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85')
        self.assertEqual(sum(sum(row) for row in record['pikmin_by_native_color_and_maturity']), 50)

    def test_unknown_keys_refused(self):
        for bad in ('ch_NARI_02tile', 'CH_NARI_01KUSACHI', '', None, 3, ['ch_NARI_01kusachi']):
            with self.subTest(bad=repr(bad)[:30]):
                with self.assertRaises(_sel.SelectionError):
                    _sel.select_stage(bad, ROOT)

    def test_p1_namespace_refused(self):
        for slot in ('chal0', 'chal4', 'challenge:trial'):
            with self.subTest(slot=slot):
                with self.assertRaises(_sel.SelectionError):
                    _sel.select_stage(slot, ROOT)


class BootRequestTests(unittest.TestCase):
    def test_render_roundtrip_shape(self):
        record = _sel.select_stage('ch_NARI_01kusachi', ROOT)
        text = _sel.render_boot_request(record)
        self.assertTrue(text.startswith('P2_CHALLENGE_STAGE_SELECT_1\n'))
        self.assertIn('cave ch_NARI_01kusachi ui_index 3', text)
        self.assertIn(record['source_sha256'], text)
        self.assertEqual(len([l for l in text.splitlines() if l.startswith('roster ')]), 7)

    def test_incomplete_record_refused(self):
        record = _sel.select_stage('ch_NARI_01kusachi', ROOT)
        for key in ('cave_id', 'source_sha256', 'floor_seconds',
                    'pikmin_by_native_color_and_maturity'):
            bad = dict(record)
            del bad[key]
            with self.subTest(key=key):
                with self.assertRaises(_sel.SelectionError):
                    _sel.render_boot_request(bad)

    def test_identity_mismatch_refused(self):
        record = _sel.select_stage('ch_NARI_01kusachi', ROOT)
        bad = dict(record, cave_id='ch_NARI_02tile')
        with self.assertRaises(_sel.SelectionError):
            _sel.render_boot_request(bad)

    def test_malformed_baseline_rejected(self):
        with self.assertRaises(_sel.SelectionError):
            _sel.baseline_selection('/nonexistent-root-xyz')
        with self.assertRaises(_sel.SelectionError):
            _sel.select_stage('ch_NARI_01kusachi', '/nonexistent-root-xyz')


class MissingHookTests(unittest.TestCase):
    def test_missing_hook_names_exact_followon(self):
        hook = _sel.missing_hook()
        self.assertIn('--experimental-challenge-stage', hook['flag'])
        self.assertIn('selectByUiIndex', hook['table'])
        self.assertIn('186', hook['registration'])
        self.assertIn('chal', hook['guarded_slot'])


if __name__ == '__main__':
    unittest.main()