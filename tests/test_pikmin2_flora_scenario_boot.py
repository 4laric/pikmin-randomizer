"""Focused scenario-boot tests: staging, validation, log verdicts (#766)."""
import json
import unittest
from pathlib import Path

import experimental.pikmin2_flora_scenario_boot as boot


def _room(tmp, payload=b"GENBYTES0123456789"):
    path = Path(tmp) / "room.gen"
    path.write_bytes(payload)
    return path


class StageTests(unittest.TestCase):
    def test_stage_layout(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            manifest = boot.stage_arena(_room(tmp), 20, (34.0, 30.0, 1878.0),
                                        Path(tmp) / "arena")
            self.assertEqual(
                [r["identity"] for r in manifest["scenery"]],
                ["Clover", "Tukushi", "Chiyogami"])
            self.assertEqual(
                [(r["source_id"], r["slot"]) for r in manifest["scenery"]],
                [(47, 0), (80, 1), (89, 2)])
            self.assertEqual(manifest["guard"]["sha256"], boot.GUARD_SHA256)
            self.assertEqual(
                boot.validate_arena(Path(tmp) / "arena"), [])

    def test_bad_inputs_fail_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(boot.ArenaGapError):
                boot.stage_arena(Path(tmp) / "nope.gen", 20, (0.0, 0.0, 0.0),
                                 Path(tmp) / "arena")
            with self.assertRaises(boot.ArenaGapError):
                boot.stage_arena(_room(tmp), 0, (0.0, 0.0, 0.0), Path(tmp) / "arena")
            with self.assertRaises(boot.ArenaGapError):
                boot.stage_arena(_room(tmp), 20, ("x", 0.0, 0.0), Path(tmp) / "arena")
            with self.assertRaises(boot.ArenaGapError):
                boot.stage_arena(_room(tmp), 20, (float("nan"), 0.0, 0.0),
                                 Path(tmp) / "arena")

    def test_tampered_room_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arena = Path(tmp) / "arena"
            boot.stage_arena(_room(tmp), 20, (0.0, 0.0, 0.0), arena)
            (arena / "room.gen").write_bytes(b"TAMPERED")
            problems = boot.validate_arena(arena)
            self.assertTrue(any("hash-mismatch-room-gen" in p for p in problems))

    def test_scenery_tamper_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arena = Path(tmp) / "arena"
            boot.stage_arena(_room(tmp), 20, (0.0, 0.0, 0.0), arena)
            manifest_path = arena / "flora-arena.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["scenery"] = manifest["scenery"][:2]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            problems = boot.validate_arena(arena)
            self.assertTrue(any("scenery" in p for p in problems))


class VerdictTests(unittest.TestCase):
    GOOD = ("P2_FLORA_SCENARIO_WINDOW size=960x540\n"
            "P2_FLORA_SCENARIO_SQUAD pikis=20\n"
            "P2_FLORA_SCENARIO_SESSION identity=Clover converted=7 received=7 hauled=0\n"
            "P2_FLORA_SCENARIO_SESSION identity=Tukushi converted=7 received=7 hauled=0\n"
            "P2_FLORA_SCENARIO_SESSION identity=Chiyogami converted=3 received=3 hauled=0\n"
            "PASS FLORA_SCENARIO_BOOT\n")

    def test_full_pass_verdict(self):
        verdict = boot.verify_run_log(self.GOOD)
        self.assertTrue(verdict["window_960x540"])
        self.assertEqual(verdict["squad_counts"], [20])
        self.assertEqual(verdict["identities"],
                         {"Clover": "observed", "Tukushi": "observed",
                          "Chiyogami": "observed"})
        self.assertFalse(verdict["captain_down"])
        self.assertTrue(verdict["overall_pass"])

    def test_missing_identity_unobserved(self):
        verdict = boot.verify_run_log("P2_FLORA_SCENARIO_WINDOW size=960x540\n")
        self.assertEqual(verdict["identities"]["Clover"], "unobserved")
        self.assertFalse(verdict["overall_pass"])

    def test_hauled_contradicts(self):
        log = ("P2_FLORA_SCENARIO_SESSION identity=Clover converted=7 "
               "received=5 hauled=2\n")
        verdict = boot.verify_run_log(log)
        self.assertEqual(verdict["identities"]["Clover"], "contradicted")
        self.assertFalse(verdict["overall_pass"])

    def test_captain_down_blocks(self):
        log = ("P2_FIXTURE_CAPTAIN_DOWN tick=9 hp=0.500 orima_dead=0 "
               "dead_state=1 outcome=BLOCKED\nPASS FLORA_SCENARIO_BOOT\n")
        verdict = boot.verify_run_log(log)
        self.assertTrue(verdict["captain_down"])
        self.assertIn("FLORA_SCENARIO_BOOT", verdict["passes"])
        self.assertFalse(verdict["overall_pass"])

    def test_non_text_fails_closed(self):
        with self.assertRaises(boot.ArenaGapError):
            boot.verify_run_log(None)


class BoundaryTests(unittest.TestCase):
    def test_cli_stage_and_check(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "arena"
            self.assertEqual(boot.main(["--room-gen", str(_room(tmp)),
                                        "--out", str(out)]), 0)
            self.assertEqual(boot.main(["--out", str(out), "--check"]), 0)

    def test_cli_missing_room_refuses(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(boot.main(["--room-gen", str(Path(tmp) / "nope.gen"),
                                        "--out", str(Path(tmp) / "arena")]), 2)


if __name__ == "__main__":
    unittest.main()