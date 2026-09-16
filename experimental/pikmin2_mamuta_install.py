"""Strict private Mamuta (Miulin, ID 54) visual install; native proxy integration is separate.

Batch 2 (#221). Consumes the batch-1 extraction (`mamuta.json` schema 1) and
installs bounded source poses into a private run layout for the P1 Miurin
proxy actor. Refuses existing targets and hash mismatches before mutation.
"""
import hashlib
import json
from pathlib import Path

SPECIES = 'Miulin'
# Install every sampled pose of the live/dead/attack clips as a time-sampled
# bank (`miulin_<clip>_<i>.mod`). The native observer plays the bank by the P1
# animator frame, so the ground strike (attack1, whose KEYEVENT_2 at frame 0 is
# the bury/plant) is animated instead of a single frozen pose.
BANK_CLIPS = ('wait', 'dead', 'attack1')
MAX_POSES = 8
# The approved native baseline (static anchors, pc_p2_mamuta_policy.h) loads
# three single `miulin_<clip>.mod` files: wait pose 0, the last dead pose, and
# the attack1 bury-event pose (frame 0). Stage these alongside the bank so the
# static anchor path and the pending time-sampled bank path coexist.
STATIC_CLIPS = {'wait': 0, 'dead': -1, 'attack1': 0}
CONFIG_NAME = 'p2-mamuta-actors.txt'
CONFIG_HEADER = 'P2_MAMUTA_ACTORS_1'


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
    for clip in BANK_CLIPS:
        entry = by_file.get(clip + '.bca')
        if entry is None or entry['status'] != 'converted' or not entry['poses']:
            raise ValueError(f'Required source clip unavailable: {clip}')
        if len(entry['poses']) > MAX_POSES:
            raise ValueError(f'Too many sampled poses for {clip}')
        for index, pose in enumerate(entry['poses']):
            name = pose['file']
            if Path(name).name != name or not name.endswith('.mod'):
                raise ValueError('Unsafe pose filename')
            data = (imported / SPECIES / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != pose['sha256']:
                raise ValueError('Pose hash mismatch')
            files[f'miulin_{clip}_{index:02d}.mod'] = data
    for clip, index in STATIC_CLIPS.items():
        entry = by_file.get(clip + '.bca')
        if entry is None or entry['status'] != 'converted' or not entry['poses']:
            raise ValueError(f'Required static pose unavailable: {clip}')
        pose = entry['poses'][index]
        name = pose['file']
        if Path(name).name != name or not name.endswith('.mod'):
            raise ValueError('Unsafe static pose filename')
        data = (imported / SPECIES / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != pose['sha256']:
            raise ValueError('Static pose hash mismatch')
        files[f'miulin_{clip}.mod'] = data
    return '\n'.join(rows) + '\n', files


def install(imported, run, actors):
    config, files = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.resolve() != room.absolute():
        raise ValueError('Expected private non-junction room')
    for name in files:
        if (room / name).exists():
            raise ValueError('Refusing existing visual target')
    if (run / CONFIG_NAME).exists():
        raise ValueError('Refusing existing actor config')
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / CONFIG_NAME).write_text(config)
    return {'species': [SPECIES], 'actors': len(actors),
            'proxy_behavior': 'P1 Miurin (TEKI_Miurin 24); not source P2 FSM',
            'files': sorted(files), 'config': CONFIG_NAME}


def verify_install(imported, run, actors):
    """Reload an installed layout and prove every artifact matches the import."""
    config, files = plan(imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (run / CONFIG_NAME).read_text() != config:
        raise ValueError('Installed actor config mismatch')
    for name, data in files.items():
        target = room / name
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError(f'Installed visual mismatch: {name}')
    return {'verified': sorted(files), 'config': CONFIG_NAME}
