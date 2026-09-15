"""Tests for experimental/pikmin2_groink_carcass_teki (#198/#209).

Guards the lane 21 slice 2 native seam: an ordered run-log validator for the
Groink carcass revival markers (READY -> BECOME -> GAUGE_ACTIVE -> KILL_PELLET ->
BIRTH) that flips when the carcass-birth marker is stripped or reordered, plus
the p2-groink-teki.txt profile writer. A secondary static source-guard (only
when PIKMIN_NATIVE_ROOT points at the native worktree) confirms the seam source
still references every marker.
"""
import os
from pathlib import Path
import unittest

from experimental import pikmin2_groink_carcass_teki as teki

SAMPLE_LOG = (
    "P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=30.000 recovery=10.000 max_health=1200.000\n"
    "P2_GROINK_CARCASS_BECOME generator=201001 pos=34.000,30.000,1896.000 face_dir=1.250\n"
    "P2_GROINK_CARCASS_GAUGE_ACTIVE generator=201001 timer=30.000\n"
    "P2_GROINK_CARCASS_KILL_PELLET generator=201001 health=1200.000\n"
    "P2_GROINK_CARCASS_BIRTH generator=201001 pos=34.000,30.000,1896.000 face_dir=1.250 "
    "existence_length=-1.000 in_piklopedia=0 health=1200.000\n"
)


class RunLogValidatorTests(unittest.TestCase):
    def test_ordered_log_passes(self):
        evidence = teki.validate_log(SAMPLE_LOG)
        self.assertTrue(evidence["passed"], evidence["missing"])
        self.assertEqual(evidence["missing"], [])

    def test_birth_marker_stripped_flips(self):
        stripped = SAMPLE_LOG.replace("P2_GROINK_CARCASS_BIRTH generator=201001", "")
        evidence = teki.validate_log(stripped)
        self.assertFalse(evidence["passed"])
        self.assertIn("P2_GROINK_CARCASS_BIRTH", evidence["missing"])
        self.assertFalse(teki.has_birth_marker(stripped))

    def test_reordered_birth_flips(self):
        birth_line = "P2_GROINK_CARCASS_BIRTH generator=201001 pos=34.000,30.000,1896.000 face_dir=1.250 existence_length=-1.000 in_piklopedia=0 health=1200.000\n"
        kill_line = SAMPLE_LOG.splitlines()[3] + "\n"
        reordered = SAMPLE_LOG.replace(birth_line, "").replace(kill_line, birth_line + kill_line)
        evidence = teki.validate_log(reordered)
        self.assertFalse(evidence["passed"])
        self.assertIn("P2_GROINK_CARCASS_BIRTH", evidence["missing"])

    def test_missing_gauge_activate_flips(self):
        stripped = SAMPLE_LOG.replace("P2_GROINK_CARCASS_GAUGE_ACTIVE generator=201001 timer=30.000\n", "")
        evidence = teki.validate_log(stripped)
        self.assertFalse(evidence["passed"])
        self.assertIn("P2_GROINK_CARCASS_GAUGE_ACTIVE", evidence["missing"])

    def test_blank_log_fails_everything(self):
        evidence = teki.validate_log("")
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["missing"], list(teki.ORDER))

    def test_injected_kill_line_does_not_break_validation(self):
        kill_line = "P2_GROINK_CARCASS_KILL_INJECTED host=generated_Frog generator=201001 method=pcEscapeNow health_write=1\n"
        evidence = teki.validate_log(kill_line + SAMPLE_LOG)
        self.assertTrue(evidence["passed"], evidence["missing"])
        self.assertEqual(evidence["missing"], [])


class InjectedKillMarkerTests(unittest.TestCase):
    KILL_LINE = ("P2_GROINK_CARCASS_KILL_INJECTED host=generated_Frog generator=201001 "
                 "method=pcEscapeNow health_write=1")
    READY_LINE = ("P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=2.000 "
                  "recovery=3.000 max_health=1200.000")

    def test_is_injected_kill_true_for_kill_line(self):
        self.assertTrue(teki.is_injected_kill(self.KILL_LINE))

    def test_is_injected_kill_false_for_ready_line(self):
        self.assertFalse(teki.is_injected_kill(self.READY_LINE))

    def test_label_kill_line(self):
        self.assertEqual(teki.injected_kill_label(self.KILL_LINE), "injected (pcEscapeNow)")

    def test_label_ready_line(self):
        self.assertEqual(teki.injected_kill_label(self.READY_LINE), "-")


