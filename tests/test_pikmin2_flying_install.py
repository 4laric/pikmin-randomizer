"""Flying install/arena tests covering INSTALLED artifacts, not just output/ (#375)."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import experimental.pikmin2_flying_arena as arena
from experimental.pikmin2_flying_assets import (
    CLIPS, DISC_PARMS, EXPECTED_EVENTS, HELPER_SPECIES, SHIJIMICHOU_GROUP_COUNT, SPECIES)
from experimental.pikmin2_flying_install import (
    ACTORS_HEADER, ACTORS_TXT, INSTALL_JSON, MANIFEST, PROFILE_TXT, install, plan,
    verify_install)

SPAWNABLE = ('Mar', 'Hanachirashi')


def fake_imported(root, poses_per_clip=2):
    """Synthetic schema-1 flying import: real bytes, recorded hashes."""
    root.mkdir(parents=True, exist_ok=True)
    species_info = {}
    for name in SPECIES:
        directory = root / name
        directory.mkdir()
        clips = []
        for clip in CLIPS[name]:
            poses = []
            for index in range(poses_per_clip):
                filename = f'fly_{name}_{clip}_{index:02}.mod'
                data = f'{name}:{clip}:{index}'.encode()
                (directory / filename).write_bytes(data)
                poses.append({'file': filename, 'frame': index, 'bytes': len(data),
                              'sha256': hashlib.sha256(data).hexdigest()})
            clips.append({'name': clip,
                          'source_sha256': hashlib.sha256(clip.encode()).hexdigest(),
                          'source_frames': 40,
                          'events': [list(event) for event in EXPECTED_EVENTS[name][clip]],
                          'loop_attribute': 2, 'loop_semantics': 'repeat',
                          'event_loop_boundaries': [], 'poses': poses, 'status': 'converted'})
        species_info[name] = {
            'enemy_id': SPECIES[name], 'common_name': name,
            'helper_only': name in HELPER_SPECIES,
            'role': 'helper only' if name in HELPER_SPECIES else 'concrete spawnable',
            'proper_retail': dict(DISC_PARMS[name]['proper']),
            'parameter_blocks': [{'s000': 0.5}, dict(DISC_PARMS[name]['general']),
                                 dict(DISC_PARMS[name]['proper'])],
            'clips': clips}
    manifest = {'schema': 1, 'policy': 'P2_FLYING_1', 'native_ready': False,
                'gameplay_events_executed': False, 'btk_playback': False,
                'species': species_info}
    (root / MANIFEST).write_text(json.dumps(manifest))
    return root


def core_actors():
    return [(375001, 'Mar'), (375002, 'Hanachirashi')]


class PlanTests(unittest.TestCase):
    def test_actor_count_rejected_before_io(self):
        for actors in ([], [(i, 'Mar') for i in range(101)]):
            with self.subTest(n=len(actors)), self.assertRaises(ValueError):
                plan(Path('missing'), actors)

    def test_duplicate_and_invalid_ids_rejected_before_io(self):
        cases = [[(5, 'Mar'), (5, 'Mar')], [(-1, 'Mar')], [('5', 'Mar')],
                 [(True, 'Mar')], [(1, 'ShijimiChou')], [(1, 'Chappy')]]
        for actors in cases:
            with self.subTest(actors=actors), self.assertRaises(ValueError):
                plan(Path('missing'), actors)

    def test_schema_and_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            meta = json.loads((imported / MANIFEST).read_text())
            cases = {
                'schema': dict(meta, schema=2),
                'policy': dict(meta, policy='P2_OTHER_1'),
                'native_ready': dict(meta, native_ready=True),
                'species-set': dict(meta, species={'Mar': meta['species']['Mar']}),
                'enemy-id': dict(meta, species=dict(
                    meta['species'], Mar=dict(meta['species']['Mar'], enemy_id=30))),
                'helper-flag': dict(meta, species=dict(
                    meta['species'], Mar=dict(meta['species']['Mar'], helper_only=True))),
            }
            for key, value in cases.items():
                (imported / MANIFEST).write_text(json.dumps(value))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    plan(imported, [(1, 'Mar')])
                (imported / MANIFEST).write_text(json.dumps(meta))

    def test_pose_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            (imported / 'Mar/fly_Mar_dead_00.mod').write_bytes(b'TAMPERED')
            with self.assertRaises(ValueError):
                plan(imported, [(1, 'Mar')])

    def test_partial_visual_bank_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            next((imported / 'Hanachirashi').glob('*.mod')).unlink()
            with self.assertRaises(ValueError):
                plan(imported, [(1, 'Mar'), (2, 'Hanachirashi')])


class InstallTests(unittest.TestCase):
    def make_run(self, root):
        run = root / 'run'
        (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
        return run

    def test_install_and_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            actors = core_actors()
            receipt = install(imported, run, actors)
            self.assertEqual(receipt['visuals'], 'installed')
            expected = (len(CLIPS['Mar']) + len(CLIPS['Hanachirashi'])) * 2
            self.assertEqual(len(receipt['file_sha256']), expected)
            config = (run / ACTORS_TXT).read_text()
            self.assertEqual(config.split(),
                             [ACTORS_HEADER, '2', '375001', 'Mar', '375002', 'Hanachirashi'])
            for name, digest in receipt['file_sha256'].items():
                installed = (run / 'assets/dataDir/courses/pikmin2room' / name).read_bytes()
                self.assertEqual(hashlib.sha256(installed).hexdigest(), digest)
            verified = verify_install(imported, run, actors)
            self.assertEqual(verified['verified'], sorted(receipt['file_sha256']))
            self.assertEqual(verified['actors'], [375001, 375002])
            self.assertEqual(verified['config'], ACTORS_TXT)

    def test_helper_excluded_from_actors_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            receipt = install(imported, run, core_actors())
            self.assertEqual(receipt['helper']['species'], 'ShijimiChou')
            self.assertFalse(receipt['helper']['spawnable_actor'])
            self.assertFalse(receipt['helper']['installed_visuals'])
            self.assertEqual(receipt['helper']['group_count'], SHIJIMICHOU_GROUP_COUNT)
            self.assertNotIn('ShijimiChou', (run / ACTORS_TXT).read_text())
            room = run / 'assets/dataDir/courses/pikmin2room'
            self.assertEqual(list(room.glob('fly_ShijimiChou_*.mod')), [])
            self.assertIn('helper_group_count ShijimiChou 25',
                          (run / PROFILE_TXT).read_text())

    def test_absent_visual_bank_preserves_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            for name in SPAWNABLE:
                for pose in (imported / name).glob('*.mod'):
                    pose.unlink()
            run = self.make_run(Path(tmp))
            receipt = install(imported, run, core_actors())
            self.assertEqual(receipt['visuals'], 'absent_baseline_preserved')
            self.assertEqual(receipt['file_sha256'], {})
            self.assertEqual(list((run / 'assets/dataDir/courses/pikmin2room').iterdir()), [])

    def test_install_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, core_actors())
            with self.assertRaises(ValueError):
                install(imported, run, [(375003, 'Mar')])

    def test_verify_detects_tampered_installed_pose(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, core_actors())
            target = run / 'assets/dataDir/courses/pikmin2room/fly_Mar_dead_00.mod'
            target.write_bytes(b'X')
            with self.assertRaises(ValueError):
                verify_install(imported, run, core_actors())

    def test_verify_detects_config_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            install(imported, run, core_actors())
            (run / ACTORS_TXT).write_text(f'{ACTORS_HEADER}\n2\n')
            with self.assertRaises(ValueError):
                verify_install(imported, run, core_actors())
            (run / PROFILE_TXT).write_text('P2_FLYING_PROFILE_1\n')
            with self.assertRaises(ValueError):
                verify_install(imported, run, core_actors())

    def test_sibling_generator_overlap_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = self.make_run(Path(tmp))
            (run / 'p2-kogane-actors.txt').write_text('P2_KOGANE_ACTORS_1 1\n375001\n')
            with self.assertRaises(ValueError):
                install(imported, run, core_actors())

    def test_non_junction_room_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = fake_imported(Path(tmp) / 'imported')
            run = Path(tmp) / 'run'
            run.mkdir()
            with self.assertRaises(ValueError):
                install(imported, run, core_actors())


def entry(kind=b'iket', identity=1):
    record = bytearray(100)
    record[:8] = b'    0.0v'
    struct.pack_into('<I', record, 8, identity)
    record[72:76] = kind
    return bytes(record)


class ArenaContractTests(unittest.TestCase):
    def test_proxy_types_match_native_registry(self):
        # tekimgr.cpp tekiNames: 16 "mar" (P1 Puffy Blowhog), 3 "chappy" (control)
        self.assertEqual(arena.P1_PUFFY_TYPE, 16)
        self.assertEqual(arena.P1_CHAPPY_TYPE, 3)

    def test_gates_cover_batch1_open_items(self):
        for gate in ('native_identity', 'natural_AI', 'wind_attack', 'flick_shakeoff',
                     'death_corpse', 'day_floor_reset', 'save_load',
                     'piklopedia_observation', 'helper_group_ownership'):
            self.assertIn(gate, arena.GATES)
        self.assertEqual(set(arena.GATES), set(arena.GATE_STATES))
        for state in arena.GATE_STATES.values():
            self.assertTrue(state.startswith('blocked'), state)

    def test_helper_metadata_not_spawned(self):
        self.assertEqual(arena.HELPER_METADATA['species'], 'ShijimiChou')
        self.assertFalse(arena.HELPER_METADATA['spawned'])
        self.assertFalse(arena.HELPER_METADATA['installed_visuals'])
        self.assertEqual(arena.HELPER_METADATA['group_count'], SHIJIMICHOU_GROUP_COUNT)

    def test_roster_requires_real_stage_records(self):
        with self.assertRaises(Exception):
            arena.roster(Path('missing'))

    def test_roster_stages_two_species_plus_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp)
            source = assets / 'dataDir/stages/practice/default.gen'
            source.parent.mkdir(parents=True)
            source.write_bytes(b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))
            with patch.object(arena, 'records', return_value=[entry(b'goal')]), \
                    patch.object(arena, 'generator', return_value=b'x' * 24 + entry()):
                data, actors = arena.roster(assets)
            self.assertEqual(struct.unpack_from('>I', data, 20)[0], 4)
            self.assertEqual([a['generator'] for a in actors], [375001, 375002, 375003])
            self.assertEqual([a['source_species'] for a in actors],
                             ['Mar', 'Hanachirashi', None])
            self.assertEqual([a['native_teki_type'] for a in actors],
                             [arena.P1_PUFFY_TYPE, arena.P1_PUFFY_TYPE, arena.P1_CHAPPY_TYPE])
            for actor in actors:
                self.assertEqual(actor['offset'], [0, 0, 0])
                self.assertIsNone(actor['source_yaw'])
                self.assertFalse(actor['source_yaw_applied'])
                self.assertEqual(len(actor['expected_xyz']), 3)


if __name__ == '__main__':
    unittest.main()
