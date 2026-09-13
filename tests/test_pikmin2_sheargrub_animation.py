import tempfile
import unittest
from pathlib import Path
from experimental.pikmin2_sheargrub_animation import mapping, checked, prepare, sha, CLIPS


class SheargrubAnimationTests(unittest.TestCase):
    def test_separate_bridge_bite_eat(self):
        female, male = mapping('UjiA'), mapping('UjiB')
        self.assertEqual(female['Attack'], 'attack1')
        self.assertEqual(male['Attack'], 'attack1')
        self.assertEqual(male['Type1'], 'attack2')
        self.assertEqual(male['Type2'], 'eat')
        self.assertNotIn('Type1', female)
        self.assertNotIn('Type2', female)
        self.assertNotIn('type5', male.values())
        with self.assertRaises(ValueError): mapping('Tobi')
        female['Attack'] = 'bad'
        self.assertEqual(mapping('UjiA')['Attack'], 'attack1')

    def test_complete_source_clip_counts(self):
        self.assertEqual((len(CLIPS['UjiA']),len(CLIPS['UjiB'])), (7,9))
        self.assertEqual(mapping('UjiB')['Damage'], 'dead_p')
        self.assertEqual(mapping('UjiA')['WaitAct1'], 'appear')
        self.assertEqual(mapping('UjiA')['WaitAct2'], 'dive')

    def test_cap_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for limit in (True,1,13,1.5):
                with self.assertRaises(ValueError): prepare(root,root/'output',limit)
                self.assertFalse((root/'output').exists())

    def test_same_path_changed_source_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'source.bca'
            p.write_bytes(b'first')
            digest = sha(p.read_bytes())
            self.assertEqual(checked(p,digest), b'first')
            p.write_bytes(b'other')
            with self.assertRaises(ValueError): checked(p,digest)
            self.assertEqual(p.read_bytes(),b'other')


if __name__ == '__main__': unittest.main()