class PodReceiptTests(unittest.TestCase):
    RECEIPT_LINE = ("[Pikipelago] P2_POD_RECEIPT id=corpse:groink:201001 value=5 "
                    "new=1 pokos=5 seeds=0")

    def test_has_groink_receipt_true_for_receipt_line(self):
        self.assertTrue(teki.has_groink_receipt(self.RECEIPT_LINE))

    def test_has_groink_receipt_false_for_ready_line(self):
        self.assertFalse(teki.has_groink_receipt(
            "P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=2.000 "
            "recovery=3.000 max_health=1200.000"))

    def test_receipt_generator_captured(self):
        self.assertEqual(teki.groink_receipt_generator(self.RECEIPT_LINE), 201001)

    def test_receipt_generator_none_when_absent(self):
        self.assertIsNone(teki.groink_receipt_generator(SAMPLE_LOG))
        self.assertEqual(teki.POD_RECEIPT_PREFIX, "P2_POD_RECEIPT id=corpse:groink:")


class NaturalDeathTimelineTests(unittest.TestCase):
    KILL_LINE = ("P2_GROINK_CARCASS_KILL_INJECTED host=generated_Frog generator=201001 "
                 "method=pcEscapeNow health_write=1\n")

    def test_natural_death_has_become_without_injection(self):
        timeline = teki.natural_death_timeline(SAMPLE_LOG)
        self.assertTrue(timeline["natural"])
        self.assertFalse(timeline["injected"])
        self.assertTrue(timeline["ordered"])

    def test_injected_kill_line_flips_to_injected(self):
        timeline = teki.natural_death_timeline(self.KILL_LINE + SAMPLE_LOG)
        self.assertTrue(timeline["injected"])
        self.assertFalse(timeline["natural"])
        self.assertTrue(timeline["ordered"])


class SidecarConfigTests(unittest.TestCase):
    def test_writer_roundtrip(self):
        text = teki.sidecar_config(201001, 0, 30.0, 10.0, 1200.0)
        lines = text.splitlines()
        self.assertEqual(lines[0], teki.CONFIG_MAGIC)
        self.assertEqual(lines[1], "1")
        self.assertEqual(lines[2].split(), ["201001", "0", "30.0", "10.0", "1200.0"])

    def test_writer_rejects_invalid_identity(self):
        for generator in (0, -1, 1 << 32, 0x1_0000_0000):
            with self.assertRaises(ValueError):
                teki.sidecar_config(generator, 0)
        with self.assertRaises(ValueError):
            teki.sidecar_config(201001, -1)
        with self.assertRaises(ValueError):
            teki.sidecar_config(201001, 0, recovery_seconds=0.0)

    def test_writer_rejects_nonfinite_config(self):
        with self.assertRaises(ValueError):
            teki.sidecar_config(201001, 0, gauge_delay=float("nan"))
        with self.assertRaises(ValueError):
            teki.sidecar_config(201001, 0, max_health=float("inf"))

    def test_short_writer_tokens(self):
        text = teki.sidecar_config_short(201001, 0)
        self.assertEqual(text.splitlines()[2].split(), ["201001", "0", "2.0", "3.0", "1200.0"])


class NativeSourceTests(unittest.TestCase):
    def test_real_native_sidecar_keeps_birth_marker(self):
        source = teki.native_source()
        if source is None:
            self.skipTest("PIKMIN_NATIVE_ROOT not set or pc_p2_groink_teki.cpp missing")
        text = source.read_text(encoding="utf-8", errors="replace")
        evidence = teki.validate_source(text)
        self.assertTrue(evidence["passed"], evidence["missing"])
        self.assertTrue(teki.has_birth_marker(text))


if __name__ == "__main__":
    unittest.main()
