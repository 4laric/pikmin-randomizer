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
