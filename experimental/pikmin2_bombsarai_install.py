"""Hash-bound Careening Dirigibug installation into a private run (pipeline section 4).

Issue #244 (Careening Dirigibug lane: bomb-lob flight, projectile lifecycle),
integration contract #186, modeled on ``pikmin2_aquatic_install.py`` (#374) and
the batch-2 engine ``pikmin2_batch2_core.py``.

Provenance and schema decision
------------------------------
The lane search found a retail extraction under
``output/pikmin2-extract-bombsarai/`` (``parms/parsed_parms.json`` plus the
``bombsarai``/``bomb``/``sarai`` parm tables, BMD/SZS resources and
``aiConstants.txt``) but **no** schema-1 install manifest: the extraction has no
sampled ``.mod`` pose bank and no conversion pass has run (the audit and the
runtime evidence both record "no visual assets", converter dependency #128).
This module therefore defines the explicit lane schema ``P2_BOMBSARAI_IMPORT_1``
from the audited resource/parm/FSM data:

- ``disc_id``/``disc_revision`` identity (GPVE01 rev 0) and
  ``source_revision`` ``632af93787b9c95b63f0c13be32b161375ce3a96`` match the
  audit.
- species ``BombSarai`` (``EnemyID_BombSarai = 58``, ``enemyInfo.h:117``) and
  its payload ``Bomb`` (``EnemyID_Bomb = 36``, ``enemyInfo.h:95``) with three
  parameter blocks each: block 0 ``Creature::Property``, block 1
  ``EnemyParmsBase`` general, block 2 the proper family override - the same
  framing as the extracted ``*_enemyparm.txt`` tables.
- the clip catalog is the audited animation/FSM bank (``CARRIER_CLIPS`` /
  ``BOMB_CLIPS``); the TakeOff1/2 clip strings are not enumerated in the audit
  and stay converter (#128) work.

If a future conversion pass emits a ``bombsarai.json`` with the same schema and
recorded SHA-256 pose hashes, this installer consumes it unchanged. The sampled
pose bank is an optional all-or-nothing visual bank: when the ``.mod`` files are
absent, installation writes configs only and the room baseline is preserved
untouched. Native registration (shared ``Bomb`` manager pool, the 13-state
carrier FSM registration, the P1 static-map trace binding) belongs to the
integration lead (#186) and is flagged on #244; no shared/native edits here.
"""
import argparse
import hashlib
import json
from pathlib import Path

MANIFEST = 'bombsarai.json'
POLICY = 'P2_BOMBSARAI_IMPORT_1'
SOURCE_REVISION = '632af93787b9c95b63f0c13be32b161375ce3a96'
NATIVE_NAME = '246-BombSarai'
PROFILE_TXT = 'p2-bombsarai-profile.txt'
BANK_TXT = 'p2-bombsarai-bank.txt'
ACTORS_TXT = 'p2-bombsarai-actors.txt'
ACTORS_HEADER = 'P2_BOMBSARAI_ACTORS_1'
INSTALL_JSON = 'bombsarai-install.json'

# EnemyID_BombSarai = 58 and EnemyID_Bomb = 36 (native include/Game/enemyInfo.h).
SPECIES = {'BombSarai': 58, 'Bomb': 36}

# Clip catalog transcribed from the source audit
# (docs/PIKMIN2_BOMBSARAI_AUDIT.md, animation bank and Bomb FSM). TakeOff1/2
# clip strings are not enumerated by the audit and remain #128 converter work.
CARRIER_CLIPS = ('dead1', 'fall1', 'flick1', 'bflick1', 'mogaki1', 'release1',
                 'run1', 'run2', 'supli1', 'type5', 'wait1', 'wait2')
BOMB_CLIPS = ('hit_start', 'hit_loop')
CLIPS = {'BombSarai': CARRIER_CLIPS, 'Bomb': BOMB_CLIPS}
FSM_STATES = ('Dead', 'Damage', 'Wait', 'BombWait', 'Move', 'BombMove', 'Supply',
              'Release', 'Fall', 'TakeOff1', 'TakeOff2', 'Flick', 'BombFlick')

# One required visual anchor per source species: the carrier needs a live idle,
# an attack/release pose and a death pose; the payload needs its fuse arm loop
# and burning loop. Every clip that carries a pose is still bound and installed;
# the anchors are the minimum a proxy actor needs to be observable.
ANCHORS = {'BombSarai': ('wait1', 'release1', 'dead1'),
           'Bomb': ('hit_start', 'hit_loop')}
for _species, _anchors in ANCHORS.items():
    if _species not in SPECIES or not set(_anchors) <= set(CLIPS[_species]):
        raise ValueError('BombSarai anchor contract drifted from the audited clip bank')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _num(value):
    return f'{value:g}'


def _parm(block):
    return ' '.join(f'{key}={_num(block[key])}' for key in sorted(block))


