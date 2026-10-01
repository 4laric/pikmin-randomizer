"""Focused tests for the #732 call-site evidence (no runtime here)."""
import os
import unittest

from experimental.pikmin2_bomb_birth_hook_callsite import (
    ENGINE_EXE_SHA256,
    FIXTURE_EXE_SHA256,
    FORBIDDEN,
    GUARD_SHA256,
    HOOK_LOG_SHA256,
    MARKERS,
    NATIVE_BASE,
    NATIVE_COMMITS,
    digest,
    read_log_text,
    verify_hook_log,
)

OUT = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
       "prerequisites/bomb-birth-hook-callsite-native")
HOOK_LOG = OUT + "/run-732/callsite0/hook.log"


class EvidenceTests(unittest.TestCase):
    def test_native_pins_are_full_hashes(self):
        self.assertRegex(NATIVE_BASE, r"^[0-9a-f]{40}$")
        for commit in NATIVE_COMMITS:
            self.assertRegex(commit, r"^[0-9a-f]{40}$")

    def test_hashes_are_sha256(self):
        for value in (ENGINE_EXE_SHA256, FIXTURE_EXE_SHA256,
                      HOOK_LOG_SHA256, GUARD_SHA256):
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_hook_log_hash_matches(self):
        self.assertTrue(os.path.exists(HOOK_LOG))
        self.assertEqual(digest(HOOK_LOG), HOOK_LOG_SHA256)

    def test_hook_log_proof_chain(self):
        counts = verify_hook_log(HOOK_LOG)
        for marker in MARKERS:
            self.assertGreaterEqual(counts[marker], 1, marker)

    def test_hook_log_has_no_forbidden_markers(self):
        text = read_log_text(HOOK_LOG)
        for bad in FORBIDDEN:
            self.assertNotIn(bad, text)


class NegativeTests(unittest.TestCase):
    def test_missing_marker_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("P2_BOMB_CALLSITE_SETUP ready=1\n")
            name = fh.name
        try:
            with self.assertRaises(ValueError):
                verify_hook_log(name)
        finally:
            os.unlink(name)

    def test_captain_down_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            for marker in MARKERS:
                fh.write(marker + "\n")
            fh.write("P2_FIXTURE_CAPTAIN_DOWN tick=9\n")
            name = fh.name
        try:
            with self.assertRaises(ValueError):
                verify_hook_log(name)
        finally:
            os.unlink(name)


if __name__ == "__main__":
    unittest.main()
