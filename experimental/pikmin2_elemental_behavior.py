"""Pikmin 2 lane-22 elemental/dweevil source behavior model (#170, child #349).

Pure-Python, side-effect-free, machine-checkable encoding of the source
behavior that docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md attributes to ten IDs:
fixed hazards Hiba (20), GasHiba (21), ElecHiba (22); blowhogs Tank (24),
Wtank (25); and dweevils FireOtakara (59), WaterOtakara (60), GasOtakara (61),
ElecOtakara (62), BombOtakara (93). This is a policy reference for the future
native lane: nothing here executes game behavior, touches the ISO, or edits the
native build. Every fact carries a `source` file:line citation relative to the
`native/pikmin2-research` decompilation at revision
632af93787b9c95b63f0c13be32b161375ce3a96 (the audit's read-only source) unless
it names the audit document or the disc parameter archive. Header (build-time)
defaults and retail disc values are kept as distinct fields and never flattened.

Receiver contract: docs/PIKMIN2_RECEIVER_PATHS.md (#408). An emitted stimulus
does not itself carry immunity -- the receiving Pikmin colour decides (audit
lines 41-43). BombOtakara consumes the shared Bomb blast/projectile contract;
this module deliberately does not re-implement projectile or explosion
primitives (those belong to the projectiles lane, #169).

Audit: docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md (issue #170, child #349).
Supplementary: docs/PIKMIN2_DWEEVIL_ASSETS.md and docs/PIKMIN2_RECEIVER_PATHS.md.
"""
import math

_AUDIT = 'docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md'
_ASSETS = 'docs/PIKMIN2_DWEEVIL_ASSETS.md'
_INTERACT_PIKI = 'src/plugProjectKandoU/interactPiki.cpp'

# ---------------------------------------------------------------------------
# Roster and emitted stimuli (audit lines 7,11-20)
# ---------------------------------------------------------------------------

# Numeric IDs declared in include/Game/enemyInfo.h:79-84,118-121,152
# (audit line 7).
ENEMY_IDS = {
    'Hiba': 20, 'GasHiba': 21, 'ElecHiba': 22,
    'Tank': 24, 'Wtank': 25,
    'FireOtakara': 59, 'WaterOtakara': 60, 'GasOtakara': 61,
    'ElecOtakara': 62, 'BombOtakara': 93,
}

# Concrete stimulus each actor emits to a creature it contacts.
#   Hiba        interactFireAttack   Hiba.cpp:148-178      (audit line 11)
#   GasHiba     interactGasAttack    GasHiba.cpp:157-187    (audit line 12)
#   ElecHiba    interactDenkiAttack  ElecHiba.cpp:264-329   (audit line 13)
#   Tank/Ftank  interactCreature     Ftank.cpp:121-125      (audit line 14)
#   Wtank       interactCreature     Wtank.cpp:119-123      (audit line 15)
#   dweevils    interactCreature     Fire/Water/Gas/ElecOtakara (audit 16-19)
# BombOtakara emits no creature stimulus: its carried Bomb owns the blast
# (audit line 20), so it is recorded as None and never routed as an element.
EMITTED_STIMULUS = {
    'Hiba': 'InteractFire',
    'GasHiba': 'InteractGas',
    'ElecHiba': 'InteractDenki',
    'Tank': 'InteractFire',
    'Wtank': 'InteractBubble',
    'FireOtakara': 'InteractFire',
    'WaterOtakara': 'InteractBubble',
    'GasOtakara': 'InteractGas',
    'ElecOtakara': 'InteractDenki',
    'BombOtakara': None,
}

