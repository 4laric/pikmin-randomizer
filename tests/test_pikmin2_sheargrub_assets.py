import unittest
from pathlib import Path
from experimental.pikmin2_sheargrub_assets import animation_rows,extract,joints

class SheargrubTests(unittest.TestCase):
    def test_events_preserved(self):
        self.assertEqual(animation_rows('1 { source\\attack1.bca attack1.bca 15 2 -1 }')[0]['events'],[[15,2]])
    def test_invalid_registry(self):
        for text in ['2 { a a.bca -1 }','1 { a a.bca 15 -1 }','1 { a ../a.bca -1 }','2 { a a.bca -1 } { a a.bca -1 }']:
            with self.subTest(text=text),self.assertRaises(ValueError):animation_rows(text)
    def test_budget_rejected_before_io(self):
        for count in [1,9,True]:
            with self.subTest(count=count),self.assertRaises(ValueError):extract(Path('missing'),Path('unused'),count)

if __name__=='__main__':unittest.main()
