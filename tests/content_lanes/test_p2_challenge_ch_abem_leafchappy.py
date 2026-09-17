"""Focused P1 tests for the ch_ABEM_LeafChappy runtime import (issue #550).

Synthetic tables exercise the import boundary (decode/map/validate,
malformed/missing input); the real ISO exercises the pinned source end to
end. No test boots an engine, spawns an actor, or claims a gate.

Run directly: py -3.12 tests/content_lanes/test_p2_challenge_ch_abem_leafchappy.py
(hyphenated lane files cannot be imported by unittest discovery).
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_adapter():
    path = (ROOT / "experimental" / "content_lanes"
            / "p2-challenge-ch_abem_leafchappy.py")
    spec = importlib.util.spec_from_file_location(
        "p1_leafchappy_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p1 = _load_adapter()
from experimental.content_lanes import p2_challenge_ch_abem_leafchappy as p0

ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
HAVE_ISO = ISO.is_file()

HOST_CHAIN = """P2_CHALLENGE_MODE_BOOT cave=ch_ABEM_LeafChappy ui_index=17
P2_CHALLENGE_MODE_TICK cave=ch_ABEM_LeafChappy ui_index=17
P2_CHALLENGE_MODE_TICK cave=ch_ABEM_LeafChappy ui_index=17
P2_CHALLENGE_MODE_DONE end=none score=485
"""


def real_bytes():
    return p0.read_iso_entry(str(ISO))


def real_manifest():
    return p1.stage_manifest(iso_path=str(ISO))


class ManifestTests(unittest.TestCase):
    def test_exactly_one_source(self):
        with self.assertRaises(ValueError):
            p1.stage_manifest()
        with self.assertRaises(ValueError):
            p1.stage_manifest(raw_bytes=b"x", iso_path=str(ISO))

    def test_tampered_bytes_rejected(self):
        with self.assertRaises(ValueError):
            p1.stage_manifest(raw_bytes=b"not the stage")

    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_real_manifest_fields(self):
        manifest = real_manifest()
        self.assertEqual(manifest["schema"], "p2-challenge-import-p1-1")
        self.assertEqual(manifest["stage_id"], "ch_ABEM_LeafChappy")
        self.assertEqual(manifest["source_sha256"], p0.SOURCE_SHA256)
        self.assertEqual(len(manifest["floors"]), 2)
        self.assertEqual(manifest["starting_squad"], 30)
        self.assertEqual(manifest["ui_index"], 17)
        self.assertEqual(manifest["floor_seconds"], [85.0, 100.0])
        self.assertEqual((manifest["bitter_sprays"], manifest["spicy_sprays"]),
                         (1, 1))
        self.assertEqual(manifest["treasure_count_field"], 11)


class HostEntryTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_entry_shape_matches_native_struct(self):
        entry = p1.host_stage_entry(real_manifest())
        self.assertEqual(entry["caveId"], "ch_ABEM_LeafChappy")
        self.assertEqual(entry["uiIndex"], 17)
        self.assertEqual(entry["floorCount"], 2)
        self.assertEqual(len(entry["floorSeconds"]), 8)
        self.assertEqual(entry["floorSeconds"][:2], [85.0, 100.0])
        self.assertEqual(len(entry["roster"]), 7)
        self.assertTrue(all(len(row) == 3 for row in entry["roster"]))
        self.assertEqual(sum(sum(row) for row in entry["roster"]), 30)

    def test_bad_roster_rejected(self):
        manifest = {"starting_roster": [[1]], "floor_seconds": [1.0],
                    "floors": [{}], "ui_index": 1, "bitter_sprays": 0,
                    "spicy_sprays": 0}
        with self.assertRaises(ValueError):
            p1.host_stage_entry(manifest)


class LayoutTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_layout_writes_four_files(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            paths = p1.stage_run_layout(manifest, out)
            for key in ("stage", "squad", "expected", "manifest"):
                self.assertTrue(Path(paths[key]).is_file())
            expected = json.loads(Path(paths["expected"]).read_text())
            self.assertEqual(expected["reference_score_zero_receipt"], 485)

    def test_layout_refuses_existing_dir(self):
        manifest = {"starting_roster": [[0] * 3] * 7,
                    "floor_seconds": [85.0, 100.0], "floors": [{}, {}],
                    "stage_id": "x", "ui_index": 17, "bitter_sprays": 1,
                    "spicy_sprays": 1}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception):
                p1.stage_run_layout(manifest, tmp)


class MarkerTests(unittest.TestCase):
    def test_room_boot_baseline(self):
        checks = p1.validate_room_boot_log(
            "Experimental preview window set to 960x540 windowed and centered")
        self.assertTrue(checks["window_960x540"])
        self.assertTrue(checks["centered"])
        self.assertTrue(checks["no_extinction"])
        checks = p1.validate_room_boot_log("extinction screen")
        self.assertFalse(checks["no_extinction"])

    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_host_chain_correlates(self):
        verdict = p1.validate_host_markers(HOST_CHAIN, real_manifest())
        self.assertTrue(verdict["correlated"])
        self.assertTrue(all(verdict["markers"][k]
                            for k in ("P2_CHALLENGE_MODE_BOOT",
                                      "P2_CHALLENGE_MODE_TICK",
                                      "P2_CHALLENGE_MODE_DONE")))

    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_empty_log_is_not_correlated(self):
        verdict = p1.validate_host_markers("nothing here", real_manifest())
        self.assertFalse(verdict["correlated"])

    def test_captain_down_breaks_correlation(self):
        verdict = p1.validate_host_markers(
            HOST_CHAIN + "P2_FIXTURE_CAPTAIN_DOWN tick=1\n",
            {"stage_id": "ch_ABEM_LeafChappy"})
        self.assertFalse(verdict["correlated"])


class ReferenceTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_ISO, "retail ISO not present")
    def test_reference_score(self):
        self.assertEqual(p1.reference_score(real_manifest()), 485)
        self.assertEqual(p1.reference_score(real_manifest(), pokos=10), 585)

    def test_reference_sets_documented(self):
        self.assertIn("LeafChappy", p1.ENEMY_IDS)
        self.assertIn("Egg", p1.ENEMY_IDS)
        self.assertIn("key", p1.TREASURE_IDS)
        self.assertIn("apple", p1.TREASURE_IDS)

    def test_p0_pin_consistent(self):
        self.assertEqual(p0.SOURCE_SHA256,
                         "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf")
        self.assertEqual(p0.STAGE_ID, "ch_ABEM_LeafChappy")
        self.assertEqual(p0.UI_INDEX, 17)


if __name__ == "__main__":
    unittest.main()