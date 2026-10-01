"""Pikmin 2 bulblax family behavior reference (issue #227, parent #172).

Pure-Python, side-effect-free, machine-checkable encoding of the source FSMs
and parameters for Empress Bulblax (Queen, enemy ID 30), Bulborb Larva
(Baby, enemy ID 31) and Emperor Bulblax (KingChappy, enemy ID 53), verified
against native/pikmin2-research. This is a REFERENCE for the future runtime
lane: nothing here executes game behavior, touches the ISO or the native
build. Every fact carries a per-fact `source` file:line citation (paths are
relative to native/pikmin2-research unless they name a disc file). Disc
values (from enemy/parm/enemyParms.szs, US GPVE01 revision 0) and header
defaults are kept as distinct fields and never flattened.

Audit: output/bulblax_audit_ref.md (#172). Extraction cross-check:
output/bulblax-run1/bulblax.json (#217) via `--check`.
"""
import argparse
import json
import math
import sys
from pathlib import Path

# Animation key-event semantics (audit lines 110-114, 229-231): type 0/1 pairs
# bracket loop ranges; types 2-6 are gameplay events the state code reacts to.
KEYEVENT_2 = 2
KEYEVENT_3 = 3
KEYEVENT_4 = 4
KEYEVENT_5 = 5
KEYEVENT_6 = 6
KEYEVENT_END = 7
KEYEVENT_END_BLEND = 8
ANIM_BLEND_FRAMES = 30  # blend length when mAllowAnimBlending is set, audit:230-231

# Predicates whose evaluation order is reconstructed from retained assembly
# (audit lines 249-251); non-authoritative.
RECONSTRUCTED = (
    'queen_roll_pass',            # Queen::StateRolling::exec
    'baby_move_step',             # Baby::StateMove::exec
    'king_attack_step',           # KingChappy StateAttack::exec / searchTarget / checkAttack
    'king_flick_step',            # KingChappy StateFlick::exec
)


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Expected finite number')
    return value


# ---------------------------------------------------------------------------
# Shared roster / boss plumbing facts (audit lines 11-41)
# ---------------------------------------------------------------------------

# IS_ENEMY_BOSS membership, include/Game/enemyInfo.h:214.
IS_ENEMY_BOSS = {'Queen': True, 'KingChappy': True, 'Baby': False}

# Petrified-kill nectar drops, src/plugProjectYamashitaU/enemyBase.cpp:1340-1350
# (BDT_Boss: 5 rolls at 0.85; Baby BDT_Weak: 1 roll at 0.99, audit line 21).
NECTAR_ON_PETRIFIED_KILL = {
    'Queen': {'rolls': 5, 'yellow_chance': 0.85, 'source': 'src/plugProjectYamashitaU/enemyBase.cpp:1340-1350'},
    'KingChappy': {'rolls': 5, 'yellow_chance': 0.85, 'source': 'src/plugProjectYamashitaU/enemyBase.cpp:1340-1350'},
    'Baby': {'rolls': 1, 'yellow_chance': 0.99, 'source': 'output/bulblax_audit_ref.md:21'},
}

# Last-floor squad-adjusted held-treasure weight for IS_ENEMY_BOSS members,
# src/plugProjectYamashitaU/enemyBase.cpp:2605.
LAST_FLOOR_SQUAD_TREASURE_WEIGHT = {
    'applies_to': ('Queen', 'KingChappy'),
    'source': 'src/plugProjectYamashitaU/enemyBase.cpp:2600-2610',
}

# Carcass rewards, user/Abe/Pellet/us/carcass_config.txt (audit lines 40-41).
CARCASS = {
    'Queen': {'pokos': 15, 'carry_min': 20, 'carry_max': 30, 'source': 'user/Abe/Pellet/us/carcass_config.txt'},
    'KingChappy': {'pokos': 15, 'carry_min': 20, 'carry_max': 30, 'source': 'user/Abe/Pellet/us/carcass_config.txt'},
    'Baby': None,  # no carcass entry; leaves no corpse
}

# Registering a Queen reserves 10 Rock objects,
# src/plugProjectYamashitaU/generalEnemyMgr.cpp:851-852.
QUEEN_ROCK_RESERVE = {'count': 10, 'source': 'src/plugProjectYamashitaU/generalEnemyMgr.cpp:851-852'}
QUEEN_CHILD_BUDGET = {'species': 'Baby', 'count': 50, 'source': 'src/plugProjectYamashitaU/enemyInfo.cpp:56'}

# Retail roster placements (audit lines 24-37); no surface generator and no
# Battle definition spawns any of the three species.
ROSTERS = (
    {'cave': 'tutorial_3', 'floor': 8, 'entries': ('Queen_dashboots', 'Baby', 'Baby'),
     'treasure': 'Repugnant Appendage', 'mode': 'story',
     'notes': 'Baby rows weight 9 type 0', 'source': 'output/bulblax_audit_ref.md:28'},
    {'cave': 'forest_1', 'floor': 5, 'entries': ('Queen_radar_a',),
     'treasure': 'Prototype Detector', 'mode': 'story', 'source': 'output/bulblax_audit_ref.md:29'},
    {'cave': 'forest_3', 'floor': 7, 'entries': ('KingChappy_suit_fire',),
     'treasure': 'Forged Courage', 'mode': 'story', 'source': 'output/bulblax_audit_ref.md:30'},
    {'cave': 'last_1', 'floor': 4, 'entries': ('KingChappy_g_futa_koiwai', 'KingChappy'),
     'treasure': 'dairy lid', 'mode': 'story', 'source': 'output/bulblax_audit_ref.md:31'},
    {'cave': 'last_2', 'floor': 10, 'entries': ('KingChappy_j_block_white', 'KingChappy'),
     'treasure': 'white block', 'mode': 'story', 'source': 'output/bulblax_audit_ref.md:32'},
    {'cave': 'last_2', 'floor': 11, 'entries': ('Queen_j_block_blue',),
     'treasure': 'blue block', 'mode': 'story', 'source': 'output/bulblax_audit_ref.md:33'},
    {'cave': 'ch_MUKI_king', 'floor': 4, 'entries': ('Queen_key',),
     'treasure': 'The Key', 'mode': 'challenge', 'notes': 'type 8',
     'source': 'output/bulblax_audit_ref.md:34'},
    {'cave': 'ch_MUKI_king', 'floor': 5,
     'entries': ('KingChappy_key', 'KingChappy_gold_medal', 'KingChappy_silver_medal'),
     'treasure': None, 'mode': 'challenge', 'source': 'output/bulblax_audit_ref.md:35'},
)
NO_SURFACE_OR_BATTLE_PLACEMENTS = True  # audit line 37


