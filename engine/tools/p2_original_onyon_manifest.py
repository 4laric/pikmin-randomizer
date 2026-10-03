"""Stage literal decoded GenItem/onyn rows. Does not edit assets or launch game.

Input is the existing original-source decoder's list of member inventories.
Other kinds remain the responsibility of their actual physical providers.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def manifest(members):
    rows = []
    seen = set()
    for member in members:
        for record in member['records']:
            actor = record['actor']
            if actor['kind'] != 'item' or actor.get('item') != 'onyn':
                continue
            payload = actor['source_payload']
            if len(payload) != 2 or payload[1] != [['_eof']]:
                raise ValueError('Unexpected original onyn nested payload')
            tail = payload[0]
            if actor['object_version'] != '0002' or len(tail) != 7 or tail[0] != ['onyn'] or tail[4] != ['0001']:
                raise ValueError('Unsupported original GenItem/onyn version or tail')
            rotation = [float(x) for x in tail[1:4]]
            index, after_boot = int(tail[5]), int(tail[6])
            if rotation != actor['rotation'] or index != actor['onion_index'] or after_boot != actor['after_boot']:
                raise ValueError('Decoded onyn fields differ from literal source tail')
            if index not in (0, 1, 2, 4) or after_boot not in (0, 1):
                raise ValueError('Unsupported onyn type (pod has no provider) or boot flag')
            key = record['source_key']
            uid = 0x52000000 | int.from_bytes(hashlib.sha256(key.encode('ascii')).digest()[:3], 'big')
            if uid != record['generator_uid'] or uid in seen:
                raise ValueError('Original source UID mismatch or collision')
            if key.rsplit('/', 1)[1] != member['member'] + '#' + str(actor['index']):
                raise ValueError('Original source key/member/index mismatch')
            source_sha = member['source_sha256']
            if len(source_sha) != 64 or any(c not in '0123456789abcdef' for c in source_sha):
                raise ValueError('Invalid source member hash')
            values = actor['position'] + actor['offset'] + rotation
            if len(values) != 9 or any(not math.isfinite(x) for x in values):
                raise ValueError('Invalid literal original onyn transform')
            seen.add(uid)
            fields = [str(uid), key, source_sha, '0002', '0001', str(actor['reserved']),
                      str(actor['respawn_days']), str(actor.get('day_limit', -1)),
                      str(index), str(after_boot)] + [format(x, '.9g') for x in values]
            rows.append(' '.join(fields))
    if not rows:
        raise ValueError('No original onyn source records')
    return 'P2_ORIGINAL_ONYON_1 ' + str(len(rows)) + '\n' + '\n'.join(rows) + '\n'


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--decoded-inventory', required=True, type=Path)
    cli.add_argument('--output', required=True, type=Path)
    args = cli.parse_args()
    text = manifest(json.loads(args.decoded_inventory.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='ascii', newline='\n') as output:
        output.write(text)
    print(json.dumps({'records': len(text.splitlines()) - 1,
                      'manifest_sha256': hashlib.sha256(text.encode('ascii')).hexdigest(),
                      'source_inventory_sha256': hashlib.sha256(args.decoded_inventory.read_bytes()).hexdigest(),
                      'runtime_gameplay': False}))
