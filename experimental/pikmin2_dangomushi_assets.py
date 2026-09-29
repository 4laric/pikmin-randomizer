"""DangoMushi (Segmented Crawbster, enemy ID 94) source pose assets.

Single-species ISO extractor modeled on :mod:`experimental.pikmin2_sokkuri_assets`
for the DangoMushi slice of :mod:`experimental.pikmin2_snagret_assets` (which
extracts the whole Snagret/Crawbster family at once). Reads the retail
DangoMushi model/anim/parameter banks off the US GPVE01 rev 0 disc, validates
them against the audited snagret source contract (DangoMushi clip registry,
key events, parameter blocks, including the brace-less ``attack_2.bca``
registration block the shared sheargrub parser rejects), and samples bounded
rigid poses through the explicit draw-matrix path.

Output (``<output>/``):

* ``dangomushi.json``: schema-1 manifest (species ``DangoMushi``, enemy_id 94)
  with per-clip ``file``/``events``/``source_frames``/``sha256``/``status``,
  ``poses`` (``file``/``frame``/``bytes``/``sha256``) holding converted poses
  only under contiguous ``_00..`` slot names, and ``unsupported_frames``
  listing sampled source frames the converter rejected.
* ``snake_DangoMushi_<clip>_%02d.mod``: sampled pose meshes, named exactly as
  the batch-3 snagret loader opens them
  (``engine/pc_port/pc_p2_batch3.cpp`` ``loadPose`` with the ``snake`` family
  prefix, ``{"snagret", "snake", ...}``), plus a per-pose ``.json``
  conversion record.
* ``enemy.bmd``, ``dangomushi.brk`` (the material animation
  ``DangoMushiMgr`` loads; recorded, never played back) and the four
  ``dangomushi/enemy*.txt`` metadata files, preserved verbatim for audit.

Deterministic: hashed disc reads, fixed clip order, no timestamps. Nothing is
fabricated: a clip that fails to convert is recorded ``unsupported`` with its
reason, never replaced with a placeholder pose.
"""
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_animation import resource_chunks, sample_frames
from experimental.pikmin2_breadbug_assets import parameter_blocks, collision_nodes
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import joints
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_snagret_assets import (
    EXPECTED_EVENTS,
    LOOPS,
    MAX_POSES,
    animation_rows,
    profile,
)

SPECIES = 'DangoMushi'
ENEMY_ID = 94
MANIFEST = 'dangomushi.json'
MODEL_PATH = 'enemy/data/DangoMushi/model.szs'
ANIM_PATH = 'enemy/data/DangoMushi/anim.szs'
BRK_PATH = 'enemy/data/DangoMushi/dangomushi.brk'
PARM_PATH = 'enemy/parm/enemyParms.szs'
PARM_PREFIX = 'dangomushi/'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt',
                  'enemystoneinfo.txt')

