"""Lane-05 generated Dwarf Orange Bulborb content manifest (source 44).

Mirrors ``pikmin2_enemy.content_manifest`` for the generated Snow bank: emits a
validated, hash-bound content manifest from a revision-bounded Dwarf Orange
bank so session content staging serves ``assets/p2-dwarf-orange-profile.txt``
and ``assets/p2-dwarf-orange-bank.txt`` plus the private room ``.mod`` bank.
The manifest declares the roster source 44 so ``stage_session_content``
rejects content that does not cover the seed's bound identity. Read-only: no
installation, no native edits.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_dwarf_orange_bank import (
    BANK_JSON, BANK_TXT, PROFILE, PROFILE_JSON, PROFILE_TXT, POSE_PREFIX,
    parse_bank, validate_files)
from experimental.pikmin2_staging import build_manifest, dump_manifest

SPECIES = 'BlueKochappy'
SOURCE_ID = 44
HEALTH = 250
MODEL_DESTINATION = 'dataDir/courses/pikmin2room'
NOTES = 'Generated Dwarf Orange Bulborb bank (BlueKochappy 44)'


def content_manifest(bank):
    """Lane-05 content manifest staging a generated Dwarf Orange bank.

    Destinations are relative to the run's private asset overlay so the
    generated native bridge reads ``assets/p2-dwarf-orange-*.txt`` and the
    private room bank. The manifest declares the lane roster source 44 so
    session staging rejects content that does not serve the seed's identity.
    """
    bank = Path(bank)
    metadata = json.loads((bank / BANK_JSON).read_text())
    if (metadata.get('schema'), metadata.get('species'), metadata.get('source_id'),
            metadata.get('health')) != (1, SPECIES, SOURCE_ID, HEALTH):
        raise ValueError('Wrong Dwarf Orange bank identity')
    profile_raw = (bank / PROFILE_TXT).read_bytes()
    try:
        profile_text = profile_raw.decode('ascii')
    except UnicodeDecodeError as exc:
        raise ValueError('Profile config not ASCII') from exc
    if profile_text.split() != PROFILE.split():
        raise ValueError('Profile config drifted from audited tokens')
    bank_text = (bank / BANK_TXT).read_text()
    parsed = parse_bank(bank_text)
    recorded = metadata.get('motions', {})
    if set(parsed) != set(recorded):
        raise ValueError('Bank metadata motion set mismatch')
    for name, info in parsed.items():
        entry = recorded.get(name, {})
        if (entry.get('poses'), entry.get('source_frames'),
                entry.get('frames')) != (info['poses'], info['source_frames'], info['frames']):
            raise ValueError('Bank metadata mismatch: ' + name)
    paths, _ = validate_files(bank, parsed)
    expected_names = [f'{POSE_PREFIX}_{name}_{i:02}.mod'
                      for name, info in parsed.items() for i in range(info['poses'])]
    if set(metadata.get('file_sha256', {})) != set(expected_names) or any(
            hashlib.sha256(p.read_bytes()).hexdigest() != metadata['file_sha256'][p.name]
            for p in paths):
        raise ValueError('Dwarf Orange visual bank hash mismatch')
    entries = []
    for path in sorted(paths, key=lambda item: item.name):
        source = path.resolve()
        entries.append(dict(id=f'dwarf_orange_{path.name}', kind='model',
                            source=str(source),
                            destination=f'{MODEL_DESTINATION}/{path.name}',
                            sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    for filename, kind, destination, ident in (
            (BANK_TXT, 'config', 'p2-dwarf-orange-bank.txt', 'dwarf_orange_bank'),
            (PROFILE_TXT, 'config', 'p2-dwarf-orange-profile.txt', 'dwarf_orange_profile')):
        source = (bank / filename).resolve()
        entries.append(dict(id=ident, kind=kind, source=str(source),
                            destination=destination,
                            sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    return build_manifest(1, entries, notes=NOTES, identities=[SOURCE_ID])


def write_content_manifest(bank, path):
    """Write the lane-05 content manifest for a Dwarf Orange bank to ``path``."""
    return dump_manifest(content_manifest(bank), path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--content-manifest', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_content_manifest(args.bank, args.content_manifest), indent=2))