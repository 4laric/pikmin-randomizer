"""Lane 16 Frog/MaroFrog source combat and parameter model (#167/#194/#201).

Encodes the audited source contract used to judge a natural frog combat chain:
retail parameters, the shared FSM/motion mapping, the jump-attack resolution and
the source landing press. It also machine-checks the native ``P2_FROG_READY``
rows for source identity/health. It does not itself run the native FSM. See
``docs/PIKMIN2_FROG_RUNTIME_ACCEPTANCE.md``.
"""
import re

FROG = 0
MAROFROG = 1

PARAMS = {
    'Frog': {
        'id': FROG, 'health': 800.0, 'sight': 360.0, 'attack_range': 200.0,
        'attack_damage': 10.0, 'air_time': 1.0, 'jump_speed': 320.0,
        'jump_fail': 0.2, 'fall_speed': 300.0, 'corpse_pokos': 5,
        'carry': (7, 14), 'onion': (8, 8), 'pickup_radius': 22.0,
        'pickup_height': 14.0, 'pickup_offset': (-27.3, 0.0, 12.3),
    },
    'MaroFrog': {
        'id': MAROFROG, 'health': 1100.0, 'sight': 360.0, 'attack_range': 250.0,
        'attack_damage': 20.0, 'air_time': 1.0, 'jump_speed': 350.0,
        'jump_fail': 0.1, 'fall_speed': 330.0, 'corpse_pokos': 7,
        'carry': (7, 14), 'onion': (8, 8), 'pickup_radius': 22.0,
        'pickup_height': 14.0, 'pickup_offset': (-0.6, 0.0, -34.0),
    },
}

FSM_STATES = ('Dead', 'Wait', 'Turn', 'Jump', 'JumpWait', 'Fall', 'Attack',
              'Fail', 'TurnToHome', 'GoHome')

MOTION_CLIPS = (('Dead', 'dead'), ('Wait', 'wait1'), ('Turn', 'waitact1'),
                ('Jump', 'type1'), ('JumpWait', 'wait2'), ('Fall', 'type2'),
                ('Attack', 'attack'), ('Fail', 'damage'), ('Carry', 'type5'))

RETARGETS_CAPTAINS = ('MaroFrog',)


def _params(kind):
    if isinstance(kind, int):
        for name, values in PARAMS.items():
            if values['id'] == kind:
                return name, values
        raise ValueError('Unknown frog kind: ' + repr(kind))
    if kind not in PARAMS:
        raise ValueError('Unknown frog species: ' + repr(kind))
    return kind, PARAMS[kind]


def jump_attack(kind, distance, roll):
    """Resolve a source jump attack: velocity from displacement/air time + jump speed.

    ``roll`` is a caller-supplied ``[0, 1)`` probability; a roll below the
    per-species jump-failure probability fails the jump instead of attacking.
    """
    name, params = _params(kind)
    if distance < 0:
        raise ValueError('Jump distance must be non-negative')
    if not 0.0 <= roll < 1.0:
        raise ValueError('Jump roll must be in [0, 1)')
    return {'species': name, 'fails': roll < params['jump_fail'],
            'air_time': params['air_time'], 'jump_speed': params['jump_speed'],
            'horizontal_speed': distance / params['air_time'],
            'fall_speed': params['fall_speed'], 'attack_damage': params['attack_damage']}


def landing_press(kind, bittered):
    """Source falling collision presses a grounded Navi/Pikmin unless bittered."""
    _params(kind)
    return not bittered


def landing_press_victims(bittered, grounded_pikmin, grounded_navi):
    """Resolve which grounded actors a falling frog presses.

    The source rule (Frog.cpp:174) presses every grounded Pikmin and Navi on
    contact; a Bittered victim is skipped. ``grounded_pikmin``/``grounded_navi``
    are iterables of already-grounded actor tokens, so airborne actors stay the
    caller's concern. The returned counts match the source one-press-per-victim
    behavior.
    """
    pikmin = [] if grounded_pikmin is None else list(grounded_pikmin)
    navi = [] if grounded_navi is None else list(grounded_navi)
    if bittered:
        return {'bittered': True, 'pressed_pikmin': [], 'pressed_navi': [],
                'pressed': 0}
    return {'bittered': False, 'pressed_pikmin': pikmin, 'pressed_navi': navi,
            'pressed': len(pikmin) + len(navi)}


def retargets_captains(kind):
    """MaroFrog overrides ``attackNaviPosition`` to chase a living captain."""
    name, _ = _params(kind)
    return name in RETARGETS_CAPTAINS


def corpse(kind):
    """Return the source corpse/carry contract for one species."""
    _, params = _params(kind)
    return {'pokos': params['corpse_pokos'], 'carry': params['carry'],
            'onion': params['onion'], 'pickup_radius': params['pickup_radius'],
            'pickup_height': params['pickup_height'], 'pickup_offset': params['pickup_offset']}


def carry_route(kind):
    """Return the source corpse -> carry -> Onion transport fields for one species."""
    name, params = _params(kind)
    contract = corpse(name)
    return {'species': name, 'pokos': contract['pokos'], 'carry': params['carry'],
            'onion': params['onion'], 'pickup_radius': contract['pickup_radius'],
            'pickup_height': contract['pickup_height'], 'pickup_offset': contract['pickup_offset']}


def validate_ready(text):
    """Check native ``P2_FROG_READY`` rows report source identity and health."""
    rows = re.findall(r'P2_FROG_READY species=(\w+) generator=(\d+) health=([\d.]+) '
                      r'max_health=([\d.]+) behavior=P1_proxy rewards=P1_unchanged', text)
    checks = {'rows': len(rows) == 2}
    for species, _, health, max_health in rows:
        params = PARAMS.get(species)
        checks[species] = params is not None and float(health) == params['health'] \
            and float(max_health) == params['health']
    return {'passed': all(checks.values()), 'checks': checks, 'rows': len(rows)}
