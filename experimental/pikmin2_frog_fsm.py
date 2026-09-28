"""Validator for the native Pikmin 2 Frog/MaroFrog FSM port.

The native FSM emits one log line per state transition in this exact shape::

    P2_FROG_STATE species=Frog generator=201001 state=jump

``species`` is ``Frog`` or ``MaroFrog``, ``generator`` is a decimal integer,
and ``state`` is one of the ten states in :data:`STATES`.

This module parses those lines and applies the source state machine's
invariants: legal states, a ``wait`` start, permitted state adjacencies, and a
terminal ``dead`` state. It also supports optional trace requirements for a
combat cycle (a ``jump`` and an ``attack``) and required species variants.
"""

import re

STATES = (
    'dead',
    'wait',
    'turn',
    'jump',
    'jumpwait',
    'fall',
    'attack',
    'fail',
    'turntohome',
    'gohome',
)

ADJACENT = {
    'dead': set(),
    'wait': {'dead', 'jump', 'wait', 'turn'},
    'turn': {'jump', 'wait', 'dead'},
    'jump': {'jumpwait', 'fail'},
    'jumpwait': {'fall'},
    'fall': {'attack'},
    'attack': {'dead', 'wait', 'turntohome'},
    'fail': {'dead', 'jump', 'turntohome', 'wait'},
    'turntohome': {'gohome', 'jump', 'dead'},
    'gohome': {'wait', 'jump', 'dead'},
}

_LINE_RE = re.compile(
    r'P2_FROG_STATE\s+species=(?P<species>\S+)\s+'
    r'generator=(?P<generator>\d+)\s+state=(?P<state>\S+)'
)


def parse_states(text):
    """Parse every ``P2_FROG_STATE`` line in ``text`` into a list of dicts.

    Each matching line becomes ``{'species': s, 'generator': int(g),
    'state': st}`` in the order encountered. Any line that is not a
    ``P2_FROG_STATE`` line (e.g. ``P2_FROG_READY`` / ``P2_FROG_LAND``,
    unrelated noise) is ignored. Raises :class:`ValueError` if a matching line
    names an unknown state.
    """
    rows = []
    for line in text.splitlines():
        match = _LINE_RE.search(line)
        if match is None:
            continue
        state = match.group('state')
        if state not in STATES:
            raise ValueError(
                "unknown FSM state {!r} in line: {}".format(state, line.strip())
            )
        rows.append({
            'species': match.group('species'),
            'generator': int(match.group('generator')),
            'state': state,
        })
    return rows


def _actor_order(rows):
    """Group rows by ``(species, generator)``, preserving per-actor order."""
    actors = {}
    for row in rows:
        key = (row['species'], row['generator'])
        actors.setdefault(key, []).append(row['state'])
    return actors


def validate(rows, require_combat=False, require_variants=()):
    """Validate a parsed FSM trace against the source state machine.

    ``rows`` is the list of dicts returned by :func:`parse_states` (a raw str
    is also accepted for convenience). Returns a dict with:

    * ``passed`` -- True if every active check passed.
    * ``checks`` -- per-check booleans (``legal_states``, ``starts_wait``,
      ``adjacency``, ``dead_terminal``, ``combat``, ``variants``).
    * ``errors`` -- human-readable strings for each failed check.
    """
    if isinstance(rows, str):
        rows = parse_states(rows)

    actors = _actor_order(rows)
    errors = []

    legal_states = all(row['state'] in STATES for row in rows)
    if not legal_states:
        bad = sorted({row['state'] for row in rows if row['state'] not in STATES})
        errors.append('illegal states seen: {}'.format(bad))

    bad_starts = [
        key for key, states in actors.items()
        if states and states[0] != 'wait'
    ]
    starts_wait = not bad_starts
    if bad_starts:
        errors.append(
            'actors not starting in wait: {}'.format(sorted(bad_starts))
        )

    bad_pairs = []
    for key, states in actors.items():
        for prev, nxt in zip(states, states[1:]):
            if nxt not in ADJACENT[prev]:
                bad_pairs.append((key, prev, nxt))
    adjacency = not bad_pairs
    if bad_pairs:
        errors.append('illegal transitions: {}'.format(bad_pairs))

    non_terminal_dead = []
    for key, states in actors.items():
        if 'dead' not in states:
            continue
        if states.index('dead') != len(states) - 1:
            non_terminal_dead.append(key)
    dead_terminal = not non_terminal_dead
    if non_terminal_dead:
        errors.append(
            'dead not terminal for actors: {}'.format(sorted(non_terminal_dead))
        )

    has_jump = any(row['state'] == 'jump' for row in rows)
    has_attack = any(row['state'] == 'attack' for row in rows)
    combat = (not require_combat) or (has_jump and has_attack)
    if require_combat and not (has_jump and has_attack):
        errors.append('require_combat: missing jump/attack combat cycle')

    present = {row['species'] for row in rows}
    missing_variants = [v for v in require_variants if v not in present]
    variants = not missing_variants
    if missing_variants:
        errors.append(
            'require_variants: missing species {}'.format(missing_variants)
        )

    checks = {
        'legal_states': legal_states,
        'starts_wait': starts_wait,
        'adjacency': adjacency,
        'dead_terminal': dead_terminal,
        'combat': combat,
        'variants': variants,
    }

    return {
        'passed': all(checks.values()),
        'checks': checks,
        'errors': errors,
    }
