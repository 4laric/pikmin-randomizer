"""Source-backed, bounded ground-invertebrate import; no native actor install.

Covers enemy IDs 15 Armor (Cloaking Burrow-nit), 28 ElecBug (Anode Beetle),
65 Imomushi (Ravenous Whiskerpillar), 68 TamagoMushi (Mitite), 79 Sokkuri
(Skitter Leaf) and 84 Hana (Creeping Chrysanthemum) from the US GPVE01
revision 0 disc. Source audit: docs/PIKMIN2_GROUND_INVERTEBRATE_ASSETS.md
(issue #346, parent #165). Extraction follows the Bulblax lane: hashed disc
reads, preserved metadata text, bounded weighted/rigid pose sampling. No btk
playback, no behavior execution.
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
from experimental.pikmin2_convert import blocks, decode, u16, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

SPECIES = {'Armor': 15, 'ElecBug': 28, 'Imomushi': 65,
           'TamagoMushi': 68, 'Sokkuri': 79, 'Hana': 84}

PARM_SOURCE = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
MAX_POSES = 12

# Clip order equals the AnimID enum registration order and the
# enemyanimmgr.txt row order for each species.
# Armor.h:137-149, ElecBug.h:120-130, Imomushi.h:163-174,
# TamagoMushi.h:216-224, Sokkuri.h:149-160, Hana/ChappyBase.h:150-161.
CLIPS = {
    'Armor': ('dead', 'appear', 'dive', 'move', 'attack1', 'attack2',
              'eat', 'flick', 'attack_fail', 'carry'),
    'ElecBug': ('dead', 'move', 'wait', 'charge', 'discharge', 'turn',
                'recover', 'carry'),
    'Imomushi': ('dead', 'set', 'dive', 'move1', 'move2', 'fall1', 'fall2',
                 'eat', 'carry'),
    'TamagoMushi': ('dead', 'dive', 'move', 'set', 'wait', 'carry'),
    'Sokkuri': ('run1', 'appear1', 'wait1', 'hide1', 'dead1', 'pdead1',
                'wrun1', 'flick1', 'type5'),
    'Hana': ('attack1', 'dead', 'flick', 'move1', 'type1', 'type5',
             'wait2', 'waitact1', 'attack2'),
}

# Animation key events (frame, type) from each enemyanimmgr.txt on disc,
# cross-checked against docs/PIKMIN2_GROUND_INVERTEBRATE_ASSETS.md.
EXPECTED_EVENTS = {
    'Armor': {
        'dead': [[17, 2]],
        'appear': [[15, 2], [30, 2], [45, 2]],
        'dive': [[15, 2]],
        'move': [[0, 0], [19, 1]],
        'attack1': [[15, 2]],
        'attack2': [[12, 0], [14, 1], [18, 2], [22, 3]],
        'eat': [[60, 2]],
        'flick': [[39, 2]],
        'attack_fail': [],
        'carry': [[10, 0], [29, 1]],
    },
    'ElecBug': {
        'dead': [],
        'move': [[4, 0], [13, 1]],
        'wait': [[0, 0], [9, 1]],
        'charge': [[0, 0], [9, 1]],
        'discharge': [[8, 2], [10, 0], [17, 1]],
        'turn': [[30, 0], [69, 1]],
        'recover': [],
        'carry': [[10, 0], [29, 1]],
    },
    'Imomushi': {
        'dead': [],
        'set': [],
        'dive': [],
        'move1': [[0, 0], [9, 1]],
        'move2': [[0, 0], [14, 1]],
        'fall1': [[0, 0], [9, 1]],
        'fall2': [[0, 0], [9, 1]],
        'eat': [[5, 0], [10, 2], [14, 1]],
        'carry': [[10, 0], [39, 1]],
    },
    'TamagoMushi': {
        'dead': [],
        'dive': [],
        'move': [[0, 0], [9, 1]],
        'set': [[2, 2]],
        'wait': [[0, 0], [14, 1]],
        'carry': [[10, 0], [29, 1]],
    },
    'Sokkuri': {
        'run1': [[4, 0], [19, 1]],
        'appear1': [],
        'wait1': [[0, 0], [9, 1]],
        'hide1': [[6, 2]],
        'dead1': [[14, 2]],
        'pdead1': [[8, 2]],
        'wrun1': [[6, 0], [29, 1]],
        'flick1': [[14, 2], [18, 3], [40, 4]],
        'type5': [[10, 0], [29, 1]],
    },
    'Hana': {
        'attack1': [[18, 2], [71, 3]],
        'dead': [],
        'flick': [[50, 2]],
        'move1': [[10, 0], [40, 1]],
        'type1': [[27, 2], [30, 0], [100, 1], [103, 3], [120, 4]],
        'type5': [[10, 0], [30, 1]],
        'wait2': [],
        'waitact1': [[10, 0], [40, 1]],
        'attack2': [[24, 2], [62, 3]],
    },
}

# Valid EnemyParmsBase general-block field identifiers (EnemyParmsBase.h:55-101).
# fp07 is not declared; unknown fp/ip keys must be rejected before mutation.
GENERAL_KEYS = frozenset(
    [f'fp{i:02}' for i in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                           17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                           31, 32, 33, 34, 35, 36, 37, 38)]
    + [f'ip{i:02}' for i in range(1, 8)])

# State IDs from the headers.
# Armor.h:164-181, ElecBug.h:143-155, Imomushi.h:20-37,
# TamagoMushi.h:239-247, Sokkuri.h:19-31, ChappyBase.h:176-186.
STATE_IDS = {
    'Armor': {'dead': 0, 'stay': 1, 'appear': 2, 'dive': 3, 'move': 4,
              'moveside': 5, 'movecentre': 6, 'movetop': 7, 'gohome': 8,
              'attack1': 9, 'attack2': 10, 'eat': 11, 'flick': 12, 'fail': 13},
    'ElecBug': {'dead': 0, 'wait': 1, 'turn': 2, 'move': 3, 'charge': 4,
                'discharge': 5, 'childcharge': 6, 'childdischarge': 7,
                'reverse': 8, 'return': 9},
    'Imomushi': {'dead': 0, 'wait': 1, 'falldive': 2, 'fallmove': 3,
                 'stay': 4, 'appear': 5, 'dive': 6, 'move': 7, 'gohome': 8,
                 'attack': 9, 'climb': 10, 'zukanstay': 11,
                 'zukanappear': 12, 'zukanmove': 13},
    'TamagoMushi': {'walk': 0, 'turn': 1, 'appear': 2, 'hide': 3,
                    'dead': 4, 'wait': 5},
    'Sokkuri': {'dead': 0, 'press': 1, 'stay': 2, 'appear': 3,
                'disappear': 4, 'wait': 5, 'moveground': 6, 'movewater': 7,
                'flick': 8},
    'Hana': {'turn': 0, 'dead': 1, 'flick': 2, 'walk': 3, 'attack': 4,
             'turntohome': 5, 'gohome': 6, 'sleep': 7},
}

# Header defaults for the species-specific ProperParms block(s).
# Armor.h:110-121, ElecBug.h:93-104, Imomushi.h:132-148,
# TamagoMushi.h:26-45, Sokkuri.h:34-60, ChappyBase.h:122-133.
PROPER_PARM_DEFAULTS = {
    'Armor': {'fp01': 300.0, 'fp11': 0.0, 'fp12': 100.0},
    'ElecBug': {'fp01': 5.0, 'fp02': 1.5, 'fp11': 3.0},
    'Imomushi': {'fp01': 2.0, 'fp02': 0.3, 'fp11': 10.0, 'fp90': 0.75,
                 'fp91': 0.05},
    'TamagoMushi': {'fp01': 300.0, 'fp02': 80.0, 'fp03': 1.0, 'ip01': 60,
                    'ip02': 100, 'ip03': 10, 'ip04': 50},
    'Sokkuri': {'fp01': 1.0, 'fp02': 0.0, 'fp03': 90.0, 'fp04': 45.0,
                'fp11': 0.25, 'fp12': 2.0, 'fp13': 1.0, 'fp21': 25.0,
                'fp22': 0.05, 'fp23': 1.0},
    'Hana': {'fp01': 50.0, 'fp02': 300.0, 'fp03': 400.0},
}

# Retail (disc) values verified against enemyParms.szs on US GPVE01 rev 0.
# Keys are (block, parm): 'general' is the first EnemyParmsBase block,
# 'proper' the species block. Audit-quoted semantics from the source.
DISC_PARMS = {
    'Armor': {
        'general': {'fp00': 300.0, 'fp06': 50.0, 'fp09': 400.0, 'fp10': 30.0,
                    'fp12': 200.0, 'fp20': 75.0, 'fp22': 75.0, 'fp24': 10.0,
                    'fp32': 60.0},
        'proper': {'fp01': 300.0, 'fp11': 1.0},
    },
    'ElecBug': {
        'general': {'fp00': 500.0, 'fp06': 30.0, 'fp09': 200.0, 'fp10': 100.0,
                    'fp12': 200.0, 'fp24': 10.0},
        'proper': {'fp01': 5.0, 'fp02': 1.5, 'fp11': 3.0},
    },
    'Imomushi': {
        'general': {'fp00': 200.0, 'fp06': 40.0, 'fp09': 500.0, 'fp10': 30.0,
                    'fp11': 250.0, 'fp12': 500.0, 'fp24': 1000.0},
        'proper': {'fp01': 2.0, 'fp02': 0.3, 'fp11': 10.0, 'fp90': 0.75,
                   'fp91': 0.075},
    },
    'TamagoMushi': {
        'general': {'fp00': 50.0, 'fp06': 100.0, 'fp09': 120.0, 'fp10': 30.0,
                    'fp12': 150.0},
        'proper': {'fp01': 180.0, 'fp02': 120.0, 'fp03': 1.0, 'ip01': 25,
                   'ip02': 80, 'ip03': 20, 'ip04': 90},
    },
    'Sokkuri': {
        'general': {'fp00': 120.0, 'fp06': 120.0, 'fp09': 200.0, 'fp10': 150.0,
                    'fp12': 150.0},
        'proper': {'fp01': 1.0, 'fp02': 0.0, 'fp03': 90.0, 'fp04': 30.0,
                   'fp11': 0.4, 'fp12': 3.25, 'fp13': 1.75, 'fp21': 25.0,
                   'fp22': 0.05, 'fp23': 1.0},
    },
    'Hana': {
        'general': {'fp00': 2500.0, 'fp06': 100.0, 'fp09': 300.0, 'fp10': 15.0,
                    'fp11': 70.0, 'fp12': 500.0, 'fp13': 90.0, 'fp20': 75.0,
                    'fp22': 80.0, 'fp24': 10.0, 'fp32': 100.0},
        'proper': {'fp01': 30.0, 'fp02': 2500.0},
    },
}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = [
    'Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events, loop markers and parameter text are preserved as data only; no damage, drop, birth or flick behavior executes.',
    'No native runtime, AI/FSM, install or arena placement is provided by this slice.',
    'Egg (ID 37) is a helper spawner for TamagoMushi (ID 68); not claimed by this lane (scope: #346).',
    'Hana inherits ChappyBase; its ChappyParms disc block has fp01 (foot range) and fp02 (poison) only; fp03 (wake radius) uses the ChappyBase.h:127 constructor default of 400.0.',
    'TamagoMushi manager limit overridden in generalEnemyMgr.cpp:436-443: surface=10, cave=30 (TAMAGOMUSHI_GROUP_COUNT).',
    'Sokkuri and Hana Mgr::loadModelData call setTexMtxLoadType(0x2000) for TEX1MTXIDX display list attributes; poses require the explicit draw_matrices path.',
]

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
TOLERANCES = {}

TEXT = (
    'P2_GROUND_INVERTS_1\n'
    'species Armor ElecBug Imomushi TamagoMushi Sokkuri Hana\n'
    'armor_health 300\narmor_speed 50\narmor_poison 300\narmor_attack_loop 1.0\n'
    'elecbug_health 500\nelecbug_speed 30\nelecbug_flip_time 5.0\n'
    'elecbug_wait_time 1.5\nelecbug_discharge_time 3.0\n'
    'imomushi_health 200\nimomushi_speed 40\nimomushi_climb_speed 2.0\n'
    'imomushi_eating_time 10.0\nimomushi_attack_damage 1000\n'
    'tamago_health 50\ntamago_speed 100\ntamago_survival_time 180\n'
    'tamago_honey_rate 1.0\ntamago_group_surface 10\ntamago_group_cave 30\n'
    'sokkuri_health 120\nsokkuri_speed 120\nsokkuri_wait_probability 0.4\n'
    'sokkuri_underwater_speed 25.0\n'
    'hana_health 2500\nhana_speed 100\nhana_poison 2500\nhana_foot_range 30.0\n'
    'hana_attack_damage 10\nhana_lod_radius 100\n'
    'native_ready false\ngameplay_events_executed false\nbtk_playback false\n'
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def profile(species, blocks_list, rows):
    """Validate parsed metadata for one species against the source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general,
    proper in order. ``rows`` is animation_rows(enemyanimmgr.txt) in
    registration order. Duplicate keys are rejected by the parsers upstream;
    header defaults and disc values are reported separately, never flattened.
    """
    if species not in SPECIES:
        raise ValueError('Unknown ground-invertebrate species')
    if len(blocks_list) != 3:
        raise ValueError(f'Expected 3 parameter blocks for {species}')
    general, proper = blocks_list[1], blocks_list[2]
    unknown_general = set(general) - GENERAL_KEYS
    if unknown_general:
        raise ValueError(f'Unexpected {species} general parameter keys: {sorted(unknown_general)}')
    if not set(proper) <= set(PROPER_PARM_DEFAULTS[species]):
        raise ValueError(f'Unexpected {species} proper parameter keys: {sorted(proper)}')
    for group in ('general', 'proper'):
        source = general if group == 'general' else proper
        for key, value in DISC_PARMS[species][group].items():
            if key not in source or not math.isclose(source[key], float(value),
                                                     rel_tol=0, abs_tol=1e-6):
                raise ValueError(f'{species} disc {group} parameter {key} mismatch')
    clips = tuple(Path(r['file']).stem for r in rows)
    if clips != CLIPS[species]:
        raise ValueError(f'Unexpected {species} clip registry: {clips}')
    for row in rows:
        name = Path(row['file']).stem
        if row['events'] != EXPECTED_EVENTS[species][name]:
            raise ValueError(f'{species} clip {name} key events mismatch')
    defaulted = set(PROPER_PARM_DEFAULTS[species]) - set(proper)
    return {'enemy_id': SPECIES[species], 'state_ids': dict(STATE_IDS[species]),
            'anim_id_by_clip': {name: i for i, name in enumerate(CLIPS[species])},
            'parameter_blocks': blocks_list,
            'proper_header_defaults': dict(PROPER_PARM_DEFAULTS[species]),
            'proper_retail': {k: proper[k] for k in proper},
            'proper_keys_defaulted_from_header': sorted(defaulted),
            }


def extract(iso, source, output, pose_limit=6):
    if type(pose_limit) is not int or not 2 <= pose_limit <= MAX_POSES:
        raise ValueError(f'Pose limit must be 2..{MAX_POSES}')
    if output.exists():
        raise ValueError('Output already exists')
    head = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
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
        output.mkdir(parents=True)
        report = dict(schema=1, policy='P2_GROUND_INVERTS_1',
                      disc_id=header[:6].decode(), disc_revision=header[7],
                      source_revision=head, source_sha256=source_hashes,
                      native_ready=False, gameplay_events_executed=False,
                      btk_playback=False, species={},
                      total_pose_bytes=0, total_poses=0)
        for species, identity in SPECIES.items():
            root = output / species
            root.mkdir()
            model = archive_files(
                read(f'enemy/data/{species}/model.szs'))['enemy.bmd']
            model_blocks = blocks(model)
            motions = archive_files(
                read(f'enemy/data/{species}/anim.szs'))
            names = joints(model)
            (root / 'enemy.bmd').write_bytes(model)
            metadata = {}
            for filename in METADATA_FILES:
                raw = params[species.lower() + '/' + filename]
                metadata[filename] = sha(raw)
                (root / filename).write_bytes(raw)
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
            blocks_list = parameter_blocks(
                params[species.lower() + '/enemyparm.txt'])
            rows = animation_rows(
                params[species.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
            info = profile(species, blocks_list, rows)
            info.update(role='concrete spawnable',
                        model_sha256=sha(model), joints=names,
                        metadata_sha256=metadata,
                        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                      weighted_baking=envelopes > 0,
                                      self_contained_resources=draws > 0),
                        collision=collision_nodes(
                            params[species.lower() + '/enemycoll.txt'],
                            len(names)),
                        clips=[])
            reference = None
            for row in rows:
                raw = motions[row['file']]
                (root / row['file']).write_bytes(raw)
                duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
                if raw[40] not in LOOPS:
                    raise ValueError('Unsupported source loop attribute')
                frames = sample_frames(duration, pose_limit)
                clip = dict(name=Path(row['file']).stem,
                            source_sha256=sha(raw),
                            source_frames=duration,
                            events=row['events'],
                            loop_attribute=raw[40],
                            loop_semantics=LOOPS[raw[40]],
                            event_loop_boundaries=[r for r in row['events']
                                                   if r[1] in (0, 1)],
                            poses=[], status='unsupported')
                for number, frame in enumerate(frames):
                    try:
                        tolerances = TOLERANCES.get(species, {})
                        _, pose = bca_pose(raw, frame, len(names),
                                           allow_scale=True)
                        matrices = draw_matrices(model_blocks, pose)
                        decoded = decode(model, True, bake_rigid=True,
                                         draw_matrices=matrices,
                                         **tolerances)
                        name = f'ginv_{species}_{clip["name"]}_{number:02}.mod'
                        conversion = write_model(decoded, root / name,
                                                 'enemy.bmd')
                        conversion.update(source='enemy.bmd', output=name,
                                          weighted_pose_baked=envelopes > 0)
                        data = (root / name).read_bytes()
                        resources = resource_chunks(data)
                        if reference is not None and resources != reference:
                            raise ValueError(
                                'Ground-inverts pose changes immutable render resources')
                        reference = resources
                        report['total_pose_bytes'] += len(data)
                        report['total_poses'] += 1
                        clip['poses'].append(
                            dict(file=name, frame=frame, bytes=len(data),
                                 sha256=sha(data)))
                        (root / Path(name).with_suffix('.json')).write_bytes(
                            (json.dumps(conversion, sort_keys=True, indent=2)
                             + '\n').encode())
                    except (ValueError, KeyError, ArithmeticError) as error:
                        clip['poses'].append(
                            dict(frame=frame,
                                 unsupported_reason=f'{type(error).__name__}: {error}'))
                converted = [p for p in clip['poses'] if 'file' in p]
                if converted:
                    clip['status'] = 'converted'
                else:
                    clip['unsupported_reason'] = \
                        clip['poses'][0]['unsupported_reason'] \
                        if clip['poses'] else 'no sampled frames'
                info['clips'].append(clip)
            report['species'][species] = info
        report['limitations'] = list(LIMITATIONS)
        report['extract_seconds'] = round(time.perf_counter() - started, 3)
        (output / 'ground_inverts.json').write_bytes(
            (json.dumps(report, sort_keys=True, indent=2) + '\n').encode())
        (output / 'p2-ground-inverts.txt').write_text(TEXT)
        return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'source', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--pose-limit', type=int, default=6)
    a = p.parse_args()
    r = extract(a.iso, a.source, a.output, a.pose_limit)
    print(json.dumps({
        'bytes': r['total_pose_bytes'], 'poses': r['total_poses'],
        'seconds': r['extract_seconds'],
        'species': {s: {
            'clips': len(v['clips']),
            'converted': sum(c['status'] == 'converted' for c in v['clips']),
            'poses': sum(1 for c in v['clips']
                         for p in c['poses'] if 'file' in p),
            'unsupported_poses': sum(1 for c in v['clips']
                                     for p in c['poses'] if 'file' not in p),
            'skinning': v['skinning'],
        } for s, v in r['species'].items()}
    }, indent=2))
