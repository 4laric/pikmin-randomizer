"""Convert literal retail decorative foliage into private native pose resources.

Uses the accepted randomizer J3D converters without species aliases or converter
tolerances. Assets remain private; this script does not install or launch actors.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--randomizer-root', type=Path, required=True)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=12)
    parser.add_argument('--sources', type=int, nargs='+', choices=(46, 47, 49, 51, 52, 80, 81, 88, 90, 91, 92),
                        default=[91, 88],
                        help='Literal source IDs to convert; default preserves original 91/88 bank')
    args = parser.parse_args()
    if not 2 <= args.pose_limit <= 64:
        raise ValueError('pose-limit must be 2..64')
    if len(set(args.sources)) != len(args.sources):
        raise ValueError('Duplicate source selection')
    if args.output.exists():
        raise ValueError('Output already exists; preserve previous evidence')
    root = args.randomizer_root.resolve(strict=True)
    sys.path.insert(0, str(root))
    from experimental.pikmin2_assets import archive_files, disc_files
    from experimental.pikmin2_animation import resource_chunks, sample_frames
    from experimental.pikmin2_breadbug_assets import collision_nodes, parameter_blocks
    from experimental.pikmin2_convert import blocks, decode, write_model
    from experimental.pikmin2_flora_assets import flora_animation_rows
    from experimental.pikmin2_purple import bca_pose
    from experimental.pikmin2_rigid import joint_matrices
    from experimental.pikmin2_sheargrub_assets import joints
    from experimental.pikmin2_skinning import draw_matrices

    # Literal identities and authored BCA metadata; never alias red Figwort49
    # to brown Figwort91 or globally admit arbitrary animation loop attributes.
    catalog = {91: ('KareOoinu_s', 'kareooinu_s', 'normal', 0),
               88: ('Nekojarashi', 'nekojarashi', 'postshadow', 0),
               47: ('Clover', 'clover', 'normal', 0),
               49: ('Ooinu_s', 'ooinu_s', 'normal', 2),
               46: ('Tanpopo', 'tanpopo', 'normal', 0),
               51: ('Wakame_s', 'wakame_s', 'normal', 2),
               52: ('Wakame_l', 'wakame_l', 'normal', 2),
               80: ('Tukushi', 'tukushi', 'normal', 2),
               81: ('Watage', 'watage', 'postshadow', 0),
               90: ('Zenmai', 'zenmai', 'normal', 0),
               92: ('KareOoinu_l', 'karaooinu_l', 'normal', 0)}

    species = [(source_id, *catalog[source_id]) for source_id in args.sources]
    index = disc_files(args.iso)
    hashes = {}
    args.output.mkdir(parents=True)
    lines = ['P2_ORIGINAL_FOLIAGE_1']
    report = {'schema': 1, 'policy': lines[0], 'species': {},
              'source_sha256': hashes, 'source_revision': subprocess.check_output(
                  ['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip(),
              'native_runtime_validated': False,
              'limitations': ['Sampled flattened geometry and approximate source materials.',
                              'No runtime behavior is executed by this converter.',
                              'Fully culled touched-clock fidelity remains unqualified: retail lifecycle pauses the animator without visibility or nearby Pikmin cell activation.']}
    report['converter_sha256'] = {filename: sha((root / 'experimental' / filename).read_bytes())
        for filename in ('pikmin2_convert.py', 'pikmin2_skinning.py', 'pikmin2_rigid.py',
                         'pikmin2_purple.py', 'pikmin2_flora_assets.py')}
    report['source_code_sha256'] = {filename: sha((args.source / filename).read_bytes())
        for filename in ('include/Game/enemyInfo.h', 'include/Game/plantsMgr.h',
                         'src/plugProjectMorimuraU/plants.cpp',
                         'src/plugProjectMorimuraU/plantsMgr.cpp',
                         'src/plugProjectYamashitaU/enemyBase.cpp',
                         'src/sysGCU/sysShape.cpp',
                         'src/plugProjectKandoU/creatureLOD.cpp',
                         'src/sysCommonU/geomCylinder.cpp',
                         'src/sysCommonU/camera.cpp')}
    report['parameter_order'] = ['health_fp00', 'territory_fp09', 'private_fp11',
                                 'home_fp10', 'lod_radius_fp32', 'floor_parameter_fp01']
    report['source_semantics'] = {
        'collision': 'Static frame0 joint transforms; root bounding sphere; child contact spheres.',
        'position': 'Authored generator position; no fp01 vertical translation. Plants::Obj::doSimulation is empty.',
        'animation': 'Idle frame0; contact/earthquake activates stop-at-end source clip; ordinary Plants::Obj behavior.',
        'animation_end_clock': 'SysShape::Animator::animate (sysShape.cpp133-187) clamps manual timer at duration-1 and emits END. Registered LOOP_END keys govern repetition; these plant registrations have none. Raw BCA loop attributes49/51/52/80=2 are retained without repeating the actor touch clock.',
        'fully_culled_clock_caveat': 'EnemyBase lifecycle State::animation (enemyBase.cpp86-112) only calls doAnimationCullingOff when isCullingOff (1850-1857): not Cullable, visible, Pikmin in cell, or Dropping. Converter output does not implement or qualify that lifecycle gate.',
        'resources': 'Literal original species model.szs/anim.szs and parameter directory; no aliases.',
        'brown_large_clip': 'Source92 registry karaOoinu_l.bca matches archive karaooinu_l.bca by casefold; the literal kara spelling is preserved.',
        'fully_culled_clock_caveat': 'EnemyBase lifecycle State::animation (enemyBase.cpp86-112) only calls doAnimationCullingOff when isCullingOff (1850-1857): not Cullable, visible, Pikmin in cell, or Dropping. Converter output does not implement or qualify that lifecycle gate.',
        'rewards': 'Plants::Mgr plain EnemyParmsBase; invulnerable nonliving actor, carcass disabled.',
        'foxtail_lod': 'Cylinder origin offset -50*sin(face), -50*cos(face); height fp11; radius fp10.'}
    with args.iso.open('rb') as disc:
        header = disc.read(8)
        if header[:6] != b'GPVE01' or header[7] != 0:
            raise ValueError('Expected GPVE01 retail revision 0')
        report.update(disc_id='GPVE01', disc_revision=0)

        def read(path):
            offset, size = index[path]
            disc.seek(offset)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated ISO member ' + path)
            hashes[path] = sha(raw)
            # Source81 was independently audited against GPVE01. Changed retail
            # archives require a new audit, not automatic requalification.
            watage_pins = {
                'enemy/data/Watage/model.szs': '6fe6a304db148682ff4f65378405b6adcc74adf99489dfcdcf65eb36d39c2693',
                'enemy/data/Watage/anim.szs': 'b6abec15b318d5be8fa3233babd2e64191108b42dc460f1b42a3cade153c14f7',
                'enemy/parm/enemyParms.szs': '3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84',
            }
            if 81 in args.sources and path in watage_pins and hashes[path] != watage_pins[path]:
                raise ValueError('Watage audited archive changed: ' + path)
            return raw

        params = archive_files(read('enemy/parm/enemyParms.szs'))
        for source_id, name, expected_clip, layer, expected_loop in species:
            directory = args.output / name
            directory.mkdir()
            models = archive_files(read(f'enemy/data/{name}/model.szs'))
            motions = archive_files(read(f'enemy/data/{name}/anim.szs'))
            model = models['enemy.bmd']
            directory.joinpath('enemy.bmd').write_bytes(model)
            model_blocks = blocks(model)
            joint_names = joints(model)
            metadata = {}
            for filename in ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt'):
                raw = params[name.lower() + '/' + filename]
                directory.joinpath(filename).write_bytes(raw)
                metadata[filename] = sha(raw)
            parsed = parameter_blocks(directory.joinpath('enemyparm.txt').read_bytes())
            if len(parsed) < 2:
                raise ValueError('Missing Creature/EnemyParmsBase parameter blocks')
            # Plants::Mgr allocates EnemyParmsBase and reads ONLY the first two
            # blocks. Retail may serialize trailing unused proper parameters.
            collision = collision_nodes(directory.joinpath('enemycoll.txt').read_bytes(), len(joint_names))
            rows = flora_animation_rows(directory.joinpath('enemyanimmgr.txt').read_bytes().decode('shift_jis'))
            if len(rows) != 1 or Path(rows[0]['file']).stem.casefold() != expected_clip or rows[0]['events']:
                raise ValueError('Unexpected literal plant animation registry')
            matching = [key for key in motions if key.casefold() == rows[0]['file'].casefold()]
            if len(matching) != 1:
                raise ValueError('Missing or ambiguous literal source motion')
            raw = motions[matching[0]]
            directory.joinpath(matching[0]).write_bytes(raw)
            if len(raw) <= 40 or raw[40] != expected_loop:
                raise ValueError(f'Literal source{source_id} BCA loop metadata mismatch; expected {expected_loop}')
            duration, _ = bca_pose(raw, 0, len(joint_names), allow_scale=True)
            frames = sample_frames(duration, args.pose_limit)
            stem = f'flora_{name}_{expected_clip}'
            reference = None
            poses = []
            world_poses = []
            for number, frame in enumerate(frames):
                _, pose = bca_pose(raw, frame, len(joint_names), allow_scale=True)
                matrices = draw_matrices(model_blocks, pose)
                decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                filename = f'{stem}_{number:02}.mod'
                conversion = write_model(decoded, directory / filename, 'enemy.bmd')
                data = directory.joinpath(filename).read_bytes()
                resources = resource_chunks(data)
                if reference is not None and resources != reference:
                    raise ValueError('Pose changes immutable resources')
                reference = resources
                poses.append({'frame': frame, 'file': filename, 'sha256': sha(data), 'bytes': len(data),
                              'conversion': conversion})
                world_poses.append({'frame': frame, 'matrices': joint_matrices(model_blocks, pose)})
            general = parsed[1]
            keys = ('fp00', 'fp09', 'fp11', 'fp10', 'fp32', 'fp01')
            values = [general[key] for key in keys]
            fmt = lambda values: ' '.join(format(value, '.9g') for value in values)
            lines.append(f'species {source_id} {name} {stem} {len(poses)} {duration}')
            lines.append(f'frames {source_id} ' + ' '.join(map(str, frames)))
            lines.append(f'params {source_id} ' + fmt(values))
            lines.append(f'layer {source_id} {layer}')
            for entry in world_poses:
                for joint, matrix in enumerate(entry['matrices']):
                    lines.append(f"joint {source_id} {entry['frame']} {joint} " + fmt([v for row in matrix for v in row]))
            for number, node in enumerate(collision):
                parent = node['parent'] if node['parent'] is not None else -1
                lines.append(f"collider {source_id} {number} {node['joint']} {parent} {node['id']} {node['code']} {node['attribute']} "
                             + fmt([*node['offset'], node['radius']]))
            report['species'][name] = {'source_id': source_id, 'resource_name': name,
                'model_sha256': sha(model), 'motion_sha256': sha(raw), 'metadata_sha256': metadata,
                'joints': joint_names, 'collision': collision, 'parameter_blocks': parsed,
                'unused_disc_blocks': parsed[2:], 'parameters_consumed': parsed[:2],
                'clip': expected_clip, 'source_frames': duration, 'loop_attribute': raw[40],
                'events': rows[0]['events'], 'poses': poses, 'world_poses': world_poses,
                'layer': layer, 'geometry_flattened': True, 'converter_tolerances': {},
                'source_envelopes': struct.unpack_from('>H', model_blocks['EVP1'], 8)[0],
                'source_lod': {'kind': 'cylinder' if source_id in (51, 52, 80, 88, 90) else 'sphere',
                    'sphere_center_y_offset_fp09': general['fp09'], 'sphere_radius_fp32': general['fp32'],
                    'cylinder_height_fp11': general['fp11'] if source_id in (51, 52, 80, 88, 90) else None,
                    'cylinder_radius_fp10': general['fp10'] if source_id in (51, 52, 80, 88, 90) else None,
                    'backward_facing_offset': 50 if source_id == 88 else 0,
                    'source_function': 'Game::' + name + '::Obj::getLODCylinder' if source_id in (51, 52, 80, 88, 90) else 'Game::Plants::Obj::setParameters',
                    'source_cull_function': 'Sys::Cylinder::culled' if source_id in (51, 52, 80, 88, 90) else 'CullPlane::isPointVisible'}}
    args.output.joinpath('foliage-bank.txt').write_text('\n'.join(lines) + '\n', encoding='ascii')
    args.output.joinpath('foliage.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    output_hashes = {str(path.relative_to(args.output)): sha(path.read_bytes())
                     for path in sorted(args.output.rglob('*')) if path.is_file()}
    args.output.joinpath('sha256.json').write_text(json.dumps(output_hashes, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': str(args.output), 'species': {
        name: {'source_id': info['source_id'], 'poses': len(info['poses']), 'frames': info['source_frames']}
        for name, info in report['species'].items()}}))


if __name__ == '__main__':
    main()
