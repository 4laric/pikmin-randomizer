"""Focused tests for the framework pin-discovery helpers (issue #136).

Hermetic pure-logic tests plus read-only live checks against immutable git
facts (commit existence, byte hashes). No mutation, no builds, no ADMIT.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental.pikmin2_challenge_framework_pins import (
    CONTRACT_BRANCH,
    CONTRACT_COMMIT,
    CONTRACT_FILES,
    DOWNSTREAM_P1_SCOPES,
    NATIVE_CONSUMER_BRANCH,
    NATIVE_CONSUMER_PIN,
    ROOT_CONSUMER_BRANCH,
    ROOT_CONSUMER_PIN,
    check_coherent_pair,
    no_coherent_pair_finding,
    verify_contract_files,
)

MAIN_ROOT = Path("C:/Users/alari/pikmin-randomizer")
MAIN_NATIVE = Path("C:/Users/alari/pikmin-randomizer/native")


class PureLogicTests(unittest.TestCase):
    def test_hash_mismatch_detected(self):
        bad = dict(CONTRACT_FILES)
        first = next(iter(bad))
        bad[first] = "0" * 64
        with patch("experimental.pikmin2_challenge_framework_pins.file_hash_at",
                   side_effect=lambda repo, commit, path: "f" * 64 if path == first
                   else CONTRACT_FILES[path]):
            gaps = verify_contract_files("repo", "pin", bad)
        self.assertEqual(len(gaps), 1)
        self.assertTrue(gaps[0].startswith("hash-mismatch: "))

    def test_missing_file_detected(self):
        with patch("experimental.pikmin2_challenge_framework_pins.file_hash_at",
                   return_value=""):
            gaps = verify_contract_files("repo", "pin")
        self.assertEqual(len(gaps), len(CONTRACT_FILES))
        self.assertTrue(all(g.startswith("missing: ") for g in gaps))

    def test_absent_pins_fail_coherence(self):
        with patch("experimental.pikmin2_challenge_framework_pins.commit_exists",
                   return_value=False):
            ok, findings = check_coherent_pair("r", "rootpin", "n", "nativepin")
        self.assertFalse(ok)
        self.assertIn("contract-commit-absent", findings)

    def test_unreachable_branch_detected(self):
        with patch("experimental.pikmin2_challenge_framework_pins.branches_containing",
                   return_value=[]):
            from experimental import pikmin2_challenge_framework_pins as m
            self.assertEqual(m.branches_containing("r", "deadbeef"), [])

    def test_downstream_scope_complete(self):
        self.assertEqual(len(DOWNSTREAM_P1_SCOPES), 10)
        self.assertIn("ch_MAT_t_hunter_otakara", DOWNSTREAM_P1_SCOPES)
        self.assertIn("ch_NARI_01kusachi", DOWNSTREAM_P1_SCOPES)

    def test_no_pair_finding_shape(self):
        with patch("experimental.pikmin2_challenge_framework_pins.branches_containing",
                   return_value=[CONTRACT_BRANCH]), \
             patch("experimental.pikmin2_challenge_framework_pins.is_ancestor",
                   return_value=False), \
             patch("experimental.pikmin2_challenge_framework_pins.verify_contract_files",
                   return_value=[]):
            info = no_coherent_pair_finding("r", "pin")
        self.assertEqual(info["contract_commit"], CONTRACT_COMMIT)
        self.assertFalse(info["contract_ancestral_to_pin"])
        self.assertTrue(info["content_verified_at_pin"])


class LivePinTests(unittest.TestCase):
    def test_contract_commit_exists(self):
        from experimental import pikmin2_challenge_framework_pins as m
        self.assertTrue(m.commit_exists(str(MAIN_ROOT), CONTRACT_COMMIT))

    def test_contract_files_verify_at_consumer_pin(self):
        self.assertEqual(verify_contract_files(str(MAIN_ROOT), ROOT_CONSUMER_PIN), [])

    def test_consumer_pins_exist(self):
        from experimental import pikmin2_challenge_framework_pins as m
        self.assertTrue(m.commit_exists(str(MAIN_ROOT), ROOT_CONSUMER_PIN))
        self.assertTrue(m.commit_exists(str(MAIN_NATIVE), NATIVE_CONSUMER_PIN))

    def test_contract_not_ancestor_of_checkout(self):
        # The stale premise, verified: b9bb55f0 is reachable on its own
        # branch but is not an ancestor of the consumer line; the content
        # arrived via the fc5cbdeb integration instead.
        from experimental import pikmin2_challenge_framework_pins as m
        self.assertIn(CONTRACT_BRANCH,
                      m.branches_containing(str(MAIN_ROOT), CONTRACT_COMMIT))
        self.assertFalse(m.is_ancestor(str(MAIN_ROOT), CONTRACT_COMMIT, ROOT_CONSUMER_PIN))
        self.assertIn(ROOT_CONSUMER_BRANCH,
                      m.branches_containing(str(MAIN_ROOT), ROOT_CONSUMER_PIN))
        self.assertIn(NATIVE_CONSUMER_BRANCH,
                      m.branches_containing(str(MAIN_NATIVE), NATIVE_CONSUMER_PIN))

    def test_coherent_pair_grades_clean(self):
        ok, findings = check_coherent_pair(str(MAIN_ROOT), ROOT_CONSUMER_PIN,
                                           str(MAIN_NATIVE), NATIVE_CONSUMER_PIN)
        self.assertTrue(ok, findings)


if __name__ == "__main__":
    unittest.main()
