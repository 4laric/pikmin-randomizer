"""Cloaking Burrow-nit (Armor 15) collision/mouth table generator checks (#1014).

* the generator renders a header whose collision tree has exactly one stickable node (dmg1, code st__),
  the unnamed shell sphere (_t__ on kourajnt) and the root (____ on kosijnt) are not stickable;
* against the staged retail content (skipped when the dense cache is absent) the mouth joint is
  ``kamujnt`` and the attack2 bite lunges forward past the body, which is what the native bite relies on.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import p2_armor_tables as tables  # noqa: E402

NODES = [
    dict(id='none', code='____', radius=40.0, joint=6, offset=[0.0, 0.0, 0.0], parent=None),
    dict(id='dmg1', code='st__', radius=17.5, joint=1, offset=[7.5, 0.0, 0.0], parent=0),
    dict(id='none', code='_t__', radius=22.5, joint=7, offset=[7.5, -5.0, 0.0], parent=0),
]
NAMES = ['yoroimushi', 'headjnt', 'kamujnt', 'lagojnt', 'mouthjnt', 'ragojnt', 'kosijnt', 'kourajnt']


def content_dir():
    candidates = [os.environ.get('PIKMIN_P2_CONTENT_CACHE', ''),
                  str(ROOT / 'output' / 'p2-content-dense'),
                  str(ROOT.parent / 'p2-content-dense'),
                  str(ROOT.parent.parent / 'output' / 'p2-content-dense')]
    for c in candidates:
        if c and (Path(c) / 'Armor').is_dir():
            return c
    return None


class RenderTests(unittest.TestCase):
    def test_render_has_only_dmg1_stickable(self):
        clips = {stem: (2, [[[0.0, 0.0, 0.0]] * 3] * 2, [[0.0, 0.0, 0.0]] * 2) for stem in tables.CLIPS}
        text = tables.render('m' * 64, NODES, NAMES, clips, 'c' * 64, {stem: 'a' * 64 for stem in tables.CLIPS})
        self.assertIn('kNodeCount = 3', text)
        self.assertIn('{"dmg1", "st__", 17.500f, 1, "headjnt", 0}', text)
        self.assertIn('{"none", "_t__", 22.500f, 7, "kourajnt", 0}', text)
        self.assertEqual(text.count(', "st__", '), 1)
        for stem in tables.CLIPS:
            self.assertIn('{"%s"' % stem, text)

    def test_mouth_joint_and_clip_list(self):
        self.assertEqual(tables.MOUTH_JOINT, 'kamujnt')
        self.assertEqual(NAMES.index(tables.MOUTH_JOINT), 2)
        self.assertEqual(len(tables.CLIPS), 10)
        self.assertIn('attack2', tables.CLIPS)
        self.assertIn('eat', tables.CLIPS)


@unittest.skipUnless(content_dir(), 'dense P2 content cache with Armor not present')
class RetailContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model_sha, cls.nodes, cls.names, cls.clips, cls.coll_sha, cls.clip_sha = tables.build(content_dir())

    def test_tree_is_the_retail_one(self):
        self.assertEqual([(n['id'], n['code'], n['radius'], n['joint']) for n in self.nodes],
                         [('none', '____', 40.0, 6), ('dmg1', 'st__', 17.5, 1), ('none', '_t__', 22.5, 7)])
        self.assertEqual([self.names[n['joint']] for n in self.nodes], ['kosijnt', 'headjnt', 'kourajnt'])

    def test_bite_lunges_ahead_of_the_body(self):
        duration, coll, mouth = self.clips['attack2']
        self.assertEqual(duration, 40)
        # source attackPikmin window: frames 18..26 (17 < f < 27); the jaw peaks far ahead of the feet
        peak = max(mouth[f][2] for f in range(18, 27))
        self.assertGreater(peak, 120.0)
        # the rearing head frames are NOT the lunge: the mouth is near the body there
        self.assertLess(mouth[18][2], 40.0)
        self.assertGreater(mouth[21][2], 100.0)

    def test_shell_sits_behind_the_head(self):
        for stem in ('move', 'attack2', 'eat'):
            _, coll, _ = self.clips[stem]
            ahead = sum(1 for sample in coll if sample[1][2] > sample[2][2])
            self.assertGreater(ahead, len(coll) * 0.8, stem)


if __name__ == '__main__':
    unittest.main()