# ---------------------------------------------------------------------------
# Queen (Empress Bulblax, enemy ID 30)
# ---------------------------------------------------------------------------

QUEEN_STATES = {'dead': 0, 'sleep': 1, 'wait': 2, 'damage': 3, 'flick': 4, 'rolling': 5, 'born': 6}
QUEEN_STATES_SOURCE = 'include/Game/Entities/Queen.h:26-34'

# Animation key-event streams, queen/enemyanimmgr.txt (audit lines 110-114);
# values verified against output/bulblax-run1/bulblax.json by --check.
QUEEN_CLIPS = {
    'dead': {'frames': 140, 'events': [[60, 2], [73, 2], [86, 2], [99, 2]], 'loops': []},
    'sleep': {'frames': 210, 'events': [[59, 0], [118, 1], [120, 2]], 'loops': [[59, 0], [118, 1]]},
    'wait1': {'frames': 30, 'events': [[0, 0], [29, 1]], 'loops': [[0, 0], [29, 1]]},
    'damage': {'frames': 50, 'events': [[10, 0], [29, 1]], 'loops': [[10, 0], [29, 1]]},
    'flick': {'frames': 60, 'events': [[40, 2]], 'loops': []},
    'rolling_l': {'frames': 110, 'events': [[20, 0], [67, 2], [69, 1]], 'loops': [[20, 0], [69, 1]]},
    'rolling_r': {'frames': 110, 'events': [[20, 0], [67, 2], [69, 1]], 'loops': [[20, 0], [69, 1]]},
    'born': {'frames': 28, 'events': [[24, 2]], 'loops': []},
    'carry': {'frames': 40, 'events': [[10, 0], [29, 1]], 'loops': [[10, 0], [29, 1]]},
}
# Queen anim index of rolling_r (QUEENANIM_RollingR), Queen.h:202.
QUEEN_ANIM_ROLLING_R = 6

# QueenParms proper parameters, include/Game/Entities/Queen.h:167-179; disc
# overrides from output/bulblax-run1/bulblax.json proper_retail.
QUEEN_PROPER_PARMS = {
    'rolling_time': {'key': 'fp01', 'header': 10.0, 'disc': 3.5, 'source': 'include/Game/Entities/Queen.h:167'},
    'birth_interval': {'key': 'fp02', 'header': 0.0, 'disc': 2.0, 'source': 'include/Game/Entities/Queen.h:168'},
    'hob_health': {'key': 'fp11', 'header': 2500.0, 'disc': 3300.0, 'source': 'include/Game/Entities/Queen.h'},
    'max_births': {'key': 'ip01', 'header': 50, 'disc': 50, 'source': 'include/Game/Entities/Queen.h:170'},
    'min_births': {'key': 'ip02', 'header': 25, 'disc': 25, 'source': 'include/Game/Entities/Queen.h:171'},
}

# GeneralParms disc values used by Queen behavior (audit lines 76-118),
# enemy/parm/enemyParms.szs queen/enemyparm.txt.
QUEEN_GENERAL_DISC = {
    'health': {'key': 'fp00', 'value': 5000.0},
    'move_speed': {'key': 'fp06', 'value': 125.0},
    'territory_radius': {'key': 'fp09', 'value': 200.0},
    'home_radius': {'key': 'fp10', 'value': 25.0},
    'sight_radius': {'key': 'fp12', 'value': 200.0},
    'search_distance': {'key': 'fp14', 'value': 50.0},
    'shake_chance': {'key': 'fp16', 'value': 1.0},
    'shake_knockback': {'key': 'fp17', 'value': 300.0},
    'shake_damage': {'key': 'fp18', 'value': 1.0},
    'attack_radius': {'key': 'fp22', 'value': 150.0},
    'attack_hit_angle': {'key': 'fp23', 'value': 25.0},
    'attack_damage': {'key': 'fp24', 'value': 10.0},
    'damage_scale_melee': {'key': 'fp02', 'value': 0.0},
    'damage_scale_ranged': {'key': 'fp03', 'value': 0.05},
}
QUEEN_GENERAL_DISC_SOURCE = 'enemy/parm/enemyParms.szs queen/enemyparm.txt'

# Shake-off thresholds (disc), general parms ip01..ip07 (audit lines 107-108).
QUEEN_SHAKE_OFF_DISC = {
    'blows': (30, 35, 45, 50),     # ip01, ip03, ip05, ip07
    'sticking': (5, 10, 15),       # ip02, ip04, ip06
    'source': QUEEN_GENERAL_DISC_SOURCE,
}

# Damage coefficients, src/plugProjectNishimuraU/Queen.cpp:184-198.
QUEEN_DAMAGE = {
    'sleep_factor': {'value': 0.1, 'source': 'src/plugProjectNishimuraU/Queen.cpp:188-189'},
    'flick_factor': {'value': 0.2, 'source': 'src/plugProjectNishimuraU/Queen.cpp:190-191'},
    'other_factor': {'value': 1.0, 'source': 'src/plugProjectNishimuraU/Queen.cpp:193'},
    'pikmin_part_only': {'value': True, 'source': 'src/plugProjectNishimuraU/Queen.cpp:186'},
    'captain_punch_factor': {'value': 0.0, 'source': 'output/bulblax_audit_ref.md:104'},
    'petrified_factor': {'value': 0.25, 'source': 'output/bulblax_audit_ref.md:105'},
    'earthquake_immune': {'value': True, 'source': 'src/plugProjectNishimuraU/Queen.cpp:204-207'},
}

