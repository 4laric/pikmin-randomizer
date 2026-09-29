"""Stage the native Titan Dweevil (BigTreasure, source 73) campaign inputs (#246 OWN).

Reads a verified ``pikmin2_bigtreasure_assets`` import tree (the
``<content>/BigTreasure/`` extractor output: ``bigtreasure.json``,
``BigTreasure/`` with the disc model/clips/metadata and the baked poses, and
``pellets/``) and writes exactly what ``pc_p2_bigtreasure_teki.cpp`` opens:

* ``p2-bigtreasure-parms.txt``  verbatim retail ``bigtreasure/enemyparm.txt``
* ``p2_bigtreasure_events.txt`` P2_RETAIL_EVENTS_1 (29 unique clips,
  ``pikmin2_bigtreasure_motion.encode``)
* ``p2-bigtreasure-bank.txt``   P2_BIGTREASURE_BANK_1: the staged pose frames
  per AnimID, the ``otakara_*`` / ``*_eff`` / ``kosi`` joint matrices AT EACH
  STAGED POSE (so captured weapons and the attack emit joints follow the
  animation), the bind-pose joints and the leg layout
  (``IKSystemMgr::startProgramedIK``: distance from the owner to the rhand3jnt
  foot and each foot's angle from the face direction, measured on the
  ``wait2`` frame-0 standing pose)
* ``p2-bigtreasure-coll.txt``  verbatim retail ``bigtreasure/enemycoll.txt``
  (the Titan's own collision tree: body, weapon and leg parts; the native
  actor builds real P1 CollParts from it so a hit lands on the part the
  Pikmin is stuck to, #246)
* ``assets/dataDir/courses/pikmin2room/bigtreasure_<clip>_<ii>.mod`` (the
  sampled poses) and ``bigtreasure_pellet_<weapon>.mod`` (the four weapons;
  Louie's model is unsupported by the converter and stays undrawn)

Everything is derived from the disc import; nothing is authored here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from experimental import pikmin2_bigtreasure_motion as motion
from experimental.pikmin2_convert import blocks
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices

ROOM = 'assets/dataDir/courses/pikmin2room'
PARMS_TXT = 'p2-bigtreasure-parms.txt'
EVENTS_TXT = 'p2_bigtreasure_events.txt'
BANK_TXT = 'p2-bigtreasure-bank.txt'
COLL_TXT = 'p2-bigtreasure-coll.txt'
BANK_HEADER = 'P2_BIGTREASURE_BANK_1'

# BigTreasure.h AnimID order == enemyanimmgr.txt rows (slot 29 is wait2 again).
ANIM_SLOTS = ('appear', 'appear2', 'wait1', 'preattackf', 'attackf', 'attackendf',
              'preattackfr', 'attackfr', 'attackendfr', 'preattackfl', 'attackfl',
              'attackendfl', 'preattackfb', 'attackfb', 'attackendfb', 'preattackw',
              'attackw', 'attackendw', 'preattackg', 'attackg', 'attackendg',
              'preattacke', 'attacke', 'attackende', 'dropitem', 'wait2', 'flick',
              'dead', 'move1', 'wait2')
BANK_JOINTS = ('otakara_elec', 'otakara_fire', 'otakara_gas', 'otakara_water', 'otakara_loozy', 'kosi',
               'otakara_elec_eff', 'otakara_fire_eff', 'otakara_gas_eff', 'otakara_water_eff')
# IKSystemMgr::setupJoint order (BigTreasure.cpp:453-470): legs 0..3 bottoms.
LEG_FEET = ('rhand3jnt', 'lhand3jnt', 'rfoot3jnt', 'lfoot3jnt')
WEAPONS = ('elec', 'fire', 'gas', 'water')
# Pose sampling per clip for the native draw (bounded bytes); the extractor
# samples up to its own pose limit and we keep an even subset.
MAX_POSES = 6
MAX_BYTES = 40 * 1024 * 1024


class BigTreasureStageError(ValueError):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _import_root(source):
    source = Path(source)
    for candidate in (source, source / 'bt-import'):
        if (candidate / 'bigtreasure.json').is_file() and (candidate / 'BigTreasure').is_dir():
            return candidate
    raise BigTreasureStageError(f'no BigTreasure import tree under {source}')


def _subset(poses, limit):
    if len(poses) <= limit:
        return list(poses)
    picks = sorted({round(i * (len(poses) - 1) / (limit - 1)) for i in range(limit)})
    return [poses[i] for i in picks]


def _fmt(matrix):
    for row in matrix:
        for v in row:
            if not math.isfinite(v) or abs(v) > 100000:
                raise BigTreasureStageError('nonphysical joint matrix')
    return ' '.join(f'{v:.6g}' for row in matrix for v in row)


def plan(source):
    """Build the staging plan (file bytes) from an import tree. Nothing is written."""
    root = _import_root(source)
    report = json.loads((root / 'bigtreasure.json').read_bytes())
    if report.get('policy') != 'P2_BIGTREASURE_IMPORT_1' or report.get('enemy_id') != 73:
        raise BigTreasureStageError('expected a BigTreasure (73) import report')
    boss = report['boss']
    model = (root / 'BigTreasure' / 'enemy.bmd').read_bytes()
    if _sha(model) != boss['model_sha256']:
        raise BigTreasureStageError('enemy.bmd hash mismatch')
    model_blocks = blocks(model)
    names = boss['joints']
    missing = [j for j in BANK_JOINTS + LEG_FEET if j not in names]
    if missing:
        raise BigTreasureStageError(f'missing joints {missing}')
    parms = (root / 'BigTreasure' / 'enemyparm.txt').read_bytes()
    if _sha(parms) != boss['metadata_sha256']['enemyparm.txt']:
        raise BigTreasureStageError('enemyparm.txt hash mismatch')
    coll = (root / 'BigTreasure' / 'enemycoll.txt').read_bytes()
    if _sha(coll) != boss['metadata_sha256'].get('enemycoll.txt'):
        raise BigTreasureStageError('enemycoll.txt hash mismatch')
    events = motion.encode(root / 'BigTreasure', root / 'bigtreasure.json')

    clips = {c['name']: c for c in boss['clips']}
    rows = [BANK_HEADER]
    room = []
    total = 0

    # Leg layout from the standing wait2 frame 0 (owner at the model origin,
    # model facing +Z: angle = atan2(x, z)).
    wait2 = (root / 'BigTreasure' / 'wait2.bca').read_bytes()
    _, pose = bca_pose(wait2, 0, len(names), allow_scale=True)
    world = joint_matrices(model_blocks, local_overrides=pose)
    feet = [world[names.index(j)] for j in LEG_FEET]
    leg0 = feet[0]
    distance = math.sqrt(leg0[0][3] ** 2 + leg0[1][3] ** 2 + leg0[2][3] ** 2)
    angles = [math.atan2(m[0][3], m[2][3]) for m in feet]
    rows.append(f'legs {distance:.6g} ' + ' '.join(f'{a:.6g}' for a in angles))
    bind = joint_matrices(model_blocks)
    for joint in BANK_JOINTS:
        rows.append(f'bind {joint} {_fmt(bind[names.index(joint)])}')

    for anim, name in enumerate(ANIM_SLOTS):
        clip = clips.get(name)
        if clip is None or clip['status'] != 'converted':
            raise BigTreasureStageError(f'clip {name} not converted')
        frames = clip['source_frames']
        # Slot 29 (Walk's wait2) shares wait2's poses: its rows are written
        # but no second copy of the meshes is staged (the native reuses them).
        staged = _subset([p for p in clip['poses'] if 'file' in p], MAX_POSES)
        rows.append(f'clip {anim} {name} {frames} {len(staged)}')
        raw = (root / 'BigTreasure' / f'{name}.bca').read_bytes()
        if _sha(raw) != clip['source_sha256']:
            raise BigTreasureStageError(f'{name}.bca hash mismatch')
        for index, entry in enumerate(staged):
            rows.append(f'pose {anim} {index} {entry["frame"]}')
            _, pose = bca_pose(raw, entry['frame'], len(names), allow_scale=True)
            world = joint_matrices(model_blocks, local_overrides=pose)
            for joint in BANK_JOINTS:
                rows.append(f'joint {anim} {index} {joint} {_fmt(world[names.index(joint)])}')
            if anim == 29:
                continue
            data = (root / 'BigTreasure' / entry['file']).read_bytes()
            if _sha(data) != entry['sha256']:
                raise BigTreasureStageError(f'pose hash mismatch {entry["file"]}')
            staged_name = f'bigtreasure_{name}_{index:02}.mod'
            total += len(data)
            room.append((staged_name, data))
    for weapon in WEAPONS:
        entry = report['pellet_models'][weapon]
        if entry['status'] != 'converted':
            raise BigTreasureStageError(f'weapon pellet {weapon} not converted')
        data = (root / 'pellets' / entry['file']).read_bytes()
        if _sha(data) != entry['sha256']:
            raise BigTreasureStageError(f'pellet hash mismatch {weapon}')
        total += len(data)
        room.append((f'bigtreasure_pellet_{weapon}.mod', data))
    if total > MAX_BYTES:
        raise BigTreasureStageError(f'staged bytes {total} over budget')
    rows.append('end')
    bank = ('\n'.join(rows) + '\n').encode('ascii')
    return dict(parms={PARMS_TXT: parms, EVENTS_TXT: events, BANK_TXT: bank, COLL_TXT: coll}, room=room,
                legs=dict(distance=distance, angles=angles), pose_bytes=total)


def _write_new_or_same(path, data):
    if path.exists() or path.is_symlink():
        if not path.is_file() or path.read_bytes() != data:
            raise BigTreasureStageError(f'refusing to replace existing {path.name}')
        return False
    path.write_bytes(data)
    return True


def stage(run, staged_plan):
    """Write a plan into ``run`` (files must be new or byte-identical)."""
    run = Path(run)
    room = run / ROOM
    private = room.is_dir() and room.resolve().is_relative_to(run.resolve())
    for name, data in sorted(staged_plan['parms'].items()):
        _write_new_or_same(run / name, data)
    poses = 0
    if private:
        for name, data in staged_plan['room']:
            _write_new_or_same(room / name, data)
            poses += 1
    return dict(files=sorted(staged_plan['parms']), room_files=poses,
                pose_bytes=staged_plan['pose_bytes'] if private else 0,
                room='private' if private else 'missing',
                legs=staged_plan['legs'],
                bank_sha256=_sha(staged_plan['parms'][BANK_TXT]))


def stage_from(source, run):
    return stage(run, plan(source))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='BigTreasure import tree')
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(stage_from(args.source, args.run), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
