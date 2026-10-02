import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from randomizer.native_settings import bind_settings, FILENAME


class NativeSettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.env = {"APPDATA": str(self.base)}
        self.app = self.base / "PikminRandomizer"

    def legacy(self, seed, token, text):
        path = self.app / "sessions" / seed / "runs" / token / FILENAME
        path.parent.mkdir(parents=True)
        path.write_bytes(text)
        return path

    def test_seeds_and_fresh_tokens_share_path(self):
        first = bind_settings(self.env.copy(), self.base / "seed-a")
        second = bind_settings(self.env.copy(), self.base / "seed-b")
        self.assertEqual(first["path"], second["path"])
        self.assertTrue(Path(first["path"]).is_absolute())

    def test_migration_preserves_all_legacy_bytes(self):
        a = self.legacy("a", "1", b"language=fr\n")
        b = self.legacy("b", "2", b"language=fr\n")
        result = bind_settings(self.env, a.parent.parent.parent)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(Path(result["path"]).read_bytes(), a.read_bytes())
        self.assertEqual(b.read_bytes(), b"language=fr\n")

    def test_conflicting_files_warn_without_publication(self):
        self.legacy("a", "1", b"language=fr\n")
        self.legacy("b", "2", b"language=en\n")
        result = bind_settings(self.env, self.base / "other")
        self.assertEqual(result["status"], "legacy-choice-needed")
        self.assertIn("Starting with defaults", result["warning"])
        self.assertIn("close the settings menu", result["warning"])
        self.assertFalse((self.app / FILENAME).exists())

    def test_stable_file_wins_over_conflicts(self):
        self.legacy("a", "1", b"a")
        self.legacy("b", "2", b"b")
        (self.app / FILENAME).write_bytes(b"stable")
        result = bind_settings(self.env, self.base / "other")
        self.assertEqual(result["status"], "existing")
        self.assertEqual(Path(result["path"]).read_bytes(), b"stable")

    def test_private_override_does_not_touch_player_settings(self):
        env = dict(self.env, PIKMIN_SETTINGS_PATH=str(self.base / "private" / FILENAME))
        result = bind_settings(env, self.base / "seed")
        self.assertEqual(result["status"], "explicit")
        self.assertFalse(self.app.exists())

    def test_relative_override_rejected(self):
        with self.assertRaises(ValueError):
            bind_settings(dict(self.env, PIKMIN_SETTINGS_PATH="relative.conf"), self.base)

    def test_background_fixture_is_private_without_override(self):
        env = dict(self.env, PIKMIN_RANDOMIZER_TEST_BACKGROUND="1")
        result = bind_settings(env, self.base / "session", self.base / "run")
        self.assertEqual(Path(result["path"]), self.base / "run" / FILENAME)
        self.assertFalse(self.app.exists())

    def test_empty_override_selects_stable_path(self):
        result = bind_settings(dict(self.env, PIKMIN_SETTINGS_PATH=""), self.base)
        self.assertEqual(result["status"], "new")

    def test_copy_failure_preserves_source_and_no_fallback(self):
        source = self.legacy("a", "1", b"saved")
        with patch("randomizer.native_settings.os.fsync", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                bind_settings(self.env, self.base)
        self.assertEqual(source.read_bytes(), b"saved")
        self.assertFalse((self.app / FILENAME).exists())
        self.assertFalse(list(self.app.glob(".settings-migrate-*")))

    def test_concurrent_publication_never_overwrites_winner(self):
        self.legacy("a", "1", b"old")
        target = self.app / FILENAME
        def collision(*args):
            target.write_bytes(b"other launch")
            raise FileExistsError()
        with patch("randomizer.native_settings.os.link", side_effect=collision):
            result = bind_settings(self.env, self.base)
        self.assertEqual(result["status"], "existing")
        self.assertEqual(target.read_bytes(), b"other launch")

    def test_foreign_temporary_collision_is_preserved(self):
        self.legacy("a", "1", b"saved")
        foreign = self.app / ".settings-migrate-collision"
        foreign.write_bytes(b"not ours")
        with patch("randomizer.native_settings.secrets.token_hex", return_value="collision"):
            with self.assertRaises(FileExistsError):
                bind_settings(self.env, self.base)
        self.assertEqual(foreign.read_bytes(), b"not ours")
        self.assertFalse((self.app / FILENAME).exists())


if __name__ == "__main__":
    unittest.main()
