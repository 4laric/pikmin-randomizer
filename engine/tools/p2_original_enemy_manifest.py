"""Stage complete decoded enemy inventory into P2OC1 and native p2og streams.

Private output only. Other source object kinds require their own typed producers;
these streams must be composed before a whole-course startup can be claimed.
Campaign fingerprint is supplied once for all courses, never derived per course.
"""
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path


def integer(n):
    if type(n) is not int or not -(1 << 31) <= n <= 0xffffffff:
        raise ValueError('Invalid integer field')
    return struct.pack('<I', n & 0xffffffff)


def number(n):
    if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n):
        raise ValueError('Invalid literal float')
    return struct.pack('<f', n)


def string(s):
    b = s.encode('ascii')
    return integer(len(b)) + b


def flatten(value):
    if isinstance(value, list):
        return [t for v in value for t in flatten(v)]
    if not isinstance(value, str):
        raise ValueError('Invalid raw source token')
    return [value]


def stage(members, course, campaign):
    if not re.fullmatch('[a-z_]+', course) or not re.fullmatch('[0-9a-f]{64}', campaign):
        raise ValueError('Invalid course or campaign fingerprint')
    rows, streams, seen = [], {}, set()
    skipped = {}
    for member in members:
        name = member['member']
        if name in streams:
            raise ValueError('Duplicate source member')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name) or any(p in ('.', '..') for p in name.split('/')):
            raise ValueError('Invalid member path')
        if not re.fullmatch('[0-9a-f]{64}', member['source_sha256']):
            raise ValueError('Invalid source member fingerprint')
        native = []
        for record in member['records']:
            actor = record['actor']
            if actor['kind'] != 'teki':
                skipped[actor['kind']] = skipped.get(actor['kind'], 0) + 1
                continue
            enemy = record['enemy']
            key = course + '/' + name + '#' + str(actor['index'])
            uid = 0x52000000 | int.from_bytes(hashlib.sha256(key.encode('ascii')).digest()[:3], 'big')
            if key != record['source_key'] or uid != record['generator_uid'] or uid in seen or not 0 <= actor['index'] <= 65535:
                raise ValueError('Source key, UID, index mismatch or collision')
            seen.add(uid)
            if actor['object_version'] not in ('0004', '0005'):
                raise ValueError('Unsupported original enemy object version')
            ints = [enemy[k] for k in ('source_id', 'birth_type', 'count', 'spawn_type')]
            floats = actor['position'] + actor['offset'] + [enemy[k] for k in ('direction_degrees', 'appear_radius', 'enemy_size')]
            drops = [enemy[k] for k in ('treasure_code', 'pellet_color', 'pellet_size', 'pellet_minimum', 'pellet_maximum')]
            probability = enemy['pellet_probability']
            version, tail = enemy['generator_version'], enemy['generator_tail']
            payload = flatten(actor['source_payload'])
            if actor['object_version'] == '0004':
                payload = payload[:1] + ['0'] + payload[1:]
            if len(payload) < 15 or payload[-1] != '_eof' or len(version) != 4 or payload[13:-1] != [version] + tail:
                raise ValueError('Decoded species version/tail differs from raw source')
            raw_ints = [int(payload[i]) for i in (0, 1, 2, 4, 7, 8, 9, 10, 11)]
            if raw_ints != ints[:3] + ints[3:] + drops:
                raise ValueError('Decoded common integer differs from raw source')
            if [number(float(payload[i])) for i in (3, 5, 6, 12)] != [number(x) for x in floats[6:] + [probability]]:
                raise ValueError('Decoded common float differs from raw source')
            reserved, respawn, limit = actor['reserved'], actor['respawn_days'], actor.get('day_limit', -1)
            if not 0 <= ints[0] <= 65535 or not 0 <= ints[1] <= 255 or not 0 <= ints[2] <= 10 or not 0 <= ints[3] <= 255 or len(floats) != 9 or not 0 <= reserved <= 65535 or not -32768 <= respawn <= 32767 or not -32768 <= limit <= 32767 or not -32768 <= drops[0] <= 32767 or any(not 0 <= n <= 255 for n in drops[1:]):
                raise ValueError('Common source field outside native bounds')
            if len(tail) > 4096 or any(len(t) > 4096 for t in tail):
                raise ValueError('Opaque source tail exceeds bound')
            row = string(course) + string(name) + integer(actor['index'])
            row += b''.join(integer(n) for n in (ints[0], uid, *ints[1:]))
            row += b''.join(number(n) for n in floats)
            row += b''.join(integer(n) for n in drops) + number(probability)
            row += string(version) + integer(len(tail)) + b''.join(string(t) for t in tail)
            row += b''.join(integer(n) for n in (reserved, respawn, limit))
            rows.append(row)
            # Native stream scalars are big endian; native fourcc IDs are
            # reversed at the PC boundary. GenBase has an empty Parm list.
            g = b'gp2o' + b'3.0v' + struct.pack('<I', uid) + struct.pack('>I', reserved) + bytes(32)
            g += struct.pack('>6f', *(actor['position'] + actor['offset']))
            g += b'go2p' + b'20GO'
            g += struct.pack('>IIii', uid, reserved, respawn, limit)
            g += b'\xff' * 4 + bytes(8)  # parameter terminator, null area/type
            native.append(g)
        header = member['header_start']
        if len(header) != 3:
            raise ValueError('Invalid source starting transform')
        for value in header + [member['header_direction']]:
            number(value)
        streams[name] = b'1.0v' + struct.pack('>4fI', *header, member['header_direction'], len(native)) + b''.join(native)
    if not rows or len(rows) > 65536:
        raise ValueError('Empty or oversized enemy inventory')
    payload = b'P2OC1' + string(campaign) + integer(len(rows)) + b''.join(rows)
    if len(payload) > 4 * 1024 * 1024 - 32:
        raise ValueError('Source manifest exceeds bound')
    return payload + hashlib.sha256(payload).digest(), streams, skipped


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--decoded-inventory', required=True, type=Path)
    cli.add_argument('--course', required=True)
    cli.add_argument('--campaign-fingerprint', required=True)
    cli.add_argument('--output', required=True, type=Path)
    args = cli.parse_args()
    raw = args.decoded_inventory.read_bytes()
    manifest, streams, skipped = stage(json.loads(raw), args.course, args.campaign_fingerprint)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / (args.course + '.p2c')).write_bytes(manifest)
    for name, content in streams.items():
        name = {'defaultgen.txt': 'default.gen', 'plantsgen.txt': 'plants.gen', 'initgen.txt': 'init.gen'}.get(name, name.removesuffix('.txt') + '.gen')
        path = args.output / 'enemy-streams' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    receipt = {'inventory_sha256': hashlib.sha256(raw).hexdigest(), 'manifest_sha256': hashlib.sha256(manifest).hexdigest(), 'campaign_fingerprint': args.campaign_fingerprint, 'enemy_rows': struct.unpack_from('<I', manifest, 73)[0], 'other_source_kinds_require_composition': skipped, 'runtime_gameplay': False}
    (args.output / 'staging.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))
