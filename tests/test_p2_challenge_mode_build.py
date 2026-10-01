"""Focused tests for the #656 challenge host-mode build harness helpers.

Pure-python coverage only: marker parsing, chain validation, exit
classification, evidence schema, guard resolution and the negative TU
source. No native build, ISO, runtime or registry access is required.
"""
import unittest
from pathlib import Path

from scripts.build_p2_challenge_mode_fixture import (
    check_chain,
    evidence_record,
    guard_record,
    interpret_exit,
    negative_source,
    parse_markers,
    resolve_guard,
    validate_evidence,
)

LIVE_LOG = """P2_CHALLENGE_MODE_BOOT cave=ch_MUKI_metal ui_index=1 floor=0 time_left=130.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=180
P2_CHALLENGE_MODE_SQUAD_APPLIED cave=ch_MUKI_metal ui_index=1 floor=0 time_left=130.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=180
P2_CHALLENGE_MODE_TICK cave=ch_MUKI_metal ui_index=1 floor=0 time_left=120.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=170
P2_CHALLENGE_MODE_TICK cave=ch_MUKI_metal ui_index=1 floor=0 time_left=110.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=160
P2_CHALLENGE_MODE_TICK cave=ch_MUKI_metal ui_index=1 floor=0 time_left=100.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=150
P2_CHALLENGE_MODE_FLOOR_ADVANCE cave=ch_MUKI_metal ui_index=1 floor=1 time_left=100.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=150
P2_CHALLENGE_MODE_RETRY_STATE cave=ch_MUKI_metal ui_index=1 floor=0 time_left=130.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=180
P2_CHALLENGE_MODE_RETRY_RESET cave=ch_MUKI_metal ui_index=1 floor=0 time_left=130.000 population=50 pokos=0 bitter=0 spicy=0 end=none score=180
P2_CHALLENGE_MODE_DONE end=none score=150
"""

NEGATIVE_LOG = ("P2_FIXTURE_CAPTAIN_DOWN tick=7 hp=0.000 orima_dead=1 "
                "dead_state=0 outcome=BLOCKED\n")


class MarkerTests(unittest.TestCase):
    def test_parses_challenge_and_guard_markers(self):
        rows = parse_markers(LIVE_LOG + NEGATIVE_LOG)
        kinds = [kind for kind, _ in rows]
        self.assertEqual(kinds[0], "BOOT")
        self.assertIn("TICK", kinds)
        self.assertIn("DONE", kinds)
        self.assertIn("CAPTAIN_DOWN", kinds)

    def test_ignores_unrelated_lines(self):
        self.assertEqual(parse_markers("hello\nninja: no work to do.\n"), [])

    def test_chain_passes_on_ordered_live_log(self):
        ok, detail = check_chain(parse_markers(LIVE_LOG))
        self.assertTrue(ok)
        self.assertIn("x3", detail)

    def test_chain_rejects_missing_done(self):
        rows = [row for row in parse_markers(LIVE_LOG) if row[0] != "DONE"]
        ok, detail = check_chain(rows)
        self.assertFalse(ok)
        self.assertIn("DONE", detail)

    def test_chain_rejects_short_tick_run(self):
        rows = [row for row in parse_markers(LIVE_LOG) if row[0] != "TICK"]
        ok, _ = check_chain(rows)
        self.assertFalse(ok)

    def test_chain_rejects_captain_down(self):
        ok, detail = check_chain(parse_markers(LIVE_LOG + NEGATIVE_LOG))
        self.assertFalse(ok)
        self.assertIn("captain-down", detail)


class ExitTests(unittest.TestCase):
    def test_live_exit_zero_is_pass(self):
        verdict = interpret_exit(0, LIVE_LOG)
        self.assertEqual(verdict["verdict"], "pass")

    def test_guard_exit_86_is_blocked(self):
        verdict = interpret_exit(86, NEGATIVE_LOG)
        self.assertEqual(verdict["verdict"], "blocked")

    def test_exit_86_without_marker_is_fail(self):
        verdict = interpret_exit(86, "silent death\n")
        self.assertEqual(verdict["verdict"], "fail")

    def test_nonzero_exit_is_fail(self):
        verdict = interpret_exit(2, "P2_CHALLENGE_MODE_ERROR missing_stage\n")
        self.assertEqual(verdict["verdict"], "fail")

    def test_incomplete_chain_exit_zero_is_fail(self):
        verdict = interpret_exit(0, "P2_CHALLENGE_MODE_BOOT cave=x\n")
        self.assertEqual(verdict["verdict"], "fail")


class EvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        record = evidence_record(native_head="a" * 40,
                                 exe_sha256="b" * 64,
                                 guard_sha256="c" * 64,
                                 ninja_dry_run="ninja: no work to do.",
                                 chain="pass", exit=0)
        self.assertEqual(validate_evidence(record)["kind"],
                         "p2-challenge-mode-build")

    def test_rejects_missing_keys(self):
        with self.assertRaises(ValueError):
            validate_evidence({"schema": 1})

    def test_rejects_unpassed_chain(self):
        record = evidence_record(native_head="a" * 40,
                                 exe_sha256="b" * 64,
                                 guard_sha256="c" * 64,
                                 ninja_dry_run="ninja: no work to do.",
                                 chain="blocked", exit=86)
        with self.assertRaises(ValueError):
            validate_evidence(record)




CANONICAL_SCRIPTS = Path("C:/Users/alari/pikmin-randomizer/scripts")


class GuardTests(unittest.TestCase):
    def test_resolve_guard_reads_canonical_header(self):
        # The guard lives ONLY in the canonical checkout scripts/ (host-pinned
        # like every other path in this wave); the harness takes --guard-dir
        # explicitly and never copies or edits the header.
        path = resolve_guard(CANONICAL_SCRIPTS)
        self.assertTrue(path.is_file())
        record = guard_record(CANONICAL_SCRIPTS)
        self.assertEqual(len(record["sha256"]), 64)

    def test_resolve_guard_fails_closed(self):
        with self.assertRaises(ValueError):
            resolve_guard(Path("C:/nonexistent-guard-dir-656"))

    def test_negative_source_calls_guard_with_dead_captain(self):
        src = negative_source()
        self.assertIn("p2_fixture_require_captain(true, false, 0.0f, 7)", src)
        self.assertNotIn("PASS", src)


if __name__ == "__main__":
    unittest.main()