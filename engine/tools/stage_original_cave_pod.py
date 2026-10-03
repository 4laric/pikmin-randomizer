"""Stage the pinned original cave Pod resources into fresh private output.

Uses the randomizer's read-only US-disc extractor and the existing verified MOD
conversion. Does not alter the disc, shared assets, game state or any active run.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--randomizer-root', required=True, type=Path)
    parser.add_argument('--iso', required=True, type=Path)
    parser.add_argument('--converted-model', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.randomizer_root.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(root / 'output') or output.exists():
        raise SystemExit('Output must be a fresh directory beneath the workspace output')
    header = (Path(__file__).resolve().parents[1] / 'pc_port/pc_p2_original_pod_sources.h').read_text()
    pins = dict(re.findall(r'constexpr const char\* (\w+)="([0-9a-f]{64})";', header))
    sys.path.insert(0, str(root))
    from experimental.pikmin2_assets import disc_files, archive_files
    inventory = disc_files(args.iso)
    members = {}
    raw = {}
    with args.iso.open('rb') as disc:
        for source in ('user/Kando/pod/arc.szs', 'user/Kando/pod/texts.szs'):
            offset, size = inventory[source]
            disc.seek(offset)
            raw[source] = disc.read(size)
            if len(raw[source]) != size:
                raise SystemExit('Truncated original disc member: ' + source)
            members[source] = archive_files(raw[source])
    files = {
        'pod/arc.szs': (raw['user/Kando/pod/arc.szs'], pins['archiveSha256']),
        'pod/texts.szs': (raw['user/Kando/pod/texts.szs'], pins['originalTextsSha256']),
        'pod/pot.bmd': (members['user/Kando/pod/arc.szs']['pot.bmd'], pins['originalModelSha256']),
        'pod/coll.txt': (members['user/Kando/pod/texts.szs']['coll.txt'], pins['originalCollisionSha256']),
        'pod.mod': (args.converted_model.read_bytes(), pins['convertedModelSha256']),
    }
    for name, (data, expected) in files.items():
        if sha(data) != expected:
            raise SystemExit('Source/conversion pin mismatch: ' + name)
    # Validate every member before creating the new directory.
    output.mkdir(parents=True)
    for name, (data, _) in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    report = {'version': 1, 'source': 'user/Kando/pod/arc.szs',
              'type': 3, 'objectBank': 1,
              'files': {name: {'sha256': sha(data), 'bytes': len(data)}
                        for name, (data, _) in files.items()},
              'limitations': ['Static bind pose; original animation/effects/TEV unfinished.',
                              'Resource verification is not floor, carry or SAVE acceptance.']}
    (output / 'pod-resource-evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS exact original Pod archive/model/collision/converted model; private resources:', output)


if __name__ == '__main__':
    main()