# Flick behavior, src/plugProjectNishimuraU/Queen.cpp:324-345.
QUEEN_FLICK = {
    'damage_joints': ('nose', 'head', 'bod1'),
    'reversed_joint': 'bod5',
    'knockback': {'key': 'fp17', 'disc': 300.0},
    'damage': {'key': 'fp18', 'disc': 1.0},
    'other_joints_shaken_off_without_damage': True,
    'source': 'src/plugProjectNishimuraU/Queen.cpp:324-345',
}

# rollingAttack geometry, src/plugProjectNishimuraU/Queen.cpp:287-318.
QUEEN_ROLLING_ATTACK = {
    'cell_sphere_radius': 250.0,
    'max_height_difference': 50.0,
    'attack_radius': {'key': 'fp22', 'disc': 150.0},
    'attack_hit_angle': {'key': 'fp23', 'disc': 25.0},
    'press_damage': {'key': 'fp24', 'disc': 10.0},
    'source': 'src/plugProjectNishimuraU/Queen.cpp:287-318',
}

# Collision tree, enemy/data/Queen/enemycoll.txt via output/bulblax-run1/bulblax.json.
QUEEN_COLLISION = {
    'root_radius': 275.0,
    'children': {'bod3': 90.0, 'bod4': 85.0, 'bod5': 75.0, 'bod2': 80.0,
                 'bod1': 60.0, 'head': 25.0, 'nose': 10.0},
    'all_stickable': True,
    'source': 'queen/enemycoll.txt',
}

# Larva birth (audit lines 88-94); shared Baby::Mgr pool, not per Empress.
QUEEN_LARVAE = {
    'shared_pool': True,
    'max_births': {'key': 'ip01', 'disc': 50},
    'min_births': {'key': 'ip02', 'disc': 25},
    'birth_interval_seconds': {'key': 'fp02', 'header': 0.0, 'disc': 2.0},
    'launch_speed': {'key': 'fp14', 'disc': 50.0},
    'birth_joint': 'body_end',
    'nothing_kills_larvae_on_death': True,
    'piklopedia_disables_larvae': {'value': True, 'source': 'src/plugProjectNishimuraU/Queen.cpp:90-91'},
    'source': 'src/plugProjectNishimuraU/Queen.cpp:423-479',
}

# Special-case variants, src/plugProjectNishimuraU/Queen.cpp:85-105, 355-380, 384-410.
QUEEN_VARIANTS = {
    'f_01': {'cave': 'forest_1', 'no_larvae': True, 'easy_first_roll': True,
             'health': {'key': 'fp11', 'header': 2500.0, 'disc': 3300.0},
             'source': 'src/plugProjectNishimuraU/Queen.cpp:95-100'},
    'l_02': {'cave': 'last_2', 'crash_rocks': 7, 'rock_lifetime_seconds': 30.0,
             'source': 'src/plugProjectNishimuraU/Queen.cpp:384-410'},
}

QUEEN_WAIT_IDLE_SLEEP_SECONDS = 30.0  # src/plugProjectNishimuraU/QueenState.cpp:154
QUEEN_TERRITORY_CRASH_MARGIN = 50.0   # territory - 50, QueenState.cpp:403-409


def queen_entry_state(can_create_larva):
    """Entry state: Wait when larvae are allowed, else Sleep.

    src/plugProjectNishimuraU/Queen.cpp:62-66.
    """
    return 'wait' if can_create_larva else 'sleep'


def queen_sleep_next(*, health, hit_counter_up, larva_due, start_flick, stuck_pikmin):
    """StateSleep deferred next state, or None to keep sleeping.

    Motion finishes when health is gone, the hit counter rose or a larva is
    due; then Dead > Flick > Damage (Pikmin stuck) > Wait.
    src/plugProjectNishimuraU/QueenState.cpp:89-103.
    """
    _finite(health)
    if not (health <= 0.0 or hit_counter_up or larva_due):
        return None
    if health <= 0.0:
        return 'dead'
    if start_flick:
        return 'flick'
    if stuck_pikmin:
        return 'damage'
    return 'wait'


def queen_wait_next(*, larva_due, idle_seconds, hit_counter_up, start_flick, health):
    """StateWait deferred next state, or None to keep waiting.

    Checks run Sleep, Damage, Born, Flick, Dead in that order with later
    checks overriding. src/plugProjectNishimuraU/QueenState.cpp:153-173.
    """
    for value in (idle_seconds, health):
        _finite(value)
    next_state = None
    if not larva_due and idle_seconds > QUEEN_WAIT_IDLE_SLEEP_SECONDS:
        next_state = 'sleep'
    if hit_counter_up:
        next_state = 'damage'
    if larva_due:
        next_state = 'born'
    if start_flick:
        next_state = 'flick'
    if health <= 0.0:
        next_state = 'dead'
    return next_state


def queen_damage_next(*, larva_due, stuck_pikmin, start_flick, health):
    """StateDamage deferred next state; later checks override.

    Born, Wait when nothing is stuck, Flick, Dead.
    src/plugProjectNishimuraU/QueenState.cpp:219-237.
    """
    _finite(health)
    next_state = None
    if larva_due:
        next_state = 'born'
    if not stuck_pikmin:
        next_state = 'wait'
    if start_flick:
        next_state = 'flick'
    if health <= 0.0:
        next_state = 'dead'
    return next_state


def queen_flick_end(*, health, rolling_left):
    """StateFlick KEYEVENT_END: Dead, else Rolling with side from isRollingAttackLeft.

    src/plugProjectNishimuraU/QueenState.cpp:281-293.
    """
    _finite(health)
    if health <= 0.0:
        return ('dead', None)
    return ('rolling', 'left' if rolling_left else 'right')


def queen_next_roll_is_left(current_anim_index):
    """The next Rolling pass is "left" when the current animation is rolling_r
    (anim index 6), so direction alternates.

    src/plugProjectNishimuraU/QueenState.cpp:441-447. Any non-null arg pointer
    means "left" (audit lines 252-253).
    """
    if type(current_anim_index) is not int:
        raise ValueError('Expected animation index')
    return current_anim_index == QUEEN_ANIM_ROLLING_R


