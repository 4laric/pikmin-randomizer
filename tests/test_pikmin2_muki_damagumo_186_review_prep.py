"""Focused tests for the muki-damagumo #186 review-prep adapter (#813).

Engine-free and git-free except for negative worktree checks: malformed pins,
missing worktrees, hash drift and incomplete packets are all refused
fail-closed. The Damagumo diff rendering is pinned field-for-field.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'experimental' / 'pikmin2_muki_damagumo_186_review_prep.py'
spec = importlib.util.spec_from_file_location('muki_damagumo_186_review_prep', MODULE)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


def good_packet():
    return {
        'schema': prep.PACKET_SCHEMA, 'issue': 813,
        'consumer': {'lane': prep.CONSUMER_LANE, 'issue': 740},
        'classification': prep.CLASSIFICATION,
        'damagumo_diff': prep.render_damagumo_diff(),
        'recommendations': {p: {'recommendation': 'decision-pending-missing-diff'}
                            for p in prep.SHARED_FILES},
        'missing_input': 'x',
    }


class ReviewPrepTests(unittest.TestCase):
    def test_damagumo_diff_pins_row_and_files(self):
        diff = prep.render_damagumo_diff()
        self.assertIn('--- a/native/pc_port/pc_bbft.cpp', diff)
        self.assertIn('--- a/native/CMakeLists.txt', diff)
        self.assertIn('"ch_MUKI_damagumo"', diff)
        self.assertIn('c6f2dede22acb37cb0d939b1ee9670b103dc9408d3c9fe100000482891fefa9e', diff)
        self.assertIn('pc_port/pc_p2_challenge_damagumo_stage.cpp', diff)
        self.assertIn('{0,0,50}', diff.replace(' ', ''))

    def test_validate_packet_accepts_complete(self):
        self.assertTrue(prep.validate_packet(good_packet()))

    def test_validate_packet_rejects_schema_and_diff_drift(self):
        bad = good_packet()
        bad['schema'] = 'other/1'
        self.assertFalse(prep.validate_packet(bad))
        bad2 = good_packet()
        bad2['damagumo_diff'] += ' '
        self.assertFalse(prep.validate_packet(bad2))

    def test_validate_packet_rejects_missing_shared_recommendation(self):
        bad = good_packet()
        bad['recommendations'] = {}
        self.assertFalse(prep.validate_packet(bad))

    def test_verify_producer_rejects_bad_pins_and_missing_trees(self):
        spec742 = dict(prep.PRODUCER_742, root_head='0' * 40)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(prep.PrepRejected):
                prep.verify_producer(spec742, tmp, tmp)
            with self.assertRaises(prep.PrepRejected):
                prep.verify_producer(prep.PRODUCER_742, tmp, tmp)

    def test_build_packet_fails_closed_without_worktrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(prep.PrepRejected):
                prep.build_packet(tmp, tmp, tmp, tmp)

    def test_muki_reference_hash_is_pinned(self):
        self.assertEqual(prep.MUKI_PACKET_SHA256,
                         '5361c258a40d39856316663058b39d266897252f00b159e775c0879bd1bde527')
        self.assertEqual(prep.CLASSIFICATION,
                         'edbc7faab44d86e9cffdf0ae2386d52541a1e8eebef618ab1d2ff71f9ff41db4')


if __name__ == '__main__':
    unittest.main()
