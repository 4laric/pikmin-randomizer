"""Unit tests for the muki #186 decision-request refresh driver (#824)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experimental"))
from pikmin2_muki_186_decision_refresh2 import packet


def sample_report(unlanded=True):
    return {
        "producer_root": "b" * 40,
        "producer_native_base": "a" * 40,
        "producer_native_head": "c" * 40,
        "producer_files": ["x.h"],
        "producer_insertions": 1,
        "producer_deletions": 0,
        "dest_root": "d" * 40,
        "dest_native": "e" * 40,
        "landed_at_dest": [],
        "unlanded": unlanded,
        "shared_wiring_needing_decision": ["pc_port/pc_bbft.cpp"],
    }


class PacketTests(unittest.TestCase):
    def test_packet_pins_and_scope(self):
        pack = packet(sample_report())
        self.assertEqual(pack["issue"], 824)
        self.assertEqual(pack["consumer"], "muki-stage-table-rows-native")
        self.assertEqual(pack["producer_pins"]["native"], "c" * 40)
        self.assertEqual(pack["destination_pins"]["native"], "e" * 40)
        self.assertTrue(pack["unlanded"])
        self.assertIn("#186", pack["decision_requested"])

    def test_packet_is_json_stable(self):
        pack = packet(sample_report(unlanded=False))
        self.assertFalse(pack["unlanded"])
        json.dumps(pack)

    def test_pin_constants_are_full_sha(self):
        import pikmin2_muki_186_decision_refresh2 as driver
        for pin in (driver.PRODUCER_ROOT, driver.PRODUCER_NATIVE_HEAD,
                    driver.DEST_ROOT, driver.DEST_NATIVE):
            self.assertRegex(pin, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
