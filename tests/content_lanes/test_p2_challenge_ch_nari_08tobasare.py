"""Synthetic P0 boundary tests for ch_NARI_08tobasare; no disc image required."""
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# The reserved adapter filename carries hyphens per the lane plan, so it is not
# importable by dotted path; load it from its exact reserved location.
_ADAPTER_PATH = ROOT / 'experimental/content_lanes/p2-challenge-ch_nari_08tobasare.py'
_spec = importlib.util.spec_from_file_location('p2_challenge_ch_nari_08tobasare_adapter', _ADAPTER_PATH)
_adapter = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _adapter
_spec.loader.exec_module(_adapter)

EXPECTED_DETAILS = _adapter.EXPECTED_DETAILS
EXPECTED_FLOORS = _adapter.EXPECTED_FLOORS
EXPECTED_PIKMIN_ROSTER = _adapter.EXPECTED_PIKMIN_ROSTER
SOURCE_ID = _adapter.SOURCE_ID
SOURCE_PATH = _adapter.SOURCE_PATH
SOURCE_SHA256 = _adapter.SOURCE_SHA256
UNSUPPORTED_REFERENCES = _adapter.UNSUPPORTED_REFERENCES
ImportContractError = _adapter.ImportContractError
MissingPrerequisite = _adapter.MissingPrerequisite
audit_packet = _adapter.audit_packet
check_floor_coverage = _adapter.check_floor_coverage
cross_check_catalog = _adapter.cross_check_catalog
decode_full = _adapter.decode_full
decode_structure = _adapter.decode_structure
resource_closure_requirements = _adapter.resource_closure_requirements
source_prerequisites = _adapter.source_prerequisites
stage_contract = _adapter.stage_contract
starting_population = _adapter.starting_population
verify_source = _adapter.verify_source


def floor_block(index, pool, version=0):
    version_token = '{f015} 4 %d ' % version if version else ''
    return '{ {f000} 4 %d {f001} 4 %d %s{f008} -1 %s {_eof} }' % (index, index, version_token, pool)


def stage_text(pools=('unit_a.txt', 'unit_b.txt'), version=0):
    parts = ['{ {c000} 4 %d {_eof} }' % len(pools), str(len(pools))]
    for index, pool in enumerate(pools):
        parts.append(floor_block(index, pool, version))
        parts.append('{ 0 }')  # enemy roster
        parts.append('{ 0 }')  # treasure roster
        parts.append('{ 0 }')  # gate roster
        if version:
            parts.append('{ 0 }')  # cap block
    return '\n'.join(parts) + '\n'


def details():
    return dict(EXPECTED_DETAILS)