def queen_roll_pass(*, dot_along_roll, rolling_elapsed, rolling_time, home_radius,
                    territory_radius, health):
    """Rolling pass outcome per frame: 'crash', 'wait' or 'continue'.

    Crash when the position projected along the roll direction exceeds
    territory - 50 (queues another Rolling pass); otherwise once the rolling
    time elapses and she is near home the pass ends in Wait.
    src/plugProjectNishimuraU/QueenState.cpp:405-433. RECONSTRUCTED
    (StateRolling::exec carries retained assembly; non-authoritative).
    """
    for value in (dot_along_roll, rolling_elapsed, rolling_time, home_radius,
                  territory_radius, health):
        _finite(value)
    if dot_along_roll > territory_radius - QUEEN_TERRITORY_CRASH_MARGIN:
        return 'crash'
    if rolling_elapsed > rolling_time and -(50.0 + home_radius) < dot_along_roll < 50.0:
        return 'wait'
    return 'continue'


queen_roll_pass.reconstructed = True


def queen_larva_room(*, alive_larvae, room_flag, max_births=50, min_births=25):
    """Room-flag hysteresis on the shared Baby::Mgr pool: at max_births the
    flag clears, at min_births it sets again, between them it keeps its value.

    src/plugProjectNishimuraU/Queen.cpp:469-479 (updateCreateBaby).
    """
    if type(alive_larvae) is not int or alive_larvae < 0:
        raise ValueError('Expected non-negative larva count')
    if alive_larvae >= max_births:
        return False
    if alive_larvae <= min_births:
        return True
    return bool(room_flag)


def queen_birth_due(*, can_create_larva, room_flag, birth_timer, birth_interval):
    """A birth is due when larvae are allowed, there is room and mBirthTimer
    exceeds mBirthInterval. src/plugProjectNishimuraU/Queen.cpp:469-479,
    isCreateBaby (audit lines 91-92).
    """
    for value in (birth_timer, birth_interval):
        _finite(value)
    return bool(can_create_larva and room_flag and birth_timer > birth_interval)


def queen_damage_factor(*, state, attacker, petrified=False):
    """Damage coefficient; returns 0.0 when the damage is ignored entirely.

    Only Pikmin hitting a collision part count (Queen.cpp:184-198); captain
    punches do nothing (audit:104). Petrified coefficient 0.25 (audit:105).
    Earthquake is rejected by earthquakeCallBack (Queen.cpp:204-207).
    """
    _finite(QUEEN_DAMAGE['sleep_factor']['value'])
    if attacker not in ('pikmin_part', 'captain_punch', 'earthquake'):
        raise ValueError('Unknown attacker kind')
    if attacker == 'earthquake':
        return 0.0
    if petrified:
        return QUEEN_DAMAGE['petrified_factor']['value']
    if attacker == 'captain_punch':
        return 0.0
    if state == 'sleep':
        return 0.1
    if state == 'flick':
        return 0.2
    return 1.0


def queen_flick_effect(part_id):
    """flickPikmin: Pikmin stuck to nose/head/bod1 are flicked with
    mShakeKnockback/mShakeDamage, bod5 with a reversed angle; anything else is
    shaken off without damage. src/plugProjectNishimuraU/Queen.cpp:324-345.
    """
    if part_id in QUEEN_FLICK['damage_joints']:
        return 'flick'
    if part_id == QUEEN_FLICK['reversed_joint']:
        return 'flick_reversed'
    return 'shake_off'


def queen_variant(cave_id, *, zukan_mode=False):
    """Variant overrides for a cave ID, or None for the default Empress.

    Piklopedia disables larvae (Queen.cpp:90-91); f_01 (Hole of Beasts)
    disables larvae, swaps in mHoBHealth and sets mDoEasyRoll so the first
    roll goes away from the active captain (Queen.cpp:95-100, 357-379); l_02
    (Hole of Heroes) makes each crash spawn 7 Rocks with a 30 s lifetime
    (Queen.cpp:384-410).
    """
    if zukan_mode:
        return {'no_larvae': True}
    if cave_id == 'f_01':
        return {'no_larvae': True, 'easy_first_roll': True,
                'health': QUEEN_PROPER_PARMS['hob_health']['disc']}
    if cave_id == 'l_02':
        return {'crash_rocks': 7, 'rock_lifetime_seconds': 30.0}
    return None


# ---------------------------------------------------------------------------
# Baby (Bulborb Larva, enemy ID 31)
# ---------------------------------------------------------------------------

BABY_STATES = {'dead': 0, 'press': 1, 'born': 2, 'move': 3, 'attack': 4}
BABY_STATES_SOURCE = 'include/Game/Entities/Baby.h:140'

# baby/enemyanimmgr.txt (audit lines 152-153).
BABY_CLIPS = {
    'dead': {'frames': 100, 'events': [], 'loops': []},
    'deadpress': {'frames': 80, 'events': [], 'loops': []},
    'move': {'frames': 12, 'events': [[0, 0], [11, 1]], 'loops': [[0, 0], [11, 1]]},
    'attack': {'frames': 70, 'events': [[10, 2], [30, 3]], 'loops': []},
    'attackfail': {'frames': 20, 'events': [], 'loops': []},
    'born': {'frames': 35, 'events': [[7, 0], [8, 1]], 'loops': [[7, 0], [8, 1]]},
}

# ProperParms, include/Game/Entities/Baby.h; disc = header here.
BABY_PROPER_PARMS = {
    'poison_damage': {'key': 'fp01', 'header': 300.0, 'disc': 300.0,
                      'source': 'include/Game/Entities/Baby.h'},
    'nectar_chance': {'key': 'fp11', 'header': 0.2, 'disc': 0.2,
                      'source': 'include/Game/Entities/Baby.h'},
}

BABY_GENERAL_DISC = {
    'health': {'key': 'fp00', 'value': 5.0},
    'move_speed': {'key': 'fp06', 'value': 40.0},
    'sight_radius': {'key': 'fp12', 'value': 800.0},
    'view_angle': {'key': 'fp13', 'value': 180.0},
    'max_attack_range': {'key': 'fp20', 'value': 30.0},
    'max_attack_angle': {'key': 'fp21', 'value': 45.0},
    'attack_damage': {'key': 'fp24', 'value': 2.0},
}
BABY_GENERAL_DISC_SOURCE = 'enemy/parm/enemyParms.szs baby/enemyparm.txt'

