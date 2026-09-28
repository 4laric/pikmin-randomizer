"""Source-backed, bounded Fuefuki (Antenna Beetle, ID 41) import; no native actor install.

Lane #245, converter handoff #128. Modeled on ``pikmin2_bombsarai_assets.py``
and ``pikmin2_flying_assets.py``. Source audit:
``native/tools/P2_FUEFUKI_AUDIT.md`` (projectPiki/pikmin2 revision
632af93787b9c95b63f0c13be32b161375ce3a96, US GPVE01 rev 0). Reads the private disc
copy through the shared read-only ``experimental.pikmin2_assets`` helpers and
writes a schema-1 ``P2_FUEFUKI_IMPORT_1`` manifest (``fuefuki.json``) plus the
sampled ``Fuefuki/*.mod`` pose bank.

This is an inventory/proof-of-concept extractor: bounded sampled rigid poses
with approximate materials, no btk playback, no skeletal animation runtime and
no behavior execution. The Fuefuki mesh shape-matrix types are recorded per
clip through the conversion results; the explicit ``billboard='static'``
fallback (shared with the BombSarai hard lane) bakes authored billboard
geometry through its rigid draw matrix and records the policy.
"""
import argparse
import hashlib
import json
import math
import struct
import time
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_sheargrub_assets import joints, animation_rows
from experimental.pikmin2_breadbug_assets import parameter_blocks, collision_nodes
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

SPECIES = 'Fuefuki'
ENEMY = 'Fuefuki'
ENEMY_ID = 41
POLICY = 'P2_FUEFUKI_IMPORT_1'
DISC_ID = 'GPVE01'
DISC_REVISION = 0
SOURCE_REVISION = '632af93787b9c95b63f0c13be32b161375ce3a96'

METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt',
                  'enemystoneinfo.txt')

# Raw-disc enemyanimmgr registration (fuefuki/enemyanimmgr.txt), slot order
# matching FUEFUKIANIM_* (Fuefuki.h:160-172). clip stem -> [[frame, keycode]].
# Note: carry's first loop event is (10,0); docs/PIKMIN2_ENGINE_DISC_PARMS.md
# transcribes it as (0,0), which this extraction corrects against the disc.
MGR_ROWS = (
    ('dead', []),
    ('landing', [[21, 2], [45, 3]]),
    ('landfail', [[21, 2], [60, 3]]),
    ('move', [[4, 0], [14, 1]]),
    ('pivot', [[4, 0], [13, 1]]),
    ('wait', [[0, 0], [29, 1]]),
    ('whisle', [[14, 0], [23, 1]]),
    ('struggle', [[20, 0], [39, 1]]),
    ('jump', [[3, 0], [8, 1], [13, 2], [15, 3]]),
    ('carry', [[10, 0], [29, 1]]),
)
CLIPS = tuple(stem for stem, _ in MGR_ROWS)

# Retail disc parms verified against enemyParms.szs:fuefuki/enemyparm.txt on US
# GPVE01 rev 0; consumed keys only (see docs/PIKMIN2_ENGINE_DISC_PARMS.md §#245).
GENERAL_RETAIL = {'fp00': 700.0, 'fp06': 250.0, 'fp09': 300.0, 'fp10': 100.0,
                  'fp11': 60.0, 'fp16': 1.0, 'fp17': 120.0, 'fp18': 1.0,
                  'fp19': 30.0, 'fp22': 130.0, 'fp23': 0.1, 'fp24': 10.0}
PROPER_RETAIL = {'fp01': 20.0, 'fp02': 10.0, 'fp03': 3.0, 'fp11': 0.0,
                 'fp12': 3.0, 'fp13': 10.0, 'fp21': 2.5, 'fp22': 0.0,
                 'fp31': 0.5}

MAX_POSES = 12
DEFAULT_POSES = 4
POSE_PREFIX = 'fuefuki'

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

# Type-1 billboard shapes have no view-time matrix in the static MOD format;
# the explicit, recorded static fallback (same policy as BombSarai) is required.
TOLERANCES = {'billboard': 'static'}

