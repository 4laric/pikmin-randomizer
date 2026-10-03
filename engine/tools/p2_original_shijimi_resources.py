"""Convert genuine source77 geometry and mechanical joint-zero samples privately."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

def sha(data):
    return hashlib.sha256(data).hexdigest()

EXPECTED_ARCHIVES = {
    'enemy/parm/enemyParms.szs': '3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84',
    'enemy/data/ShijimiChou/model.szs': '525e530c17fa8fd89883e4573af0fe068e00d9bac269952bed0c02b3d53d712b',
    'enemy/data/ShijimiChou/anim.szs': '0153ee36514e45abbb939e56a93f3185ccd323a3c4fba8bcce86ab6367a71c25',
}
EXPECTED_CLIPS = (
    ('carry', 40, [[10, 0], [29, 1]], '0dfce9a247fa223efc536f0766c0feb1cef338f0873bfc72576b5d9be3c4366e'),
    ('dead', 61, [], 'f74878b24c8813b46a9d29b89624362e0b611e8a1548f1fe7e87b0b4bddd8a52'),
    ('move', 8, [[0, 0], [7, 1]], '45004202a8e74994f3cebc1f6a234a08f667f0de4432b7e0f8e388ef1f17f381'),
)

def convert(args):
    sys.path.insert(0, str(args.randomizer_root.resolve()))
    from experimental import pikmin2_flying_assets as importer
    from experimental.pikmin2_purple import bca_pose
    from experimental.pikmin2_assets import disc_files
    # Check all inputs before conversion; this entry does not import other
    # flying species or invoke their install/staging paths.
    with args.iso.open('rb') as disc:
        index = disc_files(args.iso)
        for member, digest in EXPECTED_ARCHIVES.items():
            offset, size = index[member]
            disc.seek(offset)
            data = disc.read(size)
            if len(data) != size or sha(data) != digest:
                raise ValueError('original source77 archive changed: ' + member)
    importer.SPECIES = {'ShijimiChou': 77}
    receipt = importer.extract(args.iso, args.source, args.output, args.pose_limit)
    species = receipt['species']['ShijimiChou']
    if receipt['source_sha256'] != EXPECTED_ARCHIVES or species['joints'] != ['center', 'Lhane', 'Rhane'] or len(species['clips']) != 3:
        raise ValueError('original source77 source/rig changed')
    expected_collision = [
        {'parent': None, 'radius': 30., 'id': 'none', 'code': '____', 'offset': [0., 0., 0.], 'joint': 0, 'attribute': 0},
        {'parent': 0, 'radius': 20., 'id': 'none', 'code': 'st__', 'offset': [0., 0., 0.], 'joint': 0, 'attribute': 0},
    ]
    if species['collision'] != expected_collision:
        raise ValueError('original source77 collision tree changed')
    leaf = args.output / 'ShijimiChou'
    events = ['P2_RETAIL_EVENTS_1 ' + species['metadata_sha256']['enemyanimmgr.txt'] + ' 3']
    joints = ['P2_ORIGINAL_SHIJIMI_JOINT0_1 3']
    rows = []
    for clip, (name, duration, keys, digest) in zip(species['clips'], EXPECTED_CLIPS):
        if (clip['name'], clip['source_frames'], clip['events'], clip['source_sha256'], clip['loop_attribute']) != (name, duration, keys, digest, 2):
            raise ValueError('original source77 motion identity changed: ' + name)
        raw = (leaf / (name + '.bca')).read_bytes()
        if sha(raw) != digest:
            raise ValueError('original source77 raw BCA changed: ' + name)
        if any('file' not in pose for pose in clip['poses']):
            raise ValueError('original source77 conversion incomplete: ' + name)
        events.append(f'{name}.bca {duration} 2 {digest} {len(keys)}')
        events.extend(f'{frame} {kind}' for frame, kind in keys)
        joints.append(f'{name} {duration}')
        # BCA full transforms index their integer frame. Mechanical collision
        # uses every original sample, independent of render pose sampling.
        for frame in range(duration):
            matrix = bca_pose(raw, frame, 3, allow_scale=True)[1][0]
            joints.append(' '.join(format(value, '.9g') for row in matrix for value in row))
        poses = clip['poses']
        rows.append(f'clip {name} {len(poses)} {duration} fly_ShijimiChou_{name} ' + ' '.join(str(p['frame']) for p in poses))
        rows.append(' '.join(p['sha256'] for p in poses))
    event_bytes = ('\n'.join(events) + '\n').encode('ascii')
    joint_bytes = ('\n'.join(joints) + '\n').encode('ascii')
    (args.output / 'p2-original-shijimi-events.txt').write_bytes(event_bytes)
    (args.output / 'p2-original-shijimi-joint0.txt').write_bytes(joint_bytes)
    bank = ['P2_ORIGINAL_SHIJIMI_BANK_1 ' + sha((args.output / 'flying.json').read_bytes()) + ' ' + sha(event_bytes) + ' ' + sha(joint_bytes), *rows]
    (args.output / 'p2-original-shijimi-bank.txt').write_text('\n'.join(bank) + '\n', encoding='ascii')
    return {'poses': receipt['total_poses'], 'mechanical_joint_frames': 109,
            'native_gameplay': False, 'bank_sha256': sha((args.output / 'p2-original-shijimi-bank.txt').read_bytes())}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--randomizer-root', type=Path, required=True)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=10)
    print(json.dumps(convert(parser.parse_args())))