# Mouth: one slot on joint 'kamu', radius 20 (src/plugProjectNishimuraU/Baby.cpp:202-208).
BABY_MOUTH = {'slots': 1, 'joint': 'kamu', 'radius': 20.0,
              'source': 'src/plugProjectNishimuraU/Baby.cpp:202-208'}

# Collision, baby/enemycoll.txt.
BABY_COLLISION = {'root_radius': 25.0, 'children': {'stickable_child': 15.0},
                  'source': 'baby/enemycoll.txt'}

# EB_Cullable and EB_LeaveCarcass disabled at init: larvae update off camera
# and never become carcasses (src/plugProjectNishimuraU/Baby.cpp:38-41).
BABY_DISABLED_EVENTS = ('EB_Cullable', 'EB_LeaveCarcass')

# No lifetime timer and no parent link: larvae born from the Empress persist
# until killed (audit lines 145-148).
BABY_PERSISTS_UNTIL_KILLED = {
    'value': True,
    'source': 'src/plugProjectYamashitaU/enemyMgrBase.cpp:214, src/plugProjectYamashitaU/enemyBase.cpp:521',
}


def baby_entry_state(zukan_mode):
    """Starts in Born; Move in the Piklopedia.

    src/plugProjectNishimuraU/Baby.cpp:44-47 (audit line 125).
    """
    return 'move' if zukan_mode else 'born'


def baby_press_kills(*, state_id, petrified):
    """Instant crush: any press or purple pound while in Move or Attack
    (state ID > 2) and not petrified transits to Press; the damage value is
    ignored. src/plugProjectNishimuraU/Baby.cpp:114-137.
    """
    if type(state_id) is not int:
        raise ValueError('Expected state ID')
    return (not petrified) and state_id > BABY_STATES['born']


def baby_move_step(*, angle_dist, max_attack_angle, move_speed, target_distance,
                   max_attack_range, has_target):
    """StateMove: walk at full speed when facing the target, quarter speed
    while turning; enter Attack inside range and angle; wander with no target.

    Returns (target_speed, next_state_or_None).
    src/plugProjectNishimuraU/BabyState.cpp:153-186. RECONSTRUCTED
    (StateMove::exec carries retained assembly; non-authoritative).
    """
    for value in (angle_dist, max_attack_angle, move_speed, target_distance,
                  max_attack_range):
        _finite(value)
    if not has_target:
        return (0.0, None)
    speed = move_speed if abs(angle_dist) <= abs(max_attack_angle) else 0.25 * move_speed
    attack = (target_distance <= max_attack_range
              and abs(angle_dist) <= abs(max_attack_angle))
    return (speed, 'attack' if attack else None)


baby_move_step.reconstructed = True


def baby_attack_key2(*, mouth_occupied):
    """Attack KEYEVENT_2: hits captains with mAttackDamage (2 disc) and tries
    to eat; with an empty mouth the motion switches to attackfail.

    src/plugProjectNishimuraU/BabyState.cpp:516-540.
    """
    return 'continue' if mouth_occupied else 'attackfail'


def baby_born_next(*, landed, health):
    """StateBorn damps velocity (0.95 per frame) until landed, then finishes
    the motion; KEYEVENT_END goes to Move or Dead.
    src/plugProjectNishimuraU/BabyState.cpp:107-127.
    """
    _finite(health)
    if not landed:
        return None
    return 'dead' if health <= 0.0 else 'move'


# ---------------------------------------------------------------------------
# KingChappy (Emperor Bulblax, enemy ID 53)
# ---------------------------------------------------------------------------

KING_STATES = {'walk': 0, 'attack': 1, 'dead': 2, 'flick': 3, 'warcry': 4, 'damage': 5,
               'turn': 6, 'eat': 7, 'hide': 8, 'hidewait': 9, 'appear': 10,
               'caution': 11, 'swallow': 12}
KING_STATES_SOURCE = 'include/Game/Entities/KingChappy.h:22-36'

# kingchappy/enemyanimmgr.txt (audit lines 225-231).
KING_CLIPS = {
    'attack': {'frames': 95, 'events': [[25, 2], [40, 3], [70, 4], [86, 5], [92, 6]], 'loops': []},
    'cry': {'frames': 138, 'events': [[33, 2], [38, 3], [65, 4], [100, 5], [103, 6]], 'loops': []},
    'damage': {'frames': 135, 'events': [[12, 2], [14, 3], [15, 4], [46, 5], [60, 6], [65, 0], [94, 1]],
               'loops': [[65, 0], [94, 1]]},
    'dead': {'frames': 200, 'events': [[185, 2]], 'loops': []},
    'dive': {'frames': 142, 'events': [[58, 2], [60, 3], [90, 4]], 'loops': []},
    'flick': {'frames': 70, 'events': [[30, 2], [35, 3]], 'loops': []},
    'move1': {'frames': 80, 'events': [[15, 0], [54, 1]], 'loops': [[15, 0], [54, 1]]},
    'type1': {'frames': 45, 'events': [], 'loops': []},
    'type2': {'frames': 35, 'events': [], 'loops': []},
    'type3': {'frames': 75, 'events': [[3, 2], [55, 3], [58, 4]], 'loops': []},
    'wait2': {'frames': 40, 'events': [[0, 0], [39, 1]], 'loops': [[0, 0], [39, 1]]},
    'waitact1': {'frames': 50, 'events': [[10, 0], [33, 1]], 'loops': [[10, 0], [33, 1]]},
    'waitact2': {'frames': 60, 'events': [], 'loops': []},
    'carry': {'frames': 40, 'events': [[10, 0], [29, 1]], 'loops': [[10, 0], [29, 1]]},
}

