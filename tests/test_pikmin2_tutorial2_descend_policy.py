"""Focused tests for the #757 descend-policy evidence (no runtime here)."""
import os
import unittest

from experimental.pikmin2_tutorial2_descend_policy import (
    BOOT_LOGS,
    ENGINE_EXE_SHA256,
    ENTRY_VERSION,
    FIXTURE_EXE_SHA256,
    FLOORS,
    FORBIDDEN,
    GUARD_SHA256,
    NATIVE_BASE,
    NATIVE_COMMITS,
    SQUAD_COUNT,
    digest,
    read_log_text,
    verify_boot_log,
)

OUT = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
       "prerequisites/tutorial2-descend-policy-native/run-757")


def log_path(floor):
    return OUT + "/run-floor%d/boot.log" % floor


class EvidenceTests(unittest.TestCase):
    def test_native_pins_are_full_hashes(self):
        self.assertRegex(NATIVE_BASE, r"^[0-9a-f]{40}$")
        for commit in NATIVE_COMMITS:
            self.assertRegex(commit, r"^[0-9a-f]{40}$")

    def test_hashes_are_sha256(self):
        for value in (list(BOOT_LOGS.values()) + [ENGINE_EXE_SHA256,
                                                  FIXTURE_EXE_SHA256,
                                                  GUARD_SHA256]):
            for item in (value if isinstance(value, list) else [value]):
                self.assertRegex(item, r"^[0-9a-f]{64}$")

    def test_boot_log_hashes_match(self):
        for floor in FLOORS:
            self.assertTrue(os.path.exists(log_path(floor)))
            self.assertEqual(digest(log_path(floor)), BOOT_LOGS[floor],
                             "floor %d log hash" % floor)

    def test_all_floors_boot_with_policy(self):
        for floor in FLOORS:
            flag = verify_boot_log(log_path(floor), floor)
            self.assertEqual(flag, "1" if floor <= 7 else "0",
                             "floor %d descend flag" % floor)

    def test_no_forbidden_markers(self):
        for floor in FLOORS:
            text = read_log_text(log_path(floor))
            for bad in FORBIDDEN:
                self.assertNotIn(bad, text)


class ContractTests(unittest.TestCase):
    def test_entry_version_and_squad(self):
        self.assertEqual(ENTRY_VERSION, "P2_CAVE_ENTRY_4")
        self.assertEqual(FLOORS, (3, 4, 5, 6, 7, 8))
        self.assertEqual(SQUAD_COUNT, 8)

    def test_missing_ready_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("P2_CAVE_SETUP_PROBE room_preview=1\n")
            name = fh.name
        try:
            with self.assertRaises(ValueError):
                verify_boot_log(name, 3)
        finally:
            os.unlink(name)

    def test_wrong_descend_flag_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("P2_CAVE_READY floor=8 survivors=8\n"
                     "P2_TUTORIAL2_DESCEND_POLICY floor=8 descend=1\n"
                     "PASS TUTORIAL2_DESCEND\n")
            name = fh.name
        try:
            with self.assertRaises(ValueError):
                verify_boot_log(name, 8)
        finally:
            os.unlink(name)


if __name__ == "__main__":
    unittest.main()
