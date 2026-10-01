import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental import pikmin2_cave_water_units as wu

ROOMS = {
    "cave": "forest_1",
    "floor": 1,
    "seed": 468001,
    "salt": 0,
    "entrance": "forest_1:f1:segment:0",
    "hole": "forest_1:f1:segment:1",
    "edges": [["leaf_elec_0", "gate:leaf_elec_0"]],
    "units": [
        {"id": "forest_1:f1:segment:0", "kind": "segment", "hazard": None, "gx": 0, "gz": 0},
        {"id": "choke_water_0", "kind": "choke", "hazard": "water", "gx": 24, "gz": 48},
        {"id": "leaf_elec_0", "kind": "leaf", "hazard": "elec", "gx": 72, "gz": 48},
        {"id": "forest_1:f1:segment:1", "kind": "segment", "hazard": None, "gx": 0, "gz": 96},
        {"id": "gate:leaf_elec_0", "kind": "gate", "hazard": "elec", "gx": 48, "gz": 96},
        {"id": "leaf_water_0", "kind": "leaf", "hazard": "water", "gx": 24, "gz": 144},
    ],
}


def unit_manifest(name, boxes, water_collision_triangles=0):
    return {"units": {name: {
        "status": "converted",
        "assembly_ready": True,
        "material_status": "strict_converter_supported",
        "collision_triangles": 42,
        "water_collision_triangles": water_collision_triangles,
        "water": {
            "schema": 1,
            "boxes": boxes,
            "count": len(boxes),
            "empty": not boxes,
            "surface": boxes[0]["surface"] if boxes else None,
            "native_consumer_implemented": False,
        },
    }}}


BOX = {"id": 0, "min": [-408.0, -102.0, -428.0], "max": [272.0, -2.0, 372.0],
       "surface": -2.0, "runtime_min_y": -1102.0, "lowered_amount": 0.0}


class AssignModelsTests(unittest.TestCase):
    def test_unit_model_path(self):
        self.assertEqual(wu.unit_model_path("room_kingchap_b_tsuchi"),
                         "courses/pikmin2room/p2cave_room_kingchap_b_tsuchi.mod")
        with self.assertRaises(wu.WaterUnitsError):
            wu.unit_model_path("bad name")

    def test_hazard_aware_assignment(self):
        models = wu.assign_models(ROOMS, water_model="water.mod", elec_model="elec.mod",
                                  gate_model="gate.mod")
        self.assertEqual(models["choke_water_0"], "water.mod")
        self.assertEqual(models["leaf_water_0"], "water.mod")
        self.assertEqual(models["leaf_elec_0"], "elec.mod")
        self.assertEqual(models["gate:leaf_elec_0"], "gate.mod")
        self.assertNotIn("forest_1:f1:segment:0", models)

    def test_bad_model_token_rejected(self):
        with self.assertRaises(wu.WaterUnitsError):
            wu.assign_models(ROOMS, water_model="", elec_model="elec.mod", gate_model="gate.mod")

    def test_rooms_without_units_rejected(self):
        with self.assertRaises(wu.WaterUnitsError):
            wu.assign_models({"cave": "x"}, water_model="w", elec_model="e", gate_model="g")


class RunTests(unittest.TestCase):
    def _patches(self, root):
        imports = []

        def fake_import(iso, catalog, dependencies, output, cave_id, approximate):
            imports.append((cave_id, Path(output).name))
            if cave_id == wu.WATER_CAVE:
                return unit_manifest(wu.WATER_UNIT, [BOX], water_collision_triangles=7)
            return unit_manifest(wu.ELEC_UNIT, [])

        def fake_stage(unit_dir, models_dir, name):
            target = Path(models_dir) / wu.unit_model_path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"mod:" + name.encode())
            return target

        def fake_gate(iso, output):
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_bytes(b"gate")
            return {"conversion_policy": "approximate_materials+rigid_bind_pose_bake"}

        return imports, fake_import, fake_stage, fake_gate

    def test_run_builds_hazard_aware_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rooms_path = root / "rooms.json"
            rooms_path.write_text(json.dumps(ROOMS))
            imports, fake_import, fake_stage, fake_gate = self._patches(root)
            with patch.object(wu, "import_units", side_effect=fake_import), \
                 patch.object(wu, "stage_render", side_effect=fake_stage), \
                 patch.object(wu, "convert_e_gate", side_effect=fake_gate):
                manifest = wu.run("iso", "catalog.json", "deps.json", rooms_path, root / "out")
            self.assertEqual(imports, [(wu.WATER_CAVE, "forest_3"), (wu.ELEC_CAVE, "tutorial_2")])
            self.assertEqual(manifest["water_nodes"], 2)
            self.assertEqual(manifest["elec_nodes"], 2)
            self.assertEqual(manifest["geometry"], "real")
            self.assertEqual(manifest["units"][wu.WATER_UNIT]["water"]["count"], 1)
            self.assertEqual(manifest["units"][wu.WATER_UNIT]["water_collision_triangles"], 7)
            self.assertTrue(manifest["validation"]["valid"])
            out = root / "out"
            self.assertTrue((out / "geometry" / "p2-cave-geometry.txt").is_file())
            self.assertTrue((out / "models" / wu.unit_model_path(wu.WATER_UNIT)).is_file())

    def test_run_rejects_unconverted_water_unit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rooms_path = root / "rooms.json"
            rooms_path.write_text(json.dumps(ROOMS))

            def fake_import(iso, catalog, dependencies, output, cave_id, approximate):
                if cave_id == wu.WATER_CAVE:
                    manifest = unit_manifest(wu.WATER_UNIT, [BOX])
                    manifest["units"][wu.WATER_UNIT]["status"] = "unsupported"
                    manifest["units"][wu.WATER_UNIT]["failure"] = "boom"
                    return manifest
                return unit_manifest(wu.ELEC_UNIT, [])

            with patch.object(wu, "import_units", side_effect=fake_import):
                with self.assertRaises(wu.WaterUnitsError):
                    wu.run("iso", "catalog.json", "deps.json", rooms_path, root / "out")


if __name__ == "__main__":
    unittest.main()
