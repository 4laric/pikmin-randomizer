"""Focused tests for the yakushima_4 P1 floor-1 staging/observation contract (#161).

Synthetic inputs only (no ISO, no engine, no runtime). The real pin probe is
exercise with explicit temporary trees so the blocker reporting is verified
without touching any shared checkout.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "y4p1", ROOT / "experimental/content_lanes/p2-cave-yakushima_4_p1.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def p0_packet(floors=None):
    floors = floors if floors is not None else [
        {"first": 1, "last": 1, "unit_pool": m.UNIT_POOL_FLOOR1, "enemies": 8,
         "treasures": 2, "gates": 0, "caps": 2,
         "treasure_ids": ["baum_kuchen_s", "chocoichigo"]},
        {"first": 2, "last": 2, "unit_pool": "3_units_h_k_pypes_conc.txt", "enemies": 8,
         "treasures": 2, "gates": 1, "caps": 0, "treasure_ids": ["donutschoco"]},
    ]
    return {"schema": m.P0_SCHEMA, "source_id": m.SOURCE_ID,
            "source_sha256": "a" * 64, "floors": floors}


def write_p0(directory, packet=None):
    path = Path(directory) / "audit-packet.json"
    path.write_text(json.dumps(packet if packet is not None else p0_packet()))
    return path


class StagingContractTests(unittest.TestCase):
    def test_floor1_plan_from_real_shape(self):
        plan = m.floor1_plan(p0_packet())
        self.assertEqual(plan["unit_pool"], m.UNIT_POOL_FLOOR1)
        self.assertEqual(plan["enemy_definitions"], 8)
        self.assertEqual(plan["treasure_definitions"], 2)
        self.assertEqual(plan["treasure_ids"], ["baum_kuchen_s", "chocoichigo"])

    def test_floor1_pool_drift_rejected(self):
        packet = p0_packet()
        packet["floors"][0]["unit_pool"] = "other_pool.txt"
        with self.assertRaisesRegex(m.StagingError, "unit pool drift"):
            m.floor1_plan(packet)

    def test_missing_floor1_rejected(self):
        packet = p0_packet(floors=[{"first": 2, "last": 2,
                                    "unit_pool": "x.txt", "enemies": 1,
                                    "treasures": 1, "treasure_ids": []}])
        with self.assertRaisesRegex(m.StagingError, "no floor-1 entry"):
            m.floor1_plan(packet)

    def test_wrong_p0_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_p0(directory, dict(p0_packet(), source_id="forest_2"))
            with self.assertRaisesRegex(m.StagingError, "identity"):
                m.load_p0_packet(path)

    def test_entry_line_bounds(self):
        self.assertEqual(m.cave_entry_line(1, 20, 1.0, "tok"),
                         "P2_CAVE_ENTRY_1 tok 1 1 20")
        for args in ((3, 20, 1.0, "tok"), (1, 0, 1.0, "tok"),
                     (1, 101, 1.0, "tok"), (1, 20, 0.0, "tok"),
                     (1, 20, 1.0, "bad token")):
            with self.assertRaises(m.StagingError):
                m.cave_entry_line(*args)

    def test_provider_pins_report_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "native/pc_port").mkdir(parents=True)
            (base / "root/experimental/content_lanes").mkdir(parents=True)
            pins = m.provider_pins(base / "root", base / "native")
            self.assertFalse(pins["boot_possible"])
            self.assertIn("pc_port/pc_p2_cave_generate.h", pins["missing_native_provider_files"])
            self.assertFalse(pins["p0_adapter_present"])

    def test_provider_pins_present_when_files_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "native/pc_port").mkdir(parents=True)
            for name in m.PROVIDER_NATIVE_FILES:
                (base / "native" / name).write_text("// placeholder")
            (base / "root/experimental/content_lanes").mkdir(parents=True)
            (base / "root" / m.P0_ADAPTER).write_text("# placeholder")
            pins = m.provider_pins(base / "root", base / "native")
            self.assertTrue(pins["boot_possible"])
            self.assertTrue(pins["p0_adapter_present"])

    def test_staging_manifest_reports_blockers_on_real_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            path = write_p0(directory)
            packet = m.staging_manifest(path, base / "root", base / "native")
            self.assertEqual(packet["floor"]["unit_pool"], m.UNIT_POOL_FLOOR1)
            self.assertFalse(packet["floor1_unit_staging_observed"])
            self.assertFalse(packet["generated"])
            self.assertTrue(any("#129" in b for b in packet["blockers"]))
            self.assertTrue(any("unit-staging consumer" in b for b in packet["blockers"]))


class ObservationContractTests(unittest.TestCase):
    READY = "P2_CAVE_READY floor=1 survivors=20 health=1"
    NAV = ("P2_CAVE_NAV seq=1 floor=1 captain=1 x=1.0 y=2.0 z=3.0 heading_rad=0.0 "
           "anchor_x=1.0 anchor_y=2.0 anchor_z=3.0 dx=0.0 dz=0.0 horizontal=0.0 "
           "vertical=0.0 radius=5.0 inside=1 state=3 walk=1 safe=1 pause=0 ui=0 "
           "movie=0 day_end=0 completed=0 pod=1 interaction_eligible=1 marker=none draws=0")

    def test_positive_observation(self):
        events = m.parse_observation(self.READY + "\n" + self.NAV + "\n")
        report = m.validate_observation(events)
        self.assertEqual(report["collision_routes"], "observed")
        self.assertEqual(report["unit_staging"], "NOT_OBSERVED")
        self.assertEqual(report["walk_inside_samples"], 1)

    def test_missing_ready_refused(self):
        with self.assertRaisesRegex(m.StagingError, "no P2_CAVE_READY"):
            m.validate_observation(m.parse_observation(self.NAV + "\n"))

    def test_wrong_floor_refused(self):
        with self.assertRaisesRegex(m.StagingError, "not floor 1"):
            m.validate_observation(m.parse_observation(self.READY.replace("floor=1", "floor=2") + "\n"))

    def test_no_nav_samples_refused(self):
        with self.assertRaisesRegex(m.StagingError, "no P2_CAVE_NAV"):
            m.validate_observation(m.parse_observation(self.READY + "\n"))

    def test_never_walk_inside_refused(self):
        nav = self.NAV.replace("inside=1", "inside=0")
        with self.assertRaisesRegex(m.StagingError, "never walked inside"):
            m.validate_observation(m.parse_observation(self.READY + "\n" + nav + "\n"))

    def test_unit_staging_never_inferred(self):
        events = m.parse_observation(self.READY + "\n" + self.NAV + "\n")
        self.assertNotIn("unit_staging_observed", m.validate_observation(events))


if __name__ == "__main__":
    unittest.main()
