'''Forest_1 headed-run legal-asset verification and staging (issue #681).

Verifies the exact legal assets the forest_1 headed run needs against the
recorded asset-inputs.json and the local disc with EXACT reads (offset, size,
sha256), stages the present ones into a headed-run asset layout, and records
ABSENT candidates with their exact failed read. No invented assets.

A light manifest enumeration of each floor pool (names only) is used to
discover unit archives; unit-blob GEOMETRY decode, lease/run and native
execution stay with the #154 owner and controller and are not duplicated.

No shared edits, no runtime, no ADMIT. All six runtime gates UNTESTED.'''

from __future__ import annotations

import argparse

import hashlib

import json

import shutil

from pathlib import Path

CAVE_ID = 'forest_1'
SOURCE_CAVEINFO = 'user/Mukki/mapunits/caveinfo/forest_1.txt'
UNIT_POOL_DIR = 'user/Mukki/mapunits/units'
UNIT_ARC_DIR = 'user/Mukki/mapunits/arc'
COURSE_ARC_DIR = 'user/Kando/map/forest'
ABE_COURSE_DIR = 'user/Abe/map/forest'
UNIT_SUFFIXES = ('arc.szs', 'texts.szs')
COURSE_ARCHIVES = ('arc.szs', 'texts.szs')

# Catalogued per-floor unit pools (docs/PIKMIN_CONTENT_IMPORT_LANES.json lane
# p2-cave-forest_1). Names only; geometry decode is the #154 owner scope.
FLOOR_POOLS = (
    (1, 1, '1_units_cent3_tsuchi.txt'),
    (2, 2, '1_units_cent2_tsuchi.txt'),
    (3, 3, '2_ABE_norhiba_blkhiba_tsuchi.txt'),
    (4, 4, '2_ABE_mid1_nor3_tsuchi.txt'),
    (5, 5, '1_units_boss_tsuchi.txt'),
)

# Documented wrong-path probes: exact failed reads prove these are NOT the
# retail locations (the real course data is inside the Kando arc/texts
# archives, and the pools live under mapunits/units, not mapunits/).
ABSENT_PROBES = (
    'user/Mukki/mapunits/1_units_cent3_tsuchi.txt',
    'user/Kando/map/forest/forest.bmd',
    'user/Kando/map/forest/collision.bin',
    'user/Kando/map/forest/waterbox.txt',
    'user/Kando/map/forest/mapcode.bin',
)

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_member(iso, member, members):
    '''Exact read of one disc member; returns (data, record) or ABSENT record.'''
    locator = members.get(member)
    if locator is None:
        return None, {'member': member, 'status': 'ABSENT',
                      'failed_read': 'member not present in disc index'}
    offset, size = locator
    with Path(iso).open('rb') as stream:
        stream.seek(offset)
        data = stream.read(size)
    if len(data) != size:
        return None, {'member': member, 'status': 'ABSENT',
                      'failed_read': 'short read: got %d of %d' % (len(data), size)}
    return data, {'member': member, 'status': 'PRESENT', 'offset': offset,
                  'size': size, 'sha256': sha256_bytes(data)}

def pool_member(pool):
    return UNIT_POOL_DIR + '/' + pool


def enumerate_units(pool_text):
    '''Names only from one pool blob, reusing the shared unit parser.'''
    from experimental.pikmin2_cave import unit_definition
    return [unit['name'] for unit in unit_definition(pool_text)]


def unit_asset_members(unit):
    return [UNIT_ARC_DIR + '/' + unit + '/' + suffix for suffix in UNIT_SUFFIXES]


def course_members():
    members = [COURSE_ARC_DIR + '/' + name for name in COURSE_ARCHIVES]
    members.append(ABE_COURSE_DIR + '/route.txt')
    return members


