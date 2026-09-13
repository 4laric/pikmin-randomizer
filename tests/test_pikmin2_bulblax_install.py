import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_bulblax_assets import SPECIES
from experimental.pikmin2_bulblax_bank import HEADER as BANK_HEADER, POLICIES
from experimental.pikmin2_bulblax_install import (
    EXPECTATIONS, MANIFEST, SCHEMA, DEFAULT_SQUAD, ZERO_SQUAD,
    emit, install, validate)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mod_blob(species, clip, index):
    return (f'{species}:{clip}:{index}').encode()


# One converted clip per species keeps the synthetic bank small; emit/validate
# must still cover every pose the bank report declares.
MOTIONS = {'Queen': {'wait1': {'poses': 2, 'source_frames': 60, 'frames': [0, 59]}},
           'Baby': {'move': {'poses': 2, 'source_frames': 12, 'frames': [0, 11]}},
           'KingChappy': {'move1': {'poses': 2, 'source_frames': 80, 'frames': [0, 79]}}}

PLACEMENTS = [{'placement_id': 230001, 'species': 'Queen', 'clip': 'wait1',
               'xyz': [-120.0, 30.0, 1800.0]},
              {'placement_id': 230002, 'species': 'Baby', 'clip': 'move',
               'xyz': [-100.0, 30.0, 1820.0]},
              {'placement_id': 230003, 'species': 'KingChappy', 'clip': 'move1',
               'xyz': [150.0, 30.0, 1500.0]}]


def bank_fixture(root, unsupported=None):
    """Synthetic #234 bank build directory; no disc data involved."""
    root.mkdir(parents=True)
    models = {}
    for species, clips in MOTIONS.items():
        for name, info in clips.items():
            for index in range(info['poses']):
                rel = f'{species}/bulblax_{species}_{name}_{index:02}.mod'
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                data = mod_blob(species, name, index)
                path.write_bytes(data)
                models[path.name] = sha(data)
    bank_text = BANK_HEADER + '\n'
    report = {'schema': 1, 'bank': BANK_HEADER,
              'reference_sha256': '0' * 64,
              'normal_policy': {s: dict(p) for s, p in POLICIES.items()},
              'motions': {s: {n: dict(m, mod_bytes=0) for n, m in clips.items()}
                          for s, clips in MOTIONS.items()},
              'unsupported': unsupported or {s: [] for s in MOTIONS},
              'blocked': {s: [] for s in MOTIONS},
              'file_sha256': models,
              'cost': {'poses': 6, 'mod_bytes': 0},
              'limitations': []}
    (root / 'bulblax-bank.json').write_text(json.dumps(report))
    (root / 'p2-bulblax-bank.txt').write_text(bank_text)
    return root


class EmitTests(unittest.TestCase):
    def test_emit_records_schema_identity_clips_and_policies(self):
        with tempfile.TemporaryDirectory() as d:
            bank = bank_fixture(Path(d) / 'bank')
            manifest = emit(bank, list(PLACEMENTS))
            self.assertEqual(manifest['schema'], SCHEMA)
            self.assertEqual(manifest['bank']['header'], BANK_HEADER)
            self.assertEqual(manifest['bank']['sha256'], sha((bank / 'p2-bulblax-bank.txt').read_bytes()))
            identity = {s['name']: s['enemy_id'] for s in manifest['species']}
            self.assertEqual(identity, {'Queen': 30, 'Baby': 31, 'KingChappy': 53})
            self.assertEqual(len(manifest['models']), 6)
            queen = [c for c in manifest['clips']['Queen'] if c['name'] == 'wait1'][0]
            self.assertEqual(queen['source_frames'], 60)
            self.assertEqual(queen['sampled_frames'], [0, 59])
            self.assertEqual(manifest['normal_policy'], POLICIES)
            self.assertNotIn('Baby', manifest['normal_policy'])
            self.assertEqual(manifest['unsupported_frames'], {})

    def test_emit_records_unsupported_frames(self):
        with tempfile.TemporaryDirectory() as d:
            unsupported = {'Queen': [{'clip': 'dead', 'frame': 83,
                                      'unsupported_reason': 'ValueError: Singular normal transform'}],
                           'Baby': [], 'KingChappy': []}
            bank = bank_fixture(Path(d) / 'bank', unsupported)
            manifest = emit(bank, list(PLACEMENTS))
            self.assertEqual(manifest['unsupported_frames']['Queen'], unsupported['Queen'])

    def test_emit_rejects_duplicate_ids_unknown_clip_and_nonfinite_xyz(self):
        with tempfile.TemporaryDirectory() as d:
            bank = bank_fixture(Path(d) / 'bank')
            with self.assertRaises(ValueError):
                emit(bank, [dict(PLACEMENTS[0]), dict(PLACEMENTS[0])])
            with self.assertRaises(ValueError):
                emit(bank, [dict(PLACEMENTS[0], clip='rolling_x')])
            with self.assertRaises(ValueError):
                emit(bank, [dict(PLACEMENTS[0], species='Kochappy')])
            for bad in ([0.0, float('nan'), 0.0], [0.0, float('inf'), 0.0],
                        [0.0, 0.0], '0,0,0', [0.0, 'x', 0.0]):
                with self.assertRaises(ValueError, msg=str(bad)):
                    emit(bank, [dict(PLACEMENTS[0], xyz=bad)])


