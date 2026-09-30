"""Raging Long Legs (BigFoot, 69) sampled pose bank for the native smooth draw.

The Long Legs lane bakes one static bind mesh per species. BigFoot is a 15-joint
model with four weighted EVP1 envelopes and ships four real ``.bca`` clips on
the disc (``wait``, ``landing``, ``flick``, ``dead``; ``filck.bca`` is an unused
duplicate spelling). This module bakes each clip into ``DEFAULT_POSE_LIMIT``
evenly spaced single-joint rigid meshes, exactly as the Snagret/Frog families do
(``bca_pose`` -> authored EVP1 ``draw_matrices`` -> ``decode(bake_rigid=True)``),
so the native ``p2posefamily`` loader can lerp and crossfade between them.

Files written to the output directory:

* ``longlegs_BigFoot_<clip>_NN.mod`` for every clip pose;
* ``p2-long-legs-animation.txt`` (``P2_LONG_LEGS_ANIMATION_1``): species line,
  then per clip ``name count duration frame...`` (frames strictly rising, 0
  first, duration-1 last);
* ``longlegs_BigFoot_skin_00.txt`` (``P2_BIGFOOT_SKIN_1``, #1018): the J3D
  skinning of the same vertex order (every position/normal's DRW1 draw matrix
  and raw value, the DRW1 table and the authored EVP1 inverse matrices), so the
  native draw can pose the body from the clip and the legs from the source IK
  exactly as J3DMtxBuffer::calcWeightEnvelopeMtx does.

Behaviour is unchanged: this is presentation only. The bind mesh is still
installed and remains the fallback.
"""
import argparse
import hashlib
import json
import struct
import tempfile
from pathlib import Path

from experimental.pikmin2_animation import DEFAULT_POSE_LIMIT, resource_chunks, sample_frames
from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import joints
from experimental.pikmin2_skinning import _envelopes, draw_matrices

SPECIES = 'BigFoot'
HEADER = 'P2_LONG_LEGS_ANIMATION_1'
CONFIG = 'p2-long-legs-animation.txt'
REPORT = 'long-legs-bank.json'
SKIN = 'longlegs_BigFoot_skin_00.txt'
SKIN_HEADER = 'P2_BIGFOOT_SKIN_1'
CLIPS = ('wait', 'landing', 'flick', 'dead')  # native clip names, in config order
STEM = 'longlegs_{species}_{clip}'
MAX_POSE_BYTES = 1024 * 1024  # native p2poseload::PoseFileBytes


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pose_name(clip, index):
    return STEM.format(species=SPECIES, clip=clip) + f'_{index:02}.mod'


def config_text(rows):
    """``rows`` = [(clip, duration, frames)] in CLIPS order."""
    lines = [HEADER, SPECIES]
    for clip, duration, frames in rows:
        if not frames or frames[0] != 0 or frames[-1] != duration - 1 \
                or any(b <= a for a, b in zip(frames, frames[1:])):
            raise ValueError(f'Invalid frame list for {clip}')
        lines.append(' '.join([clip, str(len(frames)), str(duration)] + [str(f) for f in frames]))
    return '\n'.join(lines) + '\n'


