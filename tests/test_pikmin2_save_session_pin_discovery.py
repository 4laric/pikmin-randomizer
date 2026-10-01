"""Focused tests for the save/session pin-discovery registry (#658).

The registry module is loaded from its reserved file location so this lane
creates no package markers outside its three reserved files.
"""
import importlib.util
import unittest
from pathlib import Path

ADAPTER_PATH = (
    Path(__file__).resolve().parents[1] / "experimental"
    / "pikmin2_save_session_pin_discovery.py"
)
_spec = importlib.util.spec_from_file_location("save_session_pin_discovery", ADAPTER_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

registry = _mod.registry
verify_pin = _mod.verify_pin
verify_registry = _mod.verify_registry
PinError = _mod.PinError
ITEMS = _mod.ITEMS
RESEARCH_ROOT = _mod.RESEARCH_ROOT

EXPECTED_IDS = {"sunset-driver", "save-serializer", "receipt-ledger-endpoint",
                "generator-cache-restore"}
EXPECTED_PIN_COUNTS = {"sunset-driver": 6, "save-serializer": 6,
                       "receipt-ledger-endpoint": 3,
                       "generator-cache-restore": 6}


class RegistrySchemaTests(unittest.TestCase):
    def test_four_items_with_unique_ids(self):
        data = registry()
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["issue"], 658)
        self.assertEqual({i["id"] for i in data["items"]}, EXPECTED_IDS)
        for item in data["items"]:
            self.assertEqual(len(item["pins"]), EXPECTED_PIN_COUNTS[item["id"]])
            self.assertTrue(item["owner"] or item["shared_review"])

    def test_full_registry_verifies_against_research_tree(self):
        self.assertTrue(verify_registry(registry()))

    def test_registry_is_a_copy(self):
        data = registry()
        data["items"][0]["pins"].append({"file": "x", "line": 1})
        self.assertEqual(len(registry()["items"][0]["pins"]),
                         EXPECTED_PIN_COUNTS["sunset-driver"])

    def test_schema_rejects_bad_input(self):
        with self.assertRaises(PinError):
            verify_registry({})
        with self.assertRaises(PinError):
            verify_registry({"schema": 1, "items": []})
        dup = registry()
        dup["items"].append(dict(dup["items"][0]))
        with self.assertRaises(PinError):
            verify_registry(dup)
        norole = registry()
        norole["items"][0]["owner"] = None
        norole["items"][0]["shared_review"] = None
        with self.assertRaises(PinError):
            verify_registry(norole)


class PinPresenceTests(unittest.TestCase):
    def test_every_recorded_pin_exists(self):
        data = registry()
        total = 0
        for item in data["items"]:
            for pin in item["pins"]:
                with self.subTest(pin="%s:%d" % (pin["file"], pin["line"])):
                    self.assertTrue(verify_pin(pin))
                    total += 1
        self.assertEqual(total, sum(EXPECTED_PIN_COUNTS.values()))

    def test_pin_failures_are_closed(self):
        good = dict(registry()["items"][0]["pins"][0])
        for bad in (dict(good, line=1),
                    dict(good, line=10 ** 9),
                    dict(good, file="nope/missing.cpp"),
                    dict(good, symbol="NoSuchFunction"),
                    {"file": good["file"], "line": good["line"]}):
            with self.subTest(bad=bad), self.assertRaises(PinError):
                verify_pin(bad)


class OwnershipCoverageTests(unittest.TestCase):
    def test_expected_shared_review_owners(self):
        owners = {i["id"]: (i["shared_review"] or {}).get("owner")
                  for i in registry()["items"]}
        self.assertIn("#186", owners["sunset-driver"])
        self.assertIn("#132", owners["save-serializer"])
        self.assertIn("#606", owners["receipt-ledger-endpoint"])
        self.assertIn("#607", owners["generator-cache-restore"])

    def test_research_root_is_read_only_reference(self):
        self.assertTrue(Path(RESEARCH_ROOT).is_dir())
        self.assertIn("pikmin2-research", str(RESEARCH_ROOT))


if __name__ == "__main__":
    unittest.main()