# Family class recorded by this lane. The three hazard IDs are numbered in
# EnemyID and are registered spawnables but carry EFlag_HasNoInfo with empty
# resource slots and BDT_Empty, so they are fixed, scenery-adjacent hazards
# rather than Piklopedia enemies (audit lines 11-13,49; assets lines 46-58).
CLASSIFICATIONS = {
    'Hiba': 'fixed_hazard',
    'GasHiba': 'fixed_hazard',
    'ElecHiba': 'fixed_hazard',
    'Tank': 'blowhog',
    'Wtank': 'blowhog',
    'FireOtakara': 'dweevil',
    'WaterOtakara': 'dweevil',
    'GasOtakara': 'dweevil',
    'ElecOtakara': 'dweevil',
    'BombOtakara': 'dweevil',
}

FIXED_HAZARD_IDS = ('Hiba', 'GasHiba', 'ElecHiba')
BLOWHOG_IDS = ('Tank', 'Wtank')
DWEEVIL_IDS = ('FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara',
               'BombOtakara')

# ---------------------------------------------------------------------------
# Receiver immunity table (audit line 43; receiver contract #408 section 4)
# ---------------------------------------------------------------------------
# The emitted stimulus does not define immunity. In the decompilation
# `interactPiki.cpp` the receiver decides: InteractDenki::actPiki (334)
# excludes Yellow/Bulbmin and requests DenkiDying; InteractFire::actPiki (445)
# excludes Red/Bulbmin; InteractBubble::actPiki (503) excludes Blue/Bulbmin;
# InteractGas::actPiki (531) excludes White/Bulbmin and checks `gasInvicible`.
# Bulbmin is excluded by every receiver. Captain equipment and enemy-side
# immunities need their own receiver audit and must not copy these rules.
ELEMENT_IMMUNITY = {
    'InteractFire': {
        'element': 'fire',
        'immune_colours': ('Red', 'Bulbmin'),
        'panic': 'Fire',
        'extra_gate': None,
        'source': _INTERACT_PIKI + ':445',
    },
    'InteractBubble': {
        'element': 'water',
        'immune_colours': ('Blue', 'Bulbmin'),
        'panic': 'Bubble',
        'extra_gate': None,
        'source': _INTERACT_PIKI + ':503',
    },
    'InteractGas': {
        'element': 'gas',
        'immune_colours': ('White', 'Bulbmin'),
        'panic': 'Gas',
        'extra_gate': 'gasInvicible',
        'source': _INTERACT_PIKI + ':531',
    },
    'InteractDenki': {
        'element': 'denki',
        'immune_colours': ('Yellow', 'Bulbmin'),
        'panic': 'DenkiDying',
        'extra_gate': None,
        'source': _INTERACT_PIKI + ':334',
    },
}
PIKMIN_COLOURS = ('Red', 'Yellow', 'Blue', 'Purple', 'White', 'Bulbmin')

# ---------------------------------------------------------------------------
# Fixed hazards Hiba (20), GasHiba (21), ElecHiba (22)
# ---------------------------------------------------------------------------

# FSM registrations: Hiba and GasHiba register Dead/Wait/Attack
# (HibaState.cpp:14-20; GasHibaState.cpp:13-19); ElecHiba adds Sign
# (ElecHibaState.cpp:13-20). State IDs Hiba.h:136-141, GasHiba.h:151-156,
# ElecHiba.h:197-203 (audit line 24; assets lines 75-80).
HAZARD_STATES = {
    'Hiba': {'dead': 0, 'wait': 1, 'attack': 2},
    'GasHiba': {'dead': 0, 'wait': 1, 'attack': 2},
    'ElecHiba': {'dead': 0, 'wait': 1, 'sign': 2, 'attack': 3},
}

# Header (build-time) proper-parameter defaults, Hiba.h/GasHiba.h/ElecHiba.h
# (assets lines 153-159).
HAZARD_TIMING_HEADER = {
    'Hiba': {'wait': 2.5, 'active': 2.5, 'stop': 10.0},
    'GasHiba': {'wait': 2.5, 'active': 2.5, 'attack_start': 1.0, 'stop': 10.0},
    'ElecHiba': {'wait': 2.5, 'warning': 2.5, 'active': 2.5, 'stop': 10.0},
}

