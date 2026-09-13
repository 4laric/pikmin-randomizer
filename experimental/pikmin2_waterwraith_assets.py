"""Source-backed, bounded Waterwraith / roller import; no native actor install.

Covers enemy IDs 98 Tyre (Waterwraith rollers, helper) and 99 BlackMan
(Waterwraith, boss) from the US GPVE01 revision 0 disc. Source audit:
docs/PIKMIN2_WATERWRAITH_ASSETS.md (issue #352, parent #175). Extraction
follows the ground-invertebrate lane: hashed disc reads, preserved metadata
text, bounded weighted/rigid pose sampling. No btk playback, no behavior
execution. Retained-asm boss FSM functions (BlackMan::walkFunc,
findNextRoutePoint and the joint-matrix callbacks) are reconstructed
evaluation-order only; nothing here claims authoritative runtime behavior.
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

SPECIES = {'Tyre': 98, 'BlackMan': 99}

PARM_SOURCE = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
MAX_POSES = 12

# Non-archive disc resources loaded alongside the model; BlackMan's material
# animation bank (blackManMgr.cpp:58-71, "/enemy/data/BlackMan/kagebozu_model.btk").
EXTRA_RESOURCES = {'Tyre': (), 'BlackMan': ('kagebozu_model.btk',)}

# Role classification: BlackMan carries EFlag_UseOwnID + BDT_Boss and is in
# IS_ENEMY_BOSS (enemyInfo.h:214-219); Tyre is its child (parentID BlackMan,
# childNum 1) with BDT_Empty and no Piklopedia entry (enemyInfo.cpp:111-112).
ROLE = {'Tyre': 'helper roller (boss child)', 'BlackMan': 'boss'}

# Clip order equals the AnimID enum registration order and the
# enemyanimmgr.txt row order for each species.
# Tyre.h:201-205, BlackMan.h:338-354.
CLIPS = {
    'Tyre': ('tyre_move', 'tyre_getoff'),
    'BlackMan': ('kagebozu_bend', 'kagebozu_bend2', 'kagebozu_dead',
                 'kagebozu_flick', 'kagebozu_flick2', 'kagebozu_getoff',
                 'kagebozu_move', 'kagebozu_recover', 'kagebozu_run',
                 'kagebozu_wait', 'kagebozu_wait2', 'kagebozu_walk',
                 'kagebozu_through', 'kagebozu_land'),
}

# Animation key events (frame, type) from each enemyanimmgr.txt on disc.
# BlackMan streams are cross-checked against docs/PIKMIN2_WATERWRAITH_ASSETS.md.
# Tyre keys are intentionally empty: the retained State machine consumes only
# the terminal KEYEVENT_END (tyreState.cpp:194) and references no per-frame
# key, so per-frame streams await disc verification.
EXPECTED_EVENTS = {
    'Tyre': {
        'tyre_move': [],
        'tyre_getoff': [],
    },
    'BlackMan': {
        'kagebozu_bend': [[4, 2], [5, 0], [24, 1]],
        'kagebozu_bend2': [[2, 2], [3, 0], [22, 1]],
        'kagebozu_dead': [[14, 2], [65, 3], [102, 4], [125, 5]],
        'kagebozu_flick': [[10, 2]],
        'kagebozu_flick2': [[12, 2]],
        'kagebozu_getoff': [[5, 2], [13, 3], [21, 4], [26, 5]],
        'kagebozu_move': [[0, 0], [29, 1]],
        'kagebozu_recover': [[14, 2], [41, 3], [43, 4], [50, 5]],
        'kagebozu_run': [[0, 0], [1, 2], [5, 3], [11, 1]],
        'kagebozu_wait': [[8, 0], [27, 1]],
        'kagebozu_wait2': [[9, 0], [28, 1]],
        'kagebozu_walk': [[7, 0], [20, 2], [35, 3], [36, 1]],
        'kagebozu_through': [[6, 0], [6, 1]],
        'kagebozu_land': [[0, 0], [0, 1], [4, 2]],
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
# Tyre.h:235-240, BlackMan.h:367-378.
STATE_IDS = {
    'Tyre': {'move': 0, 'land': 1, 'freeze': 2, 'dead': 3},
    'BlackMan': {'walk': 0, 'dead': 1, 'freeze': 2, 'bend': 3, 'escape': 4,
                 'fall': 5, 'flick': 6, 'recover': 7, 'tired': 8},
}

# Header defaults for the species-specific ProperParms block(s).
# Tyre.h:156-164 (mTyreRotationSpeed), BlackMan.h:234-270.
PROPER_PARM_DEFAULTS = {
    'Tyre': {'fp01': 0.5},
    'BlackMan': {'fp01': 10.0, 'fp02': 10.0, 'fp03': 0.1, 'fp04': 10.0,
                 'fp05': 200.0, 'fp06': 0.1, 'fp07': 10.0, 'fp11': 10.0,
                 'ip01': 300, 'ip03': 200, 'ip04': 200, 'ip05': 200,
                 'ip06': 200},
}

# Retail (disc) values read from enemyParms.szs on US GPVE01 rev 0 and recorded
# in docs/PIKMIN2_WATERWRAITH_ASSETS.md. Keys are (block, parm): 'general' is
# the first EnemyParmsBase block, 'proper' the species block. Values left out
# here are not independently asserted (header default may apply).
DISC_PARMS = {
    'Tyre': {
        'general': {'fp00': 1800.0, 'fp24': 10.0},
        'proper': {'fp01': 25.0},
    },
    'BlackMan': {
        'general': {'fp00': 1500.0},
        # Only parenthesised (disc-verified) overrides are asserted; ip03-ip06
        # are listed by the parent audit without a disc value, so they stay as
        # header defaults and are reported via proper_keys_defaulted_from_header.
        'proper': {'fp01': 20.0, 'fp02': 250.0, 'fp03': 0.2, 'fp04': 30.0,
                   'fp05': 120.0, 'fp06': 0.04, 'fp07': 3.0, 'fp11': 50.0,
                   'ip01': 0},
    },
}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = [
    'BlackMan::walkFunc, findNextRoutePoint, findNextTraceRoutePoint, setPathFinder/releasePathFinder and the l/r hand, l/r foot and body joint-matrix callbacks are reconstructed beside retained assembly (blackMan.cpp:831+); their evaluation order is inferred and is NOT authoritative behavior.',
    'Tyre::StateMove/StateLand/StateFreeze/StateDead consume only the terminal KEYEVENT_END and reference no per-frame key (tyreState.cpp:192-197); Tyre clip event streams are recorded as empty pending disc verification.',
    'Tyre is reclassified as a helper: enemyInfo.cpp:112 gives it BDT_Empty, parentID -1 with no child and it is absent from IS_ENEMY_BOSS (enemyInfo.h:214-219). BlackMan is the boss: enemyInfo.cpp:111 gives BDT_Boss with child EnemyID_Tyre x1 and it is in IS_ENEMY_BOSS.',
    'Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events, loop markers and parameter text are preserved as data only; no crush, quake, flick, fall or treasure-throw behavior executes.',
    'The BlackMan material animation bank kagebozu_model.btk is hashed and preserved but never played (btk_playback false).',
    'No native runtime, AI/FSM, cave-layout spawn hook, route finding, install or arena placement is provided by this slice.',
    'TyreTubeShadowNode/TyreShadowMgr live in plugProjectNishimuraU/TyreShadow.cpp, not the MorimuraU folder named in the lane brief.',
]

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
TOLERANCES = {}

TEXT = (
    'P2_WATERWRAITH_1\n'
    'species Tyre BlackMan\n'
    'tyre_health 1800\ntyre_attack_damage 10\ntyre_rotation_speed 25.0\n'
    'blackman_health 1500\nblackman_pod_move_speed 20.0\n'
    'blackman_escape_speed 250.0\nblackman_escape_rotation 0.2\n'
    'blackman_max_escape_rotation_step 30.0\n'
    'blackman_travel_speed 120.0\nblackman_rotation_speed 0.04\n'
    'blackman_max_rotation_step 3.0\nblackman_walking_speed 50.0\n'
    'blackman_timer_to_two_step 0\nblackman_dosin_stop_timer 200\n'
    'blackman_freeze_timer 200\nblackman_continuous_escape_timer 200\n'
    'blackman_standstill_timer 200\n'
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
        raise ValueError('Unknown waterwraith species')
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
    return {'enemy_id': SPECIES[species], 'role': ROLE[species],
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
        report = dict(schema=1, policy='P2_WATERWRAITH_1',
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
            extras = {}
            for extra in EXTRA_RESOURCES[species]:
                raw = read(f'enemy/data/{species}/{extra}')
                extras[extra] = sha(raw)
                (root / extra).write_bytes(raw)
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
            blocks_list = parameter_blocks(
                params[species.lower() + '/enemyparm.txt'])
            rows = animation_rows(
                params[species.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
            info = profile(species, blocks_list, rows)
            info.update(role=ROLE[species],
                        model_sha256=sha(model), joints=names,
                        metadata_sha256=metadata,
                        extra_resources=extras,
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
                        name = f'ww_{species}_{clip["name"]}_{number:02}.mod'
                        conversion = write_model(decoded, root / name,
                                                 'enemy.bmd')
                        conversion.update(source='enemy.bmd', output=name,
                                          weighted_pose_baked=envelopes > 0)
                        data = (root / name).read_bytes()
                        resources = resource_chunks(data)
                        if reference is not None and resources != reference:
                            raise ValueError(
                                'Waterwraith pose changes immutable render resources')
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
        (output / 'waterwraith.json').write_bytes(
            (json.dumps(report, sort_keys=True, indent=2) + '\n').encode())
        (output / 'p2-waterwraith.txt').write_text(TEXT)
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
            'role': v['role'],
            'clips': len(v['clips']),
            'converted': sum(c['status'] == 'converted' for c in v['clips']),
            'poses': sum(1 for c in v['clips']
                         for p in c['poses'] if 'file' in p),
            'unsupported_poses': sum(1 for c in v['clips']
                                     for p in c['poses'] if 'file' not in p),
            'skinning': v['skinning'],
        } for s, v in r['species'].items()}
    }, indent=2))
