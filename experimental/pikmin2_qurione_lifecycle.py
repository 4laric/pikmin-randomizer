"""Lane 15 disjoint slice: Honeywisp (Qurione, EnemyID 16) source lifecycle contract.

Fan-out scope: ``docs/PIKMIN2_IMPLEMENTATION_FANOUT.md`` lane 15
("#166/#194-#196 as applicable"). Mar and Hanachirashi are owned by the active
species lane #407, so this lane takes the disjoint Honeywisp path: it defines
the real source lifecycle the current P1 nectar proxy does not implement and
grades a future native adapter.

Source of truth (read-only decomp checkout ``native/pikmin2-research``):

* ``include/Game/Entities/Qurione.h``        FSM states, anims, parms, Egg field
* ``src/plugProjectNishimuraU/QurioneState.cpp`` Stay/Appear/Disappear/Move/Drop/Dead
* ``src/plugProjectNishimuraU/Qurione.cpp``  birth/attachItem/dropItem, isAppear/isFlyKill

Reward note: the P2 source Honeywisp carries an ``Egg`` (``EnemyID_Egg`` 37)
attached to the ``water`` joint and releases it on a Pikmin hit. The integrated
``pc_p2_qurione`` module now reuses the lane-20 ``P2Egg`` policy
(``pc_p2_egg_hazard.*``): it attaches a real Egg, releases it on Drop, breaks it
on floor impact, and births the source drop table (single/double nectar, pellets,
mitites->nectar fallback) as real P1 items. Spicy/Bitter sprays stay unsupported.
"""
from __future__ import annotations

import re

SCHEMA = 'p2-qurione-lifecycle-v1'
SOURCE_ID = 16
INTERNAL = 'Qurione'
ENGLISH = 'Honeywisp'

# Source state machine (Qurione.h StateID).
STATE_ORDER = ('stay', 'appear', 'disappear', 'move', 'drop', 'dead')
SOURCE_FSM = {
    'stay': dict(
        entry='hidden at mSpawnPositions[mSpawnIndex]; atari off; ModelHidden; Appear anim stopped',
        exit='event and timer gated: mUtilityTimer > 1.0 and isAppear() -> appear',
        notes='isAppear() is true in Piklopedia mode or when a nearest Pikmin/Navi is inside '
              'viewAngle/sightRadius'),
    'appear': dict(
        entry='atari off; Appear anim; createAppearEffect; startGlowEffect',
        exit='Appear anim KEYEVENT_END -> move',
        notes='mQurioneScale grows by 0.05/frame to 1.0; glow scale follows'),
    'move': dict(
        entry='Wait anim; target velocity zero',
        exit='distance from spawn position > mFlyDist -> disappear',
        notes='moveFaceDir: forward speed, pitch bob fp02/fp03 about map minY + fp01; '
              'flyCollisionCallBack(Piki) in this state -> drop'),
    'disappear': dict(
        entry='atari off; Hide anim; createDisppearEffect',
        exit='Hide anim KEYEVENT_END -> stay',
        notes='scale shrinks; on cleanup mSpawnIndex flips and mFaceDir += PI, so the next '
              'approach is the opposite spawn point'),
    'drop': dict(
        entry='EB_Cullable disabled; createHitEffect; Damage anim',
        exit='Damage anim KEYEVENT_2 -> dropItem; KEYEVENT_END -> dead',
        notes='dropItem ends the Egg capture and clears mEgg; no death drop'),
    'dead': dict(
        entry='setAlive(false); EB_Cullable disabled; velocity (0, fp04, 0); Run anim',
        exit='isFlyKill() -> finishGlowEffect and kill',
        notes='isFlyKill() when the actor is not LOD-visible or mUtilityTimer > fp05'),
}

ANIM_IDS = {'wait': 0, 'damage': 1, 'run': 2, 'appear': 3, 'hide': 4}
ANIM_ALIASES = {'appear': 'appear1', 'hide': 'hide1'}
PARMS = {'fp01': 'flight_height=60', 'fp02': 'pitch_rate=2.5', 'fp03': 'pitch_amp=20',
         'fp04': 'death_rate=100', 'fp05': 'death_time=1'}

# Lifecycle constants from Qurione.cpp.
BIRTH = dict(fly_distance=200.0, slide_distance=30.0, spawn_index='QSPAWN_Start',
             spawn_count=2, scale_start=0.0, scale_step=0.05,
             appear_timer=1.0, invulnerable=True, untargetable=True,
             leave_carcass=False, lifegauge_visible=False, drop_group='EDG_None')
