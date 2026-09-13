"""Source-backed, bounded local BigTreasure (Titan Dweevil) conversion import; no native actor install.

Issue #246 (parent #128 converter capability). Covers enemy ID 73 BigTreasure
plus its five captured pellets (elec/fire/gas/water weapons and loozy) from
the user-supplied US GPVE01 revision 0 disc. Follows the Bulblax lane
pattern (#217/#223): hashed disc reads, preserved metadata text, bounded
weighted/rigid pose sampling with per-frame unsupported reasons recorded,
never fabricated. Engine lane disc facts: docs/PIKMIN2_ENGINE_DISC_PARMS.md.
No .btk/.brk exists for this family — material animation is fully procedural
(resolved audit Q2), so no material-animation import is needed.
"""
import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import time
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_sheargrub_assets import joints
from experimental.pikmin2_breadbug_assets import collision_nodes
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_engine_parms import parse_anim_mgr, parse_otakara_config, parse_parm_text
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

ENEMY_ID = 73
PARM_SOURCE = 'enemy/parm/enemyParms.szs'
OTAKARA_SOURCE = 'user/Abe/Pellet/us/otakara_config.txt'
DATA_ROOT = 'enemy/data/BigTreasure'
PELLET_DIR = 'user/Abe/Pellet/us/'
MAX_POSES = 12
CLIP_BYTES = 4 * 1024 * 1024
TOTAL_BYTES = 64 * 1024 * 1024

# 30-slot animation manager registration order (BigTreasure.h AnimID enum
# matches enemyanimmgr.txt row order); wait2.bca is registered twice (slots
# 25 and 29), so 29 unique clips cover 30 slots. Registry names use retail
# casing; archive members are lowercase.
ANIM_SLOTS = ('appear', 'appear2', 'wait1', 'preattackf', 'attackf', 'attackendf',
              'preattackfr', 'attackfr', 'attackendfr', 'preattackfl', 'attackfl',
              'attackendfl', 'preattackfb', 'attackfb', 'attackendfb', 'preattackw',
              'attackw', 'attackendw', 'preattackg', 'attackg', 'attackendg',
              'preattacke', 'attacke', 'attackende', 'dropitem', 'wait2', 'flick',
              'dead', 'move1', 'wait2')
CLIPS = tuple(dict.fromkeys(ANIM_SLOTS))  # 29 unique, registration order

# Authored key events (frame, type) from bigtreasure/enemyanimmgr.txt on
# disc, cross-checked against docs/PIKMIN2_ENGINE_DISC_PARMS.md (dead.bca
# KEYEVENT_100 at frame 320 is the throwupItem anchor).
EXPECTED_EVENTS = {
    'appear': [[26, 2], [30, 3], [50, 4], [60, 5], [82, 6], [90, 7], [100, 8], [115, 9], [191, 10]],
    'appear2': [],
    'wait1': [[0, 0], [89, 1]],
    'preattackf': [[20, 2], [68, 0], [82, 1], [85, 3]],
    'attackf': [[0, 0], [1, 2], [119, 1]],
    'attackendf': [],
    'preattackfr': [],
    'attackfr': [[0, 0], [1, 2], [119, 1]],
    'attackendfr': [],
    'preattackfl': [],
    'attackfl': [[0, 0], [1, 2], [119, 1]],
    'attackendfl': [],
    'preattackfb': [],
    'attackfb': [[0, 0], [1, 2], [119, 1]],
    'attackendfb': [],
    'preattackw': [[20, 2], [68, 0], [82, 1]],
    'attackw': [[0, 0], [1, 2], [29, 1]],
    'attackendw': [],
    'preattackg': [[20, 2], [68, 0], [82, 1]],
    'attackg': [[0, 0], [1, 2], [79, 1]],
    'attackendg': [],
    'preattacke': [[20, 2], [68, 0], [82, 1]],
    'attacke': [[0, 0], [1, 2], [39, 1]],
    'attackende': [],
    'dropitem': [[60, 2]],
    'wait2': [[0, 0], [29, 1]],
    'flick': [[35, 2]],
    'dead': [[60, 2], [100, 3], [125, 4], [150, 5], [175, 6], [200, 7], [290, 8],
             [295, 9], [300, 10], [305, 11], [320, 100]],
    'move1': [],
}

