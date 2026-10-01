"""Breadbug lane batch 3 (#220): Giant/nest display-binding evidence checks.

The native display binding (native 7faa644 / root f9f0839, issue #229) lives in
the root-owned `output/p2-root-integration` worktree. These tests verify the
binding consumes this lane's exact extracted models and that the frozen
validation evidence shows display-only behavior with unchanged gameplay
counts. They never touch the root worktree's files.
"""
import hashlib
import json
import re
import unittest
from pathlib import Path

BINDING = Path('output/p2-root-integration/output/p2-giant-breadbug-binding/profile-a')
VALIDATION = Path('output/p2-root-integration/output/p2-giant-breadbug-runtime/kimi-validation-01')
LANE = Path('output/p2-lifecycle-batch/breadbug-lane-03')
BATCH2_PROFILE_SHA256 = 'e32a67d9df2a25db3bfa79b3acb257ecf96d720e5397509f7a4c974292c2061d'

present = (BINDING / 'giant-breadbug-visual.json').exists() and \
    (LANE / 'breadbug-lane.json').exists()


@unittest.skipUnless(present, 'root binding profile or lane extraction not present')
class BindingProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((BINDING / 'giant-breadbug-visual.json').read_text())
        cls.lane = json.loads((LANE / 'breadbug-lane.json').read_text())

    def test_binding_uses_exact_lane_models(self):
        lane_hashes = {}
        for species in ('OoPanModoki', 'PanHouse'):
            for path in (LANE / species).glob('*.mod'):
                lane_hashes[hashlib.sha256(path.read_bytes()).hexdigest()] = (species, path.name)
        self.assertEqual(len(self.meta['files']), 11)  # 5 wait + 5 move + nest
        for name, digest in self.meta['files'].items():
            self.assertIn(digest, lane_hashes, name)
            installed = hashlib.sha256((BINDING / 'models' / name).read_bytes()).hexdigest()
            self.assertEqual(installed, digest, name)
        kinds = {lane_hashes[d][0] for d in self.meta['files'].values()}
        self.assertEqual(kinds, {'OoPanModoki', 'PanHouse'})

    def test_binding_tracks_batch2_lane_profile(self):
        self.assertEqual(self.meta.get('lane_profile_sha256'), BATCH2_PROFILE_SHA256)
        self.assertEqual(self.meta.get('behavior'), 'display_only_no_actor_collision_rewards')
        self.assertFalse(self.meta.get('native_validated'))

    def test_binding_clip_frames_match_lane_poses(self):
        giant = self.lane['species']['OoPanModoki']
        lane_frames = {Path(c['file']).stem: sorted(p['frame'] for p in c['poses'])
                       for c in giant['clips'] if Path(c['file']).stem in ('wait1', 'move1')}
        for clip in self.meta['clips']:
            source = {'wait': 'wait1', 'move': 'move1'}[clip['kind']]
            self.assertEqual(clip['frames'], lane_frames[source], clip['kind'])
            durations = {Path(c['file']).stem: c['source_frames'] for c in giant['clips']}
            self.assertEqual(clip['duration'], durations[source])


@unittest.skipUnless((VALIDATION / 'result.json').exists(), 'validation run not present')
class ValidationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((VALIDATION / 'result.json').read_text())

    def test_all_modes_pass_all_checks(self):
        self.assertEqual(sorted(self.report), ['disabled', 'move', 'nest', 'wait'])
        for mode, evidence in self.report.items():
            self.assertTrue(evidence['passed'], mode)
            self.assertTrue(all(evidence['checks'].values()), (mode, evidence['checks']))
            self.assertEqual(evidence['exit_code'], 0, mode)

    def test_setup_draw_reset_reload_counts(self):
        for mode, evidence in self.report.items():
            log = Path(evidence['directory'], 'native.log').read_text(errors='replace')
            enabled = mode != 'disabled'
            self.assertEqual(log.count('P2_GIANT_BREADBUG_VISUAL_READY '), 2 if enabled else 0, mode)
            self.assertEqual(log.count('P2_GIANT_RESET_REQUEST'), 1, mode)
            self.assertEqual(log.count('P2_GIANT_RELOAD_REQUEST'), 1, mode)
            self.assertNotIn('P2_BREADBUG_VISUAL_READY ', log, mode)
            self.assertNotIn('P2_POD_COLLECT', log, mode)

    def test_gameplay_counts_unchanged(self):
        # Display binding asserts Teki actors 0, cargo 0, repairs 1 throughout.
        for mode, evidence in self.report.items():
            log = Path(evidence['directory'], 'native.log').read_text(errors='replace')
            baseline = re.findall(r'P2_GIANT_BASELINE actors=(\d+) cargo=(\d+) repairs=(\d+)', log)
            self.assertEqual(baseline, [('0', '0', '1')], mode)
            self.assertIn('PASS P2_GIANT_DISPLAY_RUNTIME noninteractive unchanged_actors_cargo_repairs', log)

    def test_placement_is_engineering_ground_not_source(self):
        log = Path(self.report['wait']['directory'], 'native.log').read_text(errors='replace')
        ground = re.findall(r'P2_GIANT_GROUND id=(\d+) kind=(\w+) x=([-\d.]+) y=([-\d.]+) z=([-\d.]+)', log)
        self.assertEqual(len(ground), 1)
        self.assertEqual(ground[0][0], '229001')
        self.assertEqual(ground[0][1], 'wait')
        self.assertIn('scope', self.report['wait'])
        self.assertIn('no actor or gameplay', self.report['wait']['scope'])

    def test_captures_recorded(self):
        for mode in ('wait', 'move', 'nest'):
            captures = self.report[mode].get('captures', {})
            self.assertEqual(sorted(captures),
                             ['giant-pose-a', 'giant-pose-b', 'giant-reload', 'giant-reset'], mode)


if __name__ == '__main__':
    unittest.main()