# Retail disc hazard proper blocks, US GPVE01 rev 0 <hazard>/enemyparm.txt
# (assets lines 161-166). The geyser timing differences are real: Hiba wait
# 3.0 (header 2.5); GasHiba wait 0.0 with attack-start 0.6 (header 2.5/1.0);
# ElecHiba wait 1.5 and warning 1.5 (header 2.5/2.5).
HAZARD_TIMING_DISC = {
    'Hiba': {'wait': 3.0, 'active': 2.5, 'stop': 30.0},
    'GasHiba': {'wait': 0.0, 'active': 3.0, 'attack_start': 0.6, 'stop': 30.0},
    'ElecHiba': {'wait': 1.5, 'warning': 1.5, 'active': 2.5, 'stop': 30.0},
}

# The explicit fixed-hazard reclassification. `linked_actor` records the
# runtime ownership the audit calls out: GasHiba is bridge/gate linked and can
# be temporarily not living until the link changes (GasHiba.cpp:193-296),
# while ElecHiba is one parent/child wire pair (ElecHibaMgr.cpp:110-131).
FIXED_HAZARD_CLASSIFICATION = {
    'Hiba': {
        'classification': 'fixed_hazard',
        'element': 'fire',
        'stimulus': 'InteractFire',
        'linked_actor': None,
        'evidence': 'enemyInfo.cpp:41 EFlag_HasNoInfo; Hiba.cpp:148-178',
    },
    'GasHiba': {
        'classification': 'fixed_hazard',
        'element': 'gas',
        'stimulus': 'InteractGas',
        'linked_actor': 'bridge_or_gate',
        'evidence': 'enemyInfo.cpp:42 EFlag_HasNoInfo; GasHiba.cpp:193-296',
    },
    'ElecHiba': {
        'classification': 'fixed_hazard',
        'element': 'denki',
        'stimulus': 'InteractDenki',
        'linked_actor': 'parent_child_wire_pair',
        'evidence': 'enemyInfo.cpp:43 EFlag_HasNoInfo; ElecHibaMgr.cpp:110-131',
    },
}


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Expected finite number')
    return value


def _identity(identity):
    if identity not in ENEMY_IDS:
        raise ValueError('Unknown lane-22 identity: %r' % (identity,))
    return identity


def classification(identity):
    """Family class for one lane-22 ID: 'fixed_hazard', 'blowhog' or 'dweevil'."""
    return CLASSIFICATIONS[_identity(identity)]


def stimulus_for(identity):
    """Stimulus the identity emits, or None for BombOtakara's delegated Bomb."""
    return EMITTED_STIMULUS[_identity(identity)]


def is_fixed_hazard(identity):
    """True for Hiba/GasHiba/ElecHiba, the scenery-adjacent hazard IDs."""
    return _identity(identity) in FIXED_HAZARD_IDS


def panic_for(stimulus):
    """Panic subtype requested by an elemental stimulus (audit line 43)."""
    if stimulus not in ELEMENT_IMMUNITY:
        raise ValueError('Unknown stimulus: %r' % (stimulus,))
    return ELEMENT_IMMUNITY[stimulus]['panic']


def pikmin_immune(*, stimulus, colour, gas_invincible=False):
    """True when the stimulus cannot hurt this Pikmin colour.

    Receivers exclude one colour plus Bulbmin, and InteractGas additionally
    rejects a target already flagged `gasInvicible` (audit line 43).
    """
    if stimulus not in ELEMENT_IMMUNITY:
        raise ValueError('Unknown stimulus: %r' % (stimulus,))
    if colour not in PIKMIN_COLOURS:
        raise ValueError('Unknown Pikmin colour: %r' % (colour,))
    rule = ELEMENT_IMMUNITY[stimulus]
    if colour in rule['immune_colours']:
        return True
    if rule['extra_gate'] == 'gasInvicible' and gas_invincible:
        return True
    return False


