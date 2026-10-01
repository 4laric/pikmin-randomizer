import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from experimental.pikmin2_frog_specular_stage import stage, profiled_bank, POLICY


def bank(tmp, materials=True):
    report = {'material_profile': {'policy': POLICY}} if materials else {}
    tmp.mkdir(parents=True)
    (tmp / 'frogs.json').write_text(json.dumps(report))
    for species in ('Frog', 'MaroFrog'):
        folder = tmp / species
        folder.mkdir()
        (folder / ('frog_%s_wait1_00.mod' % species)).write_bytes(b'pose')
    return tmp


class StageRefusalTests(unittest.TestCase):
    def test_nonprofiled_bank_refused(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            b = bank(root / 'bank', materials=False)
            with self.assertRaises(ValueError):
                profiled_bank(b)

    def test_existing_output_refused(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            b = bank(root / 'bank')
            out = root / 'run'
            out.mkdir()
            with self.assertRaises(ValueError):
                stage(b, root / 'assets', out)

    def test_missing_room_assets_refused(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            b = bank(root / 'bank')
            with self.assertRaises(ValueError):
                stage(b, root / 'assets', root / 'run')

    def test_missing_profiled_pose_refused(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            b = bank(root / 'bank')
            (b / 'Frog' / 'frog_Frog_wait1_00.mod').unlink()
            assets = root / 'assets'
            (assets / 'dataDir' / 'courses' / 'pikmin2room').mkdir(parents=True)
            with self.assertRaises(ValueError):
                stage(b, assets, root / 'run')


if __name__ == '__main__':
    unittest.main()
