"""Stage all-calendar literal GenPiki authority and separate native p2pi streams."""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from p2_original_source_inventory import inventory, flatten
from p2_original_enemy_manifest import integer, number, string


def stage(courses, campaign):
    if not re.fullmatch('[0-9a-f]{64}', campaign):
        raise ValueError('Invalid selected campaign fingerprint')
    records, streams, seen, dormant = [], {}, set(), 0
    for course, members in courses:
        if course not in ('tutorial', 'forest', 'yakushima', 'last'):
            raise ValueError('Unknown original surface course')
        for member in members:
            native = []
            dormant += member.get('dormant_trailing_records', 0)
            for record in member['records']:
                actor = record['actor']
                if actor['kind'] != 'piki':
                    continue
                tokens = flatten(actor['source_payload'])
                if actor['object_version'] != '0001' or len(tokens) != 10 or [tokens[i] for i in (0, 1, 3, 4, 6, 7, 9)] != ['p000', '4', 'p001', '4', 'p002', '4', '_eof']:
                    raise ValueError('Unsupported original GenPiki version/parameters')
                species, count, wild = [int(tokens[i]) for i in (2, 5, 8)]
                key = record['source_key']
                uid = 0x52000000 | int.from_bytes(hashlib.sha256(key.encode('ascii')).digest()[:3], 'big')
                if key != course + '/' + member['member'] + '#' + str(actor['index']) or uid != record['generator_uid'] or uid in seen:
                    raise ValueError('Original Piki identity collision/mismatch')
                if not 0 <= species <= 5 or not 0 <= count <= 65535 or not -(1 << 31) <= wild < (1 << 31):
                    raise ValueError('Original GenPiki parameter outside source bounds')
                reserved, respawn, limit = actor['reserved'], actor['respawn_days'], actor.get('day_limit', -1)
                if not 0 <= reserved <= 65535 or not -32768 <= respawn <= 32767 or not -32768 <= limit <= 32767:
                    raise ValueError('Original GenPiki common schedule outside bounds')
                seen.add(uid)
                transforms = actor['position'] + actor['offset']
                body = string(key) + member['source_sha256'].encode('ascii') + actor['record_version'].encode('ascii') + b'0001'
                body += b''.join(integer(n) for n in (uid, count, species, wild, reserved, respawn, limit))
                body += b''.join(number(n) for n in transforms)
                records.append((key, body))
                # The typed native object carries UID only; full parameters and
                # authored float placement are resolved against P2PK1 authority.
                g = b'ip2o' + b'3.0v' + struct.pack('<I', uid) + struct.pack('>I', reserved) + bytes(32)
                g += struct.pack('>6f', *transforms) + b'ip2p' + b'10PO' + struct.pack('>I', uid)
                g += b'\xff' * 4 + bytes(8)
                native.append(g)
            stream_key = course + '/' + member['member']
            if stream_key in streams:
                raise ValueError('Duplicate original calendar member')
            streams[stream_key] = b'1.0v' + struct.pack('>4fI', *member['header_start'], member['header_direction'], len(native)) + b''.join(native)
    records.sort()
    if not records or len(records) > 65536:
        raise ValueError('Empty or oversized immutable Piki catalog')
    rows = b''.join(body for _, body in records)
    catalog = hashlib.sha256(rows).hexdigest()
    payload = b'P2PK1' + campaign.encode('ascii') + catalog.encode('ascii') + integer(len(records)) + rows
    if len(payload) > 4 * 1024 * 1024 - 32:
        raise ValueError('Original Piki catalog exceeds bound')
    return payload + hashlib.sha256(payload).digest(), streams, {'campaign_fingerprint': campaign, 'piki_catalog_sha256': catalog, 'rows': len(records), 'dormant_trailing_rows_not_enabled': dormant, 'runtime_gameplay': False}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--randomizer-root', required=True, type=Path)
    cli.add_argument('--bundle', required=True, action='append', type=Path)
    cli.add_argument('--campaign-fingerprint', required=True)
    cli.add_argument('--output', required=True, type=Path)
    cli.add_argument('--active-census', type=Path, help='Complete selected native calendar member census')
    cli.add_argument('--course', choices=('tutorial', 'forest', 'yakushima', 'last'))
    cli.add_argument('--day', type=int, help='Zero-based original source day')
    args = cli.parse_args()
    sys.path.insert(0, str(args.randomizer_root.resolve(strict=True)))
    from experimental.pikmin2_cave import tree
    courses = [inventory(bundle, tree) for bundle in args.bundle]
    if {course for course, _ in courses} != {'tutorial', 'forest', 'yakushima', 'last'} or len(courses) != 4:
        raise ValueError('Require all four complete original calendar bundles')
    manifest, streams, receipt = stage(courses, args.campaign_fingerprint)
    active_blob = None
    if args.active_census is not None:
        if args.course is None or args.day is None or not 0 <= args.day <= 0xffffffff:
            raise ValueError('Active census requires selected course and zero-based day')
        full = {r['source_key']: (member['source_sha256'], r['actor'])
                for course, members in courses for member in members for r in member['records']
                if r['actor']['kind'] == 'piki'}
        verified_members = {member['member']: member for course, members in courses
                            if course == args.course for member in members}
        uids, seen_members, selected_keys = [], set(), set()
        for member in json.loads(args.active_census.read_text(encoding='utf-8')):
            if member['member'] in seen_members:
                raise ValueError('Duplicate selected calendar member')
            seen_members.add(member['member'])
            if member['member'] not in verified_members or member['source_sha256'] != verified_members[member['member']]['source_sha256']:
                raise ValueError('Selected calendar member not in verified full source inventory')
            for record in member['records']:
                actor = record['actor']
                if actor['kind'] != 'piki':
                    continue
                key = record['source_key']
                if not key.startswith(args.course + '/') or key not in full:
                    raise ValueError('Selected Piki absent from full immutable atlas')
                sha, actual = full[key]
                fields = ('index', 'kind', 'record_version', 'object_version', 'source_payload',
                          'position', 'offset', 'reserved', 'respawn_days')
                if sha != member['source_sha256'] or any(actor[f] != actual[f] for f in fields):
                    raise ValueError('Selected Piki differs from verified source row')
                uid = 0x52000000 | int.from_bytes(hashlib.sha256(key.encode('ascii')).digest()[:3], 'big')
                if uid != record['generator_uid'] or uid in uids:
                    raise ValueError('Selected Piki UID mismatch/duplicate')
                uids.append(uid)
                selected_keys.add(key)
        expected_keys = {r['source_key'] for name in seen_members
                         for r in verified_members[name]['records'] if r['actor']['kind'] == 'piki'}
        if selected_keys != expected_keys:
            raise ValueError('Selected calendar census omitted original Piki rows')
        active_blob = b'P2PA1' + args.campaign_fingerprint.encode('ascii') + receipt['piki_catalog_sha256'].encode('ascii')
        active_blob += string(args.course) + integer(args.day) + integer(len(uids))
        active_blob += b''.join(integer(uid) for uid in sorted(uids))
        active_blob += hashlib.sha256(active_blob).digest()
        receipt['selected_piki_rows'] = len(uids)
        receipt['selected_source_day'] = args.day
    elif args.course is not None or args.day is not None:
        raise ValueError('Course/day requires explicit complete selected calendar census')
    args.output.mkdir(parents=True, exist_ok=False)
    if active_blob is not None:
        (args.output / (args.course + '.p2pa')).write_bytes(active_blob)
    (args.output / 'campaign.p2pk').write_bytes(manifest)
    for key, content in streams.items():
        course, name = key.split('/', 1)
        name = {'defaultgen.txt': 'default.gen', 'plantsgen.txt': 'plants.gen', 'initgen.txt': 'init.gen'}.get(name, name.removesuffix('.txt') + '.gen')
        path = args.output / 'piki-streams' / course / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    receipt['manifest_sha256'] = hashlib.sha256(manifest).hexdigest()
    (args.output / 'staging.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))
