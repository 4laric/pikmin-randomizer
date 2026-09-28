"""Hash-bound Dwarf Orange Bulborb (BlueKochappy) installation into a private run.

Pipeline section 4: binds the batch-1 bank/profile hashes to the same audited
source import and installs exact-byte configs into an already private run
directory. Every conflict or changed source is refused BEFORE any mutation.
The sampled pose bank is an optional visual bank: when its .mod files are
absent, installation proceeds with configs only and the room's baseline
visuals are preserved untouched. Native registration belongs to the
integration lead (#186); no shared/native edits here.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_dwarf_orange_bank import (
    BANK_JSON, BANK_TXT, PROFILE, PROFILE_JSON, PROFILE_TXT, POSE_PREFIX,
    parse_bank, validate_files)

SPECIES = 'BlueKochappy'
SOURCE_ID = 44
HEALTH = 250
ACTORS_TXT = 'p2-dwarf-orange-actors.txt'
ACTORS_HEADER = 'P2_DWARF_ORANGE_ACTORS_1'
INSTALL_JSON = 'dwarf-orange-install.json'
# Actor-binding configs written by other family installs; generator IDs must
# never overlap across families sharing one private run.
SIBLING_ACTOR_FILES = ('p2-snow-actors.txt', 'p2-kochappy-actors.txt',
                       'p2-dwarf-bear-actors.txt')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plan(bank, profile_dir, generator_ids):
    """Validate everything and return the exact payloads; never writes."""
    ids = list(generator_ids)
    if not ids or len(ids) > 100 or len(set(ids)) != len(ids) or any(
            type(i) is not int or not 0 <= i <= 0xffffffff for i in ids):
        raise ValueError('Expected unique unsigned generator IDs')
    metadata = json.loads((bank / BANK_JSON).read_text())
    if (metadata.get('schema'), metadata.get('species'),
            metadata.get('source_id'), metadata.get('health')) != (1, SPECIES, SOURCE_ID, HEALTH):
        raise ValueError('Wrong Dwarf Orange bank identity')
    reference_bytes = (profile_dir / PROFILE_JSON).read_bytes()
    if not metadata.get('reference_sha256') or metadata['reference_sha256'] != sha(reference_bytes):
        raise ValueError('Bank bound to a different source import')
    reference = json.loads(reference_bytes)
    if reference.get('schema') != 1 or reference.get('species') != SPECIES:
        raise ValueError('Wrong reference profile identity')
    profile_raw = (bank / PROFILE_TXT).read_bytes()
    try:
        profile_text = profile_raw.decode('ascii')
    except UnicodeDecodeError as exc:
        raise ValueError('Profile config not ASCII') from exc
    if profile_text.split() != PROFILE.split():
        raise ValueError('Profile config drifted from audited tokens')
    profile_payload = PROFILE.encode('ascii')  # canonical LF exact bytes
    bank_raw = (bank / BANK_TXT).read_bytes()
    try:
        bank_text = bank_raw.decode('ascii')
    except UnicodeDecodeError as exc:
        raise ValueError('Bank config not ASCII') from exc
    parsed = parse_bank(bank_text)
    expected_motions = metadata.get('motions', {})
    if set(parsed) != set(expected_motions):
        raise ValueError('Bank metadata motion set mismatch')
    for name, info in parsed.items():
        recorded = expected_motions[name]
        if (recorded.get('poses'), recorded.get('source_frames'),
                recorded.get('frames')) != (info['poses'], info['source_frames'], info['frames']):
            raise ValueError('Bank metadata mismatch: ' + name)
    # Optional visual bank: all-or-nothing. Absent preserves the baseline.
    expected_names = [f'{POSE_PREFIX}_{name}_{i:02}.mod'
                      for name, info in parsed.items() for i in range(info['poses'])]
    found = [n for n in expected_names if (bank / n).exists()]
    stray = [p.name for p in bank.glob(POSE_PREFIX + '_*.mod') if p.name not in expected_names]
    files = {}
    if found or stray:
        if sorted(found) != sorted(expected_names) or stray:
            raise ValueError('Incomplete/unexpected Dwarf Orange visual bank')
        paths, _ = validate_files(bank, parsed)
        if set(metadata.get('file_sha256', {})) != set(expected_names) or any(
                sha(p.read_bytes()) != metadata['file_sha256'][p.name] for p in paths):
            raise ValueError('Dwarf Orange visual bank hash mismatch')
        files = {p.name: p.read_bytes() for p in paths}
    # Canonical LF exact-byte payloads; Windows CRLF sources are normalized
    # only after full token/parse validation above.
    bank_payload = bank_text.replace('\r\n', '\n').encode('ascii')
    return profile_payload, bank_payload, ids, files, metadata


def install(bank, profile_dir, run, generator_ids):
    """Install validated configs (and optional visuals) into a private run."""
    profile_text, bank_text, ids, files, metadata = plan(bank, profile_dir, generator_ids)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    targets = [run / PROFILE_TXT, run / BANK_TXT, run / ACTORS_TXT, run / INSTALL_JSON]
    targets += [room / name for name in files]
    if any(t.exists() for t in targets):
        raise ValueError('Refusing existing/conflicting Dwarf Orange installation')
    for sibling in SIBLING_ACTOR_FILES:
        other = run / sibling
        if other.exists():
            tokens = other.read_text().split()
            if len(tokens) < 2 or not tokens[0].startswith('P2_') or not tokens[0].endswith('_ACTORS_1') \
                    or int(tokens[1]) != len(tokens) - 2:
                raise ValueError('Invalid existing actor bindings: ' + sibling)
            if set(map(int, tokens[2:])) & set(ids):
                raise ValueError('Generator ID overlap with ' + sibling)
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / PROFILE_TXT).write_bytes(profile_text)
    (run / BANK_TXT).write_bytes(bank_text)
    actors_text = f'{ACTORS_HEADER} {len(ids)}\n' + '\n'.join(map(str, ids)) + '\n'
    (run / ACTORS_TXT).write_bytes(actors_text.encode('ascii'))
    receipt = dict(schema=1, species=SPECIES, source_id=SOURCE_ID, health=HEALTH,
                   generators=ids,
                   bank_manifest_sha256=sha((bank / BANK_JSON).read_bytes()),
                   reference_sha256=metadata['reference_sha256'],
                   profile_config_sha256=sha(profile_text),
                   bank_config_sha256=sha(bank_text),
                   actors_config_sha256=sha(actors_text.encode('ascii')),
                   visuals='installed' if files else 'absent_baseline_preserved',
                   file_sha256={n: sha(b) for n, b in files.items()},
                   gameplay_events_executed=False,
                   native_registration='integration lead (#186); not installed here')
    (run / INSTALL_JSON).write_bytes((json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'profile', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--generators', type=int, nargs='+', required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.bank, args.profile, args.run, args.generators), indent=2))
