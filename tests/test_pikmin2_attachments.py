import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from experimental.pikmin2_attachments import decompose
from experimental.pikmin2_rigid import local_matrix, joint_matrices

ROOT = Path(__file__).resolve().parents[1]


class AttachmentTests(unittest.TestCase):
    def test_local_trs_roundtrip(self):
        for angles in ((0, 0, 0), (16384, 0, 0), (0, 32767, 0), (3000, -5000, 12000)):
            with self.subTest(angles=angles):
                m = local_matrix(angles, (7, -2, 11))
                for r in range(3):
                    for c, scale in enumerate((.1, 2, 3)):
                        m[r][c] *= scale
                p = decompose(m)
                x, y, z, w = p[3:7]
                rotation = ((1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w),
                            (2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w),
                            (2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y))
                for r in range(3):
                    self.assertAlmostEqual(p[r], m[r][3])
                    for c in range(3):
                        self.assertAlmostEqual(rotation[r][c]*p[7+c], m[r][c])

    def test_unsupported_local_transforms_refused(self):
        for bad in (((0,0,0,0),(0,1,0,0),(0,0,1,0)),
                    ((-1,0,0,0),(0,1,0,0),(0,0,1,0)),
                    ((1,.3,0,0),(0,1,0,0),(0,0,1,0)),
                    ((math.nan,0,0,0),(0,1,0,0),(0,0,1,0))):
            with self.subTest(matrix=bad), self.assertRaises(ValueError):
                decompose(bad)

    def test_compiled_contract_and_optional_retail_matrices(self):
        compiler = shutil.which('g++')
        if not compiler:
            self.skipTest('g++ required for native contract')
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            exe = temp/'attachments.exe'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-I'+str(ROOT/'engine/pc_port'), str(ROOT/'engine/tools/test_p2_attachments.cpp'),
                            '-o', str(exe)], check=True, capture_output=True)
            self.assertIn('PASS attachments:', subprocess.check_output([str(exe)], text=True))
            if 'P2_ATTACHMENT_BANK' not in os.environ:
                return
            from experimental.pikmin2_assets import disc_files, archive_files
            from experimental.pikmin2_convert import blocks
            from experimental.pikmin2_purple import bca_pose
            from experimental.pikmin2_animation import parse_bank
            bank = Path(os.environ['P2_ATTACHMENT_BANK'])
            snow = Path(os.environ['P2_ATTACHMENT_SNOW'])
            iso = Path(os.environ['P2_ATTACHMENT_ISO'])
            dump = temp/'matrices.txt'
            self.assertIn('REAL_BANK joints=13 samples=120', subprocess.check_output([str(exe), str(bank), str(dump)], text=True))
            off, size = disc_files(iso)['enemy/data/Kochappy/anim.szs']
            with iso.open('rb') as stream:
                stream.seek(off)
                archive = archive_files(stream.read(size))
            model = blocks((snow/'snow.bmd').read_bytes())
            timing = list(parse_bank((snow/'p2-snow.txt').read_text()).items())
            expected = {}
            for ci, (name, clip) in enumerate(timing):
                for frame in clip['frames']:
                    _, pose = bca_pose(archive[name+'.bca'], frame, 13, allow_scale=True)
                    expected[ci, frame] = joint_matrices(model, pose)
            rows = dump.read_text().splitlines()
            self.assertEqual(len(rows), 1560)
            worst = 0
            for line in rows:
                parts = line.split()
                ci, frame, joint = map(int, parts[:3])
                actual = list(map(float, parts[3:]))
                reference = [v for row in expected[ci, frame][joint] for v in row]
                worst = max(worst, max(abs(a-b) for a, b in zip(actual, reference)))
                for a, b in zip(actual, reference):
                    self.assertAlmostEqual(a, b, delta=.0002)
            print('Retail attachment transforms: 1560 matrices, maximum error', worst)


if __name__ == '__main__':
    unittest.main()
