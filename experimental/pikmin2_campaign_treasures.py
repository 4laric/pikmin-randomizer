"""Convert selected original retail treasure models into a private collector bank."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import safe_name
from experimental.pikmin2_convert import convert
from experimental.pikmin2_pod import pellet_catalog
from randomizer.campaign_treasures import verified_entries

CONFIG_SHA256 = {
    'otakara': '36de6f3b05065913464d256bd2745a2ef3a6948f96f0729c6b0ee51771b7f24a',
    'item': 'fb69ac3f3736d83a7f62154c7592bc7fcd1eef456336320ba6b3ca80941c6b85',
}


def source_profiles(config_bytes, entries, selected):
    """Verify literal GPVE01 profiles before writing or converting any assets."""
    catalogs = {}
    for kind, expected_hash in CONFIG_SHA256.items():
        data = config_bytes[kind]
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError('Original retail profile source hash mismatch')
        catalogs[kind] = pellet_catalog(data.decode('shift_jis'))
    result = {}
    for identity in selected:
        expected = entries[identity]
        source = catalogs[expected['kind']][identity]
        if [int(source[key]) for key in ('dictionary', 'money', 'min', 'max')] != [
                expected[key] for key in ('dictionary', 'value', 'minimum', 'maximum')]:
            raise ValueError('Original treasure profile differs from pinned catalog')
        physics = {}
        for key in ('radius', 'p_radius', 'height', 'inertiascaling', 'friction'):
            value = float(source[key])
            if not math.isfinite(value) or value < 0 or (key != 'friction' and value == 0):
                raise ValueError('Invalid original treasure physics profile')
            physics[key] = value
        physics['dynamics'] = source['dynamics']
        result[identity] = dict(source=source, physics=physics, kind=expected['kind'])
    return result


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
        config_bytes = {}
        for kind in ('otakara', 'item'):
            config_bytes[kind] = read(f'user/Abe/Pellet/us/{kind}_config.txt')
        profiles = source_profiles(config_bytes, entries, selected)
        output = Path(output); output.mkdir(parents=True, exist_ok=False)
        for kind, data in config_bytes.items():
            target = output / 'source' / 'user/Abe/Pellet/us' / f'{kind}_config.txt'
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        def unpack(path, folder):
            raw = read(path)
            target = output / 'source' / path
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            members = archive_files(raw)
            for name, data in members.items():
                target = output / folder / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            return {name: hashlib.sha256(data).hexdigest() for name, data in members.items()}
        unpack('user/Kando/pod/arc.szs', 'pod')
        convert(output / 'pod/pot.bmd', output / 'pod.mod', True, bake_rigid=True)
        for identity in selected:
            source = profiles[identity]['source']
            members = unpack('user/Abe/Pellet/us/' + safe_name(source['archive']), identity)
            original = output / identity / safe_name(source['bmd'])
            target = output / (identity + '.mod')
            model = convert(original, target, True, bake_rigid=True)
            model = convert(original, target, True, bake_rigid=True, y_offset=-model['bounds'][1])
            facts[identity] = dict(profile=entries[identity], original_profile=source,
                                  physics=profiles[identity]['physics'], original_member_sha256=members,
                                  converted_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), model=model)
    result = dict(schema=2, selected=facts, source_sha256=hashes,
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
