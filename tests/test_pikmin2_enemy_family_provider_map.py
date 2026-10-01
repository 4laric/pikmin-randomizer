"""Focused tests for the enemy family/provider ownership map (#637).

All fixtures are synthetic mutations of the shipped map plus small synthetic
records exercising each validator rule. Real-pin evidence (decomp paths,
inventory counts, overlay gates, lane ownership) lives in
docs/PIKMIN2_ENEMY_FAMILY_PROVIDER_OWNERSHIP.md; no retail bytes are asserted
here beyond the structural rules.
"""
import copy
import importlib.util
import unittest
from pathlib import Path

ADAPTER = (Path(__file__).resolve().parents[1] / "experimental"
           / "pikmin2_enemy_family_provider_map.py")

FIRST_PRIORITY = [14, 22, 39, 47, 80, 89]
ENEMIES3 = [10, 16, 17, 24, 30, 31, 32, 37, 42, 49, 56, 64, 68, 69, 73, 84, 91]


def load_adapter():
    spec = importlib.util.spec_from_file_location("family_provider_map", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def by_id(records, sid):
    return next(r for r in records if r["source_id"] == sid)


class MapValidityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_shipped_map_validates(self):
        self.assertEqual(self.mod.validate_map(), [])

    def test_audit_coverage_complete(self):
        records = self.mod.load_map()
        ids = {r["source_id"] for r in records}
        for sid in FIRST_PRIORITY + ENEMIES3:
            self.assertIn(sid, ids)
        self.assertIn(100, ids)
        self.assertEqual(len(records), len(ids))

    def test_load_returns_deep_copy(self):
        first = self.mod.load_map()
        first[0]["owner_kind"] = "MUTATED"
        self.assertNotEqual(self.mod.load_map()[0]["owner_kind"], "MUTATED")
        self.assertEqual(self.mod.validate_map(), [])

    def test_duplicate_source_id_fails(self):
        records = self.mod.load_map()
        records.append(copy.deepcopy(records[0]))
        errors = self.mod.validate_map(records)
        self.assertTrue(any("duplicate source_id" in e for e in errors))

    def test_alias_with_actor_module_fails(self):
        records = self.mod.load_map()
        nest = by_id(records, 39)
        nest["module_files"].append({"path": "native/pc_port/pc_p2_nest.cpp",
                                     "status": "proposed", "note": "x"})
        errors = self.mod.validate_map(records)
        self.assertTrue(any("must not claim actor module" in e for e in errors))

    def test_info_less_row_with_lane_kind_fails(self):
        records = self.mod.load_map()
        tobi = by_id(records, 14)
        tobi["has_info_row"] = False
        errors = self.mod.validate_map(records)
        self.assertTrue(any("must use kind alias" in e for e in errors))

    def test_nonspawnable_with_lane_kind_fails(self):
        records = self.mod.load_map()
        base = by_id(records, 100)
        base["owner_kind"] = "lane"
        base["owner"] = {"lane": 16, "issues": [167], "note": "x"}
        errors = self.mod.validate_map(records)
        self.assertTrue(any("must use kind nonactor" in e for e in errors))

    def test_dangling_parent_fails(self):
        records = self.mod.load_map()
        records[0]["parent_id"] = 999
        errors = self.mod.validate_map(records)
        self.assertTrue(any("does not resolve" in e for e in errors))

    def test_shared_module_outside_files_fails(self):
        records = self.mod.load_map()
        wealthy = by_id(records, 10)
        wealthy["shared_module"] = "native/pc_port/pc_p2_missing.cpp"
        errors = self.mod.validate_map(records)
        self.assertTrue(any("not in module_files" in e for e in errors))

    def test_unknown_gate_fails(self):
        records = self.mod.load_map()
        by_id(records, 22)["remaining_gates"].append("gate_7_fly")
        errors = self.mod.validate_map(records)
        self.assertTrue(any("unknown gates" in e for e in errors))

    def test_bad_owner_kind_fails(self):
        records = self.mod.load_map()
        by_id(records, 22)["owner_kind"] = "unowned"
        errors = self.mod.validate_map(records)
        self.assertTrue(any("owner_kind" in e for e in errors))

    def test_bad_module_status_fails(self):
        records = self.mod.load_map()
        by_id(records, 22)["module_files"][0]["status"] = "merged"
        errors = self.mod.validate_map(records)
        self.assertTrue(any("module status" in e for e in errors))

    def test_empty_follow_on_files_fails(self):
        records = self.mod.load_map()
        by_id(records, 14)["follow_on"]["files"] = []
        errors = self.mod.validate_map(records)
        self.assertTrue(any("follow_on.files" in e for e in errors))


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()
        cls.records = cls.mod.load_map()

    def test_kogane_overlap_routed(self):
        wealthy = by_id(self.records, 10)
        self.assertEqual(wealthy["owner_kind"], "route")
        self.assertEqual(wealthy["owner"]["lane"], 17)
        self.assertEqual(wealthy["shared_module"], "native/pc_port/pc_p2_kogane.cpp")

    def test_long_legs_overlap_routed(self):
        for sid in (56, 69):
            with self.subTest(sid=sid):
                rec = by_id(self.records, sid)
                self.assertEqual(rec["owner_kind"], "route")
                self.assertEqual(rec["owner"]["lane"], 26)
                self.assertEqual(rec["shared_module"],
                                 "native/pc_port/pc_p2_long_legs.cpp")

    def test_tobi_follow_on_exact(self):
        follow = by_id(self.records, 14)["follow_on"]
        self.assertIsNotNone(follow)
        self.assertEqual(follow["slice_id"], "TOBI14-P0")
        self.assertEqual(follow["kind"], "p0-audit")
        self.assertEqual(follow["files"],
                         ["experimental/pikmin2_tobi14_audit.py",
                          "tests/test_pikmin2_tobi14_audit.py",
                          "docs/PIKMIN2_TOBI14_AUDIT.md"])
        self.assertTrue(follow["acceptance"])

    def test_hiba_follow_on_exact(self):
        follow = by_id(self.records, 22)["follow_on"]
        self.assertIsNotNone(follow)
        self.assertEqual(follow["slice_id"], "HIBA22-GATES")
        self.assertEqual(follow["kind"], "gate-closure")
        self.assertIn("native/pc_port/pc_p2_hiba.cpp", follow["files"])

    def test_aliases_carry_no_gates_or_follow_on(self):
        for sid in (39, 64):
            with self.subTest(sid=sid):
                rec = by_id(self.records, sid)
                self.assertEqual(rec["owner_kind"], "alias")
                self.assertIsNone(rec["owner"])
                self.assertEqual(rec["module_files"], [])
                self.assertIsNone(rec["follow_on"])

    def test_base_is_nonactor_parent(self):
        base = by_id(self.records, 100)
        self.assertEqual(base["owner_kind"], "nonactor")
        self.assertFalse(base["spawnable"])
        self.assertIsNone(base["follow_on"])


if __name__ == "__main__":
    unittest.main()