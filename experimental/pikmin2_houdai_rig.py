"""Man-at-Legs (Houdai, 66) sampled joint pose bank for the native rig draw (#1012, parent #173).

The Long Legs lane bakes one static bind mesh plus a rigid skin sidecar
(``longlegs_Houdai_skin_00.txt``, see :mod:`experimental.pikmin2_long_legs_visual`).
Houdai is a rigid (envelope-free) 22-joint model and ships five real ``.bca``
clips on the disc (``landing``, ``wait``, ``flick``, ``attack``, ``dead``).
Instead of baking a whole mesh per pose (the BigFoot approach, which cannot carry
the IK legs or the aimable gun), this module samples every clip into
model-space joint matrices. The native draw interpolates the joint matrices
(rotation slerped, scale and translation lerped), lets the ported leg IK
overwrite the twelve leg joints, turns the gun joints toward the target and
evaluates the rigid skin, so one sampled bank drives the clip playback, the IK
walk, the gun aim and the collision tree at the same time.

``longlegs_Houdai_rig_00.txt`` (``P2_HOUDAI_RIG_1``)::

    P2_HOUDAI_RIG_1
    joints N
    j <index> <name> <parent or -1>            # N rows, .bmd joint order
    coll M
    c <id> <code> <radius> <joint> <ox> <oy> <oz> <parent or -1>   # enemycoll.txt order
    clips C
    clip <name> <duration> <samples>
    frames f0 f1 ...                           # strictly rising, 0 first, duration-1 last
    s <12*N floats>                            # one row per frame, joint-major 3x4 row-major

Sample frames are the uniform ``pose_limit`` frames (default 48, at least the
24 of DEFAULT_POSE_LIMIT) unioned with the clip's animation key-event frames
(``houdai/enemyanimmgr.txt``), so every key the source FSM reads lands on a
sample. Matrices come from ``bca_pose`` -> ``joint_matrices`` with the same J3D
path the pose banks use, so ``wait`` frame 0 and the skin sidecar bind agree.

Behaviour is unchanged by the bank itself; the native host reads it for
presentation and, through the posed gun joint, for the shell origin.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_animation import DEFAULT_POSE_LIMIT, POSE_LIMIT_MAX
from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_breadbug_assets import collision_nodes
from experimental.pikmin2_convert import blocks
from experimental.pikmin2_long_legs_visual import joint_names
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices

SPECIES = 'Houdai'
HEADER = 'P2_HOUDAI_RIG_1'
RIG = 'longlegs_Houdai_rig_00.txt'
REPORT = 'houdai-rig.json'
CLIPS = ('landing', 'wait', 'flick', 'attack', 'dead')
# Source animation key frames (docs/PIKMIN2_LONG_LEGS_AUDIT.md, houdai/enemyanimmgr.txt).
KEY_FRAMES = {
    'landing': (54, 84, 100, 130, 150),
    'wait': (0, 39),
    'flick': (40, 45, 68),
    'attack': (33, 34, 35, 37, 38, 39),
    'dead': (),
}
DEFAULT_RIG_POSES = 2 * DEFAULT_POSE_LIMIT
MIN_POSES = DEFAULT_POSE_LIMIT  # owner bar: at least 24 poses per clip (short clips keep every frame)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sample_frame_list(clip, duration, pose_limit=DEFAULT_RIG_POSES):
    """Uniform frames plus the clip's key frames, strictly rising, 0 and duration-1 included."""
    if type(duration) is not int or duration < 2:
        raise ValueError(f'Invalid {clip} duration {duration!r}')
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f'Pose limit must be 2..{POSE_LIMIT_MAX}')
    count = min(pose_limit, duration)
    frames = {round(i * (duration - 1) / max(1, count - 1)) for i in range(count)}
    frames.update(f for f in KEY_FRAMES.get(clip, ()) if 0 <= f < duration)
    frames.update((0, duration - 1))
    return sorted(frames)


def hierarchy(model_blocks, count):
    """Joint parents from INF1 (same walk as pikmin2_rigid.joint_matrices)."""
    h = model_blocks['INF1']
    at = struct.unpack_from('>I', h, 20)[0]
    stack, current, parents = [], None, {}
    while True:
        kind, index = struct.unpack_from('>HH', h, at)
        at += 4
        if kind == 0:
            break
        if kind == 1:
            stack.append(current)
        elif kind == 2:
            current = stack.pop()
        elif kind == 0x10:
            parents[index] = stack[-1] if stack else None
            current = index
    if set(parents) != set(range(count)):
        raise ValueError('Incomplete joint hierarchy')
    return [-1 if parents[i] is None else parents[i] for i in range(count)]


def _f(value):
    return format(float(value), '.7g')


def rig_text(names, parents, nodes, rows):
    """``rows`` = [(clip, duration, frames, samples)] in CLIPS order; samples[k] = N 3x4 matrices."""
    count = len(names)
    lines = [HEADER, f'joints {count}']
    for index, (name, parent) in enumerate(zip(names, parents)):
        if not name or any(c.isspace() for c in name):
            raise ValueError('Unsupported joint name')
        lines.append(f'j {index} {name} {parent}')
    lines.append(f'coll {len(nodes)}')
    for node in nodes:
        parent = -1 if node['parent'] is None else node['parent']
        lines.append('c %s %s %s %d %s %s %s %d' % (
            node['id'], node['code'], _f(node['radius']), node['joint'],
            _f(node['offset'][0]), _f(node['offset'][1]), _f(node['offset'][2]), parent))
    lines.append(f'clips {len(rows)}')
    for clip, duration, frames, samples in rows:
        if not frames or frames[0] != 0 or frames[-1] != duration - 1 \
                or any(b <= a for a, b in zip(frames, frames[1:])) or len(samples) != len(frames):
            raise ValueError(f'Invalid frame list for {clip}')
        lines.append(f'clip {clip} {duration} {len(frames)}')
        lines.append('frames ' + ' '.join(str(f) for f in frames))
        for sample in samples:
            if len(sample) != count:
                raise ValueError('Sample joint count mismatch')
            lines.append('s ' + ' '.join(_f(v) for matrix in sample for row in matrix for v in row))
    lines.append('end')
    return '\n'.join(lines) + '\n'


