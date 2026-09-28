"""Strict source-bound Tank/Wtank identity installation; native P1 rewards remain."""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_animation import POSE_LIMIT_MAX, resident_clip_bytes, resource_chunks

SPECIES = {'Tank': 24, 'Wtank': 25}
CLIPS = ('dead', 'move1', 'flick', 'attack', 'waitact1', 'waitact2', 'type5')
# #895: native Tank loads through pc_p2_pose_loader.h (a few Shapes per clip
# plus decoded vectors): the shared native row cap, and budgets on the native
# resident measure (512 KiB per clip, 10 MiB per bank).
MAX_POSES = POSE_LIMIT_MAX
CLIP_BYTES = 512 * 1024
TOTAL_BYTES = 10 * 1024 * 1024


def plan(bank, actors):
    actors = list(actors)
    if not 1 <= len(actors) <= 32:
        raise ValueError('Expected 1..32 actors')
    seen = set()
    for identity, species in actors:
        if type(identity) is not int or not 0 <= identity <= 0xffffffff or identity in seen or species not in SPECIES:
            raise ValueError('Invalid or duplicate Tank actor')
        seen.add(identity)
    raw = (bank / 'tank.json').read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema') != 1 or set(manifest.get('variants', {})) != {'Tank', 'Wtank'}:
        raise ValueError('Unexpected Tank source manifest')
    lines = ['P2_TANK_1', str(len(actors))] + [f'{i} {s}' for i, s in actors]
    files = []
    total = 0
    for species, enemy_id in SPECIES.items():
        info = manifest['variants'][species]
        if info.get('enemy_id') != enemy_id:
            raise ValueError('Unexpected Tank species identity')
        clips = info.get('clips', [])
        if [Path(c.get('file', '')).stem for c in clips] != list(CLIPS):
            raise ValueError('Unexpected Tank clip identity')
        lines.append(species)
        reference = None
        for clip in clips:
            duration = clip.get('duration')
            poses = clip.get('poses', [])
            frames = [p.get('frame') for p in poses]
            if clip.get('status') != 'converted' or type(duration) is not int or not 1 <= duration <= 10000:
                raise ValueError('Invalid Tank clip')
            if not 2 <= len(poses) <= MAX_POSES or frames[0] != 0 or frames[-1] != duration - 1:
                raise ValueError('Invalid Tank frame sequence')
            if any(a >= b for a, b in zip(frames, frames[1:])):
                raise ValueError('Invalid Tank frame order')
            lines.append(f"{Path(clip['file']).stem} {len(poses)} {duration} " + ' '.join(map(str, frames)))
            clip_data = []
            for index, pose in enumerate(poses):
                src_name = pose.get('file')
                expected = f"{Path(clip['file']).stem}_{index:02}.mod"
                if src_name != expected:
                    raise ValueError('Unexpected Tank pose filename')
                data = (bank / species / src_name).read_bytes()
                clip_data.append(data)
                if not data:
                    raise ValueError('Tank pose budget exceeded')
                if len(data) != pose.get('bytes') or hashlib.sha256(data).hexdigest() != pose.get('sha256'):
                    raise ValueError('Tank pose size/hash mismatch')
                resources = resource_chunks(data)
                if reference is not None and reference != resources:
                    raise ValueError('Tank immutable resource mismatch')
                reference = resources
                dst = f"tank_{species}_{Path(clip['file']).stem}_{index:02}.mod"
                files.append((dst, data))
            resident = resident_clip_bytes(clip_data)
            total += resident
            if resident > CLIP_BYTES or total > TOTAL_BYTES:
                raise ValueError('Tank pose budget exceeded')
    return ('\n'.join(lines) + '\n').encode(), files, hashlib.sha256(raw).hexdigest()


def install(bank, run, actors):
    protocol, files, digest = plan(Path(bank), actors)
    run = Path(run)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or not room.resolve().is_relative_to(run.resolve()):
        raise ValueError('Expected private model destination')
    targets = [room / name for name, _ in files] + [run / 'p2-tank.txt', run / 'tank-identity-install.json']
    if any(p.exists() or p.is_symlink() for p in targets):
        raise ValueError('Refusing existing Tank target')
    for name, data in files:
        (room / name).write_bytes(data)
    (run / 'p2-tank.txt').write_bytes(protocol)
    result = dict(schema=1, manifest_sha256=digest, protocol_sha256=hashlib.sha256(protocol).hexdigest(),
                  models=len(files), bytes=sum(len(d) for _, d in files), native_ready=False,
                  behavior='P2 source FSM (Tank/Wtank); native P1 rewards unchanged')
    (run / 'tank-identity-install.json').write_bytes((json.dumps(result, sort_keys=True, indent=2) + '\n').encode())
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--actor', action='append', required=True, help='generator:species')
    a = p.parse_args()
    print(json.dumps(install(a.bank, a.run, [(int(v.split(':')[0]), v.split(':')[1]) for v in a.actor])))
