"""Extract local Groink source poses, muzzle transforms and variant parameters."""
import argparse
import json
import math
from pathlib import Path

from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_breadbug_assets import sha, parameter_blocks, collision_nodes
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_convert import blocks, convert
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices


def profile(raw):
    """Read general fields by block identity, never flatten duplicate fp keys."""
    parsed = parameter_blocks(raw)
    candidates = [b for b in parsed if all(k in b for k in ('fp00', 'fp14', 'fp22', 'fp23', 'fp24'))]
    if len(candidates) != 1:
        raise ValueError('Expected exactly one general parameter block')
    general = candidates[0]
    fields = dict(health=general['fp00'], search_distance=general['fp14'],
                  attack_radius=general['fp22'], attack_hit_angle=general['fp23'],
                  attack_damage=general['fp24'])
    if any(v < 0 for v in fields.values()) or fields['search_distance'] <= 0:
        raise ValueError('Invalid Groink general parameters')
    return dict(parameter_blocks=parsed, general=fields)


def muzzle(matrix):
    """Model-space source joint basis BEFORE the runtime vertical callback."""
    if len(matrix) != 3 or any(len(row) != 4 for row in matrix):
        raise ValueError('Expected a 3x4 muzzle matrix')
    if not all(math.isfinite(v) for row in matrix for v in row):
        raise ValueError('Nonfinite muzzle transform')
    axis = [row[0] for row in matrix]
    length = math.sqrt(sum(v*v for v in axis))
    if length <= 1e-12:
        raise ValueError('Degenerate muzzle axis')
    axis = [v/length for v in axis]
    return dict(joint_matrix=matrix, forward=axis,
                position=[matrix[i][3]+25*axis[i] for i in range(3)],
                space='model; before runtime vertical aim callback and owner transform')


def extract(iso, output, pose_limit=3):
    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
        raise ValueError('Pose limit must be 2..8')
    index = disc_files(iso)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    result = dict(schema=1, native_ready=False, source_sha256=hashes,
                  resource_family='MiniHoudai', variants={})
    with iso.open('rb') as disc:
        def read(path):
            offset, size = index[path]
            disc.seek(offset)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated disc resource')
            hashes[path] = sha(raw)
            return raw
        params = archive_files(read('enemy/parm/enemyParms.szs'))
        model = archive_files(read('enemy/data/MiniHoudai/model.szs'))['enemy.bmd']
        motions = archive_files(read('enemy/data/MiniHoudai/anim.szs'))
        root = output/'MiniHoudai'
        root.mkdir()
        modelpath = root/'enemy.bmd'
        modelpath.write_bytes(model)
        names = joints(model)
        if names.count('kuti') != 1:
            raise ValueError('Expected one source kuti muzzle joint')
        metadata = {}
        for filename in ('enemyparm.txt', 'enemycoll.txt', 'enemyanimmgr.txt', 'enemystoneinfo.txt'):
            raw = params['minihoudai/'+filename]
            (root/filename).write_bytes(raw)
            metadata[filename] = sha(raw)
        fixed = params['fminihoudai/enemyparm.txt']
        (root/'fixed-enemyparm.txt').write_bytes(fixed)
        for name, enemy_id, raw in (('MiniHoudai', 78, params['minihoudai/enemyparm.txt']),
                                    ('FminiHoudai', 97, fixed)):
            result['variants'][name] = dict(enemy_id=enemy_id, parameter_sha256=sha(raw),
                                           **profile(raw))
        clips = []
        for row in animation_rows(params['minihoudai/enemyanimmgr.txt'].decode('shift_jis')):
            raw = motions[row['file']]
            (root/row['file']).write_bytes(raw)
            clip = dict(row, sha256=sha(raw), status='unsupported', poses=[], muzzle_samples=[])
            try:
                duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
                clip['source_frames'] = duration
                for i, frame in enumerate(sample_frames(duration, pose_limit)):
                    _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                    transform = muzzle(joint_matrices(blocks(model), pose)[names.index('kuti')])
                    clip['muzzle_samples'].append(dict(frame=frame, **transform))
                    filename = Path(row['file']).stem+f'_{i:02}.mod'
                    try:
                        conversion = convert(modelpath, root/filename, True, bake_rigid=True, pose=pose)
                        conversion.update(source='enemy.bmd', output=filename)
                        (root/Path(filename).with_suffix('.json')).write_text(json.dumps(conversion, indent=2)+'\n', encoding='utf-8')
                        clip['poses'].append(dict(file=filename, frame=frame,
                                                  sha256=sha((root/filename).read_bytes()), muzzle=transform))
                    except ValueError as error:
                        clip['unsupported_reason'] = str(error)
                if len(clip['poses']) == len(clip['muzzle_samples']):
                    clip['status'] = 'converted'
            except ValueError as error:
                clip['unsupported_reason'] = str(error)
            clips.append(clip)
        result.update(model_sha256=sha(model), joints=names, muzzle_joint=names.index('kuti'),
                      metadata_sha256=metadata, clips=clips,
                      collision=collision_nodes(params['minihoudai/enemycoll.txt'], len(names)))
    result['limitations'] = [
        'Sampled rigid poses and approximate materials; no skeletal/event playback.',
        'Muzzle transforms precede runtime aim callback and owner world transform.',
        'No native actor, map collision, damage receiver or projectile rendering installed.',
        'Stationary single-shell policy is a subset of the three-shell, six-node source system.',
        'Walking, target acquisition, attack FSM, carcass delivery and revival remain unimplemented.'
    ]
    (output/'groink.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=3)
    args = parser.parse_args()
    result = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps(dict(joints=len(result['joints']), clips=len(result['clips']),
                          converted=sum(c['status']=='converted' for c in result['clips']),
                          poses=sum(len(c['poses']) for c in result['clips']))))
