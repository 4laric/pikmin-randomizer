"""Versioned Bulblax family install manifest, independent validation and installer.

Emits ``bulblax-install.json`` (schema 1, docs/PIKMIN2_BULBLAX_UNBLOCK.md) from
a #234 bank build, validates it independently against the bank directory, and
installs exact bytes into a fresh destination. This is an installation
artifact, not a native configuration format; the #235 native adapter consumes
it. Species identity is the audited Pikmin 2 enemy ID (Queen 30, Baby 31,
KingChappy 53) and is never inferred from a P1 host placement vehicle's type.

Validation refuses, BEFORE any copy: unsupported schema versions, absolute or
traversing model paths, duplicate placement IDs, placements referencing
unknown species/clips or non-finite XYZ, model hash/byte drift (tamper), and
an existing destination (never modified).

Arena expectations are emitted as a machine-readable artifact
(``p2-bulblax-arena-expectations.json``) carrying generator/placement IDs,
species, clip and expected full XYZ per placement. Arena fixtures include a
small starting Pikmin squad by default (avoiding the zero-color extinction
tutorial); an intentional zero-population case is a separate explicit
fixture. No live actor or arena gameplay is claimed.

Issue #234 (parent #172); bank policies from #233.
"""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path, PurePosixPath

from experimental.pikmin2_bulblax_assets import SPECIES
from experimental.pikmin2_bulblax_bank import HEADER as BANK_HEADER
from experimental.pikmin2_bulblax_bank import LIMITATIONS as BANK_LIMITATIONS

MANIFEST = 'bulblax-install.json'
SCHEMA = 1
BANK_TXT = 'p2-bulblax-bank.txt'
BANK_JSON = 'bulblax-bank.json'
EXPECTATIONS = 'p2-bulblax-arena-expectations.json'
MATERIAL_POLICY = 'approximate materials (texture-times-vertex-color base); no skeletal playback'

# Small default starting squad so arena fixtures never trigger the zero-color
# extinction tutorial; the intentional zero-population case stays separate.
DEFAULT_SQUAD = {'red': 5, 'yellow': 0, 'blue': 5, 'purple': 0, 'white': 0}
ZERO_SQUAD = {color: 0 for color in DEFAULT_SQUAD}

LIMITATIONS = ['Installation artifact only; the #235 native adapter emits the native configuration.',
               'Sampled-pose models with approximate materials; no skeletal/BTK playback, AI/FSM, combat or live actor claims.',
               'Placement coordinates are engineered fixtures; terrain/physical spawn acceptance is unmeasured.',
               'P2 enemy identity comes from the audited numeric species IDs, never from a P1 host type.']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _check_placements(placements, motions):
    """Validate raw placement entries against bank motions; returns a copy."""
    if type(placements) is not list or not placements or len(placements) > 100:
        raise ValueError('Expected 1..100 placement entries')
    seen = set()
    checked = []
    for entry in placements:
        if type(entry) is not dict:
            raise ValueError('Invalid placement entry')
        identity = entry.get('placement_id')
        species = entry.get('species')
        clip = entry.get('clip')
        xyz = entry.get('xyz')
        if type(identity) is not int or not 0 <= identity <= 0xffffffff or identity in seen:
            raise ValueError('Duplicate or invalid placement ID')
        seen.add(identity)
        if species not in SPECIES or clip not in motions.get(species, {}):
            raise ValueError(f'Placement {identity} references unknown species/clip')
        if (type(xyz) is not list or len(xyz) != 3
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in xyz)):
            raise ValueError(f'Placement {identity} requires finite XYZ')
        checked.append({'placement_id': identity, 'species': species, 'clip': clip,
                        'xyz': [float(v) for v in xyz]})
    return checked


