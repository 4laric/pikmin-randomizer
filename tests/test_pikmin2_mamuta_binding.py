"""Mamuta native-binding evidence tests (batch 3, #221).

Covers the production binding contract (READY identity/type/XYZ, native
resource loads, zero GX desync), the material-fidelity profile of the
installed poses, and byte-identity of installed artifacts. P2 planting,
population cap and follower lifecycle are native dependencies, not tested.
"""
import json
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_mamuta_binding import (
    BOUND_POSES, EXPECTED_MATERIAL_POLICY, installed_bytes_match,
    material_profile, validate_session_log)

READY = ('P2_MAMUTA_READY generator=221001 native_type=24 '
         'xyz=-150.000000,30.000000,1850.000000 P1_proxy_static_anchors_no_P2_planting\n')
RESOURCES = ''.join(f'[PC Port] DVDOpen("{r}") -> OK, size = 1\n' for r in (
    'dataDir/tekipara/miurin.bin', 'dataDir/tekis/miurin/miurin.mod',
    'dataDir/tekis/miurin/miurin.anm', 'dataDir/tekikeys/miurin.key'))


def conversion(**overrides):
    base = {'source': 'enemy.bmd', 'output': 'wait_00.mod', 'vertices': 401,
            'triangles': 786, 'shapes': 2, 'textures': 2,
            'bounds': [-36.0, -1.4, -22.8, 42.4, 60.0, 37.7],
            'discarded_attributes': [], 'material_policy': EXPECTED_MATERIAL_POLICY}
    return dict(base, **overrides)


def metadata(imported):
    poses = {'wait.bca': 'wait_00.mod', 'dead.bca': 'dead_02.mod',
             'attack1.bca': 'attack1_00.mod'}
    import hashlib
    clips = []
    for clip, name in poses.items():
        data = (imported / 'Miulin' / name).read_bytes()
        clips.append({'file': clip, 'status': 'converted',
                      'poses': [{'file': name, 'sha256': hashlib.sha256(data).hexdigest()}]})
    return {'schema': 1, 'species': 'Miulin', 'enemy_id': 54, 'clips': clips}


class SessionLogTests(unittest.TestCase):
    def test_valid_session_accepted(self):
        result = validate_session_log(RESOURCES + READY + '[PC Port] FPS: 30.0\n')
        self.assertEqual(result['generator'], 221001)
        self.assertEqual(result['native_type'], 24)
        self.assertEqual(result['birth_xyz'], [-150.0, 30.0, 1850.0])
        self.assertEqual(result['gx_desync'], 0)
        self.assertIn('no P2 planting parity', result['scope'])

    def test_missing_or_duplicate_ready_rejected(self):
        with self.assertRaises(ValueError):
            validate_session_log(RESOURCES)
        with self.assertRaises(ValueError):
            validate_session_log(RESOURCES + READY + READY)

    def test_identity_mismatch_rejected(self):
        for bad in ('generator=221002', 'native_type=3',
                    'xyz=-150.000000,30.000000,1900.000000'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_session_log(RESOURCES + READY.replace(
                    'generator=221001' if 'generator' in bad else
                    'native_type=24' if 'native_type' in bad else
                    'xyz=-150.000000,30.000000,1850.000000', bad))

    def test_gx_desync_rejected(self):
        with self.assertRaises(ValueError):
            validate_session_log(RESOURCES + READY + '[PC GX] DESYNC at shape 0\n')

    def test_missing_miurin_resource_rejected(self):
        with self.assertRaises(ValueError):
            validate_session_log(READY)


class MaterialProfileTests(unittest.TestCase):
    def test_retail_conversion_profile(self):
        result = material_profile(conversion())
        self.assertEqual(result['material_fidelity'], 'partial')
        self.assertEqual(result['textures'], 2)
        self.assertEqual(result['vertices'], 401)

    def test_unsupported_material_variants_rejected(self):
        for bad in ({'textures': 1}, {'shapes': 1}, {'material_policy': 'full TEV'},
                    {'discarded_attributes': ['nbt']}, {'vertices': 0},
                    {'bounds': [0.0, 0.0, 0.0]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                material_profile(conversion(**bad))


class InstalledBytesTests(unittest.TestCase):
    def make_tree(self, root):
        imported = root / 'imported'
        room = root / 'room'
        (imported / 'Miulin').mkdir(parents=True)
        room.mkdir()
        for name in ('wait_00.mod', 'dead_02.mod', 'attack1_00.mod'):
            (imported / 'Miulin' / name).write_bytes(name.encode() * 3)
        for name in BOUND_POSES:
            (room / name).write_bytes({'miulin_wait.mod': b'wait_00.mod' * 3,
                                       'miulin_dead.mod': b'dead_02.mod' * 3,
                                       'miulin_attack1.mod': b'attack1_00.mod' * 3}[name])
        return imported, room

    def test_installed_bytes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported, room = self.make_tree(Path(tmp))
            result = installed_bytes_match(room, imported, metadata(imported))
            self.assertEqual(sorted(result), sorted(BOUND_POSES))

    def test_missing_or_mismatched_pose_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported, room = self.make_tree(Path(tmp))
            (room / 'miulin_dead.mod').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                installed_bytes_match(room, imported, metadata(imported))
            (room / 'miulin_dead.mod').unlink()
            with self.assertRaises(ValueError):
                installed_bytes_match(room, imported, metadata(imported))


if __name__ == '__main__':
    unittest.main()
