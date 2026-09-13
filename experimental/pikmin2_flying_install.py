"""Hash-bound flying-remainder (Mar/Hanachirashi/ShijimiChou) install into a private run.

Pipeline section 4 for the flying remainder lane (#375, parent #166), following
batch 1 (#348, commit a7c9ad7). Consumes the batch-1 `flying.json` manifest
(schema 1, policy P2_FLYING_1) and installs exact-byte configs plus an optional
sampled-pose visual bank into an already private run directory. Every conflict,
changed source or pose-hash mismatch is refused BEFORE any mutation, mirroring
`pikmin2_mamuta_install.py` (#221) and `pikmin2_kogane_install.py` (#219).

Mar (29) and Hanachirashi (55) are concrete spawnable species. ShijimiChou (77)
is helper-only for this lane: it is never written into the spawnable actor
config and its poses are not installed as lane visuals. It is bound explicitly
as helper/reward metadata instead (enemy ID, group count, runtime owner), so no
runtime ownership is claimed. Native actor registration belongs to the
integration lead (#186) and is flagged on #375; no shared/native edits here.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_flying_assets import (
    CLIPS, HELPER_SPECIES, SHIJIMICHOU_GROUP_COUNT, SPECIES)

MANIFEST = 'flying.json'
POLICY = 'P2_FLYING_1'
PROFILE_TXT = 'p2-flying-profile.txt'
BANK_TXT = 'p2-flying-bank.txt'
ACTORS_TXT = 'p2-flying-actors.txt'
ACTORS_HEADER = 'P2_FLYING_ACTORS_1'
INSTALL_JSON = 'flying-install.json'
SPAWNABLE = tuple(name for name in SPECIES if name not in HELPER_SPECIES)
HELPER_SPECIES_NAME = HELPER_SPECIES[0]
HELPER_RUNTIME_OWNER = ('family owners (Tanpopo, Ooinu_l, Magaret, Damagumo, '
                        'Mamuta, plant nodes)')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def profile_text(metadata):
    """Canonical LF profile: per-species identity, role and retail parm contract."""
    rows = ['P2_FLYING_PROFILE_1']
    for name in ('Mar', 'Hanachirashi', HELPER_SPECIES_NAME):
        info = metadata['species'][name]
        common = '_'.join(str(info.get('common_name', name)).split())
        rows.append(f"species {name} {info['enemy_id']} {common}")
        rows.append(f"helper {name} {1 if info.get('helper_only') else 0}")
        rows.append('role {0} {1}'.format(
            name, '_'.join(str(info.get('role', '')).split()) or 'unset'))
        proper = info.get('proper_retail', {})
        rows.append(f"proper {name} " + ' '.join(
            f'{key}:{proper[key]}' for key in sorted(proper)))
    rows.append(f'helper_group_count {HELPER_SPECIES_NAME} {SHIJIMICHOU_GROUP_COUNT}')
    return '\n'.join(rows) + '\n'


def bank_text(metadata):
    """Canonical LF bank: per-species clip/frame/event/pose listing."""
    rows = ['P2_FLYING_BANK_1']
    for name in ('Mar', 'Hanachirashi', HELPER_SPECIES_NAME):
        info = metadata['species'][name]
        rows.append(f'species {name} clips {len(info.get("clips", []))}')
        for clip in info.get('clips', []):
            events = ','.join(f'{frame}:{kind}'
                              for frame, kind in clip.get('events', [])) or '-'
            poses = sum(1 for pose in clip.get('poses', []) if 'file' in pose)
            rows.append(f"clip {name} {clip['name']} {clip.get('source_frames', 0)} "
                        f"{events} poses {poses} status {clip.get('status', '')}")
    return '\n'.join(rows) + '\n'


def _validate_actors(actors):
    actors = list(actors)
    if not 1 <= len(actors) <= 100:
        raise ValueError('Expected 1..100 actors')
    ids = []
    seen = set()
    for actor in actors:
        generator, kind = actor
        if (type(generator) is not int or not 0 <= generator <= 0xffffffff
                or generator in seen):
            raise ValueError('Invalid/duplicate actor identity')
        if kind not in SPAWNABLE:
            raise ValueError('Unsupported flying actor species')
        seen.add(generator)
        ids.append(generator)
    return actors, ids


def _helper_metadata(metadata):
    species = metadata['species']
    helper = species[HELPER_SPECIES_NAME]
    return dict(species=HELPER_SPECIES_NAME, enemy_id=helper['enemy_id'],
                common_name=helper.get('common_name', HELPER_SPECIES_NAME),
                helper_only=True, spawnable_actor=False, installed_visuals=False,
                group_count=SHIJIMICHOU_GROUP_COUNT,
                clips=len(helper.get('clips', [])),
                runtime_owner=HELPER_RUNTIME_OWNER)


def plan(imported, actors):
    """Validate everything and return exact payloads; never writes.

    Actor structure (count, ID type/range/uniqueness, spawnable species) is
    rejected before the manifest is touched, so malformed rosters never reach IO.
    """
    actors, ids = _validate_actors(actors)
    metadata = json.loads((imported / MANIFEST).read_text())
    if metadata.get('schema') != 1 or metadata.get('policy') != POLICY:
        raise ValueError('Unsupported flying import schema')
    if metadata.get('native_ready') is not False:
        raise ValueError('Flying import must declare native_ready false')
    species = metadata.get('species')
    if not isinstance(species, dict) or set(species) != set(SPECIES):
        raise ValueError('Flying species set mismatch')
    for name, enemy_id in SPECIES.items():
        info = species[name]
        if info.get('enemy_id') != enemy_id:
            raise ValueError('Flying species/ID mismatch')
        if bool(info.get('helper_only')) is not (name in HELPER_SPECIES):
            raise ValueError('Flying helper classification mismatch')
    profile_payload = profile_text(metadata).encode('ascii')
    bank_payload = bank_text(metadata).encode('ascii')
    # Optional visual bank over the spawnable species only: all-or-nothing.
    # Absent .mod files preserve the room baseline untouched. Helper poses are
    # deliberately excluded: no ShijimiChou runtime/visual ownership is claimed.
    expected = {}
    for name in SPAWNABLE:
        for clip in species[name].get('clips', []):
            for pose in clip.get('poses', []):
                filename = pose.get('file')
                if not filename:
                    continue
                if Path(filename).name != filename or not filename.endswith('.mod'):
                    raise ValueError('Unsafe pose filename')
                if filename in expected:
                    raise ValueError('Duplicate pose filename: ' + filename)
                digest = pose.get('sha256')
                if not isinstance(digest, str) or len(digest) != 64:
                    raise ValueError('Missing pose hash: ' + filename)
                expected[filename] = (name, digest)
    found = [name for name, (sp, _) in expected.items()
             if (imported / sp / name).is_file()]
    stray = [path.name for name in SPAWNABLE if (imported / name).is_dir()
             for path in (imported / name).glob('*.mod') if path.name not in expected]
    files = {}
    if found or stray:
        if len(found) != len(expected) or stray:
            raise ValueError('Incomplete/unexpected flying visual bank')
        for filename, (sp, digest) in expected.items():
            data = (imported / sp / filename).read_bytes()
            if sha(data) != digest:
                raise ValueError('Pose hash mismatch: ' + filename)
            files[filename] = data
    return (profile_payload, bank_payload, ids, files,
            _helper_metadata(metadata), metadata)


def _existing_generator_ids(run):
    used = set()
    for other in sorted(run.glob('p2-*-actors.txt')):
        tokens = other.read_text().split()
        if len(tokens) < 2 or not tokens[0].startswith('P2_') or not tokens[0].endswith('_1'):
            raise ValueError('Invalid existing actor bindings: ' + other.name)
        for token in tokens[2:]:
            try:
                used.add(int(token))
            except ValueError:
                continue
    return used


def install(imported, run, actors):
    """Install validated configs (and optional visuals) into a private run."""
    actors = list(actors)
    profile_payload, bank_payload, ids, files, helper, metadata = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    targets = [run / PROFILE_TXT, run / BANK_TXT, run / ACTORS_TXT, run / INSTALL_JSON]
    targets += [room / name for name in files]
    if any(target.exists() for target in targets):
        raise ValueError('Refusing existing/conflicting flying installation')
    if _existing_generator_ids(run) & set(ids):
        raise ValueError('Generator ID overlap with existing actor bindings')
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / PROFILE_TXT).write_bytes(profile_payload)
    (run / BANK_TXT).write_bytes(bank_payload)
    actors_text = f'{ACTORS_HEADER} {len(ids)}\n' + '\n'.join(
        f'{generator} {kind}' for generator, kind in actors) + '\n'
    (run / ACTORS_TXT).write_bytes(actors_text.encode('ascii'))
    receipt = dict(schema=1, policy=POLICY, enemy_ids=dict(SPECIES),
                   spawnable=list(SPAWNABLE), helper=helper, generators=ids,
                   bank_manifest_sha256=sha((imported / MANIFEST).read_bytes()),
                   profile_config_sha256=sha(profile_payload),
                   bank_config_sha256=sha(bank_payload),
                   actors_config_sha256=sha(actors_text.encode('ascii')),
                   visuals='installed' if files else 'absent_baseline_preserved',
                   file_sha256={name: sha(data) for name, data in files.items()},
                   gameplay_events_executed=False,
                   native_registration=('integration lead (#186); flagged on #375; '
                                        'not installed here'))
    (run / INSTALL_JSON).write_bytes((json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    return receipt


def verify_install(imported, run, actors):
    """Reload an installed layout and prove every artifact matches the import."""
    actors = list(actors)
    profile_payload, bank_payload, ids, files, _helper, _metadata = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (run / PROFILE_TXT).read_bytes() != profile_payload:
        raise ValueError('Installed profile config mismatch')
    if (run / BANK_TXT).read_bytes() != bank_payload:
        raise ValueError('Installed bank config mismatch')
    actors_text = f'{ACTORS_HEADER} {len(ids)}\n' + '\n'.join(
        f'{generator} {kind}' for generator, kind in actors) + '\n'
    if (run / ACTORS_TXT).read_bytes() != actors_text.encode('ascii'):
        raise ValueError('Installed actor config mismatch')
    receipt = json.loads((run / INSTALL_JSON).read_text())
    for name, data in files.items():
        target = room / name
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError('Installed visual mismatch: ' + name)
        if receipt.get('file_sha256', {}).get(name) != sha(data):
            raise ValueError('Installed receipt mismatch: ' + name)
    return {'verified': sorted(files), 'actors': ids, 'config': ACTORS_TXT}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('imported', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--actors', type=str, nargs='+', required=True,
                        help='generator:species pairs, e.g. 375001:Mar')
    args = parser.parse_args()
    roster = [tuple((int(part.split(':')[0]), part.split(':')[1]))
              for part in args.actors]
    print(json.dumps(install(args.imported, args.run, roster), indent=2))
