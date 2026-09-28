"""Fail-closed tests for the floor-1 descend handoff emitter (#817).

Covers: clean emission against the real pinned handoffs, missing input,
malformed input and unknown-pin refusal. No engine, no builds, no ADMIT.
"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path("C:/Users/alari/pikmin-randomizer")


def _load_emitter():
    path = (ROOT / "output/workflow/autofill/planning-shards/provider-actor-birth-projectiles"
            / "prepared/tutorial2-floor1-descend-handoff-root/experimental"
            / "pikmin2_tutorial2_floor1_descend_handoff.py")
    spec = importlib.util.spec_from_file_location("descend_handoff", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


EMITTER = _load_emitter()

FLOOR1 = (ROOT / "output/workflow/autofill/planning-shards/caves-tutorial"
          / "prepared/tutorial2-p1/out/handoff.json")
POLICY = (ROOT / "output/workflow/autofill/prerequisites/tutorial2-descend-policy-native"
          / "out/handoff.json")


class EmitTests(unittest.TestCase):
    def test_clean_emission(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "packet.json"
            self.assertEqual(EMITTER.main(
                ["--floor1-handoff", str(FLOOR1), "--policy-handoff", str(POLICY),
                 "--output", str(out)]), 0)
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["downstream"]["issue"], 747)
            self.assertEqual(packet["origin"]["squad_baseline"], 20)
            self.assertEqual(packet["origin"]["anchor"], "hole")
            self.assertEqual(packet["policy"]["entry_version"], "P2_CAVE_ENTRY_4")
            self.assertEqual(packet["policy"]["terminal_floor"], 8)
            self.assertFalse(packet["admit"])
            self.assertRegex(packet["packet_sha256"], r"[0-9a-f]{64}")

    def test_missing_input_refused(self):
        with self.assertRaises(EMITTER.HandoffError):
            EMITTER.emit(str(ROOT / "no-such-handoff.json"), str(POLICY))
        with self.assertRaises(EMITTER.HandoffError):
            EMITTER.emit(str(FLOOR1), "")
        with self.assertRaises(EMITTER.HandoffError):
            EMITTER.emit("", str(POLICY))

    def test_malformed_input_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("{not json")
            bad = handle.name
        with self.assertRaises(EMITTER.HandoffError):
            EMITTER.emit(bad, str(POLICY))
        Path(bad).unlink()

    def test_unknown_pin_refused(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"schema": 1, "lane": "p2-cave-tutorial_2-p1-runtime"}, handle)
            bad = handle.name
        with self.assertRaises(EMITTER.HandoffError):
            EMITTER.emit(bad, str(POLICY))
        Path(bad).unlink()

    def test_wrong_producer_refused(self):
        with self.assertRaises(EMITTER.HandoffError):
            EMITTER.emit(str(POLICY), str(FLOOR1))

    def test_non_json_output_refused(self):
        with self.assertRaises(EMITTER.HandoffError):
            EMITTER.main(["--floor1-handoff", str(FLOOR1), "--policy-handoff",
                          str(POLICY), "--output", "packet.txt"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
