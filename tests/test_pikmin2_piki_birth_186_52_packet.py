"""Fail-closed tests for the piki-birth 186/52 decision packet builder."""
import hashlib
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))
from pikmin2_piki_birth_186_52_packet import build, blob, fail

OUT = os.path.join(os.path.dirname(__file__), "..", "..",
                   "output", "workflow", "autofill", "planning-shards",
                   "provider-treasure-receipts", "prepared",
                   "piki-birth-186-52-output", "packet-check.json")


class PacketTests(unittest.TestCase):
    def test_five_files_with_hashes(self):
        pkt = build()
        self.assertEqual(len(pkt["files"]), 5)
        for e in pkt["files"]:
            self.assertRegex(e["base_sha256"], r"[0-9a-f]{64}")
            self.assertRegex(e["head_sha256"], r"[0-9a-f]{64}")

    def test_newpikigame_zero_diff_certified(self):
        pkt = build()
        npg = [e for e in pkt["files"] if e["file"].endswith("newPikiGame.cpp")][0]
        self.assertFalse(npg["changed"])
        self.assertEqual(npg["base_sha256"], npg["head_sha256"])

    def test_four_changed(self):
        pkt = build()
        self.assertEqual(sum(1 for e in pkt["files"] if e["changed"]), 4)

    def test_malformed_pin_refused(self):
        with self.assertRaises(SystemExit):
            blob("not-a-pin", "src/plugPikiKando/pikiMgr.cpp")

    def test_unknown_file_refused(self):
        with self.assertRaises(SystemExit):
            blob("e1861e68bf4d19b51ae182be5228f471803b71d9", "src/nope/missing.cpp")

    def test_consumer_and_decisions_present(self):
        pkt = build()
        self.assertEqual(pkt["consumer"]["issue"], 741)
        kinds = {d["kind"] for d in pkt["decisions_requested"]}
        self.assertEqual(kinds, {"landing", "coverage"})

    def test_packet_roundtrip_hash_stable(self):
        a = hashlib.sha256(json.dumps(build(), indent=1).encode()).hexdigest()
        b = hashlib.sha256(json.dumps(build(), indent=1).encode()).hexdigest()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()