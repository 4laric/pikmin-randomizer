"""P0 source audit and import contract for yakushima_1 (issue #158).

Lane `p2-cave-yakushima_1`, category `p2-cave`. This module is an isolated
metadata adapter for THIS source entry only: it decodes the actual retail
definition live from the local disc image, cross-checks it against the lane
contract in `docs/PIKMIN_CONTENT_IMPORT_LANES.json` and an existing catalog
baseline, verifies unit-pool resource closure, and emits an import packet.
It reuses the shared retail parser (`experimental.pikmin2_cave_catalog.parse`)
and asset readers; it duplicates no parser and emits no placements, spawns,
topology, or gameplay claims.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import unit_definition
from experimental.pikmin2_cave_catalog import parse

LANE = 'p2-cave-yakushima_1'
SOURCE_ID = 'yakushima_1'
CAVEINFO_PATH = 'user/Mukki/mapunits/caveinfo/yakushima_1.txt'
PELLET_ARCHIVE = 'user/Abe/Pellet/us/pelletlist_us.szs'
ENEMYINFO = 'src/plugProjectYamashitaU/enemyInfo.cpp'


class ContractMismatch(ValueError):
    pass


def lane_contract(lanes_path, lane=LANE):
    """Load this lane's floor contract from the lanes document (single source)."""
    try:
        lanes = json.loads(Path(lanes_path).read_text(encoding='utf-8'))['lanes']
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ContractMismatch('Unreadable lanes document: ' + str(error)) from None
    entries = [entry for entry in lanes if entry.get('lane') == lane]
    if len(entries) != 1:
        raise ContractMismatch('Lane %r must appear exactly once' % lane)
    details = entries[0].get('details') or {}
    floors = details.get('floors')
    if not isinstance(floors, list) or not floors:
        raise ContractMismatch('Lane %r has no floor contract' % lane)
    contract = []
    for index, floor in enumerate(floors):
        for key in ('first', 'last', 'unit_pool', 'enemy_ids', 'treasure_ids'):
            if key not in floor:
                raise ContractMismatch('Contract floor %d missing %r' % (index, key))
        if not isinstance(floor['enemy_ids'], list) or not floor['enemy_ids']:
            raise ContractMismatch('Contract floor %d has no enemy roster' % index)
        if not isinstance(floor['treasure_ids'], list):
            raise ContractMismatch('Contract floor %d has no treasure roster' % index)
        contract.append(dict(index=index, first=floor['first'], last=floor['last'],
                             unit_pool=floor['unit_pool'], enemy_ids=list(floor['enemy_ids']),
                             treasure_ids=list(floor['treasure_ids'])))
    return dict(lane=lane, source_id=SOURCE_ID, source=CAVEINFO_PATH,
                floor_count=details.get('floor_count', len(contract)), floors=contract)


def read_iso_file(iso_path, disc_path):
    """Read one file from the local disc image and return (bytes, sha256)."""
    iso = Path(iso_path)
    try:
        catalog = disc_files(iso)
    except (OSError, ValueError) as error:
        raise ContractMismatch('Unreadable disc image: ' + str(error)) from None
    if disc_path not in catalog:
        raise ContractMismatch('Disc entry missing: ' + disc_path)
    at, size = catalog[disc_path]
    try:
        with iso.open('rb') as disc:
            disc.seek(at)
            data = disc.read(size)
    except OSError as error:
        raise ContractMismatch('Disc read failed: ' + str(error)) from None
    if len(data) != size:
        raise ContractMismatch('Truncated disc source: ' + disc_path)
    return data, hashlib.sha256(data).hexdigest()


def reference_ids(iso_path, research_root):
    """Enemy IDs from the research source plus treasure IDs from the disc pellet
    archive. These are the exact decoder inputs the shared parser requires."""
    enemy_source = Path(research_root) / ENEMYINFO
    try:
        raw = enemy_source.read_bytes().decode('utf-8')
    except OSError as error:
        raise ContractMismatch('Missing research enemy catalog: ' + str(error)) from None
    enemy_ids = set(re.findall(r'\{"([A-Za-z0-9_]+)"', raw))
    if not enemy_ids:
        raise ContractMismatch('No enemy IDs decoded from research source')
    archive_data, _ = read_iso_file(iso_path, PELLET_ARCHIVE)
    try:
        from experimental.pikmin2_pod import pellet_catalog
        archive = archive_files(archive_data)
        treasure_ids = set()
        for name in ('otakara_config.txt', 'item_config.txt'):
            treasure_ids.update(pellet_catalog(archive[name].decode('shift_jis')))
    except (ValueError, KeyError) as error:
        raise ContractMismatch('Unreadable pellet archive: ' + str(error)) from None
    if not treasure_ids:
        raise ContractMismatch('No treasure IDs decoded from pellet archive')
    return enemy_ids, treasure_ids


def decode_live(iso_path, research_root, source=CAVEINFO_PATH):
    """Decode the actual retail definition from local sources.

    Returns (cave, file_sha256). The returned floor records carry decoded
    enemy/treasure identities, raw source tokens, weights, gates and caps;
    weights are definition inputs, never spawn instances (see module packet).
    """
    data, digest = read_iso_file(iso_path, source)
    try:
        text = data.decode('shift_jis')
    except UnicodeDecodeError as error:
        raise ContractMismatch('Caveinfo is not shift_jis: ' + str(error)) from None
    enemy_ids, treasure_ids = reference_ids(iso_path, research_root)
    try:
        cave = parse(text, enemy_ids, treasure_ids)
    except ValueError as error:
        raise ContractMismatch('Retail definition failed shared parse: ' + str(error)) from None
    cave.update(cave_id=SOURCE_ID, source=source)
    return cave, digest


