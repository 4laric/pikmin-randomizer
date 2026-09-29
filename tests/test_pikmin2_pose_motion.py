"""P2 pose-fidelity helpers (#895): native motion test + bake trailer policy."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_animation import (
    DEFAULT_POSE_LIMIT,
    LEGACY_POSE_LIMIT,
    POSE_LIMIT_MAX,
    frames_trailer,
    sample_frames,
)

ROOT = Path(__file__).resolve().parents[1]


class PoseMotionNativeTest(unittest.TestCase):
    def test_native_motion_helpers(self):
        compiler = shutil.which('g++') or 'C:/msys64/mingw64/bin/g++.exe'
        if not Path(compiler).exists() and not shutil.which('g++'):
            self.skipTest('g++ unavailable')
        source = ROOT / 'engine' / 'tools' / 'p2_pose_motion_test.cpp'
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'p2_pose_motion_test.exe'
            subprocess.run([compiler, '-std=c++17', '-O1', '-UNDEBUG', '-I', str(ROOT / 'engine' / 'pc_port'),
                            str(source), '-o', str(exe)], check=True)
            result = subprocess.run([str(exe)], capture_output=True, text=True, check=True)
        self.assertIn('p2_pose_motion_test OK', result.stdout)


class PoseDensityPolicyTest(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(POSE_LIMIT_MAX, 64)
        self.assertGreaterEqual(DEFAULT_POSE_LIMIT, 12)
        self.assertEqual(LEGACY_POSE_LIMIT, DEFAULT_POSE_LIMIT)  # no sparser legacy tier (#895)

    def test_sample_frames_accepts_dense_limits(self):
        frames = sample_frames(61, 16)
        self.assertEqual(frames[0], 0)
        self.assertEqual(frames[-1], 60)
        self.assertEqual(len(frames), 16)
        self.assertEqual(len(sample_frames(200, POSE_LIMIT_MAX)), 64)
        with self.assertRaises(ValueError):
            sample_frames(200, POSE_LIMIT_MAX + 1)

    def test_frames_trailer(self):
        poses = [{'frame': f} for f in (0, 4, 8, 60)]
        self.assertEqual(frames_trailer(poses, 61), ' frames 0,4,8,60')
        self.assertEqual(frames_trailer(poses[:-1], 61), '')          # dropped end pose
        self.assertEqual(frames_trailer([{'frame': 0}, {'frame': 0}], 1), '')
        self.assertEqual(frames_trailer([{'frame': 0}, {}], 2), '')    # missing frame
        self.assertEqual(frames_trailer([{'frame': 0}, {'frame': 1}], 2), ' frames 0,1')
        self.assertEqual(frames_trailer([{'frame': i} for i in range(65)], 65), '')


if __name__ == '__main__':
    unittest.main()