LIMITATIONS = [
    'Sampled rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events and parameter text are preserved as data only; no roll, flick, swallow, birth or death behavior executes.',
    'The dangomushi.brk material animation is recorded, never played back.',
    'No native runtime, AI/FSM, install or arena placement is provided by this module; see experimental.pikmin2_dangomushi_content for staging.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pose_name(clip, number):
    """Native bank filename for one sampled pose (batch-3 ``loadPose`` grammar)."""
    return f'snake_{SPECIES}_{clip}_{number:02}.mod'


# Adaptive sampling (#897). The native batch-3 draw blends linearly between
# the two staged poses around the clip frame. Uniform 3..8 samples cannot
# carry the Crawbster's fast curl, ball roll, belly-up flip and claw sweep
# (a 3-pose attack clip blends the uncurled body into the ball), so poses are
# chosen where linear blending deviates most from the real skinned pose
# (Ramer-Douglas-Peucker over whole-mesh vertex error), seeded with the clip
# ends and every key-event frame (loop seams, roll start, windows).
ADAPTIVE_MAX_POSES = 40
ADAPTIVE_FLOOR = 3.0          # stop once every in-between frame is within 3 units
# Native resident budget per clip (#895 pose-fidelity loader,
# pc_p2_pose_loader.h p2poseload::ClipBytes, owner-approved 1 MiB): the first
# RESIDENT_SLOT_SHAPES spread poses cost their whole file as Shapes, every
# other pose its decoded position+normal vectors (12 bytes each). An adaptive
# clip that would exceed it is re-sampled with a lower cap, never shipped over.
RESIDENT_CLIP_BYTES = 1024 * 1024
RESIDENT_SLOT_SHAPES = 4
CARCASS_PATH = 'user/Abe/Pellet/us/carcass_config.txt'
# The 'body' material's TEV stage 0 is RASC + lerp(C0, C1, env-mapped
# IP2_glow1_i); dangomushi.brk animates C0. The approximate converter would
# otherwise draw the raw greyscale glow texture (the grey hemisphere of the
# #897 review). It is drawn untextured in its own MAT3 C0 register colour.
TEV_COLOR_MATERIALS = ('body',)


def _blend_error(positions, i, j, k):
    w = (k - i) / (j - i)
    worst = 0.0
    for a, b, c in zip(positions[i], positions[j], positions[k]):
        d = sum(((1.0 - w) * a[q] + w * b[q] - c[q]) ** 2 for q in range(3))
        if d > worst:
            worst = d
    return worst ** 0.5


def adaptive_frames(positions, cap, anchors=(), floor=ADAPTIVE_FLOOR):
    """Deterministic RDP key-pose choice over per-frame vertex positions."""
    duration = len(positions)
    if duration < 1:
        raise ValueError('empty clip')
    if duration == 1:
        return [0]
    keys = sorted({0, duration - 1, *(f for f in anchors if 0 <= f < duration)})
    if len(keys) > cap:
        raise ValueError('more anchors than the pose cap')
    while len(keys) < cap:
        best = (0.0, None, None)
        for x in range(len(keys) - 1):
            i, j = keys[x], keys[x + 1]
            for k in range(i + 1, j):
                e = _blend_error(positions, i, j, k)
                if e > best[0]:
                    best = (e, k, x)
        if best[1] is None or best[0] <= floor:
            break
        keys.insert(best[2] + 1, best[1])
    return keys


def _material_shapes(model_blocks):
    """Shape index -> MAT3 material index from the INF1 draw hierarchy."""
    hierarchy = model_blocks['INF1']
    at = struct.unpack_from('>I', hierarchy, 20)[0]
    material, mapping = 0, {}
    while True:
        kind, index = struct.unpack_from('>HH', hierarchy, at)
        at += 4
        if kind == 0:
            return mapping
        if kind == 0x11:
            material = index
        elif kind == 0x12:
            mapping[index] = material


def tev_color_overrides(model_blocks, shape_count):
    """``(textures, colors)`` overrides for TEV_COLOR_MATERIALS shapes."""
    mat3 = model_blocks['MAT3']
    u32 = lambda at: struct.unpack_from('>I', mat3, at)[0]
    u16 = lambda at: struct.unpack_from('>H', mat3, at)[0]
    names_at = u32(0x14)
    names = []
    for i in range(u16(names_at)):
        off = u16(names_at + 4 + 4 * i + 2)
        end = mat3.index(b'\0', names_at + off)
        names.append(mat3[names_at + off:end].decode('ascii'))
    mapping = _material_shapes(model_blocks)
    textures, colors = {}, {}
    for shape in range(shape_count):
        material = mapping[shape]
        if names[material] not in TEV_COLOR_MATERIALS:
            continue
        entry = u32(0x0C) + u16(u32(0x10) + 2 * material) * 332
        reg = u16(entry + 0xDC)            # tevColor[0] = GX_TEVREG0 (C0)
        if reg == 0xFFFF:
            raise ValueError(f'material {names[material]} has no C0 register')
        rgba = struct.unpack_from('>4h', mat3, u32(0x50) + reg * 8)
        colors[shape] = tuple(max(0, min(255, v)) for v in rgba[:3]) + (255,)
        textures[shape] = -1
    return textures, colors


def _slot_indices(count, shapes=RESIDENT_SLOT_SHAPES):
    """p2motion::shapeSlots: `shapes` evenly spread Shape slots."""
    if count <= shapes:
        return set(range(count))
    out = []
    for i in range(shapes):
        slot = int(math.floor(i * (count - 1) / (shapes - 1) + 0.5))
        if not out or slot != out[-1]:
            out.append(slot)
    return set(out)


def pose_vector_count(data):
    """Position + normal vector count of one pose .mod (chunk tags 16/17)."""
    at, vectors = 0, 0
    while at + 12 <= len(data):
        tag, size, count = struct.unpack_from('>III', data, at)
        if tag in (16, 17):
            vectors += count
        if tag == 65535:
            break
        at += 8 + size
    return vectors


def resident_clip_bytes(pose_datas):
    """Mirror of the native p2poseload::estimateStem resident estimate."""
    slots = _slot_indices(len(pose_datas))
    return sum(len(data) if i in slots else 12 * pose_vector_count(data)
               for i, data in enumerate(pose_datas))


def carcass_row(config_text):
    """The retail carcass_config.txt DangoMushi row (min/max/pikicount/money)."""
    text = config_text.decode('shift_jis') if isinstance(config_text, bytes) else config_text
    match = re.search(r'^\s*name\s+DangoMushi\s*$', text, re.M)
    if match is None:
        raise ValueError('carcass_config.txt has no DangoMushi row')
    at = match.start()
    block = text[at:re.search(r'^\s*end\s*$', text[at:], re.M).start() + at]
    row = {}
    for line in block.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in ('min', 'max', 'pikicountmax', 'pikicountmin', 'money'):
            row[parts[0]] = int(parts[1])
    if row.get('pikicountmax') != row.get('pikicountmin') or not {'min', 'max', 'money'} <= set(row):
        raise ValueError('carcass_config.txt DangoMushi row incomplete')
    return dict(min=row['min'], max=row['max'], pikicount=row['pikicountmax'],
                money=row['money'], source=CARCASS_PATH)


def extract(iso, output, pose_limit=6, sampling='uniform'):
    """Extract the DangoMushi bank.

    ``sampling='uniform'`` keeps the historical ``sample_frames`` spacing with
    ``pose_limit`` <= MAX_POSES. ``sampling='adaptive'`` (#897, what
    ``scripts/p2_prepare_content.py`` stages) picks up to ``pose_limit`` <=
    ADAPTIVE_MAX_POSES key poses per clip by blend error (``adaptive_frames``),
    draws the TEV-register 'body' material in its C0 colour and records the
    retail carcass_config.txt row.
    """
    if sampling not in ('uniform', 'adaptive'):
        raise ValueError(f'Unknown sampling: {sampling!r}')
    limit = ADAPTIVE_MAX_POSES if sampling == 'adaptive' else MAX_POSES
    if type(pose_limit) is not int or not 2 <= pose_limit <= limit:
        raise ValueError(f'Pose limit must be 2..{limit}')
    adaptive = sampling == 'adaptive'
    iso, output = Path(iso), Path(output)
    if not iso.is_file():
        raise ValueError(f'ISO not found: {iso}')
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    output.mkdir(parents=True, exist_ok=False)
    index = disc_files(iso)
    hashes = {}

    def read(disc, path):
        try:
            at, size = index[path]
        except KeyError:
            raise ValueError(f'Disc entry missing: {path}') from None
        disc.seek(at)
        raw = disc.read(size)
        if len(raw) != size:
            raise ValueError(f'Truncated disc entry: {path}')
        hashes[path] = sha(raw)
        return raw

    with iso.open('rb') as disc:
        header = disc.read(8)
        if header[:6] != b'GPVE01':
            raise ValueError('Expected supplied US GPVE01 disc')
        try:
            model = archive_files(read(disc, MODEL_PATH))['enemy.bmd']
        except KeyError:
            raise ValueError('DangoMushi model missing enemy.bmd') from None
        motions = archive_files(read(disc, ANIM_PATH))
        brk = read(disc, BRK_PATH)
        params = archive_files(read(disc, PARM_PATH))
        carcass = carcass_row(read(disc, CARCASS_PATH)) if adaptive else None
    names = joints(model)
    if not names:
        raise ValueError('DangoMushi model carries no joints')
    model_blocks = blocks(model)
    try:
        envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
        draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
    except (KeyError, struct.error) as error:
        raise ValueError(f'Invalid DangoMushi model skinning blocks: {error}') from None

    metadata = {}
    for filename in METADATA_FILES:
        try:
            raw = params[PARM_PREFIX + filename]
        except KeyError:
            raise ValueError(
                f'DangoMushi parameter entry missing: {PARM_PREFIX + filename}') from None
        metadata[filename] = sha(raw)
        (output / filename).write_bytes(raw)
    (output / 'enemy.bmd').write_bytes(model)
    (output / 'dangomushi.brk').write_bytes(brk)

    blocks_list = parameter_blocks(params[PARM_PREFIX + 'enemyparm.txt'])
    # The snagret registry parser tolerates the missing `{` before attack_2.bca.
    rows = animation_rows(params[PARM_PREFIX + 'enemyanimmgr.txt'].decode('shift_jis'))
    # Validates the general/proper parameter blocks, the disc values, the clip
    # registry order and every clip's key events; raises ValueError on mismatch.
    info = profile(SPECIES, blocks_list, rows)
    collision = collision_nodes(params[PARM_PREFIX + 'enemycoll.txt'], len(names))

    clips = []
    reference = None
    total_pose_bytes = 0
    for row in rows:
        stem = Path(row['file']).stem
        try:
            raw = motions[row['file']]
        except KeyError:
            raise ValueError(f'DangoMushi motion missing: {row["file"]}') from None
        (output / row['file']).write_bytes(raw)
        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        if raw[40] not in LOOPS:
            raise ValueError(f'Unsupported DangoMushi loop attribute: {row["file"]}')
        clip = dict(file=row['file'], events=[list(event) for event in row['events']],
                    source_frames=duration, sha256=sha(raw),
                    loop_attribute=raw[40], loop_semantics=LOOPS[raw[40]],
                    poses=[], unsupported_frames=[], status='unsupported')
        if row['events'] != EXPECTED_EVENTS[SPECIES][stem]:
            raise ValueError(f'DangoMushi clip {stem} key events mismatch')
        # Bank slots are assigned to converted poses only, contiguously from
        # zero: the native loader opens indices 0..N-1 and aborts on a gap, so
        # an unconvertible sampled frame is recorded under unsupported_frames
        # (never replaced with a placeholder) and never occupies a slot.
        baked = None
        if adaptive:
            baked = []
            for frame in range(duration):
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                baked.append(decode(model, True, bake_rigid=True,
                                    draw_matrices=draw_matrices(model_blocks, pose))[1][9])
        cap = pose_limit
        while True:
            if adaptive:
                frames = adaptive_frames(baked, cap,
                                         anchors=[event[0] for event in row['events']])
                clip['sampling'] = dict(policy='adaptive_rdp', cap=cap,
                                        floor=ADAPTIVE_FLOOR,
                                        resident_budget=RESIDENT_CLIP_BYTES,
                                        anchors=sorted({event[0] for event in row['events']
                                                        if 0 <= event[0] < duration}))
            else:
                frames = sample_frames(duration, pose_limit)
            clip['poses'], clip['unsupported_frames'] = [], []
            pose_datas = []
            for frame in frames:
                try:
                    _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                    matrices = draw_matrices(model_blocks, pose)
                    decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                    name = pose_name(stem, len(clip['poses']))
                    colors = None
                    if adaptive:
                        textures, tints = tev_color_overrides(model_blocks, len(decoded[3]))
                        mats = list(decoded[3])
                        for shape, texture in textures.items():
                            mats[shape] = texture
                        decoded = (decoded[0], decoded[1], decoded[2], mats)
                        colors = [tints.get(i, (255, 255, 255, 255)) for i in range(len(mats))]
                    conversion = write_model(decoded, output / name, 'enemy.bmd',
                                             material_colors=colors)
                    if colors is not None:
                        conversion['tev_color_shapes'] = {
                            str(shape): list(tints[shape]) for shape in sorted(tints)}
                    conversion.update(source='enemy.bmd', output=name,
                                      weighted_pose_baked=envelopes > 0,
                                      source_frame=frame)
                    data = (output / name).read_bytes()
                    resources = resource_chunks(data)
                    if reference is not None and resources != reference:
                        raise ValueError('DangoMushi pose changes immutable render resources')
                    reference = resources
                    pose_datas.append(data)
                    clip['poses'].append(dict(file=name, frame=frame, bytes=len(data),
                                              sha256=sha(data)))
                    (output / Path(name).with_suffix('.json')).write_text(
                        json.dumps(conversion, sort_keys=True, indent=2) + '\n',
                        encoding='utf-8')
                except (ValueError, KeyError, ArithmeticError) as error:
                    clip['unsupported_frames'].append(frame)
            resident = resident_clip_bytes(pose_datas)
            if not adaptive or resident <= RESIDENT_CLIP_BYTES:
                break
            # Over the native resident budget: drop this sampling and retry
            # with one fewer key pose (deterministic, same RDP order).
            for pose in clip['poses']:
                (output / pose['file']).unlink()
                (output / Path(pose['file']).with_suffix('.json')).unlink()
            if cap <= 2:
                raise ValueError(f'DangoMushi clip {stem} exceeds the resident clip budget')
            cap = min(cap, len(frames)) - 1
        if adaptive:
            clip['resident_bytes'] = resident
        total_pose_bytes += sum(len(data) for data in pose_datas)
        if clip['poses']:
            clip['status'] = 'converted'
        else:
            clip['unsupported_reason'] = 'no sampled frames'
        clips.append(clip)

    result = dict(
        schema=1, species=SPECIES, enemy_id=ENEMY_ID,
        disc_id=header[:6].decode(), disc_revision=header[7],
        source_sha256=hashes, model_sha256=sha(model), joints=names,
        parameters=blocks_list, state_ids=info['state_ids'],
        anim_id_by_clip=info['anim_id_by_clip'],
        proper_retail=info['proper_retail'],
        proper_keys_defaulted_from_header=info['proper_keys_defaulted_from_header'],
        metadata_sha256=metadata, brk_sha256=sha(brk),
        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                      weighted_baking=envelopes > 0,
                      self_contained_resources=draws > 0),
        collision=collision,
        clips=clips, total_pose_bytes=total_pose_bytes,
        limitations=list(LIMITATIONS))
    if carcass is not None:
        result['carcass'] = carcass
        result['sampling'] = 'adaptive'
    (output / MANIFEST).write_text(
        json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=6)
    parser.add_argument('--sampling', choices=('uniform', 'adaptive'), default='uniform')
    args = parser.parse_args()
    summary = extract(args.iso, args.output, args.pose_limit, args.sampling)
    print(json.dumps({
        'clips': len(summary['clips']),
        'converted': sum(c['status'] == 'converted' for c in summary['clips']),
        'poses': sum(1 for c in summary['clips'] for p in c['poses'] if 'file' in p),
        'pose_bytes': summary['total_pose_bytes'],
    }, indent=2))
