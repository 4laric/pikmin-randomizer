"""Tests for experimental/pikmin2_groink_carcass_teki (#198/#209).

Guards the lane 21 slice 2 native seam: the Groink carcass sidecar must keep the
ordered P2_GROINK_CARCASS_* markers, and the carcass-birth marker (RequestBirth)
must not be stripped. The pure validator tests always run; the real-source check
only runs when PIKMIN_NATIVE_ROOT points at the native worktree (no lane paths).
"""
import os
from pathlib import Path
import unittest

from experimental import pikmin2_groink_carcass_teki as teki

SYNTHETIC_SOURCE = """\
void pc_p2_groink_teki_setup() {
    std::printf("P2_GROINK_CARCASS_READY generator=%u type=%d gauge_delay=%.3f recovery=%.3f max_health=%.3f\\n", gen, type, a, b, c);
}
void pc_p2_groink_teki_tick(BTeki* t) {
    std::printf("P2_GROINK_CARCASS_BECOME generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f\\n", gen, x, y, z, d);
    std::printf("P2_GROINK_CARCASS_GAUGE_ACTIVE generator=%u timer=%.3f\\n", gen, tmr);
    std::printf("P2_GROINK_CARCASS_GAUGE_INACTIVE generator=%u\\n", gen);
    std::printf("P2_GROINK_CARCASS_KILL_PELLET generator=%u health=%.3f\\n", gen, hp);
    std::printf("P2_GROINK_CARCASS_BIRTH generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f existence_length=%.3f in_piklopedia=%d health=%.3f\\n", gen, x, y, z, d, -1.0f, 0, hp);
}
"""


class MarkerValidatorTests(unittest.TestCase):
    def test_all_markers_present_passes(self):
        evidence = teki.validate(SYNTHETIC_SOURCE)
        self.assertTrue(evidence["passed"], evidence["missing"])
        self.assertEqual(evidence["missing"], [])

    def test_birth_marker_stripped_flips(self):
        stripped = SYNTHETIC_SOURCE.replace(
            'P2_GROINK_CARCASS_BIRTH generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f existence_length=%.3f in_piklopedia=%d health=%.3f',
            '')
        evidence = teki.validate(stripped)
        self.assertFalse(evidence["passed"])
        self.assertIn("P2_GROINK_CARCASS_BIRTH", evidence["missing"])
        self.assertFalse(teki.has_birth_marker(stripped))

    def test_kill_pellet_stripped_flips(self):
        stripped = SYNTHETIC_SOURCE.replace(
            'P2_GROINK_CARCASS_KILL_PELLET generator=%u health=%.3f\\n', '')
        evidence = teki.validate(stripped)
        self.assertFalse(evidence["passed"])
        self.assertIn("P2_GROINK_CARCASS_KILL_PELLET", evidence["missing"])

    def test_blank_source_fails_everything(self):
        evidence = teki.validate("")
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["missing"], list(teki.MARKERS))


class NativeSourceTests(unittest.TestCase):
    def test_real_native_sidecar_keeps_birth_marker(self):
        source = teki.native_source()
        if source is None:
            self.skipTest("PIKMIN_NATIVE_ROOT not set or pc_p2_groink_teki.cpp missing")
        text = source.read_text(encoding="utf-8", errors="replace")
        evidence = teki.validate(text)
        self.assertTrue(evidence["passed"], evidence["missing"])
        self.assertTrue(teki.has_birth_marker(text))


if __name__ == "__main__":
    unittest.main()