def emit(bank, placements, output=None):
    """Build the schema-1 install manifest from a #234 bank build.

    ``placements`` is a list of dicts with placement_id, species, clip, xyz.
    When ``output`` is given the manifest is written there (refusing an
    existing file) and the machine-readable arena expectations artifact is
    written alongside it.
    """
    bank = Path(bank)
    report = json.loads((bank / BANK_JSON).read_text())
    if report.get('schema') != 1 or report.get('bank') != BANK_HEADER:
        raise ValueError('Expected a P2 Bulblax bank build')
    if set(report.get('motions', {})) != set(SPECIES):
        raise ValueError('Bank build misses a Bulblax species')
    motions = report['motions']
    placements = _check_placements(placements, motions)
    bank_raw = (bank / BANK_TXT).read_bytes()
    models = []
    for species in SPECIES:
        for name, info in motions[species].items():
            for index in range(info['poses']):
                rel = f'{species}/bulblax_{species}_{name}_{index:02}.mod'
                path = bank / rel
                data = path.read_bytes()
                if report.get('file_sha256', {}).get(path.name) != sha(data):
                    raise ValueError('Bank report/file hash mismatch: ' + rel)
                models.append({'path': rel, 'bytes': len(data), 'sha256': sha(data)})
    clips = {species: [{'name': name,
                        'source_frames': info['source_frames'],
                        'sampled_frames': list(info['frames'])}
                       for name, info in motions[species].items()]
             for species in SPECIES}
    unsupported = {s: u for s, u in report.get('unsupported', {}).items() if u}
    manifest = {'schema': SCHEMA,
                'artifact': MANIFEST,
                'bank': {'header': BANK_HEADER, 'sha256': sha(bank_raw)},
                'species': [{'name': name, 'enemy_id': identity} for name, identity in SPECIES.items()],
                'models': models,
                'clips': clips,
                'placements': placements,
                'normal_policy': {s: dict(p) for s, p in report.get('normal_policy', {}).items()},
                'material_policy': MATERIAL_POLICY,
                'unsupported_frames': unsupported,
                'native_ready': False,
                'limitations': list(LIMITATIONS)}
    if output is not None:
        output = Path(output)
        target = output if output.suffix == '.json' else output / MANIFEST
        if target.exists():
            raise ValueError('Refusing to overwrite existing manifest')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((json.dumps(manifest, indent=2) + '\n').encode('ascii'))
        write_expectations(manifest, target.parent / EXPECTATIONS)
    return manifest


def write_expectations(manifest, path):
    """Write the machine-readable arena expectations artifact.

    Every fixture carries the default small starting squad; the intentional
    zero-population case is a separate, explicitly named fixture.
    """
    if Path(path).exists():
        raise ValueError('Refusing to overwrite existing expectations artifact')
    base = {'schema': 1,
            'manifest_sha256': sha((json.dumps(manifest, sort_keys=True) + '\n').encode('ascii')),
            'starting_squad': dict(DEFAULT_SQUAD),
            'placements': [{'generator': p['placement_id'], 'species': p['species'],
                            'enemy_id': SPECIES[p['species']], 'clip': p['clip'],
                            'expected_xyz': list(p['xyz'])}
                           for p in manifest['placements']],
            'gates': {key: 'untested' for key in
                      ('native_identity', 'natural_AI', 'combat', 'death', 'delivery', 'reload')},
            'limitations': list(LIMITATIONS)}
    zero = dict(base)
    zero['starting_squad'] = dict(ZERO_SQUAD)
    zero['note'] = 'Intentional zero-population fixture; separate from the default squad fixtures.'
    payload = {'schema': 1,
               'artifact': EXPECTATIONS,
               'fixtures': {'default': base, 'zero_population': zero}}
    Path(path).write_bytes((json.dumps(payload, indent=2) + '\n').encode('ascii'))
    return payload


