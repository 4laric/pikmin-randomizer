import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_surface_pocket import generators, prepare_surface
from scripts.test_pikmin2_surface_native import executable_identity


def manager(version='v0.3', pos='-190 80 1160'):
    label=' '.join(map(str, list(b'entrance')+[0]*24))
    return '{v0.1} 0 0 0 0 1 { {'+version+'} 0 0 '+label+' '+pos+' 1 2 3 {item} {0002} { {cave} 0 -45 0 {0002} tutorial_1.txt units.txt {t_01} } { {_eof} } }'


class PocketTests(unittest.TestCase):
    def test_source_anchor_and_offsets(self):
        row=generators(manager())['actors'][0]
        self.assertEqual(row['position'],[-190,80,1160])
        self.assertEqual(row['effective_position'],[-189,82,1163])
        self.assertEqual(row['rotation'],[0,-45,0])
        self.assertEqual(row['cave_id'],'t_01')
    def test_older_disc_header(self):
        self.assertEqual(generators(manager('v0.1'))['actors'][0]['kind'],'item')
    def test_reject_bad_count(self):
        with self.assertRaises(ValueError): generators(manager().replace('0 0 0 0 1','0 0 0 0 2',1))
    def test_reject_nonfinite(self):
        with self.assertRaises(ValueError): generators(manager(pos='nan 80 1160'))
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError): prepare_surface(Path('unused.iso'),Path(directory))
    def test_executable_identity_is_captured_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.exe';path.write_bytes(b'abc')
            captured=executable_identity(path);path.write_bytes(b'new binary')
            self.assertEqual(captured['sha256'],'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
            self.assertEqual(captured['path'],str(path.resolve()))
            self.assertNotEqual(captured['sha256'],executable_identity(path)['sha256'])

if __name__ == '__main__': unittest.main()
