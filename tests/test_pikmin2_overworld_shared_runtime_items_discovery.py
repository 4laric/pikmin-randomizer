"""Focused tests for experimental/pikmin2_overworld_shared_runtime_items_discovery.py.

Covers the three-item registry shape, the fail-closed pin verifier against the
read-only research tree, and the packet emission. No engine, build, runtime or
display needed.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_overworld_shared_runtime_items_discovery import (
    DEFAULT_RESEARCH_ROOT,
    ITEMS,
    emit_packet,
    verify_pins,
)

EXPECTED_OWNERS = {
    "native_sunset_driver": 605,
    "native_receipt_ledger_endpoint": 606,
    "native_generator_cache_restore": 607,
}


class RegistryShapeTest(unittest.TestCase):
    def test_three_items_unique_keys(self):
        keys = [i["key"] for i in ITEMS]
        self.assertEqual(len(keys), 3)
        self.assertEqual(len(set(keys)), 3)
        self.assertEqual(set(keys), set(EXPECTED_OWNERS))

    def test_each_item_has_owner_and_deliverable(self):
        for item in ITEMS:
            with self.subTest(key=item["key"]):
                self.assertEqual(item["owner_issue"], EXPECTED_OWNERS[item["key"]])
                self.assertTrue(item["owner_shard"])
                self.assertTrue(item["review_186"])
                self.assertTrue(item["pins"])
                deliverable = item["deliverable"]
                self.assertTrue(deliverable["owned_files"])
                self.assertTrue(deliverable["acceptance"])

    def test_save_serializer_excluded(self):
        from experimental.pikmin2_overworld_shared_runtime_items_discovery import (
            DOWNLOADSTREAM_EXCLUDED,
        )
        self.assertIn("native save serializer", DOWNLOADSTREAM_EXCLUDED)


class PinVerificationTest(unittest.TestCase):
    def test_real_pins_verify(self):
        ok, report, problems = verify_pins(DEFAULT_RESEARCH_ROOT)
        self.assertEqual(problems, [])
        self.assertTrue(ok)
        self.assertEqual(len(report["items"]), 3)
        for entry in report["items"]:
            self.assertGreater(entry["pin_count"], 0)
            for pin in entry["verified_pins"]:
                self.assertRegex(pin["file_sha256"], r"^[0-9a-f]{64}$")

    def test_missing_root_fails_closed(self):
        ok, _report, problems = verify_pins(os.path.join(tempfile.gettempdir(),
                                                         "no-such-research-tree"))
        self.assertFalse(ok)
        self.assertEqual(len(problems), len(ITEMS) and sum(
            len(i["pins"]) for i in ITEMS))
        self.assertTrue(all("missing file" in p for p in problems))

    def test_tampered_token_fails_closed(self):
        tmp = tempfile.mkdtemp(prefix="items-discovery-")
        self.addCleanup(shutil.rmtree, tmp, True)
        # Build a minimal tree with a deliberately wrong line for one pin.
        rel = os.path.join("src", "plugProjectKandoU", "gameGeneratorCache.cpp")
        target = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(target))
        with open(target, "w", encoding="utf-8") as stream:
            for _ in range(203):
                stream.write("// filler\n")
            stream.write("void GeneratorCache::NOTloadGenerators()\n")
            for _ in range(700):
                stream.write("// filler\n")
        ok, _report, problems = verify_pins(tmp)
        self.assertFalse(ok)
        self.assertTrue(any("token" in p or "missing file" in p for p in problems))

    def test_emit_packet_writes_fail_closed_report(self):
        tmp = tempfile.mkdtemp(prefix="items-packet-")
        self.addCleanup(shutil.rmtree, tmp, True)
        out = os.path.join(tmp, "packet.json")
        ok, report, problems = emit_packet(out, DEFAULT_RESEARCH_ROOT)
        self.assertTrue(ok)
        self.assertEqual(problems, [])
        written = json.load(open(out, encoding="utf-8"))
        self.assertTrue(written["ok"])
        self.assertEqual(written["schema"], "p2-overworld-shared-runtime-items-1")
        self.assertIn("excluded", written)


if __name__ == "__main__":
    unittest.main()
