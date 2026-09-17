"""Focused P1 tests for the tutorial_2 later-floor staging adapter (#747)."""
import json
import tempfile
import unittest
from pathlib import Path

import experimental  # noqa: F401  (namespace import guard)

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "p2_cave_tutorial_2_p1_later_floors",
    ROOT / "experimental" / "content_lanes" / "p2-cave-tutorial_2_p1_later_floors.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def packet_floors():
    floors = []
    pools = ["p1.txt", "2_MAT_h335_h447_metal.txt", "3_MAT_mid1_mid2_uzu1_snow.txt",
             "p4.txt", "p5.txt", "p6.txt", "p7.txt", "p8.txt", "p9.txt"]
    for number in range(1, 10):
        floors.append({"floor": number, "unit_pool": pools[number - 1],
                       "enemy_tokens": 2, "treasure_tokens": 1, "missing_treasure": [],
                       "tokens": [
                           {"source_token": "Sarai", "kind": "exact",
                            "base": "Sarai", "carried": None, "drop": 0},
                           {"source_token": "Bomb", "kind": "exact",
                            "base": "Bomb", "carried": None, "drop": 0}]})
    return floors


PACKET = {
    "schema": "p2-cave-tutorial_2-p0/1", "source_id": "tutorial_2",
    "source_path": "user/Mukki/mapunits/caveinfo/tutorial_2.txt",
    "floor_count": 9, "floors": packet_floors(), "generated": False,
}


def _write_packet(tmp, payload):
    path = Path(tmp) / "packet.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class LaterFloorTests(unittest.TestCase):
    def test_floor1_refused_duplicate_scope(self):
        with self.assertRaisesRegex(ValueError, "not in later-floor scope"):
            adapter.floor_plan(PACKET, 1)

    def test_all_later_floors_plan_clean(self):
        for number in range(2, 10):
            plan = adapter.floor_plan(PACKET, number)
            self.assertEqual(plan["floor"], number)
            self.assertFalse(plan["generated"])
            self.assertEqual(plan["placements"], [])
            self.assertEqual(adapter.validate_plan(plan), [])

    def test_floors2_through_8_are_entry_bootable(self):
        for number in range(2, 9):
            self.assertTrue(adapter.floor_plan(PACKET, number)["entry_bootable"])

    def test_counts_aggregate_tokens(self):
        plan = adapter.floor_plan(PACKET, 2)
        counts = {row["enemy_id"]: row["count"] for row in plan["enemies"]}
        self.assertEqual(counts, {"Bomb": 1, "Sarai": 1})

    def test_sidecar_marks_bootability(self):
        text = adapter.sidecar_text(adapter.floor_plan(PACKET, 4))
        self.assertIn("P2_TUTORIAL2_LATER_1", text)
        self.assertIn("entry_bootable 1", text)
        text2 = adapter.sidecar_text(adapter.floor_plan(PACKET, 2))
        self.assertIn("entry_bootable 1", text2)

    def test_floor9_plan_refused_unknown_cargo(self):
        bad = json.loads(json.dumps(PACKET))
        bad["floors"][8]["tokens"] = [
            {"source_token": "Houdai_light_a", "kind": "unknown_cargo",
             "base": "Houdai", "carried": "light_a", "drop": 0}]
        with self.assertRaisesRegex(ValueError, "unresolvable"):
            adapter.floor_plan(bad, 9)

    def test_runtime_inputs_stub_for_floor2(self):
        class Stub:
            @staticmethod
            def render_entry(preset):
                assert preset["floor"] == 2 and len(preset["squad"]) == 20
                return "ENTRY2"
            @staticmethod
            def render_generate(preset):
                assert preset["pool"] == "2_MAT_h335_h447_metal.txt"
                return "GENERATE2"
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.build_runtime_inputs(
                adapter.floor_plan(PACKET, 2), tmp, entry_builder=Stub)
            self.assertEqual(
                Path(result["entry"]).read_text(encoding="utf-8"), "ENTRY2")
            provenance = json.loads(
                Path(tmp, "p2-cave-runtime-inputs.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["floor"], 2)

    def test_entry4_version_swap_for_floor3(self):
        class Stub:
            @staticmethod
            def render_entry(preset):
                return "P2_CAVE_ENTRY_1 %s %d 1.0 20\n" % ("0" * 32, preset["floor"])
            @staticmethod
            def render_generate(preset):
                return "GENERATE"
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.build_runtime_inputs(
                adapter.floor_plan(PACKET, 3), tmp, entry_builder=Stub)
            first = Path(result["entry"]).read_text(encoding="utf-8").split()[0]
            self.assertEqual(first, "P2_CAVE_ENTRY_4")

    def test_descend_chain(self):
        chain = adapter.descend_plan(2)
        self.assertEqual((chain["from"], chain["to"]), (2, 3))
        with self.assertRaises(ValueError):
            adapter.descend_plan(9)

    def test_write_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.write_floor(_write_packet(tmp, PACKET), tmp, 6)
            self.assertEqual(result["problems"], [])
            self.assertTrue(Path(result["json"]).is_file())


if __name__ == "__main__":
    unittest.main()
