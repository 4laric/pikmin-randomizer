"""Separate Bulblax family motion bank built from the #217 import; no native actor install.

Re-reads the bounded Bulblax import (``bulblax.json`` report + ``p2-bulblax.txt``
profile) from an import directory, verifies the SHA-256 of every species model
and every source clip against the recorded hashes, then re-samples and converts
poses deterministically:

- Queen (enemy 30, weighted EVP1): baked with explicit
  ``pikmin2_skinning.draw_matrices`` exactly like the assets module. Frames the
  converter rejects (singular normal transform on ``dead``/``carry``) are
  skipped and recorded as unsupported entries, never approximated.
- Baby (enemy 31, rigid EVP1 0): baked with the joint pose, all 6 clips.
- KingChappy (enemy 53): every clip is enumerated as a ``blocked`` entry
  referencing the converter limitation (shape 0 display list omits the normal
  attribute while VTX1 carries normals); no pose is ever fabricated.

Issue #223 (parent #172).
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

from experimental import pikmin2_animation as animation
from experimental.pikmin2_animation import resource_chunks, sample_frames
from experimental.pikmin2_bulblax_assets import CLIPS, SPECIES, TEXT
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices

HEADER = 'P2_BULBLAX_BANK_1'
CLIP_BYTES = 1024 * 1024        # per-clip pose budget (Queen poses are ~60 KB each)
TOTAL_BYTES = 16 * 1024 * 1024  # whole-bank budget across all three species
MAX_POSES = 12

LIMITATIONS = ['Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
               'Queen dead/carry frames with a singular normal transform are recorded unsupported, never approximated.',
               'All KingChappy clips are blocked: shape 0 omits the normal attribute in its display list (VTX1 normal array exists) and the existing rigid/weighted bake requires per-vertex normals; poses are never fabricated.',
               'No native runtime, AI/FSM, install or arena placement is provided by this slice.']


def parse_bank(text):
    """Parse a Bulblax bank with Snow-style bounds per species.

    Unlike the Snow parser, converted frames need not span 0..duration-1:
    unsupported frames (e.g. Queen singular-normal dead frames) are skipped,
    so only strict ordering and range bounds are enforced here.
    """
    tokens = text.split()
    if not tokens or tokens[0] != HEADER:
        raise ValueError('Expected separate Bulblax bank')
    at = 1
    result = {}
    while at < len(tokens):
        species = tokens[at]
        at += 1
        if species not in CLIPS or species in result:
            raise ValueError('Invalid Bulblax bank species')
        try:
            count = int(tokens[at])
        except (IndexError, ValueError) as exc:
            raise ValueError('Truncated Bulblax bank') from exc
        at += 1
        if not 0 <= count <= len(CLIPS[species]):
            raise ValueError('Invalid Bulblax bank clip count')
        names = []
        clips = {}
        for _ in range(count):
            name = tokens[at] if at < len(tokens) else ''
            if name not in CLIPS[species] or name in names:
                raise ValueError('Invalid Bulblax bank clip order')
            names.append(name)
            try:
                poses, duration = int(tokens[at + 1]), int(tokens[at + 2])
                frames = [int(t) for t in tokens[at + 3:at + 3 + poses]]
            except (IndexError, ValueError) as exc:
                raise ValueError('Truncated Bulblax bank') from exc
            if len(frames) != poses or not 1 <= poses <= animation.MAX_POSES \
                    or not 1 <= duration <= 10000:
                raise ValueError('Invalid Bulblax clip bounds')
            if any(not 0 <= f < duration for f in frames) or \
                    any(a >= b for a, b in zip(frames, frames[1:])):
                raise ValueError('Invalid Bulblax source frames')
            clips[name] = {'poses': poses, 'source_frames': duration, 'frames': frames}
            at += 3 + poses
        if names != [n for n in CLIPS[species] if n in names]:
            raise ValueError('Bulblax bank clips out of registration order')
        result[species] = clips
    return result


def validate_files(directory, bank):
    paths = []
    total = 0
    for species, clips in bank.items():
        reference = None
        for name, info in clips.items():
            clip_bytes = 0
            for index in range(info['poses']):
                path = directory / species / f'bulblax_{species}_{name}_{index:02}.mod'
                size = path.stat().st_size
                clip_bytes += size
                total += size
                if not size or clip_bytes > CLIP_BYTES or total > TOTAL_BYTES:
                    raise ValueError('Bulblax bank exceeds byte budget')
                resources = resource_chunks(path.read_bytes())
                if reference is not None and reference != resources:
                    raise ValueError(f'{species} materials/textures differ between poses')
                reference = resources
                paths.append(path)
    return paths, total


def _verified(reference):
    if reference.get('schema') != 1 or reference.get('policy') != 'P2_BULBLAX_IMPORT_1':
        raise ValueError('Expected Bulblax reference import')
    if set(reference.get('species', {})) != set(SPECIES):
        raise ValueError('Incomplete Bulblax reference import')


def _convert_pose(model, model_blocks, envelopes, joint_count, clip, frame, output):
    duration, pose = bca_pose(clip, frame, joint_count, allow_scale=True)
    matrices = draw_matrices(model_blocks, pose) if envelopes else None
    decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices) \
        if matrices is not None else decode(model, True, bake_rigid=True, pose=pose)
    conversion = write_model(decoded, output, 'enemy.bmd')
    conversion.update(source='enemy.bmd', output=output.name, weighted_pose_baked=matrices is not None)
    return conversion


def build(imported, output, pose_limit=6):
    if type(pose_limit) is not int or not 2 <= pose_limit <= MAX_POSES:
        raise ValueError(f'Pose limit must be 2..{MAX_POSES}')
    if output.exists():
        raise ValueError('Output already exists')
    report_bytes = (imported / 'bulblax.json').read_bytes()
    reference = json.loads(report_bytes)
    _verified(reference)
    if (imported / 'p2-bulblax.txt').read_text().split() != TEXT.split():
        raise ValueError('Unsupported Bulblax import profile')
    started = time.perf_counter()
    verified = {}
    for species in SPECIES:  # verify every hash before any output is written
        info = reference['species'][species]
        root = imported / species
        model = (root / 'enemy.bmd').read_bytes()
        if hashlib.sha256(model).hexdigest() != info['model_sha256']:
            raise ValueError(f'{species} reference model hash mismatch')
        clips = {}
        for clip in info['clips']:
            raw = (root / (clip['name'] + '.bca')).read_bytes()
            if hashlib.sha256(raw).hexdigest() != clip['source_sha256']:
                raise ValueError(f'{species} reference clip hash mismatch')
            clips[clip['name']] = raw
        verified[species] = (model, clips)
    rows = [HEADER]
    motions = {}
    unsupported = {}
    blocked = {}
    totals = {'poses': 0, 'mod_bytes': 0}
    output.mkdir(parents=True)
    for species in SPECIES:
        info = reference['species'][species]
        model, clip_data = verified[species]
        model_blocks = blocks(model)
        envelopes = info['skinning']['envelopes']
        if (envelopes > 0) != info['skinning']['weighted_baking']:
            raise ValueError(f'{species} skinning metadata mismatch')
        species_rows = []
        motions[species] = {}
        unsupported[species] = []
        blocked[species] = []
        for clip in info['clips']:
            name = clip['name']
            raw = clip_data[name]
            if species == 'KingChappy':
                # Converter limitation (shape 0 display list omits the normal
                # attribute); enumerate, never fabricate. See LIMITATIONS.
                blocked[species].append({'clip': name, 'source_frames': clip['source_frames'],
                                         'reason': clip.get('unsupported_reason',
                                                            'shape display list omits normal attribute')})
                continue
            duration, _ = bca_pose(raw, 0, len(info['joints']), allow_scale=True)
            if duration != clip['source_frames']:
                raise ValueError(f'{species} clip {name} duration mismatch')
            frames = sample_frames(duration, pose_limit)
            converted = 0
            clip_bytes = 0
            for frame in frames:
                try:
                    path = output / species / f'bulblax_{species}_{name}_{converted:02}.mod'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    conversion = _convert_pose(model, model_blocks, envelopes,
                                               len(info['joints']), raw, frame, path)
                    (path.with_suffix('.json')).write_text(json.dumps(conversion, indent=2))
                    clip_bytes += path.stat().st_size
                    converted += 1
                except (ValueError, KeyError, ArithmeticError) as error:
                    # Converter limitation (e.g. singular normal transform);
                    # recorded, never fabricated.
                    unsupported[species].append({'clip': name, 'frame': frame,
                                                 'unsupported_reason': f'{type(error).__name__}: {error}'})
            if converted:
                species_rows.append(f'{name} {converted} {duration} '
                                    + ' '.join(str(f) for f in frames
                                               if not any(u['clip'] == name and u['frame'] == f
                                                          for u in unsupported[species])))
                motions[species][name] = {'poses': converted, 'source_frames': duration,
                                          'frames': [f for f in frames
                                                     if not any(u['clip'] == name and u['frame'] == f
                                                                for u in unsupported[species])],
                                          'mod_bytes': clip_bytes}
        rows.append(f'{species} {len(species_rows)}')
        rows.extend(species_rows)
    bank = '\n'.join(rows) + '\n'
    parsed = parse_bank(bank)
    if parsed != {s: {n: {k: v for k, v in m.items() if k != 'mod_bytes'} for n, m in motions[s].items()}
                  for s in motions}:
        raise ValueError('Bulblax bank round-trip mismatch')
    paths, total = validate_files(output, parsed)
    totals['poses'] = sum(m['poses'] for s in motions.values() for m in s.values())
    totals['mod_bytes'] = total
    result = {'schema': 1, 'bank': HEADER,
              'reference_sha256': hashlib.sha256(report_bytes).hexdigest(),
              'motions': motions,
              'unsupported': {s: u for s, u in unsupported.items()},
              'blocked': {s: b for s, b in blocked.items()},
              'file_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'cost': {'poses': totals['poses'], 'mod_bytes': totals['mod_bytes'],
                       'extract_seconds': time.perf_counter() - started,
                       'clip_budget': CLIP_BYTES, 'total_budget': TOTAL_BYTES},
              'limitations': list(LIMITATIONS)}
    (output / 'bulblax-bank.json').write_text(json.dumps(result, indent=2))
    (output / 'p2-bulblax-bank.txt').write_text(bank)
    (output / 'p2-bulblax.txt').write_text(TEXT)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=6)
    args = parser.parse_args()
    result = build(args.imported, args.output, args.pose_limit)
    print(json.dumps({'poses': result['cost']['poses'], 'mod_bytes': result['cost']['mod_bytes'],
                      'seconds': result['cost']['extract_seconds'],
                      'species': {s: {'clips': len(result['motions'][s]),
                                      'poses': sum(m['poses'] for m in result['motions'][s].values()),
                                      'mod_bytes': sum(m['mod_bytes'] for m in result['motions'][s].values()),
                                      'unsupported': len(result['unsupported'][s]),
                                      'blocked': len(result['blocked'][s])}
                                  for s in SPECIES}}, indent=2))
