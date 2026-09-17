"""Focused guard-verifier tests: adoption, negatives, fail-closed (#731)."""
import json
import unittest
from pathlib import Path

import experimental.pikmin2_captain_guard_verify as guard


GOOD_SOURCE = """#include "scripts/p2_fixture_captain_guard.h"
int idle() {
    p2_fixture_require_captain(GameStat::orimaDead, !n->isAlive(), n->mHealth, observed);
    ++observed;
    return result;
}
"""

INLINE_SOURCE = """inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void burner(bool a, bool b, float c, int t) {
    if (!p2_fixture_captain_down(a, b, c)) return;
    std::puts("P2_FIXTURE_CAPTAIN_DOWN"); std::fflush(nullptr); std::_Exit(86);
}
int idle() {
    p2_fixture_require_captain(GameStat::orimaDead, !n->isAlive(), n->mHealth, observed);
    return result;
}
"""

CLEAN_LOG = "Booted 960x540\nPASS TUTORIAL1_P1\n"
DOWN_LOG = ("Booted\nP2_FIXTURE_CAPTAIN_DOWN tick=1273 hp=0.000 orima_dead=0 "
            "dead_state=1 outcome=BLOCKED\n")
DOWN_PASS_LOG = DOWN_LOG + "PASS TUTORIAL1_P1\n"
NAN_LOG = ("Booted\nP2_FIXTURE_CAPTAIN_DOWN tick=5 hp=nan orima_dead=0 "
           "dead_state=0 outcome=BLOCKED\n")


class SourceTests(unittest.TestCase):
    def test_header_plus_require_is_clean(self):
        self.assertEqual(guard.source_checks(GOOD_SOURCE), [])

    def test_inline_equivalent_labelled_not_clean(self):
        problems = guard.source_checks(INLINE_SOURCE)
        self.assertTrue(any("inline equivalent" in p for p in problems))
        self.assertFalse(any("missing p2_fixture_require_captain" in p for p in problems))

    def test_unguarded_fixture_fails(self):
        problems = guard.source_checks("int idle() { ++observed; return result; }\n")
        self.assertTrue(any("not included" in p for p in problems))
        self.assertTrue(any("missing p2_fixture_require_captain" in p for p in problems))

    def test_missing_require_call_fails(self):
        src = '#include "scripts/p2_fixture_captain_guard.h"\nint idle() { return 0; }\n'
        self.assertTrue(any("missing p2_fixture_require_captain" in p
                            for p in guard.source_checks(src)))

    def test_non_text_fails_closed(self):
        with self.assertRaises(guard.VerifyGapError):
            guard.source_checks(None)


class LogTests(unittest.TestCase):
    def test_clean_run(self):
        result = guard.log_checks(CLEAN_LOG, 0)
        self.assertEqual(result["problems"], [])
        self.assertEqual(result["passes"], ["TUTORIAL1_P1"])

    def test_captain_down_blocks(self):
        result = guard.log_checks(DOWN_LOG, 86)
        self.assertEqual(result["problems"], [])
        self.assertEqual(len(result["captain_down_events"]), 1)

    def test_down_with_zero_exit_fails(self):
        self.assertTrue(guard.log_checks(DOWN_LOG, 0)["problems"])

    def test_down_with_pass_fails(self):
        result = guard.log_checks(DOWN_PASS_LOG, 86)
        self.assertTrue(any("still claims PASS" in p for p in result["problems"]))

    def test_nan_hp_is_down(self):
        event = guard.parse_captain_down(NAN_LOG.splitlines()[1])
        self.assertTrue(event["down"])
        self.assertTrue(math_isnan(event["hp"]))

    def test_unknown_grammar_fails_closed(self):
        with self.assertRaises(guard.VerifyGapError):
            guard.parse_captain_down("P2_FIXTURE_CAPTAIN_DOWN gibberish here")

    def test_bad_exit_fails_closed(self):
        with self.assertRaises(guard.VerifyGapError):
            guard.log_checks(CLEAN_LOG, "0")


def math_isnan(value):
    import math
    return math.isnan(value)


class AdoptionTests(unittest.TestCase):
    def test_unprotected_with_evidence(self):
        adoption = {"policy": "unprotected", "evidence": ["guard_source", "runlog"]}
        evidence = {"guard_source": {"sha256": "x"}, "runlog": {"sha256": "y"}}
        self.assertEqual(guard.verify_adoption(adoption, evidence), [])

    def test_protected_claiming_damage_fails(self):
        adoption = {"policy": "protected_observation", "evidence": ["runlog"]}
        evidence = {"runlog": {"sha256": "y"}}
        gates = {"attacks_receivers": {"status": "PASS"}}
        problems = guard.verify_adoption(adoption, evidence, gates)
        self.assertTrue(any("cannot yield" in p for p in problems))

    def test_missing_evidence_key_fails(self):
        adoption = {"policy": "unprotected", "evidence": ["nope"]}
        self.assertTrue(guard.verify_adoption(adoption, {"runlog": {}}))

    def test_unknown_policy_fails(self):
        self.assertTrue(guard.verify_adoption({"policy": "invincible", "evidence": ["a"]},
                                              {"a": {}}))

    def test_full_verdict(self):
        verdict = guard.verify_fixture(
            GOOD_SOURCE, CLEAN_LOG, 0,
            {"policy": "unprotected", "evidence": ["runlog"]},
            {"runlog": {"sha256": "y"}})
        self.assertTrue(verdict["ok"])
        bad = guard.verify_fixture(GOOD_SOURCE, DOWN_PASS_LOG, 86)
        self.assertFalse(bad["ok"])


class BoundaryTests(unittest.TestCase):
    def test_cli_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "fx.cpp"
            src.write_text(GOOD_SOURCE, encoding="utf-8")
            log = Path(tmp) / "run.log"
            log.write_text(CLEAN_LOG, encoding="utf-8")
            out = Path(tmp) / "verdict.json"
            self.assertEqual(guard.main(["--source", str(src), "--log", str(log),
                                         "--exit-code", "0",
                                         "--out", str(out)]), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()