# ProperParms, include/Game/Entities/KingChappy.h:51-74; disc overrides from
# output/bulblax-run1/bulblax.json proper_retail.
KING_PROPER_PARMS = {
    'required_turning_angle_deg': {'key': 'fp01', 'header': 20.0, 'disc': 60.0,
                                   'source': 'include/Game/Entities/KingChappy.h:51'},
    'distance_to_spawn': {'key': 'fp02', 'header': 150.0, 'disc': 60.0,
                          'source': 'include/Game/Entities/KingChappy.h:52'},
    'roar_effective_angle_deg': {'key': 'fp03', 'header': 45.0, 'disc': 180.0,
                                 'source': 'include/Game/Entities/KingChappy.h:53'},
    'roar_effective_range': {'key': 'fp04', 'header': 100.0, 'disc': 300.0,
                             'source': 'include/Game/Entities/KingChappy.h:54'},
    'bomb_damage': {'key': 'fp05', 'header': 200.0, 'disc': 200.0,
                    'source': 'include/Game/Entities/KingChappy.h:55'},
    'invisible_range': {'key': 'fp06', 'header': 70.0, 'disc': 80.0,
                        'source': 'include/Game/Entities/KingChappy.h:56'},
    'turning_end_angle': {'key': 'fp07', 'header': 10.0, 'disc': 40.0,
                          'source': 'include/Game/Entities/KingChappy.h:57'},
    'trampling_range': {'key': 'fp08', 'header': 45.0, 'disc': 45.0,
                        'source': 'include/Game/Entities/KingChappy.h:58'},
    'appearance_shake_off_range': {'key': 'fp09', 'header': 100.0, 'disc': 100.0,
                                   'source': 'include/Game/Entities/KingChappy.h:59'},
    'appearance_shake_off_power': {'key': 'fp10', 'header': 200.0, 'disc': 200.0,
                                   'source': 'include/Game/Entities/KingChappy.h:60'},
    'death_rate': {'key': 'fp12', 'header': 0.0, 'disc': 0.0,
                   'source': 'include/Game/Entities/KingChappy.h:62'},
    'flick_shout_rate': {'key': 'fp13', 'header': 0.5, 'disc': 0.5,
                         'source': 'include/Game/Entities/KingChappy.h:63'},
    'white_pikmin': {'key': 'fp14', 'header': 300.0, 'disc': 200.0,
                     'source': 'include/Game/Entities/KingChappy.h:64'},
    'big_scale': {'key': 'fp15', 'header': 1.0, 'disc': 1.5,
                  'source': 'include/Game/Entities/KingChappy.h:65'},
    'big_life': {'key': 'fp16', 'header': 100.0, 'disc': 1800.0,
                 'source': 'include/Game/Entities/KingChappy.h:66'},
    'big_speed': {'key': 'fp17', 'header': 80.0, 'disc': 45.0,
                  'source': 'include/Game/Entities/KingChappy.h:67'},
    'period_of_incubation': {'key': 'ip01', 'header': 500, 'disc': 500,
                             'source': 'include/Game/Entities/KingChappy.h:72'},
    'time_to_appearance': {'key': 'ip02', 'header': 200, 'disc': 0,
                           'source': 'include/Game/Entities/KingChappy.h:73'},
    'bomb_damage_time': {'key': 'ip03', 'header': 10, 'disc': 180,
                         'source': 'include/Game/Entities/KingChappy.h:74'},
}

KING_GENERAL_DISC = {
    'health': {'key': 'fp00', 'value': 1300.0},
    'shake_range': {'key': 'fp19', 'value': 60.0},
    'attack_damage': {'key': 'fp24', 'value': 5.0},
}
KING_GENERAL_DISC_SOURCE = 'enemy/parm/enemyParms.szs kingchappy/enemyparm.txt'

# Mouth: 9 slots kamu1..kamu9, radius 25 * mScaleModifier; tongue tip joint
# bero6 (radius 5) aborts the lick on floor/wall contact.
KING_MOUTH = {
    'slots': 9,
    'slot_joints': tuple('kamu%d' % i for i in range(1, 10)),
    'slot_radius': 25.0,
    'slot_radius_scaled': True,
    'tongue_joint': 'bero6',
    'tongue_radius': 5.0,
    'source': 'src/plugProjectMorimuraU/kingChappy.cpp:98,993-1003',
}

# Collision, kingchappy/enemycoll.txt (audit lines 217-219).
KING_COLLISION = {
    'root_radius': 80.0,
    'children': {'back': 35.0, 'ketu': 40.0, 'asiL': 8.0, 'asiR': 8.0,
                 'head': 30.0, 'hana': 18.0, 'kuti': 22.0},
    'stickable': ('head', 'hana', 'kuti'),
    'source': 'kingchappy/enemycoll.txt',
}

# Stone state marks back and ketu stickable and restores them afterwards,
# src/plugProjectMorimuraU/kingChappy.cpp:917-953.
KING_STONE_STATE_PARTS = {'mark_stickable': ('back', 'ketu'), 'restore_code': '_t__',
                          'source': 'src/plugProjectMorimuraU/kingChappy.cpp:917-953'}

# Attack key events (audit lines 180-185): key 3 arms eating, key 6 allows
# bomb eating; captains in any mouth slot take mAttackDamage (5 disc).
KING_ATTACK = {
    'arm_eat_key': KEYEVENT_3,
    'allow_bombs_key': KEYEVENT_6,
    'captain_damage': {'key': 'fp24', 'disc': 5.0},
    'swallow_poison_damage': {'value': 300.0, 'hardcoded': True,
                              'source': 'src/plugProjectMorimuraU/kingChappyState.cpp StateSwallow::exec'},
    'source': 'src/plugProjectMorimuraU/kingChappyState.cpp:133-743',
}

# Bomb ingestion (audit lines 201-205): eatBomb only takes bombs that can be
# eaten (BOMB_Wait); damage multiplies by count; external blasts are quartered.
KING_BOMB = {
    'eatable_state': 'BOMB_Wait',
    'damage_per_bomb': {'key': 'fp05', 'header': 200.0, 'disc': 200.0},
    'stun_frames': {'key': 'ip03', 'header': 10, 'disc': 180},
    'external_blast_factor': {'value': 0.25, 'source': 'src/plugProjectMorimuraU/kingChappy.cpp:873-877'},
    'source': 'src/plugProjectMorimuraU/kingChappy.cpp:1009-1043',
}

# Big variant, src/plugProjectMorimuraU/kingChappy.cpp:60-72, 148-158.
KING_BIG_VARIANT = {
    'trigger_cave_id': 'f_03',
    'force_flag': 'mDoForceBig',
    'scale': {'key': 'fp15', 'disc': 1.5},
    'health': {'key': 'fp16', 'disc': 1800.0},
    'speed': {'key': 'fp17', 'disc': 45.0},
    'floor_offset': 60.0,
    'source': 'src/plugProjectMorimuraU/kingChappy.cpp:60-72,148-158',
}

