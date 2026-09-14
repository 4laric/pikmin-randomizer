"""Strict private Mamuta (Miulin, ID 54) visual install; native proxy integration is separate.

Batch 2 (#221). Consumes the batch-1 extraction (`mamuta.json` schema 1) and
installs bounded source poses into a private run layout for the P1 Miurin
proxy actor. Refuses existing targets and hash mismatches before mutation.

Every motion the native observer maps installs all sampled poses as
`miulin_<clip>_<i>.mod` plus a bank manifest (`p2-mamuta-bank.txt`) carrying the
clip length, sampled source frames and gameplay event frames, so the observer
can place the strike at its sampled event frame instead of a uniform index.
"""
import hashlib
import json
from pathlib import Path

SPECIES = 'Miulin'
BANK_CLIPS = ('wait', 'waitact', 'move', 'attack0', 'attack1', 'attack4',
              'flick', 'dead', 'type5')
MAX_POSES = 8
CONFIG_NAME = 'p2-mamuta-actors.txt'
CONFIG_HEADER = 'P2_MAMUTA_ACTORS_1'
BANK_NAME = 'p2-mamuta-bank.txt'
BANK_HEADER = 'P2_MAMUTA_BANK_1'


def plan(imported, actors):
    actors = list(actors)
    if not 1 <= len(actors) <= 100:
        raise ValueError('Expected 1..100 actors')
    metadata = json.loads((imported / 'mamuta.json').read_text())
    if metadata.get('schema') != 1 or metadata.get('species') != SPECIES:
        raise ValueError('Unsupported Mamuta import schema')
    if metadata.get('enemy_id') != 54:
        raise ValueError('Unexpected Mamuta enemy identity')
    ids = set()
    rows = [CONFIG_HEADER, str(len(actors))]
    files = {}
    for generator, species in actors:
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('Invalid/duplicate actor identity')
        if species != SPECIES:
            raise ValueError('Unsupported Mamuta actor species')
        ids.add(generator)
        rows.append(f'{generator} {SPECIES}')
    by_file = {c['file']: c for c in metadata['clips']}
    manifest = [f'{BANK_HEADER} {len(BANK_CLIPS)}']
    for clip in BANK_CLIPS:
        entry = by_file.get(clip + '.bca')
        if entry is None or entry['status'] != 'converted' or not entry['poses']:
            raise ValueError(f'Required source clip unavailable: {clip}')
        if len(entry['poses']) > MAX_POSES:
            raise ValueError(f'Too many sampled poses for {clip}')
        frames = []
        for index, pose in enumerate(entry['poses']):
            name = pose['file']
            if Path(name).name != name or not name.endswith('.mod'):
                raise ValueError('Unsafe pose filename')
            data = (imported / SPECIES / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != pose['sha256']:
                raise ValueError('Pose hash mismatch')
            files[f'miulin_{clip}_{index:02d}.mod'] = data
            frames.append(int(pose['frame']))
        if frames != sorted(frames) or len(set(frames)) != len(frames) or frames[0] != 0:
            raise ValueError(f'Unsorted or non-zero-start sampled frames for {clip}')
        source = frames[-1] + 1
        events = sorted({int(e['frame']) for e in entry.get('events', [])})
        if any(not 0 <= f < source for f in events):
            raise ValueError(f'Out-of-range event frame for {clip}')
        manifest.append(f'clip {clip} {source} {len(frames)} {len(events)}')
        manifest.append('frames ' + ' '.join(str(f) for f in frames))
        manifest.append('events ' + ' '.join(str(f) for f in events))
    files[BANK_NAME] = ('\n'.join(manifest) + '\n').encode('ascii')
    return '\n'.join(rows) + '\n', files


def _targets(run, files):
    room = run / 'assets/dataDir/courses/pikmin2room'
    for name, data in files.items():
        yield (run / name if name == BANK_NAME else room / name), data


def install(imported, run, actors):
    config, files = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.resolve() != room.absolute():
        raise ValueError('Expected private non-junction room')
    for target, _ in _targets(run, files):
        if target.exists():
            raise ValueError('Refusing existing visual target')
    if (run / CONFIG_NAME).exists():
        raise ValueError('Refusing existing actor config')
    for target, data in _targets(run, files):
        target.write_bytes(data)
    (run / CONFIG_NAME).write_text(config)
    return {'species': [SPECIES], 'actors': len(actors),
            'proxy_behavior': 'P1 Miurin (TEKI_Miurin 24); not source P2 FSM',
            'files': sorted(files), 'config': CONFIG_NAME, 'bank': BANK_NAME}


def verify_install(imported, run, actors):
    """Reload an installed layout and prove every artifact matches the import."""
    config, files = plan(imported, actors)
    if (run / CONFIG_NAME).read_text() != config:
        raise ValueError('Installed actor config mismatch')
    for target, data in _targets(run, files):
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError(f'Installed visual mismatch: {target.name}')
    return {'verified': sorted(files), 'config': CONFIG_NAME, 'bank': BANK_NAME}
