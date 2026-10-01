"""Focused fail-closed tests for the #710 host-mode hook landing (#714)."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "hostmode_hook_landing",
    ROOT / "experimental" / "pikmin2_challenge_hostmode_hook_landing.py")
landing = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(landing)


class RegistryTests(unittest.TestCase):
    def test_build_validates_clean(self):
        registry = landing.build_registry()
        self.assertEqual(landing.validate_registry(registry), [])
        self.assertEqual(registry["schema"], "p2-challenge-hostmode-hook-landing-1")
        self.assertEqual((registry["lane"], registry["issue"], registry["generation"]),
                         ("challenge-hostmode-hook-landing", 714, 2))
        self.assertFalse(registry["runtime_claim"])

    def test_hook_pins_match_review(self):
        hook = landing.build_registry()["hook_710"]
        self.assertEqual(hook["root_commit"],
                         "3e3cdd1d93a3b0196cdd19202ab9eb922a80e9d8")
        self.assertEqual(hook["native_commit"],
                         "db245877a090d017a09e28ac1c144e6497857227")
        self.assertEqual(hook["root_base"],
                         "ecf5f53a601a3c563bb44339ec7abf4665795451")
        self.assertEqual(hook["native_base"],
                         "78b67349b50a729a53caec0006d2ebbc70aa5308")

    def test_nine_files_no_duplication_gap(self):
        files = landing.build_registry()["hook_710"]["files"]
        self.assertEqual(len(files), 9)
        self.assertEqual(len({(f["repo"], f["path"]) for f in files}), 9)
        for f in files:
            self.assertEqual(len(f["blob"]), 40)
            int(f["blob"], 16)

    def test_integrated_701_702_pins(self):
        integrated = landing.build_registry()["integrated"]
        self.assertEqual(set(integrated), {"701", "702"})
        self.assertEqual(integrated["701"]["native_commit"],
                         "f91c21438163e3fa21862074fb2eec62a19c0e32")
        self.assertEqual(integrated["701"]["root_commit"],
                         "806952dbe60e11f5bb10e957b5c5898066957cd7")
        self.assertEqual(integrated["702"]["native_commit"],
                         "78b67349b50a729a53caec0006d2ebbc70aa5308")
        self.assertEqual(integrated["702"]["root_commit"],
                         "75dddcd2fa96ea4e52ba4c899e7a21f8a7d2a499")

    def test_evidence_710_complete(self):
        evidence = landing.build_registry()["evidence_710"]
        self.assertEqual(set(evidence),
                         {"pytest", "verify", "fixturecompile", "buildlog",
                          "buildrecord", "buildrecord_on", "headedrun",
                          "guard", "doc"})
        for item in evidence.values():
            self.assertEqual(len(item["sha256"]), 64)

    def test_hook_186_pending(self):
        review = landing.build_registry()["hook_186"]
        self.assertEqual(review["status"], "review pending")
        self.assertEqual(len(review["items"]), 2)

    def test_downstream_550(self):
        downstream = landing.build_registry()["downstream"]
        self.assertEqual(downstream["issue"], 550)
        self.assertEqual(downstream["lane"], "p2-challenge-ch-abem-leafchappy-p1")
        self.assertEqual(downstream["consumer_evidence"]["sha256"],
                         "9ceb1571c8fbbcb2f2beea33cf8f02bdc039b33ffb8d1529c01f10901bc89a93")

    def test_gates_untested(self):
        gates = landing.build_registry()["gates"]
        self.assertEqual(set(gates),
                         {"identity_spawn", "movement_animation", "attacks_receivers",
                          "death_corpse", "transport_reward", "cleanup_reentry"})
        self.assertTrue(all(v == "UNTESTED" for v in gates.values()))

    def test_packet_names_exact_commits(self):
        packet = landing.build_packet(landing.build_registry())
        self.assertEqual(packet["kind"], "integration-ready")
        self.assertEqual(packet["hook_commits"]["root"],
                         "3e3cdd1d93a3b0196cdd19202ab9eb922a80e9d8")
        self.assertEqual(packet["hook_commits"]["native"],
                         "db245877a090d017a09e28ac1c144e6497857227")
        self.assertEqual(len(packet["hook_file_blobs"]), 9)
        self.assertEqual(packet["downstream"]["issue"], 550)

    def test_sha_stable(self):
        registry = landing.build_registry()
        self.assertEqual(landing.registry_sha256(registry),
                         landing.registry_sha256(registry))
        self.assertEqual(len(landing.registry_sha256(registry)), 64)

    def test_no_aliasing(self):
        first = landing.build_registry()
        first["hook_710"]["files"][0]["blob"] = "0" * 40
        second = landing.build_registry()
        self.assertNotEqual(second["hook_710"]["files"][0]["blob"], "0" * 40)


class RefusalTests(unittest.TestCase):
    def test_non_dict_refused(self):
        self.assertEqual(landing.validate_registry([]), ["registry-must-be-dict"])

    def test_bad_schema_refused(self):
        row = landing.build_registry()
        row["schema"] = "x"
        self.assertIn("bad-schema", landing.validate_registry(row))

    def test_bad_identity_refused(self):
        row = landing.build_registry()
        row["issue"] = 1
        self.assertIn("bad-identity", landing.validate_registry(row))

    def test_hook_pin_changed_refused(self):
        row = landing.build_registry()
        row["hook_710"]["native_commit"] = "0" * 40
        self.assertIn("hook-pin-changed-native_commit", landing.validate_registry(row))

    def test_hook_blob_changed_refused(self):
        row = landing.build_registry()
        row["hook_710"]["files"][0]["blob"] = "0" * 40
        problems = landing.validate_registry(row)
        self.assertTrue(any(p.startswith("hook-blob-changed-") for p in problems))

    def test_short_file_list_refused(self):
        row = landing.build_registry()
        row["hook_710"]["files"] = row["hook_710"]["files"][:8]
        self.assertIn("bad-hook-files", landing.validate_registry(row))

    def test_integration_pin_changed_refused(self):
        row = landing.build_registry()
        row["integrated"]["702"]["native_commit"] = "0" * 40
        self.assertIn("integration-pin-changed-702-native_commit",
                      landing.validate_registry(row))

    def test_evidence_changed_refused(self):
        row = landing.build_registry()
        row["evidence_710"]["pytest"]["sha256"] = "0" * 64
        self.assertIn("evidence-changed-pytest", landing.validate_registry(row))

    def test_hook_186_resolved_refused(self):
        row = landing.build_registry()
        row["hook_186"]["status"] = "approved"
        self.assertIn("bad-hook-186", landing.validate_registry(row))

    def test_wrong_downstream_refused(self):
        row = landing.build_registry()
        row["downstream"]["issue"] = 1
        self.assertIn("bad-downstream", landing.validate_registry(row))

    def test_runtime_claim_refused(self):
        row = landing.build_registry()
        row["runtime_claim"] = True
        self.assertIn("no-runtime-claims", landing.validate_registry(row))

    def test_bad_gates_refused(self):
        row = landing.build_registry()
        row["gates"] = {"identity_spawn": "PASS"}
        self.assertIn("bad-gates", landing.validate_registry(row))

    def test_main_check_passes(self):
        self.assertEqual(landing.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
