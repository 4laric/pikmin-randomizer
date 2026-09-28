"""Validate the opt-in room fixture's observed native corpse lifecycle."""
import math
import re


def validate_corpse(log, approach=True):
    rows = []
    for line in log.splitlines():
        if line.startswith(('P2_LIFECYCLE_', 'P2_CORPSE_CAPTAIN_APPROACH ')):
            name, *fields = line.split()
            rows.append((name, dict(field.split('=', 1) for field in fields)))

    def one(name):
        matches = [(i, fields) for i, (kind, fields) in enumerate(rows) if kind == name]
        if len(matches) != 1:
            raise ValueError('Expected one '+name)
        return matches[0]

    def number(row, key):
        value = float(row[key])
        if not math.isfinite(value):
            raise ValueError('Nonfinite corpse evidence')
        return value

    def pointer(row, key):
        value = row[key]
        if not re.fullmatch(r'(?:0x)?[0-9a-fA-F]+', value) or not int(value, 16):
            raise ValueError('Missing corpse identity or goal')
        return int(value, 16)

    try:
        ei, enemy = one('P2_LIFECYCLE_ENEMY')
        di, death = one('P2_LIFECYCLE_DEATH')
        bi, birth = one('P2_LIFECYCLE_BIRTH')
        ri, removed = one('P2_LIFECYCLE_REMOVED')
        goals = [(i, row) for i, (kind, row) in enumerate(rows)
                 if kind == 'P2_LIFECYCLE_STATE' and row.get('state') == '1']
        if len(goals) != 1:
            raise ValueError('Expected one native goal intake')
        gi, goal = goals[0]
        if not ei < di <= bi < gi < ri:
            raise ValueError('Corpse lifecycle order differs')
        frames = [number(row, 'frame') for row in (enemy, death, birth, goal, removed)]
        if frames != sorted(frames):
            raise ValueError('Corpse frames went backwards')
        identity = pointer(enemy, 'enemy')
        pointer(enemy, 'generator')
        if any(pointer(row, 'enemy') != identity for row in (death, birth)):
            raise ValueError('Enemy identity changed')
        pellet = pointer(birth, 'pellet')
        for kind, row in rows:
            if kind in ('P2_LIFECYCLE_STATE', 'P2_LIFECYCLE_REMOVED') and pointer(row, 'pellet') != pellet:
                raise ValueError('Pellet identity changed')
        pointer(goal, 'goal')
        if number(death, 'health') > 0 or removed['last_state'] != '1':
            raise ValueError('Missing death or terminal goal state')
        distance = number(removed, 'distance')
        if number(goal, 'distance') <= 100 or distance < number(goal, 'distance'):
            raise ValueError('Corpse did not traverse the room')
        if approach:
            ai, arrival = one('P2_CORPSE_CAPTAIN_APPROACH')
            if not ei < ai < di or not 0 <= number(arrival, 'distance') <= 120 or arrival['controller_only'] != '1':
                raise ValueError('Missing captain controller approach')
        elif any(kind == 'P2_CORPSE_CAPTAIN_APPROACH' for kind, _ in rows):
            raise ValueError('Unexpected approach in distant control')
        return dict(death_frame=frames[1], birth_frame=frames[2], goal_frame=frames[3],
                    removal_frame=frames[4], distance=distance, controller_approach=approach)
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError('Malformed corpse lifecycle evidence') from error
