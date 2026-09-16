import unittest
from pathlib import Path
from experimental.pikmin2_sheargrub_install import plan

class InstallTests(unittest.TestCase):
    def test_empty_rejected_before_io(self):
        with self.assertRaises(ValueError):plan(Path('missing'),[])
    def test_oversized_rejected_before_io(self):
        with self.assertRaises(ValueError):plan(Path('missing'),[(i,'UjiA') for i in range(101)])

if __name__=='__main__':unittest.main()
