"""Focused tests for the challenge persistence-wiring adapter (#708)."""
import hashlib
import importlib.util
import unittest
from pathlib import Path

MODULE = (Path(__file__).resolve().parents[1] / "experimental"
          / "pikmin2_challenge_persistence_wiring.py")
_spec = importlib.util.spec_from_file_location("persistence_wiring", MODULE)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

pinned_stages = _mod.pinned_stages
stage_keys = _mod.stage_keys
marker_for = _mod.marker_for
probe_artifacts = _mod.probe_artifacts
all_keys = _mod.all_keys
verify_stage_table = _mod.verify_stage_table
verify_table_bytes = _mod.verify_table_bytes
adapter_packet = _mod.adapter_packet
DriftError = _mod.DriftError


class TableTests(unittest.TestCase):
    def test_thirty_stages_pinned(self):
        stages = pinned_stages()
        self.assertEqual(len(stages), 30)
        self.assertEqual(len({s["cave_id"] for s in stages}), 30)
        self.assertEqual(sorted(s["ui_index"] for s in stages), list(range(30)))

    def test_known_rows(self):
        by_id = {s["cave_id"]: s for s in pinned_stages()}
        self.assertEqual(by_id["ch_MAT_route_rover"],
                         {"cave_id": "ch_MAT_route_rover", "ui_index": 27, "floors": 1})
        self.assertEqual(by_id["ch_MAT_crawler"],
                         {"cave_id": "ch_MAT_crawler", "ui_index": 29, "floors": 2})
        self.assertEqual(by_id["ch_NARI_01kusachi"],
                         {"cave_id": "ch_NARI_01kusachi", "ui_index": 3, "floors": 1})
        self.assertEqual(by_id["ch_ABEM_tutorial"],
                         {"cave_id": "ch_ABEM_tutorial", "ui_index": 0, "floors": 2})

    def test_table_bytes_gate(self):
        with self.assertRaises(DriftError):
            verify_table_bytes(b"not the table")
        with self.assertRaises(DriftError):
            verify_table_bytes(b"x" * _mod.SOURCE_TABLE_SIZE)

    def test_real_table_bytes_pin(self):
        iso = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
        if not iso.is_file():
            self.skipTest("local legal disc absent")
        from experimental.pikmin2_assets import disc_files
        catalog = disc_files(iso)
        self.assertIn(_mod.SOURCE_TABLE_PATH, catalog)
        offset, length = catalog[_mod.SOURCE_TABLE_PATH]
        self.assertEqual((offset, length),
                         (_mod.SOURCE_TABLE_OFFSET, _mod.SOURCE_TABLE_SIZE))
        with iso.open("rb") as handle:
            handle.seek(offset)
            data = handle.read(length)
        pin = verify_table_bytes(data)
        self.assertEqual(pin["sha256"], _mod.SOURCE_TABLE_SHA256)


class KeyTests(unittest.TestCase):
    def test_all_stages_map_five_keys(self):
        for stage in pinned_stages():
            keys = stage_keys(stage["cave_id"])
            self.assertEqual(sorted(keys),
                             ["clear", "highscore", "load", "save", "unlock"])
            for field, key in keys.items():
                self.assertEqual(key, "p2_challenge_%s_%s" % (field, stage["cave_id"]))

    def test_probe_artifacts_seven(self):
        artifacts = probe_artifacts("ch_MAT_route_rover")
        self.assertEqual(artifacts, ["challenge_save_key", "challenge_load_key",
                                     "clear_flag", "highscore", "unlock",
                                     "receipt_dedup", "reentry"])

    def test_no_key_collisions(self):
        keys = all_keys()
        self.assertEqual(len(keys), 30 * 5)
        self.assertEqual(len(set(keys)), 30 * 5)

    def test_unknown_stage_rejected(self):
        with self.assertRaises(DriftError):
            stage_keys("ch_NOPE")
        with self.assertRaises(DriftError):
            probe_artifacts("ch_NOPE")

    def test_unsafe_cave_id_rejected(self):
        for bad in ("../evil", "a b", "", "x/y", "a-b"):
            with self.subTest(cave_id=bad), self.assertRaises(DriftError):
                stage_keys(bad)


class DriftTests(unittest.TestCase):
    def test_verify_ok(self):
        self.assertTrue(verify_stage_table(pinned_stages()))

    def test_dropped_row_fails(self):
        with self.assertRaises(DriftError):
            verify_stage_table(pinned_stages()[:-1])

    def test_swapped_ui_fails(self):
        rows = pinned_stages()
        rows[0] = dict(rows[0], ui_index=1)
        with self.assertRaises(DriftError):
            verify_stage_table(rows)

    def test_extra_or_unknown_row_fails(self):
        rows = pinned_stages() + [{"cave_id": "ch_EXTRA", "ui_index": 30, "floors": 1}]
        with self.assertRaises(DriftError):
            verify_stage_table(rows)

    def test_non_mapping_or_missing_key_fails(self):
        rows = pinned_stages()
        rows[5] = "not-a-mapping"
        with self.assertRaises(DriftError):
            verify_stage_table(rows)
        rows = pinned_stages()
        del rows[7]["floors"]
        with self.assertRaises(DriftError):
            verify_stage_table(rows)


class MarkerTests(unittest.TestCase):
    def test_marker_shape(self):
        self.assertEqual(marker_for("challenge_save_key", "ch_MAT_route_rover"),
                         "P2_CHALLENGE_SAVE_KEY stage=ch_MAT_route_rover")
        self.assertEqual(marker_for("clear_flag", "ch_MAT_route_rover"),
                         "P2_CHALLENGE_CLEAR stage=ch_MAT_route_rover")
        self.assertEqual(marker_for("reentry", "ch_MAT_crawler"),
                         "P2_CHALLENGE_REENTRY stage=ch_MAT_crawler")
        self.assertEqual(len({marker_for(a, "ch_MAT_route_rover")
                              for a in _mod.PROBE_ARTIFACTS}), 7)

    def test_unknown_artifact_rejected(self):
        with self.assertRaises(DriftError):
            marker_for("nope", "ch_MAT_route_rover")


class PacketTests(unittest.TestCase):
    def test_packet_shape(self):
        packet = adapter_packet()
        self.assertEqual(packet["schema"], 1)
        self.assertEqual(packet["stage_count"], 30)
        self.assertEqual(packet["source_table"]["sha256"], _mod.SOURCE_TABLE_SHA256)
        self.assertEqual(packet["downstream_consumer"],
                         "p2-challenge-ch_mat_route_rover-p1 (#561)")
        self.assertIn("#186", packet["native_hookup"]["route"])
        self.assertIn("#132", packet["native_hookup"]["owner"])
        self.assertFalse(packet["generated"])
        self.assertEqual(packet["semantic_resolution"], "open")
        self.assertTrue(packet["blockers"] and packet["limitations"])

    def test_packet_stage_map_covers_all(self):
        stage_map = adapter_packet()["stage_map"]
        self.assertEqual(len(stage_map), 30)
        for cave_id, keys in stage_map.items():
            self.assertEqual(keys, stage_keys(cave_id))


if __name__ == "__main__":
    unittest.main()