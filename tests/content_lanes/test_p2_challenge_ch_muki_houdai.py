"""Focused P0 tests for the ch_MUKI_houdai import adapter (#541).

Uses synthetic caveinfo text only; no retail assets are read and no
placements are emitted. Covers the happy path, malformed/missing inputs,
challenge-pin validation and the no-invention boundary.
"""
import importlib.util
import json
import unittest
from pathlib import Path


def _load_adapter():
    path = Path(__file__).resolve().parents[2] / "experimental" / "content_lanes" / "p2-challenge-ch_muki_houdai.py"
    spec = importlib.util.spec_from_file_location("houdai_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


houdai = _load_adapter()

FLOOR = ("{ {f000} 4 %d {f001} 4 %d {f008} -1 unit%d.txt {_eof} } "
         "{ 1 Houdai 30 2 } { 1 Takara 10 } { 0 } { 0 }")
GOOD = "{ {c000} 4 2 {_eof} } 2 " + (FLOOR % (0, 0, 1)) + " " + (FLOOR % (1, 1, 2))

CHALLENGE = dict(
    table_order=24,
    ui_index=8,
    floors=2,
    floor_seconds=[100.0, 150.0],
    bitter_sprays=1,
    spicy_sprays=1,
    treasure_count_field=0,
    legacy_time=0.0,
    pikmin_by_native_color_and_maturity=[
        [0, 0, 10], [0, 0, 10], [0, 0, 10], [0, 0, 10], [0, 0, 10],
        [0, 0, 0], [0, 0, 0],
    ],
)


class HoudaiAdapterTests(unittest.TestCase):
    def test_decode_two_floors_preserves_source_rows(self):
        floors = houdai.decode_cave(GOOD)
        self.assertEqual([floor["number"] for floor in floors], [1, 2])
        self.assertEqual(floors[0]["enemies"],
                         [dict(id="Houdai", packed_weight=30, placement_type=2)])
        self.assertEqual(floors[0]["treasures"],
                         [dict(id="Takara", packed_weight=10)])

    def test_floor_count_mismatch_fails_closed(self):
        one = "{ {c000} 4 1 {_eof} } 1 " + (FLOOR % (0, 0, 1))
        with self.assertRaisesRegex(ValueError, "floor coverage mismatch"):
            houdai.decode_cave(one)

    def test_missing_or_empty_input_fails(self):
        for bad in (None, "", "   ", 123, b"bytes"):
            with self.assertRaises(ValueError):
                houdai.decode_cave(bad)

    def test_malformed_definition_fails(self):
        with self.assertRaises(ValueError):
            houdai.decode_cave("not a cave definition")
        with self.assertRaises(ValueError):
            houdai.decode_cave(GOOD.replace("{c000} 4 2", "{c000} 4 3"))

    def test_manifest_marks_unplayable_and_lists_closure(self):
        manifest = houdai.build_manifest(GOOD, "b" * 64, dict(CHALLENGE))
        self.assertFalse(manifest["playable"])
        self.assertEqual(manifest["floor_coverage"], [1, 2])
        self.assertEqual(manifest["challenge"]["status"], "matches_catalogue")
        self.assertEqual(manifest["resource_closure"],
                         [dict(path=houdai.SOURCE_PATH, sha256="b" * 64,
                               status="hash_unvalidated")])
        self.assertNotIn('"placement":', json.dumps(manifest))
        self.assertTrue(houdai.validate_manifest(manifest))

    def test_manifest_without_hash_stays_unvalidated(self):
        manifest = houdai.build_manifest(GOOD)
        self.assertEqual(manifest["hash_status"], "hash_unvalidated")
        self.assertEqual(manifest["challenge"]["status"], "baseline_catalogued")

    def test_expected_hash_marks_validated(self):
        manifest = houdai.build_manifest(GOOD, houdai.EXPECTED_SHA256)
        self.assertEqual(manifest["hash_status"], "hash_validated")

    def test_bad_hash_and_challenge_rejected(self):
        with self.assertRaises(ValueError):
            houdai.build_manifest(GOOD, "short")
        bad = dict(CHALLENGE, ui_index=99)
        with self.assertRaisesRegex(ValueError, "challenge field mismatch"):
            houdai.build_manifest(GOOD, None, bad)
        manifest = houdai.build_manifest(GOOD)
        manifest["playable"] = True
        with self.assertRaisesRegex(ValueError, "playability"):
            houdai.validate_manifest(manifest)

    def test_missing_prerequisite_is_exact(self):
        text = houdai.missing_prerequisite()
        self.assertIn("ch_MUKI_houdai.txt", text)
        self.assertIn("GPVE01", text)

    def test_sha256_helper_rejects_non_bytes(self):
        with self.assertRaises(ValueError):
            houdai.sha256_bytes("not-bytes")
        self.assertEqual(len(houdai.sha256_bytes(b"abc")), 64)


if __name__ == "__main__":
    unittest.main()