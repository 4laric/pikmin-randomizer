"""Dwarf Bulbear (KumaKochappy) sampled pose bank; placement is supplied by the caller.

Builds a deterministic rigid pose bank from an audited
pikmin2_dwarf_bear_profile extraction. Sampled frames always include the
source animation event frames and loop boundary so event timing survives
sampling. No native installation in this batch.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

from experimental.pikmin2_animation import CLIPS, CLIP_BYTES, TOTAL_BYTES, parse_bank as parse_timing, resource_chunks, sample_frames
from experimental.pikmin2_convert import blocks, convert, u16
from experimental.pikmin2_purple import bca_pose

HEADER = 'P2_DWARF_BEAR_BANK_1'
PROFILE = 'P2_DWARF_BEAR_PROFILE_1\nspecies KumaKochappy\nhealth 500\n'
MODEL = 'dwarf-bear.bmd'
PROFILE_JSON = 'dwarf-bear-profile.json'
BANK_JSON = 'dwarf-bear-bank.json'
BANK_TXT = 'p2-dwarf-bear-bank.txt'
PROFILE_TXT = 'p2-dwarf-bear-profile.txt'
POSE_PREFIX = 'dwarf_bear'


def event_frames(events, clip):
    """Source event frame numbers for one clip (visual and gameplay events alike)."""
    return [e['frame'] for e in events.get(clip + '.bca', [])]


def sample_with_events(duration, events, limit):
    """Even samples plus every in-range source event frame, bounded and ordered."""
    frames = set(sample_frames(duration, limit))
    frames.update(f for f in events if 0 <= f < duration)
    frames.add(0)
    frames.add(duration - 1)
    if len(frames) > 24:
        raise ValueError('Event-preserving sample exceeds pose limit')
    return sorted(frames)


def parse_bank(text):
    tokens = text.split()
    if not tokens or tokens[0] != HEADER:
        raise ValueError('Expected Dwarf Bulbear bank')
    return parse_timing('P2_SNOW_2 ' + ' '.join(tokens[1:]))


def validate_files(directory, bank):
    paths = []
    total = 0
    reference = None
    for name, info in bank.items():
        count = 0
        for index in range(info['poses']):
            path = directory / f'{POSE_PREFIX}_{name}_{index:02}.mod'
            size = path.stat().st_size
            count += size
            total += size
            if not size or count > CLIP_BYTES or total > TOTAL_BYTES:
                raise ValueError('Dwarf Bulbear bank exceeds byte budget')
            resources = resource_chunks(path.read_bytes())
            if reference is not None and resources != reference:
                raise ValueError('Dwarf Bulbear materials/textures differ between poses')
            reference = resources
            paths.append(path)
    return paths, total


def build(imported, output, pose_limit=12):
    if type(pose_limit) is not int or not 2 <= pose_limit <= 24:
        raise ValueError('Expected 2..24 pose limit')
    reference = json.loads((imported / PROFILE_JSON).read_text())
    if reference.get('schema') != 1 or reference.get('species') != 'KumaKochappy':
        raise ValueError('Expected KumaKochappy reference import')
    model = imported / MODEL
    data = model.read_bytes()
    if hashlib.sha256(data).hexdigest() != reference['exported_model_sha256']:
        raise ValueError('Reference model hash mismatch')
    events = reference['shared_animation_events']
    motions = {}
    for name in CLIPS:
        clip = (imported / 'source-animation' / (name + '.bca')).read_bytes()
        if hashlib.sha256(clip).hexdigest() != reference['shared_animation_sha256'][name + '.bca']:
            raise ValueError('Reference clip hash mismatch')
        motions[name] = clip
    joints = u16(blocks(data)['JNT1'], 8)
    rows = [HEADER]
    report = {}
    started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    for name, clip in motions.items():
        duration, _ = bca_pose(clip, 0, joints, allow_scale=True)
        frames = sample_with_events(duration, event_frames(events, name), pose_limit)
        rows.append(f'{name} {len(frames)} {duration} ' + ' '.join(map(str, frames)))
        for i, frame in enumerate(frames):
            _, pose = bca_pose(clip, frame, joints, allow_scale=True)
            convert(model, output / f'{POSE_PREFIX}_{name}_{i:02}.mod', True, bake_rigid=True, pose=pose)
        report[name] = {'poses': len(frames), 'source_frames': duration, 'frames': frames,
                        'event_frames': event_frames(events, name)}
    bank = '\n'.join(rows) + '\n'
    paths, total = validate_files(output, parse_bank(bank))
    result = {'schema': 1, 'species': 'KumaKochappy', 'source_id': 76, 'health': 500,
              'motions': report,
              'reference_sha256': hashlib.sha256((imported / PROFILE_JSON).read_bytes()).hexdigest(),
              'file_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'cost': {'poses': sum(v['poses'] for v in report.values()), 'mod_bytes': total,
                       'extract_seconds': time.perf_counter() - started,
                       'clip_budget': CLIP_BYTES, 'total_budget': TOTAL_BYTES},
              'materials': 'Rigid bake with approximate_materials=True; TEV stages approximated, embedded model TEX1 used (no texture replacement).',
              'supported': 'Source KumaKochappy visuals and health 500; deterministic pose bank.',
              'not_implemented': ['P2 FSM/event parity', 'parent-following (ChappyRelation)',
                                  'source Purple stun 5s reaction',
                                  'native installation and arena lifecycle']}
    (output / BANK_JSON).write_text(json.dumps(result, indent=2))
    (output / BANK_TXT).write_text(bank)
    (output / PROFILE_TXT).write_text(PROFILE)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(build(args.imported, args.output, args.pose_limit), indent=2))
