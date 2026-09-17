"""Focused fail-closed tests for the overworld surface boot-path pin discovery (#707)."""
import copy
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "surface_boot_pin_discovery",
    ROOT / "experimental" / "pikmin2_overworld_surface_boot_path_pin_discovery.py")
discovery = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(discovery)


class RegistryTests(unittest.TestCase):
    def test_build_validates_clean(self):
        registry = discovery.build_registry()
        self.assertEqual(discovery.validate_registry(registry), [])
        self.assertEqual(registry["schema"], "p2-overworld-surface-boot-path-1")
        self.assertEqual(registry["root_base"],
                         "c86e4029fc654f3548c47d858bd80b402b9977fd")
        self.assertEqual(registry["native_pin"],
                         "b805d9c626e4f4558c95aef7cac311a5d9a2068f")
        self.assertFalse(registry["runtime_claim"])

    def test_three_absent_items_with_186_requests(self):
        registry = discovery.build_registry()
        self.assertEqual(len(registry["items"]), 3)
        for item in registry["items"]:
            self.assertEqual(item["status"], "ABSENT")
            self.assertTrue(item["evidence"])
            self.assertIn("request", item["review_186"])
        keys = {item["key"] for item in registry["items"]}
        self.assertEqual(keys, {"course_boot", "day_trigger", "exit_reentry"})

    def test_132_excluded_not_reaudited(self):
        registry = discovery.build_registry()
        self.assertEqual(len(registry["excluded_132"]), 4)
        for entry in registry["excluded_132"]:
            self.assertEqual(entry["status"], "EXCLUDED")
            self.assertIn("#658", entry["owner"])

    def test_downstream_and_gates(self):
        registry = discovery.build_registry()
        self.assertEqual(sorted(registry["downstream"]), [148, 149, 150, 151, 660, 696])
        self.assertEqual(set(registry["gates"]),
                         {"identity_spawn", "movement_animation", "attacks_receivers",
                          "death_corpse", "transport_reward", "cleanup_reentry"})
        self.assertTrue(all(v == "UNTESTED" for v in registry["gates"].values()))

    def test_diagnostic_plan_complete(self):
        plan = discovery.build_registry()["diagnostic_plan"]
        self.assertIn("stall", plan)
        self.assertGreaterEqual(len(plan["observation_points"]), 3)
        self.assertIn("data-ready", plan["data_ready_assumption"])
        self.assertGreaterEqual(len(plan["smallest_instrumentation"]), 2)
        self.assertIn("#186", plan["owner_contract"])

    def test_sha_stable(self):
        registry = discovery.build_registry()
        self.assertEqual(discovery.registry_sha256(registry),
                         discovery.registry_sha256(registry))
        self.assertEqual(len(discovery.registry_sha256(registry)), 64)

    def test_no_aliasing(self):
        first = discovery.build_registry()
        first["items"][0]["status"] = "PINNED"
        second = discovery.build_registry()
        self.assertEqual(second["items"][0]["status"], "ABSENT")


class RefusalTests(unittest.TestCase):
    def test_non_dict_refused(self):
        self.assertEqual(discovery.validate_registry([]), ["registry-must-be-dict"])

    def test_bad_schema_refused(self):
        row = discovery.build_registry()
        row["schema"] = "x"
        self.assertIn("bad-schema", discovery.validate_registry(row))

    def test_bad_root_base_refused(self):
        row = discovery.build_registry()
        row["root_base"] = "0" * 40
        self.assertIn("bad-root-base", discovery.validate_registry(row))

    def test_absent_without_186_request_refused(self):
        row = discovery.build_registry()
        del row["items"][0]["review_186"]
        self.assertIn("missing-186-request-course_boot", discovery.validate_registry(row))

    def test_pinned_without_owner_refused(self):
        row = discovery.build_registry()
        row["items"][0]["status"] = "PINNED"
        self.assertIn("missing-owner-course_boot", discovery.validate_registry(row))

    def test_missing_evidence_refused(self):
        row = discovery.build_registry()
        row["items"][1]["evidence"] = []
        self.assertIn("missing-evidence-day_trigger", discovery.validate_registry(row))

    def test_wrong_item_count_refused(self):
        row = discovery.build_registry()
        row["items"] = row["items"][:2]
        self.assertIn("bad-items", discovery.validate_registry(row))

    def test_short_excluded_refused(self):
        row = discovery.build_registry()
        row["excluded_132"] = row["excluded_132"][:3]
        self.assertIn("bad-excluded-132", discovery.validate_registry(row))

    def test_incomplete_plan_refused(self):
        row = discovery.build_registry()
        del row["diagnostic_plan"]["stall"]
        self.assertIn("missing-plan-stall", discovery.validate_registry(row))

    def test_wrong_downstream_refused(self):
        row = discovery.build_registry()
        row["downstream"] = [148]
        self.assertIn("bad-downstream", discovery.validate_registry(row))

    def test_runtime_claim_refused(self):
        row = discovery.build_registry()
        row["runtime_claim"] = True
        self.assertIn("no-runtime-claims", discovery.validate_registry(row))

    def test_bad_gates_refused(self):
        row = discovery.build_registry()
        row["gates"] = {"identity_spawn": "PASS"}
        self.assertIn("bad-gates", discovery.validate_registry(row))

    def test_main_check_passes(self):
        self.assertEqual(discovery.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
