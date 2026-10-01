import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from scripts.test_pikmin2_surface_roundtrip import native_position,run_test


class NativeRoundtripDriverTests(unittest.TestCase):
    def test_native_source_position_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);(path/'surface-position.txt').write_text('token\n-209.618118 80 1159.99622\n')
            self.assertEqual(native_position(path,'token'),[-209.618118,80,1159.99622])
    def test_reject_stale_outside_nonfinite_and_truncated(self):
        cases=('other\n-210 80 1160\n','token\n0 80 0\n','token\n-190 nan 1160\n',
               'token\n-190 85 1160\n','token\n','token\n-190 80 1160\nextra')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            for text in cases:
                with self.subTest(text=text):
                    (path/'surface-position.txt').write_text(text)
                    with self.assertRaises(ValueError):native_position(path,'token')
    def test_existing_output_refused_before_native(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):run_test(SimpleNamespace(output=Path(directory)))

if __name__=='__main__':unittest.main()
