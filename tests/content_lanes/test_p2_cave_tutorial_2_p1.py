"""Focused P1 tests for the tutorial_2 floor-1 staging adapter (#152)."""
import json
import tempfile
import unittest
from pathlib import Path

import experimental.content_lanes  # noqa: F401  (namespace import guard)

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "p2_cave_tutorial_2_p1",
    ROOT / "experimental" / "content_lanes" / "p2-cave-tutorial_2_p1.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

PACKET = {
    "schema": "p2-cave-tutorial_2-p0/1", "source_id": "tutorial_2",
    "source_path": "user/Mukki/mapunits/caveinfo/tutorial_2.txt",
    "floor_count": 9,
    "floors": [
        {"floor": 1, "unit_pool": "3_MAT_mid1_mid2_uzu1_snow.txt",
         "enemy_tokens": 10, "treasure_tokens": 2, "missing_treasure": [],
         "tokens": [
             {"source_token": "YellowKochappy", "kind": "exact",
              "base": "YellowKochappy", "carried": None, "drop": 0},
             {"source_token": "YellowKochappy", "kind": "exact",
              "base": "YellowKochappy", "carried": None, "drop": 0},
             {"source_token": "Demon", "kind": "exact",
              "base": "Demon", "carried": None, "drop": 0}]},
        {"floor": 2, "unit_pool": "2_MAT_h335_h447_metal.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
        {"floor": 3, "unit_pool": "p3.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
        {"floor": 4, "unit_pool": "p4.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
        {"floor": 5, "unit_pool": "p5.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
        {"floor": 6, "unit_pool": "p6.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
        {"floor": 7, "unit_pool": "p7.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
        {"floor": 8, "unit_pool": "p8.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
        {"floor": 9, "unit_pool": "p9.txt",
         "enemy_tokens": 1, "treasure_tokens": 0, "missing_treasure": [],
         "tokens": [{"source_token": "Sarai", "kind": "exact",
                     "base": "Sarai", "carried": None, "drop": 0}]},
    ],
    "generated": False,
}


def _write_packet(tmp, payload):
    path = Path(tmp) / "packet.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class AdapterTests(unittest.TestCase):
    def test_plan_is_placement_free(self):
        plan = adapter.staging_plan(PACKET)
        self.assertEqual(plan["cave_id"], "tutorial_2")
        self.assertFalse(plan["generated"])
        self.assertEqual(plan["placements"], [])
        self.assertEqual(plan["unit_pool"], "3_MAT_mid1_mid2_uzu1_snow.txt")
        self.assertEqual(plan["source_sha256"], adapter.SOURCE_SHA256)
        counts = {row["enemy_id"]: row["count"] for row in plan["enemies"]}
        self.assertEqual(counts, {"YellowKochappy": 2, "Demon": 1})
        self.assertEqual(plan["treasure_count"], 2)
        self.assertTrue(plan["treasure_ids_unresolved"])
        self.assertEqual(adapter.validate_plan(plan), [])

    def test_non_exact_token_refused(self):
        bad = json.loads(json.dumps(PACKET))
        bad["floors"][0]["tokens"][0]["kind"] = "carrier"
        with self.assertRaisesRegex(ValueError, "non-exact"):
            adapter.staging_plan(bad)

    def test_wrong_coverage_refused(self):
        bad = json.loads(json.dumps(PACKET))
        bad["floors"] = [f for f in bad["floors"] if f["floor"] != 9]
        with self.assertRaisesRegex(ValueError, "coverage"):
            adapter.load_packet(_write_packet(tempfile.mkdtemp(), bad))

    def test_sidecar_roundtrip(self):
        plan = adapter.staging_plan(PACKET)
        text = adapter.sidecar_text(plan)
        self.assertIn("P2_TUTORIAL2_P1_1", text)
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
                assert preset["pool"] == "3_MAT_mid1_mid2_uzu1_snow.txt"
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
            self.assertEqual(provenance["cave"], "tutorial_2")

    def test_missing_shared_builder_refused(self):
        # Integrator compat (#636): the #642 shared builder has since landed
        # on this line, so absence is simulated to keep the fail-closed
        # branch covered instead of asserting on line state.
        import unittest.mock as mock
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