class ValidateTests(unittest.TestCase):
    def fresh(self, d):
        bank = bank_fixture(Path(d) / 'bank')
        manifest = emit(bank, list(PLACEMENTS))
        return bank, manifest

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            bank, manifest = self.fresh(d)
            self.assertEqual(validate(manifest, bank), manifest)
            path = Path(d) / 'manifest.json'
            path.write_text(json.dumps(manifest))
            self.assertEqual(validate(path, bank)['schema'], SCHEMA)

    def test_rejects_tampered_model_bytes_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            bank, manifest = self.fresh(d)
            target = bank / manifest['models'][0]['path']
            target.write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                validate(manifest, bank)

    def test_rejects_tampered_manifest_bytes_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            bank, manifest = self.fresh(d)
            for entry in (dict(manifest['models'][0], bytes=1),
                          dict(manifest['models'][0], sha256='0' * 64)):
                tampered = dict(manifest, models=[entry] + manifest['models'][1:])
                with self.assertRaises(ValueError):
                    validate(tampered, bank)

    def test_rejects_bad_version_and_wrong_bank(self):
        with tempfile.TemporaryDirectory() as d:
            bank, manifest = self.fresh(d)
            with self.assertRaises(ValueError):
                validate(dict(manifest, schema=2), bank)
            with self.assertRaises(ValueError):
                validate(dict(manifest, bank=dict(manifest['bank'], sha256='0' * 64)), bank)

    def test_rejects_duplicate_placement_ids(self):
        with tempfile.TemporaryDirectory() as d:
            bank, manifest = self.fresh(d)
            dup = dict(manifest, placements=[manifest['placements'][0]] * 2)
            with self.assertRaises(ValueError):
                validate(dup, bank)

    def test_rejects_absolute_and_traversing_paths(self):
        with tempfile.TemporaryDirectory() as d:
            bank, manifest = self.fresh(d)
            entry = manifest['models'][0]
            for bad in ('/etc/passwd', 'C:/windows/x.mod', '../escape.mod',
                        'Queen/../../escape.mod', 'Queen\\x.mod', 'Queen//x.mod'):
                tampered = dict(manifest, models=[dict(entry, path=bad)] + manifest['models'][1:])
                with self.assertRaises(ValueError, msg=bad):
                    validate(tampered, bank)

    def test_rejects_missing_clip_pose_and_wrong_frames(self):
        with tempfile.TemporaryDirectory() as d:
            bank, manifest = self.fresh(d)
            dropped = dict(manifest, models=manifest['models'][1:])
            with self.assertRaises(ValueError):
                validate(dropped, bank)
            bad_clips = json.loads(json.dumps(manifest))
            bad_clips['clips']['Queen'][0]['sampled_frames'] = [0, 58]
            with self.assertRaises(ValueError):
                validate(bad_clips, bank)


class InstallTests(unittest.TestCase):
    def test_install_conserves_hashes_and_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as d:
            bank = bank_fixture(Path(d) / 'bank')
            manifest = emit(bank, list(PLACEMENTS))
            run = Path(d) / 'run'
            receipt = install(manifest, bank, run)
            self.assertEqual(receipt['models'], len(manifest['models']))
            for entry in manifest['models']:
                data = run.joinpath(*entry['path'].split('/')).read_bytes()
                self.assertEqual(sha(data), entry['sha256'])
                self.assertEqual(len(data), entry['bytes'])
            self.assertEqual(sha((run / MANIFEST).read_bytes()), receipt['manifest_sha256'])
            self.assertTrue((run / EXPECTATIONS).is_file())
            snapshot = {p.name for p in run.iterdir()}
            with self.assertRaises(ValueError):
                install(manifest, bank, run)
            self.assertEqual({p.name for p in run.iterdir()}, snapshot)  # untouched

    def test_refusal_precedes_any_copy(self):
        with tempfile.TemporaryDirectory() as d:
            bank = bank_fixture(Path(d) / 'bank')
            manifest = emit(bank, list(PLACEMENTS))
            target = bank / manifest['models'][0]['path']
            target.write_bytes(b'tampered')
            run = Path(d) / 'run'
            with self.assertRaises(ValueError):
                install(manifest, bank, run)
            self.assertFalse(run.exists())


class ExpectationsTests(unittest.TestCase):
    def test_expectations_well_formed_with_default_and_zero_squads(self):
        with tempfile.TemporaryDirectory() as d:
            bank = bank_fixture(Path(d) / 'bank')
            emit(bank, list(PLACEMENTS), Path(d) / 'out' / MANIFEST)
            payload = json.loads((Path(d) / 'out' / EXPECTATIONS).read_text())
            self.assertEqual(payload['schema'], 1)
            self.assertEqual(set(payload['fixtures']), {'default', 'zero_population'})
            default = payload['fixtures']['default']
            self.assertEqual(default['starting_squad'], DEFAULT_SQUAD)
            self.assertGreater(sum(DEFAULT_SQUAD.values()), 0)
            self.assertEqual(payload['fixtures']['zero_population']['starting_squad'], ZERO_SQUAD)
            ids = set()
            for placement in default['placements']:
                ids.add(placement['generator'])
                self.assertIn(placement['species'], SPECIES)
                self.assertEqual(placement['enemy_id'], SPECIES[placement['species']])
                self.assertEqual(len(placement['expected_xyz']), 3)
                self.assertTrue(all(isinstance(v, float) for v in placement['expected_xyz']))
            self.assertEqual(len(ids), len(PLACEMENTS))
            self.assertTrue(all(v == 'untested' for v in default['gates'].values()))


if __name__ == '__main__':
    unittest.main()
