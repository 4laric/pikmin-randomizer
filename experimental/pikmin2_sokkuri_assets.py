"""Sokkuri (Skitter Leaf, enemy ID 79) source pose assets; no native behavior substitution.

Single-species ISO extractor modeled on
:mod:`experimental.pikmin2_kogane_assets`. Reads the retail Sokkuri
model/anim/parameter banks off the US GPVE01 rev 0 disc, validates them against
the audited ground-invertebrate source contract
(:mod:`experimental.pikmin2_ground_inverts_assets`: Sokkuri clip registry, key
events, parameter blocks), and samples bounded rigid poses through the explicit
draw-matrix path Sokkuri's TEX1MTXIDX display lists require
(``Sokkuri`` manager calls ``setTexMtxLoadType(0x2000)``).

Output (``<output>/``):

* ``sokkuri.json``: schema-1 manifest (species ``Sokkuri``, enemy_id 79) with
  per-clip ``file``/``events``/``source_frames``/``sha256``/``status``,
  ``poses`` (``file``/``frame``/``bytes``/``sha256``) holding converted poses
  only under contiguous ``_00..`` slot names, and ``unsupported_frames``
  listing sampled source frames the converter rejected.
* ``ginv_Sokkuri_<clip>_%02d.mod``: sampled pose meshes, named exactly as the
  batch-2 ground loader opens them
  (``engine/pc_port/pc_p2_batch2.cpp:92-117`` ``loadPose``), plus a per-pose
  ``.json`` conversion record.
* ``enemy.bmd`` and the four ``sokkuri/enemy*.txt`` metadata files, preserved
  verbatim for audit.

Deterministic: hashed disc reads, fixed clip order, no timestamps. Nothing is
fabricated: a clip that fails to convert is recorded ``unsupported`` with its
reason, never replaced with a placeholder pose.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_animation import resource_chunks, sample_frames
from experimental.pikmin2_breadbug_assets import parameter_blocks
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_ground_inverts_assets import (
    EXPECTED_EVENTS,
    LOOPS,
    MAX_POSES,
    profile,
)
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_skinning import draw_matrices

SPECIES = 'Sokkuri'
ENEMY_ID = 79
MANIFEST = 'sokkuri.json'
MODEL_PATH = 'enemy/data/Sokkuri/model.szs'
ANIM_PATH = 'enemy/data/Sokkuri/anim.szs'
PARM_PATH = 'enemy/parm/enemyParms.szs'
PARM_PREFIX = 'sokkuri/'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt',
                  'enemystoneinfo.txt')

LIMITATIONS = [
    'Sampled rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events and parameter text are preserved as data only; no damage, disguise, flick or carry behavior executes.',
    'No native runtime, AI/FSM, install or arena placement is provided by this module; see experimental.pikmin2_sokkuri_content for staging.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pose_name(clip, number):
    """Native bank filename for one sampled pose (batch-2 ``loadPose`` grammar)."""
    return f'ginv_{SPECIES}_{clip}_{number:02}.mod'


def extract(iso, output, pose_limit=6):
    if type(pose_limit) is not int or not 2 <= pose_limit <= MAX_POSES:
        raise ValueError(f'Pose limit must be 2..{MAX_POSES}')
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
            raise ValueError('Sokkuri model missing enemy.bmd') from None
        motions = archive_files(read(disc, ANIM_PATH))
        params = archive_files(read(disc, PARM_PATH))
    names = joints(model)
    if not names:
        raise ValueError('Sokkuri model carries no joints')
    model_blocks = blocks(model)
    try:
        envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
        draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
    except (KeyError, struct.error) as error:
        raise ValueError(f'Invalid Sokkuri model skinning blocks: {error}') from None

    metadata = {}
    for filename in METADATA_FILES:
        try:
            raw = params[PARM_PREFIX + filename]
        except KeyError:
            raise ValueError(f'Sokkuri parameter entry missing: {PARM_PREFIX + filename}') from None
        metadata[filename] = sha(raw)
        (output / filename).write_bytes(raw)
    (output / 'enemy.bmd').write_bytes(model)

    blocks_list = parameter_blocks(params[PARM_PREFIX + 'enemyparm.txt'])
    rows = animation_rows(params[PARM_PREFIX + 'enemyanimmgr.txt'].decode('shift_jis'))
    # Validates the general/proper parameter blocks, the disc values, the clip
    # registry order and every clip's key events; raises ValueError on mismatch.
    info = profile(SPECIES, blocks_list, rows)

    clips = []
    reference = None
    total_pose_bytes = 0
    for row in rows:
        stem = Path(row['file']).stem
        try:
            raw = motions[row['file']]
        except KeyError:
            raise ValueError(f'Sokkuri motion missing: {row["file"]}') from None
        (output / row['file']).write_bytes(raw)
        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        if raw[40] not in LOOPS:
            raise ValueError(f'Unsupported Sokkuri loop attribute: {row["file"]}')
        clip = dict(file=row['file'], events=[list(event) for event in row['events']],
                    source_frames=duration, sha256=sha(raw),
                    loop_attribute=raw[40], loop_semantics=LOOPS[raw[40]],
                    poses=[], unsupported_frames=[], status='unsupported')
        if row['events'] != EXPECTED_EVENTS[SPECIES][stem]:
            raise ValueError(f'Sokkuri clip {stem} key events mismatch')
        # Bank slots are assigned to converted poses only, contiguously from
        # zero: the native loader opens indices 0..N-1 and aborts on a gap, so
        # an unconvertible sampled frame is recorded under unsupported_frames
        # (never replaced with a placeholder) and never occupies a slot.
        for frame in sample_frames(duration, pose_limit):
            try:
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                matrices = draw_matrices(model_blocks, pose)
                decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                name = pose_name(stem, len(clip['poses']))
                conversion = write_model(decoded, output / name, 'enemy.bmd')
                conversion.update(source='enemy.bmd', output=name,
                                  weighted_pose_baked=envelopes > 0,
                                  source_frame=frame)
                data = (output / name).read_bytes()
                resources = resource_chunks(data)
                if reference is not None and resources != reference:
                    raise ValueError('Sokkuri pose changes immutable render resources')
                reference = resources
                total_pose_bytes += len(data)
                clip['poses'].append(dict(file=name, frame=frame, bytes=len(data),
                                          sha256=sha(data)))
                (output / Path(name).with_suffix('.json')).write_text(
                    json.dumps(conversion, sort_keys=True, indent=2) + '\n',
                    encoding='utf-8')
            except (ValueError, KeyError, ArithmeticError) as error:
                clip['unsupported_frames'].append(frame)
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
        metadata_sha256=metadata,
        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                      weighted_baking=envelopes > 0,
                      self_contained_resources=draws > 0),
        clips=clips, total_pose_bytes=total_pose_bytes,
        limitations=list(LIMITATIONS))
    (output / MANIFEST).write_text(
        json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=6)
    args = parser.parse_args()
    summary = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps({
        'clips': len(summary['clips']),
        'converted': sum(c['status'] == 'converted' for c in summary['clips']),
        'poses': sum(1 for c in summary['clips'] for p in c['poses'] if 'file' in p),
        'pose_bytes': summary['total_pose_bytes'],
    }, indent=2))
