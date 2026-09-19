"""Focused P0 tests for the ch_MAT_limited_time import contract (#544)."""
import copy
import tempfile
import unittest
from pathlib import Path

import experimental.content_lanes.p2_challenge_ch_mat_limited_time as ch

ENEMIES = {'Chappy', 'KareOoinu_s'}
TREASURES = {'gem_one'}
LANES_PLAN = Path('docs/PIKMIN_CONTENT_IMPORT_LANES.json')
INVENTORY = Path('docs/PIKMIN2_CONTENT_INVENTORY.json')


def stage_text(floors=1):
    head = '{ {c000} 4 %d {_eof} } %d\n' % (floors, floors)
    body = ''
    for i in range(floors):
        body += ('{ {f000} 4 %d {f001} 4 %d {f008} -1 pool.txt {f015} 4 0 {_eof} }\n'
                 '{ 1 Chappy 10 1 }\n{ 0 }\n{ 0 }\n' % (i, i))
    return head + body


def baseline_details():
    import json
    lanes = json.loads(LANES_PLAN.read_text(encoding='utf-8'))
    entry = next(l for l in lanes['lanes']
                 if l['lane'] == 'p2-challenge-ch_mat_limited_time')
    return copy.deepcopy(entry['details'])


class HashPinTests(unittest.TestCase):
    def test_pin_format_and_triple_consistency(self):
        self.assertRegex(ch.SOURCE_SHA256, r'^[0-9a-f]{64}$')
        self.assertTrue(ch.hash_pin_consistency(str(LANES_PLAN), str(INVENTORY)))

    def test_pin_drift_fails_closed(self):
        import json
        lanes = json.loads(LANES_PLAN.read_text(encoding='utf-8'))
        for lane in lanes['lanes']:
            if lane['lane'] == 'p2-challenge-ch_mat_limited_time':
                lane['source_sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'lanes.json'
            bad.write_text(json.dumps(lanes))
            with self.assertRaises(ValueError):
                ch.hash_pin_consistency(str(bad), str(INVENTORY))
            with self.assertRaises(ValueError):
                ch.hash_pin_consistency(str(LANES_PLAN), str(Path(tmp) / 'missing.json'))

    def test_verify_hash_logic(self):
        with self.assertRaises(ValueError):
            ch.verify_source_hash(b'wrong bytes for this stage')
        with self.assertRaises(ValueError):
            ch.verify_source_hash(b'')
        with self.assertRaises(ValueError):
            ch.verify_source_hash(None)
        self.assertEqual(len(ch.sha256_bytes(b'abc')), 64)
        with self.assertRaises(ValueError):
            ch.sha256_bytes('abc')


class MetadataTests(unittest.TestCase):
    def test_embedded_baseline_validates(self):
        result = ch.validate_stage_metadata(dict(ch.BASELINE_METADATA))
        self.assertEqual(result['starting_pikmin'], 40)
        self.assertEqual(result['floor_seconds'], [130.0])
        self.assertEqual(result['ui_index'], 11)
        self.assertEqual((result['bitter_sprays'], result['spicy_sprays']), (3, 4))

    def test_live_lane_entry_agrees(self):
        report = ch.metadata_agreement(baseline_details())
        self.assertTrue(report['agrees'], report['mismatches'])

    def test_malformed_metadata_fails_closed(self):
        good = dict(ch.BASELINE_METADATA)
        zero = [[0, 0, 0]] * 7
        cases = [
            dict(good, floors=2),
            dict(good, floors='1'),
            dict(good, pikmin_by_native_color_and_maturity=[[0, 0, 0]] * 6 + [[[0]]]),
            dict(good, pikmin_by_native_color_and_maturity=[[0, 0, 0]] * 6),
            dict(good, pikmin_by_native_color_and_maturity=zero),
            dict(good, pikmin_by_native_color_and_maturity='matrix'),
            dict(good, legacy_time=-5),
            dict(good, legacy_time='nan'),
            dict(good, legacy_time='x'),
            dict(good, bitter_sprays=-1),
            dict(good, spicy_sprays=100),
            dict(good, treasure_count_field='x'),
            dict(good, ui_index=30),
            dict(good, ui_index=-1),
            dict(good, floor_seconds=[]),
            dict(good, floor_seconds=[130.0, 5.0]),
            dict(good, floor_seconds=[0]),
            dict(good, floor_seconds=['x']),
        ]
        for details in cases:
            with self.subTest(details=str(details)[:70]), self.assertRaises(ValueError):
                ch.validate_stage_metadata(details)
        broken = dict(good)
        del broken['ui_index']
        with self.assertRaises(ValueError):
            ch.validate_stage_metadata(broken)
        with self.assertRaises(ValueError):
            ch.validate_stage_metadata('not-a-mapping')

    def test_agreement_detects_drift(self):
        drifted = dict(ch.BASELINE_METADATA, spicy_sprays=9)
        report = ch.metadata_agreement(drifted)
        self.assertFalse(report['agrees'])
        drifted = dict(ch.BASELINE_METADATA, floor_seconds=(999.0,))
        self.assertFalse(ch.metadata_agreement(drifted)['agrees'])
        drifted = dict(ch.BASELINE_METADATA,
                       pikmin_by_native_color_and_maturity=tuple([0, 0, 0] for _ in range(7)))
        with self.assertRaises(ValueError):
            ch.metadata_agreement(drifted)


class DecodeBoundaryTests(unittest.TestCase):
    def test_single_floor_stage_decodes(self):
        parsed = ch.decode_source(stage_text(), ENEMIES, TREASURES)
        self.assertEqual(parsed['floor_count'], 1)
        self.assertEqual(ch.occupied_floors(parsed), [1])
        coverage = ch.validate_floor_coverage(parsed)
        self.assertEqual(coverage, [{'floor': 1, 'covered': True}])

    def test_missing_text_and_references_fail_closed(self):
        for bad in ('', '   ', None):
            with self.assertRaises(ValueError):
                ch.decode_source(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            ch.decode_source(stage_text(), None, TREASURES)
        with self.assertRaises(ValueError):
            ch.decode_source(stage_text(), ENEMIES, None)

    def test_malformed_definitions_fail_closed(self):
        good = stage_text()
        cases = [
            good.replace('{ {c000} 4 1 {_eof} } 1', '{ {c000} 4 2 {_eof} } 1'),
            good.replace('{f008} -1 pool.txt', '{f008} 4 pool.txt'),
            good.replace('pool.txt', '../pool.txt'),
            good.replace('Chappy 10 1', 'Nope 10 1'),
            good.replace('Chappy 10 1', 'Chappy x 1'),
            good + ' trailing',
            good[:-2],
        ]
        for text in cases:
            with self.subTest(text=text[:60]), self.assertRaises(ValueError):
                ch.decode_source(text, ENEMIES, TREASURES)

    def test_extra_floor_breaks_coverage(self):
        parsed = ch.decode_source(stage_text(floors=2), ENEMIES, TREASURES)
        self.assertEqual(ch.occupied_floors(parsed), [1, 2])
        with self.assertRaises(ValueError):
            ch.validate_floor_coverage(parsed)

    def test_occupied_floors_rejects_non_struct(self):
        for bad in (None, {}, {'floors': None}, {'floors': [{'first_floor': 0, 'last_floor': 1}]}):
            with self.assertRaises(ValueError):
                ch.occupied_floors(bad)


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_file_exact_error(self):
        with self.assertRaisesRegex(ValueError, 'Source unavailable'):
            ch.read_source_file('user/Mukki/mapunits/caveinfo/ch_MAT_limited_time.txt')

    def test_missing_iso_exact_prerequisite(self):
        with self.assertRaisesRegex(ValueError, 'retail ISO not present'):
            ch.read_iso_entry('output/pikmin2-runtime/pikmin2-source-test.iso')

    def test_non_retail_iso_rejected(self):
        with tempfile.NamedTemporaryFile(suffix='.iso', delete=False) as handle:
            handle.write(b'\x00' * 0x500)
            path = handle.name
        try:
            with self.assertRaisesRegex(ValueError, 'US GPVE01'):
                ch.read_iso_entry(path)
        finally:
            Path(path).unlink()

    def test_hash_needs_bytes(self):
        self.assertEqual(len(ch.sha256_bytes(b'abc')), 64)
        with self.assertRaises(ValueError):
            ch.sha256_bytes('abc')


class PacketTests(unittest.TestCase):
    def test_packet_is_metadata_only(self):
        packet = ch.summarize(dict(ch.BASELINE_METADATA), None)
        self.assertEqual(packet['schema'], ch.SCHEMA)
        self.assertEqual(packet['stage'], 'ch_MAT_limited_time')
        self.assertEqual(packet['floor_coverage'], 1)
        self.assertTrue(packet['baseline_agrees'])
        self.assertEqual(packet['source_sha256'], None)
        self.assertIn('withheld', packet['source_status'])
        self.assertFalse(packet['playable'])
        self.assertFalse(packet['retail_generation'])
        self.assertEqual(packet['stage_metadata']['starting_pikmin'], 40)
        self.assertTrue(any('#136' in blocker for blocker in packet['blockers']))
        self.assertNotIn('enemies', packet['stage_metadata'])
        self.assertNotIn('placements', packet)

    def test_verified_pin_status(self):
        packet = ch.summarize(dict(ch.BASELINE_METADATA), ch.SOURCE_SHA256)
        self.assertIn('hash-verified', packet['source_status'])


if __name__ == '__main__':
    unittest.main()