def bake(model, motions, coll_raw, pose_limit=DEFAULT_RIG_POSES):
    """Sample every clip of ``motions`` ({name.bca: bytes}); returns (text, report)."""
    if len(model) < 32 or model[:8] != b'J3D2bmd3':
        raise ValueError('Expected complete J3D2bmd3 model')
    model_blocks = blocks(model)
    if struct.unpack_from('>H', model_blocks['EVP1'], 8)[0] != 0:
        raise ValueError('Expected a rigid (envelope-free) Houdai model')
    names = joint_names(model_blocks)
    parents = hierarchy(model_blocks, len(names))
    nodes = collision_nodes(coll_raw, len(names))
    rows, clips = [], {}
    total = 0
    for clip in CLIPS:
        raw = motions[clip + '.bca']
        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        frames = sample_frame_list(clip, duration, pose_limit)
        samples = []
        for frame in frames:
            _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
            samples.append(joint_matrices(model_blocks, pose))
        rows.append((clip, duration, frames, samples))
        total += len(frames)
        clips[clip] = dict(source_frames=duration, poses=len(frames), frames=frames,
                           key_frames=list(KEY_FRAMES[clip]), source_sha256=sha(raw))
    text = rig_text(names, parents, nodes, rows)
    report = dict(schema=1, species=SPECIES, joints=len(names), collision_nodes=len(nodes),
                  pose_limit=pose_limit, total_poses=total, min_poses=min(c['poses'] for c in clips.values()),
                  rig_bytes=len(text.encode('ascii')), rig_sha256=sha(text.encode('ascii')),
                  model_sha256=sha(model), collision_sha256=sha(coll_raw), clips=clips)
    return text, report


def parse(text):
    """Validate and decode a rig text (test and tooling helper mirroring the native loader)."""
    tokens = text.split('\n')
    at = 0

    def line():
        nonlocal at
        if at >= len(tokens):
            raise ValueError('Truncated rig')
        at += 1
        return tokens[at - 1].split()

    if line() != [HEADER]:
        raise ValueError('Bad header')
    count = int(line()[1])
    names, parents = [], []
    for index in range(count):
        row = line()
        if row[0] != 'j' or int(row[1]) != index:
            raise ValueError('Bad joint row')
        names.append(row[2])
        parents.append(int(row[3]))
    coll = []
    for _ in range(int(line()[1])):
        row = line()
        coll.append(dict(id=row[1], code=row[2], radius=float(row[3]), joint=int(row[4]),
                         offset=[float(v) for v in row[5:8]], parent=int(row[8])))
    clips = {}
    for _ in range(int(line()[1])):
        head = line()
        name, duration, samples = head[1], int(head[2]), int(head[3])
        frames = [int(v) for v in line()[1:]]
        if len(frames) != samples or frames[0] != 0 or frames[-1] != duration - 1 \
                or any(b <= a for a, b in zip(frames, frames[1:])):
            raise ValueError(f'Bad frame list for {name}')
        matrices = []
        for _ in range(samples):
            row = line()
            if row[0] != 's' or len(row) != 1 + 12 * count:
                raise ValueError('Bad sample row')
            matrices.append([float(v) for v in row[1:]])
        clips[name] = dict(duration=duration, frames=frames, samples=matrices)
    if line() != ['end']:
        raise ValueError('Missing end')
    return dict(names=names, parents=parents, coll=coll, clips=clips)


def extract(iso, output, pose_limit=DEFAULT_RIG_POSES):
    """Bake the rig from the disc into ``output`` (created; existing files are refused)."""
    iso, output = Path(iso), Path(output)
    if (output / RIG).exists():
        raise FileExistsError('Refusing to overwrite existing Houdai rig')
    index = disc_files(iso)
    with iso.open('rb') as disc:
        def read(path):
            at, size = index[path]
            disc.seek(at)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError(f'Truncated disc entry: {path}')
            return raw
        model = archive_files(read(f'enemy/data/{SPECIES}/model.szs'))['enemy.bmd']
        motions = archive_files(read(f'enemy/data/{SPECIES}/anim.szs'))
        coll = archive_files(read('enemy/parm/enemyParms.szs'))['houdai/enemycoll.txt']
    missing = [c for c in CLIPS if c + '.bca' not in motions]
    if missing:
        raise ValueError(f'Houdai anim archive lacks {missing}')
    text, report = bake(model, motions, coll, pose_limit)
    output.mkdir(parents=True, exist_ok=True)
    (output / RIG).write_bytes(text.encode('ascii'))
    (output / REPORT).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=DEFAULT_RIG_POSES)
    args = parser.parse_args()
    result = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps({k: v for k, v in result.items() if k != 'clips'}, sort_keys=True))
