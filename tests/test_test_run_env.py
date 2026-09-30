import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from randomizer import test_run


class TestRunEnvTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workflow = Path(self._tmp.name) / "workflow"
        self.workflow.mkdir()
        patch = mock.patch.dict(os.environ, {"PIKMIN_WORKFLOW_DIR": str(self.workflow)})
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop("PIKMIN_WATCH_RUNS", None)

    def test_default_is_background_and_hidden(self):
        env = test_run.apply_test_run_env({})
        self.assertEqual(env["PIKMIN_RANDOMIZER_TEST_BACKGROUND"], "1")
        self.assertNotIn("PIKMIN_RANDOMIZER_TEST_VISIBLE", env)

    def test_watch_file_adds_visible_and_toggles_live(self):
        marker = self.workflow / "WATCH_RUNS"
        marker.write_text("")
        env = test_run.apply_test_run_env({})
        self.assertEqual(env["PIKMIN_RANDOMIZER_TEST_VISIBLE"], "1")
        self.assertEqual(env["PIKMIN_RANDOMIZER_TEST_BACKGROUND"], "1")
        marker.unlink()
        env = test_run.apply_test_run_env(env)
        self.assertNotIn("PIKMIN_RANDOMIZER_TEST_VISIBLE", env)

    def test_env_var_adds_visible(self):
        env = test_run.apply_test_run_env({"PIKMIN_WATCH_RUNS": "1"})
        self.assertEqual(env["PIKMIN_RANDOMIZER_TEST_VISIBLE"], "1")

    @unittest.skipUnless(hasattr(subprocess, "STARTUPINFO"), "Windows only")
    def test_hidden_startupinfo_dropped_while_watching(self):
        self.assertIsNotNone(test_run.hidden_startupinfo({}))
        self.assertIsNone(test_run.hidden_startupinfo({"PIKMIN_WATCH_RUNS": "1"}))


if __name__ == "__main__":
    unittest.main()
