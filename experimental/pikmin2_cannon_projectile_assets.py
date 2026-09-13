"""Source-backed, bounded cannon/projectile import; no native actor install.

Covers enemy IDs 75 Kabuto (Armored Cannon Beetle Larva), 95 Rkabuto
(Decorated Cannon Beetle), 96 Fkabuto (burrowed, helper variant), and the
projectile/hazard entries 19 Rock (falling boulder), 74 Stone (Rock
projectile), 36 Bomb (bomb-rock), 37 Egg (egg drop container) and 97
FminiHoudai (pedestal Gatling Groink helper alias). Source audit:
docs/PIKMIN2_CANNON_GROINK_AUDIT.md and docs/PIKMIN2_CANNON_PROJECTILE_ASSETS.md
(issue #350, parent #169). Extraction follows the ground-invertebrate lane:
hashed disc reads, preserved metadata text, bounded weighted/rigid pose
sampling. No btk playback, no behavior execution. Projectile lifecycle policy
is cross-referenced, not duplicated: docs/PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md
(#244).
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
from experimental.pikmin2_convert import blocks, decode, u16, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

SPECIES = {'Kabuto': 75, 'Rkabuto': 95, 'Fkabuto': 96, 'Rock': 19, 'Stone': 74,
           'Bomb': 36, 'Egg': 37, 'FminiHoudai': 97}

PARM_SOURCE = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
MAX_POSES = 12

# Model/anim/collision/stone/animmgr resource owner. Empty EnemyInfo resource
# slots fall back to the row's own name (enemyMgrBase.cpp:519-565); Rkabuto,
# Fkabuto and FminiHoudai alias another bank (enemyInfo.cpp:39,40,108) and
# Stone is owned by the Rock manager (enemyInfo.cpp:37).
RESOURCE_OWNER = {'Rkabuto': 'Kabuto', 'Fkabuto': 'Kabuto',
                  'Stone': 'Rock', 'FminiHoudai': 'MiniHoudai'}
# The single metadata block that does NOT follow the resource owner: Stone's
# mParamName also resolves to "Rock" (enemyInfo.cpp:37).
PARM_OWNER = {'Stone': 'Rock'}

# Classification from the registration rows and content inventory. Helpers are
# distinct EnemyIDs with their own manager and parm block but no separate
# Piklopedia identity (content inventory classification
# "variant_no_separate_entry"); projectile entries carry EFlag_HasNoInfo.
ROLE = {
    'Kabuto': 'concrete spawnable',
    'Rkabuto': 'concrete spawnable',
    'Fkabuto': 'buried helper variant (no separate entry)',
    'Rock': 'projectile/hazard (falling boulder)',
    'Stone': 'projectile/hazard (Rock-manager alias)',
    'Bomb': 'projectile/hazard (bomb-rock)',
    'Egg': 'projectile/hazard (egg drop container)',
    'FminiHoudai': 'fixed-pedestal helper alias (MiniHoudai resources)',
}
HELPER_ENTRIES = ('Fkabuto', 'FminiHoudai')
PROJECTILE_ENTRIES = ('Rock', 'Stone', 'Bomb', 'Egg')

# Clip order equals the AnimID enum registration order and the resolved
# enemyanimmgr.txt row order for each species. Kabuto/Rkabuto/Fkabuto share the
# Kabuto bank (Kabuto.h:146-162); Rock and Stone share the Rock bank, whose
# second authored clip is run.bca; Bomb.h:163-167; Egg.h:141-144;
# FminiHoudai shares MiniHoudai (MiniHoudai.h:181-191).
CLIPS = {
    'Kabuto': ('dead', 'move', 'flick', 'attack', 'pivot', 'wait', 'K_pivot',
               'K_wait', 'K_attack', 'K_flick', 'K_dead', 'K_appear', 'K_hide',
               'carry'),
    'Rkabuto': ('dead', 'move', 'flick', 'attack', 'pivot', 'wait', 'K_pivot',
                'K_wait', 'K_attack', 'K_flick', 'K_dead', 'K_appear', 'K_hide',
                'carry'),
    'Fkabuto': ('dead', 'move', 'flick', 'attack', 'pivot', 'wait', 'K_pivot',
                'K_wait', 'K_attack', 'K_flick', 'K_dead', 'K_appear', 'K_hide',
                'carry'),
    'Rock': ('dead', 'run'),
    'Stone': ('dead', 'run'),
    'Bomb': ('hit_start', 'hit_loop'),
    'Egg': ('damage1',),
    'FminiHoudai': ('walk', 'search1', 'turn1', 'attack1', 'flick1', 'dead1',
                    'type5', 'rebirth'),
}

# The Kabuto enemyanimmgr.txt keeps the authored upper-case ``K_*.bca``
# registration names for the buried clips, but the packed
# ``enemy/data/Kabuto/anim.szs`` ships them lower-case
# (``k_pivot.bca`` .. ``k_hide.bca``) on US GPVE01 rev 0. Record the shipped
# member explicitly rather than relying on host filesystem case folding;
# ``motion_member`` still verifies the resolved member exists.
SHIPPED_MOTION_ALIASES = {
    f'{name}.bca': f'{name[0].lower()}{name[1:]}.bca'
    for name in CLIPS['Kabuto'] if name.startswith('K_')
}

# Animation key events (frame, type) from each resolved enemyanimmgr.txt on
# disc, cross-checked against docs/PIKMIN2_CANNON_PROJECTILE_ASSETS.md.
EXPECTED_EVENTS = {
    'Kabuto': {
        'dead': [],
        'move': [[15, 0], [44, 1]],
        'flick': [[30, 2]],
        'attack': [[50, 2]],
        'pivot': [[0, 0], [34, 1]],
        'wait': [[0, 0], [49, 1]],
        'K_pivot': [[0, 0], [34, 1]],
        'K_wait': [[0, 0], [49, 1]],
        'K_attack': [[55, 2]],
        'K_flick': [[30, 2]],
        'K_dead': [],
        'K_appear': [],
        'K_hide': [],
        'carry': [[10, 0], [29, 1]],
    },
    'Rkabuto': {
        'dead': [],
        'move': [[15, 0], [44, 1]],
        'flick': [[30, 2]],
        'attack': [[50, 2]],
        'pivot': [[0, 0], [34, 1]],
        'wait': [[0, 0], [49, 1]],
        'K_pivot': [[0, 0], [34, 1]],
        'K_wait': [[0, 0], [49, 1]],
        'K_attack': [[55, 2]],
        'K_flick': [[30, 2]],
        'K_dead': [],
        'K_appear': [],
        'K_hide': [],
        'carry': [[10, 0], [29, 1]],
    },
    'Fkabuto': {
        'dead': [],
        'move': [[15, 0], [44, 1]],
        'flick': [[30, 2]],
        'attack': [[50, 2]],
        'pivot': [[0, 0], [34, 1]],
        'wait': [[0, 0], [49, 1]],
        'K_pivot': [[0, 0], [34, 1]],
        'K_wait': [[0, 0], [49, 1]],
        'K_attack': [[55, 2]],
        'K_flick': [[30, 2]],
        'K_dead': [],
        'K_appear': [],
        'K_hide': [],
        'carry': [[10, 0], [29, 1]],
    },
    'Rock': {
        'dead': [],
        'run': [[0, 0], [39, 1]],
    },
    'Stone': {
        'dead': [],
        'run': [[0, 0], [39, 1]],
    },
    'Bomb': {
        'hit_start': [[10, 2]],
        'hit_loop': [[0, 0], [7, 1]],
    },
    'Egg': {
        'damage1': [],
    },
    'FminiHoudai': {
        'walk': [[10, 0], [18, 2], [25, 1]],
        'search1': [],
        'turn1': [[5, 0], [16, 1]],
        'attack1': [[11, 2], [22, 3], [25, 4], [32, 5]],
        'flick1': [[10, 2]],
        'dead1': [[32, 2], [52, 3]],
        'type5': [[10, 0], [29, 1]],
        'rebirth': [[32, 2], [45, 3]],
    },
}

# Valid EnemyParmsBase general-block field identifiers (EnemyParmsBase.h:55-101).
# fp07 is not declared; unknown fp/ip keys must be rejected before mutation.
GENERAL_KEYS = frozenset(
    [f'fp{i:02}' for i in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                           17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                           31, 32, 33, 34, 35, 36, 37, 38)]
    + [f'ip{i:02}' for i in range(1, 8)])

# State IDs from the headers. Kabuto.h:28-44 (shared by Rkabuto/Fkabuto via the
# Kabuto::Obj base), Rock.h:178-186 (shared by Stone), Bomb.h:182-186,
# Egg.h:159-162, MiniHoudai.h:25-39 (shared by FminiHoudai).
STATE_IDS = {
    'Kabuto': {'dead': 0, 'wait': 1, 'turn': 2, 'move': 3, 'flick': 4,
               'attack': 5, 'fixstay': 6, 'fixappear': 7, 'fixhide': 8,
               'fixwait': 9, 'fixturn': 10, 'fixattack': 11, 'fixflick': 12},
    'Rkabuto': {'dead': 0, 'wait': 1, 'turn': 2, 'move': 3, 'flick': 4,
                'attack': 5, 'fixstay': 6, 'fixappear': 7, 'fixhide': 8,
                'fixwait': 9, 'fixturn': 10, 'fixattack': 11, 'fixflick': 12},
    'Fkabuto': {'dead': 0, 'wait': 1, 'turn': 2, 'move': 3, 'flick': 4,
                'attack': 5, 'fixstay': 6, 'fixappear': 7, 'fixhide': 8,
                'fixwait': 9, 'fixturn': 10, 'fixattack': 11, 'fixflick': 12},
    'Rock': {'wait': 0, 'appear': 1, 'dropwait': 2, 'fall': 3, 'move': 4,
             'dead': 5},
    'Stone': {'wait': 0, 'appear': 1, 'dropwait': 2, 'fall': 3, 'move': 4,
              'dead': 5},
    'Bomb': {'wait': 0, 'bomb': 1},
    'Egg': {'wait': 0},
    'FminiHoudai': {'dead': 0, 'rebirth': 1, 'lost': 2, 'attack': 3,
                    'flick': 4, 'turn': 5, 'turnhome': 6, 'turnpath': 7,
                    'walk': 8, 'walkhome': 9, 'walkpath': 10},
}

# Header defaults for the species-specific ProperParms block(s).
# Kabuto::Parms declares an empty ParmParms (Kabuto.h:125-144), so the Kabuto
# family disc proper block is empty in retail. Rock.h:38, Bomb.h:135-148,
# Egg.h:104-120, MiniHoudai.h:154-166.
PROPER_PARM_DEFAULTS = {
    'Kabuto': {},
    'Rkabuto': {},
    'Fkabuto': {},
    'Rock': {'fp01': 150.0},
    'Stone': {'fp01': 150.0},
    'Bomb': {'fp01': 250.0, 'fp02': 50.0, 'ip01': 2, 'ip02': 50},
    'Egg': {'fp01': 1.0, 'fp02': 1.0, 'fp03': 1.0, 'fp04': 1.0, 'fp05': 1.0},
    'FminiHoudai': {'fp11': 30.0, 'fp12': 10.0},
}

# Retail (disc) values verified against enemyParms.szs on US GPVE01 rev 0.
# Keys are (block, parm): 'general' is the first EnemyParmsBase block,
# 'proper' the species block. Stone's mParamName resolves to Rock, so its
# dormant stone/enemyparm.txt (SHA-identical to rock/enemyparm.txt) is not
# used; Rkabuto's parm is SHA-identical to Kabuto's.
DISC_PARMS = {
    'Kabuto': {
        'general': {'fp00': 850.0, 'fp27': 50.0, 'fp31': 0.0001, 'fp30': 100.0,
                    'fp01': 45.0, 'fp33': 40.0, 'fp34': 15.0, 'fp32': 45.0,
                    'fp02': 0.35, 'fp03': 0.25, 'fp04': 0.35, 'fp05': 0.0001,
                    'fp06': 60.0, 'fp08': 0.05, 'fp28': 5.0, 'fp09': 150.0,
                    'fp10': 30.0, 'fp11': 75.0, 'fp12': 350.0, 'fp25': 100.0,
                    'fp13': 90.0, 'fp14': 0.0, 'fp26': 0.0, 'fp15': 0.0,
                    'fp17': 400.0, 'fp18': 1.0, 'fp19': 45.0, 'fp16': 1.0,
                    'fp20': 180.0, 'fp21': 0.0, 'fp22': 25.0, 'fp23': 0.0,
                    'fp24': 10.0, 'fp29': 15.0, 'fp35': 1.0, 'fp36': 50.0,
                    'fp37': 0.3, 'fp38': 5.0, 'ip01': 3, 'ip02': 2, 'ip03': 3,
                    'ip04': 5, 'ip05': 3, 'ip06': 10, 'ip07': 3},
        'proper': {},
    },
    'Rkabuto': {
        'general': {'fp00': 850.0, 'fp27': 50.0, 'fp31': 0.0001, 'fp30': 100.0,
                    'fp01': 45.0, 'fp33': 40.0, 'fp34': 15.0, 'fp32': 45.0,
                    'fp02': 0.35, 'fp03': 0.25, 'fp04': 0.35, 'fp05': 0.0001,
                    'fp06': 60.0, 'fp08': 0.05, 'fp28': 5.0, 'fp09': 150.0,
                    'fp10': 30.0, 'fp11': 75.0, 'fp12': 350.0, 'fp25': 100.0,
                    'fp13': 90.0, 'fp14': 0.0, 'fp26': 0.0, 'fp15': 0.0,
                    'fp17': 400.0, 'fp18': 1.0, 'fp19': 45.0, 'fp16': 1.0,
                    'fp20': 180.0, 'fp21': 0.0, 'fp22': 25.0, 'fp23': 0.0,
                    'fp24': 10.0, 'fp29': 15.0, 'fp35': 1.0, 'fp36': 50.0,
                    'fp37': 0.3, 'fp38': 5.0, 'ip01': 3, 'ip02': 2, 'ip03': 3,
                    'ip04': 5, 'ip05': 3, 'ip06': 10, 'ip07': 3},
        'proper': {},
    },
    'Fkabuto': {
        'general': {'fp00': 2000.0, 'fp27': 50.0, 'fp31': 0.0001, 'fp30': 100.0,
                    'fp01': 45.0, 'fp33': 40.0, 'fp34': 15.0, 'fp32': 45.0,
                    'fp02': 0.35, 'fp03': 0.25, 'fp04': 0.35, 'fp05': 0.0001,
                    'fp06': 60.0, 'fp08': 0.075, 'fp28': 7.5, 'fp09': 150.0,
                    'fp10': 30.0, 'fp11': 75.0, 'fp12': 350.0, 'fp25': 100.0,
                    'fp13': 90.0, 'fp14': 0.0, 'fp26': 0.0, 'fp15': 0.0,
                    'fp17': 400.0, 'fp18': 1.0, 'fp19': 45.0, 'fp16': 1.0,
                    'fp20': 180.0, 'fp21': 0.0, 'fp22': 25.0, 'fp23': 0.0,
                    'fp24': 10.0, 'fp29': 15.0, 'fp35': 1.0, 'fp36': 50.0,
                    'fp37': 0.3, 'fp38': 5.0, 'ip01': 3, 'ip02': 2, 'ip03': 3,
                    'ip04': 5, 'ip05': 3, 'ip06': 10, 'ip07': 3},
        'proper': {},
    },
    'Rock': {
        'general': {'fp00': 99999.0, 'fp27': 0.0, 'fp31': 0.0, 'fp30': 0.0,
                    'fp01': 25.0, 'fp33': 40.0, 'fp34': 25.0, 'fp32': 50.0,
                    'fp02': 0.0, 'fp03': 0.0, 'fp04': 0.0, 'fp05': 0.0001,
                    'fp06': 250.0, 'fp08': 0.03, 'fp28': 3.0, 'fp09': 1.0,
                    'fp10': 1.0, 'fp11': 75.0, 'fp12': 150.0, 'fp25': 100.0,
                    'fp13': 180.0, 'fp14': 1000.0, 'fp26': 550.0, 'fp15': 0.6,
                    'fp17': 0.0, 'fp18': 0.0, 'fp19': 0.0, 'fp16': 0.0,
                    'fp20': 0.0, 'fp21': 0.0, 'fp22': 20.0, 'fp23': 0.0,
                    'fp24': 10.0, 'fp29': 0.0, 'fp35': 1.0, 'fp36': 10.0,
                    'fp37': 0.05, 'fp38': 10.0, 'ip01': 0, 'ip02': 0, 'ip03': 0,
                    'ip04': 0, 'ip05': 0, 'ip06': 0, 'ip07': 0},
        'proper': {'fp01': 100.0},
    },
    'Stone': {
        'general': {'fp00': 99999.0, 'fp27': 0.0, 'fp31': 0.0, 'fp30': 0.0,
                    'fp01': 25.0, 'fp33': 40.0, 'fp34': 25.0, 'fp32': 50.0,
                    'fp02': 0.0, 'fp03': 0.0, 'fp04': 0.0, 'fp05': 0.0001,
                    'fp06': 250.0, 'fp08': 0.03, 'fp28': 3.0, 'fp09': 1.0,
                    'fp10': 1.0, 'fp11': 75.0, 'fp12': 150.0, 'fp25': 100.0,
                    'fp13': 180.0, 'fp14': 1000.0, 'fp26': 550.0, 'fp15': 0.6,
                    'fp17': 0.0, 'fp18': 0.0, 'fp19': 0.0, 'fp16': 0.0,
                    'fp20': 0.0, 'fp21': 0.0, 'fp22': 20.0, 'fp23': 0.0,
                    'fp24': 10.0, 'fp29': 0.0, 'fp35': 1.0, 'fp36': 10.0,
                    'fp37': 0.05, 'fp38': 10.0, 'ip01': 0, 'ip02': 0, 'ip03': 0,
                    'ip04': 0, 'ip05': 0, 'ip06': 0, 'ip07': 0},
        'proper': {'fp01': 100.0},
    },
    'Bomb': {
        'general': {'fp00': 4.5, 'fp27': 35.0, 'fp31': 0.0, 'fp30': 0.0,
                    'fp01': 25.0, 'fp33': 25.0, 'fp34': 25.0, 'fp32': 25.0,
                    'fp02': 0.2, 'fp03': 0.25, 'fp04': 0.35, 'fp05': 0.5,
                    'fp06': 30.0, 'fp08': 0.1, 'fp28': 10.0, 'fp09': 300.0,
                    'fp10': 30.0, 'fp11': 30.0, 'fp12': 700.0, 'fp25': 50.0,
                    'fp13': 180.0, 'fp14': 0.0, 'fp26': 0.0, 'fp15': 0.0,
                    'fp17': 0.0, 'fp18': 0.0, 'fp19': 0.0, 'fp16': 1.0,
                    'fp20': 30.0, 'fp21': 15.0, 'fp22': 90.0, 'fp23': 15.0,
                    'fp24': 10.0, 'fp29': 0.0, 'fp35': 1.0, 'fp36': 10.0,
                    'fp37': 0.0, 'fp38': 10.0, 'ip01': 1, 'ip02': 1, 'ip03': 2,
                    'ip04': 2, 'ip05': 5, 'ip06': 3, 'ip07': 10},
        'proper': {'fp01': 500.0, 'fp02': 50.0, 'ip01': 1, 'ip02': 15},
    },
    'Egg': {
        'general': {'fp00': 50.0, 'fp27': 40.0, 'fp31': 0.0, 'fp30': 0.0,
                    'fp01': 10.0, 'fp33': 20.0, 'fp34': 7.0, 'fp32': 30.0,
                    'fp02': 0.2, 'fp03': 0.25, 'fp04': 0.35, 'fp05': 0.5,
                    'fp06': 30.0, 'fp08': 0.1, 'fp28': 10.0, 'fp09': 300.0,
                    'fp10': 30.0, 'fp11': 30.0, 'fp12': 700.0, 'fp25': 50.0,
                    'fp13': 180.0, 'fp14': 0.0, 'fp26': 0.0, 'fp15': 0.0,
                    'fp17': 150.0, 'fp18': 0.0, 'fp19': 0.0, 'fp16': 1.0,
                    'fp20': 30.0, 'fp21': 15.0, 'fp22': 30.0, 'fp23': 15.0,
                    'fp24': 10.0, 'fp29': 0.0, 'fp35': 1.0, 'fp36': 50.0,
                    'fp37': 0.0, 'fp38': 10.0, 'ip01': 1, 'ip02': 1, 'ip03': 2,
                    'ip04': 2, 'ip05': 5, 'ip06': 3, 'ip07': 10},
        'proper': {'fp01': 0.5, 'fp02': 0.35, 'fp03': 0.05, 'fp04': 0.05,
                   'fp05': 0.05},
    },
    'FminiHoudai': {
        'general': {'fp00': 700.0, 'fp27': 90.0, 'fp31': 0.00001, 'fp30': 50.0,
                    'fp01': 45.0, 'fp33': 50.0, 'fp34': 15.0, 'fp32': 70.0,
                    'fp02': 0.3, 'fp03': 0.3, 'fp04': 0.35, 'fp05': 0.0001,
                    'fp06': 100.0, 'fp08': 0.15, 'fp28': 2.0, 'fp09': 250.0,
                    'fp10': 50.0, 'fp11': 70.0, 'fp12': 500.0, 'fp25': 50.0,
                    'fp13': 180.0, 'fp14': 250.0, 'fp26': 50.0, 'fp15': 90.0,
                    'fp17': 300.0, 'fp18': 1.0, 'fp19': 50.0, 'fp16': 1.0,
                    'fp20': 500.0, 'fp21': 10.0, 'fp22': 15.0, 'fp23': 65.0,
                    'fp24': 10.0, 'fp29': 15.0, 'fp35': 1.0, 'fp36': 50.0,
                    'fp37': 0.3, 'fp38': 5.0, 'ip01': 20, 'ip02': 5, 'ip03': 35,
                    'ip04': 10, 'ip05': 45, 'ip06': 20, 'ip07': 25},
        'proper': {'fp11': 2.0, 'fp12': 118.0},
    },
}

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

LIMITATIONS = [
    'Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events, loop markers and parameter text are preserved as data only; no Stone birth, homing, bomb blast, egg drop or shotgun behavior executes.',
    'No native runtime, AI/FSM, install or arena placement is provided by this slice.',
    'Stone (74) has no EFlag_UseOwnID and is owned by the Rock manager (RockMgr.cpp:101-115); its dormant stone/enemyparm.txt and stone/enemyanimmgr.txt are present on disc but not selected (enemyInfo.cpp:37 resolves mParamName/mAnimMgrName to "Rock").',
    'Rkabuto and Fkabuto share the Kabuto model/anim/collision bank (enemyInfo.cpp:39-40) but keep their own enemyparm.txt; Fkabuto life is 2000 vs Kabuto/Rkabuto 850.',
    'FminiHoudai (97) aliases MiniHoudai (78) resources and parm layout; only the fixed pedestal variant is claimed here and the roaming MiniHoudai identity belongs to the Groink lane (#169).',
    'Projectile/hazard lifecycle mechanics (Rock fall/roll/dead, Bomb fuse and blast, Egg genItem, Groink shotgun) are cross-referenced from docs/PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md and docs/PIKMIN2_CANNON_GROINK_AUDIT.md; none are reimplemented here.',
]

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
TOLERANCES = {}

TEXT = (
    'P2_CANNON_PROJECTILE_1\n'
    'species Kabuto Rkabuto Fkabuto Rock Stone Bomb Egg FminiHoudai\n'
    'kabuto_health 850\nkabuto_speed 60\nkabuto_sight 350\nkabuto_attack_damage 10\n'
    'rkabuto_health 850\nrkabuto_homing true\n'
    'fkabuto_health 2000\nfkabuto_speed 60\n'
    'rock_health 99999\nrock_speed 250\nrock_attack_damage 10\n'
    'stone_attack_damage 250\n'
    'rock_search_rumble_speed 100\n'
    'bomb_health 4.5\nbomb_damage_to_enemies 500\nbomb_blast_halfheight 50\n'
    'bomb_damage_limit 1\nbomb_trigger_limit 15\nbomb_navi_pikmin_damage 10\n'
    'egg_health 50\negg_nectar_rate 0.5\negg_double_nectar_rate 0.35\n'
    'egg_mitite_rate 0.05\negg_spicy_rate 0.05\negg_bitter_rate 0.05\n'
    'fminihoudai_health 700\nfminihoudai_gauge_delay 2.0\n'
    'fminihoudai_respawn_rate 118.0\nfminihoudai_attack_damage 10\n'
    'native_ready false\ngameplay_events_executed false\nbtk_playback false\n'
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def animation_rows(text):
    """Parse enemyanimmgr.txt, allowing the Kabuto ``K_*`` capitalised clips.

    Mirrors experimental.pikmin2_sheargrub_assets.animation_rows but relaxes the
    clip-name pattern to ``[A-Za-z0-9_]+`` so the buried-state ``K_pivot``,
    ``K_wait``, ``K_attack``, ``K_flick``, ``K_dead``, ``K_appear`` and
    ``K_hide`` registrations are accepted.
    """
    clean = re.sub(r'#[^\r\n]*', '', text)
    count = int(clean.split()[0])
    rows = []
    for block in re.findall(r'\{([^{}]*)\}', clean):
        fields = block.split()
        if (len(fields) < 3
                or not re.fullmatch(r'[A-Za-z0-9_]+\.bca', fields[1])
                or fields[-1] != '-1'):
            raise ValueError('Invalid animation registration')
        events = fields[2:-1]
        if len(events) % 2:
            raise ValueError('Invalid animation event pairs')
        rows.append({'file': fields[1],
                     'events': [[int(events[i]), int(events[i + 1])]
                                for i in range(0, len(events), 2)]})
    if len(rows) != count or len({r['file'] for r in rows}) != count:
        raise ValueError('Animation registry count/identity mismatch')
    return rows


def motion_member(motions, filename):
    """Resolve a registered ``enemyanimmgr.txt`` ``.bca`` name to its member.

    The archived member normally matches the registration name exactly; the
    buried Kabuto clips are the exception, registered as ``K_*.bca`` but
    shipped as ``k_*.bca`` (``SHIPPED_MOTION_ALIASES``). A case-insensitive
    fallback guards any other repack, but a missing or ambiguous member is a
    hard error rather than a silent guess.
    """
    member = SHIPPED_MOTION_ALIASES.get(filename, filename)
    if member not in motions:
        matches = [name for name in motions
                   if name.lower() == filename.lower()]
        if len(matches) != 1:
            raise KeyError(filename)
        member = matches[0]
    return member


def profile(species, blocks_list, rows):
    """Validate parsed metadata for one entry against the source contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt): creature, general,
    proper in order. ``rows`` is animation_rows(enemyanimmgr.txt) in
    registration order. Duplicate keys are rejected by the parsers upstream;
    header defaults and disc values are reported separately, never flattened.
    """
    if species not in SPECIES:
        raise ValueError('Unknown cannon/projectile species')
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
        report = dict(schema=1, policy='P2_CANNON_PROJECTILE_1',
                      disc_id=header[:6].decode(), disc_revision=header[7],
                      source_revision=head, source_sha256=source_hashes,
                      native_ready=False, gameplay_events_executed=False,
                      btk_playback=False, species={},
                      total_pose_bytes=0, total_poses=0)
        for species, identity in SPECIES.items():
            owner = RESOURCE_OWNER.get(species, species)
            parm_owner = PARM_OWNER.get(species, species)
            root = output / species
            root.mkdir()
            model = archive_files(
                read(f'enemy/data/{owner}/model.szs'))['enemy.bmd']
            model_blocks = blocks(model)
            motions = archive_files(
                read(f'enemy/data/{owner}/anim.szs'))
            names = joints(model)
            (root / 'enemy.bmd').write_bytes(model)
            metadata = {}
            for filename in METADATA_FILES:
                block_owner = parm_owner if filename == 'enemyparm.txt' else owner
                key = block_owner.lower() + '/' + filename
                if key not in params:
                    continue
                raw = params[key]
                metadata[filename] = sha(raw)
                (root / filename).write_bytes(raw)
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
            blocks_list = parameter_blocks(
                params[parm_owner.lower() + '/enemyparm.txt'])
            rows = animation_rows(
                params[owner.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
            info = profile(species, blocks_list, rows)
            info.update(role=ROLE[species], resource_owner=owner,
                        parm_owner=parm_owner,
                        model_sha256=sha(model), joints=names,
                        metadata_sha256=metadata,
                        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                      weighted_baking=envelopes > 0,
                                      self_contained_resources=draws > 0),
                        collision=collision_nodes(
                            params[owner.lower() + '/enemycoll.txt'],
                            len(names)),
                        clips=[])
            reference = None
            for row in rows:
                member = motion_member(motions, row['file'])
                raw = motions[member]
                (root / member).write_bytes(raw)
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
                        name = f'cannon_{species}_{clip["name"]}_{number:02}.mod'
                        conversion = write_model(decoded, root / name,
                                                 'enemy.bmd')
                        conversion.update(source='enemy.bmd', output=name,
                                          weighted_pose_baked=envelopes > 0)
                        data = (root / name).read_bytes()
                        resources = resource_chunks(data)
                        if reference is not None and resources != reference:
                            raise ValueError(
                                'Cannon projectile pose changes immutable render resources')
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
        (output / 'cannon_projectile.json').write_bytes(
            (json.dumps(report, sort_keys=True, indent=2) + '\n').encode())
        (output / 'p2-cannon-projectile.txt').write_text(TEXT)
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