def validate(manifest_source, bank):
    """Independently validate a manifest against its bank build; no writes.

    ``manifest_source`` is a manifest dict or a path to one. Rejects
    unsupported schema versions, absolute/traversing model paths, duplicate
    placement IDs, unknown species/clips, non-finite XYZ, hash/byte drift and
    any clip/frame set that does not match the bank report.
    """
    if type(manifest_source) is dict:
        manifest = manifest_source
    else:
        manifest = json.loads(Path(manifest_source).read_bytes())
    if manifest.get('schema') != SCHEMA:
        raise ValueError('Unsupported bulblax-install schema version')
    bank = Path(bank)
    report = json.loads((bank / BANK_JSON).read_text())
    if report.get('schema') != 1 or report.get('bank') != BANK_HEADER:
        raise ValueError('Expected a P2 Bulblax bank build')
    if manifest.get('bank', {}).get('header') != BANK_HEADER or \
            manifest['bank'].get('sha256') != sha((bank / BANK_TXT).read_bytes()):
        raise ValueError('Manifest bound to a different bank')
    species = manifest.get('species')
    if type(species) is not list or {s.get('name'): s.get('enemy_id') for s in species
                                     if type(s) is dict} != SPECIES:
        raise ValueError('Manifest species identity mismatch')
    motions = report.get('motions', {})
    clips = manifest.get('clips', {})
    if set(clips) != set(SPECIES):
        raise ValueError('Manifest clip set mismatch')
    for name in SPECIES:
        expected = [{'name': c, 'source_frames': m['source_frames'], 'sampled_frames': m['frames']}
                    for c, m in motions[name].items()]
        if clips[name] != expected:
            raise ValueError(f'Manifest clips mismatch for {name}')
    _check_placements(manifest.get('placements'), motions)
    models = manifest.get('models')
    if type(models) is not list or not models:
        raise ValueError('Manifest carries no models')
    seen = set()
    for entry in models:
        if type(entry) is not dict:
            raise ValueError('Invalid manifest model entry')
        rel = entry.get('path')
        if type(rel) is not str or '\\' in rel or ':' in rel:
            raise ValueError('Invalid manifest model path')
        parts = PurePosixPath(rel).parts
        if PurePosixPath(rel).is_absolute() or rel.startswith('/') or '..' in parts \
                or str(PurePosixPath(rel)) != rel \
                or any(not part or part == '.' for part in parts):
            raise ValueError('Absolute/traversing manifest model path: ' + rel)
        if rel in seen:
            raise ValueError('Duplicate manifest model path: ' + rel)
        seen.add(rel)
        data = (bank / rel).read_bytes() if (bank / rel).is_file() else None
        if data is None or len(data) != entry.get('bytes') or sha(data) != entry.get('sha256'):
            raise ValueError('Manifest model hash/byte mismatch: ' + rel)
    expected_models = {f'{s}/bulblax_{s}_{c}_{i:02}.mod'
                       for s in SPECIES for c, m in motions[s].items()
                       for i in range(m['poses'])}
    if seen != expected_models:
        raise ValueError('Manifest does not cover every converted bank clip pose')
    if manifest.get('unsupported_frames') != {s: u for s, u in report.get('unsupported', {}).items() if u}:
        raise ValueError('Manifest unsupported-frame record mismatch')
    return manifest


def install(manifest_source, bank, destination):
    """Install validated manifest bytes into a FRESH destination directory.

    The destination must not exist beforehand and is never modified when any
    check fails; validation completes before the first copy.
    """
    destination = Path(destination)
    manifest = validate(manifest_source, bank)
    if destination.exists():
        raise ValueError('Refusing existing Bulblax installation destination')
    bank = Path(bank)
    payloads = [(PurePosixPath(m['path']), (bank / m['path']).read_bytes())
                for m in manifest['models']]
    manifest_bytes = (json.dumps(manifest, indent=2) + '\n').encode('ascii')
    started = time.perf_counter()
    destination.mkdir(parents=True)
    for rel, data in payloads:
        target = destination.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination / MANIFEST).write_bytes(manifest_bytes)
    expectations = write_expectations(manifest, destination / EXPECTATIONS)
    receipt = {'schema': 1, 'artifact': 'bulblax-install-receipt.json',
               'manifest_sha256': sha(manifest_bytes),
               'bank_sha256': manifest['bank']['sha256'],
               'models': len(payloads),
               'model_bytes': sum(len(d) for _, d in payloads),
               'placements': [p['placement_id'] for p in manifest['placements']],
               'expectations_sha256': sha((destination / EXPECTATIONS).read_bytes()),
               'native_ready': False,
               'install_seconds': time.perf_counter() - started}
    (destination / 'bulblax-install-receipt.json').write_bytes(
        (json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    emit_args = sub.add_parser('emit')
    emit_args.add_argument('--bank', type=Path, required=True)
    emit_args.add_argument('--output', type=Path, required=True)
    emit_args.add_argument('--placement', action='append', required=True,
                           metavar='ID:SPECIES:CLIP:X,Y,Z')
    install_args = sub.add_parser('install')
    install_args.add_argument('--manifest', type=Path, required=True)
    install_args.add_argument('--bank', type=Path, required=True)
    install_args.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'emit':
        placements = []
        for raw in args.placement:
            identity, species, clip, xyz = raw.split(':', 3)
            placements.append({'placement_id': int(identity), 'species': species,
                               'clip': clip, 'xyz': [float(v) for v in xyz.split(',')]})
        result = emit(args.bank, placements, args.output)
        print(json.dumps({'models': len(result['models']),
                          'placements': len(result['placements'])}, indent=2))
    else:
        print(json.dumps(install(args.manifest, args.bank, args.destination), indent=2))
