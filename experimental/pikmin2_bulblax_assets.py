"""Source-backed, bounded local Bulblax family import; no native actor install.

Covers enemy IDs 30 Queen (Empress Bulblax), 31 Baby (Bulborb Larva) and 53
KingChappy (Emperor Bulblax) from the US GPVE01 revision 0 disc. Source audit:
docs/PIKMIN2_BULBLAX_BOSS_AUDIT.md (issue #217, parent #172). Extraction
follows the Frog lane: hashed disc reads, preserved metadata text, bounded
weighted/rigid pose sampling, carcass preservation. No btk playback, no
behavior execution.
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
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_breadbug_assets import parameter_blocks, collision_nodes
from experimental.pikmin2_pod import pellet_catalog
from experimental.pikmin2_convert import blocks, decode, u16, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

SPECIES = {'Queen': 30, 'Baby': 31, 'KingChappy': 53}
PARM_SOURCE = 'enemy/parm/enemyParms.szs'
CARCASS_SOURCE = 'user/Abe/Pellet/us/carcass_config.txt'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
EXTRA_DISC_FILES = {'Queen': 'enemy/data/Queen/queenchappy_model.btk'}  # hash + preserve only; no btk playback
MAX_POSES = 12

# Clip order equals the AnimID enum registration order (Queen.h:195-205,
# Baby.h:116-123, KingChappy.h:318-333) and the enemyanimmgr.txt row order.
CLIPS = {'Queen': ('dead', 'sleep', 'wait1', 'damage', 'flick', 'rolling_l', 'rolling_r', 'born', 'carry'),
         'Baby': ('dead', 'deadpress', 'move', 'attack', 'attackfail', 'born'),
         'KingChappy': ('attack', 'cry', 'damage', 'dead', 'dive', 'flick', 'move1',
                        'type1', 'type2', 'type3', 'wait2', 'waitact1', 'waitact2', 'carry')}

# Animation key events (frame, type) from each enemyanimmgr.txt on disc,
# cross-checked against docs/PIKMIN2_BULBLAX_BOSS_AUDIT.md.
EXPECTED_EVENTS = {
    'Queen': {'dead': [[60, 2], [73, 2], [86, 2], [99, 2]],
              'sleep': [[59, 0], [118, 1], [120, 2]],
              'wait1': [[0, 0], [29, 1]],
              'damage': [[10, 0], [29, 1]],
              'flick': [[40, 2]],
              'rolling_l': [[20, 0], [67, 2], [69, 1]],
              'rolling_r': [[20, 0], [67, 2], [69, 1]],
              'born': [[24, 2]],
              'carry': [[10, 0], [29, 1]]},
    'Baby': {'dead': [], 'deadpress': [],
             'move': [[0, 0], [11, 1]],
             'attack': [[10, 2], [30, 3]],
             'attackfail': [],
             'born': [[7, 0], [8, 1]]},
    'KingChappy': {'attack': [[25, 2], [40, 3], [70, 4], [86, 5], [92, 6]],
                   'cry': [[33, 2], [38, 3], [65, 4], [100, 5], [103, 6]],
                   'damage': [[12, 2], [14, 3], [15, 4], [46, 5], [60, 6], [65, 0], [94, 1]],
                   'dead': [[185, 2]],
                   'dive': [[58, 2], [60, 3], [90, 4]],
                   'flick': [[30, 2], [35, 3]],
                   'move1': [[15, 0], [54, 1]],
                   'type1': [], 'type2': [],
                   'type3': [[3, 2], [55, 3], [58, 4]],
                   'wait2': [[0, 0], [39, 1]],
                   'waitact1': [[10, 0], [33, 1]],
                   'waitact2': [],
                   'carry': [[10, 0], [29, 1]]}}

# State IDs: Queen.h:26-35, Baby.h:140-147, KingChappy.h:22-37.
STATE_IDS = {'Queen': {'dead': 0, 'sleep': 1, 'wait': 2, 'damage': 3, 'flick': 4, 'rolling': 5, 'born': 6},
             'Baby': {'dead': 0, 'press': 1, 'born': 2, 'move': 3, 'attack': 4},
             'KingChappy': {'walk': 0, 'attack': 1, 'dead': 2, 'flick': 3, 'warcry': 4, 'damage': 5,
                            'turn': 6, 'eat': 7, 'hide': 8, 'hidewait': 9, 'appear': 10,
                            'caution': 11, 'swallow': 12}}

# ProperParms header defaults: Queen.h:164-179, Baby.h:91-101, KingChappy.h:48-76.
PROPER_PARM_DEFAULTS = {'Queen': {'fp01': 10.0, 'fp02': 0.0, 'fp11': 2500.0, 'ip01': 50, 'ip02': 25},
                        'Baby': {'fp01': 300.0, 'fp11': 0.2},
                        'KingChappy': {'fp01': 20.0, 'fp02': 150.0, 'fp03': 45.0, 'fp04': 100.0,
                                       'fp05': 200.0, 'fp06': 70.0, 'fp07': 10.0, 'fp08': 45.0,
                                       'fp09': 100.0, 'fp10': 200.0, 'fp11': 1.0, 'fp12': 0.0,
                                       'fp13': 0.5, 'fp14': 300.0, 'fp15': 1.0, 'fp16': 100.0,
                                       'fp17': 80.0, 'fp18': 0.1, 'fp19': 10.0, 'fp20': 15.0,
                                       'fp21': 70.0, 'ip01': 500, 'ip02': 200, 'ip03': 10}}

# Retail (disc) values verified against enemyParms.szs on US GPVE01 rev 0.
# Keys are (block, parm): 'general' is the first EnemyParmsBase block, 'proper'
# the species block. Audit-quoted semantics: Queen fp22=attack radius 150,
# fp01/fp02 roll time 3.5 s / birth interval 2.0 s, fp11 HoB health 3300,
# ip01/ip02 births max 50 / min 25; Baby fp00 health 5, fp12 sight 800,
# fp06 speed 40, fp24 attack damage 2, proper fp01 poison 300, fp11 nectar 0.2;
# KingChappy fp00 health 1300, proper fp02 spawn distance 60, fp05 bomb damage
# 200, ip03 stun 180 frames, fp15/fp16/fp17 big scale 1.5 / life 1800 / speed 45.
DISC_PARMS = {'Queen': {'general': {'fp00': 5000.0, 'fp06': 125.0, 'fp09': 200.0, 'fp10': 25.0,
                                    'fp12': 200.0, 'fp20': 150.0, 'fp21': 25.0, 'fp22': 150.0,
                                    'fp24': 10.0, 'fp32': 300.0, 'fp02': 0.0, 'fp03': 0.05,
                                    'fp17': 300.0, 'fp18': 1.0,
                                    'ip01': 30, 'ip02': 5, 'ip03': 35, 'ip04': 10,
                                    'ip05': 45, 'ip06': 15, 'ip07': 50},
                        'proper': {'fp01': 3.5, 'fp02': 2.0, 'fp11': 3300.0, 'ip01': 50, 'ip02': 25}},
              'Baby': {'general': {'fp00': 5.0, 'fp06': 40.0, 'fp12': 800.0, 'fp13': 180.0,
                                   'fp20': 30.0, 'fp21': 45.0, 'fp24': 2.0},
                       'proper': {'fp01': 300.0, 'fp11': 0.2}},
              'KingChappy': {'general': {'fp00': 1300.0, 'fp06': 45.0, 'fp19': 60.0,
                                         'fp20': 130.0, 'fp24': 5.0},
                             'proper': {'fp01': 60.0, 'fp02': 60.0, 'fp03': 180.0, 'fp04': 300.0,
                                        'fp05': 200.0, 'fp06': 80.0, 'fp07': 40.0, 'fp08': 45.0,
                                        'fp09': 100.0, 'fp10': 200.0, 'fp11': 1.0, 'fp12': 0.0,
                                        'fp13': 0.5, 'fp14': 200.0, 'fp15': 1.5, 'fp16': 1800.0,
                                        'fp17': 45.0, 'fp18': 0.02, 'fp19': 30.0, 'fp20': 30.0,
                                        'fp21': 120.0, 'ip01': 500, 'ip02': 0, 'ip03': 180}}}

# Carcass entries from carcass_config.txt: 15 pokos, carry 20-30; Baby has none
# (EB_LeaveCarcass disabled at init, Baby.cpp:40).
CARCASS = {'Queen': {'money': 15, 'min': 20, 'max': 30},
           'KingChappy': {'money': 15, 'min': 20, 'max': 30},
           'Baby': None}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = ['Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
               'Animation key events, loop markers and parameter text are preserved as data only; no damage, drop, birth or flick behavior executes.',
               'queenchappy_model.btk is hashed and byte-preserved only; no btk (texture animation) playback.',
               'No native runtime, AI/FSM, install or arena placement is provided by this slice.',
               'Baby model.szs is a self-contained 3808-byte rigid model (1 shape, 7 joints, 5 draw entries, EVP1 envelopes 0); its resources are not shared with Queen.',
               'KingChappy shape 0 references no normal attribute (the VTX1 normal array exists but the shape display list omits it); the existing rigid/weighted bake requires per-vertex normals, so those poses are recorded unsupported rather than fabricated.',
               'Queen dead/carry poses with a singular normal transform are recorded unsupported rather than approximated.']

TEXT = ('P2_BULBLAX_1\n'
        'species Queen Baby KingChappy\n'
        'queen_health 5000\nqueen_hob_health 3300\nqueen_roll_time 3.5\nqueen_birth_interval 2.0\n'
        'queen_births_max 50\nqueen_births_min 25\n'
        'baby_health 5\nbaby_sight 800\nbaby_speed 40\nbaby_attack_damage 2\nbaby_poison 300\nbaby_nectar 0.2\n'
        'king_health 1300\nking_spawn_distance 60\nking_bomb_damage 200\nking_stun_frames 180\n'
        'king_big_scale 1.5\nking_big_life 1800\nking_big_speed 45\n'
        'native_ready false\ngameplay_events_executed false\nbtk_playback false\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def corpse(fields):
    result = {'money': int(fields['money']), 'min': int(fields['min']), 'max': int(fields['max'])}
    if not 0 <= result['money'] or not 1 <= result['min'] <= result['max']:
        raise ValueError('Invalid Bulblax carcass config')
    return result


def profile(species, blocks_list, rows, corpse_entry):
    """Validate parsed metadata for one species against the source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general,
    proper in order. ``rows`` is animation_rows(enemyanimmgr.txt) in
    registration order. Duplicate keys are rejected by the parsers upstream;
    header defaults and disc values are reported separately, never flattened.
    """
    if species not in SPECIES:
        raise ValueError('Unknown Bulblax species')
    if len(blocks_list) != 3:
        raise ValueError(f'Expected 3 parameter blocks for {species}')
    general, proper = blocks_list[1], blocks_list[2]
    if set(proper) != set(PROPER_PARM_DEFAULTS[species]):
        raise ValueError(f'Unexpected {species} proper parameter keys: {sorted(proper)}')
    for group in ('general', 'proper'):
        source = general if group == 'general' else proper
        for key, value in DISC_PARMS[species][group].items():
            if key not in source or not math.isclose(source[key], float(value), rel_tol=0, abs_tol=1e-6):
                raise ValueError(f'{species} disc {group} parameter {key} mismatch')
    clips = tuple(Path(r['file']).stem for r in rows)
    if clips != CLIPS[species]:
        raise ValueError(f'Unexpected {species} clip registry: {clips}')
    for row in rows:
        name = Path(row['file']).stem
        if row['events'] != EXPECTED_EVENTS[species][name]:
            raise ValueError(f'{species} clip {name} key events mismatch')
    expected_corpse = CARCASS[species]
    if expected_corpse is None:
        if corpse_entry is not None:
            raise ValueError(f'Unexpected {species} carcass entry')
        corpse_data = None
    else:
        if corpse_entry is None:
            raise ValueError(f'Missing {species} carcass entry')
        corpse_data = corpse(corpse_entry)
        if corpse_data != expected_corpse:
            raise ValueError(f'{species} carcass values mismatch')
    return {'enemy_id': SPECIES[species], 'state_ids': dict(STATE_IDS[species]),
            'anim_id_by_clip': {name: i for i, name in enumerate(CLIPS[species])},
            'parameter_blocks': blocks_list,
            'proper_header_defaults': dict(PROPER_PARM_DEFAULTS[species]),
            'proper_retail': {k: proper[k] for k in PROPER_PARM_DEFAULTS[species]},
            'corpse': corpse_data}


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
        carcasses = pellet_catalog(read(CARCASS_SOURCE).decode('shift_jis'))
        output.mkdir(parents=True)
        report = dict(schema=1, policy='P2_BULBLAX_IMPORT_1', disc_id=header[:6].decode(),
                      disc_revision=header[7], source_revision=head, source_sha256=source_hashes,
                      native_ready=False, gameplay_events_executed=False, btk_playback=False,
                      species={}, total_pose_bytes=0, total_poses=0)
        for species, identity in SPECIES.items():
            root = output / species
            root.mkdir()
            model = archive_files(read(f'enemy/data/{species}/model.szs'))['enemy.bmd']
            model_blocks = blocks(model)
            motions = archive_files(read(f'enemy/data/{species}/anim.szs'))
            names = joints(model)
            (root / 'enemy.bmd').write_bytes(model)
            metadata = {}
            for filename in METADATA_FILES:
                raw = params[species.lower() + '/' + filename]
                metadata[filename] = sha(raw)
                (root / filename).write_bytes(raw)
            extra = {}
            if species in EXTRA_DISC_FILES:
                raw = read(EXTRA_DISC_FILES[species])
                name = Path(EXTRA_DISC_FILES[species]).name
                (root / name).write_bytes(raw)
                extra[name] = {'sha256': sha(raw), 'bytes': len(raw), 'playback': 'none; byte-preserved only'}
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
            blocks_list = parameter_blocks(params[species.lower() + '/enemyparm.txt'])
            rows = animation_rows(params[species.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
            info = profile(species, blocks_list, rows, carcasses.get(species))
            info.update(role='concrete spawnable' + ('; boss (IS_ENEMY_BOSS)' if species != 'Baby' else '; Empress-spawned larva, no carcass'),
                        model_sha256=sha(model), joints=names, metadata_sha256=metadata,
                        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                      weighted_baking=envelopes > 0,
                                      self_contained_resources=draws > 0),
                        collision=collision_nodes(params[species.lower() + '/enemycoll.txt'], len(names)),
                        extra_files=extra, clips=[])
            reference = None
            for row in rows:
                raw = motions[row['file']]
                (root / row['file']).write_bytes(raw)
                duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
                if raw[40] not in LOOPS:
                    raise ValueError('Unsupported source loop attribute')
                frames = sample_frames(duration, pose_limit)
                clip = dict(name=Path(row['file']).stem, source_sha256=sha(raw), source_frames=duration,
                            events=row['events'], loop_attribute=raw[40], loop_semantics=LOOPS[raw[40]],
                            event_loop_boundaries=[r for r in row['events'] if r[1] in (0, 1)],
                            poses=[], status='unsupported')
                for number, frame in enumerate(frames):
                    try:
                        _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                        matrices = draw_matrices(model_blocks, pose) if envelopes else None
                        decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices) \
                            if matrices is not None else decode(model, True, bake_rigid=True, pose=pose)
                        name = f'bulblax_{species}_{clip["name"]}_{number:02}.mod'
                        conversion = write_model(decoded, root / name, 'enemy.bmd')
                        conversion.update(source='enemy.bmd', output=name,
                                          weighted_pose_baked=matrices is not None)
                        data = (root / name).read_bytes()
                        resources = resource_chunks(data)
                        if reference is not None and resources != reference:
                            raise ValueError('Bulblax pose changes immutable render resources')
                        reference = resources
                        report['total_pose_bytes'] += len(data)
                        report['total_poses'] += 1
                        clip['poses'].append(dict(file=name, frame=frame, bytes=len(data), sha256=sha(data)))
                        (root / Path(name).with_suffix('.json')).write_bytes(
                            (json.dumps(conversion, sort_keys=True, indent=2) + '\n').encode())
                    except (ValueError, KeyError, ArithmeticError) as error:
                        # Converter limitation (e.g. singular normal transform,
                        # shape without a normal attribute); recorded, never fabricated.
                        clip['poses'].append(dict(frame=frame, unsupported_reason=f'{type(error).__name__}: {error}'))
                converted = [p for p in clip['poses'] if 'file' in p]
                if converted:
                    clip['status'] = 'converted'
                else:
                    clip['unsupported_reason'] = clip['poses'][0]['unsupported_reason'] if clip['poses'] \
                        else 'no sampled frames'
                info['clips'].append(clip)
            report['species'][species] = info
        report['limitations'] = list(LIMITATIONS)
        report['extract_seconds'] = round(time.perf_counter() - started, 3)
        (output / 'bulblax.json').write_bytes((json.dumps(report, sort_keys=True, indent=2) + '\n').encode())
        (output / 'p2-bulblax.txt').write_text(TEXT)
        return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'source', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--pose-limit', type=int, default=6)
    a = p.parse_args()
    r = extract(a.iso, a.source, a.output, a.pose_limit)
    print(json.dumps({'bytes': r['total_pose_bytes'], 'poses': r['total_poses'],
                      'seconds': r['extract_seconds'],
                      'species': {s: {'clips': len(v['clips']),
                                      'converted': sum(c['status'] == 'converted' for c in v['clips']),
                                      'poses': sum(1 for c in v['clips'] for p in c['poses'] if 'file' in p),
                                      'unsupported_poses': sum(1 for c in v['clips'] for p in c['poses'] if 'file' not in p),
                                      'skinning': v['skinning']}
                                  for s, v in r['species'].items()}}, indent=2))
