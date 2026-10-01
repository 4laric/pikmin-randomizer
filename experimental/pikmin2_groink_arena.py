"""Stage one source firing pose for the isolated stationary Groink harness."""
import argparse
import json
import math
from pathlib import Path

from experimental.pikmin2_breadbug_assets import sha
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_groink_assets import profile
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_sheargrub_assets import animation_rows, joints


def profile_text(owner, target, yaw, matrix, search_distance, attack_radius):
    if len(owner) != 3 or len(target) != 3 or len(matrix) != 3 or any(len(row) != 4 for row in matrix):
        raise ValueError('Invalid arena transform shape')
    values = [*owner, *target, yaw, search_distance, attack_radius, *(v for row in matrix for v in row)]
    if not all(math.isfinite(v) and abs(v) <= 100000 for v in values):
        raise ValueError('Invalid arena transform/parameter value')
    if abs(yaw) > 2*math.pi or not 0 < search_distance <= 1000 or not 0 <= attack_radius <= 1000:
        raise ValueError('Invalid arena yaw/attack parameters')
    fmt = lambda values: ' '.join(format(v, '.9g') for v in values)
    return ('P2_GROINK_ARENA_1\nmodel groink_attack.mod\n'
            + 'params '+fmt([search_distance, attack_radius])+'\n'
            + 'owner '+fmt([*owner, yaw])+'\n'
            + 'target '+fmt(target)+'\n'
            + 'muzzle '+fmt([v for row in matrix for v in row])+'\n')


def stage(source, output, owner, target, yaw=0.0, variant='FminiHoudai'):
    if variant not in ('MiniHoudai', 'FminiHoudai'):
        raise ValueError('Invalid Groink variant')
    manifest = json.loads((source/'groink.json').read_text(encoding='utf-8'))
    root = source/'MiniHoudai'
    model = (root/'enemy.bmd').read_bytes()
    clip = next(c for c in manifest['clips'] if c['file']=='attack1.bca')
    animation = (root/'attack1.bca').read_bytes()
    if sha(model) != manifest['model_sha256'] or sha(animation) != clip['sha256']:
        raise ValueError('Source model/animation fingerprint mismatch')
    registry = (root/'enemyanimmgr.txt').read_bytes()
    if sha(registry) != manifest['metadata_sha256']['enemyanimmgr.txt']:
        raise ValueError('Source animation registry fingerprint mismatch')
    source_clip = next(c for c in animation_rows(registry.decode('shift_jis')) if c['file']=='attack1.bca')
    events = [frame for frame, event in source_clip['events'] if event==4]
    if len(events) != 1:
        raise ValueError('Expected one attack emission event')
    raw_params = (root/('fixed-enemyparm.txt' if variant=='FminiHoudai' else 'enemyparm.txt')).read_bytes()
    if sha(raw_params) != manifest['variants'][variant]['parameter_sha256']:
        raise ValueError('Source parameter fingerprint mismatch')
    general = profile(raw_params)['general']
    names = joints(model)
    duration, pose = bca_pose(animation, events[0], len(names), allow_scale=True)
    if not 0 <= events[0] < duration:
        raise ValueError('Emission event outside animation')
    parsed = blocks(model)
    muzzle = joint_matrices(parsed, pose)[names.index('kuti')]
    text = profile_text(owner, target, yaw, muzzle, general['search_distance'], general['attack_radius'])
    decoded = decode(model, True, True, draw_matrices=draw_matrices(parsed, pose))
    output.mkdir(parents=True, exist_ok=False)
    destination = output/'assets/dataDir/courses/pikmin2room/groink_attack.mod'
    conversion = write_model(decoded, destination, 'enemy.bmd')
    conversion.update(source='enemy.bmd', output='groink_attack.mod', weighted_pose_baked=True)
    destination.with_suffix('.json').write_text(json.dumps(conversion, indent=2)+'\n', encoding='utf-8')
    (output/'p2-groink-arena.txt').write_text(text, encoding='utf-8')
    result = dict(schema=1, native_ready=False, variant=variant, source_frame=events[0],
                  source_model_sha256=sha(model), source_animation_sha256=sha(animation),
                  pose_sha256=sha(destination.read_bytes()), owner=list(owner), target=list(target), yaw=yaw,
                  limitations=['Stationary harness with explicit fire trigger; no attack FSM or damage.',
                               'Baked source firing pose; dynamic visual muzzle alignment unvalidated.',
                               'Host map trace and native engine hooks are required; staging is not installation.'])
    (output/'groink-arena.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--owner', type=float, nargs=3, required=True)
    parser.add_argument('--target', type=float, nargs=3, required=True)
    parser.add_argument('--yaw', type=float, default=0)
    parser.add_argument('--variant', choices=('MiniHoudai','FminiHoudai'), default='FminiHoudai')
    args = parser.parse_args()
    print(json.dumps(stage(args.source, args.output, args.owner, args.target, args.yaw, args.variant)))