def receiver_accepts(*, stimulus, colour, invincible=False,
                     gas_invincible=False):
    """Elemental routing decision for a Pikmin receiver.

    The generic invincibility gate rejects before any elemental check
    (PIKMIN2_RECEIVER_PATHS.md section 4); then the colour's immunity decides
    (audit line 43). Returns 'reject' or 'accept'.
    """
    if not isinstance(invincible, bool) or not isinstance(gas_invincible, bool):
        raise ValueError('Expected boolean gate flags')
    if invincible:
        return 'reject'
    if pikmin_immune(stimulus=stimulus, colour=colour,
                     gas_invincible=gas_invincible):
        return 'reject'
    return 'accept'


def hazard_activate(*, hazard, health, wait_elapsed, wait_time=None):
    """Wait -> Attack once the wait timer elapses; zero health is Dead.

    Both Hiba and GasHiba reset their timer/alive flags in onInit and start
    Wait (Hiba.cpp:31-50; GasHiba.cpp:33-53); Wait transitions on health or
    timer (audit line 24). `wait_time` defaults to the retail disc value.
    """
    _identity(hazard)
    if hazard not in FIXED_HAZARD_IDS:
        raise ValueError('Not a fixed hazard: %r' % (hazard,))
    if wait_time is None:
        wait_time = HAZARD_TIMING_DISC[hazard]['wait']
    _finite(health)
    _finite(wait_elapsed)
    _finite(wait_time)
    if health <= 0.0:
        return 'dead'
    return 'attack' if wait_elapsed >= wait_time else 'wait'


def hiba_activate(*, health, wait_elapsed, wait_time=None):
    """Hiba-specific Wait activation (see hazard_activate)."""
    return hazard_activate(hazard='Hiba', health=health,
                           wait_elapsed=wait_elapsed, wait_time=wait_time)


def gashiba_activate(*, health, wait_elapsed, wait_time=None):
    """GasHiba-specific Wait activation (see hazard_activate)."""
    return hazard_activate(hazard='GasHiba', health=health,
                           wait_elapsed=wait_elapsed, wait_time=wait_time)


def hiba_emit(*, state, health, active_elapsed, active_time=None):
    """True while Hiba Attack keeps stimulating InteractFire each update.

    Hiba Attack stimulates every update and requests animation finish on death
    or active-time expiry (HibaState.cpp:127-159; audit line 24).
    """
    if state not in HAZARD_STATES['Hiba']:
        raise ValueError('Unknown Hiba state: %r' % (state,))
    if active_time is None:
        active_time = HAZARD_TIMING_DISC['Hiba']['active']
    _finite(health)
    _finite(active_elapsed)
    _finite(active_time)
    if health <= 0.0 or state != 'attack':
        return False
    return active_elapsed < active_time


def gashiba_emit(*, state, attack_elapsed, active_elapsed,
                 attack_start=None, active_time=None, wait_time=None):
    """True while GasHiba Attack stimulates InteractGas.

    GasHiba Attack stimulates only after mAttackStartTime; its active-time
    finish condition additionally requires a positive mWaitTime
    (GasHibaState.cpp:129-169; audit line 24). The retail disc wait time is
    0.0, so time alone never satisfies the finish condition.
    """
    if state not in HAZARD_STATES['GasHiba']:
        raise ValueError('Unknown GasHiba state: %r' % (state,))
    disc = HAZARD_TIMING_DISC['GasHiba']
    if attack_start is None:
        attack_start = disc['attack_start']
    if active_time is None:
        active_time = disc['active']
    if wait_time is None:
        wait_time = disc['wait']
    _finite(attack_elapsed)
    _finite(active_elapsed)
    _finite(attack_start)
    _finite(active_time)
    _finite(wait_time)
    if state != 'attack':
        return False
    if attack_elapsed < attack_start:
        return False
    finished = active_elapsed >= active_time and wait_time > 0.0
    return not finished


