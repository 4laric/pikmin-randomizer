"""Private ShijimiChou (EnemyID 77) install from the converted flying bank.

Lane 15 (#166) bounded native slice. The batch-1/batch-2 flying installer
(``pikmin2_flying_install.py``) deliberately classifies ShijimiChou as helper
only and refuses a ShijimiChou actor row. This module wires the explicit
staging the native ``pc_p2_shijimi`` slice consumes, reusing the *same*
already-converted poses (``fly_ShijimiChou_<clip>_<nn>.mod``) from the flying
import. It writes ``p2-shijimi-bank.txt`` (``P2_SHIJIMI_BANK_1``) in the source
ShijimiAnimID order carry/dead/move and ``p2-shijimi-actors.txt``
(``P2_SHIJIMI_ACTORS_1``), and copies each pose to
``assets/dataDir/courses/pikmin2room/shijimi_<clip>_<nn>.mod``.

No retail asset is committed or distributed here; everything stays in a private
ignored run directory. All conflicts are refused before any mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_animation import resource_chunks

MANIFEST = 'flying.json'
SOURCE_ID = 77
SPECIES = 'ShijimiChou'
CLIPS = ('carry', 'dead', 'move')
EXPECTED_EVENTS = {'carry': [[10, 0], [29, 1]], 'dead': [], 'move': [[0, 0], [7, 1]]}
BANK_TXT = 'p2-shijimi-bank.txt'
ACTORS_TXT = 'p2-shijimi-actors.txt'
ACTORS_HEADER = 'P2_SHIJIMI_ACTORS_1'
BANK_HEADER = 'P2_SHIJIMI_BANK_1'
INSTALL_JSON = 'shijimi-install.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _species(metadata):
    if metadata.get('schema') != 1 or metadata.get('policy') != 'P2_FLYING_1':
        raise ValueError('Unsupported flying import schema')
    species = metadata.get('species')
    if not isinstance(species, dict) or SPECIES not in species:
        raise ValueError('Missing ShijimiChou flying import')
    info = species[SPECIES]
    if info.get('enemy_id') != SOURCE_ID:
        raise ValueError('ShijimiChou enemy ID mismatch')
    return info


def payload(imported):
    """Validate the converted ShijimiChou bank and return (bank_bytes, files)."""
    metadata = json.loads((imported / MANIFEST).read_text())
    info = _species(metadata)
    by_name = {clip['name']: clip for clip in info.get('clips', [])}
    if set(by_name) != set(CLIPS):
        raise ValueError('Unexpected ShijimiChou clip registry')
    lines = [BANK_HEADER]
    files = {}
    reference = None
    total = 0
    for name in CLIPS:
        clip = by_name[name]
        duration = clip.get('source_frames')
        if type(duration) is not int or not 1 <= duration <= 10000:
            raise ValueError('Invalid ShijimiChou clip duration')
        if clip.get('events') != EXPECTED_EVENTS[name]:
            raise ValueError('ShijimiChou key events mismatch: ' + name)
        poses = [pose for pose in clip.get('poses', []) if 'file' in pose]
        if not 2 <= len(poses) <= 10:
            raise ValueError('Invalid ShijimiChou pose count: ' + name)
        frames = [pose['frame'] for pose in poses]
        if frames != sorted(set(frames)) or frames[0] != 0 or frames[-1] != duration - 1:
            raise ValueError('Invalid ShijimiChou source frames: ' + name)
        lines.append(f'{name} {len(poses)} {duration} ' + ' '.join(map(str, frames)))
        for index, pose in enumerate(poses):
            filename = pose['file']
            if Path(filename).name != filename or not filename.endswith('.mod'):
                raise ValueError('Unsafe pose filename')
            source = imported / SPECIES / filename
            data = source.read_bytes()
            if sha(data) != pose.get('sha256'):
                raise ValueError('Pose hash mismatch: ' + filename)
            resources = resource_chunks(data)
            if reference is not None and resources != reference:
                raise ValueError('ShijimiChou pose changes immutable render resources')
            reference = resources
            total += len(data)
            if total > 2 * 1024 * 1024:
                raise ValueError('Native bank budget exceeded')
            files[f'shijimi_{name}_{index:02}.mod'] = data
    return ('\n'.join(lines) + '\n').encode('ascii'), files, len(files)


def install(imported, run, generators):
    """Install the bank/actors configs and private poses into a private run."""
    ids = list(generators)
    if not 1 <= len(ids) <= 8 or any(type(i) is not int or not 0 <= i <= 0xffffffff for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Invalid actor IDs')
    bank, files, poses = payload(imported)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction model directory')
    configs = {
        BANK_TXT: bank,
        ACTORS_TXT: (f'{ACTORS_HEADER} {len(ids)}\n' + '\n'.join(map(str, ids)) + '\n').encode('ascii'),
    }
    for existing in run.glob('p2-*-actors.txt'):
        tokens = existing.read_text().split()
        if len(tokens) < 2 or not tokens[1].isdigit() or int(tokens[1]) != len(tokens) - 2:
            raise ValueError('Malformed existing actor bindings: ' + existing.name)
        if set(ids) & set(map(int, tokens[2:])):
            raise ValueError('Actor binding overlap')
    targets = [run / name for name in configs] + [room / name for name in files]
    if any(target.exists() for target in targets):
        raise ValueError('Refusing existing ShijimiChou installation')
    for name, data in files.items():
        (room / name).write_bytes(data)
    for name, data in configs.items():
        (run / name).write_bytes(data)
    receipt = dict(schema=1, source_id=SOURCE_ID, species=SPECIES, generators=ids,
                   manifest_sha256=sha((imported / MANIFEST).read_bytes()),
                   poses=poses,
                   file_sha256={name: sha(data) for name, data in files.items()},
                   bank_sha256=sha(bank),
                   actors_sha256=sha(configs[ACTORS_TXT]),
                   reward='source plant-origin P1 nectar on dead-animation end',
                   native_runtime='pc_p2_shijimi (lane 15)')
    (run / INSTALL_JSON).write_bytes((json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode('ascii'))
    return receipt


def verify_install(imported, run, generators):
    ids = list(generators)
    bank, files, _poses = payload(imported)
    if (run / BANK_TXT).read_bytes() != bank:
        raise ValueError('Installed bank mismatch')
    expected = (f'{ACTORS_HEADER} {len(ids)}\n' + '\n'.join(map(str, ids)) + '\n').encode('ascii')
    if (run / ACTORS_TXT).read_bytes() != expected:
        raise ValueError('Installed actors mismatch')
    room = run / 'assets/dataDir/courses/pikmin2room'
    receipt = json.loads((run / INSTALL_JSON).read_text())
    for name, data in files.items():
        target = room / name
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError('Installed pose mismatch: ' + name)
        if receipt.get('file_sha256', {}).get(name) != sha(data):
            raise ValueError('Receipt pose mismatch: ' + name)
    return dict(verified=sorted(files), generators=ids, poses=len(files))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--generators', type=int, nargs='+', required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.imported, args.run, args.generators), indent=2, sort_keys=True))
