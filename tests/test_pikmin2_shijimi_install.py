"""Unit tests for the lane-15 ShijimiChou staging and lifecycle contract (#166)."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

import experimental.pikmin2_shijimi_install as inst
from experimental.pikmin2_shijimi_install import (
    ACTORS_HEADER, BANK_HEADER, CLIPS, EXPECTED_EVENTS, SOURCE_ID, install,
    payload, verify_install)
import experimental.pikmin2_shijimi_lifecycle as life


def mod_bytes(seed):
    def chunk(tag, body):
        return struct.pack('>II', tag, len(body)) + body
    return (chunk(32, bytes([seed]) * 8) + chunk(34, bytes([seed + 1]) * 4)
            + chunk(48, bytes([seed + 2]) * 2) + struct.pack('>II', 65535, 0))


def write_import(root, enemy_id=77, bad_events=False, hash_break=False):
    root.mkdir(parents=True)
    species = root / 'ShijimiChou'
    species.mkdir()
    durations = {'carry': 40, 'dead': 61, 'move': 8}
    clips = []
    reference = mod_bytes(1)
    for name in CLIPS:
        duration = durations[name]
        events = [[9, 9]] if (bad_events and name == 'carry') else EXPECTED_EVENTS[name]
        poses = []
        for index, frame in enumerate((0, duration - 1)):
            data = reference if index == 0 else mod_bytes(1)
            filename = f'fly_ShijimiChou_{name}_{index:02}.mod'
            (species / filename).write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            if hash_break and name == 'carry' and index == 0:
                digest = '0' * 64
            poses.append(dict(file=filename, frame=frame, sha256=digest))
        clips.append(dict(name=name, source_frames=duration, events=events, poses=poses))
    manifest = dict(schema=1, policy='P2_FLYING_1', native_ready=False,
                    species={'ShijimiChou': dict(enemy_id=enemy_id, clips=clips)})
    (root / 'flying.json').write_text(json.dumps(manifest))
    return root


def make_run(root):
    run = root / 'run'
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    return run


class ShijimiInstallTests(unittest.TestCase):
    def test_bank_header_and_clip_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = write_import(root / 'imported')
            bank, files, poses = payload(imported)
            lines = bank.decode().splitlines()
            self.assertEqual(lines[0], BANK_HEADER)
            self.assertEqual([line.split()[0] for line in lines[1:]], list(CLIPS))
            self.assertEqual(poses, 6)
            self.assertTrue(all(name.startswith('shijimi_') for name in files))

    def test_install_and_verify_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = write_import(root / 'imported')
            run = make_run(root)
            receipt = install(imported, run, [204001, 204002])
            self.assertEqual(receipt['generators'], [204001, 204002])
            self.assertEqual(receipt['source_id'], SOURCE_ID)
            self.assertTrue((run / 'p2-shijimi-bank.txt').is_file())
            self.assertEqual((run / 'p2-shijimi-actors.txt').read_text(),
                             f'{ACTORS_HEADER} 2\n204001\n204002\n')
            verified = verify_install(imported, run, [204001, 204002])
            self.assertEqual(verified['poses'], 6)

    def test_rejects_wrong_enemy_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = write_import(root / 'imported', enemy_id=16)
            with self.assertRaises(ValueError):
                payload(imported)

    def test_rejects_unexpected_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = write_import(root / 'imported', bad_events=True)
            with self.assertRaises(ValueError):
                payload(imported)

    def test_rejects_pose_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = write_import(root / 'imported', hash_break=True)
            with self.assertRaises(ValueError):
                payload(imported)

    def test_refuses_duplicate_or_overlapping_actors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = write_import(root / 'imported')
            run = make_run(root)
            with self.assertRaises(ValueError):
                install(imported, run, [204001, 204001])
            install(imported, run, [204001])
            with self.assertRaises(ValueError):
                install(imported, run, [204001])


GOOD_LOG = '\n'.join([
    'P2_SHIJIMI_BIND generator=204001 source_id=77 visual_only=0',
    'P2_ENEMY_READY species=ShijimiChou native_family=Chappy generator=204001 x=0.0 y=70.0 '
    'z=0.0 health=200.0 max_health=200.0 behavior=native source_FSM=implemented attack=none '
    'reward=P1_nectar source=plants leader=1 group_count=2',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_SHIJIMI_BANK poses=6 mod_bytes=100 texture_attach_calls=3 load_seconds=0.010',
    'P2_SHIJIMI_STATE generator=204001 state=wait',
    'P2_SHIJIMI_STATE generator=204001 state=fly',
    'P2_SHIJIMI_DRAW corpse=0',
    'P2_SHIJIMI_STATE generator=204001 state=leave',
])


class ShijimiLifecycleTests(unittest.TestCase):
    def test_contract(self):
        contract = life.contract()
        self.assertEqual(contract['schema'], 'p2-shijimi-lifecycle-v1')
        self.assertEqual(life.SOURCE_ID, 77)
        self.assertEqual(life.STATE_IDS, {'wait': 0, 'fly': 1, 'fall': 2, 'dead': 3,
                                          'leave': 4, 'rest': 5})
        self.assertEqual(life.ANIM_IDS, {'carry': 0, 'dead': 1, 'move': 2})

    def test_validator_accepts_good_log(self):
        result = life.validate_lifecycle(GOOD_LOG)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['no_extinction'])

    def test_validator_rejects_extinction(self):
        result = life.validate_lifecycle(GOOD_LOG + '\nExtinction')
        self.assertFalse(result['passed'])

    def test_validator_rejects_missing_window(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines() if 'window set' not in line)
        self.assertFalse(life.validate_lifecycle(log)['passed'])

    def test_validator_requires_departure(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines() if 'state=leave' not in line)
        result = life.validate_lifecycle(log)
        self.assertFalse(result['checks']['departure'])


if __name__ == '__main__':
    unittest.main()
