"""Focused contract tests for the ch_MIYA_trap P0 adapter (issue #560).

Positive pins come from the catalogued baseline (observed values, never
invented): 1 floor, timer [300.0], starting-population total 25 at cell
[3][2], sprays 2/2, treasure field 0, ui_index 26, table_order 27, sha pin
e5b2a21c... The shared cave parser is exercised on a synthetic minimal
1-floor caveinfo text (labeled synthetic, never presented as source
evidence). Negative tests cover malformed/missing inputs and the
missing-source prerequisite boundary.
"""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

WORKTREE = Path("C:/Users/alari/pikmin-randomizer/output/autofill-root-560")
ADAPTER_PATH = WORKTREE / "experimental/content_lanes/p2-challenge-ch_miya_trap.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("p2_challenge_ch_miya_trap", ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()

INVENTORY = json.loads((WORKTREE / "docs/PIKMIN2_CONTENT_INVENTORY.json").read_text(encoding="utf-8"))
LANES = json.loads((WORKTREE / "docs/PIKMIN_CONTENT_IMPORT_LANES.json").read_text(encoding="utf-8"))
ENTRY = next(s for s in INVENTORY["challenge"]["stages"] if s["cave_id"] == "ch_MIYA_trap")
ENEMIES = adapter.enemy_universe_from_inventory(INVENTORY)
TREASURES = adapter.treasure_universe_from_inventory(INVENTORY)
TREASURE = sorted(TREASURES)[0]


def floor_block(first, last, pool, enemies="0", treasures="0", gates="0"):
    return ("{ {f000} 4 %d {f001} 4 %d {f008} -1 %s {_eof} } "
            "{ %s } { %s } { %s }") % (first, last, pool, enemies, treasures, gates)


SYNTHETIC_1 = ("{ {c000} 4 1 {_eof} } 1 "
               + floor_block(0, 0, "poolA.txt", "1 Pelplant 10 1",
                             "1 %s 5" % TREASURE, "1 gateA 100.0 5"))


class LaneEntryTests(unittest.TestCase):
    def test_finds_lane_entry(self):
        entry = adapter.find_lane_entry(LANES)
        self.assertEqual(entry["lane"], "p2-challenge-ch_miya_trap")
        self.assertEqual(entry["issue"], 560)
        self.assertEqual(entry["source"], "user/Mukki/mapunits/caveinfo/ch_MIYA_trap.txt")
        self.assertEqual(entry["source_sha256"], adapter.EXPECTED_SHA256)

    def test_missing_lane_entry(self):
        with self.assertRaises(ValueError):
            adapter.find_lane_entry({"lanes": []})

    def test_lane_entry_wrong_type(self):
        with self.assertRaises(TypeError):
            adapter.find_lane_entry([])

    def test_finds_stage_entry(self):
        stage = adapter.find_stage_entry(INVENTORY)
        self.assertEqual(stage["cave_id"], "ch_MIYA_trap")
        self.assertEqual(stage["floors"], 1)

    def test_missing_stage_entry(self):
        with self.assertRaises(ValueError):
            adapter.find_stage_entry({"challenge": {"stages": []}})

    def test_stage_entry_wrong_type(self):
        with self.assertRaises(TypeError):
            adapter.find_stage_entry([])


