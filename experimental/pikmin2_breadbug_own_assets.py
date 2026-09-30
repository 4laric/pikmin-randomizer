"""Breadbug (PanModoki, enemy ID 38) OWN source assets; no native behaviour substitution.

Single-species ISO extractor for the campaign OWN port (#898), modelled on
:mod:`experimental.pikmin2_minihoudai_assets` (hashed disc reads, GPVE01
check, deterministic sampled rigid poses through the explicit draw-matrix
path). It re-reads the retail PanModoki model/animation/parameter banks off
the US GPVE01 rev 0 disc; the older ``pikmin2_breadbug_assets`` import (one
first-frame pose per clip, visual-proxy era) is not used.

Output (``<output>/``, the identity-keyed ``PanModoki`` directory the family
installer pre-flights via ``_read_identity_source(source, 38, 'PanModoki')``):

* ``identity.json`` (schema 1, source_id 38, enum_name ``PanModoki``).
* ``breadbug.json``: schema-1 manifest (species ``PanModoki``, enemy_id 38)
  with per-clip ``file``/``events``/``source_frames``/``sha256``/``status``
  and ``poses`` (``file``/``frame``/``sha256``) under contiguous ``_00..``
  slot names; ``unsupported_frames`` lists sampled frames the converter
  rejected (never replaced by a placeholder).
* ``breadbug_<clip>_<ii:02>.mod`` pose meshes (+ per-pose ``.json``
  conversion records). ``experimental.pikmin2_breadbug_stage`` stages them
  into the private model room with ``p2-breadbug-bank.txt``; the native draw
  hook ``pc_p2_breadbug_teki_draw`` picks the pose nearest the source FSM's
  clip frame.
* ``enemy.bmd`` and the four ``panmodoki/enemy*.txt`` files verbatim
  (``enemyparm.txt`` is staged as ``p2-breadbug-parms.txt`` and parsed by
  native ``p2breadbugfsm::parseEnemyParm``).

The clip order is the retail ``panmodoki/enemyanimmgr.txt`` row order, which
is the PanModokiBase AnimID order (PanModokiBase.h:242-253): dead, move1
(walk), move2 (back), type1 (pulled), type2 (appear), type3 (hide), type4
(damage), type5 (carcass carry), wait1.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_breadbug_assets import collision_nodes, parameter_blocks, sha
from experimental.pikmin2_convert import decode, write_model, blocks
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_skinning import draw_matrices

SPECIES = 'PanModoki'
ENEMY_ID = 38
ENUM_NAME = 'PanModoki'
MANIFEST = 'breadbug.json'
IDENTITY = 'identity.json'
MODEL_PATH = 'enemy/data/PanModoki/model.szs'
ANIM_PATH = 'enemy/data/PanModoki/anim.szs'
PARM_PATH = 'enemy/parm/enemyParms.szs'
PARM_PREFIX = 'panmodoki/'
METADATA_FILES = ('enemyparm.txt', 'enemycoll.txt', 'enemyanimmgr.txt', 'enemystoneinfo.txt')

# PanModokiBase AnimID order == retail enemyanimmgr.txt row order.
CLIPS = ('dead', 'move1', 'move2', 'type1', 'type2', 'type3', 'type4', 'type5', 'wait1')

# Poses sampled per clip (native bound: <= 24 per clip, <= 1 MiB per mesh,
# <= 24 MiB total). Looping locomotion gets the most; type5 is the carcass
# hold, type1 the short pulled loop.
POSE_LIMITS = {'dead': 6, 'move1': 8, 'move2': 8, 'type1': 4, 'type2': 6,
               'type3': 6, 'type4': 6, 'type5': 3, 'wait1': 4}

LIMITATIONS = [
    'Sampled rigid poses with approximate materials; no skeletal playback. The native draw holds the staged pose nearest the source FSM clip frame.',
    'Key events are data for the native source FSM clock (pc_p2_breadbug_fsm).',
    'The PanHouse nest model is not extracted; the native port keeps only the home point.',
    'This module extracts data only; the native source FSM owns behaviour.',
]


def pose_name(clip, number):
    """Deterministic pose mesh filename for one sampled pose."""
    return f'breadbug_{clip}_{number:02}.mod'


def extract(iso, output, pose_limit=None):
    if pose_limit is not None and (type(pose_limit) is not int or not 2 <= pose_limit <= 8):
        raise ValueError(f'Pose limit must be 2..8 or None: {pose_limit!r}')
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
            raise ValueError('PanModoki model missing enemy.bmd') from None
        motions = archive_files(read(disc, ANIM_PATH))
        params = archive_files(read(disc, PARM_PATH))
    names = joints(model)
    model_blocks = blocks(model)

    metadata = {}
    for filename in METADATA_FILES:
        try:
            raw = params[PARM_PREFIX + filename]
        except KeyError:
            raise ValueError(f'PanModoki parameter entry missing: {PARM_PREFIX + filename}') from None
        metadata[filename] = sha(raw)
        (output / filename).write_bytes(raw)
    (output / 'enemy.bmd').write_bytes(model)
    parameter = parameter_blocks(params[PARM_PREFIX + 'enemyparm.txt'])
    rows = animation_rows(params[PARM_PREFIX + 'enemyanimmgr.txt'].decode('shift_jis'))
    stems = [Path(row['file']).stem for row in rows]
    if stems != list(CLIPS):
        raise ValueError(f'Unexpected PanModoki clip order: {stems!r}')

    clips = []
    for row in rows:
        stem = Path(row['file']).stem
        try:
            raw = motions[row['file']]
        except KeyError:
            raise ValueError(f'PanModoki motion missing: {row["file"]}') from None
        (output / row['file']).write_bytes(raw)
        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        clip = dict(file=row['file'], events=[list(event) for event in row['events']],
                    source_frames=duration, sha256=sha(raw), poses=[], unsupported_frames=[],
                    status='unsupported')
        limit = pose_limit if pose_limit is not None else POSE_LIMITS[stem]
        # Sampled frames plus every key-event frame (loop bounds, hide key), so
        # the short pulled loop (type1 5..10) and the carcass hold have poses.
        frames = sorted(set(sample_frames(duration, limit)) | {int(e[0]) for e in row["events"] if 0 <= int(e[0]) < duration})
        for frame in frames:
            try:
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                matrices = draw_matrices(model_blocks, pose)
                decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                name = pose_name(stem, len(clip['poses']))
                conversion = write_model(decoded, output / name, 'enemy.bmd')
                conversion.update(source='enemy.bmd', output=name, weighted_pose_baked=True, source_frame=frame)
                data = (output / name).read_bytes()
                clip['poses'].append(dict(file=name, frame=frame, sha256=hashlib.sha256(data).hexdigest()))
                (output / Path(name).with_suffix('.json')).write_text(
                    json.dumps(conversion, sort_keys=True, indent=2) + '\n', encoding='utf-8')
            except (ValueError, KeyError, ArithmeticError) as error:
                clip['unsupported_frames'].append(frame)
                clip.setdefault('unsupported_reasons', []).append(str(error))
        if clip['poses']:
            clip['status'] = 'converted'
        else:
            clip['unsupported_reason'] = 'no sampled frames converted'
        clips.append(clip)

    result = dict(
        schema=1, species=SPECIES, enemy_id=ENEMY_ID, enum_name=ENUM_NAME,
        disc_id=header[:6].decode(), disc_revision=header[7],
        source_sha256=hashes, model_sha256=sha(model), joints=names,
        parameters=parameter, metadata_sha256=metadata, clips=clips,
        pose_limits={Path(c['file']).stem: (pose_limit if pose_limit is not None else POSE_LIMITS[Path(c['file']).stem])
                     for c in clips},
        collision=collision_nodes(params[PARM_PREFIX + 'enemycoll.txt'], len(names)),
        limitations=list(LIMITATIONS))
    (output / MANIFEST).write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (output / IDENTITY).write_text(
        json.dumps(dict(schema=1, source_id=ENEMY_ID, enum_name=ENUM_NAME), indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=None)
    args = parser.parse_args()
    summary = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps({
        'clips': len(summary['clips']),
        'converted': sum(c['status'] == 'converted' for c in summary['clips']),
        'poses': sum(len(c['poses']) for c in summary['clips']),
        'joints': len(summary['joints']),
    }, indent=2))
