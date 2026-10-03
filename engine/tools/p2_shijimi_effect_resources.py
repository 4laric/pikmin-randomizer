"""Extract independently verified original GPVE01 source77 appearance resources.

Raw game bytes remain private. This importer does not admit native rendering or
claim effect fidelity: PID21/22/23 require their own continuous chase emitter.
"""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_assets import disc_files

ARCHIVE = 'user/Ebisawa/effect/game.jpc'
ARCHIVE_SHA = 'ebf889b4e5df0391662bd531e220b93d148ab56fdec96362386b9cd1e734302c'
RESOURCES = (
    ('shijimi-0015.jpa', 15268, 360, 'c3168c19baa3e9757dd86c2b616de0a0fb36a0952f1d656728c5e4753a5c1506'),
    ('shijimi-0016.jpa', 15628, 360, 'e6d3ad4dce615f325b97fcd6840bd846aaeb300f9cf5638ec6f51e6dc735536f'),
    ('shijimi-0017.jpa', 15988, 360, '1319bec150dbdafed6ce8bab9b523ad1c5cf7046ea67b8d6313e5100bad5084e'),
    ('IP2_stardust1_i.tex1', 345696, 4160, 'a58fb129361f1631d7619040f16318981bf35046d36fab740076b124a0b941f1'),
)

def extract(iso, out):
    offset, size = disc_files(iso)[ARCHIVE]
    with iso.open('rb') as source:
        source.seek(offset)
        archive = source.read(size)
    if len(archive) != size or hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA:
        raise ValueError('GPVE01 game.jpc source digest mismatch')
    checked = {}
    for name, start, length, digest in RESOURCES:
        data = archive[start:start + length]
        if len(data) != length or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Source77 appearance member digest mismatch: ' + name)
        checked[name] = data
    # Validate every existing member before any output is replaced.
    for name, data in checked.items():
        target = out / name
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Existing output changed: ' + name)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in checked.items():
        (out / name).write_bytes(data)
    receipt = {'disc_id': 'GPVE01', 'source_archive': ARCHIVE,
               'archive_sha256': ARCHIVE_SHA, 'effects': [21, 22, 23],
               'texture': 'IP2_stardust1_i', 'native_renderer_qualified': False,
               'gameplay': False,
               'files': {name: hashlib.sha256(data).hexdigest() for name, data in checked.items()}}
    (out / 'shijimi-effect-source-receipt.json').write_text(
        json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.iso, args.out)))
