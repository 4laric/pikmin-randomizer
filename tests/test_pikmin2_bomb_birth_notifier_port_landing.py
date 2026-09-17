"""Focused fail-closed tests for the #715 hook-notifier port landing (#719)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "notifier_port_landing",
    ROOT / "experimental" / "pikmin2_bomb_birth_notifier_port_landing.py")
landing = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(landing)


class RegistryTests(unittest.TestCase):
    def test_build_validates_clean(self):
        registry = landing.build_registry()
        self.assertEqual(landing.validate_registry(registry), [])
        self.assertEqual(registry["schema"], "p2-bomb-birth-notifier-port-landing-1")
        self.assertEqual((registry["lane"], registry["issue"], registry["generation"]),
                         ("bomb-birth-notifier-port-landing", 719, 2))
        self.assertFalse(registry["runtime_claim"])

    def test_port_pins_match_review(self):
        port = landing.build_registry()["port_715"]
        self.assertEqual(port["root_commit"],
                         "f807392feef43a145559350406e467136d49de06")
        self.assertEqual(port["native_commit"],
                         "a6ca7bc6842a24bb8c2321f446fcfb8ec94f1b65")
        self.assertEqual(port["root_base"],
                         "ecf5f53a601a3c563bb44339ec7abf4665795451")
        self.assertEqual(port["native_base"],
                         "5d03a79053baa888f8edac380b58ecf65669d3e7")
        self.assertIn("#677", port["native_base_identity"])

    def test_nine_files_hook_verified_intact(self):
        files = landing.build_registry()["port_715"]["files"]
        self.assertEqual(len(files), 9)
        self.assertEqual(len({(f["repo"], f["path"]) for f in files}), 9)
        hook = [f for f in files if f["path"].endswith("generalEnemyMgr.cpp")][0]
        self.assertFalse(hook["changed"])
        self.assertEqual(sum(1 for f in files if f.get("changed", True)), 8)
        for f in files:
            self.assertEqual(len(f["blob"]), 40)
            int(f["blob"], 16)

    def test_packet_186_items(self):
        packet = landing.build_registry()["packet_186"]
        self.assertEqual(packet["issue"], 186)
        self.assertEqual(packet["name"], "provider-bomb-birth-186-review-packet")
        self.assertEqual(len(packet["items"]), 3)

    def test_integrated_691_700_703_pins(self):
        integrated = landing.build_registry()["integrated"]
        self.assertEqual(set(integrated), {"691", "700", "703"})
        self.assertEqual(integrated["691"]["native_commit"],
                         "95172ea40ea27c436f3117bca97794bfb3b60ebc")
        self.assertEqual(integrated["691"]["root_commit"],
                         "1fcaf074d6c0c6e83f1a681e2503cacba9b8ad76")
        self.assertEqual(integrated["700"]["native_commit"],
                         "58df488eb1d9582b0ef625d46874f3427c18628d")
        self.assertEqual(integrated["700"]["root_commit"],
                         "347526301a4a91df673a631c7d7ab0579e5823a9")
        self.assertEqual(integrated["703"]["root_commit"],
                         "f985d17cb6da301c073923c57cd283c5ebe78c32")
        self.assertIsNone(integrated["703"]["native_commit"])

    def test_evidence_715_complete(self):
        evidence = landing.build_registry()["evidence_715"]
        self.assertEqual(set(evidence),
                         {"pytest", "verify", "providerlog", "buildlog",
                          "buildrecord", "buildrecord_on", "guard", "doc"})
        for item in evidence.values():
            self.assertEqual(len(item["sha256"]), 64)

    def test_downstream_573(self):
        downstream = landing.build_registry()["downstream"]
        self.assertEqual(downstream["issue"], 573)
        self.assertEqual(downstream["lane"], "enemy-bombotakara93-payload")
        self.assertEqual(downstream["consumer_evidence"]["sha256"],
                         "77e54c1944028997d97e2733e957f9060d1d93a589ffa8e55ae0a82f81b254df")

    def test_gates_untested(self):
        gates = landing.build_registry()["gates"]
        self.assertEqual(set(gates),
                         {"identity_spawn", "movement_animation", "attacks_receivers",
                          "death_corpse", "transport_reward", "cleanup_reentry"})
        self.assertTrue(all(v == "UNTESTED" for v in gates.values()))

    def test_packet_names_exact_commits(self):
        packet = landing.build_packet(landing.build_registry())
        self.assertEqual(packet["kind"], "integration-ready")
        self.assertEqual(packet["port_commits"]["root"],
                         "f807392feef43a145559350406e467136d49de06")
        self.assertEqual(packet["port_commits"]["native"],
                         "a6ca7bc6842a24bb8c2321f446fcfb8ec94f1b65")
        self.assertEqual(len(packet["port_file_blobs"]), 9)
        self.assertEqual(packet["downstream"]["issue"], 573)

    def test_sha_stable(self):
        registry = landing.build_registry()
        self.assertEqual(landing.registry_sha256(registry),
                         landing.registry_sha256(registry))
        self.assertEqual(len(landing.registry_sha256(registry)), 64)

    def test_no_aliasing(self):
        first = landing.build_registry()
        first["port_715"]["files"][0]["blob"] = "0" * 40
        second = landing.build_registry()
        self.assertNotEqual(second["port_715"]["files"][0]["blob"], "0" * 40)


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

    def test_port_pin_changed_refused(self):
        row = landing.build_registry()
        row["port_715"]["native_commit"] = "0" * 40
        self.assertIn("port-pin-changed-native_commit", landing.validate_registry(row))

    def test_port_blob_changed_refused(self):
        row = landing.build_registry()
        row["port_715"]["files"][0]["blob"] = "0" * 40
        problems = landing.validate_registry(row)
        self.assertTrue(any(p.startswith("port-blob-changed-") for p in problems))

    def test_short_file_list_refused(self):
        row = landing.build_registry()
        row["port_715"]["files"] = row["port_715"]["files"][:8]
        self.assertIn("bad-port-files", landing.validate_registry(row))

    def test_packet_186_changed_refused(self):
        row = landing.build_registry()
        row["packet_186"]["items"] = row["packet_186"]["items"][:2]
        self.assertIn("bad-packet-186", landing.validate_registry(row))

    def test_integration_pin_changed_refused(self):
        row = landing.build_registry()
        row["integrated"]["700"]["native_commit"] = "0" * 40
        self.assertIn("integration-pin-changed-700-native_commit",
                      landing.validate_registry(row))

    def test_evidence_changed_refused(self):
        row = landing.build_registry()
        row["evidence_715"]["pytest"]["sha256"] = "0" * 64
        self.assertIn("evidence-changed-pytest", landing.validate_registry(row))

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
