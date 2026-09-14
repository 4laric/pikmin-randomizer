"""Mamuta install/arena tests covering INSTALLED artifacts, not just output/ (#221)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_mamuta_install import (CONFIG_NAME, install, plan, verify_install)
from experimental.pikmin2_mamuta_arena import GATES, P1_CHAPPY_TYPE, P1_MIURIN_TYPE, roster


def fake_imported(root):
    """Synthetic schema-1 Mamuta import: real bytes, recorded hashes."""
    species = root / 'Miulin'
    species.mkdir(parents=True)
    poses = {'wait_00.mod': b'WAIT', 'dead_02.mod': b'DEAD', 'attack1_00.mod': b'ATTACK'}
    for name, data in poses.items():
        (species / name).write_bytes(data)
    clips = []
    for clip, name in (('wait.bca', 'wait_00.mod'), ('dead.bca', 'dead_02.mod'),
                       ('attack1.bca', 'attack1_00.mod')):
        clips.append({'file': clip, 'status': 'converted',
                      'poses': [{'file': name,
                                 'sha256': hashlib.sha256(poses[name]).hexdigest()}]})
    meta = {'schema': 1, 'species': 'Miulin', 'enemy_id': 54, 'clips': clips}
    (root / 'mamuta.json').write_text(json.dumps(meta))
    return root


class PlanTests(unittest.TestCase):
    def test_actor_count_rejected_before_io(self):
        for actors in ([], [(i, 'Miulin') for i in range(101)]):
            with self.subTest(n=len(actors)), self.assertRaises(ValueError):
                plan(Path('missing'), actors)

    def test_duplicate_and_invalid_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp))
            with self.assertRaises(ValueError):
                plan(imported, [(5, 'Miulin'), (5, 'Miulin')])
            for bad in [(-1, 'Miulin'), ('5', 'Miulin'), (True, 'Miulin'), (1, 'UjiA')]:
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    plan(imported, [bad])

    def test_schema_and_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp))
            meta = json.loads((imported / 'mamuta.json').read_text())
            for key, value in (('schema', 2), ('enemy_id', 55), ('species', 'UjiA')):
                broken = dict(meta, **{key: value})
                (imported / 'mamuta.json').write_text(json.dumps(broken))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    plan(imported, [(1, 'Miulin')])
                (imported / 'mamuta.json').write_text(json.dumps(meta))

    def test_pose_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp))
            (imported / 'Miulin/wait_00.mod').write_bytes(b'TAMPERED')
            with self.assertRaises(ValueError):
                plan(imported, [(1, 'Miulin')])


class InstallTests(unittest.TestCase):
    def make_run(self, root):
        run = root / 'run'
        (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
        return run

    def test_install_and_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            result = install(imported, run, [(221001, 'Miulin')])
            self.assertEqual(result['files'], ['miulin_attack1_00.mod', 'miulin_dead_00.mod',
                                               'miulin_wait_00.mod'])
            verified = verify_install(imported, run, [(221001, 'Miulin')])
            self.assertEqual(verified['verified'], result['files'])
            config = (run / CONFIG_NAME).read_text()
            self.assertEqual(config.split(), ['P2_MAMUTA_ACTORS_1', '1', '221001', 'Miulin'])

    def test_installs_full_attack_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            species = imported / 'Miulin'
            species.mkdir(parents=True)
            poses = {f'attack1_{i:02d}.mod': bytes([65 + i]) for i in range(3)}
            poses['wait_00.mod'] = b'W'
            poses['dead_00.mod'] = b'D'
            for name, data in poses.items():
                (species / name).write_bytes(data)
            clips = []
            for clip in ('wait', 'dead', 'attack1'):
                names = sorted(n for n in poses if n.startswith(clip + '_'))
                clips.append({'file': clip + '.bca', 'status': 'converted',
                              'poses': [{'file': n, 'sha256': hashlib.sha256(poses[n]).hexdigest()}
                                        for n in names]})
            (imported / 'mamuta.json').write_text(json.dumps(
                {'schema': 1, 'species': 'Miulin', 'enemy_id': 54, 'clips': clips}))
            run = self.make_run(root)
            result = install(imported, run, [(1, 'Miulin')])
            attack = sorted(n for n in result['files'] if n.startswith('miulin_attack1'))
            self.assertEqual(attack, ['miulin_attack1_00.mod', 'miulin_attack1_01.mod',
                                      'miulin_attack1_02.mod'])
            verify_install(imported, run, [(1, 'Miulin')])

    def test_install_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, [(1, 'Miulin')])
            with self.assertRaises(ValueError):
                install(imported, run, [(2, 'Miulin')])

    def test_verify_detects_tampered_installed_pose(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, [(1, 'Miulin')])
            target = run / 'assets/dataDir/courses/pikmin2room/miulin_dead_00.mod'
            target.write_bytes(b'X')
            with self.assertRaises(ValueError):
                verify_install(imported, run, [(1, 'Miulin')])

    def test_verify_detects_config_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, [(1, 'Miulin')])
            (run / CONFIG_NAME).write_text('P2_MAMUTA_ACTORS_1\n2\n')
            with self.assertRaises(ValueError):
                verify_install(imported, run, [(1, 'Miulin')])


class ArenaContractTests(unittest.TestCase):
    def test_proxy_types_match_native_registry(self):
        # tekimgr.cpp tekiNames: 24 "miurin" (Mamuta), 3 "chappy" (control)
        self.assertEqual(P1_MIURIN_TYPE, 24)
        self.assertEqual(P1_CHAPPY_TYPE, 3)

    def test_gates_cover_batch1_open_items(self):
        for gate in ('native_identity', 'bury_attack', 'flick_collateral',
                     'territory_watchdog', 'day_floor_reset', 'save_load',
                     'piklopedia_observation'):
            self.assertIn(gate, GATES)

    def test_roster_requires_real_stage_records(self):
        with self.assertRaises(Exception):
            roster(Path('missing'))


if __name__ == '__main__':
    unittest.main()
