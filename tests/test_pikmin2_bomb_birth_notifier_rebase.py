"""Focused rebase tests: pins, hook integrity, fail-closed gaps (#726)."""
import unittest
from pathlib import Path

import experimental.pikmin2_bomb_birth_notifier_rebase as rebase


class PinTests(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(rebase.WAVE_PIN,
                         "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54")
        self.assertEqual(rebase.ISSUE, 726)
        self.assertEqual(rebase.NOTIFIER_FILES,
                         ("pc_port/pc_p2_bomb_notifier.h",
                          "pc_port/pc_p2_bomb_notifier.cpp"))
        self.assertEqual(rebase.GUARD_SHA256,
                         "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")

    def test_hook_markers_named(self):
        self.assertIn("pc_p2_bomb_birth_hook_notify", rebase.HOOK_MARKERS)
        self.assertIn("EnemyID_BombOtakara", rebase.HOOK_MARKERS)


class GapTests(unittest.TestCase):
    def test_bogus_pin_fails_closed(self):
        saved = rebase.WAVE_PIN
        rebase.WAVE_PIN = "0" * 40
        try:
            with self.assertRaises(rebase.RebaseGapError):
                rebase.wave_inventory(".")
        finally:
            rebase.WAVE_PIN = saved

    def test_missing_research_path_fails_closed(self):
        with self.assertRaises(Exception):
            rebase.hook_addition_lines(".", "C:/nonexistent/generalEnemyMgr.cpp")

    def test_tampered_copy_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "generalEnemyMgr.cpp"
            target.write_bytes(b"tampered")
            with self.assertRaises(rebase.RebaseGapError):
                rebase.verify_rebased_copy(".", str(target), str(target))


if __name__ == "__main__":
    unittest.main()