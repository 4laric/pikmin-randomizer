"""Preserve literal decoded GenItem0002/Cave0002 records; no runtime admission."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def manifest(members):
    rows, seen = [], set()
    for member in members:
        for record in member['records']:
            actor = record['actor']
            if actor['kind'] != 'item' or actor.get('item') != 'cave':
                continue
            payload = actor['source_payload']
            if len(payload) != 2 or payload[1] != [['_eof']]:
                raise ValueError('Unexpected literal Cave nested payload')
            tail = payload[0]
            if (actor['object_version'] != '0002' or len(tail) != 9
                    or tail[0] != ['cave'] or tail[4] != ['0002']):
                raise ValueError('Unsupported GenItem/Cave source version/tail')
            rotation = list(map(float, tail[1:4]))
            if (rotation != actor['rotation'] or len(tail[7]) != 1
                    or tail[5] != actor.get('cave_file', tail[5])
                    or tail[6] != actor.get('units_file', tail[6])
                    or tail[7] != [actor.get('cave_id', tail[7][0])]):
                raise ValueError('Decoded Cave fields differ from literal source tail')
            parameters = tail[8]
            if len(parameters) != 31 or parameters[-1] != ['_eof']:
                raise ValueError('Unexpected Cave0002 parameter tail')
            values = actor['position'] + actor['offset'] + rotation
            if len(values) != 9 or any(not math.isfinite(x) or abs(x) > 100000 for x in values):
                raise ValueError('Invalid Cave source transform')
            fields = []
            for i in range(10):
                label, kind, value = parameters[i*3:i*3+3]
                color = 4 <= i <= 6
                number = float(value)
                if (label != [f'fg{i:02d}'] or kind != ('1' if color else '4')
                        or not math.isfinite(number) or abs(number) > 1000000
                        or (color and (number != int(number) or not 0 <= number <= 255))):
                    raise ValueError('Unsupported Cave typed parameter')
                fields += [kind, format(number, '.9g')]
            key = record['source_key']
            uid = 0x52000000 | int.from_bytes(hashlib.sha256(key.encode('ascii')).digest()[:3], 'big')
            if uid != record['generator_uid'] or uid in seen:
                raise ValueError('Cave source UID mismatch/collision')
            if key.rsplit('/', 1)[1] != member['member'] + '#' + str(actor['index']):
                raise ValueError('Cave key/member/index mismatch')
            sha = member['source_sha256']
            if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
                raise ValueError('Invalid Cave source member hash')
            if actor['reserved'] != 0 or actor['respawn_days'] != 0:
                raise ValueError('Cave nondefault respawn/cache needs separate provider')
            seen.add(uid)
            rows.append(' '.join([str(uid), key, sha, '0002', '0002',
                                  str(actor['reserved']), str(actor['respawn_days']),
                                  str(actor.get('day_limit', -1)), tail[5],
                                  tail[6], tail[7][0]]
                                 + [format(x, '.9g') for x in values] + fields))
    if not rows or len(rows) > 4096:
        raise ValueError('Invalid Cave record count')
    return f'P2_ORIGINAL_CAVE_1 {len(rows)}\n' + '\n'.join(rows) + '\n'


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--decoded-inventory', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    text = manifest(json.loads(args.decoded_inventory.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='ascii', newline='\n') as output:
        output.write(text)
    print(json.dumps({'records': len(text.splitlines())-1,
                      'manifest_sha256': hashlib.sha256(text.encode('ascii')).hexdigest(),
                      'source_inventory_sha256': hashlib.sha256(args.decoded_inventory.read_bytes()).hexdigest(),
                      'runtime_gameplay': False}))