REWARD = dict(
    kind='Egg', source_id=37, attach_joint='water',
    attach='birth EnemyID_Egg under the water joint and startCapture(worldMat)',
    drop='Damage KEYEVENT_2 -> endCapture, mEgg = null; no second drop',
    real='native host reuses lane-20 P2Egg policy (pc_p2_egg_hazard.*): release -> '
         'endCapture -> bounded gravity fall -> floor bounce (health 0) -> source '
         'drop table birthed as real P1 items (single/double nectar via OBJTYPE_Water, '
         'pellets via pelletMgr, mitites->nectar fallback).',
    markers=('P2_QURIONE_EGG action=attach', 'P2_QURIONE_EGG action=drop',
             'P2_QURIONE_EGG_REAL born=1 drop_group=0', 'P2_QURIONE_EGG_REAL released=1',
             'P2_QURIONE_EGG_BREAK', 'P2_QURIONE_EGG_ITEM'),
    note='Spicy/Bitter sprays stay unsupported until the first-spray demo flag exists.')

GATES = ('identity_spawn', 'movement_animation', 'attacks_receivers',
         'death_corpse', 'transport_reward', 'cleanup_reentry')
GATE_STATUS = {
    'identity_spawn': 'pass (integrated proxy; source_id=16, birth XYZ matched)',
    'movement_animation': 'blocked: source Stay/Appear/Move/Disappear cycle not implemented',
    'attacks_receivers': 'pass_injected (P1 InteractAttack -> nectar); natural Piki collision untested',
    'death_corpse': 'run_gate: dead is a fly-away (no carcass); isFlyKill kill untested',
    'transport_reward': 'pass: native host births a real Egg (lane-20 P2Egg policy) on attach, '
                        'releases it on Drop, breaks it on floor impact and births the source '
                        'drop table; spicy/bitter sprays unsupported',
    'cleanup_reentry': 'untested: spawn-index flip + manager recreate',
}


def lifecycle_sequence():
    """Return the expected natural state order for one surface pass."""
    return ['stay', 'appear', 'move', 'disappear', 'stay']


def drop_sequence():
    """Return the hit-triggered reward path."""
    return ['move', 'drop', 'dead']


def acceptance_contract():
    """Return the native acceptance-contract strings for Qurione."""
    return dict(
        identity=f'P2_QURIONE_BIND generator=<gen> source_id={SOURCE_ID} visual_only=0',
        ready='P2_ENEMY_READY species=Qurione .*generator=<gen> .*behavior=native '
              '.*source_FSM=implemented .*reward=P2_Egg',
        window='Experimental preview window set to 960x540 windowed and centered',
        required_states=list(STATE_ORDER),
        lifecycle=list(lifecycle_sequence()),
        drop=list(drop_sequence()),
        reward=dict(REWARD),
        gates=dict(GATE_STATUS),
    )


def validate_lifecycle(text):
    """Validate a captured native log against the Qurione source lifecycle.

    The synthetic-log unit tests pin the parser so a future native adapter can
    be graded without changing this module.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_QURIONE_STATE generator=\d+ state=(\w+)', text)
    seen = set(states)
    egg_events = set(re.findall(r'P2_QURIONE_EGG generator=\d+ action=(\w+)', text))
    drops = re.findall(r'P2_QURIONE_EGG generator=\d+ action=drop\b', text)
    real_born = bool(re.search(r'P2_QURIONE_EGG_REAL generator=\d+ born=1 drop_group=0', text))
    real_released = bool(re.search(r'P2_QURIONE_EGG_REAL generator=\d+ released=1', text))
    egg_break = bool(re.search(r'P2_QURIONE_EGG_BREAK generator=\d+ type=\d+ items=\d+ real=1', text))
    item_lines = [line for line in text.splitlines() if line.startswith('P2_QURIONE_EGG_ITEM ')]
    item_real = any(' real=1 ' in line and ' item=' in line for line in item_lines)
    item_nectar = any(' real=1' in line and ' item=nectar' in line for line in item_lines)
    checks = dict(
        identity=bool(re.search(rf'P2_QURIONE_BIND generator=\d+ source_id={SOURCE_ID} '
                                r'visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Qurione .*source_FSM=implemented '
                             r'.*reward=P2_Egg', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered',
                              text)),
        states=states,
        source_cycle=seen.issuperset({'stay', 'appear', 'move', 'disappear'}),
        drop_path=seen.issuperset({'drop', 'dead'}),
        egg_attach='attach' in egg_events,
        egg_drop='drop' in egg_events,
        exactly_one_drop=len(drops) == 1,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
        reward_real=dict(born=real_born, released=real_released, break_=egg_break,
                         item=item_real, nectar=item_nectar),
    )
    scalar = {k: v for k, v in checks.items() if isinstance(v, bool)}
    return dict(passed=all(scalar.values()), checks=checks,
                unmeasured=['glow/appear/disappear effect fidelity',
                            'Piklopedia zukan-mode utility timer',
                            'spawn-index flip after a full disappear',
                            'cleanup/re-entry',
                            'spicy/bitter spray births (first-spray demo flag)'],
                limitations=['Bounded host gravity approximates the Egg fall; there is no '
                             'physical P1 Egg creature, so the released Egg is a lane-20 policy '
                             'object whose break births real items. Mitite groups downgrade to '
                             'nectar (no P1 Mitite manager).'])


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_lifecycle(args.log.read_text(errors='replace')), indent=2))
