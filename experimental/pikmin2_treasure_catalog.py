"""Emit a private native numeric catalog from the reconciled #140 source ledger.

No models, translated names or raw disc bytes belong in the public repository.
The native consumer pins the digest of this deterministic manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from experimental.pikmin2_treasure_ledger import build

RETAIL_DIGEST = 'f0f9c1f60953f63b5460037e5bf276193172f526b869f7642b97d44a0704d751'


def verify_native_catalog(path):
    path = Path(path).resolve(strict=True)
    with path.open('rb') as source:
        data = source.read(32769)
    if len(data) > 32768 or hashlib.sha256(data).hexdigest() != RETAIL_DIGEST:
        raise ValueError('Native catalog differs from pinned GPVE01 source')
    return path


def manifest(ledger):
    if ledger.get('schema') != 1 or ledger.get('disc') != 'GPVE01 revision 0':
        raise ValueError('Unsupported treasure source')
    if ledger.get('reconciliation', {}).get('reconciled') is not True:
        raise ValueError('Unreconciled treasure source')
    rows = ledger['entries']
    if len(rows) != 201:
        raise ValueError('Incomplete retail catalog')
    ids, dictionaries, indices = set(), set(), set()
    result = ['P2_TREASURE_CATALOG_1 201']
    for entry in rows:
        name, kind = entry['treasure_id'], entry['pellet_kind']
        category = entry['classification']
        if (not re.fullmatch(r'[A-Za-z0-9_]{1,64}', name)
                or kind not in ('otakara', 'item')
                or category not in ('campaign', 'mode_only', 'unused')
                or entry['unique'] not in ('yes', 'no')):
            raise ValueError('Invalid catalog identity/classification')
        fields = ('config_index', 'dictionary', 'value', 'weight', 'slots', 'code')
        values = [entry[field] for field in fields]
        bounds = ((0, 255), (1, 201), (0, 1000000), (1, 1000), (1, 128), (0, 65535))
        if any(type(value) is not int or not low <= value <= high
               for value, (low, high) in zip(values, bounds)):
            raise ValueError('Invalid catalog parameters')
        index, dictionary, *_ = values
        if name in ids or dictionary in dictionaries or (kind, index) in indices:
            raise ValueError('Duplicate catalog identity')
        ids.add(name); dictionaries.add(dictionary); indices.add((kind, index))
        result.append(' '.join([name, kind, category, *map(str, values), entry['unique']]))
    if dictionaries != set(range(1, 202)):
        raise ValueError('Incomplete dictionary')
    return ('\n'.join(result) + '\n').encode('ascii')


def emit(iso, inventory, output):
    ledger = build(iso, inventory, output)
    data = manifest(ledger)
    target = output / 'p2-treasure-catalog.txt'
    target.write_bytes(data)
    summary = dict(entries=len(ledger['entries']),
                   campaign=sum(e['classification'] == 'campaign' for e in ledger['entries']),
                   sha256=hashlib.sha256(data).hexdigest(),
                   source_sha256=ledger['source_sha256'])
    (output / 'native-catalog-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, default=Path('docs/PIKMIN2_CONTENT_INVENTORY.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summary = emit(args.iso, args.inventory, args.output)
    print(json.dumps({key: summary[key] for key in ('entries', 'campaign', 'sha256')}))
