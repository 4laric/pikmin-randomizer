"""Focused tests for the two-captain controller pin audit (#819).

No runtime, no native reads: validates the finding-record schema against the
shipped FINDINGS table (found, absent) plus fail-closed malformed and
missing-input refusal.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experimental.pikmin2_two_captain_controller_pin_audit import (
    FILES,
    FINDINGS,
    NATIVE_PIN,
    Refused,
    summarize,
    validate_all,
    validate_finding,
)


def good_found():
    return {
        "id": "x",
        "status": "FOUND",
        "file": "native/src/plugPikiKando/naviMgr.cpp",
        "lines": [65, 70],
        "symbol": "NaviMgr::createObject",
        "detail": "indexed instantiation",
    }


class SchemaTests(unittest.TestCase):
    def test_shipped_findings_validate(self):
        self.assertEqual(len(validate_all(FINDINGS)), 9)

    def test_summary_counts(self):
        s = summarize(FINDINGS)
        self.assertEqual((s["found"], s["absent"], s["total"]), (8, 1, 9))

    def test_expected_ids_present(self):
        ids = {r["id"] for r in FINDINGS}
        for want in ("second-captain-instantiation",
                     "second-shape-object-missing",
                     "second-captain-selection",
                     "per-navi-controller-binding",
                     "per-pad-routing",
                     "global-keydown-port0-only",
                     "squad-ownership-split",
                     "versus-never-spawns-second-navi",
                     "second-navi-spawn-owner"):
            self.assertIn(want, ids)

    def test_pin_and_files_wellformed(self):
        self.assertRegex(NATIVE_PIN, r"^[0-9a-f]{40}$")
        self.assertEqual(len(FILES), 4)
        for blob in FILES.values():
            self.assertRegex(blob, r"^[0-9a-f]{40}$")


class RefusalTests(unittest.TestCase):
    def test_absent_ok(self):
        r = dict(good_found(), status="ABSENT")
        r.pop("lines", None)
        self.assertEqual(validate_finding(r)["status"], "ABSENT")

    def test_non_mapping_refused(self):
        with self.assertRaises(Refused):
            validate_finding(["not", "a", "dict"])

    def test_missing_field_refused(self):
        r = good_found()
        del r["symbol"]
        with self.assertRaises(Refused):
            validate_finding(r)

    def test_bad_status_refused(self):
        with self.assertRaises(Refused):
            validate_finding(dict(good_found(), status="MAYBE"))

    def test_bad_lines_refused(self):
        with self.assertRaises(Refused):
            validate_finding(dict(good_found(), lines=[70, 65]))
        with self.assertRaises(Refused):
            validate_finding(dict(good_found(), lines="65-70"))

    def test_empty_list_refused(self):
        with self.assertRaises(Refused):
            validate_all([])

    def test_duplicate_id_refused(self):
        with self.assertRaises(Refused):
            validate_all([good_found(), good_found()])

    def test_missing_input_refused(self):
        with self.assertRaises(Refused):
            validate_all(None)


if __name__ == "__main__":
    unittest.main()
