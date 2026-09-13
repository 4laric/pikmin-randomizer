"""Source-backed, bounded Dweevil-family import; no native actor install.

Covers enemy IDs 59 FireOtakara (Fiery Dweevil), 60 WaterOtakara (Caustic/
Hydro Dweevil), 61 GasOtakara (Munge Dweevil), 62 ElecOtakara (Anode
Dweevil) and 93 BombOtakara (Volatile Dweevil) from the US GPVE01 revision 0
disc, plus the fixed scenery-adjacent elemental hazards 20 Hiba (fire
geyser), 21 GasHiba (gas pipe) and 22 ElecHiba (electrical wire). Source
audit: docs/PIKMIN2_DWEEVIL_ASSETS.md (issue #349, parent #170).

All five dweevils share OtakaraBase (OtakaraBase.h:11-17). They therefore
share one StateID enum, one AnimID clip bank, one ProperParms block and (per
enemyInfo.cpp:96-99,110 and OtakaraBaseMgr.cpp:24-69) one model/anim resource
bank, aliased to FireOtakara; the species differ by a procedural change
texture (FireOtakaraMgr.cpp:10, WaterOtakaraMgr.cpp:8, GasOtakaraMgr.cpp:8,
ElecOtakaraMgr.cpp:8, BombOtakaraMgr.cpp:8). Extraction follows the
ground-invertebrate lane: hashed disc reads, preserved metadata text, bounded
weighted/rigid pose sampling. No btk playback, no behavior execution. Tank
(#246) and Titan Dweevil are explicitly out of scope.
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
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

# Concrete, spawnable dweevil family. IDs from include/Game/enemyInfo.h:
# FireOtakara/WaterOtakara/GasOtakara/ElecOtakara at 118-121, BombOtakara at
# 152. Registration in src/plugProjectYamashitaU/enemyInfo.cpp:96-99,110 and
# generalEnemyMgr.cpp:409-422.
SPECIES = {'FireOtakara': 59, 'WaterOtakara': 60, 'GasOtakara': 61,
           'ElecOtakara': 62, 'BombOtakara': 93}

# Registered fixed scenery-adjacent elemental hazards. IDs from
# enemyInfo.h:79-81; registration enemyInfo.cpp:41-43 and
# generalEnemyMgr.cpp:274-282. They are NOT OtakaraBase family members and are
# NOT Piklopedia enemies: their gEnemyInfo flags carry EFlag_HasNoInfo with
# EFlag_CanBeSpawned | EFlag_UseOwnID and BDT_Empty (enemyInfo.cpp:41-43).
HAZARDS = {'Hiba': 20, 'GasHiba': 21, 'ElecHiba': 22}

PARM_SOURCE = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
MAX_POSES = 12

# enemyInfo.cpp:96-99,110 alias every dweevil onto the FireOtakara model/anim
# bank; OtakaraBaseMgr.cpp:24-69 shares the first loaded model/anim across the
# five managers. FireOtakara owns the concrete bank.
SHARED_MODEL = 'FireOtakara'

# The four shared metadata tables (anim registry, collision tree, stone info)
# live under a single `otakara/` archive folder on disc; only per-species
# `enemyparm.txt` is stored under each `<species>/` folder. Confirmed against
# enemy/parm/enemyParms.szs: fireotakara/waterotakara/gasotakara/elecotakara/
# bombotakara contain only enemyparm.txt, while otakara/ contains
# enemyanimmgr.txt, enemycoll.txt and enemystoneinfo.txt.
SHARED_PARM = 'otakara'

# Per-species procedural change textures loaded by each Mgr::loadTexData.
CHANGE_TEXTURES = {
    'FireOtakara': '/enemy/data/FireOtakara/otakara_red_s3tc.bti',
    'WaterOtakara': '/enemy/data/WaterOtakara/otakara_blue_s3tc.bti',
    'GasOtakara': '/enemy/data/GasOtakara/otakara_purple_s3tc.bti',
    'ElecOtakara': '/enemy/data/ElecOtakara/otakara_yellow_s3tc.bti',
    'BombOtakara': '/enemy/data/BombOtakara/otakara_bomb_s3tc.bti',
}

# Clip order equals the shared AnimID enum (OtakaraBase.h:179-193) and the
# shared otakara/enemyanimmgr.txt registration order (confirmed on disc).
# Slot 4 / OTAKARAANIM_TakeItem is the on-disc `takeitem` stem; `dead` and
# `carry` are the enum's trailing unannotated slots and are both registered on
# disc. The 12 stems and their order are read verbatim from
# otakara/enemyanimmgr.txt, not inferred.
CLIPS = ('wait1', 'move1', 'pivot1', 'attack1', 'takeitem', 'wait2', 'move2',
         'pivot2', 'attack2', 'dropitem2', 'dead', 'carry')

# Ordered gameplay key-event types the shared FSM reads from each clip:
#   2 = flick Pikmin (StateFlick/StateItemFlick) or take/fall treasure
#       (StateTake, StateItemDrop; OtakaraBase.cpp:321-327)
#   3 = end charge / create discharge effect (StateFlick, StateItemFlick)
# Event type 0 and 1 are loop markers (start/end), not gameplay events; the
# disc otakara/enemyanimmgr.txt uses only 0/1/2/3 (no 1000 sentinel).
GAMEPLAY_EVENT_TYPES = (2, 3)

# Key events are recorded as the ordered tuple of source-read gameplay types,
# never as fabricated frame numbers. These tuples are the exact disc
# otakara/enemyanimmgr.txt streams filtered to GAMEPLAY_EVENT_TYPES (frame
# numbers come from the disc registration and are preserved in extraction).
EXPECTED_EVENTS = {
    'wait1': (),
    'move1': (),
    'pivot1': (),
    'attack1': (2, 3),
    'takeitem': (2,),
    'wait2': (),
    'move2': (),
    'pivot2': (),
    'attack2': (2, 3),
    'dropitem2': (2,),
    'dead': (),
    'carry': (),
}

# Valid EnemyParmsBase general-block field identifiers (EnemyParmsBase.h:55-101).
# fp07 is not declared; unknown fp/ip keys must be rejected before mutation.
GENERAL_KEYS = frozenset(
    [f'fp{i:02}' for i in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                           17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                           31, 32, 33, 34, 35, 36, 37, 38)]
    + [f'ip{i:02}' for i in range(1, 8)])

# Shared StateID enum, OtakaraBase.h:22-39 (OTA_Null = -1 and OTA_Count
# excluded). Every dweevil registers the same 14-state FSM
# (OtakaraBaseState.cpp:14-34), including the Bomb-carry states used only by
# BombOtakara.
STATE_IDS = {'dead': 0, 'flick': 1, 'wait': 2, 'move': 3, 'turn': 4,
             'take': 5, 'item_wait': 6, 'item_move': 7, 'item_turn': 8,
             'item_flick': 9, 'item_drop': 10, 'bomb_wait': 11,
             'bomb_move': 12, 'bomb_turn': 13}

# Header (build-time) defaults for the shared ProperParms block,
# OtakaraBase.h:150-156. These are NOT disc values.
PROPER_PARM_DEFAULTS = {'fp01': 100.0, 'fp10': 1.0, 'fp11': 1.25, 'fp21': 2.5}

# Retail general block, verbatim from the US GPVE01 rev 0 disc
# `<species>/enemyparm.txt` (the shared Otakara general block; Fire/Elec share
# this exact block). Spot-check subset consumed by profile(); the disc carries
# fp00-fp38 + ip01-ip07 (45 keys, no fp07).
_OTA_GENERAL = {
    'fp00': 150.0, 'fp01': 30.0, 'fp02': 0.1, 'fp03': 0.1, 'fp04': 0.5,
    'fp05': 0.01, 'fp06': 80.0, 'fp08': 0.25, 'fp09': 200.0, 'fp10': 75.0,
    'fp11': 70.0, 'fp12': 200.0, 'fp13': 180.0, 'fp14': 300.0, 'fp15': 90.0,
    'fp16': 1.0, 'fp17': 250.0, 'fp18': 1.0, 'fp19': 25.0, 'fp20': 25.0,
    'fp21': 25.0, 'fp22': 60.0, 'fp23': 0.0, 'fp24': 10.0, 'fp25': 50.0,
    'fp26': 50.0, 'fp27': 75.0, 'fp28': 4.0, 'fp29': 15.0, 'fp30': 50.0,
    'fp31': 0.0, 'fp32': 50.0, 'fp33': 25.0, 'fp34': 5.0, 'fp35': 1.0,
    'fp36': 50.0, 'fp37': 1.0, 'fp38': 5.0,
    'ip01': 6.0, 'ip02': 5.0, 'ip03': 12.0, 'ip04': 10.0, 'ip05': 17.0,
    'ip06': 20.0, 'ip07': 22.0,
}

# Retail (disc) values read from the US GPVE01 rev 0 `<species>/enemyparm.txt`
# tables. Keys are (block, parm): 'general' is the EnemyParmsBase block,
# 'proper' the shared OtakaraBase::ProperParms block. Retail proper fp01 is 80
# for Fire/Water/Elec/Bomb (header default 100) and 100 for Gas, so header
# defaults and disc values are reported separately and never flattened.
DISC_PARMS = {
    'FireOtakara': {'general': dict(_OTA_GENERAL),
                    'proper': {'fp01': 80.0, 'fp10': 1.0, 'fp11': 1.25, 'fp21': 2.5}},
    'WaterOtakara': {'general': {**_OTA_GENERAL, 'fp24': 0.0},
                     'proper': {'fp01': 80.0, 'fp10': 1.0, 'fp11': 1.25, 'fp21': 2.5}},
    'GasOtakara': {'general': {**_OTA_GENERAL, 'fp00': 350.0, 'fp06': 100.0, 'fp24': 0.0},
                   'proper': {'fp01': 100.0, 'fp10': 1.0, 'fp11': 1.25, 'fp21': 2.5}},
    'ElecOtakara': {'general': dict(_OTA_GENERAL),
                    'proper': {'fp01': 80.0, 'fp10': 1.0, 'fp11': 1.25, 'fp21': 2.5}},
    'BombOtakara': {'general': {**_OTA_GENERAL, 'fp24': 0.0, 'fp37': 0.0},
                    'proper': {'fp01': 80.0, 'fp10': 1.0, 'fp11': 1.25, 'fp21': 2.5}},
}

# Fixed-hazard classification. These managers ARE registered spawnables
# (generalEnemyMgr.cpp:274-282) but carry EFlag_HasNoInfo and BDT_Empty
# (enemyInfo.cpp:41-43), i.e. fixed scenery-adjacent elemental hazards with no
# Piklopedia/creature identity. This is the explicit reclassification the lane
# records instead of treating them as the "enemy" IDs they are numbered as.
HAZARD_CLASSIFICATION = {
    'Hiba': {
        'classification': 'fixed scenery-adjacent fire hazard',
        'registered': True,
        'role': 'static fire geyser; spawnable but no Piklopedia info',
        'evidence': 'enemyInfo.cpp:41 EFlag_HasNoInfo|EFlag_CanBeSpawned|2|EFlag_UseOwnID, BDT_Empty; generalEnemyMgr.cpp:274',
    },
    'GasHiba': {
        'classification': 'fixed scenery-adjacent gas hazard',
        'registered': True,
        'role': 'static gas pipe; spawnable but no Piklopedia info; bridge/gate linked',
        'evidence': 'enemyInfo.cpp:42 EFlag_HasNoInfo|EFlag_CanBeSpawned|2|EFlag_UseOwnID, BDT_Empty; generalEnemyMgr.cpp:277',
    },
    'ElecHiba': {
        'classification': 'fixed scenery-adjacent electric hazard',
        'registered': True,
        'role': 'static two-node electric wire; spawnable but no Piklopedia info',
        'evidence': 'enemyInfo.cpp:43 EFlag_HasNoInfo|EFlag_CanBeSpawned|2|EFlag_UseOwnID, BDT_Empty; generalEnemyMgr.cpp:280; ElecHibaMgr.cpp:110-131 two-node birth',
    },
}

# Header defaults for the hazard ProperParms blocks. Hiba.h:85-115 (fp02 wait,
# fp01 active, fp03 stop, fp90/fp91 LOD), GasHiba.h:98-130 (adds fp03 attack
# start, shifts stop to fp04), ElecHiba.h:125-157 (wait fp02, warning fp03,
# active fp01, stop fp04, fp90/fp91).
HAZARD_PROPER_PARM_DEFAULTS = {
    'Hiba': {'fp02': 2.5, 'fp01': 2.5, 'fp03': 10.0, 'fp90': 0.085, 'fp91': 0.05},
    'GasHiba': {'fp02': 2.5, 'fp01': 2.5, 'fp03': 1.0, 'fp04': 10.0,
                'fp90': 0.085, 'fp91': 0.05},
    'ElecHiba': {'fp02': 2.5, 'fp03': 2.5, 'fp01': 2.5, 'fp04': 10.0,
                 'fp90': 0.085, 'fp91': 0.05},
}

# Hazard state IDs. Hiba.h:136-141 and GasHiba.h:151-156 share
# Dead/Wait/Attack; ElecHiba.h:197-203 adds Sign. Hazard AnimID banks:
# Hiba.h:117-121 and GasHiba.h:132-136 (wait, attack); ElecHiba.h:179-182
# (wait only).
HAZARD_STATE_IDS = {
    'Hiba': {'dead': 0, 'wait': 1, 'attack': 2},
    'GasHiba': {'dead': 0, 'wait': 1, 'attack': 2},
    'ElecHiba': {'dead': 0, 'wait': 1, 'sign': 2, 'attack': 3},
}
HAZARD_CLIPS = {
    'Hiba': ('wait', 'attack'),
    'GasHiba': ('wait', 'attack'),
    'ElecHiba': ('wait',),
}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = [
    'Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events, loop markers and parameter text are preserved as data only; no fire/bubble/gas/electric discharge, treasure theft, flick or Bomb detonation behavior executes.',
    'All five dweevils share one OtakaraBase model/anim bank aliased to FireOtakara (enemyInfo.cpp:96-99,110; OtakaraBaseMgr.cpp:24-69); per-species identity is a procedural change texture only, so no per-species model is claimed.',
    'BombOtakara relies on the separate EnemyID_Bomb payload (enemyInfo.cpp:110 childID); payload birth, mCarrier linkage and explosion lifetime are owned by the Bomb implementation and are not reproduced here.',
    'Hiba/GasHiba/ElecHiba are registered spawnables flagged EFlag_HasNoInfo (enemyInfo.cpp:41-43); they are reclassified here as fixed scenery-adjacent hazards, not Piklopedia enemies, and only their source/parm contract is recorded.',
    'Exact animation key-event frames are re-extracted from the disc .bca/registration and preserved verbatim; EXPECTED_EVENTS records the ordered disc gameplay event types, and the disc .bca files remain the frame authority.',
    'The 12 clip stems and their order are read verbatim from otakara/enemyanimmgr.txt (slot 4 is the on-disc takeitem stem; dead/carry are registered); the shared anim/collision/stone tables live under otakara/ while only enemyparm.txt is per-species, as confirmed on disc.',
    'No native runtime, AI/FSM, install or arena placement is provided by this slice.',
    'Tank (done) and Titan Dweevil / BigTreasure (#246) are explicitly out of scope for this lane.',
]

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
TOLERANCES = {}

TEXT = (
    'P2_OTA_DWEEVIL_1\n'
    'species FireOtakara WaterOtakara GasOtakara ElecOtakara BombOtakara\n'
    'hazards Hiba GasHiba ElecHiba\n'
    'shared_base Otakara model FireOtakara\n'
    'fire_health 150\nfire_speed 80\nfire_attack 10\nfire_otakara_life 80\n'
    'water_health 150\nwater_speed 80\nwater_attack 0\nwater_otakara_life 80\n'
    'gas_health 350\ngas_speed 100\ngas_attack 0\ngas_otakara_life 100\n'
    'elec_health 150\nelec_speed 80\nelec_attack 10\nelec_otakara_life 80\n'
    'bomb_health 150\nbomb_speed 80\nbomb_attack 0\nbomb_otakara_life 80\n'
    'native_ready false\ngameplay_events_executed false\nbtk_playback false\n'
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _gameplay_events(events):
    """Ordered gameplay event types from a parsed animation row."""
    return tuple(event[1] for event in events if event[1] in GAMEPLAY_EVENT_TYPES)


def profile(species, blocks_list, rows):
    """Validate parsed metadata for one dweevil against the source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general,
    proper in order. ``rows`` is animation_rows(enemyanimmgr.txt) in
    registration order. Duplicate keys are rejected by the parsers upstream;
    header defaults and disc values are reported separately, never flattened.
    """
    if species not in SPECIES:
        raise ValueError('Unknown dweevil species')
    if len(blocks_list) != 3:
        raise ValueError(f'Expected 3 parameter blocks for {species}')
    general, proper = blocks_list[1], blocks_list[2]
    unknown_general = set(general) - GENERAL_KEYS
    if unknown_general:
        raise ValueError(f'Unexpected {species} general parameter keys: {sorted(unknown_general)}')
    if not set(proper) <= set(PROPER_PARM_DEFAULTS):
        raise ValueError(f'Unexpected {species} proper parameter keys: {sorted(proper)}')
    for group in ('general', 'proper'):
        source = general if group == 'general' else proper
        for key, value in DISC_PARMS[species][group].items():
            if key not in source or not math.isclose(source[key], float(value),
                                                     rel_tol=0, abs_tol=1e-6):
                raise ValueError(f'{species} disc {group} parameter {key} mismatch')
    clips = tuple(Path(r['file']).stem for r in rows)
    if clips != CLIPS:
        raise ValueError(f'Unexpected {species} clip registry: {clips}')
    for row in rows:
        name = Path(row['file']).stem
        if _gameplay_events(row['events']) != EXPECTED_EVENTS[name]:
            raise ValueError(f'{species} clip {name} key event stream mismatch')
    defaulted = set(PROPER_PARM_DEFAULTS) - set(proper)
    return {'enemy_id': SPECIES[species], 'shared_base': 'OtakaraBase',
            'state_ids': dict(STATE_IDS),
            'anim_id_by_clip': {name: i for i, name in enumerate(CLIPS)},
            'parameter_blocks': blocks_list,
            'proper_header_defaults': dict(PROPER_PARM_DEFAULTS),
            'proper_retail': {k: proper[k] for k in proper},
            'proper_keys_defaulted_from_header': sorted(defaulted),
            'role': 'concrete spawnable',
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
        report = dict(schema=1, policy='P2_OTA_DWEEVIL_1',
                      disc_id=header[:6].decode(), disc_revision=header[7],
                      source_revision=head, source_sha256=source_hashes,
                      native_ready=False, gameplay_events_executed=False,
                      btk_playback=False,
                      shared_base=dict(model=SHARED_MODEL, clips=list(CLIPS)),
                      species={}, hazards={},
                      total_pose_bytes=0, total_poses=0)

        # The five dweevils share one model/anim bank (enemyInfo.cpp:96-99,110;
        # OtakaraBaseMgr.cpp:24-69), read once and written into each species.
        model = archive_files(
            read(f'enemy/data/{SHARED_MODEL}/model.szs'))['enemy.bmd']
        model_blocks = blocks(model)
        motions = archive_files(read(f'enemy/data/{SHARED_MODEL}/anim.szs'))
        names = joints(model)
        if sorted(motions) != sorted(name + '.bca' for name in CLIPS):
            raise ValueError(f'anim.szs members mismatch: {sorted(motions)}')

        for species, identity in SPECIES.items():
            root = output / species
            root.mkdir()
            (root / 'enemy.bmd').write_bytes(model)
            metadata = {}
            for filename in METADATA_FILES:
                folder = species.lower() if filename == 'enemyparm.txt' else SHARED_PARM
                raw = params[folder + '/' + filename]
                metadata[filename] = sha(raw)
                (root / filename).write_bytes(raw)
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
            blocks_list = parameter_blocks(
                params[species.lower() + '/enemyparm.txt'])
            rows = animation_rows(
                params[SHARED_PARM + '/enemyanimmgr.txt'].decode('shift_jis'))
            info = profile(species, blocks_list, rows)
            info.update(model_sha256=sha(model), joints=names,
                        change_texture=CHANGE_TEXTURES[species],
                        metadata_sha256=metadata,
                        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                      weighted_baking=envelopes > 0,
                                      self_contained_resources=draws > 0),
                        collision=collision_nodes(
                            params[SHARED_PARM + '/enemycoll.txt'],
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
                            event_types=list(_gameplay_events(row['events'])),
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
                        name = f'ota_{species}_{clip["name"]}_{number:02}.mod'
                        conversion = write_model(decoded, root / name,
                                                 'enemy.bmd')
                        conversion.update(source='enemy.bmd', output=name,
                                          weighted_pose_baked=envelopes > 0)
                        data = (root / name).read_bytes()
                        resources = resource_chunks(data)
                        if reference is not None and resources != reference:
                            raise ValueError(
                                'Dweevil pose changes immutable render resources')
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

        # Fixed hazards: source/parm contract only, no pose conversion.
        for species, identity in HAZARDS.items():
            root = output / 'hazards' / species
            root.mkdir(parents=True)
            metadata = {}
            for filename in METADATA_FILES:
                key = species.lower() + '/' + filename
                if key not in params:
                    continue
                raw = params[key]
                metadata[filename] = sha(raw)
                (root / filename).write_bytes(raw)
            classification = dict(HAZARD_CLASSIFICATION[species])
            classification.update(
                enemy_id=identity,
                state_ids=dict(HAZARD_STATE_IDS[species]),
                clips=list(HAZARD_CLIPS[species]),
                proper_header_defaults=dict(HAZARD_PROPER_PARM_DEFAULTS[species]),
                metadata_sha256=metadata)
            report['hazards'][species] = classification

        report['limitations'] = list(LIMITATIONS)
        manifest = {k: v for k, v in report.items()
                    if k != 'extract_seconds'}
        (output / 'dweevils.json').write_bytes(
            (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
        report['extract_seconds'] = round(time.perf_counter() - started, 3)
        (output / 'p2-dweevils.txt').write_text(TEXT)
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
        } for s, v in r['species'].items()},
        'hazards': {h: v['classification'] for h, v in r['hazards'].items()},
    }, indent=2))