# WarCry cross-Emperor coordination: key 3 asks the manager to wake one
# buried Emperor (forceTransit to Appear) and make one walking Emperor roar
# (forceTransit to WarCry); the only cross-Emperor contract.
KING_WARCRY = {
    'astonish_range': {'key': 'fp04', 'header': 100.0, 'disc': 300.0},
    'astonish_angle_deg': {'key': 'fp03', 'header': 45.0, 'disc': 180.0},
    'cross_emperor': {'wake_state': 'appear', 'roar_state': 'warcry',
                      'source': 'src/plugProjectMorimuraU/kingChappyMgr.cpp:53-62, src/plugProjectMorimuraU/kingChappy.cpp:1548'},
    'source': 'src/plugProjectMorimuraU/kingChappyState.cpp StateWarCry::exec',
}

# Entry: buried in HideWait with hard constraint on, life gauge hidden and
# bitter immunity (src/plugProjectMorimuraU/kingChappy.cpp:107,
# kingChappyState.cpp:1954-1965).
KING_ENTRY_STATE = 'hidewait'


def king_entry_state():
    """Starts buried in HideWait. src/plugProjectMorimuraU/kingChappy.cpp:107."""
    return KING_ENTRY_STATE


def king_hidewait_wake(*, nearest_target_distance, frames_waited, scale,
                       distance_to_spawn, time_to_appearance):
    """HideWait -> Appear when a captain or any Pikmin is within
    mDistanceToSpawn * scale after mTimeToAppearance frames (or at animation
    end, handled by the caller). src/plugProjectMorimuraU/kingChappyState.cpp:1970-2016.
    """
    for value in (nearest_target_distance, scale, distance_to_spawn):
        _finite(value)
    if type(frames_waited) is not int or frames_waited < 0:
        raise ValueError('Expected non-negative frame count')
    if frames_waited <= time_to_appearance:
        return False
    return nearest_target_distance < distance_to_spawn * scale


def king_walk_turn(*, goal_angle_off, required_turning_angle, turning_end_angle):
    """Walk turn decision: 'turn' when the goal is more than the required
    turning angle off, 'finish_turn' when back within the turning end angle,
    else 'walk'. src/plugProjectMorimuraU/kingChappyState.cpp:53-117.
    """
    for value in (goal_angle_off, required_turning_angle, turning_end_angle):
        _finite(value)
    off = abs(goal_angle_off)
    if off > required_turning_angle:
        return 'turn'
    if off <= turning_end_angle:
        return 'finish_turn'
    return 'walk'


def king_walk_give_up(*, frames_without_target, period_of_incubation, out_of_territory):
    """Walk loses interest after mPeriodOfIncubation frames without a target
    or when out of territory; returns home and enters Hide.
    src/plugProjectMorimuraU/kingChappyState.cpp:53-117.
    """
    if type(frames_without_target) is not int or frames_without_target < 0:
        raise ValueError('Expected non-negative frame count')
    return out_of_territory or frames_without_target > period_of_incubation


def king_check_flick(*, health, max_health, roll, flick_shout_rate=0.5):
    """checkFlick once isStartFlick fires: roar (WarCry) with probability
    mFlickShoutRate when under half health, otherwise Flick.
    src/plugProjectMorimuraU/kingChappy.cpp:2457-2474.
    """
    for value in (health, max_health, roll, flick_shout_rate):
        _finite(value)
    if not 0.0 <= roll <= 1.0 or max_health <= 0.0:
        raise ValueError('Invalid flick input')
    if health < 0.5 * max_health and roll < flick_shout_rate:
        return 'warcry'
    return 'flick'


def king_damage_tier(*, petrified, has_part, stuck_to_part, attacker_dy, sqr_distance_xz):
    """damageCallBack: 0.1 while petrified; full damage from a creature stuck
    to a collision part; 0.2 from a ground-level attacker (y < 5 + position)
    within 40 units with no part; nothing from above.
    src/plugProjectMorimuraU/kingChappy.cpp:824-856. Returns the coefficient.
    """
    for value in (attacker_dy, sqr_distance_xz):
        _finite(value)
    if petrified:
        return 0.1
    if has_part:
        return 1.0 if stuck_to_part else 0.0
    if attacker_dy < 5.0:
        return 0.2 if sqr_distance_xz < 40.0 ** 2 else 0.0
    return 0.0


def king_bomb_damage(*, bombs_eaten, bomb_damage=200.0):
    """Damage KEYEVENT_4: kills everything in the mouth and applies
    bombs * mBombDamage. src/plugProjectMorimuraU/kingChappyState.cpp StateDamage::exec.
    """
    _finite(bomb_damage)
    if type(bombs_eaten) is not int or bombs_eaten < 0:
        raise ValueError('Expected non-negative bomb count')
    return bombs_eaten * bomb_damage


def king_eatable_bomb(bomb_state):
    """eatBomb only accepts a Bomb that can be eaten (BOMB_Wait) and is not
    already stuck to a mouth. src/plugProjectMorimuraU/kingChappy.cpp:1009-1043.
    """
    return bomb_state == KING_BOMB['eatable_state']


def king_is_big(*, cave_id, force_big=False):
    """Big variant in forest_3 (getCaveID() == 'f_03') or with mDoForceBig.
    src/plugProjectMorimuraU/kingChappy.cpp:148-158.
    """
    return bool(force_big) or cave_id == KING_BIG_VARIANT['trigger_cave_id']


def king_attack_step(*, key, mouth_slots_free, bombs_in_range, pikmin_in_range):
    """Attack armed-frame contract (key 3 arms eating, key 6 allows bombs):
    each armed frame tries eatBomb and EnemyFunc::eatPikmin.
    Returns a frozenset of actions. RECONSTRUCTED (StateAttack::exec,
    searchTarget and checkAttack carry retained assembly; non-authoritative).
    src/plugProjectMorimuraU/kingChappyState.cpp:133-743.
    """
    actions = set()
    if key == KEYEVENT_6 and bombs_in_range and mouth_slots_free:
        actions.add('eat_bomb')
    if key in (KEYEVENT_3, KEYEVENT_6) and pikmin_in_range and mouth_slots_free:
        actions.add('eat_pikmin')
    return frozenset(actions)