# Five captured pellet configurations from otakara_config.txt (verbatim disc
# values, docs/PIKMIN2_ENGINE_DISC_PARMS.md): carry min/max, poko value and
# treasure dictionary ID. loozy money 10 is the verbatim config value.
PELLETS = {'elec': {'archive': 'elec.szs', 'bmd': 'elements_elec.bmd', 'min': 30, 'max': 40,
                    'money': 1000, 'dictionary': 197, 'radius': 35, 'height': 50},
           'fire': {'archive': 'fire.szs', 'bmd': 'elements_fire.bmd', 'min': 30, 'max': 40,
                    'money': 1000, 'dictionary': 198, 'radius': 35, 'height': 52},
           'gas': {'archive': 'gas.szs', 'bmd': 'elements_gas.bmd', 'min': 30, 'max': 40,
                   'money': 1000, 'dictionary': 199, 'radius': 37, 'height': 20},
           'water': {'archive': 'water.szs', 'bmd': 'elements_water.bmd', 'min': 30, 'max': 40,
                     'money': 1000, 'dictionary': 200, 'radius': 35, 'height': 51},
           'loozy': {'archive': 'loozy.szs', 'bmd': 'otakara_loozy.bmd', 'min': 1, 'max': 5,
                     'money': 10, 'dictionary': 201, 'radius': 12, 'height': 10}}
PELLET_JOINTS = {'elec': 'otakara_elec', 'fire': 'otakara_fire', 'gas': 'otakara_gas',
                 'water': 'otakara_water', 'loozy': 'otakara_loozy'}
REFERENCE_JOINTS = ('kosi', 'otakara_elec_eff', 'otakara_fire_eff')

# Retail disc general parms spot-checked (full values in
# output/p2-engine-parms/engine_disc_parms.json, #128 batch).
DISC_GENERAL = {'fp00': 5000.0, 'fp11': 100.0, 'fp09': 250.0, 'fp10': 75.0,
                'fp12': 300.0, 'fp25': 50.0, 'fp14': 300.0, 'fp15': 90.0,
                'fp20': 75.0, 'fp21': 25.0, 'fp22': 75.0, 'fp23': 25.0,
                'fp24': 10.0, 'fp16': 1.0, 'fp17': 100.0, 'fp18': 0.0, 'fp19': 25.0,
                'ip01': 6.0, 'ip02': 5.0, 'ip03': 12.0, 'ip04': 10.0,
                'ip05': 17.0, 'ip06': 20.0, 'ip07': 22.0}

# State IDs: BigTreasure.h:57-72 (source audit docs/PIKMIN2_BIGTREASURE_AUDIT.md).
STATE_IDS = {'Dead': 0, 'Stay': 1, 'Land': 2, 'Wait': 3, 'ItemWait': 4, 'Flick': 5,
             'PreAttack': 6, 'Attack': 7, 'PutItem': 8, 'DropItem': 9, 'Walk': 10,
             'ItemWalk': 11}

LIMITATIONS = ['Sampled weighted/rigid poses with approximate materials; no skeletal playback.',
               'Pellet attachment uses bind-pose otakara_* joint transforms; baked poses flatten per-frame skeletal joint motion, so captured pellets do not track animated joints.',
               'Animation key events and loop markers are preserved as data for the retail event player; no damage, drop, flick or capture behavior executes.',
               'No .btk/.brk exists for this family (audit Q2 resolved); material animation is procedural and not reproduced.',
               'No native runtime, AI/FSM, install or arena placement is provided by this import.']