LIMITATIONS = [
    'Bounded sampled rigid poses with approximate materials; type-1 billboard shapes '
    'are statically baked through their rigid draw matrices (camera-facing orientation '
    'is not reproduced), and no skeletal playback or event execution runs.',
    'Animation key events, loop markers and parameter text are preserved as data only; '
    'no whistle theft, follow, struggle or death behavior executes.',
    'No native runtime, AI/FSM, install, arena placement, collision installation or '
    'whistle-effect ring is provided by this slice.',
    'The 10 FUEFUKIANIM slots are converted from the disc bank only when their source '
    'clip decodes; unsupported clips are recorded with a reason, never fabricated.',
    'landing and landfail author a singular joint scale, which the strict bca_pose '
    'policy refuses; both are recorded unsupported rather than silently collapsed.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def profile(blocks_list, rows):
    """Validate parsed metadata against the audited Fuefuki source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general,
    proper in order. ``rows`` is animation_rows(enemyanimmgr.txt) in
    registration order.
    """
    if len(blocks_list) != 3:
        raise ValueError('Expected 3 Fuefuki parameter blocks')
    general, proper = blocks_list[1], blocks_list[2]
    for key, value in GENERAL_RETAIL.items():
        if key not in general or not math.isclose(general[key], float(value),
                                                  rel_tol=0, abs_tol=1e-6):
            raise ValueError('Fuefuki disc general parameter mismatch: ' + key)
    for key, value in PROPER_RETAIL.items():
        if key not in proper or not math.isclose(proper[key], float(value),
                                                 rel_tol=0, abs_tol=1e-6):
            raise ValueError('Fuefuki disc proper parameter mismatch: ' + key)
    registration = tuple((Path(row['file']).stem, [list(event) for event in row['events']])
                         for row in rows)
    if registration != MGR_ROWS:
        raise ValueError('Unexpected Fuefuki animmgr registration: ' + repr(registration))
    return {'enemy_id': ENEMY_ID,
            'role': 'spawnable whistling beetle; whistle-theft squad controller',
            'parameter_blocks': blocks_list,
            'proper_retail': {key: proper[key] for key in PROPER_RETAIL},
            'general_retail': {key: general[key] for key in GENERAL_RETAIL}}


def material_probe(model, mb, names, motions, rows):
    """Record whether any clip decodes with strict (retail) materials.

    The restricted converter rejects the Fuefuki model's multi-stage materials
    ("Only single-stage materials supported"), so the import uses the explicit
    approximate-material path. This probe gives provider 09 a reproducible gate.
    """
    for row in rows:
        stem = Path(row['file']).stem
        raw = motions.get(row['file'])
        if raw is None:
            continue
        try:
            _, pose = bca_pose(raw, 0, len(names), allow_scale=True, singular_scale='allow')
            matrices = draw_matrices(mb, pose)
            decode(model, False, bake_rigid=True, draw_matrices=matrices, billboard='static')
            return {'clip': stem, 'strict_ok': True}
        except (ValueError, KeyError, ArithmeticError) as error:
            return {'clip': stem, 'strict_ok': False,
                    'reason': f'{type(error).__name__}: {error}'}
    return {'clip': None, 'strict_ok': False, 'reason': 'no clips'}


def _read_archive(raw, member):
    files = archive_files(raw)
    if member not in files:
        raise ValueError('Missing archive member: ' + member)
    return files[member]


def _load_extracted(source):
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[path.name] = sha(raw)
        return raw

    result = {'disc_id': DISC_ID, 'disc_revision': DISC_REVISION,
              'source_sha256': hashes, 'parms': {}}
    result['model'] = _read_archive(read(source / 'fuefuki_model.szs.bin'), 'enemy.bmd')
    result['anim'] = archive_files(read(source / 'fuefuki_anim.szs.bin'))
    for filename in METADATA_FILES:
        result['parms'][SPECIES.lower() + '/' + filename] = read(
            source / 'parms' / (SPECIES.lower() + '_' + filename))
    return result


def _load_iso(iso):
    index = disc_files(iso)
    hashes = {}

    def read(name):
        at, size = index[name]
        with iso.open('rb') as disc:
            disc.seek(at)
            raw = disc.read(size)
        if len(raw) != size:
            raise ValueError('Truncated ISO resource: ' + name)
        hashes[name] = sha(raw)
        return raw

    with iso.open('rb') as disc:
        header = disc.read(8)
    if header[:6] != b'GPVE01' or header[7] != 0:
        raise ValueError('Expected supplied US GPVE01 revision 0 disc')
    result = {'disc_id': header[:6].decode(), 'disc_revision': header[7],
              'source_sha256': hashes, 'parms': {}}
    result['model'] = _read_archive(read('enemy/data/Fuefuki/model.szs'), 'enemy.bmd')
    result['anim'] = archive_files(read('enemy/data/Fuefuki/anim.szs'))
    params = archive_files(read('enemy/parm/enemyParms.szs'))
    for filename in METADATA_FILES:
        name = SPECIES.lower() + '/' + filename
        if name in params:
            result['parms'][name] = params[name]
    return result


def load(source):
    source = Path(source)
    if source.is_dir():
        return _load_extracted(source)
    return _load_iso(source)


def _convert_bank(species, model, mb, names, motions, rows, root, pose_limit,
                  prefix, report, reference):
    """Write enemy.bmd and the sampled pose bank; return (clips, reference)."""
    (root / 'enemy.bmd').write_bytes(model)
    clips = []
    for row in rows:
        stem = Path(row['file']).stem
        raw = motions[row['file']]
        (root / row['file']).write_bytes(raw)
        events = [list(event) for event in row['events']]
        if raw[40] not in LOOPS:
            raise ValueError('Unsupported source loop attribute: ' + stem)
        clip = dict(name=stem, source_sha256=sha(raw), source_frames=0, events=events,
                    loop_attribute=raw[40], loop_semantics=LOOPS[raw[40]],
                    event_loop_boundaries=[event for event in events if event[1] in (0, 1)],
                    poses=[], status='unsupported')
        try:
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
            clip['source_frames'] = duration
            for number, frame in enumerate(sample_frames(duration, pose_limit)):
                try:
                    _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                    matrices = draw_matrices(mb, pose)
                    decoded = decode(model, True, bake_rigid=True,
                                     draw_matrices=matrices, **TOLERANCES)
                    name = f'{prefix}_{species}_{stem}_{number:02}.mod'
                    conversion = write_model(decoded, root / name, 'enemy.bmd')
                    conversion.update(source='enemy.bmd', output=name)
                    data = (root / name).read_bytes()
                    resources = resource_chunks(data)
                    if reference is not None and resources != reference:
                        raise ValueError(species + ' pose changes immutable render resources')
                    reference = resources
                    report['total_pose_bytes'] += len(data)
                    report['total_poses'] += 1
                    clip['poses'].append(dict(file=name, frame=frame, bytes=len(data),
                                              sha256=sha(data)))
                    (root / Path(name).with_suffix('.json')).write_bytes(
                        (json.dumps(conversion, sort_keys=True, indent=2) + '\n').encode())
                except (ValueError, KeyError, ArithmeticError) as error:
                    clip['poses'].append(dict(frame=frame,
                                              unsupported_reason=f'{type(error).__name__}: {error}'))
        except (ValueError, KeyError, ArithmeticError) as error:
            clip['unsupported_reason'] = f'{type(error).__name__}: {error}'
        converted = [pose for pose in clip['poses'] if 'file' in pose]
        if converted:
            clip['status'] = 'converted'
        else:
            clip['unsupported_reason'] = clip.get('unsupported_reason') or (
                clip['poses'][0]['unsupported_reason'] if clip['poses'] else 'no sampled frames')
        clips.append(clip)
    return clips, reference


def extract(source, output, pose_limit=DEFAULT_POSES):
    if type(pose_limit) is not int or not 2 <= pose_limit <= MAX_POSES:
        raise ValueError(f'Pose limit must be 2..{MAX_POSES}')
    res = load(source)
    root = output / ENEMY
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = dict(schema=1, policy=POLICY, disc_id=res['disc_id'],
                  disc_revision=res['disc_revision'], source_revision=SOURCE_REVISION,
                  source_sha256=res['source_sha256'], native_ready=False,
                  species={}, total_poses=0, total_pose_bytes=0)

    model = res['model']
    mb = blocks(model)
    names = joints(model)
    for filename in METADATA_FILES:
        raw = res['parms'][SPECIES.lower() + '/' + filename]
        (root / filename).write_bytes(raw)
    blocks_list = parameter_blocks(res['parms'][SPECIES.lower() + '/enemyparm.txt'])
    rows = animation_rows(res['parms'][SPECIES.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
    envelopes = struct.unpack_from('>H', mb['EVP1'], 8)[0]
    draws = struct.unpack_from('>H', mb['DRW1'], 8)[0]
    info = profile(blocks_list, rows)
    info.update(
        material_mode='approximate',
        material_probe=material_probe(model, mb, names, res['anim'], rows),
        model_sha256=sha(model), joints=names,
        metadata_sha256={filename: sha((root / filename).read_bytes())
                         for filename in METADATA_FILES},
        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                      weighted_baking=envelopes > 0,
                      self_contained_resources=draws > 0),
        collision=collision_nodes(
            res['parms'][SPECIES.lower() + '/enemycoll.txt'], len(names)),
        registration=[(Path(row['file']).stem,
                       [list(event) for event in row['events']]) for row in rows])
    info['clips'], _ = _convert_bank(
        SPECIES, model, mb, names, res['anim'], rows, root, pose_limit,
        POSE_PREFIX, report, None)
    report['species'][SPECIES] = info
    report['limitations'] = list(LIMITATIONS)
    manifest = {key: value for key, value in report.items() if key != 'extract_seconds'}
    (output / 'fuefuki.json').write_bytes(
        (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
    report['extract_seconds'] = round(time.perf_counter() - started, 3)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='private GPVE01 rev 0 ISO or a pre-extracted Fuefuki tree')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=DEFAULT_POSES)
    args = parser.parse_args()
    result = extract(args.source, args.output, args.pose_limit)

    def summary(info):
        clips = info['clips']
        return {'clips': len(clips),
                'converted': sum(clip['status'] == 'converted' for clip in clips),
                'poses': sum(1 for clip in clips for pose in clip['poses'] if 'file' in pose)}

    print(json.dumps({'bytes': result['total_pose_bytes'], 'poses': result['total_poses'],
                      'seconds': result['extract_seconds'],
                      'fuefuki': summary(result['species'][ENEMY])}, indent=2))
