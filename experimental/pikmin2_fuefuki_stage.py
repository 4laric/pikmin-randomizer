"""Stage the converted Fuefuki pose bank + visual profile for the private runtime (#245).

Reads a verified ``pikmin2_fuefuki_assets`` import directory and writes a bounded
stage directory: the visual profile (``P2_FUEFUKI_VISUAL_1``) and every
converted pose ``.mod`` laid out for the run overlay
(``assets/dataDir/courses/pikmin2room/``). Unsupported clips
(``landing``/``landfail``) are simply absent from the profile; nothing is
fabricated.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental import pikmin2_fuefuki_motion as motion

HEADER = 'P2_FUEFUKI_VISUAL_1'
MOTION_FILE = 'p2-fuefuki-motion.txt'
MAX_STAGE_BYTES = 32 * 1024 * 1024


def build(imported, output):
    imported = Path(imported)
    output = Path(output)
    if output.exists():
        raise ValueError('Stage output already exists')
    report = json.loads((imported / 'fuefuki.json').read_bytes())
    if report.get('policy') != 'P2_FUEFUKI_IMPORT_1':
        raise ValueError('Expected a Fuefuki import report')
    species = report['species']['Fuefuki']
    clips = [clip for clip in species['clips'] if clip['status'] == 'converted']
    if not clips:
        raise ValueError('No converted Fuefuki clips')
    rows = [HEADER]
    copied = {}
    total = 0

    def place(source, name):
        nonlocal total
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
            raise ValueError('Unsafe staged filename')
        data = Path(source).read_bytes()
        total += len(data)
        if total > MAX_STAGE_BYTES:
            raise ValueError('Stage byte budget exceeded')
        target = output / 'assets' / 'dataDir' / 'courses' / 'pikmin2room' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        copied[name] = hashlib.sha256(data).hexdigest()

    for clip in clips:
        poses = [pose for pose in clip['poses'] if 'file' in pose]
        if not poses:
            raise ValueError(f'Clip {clip["name"]} has no converted poses')
        for pose in poses:
            source = imported / 'Fuefuki' / pose['file']
            if hashlib.sha256(source.read_bytes()).hexdigest() != pose['sha256']:
                raise ValueError(f'Pose hash mismatch: {pose["file"]}')
            place(source, pose['file'])
        frames = ' '.join(str(pose['frame']) for pose in poses)
        rows.append(f'clip {clip["name"]} {len(poses)} {clip["source_frames"]} {frames}')

    profile = '\n'.join(rows) + '\n'
    (output / 'p2-fuefuki-visual.txt').write_text(profile)
    copied['p2-fuefuki-visual.txt'] = hashlib.sha256(profile.encode()).hexdigest()
    events = motion.encode(imported / 'Fuefuki', imported / 'fuefuki.json')
    (output / MOTION_FILE).write_bytes(events)
    copied[MOTION_FILE] = hashlib.sha256(events).hexdigest()
    manifest = {
        'schema': 1, 'profile': HEADER, 'motion_file': MOTION_FILE, 'clips': len(clips),
        'poses': sum(1 for clip in clips for pose in clip['poses'] if 'file' in pose),
        'unsupported_clips': [clip['name'] for clip in species['clips']
                              if clip['status'] != 'converted'],
        'file_sha256': copied,
        'limitations': [
            'Baked sampled rigid poses with approximate materials; no skeletal playback.',
            'landing/landfail are absent (singular source joint scale); nothing fabricated.',
            'No whistle effect ring, audio or camera-facing billboard orientation.',
        ],
    }
    (output / 'stage.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.imported, args.output)
    print(json.dumps({'clips': result['clips'], 'poses': result['poses'],
                      'unsupported': result['unsupported_clips']}, indent=2))
