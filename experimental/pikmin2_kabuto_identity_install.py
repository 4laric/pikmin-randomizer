"""Strict source-bound Kabuto 75 identity installation."""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_animation import resource_chunks

SPECIES = 'Kabuto'
SOURCE_ID = 75
CLIPS = ('dead', 'move', 'flick', 'attack', 'wait')
MAX_POSES = 12
TOTAL_BYTES = 10 * 1024 * 1024


def plan(bank, actors):
    actors = list(actors)
    if not 1 <= len(actors) <= 32:
        raise ValueError('Expected 1..32 actors')
    seen = set()
    for identity, species in actors:
        if type(identity) is not int or not 0 <= identity <= 0xffffffff or identity in seen or species != SPECIES:
            raise ValueError('Invalid or duplicate Kabuto actor')
        seen.add(identity)
    raw = (bank / 'cannon_projectile.json').read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema') != 1 or manifest.get('policy') != 'P2_CANNON_PROJECTILE_1':
        raise ValueError('Unexpected Kabuto source manifest')
    info = manifest.get('species', {}).get(SPECIES)
    if info is None or info.get('enemy_id') != SOURCE_ID:
        raise ValueError('Unexpected Kabuto species identity')
    by_name = {Path(c.get('file', '')).stem if False else c.get('name', ''): c for c in info.get('clips', [])}
    # Cannon clips carry 'name' as stem (e.g. dead) plus file .bca; accept both keys.
    clips = []
    for name in CLIPS:
        c = None
        for cand in info.get('clips', []):
            stem = Path(cand.get('file', 'x.bca')).stem if 'file' in cand else cand.get('name', '')
            # Extractor writes clips with 'name' == stem? Handle both.
            n = cand.get('name', stem)
            if n == name or stem == name:
                c = cand
                break
        if c is None:
            raise ValueError(f'Missing Kabuto clip {name}')
        clips.append(c)
    lines = ['P2_KABUTO_1', str(len(actors))] + [f'{i} {s}' for i, s in actors]
    lines.append(SPECIES)
    files = []
    total = 0
    reference = None
    for clip, name in zip(clips, CLIPS):
        duration = clip.get('source_frames', clip.get('duration'))
        poses = clip.get('poses', [])
        frames = [p.get('frame') for p in poses]
        if clip.get('status') != 'converted' or type(duration) is not int or not 1 <= duration <= 10000:
            raise ValueError('Invalid Kabuto clip')
        if not 2 <= len(poses) <= MAX_POSES or frames[0] != 0 or frames[-1] != duration - 1:
            raise ValueError('Invalid Kabuto frame sequence')
        lines.append(f"{name} {len(poses)} {duration} " + ' '.join(map(str, frames)))
        for index, pose in enumerate(poses):
            src = pose.get('file')
            data = (bank / SPECIES / src).read_bytes() if (bank / SPECIES / src).is_file() else (bank / src).read_bytes()
            total += len(data)
            if not data or total > TOTAL_BYTES:
                raise ValueError('Kabuto pose budget exceeded')
            if len(data) != pose.get('bytes') or hashlib.sha256(data).hexdigest() != pose.get('sha256'):
                raise ValueError('Kabuto pose size/hash mismatch')
            resources = resource_chunks(data)
            if reference is not None and reference != resources:
                raise ValueError('Kabuto immutable resource mismatch')
            reference = resources
            dst = f"kabuto_{SPECIES}_{name}_{index:02}.mod"
            files.append((dst, data))
    return ('\n'.join(lines) + '\n').encode(), files, hashlib.sha256(raw).hexdigest()


def install(bank, run, actors):
    protocol, files, digest = plan(Path(bank), actors)
    run = Path(run)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or not room.resolve().is_relative_to(run.resolve()):
        raise ValueError('Expected private model destination')
    targets = [room / name for name, _ in files] + [run / 'p2-kabuto.txt', run / 'kabuto-identity-install.json']
    if any(p.exists() or p.is_symlink() for p in targets):
        raise ValueError('Refusing existing Kabuto target')
    for name, data in files:
        (room / name).write_bytes(data)
    (run / 'p2-kabuto.txt').write_bytes(protocol)
    result = dict(schema=1, manifest_sha256=digest, protocol_sha256=hashlib.sha256(protocol).hexdigest(),
                  models=len(files), bytes=sum(len(d) for _, d in files), native_ready=False,
                  behavior='P2 source FSM (Kabuto 75 stone fire); native P1 rewards unchanged')
    (run / 'kabuto-identity-install.json').write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--actor', action='append', required=True, help='generator:species')
    a = p.parse_args()
    print(json.dumps(install(a.bank, a.run, [(int(v.split(':')[0]), v.split(':')[1]) for v in a.actor])))