def gashiba_linked_owner(*, bridge_linked, gate_linked):
    """Owner of a story-outdoor GasHiba's living/emission state.

    `setInitLivingThing` can temporarily mark the pipe not living until a
    nearby bridge or gate changes, and the association applies in story
    outdoor mode (GasHiba.cpp:193-296,204-272; audit lines 12,49).
    RECONSTRUCTED: the exact setInitLivingThing gate is not reproduced here.
    """
    if not isinstance(bridge_linked, bool) or not isinstance(gate_linked, bool):
        raise ValueError('Expected boolean link flags')
    if bridge_linked and gate_linked:
        return 'bridge+gate'
    if bridge_linked:
        return 'bridge'
    if gate_linked:
        return 'gate'
    return None


def elechiba_node_positions(*, center, separation):
    """The two wire nodes are born at center -/+ mSeperation/2.

    Birth creates a two-node team at +/- mSeperation/2
    (ElecHibaMgr.cpp:110-131); setElecHibaPosition computes the same separation
    (ElecHiba.cpp:249-258; audit lines 13,49). Returns
    (negative_node, positive_node).
    """
    _finite(center)
    _finite(separation)
    if separation < 0.0:
        raise ValueError('Expected non-negative separation')
    half = separation / 2.0
    return (center - half, center + half)


def elechiba_team_head_damage(*, is_parent, invulnerable):
    """Damage routing for the ElecHiba team.

    Only the parent executes FSM updates (ElecHiba.cpp:88-93); child
    initialization is recursive (ElecHiba.cpp:67-73). Normal damage routes to
    the team head through addDamageMyself/damageIncrement, where the
    invulnerability check lives (ElecHiba.cpp:139-157,752-776; audit line 26).
    Returns 'reject' when invulnerable, else 'route_to_head' from either node.
    """
    if not isinstance(is_parent, bool) or not isinstance(invulnerable, bool):
        raise ValueError('Expected boolean flags')
    if invulnerable:
        return 'reject'
    return 'route_to_head'


def elechiba_advance(*, state, health, elapsed, wait_time=None,
                     warning_time=None, active_time=None, counter_done=False):
    """Advance the ElecHiba chain Wait -> Sign -> Attack -> Wait.

    Wait enters Sign on timer (or the versus counter condition); Sign disables
    culling and charges for the warning time; Attack discharges until the
    active time expires or the counter completes
    (ElecHibaState.cpp:93-131,145-198,204-268; audit line 26). Returns
    (next_state, emits_this_step). Only the parent drives this chain.
    """
    if state not in HAZARD_STATES['ElecHiba']:
        raise ValueError('Unknown ElecHiba state: %r' % (state,))
    disc = HAZARD_TIMING_DISC['ElecHiba']
    if wait_time is None:
        wait_time = disc['wait']
    if warning_time is None:
        warning_time = disc['warning']
    if active_time is None:
        active_time = disc['active']
    if not isinstance(counter_done, bool):
        raise ValueError('Expected boolean counter flag')
    _finite(health)
    _finite(elapsed)
    _finite(wait_time)
    _finite(warning_time)
    _finite(active_time)
    if health <= 0.0:
        return ('dead', False)
    if state == 'wait':
        return ('sign', False) if elapsed >= wait_time else ('wait', False)
    if state == 'sign':
        return ('attack', True) if elapsed >= warning_time else ('sign', False)
    finished = elapsed >= active_time or counter_done
    return ('wait', False) if finished else ('attack', True)


