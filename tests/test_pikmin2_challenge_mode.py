"""Focused tests for the P2 challenge host-mode consumer (#651).

Contract-driven; no retail values are re-derived here and no gameplay gate is
passed. Unsupported semantics stay explicit and are asserted as such.
"""

import unittest

from experimental.pikmin2_challenge_framework_contract import compute_score
from experimental.pikmin2_challenge_mode import (
    END_CAPTAIN_DOWN,
    END_EXTINCTION,
    END_TIMEOUT,
    ModeError,
    RESULT_DEATHLESS,
    RESULT_ORDINARY,
    UNSUPPORTED,
    check_end,
    descend,
    result,
    retry,
    stage_select,
    starting_state,
    tick,
    unsupported_semantics,
)


def stage(ui_index=1, floors=2, timers=(130.0, 100.0), roster=None):
    base = [[0] * 3 for _ in range(7)]
    if roster is None:
        base[0][0] = 5
    else:
        base = roster
    return {'cave_id': 'ch_MUKI_metal', 'ui_index': ui_index, 'floors': floors,
            'floor_seconds': list(timers), 'roster': base,
            'bitter_sprays': 1, 'spicy_sprays': 2}


class StageSelectTests(unittest.TestCase):
    def test_select_by_ui_index(self):
        pages = [stage(ui_index=0), stage(ui_index=1)]
        self.assertEqual(stage_select(pages, 1)['ui_index'], 1)

    def test_unknown_and_bad_index(self):
        for value in (9, -1, '1'):
            with self.assertRaises(ModeError):
                stage_select([stage(1)], value)
        with self.assertRaises(ModeError):
            stage_select([], 0)


class StartStateTests(unittest.TestCase):
    def test_squad_and_sprays_from_contract_fields(self):
        state = starting_state(stage())
        self.assertEqual(state['population'], 5)
        self.assertEqual(state['bitter_sprays'], 1)
        self.assertEqual(state['spicy_sprays'], 2)
        self.assertEqual(state['time_left'], 130.0)

    def test_timer_count_must_match_floors(self):
        with self.assertRaises(ModeError):
            starting_state(stage(floors=2, timers=(100.0,)))

    def test_negative_roster_rejected(self):
        bad = [[0] * 3 for _ in range(7)]
        bad[0][0] = -1
        with self.assertRaises(ModeError):
            starting_state(stage(roster=bad))


class CountdownTests(unittest.TestCase):
    def test_timeout_ends_attempt(self):
        state = starting_state(stage(floors=1, timers=(10.0,)))
        tick(state, 4.0)
        self.assertEqual(state['end_state'], None)
        tick(state, 6.0)
        self.assertEqual(state['end_state'], END_TIMEOUT)

    def test_negative_tick_rejected(self):
        state = starting_state(stage())
        with self.assertRaises(ModeError):
            tick(state, -1)

    def test_descend_extends_timer_and_floor(self):
        state = starting_state(stage())
        descend(state)
        self.assertEqual(state['floor_index'], 1)
        self.assertEqual(state['time_left'], 100.0)
        with self.assertRaises(ModeError):
            descend(state)  # no deeper floor

    def test_tick_after_end_is_noop(self):
        state = starting_state(stage(floors=1, timers=(5.0,)))
        tick(state, 5.0)
        before = state['time_left']
        tick(state, 1.0)
        self.assertEqual(state['time_left'], before)


class EndStateTests(unittest.TestCase):
    def test_captain_down_wins(self):
        state = starting_state(stage())
        check_end(state, 0, captain_dead=True)
        self.assertEqual(state['end_state'], END_CAPTAIN_DOWN)

    def test_extinction(self):
        state = starting_state(stage())
        check_end(state, 0)
        self.assertEqual(state['end_state'], END_EXTINCTION)

    def test_give_up(self):
        state = starting_state(stage())
        check_end(state, 5, gave_up=True)
        self.assertEqual(state['end_state'], 'give_up')


class ResultTests(unittest.TestCase):
    def test_result_delegates_score_to_contract(self):
        state = starting_state(stage(floors=1, timers=(10.0,)))
        state['pokos'] = 3
        tick(state, 4.0)
        check_end(state, state['population'], gave_up=True)
        outcome = result(state)
        self.assertEqual(outcome['score'],
                         compute_score(3, int(state['time_left']), state['population']))
        self.assertEqual(outcome['result_kind'], RESULT_ORDINARY)

    def test_deathless_boundary(self):
        state = starting_state(stage(floors=1, timers=(10.0,)))
        tick(state, 10.0)
        self.assertTrue(result(state, deathless=True)['deathless'])
        self.assertEqual(result(state, deathless=True)['result_kind'], RESULT_DEATHLESS)

    def test_deathless_false_on_captain_down(self):
        state = starting_state(stage())
        check_end(state, 3, captain_dead=True)
        self.assertFalse(result(state, deathless=True)['deathless'])

    def test_result_before_end_rejected(self):
        with self.assertRaises(ModeError):
            result(starting_state(stage()))


class RetryTests(unittest.TestCase):
    def test_retry_resets_attempt_local(self):
        state = starting_state(stage())
        tick(state, 50.0)
        state['pokos'] = 7
        state['end_state'] = END_TIMEOUT
        fresh = retry(state)
        self.assertEqual(fresh['time_left'], 130.0)
        self.assertEqual(fresh['floor_index'], 0)
        self.assertEqual(fresh['pokos'], 0)
        self.assertIsNone(fresh['end_state'])

    def test_retry_preserves_persistent(self):
        state = starting_state(stage())
        state['persistent']['high_score'] = 999
        state['persistent']['cleared'] = True
        fresh = retry(state)
        self.assertEqual(fresh['persistent']['high_score'], 999)
        self.assertTrue(fresh['persistent']['cleared'])


class UnsupportedTests(unittest.TestCase):
    def test_unsupported_semantics_explicit(self):
        described = unsupported_semantics()
        self.assertEqual(sorted(described), sorted(UNSUPPORTED))
        for name, text in described.items():
            self.assertIn('unsupported', text)


if __name__ == '__main__':
    unittest.main()