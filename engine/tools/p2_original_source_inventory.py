"""Decode verified private original generator members without calendar filtering."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath


def flatten(value):
    if isinstance(value, list):
        return [token for child in value for token in flatten(child)]
    return [value]


def inventory(bundle, tree, decode_enemies=False):
    bundle = Path(bundle)
    receipt = json.loads((bundle / 'surface-receipt.json').read_text(encoding='utf-8'))
    course = receipt['course']
    result = []
    expected = {name for name in receipt['files'] if name.startswith('generators/') and name.endswith('.txt') and not name.endswith('/route.txt')}
    for name in expected:
        path = PurePosixPath(name)
        if '\\' in name or ':' in name or path.is_absolute() or any(part in ('.', '..') for part in path.parts) or str(path) != name:
            raise ValueError('Unsafe private source receipt path')
    actual = {'generators/' + p.relative_to(bundle / 'generators').as_posix() for p in (bundle / 'generators').rglob('*.txt') if p.name != 'route.txt'}
    if expected != actual:
        raise ValueError('Private source member inventory differs from receipt')
    for path in sorted(expected):
        raw = (bundle / path).read_bytes()
        pin = receipt['files'][path]
        if len(raw) != pin['size'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('Private generator member changed: ' + path)
        values = tree(raw.decode('cp932'))
        if len(values) < 6 or values[0] != ['v0.1']:
            raise ValueError('Unsupported native source manager header')
        count = int(values[5])
        if count < 0 or count > len(values) - 6:
            raise ValueError('Truncated source manager declared prefix')
        member = {'member': path[len('generators/'):], 'source_sha256': pin['sha256'], 'header_start': list(map(float, values[1:4])), 'header_direction': float(values[4]), 'records': [], 'dormant_trailing_records': len(values) - 6 - count}
        if any(not math.isfinite(x) for x in member['header_start'] + [member['header_direction']]):
            raise ValueError('Nonfinite source manager transform')
        for index, row in enumerate(values[6:6 + count]):
            if not isinstance(row, list) or len(row) < 43 or row[0] not in (['v0.1'], ['v0.2'], ['v0.3']) or len(row[41]) != 1 or len(row[42]) != 1:
                raise ValueError('Unsupported source common record')
            position, offset = list(map(float, row[35:38])), list(map(float, row[38:41]))
            if any(not math.isfinite(x) for x in position + offset):
                raise ValueError('Nonfinite source record transform')
            key = course + '/' + member['member'] + '#' + str(index)
            uid = 0x52000000 | int.from_bytes(hashlib.sha256(key.encode('ascii')).digest()[:3], 'big')
            actor = {'index': index, 'kind': row[41][0], 'record_version': row[0][0], 'object_version': row[42][0], 'source_payload': row[43:], 'reserved': int(row[1]), 'respawn_days': int(row[2]), 'position': position, 'offset': offset}
            record = {'source_key': key, 'generator_uid': uid, 'actor': actor}
            if actor['kind'] == 'teki' and decode_enemies:
                tokens = flatten(actor['source_payload'])
                if actor['object_version'] not in ('0004', '0005'):
                    raise ValueError('Unsupported original enemy object version')
                # GenTeki versions before0005 retain constructor birthType0;
                # 0004 begins with source ID then count, without that byte.
                if actor['object_version'] == '0004':
                    tokens = tokens[:1] + ['0'] + tokens[1:]
                if len(tokens) < 15 or tokens[-1] != '_eof':
                    raise ValueError('Truncated original enemy payload')
                keys = ['source_id', 'birth_type', 'count', 'direction_degrees', 'spawn_type', 'appear_radius', 'enemy_size', 'treasure_code', 'pellet_color', 'pellet_size', 'pellet_minimum', 'pellet_maximum', 'pellet_probability']
                record['enemy'] = {key: (float if i in (3, 5, 6, 12) else int)(tokens[i]) for i, key in enumerate(keys)}
                record['enemy'].update(generator_version=tokens[13], generator_tail=tokens[14:-1])
            member['records'].append(record)
        result.append(member)
    return course, result