class MetadataAuditTests(unittest.TestCase):
    def test_catalogued_pins(self):
        audit = adapter.audit_metadata(ENTRY)
        self.assertEqual(audit["floors"], 1)
        self.assertEqual(audit["floor_seconds"], [300.0])
        self.assertEqual(audit["total_starting_pikmin"], 25)
        self.assertEqual(audit["nonzero_population_cells"], [(3, 2)])
        self.assertEqual(audit["bitter_sprays"], 2)
        self.assertEqual(audit["spicy_sprays"], 2)
        self.assertEqual(audit["treasure_count_field"], 0)
        self.assertEqual(audit["legacy_time"], 0.0)
        self.assertEqual(audit["ui_index"], 26)
        self.assertEqual(audit["table_order"], 27)

    def test_wrong_floor_count(self):
        bad = dict(ENTRY, floors=2)
        with self.assertRaises(ValueError):
            adapter.audit_metadata(bad)

    def test_timer_length_mismatch(self):
        bad = dict(ENTRY, floor_seconds=[300.0, 100.0])
        with self.assertRaises(ValueError):
            adapter.audit_metadata(bad)

    def test_nonpositive_timer(self):
        bad = dict(ENTRY, floor_seconds=[0.0])
        with self.assertRaises(ValueError):
            adapter.audit_metadata(bad)

    def test_ragged_population_matrix(self):
        matrix = [list(row) for row in ENTRY["pikmin_by_native_color_and_maturity"]]
        matrix[3] = [0, 25]
        with self.assertRaises(ValueError):
            adapter.audit_metadata(dict(ENTRY, pikmin_by_native_color_and_maturity=matrix))

    def test_negative_population(self):
        matrix = [list(row) for row in ENTRY["pikmin_by_native_color_and_maturity"]]
        matrix[3][2] = -1
        with self.assertRaises(ValueError):
            adapter.audit_metadata(dict(ENTRY, pikmin_by_native_color_and_maturity=matrix))

    def test_bool_population_rejected(self):
        matrix = [list(row) for row in ENTRY["pikmin_by_native_color_and_maturity"]]
        matrix[0][0] = True
        with self.assertRaises(ValueError):
            adapter.audit_metadata(dict(ENTRY, pikmin_by_native_color_and_maturity=matrix))

    def test_negative_spray(self):
        with self.assertRaises(ValueError):
            adapter.audit_metadata(dict(ENTRY, bitter_sprays=-1))

    def test_string_ui_index(self):
        with self.assertRaises(ValueError):
            adapter.audit_metadata(dict(ENTRY, ui_index="26"))

    def test_non_mapping(self):
        with self.assertRaises(TypeError):
            adapter.audit_metadata([])


class UniverseTests(unittest.TestCase):
    def test_enemy_universe_pins(self):
        self.assertEqual(len(ENEMIES), 102)
        self.assertIn("Pelplant", ENEMIES)

    def test_enemy_universe_missing(self):
        with self.assertRaises(ValueError):
            adapter.enemy_universe_from_inventory({})

    def test_treasure_universe_pins(self):
        self.assertEqual(len(TREASURES), 188)

    def test_treasure_universe_missing(self):
        with self.assertRaises(ValueError):
            adapter.treasure_universe_from_inventory({})


class SourceBoundaryTests(unittest.TestCase):
    def test_hash_reports_drift_honestly(self):
        data = b"synthetic-bytes-not-source"
        report = adapter.verify_source_bytes(data)
        self.assertEqual(report["sha256"], hashlib.sha256(data).hexdigest())
        self.assertFalse(report["match"])

    def test_hash_rejects_text(self):
        with self.assertRaises(TypeError):
            adapter.verify_source_bytes("not-bytes")

    def test_prerequisite_missing(self):
        report = adapter.source_prerequisite()
        self.assertFalse(report["available"])
        self.assertIn(adapter.SOURCE_PATH, report["prerequisite"])
        self.assertIn("No retail ISO", report["prerequisite"])

    def test_prerequisite_present_reports_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / adapter.SOURCE_PATH
            target.parent.mkdir(parents=True)
            target.write_bytes(b"synthetic-bytes-not-source")
            report = adapter.source_prerequisite(tmp)
            self.assertTrue(report["available"])
            self.assertEqual(report["sha256"], hashlib.sha256(b"synthetic-bytes-not-source").hexdigest())
            self.assertFalse(report["match"])


