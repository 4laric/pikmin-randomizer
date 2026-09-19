"""Focused fail-closed tests for the 02tile stage-select landing (#705)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experimental.pikmin2_challenge_02tile_stage_select_landing import (
    LandingError,
    render_boot_request_extended,
    select_stage_extended,
    selector_record,
    staged_pins,
    tile_baseline,
    tile_record,
    TILE_KEY,
)


class SelectorReverificationTests(unittest.TestCase):
    def test_selector_bytes_pinned(self):
        record = selector_record()
        self.assertEqual(record["commit"], "01a35f3a5a74ed2a3fe1e07ddcde23184804010e")
        self.assertEqual(record["blob_sha256"],
                         "d8c2413cb60616571e3df02be1f9ef0b40ced36f9580a513fb760fa4203410f0")

    def test_kusachi_still_resolves(self):
        record, source = select_stage_extended("ch_NARI_01kusachi")
        self.assertEqual(source, "base")
        self.assertEqual(record["cave_id"], "ch_NARI_01kusachi")
        self.assertEqual(record["ui_index"], 3)


class TileExtensionTests(unittest.TestCase):
    def test_02tile_resolves_extended(self):
        record, source = select_stage_extended("ch_NARI_02tile")
        self.assertEqual(source, "extended")
        self.assertEqual(record["cave_id"], TILE_KEY)
        self.assertEqual(record["ui_index"], 4)
        self.assertEqual(record["floors"], 2)
        self.assertEqual(record["floor_seconds"], [200.0, 150.0])
        self.assertEqual(record["table_order"], 19)
        self.assertEqual(record["source_sha256"],
                         "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6")
        self.assertEqual(record["bitter_sprays"], 0)
        self.assertEqual(record["spicy_sprays"], 5)

    def test_02tile_matches_canonical_baseline(self):
        base = tile_baseline()
        record = tile_record()
        self.assertEqual(record["cave_path"], base["details"]["cave_path"])
        self.assertEqual(record["ui_index"], base["details"]["ui_index"])

    def test_render_boot_request_02tile(self):
        record, _source = select_stage_extended("ch_NARI_02tile")
        text = render_boot_request_extended(record)
        lines = text.splitlines()
        self.assertEqual(lines[0], "P2_CHALLENGE_STAGE_SELECT_1")
        self.assertIn("ch_NARI_02tile", lines[1])
        self.assertIn("ui_index 4", lines[1])
        self.assertTrue(text.endswith("\n"))

    def test_render_boot_request_kusachi(self):
        record, _source = select_stage_extended("ch_NARI_01kusachi")
        text = render_boot_request_extended(record)
        self.assertTrue(text.startswith("P2_CHALLENGE_STAGE_SELECT_1\n"))
        self.assertIn("ch_NARI_01kusachi", text)

    def test_staged_pins_recorded(self):
        pins = staged_pins()
        self.assertEqual(pins["stage-manifest.json"],
                         "d8634b9c31574f3a4ab383b248d75ec7396ed14ffed7cd15427a6c7f09e7d2cb")
        self.assertEqual(pins["p1-input-package.json"],
                         "5dea109ebb84ba7bbb6386f0b147d6c35b02e1c05ce3609385f56f0bd6ca634c")
        self.assertEqual(pins["run-plan.json"],
                         "7193bedb3198490fc2f11adc76328c596a7faec96faa367dca728ee0351cbeaa")


class RefusalTests(unittest.TestCase):
    def test_unknown_key_refused(self):
        with self.assertRaises(LandingError):
            select_stage_extended("ch_NARI_99nowhere")

    def test_p1_slots_refused(self):
        with self.assertRaises(LandingError) as ctx:
            select_stage_extended("chal2")
        self.assertIn("different namespace", str(ctx.exception))

    def test_empty_key_refused(self):
        with self.assertRaises(LandingError):
            select_stage_extended("")

    def test_non_string_refused(self):
        with self.assertRaises(LandingError):
            select_stage_extended(None)

    def test_render_rejects_wrong_identity(self):
        record, _source = select_stage_extended("ch_NARI_02tile")
        record = dict(record)
        record["cave_id"] = "ch_NARI_03toy"
        with self.assertRaises(LandingError):
            render_boot_request_extended(record)

    def test_render_rejects_missing_fields(self):
        with self.assertRaises(LandingError):
            render_boot_request_extended({"cave_id": TILE_KEY})


if __name__ == "__main__":
    unittest.main()