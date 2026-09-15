"""Root-side validator for the BigTreasure (Titan Dweevil) elemental-receiver
runtime log, slice 2.

Parses a real-GL text log and checks the required observations, one token per
space, no escaping. Unrelated lines are ignored and CRLF line endings, extra
spaces and tabs are tolerated. Standard library only.
"""

_IMMUNE_SPECIES = {
    'fire': {'1'},   # red
    'water': {'0'},  # blue
    'elec': {'2'},   # yellow
    'gas': {'4'},    # white
}

_ADVANCE_PHASES = frozenset({'PreAttack', 'ItemWalk', 'DropItem'})


def _to_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_line(line):
    tokens = line.split()
    if not tokens:
        return None, {}
    marker = tokens[0]
    fields = {}
    for token in tokens[1:]:
        if '=' in token:
            key, value = token.split('=', 1)
            fields[key] = value
    return marker, fields


def _non_increasing_with_drop(counts):
    if len(counts) < 2:
        return False
    dropped = False
    for previous, current in zip(counts, counts[1:]):
        if current > previous:
            return False
        if current < previous:
            dropped = True
    return dropped


def _weapon_drop_index(fsm_lines):
    for index in range(1, len(fsm_lines)):
        previous_weapons = fsm_lines[index - 1][1]
        weapons = fsm_lines[index][1]
        if (
            previous_weapons is not None
            and weapons is not None
            and weapons < previous_weapons
        ):
            return index
    return None


def validate_slice2(text: str) -> dict:
    result = {
        'attack_started': False,
        'emitted': False,
        'recv_observed': False,
        'nonimmune_accepted': False,
        'immune_rejected': False,
        'handled_set_held': False,
        'phase_advanced': False,
        'weapon_count_dropped': False,
    }
    recv_lines = []
    weapon_counts = []
    fsm_lines = []

    if not text:
        result['recv_lines'] = recv_lines
        return result

    for line in text.splitlines():
        marker, fields = _parse_line(line)
        if marker == 'P2_BIGTREASURE_ATTACK_START':
            result['attack_started'] = True
        elif marker == 'P2_BIGTREASURE_ATTACK_EMIT':
            nodes = _to_int(fields.get('nodes'))
            if nodes is not None and nodes >= 1:
                result['emitted'] = True
        elif marker == 'P2_BIGTREASURE_RECV':
            result['recv_observed'] = True
            recv_lines.append(line.strip())
            accepted = fields.get('accepted')
            if accepted == '1':
                result['nonimmune_accepted'] = True
            if accepted == '0':
                result['immune_rejected'] = True
        elif marker == 'P2_BIGTREASURE_FSM':
            phase = fields.get('phase')
            weapons = _to_int(fields.get('weapons'))
            fsm_lines.append((phase, weapons))
            if weapons is not None:
                weapon_counts.append(weapons)
        elif marker == 'P2_BIGTREASURE_SLICE2_HANDLED':
            first = _to_int(fields.get('first'))
            second = _to_int(fields.get('second'))
            if first == 1 and second == 0:
                result['handled_set_held'] = True

    drop_index = _weapon_drop_index(fsm_lines)
    if drop_index is None:
        result['phase_advanced'] = False
    else:
        result['phase_advanced'] = any(
            phase in _ADVANCE_PHASES
            for phase, _weapons in fsm_lines[drop_index + 1:]
        )
    result['weapon_count_dropped'] = _non_increasing_with_drop(weapon_counts)
    result['recv_lines'] = recv_lines
    return result