def verify_contract(cave, contract):
    """Cross-check a decoded definition against the lane floor contract.

    Compares floor coverage, per-floor ranges, unit pools (raw `f008`), raw
    enemy source-token sequences and treasure sequences. Returns the coverage
    report; raises ContractMismatch on the first divergence.
    """
    if cave.get('cave_id') != contract['source_id'] or cave.get('source') != contract['source']:
        raise ContractMismatch('Decoded identity does not match lane contract source')
    if cave.get('floor_count') != contract['floor_count']:
        raise ContractMismatch('Floor count %r != contract %r'
                               % (cave.get('floor_count'), contract['floor_count']))
    if len(cave.get('floors', ())) != len(contract['floors']):
        raise ContractMismatch('Decoded floor records do not cover the contract')
    coverage = []
    for decoded, wanted in zip(cave['floors'], contract['floors']):
        if (decoded['first_floor'], decoded['last_floor']) != (wanted['first'], wanted['last']):
            raise ContractMismatch('Floor range %r != contract %r'
                                   % ((decoded['first_floor'], decoded['last_floor']),
                                      (wanted['first'], wanted['last'])))
        pool = decoded['parameters'].get('f008')
        if pool != wanted['unit_pool']:
            raise ContractMismatch('Floor %d unit pool %r != contract %r'
                                   % (wanted['first'], pool, wanted['unit_pool']))
        tokens = [enemy['source_token'] for enemy in decoded['enemies']]
        if tokens != wanted['enemy_ids']:
            raise ContractMismatch('Floor %d enemy tokens diverge from contract' % wanted['first'])
        treasures = [treasure['treasure_id'] for treasure in decoded['treasures']]
        if treasures != wanted['treasure_ids']:
            raise ContractMismatch('Floor %d treasure roster diverges from contract' % wanted['first'])
        coverage.append(dict(floor=wanted['first'], unit_pool=pool,
                             enemies=len(tokens), treasures=len(treasures),
                             gates=len(decoded['gates']), caps=len(decoded['caps'])))
    return coverage


def verify_closure(cave, catalog):
    """Verify unit-pool resource closure against an existing catalog baseline.

    Every referenced pool must exist in the catalog with decoded unit
    definitions; the pool source path is recorded. Returns the closure report;
    raises ContractMismatch on a missing pool.
    """
    pools = (catalog.get('unit_pools') or {})
    closure = []
    for floor in cave['floors']:
        pool = floor['parameters'].get('f008')
        entry = pools.get(pool)
        if not entry or not entry.get('units'):
            raise ContractMismatch('Unit pool without decoded closure: %r' % pool)
        closure.append(dict(floor=floor['first_floor'], unit_pool=pool,
                            source=entry.get('source'),
                            units=[unit['name'] for unit in entry['units']]))
    return closure


def p1_blockers(coverage, closure):
    """Exact native/framework prerequisites for a future P1 runtime import."""
    pools = sorted({row['unit_pool'] for row in closure})
    return [
        'Native cave/generator import hook for caveinfo definitions (integration owner); '
        'this packet decodes definitions only and wires no native path.',
        'Unit-pool asset staging for %s via the existing unit pipeline; packet records '
        'pool sources, not staged assets.' % ', '.join(pools),
        'Seeded topology/hole selection and per-floor generator pins are unproven for '
        'these %d floors; weights in the packet are definition inputs, not placements.'
        % len(coverage),
        'Enemy admission resolved per enemy roster at P1; unresolved admission blocks '
        'promotion, not this preparatory packet.',
    ]


def build_packet(iso_path, research_root, lanes_path, catalog, output):
    """Run the full P0 audit and write the import packet JSON. Returns (packet, path)."""
    contract = lane_contract(lanes_path)
    cave, digest = decode_live(iso_path, research_root)
    coverage = verify_contract(cave, contract)
    closure = verify_closure(cave, catalog)
    packet = dict(
        schema=1, lane=LANE, source_id=SOURCE_ID, source=CAVEINFO_PATH,
        source_sha256=digest, floor_count=cave['floor_count'],
        definition_count=cave['definition_count'], coverage=coverage, closure=closure,
        blockers=p1_blockers(coverage, closure), generated=False,
        limitations=[
            'Weights/counts are definition inputs, not final spawn instances or placements.',
            'No seeded topology, hole selection, radial distribution or restart identity is generated.',
            'Metadata only; no claim of imported or playable content.',
        ])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / ('content-%s-p0.json' % SOURCE_ID.replace('_', '-'))
    path.write_text(json.dumps(packet, indent=2) + '\n', encoding='utf-8')
    return packet, path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--research', type=Path, required=True)
    parser.add_argument('--lanes', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
    packet, path = build_packet(args.iso, args.research, args.lanes, catalog, args.output)
    print(json.dumps(dict(packet=str(path), floors=packet['floor_count'],
                          source_sha256=packet['source_sha256'])))