def profile_text(manifest):
    """Canonical LF per-species parameter/profile contract from the manifest."""
    rows = ['P2_BOMBSARAI_PROFILE_1']
    for species, identity in SPECIES.items():
        info = manifest['species'][species]
        blocks = info.get('parameter_blocks', [])
        if len(blocks) != 3:
            raise ValueError('Unexpected parameter block framing: ' + species)
        rows.append(f'species {species} {identity}')
        rows.append(f'role {species} {info.get("role", "")}'.rstrip())
        rows.append(f'general {species} {_parm(blocks[1])}')
        rows.append(f'proper {species} {_parm(blocks[2])}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def bank_text(manifest):
    """Canonical LF clip/frame/event/pose listing for every sourced species."""
    rows = ['P2_BOMBSARAI_BANK_1']
    for species in SPECIES:
        info = manifest['species'][species]
        rows.append(f'species {species} {info["enemy_id"]}')
        for clip in info.get('clips', []):
            events = ','.join(f'{frame}:{event}' for frame, event in clip.get('events', []))
            poses = sum(1 for pose in clip.get('poses', []) if 'file' in pose)
            rows.append(f'clip {species} {clip["name"]} {clip.get("source_frames", 0)} '
                        f'{events or "-"} poses {poses} {clip.get("status", "unknown")}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def actors_text(actors):
    rows = [ACTORS_HEADER, str(len(actors))]
    rows += [f'{generator} {species}' for generator, species in actors]
    return ('\n'.join(rows) + '\n').encode('ascii')


def _actor_species(actors):
    used = {species for _, species in actors}
    return [species for species in SPECIES if species in used]


def _visual_files(imported, manifest, species_list):
    """Return installed-name -> exact bytes, or {} for a preserved baseline.

    The bank is all-or-nothing over the actor species: a partial bank, a stray
    ``.mod`` or any SHA-256 mismatch is refused before the caller mutates
    anything.
    """
    expected = {}
    for species in species_list:
        info = manifest['species'][species]
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
            raise ValueError('Incomplete/unexpected BombSarai visual bank: ' + ', '.join(stray))
        for (species, name), digest in expected.items():
            data = (imported / species / name).read_bytes()
            if sha(data) != digest:
                raise ValueError('Pose hash mismatch: ' + name)
            files[name] = data
    return files


def plan(imported, actors):
    """Validate everything and return exact payloads; never writes.

    Returns ``(profile_payload, bank_payload, actors_payload, files, metadata)``.
    """
    actors = list(actors)
    if not 1 <= len(actors) <= 100:
        raise ValueError('Expected 1..100 actors')
    ids = set()
    for generator, species in actors:
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('Invalid/duplicate actor identity')
        if species not in SPECIES:
            raise ValueError('Unsupported BombSarai actor species: ' + str(species))
        ids.add(generator)
    metadata = json.loads((imported / MANIFEST).read_bytes())
    if metadata.get('schema') != 1 or metadata.get('policy') != POLICY:
        raise ValueError('Unsupported BombSarai import schema/policy')
    if metadata.get('disc_id') != 'GPVE01' or metadata.get('disc_revision') != 0:
        raise ValueError('Unexpected BombSarai disc identity')
    if set(metadata.get('species', {})) != set(SPECIES):
        raise ValueError('BombSarai species set mismatch')
    for species, identity in SPECIES.items():
        if metadata['species'][species].get('enemy_id') != identity:
            raise ValueError('BombSarai species/ID mismatch: ' + species)
    species_list = _actor_species(actors)
    for species in species_list:
        by_clip = {clip['name']: clip for clip in metadata['species'][species].get('clips', [])}
        for anchor in ANCHORS[species]:
            clip = by_clip.get(anchor)
            if clip is None or clip.get('status') != 'converted' or not clip.get('poses'):
                raise ValueError(f'Required {species} source anchor unavailable: ' + anchor)
    profile_payload = profile_text(metadata)
    bank_payload = bank_text(metadata)
    actors_payload = actors_text(actors)
    files = _visual_files(Path(imported), metadata, species_list)
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
                pass  # species/id columns in legacy row formats
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
        raise ValueError('Refusing existing/conflicting BombSarai installation')
    ids = [generator for generator, _ in actors]
    _check_sibling_overlap(run, ids)
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / PROFILE_TXT).write_bytes(profile_payload)
    (run / BANK_TXT).write_bytes(bank_payload)
    (run / ACTORS_TXT).write_bytes(actors_payload)
    receipt = dict(schema=1, policy=POLICY, species=SPECIES,
                   source_revision=SOURCE_REVISION, native_name=NATIVE_NAME,
                   fsm_states=list(FSM_STATES), carrier_clips=list(CARRIER_CLIPS),
                   bomb_clips=list(BOMB_CLIPS),
                   generators=ids, actors=[[generator, species] for generator, species in actors],
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
