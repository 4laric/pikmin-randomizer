"""Source-backed, bounded Snagret/Crawbster import; no native actor install.

Covers enemy IDs 34 SnakeCrow (Burrowing Snagret), 70 SnakeWhole (Pileated
Snagret) and 94 DangoMushi (Segmented Crawbster) from the US GPVE01 revision 0
disc. Source audit: docs/PIKMIN2_SNAGRET_ASSETS.md (issue #351, parent #174).
Extraction follows the ground-invertebrate lane: hashed disc reads, preserved
metadata text, bounded weighted/rigid pose sampling. No btk playback, no
behavior execution.

The two snagrets are a shared-base pair: `Game::SnakeJointMgr` drives the
`bodyjnt3`-`bodyjnt8` spine for both `SnakeCrow` and `SnakeWhole`
(SnakeJointMgr.h:30, SnakeCrow.cpp:1471, SnakeWhole.cpp:1898). DangoMushi is a
distinct segmented-body boss that inherits `EnemyBase` directly and uses
`EnemyBlendAnimatorBase`, with no `SnakeJointMgr` and no `ChappyBase`
relationship (DangoMushi.h:72,224).
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
from experimental.pikmin2_breadbug_assets import parameter_blocks, collision_nodes
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

# Concrete spawnable boss family. IDs from include/Game/enemyInfo.h:
# EnemyID_SnakeCrow=34 (enemyInfo.h:93), EnemyID_SnakeWhole=70
# (enemyInfo.h:129), EnemyID_DangoMushi=94 (enemyInfo.h:153). All three are in
# IS_ENEMY_BOSS (enemyInfo.h:214-219) and registered in
# src/plugProjectYamashitaU/generalEnemyMgr.cpp:316,447,497.
SPECIES = {'SnakeCrow': 34, 'SnakeWhole': 70, 'DangoMushi': 94}

PARM_SOURCE = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
MAX_POSES = 12

# Clip order equals each species' AnimID enum (the order registered in
# enemyanimmgr.txt) and the .bca member names in anim.szs. The attack stems are
# the disc spellings `hit_near`/`hit`/`hit_far` (SnakeCrow.h:232-236,
# SnakeWhole.h:230-234) and DangoMushi's flick clip is `attack_2`
# (DangoMushi.h:210-222). SnakeCrow.h:225-243 (13 slots),
# SnakeWhole.h:223-242 (14 slots), DangoMushi.h:210-222 (9 slots).
CLIPS = {
    'SnakeCrow': ('dead', 'appear1', 'appear2', 'dive', 'hit_near', 'hit',
                  'hit_far', 'hit_r', 'hit_l', 'wait1', 'waitact1',
                  'waitact2', 'type5'),
    'SnakeWhole': ('dead', 'appear1', 'appear2', 'dive', 'hit_near', 'hit',
                   'hit_far', 'hit_r', 'hit_l', 'wait1', 'waitact1',
                   'waitact2', 'run1', 'type5'),
    'DangoMushi': ('fly', 'wait', 'move', 'attack', 'attack_2', 'turn',
                   'recover', 'dead', 'carry'),
}

# Exact (frame, type) key events read from each species' enemyanimmgr.txt on
# the US GPVE01 rev 0 disc. Types: 0 = KEYEVENT_LOOP_START, 1 =
# KEYEVENT_LOOP_END, 2 = spawn/impact effect hook, 3 = joint callback or
# swallow/attack hook, 4 = joint return or looping phase hook, 5/6 = late
# appearance beats. KEYEVENT_END (1000) is generated when a clip completes, so
# it is not recorded in the registration; the trailing `-1` terminator is the
# registry sentinel, not an event.
#
# FSM reads: SnakeCrowState.cpp:58-87 (dead), :245-272 (appear1), :313-353
# (appear2), :395-424 (dive), :456-526 (wait), :554-632 (attack), :657-687
# (eat), :713-738 (struggle).
# SnakeWholeState.cpp:60-90 (dead), :251-301 (appear1), :343-398 (appear2),
# :433-474 (dive), :510-541 (wait), :568-626 (walk/run1), :654-695 (home),
# :722-817 (attack), :842-887 (eat), :913-951 (struggle).
# DangoMushiState.cpp:53-78 (dead), :171-212 (appear/fly), :249-287 (wait),
# :316-379 (move), :411-465 (attack), :507-554 (turn), :587-607 (recover),
# :637-670 (flick/attack_2). Only turn.bca emits LOOP_START (0) and attack.bca
# emits LOOP_END (1) with the roll gate (DangoMushiState.cpp:448,530).
EXPECTED_EVENTS = {
    'SnakeCrow': {
        'dead': [[67, 2], [75, 2], [110, 5], [131, 3], [143, 4], [149, 4]],
        'appear1': [[14, 2]],
        'appear2': [[20, 2], [58, 3], [115, 4], [141, 5]],
        'dive': [[12, 2], [28, 3]],
        'hit_near': [[33, 2], [36, 3], [48, 4]],
        'hit': [[32, 2], [34, 3], [48, 4]],
        'hit_far': [[32, 2], [36, 3], [48, 4]],
        'hit_r': [[28, 2], [32, 3], [48, 4]],
        'hit_l': [[28, 2], [32, 3], [48, 4]],
        'wait1': [[0, 0], [49, 1]],
        'waitact1': [[42, 2]],
        'waitact2': [[0, 0], [19, 1]],
        'type5': [[10, 0], [29, 1]],
    },
    'SnakeWhole': {
        'dead': [[65, 5], [89, 2], [118, 3], [131, 4]],
        'appear1': [[13, 2], [17, 3], [30, 4]],
        'appear2': [[20, 2], [58, 3], [115, 4], [145, 5], [159, 6]],
        'dive': [[12, 2], [31, 3], [33, 4], [45, 5]],
        'hit_near': [[33, 2], [36, 3], [48, 4]],
        'hit': [[32, 2], [34, 3], [48, 4]],
        'hit_far': [[32, 2], [36, 3], [48, 4]],
        'hit_r': [[28, 2], [32, 3], [48, 4]],
        'hit_l': [[28, 2], [32, 3], [48, 4]],
        'wait1': [[0, 0], [49, 1]],
        'waitact1': [[42, 2]],
        'waitact2': [[0, 0], [19, 1]],
        'run1': [[10, 0], [10, 2], [32, 3], [34, 1]],
        'type5': [[10, 0], [29, 1]],
    },
    'DangoMushi': {
        'fly': [[13, 2], [30, 3], [35, 4]],
        'wait': [[0, 0], [39, 1]],
        'move': [[0, 0], [8, 2], [19, 1]],
        'attack': [[6, 2], [17, 3], [23, 4], [50, 0], [100, 1], [118, 5]],
        'attack_2': [[26, 2], [32, 3], [38, 2], [50, 3], [57, 2], [65, 3]],
        'turn': [[10, 2], [32, 0], [81, 1], [108, 3], [114, 4]],
        'recover': [[20, 2]],
        'dead': [[32, 2], [40, 3]],
        'carry': [[10, 0], [29, 1]],
    },
}

# Valid EnemyParmsBase general-block field identifiers (EnemyParmsBase.h:55-101).
# fp07 is not declared; unknown fp/ip keys must be rejected before mutation.
GENERAL_KEYS = frozenset(
    [f'fp{i:02}' for i in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                           17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                           31, 32, 33, 34, 35, 36, 37, 38)]
    + [f'ip{i:02}' for i in range(1, 8)])

# Header (build-time) defaults for the general EnemyParmsBase block
# (EnemyParmsBase.h:55-101). These are NOT disc values; retail general values
# are kept separately in DISC_PARMS and the two are never flattened.
GENERAL_DEFAULTS = {
    'fp00': 100.0, 'fp27': 50.0, 'fp31': 0.01, 'fp30': 30.0, 'fp01': 40.0,
    'fp33': 40.0, 'fp34': 40.0, 'fp32': 40.0, 'fp02': 0.2, 'fp03': 0.25,
    'fp04': 0.35, 'fp05': 1.0, 'fp06': 80.0, 'fp08': 0.1, 'fp28': 10.0,
    'fp09': 200.0, 'fp10': 15.0, 'fp11': 70.0, 'fp12': 200.0, 'fp25': 50.0,
    'fp13': 90.0, 'fp14': 200.0, 'fp26': 50.0, 'fp15': 120.0, 'fp17': 300.0,
    'fp18': 0.0, 'fp19': 120.0, 'fp16': 1.0, 'fp20': 70.0, 'fp21': 15.0,
    'fp22': 70.0, 'fp23': 15.0, 'fp24': 10.0, 'fp29': 15.0, 'fp35': 1.0,
    'fp36': 10.0, 'fp37': 0.05, 'fp38': 10.0,
    'ip01': 3, 'ip02': 3, 'ip03': 8, 'ip04': 5, 'ip05': 15, 'ip06': 10,
    'ip07': 30,
}

# State IDs from the headers.
# SnakeCrow.h:54-66 (9 states), SnakeWhole.h:53-67 (11 states),
# DangoMushi.h:23-35 (9 states). Registration order matches the enum.
STATE_IDS = {
    'SnakeCrow': {'dead': 0, 'stay': 1, 'appear1': 2, 'appear2': 3,
                  'disappear': 4, 'wait': 5, 'attack': 6, 'eat': 7,
                  'struggle': 8},
    'SnakeWhole': {'dead': 0, 'stay': 1, 'appear1': 2, 'appear2': 3,
                   'disappear': 4, 'wait': 5, 'walk': 6, 'home': 7,
                   'attack': 8, 'eat': 9, 'struggle': 10},
    'DangoMushi': {'dead': 0, 'stay': 1, 'appear': 2, 'wait': 3, 'move': 4,
                   'attack': 5, 'turn': 6, 'recover': 7, 'flick': 8},
}

# Header defaults for the species-specific ProperParms block(s).
# SnakeCrow.h:196-209 (fp01/fp11/fp12/fp21/fp31),
# SnakeWhole.h:197-207 (fp01/fp11/fp12/fp21),
# DangoMushi.h:46-56 (fp01/fp02/fp03/fp10).
PROPER_PARM_DEFAULTS = {
    'SnakeCrow': {'fp01': 0.8, 'fp11': 2.0, 'fp12': 1.0, 'fp21': 300.0,
                  'fp31': 7500.0},
    'SnakeWhole': {'fp01': 0.8, 'fp11': 2.0, 'fp12': 1.0, 'fp21': 300.0},
    'DangoMushi': {'fp01': 200.0, 'fp02': 0.1, 'fp03': 10.0, 'fp10': 7.5},
}

# Retail (disc) values re-read directly from enemy/parm/enemyParms.szs on the
# supplied US GPVE01 rev 0 disc and cross-checked against the published US
# Pikmin 2 enemy property listings (Pikipedia "Pikmin 2 enemy properties",
# pages 1-4). Keys are (block, parm): 'general' is the EnemyParmsBase block,
# 'proper' the species block. The disc proper blocks do NOT match the header
# constructor defaults (SnakeCrow fp01 0.6 vs 0.8; SnakeWhole fp11 0.5 vs 2.0;
# DangoMushi fp02 0.03 vs 0.1, fp03 3.0 vs 10.0), and the DangoMushi disc block
# omits fp10 entirely, so the header default 7.5 stays in
# PROPER_PARM_DEFAULTS and is reported as defaulted. The two are kept separate
# and never flattened. Notable retail facts: SnakeCrow is stationary (fp06=0)
# with a low 80-unit territory (the White Flower Garden cave overrides its
# health to the proper fp31 `mWFGHealth`, SnakeCrow.cpp:95-105); SnakeWhole's
# high fp06=1000 is the leaping walk speed; DangoMushi is the only roller
# (fp20=300 ranged shock, fp28=5 max turn).
DISC_PARMS = {
    'SnakeCrow': {
        'general': {'fp00': 1500.0, 'fp01': 15.0, 'fp02': 0.025,
                    'fp03': 0.025, 'fp04': 0.4, 'fp05': 0.0001, 'fp06': 0.0,
                    'fp08': 0.1, 'fp09': 80.0, 'fp10': 100.0, 'fp11': 100.0,
                    'fp12': 150.0, 'fp13': 90.0, 'fp14': 0.0, 'fp15': 0.0,
                    'fp16': 1.0, 'fp17': 200.0, 'fp18': 1.0, 'fp19': 40.0,
                    'fp20': 0.0, 'fp21': 0.0, 'fp22': 0.0, 'fp23': 0.0,
                    'fp24': 10.0, 'fp25': 100.0, 'fp26': 0.0, 'fp27': 50.0,
                    'fp28': 10.0, 'fp29': 0.0, 'fp30': 0.0, 'fp31': 0.0,
                    'fp32': 225.0, 'fp33': 111.0, 'fp34': 5.0, 'fp35': 1.0,
                    'fp36': 50.0, 'fp37': 0.1, 'fp38': 5.0, 'ip01': 15,
                    'ip02': 4, 'ip03': 25, 'ip04': 8, 'ip05': 30, 'ip06': 12,
                    'ip07': 35},
        'proper': {'fp01': 0.6, 'fp11': 2.5, 'fp12': 2.5, 'fp21': 200.0,
                   'fp31': 2500.0},
    },
    'SnakeWhole': {
        'general': {'fp00': 5000.0, 'fp01': 20.0, 'fp02': 0.025,
                    'fp03': 0.025, 'fp04': 0.4, 'fp05': 0.0001, 'fp06': 1000.0,
                    'fp09': 380.0, 'fp10': 100.0, 'fp11': 100.0,
                    'fp12': 400.0, 'fp13': 90.0, 'fp14': 0.0, 'fp15': 0.0,
                    'fp16': 1.0, 'fp17': 200.0, 'fp18': 1.0, 'fp19': 40.0,
                    'fp20': 0.0, 'fp21': 0.0, 'fp22': 0.0, 'fp23': 0.0,
                    'fp24': 10.0, 'fp25': 100.0, 'fp26': 0.0, 'fp27': 50.0,
                    'fp28': 10.0, 'fp29': 0.0, 'fp30': 0.0, 'fp31': 0.0,
                    'fp32': 225.0, 'fp33': 130.0, 'fp34': 5.0, 'fp35': 1.0,
                    'fp36': 50.0, 'fp37': 0.01, 'fp38': 5.0, 'ip01': 15,
                    'ip02': 4, 'ip03': 25, 'ip04': 8, 'ip05': 30, 'ip06': 12,
                    'ip07': 35},
        'proper': {'fp01': 0.6, 'fp11': 0.5, 'fp12': 2.5, 'fp21': 400.0},
    },
    'DangoMushi': {
        'general': {'fp00': 3000.0, 'fp01': 70.0, 'fp02': 0.1, 'fp03': 0.1,
                    'fp04': 0.35, 'fp05': 0.0001, 'fp06': 50.0, 'fp08': 0.05,
                    'fp09': 150.0, 'fp10': 100.0, 'fp11': 150.0,
                    'fp12': 500.0, 'fp13': 90.0, 'fp14': 500.0, 'fp15': 90.0,
                    'fp16': 1.0, 'fp17': 200.0, 'fp18': 1.0, 'fp19': 100.0,
                    'fp20': 300.0, 'fp21': 15.0, 'fp22': 100.0, 'fp23': 45.0,
                    'fp24': 10.0, 'fp25': 100.0, 'fp26': 100.0, 'fp27': 90.0,
                    'fp28': 5.0, 'fp29': 15.0, 'fp30': 30.0, 'fp31': 0.0001,
                    'fp32': 250.0, 'fp33': 200.0, 'fp34': 50.0, 'fp35': 1.0,
                    'fp36': 10.0, 'fp37': 0.0, 'fp38': 0.0, 'ip01': 6, 'ip02': 5,
                    'ip03': 12, 'ip04': 10, 'ip05': 17, 'ip06': 20, 'ip07': 22},
        'proper': {'fp01': 200.0, 'fp02': 0.03, 'fp03': 3.0},
    },
}

# Explicit shared-base reclassification. SnakeCrow and SnakeWhole share the
# `Game::SnakeJointMgr` spine driver; DangoMushi is a standalone segmented-body
# boss with no SnakeJointMgr and no ChappyBase relationship. Evidence:
#   SnakeJointMgr.h:30  mObj comment "SnakeCrow obj or SnakeWhole obj";
#                       :47 joints bodyjnt3..bodyjnt8.
#   SnakeCrow.cpp:1471  createJointCallBack -> new SnakeJointMgr(this).
#   SnakeWhole.cpp:1898  createJointCallBack -> new SnakeJointMgr(this).
#   SnakeCrowAnimator.cpp:9-21 and SnakeWholeAnimator.cpp:9-21 are the same
#                       0x8034B63C ProperAnimator thunk pair.
#   DangoMushi.h:72      Obj : public EnemyBase (direct).
#   DangoMushi.h:224     ProperAnimator : EnemyBlendAnimatorBase.
#   DangoMushiMgr.cpp:13 loads /enemy/data/DangoMushi/dangomushi.brk.
SHARED_BASE = {'SnakeCrow': 'SnakeJointMgr', 'SnakeWhole': 'SnakeJointMgr',
               'DangoMushi': None}
BASE_CLASSIFICATION = {
    'SnakeCrow': {
        'family': 'Snagret (shared SnakeJointMgr base)',
        'base_class': 'Game::SnakeJointMgr',
        'obj_base': 'EnemyBase',
        'animator': 'EnemyAnimatorBase::ProperAnimator',
        'shared_with': ['SnakeWhole'],
        'evidence': 'SnakeJointMgr.h:30; SnakeCrow.cpp:1471; SnakeCrowAnimator.cpp:9-21',
    },
    'SnakeWhole': {
        'family': 'Snagret (shared SnakeJointMgr base)',
        'base_class': 'Game::SnakeJointMgr',
        'obj_base': 'EnemyBase',
        'animator': 'EnemyAnimatorBase::ProperAnimator',
        'shared_with': ['SnakeCrow'],
        'evidence': 'SnakeWhole.cpp:1898 new SnakeJointMgr; SnakeJointMgr.h:30; SnakeWholeAnimator.cpp:9-21; SnakeWhole.h:236-241 adds Jump(run1)',
    },
    'DangoMushi': {
        'family': 'Segmented Crawbster (standalone, not Snagret/chappy base)',
        'base_class': None,
        'obj_base': 'EnemyBase',
        'animator': 'EnemyBlendAnimatorBase::ProperAnimator',
        'shared_with': [],
        'evidence': 'DangoMushi.h:72,224; DangoMushiMgr.cpp:13; no SnakeJointMgr / not ChappyBase',
    },
}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = [
    'Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key-event frames, loop markers and parameter text are preserved as data only; no bite, swallow, flick, jump, roll or death behavior executes.',
    'No native runtime, AI/FSM, install or arena placement is provided by this slice.',
    'SnakeCrow and SnakeWhole share the Game::SnakeJointMgr spine base (bodyjnt3-bodyjnt8) but own distinct AnimID/Parm banks (SnakeWhole inserts the run1 jump clip at slot 12); DangoMushi is a standalone EnemyBase/EnemyBlendAnimatorBase segmented-body boss with no SnakeJointMgr and no ChappyBase relationship.',
    'EXPECTED_EVENTS records the exact disc (frame, type) key events read from enemyanimmgr.txt; the DangoMushi bank omits the `{` before attack_2.bca, so a terminator-based parser is used. Individual sampled poses that the converter cannot bake are recorded unsupported with a reason rather than aborting the run.',
    'The attack clip stems are the disc spellings hit_near/hit/hit_far (SnakeCrow.h:232-236, SnakeWhole.h:230-234) and DangoMushi flick is attack_2 (DangoMushi.h:210-222), confirmed against anim.szs members and enemyanimmgr.txt.',
    'Burrowing Snagret health is overridden to the proper parm mWFGHealth (fp31) only in the White Flower Garden cave f_02 story mode (SnakeCrow.cpp:95-105); the disc proper block now carries the re-read fp31 value 2500, distinct from the header default 7500.',
    'DangoMushi disc proper fp10 is absent (only fp01/fp02/fp03 are stored), so the header mFlipTime default 7.5 is reported as defaulted rather than as a disc value.',
    'DangoMushi births falling Rock/Egg enemies through generalEnemyMgr.cpp:842-848 and DangoMushi.cpp:649-776; that child-spawner behavior is source-documented only and not reproduced.',
    'DangoMushi Mgr::loadTexData requires the enemy/data/DangoMushi/dangomushi.brk material animation (DangoMushiMgr.cpp:71-84); extraction records the brk resource but does not play it back.',
]

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
TOLERANCES = {}

TEXT = (
    'P2_SNAGRET_1\n'
    'species SnakeCrow SnakeWhole DangoMushi\n'
    'shared_base SnakeCrow SnakeWhole SnakeJointMgr\n'
    'dango_base EnemyBase EnemyBlendAnimatorBase standalone\n'
    'snakecrow_health 1500\nsnakecrow_speed 0\nsnakecrow_territory 80\n'
    'snakecrow_wfg_health 2500\nsnakecrow_fast_appear 0.6\n'
    'snakewhole_health 5000\nsnakewhole_speed 1000\nsnakewhole_territory 380\n'
    'dangomushi_health 3000\ndangomushi_speed 50\ndangomushi_attack_range 300\n'
    'dangomushi_roll_speed 200\ndangomushi_flip_time 7.5\n'
    'native_ready false\ngameplay_events_executed false\nbtk_playback false\n'
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def animation_rows(text):
    """Parse a disc enemyanimmgr.txt bank into registration-order rows.

    The shared sheargrub parser requires every `{...}` record to open with a
    brace, but the US GPVE01 DangoMushi bank omits the `{` before
    `attack_2.bca`. Parse by the `-1` record terminator instead so all three
    banks (13/14/9 rows) load. Events are exact `[frame, type]` pairs.
    """
    clean = re.sub(r'#[^\r\n]*', '', text)
    tokens = clean.split()
    if not tokens:
        raise ValueError('Empty animation registration')
    count = int(tokens[0])
    rows = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in ('{', '}'):
            index += 1
            continue
        if not re.fullmatch(r'[a-z0-9_]+\.bca', token):
            index += 1
            continue
        name = token
        index += 1
        events = []
        while index < len(tokens) and tokens[index] != '-1':
            if index + 1 >= len(tokens):
                raise ValueError('Truncated animation event pair')
            events.append([int(tokens[index]), int(tokens[index + 1])])
            index += 2
        index += 1
        rows.append({'file': name, 'events': events})
    if len(rows) != count or len({r['file'] for r in rows}) != count:
        raise ValueError('Animation registration count/identity mismatch')
    return rows


def profile(species, blocks_list, rows):
    """Validate parsed metadata for one species against the source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general,
    proper in order. ``rows`` is animation_rows(enemyanimmgr.txt) in
    registration order. Duplicate keys are rejected by the parsers upstream;
    header defaults and disc values are reported separately, never flattened.
    """
    if species not in SPECIES:
        raise ValueError('Unknown snagret/crawbster species')
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
            raise ValueError(f'{species} clip {name} key event stream mismatch')
    defaulted = set(PROPER_PARM_DEFAULTS[species]) - set(proper)
    return {'enemy_id': SPECIES[species],
            'family': BASE_CLASSIFICATION[species]['family'],
            'base_class': BASE_CLASSIFICATION[species]['base_class'],
            'shared_with': list(BASE_CLASSIFICATION[species]['shared_with']),
            'state_ids': dict(STATE_IDS[species]),
            'anim_id_by_clip': {name: i for i, name in enumerate(CLIPS[species])},
            'parameter_blocks': blocks_list,
            'general_header_defaults': dict(GENERAL_DEFAULTS),
            'general_retail': {k: general[k] for k in general},
            'proper_header_defaults': dict(PROPER_PARM_DEFAULTS[species]),
            'proper_retail': {k: proper[k] for k in proper},
            'proper_keys_defaulted_from_header': sorted(defaulted),
            'role': 'concrete spawnable boss',
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
        report = dict(schema=1, policy='P2_SNAGRET_1',
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
            info.update(role='concrete spawnable boss',
                        model_sha256=sha(model), joints=names,
                        metadata_sha256=metadata,
                        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                      weighted_baking=envelopes > 0,
                                      self_contained_resources=draws > 0),
                        collision=collision_nodes(
                            params[species.lower() + '/enemycoll.txt'],
                            len(names)),
                        clips=[])
            if species == 'DangoMushi':
                brk = read('enemy/data/DangoMushi/dangomushi.brk')
                (root / 'dangomushi.brk').write_bytes(brk)
                info['brk_sha256'] = sha(brk)
            reference = None
            for row in rows:
                raw = motions[row['file']]
                (root / row['file']).write_bytes(raw)
                clip = dict(name=Path(row['file']).stem,
                            source_sha256=sha(raw),
                            events=row['events'],
                            event_types=[event[1] for event in row['events']],
                            loop_attribute=raw[40],
                            loop_semantics=LOOPS.get(raw[40], 'unknown'),
                            event_loop_boundaries=[r for r in row['events']
                                                   if r[1] in (0, 1)],
                            poses=[], status='unsupported')
                try:
                    duration, _ = bca_pose(raw, 0, len(names),
                                           allow_scale=True)
                    clip['source_frames'] = duration
                    frames = sample_frames(duration, pose_limit)
                except (ValueError, KeyError, ArithmeticError) as error:
                    clip['unsupported_reason'] = \
                        f'{type(error).__name__}: {error}'
                    info['clips'].append(clip)
                    continue
                for number, frame in enumerate(frames):
                    try:
                        tolerances = TOLERANCES.get(species, {})
                        _, pose = bca_pose(raw, frame, len(names),
                                           allow_scale=True)
                        matrices = draw_matrices(model_blocks, pose)
                        decoded = decode(model, True, bake_rigid=True,
                                         draw_matrices=matrices,
                                         **tolerances)
                        name = f'snake_{species}_{clip["name"]}_{number:02}.mod'
                        conversion = write_model(decoded, root / name,
                                                 'enemy.bmd')
                        conversion.update(source='enemy.bmd', output=name,
                                          weighted_pose_baked=envelopes > 0)
                        data = (root / name).read_bytes()
                        resources = resource_chunks(data)
                        if reference is not None and resources != reference:
                            raise ValueError(
                                'Snagret pose changes immutable render resources')
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
        (output / 'snagret.json').write_bytes(
            (json.dumps(report, sort_keys=True, indent=2) + '\n').encode())
        (output / 'p2-snagret.txt').write_text(TEXT)
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
