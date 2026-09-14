"""Lane 18 contested-cargo, nest and release model (#168/#220).

Host-side model of the source ``PanModokiBase`` cargo rules used by the small
Breadbug (38) and Giant Breadbug (40): eligibility, single-channel contest
strength, interruption (``Damage``/``giveup``) release, death throw-up recovery
and the 15-slot treasure cap. It records what the family must prove natively and
does not itself mutate a save or an actor. See
``docs/PIKMIN2_BREADBUG_ACTOR_RUNTIME.md``.
"""
import math

CARRY_CHANNEL = 'PCS_Unk2'
MAX_TREASURE_SLOTS = 15
TAKEOVER_STALL_SECONDS = 0.5
NEST_DROP_HEIGHT = 10.0
THROW_UP_RING_RADIUS = 40.0

EAT = 'eat'
DROP = 'drop'
RECOVER = 'recover'
DIGEST = 'digest'

RELEASE_REASONS = (EAT, DROP, RECOVER, DIGEST)


def carry_strength(min_pikis, max_pikis):
    """Source ``mCarryStrength``: ``(pelletMin + pelletMax) * 0.5``."""
    if type(min_pikis) is not int or type(max_pikis) is not int:
        raise ValueError('Carry bounds must be integers')
    if min_pikis < 0 or max_pikis < min_pikis:
        raise ValueError('Invalid carry bounds')
    return (min_pikis + max_pikis) * 0.5


def carriers_win(carrier_count, min_pikis, max_pikis):
    """True when Pikmin carriers strictly out-pull the Breadbug each frame."""
    if type(carrier_count) is not int or carrier_count < 0:
        raise ValueError('Invalid carrier count')
    return carrier_count >= carry_strength(min_pikis, max_pikis)


def targetable(*, already_stuck, pellet_carryable, treasure_slots, min_weight,
               weight_limit, variant='small'):
    """Source ``isTargetable`` eligibility for a candidate cargo pellet.

    ``variant='small'`` (id 38) targets strictly lighter cargo
    (``weight_limit > min_weight``); ``variant='giant'`` (id 40) targets cargo at
    or above its threshold (``weight_limit <= min_weight``).
    """
    if variant not in ('small', 'giant'):
        raise ValueError('Unknown breadbug variant: ' + repr(variant))
    if not pellet_carryable or already_stuck:
        return False
    if treasure_slots >= MAX_TREASURE_SLOTS:
        return False
    if variant == 'small':
        return weight_limit > min_weight
    return weight_limit <= min_weight


def release_plan(reason, held_slots=0):
    """Classify a cargo release by source outcome.

    - ``EAT``: ``endCarry`` consumes carcasses/items and kills stuck Pikmin;
      treasure slot 0 stays captured-alive inside the nest matrix.
    - ``DROP``: an interruption (press/hipdrop ``Damage`` state) gives up the
      pull channel and drops the cargo in place.
    - ``RECOVER``: losing the contest returns the cargo to the carriers.
    - ``DIGEST``: entering the underground ``Hide`` state digests the held cargo.
    """
    if reason not in RELEASE_REASONS:
        raise ValueError('Unknown release reason: ' + repr(reason))
    if type(held_slots) is not int or held_slots < 0:
        raise ValueError('Invalid held-slot count')
    if held_slots > MAX_TREASURE_SLOTS:
        raise ValueError('Held treasure exceeds the source slot cap')
    if reason == EAT:
        return {'reason': EAT, 'keeps_slot0_in_nest': held_slots > 0,
                'returns_cargo': False, 'cargo_consumed': True}
    if reason == DROP:
        return {'reason': DROP, 'keeps_slot0_in_nest': False,
                'returns_cargo': True, 'cargo_consumed': False}
    if reason == RECOVER:
        return {'reason': RECOVER, 'keeps_slot0_in_nest': False,
                'returns_cargo': True, 'cargo_consumed': False}
    return {'reason': DIGEST, 'keeps_slot0_in_nest': True,
            'returns_cargo': False, 'cargo_consumed': True}


def throw_up_positions(nest_x, nest_y, nest_z, count):
    """Death throw-up geometry: nest + 10y, radial ring ``TAU*i/n`` (skipped n=1)."""
    if type(count) is not int or not 0 <= count <= MAX_TREASURE_SLOTS:
        raise ValueError('Invalid throw-up count')
    if count == 1:
        return [(nest_x, nest_y + NEST_DROP_HEIGHT, nest_z)]
    spots = []
    for i in range(count):
        angle = 2.0 * math.pi * i / count
        spots.append((nest_x + THROW_UP_RING_RADIUS * math.cos(angle),
                      nest_y + NEST_DROP_HEIGHT,
                      nest_z + THROW_UP_RING_RADIUS * math.sin(angle)))
    return spots


def reconcile_death(held_slots, released):
    """Exactly-once recovery: every held treasure is returned, none created."""
    if type(held_slots) is not int or not 0 <= held_slots <= MAX_TREASURE_SLOTS:
        raise ValueError('Invalid held-slot count')
    if type(released) is not int or released < 0:
        raise ValueError('Invalid released count')
    return {'held': held_slots, 'returned': released,
            'lost': held_slots - released if released <= held_slots else 0,
            'duplicated': released > held_slots}
