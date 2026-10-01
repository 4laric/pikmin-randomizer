"""Synthetic carrier-landing boundary tests; never touches a build or game code."""
import unittest

from experimental.pikmin2_waterwraith_carrier_landing import (
    CANDIDATE_BASE,
    CATALOG_BLOB,
    CATALOG_MARKERS,
    CATALOG_PATH,
    NATIVE_FILES,
    NATIVE_PIN,
    PACKAGING_BLOB,
    PACKAGING_MARKERS,
    PACKAGING_PATH,
    CarrierRejected,
    check_ancestry,
    check_carrier_text,
    check_catalog_packaging_consistency,
    check_markers,
    git_blob,
    landable_packet,
    sha256_bytes,
)

CATALOG_FIXTURE = 'spec WATERWRAITH_CANDIDATE_SPEC slot 568677317 id 99\n'
PACKAGING_FIXTURE = 'bind BlackMan99 sidecar Tyre98 id 99\n'


class MarkerTests(unittest.TestCase):
    def test_required_markers_present(self):
        self.assertTrue(check_markers(CATALOG_FIXTURE, CATALOG_MARKERS, 'catalog')['present'])
        self.assertTrue(check_markers(PACKAGING_FIXTURE, PACKAGING_MARKERS, 'packaging')['present'])

    def test_missing_or_malformed_text_fails_closed(self):
        with self.assertRaises(CarrierRejected):
            check_markers('spec only, no slot\n', CATALOG_MARKERS, 'catalog')
        for bad in ('', '   ', None, 42, b'x', ['x']):
            with self.subTest(text=repr(bad)):
                with self.assertRaises(CarrierRejected):
                    check_markers(bad, CATALOG_MARKERS, 'catalog')

    def test_consistency_requires_shared_slot_scope(self):
        self.assertTrue(check_catalog_packaging_consistency(CATALOG_FIXTURE, PACKAGING_FIXTURE)['consistent'])
        with self.assertRaises(CarrierRejected):
            check_catalog_packaging_consistency('spec WATERWRAITH_CANDIDATE_SPEC slot 568677317\n', PACKAGING_FIXTURE)


class PinTests(unittest.TestCase):
    def test_blob_gate_enforces_exact_bytes(self):
        import hashlib
        data = b'carrier-bytes'
        pin = hashlib.sha256(data).hexdigest()
        record = check_carrier_text('carrier.txt', data, pin, ('carrier',))
        self.assertEqual(record['sha256'], pin)
        with self.assertRaises(CarrierRejected):
            check_carrier_text('carrier.txt', b'other-bytes', pin, ('carrier',))
        with self.assertRaises(CarrierRejected):
            check_carrier_text('carrier.txt', data, pin, ('carrier', 'absent-marker'))
        with self.assertRaises(CarrierRejected):
            sha256_bytes(b'')
        with self.assertRaises(CarrierRejected):
            sha256_bytes('not-bytes')

    def test_git_helpers_fail_closed(self):
        with self.assertRaises(CarrierRejected):
            git_blob(r'C:\nonexistent-repo-xyz', 'HEAD', 'file.txt')
        with self.assertRaises(CarrierRejected):
            git_blob(r'C:\Users\alari\pikmin-randomizer', 'deadbeef' * 5, 'README.md')
        with self.assertRaises(CarrierRejected):
            check_ancestry(r'C:\nonexistent-repo-xyz', 'a', 'b')

    def test_recorded_pins_have_expected_shape(self):
        self.assertEqual(len(CATALOG_BLOB), 40)
        self.assertEqual(len(PACKAGING_BLOB), 40)
        self.assertTrue(all(len(v) == 40 for v in NATIVE_FILES.values()))
        self.assertEqual(len(NATIVE_PIN), 40)
        self.assertEqual(len(CANDIDATE_BASE), 40)

    def test_packet_skeleton_names_downstream(self):
        packet = landable_packet(['c1', 'c2'], 'c2')
        self.assertEqual(packet['candidate_base'], CANDIDATE_BASE)
        self.assertEqual(packet['downstream'], ['#572', 'recovery f42ecca0', '#575/#576'])
        self.assertIn('native_recorded_only', packet['carriers'])


if __name__ == '__main__':
    unittest.main()
