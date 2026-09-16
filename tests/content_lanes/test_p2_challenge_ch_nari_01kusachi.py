"""Focused P0 tests for the ch_NARI_01kusachi import-contract adapter (#533).

Pure unit tests: no disc image, no native build, no runtime. Synthetic
caveinfo documents below exercise the shared-parser boundary only and are
never presented as source evidence; actual source bytes were unavailable, so
every positive path asserts the adapter reports hash/closure status honestly.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# content_lanes/ carries no __init__.py (lane owns exactly its three reserved
# files), so load the adapter by path instead of package import.
_spec = importlib.util.spec_from_file_location(
    'p2_challenge_ch_nari_01kusachi',
    ROOT / 'experimental/content_lanes/p2-challenge-ch_nari_01kusachi.py')
_adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_adapter)

CAVE_ID = _adapter.CAVE_ID
EXPECTED_FLOORS = _adapter.EXPECTED_FLOORS
MISSING_SOURCE_PREREQUISITE = _adapter.MISSING_SOURCE_PREREQUISITE
SOURCE_PATH = _adapter.SOURCE_PATH
SOURCE_SHA256 = _adapter.SOURCE_SHA256
MissingSourcePrerequisite = _adapter.MissingSourcePrerequisite
SourceHashMismatch = _adapter.SourceHashMismatch
StageDecodeError = _adapter.StageDecodeError
build_import_packet = _adapter.build_import_packet
decode_stage = _adapter.decode_stage
locate_source = _adapter.locate_source
resource_closure = _adapter.resource_closure
source_identity = _adapter.source_identity
verify_source_bytes = _adapter.verify_source_bytes
write_packet = _adapter.write_packet

ENEMIES = {'Bulborb', 'DwarfBulborb'}
TREASURES = {'MiracleGas'}

ONE_FLOOR = """{ {c000} 4 1 {_eof} }
1
{ {f000} 4 0 {f001} 4 0 {f008} -1 testpool {_eof} }
{ 1 Bulborb 10 1 }
{ 0 }
{ 0 }
"""

TWO_FLOORS = """{ {c000} 4 2 {_eof} }
2
{ {f000} 4 0 {f001} 4 0 {f008} -1 testpool {_eof} }
{ 1 Bulborb 10 1 }
{ 0 }
{ 0 }
{ {f000} 4 1 {f001} 4 1 {f008} -1 testpool {_eof} }
{ 1 DwarfBulborb 20 1 }
{ 0 }
{ 0 }
"""


def test_identity_matches_canonical_inventory_and_plan():
    inventory = json.loads((ROOT / 'docs/PIKMIN2_CONTENT_INVENTORY.json').read_text(encoding='utf-8'))
    stages = inventory['challenge']['stages']
    entry = next(e for e in stages if e['cave_id'] == CAVE_ID)
    assert entry['cave_path'] == SOURCE_PATH
    assert inventory['source_sha256'][SOURCE_PATH] == SOURCE_SHA256
    assert entry['floors'] == EXPECTED_FLOORS
    identity = source_identity()
    assert identity['roster'] == entry['pikmin_by_native_color_and_maturity']
    assert identity['floor_seconds'] == entry['floor_seconds']
    assert identity['legacy_time'] == entry['legacy_time']
    assert (identity['bitter_sprays'], identity['spicy_sprays']) == (entry['bitter_sprays'], entry['spicy_sprays'])
    assert identity['ui_index'] == entry['ui_index']
    plan = json.loads((ROOT / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json').read_text(encoding='utf-8'))
    lane = next(e for e in plan['lanes'] if e['lane'] == 'p2-challenge-ch_nari_01kusachi')
    assert lane['source'] == SOURCE_PATH and lane['source_sha256'] == SOURCE_SHA256
    assert lane['issue'] == 533


def test_missing_source_reports_exact_prerequisite():
    for roots in ([], ['C:/nonexistent-disc-root']):
        try:
            locate_source(roots)
        except MissingSourcePrerequisite as exc:
            assert 'PIKMIN2.iso' in str(exc) and SOURCE_PATH in str(exc) and SOURCE_SHA256 in str(exc)
        else:
            raise AssertionError('expected MissingSourcePrerequisite')


def test_locate_source_finds_staged_file(tmp_path):
    staged = tmp_path / Path(*SOURCE_PATH.split('/'))
    staged.parent.mkdir(parents=True)
    staged.write_bytes(b'staged-bytes')
    assert locate_source([str(tmp_path)]) == staged


def test_verify_rejects_unpinned_bytes():
    try:
        verify_source_bytes(b'synthetic-bytes-are-not-source')
    except SourceHashMismatch as exc:
        assert SOURCE_SHA256 in str(exc)
    else:
        raise AssertionError('expected SourceHashMismatch')


def test_decode_accepts_single_floor_structure():
    cave = decode_stage(ONE_FLOOR, ENEMIES, TREASURES)
    assert cave['floor_count'] == 1 and len(cave['floors']) == 1
    floor = cave['floors'][0]
    assert (floor['first_floor'], floor['last_floor']) == (1, 1)
    assert floor['enemies'][0]['enemy_id'] == 'Bulborb'


def test_decode_rejects_wrong_floor_count():
    try:
        decode_stage(TWO_FLOORS, ENEMIES, TREASURES)
    except StageDecodeError as exc:
        assert 'Floor coverage mismatch' in str(exc)
    else:
        raise AssertionError('expected StageDecodeError')


def test_decode_rejects_malformed_inputs():
    bad = ['', '{ {c000} 4 1', '{ {c000} 4 1 {_eof} }\n1\n',
           ONE_FLOOR.replace('Bulborb', 'NotAnEnemy'),
           ONE_FLOOR.replace('{ 1 Bulborb 10 1 }', '{ 2 Bulborb 10 1 }')]
    for text in bad:
        try:
            decode_stage(text, ENEMIES, TREASURES)
        except StageDecodeError:
            continue
        raise AssertionError('expected StageDecodeError for %r' % text[:40])


def test_closure_lists_pools_unresolved():
    closure = resource_closure(decode_stage(ONE_FLOOR, ENEMIES, TREASURES))
    assert closure['unit_pools'] == ['testpool'] and closure['resolved'] is False
    assert closure['prerequisite'] == MISSING_SOURCE_PREREQUISITE


def test_packet_is_honest_without_source():
    verification = dict(source_path=SOURCE_PATH, sha256=None, verified=False,
                         note='Actual source bytes unavailable; hash not validated')
    packet = build_import_packet(decode_stage(ONE_FLOOR, ENEMIES, TREASURES), verification)
    assert packet['schema'] == 1 and packet['issue'] == 533
    assert packet['floor_coverage']['decoded_floor_count'] == EXPECTED_FLOORS
    assert packet['verification']['verified'] is False
    assert packet['resource_closure']['resolved'] is False
    assert packet['blockers']['runtime_dependencies'] == [136, 137, 129, 130, 131]
    assert any('No claim of playability' in limit for limit in packet['limitations'])


def test_write_packet_round_trips(tmp_path):
    verification = dict(source_path=SOURCE_PATH, sha256=None, verified=False, note='unavailable')
    packet = build_import_packet(decode_stage(ONE_FLOOR, ENEMIES, TREASURES), verification)
    record = write_packet(packet, tmp_path / 'p0-533')
    path = Path(record['path'])
    assert path.is_file()
    import hashlib
    assert record['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert json.loads(path.read_text(encoding='utf-8'))['identity']['cave_id'] == CAVE_ID
