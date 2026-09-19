import os
import tempfile
import unittest

from workflow import runner


class WorkerEnvTest(unittest.TestCase):
    def test_prepends_existing_toolchain_dirs_once(self):
        with tempfile.TemporaryDirectory() as tool, tempfile.TemporaryDirectory() as other:
            missing = os.path.join(other, 'nope')
            env = runner.worker_env({'PATH': other}, 'cfg.json', (tool, missing))
            self.assertEqual(env['PATH'].split(os.pathsep), [tool, other])
            self.assertEqual(env['OPENCODE_CONFIG'], 'cfg.json')
            again = runner.worker_env({'PATH': tool.upper() + os.pathsep + other}, 'c', (tool,))
            self.assertEqual(again['PATH'], tool.upper() + os.pathsep + other)


if __name__ == '__main__':
    unittest.main()
