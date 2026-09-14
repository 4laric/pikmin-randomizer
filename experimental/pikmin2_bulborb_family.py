"""Lane 13 source audit and behavior contract: Bulborbs, dwarfs and Sheargrubs.

Fan-out scope: ``docs/PIKMIN2_IMPLEMENTATION_FANOUT.md`` lane 13
("#120/#197; existing Snow/Kochappy/Uji paths"). This module is the lane's
required *source ID / variant difference audit* plus the special Bulbear and
Fiery Bulblax rules, expressed as machine-readable data and a native
acceptance-contract validator.

Source of truth (read-only decomp checkout ``native/pikmin2-research``):

* ``include/Game/enemyInfo.h``            source IDs and English names
* ``include/Game/Entities/ChappyBase.h``  adult bulborb FSM, anims, parms
* ``include/Game/Entities/KochappyBase.h``dwarf bulborb FSM, anims, parms
* ``include/Game/Entities/FireChappy.h``  Fiery Bulblax fire/water state
* ``include/Game/Entities/KumaChappy.h``  Spotty Bulbear FSM (rebirth, path)
* ``include/Game/Entities/KumaKochappy.h``Dwarf Bulbear parent-following
* ``include/Game/ChappyRelation.h``       Bulbear <-> Dwarf Bulbear relation
* ``include/Game/Entities/Ujia.h`` / ``Ujib.h`` Sheargrub FSMs and anims

This module does **not** own the canonical roster/schema (lane 02 / #438); it
supplies the family-specific variant and behavior facts lane 02 consumes. It
does not claim any arena gate: gate status here is source-backed until a real
native run exists for that identity.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SCHEMA = 'p2-bulborb-family-v1'

CHAPPY_BASE_OBJECT = 'ChappyBase'
KOCHAPPY_BASE_OBJECT = 'KochappyBase'
KUMA_BASE_OBJECT = 'KumaChappy'
UJI_BASE_OBJECT = 'EnemyBase'

CHAPPY_BASE_STATES = ('turn', 'dead', 'flick', 'walk', 'attack', 'turntohome',
                      'gohome', 'sleep')
CHAPPY_BASE_ANIMS = ('attack', 'dead', 'flick', 'move1', 'sleep(type1)',
                     'carry(type5)', 'wait2', 'waitact1', 'waitact2')
CHAPPY_BASE_PARMS = {'fp01': 'foot_range=50', 'fp02': 'poison_damage=300',
                     'fp03': 'wake_radius=400'}

KOCHAPPY_BASE_STATES = ('wait', 'dead', 'turn', 'walk', 'attack', 'flick',
                        'turntohome', 'gohome', 'press', 'demo')
KOCHAPPY_BASE_ANIMS = ('attack', 'dead', 'flick', 'move1', 'press(type1)',
                       'carry(type5)', 'wait1', 'waitact1', 'waitact2')
KOCHAPPY_BASE_PARMS = {'fp01': 'absentminded_time=2', 'fp02': 'poison_damage=300',
                       'fp03': 'rotation_end_angle=90'}

KUMA_STATES = ('dead', 'rebirth', 'lost', 'attack', 'flick', 'turn',
               'turnpath', 'walk', 'walkpath')
KUMA_ANIMS = ('attack', 'dead', 'flick', 'move1', 'carry(type5)', 'lost(wait2)',
              'turn(waitact1)', 'eat(waitact2)', 'rebirth')
KUMA_PARMS = {'fp01': 'poison_damage=300', 'fp11': 'health_gauge_timer=30',
              'fp12': 'respawn_rate=10'}

KUMAKOCHAPPY_STATES = ('dead', 'press', 'wait', 'attack', 'flick', 'walk',
                       'walkpath')
KUMAKOCHAPPY_ANIMS = ('attack', 'dead', 'flick', 'move1', 'press(type1)',
                      'carry(type5)', 'wait1', 'waitact1', 'waitact2')
KUMAKOCHAPPY_PARMS = {'fp01': 'poison_damage=300'}

UJIA_STATES = ('dead', 'press', 'stay', 'appear', 'dive', 'move', 'moveside',
               'movecentre', 'movetop', 'gohome', 'attack1')
UJIA_ANIMS = ('dead', 'dead_p', 'appear', 'dive', 'move', 'attack1', 'carry')
UJIB_STATES = ('dead', 'press', 'stay', 'appear', 'dive', 'move', 'moveside',
               'movecentre', 'movetop', 'gohome', 'attack1', 'attack2', 'eat')
UJIB_ANIMS = ('dead', 'dead_p', 'appear', 'dive', 'move', 'attack1', 'attack2',
              'eat', 'carry')
UJI_PARMS = {'Ujia': {'fp01': 'bridge_damage=25'},
             'Ujib': {'fp01': 'poison_damage=300', 'fp02': 'bridge_damage=50'}}


@dataclass(frozen=True)
class Identity:
    """One lane-13 source identity and its variant/behavior facts."""

    source_id: int
    internal: str
    english: str
    base: str
    branch: str                       # adult | dwarf | sheargrub
    fsm_states: tuple
    anims: tuple
    parms: dict
    special: tuple = ()
    status: str = 'missing'           # implemented | staged | missing
    native_module: str = ''
    native_marker: str = ''
    evidence: str = ''
    blockers: tuple = ()


IDENTITIES = (
    Identity(2, 'Chappy', 'Red Bulborb', CHAPPY_BASE_OBJECT, 'adult',
             CHAPPY_BASE_STATES, CHAPPY_BASE_ANIMS, CHAPPY_BASE_PARMS,
             special=('adult_sleep_wake', 'adult_set_underground'),
             status='missing', native_module='pc_p2_enemy (Snow only, YellowKochappy)',
             evidence='none: adult identities ride the P1 Chappy host only',
             blockers=('no adult-specific native module; P1-proxy only',)),
    Identity(33, 'FireChappy', 'Fiery Bulblax', CHAPPY_BASE_OBJECT, 'adult',
             CHAPPY_BASE_STATES, CHAPPY_BASE_ANIMS, CHAPPY_BASE_PARMS,
             special=('fire_body_state', 'water_extinguish', 'fire_touch_receiver',
                      'btk_brk_material_loop', 'dead_smoke_vs_steam'),
             status='missing', native_marker='FIRECHAPPY',
             evidence='none: no module/harness/doc (source audit only)',
             blockers=('no converted FireChappy assets staged (enemy/data/FireChappy)',
                       'InteractFire elemental receiver contract (lane 10)',
                       'mWaterBox water state not exposed to the adapter')),
    Identity(35, 'KumaChappy', 'Spotty Bulbear', KUMA_BASE_OBJECT, 'adult',
             KUMA_STATES, KUMA_ANIMS, KUMA_PARMS,
             special=('revive_carcass', 'gauge_rebirth', 'waypoint_patrol',
                      'chappy_relation_owner'),
             status='missing', native_marker='KUMACHAPPY',
             evidence='none: no module/harness/doc',
             blockers=('no converted KumaChappy assets staged',
                       'revival/carcass lifecycle contract (lane 06/07)',
                       'WayPoint patrol route asset not staged')),
    Identity(42, 'BlueChappy', 'Orange Bulborb', CHAPPY_BASE_OBJECT, 'adult',
             CHAPPY_BASE_STATES, CHAPPY_BASE_ANIMS, CHAPPY_BASE_PARMS,
             special=('adult_sleep_wake',),
             status='missing', native_marker='BLUECHAPPY',
             evidence='none: adult variant rides the P1 Chappy host only',
             blockers=('no adult-specific native module; P1-proxy only',)),
    Identity(43, 'YellowChappy', 'Hairy Bulborb', CHAPPY_BASE_OBJECT, 'adult',
             CHAPPY_BASE_STATES, CHAPPY_BASE_ANIMS, CHAPPY_BASE_PARMS,
             special=('adult_sleep_wake',),
             status='missing', native_marker='YELLOWCHAPPY',
             evidence='none: adult variant rides the P1 Chappy host only',
             blockers=('no adult-specific native module; P1-proxy only',)),
    Identity(1, 'Kochappy', 'Dwarf Red Bulborb', KOCHAPPY_BASE_OBJECT, 'dwarf',
             KOCHAPPY_BASE_STATES, KOCHAPPY_BASE_ANIMS, KOCHAPPY_BASE_PARMS,
             special=('press_flip', 'dwarf_mimicry_red', 'purple_earthquake_stun'),
             status='implemented', native_module='pc_p2_kochappy + pc_p2_kochappy_stun',
             native_marker='KOCHAPPY',
             evidence='docs/pikmin2-kochappy-*.md (combat/delivery/reentry PASS, P1 proxy)',
             blockers=('P2 source FSM not ported (P1 proxy AI)',)),
    Identity(44, 'BlueKochappy', 'Dwarf Orange Bulborb', KOCHAPPY_BASE_OBJECT,
             'dwarf', KOCHAPPY_BASE_STATES, KOCHAPPY_BASE_ANIMS,
             KOCHAPPY_BASE_PARMS, special=('press_flip', 'dwarf_mimicry_orange'),
             status='native_candidate',
             native_module='pc_p2_dwarf_orange (+ parameterized pc_p2_kochappy_stun)',
             native_marker='DWARF_ORANGE',
             evidence='docs/PIKMIN2_DWARF_ORANGE_NATIVE.md (private native candidate, natural '
                      'P1-proxy fight/corpse/carry PASS)',
             blockers=('P2 source FSM not ported (shared KochappyBase FSM runs host P1 AI)',
                       'native candidate not on the maintained line (lane 01 owns integration)',
                       'manager-swap re-entry blocked: actor dies to the overlay squad before the swap',
                       'P2 reward semantics, persistence restart and mixed scene untested')),
    Identity(45, 'YellowKochappy', 'Snow Bulborb', KOCHAPPY_BASE_OBJECT, 'dwarf',
             KOCHAPPY_BASE_STATES, KOCHAPPY_BASE_ANIMS, KOCHAPPY_BASE_PARMS,
             special=('press_flip', 'source_health_policy', 'source_chase_turn_attack_entry'),
             status='implemented', native_module='pc_p2_enemy (Snow)',
             native_marker='SNOW',
             evidence='docs/pikmin2-snow-*.md, docs/pikmin2-snow-lifecycle.md (reference lane #120)',
             blockers=('full P2 source FSM not ported (opt-in source policies only; host P1 AI)',
                       'scene-revisit teardown untested (#397)')),
    Identity(76, 'KumaKochappy', 'Dwarf Bulbear', KUMA_BASE_OBJECT, 'dwarf',
             KUMAKOCHAPPY_STATES, KUMAKOCHAPPY_ANIMS, KUMAKOCHAPPY_PARMS,
             special=('parent_following_walkpath', 'press_flip',
                      'hipdrop_callback', 'no_parent_home_return'),
             status='staged', native_marker='KUMAKOCHAPPY',
             evidence='docs/PIKMIN2_DWARF_VARIANTS.md batch 2 install + arena staging (standalone only)',
             blockers=('native registration not implemented (integration lead / #186)',
                       'parent Spotty Bulbear (KumaChappy #35) not imported',
                       'ChappyRelation/WalkPath not staged')),
    Identity(12, 'Ujia', 'Female Sheargrub', UJI_BASE_OBJECT, 'sheargrub',
             UJIA_STATES, UJIA_ANIMS, UJI_PARMS['Ujia'],
             special=('underground_cycle', 'bridge_eating', 'no_mouth_slots',
                      'no_pikmin_damage'),
             status='implemented', native_module='pc_p2_sheargrub',
             native_marker='SHEARGRUB',
             evidence='docs/PIKMIN2_UJI_*.md',
             blockers=('fan-out groups Sheargrubs under lane 13 while the repo tracks Uji under '
                       'Ground #165/lane 14; ownership reconciliation needed',
                       'ItemBridge work object absent: female bridge-break path unsupported')),
    Identity(13, 'Ujib', 'Male Sheargrub', UJI_BASE_OBJECT, 'sheargrub',
             UJIB_STATES, UJIB_ANIMS, UJI_PARMS['Ujib'],
             special=('underground_cycle', 'bridge_eating', 'bite_and_swallow',
                      'white_poison'),
             status='implemented', native_module='pc_p2_sheargrub',
             native_marker='SHEARGRUB',
             evidence='docs/PIKMIN2_UJI_OBSERVER_ACCEPTANCE.md, PIKMIN2_UJI_GROUNDED_FIXTURE.md',
             blockers=('same lane 13 / lane 14 Sheargrub ownership reconciliation',
                       'ItemBridge work object absent (bridge-break visual)')),
)

BY_ID = {ident.source_id: ident for ident in IDENTITIES}
BY_INTERNAL = {ident.internal: ident for ident in IDENTITIES}

# Per-identity arena gates, in fan-out order.
GATES = ('identity_spawn', 'movement_animation', 'attacks_receivers',
         'death_corpse', 'transport_reward', 'cleanup_reentry')

# Documented gate status per identity. Source-backed N/A is used where the
# source has no such behavior (for example no Pikmin-damaging attack).
GATE_STATUS = {
    'Chappy': dict.fromkeys(GATES, 'untested'),
    'FireChappy': {'identity_spawn': 'blocked', 'movement_animation': 'blocked',
                   'attacks_receivers': 'blocked: InteractFire contract (lane 10)',
                   'death_corpse': 'blocked: no assets', 'transport_reward': 'untested',
                   'cleanup_reentry': 'untested'},
    'KumaChappy': {'identity_spawn': 'blocked', 'movement_animation': 'blocked',
                   'attacks_receivers': 'untested', 'death_corpse': 'untested',
                   'transport_reward': 'untested',
                   'cleanup_reentry': 'blocked: revival lifecycle (lane 06/07)'},
    'BlueChappy': dict.fromkeys(GATES, 'untested'),
    'YellowChappy': dict.fromkeys(GATES, 'untested'),
    'Kochappy': {'identity_spawn': 'pass', 'movement_animation': 'pass_p1_proxy',
                 'attacks_receivers': 'pass_purple_stun', 'death_corpse': 'pass_p1_proxy',
                 'transport_reward': 'pass_p1_proxy', 'cleanup_reentry': 'partial_manager_only'},
    'BlueKochappy': {'identity_spawn': 'pass_native_candidate',
                     'movement_animation': 'pass_p1_proxy',
                     'attacks_receivers': 'pass_p1_proxy_natural_combat',
                     'death_corpse': 'pass_p1_proxy_corpse',
                     'transport_reward': 'pass_p1_proxy_corpse_carry',
                     'cleanup_reentry': 'blocked_actor_dies_before_swap'},
    'YellowKochappy': {'identity_spawn': 'pass', 'movement_animation': 'pass_p1_proxy',
                       'attacks_receivers': 'pass_entry_geometry', 'death_corpse': 'pass',
                       'transport_reward': 'pass', 'cleanup_reentry': 'untested_scene_revisit'},
    'KumaKochappy': {'identity_spawn': 'staged', 'movement_animation': 'untested',
                     'attacks_receivers': 'untested', 'death_corpse': 'untested',
                     'transport_reward': 'untested', 'cleanup_reentry': 'untested'},
    'Ujia': {'identity_spawn': 'pass', 'movement_animation': 'pass_sampled',
             'attacks_receivers': 'source_backed_na_no_damage', 'death_corpse': 'pass',
             'transport_reward': 'pass', 'cleanup_reentry': 'partial_forget_fallback'},
    'Ujib': {'identity_spawn': 'pass', 'movement_animation': 'pass_sampled',
             'attacks_receivers': 'pass_bite_eat', 'death_corpse': 'pass',
             'transport_reward': 'pass', 'cleanup_reentry': 'partial_forget_fallback'},
}

# Special-rule records required by the fan-out's "then special Bulbear/Fiery
# Bulblax rules" and "report revival ... separately".
SPECIAL_RULES = {
    'fire_body_state': {
        'identity': 'FireChappy',
        'source': 'FireChappy.cpp:startFireState/updateFireState',
        'rule': 'mOnFire defaults true; mAnimationFireTimer resets to 30 on (re)ignite',
    },
    'water_extinguish': {
        'identity': 'FireChappy',
        'source': 'FireChappy.cpp:updateFireState',
        'rule': 'while mOnFire and mWaterBox is set, extinguish (finishBodyEffect + dead '
                'steam + F_END sound); re-ignite only when alive and not in water',
    },
    'fire_touch_receiver': {
        'identity': 'FireChappy',
        'source': 'FireChappy.cpp:collisionCallback',
        'rule': 'on fire contact with a living Pikmin/Navi, stimulate InteractFire with '
                'mGeneral.mAttackDamage; owns damage/immunity semantics in lane 10',
    },
    'dead_smoke_vs_steam': {
        'identity': 'FireChappy',
        'source': 'FireChappy.cpp:onKill/finishFireState(bool)',
        'rule': 'onKill -> finishFireState(false) -> dead smoke; water extinguish -> dead steam',
    },
    'revive_carcass': {
        'identity': 'KumaChappy',
        'source': 'KumaChappy.h:doUpdateCarcass/doBecomeCarcass + StateRebirth',
        'rule': 'death leaves a reviving carcass (unlike ChappyBase); revival is a state, '
                'not a respawn of the same manager slot',
    },
    'gauge_rebirth': {
        'identity': 'KumaChappy',
        'source': 'KumaChappy.h Parms fp11/fp12 + mReviveTimer',
        'rule': 'health-gauge timer fp11=30 before gauge, respawn rate fp12=10 before '
                'rebirth; must be reported separately from ordinary death',
    },
    'waypoint_patrol': {
        'identity': 'KumaChappy',
        'source': 'KumaChappy.h:setNearestWayPoint/setLinkWayPoint/mCurrWP/mPrevWP',
        'rule': 'patrols authored WayPoints instead of a home point; requires a staged route',
    },
    'chappy_relation_owner': {
        'identity': 'KumaChappy',
        'source': 'Game/ChappyRelation.h + KumaChappy::createChappyRelation',
        'rule': 'owns a ChappyRelation list consumed by Dwarf Bulbears; relation must '
                'survive captain death/capture and be released on Bulbear death',
    },
    'parent_following_walkpath': {
        'identity': 'KumaKochappy',
        'source': 'KumaKochappyState.cpp StateWalkPath/setTargetParentPosition',
        'rule': 'follows the nearest live Spotty Bulbear via WalkPath; with no parent it '
                'returns home and Waits (home radius check)',
    },
    'no_parent_home_return': {
        'identity': 'KumaKochappy',
        'source': 'KumaKochappyState.cpp',
        'rule': 'parent loss must not strand the dwarf: releaseParent -> home return',
    },
    'no_pikmin_damage': {
        'identity': 'Ujia',
        'source': 'Ujia.h (no mMouthSlots, no swallow) + Ujib.h',
        'rule': 'female Sheargrub has no Pikmin-damaging attack; only bridge damage '
                '(fp01=25). Male Ujib bites and swallows with white poison fp01=300',
    },
    'underground_cycle': {
        'identity': 'Ujia/Ujib',
        'source': 'Ujia.h/Ujib.h mIsUnderground + Appear/Dive states',
        'rule': 'surface/underground appear+dive cycle; isUnderground exposed for receiver '
                'gating',
    },
}


def identity(source_id):
    """Return the lane-13 identity for a source EnemyID, or raise KeyError."""
    return BY_ID[source_id]


def variant_matrix():
    """Return the audit rows: every lane-13 identity with its variant fields."""
    rows = []
    for ident in IDENTITIES:
        rows.append(dict(
            source_id=ident.source_id, internal=ident.internal, english=ident.english,
            base=ident.base, branch=ident.branch, status=ident.status,
            native_module=ident.native_module, native_marker=ident.native_marker,
            fsm_states=list(ident.fsm_states), anims=list(ident.anims),
            parms=dict(ident.parms), special=list(ident.special),
            gates=dict(GATE_STATUS[ident.internal]), evidence=ident.evidence,
            blockers=list(ident.blockers)))
    return rows


def variant_differences():
    """Return the structural differences that distinguish the lane-13 variants."""
    return [
        dict(key='adult_vs_dwarf', adults=[i.internal for i in IDENTITIES if i.branch == 'adult'],
             dwarfs=[i.internal for i in IDENTITIES if i.branch == 'dwarf'],
             difference='adult ChappyBase has Sleep+turntohome/gohome and no Press; dwarf '
                        'KochappyBase has Wait/Demo/Press and no Sleep'),
        dict(key='elemental', identities=['FireChappy'],
             difference='only FireChappy owns a fire body state, water extinguish and an '
                        'InteractFire touch receiver'),
        dict(key='revival', identities=['KumaChappy'],
             difference='only KumaChappy carries a reviving carcass + gauge rebirth timer'),
        dict(key='relation', identities=['KumaChappy', 'KumaKochappy'],
             difference='Bulbear owns ChappyRelation; Dwarf Bulbear is the relation consumer'),
        dict(key='sheargrub_sex', identities=['Ujia', 'Ujib'],
             difference='Ujia has no mouth slots and no Pikmin-damaging attack; Ujib has '
                        'mMouthSlots, bite/swallow and white poison'),
        dict(key='mimicry', identities=['Kochappy', 'BlueKochappy', 'KumaKochappy'],
             difference='dwarf variants reuse an adult model/anim bank; identity differs '
                        'by change-texture and, for KumaKochappy, parent relation'),
    ]


def special_rules(internal):
    """Return the special-rule records owned by an identity."""
    ident = BY_INTERNAL[internal]
    return {name: dict(SPECIAL_RULES[name]) for name in ident.special
            if name in SPECIAL_RULES}


def acceptance_contract(internal):
    """Return the native acceptance-contract strings for one identity.

    The marker set follows the established species behavior harnesses
    (``P2_<MARKER>_*`` / ``P2_ENEMY_READY``). A missing identity has no native
    marker yet; the caller still gets the intended contract for the future
    adapter and for documentation/unit tests.
    """
    ident = BY_INTERNAL[internal]
    marker = ident.native_marker or ident.internal.upper()
    prefix = f'P2_{marker}_'
    return dict(
        identity=f'{prefix}BIND generator=<gen> source_id={ident.source_id} visual_only=0',
        ready=(f'P2_ENEMY_READY species={ident.internal} .*generator=<gen> '
               f'.*source_FSM=implemented'),
        window='Experimental preview window set to 960x540 windowed and centered',
        required_states=list(ident.fsm_states),
        required_events=[rule for rule in ident.special
                         if rule in ('fire_body_state', 'fire_touch_receiver',
                                     'revive_carcass', 'parent_following_walkpath',
                                     'no_pikmin_damage')],
        gates={gate: GATE_STATUS[ident.internal][gate] for gate in GATES},
    )


def validate_acceptance(text, internal=None):
    """Validate a captured native log against the identity contract.

    ``internal`` may be omitted to infer the identity from the ``P2_*_BIND``
    source ID. Returns a checks dict and whether every mandatory check passed.
    This is a contract validator only; a missing identity is expected to fail.
    The synthetic-log unit tests pin the parser so future native adapters can
    be graded without changing this module.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    if internal is None:
        match = re.search(r'P2_\w+_BIND generator=\d+ source_id=(\d+) visual_only=0', text)
        if not match:
            raise ValueError('Cannot infer identity: no P2_*_BIND source_id in log')
        source_id = int(match.group(1))
        if source_id not in BY_ID:
            raise ValueError(f'source_id {source_id} is not a lane-13 identity')
        internal = BY_ID[source_id].internal
    ident = BY_INTERNAL[internal]
    marker = ident.native_marker or ident.internal.upper()
    states = set(re.findall(rf'P2_{marker}_STATE generator=\d+ state=(\w+)', text))
    checks = dict(
        identity=bool(re.search(rf'P2_{marker}_BIND generator=\d+ source_id={ident.source_id} '
                                r'visual_only=0', text)),
        ready=bool(re.search(rf'P2_ENEMY_READY species={ident.internal} .*source_FSM=implemented',
                             text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered',
                              text)),
        states=sorted(states),
        has_source_states=bool(states.intersection(ident.fsm_states)),
        death='dead' in states or bool(re.search(rf'P2_{marker}_CORPSE ', text)),
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for key, v in checks.items()
                           if key != 'states' and not isinstance(v, str)),
                checks=checks, identity=ident.internal, source_id=ident.source_id,
                gates=acceptance_contract(internal)['gates'])
