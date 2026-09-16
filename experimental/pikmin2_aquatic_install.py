"""Hash-bound aquatic-remainder installation into a private run (pipeline section 4).

Batch 2 (#374, parent #167), following batch 1 (#347, commit ``a7c9ad7``) and
modeled on ``pikmin2_mamuta_install.py`` (#221) and ``pikmin2_kogane_install.py``
(#219). Consumes the batch-1 ``aquatic.json`` schema-1 manifest (policy
``P2_AQUATIC_IMPORT_1``, species IDs 26 Catfish, 27 Tadpole, 63 Jigumo,
71 UmiMushi), validates identity and the required live/dead/attack visual
anchors, binds every installed pose by SHA-256, and refuses conflicting or
changed sources BEFORE any mutation. The sampled pose bank is an optional visual
bank: when the ``.mod`` files are absent, installation writes configs only and
the room's baseline is preserved untouched. Native registration (shared
Catfish/KochappyBase FSM, Jigumo PanHouse nest, shared ``UmiMushi::Mgr``) belongs
to the integration lead (#186) and is flagged on #374; no shared/native edits
here.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_aquatic_assets import SPECIES, CLIPS

MANIFEST = 'aquatic.json'
POLICY = 'P2_AQUATIC_IMPORT_1'
PROFILE_TXT = 'p2-aquatic-profile.txt'
BANK_TXT = 'p2-aquatic-bank.txt'
ACTORS_TXT = 'p2-aquatic-actors.txt'
ACTORS_HEADER = 'P2_AQUATIC_ACTORS_1'
INSTALL_JSON = 'aquatic-install.json'

# One required visual anchor per spawnable species (live/idle, attack, death).
# Every clip that carries a pose is still bound and installed; the anchors are
# the minimum a proxy actor needs to be observable at spawn, in combat and dead.
ANCHORS = {'Catfish': ('wait1', 'attack', 'dead'),
           'Tadpole': ('wait1', 'move1', 'dead'),
           'Jigumo': ('wait1', 'attack1', 'dead1'),
           'UmiMushi': ('run1', 'attack1', 'dead1')}
for _species, _anchors in ANCHORS.items():
    if _species not in SPECIES or not set(_anchors) <= set(CLIPS[_species]):
        raise ValueError('Aquatic anchor contract drifted from the batch-1 clips')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _num(value):
    return f'{value:g}'


def _parm(prefix, block):
    return ' '.join(f'{key}={_num(block[key])}' for key in sorted(block))


def profile_text(manifest):
    """Canonical LF per-species parameter/profile contract from the manifest."""
    rows = ['P2_AQUATIC_PROFILE_1']
    for species, identity in SPECIES.items():
        info = manifest['species'][species]
        blocks = info.get('parameter_blocks', [])
        if len(blocks) != 3:
            raise ValueError('Unexpected parameter block framing: ' + species)
        rows.append(f'species {species} {identity}')
        rows.append(f'role {species} {info.get("role", "")}'.rstrip())
        rows.append(f'general {species} {_parm("", blocks[1])}')
        rows.append(f'proper {species} {_parm("", blocks[2])}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def bank_text(manifest):
    """Canonical LF clip/frame/event/pose listing for every sourced species."""
    rows = ['P2_AQUATIC_BANK_1']
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
            raise ValueError('Incomplete/unexpected aquatic visual bank: ' + ', '.join(stray))
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
            raise ValueError('Unsupported aquatic actor species: ' + str(species))
        ids.add(generator)
    metadata = json.loads((imported / MANIFEST).read_bytes())
    if metadata.get('schema') != 1 or metadata.get('policy') != POLICY:
        raise ValueError('Unsupported aquatic import schema/policy')
    if metadata.get('disc_id') != 'GPVE01' or metadata.get('disc_revision') != 0:
        raise ValueError('Unexpected aquatic disc identity')
    if set(metadata.get('species', {})) != set(SPECIES):
        raise ValueError('Aquatic species set mismatch')
    for species, identity in SPECIES.items():
        if metadata['species'][species].get('enemy_id') != identity:
            raise ValueError('Aquatic species/ID mismatch: ' + species)
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
        raise ValueError('Refusing existing/conflicting aquatic installation')
    ids = [generator for generator, _ in actors]
    _check_sibling_overlap(run, ids)
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / PROFILE_TXT).write_bytes(profile_payload)
    (run / BANK_TXT).write_bytes(bank_payload)
    (run / ACTORS_TXT).write_bytes(actors_payload)
    receipt = dict(schema=1, policy=POLICY, species=SPECIES,
                   generators=ids, actors=[[generator, species] for generator, species in actors],
                   manifest_sha256=sha((imported / MANIFEST).read_bytes()),
                   profile_config_sha256=sha(profile_payload),
                   bank_config_sha256=sha(bank_payload),
                   actors_config_sha256=sha(actors_payload),
                   visuals='installed' if files else 'absent_baseline_preserved',
                   file_sha256={name: sha(data) for name, data in files.items()},
                   gameplay_events_executed=False, native_ready=False,
                   native_registration='integration lead (#186); flagged on #374; not installed here')
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
                        help='generator:species, e.g. 374001:Catfish')
    args = parser.parse_args()
    parsed = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(install(args.imported, args.run, parsed), sort_keys=True, indent=2))
