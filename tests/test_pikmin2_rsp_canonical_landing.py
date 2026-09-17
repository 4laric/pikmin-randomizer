"""Focused landing tests: gap proof, fix refs, patch validity, evidence (#659)."""
import json
import unittest
from pathlib import Path

import experimental.pikmin2_rsp_canonical_landing as land


class GapTests(unittest.TestCase):
    def test_gap_recorded(self):
        gap = land.canonical_gap()
        self.assertEqual(gap["pin"], "36b868391e62cccf37d992aa2f796f3cc9c6dc31")
        self.assertTrue(gap["rejects_rsp"])
        self.assertFalse(any(gap["fix_absent"].values()))
        self.assertEqual(gap["shared_files"],
                         ["scripts/build_pikmin2_fixture.py",
                          "tests/test_pikmin2_fixture_build.py"])

    def test_fix_refs(self):
        fix = land.reviewed_fix()
        self.assertEqual(fix["fix_commit"],
                         "0cab1fa111216250ce57e02600f697ab850ae592")
        for path, entry in fix["files"].items():
            self.assertEqual(len(entry["pin_sha256"]), 64)
            self.assertNotEqual(entry["pin_sha256"], entry["fix_sha256"])
            self.assertGreater(entry["fix_bytes"], 0)


class PatchTests(unittest.TestCase):
    def test_patch_applies_clean(self):
        patch = land.derive_landable_patch()
        self.assertGreater(patch["patch_bytes"], 0)
        self.assertEqual(len(patch["patch_sha256"]), 64)
        self.assertIn("build_pikmin2_fixture", patch["patch"])

    def test_packet_shape(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            packet = land.emit_packet(tmp)
            self.assertEqual(packet["issue"], 659)
            self.assertEqual(packet["gates"], "all six UNTESTED")
            self.assertEqual(len(packet["downstream"]), 2)
            self.assertTrue(Path(packet["packet_path"]).is_file())
            back = json.loads(Path(packet["packet_path"]).read_text(encoding="utf-8"))
            self.assertEqual(back["patch_sha256"], packet["patch_sha256"])


class EvidenceTests(unittest.TestCase):
    def test_616_hashes_match(self):
        evidence = land.verify_616_evidence()
        self.assertGreaterEqual(len(evidence["matches"]), 10)
        self.assertEqual(evidence["handoff_root"],
                         "b779b00fe26326451d10b6b68f7ad054f63f91c2")
        self.assertEqual(evidence["handoff_native"],
                         "6d4cbc4afc112c02b7166ef30d8a1f684c7f3ba5")


class FailClosedTests(unittest.TestCase):
    def test_bogus_pin_fails(self):
        saved = land.CANONICAL_PIN
        land.CANONICAL_PIN = "0" * 40
        try:
            with self.assertRaises(land.LandingGapError):
                land.canonical_gap()
        finally:
            land.CANONICAL_PIN = saved

    def test_missing_handoff_fails(self):
        saved = land.H616_HANDOFF
        land.H616_HANDOFF = "output/no-such-handoff.json"
        try:
            with self.assertRaises(land.LandingGapError):
                land.verify_616_evidence()
        finally:
            land.H616_HANDOFF = saved

    def test_hash_helper_rejects_non_bytes(self):
        with self.assertRaises(land.LandingGapError):
            land.sha256_bytes("not-bytes")


if __name__ == "__main__":
    unittest.main()