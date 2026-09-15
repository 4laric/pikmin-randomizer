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


def validate_slice2(text: str) -> dict:
    result = {
        'attack_started': False,
        'emitted': False,
        'recv_observed': False,
        'nonimmune_accepted': False,
        'immunity_via_handled': False,
        'phase_advanced': False,
        'weapon_count_dropped': False,
    }
    recv_lines = []
    phases = set()
    weapon_counts = []

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
                result['immunity_via_handled'] = True
        elif marker == 'P2_BIGTREASURE_FSM':
            phase = fields.get('phase')
            if phase is not None:
                phases.add(phase)
            weapons = _to_int(fields.get('weapons'))
            if weapons is not None:
                weapon_counts.append(weapons)

    result['phase_advanced'] = len(phases) >= 2
    result['weapon_count_dropped'] = _non_increasing_with_drop(weapon_counts)
    result['recv_lines'] = recv_lines
    return result
