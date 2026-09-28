"""Breadbug lane batch 2 (#220): installation tests over installed artifacts."""
import json
import unittest
from pathlib import Path

from experimental.pikmin2_breadbug_lane_install import (
    prepare, install, verify_installation, verify_mod, PREFIXES)
from experimental.pikmin2_breadbug_visual import sha

LANE_IMPORT = Path('output/p2-lifecycle-batch/breadbug-lane-03')


def fake_mod(vertices=4, meshes=1):
    """Minimal structurally valid MOD per pikmin2_convert.write_model layout."""
    import struct as st
    data = bytearray()

    def begin(tag, *counts):
        data.extend(b'\0' * ((-len(data)) % 32))
        start = len(data)
        data.extend(st.pack('>II', tag, 0))
        for n in counts:
            data.extend(st.pack('>I', n))
        return start

    def end(start):
        data.extend(b'\0' * ((-len(data)) % 32))
        st.pack_into('>I', data, start + 4, len(data) - start - 8)

    s = begin(0)
    end(s)
    s = begin(16, vertices)
    data.extend(b'\0' * (12 * vertices))
    end(s)
    s = begin(48, meshes, meshes)
    end(s)
    s = begin(80, meshes)
    end(s)
    s = begin(96, 1)
    end(s)
    s = begin(0xFFFF)
    end(s)
    return bytes(data)


def fake_lane(root):
    lane = dict(schema=1, lane=213,
                classification={'39': {'spawnable': False}, '83': {'spawnable': False}},
                species={}, source_sha256={},
                limitations=[])
    for species, stems in (('PanModoki', ('wait1', 'move1')),
                           ('OoPanModoki', ('wait1', 'move1'))):
        (root / species).mkdir(parents=True)
        clips = []
        for stem in stems:
            poses = []
            for frame in (0, 10):
                mod = fake_mod(vertices=4 + frame % 3)
                name = f'{stem}_{frame:03}.mod'
                (root / species / name).write_bytes(mod)
                poses.append(dict(file=name, frame=frame, sha256=sha(mod)))
            clips.append(dict(file=stem + '.bca', sha256='x', source_frames=11,
                              events=[], status='sampled_poses_converted', poses=poses))
        lane['species'][species] = dict(model_sha256='m', joints=['a'], clips=clips,
                                        static_pose=None, metadata_sha256={},
                                        parameter_blocks=[], collision=[])
    (root / 'PanHouse').mkdir()
    nest = fake_mod()
    (root / 'PanHouse/nest.mod').write_bytes(nest)
    lane['species']['PanHouse'] = dict(model_sha256='n', joints=['j'], clips=[],
                                       static_pose=dict(file='nest.mod', sha256=sha(nest)),
                                       metadata_sha256={}, parameter_blocks=[], collision=[])
    (root / 'breadbug-lane.json').write_text(json.dumps(lane))
    return root


def fake_run(root):
    (root / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    return root


class ModVerifierTests(unittest.TestCase):
    def test_valid_and_broken_models(self):
        info = verify_mod(fake_mod())
        self.assertEqual((info['vertices'], info['meshes']), (4, 1))
        with self.assertRaises(ValueError):
            verify_mod(b'')
        with self.assertRaises(ValueError):
            verify_mod(fake_mod()[:40])  # truncated
        with self.assertRaises(ValueError):
            verify_mod(fake_mod() + b'junk')  # trailing data


class InstallTests(unittest.TestCase):
    def test_install_verify_and_reproducibility(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lane = fake_lane(tmp / 'lane')
            profile = prepare(lane, tmp / 'profile')
            run_a = fake_run(tmp / 'run_a')
            run_b = fake_run(tmp / 'run_b')
            a = install(tmp / 'profile', run_a)
            b = install(tmp / 'profile', run_b)
            self.assertEqual(a, b)  # reproducible double install
            verify_installation(run_a)
            room = run_a / 'assets/dataDir/courses/pikmin2room'
            self.assertEqual(len(list(room.glob('lane_*.mod'))), len(profile['files']))
            self.assertTrue(any(n.startswith(PREFIXES['OoPanModoki']) for n in profile['files']))
            self.assertIn(PREFIXES['PanHouse'] + 'nest.mod', profile['files'])

    def test_refuses_conflicts_and_tampering(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lane = fake_lane(tmp / 'lane')
            profile = prepare(lane, tmp / 'profile')
            run = fake_run(tmp / 'run')
            install(tmp / 'profile', run)
            with self.assertRaises(ValueError):
                install(tmp / 'profile', run)  # no overwrite
            name = next(iter(profile['files']))
            target = run / 'assets/dataDir/courses/pikmin2room' / name
            target.write_bytes(fake_mod(vertices=9))
            with self.assertRaises(ValueError):
                verify_installation(run)  # tamper detected

    def test_rejects_spawnable_helper_classification(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lane = fake_lane(tmp / 'lane')
            data = json.loads((lane / 'breadbug-lane.json').read_text())
            data['classification']['39']['spawnable'] = True
            (lane / 'breadbug-lane.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                prepare(lane, tmp / 'profile')


@unittest.skipUnless((LANE_IMPORT / 'breadbug-lane.json').exists(),
                     'lane extraction output not present')
class RealInstallTests(unittest.TestCase):
    def test_real_lane_installs_and_reproduces(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            profile = prepare(LANE_IMPORT, tmp / 'profile')
            # Giant weighted poses and nest are staged with verified hashes.
            giant = [n for n in profile['files'] if n.startswith(PREFIXES['OoPanModoki'])]
            self.assertGreaterEqual(len(giant), 6)
            self.assertIn(PREFIXES['PanHouse'] + 'nest.mod', profile['files'])
            a = install(tmp / 'profile', fake_run(tmp / 'a'))
            b = install(tmp / 'profile', fake_run(tmp / 'b'))
            self.assertEqual(a['installed'], b['installed'])
            verify_installation(tmp / 'a')
            for record in a['installed'].values():
                self.assertGreater(record['vertices'], 0)
                self.assertGreater(record['meshes'], 0)


if __name__ == '__main__':
    unittest.main()