def bake(model, motions, out, pose_limit=DEFAULT_POSE_LIMIT):
    """Bake every clip of ``motions`` ({clip: bca bytes}) into ``out``."""
    out = Path(out)
    if not 2 <= pose_limit <= 64:
        raise ValueError('Pose limit must be 2..64')
    model_blocks = blocks(model)
    names = joints(model)
    if struct.unpack_from('>H', model_blocks['EVP1'], 8)[0] == 0:
        raise ValueError('Expected a weighted (EVP1) BigFoot model')
    out.mkdir(parents=True, exist_ok=True)
    rows, clips, reference = [], {}, None
    total_bytes = 0
    for clip in CLIPS:
        raw = motions[clip + '.bca']
        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        frames = sample_frames(duration, pose_limit)
        entries = []
        for number, frame in enumerate(frames):
            _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
            decoded = decode(model, True, bake_rigid=True,
                             draw_matrices=draw_matrices(model_blocks, pose))
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / 'pose.mod'
                write_model(decoded, target, 'enemy.bmd')
                data = target.read_bytes()
            if len(data) > MAX_POSE_BYTES:
                raise ValueError(f'{clip} pose {number} exceeds the native pose file budget')
            resources = resource_chunks(data)
            if reference is not None and resources != reference:
                raise ValueError('Pose changes immutable render resources')
            reference = resources
            (out / pose_name(clip, number)).write_bytes(data)
            entries.append(dict(file=pose_name(clip, number), frame=frame, bytes=len(data), sha256=sha(data)))
            total_bytes += len(data)
        rows.append((clip, duration, frames))
        clips[clip] = dict(source_frames=duration, source_sha256=sha(raw), loop_attribute=raw[40],
                           poses=entries)
    text = config_text(rows)
    (out / CONFIG).write_text(text, encoding='ascii')
    report = dict(schema=1, species=SPECIES, pose_limit=pose_limit, joints=len(names),
                  total_pose_bytes=total_bytes, total_poses=sum(len(c['poses']) for c in clips.values()),
                  config_sha256=sha(text.encode('ascii')), clips=clips)
    (out / REPORT).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def skin_text(model):
    """``P2_BIGFOOT_SKIN_1``: the skinning of the baked vertex order (#1018).

    Rows: joint count; the authored EVP1 inverse matrix of every joint; the DRW1
    table (``d i r joint`` rigid, ``d i e n joint weight ...`` envelope); then
    every baked position and normal in ``.mod`` order as its DRW1 index and raw
    value. Native evaluates draw matrix D (rigid: animated joint; envelope:
    sum weight * animated joint * inverse), position D*p and normal
    cofactor(D)*n normalised, the same maths the bake uses, so any joint pose
    (clip body + IK legs) reproduces the baked mesh for that pose.
    """
    model_blocks = blocks(model)
    names = joints(model)
    envelopes, inverse = _envelopes(model_blocks['EVP1'], len(names))
    drw = model_blocks['DRW1']
    count = struct.unpack_from('>H', drw, 8)[0]
    flags_at, refs_at = struct.unpack_from('>II', drw, 12)
    bindings = {}
    decode(model, True, bake_rigid=True, draw_matrices=draw_matrices(model_blocks), bindings=bindings)

    def f(v):
        return format(float(v), '.9g')

    rows = [SKIN_HEADER, f'joints {len(names)}']
    for index, matrix in enumerate(inverse):
        rows.append(f'i {index} ' + ' '.join(f(v) for row in matrix for v in row))
    rows.append(f'draws {count}')
    for index in range(count):
        kind = drw[flags_at + index]
        ref = struct.unpack_from('>H', drw, refs_at + 2 * index)[0]
        if kind == 0:
            if ref >= len(names):
                raise ValueError('DRW1 joint out of range')
            rows.append(f'd {index} r {ref}')
        elif kind == 1:
            influences = envelopes[ref]
            rows.append(f'd {index} e {len(influences)} '
                        + ' '.join(f'{joint} {f(weight)}' for joint, weight in influences))
        else:
            raise ValueError('Unsupported DRW1 kind')
    for label, attr in (('positions', 9), ('normals', 10)):
        entries = bindings[attr]
        rows.append(f'{label} {len(entries)}')
        for draw, value in entries:
            if not 0 <= draw < count:
                raise ValueError('Skin draw index out of range')
            rows.append(f'{draw} ' + ' '.join(f(v) for v in value))
    rows.append('end')
    return ('\n'.join(rows) + '\n').encode('ascii')


def extract(iso, out, pose_limit=DEFAULT_POSE_LIMIT):
    iso = Path(iso)
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
    missing = [c for c in CLIPS if c + '.bca' not in motions]
    if missing:
        raise ValueError(f'BigFoot anim archive lacks {missing}')
    report = bake(model, motions, out, pose_limit)
    skin = skin_text(model)
    (Path(out) / SKIN).write_bytes(skin)
    report.update(skin=SKIN, skin_bytes=len(skin), skin_sha256=sha(skin))
    (Path(out) / REPORT).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=DEFAULT_POSE_LIMIT)
    args = parser.parse_args()
    result = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps({k: v for k, v in result.items() if k != 'clips'}, sort_keys=True))
