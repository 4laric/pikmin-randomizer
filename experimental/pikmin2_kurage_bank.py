"""Jellyfloat (Kurage 57 / OniKurage 72) sampled pose bank (#972).

The native Jellyfloat loader used one static mesh per source clip, so the
bell barely animated.  This module bakes up to ``pose_limit`` evenly spaced
rigid poses per source clip (``<clip>_<NN>.mod``, the same naming the other
pose-bank families use) and records, for each pose, the world translation of
the ``Proom`` joint (the source ``suck`` collision part the native host holds
captured Pikmin and the captain at).  The staged ``p2-<species>-animation.txt``
carries the per-clip frame list and those Proom rows, so the host can follow
the pose it draws instead of one tabulated frame.

The pre-existing static ``<clip>_<frame:04>.mod`` visuals stay untouched: they
are the no-bank fallback, so a content cache extracted before this change
still loads.
"""
import json
from pathlib import Path

from experimental.pikmin2_animation import (DEFAULT_POSE_LIMIT, POSE_LIMIT_MAX,
                                            decode_pose, sample_frames)
from experimental.pikmin2_breadbug_assets import sha
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices

POLICY = 'P2_KURAGE_BANK_1'
PROFILE_MAGIC = 'P2_KURAGE_ANIMATION_1'
PROOM_JOINT = 'Proom'


def bake_bank(model, names, motions, rows, output, pose_limit=DEFAULT_POSE_LIMIT):
    """Bake the per-clip pose bank into ``output``; return the manifest ``bank``.

    ``rows`` are the registry rows (``file`` = ``<clip>.bca``); clips that do
    not decode are recorded with ``status='unsupported'`` and no poses.
    """
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f'Pose limit must be 2..{POSE_LIMIT_MAX}')
    if PROOM_JOINT not in names:
        raise ValueError('Jellyfloat model has no Proom joint')
    proom = names.index(PROOM_JOINT)
    parsed = blocks(model)
    clips = []
    total = 0
    for row in rows:
        stem = Path(row['file']).stem
        raw = motions[row['file']]
        clip = dict(name=stem, status='unsupported', source_frames=None, poses=[])
        try:
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
            clip['source_frames'] = duration
            poses = []
            for index, frame in enumerate(sample_frames(duration, pose_limit)):
                decoded, pose = decode_pose(decode, model, parsed, raw, frame, len(names))
                path = output / f'{stem}_{index:02}.mod'
                conversion = write_model(decoded, path, 'enemy.bmd')
                conversion.update(source='enemy.bmd', output=path.name)
                path.with_suffix('.json').write_text(json.dumps(conversion, indent=2) + '\n',
                                                     encoding='utf-8')
                matrix = joint_matrices(parsed, pose)[proom]
                data = path.read_bytes()
                total += len(data)
                poses.append(dict(frame=frame, file=path.name, bytes=len(data), sha256=sha(data),
                                  proom=[round(float(matrix[r][3]), 3) for r in range(3)]))
            clip['poses'] = poses
            clip['status'] = 'converted'
        except ValueError as error:
            clip['reason'] = str(error)
        clips.append(clip)
    return dict(policy=POLICY, pose_limit=pose_limit, total_bytes=total, clips=clips)


def profile_text(bank):
    """Native ``p2-<species>-animation.txt`` for a manifest ``bank``.

    ``P2_KURAGE_ANIMATION_1`` then, per converted clip::

        <clip> <count> <duration> <frame>*count <x y z>*count

    Frames are strictly increasing from 0 to ``duration-1``; each x y z is the
    Proom joint world translation of that pose (model units, yaw 0, scale 1).
    """
    lines = [PROFILE_MAGIC]
    for clip in bank['clips']:
        poses = clip['poses']
        if clip.get('status') != 'converted' or not poses:
            continue
        duration = clip['source_frames']
        frames = [pose['frame'] for pose in poses]
        if (type(duration) is not int or frames[0] != 0 or frames[-1] != duration - 1
                or any(a >= b for a, b in zip(frames, frames[1:]))):
            raise ValueError(f'Invalid pose frame list for clip {clip["name"]}')
        proom = ' '.join(f'{v:.3f}' for pose in poses for v in pose['proom'])
        lines.append(f'{clip["name"]} {len(poses)} {duration} '
                     + ' '.join(str(f) for f in frames) + ' ' + proom)
    return '\n'.join(lines) + '\n'


def staged_bank(source, document, prefix, profile_name):
    """Validated ``{run-relative destination: bytes}`` for a manifest's ``bank``.

    Returns ``{}`` when the manifest carries no bank (an extraction made before
    #972): staging then writes only the static visuals and native keeps them.
    Pose meshes land in the private room as ``<prefix><clip>_<NN>.mod``; the
    profile lands at the run root as ``profile_name``.  Hash, frame and name
    mismatches raise ``StagingError`` before anything is written.
    """
    import re
    from experimental.pikmin2_staging import StagingError
    bank = document.get('bank')
    if bank is None:
        return {}
    if not isinstance(bank, dict) or bank.get('policy') != POLICY:
        raise StagingError('Jellyfloat pose bank policy mismatch')
    room = Path('assets/dataDir/courses/pikmin2room')
    clip_re = re.compile(r'[a-z0-9]+')
    files, used = {}, 0
    for clip in bank.get('clips', ()):
        if not isinstance(clip, dict) or clip.get('status') != 'converted':
            continue
        name = clip.get('name')
        if not isinstance(name, str) or not clip_re.fullmatch(name):
            raise StagingError(f'Jellyfloat bank clip name rejected: {name!r}')
        for index, pose in enumerate(clip.get('poses', ())):
            expected = f'{name}_{index:02}.mod'
            if pose.get('file') != expected:
                raise StagingError(f'Jellyfloat bank pose name mismatch: {pose.get("file")!r}')
            path = Path(source) / expected
            if not path.is_file():
                raise StagingError(f'Jellyfloat bank pose missing: {path}')
            data = path.read_bytes()
            if not data or sha(data) != pose.get('sha256'):
                raise StagingError(f'Jellyfloat bank pose hash mismatch: {path}')
            files[str(room / f'{prefix}{expected}')] = data
            used += 1
    if not used:
        raise StagingError('Jellyfloat pose bank has no converted clips')
    try:
        text = profile_text(bank)
    except ValueError as error:
        raise StagingError(str(error)) from error
    files[profile_name] = text.encode('ascii')
    return files
