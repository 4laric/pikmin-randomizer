"""Focused tests for the overworld save/progression boundary contract (#132).

All fixtures are synthetic inventory/snapshot/ledger inputs exercising the
adapter boundary: malformed and missing inputs, unknown/duplicate areas,
snapshot schema, ledger envelope, event prefixes and the published unsupported
references. No value here is claimed as retail fact.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "experimental" / "content_lanes" / "p2-overworld-save-progression.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("p2_overworld_save_progression", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def good_inventory(**over):
    rows = [
        {"id": "tutorial", "name": "Valley of Repose", "issue": 148,
         "source": "user/Abe/stages.txt"},
        {"id": "forest", "name": "Awakening Wood", "issue": 149,
         "source": "user/Abe/stages.txt"},
        {"id": "yakushima", "name": "Perplexing Pool", "issue": 150,
         "source": "user/Abe/stages.txt"},
        {"id": "last", "name": "Wistful Wild", "issue": 151,
         "source": "user/Abe/stages.txt"},
    ]
    data = {"surfaces": rows}
    data.update(over)
    return data


def good_snapshot(**over):
    snap = {"region": "forest", "day": 3, "time": 12.5,
            "position": [10.0, 0.0, -4.0], "squad": [], "health": [],
            "receipts": {}}
    snap.update(over)
    return snap


def good_ledger(snapshot=None):
    snap = snapshot or good_snapshot()
    return {"schema": 1, "campaign": "a" * 32, "content": "b" * 64,
            "origin": "c" * 64, "revision": 0, "phase": "surface",
            "surface": snap, "trip": None, "events": {}}


class BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def write(self, tmp, name, data):
        path = Path(tmp) / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_inventory_loads_all_four(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = self.mod.load_inventory(self.write(tmp, "inv.json", good_inventory()))
        self.assertEqual(sorted(reg), ["forest", "last", "tutorial", "yakushima"])
        self.assertEqual(reg["last"]["issue"], 151)

    def test_missing_inventory_rejected(self):
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.load_inventory("/nonexistent/inventory.json")

    def test_malformed_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inv.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(self.mod.BoundaryError):
                self.mod.load_inventory(str(path))

    def test_wrong_surface_count_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = good_inventory()
            data["surfaces"] = data["surfaces"][:3]
            with self.assertRaises(self.mod.BoundaryError):
                self.mod.load_inventory(self.write(tmp, "inv.json", data))

    def test_unknown_area_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = good_inventory()
            data["surfaces"][0]["id"] = "atlantis"
            with self.assertRaises(self.mod.BoundaryError):
                self.mod.load_inventory(self.write(tmp, "inv.json", data))

    def test_issue_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = good_inventory()
            data["surfaces"][1]["issue"] = 999
            with self.assertRaises(self.mod.BoundaryError):
                self.mod.load_inventory(self.write(tmp, "inv.json", data))

    def test_unexpected_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = good_inventory()
            data["surfaces"][2]["source"] = "user/Other/stages.txt"
            with self.assertRaises(self.mod.BoundaryError):
                self.mod.load_inventory(self.write(tmp, "inv.json", data))

    def test_malformed_row_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = good_inventory()
            data["surfaces"][3] = {"id": "last", "name": "Wistful Wild"}
            with self.assertRaises(self.mod.BoundaryError):
                self.mod.load_inventory(self.write(tmp, "inv.json", data))

    def test_snapshot_valid(self):
        self.assertEqual(self.mod.validate_snapshot(good_snapshot())["region"], "forest")

    def test_snapshot_missing_field_rejected(self):
        snap = good_snapshot()
        del snap["day"]
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_snapshot(snap)

    def test_snapshot_bad_region_rejected(self):
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_snapshot(good_snapshot(region="Forest!"))
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_snapshot(good_snapshot(region=""))

    def test_snapshot_bad_day_and_time_rejected(self):
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_snapshot(good_snapshot(day=0))
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_snapshot(good_snapshot(time=25))

    def test_snapshot_bad_position_rejected(self):
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_snapshot(good_snapshot(position=[1.0, 2.0]))
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_snapshot(good_snapshot(position=[1.0, 2.0, 1e9]))

    def test_ledger_envelope_valid(self):
        self.assertEqual(self.mod.validate_ledger_envelope(good_ledger())["phase"], "surface")

    def test_ledger_bad_phase_rejected(self):
        state = good_ledger()
        state["phase"] = "napping"
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_ledger_envelope(state)

    def test_ledger_revision_mismatch_rejected(self):
        state = good_ledger()
        state["revision"] = 3
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_ledger_envelope(state)

    def test_ledger_bad_event_rejected(self):
        state = good_ledger()
        state["events"] = {"journey:" + "a" * 32: "b" * 64}
        state["revision"] = 1
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_ledger_envelope(state)

    def test_ledger_bad_identity_rejected(self):
        state = good_ledger()
        state["campaign"] = "short"
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.validate_ledger_envelope(state)

    def test_audit_area_requires_known_area(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = self.mod.load_inventory(self.write(tmp, "inv.json", good_inventory()))
        report = self.mod.audit_area("forest", reg, good_snapshot(), good_ledger())
        self.assertEqual(report["snapshot"], "valid")
        self.assertEqual(report["ledger"], "valid")
        with self.assertRaises(self.mod.BoundaryError):
            self.mod.audit_area("atlantis", reg)

    def test_contract_publishes_covered_and_unsupported(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract = self.mod.boundary_contract(
                self.write(tmp, "inv.json", good_inventory()))
        self.assertEqual(len(contract["areas"]), 4)
        self.assertIn("experimental/pikmin2_surface_ledger.py", contract["covered_modules"])
        unsupported = contract["unsupported"]
        self.assertEqual(sorted(unsupported["native_integration_items"]),
                         ["generator_cache_restore", "receipt_ledger_endpoint",
                          "save_serializer", "sunset_driver"])
        self.assertEqual(unsupported["native_pin_provenance"],
                         "shard-overworld-last-save-session-pin-discovery (#658)")
        self.assertIn("user/Abe/stages.txt", unsupported["missing_local_disc_tables"])

    def test_real_inventory_at_root(self):
        # The committed inventory is the real decoded table registry.
        contract = self.mod.boundary_contract(str(ROOT / "docs" / "PIKMIN2_CONTENT_INVENTORY.json"))
        self.assertEqual([a["area"] for a in contract["areas"]],
                         ["forest", "last", "tutorial", "yakushima"])


if __name__ == "__main__":
    unittest.main()