TEXT = ('P2_BIGTREASURE_1\n'
        'enemy bigtreasure 73\n'
        'weapon_health 6000\npinch_threshold 3000\n'
        'pellet elec 30 40 1000 197\npellet fire 30 40 1000 198\n'
        'pellet gas 30 40 1000 199\npellet water 30 40 1000 200\n'
        'pellet loozy 1 5 10 201\n'
        'native_ready false\ngameplay_events_executed false\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_registry(rows):
    """Cross-check the 30-slot registry against the source contract.

    wait2.bca is registered twice with different authored event rows
    (slot 25 carries the (0,0)/(29,1) loop markers, slot 29 none); both
    variants are source-legitimate and returned per slot. The clip table
    keys on the first registration, matching the loop-carrying variant the
    retail player needs.
    """
    if len(rows) != 30:
        raise ValueError(f'Expected 30 animation slots, got {len(rows)}')
    names = [r['file'].lower() for r in rows]
    if tuple(n[:-4] for n in names) != ANIM_SLOTS:
        raise ValueError(f'Unexpected BigTreasure clip registry: {names}')
    slot_events = [[list(event) for event in row['events']] for row in rows]
    seen = {}
    for row in rows:
        name = row['file'].lower()[:-4]
        if name not in seen:
            seen[name] = [list(event) for event in row['events']]
    if set(seen) != set(CLIPS):
        raise ValueError('Registry does not cover the 29 unique clips')
    for name, events in seen.items():
        if events != EXPECTED_EVENTS[name]:
            raise ValueError(f'BigTreasure clip {name} key events mismatch: {events}')
    return seen, slot_events


def validate_parms(text):
    """Spot-check disc general parms via the engine extractor's tolerant
    section parser (bigtreasure/enemyparm.txt repeats keys in the proper
    block, which the strict parameter_blocks parser rejects; first
    occurrence wins, duplicates recorded)."""
    sections = parse_parm_text(text)
    if len(sections) != 3:
        raise ValueError(f'Expected 3 parameter blocks, got {len(sections)}')
    general = {key: float(value) for key, (value, _comment) in sections[1][1].items()}
    for key, value in DISC_GENERAL.items():
        if key not in general or not math.isclose(general[key], float(value), rel_tol=0, abs_tol=1e-6):
            raise ValueError(f'BigTreasure disc general parameter {key} mismatch')
    return [{'section': name, 'params': {k: v[0] for k, v in params.items()}}
            for name, params in sections]


def validate_pellet_config(configs):
    result = {}
    for name, expected in PELLETS.items():
        fields = configs.get(name)
        if fields is None:
            raise ValueError(f'Missing pellet config: {name}')
        actual = {'archive': fields['archive'], 'bmd': fields['bmd'],
                  'min': int(fields['min']), 'max': int(fields['max']),
                  'money': int(fields['money']), 'dictionary': int(fields['dictionary']),
                  'radius': int(fields['radius']), 'height': int(fields['height'])}
        if actual != expected:
            raise ValueError(f'Pellet {name} config mismatch: {actual}')
        result[name] = actual
    return result


def rigid_draw_matrices(model_blocks, pose):
    """Explicit per-draw matrices for a rigid (EVP1 0) model.

    decode() only accepts TEX*MTXIDX display-list attributes when explicit
    draw matrices are supplied; BigTreasure shape 0 carries TEX1MTXIDX
    despite being fully rigid, so the plain pose path rejects it. Each DRW1
    draw entry maps 1:1 to a joint (weighted flag must be clear).
    """
    matrices = joint_matrices(model_blocks, local_overrides=pose)
    drw = model_blocks['DRW1']
    count = struct.unpack_from('>H', drw, 8)[0]
    weighted = struct.unpack_from(f'>{count}B', drw, struct.unpack_from('>I', drw, 12)[0])
    draw_joints = struct.unpack_from(f'>{count}H', drw, struct.unpack_from('>I', drw, 16)[0])
    if any(weighted) or any(joint >= len(matrices) for joint in draw_joints):
        raise ValueError('Non-rigid draw matrix')
    return [matrices[joint] for joint in draw_joints]


def capture_transforms(model_blocks, names):
    """Bind-pose world matrices for the otakara_* capture joints.

    The ownership policy captures each weapon on its named joint; these
    transforms seed the host seam's fixed-placement pellet display. Baked
    poses flatten skeletal motion, so they are bind-pose constants.
    """
    matrices = joint_matrices(model_blocks)
    wanted = dict(PELLET_JOINTS)
    transforms = {}
    for key, joint in list(wanted.items()) + [('ref', j) for j in REFERENCE_JOINTS]:
        if joint not in names:
            raise ValueError(f'Missing capture joint: {joint}')
        matrix = matrices[names.index(joint)]
        if len(matrix) != 3 or any(len(row) != 4 or not all(math.isfinite(v) for v in row)
                                   for row in matrix):
            raise ValueError(f'Invalid capture transform for {joint}')
        transforms[joint] = matrix
    return transforms


def extract(iso, source, output, pose_limit=6):
    if type(pose_limit) is not int or not 2 <= pose_limit <= MAX_POSES:
        raise ValueError(f'Pose limit must be 2..{MAX_POSES}')
    if output.exists():
        raise ValueError('Output already exists')
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('Invalid source revision')
    index = disc_files(iso)
    source_hashes = {}
    started = time.perf_counter()
    with iso.open('rb') as disc:
        header = disc.read(8)
        if header[:6] != b'GPVE01':
            raise ValueError('Expected supplied US GPVE01 disc')

        def read(name):
            at, size = index[name]
            disc.seek(at)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated ISO resource')
            source_hashes[name] = sha(raw)
            return raw

        params = archive_files(read(PARM_SOURCE))
        configs = parse_otakara_config(read(OTAKARA_SOURCE).decode('shift_jis'), tuple(PELLETS))
        pellets = validate_pellet_config(configs)
        output.mkdir(parents=True)
        report = dict(schema=1, policy='P2_BIGTREASURE_IMPORT_1', disc_id=header[:6].decode(),
                      disc_revision=header[7], source_revision=head, source_sha256=source_hashes,
                      native_ready=False, gameplay_events_executed=False, material_animation='none on disc',
                      enemy_id=ENEMY_ID, state_ids=dict(STATE_IDS),
                      anim_slots=list(ANIM_SLOTS), pellets=pellets,
                      total_pose_bytes=0, total_poses=0)

        # Boss model, metadata and animation clips.
        root = output / 'BigTreasure'
        root.mkdir()
        model = archive_files(read(f'{DATA_ROOT}/model.szs'))['enemy.bmd']
        model_blocks = blocks(model)
        motions = archive_files(read(f'{DATA_ROOT}/anim.szs'))
        motion_lower = {name.lower(): data for name, data in motions.items()}
        if sorted(motion_lower) != sorted(n + '.bca' for n in CLIPS):
            raise ValueError(f'anim.szs members mismatch: {sorted(motions)}')
        names = joints(model)
        (root / 'enemy.bmd').write_bytes(model)
        metadata = {}
        for filename in ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt'):
            raw = params['bigtreasure/' + filename]
            metadata[filename] = sha(raw)
            (root / filename).write_bytes(raw)
        rows = parse_anim_mgr(params['bigtreasure/enemyanimmgr.txt'].decode('shift_jis'))['clips']
        events, slot_events = validate_registry(rows)
        report['anim_slot_events'] = slot_events
        blocks_list = validate_parms(params['bigtreasure/enemyparm.txt'].decode('shift_jis'))
        envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
        draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
        boss = dict(model_sha256=sha(model), joints=names, joint_count=len(names),
                    metadata_sha256=metadata,
                    skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                  weighted_baking=envelopes > 0),
                    capture_transforms=capture_transforms(model_blocks, names),
                    collision=collision_nodes(params['bigtreasure/enemycoll.txt'], len(names)),
                    parameter_blocks=blocks_list, clips=[])
        reference = None
        for name in CLIPS:
            raw = motion_lower[name + '.bca']
            (root / (name + '.bca')).write_bytes(raw)
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
            frames = sample_frames(duration, pose_limit)
            clip = dict(name=name, source_sha256=sha(raw), source_frames=duration,
                        events=events[name], loop_attribute=raw[40], poses=[], status='unsupported')
            clip_bytes = 0
            for number, frame in enumerate(frames):
                try:
                    _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                    matrices = draw_matrices(model_blocks, pose) if envelopes \
                        else rigid_draw_matrices(model_blocks, pose)
                    decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                    filename = f'bigtreasure_{name}_{number:02}.mod'
                    conversion = write_model(decoded, root / filename, 'enemy.bmd')
                    conversion.update(source='enemy.bmd', output=filename,
                                      weighted_pose_baked=envelopes > 0)
                    data = (root / filename).read_bytes()
                    clip_bytes += len(data)
                    if clip_bytes > CLIP_BYTES or report['total_pose_bytes'] + clip_bytes > TOTAL_BYTES:
                        raise ValueError('BigTreasure pose budget exceeded')
                    resources = resource_chunks(data)
                    if reference is not None and resources != reference:
                        raise ValueError('BigTreasure pose changes immutable render resources')
                    reference = resources
                    report['total_pose_bytes'] += len(data)
                    report['total_poses'] += 1
                    clip['poses'].append(dict(file=filename, frame=frame, bytes=len(data), sha256=sha(data)))
                    (root / Path(filename).with_suffix('.json')).write_bytes(
                        (json.dumps(conversion, sort_keys=True, indent=2) + '\n').encode())
                except (ValueError, KeyError, ArithmeticError) as error:
                    # Converter limitation; recorded, never fabricated.
                    clip['poses'].append(dict(frame=frame, unsupported_reason=f'{type(error).__name__}: {error}'))
            if any('file' in p for p in clip['poses']):
                clip['status'] = 'converted'
            else:
                clip['unsupported_reason'] = clip['poses'][0]['unsupported_reason'] if clip['poses'] \
                    else 'no sampled frames'
            boss['clips'].append(clip)
        report['boss'] = boss

        # Pellet models: rigid bind-pose bakes.
        pellet_root = output / 'pellets'
        pellet_root.mkdir()
        report['pellet_models'] = {}
        for name, info in PELLETS.items():
            members = archive_files(read(PELLET_DIR + info['archive']))
            if info['bmd'] not in members:
                raise ValueError(f'Pellet archive {info["archive"]} missing {info["bmd"]}')
            raw = members[info['bmd']]
            (pellet_root / info['bmd']).write_bytes(raw)
            pellet_blocks = blocks(raw)
            p_envelopes = struct.unpack_from('>H', pellet_blocks['EVP1'], 8)[0]
            filename = f'bigtreasure_pellet_{name}.mod'
            entry = dict(bmd=info['bmd'], bmd_sha256=sha(raw), bmd_bytes=len(raw),
                         archive_members=sorted(members), envelopes=p_envelopes,
                         status='unsupported')
            try:
                if p_envelopes:
                    # Bind-pose weighted bake (no clips exist for pellets).
                    decoded = decode(raw, True, bake_rigid=True,
                                     draw_matrices=draw_matrices(pellet_blocks))
                else:
                    decoded = decode(raw, True, bake_rigid=True)
                conversion = write_model(decoded, pellet_root / filename, info['bmd'])
                conversion.update(source=info['bmd'], output=filename)
                data = (pellet_root / filename).read_bytes()
                (pellet_root / Path(filename).with_suffix('.json')).write_bytes(
                    (json.dumps(conversion, sort_keys=True, indent=2) + '\n').encode())
                entry.update(status='converted', file=filename, bytes=len(data), sha256=sha(data))
            except (ValueError, KeyError, ArithmeticError) as error:
                entry['unsupported_reason'] = f'{type(error).__name__}: {error}'
            report['pellet_models'][name] = entry

        report['limitations'] = list(LIMITATIONS)
        manifest = {k: v for k, v in report.items()
                    if k != 'extract_seconds'}
        (output / 'bigtreasure.json').write_bytes(
            (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
        report['extract_seconds'] = round(time.perf_counter() - started, 3)
        (output / 'p2-bigtreasure.txt').write_text(TEXT)
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True, help='native research checkout for revision stamping')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=6)
    args = parser.parse_args()
    result = extract(args.iso, args.source, args.output, args.pose_limit)
    print(json.dumps({'poses': result['total_poses'], 'mod_bytes': result['total_pose_bytes'],
                      'clips_converted': sum(1 for c in result['boss']['clips'] if c['status'] == 'converted'),
                      'pellets_converted': sum(1 for p in result['pellet_models'].values()
                                               if p['status'] == 'converted'),
                      'seconds': result['extract_seconds']}, indent=2))