def build_closure(iso, members, floor=1):
    '''Verify the headed-run closure for the given floor; returns packet.'''
    records = []
    data, record = read_member(iso, SOURCE_CAVEINFO, members)
    records.append(record)
    units = []
    for first, last, pool in FLOOR_POOLS:
        member = pool_member(pool)
        data, record = read_member(iso, member, members)
        record['pool'] = pool
        record['floors'] = [first, last]
        records.append(record)
        if data is not None and (first <= floor <= last):
            try:
                units = enumerate_units(data.decode('shift_jis'))
                record['units'] = units
            except Exception as error:
                record['status'] = 'ABSENT'
                record['failed_read'] = 'pool decode failed: ' + str(error)
    for member in course_members():
        data, record = read_member(iso, member, members)
        records.append(record)
    for unit in units:
        for member in unit_asset_members(unit):
            data, record = read_member(iso, member, members)
            record['unit'] = unit
            records.append(record)
    for member in ABSENT_PROBES:
        data, record = read_member(iso, member, members)
        record['probe'] = True
        records.append(record)
    present = [r for r in records if r['status'] == 'PRESENT']
    absent = [r for r in records if r['status'] == 'ABSENT']
    return dict(schema='p2-forest1-legal-assets-1', cave=CAVE_ID, floor=floor,
                source_disc=str(iso), present=present, absent=absent,
                floor1_units=units,
                consumers=['#154 gap 1 (headed-run legal assets)'],
                next_scope='#154 owner: unit geometry decode (gap 2) then controller lease/run (gap 3)')

def validate_packet(packet):
    '''Fail closed on a malformed or invented-asset packet.'''
    if packet.get('schema') != 'p2-forest1-legal-assets-1':
        raise ValueError('packet schema mismatch')
    if packet.get('cave') != CAVE_ID:
        raise ValueError('packet cave mismatch')
    for record in packet['present']:
        if not record.get('member') or not record.get('sha256'):
            raise ValueError('present asset missing member/sha256')
        if len(record['sha256']) != 64:
            raise ValueError('present asset has non-sha256 digest')
    for record in packet['absent']:
        if not record.get('member') or not record.get('failed_read'):
            raise ValueError('absent asset must name an exact failed read')
    return packet


def stage(packet, iso, members, output):
    '''Copy present members into the headed-run layout with a staged manifest.'''
    root = Path(output)
    if root.exists():
        shutil.rmtree(root)
    staged = []
    for record in packet['present']:
        member = record['member']
        data, again = read_member(iso, member, members)
        if data is None or again['sha256'] != record['sha256']:
            raise ValueError('asset changed during staging: ' + member)
        target = root / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        staged.append({'member': member, 'path': str(target),
                       'size': len(data), 'sha256': record['sha256']})
    manifest = dict(packet, staged=staged,
                    staged_root=str(root), staging='exact-read copy')
    (root / 'staged-manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    return manifest


def load_members(iso):
    from experimental.pikmin2_assets import disc_files
    return disc_files(Path(iso))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Forest_1 headed-run legal-asset verify/stage')
    parser.add_argument('--iso', required=True)
    parser.add_argument('--asset-inputs', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--floor', type=int, default=1)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args(argv)
    members = load_members(args.iso)
    recorded = json.loads(Path(args.asset_inputs).read_text(encoding='utf-8-sig'))
    packet = build_closure(args.iso, members, args.floor)
    validate_packet(packet)
    known = {v['member']: v for v in recorded.get('verified_members', [])}
    for record in packet['present']:
        expected = known.get(record['member'])
        if expected is not None and expected.get('sha256') != record['sha256']:
            raise ValueError('asset-inputs sha mismatch: ' + record['member'])
    packet['recorded_matches'] = [r['member'] for r in packet['present'] if r['member'] in known]
    if args.verify_only:
        result = packet
    else:
        result = stage(packet, args.iso, members, args.output)
    print(json.dumps({'present': len(packet['present']), 'absent': len(packet['absent']),
                      'floor1_units': packet['floor1_units'],
                      'recorded_matches': packet['recorded_matches']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
