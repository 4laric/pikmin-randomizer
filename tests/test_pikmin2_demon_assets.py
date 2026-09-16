import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experimental.pikmin2_demon_assets import frames_for, extract


class DemonAssetsTests(unittest.TestCase):
    def test_capture_and_event_frames(self):
        self.assertEqual(frames_for(50, [[13, 2], [50, 1000]]), [0, 10, 13, 16, 17, 30, 49])
        self.assertEqual(frames_for(1, []), [0])

    def test_invalid_and_budget(self):
        for duration, events in [(0, []), (5, [[6, 2]]), (100, [[i, 2] for i in range(40)])]:
            with self.assertRaises(ValueError):
                frames_for(duration, events)

    def test_existing_output_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root/'marker'
            marker.write_bytes(b'preserve')
            with patch('experimental.pikmin2_demon_assets.disc_files', return_value={}):
                with self.assertRaises(FileExistsError):
                    extract(Path('unused.iso'), root)
            self.assertEqual(marker.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
