"""Focused P1 tests for the tutorial_3 floor-1 staging adapter (#153)."""
import json
import tempfile
import unittest
from pathlib import Path

import experimental.content_lanes  # noqa: F401  (namespace import guard)

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "p2_cave_tutorial_3_p1",
    ROOT / "experimental" / "content_lanes" / "p2-cave-tutorial_3_p1.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def _enemy(token, base=None):
    return {"source": {"source_token": token, "enemy_id": base or token,
                       "carried_treasure": None, "drop_mode": 0},
            "runtime_status": "unsupported", "placement": None}


def _floor(number, pool, enemies, treasures=(), caps=()):
    return {"first_floor": number, "last_floor": number,
            "parameters": {"f008": pool}, "enemies": enemies,
            "treasures": [{"treasure_id": t} for t in treasures],
            "gates": [], "caps": list(caps)}


PACKET = {
    "schema": "p2-cave-import-p0-1", "cave": "tutorial_3",
    "source": "user/Mukki/mapunits/caveinfo/tutorial_3.txt",
    "source_sha256": adapter.SOURCE_SHA256,
    "floor_coverage": 8,
    "floors": [
        _floor(1, "3_MAT_nor4_hit2_blk1_snow.txt",
               [_enemy("YellowKochappy"), _enemy("YellowKochappy"),
                _enemy("YellowChappy")],
               ["Xmas_item", "teala_dia_a"], [{"empty": False}, {"empty": False}]),
        _floor(2, "p2.txt", [_enemy("RKabuto")], ["chess_king_black"]),
        _floor(3, "p3.txt", [_enemy("LeafChappy")], ["toy_ring_a_green"]),
        _floor(4, "p4.txt", [_enemy("Sarai")], ["toy_ring_c_green"]),
        _floor(5, "p5.txt", [_enemy("Miulin")]),
        _floor(6, "p6.txt", [_enemy("Catfish")], ["chess_king_white"]),
        _floor(7, "p7.txt", [_enemy("BlueChappy")], ["yoyo_red"]),
        _floor(8, "p8.txt", [_enemy("Queen_dashboots")]),
    ],
    "retail_generation": False,
    "playable": False,
}


def _write_packet(tmp, payload):
    path = Path(tmp) / "packet.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class AdapterTests(unittest.TestCase):
    def test_plan_is_placement_free(self):
        plan = adapter.staging_plan(PACKET)
        self.assertEqual(plan["cave_id"], "tutorial_3")
        self.assertFalse(plan["generated"])
        self.assertEqual(plan["placements"], [])
        self.assertEqual(plan["unit_pool"], "3_MAT_nor4_hit2_blk1_snow.txt")
        self.assertEqual(plan["source_sha256"], adapter.SOURCE_SHA256)
        counts = {row["enemy_id"]: row["count"] for row in plan["enemies"]}
        self.assertEqual(counts, {"YellowKochappy": 2, "YellowChappy": 1})
        self.assertEqual(plan["treasure_count"], 2)
        self.assertEqual(plan["treasures"], ["Xmas_item", "teala_dia_a"])
        self.assertEqual(plan["cap_count"], 2)
        self.assertEqual(adapter.validate_plan(plan), [])

    def test_non_exact_token_refused(self):
        bad = json.loads(json.dumps(PACKET))
        bad["floors"][0]["enemies"][0]["source"]["carried_treasure"] = "bolt"
        with self.assertRaisesRegex(ValueError, "non-exact"):
            adapter.staging_plan(bad)

    def test_wrong_coverage_refused(self):
        bad = json.loads(json.dumps(PACKET))
        bad["floors"] = [f for f in bad["floors"] if f["first_floor"] != 8]
        with self.assertRaisesRegex(ValueError, "coverage"):
            adapter.load_packet(_write_packet(tempfile.mkdtemp(), bad))

    def test_source_hash_drift_refused(self):
        bad = json.loads(json.dumps(PACKET))
        bad["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source_sha256"):
            adapter.load_packet(_write_packet(tempfile.mkdtemp(), bad))

    def test_sidecar_roundtrip(self):
        plan = adapter.staging_plan(PACKET)
        text = adapter.sidecar_text(plan)
        self.assertIn("P2_TUTORIAL3_P1_1", text)
        self.assertIn("enemy YellowKochappy count=2", text)
        self.assertIn("treasure_count 2", text)
        self.assertTrue(text.endswith("end\n"))

    def test_write_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.write_plan(_write_packet(tmp, PACKET), tmp)
            self.assertEqual(result["problems"], [])
            self.assertTrue(Path(result["json"]).is_file())
            self.assertTrue(Path(result["sidecar"]).is_file())

    def test_runtime_inputs_stub(self):
        class Stub:
            @staticmethod
            def render_entry(preset):
                assert preset["floor"] == 1 and len(preset["squad"]) == 20
                return "ENTRY"
            @staticmethod
            def render_generate(preset):
                assert preset["pool"] == "3_MAT_nor4_hit2_blk1_snow.txt"
                return "GENERATE"
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.build_runtime_inputs(
                adapter.staging_plan(PACKET), tmp, entry_builder=Stub)
            self.assertEqual(
                Path(result["entry"]).read_text(encoding="utf-8"), "ENTRY")
            self.assertEqual(
                Path(result["generate"]).read_text(encoding="utf-8"), "GENERATE")
            provenance = json.loads(
                Path(tmp, "p2-cave-runtime-inputs.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["cave"], "tutorial_3")

    def test_missing_shared_builder_refused(self):
        # Integrator compat (#636): the #642 shared builder has since landed
        # on this line, so absence is simulated to keep the fail-closed
        # branch covered instead of asserting on line state.
        import unittest.mock as mock
        from pathlib import Path
        real_is_file = Path.is_file

        def fake_is_file(self):
            if self.name == "pikmin2_cave_runtime_inputs.py":
                return False
            return real_is_file(self)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(Path, "is_file", fake_is_file):
                with self.assertRaises(FileNotFoundError):
                    adapter.build_runtime_inputs(
                        adapter.staging_plan(PACKET), tmp)


if __name__ == "__main__":
    unittest.main()