class DecodeBoundaryTests(unittest.TestCase):
    def test_synthetic_one_floor_decode(self):
        parsed = adapter.decode_source_text(SYNTHETIC_1, ENEMIES, TREASURES)
        summary = adapter.summarize_decoded(parsed)
        self.assertEqual(summary["floor_count"], 1)
        self.assertEqual(summary["unit_pools_ordered"], ["poolA.txt"])
        self.assertEqual(summary["unit_pools_distinct"], ["poolA.txt"])
        first = summary["floors"][0]
        self.assertEqual((first["first_floor"], first["last_floor"]), (1, 1))
        self.assertEqual(first["enemy_tokens"], 1)
        self.assertEqual(first["distinct_enemy_ids"], ["Pelplant"])
        self.assertEqual(first["treasure_tokens"], 1)
        self.assertEqual(first["gate_tokens"], 1)
        self.assertFalse(summary["generated"])

    def test_truncated_text_rejected(self):
        with self.assertRaises(ValueError):
            adapter.decode_source_text("{ {c000} 4 1 {_eof} } 1", ENEMIES, TREASURES)

    def test_count_mismatch_rejected(self):
        text = "{ {c000} 4 2 {_eof} } 1 " + floor_block(0, 0, "poolA.txt")
        with self.assertRaises(ValueError):
            adapter.decode_source_text(text, ENEMIES, TREASURES)

    def test_unknown_enemy_rejected(self):
        text = ("{ {c000} 4 1 {_eof} } 1 "
                + floor_block(0, 0, "poolA.txt", "1 NoSuchEnemyXYZ 10 1"))
        with self.assertRaises(ValueError):
            adapter.decode_source_text(text, ENEMIES, TREASURES)

    def test_coverage_mismatch_rejected(self):
        text = "{ {c000} 4 1 {_eof} } 1 " + floor_block(1, 1, "poolA.txt")
        parsed = adapter.decode_source_text(text, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.summarize_decoded(parsed)

    def test_summarize_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            adapter.summarize_decoded([])


class ClosureContractTests(unittest.TestCase):
    def test_closed_pool(self):
        result = adapter.resource_closure_contract(
            ["poolA.txt"], {"user/Mukki/mapunits/units/poolA.txt"})
        self.assertTrue(result["closed"])
        self.assertEqual(result["missing"], [])

    def test_missing_pool_file(self):
        result = adapter.resource_closure_contract(["poolA.txt"], set())
        self.assertFalse(result["closed"])
        self.assertEqual(result["missing"], ["user/Mukki/mapunits/units/poolA.txt"])

    def test_unit_tables_expand_requirements(self):
        available = {"user/Mukki/mapunits/units/poolA.txt",
                     "user/Mukki/mapunits/arc/room1/arc.szs"}
        result = adapter.resource_closure_contract(
            ["poolA.txt"], available, {"poolA.txt": ["room1"]})
        self.assertFalse(result["closed"])
        self.assertEqual(result["missing"], ["user/Mukki/mapunits/arc/room1/texts.szs"])

    def test_missing_disc_set_rejected(self):
        with self.assertRaises(ValueError):
            adapter.resource_closure_contract(["poolA.txt"], None)

    def test_empty_pools_rejected(self):
        with self.assertRaises(ValueError):
            adapter.resource_closure_contract([], set())


class PacketTests(unittest.TestCase):
    def test_packet_shape(self):
        packet = adapter.audit_packet(adapter.audit_metadata(ENTRY),
                                      adapter.source_prerequisite(),
                                      adapter.find_lane_entry(LANES))
        self.assertEqual(packet["schema"], adapter.SCHEMA)
        self.assertEqual(packet["lane"], "p2-challenge-ch_miya_trap")
        self.assertEqual(packet["issue"], 560)
        self.assertEqual(packet["source_sha256_pin"], adapter.EXPECTED_SHA256)
        self.assertFalse(packet["generated"])
        self.assertTrue(packet["limitations"])
        self.assertEqual(packet["lane_entry_issue"], 560)
        self.assertFalse(packet["source"]["available"])

    def test_packet_rejects_bad_metadata(self):
        with self.assertRaises(ValueError):
            adapter.audit_packet({"floors": 2}, adapter.source_prerequisite())

    def test_packet_rejects_bad_prerequisite(self):
        with self.assertRaises(ValueError):
            adapter.audit_packet(adapter.audit_metadata(ENTRY), {})


if __name__ == "__main__":
    unittest.main()