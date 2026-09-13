"""Long Legs family batch-2 installation into a private run (#312, parent #173).

Consumes the lane's batch-1 ``long-legs-family.json`` mesh profile (produced by
``experimental/pikmin2_long_legs_assets.py`` on branch ``codex/p2-longlegs-family``)
and installs the two owned ``enemy.bmd`` bind-pose meshes plus per-species
profile/bank/actor configs into a private run. Every installed mesh is bound by
SHA-256 to the manifest and conflicting or changed sources are refused before
any mutation. This is a visual/profile slice only: no skeleton playback, no
animation bank, no native actor. Native registration stays with the integration
lead (#186); Damagumo/Beady Long Legs (56) remains owned by the demon lane.
"""
import argparse
import json
import re
from pathlib import Path

MANIFEST = 'long-legs-family.json'
SPECIES = {'Houdai': 66, 'BigFoot': 69}
FOLDERS = {'Houdai': 'Houdai', 'BigFoot': 'BigFoot'}
ANCHORS = {'Houdai': ('wait', 'attack', 'landing'),
           'BigFoot': ('wait', 'flick', 'dead')}
PROFILE_TXT = 'p2-long-legs-profile.txt'
BANK_TXT = 'p2-long-legs-bank.txt'
ACTORS_TXT = 'p2-long-legs-actors.txt'
ACTORS_HEADER = 'P2_LONG_LEGS_ACTORS_1'
INSTALL_JSON = 'long-legs-install.json'
LANE = 'codex/p2-longlegs-family'


def sha(data):
    return __import__('hashlib').sha256(data).hexdigest()


def profile_text(manifest):
    rows = ['P2_LONG_LEGS_PROFILE_1']
    for species, identity in SPECIES.items():
        info = manifest['profiles'][str(identity)]
        present = ','.join(j['name'] for j in info['special_joints'] if j['present']) or '-'
        absent = ','.join(j['name'] for j in info['special_joints'] if not j['present']) or '-'
        rows.append(f'species {species} {identity} {info["retail"]}')
        rows.append(f'folder {species} {info["folder"]} joints {info["joint_count"]} '
                    f'textures {info["embedded_texture_count"]}')
        rows.append(f'special_present {species} {present}')
        rows.append(f'special_absent {species} {absent}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def bank_text(manifest):
    rows = ['P2_LONG_LEGS_BANK_1']
    for species, identity in SPECIES.items():
        info = manifest['profiles'][str(identity)]
        rows.append(f'species {species} {identity}')
        for clip, frames in sorted(info['animation_rows'].items()):
            rows.append(f'clip {species} {clip} frames {",".join(str(f) for f in frames)}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def actors_text(actors):
    rows = [ACTORS_HEADER, str(len(actors))]
    rows += [f'{generator} {species}' for generator, species in actors]
    return ('\n'.join(rows) + '\n').encode('ascii')


def _mesh_files(imported, manifest, species_list):
    expected = {}
    for species in species_list:
        info = manifest['profiles'][str(SPECIES[species])]
        digest = info.get('model_sha256')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Missing mesh SHA-256: ' + species)
        expected[species] = digest
    found = {species for species in expected
             if (imported / FOLDERS[species] / 'enemy.bmd').is_file()}
    stray = sorted(path.parent.name for path in imported.glob('*/enemy.bmd')
                   if path.parent.name not in FOLDERS.values())
    files = {}
    if found or stray:
        if found != set(expected) or stray:
            raise ValueError('Incomplete/unexpected Long Legs mesh bank: ' + ', '.join(stray))
        for species, digest in expected.items():
            data = (imported / FOLDERS[species] / 'enemy.bmd').read_bytes()
            if sha(data) != digest:
                raise ValueError('Mesh hash mismatch: ' + species)
            files[species] = data
    return files


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


def plan(imported, actors):
    actors = list(actors)
    if not 1 <= len(actors) <= 100:
        raise ValueError('Expected 1..100 actors')
    ids = set()
    for generator, species in actors:
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('Invalid/duplicate actor identity')
        if species not in SPECIES:
            raise ValueError('Unsupported Long Legs actor species: ' + str(species))
        ids.add(generator)
    manifest = json.loads((Path(imported) / MANIFEST).read_bytes())
    if manifest.get('schema') != 1 or manifest.get('family') != 'Long Legs':
        raise ValueError('Unsupported Long Legs import schema/family')
    if set(manifest.get('profiles', {})) != {str(v) for v in SPECIES.values()}:
        raise ValueError('Long Legs profile set mismatch')
    for species, identity in SPECIES.items():
        if manifest['profiles'][str(identity)].get('enemy_id') != identity:
            raise ValueError('Long Legs species/ID mismatch: ' + species)
    species_list = [s for s in SPECIES if s in {x[1] for x in actors}]
    for species in species_list:
        rows = manifest['profiles'][str(SPECIES[species])].get('animation_rows', {})
        for anchor in ANCHORS[species]:
            if anchor not in rows or not rows[anchor]:
                raise ValueError(f'Required {species} source anchor unavailable: ' + anchor)
    return (profile_text(manifest), bank_text(manifest), actors_text(actors),
            _mesh_files(Path(imported), manifest, species_list), manifest)


def install(imported, run, actors):
    imported = Path(imported)
    run = Path(run)
    profile_payload, bank_payload, actors_payload, files, manifest = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    targets = [run / PROFILE_TXT, run / BANK_TXT, run / ACTORS_TXT, run / INSTALL_JSON]
    targets += [room / (species + '_enemy.bmd') for species in files]
    if any(target.exists() or target.is_symlink() for target in targets):
        raise ValueError('Refusing existing/conflicting Long Legs installation')
    ids = [generator for generator, _ in actors]
    _check_sibling_overlap(run, ids)
    for species, data in files.items():
        (room / (species + '_enemy.bmd')).write_bytes(data)
    (run / PROFILE_TXT).write_bytes(profile_payload)
    (run / BANK_TXT).write_bytes(bank_payload)
    (run / ACTORS_TXT).write_bytes(actors_payload)
    receipt = dict(schema=1, family='Long Legs', lane=LANE, species=SPECIES,
                   generators=ids,
                   actors=[[generator, species] for generator, species in actors],
                   manifest_sha256=sha((imported / MANIFEST).read_bytes()),
                   profile_config_sha256=sha(profile_payload),
                   bank_config_sha256=sha(bank_payload),
                   actors_config_sha256=sha(actors_payload),
                   visuals='installed' if files else 'absent_baseline_preserved',
                   file_sha256={species: sha(data) for species, data in files.items()},
                   gameplay_events_executed=False, native_ready=False,
                   skeleton_playback=False,
                   native_registration='integration lead (#186); flagged on #312; not installed here')
    (run / INSTALL_JSON).write_bytes(
        (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('ascii'))
    return receipt


def verify_install(imported, run, actors):
    imported = Path(imported)
    run = Path(run)
    profile_payload, bank_payload, actors_payload, files, manifest = plan(imported, actors)
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
    for species, data in files.items():
        target = room / (species + '_enemy.bmd')
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError('Installed mesh mismatch: ' + species)
    return {'verified': sorted(files), 'config': ACTORS_TXT,
            'visuals': 'installed' if files else 'absent_baseline_preserved'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('imported', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 312001:Houdai')
    args = parser.parse_args()
    parsed = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(install(args.imported, args.run, parsed), sort_keys=True, indent=2))
