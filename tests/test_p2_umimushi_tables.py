"""UmiMushi (Bloyster 71/101) extractor and table generator checks (#995).

* ``bca_pose(extra_tracks=True)`` accepts a clip that carries trailing tracks the skeleton lacks
  (the retail UmiMushi sturn1.bca has 26 tracks for the 25-joint model) and decodes exactly the
  first ``expected_joints`` tracks; the strict default still rejects the mismatch.
* ``scripts/p2_umimushi_tables.py`` renders a header whose collision tree has only the ``weak``
  tail bulb stickable, and refuses a tree that drifts from that.
"""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from experimental.pikmin2_purple import bca_pose  # noqa: E402
import p2_umimushi_tables as tables  # noqa: E402


def make_bca(tracks, frames=2):
    """A minimal framed ANF1 full-transform BCA: every joint has scale 1, rotation 0 and a distinct
    constant translation (joint index, 0, 0) so a decoded pose proves which track went where."""
    table_at = 36
    scales_at = table_at + tracks * 36
    scale_values = [1.0]
    rot_values = [0]
    trans_values = [float(j) for j in range(tracks)]
    rotations_at = scales_at + len(scale_values) * 4
    translations_at = rotations_at + ((len(rot_values) * 2 + 3) // 4) * 4
    body = bytearray(translations_at + len(trans_values) * 4)
    body[0:4] = b'ANF1'
    body[8] = 2  # loop attribute
    struct.pack_into('>HH', body, 10, frames, tracks)
    struct.pack_into('>4I', body, 20, table_at, scales_at, rotations_at, translations_at)
    for j in range(tracks):
        for axis in range(3):
            # scale: one shared 1.0; rotation: one shared 0; translation: per joint for x, shared 0 else
            struct.pack_into('>HH', body, table_at + j * 36 + axis * 12 + 0, 1, 0)
            struct.pack_into('>HH', body, table_at + j * 36 + axis * 12 + 4, 1, 0)
            struct.pack_into('>HH', body, table_at + j * 36 + axis * 12 + 8, 1, j if axis == 0 else 0)
    struct.pack_into('>f', body, scales_at, 1.0)
    for j, value in enumerate(trans_values):
        struct.pack_into('>f', body, translations_at + j * 4, value)
    data = bytearray(b'J3D1bca1' + b'\0' * 24 + bytes(body))
    padded = (len(data) + 31) // 32 * 32
    struct.pack_into('>I', data, 8, padded)
    data.extend(b'\0' * (padded - len(data)))
    return bytes(data)


class ExtraTrackTests(unittest.TestCase):
    def test_strict_default_rejects_a_longer_skeleton(self):
        raw = make_bca(26)
        with self.assertRaises(ValueError):
            bca_pose(raw, 0, 25, allow_scale=True)

    def test_extra_tracks_decodes_only_the_skeleton_joints(self):
        raw = make_bca(26)
        duration, pose = bca_pose(raw, 0, 25, allow_scale=True, extra_tracks=True)
        self.assertEqual(duration, 2)
        self.assertEqual(len(pose), 25)
        # joint j carries translation x = j (track j), so the trailing 26th track is dropped
        self.assertEqual([round(m[0][3]) for m in pose], list(range(25)))

    def test_extra_tracks_still_rejects_a_short_clip(self):
        with self.assertRaises(ValueError):
            bca_pose(make_bca(24), 0, 25, allow_scale=True, extra_tracks=True)

    def test_exact_match_is_unchanged(self):
        duration, pose = bca_pose(make_bca(25), 0, 25, allow_scale=True)
        self.assertEqual((duration, len(pose)), (2, 25))


class TableRenderTests(unittest.TestCase):
    NODES = [
        dict(id='root', code='____', radius=180.0, parent=None),
        dict(id='head', code='____', radius=80.0, parent=0),
        dict(id='kuti', code='____', radius=40.0, parent=0),
        dict(id='ketu', code='____', radius=25.0, parent=0),
        dict(id='weak', code='st__', radius=10.0, parent=0),
    ]

    def test_sample_frames_cover_short_and_long_clips(self):
        self.assertEqual(tables.sample_frames(15), list(range(15)))
        long = tables.sample_frames(170)
        self.assertEqual(len(long), tables.MAX_SAMPLES)
        self.assertEqual((long[0], long[-1]), (0, 169))

    def test_render_has_only_the_weak_node_stickable(self):
        clips = {}
        for stem in tables.CLIPS:
            coll = [[[0.0, 0.0, 0.0]] * 5] * 2
            tongue = [[[0.0, 0.0, 0.0]] * 7] * 2 if stem in tables.KAMU_CLIPS else []
            clips[stem] = (2, coll, tongue)
        text = tables.render('m' * 64, self.NODES, clips, 'c' * 64, {stem: 'a' * 64 for stem in tables.CLIPS})
        self.assertIn('kNodeCount = 5', text)
        self.assertIn('{"weak", "st__", 10.000f, 0}', text)
        self.assertEqual(text.count(', "st__", '), 1)
        self.assertIn('kKamuCount = 7', text)
        for stem in tables.CLIPS:
            self.assertIn('{"%s"' % stem, text)

    def test_kamu_joints_are_the_seven_mouth_slots(self):
        self.assertEqual(tables.KAMU, tuple('kamu_joint%d' % i for i in range(1, 8)))
        self.assertEqual(tables.KAMU_CLIPS, ('attack1', 'eat1'))


if __name__ == '__main__':
    unittest.main()
