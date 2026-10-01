"""Focused fail-closed tests for the P1 impact freeze-frame diagnosis (#797)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_p1_impact_freeze_frame_diagnosis as diag


def gen4_like():
    # The observed gen-4 signature: PARK baseline, then render-only silence.
    return chr(10).join([
        "P2_CHALLENGE_PARK nx=309.663 ny=0.000 nz=1505.612",
        "P2_CHALLENGE_PARK_ALIVE pikis=1",
        "[PC Port] FPS: 30.0, DeltaTime: 32.4100ms, clamp: 2",
        "[PC Port] Textures: 511 live, 60 MB",
    ]) + chr(10)


class FreezeFrameTests(unittest.TestCase):
    def test_gen4_signature_attributes_engine_owner(self):
        v = diag.attribute(diag.parse(gen4_like()))
        self.assertEqual(v["verdict"], "engine-owner")
        self.assertIn("#649", v["route"])
        self.assertIn("62-65", " ".join(v["pins"]))

    def test_gate_diag_routes_throttle_or_gate(self):
        text = gen4_like() + "P2_CHALLENGE_GATE_DIAG gate=pause observed=1 alive=1 frames=300" + chr(10)
        v = diag.attribute(diag.parse(text))
        self.assertEqual(v["verdict"], "throttle-or-gate")
        self.assertIn("pause", v["detail"])
        self.assertIn("longer-run", v["route"])

    def test_pass_is_passing(self):
        v = diag.attribute(diag.parse(gen4_like() + "PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive" + chr(10)))
        self.assertEqual(v["verdict"], "passing")

    def test_captain_down_blocks(self):
        v = diag.attribute(diag.parse(gen4_like() + "P2_FIXTURE_CAPTAIN_DOWN tick=5 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED" + chr(10)))
        self.assertEqual(v["verdict"], "blocked")

    def test_fail_row_refuses(self):
        v = diag.attribute(diag.parse(gen4_like() + "FAIL challenge boot observer timeout" + chr(10)))
        self.assertEqual(v["verdict"], "refused")

    def test_missing_park_refuses(self):
        v = diag.attribute(diag.parse("[PC Port] FPS: 30.0" + chr(10)))
        self.assertEqual(v["verdict"], "refused")

    def test_partial_progress_unattributable(self):
        text = gen4_like() + "P2_CHALLENGE_SQUAD pikis=1" + chr(10)
        v = diag.attribute(diag.parse(text))
        self.assertEqual(v["verdict"], "unattributable")

    def test_empty_input_refused(self):
        with self.assertRaises(diag.DiagnosisError):
            diag.parse("   " + chr(10))

    def test_missing_file_refused(self):
        with self.assertRaises(diag.DiagnosisError):
            diag.read_log(str(ROOT / "no-such-native.log"))

    def test_packet_shape(self):
        parsed = diag.parse(gen4_like())
        pkt = diag.packet(parsed, diag.attribute(parsed), "native.log", "abc123")
        self.assertEqual(pkt["schema"], diag.SCHEMA)
        self.assertEqual(pkt["verdict"], "engine-owner")
        self.assertEqual(pkt["gates"], "UNTESTED")
        self.assertEqual(pkt["park_baseline_pikis"], 1)
        self.assertEqual(pkt["log"]["sha256"], "abc123")


if __name__ == "__main__":
    unittest.main()