"""Focused tests for the #793 probe evidence (no runtime here)."""
import os
import unittest

from experimental.pikmin2_kusachi_extinction_probe import (
    ENGINE_EXE_SHA256,
    FIXTURE_EXE_SHA256,
    FORBIDDEN,
    GUARD_SHA256,
    NATIVE_BASE,
    NATIVE_COMMITS,
    PROBE_LOG_SHA256,
    digest,
    parse_probe_line,
    read_log_text,
    verify_probe_log,
)

PROBE_LOG = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
             "prerequisites/kusachi-extinction-probe-native/run-793/"
             "probe0/probe.log")


class EvidenceTests(unittest.TestCase):
    def test_native_pins_are_full_hashes(self):
        self.assertRegex(NATIVE_BASE, r"^[0-9a-f]{40}$")
        for commit in NATIVE_COMMITS:
            self.assertRegex(commit, r"^[0-9a-f]{40}$")

    def test_hashes_are_sha256(self):
        for value in (ENGINE_EXE_SHA256, FIXTURE_EXE_SHA256,
                      GUARD_SHA256, PROBE_LOG_SHA256):
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_probe_log_hash_matches(self):
        self.assertTrue(os.path.exists(PROBE_LOG))
        self.assertEqual(digest(PROBE_LOG), PROBE_LOG_SHA256)

    def test_probe_stream_parses_and_passes(self):
        rows = verify_probe_log(PROBE_LOG)
        self.assertGreaterEqual(len(rows), 600)
        self.assertTrue(any(r["navimgr"] == "0" for r in rows),
                        "manager-loss ticks expected early")
        self.assertTrue(any(int(r["alive"]) > 0 for r in rows),
                        "live squad ticks expected")

    def test_no_forbidden_markers(self):
        text = read_log_text(PROBE_LOG)
        for bad in FORBIDDEN:
            self.assertNotIn(bad, text)


class NegativeTests(unittest.TestCase):
    def test_malformed_line_refused(self):
        with self.assertRaises(ValueError):
            parse_probe_line("P2_KUSACHI_PROBE tick=1 alive=2")

    def test_slots_mismatch_refused(self):
        with self.assertRaises(ValueError):
            parse_probe_line("P2_KUSACHI_PROBE tick=9 navimgr=1 navi=1 "
                             "navi_alive=1 orima_dead=0 alive=2 reds=2 "
                             "slots=10")

    def test_short_stream_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("P2_CHALLENGE_MODE_BOOT\n"
                     "P2_KUSACHI_PROBE tick=1 navimgr=1 navi=1 navi_alive=1 "
                     "orima_dead=0 alive=1 reds=1 slots=1\n"
                     "PASS KUSACHI_PROBE\n")
            name = fh.name
        try:
            with self.assertRaises(ValueError):
                verify_probe_log(name, minimum_ticks=600)
        finally:
            os.unlink(name)


if __name__ == "__main__":
    unittest.main()
