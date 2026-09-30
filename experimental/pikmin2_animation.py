"""Bounded sampled Snow animation protocol; no gameplay animation events."""
import struct

CLIPS = ('wait1', 'move1', 'attack', 'dead', 'flick')
MAX_POSES = 24  # P2_SNOW_2 bank format cap (native p2animation::parse)
# Pose-density policy (#895). POSE_LIMIT_MAX is the native bank row cap
# (pc_p2_batch2 parseBank / p2sampled::Clip::valid). DEFAULT_POSE_LIMIT is the
# campaign default for every family: all native pose-bank loaders (batch2,
# batch3, Chappy, Frog, Tank, Kabuto, Sheargrub, Dwarf Orange, Mamuta) now go
# through pc_p2_pose_loader.h (a few full Shapes per clip plus decoded
# vectors), so there is no longer a sparser legacy tier. LEGACY_POSE_LIMIT is
# kept as an alias for callers that still pass it.
POSE_LIMIT_MAX = 64
DEFAULT_POSE_LIMIT = 24
LEGACY_POSE_LIMIT = DEFAULT_POSE_LIMIT
CLIP_BYTES = 512 * 1024
TOTAL_BYTES = 2 * 1024 * 1024
# Resident pose-bank accounting, mirroring native pc_p2_pose_loader.h (#895).
# Each clip keeps FALLBACK_SHAPES evenly spread poses as full Shapes (their
# file size) and every other pose as decoded positions+normals (12 bytes per
# vector). Budgets: 1 MiB per clip (owner-approved, was 512 KiB) and 48 MiB
# per setup (RESIDENT_CLIP_BYTES / RESIDENT_TOTAL_BYTES); the proxy guard keeps
# its 8 MiB per species on the same resident measure.
FALLBACK_SHAPES = 4
RESIDENT_CLIP_BYTES = 1024 * 1024
RESIDENT_TOTAL_BYTES = 48 * 1024 * 1024


def sample_frames(duration, limit=MAX_POSES):
    if type(duration) is not int or not 1 <= duration <= 10000 or not 2 <= limit <= POSE_LIMIT_MAX:
        raise ValueError('Invalid Snow sample limit/duration')
    count = min(limit, duration)
    return [round(i * (duration - 1) / max(1, count - 1)) for i in range(count)]



def shape_slots(count, max_shapes=FALLBACK_SHAPES):
    """Pose indices native keeps as full Shapes (p2motion::shapeSlots)."""
    if count <= 0:
        return []
    max_shapes = max(1, max_shapes)
    if count <= max_shapes:
        return list(range(count))
    if max_shapes == 1:
        return [0]
    out = []
    for i in range(max_shapes):
        slot = int(i * (count - 1) / (max_shapes - 1) + 0.5)
        if not out or slot != out[-1]:
            out.append(slot)
    return out


def mod_vector_count(data):
    """Positions + normals in one pose MOD (tags 16/17), as native estimates."""
    at, vectors = 0, 0
    while at + 12 <= len(data):
        tag, size, count = struct.unpack_from('>III', data, at)
        if tag in (16, 17):
            vectors += count
        if tag == 0xFFFF:
            break
        at += 8 + size
    return vectors


def resident_clip_bytes(poses, max_shapes=FALLBACK_SHAPES):
    """Native resident bytes of one clip from its pose MOD bytes, in order."""
    slots = set(shape_slots(len(poses), max_shapes))
    return sum(len(data) if index in slots else 12 * mod_vector_count(data)
               for index, data in enumerate(poses))


def _collapsed(error):
    text = str(error)
    return ('Singular normal transform' in text or 'annihilates normal' in text
            or 'Singular animation scale' in text)