def elechiba_versus_stimulus(*, attribute):
    """Stimulus for an ElecHiba discharge attribute mode.

    interactDenkiAttack applies InteractDenki normally, or Fire/Bubble in
    versus attribute modes; neutral/red/blue discharge changes both the
    interaction and the visual effect
    (ElecHiba.cpp:264-329,307-324,841-860; audit line 13). RECONSTRUCTED: the
    versus counter that selects the mode and its persistence across an area
    reload are not pinned by the audit (lines 26,51).
    """
    modes = {'neutral': 'InteractDenki',
             'red': 'InteractFire',
             'blue': 'InteractBubble'}
    if attribute not in modes:
        raise ValueError('Unknown ElecHiba attribute: %r' % (attribute,))
    return modes[attribute]


# ---------------------------------------------------------------------------
# Blowhogs Tank (24) and Wtank (25)
# ---------------------------------------------------------------------------

# Tank registers Dead/Wait/Move/MoveTurn/ChaseTurn/Attack/Flick
# (TankState.cpp:9-19; audit line 28). Entry resets timers and starts Wait
# (Tank.cpp:29-44).
BLOWHOG_STATES = {
    'dead': 0, 'wait': 1, 'move': 2, 'move_turn': 3, 'chase_turn': 4,
    'attack': 5, 'flick': 6,
}

# Concrete element each blowhog ejects. Ftank supplies InteractFire
# (Ftank.cpp:121-125); Wtank supplies InteractBubble (Wtank.cpp:119-123).
BLOWHOG_STIMULUS = {'Tank': 'InteractFire', 'Wtank': 'InteractBubble'}

# KEYEVENT_2 starts the blow effect and KEYEVENT_END selects the next state
# (TankState.cpp:844-899; audit line 28).
BLOWHOG_ATTACK_START_KEY = 2
BLOWHOG_ATTACK_END_KEY = 7

# emitCollideRatio traces a radius-2.5 sphere to stop range growth at
# floor/wall contact (Tank.cpp:325-368; audit line 28).
BLOWHOG_BLOW_TRACE_RADIUS = 2.5

# onKill finishes the blow effect before the base kill (Tank.cpp:50-54);
# stone/earthquake/movie/birth-drop hooks stop or hide it (Tank.cpp:117-207).
TANK_KILL_FINISHES_EFFECT = True


def blowhog_entry_state():
    """Both blowhogs reset their timers and start Wait (Tank.cpp:29-44)."""
    return 'wait'


def blowhog_attack(*, species, lateral_distance, vertical_distance,
                   forward_distance, attack_radius, range_distance,
                   wall_blocked=False):
    """Concrete element a blowhog's expanding sweep emits, or None.

    During Attack the expanding sweep supplies broad-phase candidates (a
    sphere) and tests exact hits: vertical and lateral separation are each
    bounded by mAttackRadius and forward distance by the growing range; a
    radius-2.5 trace stops growth at a floor/wall collision
    (Tank.cpp:266-319,325-368; TankState.cpp:844-899; audit line 28). A
    non-blowhog species raises. `range_distance` is the value already produced
    by blowhog_range for the current blow frame.
    """
    if species not in BLOWHOG_STIMULUS:
        raise ValueError('Not a blowhog species: %r' % (species,))
    for value in (lateral_distance, vertical_distance, forward_distance,
                  attack_radius, range_distance):
        _finite(value)
    if attack_radius < 0.0 or range_distance < 0.0:
        raise ValueError('Expected non-negative geometry')
    if not isinstance(wall_blocked, bool):
        raise ValueError('Expected boolean wall flag')
    if wall_blocked:
        return None
    if abs(lateral_distance) > attack_radius:
        return None
    if abs(vertical_distance) > attack_radius:
        return None
    if forward_distance < 0.0 or forward_distance > range_distance:
        return None
    return BLOWHOG_STIMULUS[species]