king_attack_step.reconstructed = True


def king_flick_step(*, pikmin_in_trample_range, captains_in_trample_range):
    """Flick key 3 presses every Pikmin and captain within mTramplingRange
    (45) * scale of the foot in a 30 unit height band, then the standard
    flick triple; captains are only flicked if none was pressed.
    RECONSTRUCTED (StateFlick::exec carries retained assembly;
    non-authoritative). src/plugProjectMorimuraU/kingChappyState.cpp:835-1574.
    """
    if type(pikmin_in_trample_range) is not int or type(captains_in_trample_range) is not int:
        raise ValueError('Expected creature counts')
    if pikmin_in_trample_range < 0 or captains_in_trample_range < 0:
        raise ValueError('Expected non-negative counts')
    return {'pressed_pikmin': pikmin_in_trample_range,
            'pressed_captains': captains_in_trample_range,
            'flick_captains': captains_in_trample_range == 0}


king_flick_step.reconstructed = True


# ---------------------------------------------------------------------------
# Species table for --check cross-validation
# ---------------------------------------------------------------------------

SPECIES = {
    'Queen': {'enemy_id': 30, 'states': QUEEN_STATES, 'clips': QUEEN_CLIPS,
              'proper': QUEEN_PROPER_PARMS, 'general': QUEEN_GENERAL_DISC,
              'collision_root': QUEEN_COLLISION['root_radius'],
              'collision_children': QUEEN_COLLISION['children']},
    'Baby': {'enemy_id': 31, 'states': BABY_STATES, 'clips': BABY_CLIPS,
             'proper': BABY_PROPER_PARMS, 'general': BABY_GENERAL_DISC,
             'collision_root': BABY_COLLISION['root_radius'],
             'collision_children': BABY_COLLISION['children']},
    'KingChappy': {'enemy_id': 53, 'states': KING_STATES, 'clips': KING_CLIPS,
                   'proper': KING_PROPER_PARMS, 'general': KING_GENERAL_DISC,
                   'collision_root': KING_COLLISION['root_radius'],
                   'collision_children': KING_COLLISION['children']},
}

_BABY_COLLISION_CHILD_RADII = (15.0,)


def check(report_path):
    """Validate module clips, key events and disc parameter values against the
    #217 extraction report. Returns a list of mismatch strings (empty = ok).
    """
    report = json.loads(Path(report_path).read_text())
    if report.get('policy') != 'P2_BULBLAX_IMPORT_1':
        raise ValueError('Unexpected extraction report policy')
    problems = []
    for name, spec in SPECIES.items():
        entry = report['species'].get(name)
        if entry is None:
            problems.append('%s: missing from report' % name)
            continue
        if entry['enemy_id'] != spec['enemy_id']:
            problems.append('%s: enemy_id %r != %r' % (name, entry['enemy_id'], spec['enemy_id']))
        if {k: v for k, v in entry['state_ids'].items()} != {k: v for k, v in spec['states'].items()}:
            problems.append('%s: state_ids mismatch: %r' % (name, entry['state_ids']))
        clips = {c['name']: c for c in entry['clips']}
        if set(clips) != set(spec['clips']):
            problems.append('%s: clip list mismatch: report %r vs module %r'
                            % (name, sorted(clips), sorted(spec['clips'])))
        for clip_name, clip in spec['clips'].items():
            got = clips.get(clip_name)
            if got is None:
                continue
            if got['events'] != clip['events']:
                problems.append('%s/%s: events %r != %r'
                                % (name, clip_name, got['events'], clip['events']))
            if got['event_loop_boundaries'] != clip['loops']:
                problems.append('%s/%s: loop boundaries %r != %r'
                                % (name, clip_name, got['event_loop_boundaries'], clip['loops']))
            if got['source_frames'] != clip['frames']:
                problems.append('%s/%s: frames %r != %r'
                                % (name, clip_name, got['source_frames'], clip['frames']))
        # Proper parameters: header defaults and disc (retail) values.
        by_key_header = dict(entry['proper_header_defaults'])
        by_key_retail = dict(entry['proper_retail'])
        for parm_name, parm in spec['proper'].items():
            key = parm['key']
            if key not in by_key_header or key not in by_key_retail:
                problems.append('%s: missing proper key %s (%s)' % (name, key, parm_name))
                continue
            if float(by_key_header[key]) != float(parm['header']):
                problems.append('%s/%s header %r != %r'
                                % (name, key, by_key_header[key], parm['header']))
            if float(by_key_retail[key]) != float(parm['disc']):
                problems.append('%s/%s disc %r != %r'
                                % (name, key, by_key_retail[key], parm['disc']))
        # General disc values come from the second parameter block.
        general = entry['parameter_blocks'][1]
        for parm_name, parm in spec['general'].items():
            key = parm['key']
            if key not in general:
                problems.append('%s: missing general key %s (%s)' % (name, key, parm_name))
            elif float(general[key]) != float(parm['value']):
                problems.append('%s/%s general disc %r != %r'
                                % (name, key, general[key], parm['value']))
        # Collision radii.
        parts = entry['collision']
        root = [p for p in parts if p['parent'] is None]
        if len(root) != 1 or root[0]['radius'] != spec['collision_root']:
            problems.append('%s: root collision radius mismatch' % name)
        child_radii = sorted(p['radius'] for p in parts if p['parent'] is not None)
        if child_radii != sorted(spec['collision_children'].values()):
            problems.append('%s: child collision radii %r != %r'
                            % (name, child_radii, sorted(spec['collision_children'].values())))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', type=Path, metavar='REPORT',
                        help='validate against the #217 extraction report JSON')
    args = parser.parse_args(argv)
    if args.check:
        problems = check(args.check)
        if problems:
            for problem in problems:
                print('MISMATCH: %s' % problem)
            return 1
        print('bulblax behavior reference matches %s' % args.check)
        return 0
    parser.error('nothing to do; pass --check')


if __name__ == '__main__':
    sys.exit(main())
