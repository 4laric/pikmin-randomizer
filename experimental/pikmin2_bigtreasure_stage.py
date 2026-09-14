"""Stage BigTreasure converted assets + visual profile for the private runtime fixture (#246).

Reads a verified ``pikmin2_bigtreasure_assets`` import directory, regenerates
the retail motion event table, and writes a bounded stage directory: the
visual profile (P2_BIGTREASURE_VISUAL_1), the event table, and every
converted pose/pellet .mod laid out for the run overlay
(assets/dataDir/courses/pikmin2room/). Pellets whose model is unsupported by
the restricted converter (currently loozy, shape matrix type 1) are declared
``pellet_debug`` rows instead of being fabricated.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from experimental import pikmin2_bigtreasure_motion as motion

HEADER = 'P2_BIGTREASURE_VISUAL_1'
MAX_STAGE_BYTES = 96 * 1024 * 1024


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(imported, output, only_clips=None):
    imported = Path(imported)
    output = Path(output)
    if output.exists():
        raise ValueError('Stage output already exists')
    report = json.loads((imported / 'bigtreasure.json').read_bytes())
    if report.get('policy') != 'P2_BIGTREASURE_IMPORT_1':
        raise ValueError('Expected a BigTreasure import report')
    boss = report['boss']
    clips = [c for c in boss['clips'] if c['status'] == 'converted']
    if len(clips) != 29:
        raise ValueError(f'Expected 29 converted clips, got {len(clips)}')
    if only_clips is not None:
        wanted = set(only_clips)
        if not wanted or any(c['name'] not in wanted for c in clips if c['name'] in wanted) \
                or any(name not in {c['name'] for c in clips} for name in wanted):
            raise ValueError(f'Unknown clips requested: {sorted(wanted)}')
        clips = [c for c in clips if c['name'] in wanted]
    transforms = boss['capture_transforms']
    rows = [HEADER, 'events p2_bigtreasure_events.txt']
    copied = {}
    total = 0

    def place(source, name):
        nonlocal total
        data = Path(source).read_bytes()
        total += len(data)
        if total > MAX_STAGE_BYTES:
            raise ValueError('Stage byte budget exceeded')
        target = output / 'assets' / 'dataDir' / 'courses' / 'pikmin2room' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        copied[name] = hashlib.sha256(data).hexdigest()

    for clip in clips:
        poses = [p for p in clip['poses'] if 'file' in p]
        if not poses:
            raise ValueError(f'Clip {clip["name"]} has no converted poses')
        for pose in poses:
            source = imported / 'BigTreasure' / pose['file']
            if sha(source) != pose['sha256']:
                raise ValueError(f'Pose hash mismatch: {pose["file"]}')
            place(source, pose['file'])
        frames = ' '.join(str(p['frame']) for p in poses)
        rows.append(f'clip {clip["name"]} {len(poses)} {clip["source_frames"]} {frames}')
    pellet_debug = []
    for name, entry in sorted(report['pellet_models'].items()):
        joint = {'elec': 'otakara_elec', 'fire': 'otakara_fire', 'gas': 'otakara_gas',
                 'water': 'otakara_water', 'loozy': 'otakara_loozy'}[name]
        if entry['status'] != 'converted':
            pellet_debug.append((name, entry.get('unsupported_reason', 'unknown')))
            rows.append(f'pellet_debug {name} {joint}')
            continue
        source = imported / 'pellets' / entry['file']
        if sha(source) != entry['sha256']:
            raise ValueError(f'Pellet hash mismatch: {name}')
        place(source, entry['file'])
        matrix = transforms[joint]
        values = ' '.join(f'{v:.6g}' for row in matrix for v in row)
        rows.append(f'pellet {name} {entry["file"]} {joint} {values}')
    events = motion.encode(imported / 'BigTreasure', imported / 'bigtreasure.json')
    (output / 'p2_bigtreasure_events.txt').write_bytes(events)
    copied['p2_bigtreasure_events.txt'] = hashlib.sha256(events).hexdigest()
    profile = '\n'.join(rows) + '\n'
    (output / 'p2-bigtreasure-visual.txt').write_text(profile)
    copied['p2-bigtreasure-visual.txt'] = hashlib.sha256(profile.encode()).hexdigest()
    manifest = {'schema': 1, 'profile': HEADER, 'clips': len(clips),
                'clip_subset': sorted(only_clips) if only_clips is not None else None,
                'poses': sum(len([p for p in c['poses'] if 'file' in p]) for c in clips),
                'pellets_converted': sum(1 for r in rows if r.startswith('pellet ')),
                'pellet_debug': [{'name': n, 'reason': r} for n, r in pellet_debug],
                'file_sha256': copied,
                'limitations': ['Baked sampled poses with approximate materials; no skeletal playback.',
                                'Pellet attachment uses bind-pose joint transforms; pellets do not track animated joints.',
                                'loozy (King of Bugs) model uses an unsupported shape matrix type and stays a debug marker.']}
    (output / 'stage.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clips', type=str, default=None,
                        help='comma-separated clip subset for the runtime stage (default: all 29)')
    args = parser.parse_args()
    result = build(args.imported, args.output,
                   args.clips.split(',') if args.clips else None)
    print(json.dumps({'clips': result['clips'], 'poses': result['poses'],
                      'pellets_converted': result['pellets_converted'],
                      'pellet_debug': [p['name'] for p in result['pellet_debug']]}, indent=2))
