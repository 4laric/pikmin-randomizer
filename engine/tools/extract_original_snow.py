"""Build private source45 resources through the established retail converters."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--randomizer-root', type=Path, required=True)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--poses', type=int, default=12)
    args = parser.parse_args()
    if not 2 <= args.poses <= 24:
        parser.error('--poses must be 2..24')
    sys.path.insert(0, str(args.randomizer_root.resolve()))
    from experimental.pikmin2_assets import disc_files, archive_files
    from experimental.pikmin2_enemy import replace_texture_zero
    from experimental.pikmin2_animation import sample_frames, resource_chunks, CLIP_BYTES, TOTAL_BYTES
    from experimental.pikmin2_convert import blocks, convert, u16
    from experimental.pikmin2_purple import bca_pose
    from experimental.pikmin2_snow_policy import parameter_groups
    catalog = disc_files(args.iso)
    hashes = {}
    with args.iso.open('rb') as stream:
        def read(member):
            offset, size = catalog[member]
            stream.seek(offset)
            data = stream.read(size)
            if len(data) != size:
                raise ValueError('Truncated source member: ' + member)
            hashes[member] = hashlib.sha256(data).hexdigest()
            return data
        model = archive_files(read('enemy/data/Kochappy/model.szs'))['enemy.bmd']
        motions = archive_files(read('enemy/data/Kochappy/anim.szs'))
        texture = read('enemy/data/YellowKochappy/kochappy_body_s3tc.2.bti')
        parms = archive_files(read('enemy/parm/enemyParms.szs'))['yellowkochappy/enemyparm.txt']
    groups = parameter_groups(parms.decode('shift_jis'))
    if (groups[1]['fp00'], groups[1]['fp06'], groups[1]['fp38']) != (150, 50, 5):
        raise ValueError('Unsupported retail YellowKochappy parameters')
    args.output.mkdir(parents=True, exist_ok=False)
    model_path = args.output / 'snow.bmd'
    model_path.write_bytes(replace_texture_zero(model, texture))
    joints = u16(blocks(model_path.read_bytes())['JNT1'], 8)
    rows = ['P2_SNOW_BANK_1']
    clips = [('wait1', 75), ('move1', 55), ('attack', 90), ('dead', 90),
             ('flick', 80), ('waitact1', 25), ('type1', 105)]
    reference = None
    total = 0
    file_hashes = {}
    source_clips = {}
    for name, expected_duration in clips:
        clip = motions[name + '.bca']
        duration, _ = bca_pose(clip, 0, joints, allow_scale=True)
        if duration != expected_duration:
            raise ValueError('Unsupported source duration: ' + name)
        frames = sample_frames(duration, args.poses)
        rows.append(f'{name} {len(frames)} {duration} ' + ' '.join(map(str, frames)))
        source_clips[name] = hashlib.sha256(clip).hexdigest()
        clip_bytes = 0
        for index, frame in enumerate(frames):
            _, pose = bca_pose(clip, frame, joints, allow_scale=True)
            destination = args.output / f'snow_{name}_{index:02}.mod'
            convert(model_path, destination, True, bake_rigid=True, pose=pose)
            data = destination.read_bytes()
            resources = resource_chunks(data)
            if reference is not None and reference != resources:
                raise ValueError('Snow immutable bank resources differ')
            reference = resources
            clip_bytes += len(data)
            total += len(data)
            if clip_bytes > CLIP_BYTES or total > TOTAL_BYTES:
                raise ValueError('Snow resource budget exceeded')
            file_hashes[destination.name] = hashlib.sha256(data).hexdigest()
    bank = '\n'.join(rows) + '\n'
    (args.output / 'p2-snow.txt').write_text(bank, encoding='ascii')
    file_hashes['p2-snow.txt'] = hashlib.sha256(bank.encode('ascii')).hexdigest()
    report = {'schema': 1, 'source_id': 45, 'species': 'YellowKochappy',
              'source_sha256': hashes, 'source_animation_sha256': source_clips,
              'parameter_sha256': hashlib.sha256(parms).hexdigest(),
              'parameters': groups, 'file_sha256': file_hashes, 'mod_bytes': total}
    (args.output / 'snow-source.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'source_id': 45, 'poses': len(file_hashes) - 1, 'mod_bytes': total}))


if __name__ == '__main__':
    main()
