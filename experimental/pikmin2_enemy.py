"""Local-disc Snow Bulborb assets; sampled source animation, P1 behavior scaffold."""
import argparse
import hashlib
import json
import struct
import time
from pathlib import Path
from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_convert import blocks, convert, u32, u16, texture_layout
from experimental.pikmin2_purple import bca_pose

SPECIES = 'YellowKochappy'
from experimental.pikmin2_animation import CLIPS, sample_frames, parse_bank, validate_files, CLIP_BYTES, TOTAL_BYTES

def replace_texture_zero(model, texture):
    """Match YellowKochappy::Obj::changeMaterial's image slot zero replacement."""
    b = blocks(model)
    if len(texture) < 32 or texture[8]:
        raise ValueError('Expected non-paletted BTI')
    _, size = texture_layout(texture[0], u16(texture, 2), u16(texture, 4))
    start = u32(texture, 28)
    if start < 32 or start + size > len(texture):
        raise ValueError('Truncated BTI')
    t = bytearray(b['TEX1'])
    if u16(t, 8) < 1:
        raise ValueError('Missing image slot zero')
    header = u32(t, 12)
    if header < 20 or header + 32 > len(t):
        raise ValueError('Invalid texture header')
    at = len(t)
    t[header:header+32] = texture[:32]
    struct.pack_into('>I', t, header+28, at-header)
    t.extend(texture[start:start+size])
    t.extend(bytes((-len(t)) % 32))
    struct.pack_into('>I', t, 4, len(t))
    b['TEX1'] = bytes(t)
    result = bytearray(model[:32] + b''.join(b.values()))
    struct.pack_into('>I', result, 8, len(result))
    return bytes(result)

def extract(iso, output, pose_limit=24):
    started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    catalog = disc_files(iso)
    hashes = {}
    with iso.open('rb') as disc:
        def read(path):
            offset, size = catalog[path]
            disc.seek(offset)
            data = disc.read(size)
            hashes[path] = hashlib.sha256(data).hexdigest()
            return data
        model = archive_files(read('enemy/data/Kochappy/model.szs'))['enemy.bmd']
        motions = archive_files(read('enemy/data/Kochappy/anim.szs'))
        texture = read('enemy/data/YellowKochappy/kochappy_body_s3tc.2.bti')
    model = replace_texture_zero(model, texture)
    path = output/'snow.bmd'
    path.write_bytes(model)
    joints = u16(blocks(model)['JNT1'], 8)
    rows = ['P2_SNOW_2']
    report = {}
    for name in CLIPS:
        clip = motions[name+'.bca']
        duration, _ = bca_pose(clip, 0, joints, allow_scale=True)
        frames = sample_frames(duration, pose_limit)
        count = len(frames)
        rows.append(f'{name} {count} {duration} ' + ' '.join(map(str, frames)))
        for i in range(count):
            # Include final death pose rather than looping short of it.
            frame = frames[i]
            _, pose = bca_pose(clip, frame, joints, allow_scale=True)
            convert(path, output/f'snow_{name}_{i:02}.mod', True, bake_rigid=True, pose=pose)
        report[name] = {'source_frames': duration, 'poses': count, 'frames': frames, 'sha256': hashlib.sha256(clip).hexdigest()}
    (output/'p2-snow.txt').write_text('\n'.join(rows)+'\n')
    _, mod_bytes = validate_files(output, parse_bank('\n'.join(rows)))
    result = {'schema': 1, 'species': SPECIES, 'source_sha256': hashes, 'joints': joints, 'motions': report,
              'animation_version': 2,
              'cost': {'mod_bytes': mod_bytes, 'clip_budget_bytes': CLIP_BYTES, 'total_budget_bytes': TOTAL_BYTES,
                       'extract_seconds': round(time.perf_counter()-started, 3),
                       'extract_advisory_seconds': 30, 'load_advisory_seconds': 5,
                       'legacy_pose_count': 60, 'pose_count': sum(x['poses'] for x in report.values())},
              'limitations': ['P1 dwarf combat, collision and animation event timing remain in use.',
                              'Sampled source poses; no source skeletal animation runtime or blending.']}
    (output/'snow.json').write_text(json.dumps(result, indent=2))
    return result

def install(imported, run, generator_ids):
    """Opt in selected native Chappy instances; caller owns floor-scoped placement IDs."""
    import shutil
    ids=list(generator_ids)
    if not ids or len(ids)>100 or len(set(ids))!=len(ids) or any(type(i)!=int or not 0<=i<=0xffffffff for i in ids):
        raise ValueError('Expected unique unsigned generator IDs')
    metadata=json.loads((imported/'snow.json').read_text())
    if metadata.get('schema')!=1 or metadata.get('species')!=SPECIES:
        raise ValueError('Expected Snow Bulborb import')
    destination=run/'assets/dataDir/courses/pikmin2room'
    # Overlay creates junction-backed base assets; this room itself is private.
    if not destination.is_dir():raise ValueError('Expected prepared private room')
    bank = parse_bank((imported/'p2-snow.txt').read_text())
    for name, info in bank.items():
        if any(metadata['motions'][name].get(key) != info[key] for key in ('poses', 'source_frames')):
            raise ValueError('Snow metadata and animation config disagree')
        if info['frames'] is not None and metadata['motions'][name].get('frames') != info['frames']:
            raise ValueError('Snow source frame metadata disagrees')
    paths, _ = validate_files(imported, bank)
    for path in paths:shutil.copyfile(path,destination/path.name)
    shutil.copyfile(imported/'p2-snow.txt',run/'p2-snow.txt')
    (run/'p2-snow-actors.txt').write_text('P2_SNOW_ACTORS_1 '+str(len(ids))+'\n'+'\n'.join(map(str,ids))+'\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=24, choices=range(2,25))
    args = parser.parse_args()
    print(json.dumps(extract(args.iso, args.output, args.pose_limit), indent=2))

