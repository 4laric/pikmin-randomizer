"""Focused tests for the Chiyogami89 placement audit (#653 prerequisite)."""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
adapter = importlib.import_module("experimental.pikmin2_chiyogami89_placement_audit")


class PlacementAuditTest(unittest.TestCase):
    def test_row_validates_clean(self):
        row = adapter.audit_row()
        self.assertEqual(adapter.validate_audit(row), [])
        self.assertEqual(row["source_id"], 89)
        self.assertEqual(row["classification"], "spawnable_plant_actor")

    def test_packet_schema_and_no_runtime_claim(self):
        packet = adapter.build_packet(adapter.audit_row())
        self.assertEqual(packet["schema"], adapter.PACKET_SCHEMA)
        self.assertFalse(packet["runtime_claim"])
        self.assertEqual(packet["placement"]["gen_type"], 6)
        self.assertEqual(packet["placement"]["cave_id"], "yakushima_2")

    def test_packet_sha_stable(self):
        packet = adapter.build_packet(adapter.audit_row())
        self.assertEqual(adapter.packet_sha256(packet), adapter.packet_sha256(packet))
        self.assertEqual(len(adapter.packet_sha256(packet)), 64)

    def test_non_dict_refused(self):
        self.assertEqual(adapter.validate_audit([]), ["row-must-be-dict"])

    def test_bad_schema_refused(self):
        row = adapter.audit_row()
        row["schema"] = "something-else"
        self.assertIn("bad-schema", adapter.validate_audit(row))

    def test_bad_source_id_refused(self):
        row = adapter.audit_row()
        row["source_id"] = 88
        self.assertIn("bad-source-id", adapter.validate_audit(row))

    def test_unknown_classification_refused(self):
        row = adapter.audit_row()
        row["classification"] = "boss"
        self.assertIn("unknown-classification", adapter.validate_audit(row))

    def test_missing_anchor_refused(self):
        row = adapter.audit_row()
        del row["anchors"]["generator_case"]
        self.assertIn("missing-anchor-generator_case", adapter.validate_audit(row))

    def test_bad_anchor_hash_refused(self):
        row = adapter.audit_row()
        row["anchors"]["enum"]["sha256"] = "zzz"
        self.assertIn("bad-anchor-hash-enum", adapter.validate_audit(row))

    def test_missing_placement_field_refused(self):
        row = adapter.audit_row()
        del row["placement"]["weight"]
        self.assertIn("missing-placement-weight", adapter.validate_audit(row))

    def test_non_plant_type_refused(self):
        row = adapter.audit_row()
        row["placement"]["gen_type"] = 0
        self.assertIn("placement-not-plant-type", adapter.validate_audit(row))

    def test_bad_gates_refused(self):
        row = adapter.audit_row()
        row["gates"] = {"identity_spawn": "PASS"}
        self.assertIn("bad-gates", adapter.validate_audit(row))
        row = adapter.audit_row()
        row["gates"]["identity_spawn"] = "MAYBE"
        self.assertIn("bad-gate-identity_spawn", adapter.validate_audit(row))

    def test_empty_blockers_refused(self):
        row = adapter.audit_row()
        row["p1_blockers"] = []
        self.assertIn("bad-blockers", adapter.validate_audit(row))

    def test_build_packet_refuses_invalid(self):
        row = adapter.audit_row()
        row["source_id"] = 1
        with self.assertRaises(ValueError):
            adapter.build_packet(row)

    def test_main_check_passes(self):
        self.assertEqual(adapter.main(["--check"]), 0)

    def test_main_packet_out(self):
        tmp = tempfile.mkdtemp(prefix="chiyogami89-")
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, True))
        out = os.path.join(tmp, "packet.json")
        self.assertEqual(adapter.main(["--packet-out", out]), 0)
        packet = json.load(open(out, encoding="utf-8"))
        self.assertEqual(packet["source_id"], 89)
        self.assertEqual(packet["classification"], "spawnable_plant_actor")

    def test_row_does_not_alias_module_tables(self):
        row = adapter.audit_row()
        row["anchors"]["enum"]["line"] = 1
        row["placement"]["weight"] = 99
        row["p1_blockers"].append("x")
        fresh = adapter.audit_row()
        self.assertEqual(fresh["anchors"]["enum"]["line"], 148)
        self.assertEqual(fresh["placement"]["weight"], 2)
        self.assertEqual(len(fresh["p1_blockers"]), 2)


if __name__ == "__main__":
    unittest.main()