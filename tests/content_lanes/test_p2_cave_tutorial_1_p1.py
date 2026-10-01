"""Focused P1 tests for the tutorial_1 floor-1 staging adapter (#114)."""
import json
import tempfile
import unittest
from pathlib import Path

import experimental.content_lanes  # noqa: F401  (namespace import guard)

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "p2_cave_tutorial_1_p1",
    ROOT / "experimental" / "content_lanes" / "p2-cave-tutorial_1_p1.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

PACKET = {
    "schema": 1, "cave_id": "tutorial_1",
    "source": "user/Mukki/mapunits/caveinfo/tutorial_1.txt",
    "source_sha256": "5dae39d831ec5b68f16176cc4a54bb828aaed4a4bda10d05aef409c54987a84d",
    "unit_pool_sha256": {"1_units_north_tutorial_snow.txt": "a" * 64},
    "floors": [
        {"first": 1, "last": 1, "unit_pool": "1_units_north_tutorial_snow.txt",
         "unit_names": ["cap_snow", "way3_snow"], "cap_count": 0,
         "enemies": [{"enemy_id": "YellowKochappy", "minimum_count": 4,
                      "selection_weight": 0, "target_count": None,
                      "carried_treasure": None}],
         "treasures": [], "gates": []},
        {"first": 2, "last": 2, "unit_pool": "1_units_purple_snow.txt",
         "unit_names": ["cap_purple"], "enemies": [], "treasures": [], "gates": []},
    ],
    "generated": False, "contract_mismatches": [], "missing_unit_assets": [],
}


def _write_packet(tmp, payload):
    path = Path(tmp) / "packet.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class AdapterTests(unittest.TestCase):
    def test_plan_is_placement_free(self):
        plan = adapter.staging_plan(PACKET)
        self.assertEqual(plan["cave_id"], "tutorial_1")
        self.assertFalse(plan["generated"])
        self.assertEqual(plan["placements"], [])
        self.assertEqual(plan["unit_names"], ["cap_snow", "way3_snow"])
        self.assertEqual(plan["enemies"][0]["enemy_id"], "YellowKochappy")
        self.assertEqual(adapter.validate_plan(plan), [])

    def test_sidecar_roundtrip(self):
        plan = adapter.staging_plan(PACKET)
        text = adapter.sidecar_text(plan)
        self.assertIn("P2_TUTORIAL1_P1_1", text)
        self.assertIn("enemy YellowKochappy", text)
        self.assertTrue(text.endswith("end\n"))

    def test_write_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_packet(tmp, PACKET)
            out = Path(tmp) / "out"
            result = adapter.write_plan(path, out)
            self.assertTrue(Path(result["json"]).is_file())
            self.assertTrue(Path(result["sidecar"]).is_file())
            self.assertEqual(result["problems"], [])

    def test_wrong_cave_fails_closed(self):
        bad = dict(PACKET, cave_id="forest_1")
        with self.assertRaises(ValueError):
            adapter.load_packet(_write_packet(tempfile.mkdtemp(), bad))

    def test_wrong_floor_coverage_fails(self):
        bad = json.loads(json.dumps(PACKET))
        bad["floors"] = bad["floors"][:1]
        with self.assertRaises(ValueError):
            adapter.load_packet(_write_packet(tempfile.mkdtemp(), bad))

    def test_missing_packet_raises(self):
        with self.assertRaises(FileNotFoundError):
            adapter.load_packet("C:/nonexistent/packet.json")

    def test_missing_unit_pool_hash_is_a_problem(self):
        plan = adapter.staging_plan(PACKET)
        plan["unit_pool_sha256"] = None
        self.assertIn("unit_pool_sha256 missing", adapter.validate_plan(plan))

    def test_runtime_inputs_with_injected_renderer(self):
        # Self-contained: no dependency on the #642 shared input builder, which
        # lives on the species wave line only. The adapter accepts an injected
        # renderer; the real shared builder is used at runtime when present.
        class StubRenderer:
            def render_entry(self, preset):
                return "P2_CAVE_ENTRY_1 %s %d 1.0 %d\n" % (
                    preset["token"], preset["floor"], len(preset["squad"]))

            def render_generate(self, preset):
                lines = ["P2_CAVE_GENERATE_1",
                         "pool %s %d" % (preset["pool"], len(preset["units"]))]
                for name, _w, _d, _k in preset["units"]:
                    lines.append("unit %s" % name)
                for sid, count in preset["spawns"]:
                    lines.append("spawn %s %d" % (sid, count))
                lines.append("anchor %s" % preset["anchor"])
                return "\n".join(lines) + "\n"

        plan = adapter.staging_plan(PACKET)
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.build_runtime_inputs(plan, tmp, entry_builder=StubRenderer())
            entry = Path(result["entry"]).read_text(encoding="utf-8")
            generate = Path(result["generate"]).read_text(encoding="utf-8")
            self.assertTrue(entry.startswith("P2_CAVE_ENTRY_1"))
            self.assertIn("YellowKochappy 4", generate)
            self.assertIn("pool 1_units_north_tutorial_snow.txt", generate)
            self.assertEqual(result["provenance"]["cave"], "tutorial_1")

    def test_adapter_plan_works_without_shared_module(self):
        # Content-line portability: the module imports and plans without the
        # #642 shared builder present (it is loaded lazily only at runtime
        # staging). The injected-renderer test above exercises the write path.
        import sys
        self.assertNotIn("experimental.pikmin2_cave_runtime_inputs", sys.modules)
        plan = adapter.staging_plan(PACKET)
        self.assertEqual(adapter.validate_plan(plan), [])


if __name__ == "__main__":
    unittest.main()