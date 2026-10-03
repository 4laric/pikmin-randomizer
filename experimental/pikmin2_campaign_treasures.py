"""Convert selected original retail treasure models into a private collector bank."""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import safe_name
from experimental.pikmin2_convert import convert
from experimental.pikmin2_pod import pellet_catalog
from randomizer.campaign_treasures import verified_entries


def extract(iso, catalog, output, selected):
    entries = verified_entries(catalog)
    if not selected or len(set(selected)) != len(selected) or any(name not in entries for name in selected):
        raise ValueError('Explicit unique retail catalog identities required')
    files = disc_files(iso)
    hashes, facts = {}, {}
    with Path(iso).open('rb') as disc:
        def read(path):
            offset, size = files[path]; disc.seek(offset); data = disc.read(size)
            if len(data) != size:
                raise ValueError('Truncated original asset')
            hashes[path] = hashlib.sha256(data).hexdigest(); return data
        configs = {}
        for kind in ('otakara', 'item'):
            source = pellet_catalog(read(f'user/Abe/Pellet/us/{kind}_config.txt').decode('shift_jis'))
            if configs.keys() & source.keys():
                raise ValueError('Ambiguous retail identity')
            configs.update(source)
        for identity in selected:
            source = configs[identity]; expected = entries[identity]
            if [int(source[key]) for key in ('money', 'min', 'max')] != [expected[key] for key in ('value', 'minimum', 'maximum')]:
                raise ValueError('Original treasure profile differs from pinned catalog')
        output = Path(output); output.mkdir(parents=True, exist_ok=False)
        def unpack(path, folder):
            for name, data in archive_files(read(path)).items():
                target = output / folder / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        unpack('user/Kando/pod/arc.szs', 'pod')
        convert(output / 'pod/pot.bmd', output / 'pod.mod', True, bake_rigid=True)
        for identity in selected:
            source = configs[identity]
            unpack('user/Abe/Pellet/us/' + safe_name(source['archive']), identity)
            original = output / identity / safe_name(source['bmd'])
            target = output / (identity + '.mod')
            model = convert(original, target, True, bake_rigid=True)
            model = convert(original, target, True, bake_rigid=True, y_offset=-model['bounds'][1])
            facts[identity] = dict(profile=entries[identity], converted_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), model=model)
    result = dict(schema=1, selected=facts, source_sha256=hashes,
                  limitations=['Static bind pose; animation/effects and source collision geometry remain unverified.',
                               'Private model extraction does not activate a campaign or grant receipts.',
                               'Engineering positions require terrain, carry and native SAVE/resume acceptance.'])
    (output / 'treasure-bank.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--treasure', action='append', required=True)
    args = parser.parse_args()
    result = extract(args.iso, args.catalog, args.output, args.treasure)
    print(json.dumps(dict(converted=len(result['selected']), activated=False)))
