"""Hash-bound Careening Dirigibug (BombSarai, enemy ID 58) installation into a private run.

Lane #244, arena/integration contract #186, converter handoff #128. Modeled on
``pikmin2_aquatic_install.py`` and ``pikmin2_flying_install.py``.

There is no upstream schema-1 extraction manifest for this lane, so this module
defines its own explicit schema-1 policy ``P2_BOMBSARAI_IMPORT_1`` directly from
the audited data and binds every installed pose by SHA-256. Provenance:

- source audit: ``docs/PIKMIN2_BOMBSARAI_AUDIT.md`` (projectPiki/pikmin2
  revision 632af93787b9c95b63f0c13be32b161375ce3a96, US GPVE01 rev 0)
- projectile lifecycle: ``docs/PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md``
- carrier FSM: ``docs/PIKMIN2_BOMBSARAI_FSM.md``
- runtime probes: ``docs/PIKMIN2_BOMBSARAI_RUNTIME_EVIDENCE.md``

The import manifest is consumed as schema 1 with policy ``P2_BOMBSARAI_IMPORT_1``;
identity is validated against the audited enemy ID 58, the Bomb payload child ID
36 / child count 2 and the audited GPVE01 rev 0 source revision. Actor structure
is validated before the manifest is read, so malformed rosters never reach IO.
Conflicts and changed sources are refused before any mutation. The sampled pose
bank is all-or-nothing: absent ``.mod`` files preserve the room baseline.
Native actor registration belongs to the integration lead (#186) and is flagged
on #244; no shared/native edits here.
"""
import argparse
import hashlib
import json
from pathlib import Path

MANIFEST = 'bombsarai.json'
POLICY = 'P2_BOMBSARAI_IMPORT_1'
ENEMY = 'BombSarai'
ENEMY_ID = 58
PAYLOAD_ENEMY = 'Bomb'
PAYLOAD_ENEMY_ID = 36
PAYLOAD_CHILD_NUM = 2
DISC_ID = 'GPVE01'
DISC_REVISION = 0
SOURCE_REVISION = '632af93787b9c95b63f0c13be32b161375ce3a96'
DOCUMENTS = ('docs/PIKMIN2_BOMBSARAI_AUDIT.md',
             'docs/PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md',
             'docs/PIKMIN2_BOMBSARAI_FSM.md',
             'docs/PIKMIN2_BOMBSARAI_RUNTIME_EVIDENCE.md')
PROFILE_TXT = 'p2-bombsarai-profile.txt'
BANK_TXT = 'p2-bombsarai-bank.txt'
ACTORS_TXT = 'p2-bombsarai-actors.txt'
ACTORS_HEADER = 'P2_BOMBSARAI_ACTORS_1'
INSTALL_JSON = 'bombsarai-install.json'

# Audited clip bank (BombSarai.h:161-177, 14 clips). The import may carry a
# subset but nothing outside this list is accepted.
AUDITED_CLIPS = ('dead1', 'fall1', 'flick1', 'bflick1', 'mogaki1', 'release1',
                 'run1', 'run2', 'supli1', 'takeoff1', 'takeoff2', 'type5',
                 'wait1', 'wait2')
# Minimum visual anchors for a spawnable proxy: live/idle, carrying, throw and
# corpse. Every clip that carries a pose is still bound and installed.
ANCHORS = ('wait1', 'wait2', 'release1', 'dead1')

