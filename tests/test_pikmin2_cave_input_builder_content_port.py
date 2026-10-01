"""Focused fail-closed tests for the cave input builder content port.

Lane provider-cave-input-builder-content-port (#642). Hermetic: the carried
bytes are checked against their recorded hashes, packet emission round-trips
through temp dirs, and every refusal class is exercised. No engine, no
assets, no display, no runtime, no build.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from pikmin2_cave_input_builder_content_port import (
    DOWNSTREAM,
    FILE_META,
    SCHEMA,
    emit_packet,
    expected_blob,
    expected_sha256,
    main,
    packet_bytes,
    verify_bytes,
    verify_packet_self,
    verify_producer_tree,
)

BUILDER = "experimental/pikmin2_cave_runtime_inputs.py"
TESTMOD = "tests/test_pikmin2_cave_runtime_inputs.py"


class ContentPortPacketTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cave-port-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_carried_bytes_match_recorded_hashes(self):
        for path in (BUILDER, TESTMOD):
            data = packet_bytes(path)
            self.assertTrue(data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected_sha256(path))
            self.assertEqual(len(expected_blob(path)), 40)
            self.assertEqual(verify_bytes(path, data), [])

    def test_self_verify_clean(self):
        self.assertEqual(verify_packet_self(), [])

    def test_unknown_file_refused(self):
        with self.assertRaises(KeyError):
            expected_sha256("no/such/file.py")
        with self.assertRaises(KeyError):
            packet_bytes("no/such/file.py")
        self.assertEqual(verify_bytes("no/such/file.py", b"x"), ["unknown-file"])

    def test_empty_and_nonbytes_refused(self):
        self.assertEqual(verify_bytes(BUILDER, b""), ["empty-bytes"])
        self.assertEqual(verify_bytes(BUILDER, "text-not-bytes"), ["not-bytes"])
        self.assertEqual(verify_bytes(BUILDER, None), ["not-bytes"])

    def test_tampered_bytes_mismatch(self):
        data = bytearray(packet_bytes(BUILDER))
        data[100] ^= 0xFF
        self.assertEqual(verify_bytes(BUILDER, bytes(data)), ["hash-mismatch"])

    def _populate(self, root, tamper=None, drop=None):
        for path in (BUILDER, TESTMOD):
            if path == drop:
                continue
            data = packet_bytes(path)
            if path == tamper:
                data = bytearray(data)
                data[10] ^= 0x01
                data = bytes(data)
            dest = os.path.join(root, *path.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)

    def test_producer_tree_populated_passes(self):
        root = os.path.join(self.tmp, "producer")
        self._populate(root)
        self.assertEqual(verify_producer_tree(root), [])

    def test_producer_tree_missing_and_tampered(self):
        root = os.path.join(self.tmp, "producer")
        self._populate(root, drop=TESTMOD)
        problems = verify_producer_tree(root)
        self.assertIn("missing-file:%s" % TESTMOD, problems)
        root2 = os.path.join(self.tmp, "producer2")
        self._populate(root2, tamper=BUILDER)
        problems2 = verify_producer_tree(root2)
        self.assertIn("%s:hash-mismatch" % BUILDER, problems2)
        self.assertEqual(verify_producer_tree(os.path.join(self.tmp, "absent")),
                         ["missing-file:%s" % BUILDER, "missing-file:%s" % TESTMOD])

    def test_emit_packet_roundtrip(self):
        out = os.path.join(self.tmp, "packet")
        packet = emit_packet(out)
        self.assertEqual(packet["schema"], SCHEMA)
        self.assertEqual(packet["producer"]["head"],
                         "74f5a099038149b36c49ff8cb7d699533b41f997")
        self.assertEqual(packet["content_base"]["ref"],
                         "b0d2c08c1ccb8c67f23946241b4b67dcb9ae9f53")
        self.assertEqual(sorted(d["issue"] for d in packet["downstream"]), [114, 154, 161])
        disk = json.load(open(os.path.join(out, "packet.json"), encoding="utf-8"))
        self.assertEqual(disk, packet)
        for path in (BUILDER, TESTMOD):
            with open(os.path.join(out, "packet-files", *path.split("/")), "rb") as f:
                self.assertEqual(f.read(), packet_bytes(path))

    def test_emit_empty_out_refused(self):
        with self.assertRaises(ValueError):
            emit_packet("")

    def test_cli_emit_and_verify_self(self):
        out = os.path.join(self.tmp, "cli-packet")
        self.assertEqual(main(["emit", "--out", out]), 0)
        self.assertTrue(os.path.isfile(os.path.join(out, "packet.json")))
        self.assertEqual(main(["verify", "--self"]), 0)

    def test_cli_verify_producer_root(self):
        root = os.path.join(self.tmp, "producer")
        self._populate(root)
        self.assertEqual(main(["verify", "--producer-root", root]), 0)
        self.assertEqual(main(["verify", "--producer-root", os.path.join(self.tmp, "absent")]), 1)

    def test_cli_verify_needs_target(self):
        self.assertEqual(main(["verify"]), 2)


if __name__ == "__main__":
    unittest.main()
