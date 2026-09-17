"""Tests for the gap-stages stage-select extension (#743).

Every gap key resolves to a validated boot-selection record; kusachi/02tile
still resolve unchanged through the wrapped byte-pinned selectors; unknown
keys (including P1 chal slots) are refused fail-closed. No runtime, no native
code, no shared edits.
"""
import unittest

from experimental.pikmin2_challenge_gap_stages_select import (
    GAP_KEYS,
    KUSACHI_KEY,
    TILE_KEY,
    GapStagesError,
    base_records,
    gap_record,
    render_boot_request_extended,
    select_stage_extended,
)

EXPECTED_FLOORS = {
    "ch_MUKI_damagumo": 1,
    "ch_MUKI_houdai": 2,
    "ch_NARI_03toy": 2,
    "ch_NARI_06start3hard": 3,
    "ch_MUKI_redblue": 2,
    "ch_NARI_07whitepurple": 2,
}


class GapResolutionTests(unittest.TestCase):
    def test_all_six_gap_keys_resolve(self):
        self.assertEqual(tuple(sorted(GAP_KEYS)), tuple(sorted(EXPECTED_FLOORS)))
        for key in GAP_KEYS:
            with self.subTest(key=key):
                record = gap_record(key)
                self.assertEqual(record["cave_id"], key)
                self.assertEqual(record["floors"], EXPECTED_FLOORS[key])
                self.assertTrue(record["cave_path"].endswith(key + ".txt"))
                self.assertEqual(len(record["source_sha256"]), 64)
                self.assertEqual(len(record["floor_seconds"]), record["floors"])
                text = render_boot_request_extended(record)
                self.assertTrue(text.startswith("P2_CHALLENGE_STAGE_SELECT_1\n"))
                self.assertIn("cave %s " % key, text)

    def test_kusachi_and_02tile_unchanged(self):
        base = base_records()
        self.assertEqual(base["kusachi"]["cave_id"], KUSACHI_KEY)
        self.assertEqual(base["tile"]["cave_id"], TILE_KEY)
        self.assertEqual(base["tile_provenance"], "extended")
        record, provenance = select_stage_extended(KUSACHI_KEY)
        self.assertEqual(provenance, "base")
        self.assertEqual(record["cave_id"], KUSACHI_KEY)
        record, provenance = select_stage_extended(TILE_KEY)
        self.assertEqual(provenance, "landing-extended")
        self.assertEqual(record["cave_id"], TILE_KEY)

    def test_gap_provenance_labelled(self):
        for key in GAP_KEYS:
            with self.subTest(key=key):
                record, provenance = select_stage_extended(key)
                self.assertEqual(provenance, "gap")
                self.assertEqual(record["cave_id"], key)

    def test_unknown_and_p1_keys_refused(self):
        for bad in ("", None, 42, "ch_NARI_99nope", "chal0", "chal4", "CH_MUKI_HOUDAI",
                    " ch_MUKI_houdai", "kusachi"):
            with self.subTest(key=repr(bad)):
                with self.assertRaises(GapStagesError):
                    select_stage_extended(bad)

    def test_render_rejects_foreign_records(self):
        with self.assertRaises(GapStagesError):
            render_boot_request_extended({"cave_id": "ch_NARI_99nope"})
        record = gap_record("ch_MUKI_houdai")
        tampered = dict(record, cave_id="ch_MUKI_damagumo")
        with self.assertRaises(GapStagesError):
            render_boot_request_extended(tampered)


if __name__ == "__main__":
    unittest.main()
