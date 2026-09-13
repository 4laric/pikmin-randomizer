"""Source-backed, bounded flying-remainder import; no native actor install.

Covers enemy IDs 29 Mar (Puffy Blowhog), 55 Hanachirashi (Withering Blowhog)
and 77 ShijimiChou (Unmarked Spectralids, shared helper identity; source-only,
no runtime ownership claimed) from the US GPVE01 revision 0 disc. Source audit:
docs/PIKMIN2_FLYING_REMAINDER_ASSETS.md (issue #348, parent #166). Extraction
follows the ground-invertebrate lane: hashed disc reads, preserved metadata
text, bounded weighted/rigid pose sampling. No btk playback, no behavior
execution.
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

# Identity (EnemyID registration) is kept separate from state IDs, event
# streams and parameter values below. enemyInfo.h:88 (Mar = 29),
# enemyInfo.h:114 (Hanachirashi = 55), enemyInfo.h:136 (ShijimiChou = 77).
SPECIES = {'Mar': 29, 'Hanachirashi': 55, 'ShijimiChou': 77}
IDENTITY = {'Mar': 'Puffy Blowhog', 'Hanachirashi': 'Withering Blowhog',
            'ShijimiChou': 'Unmarked Spectralids'}
HELPER_SPECIES = ('ShijimiChou',)
SHIJIMICHOU_GROUP_COUNT = 25  # enemyInfo.h:211

PARM_SOURCE = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
MAX_POSES = 12

# Clip order equals the AnimID enum registration order and the
# enemyanimmgr.txt row order for each species.
# Mar.h:183-195, Hanachirashi.h:190-203, ShijimiChou.h:285-290.
CLIPS = {
    'Mar': ('dead', 'dead2', 'damage', 'flick', 'wait2', 'move1', 'move2',
            'type1', 'type2', 'attack'),
    'Hanachirashi': ('dead', 'dead2', 'damage', 'flick', 'wait2', 'move1',
                     'move2', 'type1', 'type2', 'attack', 'laugh'),
    'ShijimiChou': ('carry', 'dead', 'move'),
}

# Animation key events (frame, type) from each enemyanimmgr.txt on disc,
# cross-checked against docs/PIKMIN2_FLYING_REMAINDER_ASSETS.md. Event frames
# are data only: no wind attack, flick, shake-off, nectar-drop or death
# behavior executes (see LIMITATIONS).
EXPECTED_EVENTS = {
    'Mar': {
        'dead': [],
        'dead2': [],
        'damage': [[15, 2]],
        'flick': [[30, 2]],
        'wait2': [[0, 0], [39, 1]],
        'move1': [[0, 0], [39, 1]],
        'move2': [],
        'type1': [[30, 2]],
        'type2': [[5, 0], [19, 1]],
        'attack': [[50, 2]],
    },
    'Hanachirashi': {
        'dead': [],
        'dead2': [],
        'damage': [[15, 2]],
        'flick': [[25, 2]],
        'wait2': [[0, 0], [39, 1]],
        'move1': [[0, 0], [39, 1]],
        'move2': [],
        'type1': [[30, 2]],
        'type2': [[5, 0], [19, 1]],
        'attack': [[50, 2]],
        'laugh': [],
    },
    'ShijimiChou': {
        'carry': [[10, 0], [29, 1]],
        'dead': [],
        'move': [[0, 0], [7, 1]],
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
# Mar.h:20-35, Hanachirashi.h:27-43, ShijimiChou.h:41-49.
STATE_IDS = {
    'Mar': {'dead': 0, 'wait': 1, 'move': 2, 'chase': 3, 'chaseinside': 4,
            'attack': 5, 'fall': 6, 'land': 7, 'ground': 8, 'takeoff': 9,
            'flyflick': 10, 'groundflick': 11},
    'Hanachirashi': {'dead': 0, 'wait': 1, 'move': 2, 'chase': 3,
                     'chaseinside': 4, 'attack': 5, 'fall': 6, 'land': 7,
                     'ground': 8, 'takeoff': 9, 'flyflick': 10,
                     'groundflick': 11, 'laugh': 12},
    'ShijimiChou': {'wait': 0, 'fly': 1, 'fall': 2, 'dead': 3, 'leave': 4,
                    'rest': 5},
}

# Header defaults for the species-specific ProperParms block(s), construction
# order preserved. Mar.h:146-168, Hanachirashi.h:152-175, ShijimiChou.h:215-238.
PROPER_PARM_DEFAULTS = {
    'Mar': {'fp01': 90.0, 'fp02': 1.0, 'fp03': 3.0, 'fp10': 3.0, 'fp04': 3.0,
            'ip01': 10, 'fp05': 2.5, 'fp06': 5.0},
    'Hanachirashi': {'fp01': 90.0, 'fp02': 1.0, 'fp03': 3.0, 'fp10': 3.0,
                     'fp04': 3.0, 'ip01': 10, 'fp05': 2.5, 'fp06': 5.0},
    'ShijimiChou': {'fp01': 300.0, 'fp08': 100.0, 'fp02': 1.0, 'fp03': 100.0,
                    'fp04': 0.05, 'fp05': 1.0, 'fp06': 0.1, 'fp07': 0.1},
}

# Retail (disc) values verified against enemyParms.szs on US GPVE01 rev 0.
# Keys are (block, parm): 'general' is the first EnemyParmsBase block,
# 'proper' the species block. Header defaults and disc values are reported
# separately, never flattened. Audit semantics: fp01 flight height,
# fp10 ground wait time, fp04 shake-off/fall time, ip01 minimum Pikmin to
# trigger fall; ShijimiChou fp08 plant-source flight time, fp06/fp07 red/purple
# Spectralid spawn chance. Mar/Hanachirashi fp24 = 0 (wind does no HP damage).
DISC_PARMS = {
    'Mar': {
        'general': {'fp00': 3000.0, 'fp06': 120.0, 'fp09': 400.0, 'fp10': 100.0,
                    'fp12': 275.0, 'fp17': 200.0, 'fp20': 200.0, 'fp22': 300.0,
                    'fp24': 0.0, 'fp32': 125.0, 'fp34': 40.0},
        'proper': {'fp01': 80.0, 'fp02': 1.0, 'fp03': 3.0, 'fp04': 1.0,
                   'fp05': 2.5, 'fp06': 5.0, 'fp10': 1.0, 'ip01': 6},
    },
    'Hanachirashi': {
        'general': {'fp00': 1800.0, 'fp06': 100.0, 'fp09': 250.0, 'fp10': 100.0,
                    'fp12': 275.0, 'fp17': 150.0, 'fp20': 200.0, 'fp22': 300.0,
                    'fp24': 0.0, 'fp32': 80.0, 'fp34': 30.0},
        'proper': {'fp01': 70.0, 'fp02': 1.0, 'fp03': 3.0, 'fp04': 1.0,
                   'fp05': 2.5, 'fp06': 5.0, 'fp10': 1.0, 'ip01': 4},
    },
    'ShijimiChou': {
        'general': {'fp00': 200.0, 'fp06': 150.0, 'fp09': 250.0, 'fp10': 30.0,
                    'fp12': 700.0, 'fp17': 150.0, 'fp20': 30.0, 'fp22': 30.0,
                    'fp24': 10.0, 'fp32': 30.0, 'fp34': 7.0},
        'proper': {'fp01': 250.0, 'fp02': 0.2, 'fp03': 70.0, 'fp04': 0.02,
                   'fp05': 2.0, 'fp06': 0.1, 'fp07': 0.1, 'fp08': 250.0},
    },
}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = [
    'Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events, loop markers and parameter text are preserved as data only; no wind attack, flick, shake-off, nectar-drop or death behavior executes.',
    'Mar fuusen_model.btk/.brk and Hanachirashi hanachirashi_model.btk/.brk are not read by this lane; no btk playback.',
    'No native runtime, AI/FSM, install, arena placement or spiral-bridge spawning is provided by this slice.',
    'ShijimiChou is source-only helper data; full runtime ownership (group factory wiring, colour selection, nectar-roll, spawn-source attribution) belongs to the respective family owners (Tanpopo, Ooinu_l, Magaret, Damagumo, Mamuta, plant nodes) and is not wired here.',
    'Hanachirashi enemyanimmgr.txt source paths reference the Mar animation workspace (Z:\\Pikmin2Data\\conversion\\enemy\\nishimura\\Mar\\anim\\); disc archive filenames are species-scoped and do not overlap.',
]

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
TOLERANCES = {}

TEXT = (
    'P2_FLYING_1\n'
    'species Mar Hanachirashi ShijimiChou\n'
    'mar_health 3000\nmar_speed 120\nmar_flight_height 80.0\n'
    'mar_air_wait_time 3.0\nmar_ground_wait_time 1.0\nmar_fall_min_piki 6\n'
    'hanachirashi_health 1800\nhanachirashi_speed 100\n'
    'hanachirashi_flight_height 70.0\nhanachirashi_fall_min_piki 4\n'
    'shijimi_health 200\nshijimi_speed 150\nshijimi_flight_height 70.0\n'
    'shijimi_flight_duration 250.0\nshijimi_plant_flight_duration 250.0\n'
    'shijimi_red_spawn_chance 0.1\nshijimi_purple_spawn_chance 0.1\n'
    'shijimi_group_count 25\n'
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
        raise ValueError('Unknown flying-remainder species')
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
    return {'enemy_id': SPECIES[species],
            'common_name': IDENTITY[species],
            'helper_only': species in HELPER_SPECIES,
            'state_ids': dict(STATE_IDS[species]),
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
        report = dict(schema=1, policy='P2_FLYING_1',
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
            info.update(role='helper only' if species in HELPER_SPECIES
                        else 'concrete spawnable',
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
                        name = f'fly_{species}_{clip["name"]}_{number:02}.mod'
                        conversion = write_model(decoded, root / name,
                                                 'enemy.bmd')
                        conversion.update(source='enemy.bmd', output=name,
                                          weighted_pose_baked=envelopes > 0)
                        data = (root / name).read_bytes()
                        resources = resource_chunks(data)
                        if reference is not None and resources != reference:
                            raise ValueError(
                                'Flying pose changes immutable render resources')
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
        (output / 'flying.json').write_bytes(
            (json.dumps(report, sort_keys=True, indent=2) + '\n').encode())
        (output / 'p2-flying.txt').write_text(TEXT)
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
