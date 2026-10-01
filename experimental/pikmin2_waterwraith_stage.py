"""Stage Waterwraith/Tyre converted assets for a private runtime visual fixture (#175/#443).

Reads a verified ``pikmin2_waterwraith_assets`` import directory and writes a
bounded stage layout: a two-species visual profile (``P2_WATERWRAITH_VISUAL_1``)
and every converted sampled-pose ``.mod`` laid out for a run overlay
(``assets/dataDir/courses/pikmin2room/``). This prepares the native visual
consumer; it is root-side staging only and claims no actor or gameplay
behavior. Mirrors :mod:`experimental.pikmin2_bigtreasure_stage`.

Profile row grammar (pending native consumer):

    P2_WATERWRAITH_VISUAL_1
    species <name> <enemy_id>
    clip <species> <clip> <poseCount> <sourceFrames> <frame...>
    ...
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

HEADER = 'P2_WATERWRAITH_VISUAL_1'
EXPECTED_TOTAL_CONVERTED_CLIPS = 16  # BlackMan 14 + Tyre 2 (US GPVE01 rev 0)
MAX_STAGE_BYTES = 96 * 1024 * 1024


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def converted_clips(report):
    clips = []
    for species, entry in report['species'].items():
        for clip in entry['clips']:
            if clip['status'] != 'converted':
                continue
            clips.append((species, entry['enemy_id'], clip))
    return clips


def build(imported, output, only_clips=None):
    imported = Path(imported)
    output = Path(output)
    if output.exists():
        raise ValueError('Stage output already exists')
    report = json.loads((imported / 'waterwraith.json').read_bytes())
    if report.get('policy') != 'P2_WATERWRAITH_1':
        raise ValueError('Expected a Waterwraith import report')
    for species, entry in report["species"].items():
        if species not in ("BlackMan", "Tyre"):
            raise ValueError("Unknown Waterwraith species")
        for clip in entry["clips"]:
            for pose in clip.get("poses", []):
                if "file" in pose and not re.fullmatch(r"[A-Za-z0-9_-]+\.mod", pose["file"]):
                    raise ValueError("Unsafe pose filename")
    clips = converted_clips(report)
    names = [name for _species, _id, clip in clips for name in [clip['name']]]
    if only_clips is not None:
        wanted = list(only_clips)
        unknown = [name for name in wanted if name not in names]
        if not wanted or unknown:
            raise ValueError(f'Unknown clips requested: {sorted(unknown)}')
        clips = [row for row in clips if row[2]['name'] in set(wanted)]
    elif len(clips) != EXPECTED_TOTAL_CONVERTED_CLIPS:
        raise ValueError(
            f'Expected {EXPECTED_TOTAL_CONVERTED_CLIPS} converted clips, got {len(clips)}')

    rows = [HEADER]
    copied = {}
    total = 0
    species_counts = {}
    for species, enemy_id, clip in clips:
        poses = [pose for pose in clip['poses'] if 'file' in pose]
        if not poses:
            raise ValueError(f'Clip {species}/{clip["name"]} has no converted poses')
        species_counts.setdefault(species, {'enemy_id': enemy_id, 'clips': 0})
        species_counts[species]['clips'] += 1
        frames = ' '.join(str(pose['frame']) for pose in poses)
        rows.append(f'clip {species} {clip["name"]} {len(poses)} {clip["source_frames"]} {frames}')
        for pose in poses:
            source = imported / species / pose['file']
            data = Path(source).read_bytes()
            if hashlib.sha256(data).hexdigest() != pose['sha256']:
                raise ValueError(f'Pose hash mismatch: {pose["file"]}')
            total += len(data)
            if total > MAX_STAGE_BYTES:
                raise ValueError('Stage byte budget exceeded')
            target = output / 'assets' / 'dataDir' / 'courses' / 'pikmin2room' / pose['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            copied[pose['file']] = pose['sha256']

    profile_rows = [HEADER]
    for species, info in species_counts.items():
        profile_rows.append(f'species {species} {info["enemy_id"]}')
    for row in rows[1:]:
        profile_rows.append(row)
    profile = '\n'.join(profile_rows) + '\n'
    (output / 'p2-waterwraith-visual.txt').write_text(profile)
    copied['p2-waterwraith-visual.txt'] = hashlib.sha256(profile.encode()).hexdigest()
    manifest = {
        'schema': 1,
        'profile': HEADER,
        'species': {name: {'enemy_id': info['enemy_id'], 'clips': info['clips']}
                    for name, info in species_counts.items()},
        'clips': len(clips),
        'clip_subset': sorted(only_clips) if only_clips is not None else None,
        'poses': sum(len([p for p in clip['poses'] if 'file' in p])
                     for _s, _i, clip in clips),
        'file_sha256': copied,
        'limitations': [
            'Baked sampled poses with approximate materials; no skeletal playback.',
            'No retail event table or native visual consumer is wired yet; the profile is staging data.',
            'BlackMan (boss) and Tyre (dependent roller) are staged independently; ownership/phases are the native policy lane.',
        ],
    }
    (output / 'stage.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clips', type=str, default=None,
                        help='comma-separated clip subset for the runtime stage (default: all)')
    args = parser.parse_args(argv)
    result = build(args.imported, args.output,
                   args.clips.split(',') if args.clips else None)
    print(json.dumps({'clips': result['clips'], 'poses': result['poses'],
                      'species': {k: v['clips'] for k, v in result['species'].items()}},
                     indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