def blowhog_range(*, base_range, attack_timer, grow_rate, trace_hit=False):
    """Range the blow has reached this frame.

    emitCollideRatio grows the blow range with mAttackTimer and a radius-2.5
    sphere trace stops the growth at floor/wall contact (Tank.cpp:325-368;
    audit line 28). RECONSTRUCTED: the source growth curve is not pinned by the
    audit, so this is an explicit linear model.
    """
    for value in (base_range, attack_timer, grow_rate):
        _finite(value)
    if base_range < 0.0 or grow_rate < 0.0:
        raise ValueError('Expected non-negative range inputs')
    if not isinstance(trace_hit, bool):
        raise ValueError('Expected boolean trace flag')
    if trace_hit:
        return base_range
    return base_range + grow_rate * max(attack_timer, 0.0)


# ---------------------------------------------------------------------------
# Dweevils FireOtakara (59), WaterOtakara (60), GasOtakara (61),
# ElecOtakara (62) and BombOtakara (93)
# ---------------------------------------------------------------------------

# All five share OtakaraBase (OtakaraBase.h:11-17) and register the same
# 14-state FSM (OtakaraBaseState.cpp:14-34). State IDs OtakaraBase.h:22-39
# (audit line 30; assets lines 66-70).
DWEEVIL_STATES = {
    'dead': 0, 'flick': 1, 'wait': 2, 'move': 3, 'turn': 4, 'take': 5,
    'item_wait': 6, 'item_move': 7, 'item_turn': 8, 'item_flick': 9,
    'item_drop': 10, 'bomb_wait': 11, 'bomb_move': 12, 'bomb_turn': 13,
}
BOMB_CARRY_STATES = ('bomb_wait', 'bomb_move', 'bomb_turn')

# Per-species emitted stimulus from interactCreature (audit lines 16-19).
DWEEVIL_STIMULUS = {
    'FireOtakara': 'InteractFire',
    'WaterOtakara': 'InteractBubble',
    'GasOtakara': 'InteractGas',
    'ElecOtakara': 'InteractDenki',
    'BombOtakara': None,
}

# stimulateBomb disables culling and calls the payload Bomb's forceBomb after
# 1.5 seconds (OtakaraBase.cpp:699-707; audit line 30).
BOMB_FORCE_DELAY_SECONDS = 1.5

# BombOtakara consumes the shared Bomb blast contract; this module must not
# duplicate projectile/explosion primitives (audit line 36; receiver contract
# section 4).
BOMB_OTAKARA_CONSUMES_SHARED_BLAST = True


def dweevil_stimulus(species):
    """Stimulus a dweevil emits; None for BombOtakara's delegated Bomb.

    Fire/Bubble/Gas/Denki per species (audit lines 16-19). The dweevil's own
    element does not make it immune: immunity is a receiver property of the
    target Pikmin (audit lines 41-43).
    """
    if species not in DWEEVIL_IDS:
        raise ValueError('Not a dweevil species: %r' % (species,))
    return DWEEVIL_STIMULUS[species]


def dweevil_theft_decision(*, alive, pickable, captured, within_territory,
                           carrying=False):
    """Whether the shared Otakara search would pick this pellet up.

    Only alive, pickable, uncaptured pellets inside the home territory are
    eligible, and a dweevil already carrying cannot take a second
    (OtakaraBase.cpp:395-417; audit line 34). All inputs are treated as
    booleans.
    """
    return bool(alive and pickable and not captured and within_territory
                and not carrying)


def dweevil_capture_health(*, otakara_life):
    """Health the captured treasure is given (mOtakaraLife).

    The chosen pellet is captured on the `otakara` joint and given mOtakaraLife
    health (OtakaraBase.cpp:472-524; audit line 34). A non-positive value is
    rejected.
    """
    _finite(otakara_life)
    if otakara_life <= 0.0:
        raise ValueError('Expected positive treasure health')
    return otakara_life


def dweevil_damage_route(*, carrying):
    """'treasure' while a treasure is held, else 'dweevil'.

    Damage while a treasure is held decrements treasure health; otherwise it
    damages the Dweevil (OtakaraBase.cpp:550-574; audit line 34).
    """
    return 'treasure' if carrying else 'dweevil'


