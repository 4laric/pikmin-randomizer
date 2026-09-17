"""Focused tests for the ypw P1 runtime observation helpers (#552).

Hermetic except for read-only reuse of the done P1 content lane and the
canonical guard header: no disc image, no native build, no runtime. Real
decoded tokens/pins appear only as validated constants, never as invented
placements.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_mat_ypw_p1_runtime_obs import (
    ANCHOR,
    CAVE_ID,
    GUARD_PATH,
    GUARD_SHA256,
    REAL_POOL,
    REAL_SPAWNS,
    REQUIRED_MARKERS,
    ObsError,
    guard_record,
    p1_adapter,
    read_run_log,
    render_generate_manifest,
    render_sidecar,
    stage_fresh_run,
)


class SidecarTest(unittest.TestCase):
    def test_exact_text(self):
        self.assertEqual(
            render_sidecar(),
            "P2_CHALLENGE_CONTENT_1\n"
            "stage ch_MAT_yellow_purple_white 1\n"
            "pool 1_MAT_tower2_toy.txt\n"
            "spawn FminiHoudai_key 1\n"
            "spawn ElecBug_wadou_kaichin 2\n"
            "spawn GasHiba 1\n"
            "anchor hole\n")

    def test_real_tokens_pinned(self):
        self.assertEqual(REAL_SPAWNS,
                         (("FminiHoudai_key", 1),
                          ("ElecBug_wadou_kaichin", 2), ("GasHiba", 1)))
        self.assertEqual((REAL_POOL, ANCHOR),
                         ("1_MAT_tower2_toy.txt", "hole"))

    def test_refusals(self):
        with self.assertRaises(ObsError):
            render_sidecar(cave_id="ch_OTHER")
        with self.assertRaises(ObsError):
            render_sidecar(floor=2)
        with self.assertRaises(ObsError):
            render_sidecar(pool="../evil")
        with self.assertRaises(ObsError):
            render_sidecar(spawns=[])
        with self.assertRaises(ObsError):
            render_sidecar(spawns=[("ok", 1), ("ok", 2)])
        with self.assertRaises(ObsError):
            render_sidecar(spawns=[("bad id", 1)])
        with self.assertRaises(ObsError):
            render_sidecar(spawns=[("ok", 0)])
        with self.assertRaises(ObsError):
            render_sidecar(anchor="portal")

    def test_generate_manifest(self):
        text = render_generate_manifest()
        self.assertEqual(text, "spawn FminiHoudai_key 1\n"
                               "spawn ElecBug_wadou_kaichin 2\n"
                               "spawn GasHiba 1\n")
        with self.assertRaises(ObsError):
            render_generate_manifest([])


class StagingTest(unittest.TestCase):
    def test_fresh_run_requires_fresh_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run"
            target.mkdir()
            with self.assertRaises(ObsError):
                stage_fresh_run(target)

    def test_missing_adapter_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ObsError):
                stage_fresh_run(Path(tmp) / "run",
                                root=str(Path(tmp) / "absent-root"))


class ReaderTest(unittest.TestCase):
    GOOD = ("P2_CHALLENGE_CONTENT_SELECTED cave=ch_MAT_yellow_purple_white\n"
            "P2_CHALLENGE_CONTENT_SPAWN_COVERED id=ElecBug_wadou_kaichin\n"
            "P2_CHALLENGE_CONTENT_READY cave=ch_MAT_yellow_purple_white\n"
            "P2_CHALLENGE_CONTENT_LIVE squad=20 actors=1\n"
            "PASS P2_CHALLENGE_CONTENT_RUN content=1\n")

    def test_good_log_passes(self):
        observations, passed = read_run_log(self.GOOD)
        self.assertTrue(passed)
        self.assertTrue(all(observations["markers"].values()))
        self.assertEqual((observations["squad"], observations["actors"]),
                         (20, 1))

    def test_missing_marker_fails(self):
        observations, passed = read_run_log("PASS P2_CHALLENGE_CONTENT_RUN content=1\n")
        self.assertFalse(passed)

    def test_fail_tokens_fail(self):
        for text in ("P2_FIXTURE_CAPTAIN_DOWN tick=0\n" + self.GOOD,
                     "FAIL KUSACHI something\n" + self.GOOD,
                     "P2 preview: duplicate treasure\n"):
            _, passed = read_run_log(text)
            self.assertFalse(passed, text[:30])

    def test_injected_rejected(self):
        observations, passed = read_run_log(self.GOOD + "injection=1\n")
        self.assertFalse(passed)
        self.assertTrue(observations["injected"])

    def test_empty_fails_closed(self):
        with self.assertRaises(ObsError):
            read_run_log("")
        with self.assertRaises(ObsError):
            read_run_log(None)


class GuardTest(unittest.TestCase):
    def test_guard_hash_pinned(self):
        # Pin gap, recorded honestly: the #632 guard header postdates this
        # lane pinned root base, so it is consumed read-only from the
        # canonical workspace, never vendored into the pinned tree.
        canonical = Path("C:/Users/alari/pikmin-randomizer")
        if not (canonical / "scripts/p2_fixture_captain_guard.h").is_file():
            return  # canonical workspace unavailable: no hash to assert
        record = guard_record(str(canonical))
        self.assertEqual(record["path"], GUARD_PATH)
        self.assertEqual(record["sha256"], GUARD_SHA256)
        self.assertFalse((ROOT / "scripts/p2_fixture_captain_guard.h").exists())

    def test_guard_missing_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ObsError):
                guard_record(tmp)


if __name__ == "__main__":
    unittest.main()
