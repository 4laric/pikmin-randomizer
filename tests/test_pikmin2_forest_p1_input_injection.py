"""Focused tests for the forest P1 input-injection helpers (#660).

Hermetic: synthetic logs and temp dirs only; the staged-rerun adapter is
loaded read-only for interface shape, never executed against assets. No disc
image, no native build, no runtime.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_forest_p1_input_injection import (
    CLEARED_PREFIX,
    GUARD_PATH,
    GUARD_SHA256,
    INJECTED_PREFIX,
    InjectionError,
    guard_record,
    load_staged_rerun_adapter,
    read_run_log,
    split_injection_phases,
)

GOOD_LOG = ("P2_FOREST_P1_INPUT_WINDOW size=960x540 centered=1\n"
            "P2_FOREST_P1_INPUT_ENGINE_FACT observed=120 squad_alive=20\n"
            "P2_FOREST_INPUT_INJECTED button=START tick=121 injected=1\n"
            "P2_FOREST_INPUT_CLEARED tick=126 injected=1\n"
            "Loading map select screen\n"
            "<<<<<<<<< SAVE Mgr START! >>>>>>>>>\n")


class PhaseTest(unittest.TestCase):
    def test_split(self):
        before, after = split_injection_phases(GOOD_LOG)
        self.assertEqual(len(before), 2)
        self.assertTrue(after[0].startswith(INJECTED_PREFIX))

    def test_no_injection(self):
        before, after = split_injection_phases("boot line\n")
        self.assertEqual(after, [])

    def test_empty_fails(self):
        with self.assertRaises(InjectionError):
            split_injection_phases("")
        with self.assertRaises(InjectionError):
            split_injection_phases(None)


class ReaderTest(unittest.TestCase):
    def test_advance_passes(self):
        observations, passed = read_run_log(GOOD_LOG)
        self.assertTrue(passed)
        self.assertEqual(observations["injected_presses"], 1)
        self.assertTrue(observations["save_started"])
        self.assertTrue(observations["window_960"])

    def test_injection_alone_never_passes(self):
        text = ("P2_FOREST_INPUT_INJECTED button=START tick=1 injected=1\n"
                "heartbeat\n" * 10)
        _, passed = read_run_log(text)
        self.assertFalse(passed)

    def test_fail_tokens_fail(self):
        for text in ("P2_FIXTURE_CAPTAIN_DOWN tick=0\n" + GOOD_LOG,
                     "FAIL FOREST_P1_INPUT timeout\n",
                     "P2 preview: duplicate treasure\n"):
            _, passed = read_run_log(text)
            self.assertFalse(passed, text[:30])

    def test_benign_failed_open_noise_passes(self):
        _, passed = read_run_log(
            'DVDOpen("dataDir/x") -> FAILED to open\n' + GOOD_LOG)
        self.assertTrue(passed)

    def test_injected_rejected(self):
        _, passed = read_run_log(GOOD_LOG + "injection=1\n")
        self.assertFalse(passed)

    def test_empty_fails_closed(self):
        with self.assertRaises(InjectionError):
            read_run_log("")


class AdapterTest(unittest.TestCase):
    def test_adapter_loads(self):
        adapter = load_staged_rerun_adapter()
        self.assertTrue(hasattr(adapter, "stage_run_root"))

    def test_adapter_missing_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InjectionError):
                load_staged_rerun_adapter(str(Path(tmp) / "absent"))

    def test_stage_requires_fresh_dir(self):
        import tempfile
        from experimental.pikmin2_forest_p1_input_injection import stage_injection_run
        adapter = load_staged_rerun_adapter()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run"
            target.mkdir()
            with self.assertRaises(InjectionError):
                stage_injection_run(adapter, "m", "s", "snd", target)


class GuardTest(unittest.TestCase):
    def test_guard_hash_pinned(self):
        canonical = Path("C:/Users/alari/pikmin-randomizer")
        if not (canonical / "scripts/p2_fixture_captain_guard.h").is_file():
            return
        record = guard_record(str(canonical))
        self.assertEqual(record["sha256"], GUARD_SHA256)
        self.assertFalse((ROOT / "scripts/p2_fixture_captain_guard.h").exists())

    def test_guard_missing_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InjectionError):
                guard_record(tmp)


if __name__ == "__main__":
    unittest.main()