class PinTests(unittest.TestCase):
    def test_module_pins_match_canonical_plan_and_inventory(self):
        plan = json.loads((ROOT / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json').read_text(encoding='utf-8-sig'))
        inventory = json.loads((ROOT / 'docs/PIKMIN2_CONTENT_INVENTORY.json').read_text(encoding='utf-8-sig'))
        lanes = [lane for lane in plan['lanes'] if lane['lane'] == 'p2-challenge-ch_nari_08tobasare']
        self.assertEqual(len(lanes), 1)
        lane = lanes[0]
        stages = [s for s in inventory['challenge']['stages'] if s['cave_id'] == SOURCE_ID]
        self.assertEqual(len(stages), 1)
        stage = stages[0]
        self.assertEqual(lane['source'], SOURCE_PATH)
        self.assertEqual(lane['source_sha256'], SOURCE_SHA256)
        self.assertEqual(inventory['source_sha256'][SOURCE_PATH], SOURCE_SHA256)
        self.assertEqual({k: lane['details'][k] for k in EXPECTED_DETAILS}, EXPECTED_DETAILS)
        self.assertEqual(lane['details']['floors'], EXPECTED_FLOORS)
        for key, value in EXPECTED_DETAILS.items():
            self.assertEqual(stage[key], value, 'inventory detail: ' + key)
        self.assertEqual(stage['pikmin_by_native_color_and_maturity'], EXPECTED_PIKMIN_ROSTER)

    def test_verify_source_enforces_pin(self):
        data = 'fixture-bytes'.encode('utf-8')
        pin = hashlib.sha256(data).hexdigest()
        record = verify_source(data, pin)
        self.assertTrue(record['verified'])
        self.assertEqual(record['sha256'], pin)
        self.assertEqual(record['source_id'], SOURCE_ID)
        with self.assertRaises(ImportContractError):
            verify_source(data)
        with self.assertRaises(ImportContractError):
            verify_source(b'')
        with self.assertRaises(ImportContractError):
            verify_source('not-bytes')


class StructureTests(unittest.TestCase):
    def test_two_floor_structure_walks_roster_sections(self):
        result = decode_structure(stage_text())
        self.assertEqual(result['definition_count'], 2)
        self.assertEqual([(f['first_floor'], f['last_floor']) for f in result['floors']], [(1, 1), (2, 2)])
        self.assertEqual(result['floors'][0]['unit_pool_path'], 'user/Mukki/mapunits/units/unit_a.txt')
        self.assertEqual(result['floors'][1]['unit_pool_path'], 'user/Mukki/mapunits/units/unit_b.txt')
        coverage = check_floor_coverage(result['floors'])
        self.assertTrue(coverage['complete'])
        self.assertEqual(coverage['covered_floors'], [1, 2])

    def test_versioned_cap_sections_decode(self):
        result = decode_structure(stage_text(('unit_a.txt', 'unit_b.txt'), version=1))
        self.assertEqual([f['version'] for f in result['floors']], [1, 1])
        self.assertTrue(check_floor_coverage(result['floors'])['complete'])

    def test_malformed_framing_fails_closed(self):
        broken = [
            '',
            '   ',
            '{ {c000} 4 2 {_eof} ',
            '{ {c000} 4 2 {_eof} }\n3\n' + floor_block(0, 'unit_a.txt') + '\n{ 0 }\n{ 0 }\n{ 0 }\n',
            '{ {c999} 4 2 {_eof} }\n2\n' + stage_text().split('\n', 2)[2],
            '{ {c000} 4 1 {_eof} }\n1\n' + floor_block(1, 'unit_a.txt') + '\n{ 0 }\n{ 0 }\n{ 0 }\n',
            '{ {c000} 4 1 {_eof} }\n1\n{ {f000} 4 1 {f001} 4 0 {_eof} }\n{ 0 }\n{ 0 }\n{ 0 }\n',
            '{ {c000} 4 1 {_eof} }\n1\n{ {f001} 4 0 {_eof} }\n{ 0 }\n{ 0 }\n{ 0 }\n',
            '{ {c000} 4 1 {_eof} }\n1\n' + floor_block(0, 'unit_a.txt') + '\n{ 0 }\n{ 0 }\n',
            '{ {c000} 4 1 {_eof} }\n1\n' + floor_block(0, 'unit_a.txt') + '\n{ 0 }\n{ 0 }\n{ 0 }\n{ 0 }\n',
        ]
        for index, text in enumerate(broken):
            with self.subTest(case=index):
                with self.assertRaises(ImportContractError):
                    check_floor_coverage(decode_structure(text)['floors'])

    def test_unsafe_pool_name_rejected(self):
        text = '{ {c000} 4 1 {_eof} }\n1\n{ {f000} 4 0 {f001} 4 0 {f008} -1 ../evil.txt {_eof} }\n{ 0 }\n{ 0 }\n{ 0 }\n'
        with self.assertRaises(ImportContractError):
            decode_structure(text)

    def test_coverage_gap_and_overlap_rejected(self):
        with self.assertRaises(ImportContractError):
            check_floor_coverage([dict(first_floor=1, last_floor=1)])
        with self.assertRaises(ImportContractError):
            check_floor_coverage([dict(first_floor=1, last_floor=1), dict(first_floor=1, last_floor=2)])
        with self.assertRaises(ImportContractError):
            check_floor_coverage([dict(first_floor=0, last_floor=2)])
        with self.assertRaises(ImportContractError):
            check_floor_coverage([dict(first_floor=1, last_floor=3)])


class ContractTests(unittest.TestCase):
    def test_catalog_cross_check(self):
        self.assertTrue(cross_check_catalog(details(), EXPECTED_PIKMIN_ROSTER)['match'])
        bad = details()
        bad['floor_seconds'] = [100.0, 100.0]
        with self.assertRaises(ImportContractError):
            cross_check_catalog(bad, EXPECTED_PIKMIN_ROSTER)
        with self.assertRaises(ImportContractError):
            cross_check_catalog(details(), [[0, 0, 0]] * 7)

    def test_full_decode_needs_catalogs(self):
        with self.assertRaises(MissingPrerequisite) as ctx:
            decode_full(stage_text(), set(), set())
        self.assertTrue(ctx.exception.prerequisites)
        with self.assertRaises(MissingPrerequisite):
            decode_full(stage_text(), {'Foo'}, set())

    def test_starting_population_pins(self):
        population = starting_population(EXPECTED_PIKMIN_ROSTER)
        self.assertEqual(population['total'], 50)
        self.assertEqual([r['total'] for r in population['rows']], [25, 20, 0, 5, 0, 0, 0])
        with self.assertRaises(ImportContractError):
            starting_population([[0, 0, 0]])
        with self.assertRaises(ImportContractError):
            starting_population([[0, 0]] * 7)
        with self.assertRaises(ImportContractError):
            starting_population([[0, 0, -1]] + [[0, 0, 0]] * 6)

    def test_stage_contract_is_metadata_only(self):
        contract = stage_contract(details(), EXPECTED_PIKMIN_ROSTER)
        self.assertTrue(contract['metadata_only'])
        self.assertEqual(contract['floors'], 2)
        self.assertEqual(contract['floor_seconds'], [150.0, 100.0])
        self.assertEqual(contract['bitter_sprays'], 2)
        self.assertEqual(contract['spicy_sprays'], 0)
        self.assertEqual(contract['ui_index'], 24)
        self.assertEqual(contract['starting_population']['total'], 50)
        self.assertTrue(contract['unsupported_references'])
        with self.assertRaises(ImportContractError):
            stage_contract(details(), [[0, 0, 0]] * 7)

    def test_resource_closure_lists_exact_needs(self):
        structure = decode_structure(stage_text())
        closure = resource_closure_requirements(structure)
        self.assertFalse(closure['closed'])
        self.assertEqual(len(closure['unit_pools']), 2)
        self.assertTrue(closure['missing'])
        self.assertTrue(closure['unsupported_references'])
        self.assertTrue(any(p['path'] == SOURCE_PATH for p in closure['missing'] if p['kind'] == 'disc_path'))
        with self.assertRaises(ImportContractError):
            resource_closure_requirements(dict(floors=[]))

    def test_prerequisites_name_exact_retail_inputs(self):
        prereqs = source_prerequisites()
        self.assertTrue(prereqs)
        by_kind = {p['kind'] for p in prereqs}
        self.assertTrue({'disc_image', 'disc_path', 'enemy_catalog', 'treasure_catalog'} <= by_kind)
        disc = [p for p in prereqs if p['kind'] == 'disc_path'][0]
        self.assertEqual(disc['expected_sha256'], SOURCE_SHA256)

    def test_unsupported_references_cover_named_acceptance(self):
        items = ' '.join(entry['item'] for entry in UNSUPPORTED_REFERENCES)
        for token in ('TheKey', 'scoring', 'retry', 'generator', 'admission'):
            self.assertIn(token, items)
        owners = {entry['owner'] for entry in UNSUPPORTED_REFERENCES}
        self.assertTrue({'#136', '#129', '#130/#131'} <= owners)

    def test_audit_packet_without_source_bytes(self):
        packet = audit_packet(details(), EXPECTED_PIKMIN_ROSTER)
        self.assertFalse(packet['decoded'])
        self.assertIsNone(packet['coverage'])
        self.assertTrue(packet['missing_prerequisites'])
        self.assertTrue(packet['catalog']['match'])
        self.assertTrue(packet['unsupported_references'])

    def test_audit_packet_with_fixture_bytes(self):
        data = stage_text().encode('shift_jis')
        pin = hashlib.sha256(data).hexdigest()
        packet = audit_packet(details(), EXPECTED_PIKMIN_ROSTER, source_bytes=data, expected_sha256=pin)
        self.assertTrue(packet['decoded'])
        self.assertTrue(packet['coverage']['complete'])
        self.assertEqual(len(packet['resource_closure']['unit_pools']), 2)
        with self.assertRaises(ImportContractError):
            audit_packet(details(), EXPECTED_PIKMIN_ROSTER, source_bytes=data)


if __name__ == '__main__':
    unittest.main()

