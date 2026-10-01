"""Git-backed snapshot regressions; targets are disposable private test folders."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

EXPORTER = Path(os.environ.get('EXPORTER_UNDER_TEST',
                               str(Path(__file__).resolve().parents[1] / 'scripts/export_native_source.py')))
spec = importlib.util.spec_from_file_location('exporter_under_test', EXPORTER)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class NativeSourceExportTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(os.environ.get('EXPORT_TEST_OUTPUT',
                                       str(Path(__file__).resolve().parents[1] / 'output/native-source-export-tests')))
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'native'
        self.target = Path(self.temp.name) / 'engine'
        self.source.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.source)], check=True)
        subprocess.run(['git', '-C', str(self.source), 'config', 'core.autocrlf', 'false'], check=True)

    def track(self, files):
        for name, data in files.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        subprocess.run(['git', '-C', str(self.source), 'add', '.'], check=True)

    def run_export(self):
        with contextlib.redirect_stdout(io.StringIO()):
            exporter.export(self.source, self.target)

    def target_bytes(self):
        return {str(p.relative_to(self.target)): p.read_bytes()
                for p in self.target.rglob('*') if p.is_file()}

    def test_dirty_tracked_bytes_icons_and_retained_target(self):
        self.track({'src/unit.cpp': b'clean\n',
                    'packaging/icon/nectar.ico': b'\x00desktop-icon',
                    'packaging/icon/open_nectar.png': b'png\x00desktop-icon',
                    'android/app/src/main/res/mipmap-hdpi/ic_launcher.png': b'png\x00mobile-icon',
                    '.github/workflows/build.yml': b'ignored\x00ci',
                    'formatter.exe': b'ignored\x00tool', 'portable.gz': b'ignored\x00archive'})
        dirty = b'// dirty tracked bytes\r\nint value = 7;\n'
        (self.source / 'src/unit.cpp').write_bytes(dirty)
        (self.source / 'untracked-save.bin').write_bytes(b'private\x00save')
        self.target.mkdir()
        (self.target / 'stale.cpp').write_bytes(b'retain-for-manual-review')
        self.run_export()
        self.assertEqual((self.target / 'src/unit.cpp').read_bytes(), dirty)
        for name in ('packaging/icon/nectar.ico', 'packaging/icon/open_nectar.png'):
            self.assertEqual((self.target / name).read_bytes(), (self.source / name).read_bytes())
        self.assertEqual((self.target / 'stale.cpp').read_bytes(), b'retain-for-manual-review')
        for name in ('.git', '.github', 'formatter.exe', 'portable.gz', 'untracked-save.bin', 'android'):
            self.assertFalse((self.target / name).exists(), name)

    def test_late_binary_preserves_existing_target(self):
        self.track({'a.cpp': b'new source', 'z.cpp': b'bad\x00source'})
        self.target.mkdir()
        (self.target / 'a.cpp').write_bytes(b'existing bytes')
        (self.target / 'retained.bin').write_bytes(b'local\x00data')
        before = self.target_bytes()
        with self.assertRaisesRegex(ValueError, 'Unexpected binary source: z.cpp'):
            self.run_export()
        self.assertEqual(self.target_bytes(), before)

    def test_late_binary_does_not_create_absent_target(self):
        self.track({'a.cpp': b'new source', 'z.cpp': b'bad\x00source'})
        with self.assertRaises(ValueError):
            self.run_export()
        self.assertFalse(self.target.exists())

    def test_new_android_binary_is_not_silently_excluded(self):
        self.track({'android/new-resource.bin': b'new\x00resource'})
        with self.assertRaisesRegex(ValueError, 'android/new-resource.bin'):
            self.run_export()
        self.assertFalse(self.target.exists())

    def test_new_vendor_binary_is_not_silently_excluded(self):
        self.track({'third_party/SDL2-android/new-resource.bin': b'new\x00resource'})
        with self.assertRaisesRegex(ValueError, 'third_party/SDL2-android/new-resource.bin'):
            self.run_export()
        self.assertFalse(self.target.exists())

    def test_new_touch_binary_is_not_silently_excluded(self):
        self.track({'pc_port/touch/assets/new-resource.bin': b'new\x00resource'})
        with self.assertRaisesRegex(ValueError, 'pc_port/touch/assets/new-resource.bin'):
            self.run_export()
        self.assertFalse(self.target.exists())

    def test_new_packaging_binary_is_not_silently_copied(self):
        self.track({'packaging/icon/new-resource.bin': b'new\x00resource'})
        with self.assertRaisesRegex(ValueError, 'packaging/icon/new-resource.bin'):
            self.run_export()
        self.assertFalse(self.target.exists())

    def test_missing_tracked_input_preserves_existing_target(self):
        self.track({'a.cpp': b'new source', 'z.cpp': b'missing source'})
        (self.source / 'z.cpp').unlink()
        self.target.mkdir()
        (self.target / 'a.cpp').write_bytes(b'existing bytes')
        before = self.target_bytes()
        with self.assertRaises(FileNotFoundError):
            self.run_export()
        self.assertEqual(self.target_bytes(), before)

    def test_source_change_after_preflight_copies_validated_bytes(self):
        self.track({'a.cpp': b'first source', 'z.cpp': b'validated source'})
        original_mkdir = Path.mkdir
        changed = False

        def mkdir(path, *args, **kwargs):
            nonlocal changed
            result = original_mkdir(path, *args, **kwargs)
            if path.is_relative_to(self.target) and not changed:
                changed = True
                (self.source / 'z.cpp').write_bytes(b'changed\x00after-preflight')
            return result

        with patch.object(Path, 'mkdir', mkdir):
            self.run_export()
        self.assertTrue(changed)
        self.assertEqual((self.target / 'z.cpp').read_bytes(), b'validated source')


if __name__ == '__main__':
    unittest.main()
