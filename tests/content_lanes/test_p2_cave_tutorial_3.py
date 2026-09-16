"""Focused P0 tests for the tutorial_3 import-contract adapter (issue #153)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

# The reserved adapter is loaded by file path so the reserved hyphenated
# filename needs no package re-export; the integrator's tree provides
# experimental/content_lanes/__init__.py when it lands content lanes.
_ADAPTER = importlib.util.spec_from_file_location(
    'p2_cave_tutorial_3_adapter',
    Path(__file__).resolve().parents[2] / 'experimental' / 'content_lanes' / 'p2-cave-tutorial_3.py')
t3 = importlib.util.module_from_spec(_ADAPTER)
_ADAPTER.loader.exec_module(t3)

# Verified local retail source (read-only); live tests skip cleanly if absent.
ISO = Path(r'C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso')
DECOMP = Path(r'C:\Users\alari\pikmin-randomizer\native\pikmin2-research')
LIVE = ISO.is_file() and (DECOMP / 'src/plugProjectYamashitaU/enemyInfo.cpp').is_file()

ENEMIES = {'Chappy', 'KareOoinu_s', 'Rkabuto'}
TREASURES = {'gem_one', 'map01'}
LANE_PLAN = Path('docs/PIKMIN_CONTENT_IMPORT_LANES.json')


def floor_block(index, pool='pool.txt', enemy='Chappy 10 1', treasures='0'):
    params = ('{ {f000} 4 %d {f001} 4 %d {f008} -1 %s {f015} 4 0 {_eof} }'
              % (index, index, pool))
    return '%s\n{ 1 %s }\n{ %s }\n{ 0 }\n' % (params, enemy, treasures)


def cave_text(count=8, pool='pool.txt', enemy='Chappy 10 1'):
    head = '{ {c000} 4 %d {_eof} } %d\n' % (count, count)
    return head + ''.join(floor_block(i, pool, enemy) for i in range(count))


def parsed_from_baseline(pool_override=None, drop_floor=None):
    floors = []
    for number, pool, enemies, treasures in t3.BASELINE_FLOORS:
        if number == drop_floor:
            continue
        floors.append(dict(definition_index=number - 1,
                           first_floor=number, last_floor=number,
                           parameters={'f008': pool_override.get(number, pool)
                                       if pool_override else pool},
                           enemies=[dict(source_token=tok, enemy_id=tok)
                                    for tok in enemies],
                           treasures=[dict(treasure_id=name) for name in treasures],
                           gates=[], caps=[]))
    return dict(floors=floors)


class DecodeBoundaryTests(unittest.TestCase):
    def test_minimal_eight_floor_cave_decodes(self):
        parsed = t3.decode_source(cave_text(), ENEMIES, TREASURES)
        self.assertEqual(parsed['floor_count'], 8)
        self.assertEqual(t3.occupied_floors(parsed), list(range(1, 9)))
        coverage = t3.validate_floor_coverage(parsed)
        self.assertEqual(len(coverage), 8)
        self.assertTrue(all(row['covered'] for row in coverage))

    def test_missing_text_and_references_fail_closed(self):
        for bad in ('', '   ', None):
            with self.assertRaises(ValueError):
                t3.decode_source(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            t3.decode_source(cave_text(), None, TREASURES)
        with self.assertRaises(ValueError):
            t3.decode_source(cave_text(), ENEMIES, None)

    def test_malformed_definitions_fail_closed(self):
        good = cave_text()
        cases = [
            good.replace('{ {c000} 4 8 {_eof} } 8', '{ {c000} 4 7 {_eof} } 8'),
            good.replace('{f008} -1 pool.txt', '{f008} 4 pool.txt'),
            good.replace('pool.txt', '../pool.txt'),
            good.replace('Chappy 10 1', 'Nope 10 1'),
            good.replace('Chappy 10 1', 'Chappy x 1'),
            good.replace('{ 1 Chappy 10 1 }\n{ 0 }',
                         '{ 1 Chappy 10 1 }\n{ 1 missing 12 }'),
            good + ' trailing',
            good[:-2],
        ]
        for text in cases:
            with self.subTest(text=text[:60]), self.assertRaises(ValueError):
                t3.decode_source(text, ENEMIES, TREASURES)

    def test_short_cave_breaks_coverage(self):
        parsed = t3.decode_source(cave_text(count=7), ENEMIES, TREASURES)
        self.assertEqual(t3.occupied_floors(parsed), list(range(1, 8)))
        with self.assertRaises(ValueError):
            t3.validate_floor_coverage(parsed)

    def test_overlapping_floors_rejected(self):
        text = ('{ {c000} 4 2 {_eof} } 2\n' + floor_block(0) + floor_block(0))
        with self.assertRaises(ValueError):
            t3.decode_source(text, ENEMIES, TREASURES)

    def test_occupied_floors_rejects_non_struct(self):
        for bad in (None, {}, {'floors': None}, {'floors': [{'first_floor': 0, 'last_floor': 1}]}):
            with self.assertRaises(ValueError):
                t3.occupied_floors(bad)


class BaselineTests(unittest.TestCase):
    def test_baseline_shape_matches_issue(self):
        self.assertEqual(t3.CAVE_ID, 'tutorial_3')
        self.assertEqual(t3.EXPECTED_FLOORS, 8)
        self.assertEqual([row[0] for row in t3.BASELINE_FLOORS], list(range(1, 9)))
        enemies = sum((len(row[2]) for row in t3.BASELINE_FLOORS))
        treasures = sum((len(row[3]) for row in t3.BASELINE_FLOORS))
        self.assertEqual((enemies, treasures), (72, 12))

    def test_baseline_guarded_against_lane_entry(self):
        self.assertTrue(t3.baseline_matches_lane_entry(str(LANE_PLAN)))
        with self.assertRaises(ValueError):
            t3.baseline_matches_lane_entry('docs/does-not-exist.json')

    def test_agreement_passes_on_exact_baseline(self):
        report = t3.baseline_agreement(parsed_from_baseline())
        self.assertEqual(len(report), 8)
        self.assertTrue(all(row['agrees'] for row in report))

    def test_agreement_reports_pool_and_roster_drift(self):
        report = t3.baseline_agreement(parsed_from_baseline(pool_override={3: 'other.txt'}))
        self.assertFalse(report[2]['agrees'])
        self.assertTrue(any('unit_pool' in m for m in report[2]['mismatches']))
        altered = parsed_from_baseline()
        altered['floors'][0]['enemies'] = altered['floors'][0]['enemies'][:-1]
        report = t3.baseline_agreement(altered)
        self.assertFalse(report[0]['agrees'])

    def test_agreement_flags_missing_floor(self):
        report = t3.baseline_agreement(parsed_from_baseline(drop_floor=8))
        self.assertFalse(report[7]['agrees'])
        self.assertIn('missing', report[7]['reason'].lower())


class ReferenceTests(unittest.TestCase):
    def test_unsupported_references_listed(self):
        parsed = parsed_from_baseline()
        parsed['floors'][0]['enemies'].append(dict(source_token='Nope', enemy_id='Nope'))
        parsed['floors'][0]['treasures'].append(dict(treasure_id='missing'))
        known_enemies = {row['enemy_id'] for floor in parsed['floors'] for row in floor['enemies']
                         if row['enemy_id'] != 'Nope'}
        known_treasures = {row['treasure_id'] for floor in parsed['floors'] for row in floor['treasures']
                           if row['treasure_id'] != 'missing'}
        missing = t3.unsupported_references(parsed, known_enemies, known_treasures)
        self.assertEqual(missing, dict(enemies=['Nope'], treasures=['missing']))

    def test_unsupported_references_need_sets(self):
        parsed = parsed_from_baseline()
        with self.assertRaises(ValueError):
            t3.unsupported_references(parsed, None, set())
        with self.assertRaises(ValueError):
            t3.unsupported_references(parsed, set(), None)

    def test_resource_closure_manifest(self):
        manifest = t3.resource_closure_manifest(parsed_from_baseline())
        self.assertEqual(len(manifest), 8)
        self.assertEqual(manifest[0]['unit_pool'], '3_MAT_nor4_hit2_blk1_snow.txt')
        self.assertEqual(manifest[7]['unit_pool'], '1_units_queen_b_tsuchi.txt')
        with self.assertRaises(ValueError):
            t3.resource_closure_manifest(dict(floors=[dict(first_floor=1, last_floor=1,
                                                           parameters={})]))


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_file_exact_error(self):
        with self.assertRaisesRegex(ValueError, 'Source unavailable'):
            t3.read_source_file('user/Mukki/mapunits/caveinfo/tutorial_3.txt')

    def test_missing_iso_exact_prerequisite(self):
        with self.assertRaisesRegex(ValueError, 'retail ISO not present'):
            t3.read_iso_entry('output/pikmin2-runtime/pikmin2-source-test.iso')

    def test_non_retail_iso_rejected(self):
        with tempfile.NamedTemporaryFile(suffix='.iso', delete=False) as handle:
            handle.write(b'\x00' * 0x500)
            path = handle.name
        try:
            with self.assertRaisesRegex(ValueError, 'US GPVE01'):
                t3.read_iso_entry(path)
        finally:
            Path(path).unlink()

    def test_hash_needs_bytes(self):
        self.assertEqual(len(t3.sha256_bytes(b'abc')), 64)
        with self.assertRaises(ValueError):
            t3.sha256_bytes('abc')
        with self.assertRaises(ValueError):
            t3.sha256_bytes(None)


class PacketTests(unittest.TestCase):
    def test_packet_is_metadata_only(self):
        parsed = parsed_from_baseline()
        known_enemies = {row['enemy_id'] for floor in parsed['floors'] for row in floor['enemies']}
        known_treasures = {row['treasure_id'] for floor in parsed['floors'] for row in floor['treasures']}
        packet = t3.summarize(parsed, 'deadbeef', known_enemies, known_treasures)
        self.assertEqual(packet['schema'], t3.SCHEMA)
        self.assertEqual(packet['cave'], 'tutorial_3')
        self.assertEqual(packet['floor_coverage'], 8)
        self.assertTrue(packet['baseline_agrees'])
        self.assertFalse(packet['playable'])
        self.assertFalse(packet['retail_generation'])
        rows = [row for floor in packet['floors'] for row in floor['enemies']]
        self.assertEqual(len(rows), 72)
        self.assertTrue(all(row['runtime_status'] == 'unsupported' for row in rows))
        self.assertTrue(all(row['placement'] is None for row in rows))
        self.assertTrue(packet['blockers'])
        self.assertTrue(any('#129' in blocker for blocker in packet['blockers']))
        self.assertEqual(packet['unsupported'], dict(enemies=[], treasures=[]))


class LiveDecodeTests(unittest.TestCase):
    """Live decode against the verified local retail ISO; skips cleanly if absent."""

    @unittest.skipUnless(LIVE, 'local retail ISO or decomp reference not present')
    def test_live_decode_covers_eight_floors(self):
        result = t3.decode_live(ISO, DECOMP)
        self.assertEqual(result['parsed']['floor_count'], 8)
        self.assertEqual(t3.occupied_floors(result['parsed']), list(range(1, 9)))
        report = t3.baseline_agreement(result['parsed'])
        self.assertTrue(all(row['agrees'] for row in report), report)

    @unittest.skipUnless(LIVE, 'local retail ISO or decomp reference not present')
    def test_live_observed_hashes_recorded(self):
        result = t3.decode_live(ISO, DECOMP)
        self.assertRegex(result['cave_sha256'], r'^[0-9a-f]{64}$')
        self.assertGreater(result['cave_bytes'], 0)
        self.assertEqual(len(result['unit_pools']), 8)
        for name, info in result['unit_pools'].items():
            self.assertRegex(info['sha256'], r'^[0-9a-f]{64}$', name)
            self.assertGreater(info['bytes'], 0)
            self.assertTrue(info['units'])

    @unittest.skipUnless(LIVE, 'local retail ISO or decomp reference not present')
    def test_live_unit_arc_texts_closure_complete(self):
        result = t3.decode_live(ISO, DECOMP)
        for name, info in result['unit_pools'].items():
            self.assertEqual(info['missing_assets'], [], name)

    @unittest.skipUnless(LIVE, 'local retail ISO or decomp reference not present')
    def test_live_packet_is_metadata_only(self):
        packet = t3.live_packet(ISO, DECOMP)
        self.assertTrue(packet['baseline_agrees'])
        self.assertTrue(packet['unit_closure_complete'])
        self.assertTrue(packet['decoded_from_source'])
        self.assertFalse(packet['playable'])
        self.assertFalse(packet['retail_generation'])
        self.assertEqual(packet['schema'], t3.SCHEMA)
        self.assertEqual(packet['unsupported'], dict(enemies=[], treasures=[]))
        self.assertGreater(packet['enemy_catalog_size'], 50)
        self.assertGreater(packet['treasure_catalog_size'], 50)
        rows = [row for floor in packet['floors'] for row in floor['enemies']]
        self.assertEqual(len(rows), 72)
        self.assertTrue(all(row['placement'] is None for row in rows))
        self.assertTrue(all(row['runtime_status'] == 'unsupported' for row in rows))


class ReferenceBoundaryTests(unittest.TestCase):
    def test_missing_decomp_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'decomp enemyInfo.cpp'):
                t3.read_reference_sets(directory, 'missing.iso')

    def test_unit_asset_closure_flags_every_missing_member(self):
        missing = t3.unit_asset_closure({}, [dict(name='room_a')])
        self.assertEqual(missing, [t3.BASE + '/arc/room_a/arc.szs',
                                   t3.BASE + '/arc/room_a/texts.szs'])

    def test_unit_asset_closure_clean_when_present(self):
        index = {t3.BASE + '/arc/room_a/arc.szs': (0, 1),
                 t3.BASE + '/arc/room_a/texts.szs': (0, 1)}
        self.assertEqual(t3.unit_asset_closure(index, [dict(name='room_a')]), [])

    def test_read_member_missing_is_exact(self):
        with self.assertRaisesRegex(ValueError, 'absent from ISO'):
            t3.read_member('x.iso', {}, t3.SOURCE_PATH)

    def test_decode_live_rejects_non_retail_bytes(self):
        with tempfile.NamedTemporaryFile(suffix='.iso', delete=False) as handle:
            handle.write(b'\x00' * 0x500)
            path = handle.name
        try:
            with self.assertRaisesRegex(ValueError, 'US GPVE01'):
                t3.decode_live(path, DECOMP if LIVE else 'missing')
        finally:
            Path(path).unlink()


if __name__ == '__main__':
    unittest.main()
