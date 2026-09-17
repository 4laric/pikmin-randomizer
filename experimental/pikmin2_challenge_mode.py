"""P2 Challenge host-mode consumer (#651).

Cross-partition prerequisite for challenge-0/1/2/3 P1 scopes. Consumes the
DONE framework contract (``experimental.pikmin2_challenge_framework_contract``)
as an artifact - it never forks the stage-table parser. Implements the
1P Challenge host state machine:

- stage select by the contract's ``ui_index`` over decoded stage entries;
- starting squad + sprays applied from the contract's ``roster`` /
  ``bitter_sprays`` / ``spicy_sprays``;
- ``mTimeLimit`` countdown with per-floor extension on descent;
- end states: timeout, extinction, give-up, captain_down;
- ordinary vs deathless result boundary, and the retry/reset boundary
  (attempt-local reset, persistent clear/score);
- score delegation to the contract's ``compute_score``.

Explicitly unsupported (kept visible, never silently approximated):
``coop_2p``, ``key_completion``, ``result_screen``.

No runtime, no gameplay acceptance. Stdlib only; pure logic.
"""

from experimental.pikmin2_challenge_framework_contract import (
    COLORS,
    ContractError,
    HAPPA,
    compute_score,
)

UNSUPPORTED = ('coop_2p', 'key_completion', 'result_screen')

END_TIMEOUT = 'timeout'
END_EXTINCTION = 'extinction'
END_GIVE_UP = 'give_up'
END_CAPTAIN_DOWN = 'captain_down'
END_STATES = (END_TIMEOUT, END_EXTINCTION, END_GIVE_UP, END_CAPTAIN_DOWN)

RESULT_ORDINARY = 'ordinary'
RESULT_DEATHLESS = 'deathless'

# Attempt-local resets on retry; persistent survives retry.
ATTEMPT_LOCAL_KEYS = ('population', 'time_left', 'floor_index', 'pokos',
                      'end_state', 'score')
PERSISTENT_KEYS = ('cleared', 'high_score', 'pink_flower', 'perfect')


class ModeError(ValueError):
    pass


def stage_select(stages, ui_index):
    """Select a decoded stage entry by its contract ``ui_index``."""
    if not isinstance(stages, list) or not stages:
        raise ModeError('Decoded stage table required')
    if type(ui_index) is not int or ui_index < 0:
        raise ModeError('ui_index must be a non-negative int')
    for stage in stages:
        if stage.get('ui_index') == ui_index:
            return dict(stage)
    raise ModeError('Unknown stage ui_index: %d' % ui_index)


def _validate_roster(roster):
    if (not isinstance(roster, list) or len(roster) != len(COLORS)
            or any(not isinstance(row, list) or len(row) != len(HAPPA)
                   for row in roster)):
        raise ModeError('Roster must be %dx%d (color x happa)' % (len(COLORS), len(HAPPA)))
    if any(type(v) is not int or v < 0 for row in roster for v in row):
        raise ModeError('Roster values must be non-negative ints')
    return [list(row) for row in roster]


def starting_state(stage):
    """Build the attempt-local start state from a decoded stage entry.

    Applies the contract roster (squad) and spray counts exactly.
    """
    if not isinstance(stage, dict):
        raise ModeError('Stage entry must be a mapping')
    floors = stage.get('floors')
    timers = stage.get('floor_seconds')
    if type(floors) is not int or floors < 1:
        raise ModeError('Stage needs a positive floor count')
    if (not isinstance(timers, list) or len(timers) != floors
            or any(type(t) not in (int, float) or t < 0 for t in timers)):
        raise ModeError('floor_seconds must list one non-negative timer per floor')
    return {
        'cave_id': stage.get('cave_id'),
        'ui_index': stage.get('ui_index'),
        'floor_count': floors,
        'floor_seconds': [float(t) for t in timers],
        'floor_index': 0,
        'time_left': float(timers[0]),
        'squad': _validate_roster(stage.get('roster')),
        'bitter_sprays': int(stage.get('bitter_sprays', 0)),
        'spicy_sprays': int(stage.get('spicy_sprays', 0)),
        'population': sum(sum(row) for row in _validate_roster(stage.get('roster'))),
        'pokos': 0,
        'end_state': None,
        'attempt_local': {k: None for k in ATTEMPT_LOCAL_KEYS},
        'persistent': {k: None for k in PERSISTENT_KEYS},
    }


def tick(state, seconds):
    """Advance the mTimeLimit countdown; timeout ends the attempt."""
    if state['end_state'] is not None:
        return state
    if type(seconds) not in (int, float) or seconds < 0:
        raise ModeError('Tick seconds must be non-negative')
    state['time_left'] = max(0.0, state['time_left'] - float(seconds))
    if state['time_left'] <= 0.0:
        state['end_state'] = END_TIMEOUT
    return state


def descend(state):
    """Advance one floor, extending the timer by that floor's contract value."""
    if state['end_state'] is not None:
        raise ModeError('Cannot descend after the attempt ended')
    nxt = state['floor_index'] + 1
    if nxt >= state['floor_count']:
        raise ModeError('No deeper floor in this stage')
    state['floor_index'] = nxt
    state['time_left'] = state['floor_seconds'][nxt]
    return state


def check_end(state, pikmin_left, captain_dead=False, gave_up=False):
    """Apply terminal conditions in engine order; captain death wins first.

    #632 captain safety: a dead captain must end the attempt, never be
    papered over by invincibility.
    """
    if state['end_state'] is not None:
        return state
    if captain_dead:
        state['end_state'] = END_CAPTAIN_DOWN
    elif gave_up:
        state['end_state'] = END_GIVE_UP
    elif pikmin_left is None or pikmin_left <= 0:
        state['end_state'] = END_EXTINCTION
    return state


def result(state, deathless=False):
    """Ordinary vs deathless result boundary plus contract score.

    Deathless requires no captain-down/give-up and no extinction. Score is
    delegated to the contract's ``compute_score`` (never reimplemented).
    """
    if state['end_state'] is None:
        raise ModeError('Attempt has not ended')
    pikmin_left = state['population']
    score = compute_score(int(state['pokos']), int(state['time_left']), int(pikmin_left))
    deathless_ok = (deathless
                    and state['end_state'] not in (END_EXTINCTION, END_CAPTAIN_DOWN, END_GIVE_UP))
    return {
        'cave_id': state['cave_id'],
        'end_state': state['end_state'],
        'result_kind': RESULT_DEATHLESS if deathless_ok else RESULT_ORDINARY,
        'deathless': deathless_ok,
        'score': score,
        'cleared': state['end_state'] == END_TIMEOUT and pikmin_left > 0,
        'unsupported': list(UNSUPPORTED),
    }


def retry(state):
    """Reset attempt-local state; persistent clear/high-score survive."""
    attempt_local = dict(state['attempt_local'])
    persistent = dict(state['persistent'])
    if persistent.get('high_score') is None:
        persistent['high_score'] = 0
    fresh = starting_state({
        'cave_id': state['cave_id'],
        'ui_index': state['ui_index'],
        'floors': state['floor_count'],
        'floor_seconds': state['floor_seconds'],
        'roster': state['squad'],
        'bitter_sprays': state['bitter_sprays'],
        'spicy_sprays': state['spicy_sprays'],
    })
    fresh['persistent'] = persistent
    return fresh


def unsupported_semantics():
    """Expose the explicitly unsupported contract surfaces."""
    return {name: 'unsupported: no source-proven runtime semantics yet'
            for name in UNSUPPORTED}