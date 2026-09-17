"""Focused tests for the #651 host-mode registration packet (#661)."""
import importlib.util
import unittest
from pathlib import Path

MODULE = (Path(__file__).resolve().parents[1] / "experimental"
          / "pikmin2_challenge_mode_registration.py")
_spec = importlib.util.spec_from_file_location("challenge_mode_registration", MODULE)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

ANCHOR_AFTER = _mod.ANCHOR_AFTER
ANCHOR_NEXT = _mod.ANCHOR_NEXT
GUARD_SHA256 = _mod.GUARD_SHA256
RegistrationError = _mod.RegistrationError
anchors = _mod.anchors
assert_guard = _mod.assert_guard
packet = _mod.packet
GUARD_PATH = Path(r"C:\Users\alari\pikmin-randomizer\scripts\p2_fixture_captain_guard.h")


def sample_cmake():
    return ("top\n" + ANCHOR_AFTER + "\n\n" + ANCHOR_NEXT + "\nbody\n")


class AnchorTests(unittest.TestCase):
    def test_anchors_found_with_blank_between(self):
        where = anchors(sample_cmake())
        self.assertEqual(where["insert_after_line"], 2)
        self.assertEqual(where["next_line"], 4)
        self.assertEqual(where["after"], ANCHOR_AFTER)

    def test_anchors_fail_closed(self):
        for text in ("", "no anchors here\n",
                     sample_cmake().replace(ANCHOR_AFTER, "removed"),
                     sample_cmake().replace(ANCHOR_NEXT, "removed"),
                     ANCHOR_AFTER + "\nnonblank\n" + ANCHOR_NEXT + "\n"):
            with self.subTest(text=text[:30]), self.assertRaises(RegistrationError):
                anchors(text)


class GuardTests(unittest.TestCase):
    def test_canonical_guard_hash_pinned(self):
        self.assertEqual(assert_guard(GUARD_PATH), GUARD_SHA256)

    def test_guard_hash_drift_fails_closed(self):
        drift = Path(__file__).parent / "_guard_drift.tmp"
        try:
            drift.write_text("#ifndef X\n#endif\n", encoding="utf-8")
            with self.assertRaises(RegistrationError):
                assert_guard(drift)
        finally:
            drift.unlink(missing_ok=True)


class PacketTests(unittest.TestCase):
    def test_packet_shape_and_patch_hash(self):
        p = packet(sample_cmake(), GUARD_PATH, {"fixture": "deadbeef"})
        for key in ("schema", "issue", "fixture", "host_module", "host_header",
                    "guard_header", "guard_sha256", "anchor", "patch",
                    "patch_sha256", "validation", "source_pins",
                    "review_owner", "downstream"):
            self.assertIn(key, p)
        self.assertEqual(p["issue"], 661)
        self.assertEqual(p["guard_sha256"], GUARD_SHA256)
        self.assertEqual(len(p["patch_sha256"]), 64)
        self.assertIn("#186", p["review_owner"])
        self.assertTrue(any("#651" in d for d in p["downstream"]))

    def test_patch_does_not_edit_guard_or_shared_headers(self):
        p = packet(sample_cmake(), GUARD_PATH, {})
        self.assertIn("tools/p2_challenge_mode_fixture.cpp", p["patch"])
        self.assertIn("pc_port/pc_p2_challenge_mode.cpp", p["patch"])
        self.assertIn("${CMAKE_SOURCE_DIR}/../scripts", p["patch"])
        self.assertNotIn("p2_fixture_captain_guard.h\n+++", p["patch"])

    def test_patch_is_deterministic(self):
        a = packet(sample_cmake(), GUARD_PATH, {})["patch_sha256"]
        b = packet(sample_cmake(), GUARD_PATH, {})["patch_sha256"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