def dweevil_drop(*, carrying, reason, already_dropped=False):
    """Exactly-once forced treasure drop; returns (dropped, carrying_after).

    A death/stone/earthquake path calls fallTreasure, ending capture and
    resetting collision geometry (OtakaraBase.cpp:530-544,242-304); the shared
    item-drop event type 2 also calls fallTreasure(true)
    (OtakaraBaseState.cpp:680-727; audit lines 30,34). A second drop for the
    same capture does nothing, so recovery cannot be duplicated.
    """
    if reason not in ('death', 'stone', 'earthquake', 'interruption'):
        raise ValueError('Unknown drop reason: %r' % (reason,))
    if not isinstance(carrying, bool) or not isinstance(already_dropped, bool):
        raise ValueError('Expected boolean carry flags')
    if not carrying or already_dropped:
        return (False, False)
    return (True, False)


def bomb_otakara_payload(*, payload_present, bittered, earthquake,
                         chase_elapsed=0.0):
    """Delegated action for BombOtakara's carried Bomb payload.

    The payload Bomb owns damage/explosion: while bittered, damage calls the
    Bomb damageCallBack; otherwise forceBomb; an earthquake also forces it
    (BombOtakara.cpp:42-87; audit line 20). initBombOtakara requests the
    separate EnemyID_Bomb payload, captures it on the `otakara` joint and sets
    mCarrier (OtakaraBase.cpp:649-677); doFinishWaitingBirthTypeDrop
    reinitializes the payload (OtakaraBase.cpp:321-327). The bomb-carry states
    kill the Dweevil if the payload pointer disappears and call stimulateBomb
    while chasing; after 1.5 s stimulateBomb disables culling and calls the
    payload Bomb's forceBomb
    (OtakaraBaseState.cpp:744-846,863-907; OtakaraBase.cpp:699-707; audit line
    30). Returns one of 'kill_carrier', 'force_bomb', 'damage_payload' or
    'chase_payload'. RECONSTRUCTED: the Bomb's own explosion
    lifetime/carcass/Piklopedia behavior is outside this audit (audit line 36).
    """
    if not isinstance(payload_present, bool) or not isinstance(bittered, bool):
        raise ValueError('Expected boolean payload flags')
    if not isinstance(earthquake, bool):
        raise ValueError('Expected boolean earthquake flag')
    _finite(chase_elapsed)
    if not payload_present:
        return 'kill_carrier'
    if earthquake:
        return 'force_bomb'
    if bittered:
        return 'damage_payload'
    if chase_elapsed >= BOMB_FORCE_DELAY_SECONDS:
        return 'force_bomb'
    return 'chase_payload'


# ---------------------------------------------------------------------------
# Reconstruction markers and unknowns
# ---------------------------------------------------------------------------
# Behavior the audit does not pin to exact source/frame values is marked here
# and carries a `.reconstructed = True` attribute on its function.
RECONSTRUCTED = frozenset({
    'gashiba_linked_owner',        # setInitLivingThing gate not reproduced
    'elechiba_versus_stimulus',    # versus counter/mode persistence unpinned
    'blowhog_range',               # emitCollideRatio growth curve not pinned
    'bomb_otakara_payload',        # Bomb lifetime outside the audit
})

# Unresolved from source-only inspection (audit lines 36,43,51).
UNKNOWNS = (
    'Exact frame timing and radius values from the runtime parameter assets.',
    'Whether hazard/dweevil state survives a save/area reload or day transition.',
    'Whether randomized placements preserve valid terrain/clearance for every '
    'elemental footprint.',
    'Complete Bomb explosion object lifetime, carcass and Piklopedia behavior.',
    'Captain equipment and enemy-side immunities require their own receiver '
    'audit; Pikmin receiver rules must not be copied to them.',
)

gashiba_linked_owner.reconstructed = True
elechiba_versus_stimulus.reconstructed = True
blowhog_range.reconstructed = True
bomb_otakara_payload.reconstructed = True
