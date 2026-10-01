from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from run_pikmin2_captain_combined_sdl import runtime_dependencies


class PackagedCaptainRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.package = self.root / 'package'
        self.package.mkdir()
        self.exe = self.package / 'fixture.exe'
        self.exe.write_bytes(b'not executed')
        self.names = ('libstdc++-6.dll', 'libgcc_s_seh-1.dll',
                      'libwinpthread-1.dll', 'SDL2.dll')
        for name in self.names:
            (self.package / name).write_bytes(name.encode())

    def test_complete_artifact_uses_its_own_runtime(self):
        directory, hashes = runtime_dependencies(self.exe, self.package)
        self.assertEqual(directory, self.package.resolve())
        self.assertEqual(hashes, {name: hashlib.sha256(name.encode()).hexdigest()
                                  for name in self.names})

    def test_executable_local_conflicts_fail_for_every_dependency(self):
        other = self.root / 'other'
        other.mkdir()
        for name in self.names:
            (other / name).write_bytes(name.encode())
        for name in self.names:
            with self.subTest(name=name):
                (other / name).write_bytes(b'different build')
                with self.assertRaisesRegex(ValueError, 'Conflicting executable-local'):
                    runtime_dependencies(self.exe, other)
                (other / name).write_bytes(name.encode())

    def test_incomplete_artifact_never_falls_back_to_local_installation(self):
        for name in self.names:
            with self.subTest(name=name):
                (self.package / name).unlink()
                with self.assertRaises(FileNotFoundError):
                    runtime_dependencies(self.exe, self.package)
                (self.package / name).write_bytes(name.encode())


if __name__ == '__main__':
    unittest.main()
