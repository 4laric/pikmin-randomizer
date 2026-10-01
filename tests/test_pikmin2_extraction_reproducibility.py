import os
from pathlib import Path
import tempfile
import unittest

from scripts.compare_pikmin2_extractions import compare, manifest, write_report


class ReproducibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.left, self.right = self.root / 'left', self.root / 'right'
        for path in (self.left, self.right):
            path.mkdir()
            (path / 'model.mod').write_bytes(b'model\x00')

    def test_identical_contents_ignore_filesystem_mtime(self):
        os.utime(self.left / 'model.mod', (1, 1))
        result = compare(self.left, self.right)
        self.assertTrue(result['identical'])
        self.assertEqual(result['trees'][0]['sha256'], result['trees'][1]['sha256'])

    def test_added_removed_and_changed(self):
        (self.left / 'removed').write_bytes(b'a')
        (self.right / 'added').write_bytes(b'b')
        (self.right / 'model.mod').write_bytes(b'different')
        result = compare(self.left, self.right)
        self.assertFalse(result['identical'])
        self.assertEqual(result['only_left'], ['removed'])
        self.assertEqual(result['only_right'], ['added'])
        self.assertEqual(result['changed'], ['model.mod'])

    def test_json_paths_are_not_normalized(self):
        for directory in (self.left, self.right):
            (directory / 'metadata.json').write_text('{"output": "' + directory.name + '"}')
        self.assertEqual(compare(self.left, self.right)['changed'], ['metadata.json'])

    def test_empty_and_missing_inputs_rejected(self):
        (self.left / 'model.mod').unlink()
        with self.assertRaises(ValueError):
            manifest(self.left)
        with self.assertRaises(ValueError):
            manifest(self.root / 'missing')

    def test_report_cannot_modify_inputs_or_overwrite(self):
        with self.assertRaises(ValueError):
            write_report(self.left, self.right, self.left / 'new.json')
        self.assertFalse((self.left / 'new.json').exists())
        output = self.root / 'report.json'
        self.assertTrue(write_report(self.left, self.right, output)['identical'])
        original = output.read_bytes()
        with self.assertRaises(ValueError):
            write_report(self.left, self.right, output)
        self.assertEqual(output.read_bytes(), original)

    def test_linked_directory_rejected(self):
        link = self.left / 'linked'
        try:
            link.symlink_to(self.right, target_is_directory=True)
        except OSError as error:
            self.skipTest(str(error))
        with self.assertRaises(ValueError):
            manifest(self.left)


if __name__ == '__main__':
    unittest.main()
