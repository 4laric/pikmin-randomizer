"""Transition/replay fixtures for the surface session contract (#132).

Positive fixtures drive legal day/sunset/save/reload/receipt/cave chains;
negative fixtures prove monotonicity, exactly-once, gating and unsupported
rejections. Pure state dicts only: no engine, no saves, no gameplay claim.
"""
import unittest

from experimental.pikmin2_surface_session_contract import (
    SessionContractError,
    blank_session,
    check_transition,
    request_integration,
    wake_criteria,
)


def run_chain(course="last"):
    state = blank_session(course)
    log = []
    for event in ({"type": "sunset", "time_of_day": 0.9},
                  {"type": "save"},
                  {"type": "deliver_receipt", "identity": "treasure:citrus",
                   "slot": "g7", "pokos": 180},
                  {"type": "begin_day", "day": 2}):
        ok, state, reason = check_transition(state, event)
        log.append((ok, reason))
        assert ok, reason
    return state, log


class SessionContractTests(unittest.TestCase):
    def test_full_day_chain_positive(self):
        state, log = run_chain()
        self.assertEqual(state["day"], 2)
        self.assertFalse(state["day_ended"])
        self.assertEqual(state["pokos"], 180)
        self.assertEqual(len(state["receipts"]), 1)
        self.assertTrue(all(ok for ok, _ in log))

    def test_save_reload_roundtrip_preserves_state(self):
        state, _ = run_chain()
        ok, saved, _ = check_transition(dict(state), {"type": "sunset"})
        self.assertTrue(ok)
        ok, saved, _ = check_transition(saved, {"type": "save"})
        self.assertTrue(ok)
        saved["pokos"] = 9999
        ok, restored, reason = check_transition(saved, {"type": "reload"})
        self.assertTrue(ok, reason)
        self.assertEqual(restored["pokos"], 180)
        self.assertEqual(restored["day"], 2)

    def test_duplicate_receipt_rejected(self):
        state = blank_session()
        ok, state, _ = check_transition(state, {"type": "deliver_receipt",
                                                "identity": "a", "slot": "g1"})
        self.assertTrue(ok)
        ok, _, reason = check_transition(state, {"type": "deliver_receipt",
                                                 "identity": "a", "slot": "g1"})
        self.assertFalse(ok)
        self.assertIn("exactly-once", reason)

    def test_day_rewind_and_double_sunset_rejected(self):
        state = blank_session(day=3)
        ok, _, reason = check_transition(state, {"type": "begin_day", "day": 2})
        self.assertFalse(ok)
        self.assertIn("monotonic", reason)
        ok, state, _ = check_transition(state, {"type": "sunset"})
        self.assertTrue(ok)
        ok, _, reason = check_transition(state, {"type": "sunset"})
        self.assertFalse(ok)
        self.assertIn("double day-end", reason)

    def test_save_before_sunset_and_reload_without_save_rejected(self):
        state = blank_session()
        ok, _, reason = check_transition(state, {"type": "save"})
        self.assertFalse(ok)
        self.assertIn("sunset", reason)
        ok, _, reason = check_transition(state, {"type": "reload"})
        self.assertFalse(ok)
        self.assertIn("no saved snapshot", reason)

    def test_reload_course_mismatch_rejected(self):
        state, _ = run_chain()
        ok, state, _ = check_transition(state, {"type": "sunset"})
        ok, state, _ = check_transition(state, {"type": "save"})
        state["course"] = "forest"
        ok, _, reason = check_transition(state, {"type": "reload"})
        self.assertFalse(ok)
        self.assertIn("mismatch", reason)

    def test_cave_enter_exit_gating(self):
        state = blank_session()
        ok, _, _ = check_transition(state, {"type": "exit_cave"})
        self.assertFalse(ok)
        ok, state, _ = check_transition(state, {"type": "enter_cave",
                                                "cave_id": "last_1", "floor": 2})
        self.assertTrue(ok)
        self.assertEqual((state["in_cave"], state["cave_floor"]), (True, 2))
        ok, _, _ = check_transition(state, {"type": "enter_cave", "cave_id": "x"})
        self.assertFalse(ok)
        ok, state, _ = check_transition(state, {"type": "exit_cave", "cave_pokos": 100})
        self.assertTrue(ok)
        self.assertEqual((state["in_cave"], state["cave_pokos"]), (False, 100))

    def test_malformed_state_event_and_unknown_types(self):
        with self.assertRaises(SessionContractError):
            check_transition({"schema": "wrong"}, {"type": "sunset"})
        with self.assertRaises(SessionContractError):
            check_transition(blank_session(), {"no_type": 1})
        with self.assertRaises(SessionContractError):
            blank_session(course="")
        with self.assertRaises(SessionContractError):
            blank_session(day=0)
        ok, _, reason = check_transition(blank_session(), {"type": "rewind_time"})
        self.assertFalse(ok)
        self.assertIn("unsupported event", reason)
        ok, _, reason = check_transition(blank_session(), {"type": "deliver_receipt"})
        self.assertFalse(ok)

    def test_negative_pokos_rejected(self):
        ok, _, reason = check_transition(blank_session(), {"type": "deliver_receipt",
                                                           "identity": "a", "slot": "g1",
                                                           "pokos": -5})
        self.assertFalse(ok)
        self.assertIn("non-negative", reason)

    def test_missing_integration_always_rejected(self):
        for name in ("native sunset driver", "native save serializer",
                     "native receipt ledger endpoint", "native generator-cache restore"):
            ok, _, reason = request_integration(name)
            self.assertFalse(ok)
            self.assertIn("missing native integration", reason)
        ok, _, _ = request_integration("teleport")
        self.assertFalse(ok)

    def test_wake_criteria_all_false(self):
        for course in ("tutorial", "forest", "yakushima", "last"):
            criteria = wake_criteria(course)
            self.assertFalse(criteria["ready"])
            self.assertFalse(any((criteria["course_record_decoded"],
                                  criteria["cave_entrances_known"],
                                  criteria["receipt_endpoints_admitted"])))
        with self.assertRaises(SessionContractError):
            wake_criteria("nowhere")


if __name__ == "__main__":
    unittest.main()
