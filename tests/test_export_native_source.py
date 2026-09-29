import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import export_native_source  # noqa: E402


def _git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


class ExportNativeSourceTest(unittest.TestCase):
    def _repo(self, files):
        tmp = Path(tempfile.mkdtemp())
        source = tmp / 'native'
        source.mkdir()
        _git(source, 'init', '-q')
        for name, data in files.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        _git(source, 'add', '-A')
        return source, tmp / 'engine'

    def test_copies_text_and_skips_android_binaries(self):
        source, target = self._repo({
            'src/game.cpp': b'int main() {}\n',
            'android/app/icon.png': b'\x89PNG\x00\x01',
            'third_party/SDL2-android/demo/font.bmp': b'BM\x00\x00',
            'pc_port/touch/assets/art/whistle.png': b'\x89PNG\x00\x02',
        })
        export_native_source.export(source, target)
        self.assertEqual((target / 'src/game.cpp').read_bytes(), b'int main() {}\n')
        self.assertFalse((target / 'android').exists())
        self.assertFalse((target / 'third_party').exists())
        self.assertFalse((target / 'pc_port/touch/assets').exists())

    def test_unexpected_binary_still_stops_the_export(self):
        source, target = self._repo({
            'src/game.cpp': b'int main() {}\n',
            'pc_port/stray.bin': b'\x00\x01\x02',
        })
        with self.assertRaisesRegex(ValueError, 'pc_port/stray.bin'):
            export_native_source.export(source, target)


if __name__ == '__main__':
    unittest.main()
