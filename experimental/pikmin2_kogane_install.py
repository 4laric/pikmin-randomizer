"""Hash-bound beetle family (Kogane/Wealthy/Fart) installation into a private run.

Pipeline section 4: binds the batch-1 (#212) manifest hashes to the audited
source import and installs exact-byte configs into an already private run
directory. Every conflict or changed source is refused BEFORE any mutation.
The sampled pose bank is an optional visual bank: when its .mod files are
absent, installation proceeds with configs only and the room's baseline
visuals are preserved untouched. Native registration (pc_p2_kogane hook
wiring) belongs to the integration lead (#186) and is flagged on #219;
no shared/native edits here.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_kogane_assets import SPECIES, DROP_TABLES, MAX_FLIPS, FART_GAS_DURATION

BANK_JSON = 'beetles.json'
PROFILE_TXT = 'p2-kogane-profile.txt'
BANK_TXT = 'p2-kogane-bank.txt'
ACTORS_TXT = 'p2-kogane-actors.txt'
ACTORS_HEADER = 'P2_KOGANE_ACTORS_1'
INSTALL_JSON = 'kogane-install.json'
POSE_PREFIX = 'kogane'
EXPECTED_CLIPS = {'move.bca': [[2, 0], [11, 1]],
                  'wait.bca': [[0, 0], [14, 1]],
                  'damage.bca': [[5, 2], [7, 3], [29, 4]]}
EXPECTED_IDS = {'kogane': 9, 'wealthy': 10, 'fart': 11}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def profile_text():
    """Canonical LF profile: audited spawn/drop/gas contract tokens."""
    rows = ['P2_KOGANE_PROFILE_1']
    for name in ('kogane', 'wealthy', 'fart'):
        info = SPECIES[name]
        rows.append(f"species {name} {info['enemy_id']} {info['obj_class']} "
                    f"karada {'_'.join(map(str, info['karada_kcolor']))}")
        for hit, entry in enumerate(DROP_TABLES[name]):
            for branch in ('surface', 'cave'):
                rows.append(f'drop {name} {hit} {branch} ' + '_'.join(map(str, entry[branch][:3])))
    rows.append(f'flips {MAX_FLIPS}')
    rows.append(f'fart_gas_duration {FART_GAS_DURATION}')
    return '\n'.join(rows) + '\n'


def bank_text(manifest):
    """Canonical LF bank config from a validated manifest."""
    rows = ['P2_KOGANE_BANK_1', f"joints {len(manifest['shared']['joints'])}"]
    for clip in manifest['shared']['clips']:
        rows.append(f"clip {clip['file']} {clip['source_frames']} "
                    + ','.join(f'{f}:{e}' for f, e in clip['events'])
                    + f" poses {len(clip['poses'])}")
    return '\n'.join(rows) + '\n'


def plan(bank, generator_ids):
    """Validate everything and return the exact payloads; never writes."""
    ids = list(generator_ids)
    if not ids or len(ids) > 100 or len(set(ids)) != len(ids) or any(
            type(i) is not int or not 0 <= i <= 0xffffffff for i in ids):
        raise ValueError('Expected unique unsigned generator IDs')
    metadata = json.loads((bank / BANK_JSON).read_text())
    if metadata.get('schema') != 1 or metadata.get('family') != 'Kogane':
        raise ValueError('Wrong beetle bank identity')
    if set(metadata.get('species', {})) != set(EXPECTED_IDS) or any(
            metadata['species'][s].get('enemy_id') != i for s, i in EXPECTED_IDS.items()):
        raise ValueError('Bank species/ID mismatch')
    shared = metadata.get('shared', {})
    clips = shared.get('clips', [])
    if {c['file'] for c in clips} != set(EXPECTED_CLIPS):
        raise ValueError('Bank clip set mismatch')
    for clip in clips:
        if clip['events'] != EXPECTED_CLIPS[clip['file']]:
            raise ValueError('Bank event frames drifted: ' + clip['file'])
        if clip['status'] != 'converted' or not clip.get('poses'):
            raise ValueError('Required source pose unavailable: ' + clip['file'])
    profile_payload = profile_text().encode('ascii')
    bank_payload = bank_text(metadata).encode('ascii')
    # Optional visual bank: all-or-nothing. Absent preserves the baseline.
    expected = {}
    for clip in clips:
        for pose in clip['poses']:
            name = pose['file']
            if Path(name).name != name or not name.endswith('.mod'):
                raise ValueError('Unsafe pose filename')
            expected[name] = pose['sha256']
    found = [n for n in expected if (bank / 'shared' / n).exists()]
    stray = [p.name for p in (bank / 'shared').glob('*.mod') if p.name not in expected]
    files = {}
    if found or stray:
        if sorted(found) != sorted(expected) or stray:
            raise ValueError('Incomplete/unexpected beetle visual bank')
        for name, digest in expected.items():
            data = (bank / 'shared' / name).read_bytes()
            if sha(data) != digest:
                raise ValueError('Pose hash mismatch: ' + name)
            files[f'{POSE_PREFIX}_{name}'] = data
    return profile_payload, bank_payload, ids, files, metadata


def install(bank, run, generator_ids):
    """Install validated configs (and optional visuals) into a private run."""
    profile_payload, bank_payload, ids, files, metadata = plan(bank, generator_ids)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    targets = [run / PROFILE_TXT, run / BANK_TXT, run / ACTORS_TXT, run / INSTALL_JSON]
    targets += [room / name for name in files]
    if any(t.exists() for t in targets):
        raise ValueError('Refusing existing/conflicting beetle installation')
    for other in sorted(run.glob('p2-*-actors.txt')) + ([run / 'p2-sheargrub.txt'] if (run / 'p2-sheargrub.txt').exists() else []):
        tokens = other.read_text().split()
        if len(tokens) < 2 or not tokens[0].startswith('P2_') or not tokens[0].endswith('_1'):
            raise ValueError('Invalid existing actor bindings: ' + other.name)
        used = set()
        for token in tokens[2:]:
            try:
                used.add(int(token))
            except ValueError:
                pass  # species/id columns in legacy row formats
        if used & set(ids):
            raise ValueError('Generator ID overlap with ' + other.name)
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / PROFILE_TXT).write_bytes(profile_payload)
    (run / BANK_TXT).write_bytes(bank_payload)
    actors_text = f'{ACTORS_HEADER} {len(ids)}\n' + '\n'.join(map(str, ids)) + '\n'
    (run / ACTORS_TXT).write_bytes(actors_text.encode('ascii'))
    receipt = dict(schema=1, family='Kogane', enemy_ids=EXPECTED_IDS, generators=ids,
                   bank_manifest_sha256=sha((bank / BANK_JSON).read_bytes()),
                   profile_config_sha256=sha(profile_payload),
                   bank_config_sha256=sha(bank_payload),
                   actors_config_sha256=sha(actors_text.encode('ascii')),
                   visuals='installed' if files else 'absent_baseline_preserved',
                   file_sha256={n: sha(b) for n, b in files.items()},
                   gameplay_events_executed=False,
                   native_registration='integration lead (#186); flagged on #219; not installed here')
    (run / INSTALL_JSON).write_bytes((json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--generators', type=int, nargs='+', required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.bank, args.run, args.generators), indent=2))
