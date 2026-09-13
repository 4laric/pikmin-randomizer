"""Snagret install/arena tests covering INSTALLED artifacts, not just output/ (#376)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_snagret_install import (
    ACTORS_HEADER, ACTORS_TXT, INSTALL_JSON, MANIFEST, POSE_PREFIX, install, plan,
    verify_install)
from experimental.pikmin2_snagret_arena import (
    GATES, P1_CHAPPY_TYPE, P1_TEMPLATE_ENEMY_TYPE, roster)
from experimental.pikmin2_snagret_assets import SPECIES

IDS = {'SnakeCrow': 34, 'SnakeWhole': 70, 'DangoMushi': 94}
ROOM = 'assets/dataDir/courses/pikmin2room'
FAMILY = [(376001, 'SnakeCrow'), (376002, 'SnakeWhole'), (376003, 'DangoMushi')]


def fake_imported(root, visuals=True):
    """Synthetic schema-1 snagret import: real bytes, recorded hashes."""
    species = {}
    for name, enemy_id in IDS.items():
        folder = root / name
        folder.mkdir(parents=True)
        clips = []
        for clip in ('dead', 'wait1'):
            poses = []
            for number in range(2):
                pose = f'{POSE_PREFIX}_{name}_{clip}_{number:02}.mod'
                data = (name + clip + str(number)).encode()
                if visuals:
                    (folder / pose).write_bytes(data)
                poses.append({'file': pose, 'frame': number,
                              'sha256': hashlib.sha256(data).hexdigest()})
            clips.append({'name': clip, 'status': 'converted', 'poses': poses})
        species[name] = {'enemy_id': enemy_id, 'clips': clips}
    meta = {'schema': 1, 'policy': 'P2_SNAGRET_1', 'native_ready': False,
            'gameplay_events_executed': False, 'btk_playback': False,
            'species': species}
    (root / MANIFEST).write_text(json.dumps(meta))
    return root


class PlanTests(unittest.TestCase):
    def test_actor_count_rejected_before_io(self):
        for actors in ([], [(i, 'SnakeCrow') for i in range(101)]):
            with self.subTest(n=len(actors)), self.assertRaises(ValueError):
                plan(Path('missing'), actors)

    def test_duplicate_and_invalid_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp))
            with self.assertRaises(ValueError):
                plan(imported, [(5, 'SnakeCrow'), (5, 'SnakeWhole')])
            for bad in [(-1, 'SnakeCrow'), ('5', 'SnakeCrow'), (True, 'SnakeCrow'),
                        (1, 'UjiA'), (0x100000000, 'DangoMushi')]:
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    plan(imported, [bad])

    def test_schema_and_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp))
            meta = json.loads((imported / MANIFEST).read_text())
            for key, value in (('schema', 2), ('policy', 'P2_SNAGRET_2'),
                               ('native_ready', True),
                               ('gameplay_events_executed', True)):
                broken = dict(meta, **{key: value})
                (imported / MANIFEST).write_text(json.dumps(broken))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    plan(imported, [(1, 'SnakeCrow')])
                (imported / MANIFEST).write_text(json.dumps(meta))
            dropped = json.loads(json.dumps(meta))
            del dropped['species']['DangoMushi']
            (imported / MANIFEST).write_text(json.dumps(dropped))
            with self.assertRaises(ValueError):
                plan(imported, [(1, 'SnakeCrow')])
            drifted = json.loads(json.dumps(meta))
            drifted['species']['DangoMushi']['enemy_id'] = 95
            (imported / MANIFEST).write_text(json.dumps(drifted))
            with self.assertRaises(ValueError):
                plan(imported, [(1, 'SnakeCrow')])

    def test_pose_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp))
            (imported / 'SnakeWhole' / 'snake_SnakeWhole_dead_00.mod').write_bytes(b'TAMPERED')
            with self.assertRaises(ValueError):
                plan(imported, [(1, 'SnakeWhole')])

    def test_partial_visual_bank_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp))
            (imported / 'SnakeCrow' / 'snake_SnakeCrow_dead_00.mod').unlink()
            with self.assertRaises(ValueError):
                plan(imported, [(1, 'SnakeCrow')])


class InstallTests(unittest.TestCase):
    def make_run(self, root):
        run = root / 'run'
        (run / ROOM).mkdir(parents=True)
        return run

    def test_install_and_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            receipt = install(imported, run, FAMILY)
            self.assertEqual(receipt['visuals'], 'installed')
            self.assertEqual(len(receipt['file_sha256']), 12)
            for name, digest in receipt['file_sha256'].items():
                data = (run / ROOM / name).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
            verified = verify_install(imported, run, FAMILY)
            self.assertEqual(verified['verified'], sorted(receipt['file_sha256']))
            config = (run / ACTORS_TXT).read_text().split()
            self.assertEqual(config[:5], [ACTORS_HEADER, '3', '376001',
                                          'SnakeCrow', '376002'])

    def test_install_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, FAMILY)
            with self.assertRaises(ValueError):
                install(imported, run, [(376004, 'SnakeCrow')])

    def test_sibling_generator_overlap_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            (run / 'p2-kogane-actors.txt').write_text(
                'P2_KOGANE_ACTORS_1 1\n376001\n')
            with self.assertRaises(ValueError):
                install(imported, run, FAMILY)

    def test_verify_detects_tampered_installed_pose(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, FAMILY)
            (run / ROOM / 'snake_DangoMushi_dead_00.mod').write_bytes(b'X')
            with self.assertRaises(ValueError):
                verify_install(imported, run, FAMILY)

    def test_verify_detects_config_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, FAMILY)
            (run / ACTORS_TXT).write_text('P2_SNAGRET_ACTORS_1\n1\n')
            with self.assertRaises(ValueError):
                verify_install(imported, run, FAMILY)

    def test_verify_requires_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, FAMILY)
            (run / INSTALL_JSON).unlink()
            with self.assertRaises(Exception):
                verify_install(imported, run, FAMILY)

    def test_receipt_keeps_shared_base_and_standalone_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            receipt = install(imported, run, FAMILY)
            self.assertEqual(receipt['classification']['shared_base'],
                             {'SnakeCrow': 'SnakeJointMgr',
                              'SnakeWhole': 'SnakeJointMgr'})
            self.assertEqual(receipt['classification']['standalone'],
                             {'DangoMushi': 'EnemyBlendAnimatorBase::ProperAnimator'})
            self.assertNotIn('DangoMushi', receipt['classification']['shared_base'])
            self.assertEqual(receipt['enemy_ids'], IDS)

    def test_absent_visuals_preserve_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported', visuals=False)
            run = self.make_run(Path(tmp))
            receipt = install(imported, run, FAMILY)
            self.assertEqual(receipt['visuals'], 'absent_baseline_preserved')
            self.assertEqual(receipt['file_sha256'], {})
            self.assertEqual(list((run / ROOM).iterdir()), [])
            verify_install(imported, run, FAMILY)

    def test_non_junction_room_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = Path(tmp) / 'run'
            run.mkdir()
            with self.assertRaises(ValueError):
                install(imported, run, FAMILY)


class ArenaContractTests(unittest.TestCase):
    def test_proxy_types_match_native_registry(self):
        # tekimgr.cpp tekiNames: 3 "chappy" (P1 ordinary control)
        self.assertEqual(P1_CHAPPY_TYPE, 3)
        self.assertEqual(P1_TEMPLATE_ENEMY_TYPE, 3)

    def test_gates_cover_batch1_open_items(self):
        for gate in ('native_identity', 'shared_snake_joint_spine', 'appear_burrow',
                     'directional_bite', 'run1_jump', 'segmented_roll_turn',
                     'attack2_flick', 'falling_helpers', 'brk_material_loop',
                     'death_corpse', 'day_floor_reset', 'save_load',
                     'piklopedia_observation'):
            self.assertIn(gate, GATES)

    def test_roster_requires_real_stage_records(self):
        with self.assertRaises(Exception):
            roster(Path('missing'))


if __name__ == '__main__':
    unittest.main()