def decode_pose(decode, model, model_blocks, raw, frame, joint_count, pose_kwargs=None, **decode_kwargs):
    """Decode one sampled BCA frame into a baked pose; returns (decoded, pose).

    ``decode`` is the caller's ``pikmin2_convert.decode`` (kept injectable).
    A frame whose draw matrix is singular -- an authored zero joint scale, as
    in P2 hide/burrow/death shrink clips (Sokkuri pdead1/hide1, Snake dead,
    UmiMushi sturn) -- used to be dropped as an unsupported frame, leaving
    those clips with 4-11 poses. It is retried once with the collapsed scale
    clamped to ``COLLAPSED_SCALE_FLOOR`` and the transpose-adjugate normal
    policy: the collapsed joint's geometry stays a (sub-visible) point and its
    normals keep the rotation's direction. Frames that decode normally are
    byte-identical to before; the retry is recorded in the pose report under
    ``normal_policy.collapsed_joint``.
    """
    from experimental.pikmin2_purple import COLLAPSED_SCALE_FLOOR, bca_pose
    from experimental.pikmin2_skinning import draw_matrices
    try:
        _, pose = bca_pose(raw, frame, joint_count, allow_scale=True, **(pose_kwargs or {}))
        return decode(model, True, bake_rigid=True,
                      draw_matrices=draw_matrices(model_blocks, pose), **decode_kwargs), pose
    except ValueError as error:
        if not _collapsed(error):
            raise
    _, pose = bca_pose(raw, frame, joint_count, allow_scale=True,
                       **{**(pose_kwargs or {}), 'singular_scale': 'clamp'})
    retry = dict(decode_kwargs)
    if retry.get('singular_normal', 'error') == 'error':
        retry['singular_normal'] = 'transpose-adjugate'
    decoded = decode(model, True, bake_rigid=True,
                     draw_matrices=draw_matrices(model_blocks, pose), **retry)
    if isinstance(decoded, tuple) and decoded and isinstance(decoded[0], dict):
        policy = dict(decoded[0].get('_normal_policy') or {})
        policy['collapsed_joint'] = {'scale_floor': COLLAPSED_SCALE_FLOOR,
                                     'singular_normal': retry['singular_normal'],
                                     'reason': 'authored zero joint scale (retry)'}
        decoded[0]['_normal_policy'] = policy
    return decoded, pose


def frames_trailer(poses, source_frames):
    """Optional P2_BANK_FRAMES_1 ` frames f0,f1,...` trailer for one bank row.

    Emitted only when every pose records its integer source ``frame`` and the
    list is strictly increasing from 0 to ``source_frames - 1`` with at most
    POSE_LIMIT_MAX entries (the native validator's contract); otherwise the
    empty string, and native falls back to uniform frames.
    """
    frames = [pose.get('frame') if isinstance(pose, dict) else None for pose in poses]
    if (not 2 <= len(frames) <= POSE_LIMIT_MAX or type(source_frames) is not int
            or any(type(f) is not int for f in frames) or frames[0] != 0
            or frames[-1] != source_frames - 1 or any(a >= b for a, b in zip(frames, frames[1:]))):
        return ''
    return ' frames ' + ','.join(str(f) for f in frames)


def parse_bank(text):
    tokens = iter(text.split())
    try:
        header = next(tokens)
        if header not in ('P2_SNOW_1', 'P2_SNOW_2'):
            raise ValueError('Invalid Snow bank version')
        result = {}
        for name in CLIPS:
            if next(tokens) != name:
                raise ValueError('Invalid Snow clip order')
            count, duration = int(next(tokens)), int(next(tokens))
            if not 1 <= count <= (12 if header.endswith('1') else POSE_LIMIT_MAX) or not 1 <= duration <= 10000:
                raise ValueError('Invalid Snow clip bounds')
            frames = ([int(next(tokens)) for _ in range(count)] if header.endswith('2') else None)
            if frames is not None and (frames[0] != 0 or frames[-1] != duration-1 or
                                       any(a >= b for a, b in zip(frames, frames[1:]))):
                raise ValueError('Invalid Snow source frames')
            result[name] = {'poses': count, 'source_frames': duration, 'frames': frames}
        if next(tokens, None) is not None:
            raise ValueError('Trailing Snow bank data')
        return result
    except (StopIteration, TypeError) as exc:
        raise ValueError('Truncated Snow bank') from exc


def resource_chunks(data):
    """Static render resources must match before native material aliasing."""
    at = 0
    tag = None
    found = {}
    while at + 8 <= len(data):
        tag, size = struct.unpack_from('>II', data, at)
        end = at + 8 + size
        if end > len(data):
            raise ValueError('Truncated Snow MOD chunk')
        if tag in (32, 34, 48):
            if tag in found:
                raise ValueError('Duplicate Snow render resource')
            found[tag] = data[at:end]
        at = end
        if tag == 65535:
            break
    if at != len(data) or tag != 65535 or set(found) != {32, 34, 48}:
        raise ValueError('Incomplete Snow MOD resources')
    return b''.join(found[tag] for tag in (32, 34, 48))


def validate_files(directory, bank):
    paths, total, reference = [], 0, None
    for name, info in bank.items():
        clip_bytes = 0
        for index in range(info['poses']):
            path = directory / f'snow_{name}_{index:02}.mod'
            size = path.stat().st_size
            clip_bytes += size
            total += size
            if not size or clip_bytes > CLIP_BYTES or total > TOTAL_BYTES:
                raise ValueError('Snow pose bank exceeds byte budget')
            resources = resource_chunks(path.read_bytes())
            if reference is not None and resources != reference:
                raise ValueError('Snow pose render resources differ')
            reference = resources
            paths.append(path)
    return paths, total