AUDIT = dict(enemy=ENEMY, enemy_id=ENEMY_ID, generator='バクダンサライ',
             payload=dict(enemy=PAYLOAD_ENEMY, enemy_id=PAYLOAD_ENEMY_ID,
                          child_num=PAYLOAD_CHILD_NUM),
             disc='GPVE01 rev 0', source_revision=SOURCE_REVISION,
             documents=list(DOCUMENTS),
             policy_origin=('lane-defined schema-1 policy P2_BOMBSARAI_IMPORT_1; '
                            'no upstream extraction manifest exists'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _num(value):
    return f'{value:g}'


def _parm(block):
    return ' '.join(f'{key}={_num(block[key])}' for key in sorted(block))


def profile_text(metadata):
    """Canonical LF profile: identity, payload contract and audited parms."""
    info = metadata['species'][ENEMY]
    blocks = info.get('parameter_blocks', [])
    if len(blocks) != 3:
        raise ValueError('Unexpected parameter block framing: ' + ENEMY)
    rows = ['P2_BOMBSARAI_PROFILE_1']
    rows.append(f'species {ENEMY} {info["enemy_id"]}')
    rows.append(f'payload {PAYLOAD_ENEMY} {PAYLOAD_ENEMY_ID} {PAYLOAD_CHILD_NUM}')
    rows.append(f'role {ENEMY} {info.get("role", "")}'.rstrip())
    rows.append(f'general {ENEMY} {_parm(blocks[1])}')
    rows.append(f'proper {ENEMY} {_parm(blocks[2])}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def bank_text(metadata):
    """Canonical LF clip/frame/event/pose listing for the carrier clips."""
    info = metadata['species'][ENEMY]
    rows = ['P2_BOMBSARAI_BANK_1']
    rows.append(f'species {ENEMY} {info["enemy_id"]}')
    for clip in info.get('clips', []):
        events = ','.join(f'{frame}:{event}' for frame, event in clip.get('events', []))
        poses = sum(1 for pose in clip.get('poses', []) if 'file' in pose)
        rows.append(f'clip {ENEMY} {clip["name"]} {clip.get("source_frames", 0)} '
                    f'{events or "-"} poses {poses} {clip.get("status", "unknown")}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def actors_text(actors):
    rows = [ACTORS_HEADER, str(len(actors))]
    rows += [f'{generator} {species}' for generator, species in actors]
    return ('\n'.join(rows) + '\n').encode('ascii')


def _visual_files(imported, metadata, species_list):
    """Return installed-name -> exact bytes, or {} for a preserved baseline.

    The bank is all-or-nothing over the actor species: a partial bank, a stray
    ``.mod`` or any SHA-256 mismatch is refused before the caller mutates.
    """
    expected = {}
    for species in species_list:
        info = metadata['species'][species]
        for clip in info.get('clips', []):
            for pose in clip.get('poses', []):
                if 'file' not in pose:
                    continue
                name = pose['file']
                digest = pose.get('sha256')
                if Path(name).name != name or not name.endswith('.mod'):
                    raise ValueError('Unsafe pose filename')
                if not isinstance(digest, str) or len(digest) != 64:
                    raise ValueError('Missing pose SHA-256: ' + name)
                if (species, name) in expected:
                    raise ValueError('Duplicate pose entry: ' + name)
                expected[(species, name)] = digest
    found = {key for key in expected if (imported / key[0] / key[1]).is_file()}
    stray = sorted(f'{species}/{path.name}'
                   for species in species_list
                   for path in (imported / species).glob('*.mod')
                   if (species, path.name) not in expected)
    files = {}
    if found or stray:
        if found != set(expected) or stray:
            raise ValueError('Incomplete/unexpected bombsarai visual bank: '
                             + ', '.join(stray))
        for (species, name), digest in expected.items():
            data = (imported / species / name).read_bytes()
            if sha(data) != digest:
                raise ValueError('Pose hash mismatch: ' + name)
            files[name] = data
    return files


def plan(imported, actors):
    """Validate everything and return exact payloads; never writes.

    Actor structure (count, ID type/range/uniqueness, species) is rejected
    before the manifest is touched, so malformed rosters never reach IO.

    Returns ``(profile_payload, bank_payload, actors_payload, files, metadata)``.
    """
    actors = list(actors)
    if not 1 <= len(actors) <= 100:
        raise ValueError('Expected 1..100 actors')
    ids = set()
    for generator, species in actors:
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('Invalid/duplicate actor identity')
        if species != ENEMY:
            raise ValueError('Unsupported bombsarai actor species: ' + str(species))
        ids.add(generator)
    metadata = json.loads((imported / MANIFEST).read_bytes())
    if metadata.get('schema') != 1 or metadata.get('policy') != POLICY:
        raise ValueError('Unsupported bombsarai import schema/policy')
    if metadata.get('disc_id') != DISC_ID or metadata.get('disc_revision') != DISC_REVISION:
        raise ValueError('Unexpected bombsarai disc identity')
    if metadata.get('source_revision') != SOURCE_REVISION:
        raise ValueError('Unexpected bombsarai source revision')
    species = metadata.get('species')
    if not isinstance(species, dict) or set(species) != {ENEMY}:
        raise ValueError('Bombsarai species set mismatch')
    info = species[ENEMY]
    if info.get('enemy_id') != ENEMY_ID:
        raise ValueError('BombSarai species/ID mismatch')
    payload = metadata.get('payload')
    if (not isinstance(payload, dict) or payload.get('enemy') != PAYLOAD_ENEMY
            or payload.get('enemy_id') != PAYLOAD_ENEMY_ID
            or payload.get('child_num') != PAYLOAD_CHILD_NUM):
        raise ValueError('BombSarai payload identity mismatch')
    by_clip = {clip['name']: clip for clip in info.get('clips', [])}
    unknown = set(by_clip) - set(AUDITED_CLIPS)
    if unknown:
        raise ValueError('Unexpected bombsarai clip bank: ' + ', '.join(sorted(unknown)))
    for anchor in ANCHORS:
        clip = by_clip.get(anchor)
        if clip is None or clip.get('status') != 'converted' or not clip.get('poses'):
            raise ValueError('Required BombSarai source anchor unavailable: ' + anchor)
    profile_payload = profile_text(metadata)
    bank_payload = bank_text(metadata)
    actors_payload = actors_text(actors)
    files = _visual_files(Path(imported), metadata, [ENEMY])
    return profile_payload, bank_payload, actors_payload, files, metadata


def _check_sibling_overlap(run, ids):
    for other in sorted(run.glob('p2-*-actors.txt')):
        tokens = other.read_text().split()
        if len(tokens) < 2 or not tokens[0].startswith('P2_') or not tokens[0].endswith('_1'):
            raise ValueError('Invalid existing actor bindings: ' + other.name)
        used = set()
        for token in tokens[2:]:
            try:
                used.add(int(token))
            except ValueError:
                pass
        if used & set(ids):
            raise ValueError('Generator ID overlap with ' + other.name)


def install(imported, run, actors):
    """Install validated configs (and optional visuals) into a private run."""
    imported = Path(imported)
    run = Path(run)
    profile_payload, bank_payload, actors_payload, files, metadata = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    targets = [run / PROFILE_TXT, run / BANK_TXT, run / ACTORS_TXT, run / INSTALL_JSON]
    targets += [room / name for name in files]
    if any(target.exists() or target.is_symlink() for target in targets):
        raise ValueError('Refusing existing/conflicting bombsarai installation')
    ids = [generator for generator, _ in actors]
    _check_sibling_overlap(run, ids)
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / PROFILE_TXT).write_bytes(profile_payload)
    (run / BANK_TXT).write_bytes(bank_payload)
    (run / ACTORS_TXT).write_bytes(actors_payload)
    receipt = dict(schema=1, policy=POLICY, enemy=ENEMY, enemy_id=ENEMY_ID,
                   payload=dict(enemy=PAYLOAD_ENEMY, enemy_id=PAYLOAD_ENEMY_ID,
                                child_num=PAYLOAD_CHILD_NUM),
                   generators=ids, actors=[[generator, species] for generator, species in actors],
                   audit=AUDIT,
                   manifest_sha256=sha((imported / MANIFEST).read_bytes()),
                   profile_config_sha256=sha(profile_payload),
                   bank_config_sha256=sha(bank_payload),
                   actors_config_sha256=sha(actors_payload),
                   visuals='installed' if files else 'absent_baseline_preserved',
                   file_sha256={name: sha(data) for name, data in files.items()},
                   gameplay_events_executed=False, native_ready=False,
                   native_registration='integration lead (#186); flagged on #244; not installed here')
    (run / INSTALL_JSON).write_bytes((json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('ascii'))
    return receipt


def verify_install(imported, run, actors):
    """Reload an installed layout and prove every artifact matches the import."""
    imported = Path(imported)
    run = Path(run)
    profile_payload, bank_payload, actors_payload, files, metadata = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (run / PROFILE_TXT).read_bytes() != profile_payload:
        raise ValueError('Installed profile config mismatch')
    if (run / BANK_TXT).read_bytes() != bank_payload:
        raise ValueError('Installed bank config mismatch')
    if (run / ACTORS_TXT).read_bytes() != actors_payload:
        raise ValueError('Installed actor config mismatch')
    if not (run / INSTALL_JSON).is_file():
        raise ValueError('Installed receipt missing')
    receipt = json.loads((run / INSTALL_JSON).read_text())
    if receipt.get('manifest_sha256') != sha((imported / MANIFEST).read_bytes()):
        raise ValueError('Installed receipt manifest mismatch')
    if receipt.get('actors_config_sha256') != sha(actors_payload):
        raise ValueError('Installed receipt actor hash mismatch')
    for name, data in files.items():
        target = room / name
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError('Installed visual mismatch: ' + name)
        if receipt.get('file_sha256', {}).get(name) != sha(data):
            raise ValueError('Installed receipt visual mismatch: ' + name)
    return {'verified': sorted(files), 'config': ACTORS_TXT,
            'visuals': 'installed' if files else 'absent_baseline_preserved'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('imported', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 244001:BombSarai')
    args = parser.parse_args()
    parsed = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(install(args.imported, args.run, parsed), sort_keys=True, indent=2))
