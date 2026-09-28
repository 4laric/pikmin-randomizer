"""Source-backed, bounded BombSarai (Careening Dirigibug, ID 58) and Bomb payload
(EnemyID_Bomb, ID 36) import; no native actor install.

Lane #244, converter handoff #128. Modeled on ``pikmin2_flying_assets.py`` and
``pikmin2_aquatic_assets.py``. Source audit:
``docs/PIKMIN2_BOMBSARAI_AUDIT.md`` (projectPiki/pikmin2 revision
632af93787b9c95b63f0c13be32b161375ce3a96, US GPVE01 rev 0). Reads the private
disc copy through the shared read-only ``experimental.pikmin2_assets`` helpers,
or the pre-extracted ``output/pikmin2-extract-bombsarai`` tree, and writes a
schema-1 ``P2_BOMBSARAI_IMPORT_1`` manifest (``bombsarai.json``) plus the
converted ``BombSarai/*.mod`` (and ``Bomb/*.mod``) pose bank that
``experimental.pikmin2_bombsarai_install`` validates and installs.

The BombSarai mesh uses J3D shape matrix types 3 (skin) and 1 (billboard); the
static MOD proof-of-concept has no view-time billboard matrix, so the explicit
``billboard='static'`` fallback bakes the authored billboard geometry through
its rigid draw matrix and records the policy. Bounded sampled rigid poses only:
no btk playback, no skeletal animation runtime, no behavior execution.
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
from experimental.pikmin2_bombsarai_install import (
    POLICY, ENEMY, ENEMY_ID, PAYLOAD_ENEMY, PAYLOAD_ENEMY_ID, PAYLOAD_CHILD_NUM,
    DISC_ID, DISC_REVISION, SOURCE_REVISION)

SPECIES = ENEMY
PAYLOAD = PAYLOAD_ENEMY
MGR_ROWS = (
    ('dead1', [[10, 2], [17, 6], [24, 4], [30, 3], [36, 5], [65, 2], [66, 3],
               [67, 4], [68, 5], [69, 6], [83, 7]]),
    ('fall1', [[2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [9, 0], [10, 1],
               [11, 8]]),
    ('flick1', [[15, 2]]),
    ('bflick1', [[15, 2]]),
    ('mogaki1', [[0, 0], [1, 2], [13, 3], [17, 2], [22, 3], [24, 1], [26, 2],
                 [39, 3]]),
    ('release1', [[21, 2]]),
    ('run1', [[10, 0], [49, 1]]),
    ('run2', [[5, 0], [44, 1]]),
    ('supli1', []),
    ('takeoff1', [[65, 0], [104, 1]]),
    ('takeoff2', [[32, 0], [34, 1]]),
    ('type5', [[10, 0], [29, 1]]),
    ('wait1', [[10, 0], [49, 1]]),
    ('wait2', [[5, 0], [44, 1]]),
)
CLIPS = tuple(stem for stem, _ in MGR_ROWS)
EXPECTED_EVENTS = {stem: events for stem, events in MGR_ROWS}
BOMB_MGR_ROWS = (('hit_start', [[10, 2]]), ('hit_loop', [[0, 0], [7, 1]]))
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt',
                  'enemystoneinfo.txt')

# Retail (disc) proper block verified against enemyParms.szs on US GPVE01 rev 0
# (BombSarai.h:121-146 audited semantics) plus the consumed general keys.
GENERAL_RETAIL = {'fp00': 1500.0, 'fp06': 60.0, 'fp09': 200.0, 'fp20': 100.0,
                  'fp21': 45.0, 'fp22': 50.0, 'fp24': 10.0}
PROPER_RETAIL = {'fp01': 70.0, 'fp03': 50.0, 'fp10': 2.5, 'fp11': 20.0,
                 'fp21': 1.5, 'fp22': 1.0, 'fp31': 0.2, 'fp32': 0.8, 'fp40': 0.8}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

# The BombSarai mesh carries type-1 billboard shapes; the restricted static MOD
# format has no view-time matrix, so the explicit, recorded static fallback is
# required. Nothing else is relaxed: strict converter defaults everywhere else.
TOLERANCES = {'billboard': 'static'}

MAX_POSES = 12
DEFAULT_POSES = 4
POSE_PREFIX = 'bombsarai'

LIMITATIONS = [
    'Bounded sampled rigid poses with approximate materials; the J3D type-1 billboard '
    'shapes are statically baked through their rigid draw matrices (camera-facing '
    'orientation is not reproduced), and no skeletal playback or event execution runs.',
    'Animation key events, loop markers and parameter text are preserved as data only; '
    'no supply, throw, flick, explosion or death behavior executes.',
    'The supli1 clip authors a zero/annihilated joint scale, which the strict bca_pose '
    'policy refuses; it is recorded unsupported rather than silently collapsed.',
    'The Bomb payload (EnemyID_Bomb 36) is extracted and pose-sampled alongside the '
    'carrier for the projectile contract; only the BombSarai bank is installed by '
    'pikmin2_bombsarai_install, matching the shared Bomb manager asset path.',
    'No native runtime, AI/FSM, install, arena placement or collision installation is '
    'provided by this slice.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def profile(blocks_list, rows):
    """Validate parsed metadata for BombSarai against the source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general, proper
    in order. ``rows`` is animation_rows(enemyanimmgr.txt) in registration order.
    """
    if len(blocks_list) != 3:
        raise ValueError('Expected 3 BombSarai parameter blocks')
    general, proper = blocks_list[1], blocks_list[2]
    for key, value in GENERAL_RETAIL.items():
        if key not in general or not math.isclose(general[key], float(value),
                                                  rel_tol=0, abs_tol=1e-6):
            raise ValueError('BombSarai disc general parameter mismatch: ' + key)
    for key, value in PROPER_RETAIL.items():
        if key not in proper or not math.isclose(proper[key], float(value),
                                                 rel_tol=0, abs_tol=1e-6):
            raise ValueError('BombSarai disc proper parameter mismatch: ' + key)
    registration = tuple((Path(row['file']).stem, [list(event) for event in row['events']])
                         for row in rows)
    if registration != MGR_ROWS:
        raise ValueError('Unexpected BombSarai animmgr registration: ' + repr(registration))
    return {'enemy_id': ENEMY_ID,
            'role': 'concrete spawnable carrier of the Bomb payload; two bomb-rocks '
                    'preallocated (mChildNum 2)',
            'parameter_blocks': blocks_list,
            'proper_retail': {key: proper[key] for key in PROPER_RETAIL},
            'general_retail': {key: general[key] for key in GENERAL_RETAIL}}


def _read_archive(raw, member):
    files = archive_files(raw)
    if member not in files:
        raise ValueError('Missing archive member: ' + member)
    return files[member]


def _load_extracted(source):
    """Read the pre-extracted output/pikmin2-extract-bombsarai tree."""
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[path.name] = sha(raw)
        return raw

    result = {'disc_id': DISC_ID, 'disc_revision': DISC_REVISION,
              'source_sha256': hashes, 'parms': {}}
    result['model'] = _read_archive(read(source / 'bombsarai_model.szs.bin'), 'enemy.bmd')
    result['anim'] = archive_files(read(source / 'bombsarai_anim.szs.bin'))
    result['bomb_model'] = _read_archive(read(source / 'bomb_model.szs.bin'), 'enemy.bmd')
    result['bomb_anim'] = archive_files(read(source / 'bomb_anim.szs.bin'))
    for key in ('bombsarai', 'bomb'):
        for filename in METADATA_FILES:
            result['parms'][key + '/' + filename] = read(source / 'parms' / (key + '_' + filename))
    return result


def _load_iso(iso):
    """Read the private US GPVE01 rev 0 disc read-only."""
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
    result['model'] = _read_archive(read('enemy/data/BombSarai/model.szs'), 'enemy.bmd')
    result['anim'] = archive_files(read('enemy/data/BombSarai/anim.szs'))
    result['bomb_model'] = _read_archive(read('enemy/data/Bomb/model.szs'), 'enemy.bmd')
    result['bomb_anim'] = archive_files(read('enemy/data/Bomb/anim.szs'))
    params = archive_files(read('enemy/parm/enemyParms.szs'))
    for key in ('bombsarai', 'bomb'):
        for filename in METADATA_FILES:
            name = key + '/' + filename
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
    source = Path(source)
    if output.exists():
        raise ValueError('Output already exists')
    res = load(source)
    output.mkdir(parents=True)
    started = time.perf_counter()
    report = dict(schema=1, policy=POLICY, disc_id=res['disc_id'],
                  disc_revision=res['disc_revision'], source_revision=SOURCE_REVISION,
                  source_sha256=res['source_sha256'], native_ready=False,
                  gameplay_events_executed=False, btk_playback=False,
                  payload=dict(enemy=PAYLOAD, enemy_id=PAYLOAD_ENEMY_ID,
                               child_num=PAYLOAD_CHILD_NUM),
                  species={}, payload_assets={}, total_pose_bytes=0, total_poses=0)

    # BombSarai carrier.
    root = output / ENEMY
    root.mkdir()
    model = res['model']
    mb = blocks(model)
    names = joints(model)
    metadata = {}
    for filename in METADATA_FILES:
        raw = res['parms'][SPECIES.lower() + '/' + filename]
        metadata[filename] = sha(raw)
        (root / filename).write_bytes(raw)
    blocks_list = parameter_blocks(res['parms'][SPECIES.lower() + '/enemyparm.txt'])
    rows = animation_rows(res['parms'][SPECIES.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
    envelopes = struct.unpack_from('>H', mb['EVP1'], 8)[0]
    draws = struct.unpack_from('>H', mb['DRW1'], 8)[0]
    info = profile(blocks_list, rows)
    info.update(model_sha256=sha(model), joints=names, metadata_sha256=metadata,
                skinning=dict(envelopes=envelopes, draw_matrices=draws,
                              weighted_baking=envelopes > 0,
                              self_contained_resources=draws > 0),
                collision=collision_nodes(
                    res['parms'][SPECIES.lower() + '/enemycoll.txt'], len(names)))
    info['clips'], reference = _convert_bank(
        SPECIES, model, mb, names, res['anim'], rows, root, pose_limit,
        POSE_PREFIX, report, None)
    report['species'][SPECIES] = info

    # Bomb payload (projectile contract; installed by the shared Bomb path only).
    bomb_root = output / PAYLOAD
    bomb_root.mkdir()
    bomb_model = res['bomb_model']
    bomb_mb = blocks(bomb_model)
    bomb_names = joints(bomb_model)
    bomb_rows = [dict(file=stem + '.bca', events=[list(event) for event in events])
                 for stem, events in BOMB_MGR_ROWS]
    bomb_info = {'enemy_id': PAYLOAD_ENEMY_ID,
                 'role': 'shared projectile payload (enemy ID 36)',
                 'parameter_blocks': parameter_blocks(res['parms']['bomb/enemyparm.txt']),
                 'model_sha256': sha(bomb_model), 'joints': bomb_names,
                 'metadata_sha256': {}}
    for filename in METADATA_FILES:
        raw = res['parms']['bomb/' + filename]
        bomb_info['metadata_sha256'][filename] = sha(raw)
        (bomb_root / filename).write_bytes(raw)
    bomb_info['clips'], _ = _convert_bank(
        PAYLOAD, bomb_model, bomb_mb, bomb_names, res['bomb_anim'], bomb_rows,
        bomb_root, pose_limit, POSE_PREFIX, report, None)
    report['payload_assets'] = bomb_info

    report['limitations'] = list(LIMITATIONS)
    manifest = {key: value for key, value in report.items() if key != 'extract_seconds'}
    (output / 'bombsarai.json').write_bytes(
        (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
    report['extract_seconds'] = round(time.perf_counter() - started, 3)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='private GPVE01 rev 0 ISO or the pre-extracted bombsarai tree')
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
                      'carrier': summary(result['species'][ENEMY]),
                      'payload': summary(result['payload_assets'])}, indent=2))
