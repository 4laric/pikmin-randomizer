"""Focused tests for the ch_ABEM_tutorial P1 runtime observation adapter (#534)."""
import json
import tempfile
import unittest
from pathlib import Path

import experimental  # noqa: F401  (namespace import guard)

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "abem_tutorial_obs",
    ROOT / "experimental" / "pikmin2_abem_tutorial_p1_runtime_obs.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

MANIFEST = {
    "cave_id": "ch_ABEM_tutorial",
    "floors": [{"number": 1, "unit_pool": "1_units_cent3_tsuchi.txt",
                "enemies": ["Clover"], "treasures": ["key"]},
               {"number": 2, "unit_pool": "2_MAT_mid1_nor2_tsuchi.txt",
                "enemies": ["Egg"], "treasures": []}],
}


class ManifestTests(unittest.TestCase):
    def test_load_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.json"
            path.write_text(json.dumps(MANIFEST), encoding="utf-8")
            loaded = adapter.load_p1_manifest(path)
            self.assertEqual(loaded["cave_id"], "ch_ABEM_tutorial")

    def test_wrong_cave_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.json"
            bad = dict(MANIFEST, cave_id="ch_MUKI_metal")
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cave mismatch"):
                adapter.load_p1_manifest(path)

    def test_missing_manifest_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                adapter.load_p1_manifest(Path(tmp) / "nope.json")


class ReaderTests(unittest.TestCase):
    LOG = ("\n".join([
        "[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)",
        "P2_TUTORIAL2_WINDOW size=960x540 pos=1,1 display=99x99 centered=1",
        "P2_CAVE_READY floor=1 survivors=20 health=1",
        "P2_CAVE_GENERATE_PASS rooms=1 spawns=4 links=0 anchor=hole",
        "P2_TUTORIAL2_P1_PASS floor=1 squad_alive=20 observed=1",
    ]))

    def test_reader_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "native.log"
            path.write_text(self.LOG, encoding="utf-8")
            obs = adapter.read_run_log(path)
            self.assertTrue(obs["window_960x540_centered"])
            self.assertEqual(obs["squad_alive_max"], 20)
            self.assertTrue(obs["generate_pass"])
            self.assertFalse(obs["captain_down"])
            self.assertEqual(obs["cave_ready"], [{"floor": 1, "survivors": 20}])

    def test_reader_captain_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "native.log"
            path.write_text("P2_FIXTURE_CAPTAIN_DOWN tick=0 outcome=BLOCKED\n",
                            encoding="utf-8")
            obs = adapter.read_run_log(path)
            self.assertTrue(obs["captain_down"])
            self.assertFalse(obs["window_960x540_centered"])

    def test_reader_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "native.log"
            path.write_text("nothing here\n", encoding="utf-8")
            obs = adapter.read_run_log(path)
            self.assertEqual(obs["squad_alive_max"], 0)
            self.assertFalse(obs["boot_pass"])


class GateTests(unittest.TestCase):
    def test_live_squad_passes_identity(self):
        obs = {"squad_alive_max": 20, "captain_down": False}
        gates = adapter.classify_gates(obs)
        self.assertEqual(gates["identity_spawn"][0], "PASS")
        self.assertEqual(gates["identity_spawn"][1], "natural")
        for gate in ("movement_animation", "attacks_receivers", "death_corpse",
                     "transport_reward", "cleanup_reentry"):
            self.assertEqual(gates[gate][0], "UNTESTED")

    def test_dead_captain_blocks_identity(self):
        obs = {"squad_alive_max": 0, "captain_down": True}
        gates = adapter.classify_gates(obs)
        self.assertEqual(gates["identity_spawn"][0], "UNTESTED")


if __name__ == "__main__":
    unittest.main()
