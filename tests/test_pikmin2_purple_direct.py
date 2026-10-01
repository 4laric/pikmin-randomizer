import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_purple_direct import write_profile


class PurpleDirectProfileTests(unittest.TestCase):
    def test_writes_adult_and_dwarf_only_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p2-purple-direct.txt"
            write_profile(path, [7, 0xFFFFFFFF])
            self.assertEqual(
                path.read_text(encoding="ascii"),
                "P2_PURPLE_DIRECT_1\nadult_fp36 50\nadult_generators 2 7 4294967295\n",
            )
            write_profile(path, [])
            self.assertEqual(path.read_text(encoding="ascii").splitlines()[-1], "adult_generators 0")

    def test_rejects_invalid_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p2-purple-direct.txt"
            for values in ([-1], [0x100000000], [5, 5], [True]):
                with self.subTest(values=values), self.assertRaises(ValueError):
                    write_profile(path, values)


if __name__ == "__main__":
    unittest.main()
