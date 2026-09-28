"""Focused staged-rerun tests: JAudio pins, layout validation, verifier (#660)."""
import json
import unittest
from pathlib import Path

import experimental.pikmin2_forest_p1_staged_rerun as rerun


def _manifest(tmp, course="forest"):
    manifest = {"course": course, "caves": []}
    path = Path(tmp) / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _seed(tmp, course="forest"):
    seed = {"schema": "p2-surface-session-1", "course": course, "day": 1}
    path = Path(tmp) / "seed.json"
    path.write_text(json.dumps(seed), encoding="utf-8")
    return path


def _snddata(tmp, with_required=True):
    base = Path(tmp) / "SndData"
    if with_required:
        (base / "Seqs").mkdir(parents=True)
        (base / "Seqs" / "pikiseq.arc").write_bytes(b"SEQSDATA")
        (base / "Banks").mkdir(parents=True, exist_ok=True)
        (base / "Banks" / "pikibank.bx").write_bytes(b"BANKDATA")
        (base / "Banks" / "cave_0.aw").write_bytes(b"WAVEDATA")
    return base


class FakeRunner:
    """Stand-in for the #660 runner interface (staging + validation + verify)."""

    @staticmethod
    def stage_run_layout(manifest_path, seed_path, run_dir, pins):
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
        if seed.get("schema") != "p2-surface-session-1":
            raise ValueError("bad seed schema")
        layout = Path(run_dir) / "forest-p1"
        layout.mkdir(parents=True, exist_ok=True)
        (layout / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (layout / "session-seed.json").write_text(json.dumps(seed), encoding="utf-8")
        record = {"schema": "p2-forest-p1-run-1",
                  "manifest_sha256": "m" * 64, "seed_sha256": "s" * 64,
                  "source_pins": pins, "staged_files": []}
        (layout / "run-metadata.json").write_text(json.dumps(record), encoding="utf-8")
        return record

    @staticmethod
    def validate_run_layout(run_dir):
        meta = Path(run_dir) / "forest-p1" / "run-metadata.json"
        if not meta.is_file():
            return ["missing-or-bad-run-metadata"]
        return []

    @staticmethod
    def verify_run_log(log_text):
        return {"engine_boot": "P2_FOREST_P1_WINDOW" in log_text,
                "boundaries": {},
                "failure_markers": [],
                "overall_pass": "PASS FOREST_P1_RUNTIME" in log_text}


class StageTests(unittest.TestCase):
    def test_stage_pins_jaudio(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            record = rerun.stage_run_root(
                _manifest(tmp), _seed(tmp), _snddata(tmp), run, FakeRunner(), {})
            pins = record["jaudio_pins"]
            self.assertIn("assets/dataDir/SndData/Seqs/pikiseq.arc", pins)
            self.assertIn("assets/dataDir/SndData/Banks/pikibank.bx", pins)
            self.assertIn("assets/dataDir/SndData/Banks/cave_0.aw", pins)
            self.assertTrue((run / "assets" / "dataDir" / "SndData"
                             / "Seqs" / "pikiseq.arc").is_file())

    def test_missing_required_member_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(rerun.StageGapError):
                rerun.stage_run_root(
                    _manifest(tmp), _seed(tmp), _snddata(tmp, with_required=False),
                    Path(tmp) / "run", FakeRunner(), {})

    def test_missing_manifest_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(rerun.StageGapError):
                rerun.stage_run_root(
                    Path(tmp) / "nope.json", _seed(tmp), _snddata(tmp),
                    Path(tmp) / "run", FakeRunner(), {})

    def test_tampered_asset_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            rerun.stage_run_root(
                _manifest(tmp), _seed(tmp), _snddata(tmp), run, FakeRunner(), {})
            target = (run / "assets" / "dataDir" / "SndData" / "Seqs" / "pikiseq.arc")
            target.write_bytes(b"TAMPERED")
            problems = rerun.validate_staged_root(run, FakeRunner())
            self.assertTrue(any("hash-mismatch-staged-asset" in p for p in problems))

    def test_validate_clean(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            rerun.stage_run_root(
                _manifest(tmp), _seed(tmp), _snddata(tmp), run, FakeRunner(), {})
            self.assertEqual(rerun.validate_staged_root(run, FakeRunner()), [])

    def test_load_runner_missing_fails(self):
        with self.assertRaises(rerun.StageGapError):
            rerun.load_runner("C:/nonexistent/runner.py")

    def test_verify_passthrough(self):
        verdict = rerun.verify_run_log(FakeRunner(), "P2_FOREST_P1_WINDOW\nPASS FOREST_P1_RUNTIME\n")
        self.assertTrue(verdict["overall_pass"])
        verdict = rerun.verify_run_log(FakeRunner(), "nothing here\n")
        self.assertFalse(verdict["overall_pass"])

    def test_verify_rejects_non_text(self):
        with self.assertRaises(rerun.StageGapError):
            rerun.verify_run_log(FakeRunner(), None)


if __name__ == "__main__":
    unittest.main()