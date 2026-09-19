"""Fail-closed tests for the damagumo stage-table row (#742).

Synthetic row/log fixtures only; no engine, disc, or runtime needed except
the live guard-header pin test, which reads the canonical header read-only.
"""
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "damagumo_stage_table_row",
        ROOT / "experimental" / "pikmin2_damagumo_stage_table_row.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()

GOOD_LOG = """P2_DAMAGUMO_STAGE_GUARD guard_inputs=SIMULATED
P2_DAMAGUMO_STAGE_RESOLVED cave=ch_MUKI_damagumo ui_index=6 floors=1 roster_total=50 bitter=0 spicy=1 legacy=0.0 treasure=0 source=c6f2dede
P2_DAMAGUMO_STAGE_GATES all=UNTESTED content_wired=0
"""


class RowTests(unittest.TestCase):
    def test_expected_row_matches_contract(self):
        row = M.expected_row()
        self.assertEqual(row["cave_id"], "ch_MUKI_damagumo")
        self.assertEqual(row["ui_index"], 6)
        self.assertEqual(row["floors"], 1)
        self.assertEqual(row["floor_seconds"], [150.0])
        self.assertEqual(row["roster"][2], [0, 0, 50])
        self.assertEqual(M.roster_total(), 50)
        self.assertTrue(M.check_row(row))

    def test_row_drift_rejected(self):
        for key, bad in (("ui_index", 7), ("floors", 2),
                         ("source_sha256", "00" * 32),
                         ("roster", [[0, 0, 0]] * 7),
                         ("legacy_time", 450.0)):
            with self.subTest(key=key):
                row = M.expected_row()
                row[key] = bad
                with self.assertRaises(ValueError):
                    M.check_row(row)
        with self.assertRaises(ValueError):
            M.check_row(["not", "a", "mapping"])

    def test_guard_header_pinned(self):
        guard = Path("C:/Users/alari/pikmin-randomizer/scripts/p2_fixture_captain_guard.h")
        digest = hashlib.sha256(guard.read_bytes()).hexdigest()
        self.assertEqual(digest, M.CAPTAIN_GUARD_SHA256)


class LogTests(unittest.TestCase):
    def test_good_log_resolves(self):
        findings = M.validate_log(GOOD_LOG)
        self.assertTrue(findings["resolved"])
        self.assertEqual(findings["cave_id"], "ch_MUKI_damagumo")
        self.assertEqual(findings["roster_total"], 50)
        self.assertTrue(findings["gates_unclaimed"])

    def test_refused_log_unresolved(self):
        findings = M.validate_log("P2_DAMAGUMO_STAGE_REFUSED cave=ch_NARI_01kusachi\n")
        self.assertFalse(findings["resolved"])
        self.assertTrue(findings["refused"])

    def test_empty_log_unresolved(self):
        findings = M.validate_log("")
        self.assertFalse(findings["resolved"])
        self.assertFalse(findings["refused"])

    def test_captain_down_blocked(self):
        with self.assertRaises(ValueError):
            M.validate_log(GOOD_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=0\n")

    def test_wrong_values_not_resolved(self):
        findings = M.validate_log(GOOD_LOG.replace("ui_index=6", "ui_index=7"))
        self.assertFalse(findings["resolved"])


if __name__ == "__main__":
    unittest.main()
