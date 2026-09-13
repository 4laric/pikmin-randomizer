import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_bulblax_bank import (HEADER, CLIP_BYTES, TOTAL_BYTES, LIMITATIONS,
                                               parse_bank, validate_files, build)
from experimental.pikmin2_bulblax_assets import CLIPS, TEXT


def sha(data):
    return hashlib.sha256(data).hexdigest()


def model_blob():
    # Minimal valid J3D2bmd3 container with zero blocks; decode is stubbed.
    data = bytearray(40)
    data[:8] = b'J3D2bmd3'
    struct.pack_into('>II', data, 8, 40, 0)
    return bytes(data)


BANK_TEXT = (HEADER + '\n'
             'Queen 2\n'
             'dead 2 140 0 139\n'
             'sleep 2 120 0 119\n'
             'Baby 1\n'
             'move 3 12 0 6 11\n'
             'KingChappy 0\n')


def mod_blob(tag_shift=0):
    return b''.join(struct.pack('>II', tag + tag_shift, 0) for tag in (32, 34, 48, 65535))


def imported_fixture(root):
    """Synthetic #217 import directory; no disc data, conversion is stubbed."""
    for species in ('Queen', 'Baby', 'KingChappy'):
        folder = root / species
        folder.mkdir(parents=True)
        model = model_blob()
        (folder / 'enemy.bmd').write_bytes(model)
        clips = []
        for name in CLIPS[species]:
            raw = f'{species}:{name}'.encode()
            (folder / (name + '.bca')).write_bytes(raw)
            clips.append({'name': name, 'source_sha256': sha(raw), 'source_frames': 12,
                          'unsupported_reason': 'KeyError: 10'} if species == 'KingChappy' else
                         {'name': name, 'source_sha256': sha(raw), 'source_frames': 12})
        report_species = report_species_entry(model, clips, species)
        report.setdefault('species', {})[species] = report_species_entry(model, clips, species)
    (root / 'p2-bulblax.txt').write_text(TEXT)
    (root / 'bulblax.json').write_text(json.dumps(report))
    return root


def report_species_entry(model, clips, species):
    return {'model_sha256': sha(model), 'joints': ['root'],
            'skinning': {'envelopes': 6 if species == 'Queen' else 0,
                         'draw_matrices': 5,
                         'weighted_baking': species == 'Queen',
                         'self_contained_resources': True},
            'clips': clips}


report = {'schema': 1, 'policy': 'P2_BULBLAX_IMPORT_1', 'species': {}}


class ParseBankTests(unittest.TestCase):
    def test_round_trip(self):
        bank = parse_bank(BANK_TEXT)
        self.assertEqual(bank['Queen']['sleep'], {'poses': 2, 'source_frames': 120, 'frames': [0, 119]})
        self.assertEqual(bank['Queen']['dead']['frames'], [0, 139])
        self.assertEqual(bank['Baby']['move']['frames'], [0, 6, 11])
        self.assertEqual(bank['KingChappy'], {})

    def test_rejects_bad_header_species_order_and_frames(self):
        for bad in (BANK_TEXT.replace(HEADER, 'P2_SNOW_2'),
                    BANK_TEXT.replace('Queen 2', 'Kochappy 2'),
                    BANK_TEXT.replace('dead 2 140 0 139\nsleep', 'sleep 2 120 0 119\ndead'),
                    BANK_TEXT.replace('0 6 11', '0 11 6'),
                    BANK_TEXT.replace('0 119', '0 120'),
                    BANK_TEXT.replace('Queen 2', 'Queen 3'),
                    BANK_TEXT + 'tail'):
            with self.assertRaises(ValueError, msg=bad[:40]):
                parse_bank(bad)

    def test_rejects_duplicate_species(self):
        with self.assertRaises(ValueError):
            parse_bank(BANK_TEXT + 'Baby 0\n')


class ValidateFilesTests(unittest.TestCase):
    def fixture(self, root):
        bank = parse_bank(BANK_TEXT)
        for species, clips in bank.items():
            (root / species).mkdir(parents=True, exist_ok=True)
            for name, info in clips.items():
                for index in range(info['poses']):
                    (root / species / f'bulblax_{species}_{name}_{index:02}.mod').write_bytes(mod_blob())
        return bank

    def test_budget_and_resource_immutability(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bank = self.fixture(root)
            paths, total = validate_files(root, bank)
            self.assertEqual(len(paths), 7)
            self.assertEqual(total, 7 * len(mod_blob()))
            # Cross-pose resource drift within a species is rejected.
            (root / 'Queen' / 'bulblax_Queen_sleep_01.mod').write_bytes(mod_blob() + b'x')
            with self.assertRaises(ValueError):
                validate_files(root, bank)

    def test_empty_pose_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bank = self.fixture(root)
            (root / 'Baby' / 'bulblax_Baby_move_00.mod').write_bytes(b'')
            with self.assertRaises(ValueError):
                validate_files(root, bank)


class BuildTests(unittest.TestCase):
    def fake_pose(self, clip, frame, joints, allow_scale=False):
        return 12, None

    def fake_convert(self, model, model_blocks, envelopes, joint_count, clip, frame, output):
        if frame == 2:  # deterministic unsupported frame, like Queen dead 83/111/139
            raise ValueError('Singular normal transform')
        output.write_bytes(mod_blob())

    def run_build(self, root, output, **kw):
        with patch('experimental.pikmin2_bulblax_bank.bca_pose', side_effect=self.fake_pose), \
             patch('experimental.pikmin2_bulblax_bank._convert_pose', side_effect=self.fake_convert):
            return build(root, output, **kw)

    def test_build_records_unsupported_and_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = imported_fixture(Path(d) / 'imported')
            result = self.run_build(root, Path(d) / 'bank')
            # 9 Queen + 6 Baby clips x 6 sampled frames, frame 2 unsupported in each.
            self.assertEqual(len(result['unsupported']['Queen']), 9)
            self.assertEqual(len(result['unsupported']['Baby']), 6)
            self.assertTrue(all(u['frame'] == 2 for u in result['unsupported']['Queen']))
            self.assertEqual(len(result['blocked']['KingChappy']), 14)
            self.assertTrue(all(b['reason'] == 'KeyError: 10' for b in result['blocked']['KingChappy']))
            self.assertEqual(result['motions']['Baby'].keys(), set(CLIPS['Baby']))
            self.assertEqual(result['cost']['poses'], 9 * 5 + 6 * 5)
            # Bank text round-trips and carries no KingChappy rows.
            text = (Path(d) / 'bank' / 'p2-bulblax-bank.txt').read_text()
            self.assertEqual(parse_bank(text)['KingChappy'], {})
            self.assertEqual(result['reference_sha256'], sha((root / 'bulblax.json').read_bytes()))
            self.assertTrue(any('KingChappy' in lim for lim in result['limitations']))
            self.assertEqual(result['limitations'], LIMITATIONS)

    def test_tampered_model_clip_and_report_fail_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = imported_fixture(Path(d) / 'imported')
            (root / 'Baby' / 'enemy.bmd').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                self.run_build(root, Path(d) / 'bank')
            self.assertFalse((Path(d) / 'bank').exists())
        with tempfile.TemporaryDirectory() as d:
            root = imported_fixture(Path(d) / 'imported')
            (root / 'Queen' / 'sleep.bca').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                self.run_build(root, Path(d) / 'bank')
            self.assertFalse((Path(d) / 'bank').exists())
        with tempfile.TemporaryDirectory() as d:
            root = imported_fixture(Path(d) / 'imported')
            entry = json.loads((root / 'bulblax.json').read_text())
            entry['policy'] = 'P2_OTHER_1'
            (root / 'bulblax.json').write_text(json.dumps(entry))
            with self.assertRaises(ValueError):
                self.run_build(root, Path(d) / 'bank')
            self.assertFalse((Path(d) / 'bank').exists())

    def test_pose_limit_bounds_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = imported_fixture(Path(d) / 'imported')
            for bad in (0, 1, 13, True, '6'):
                with self.assertRaises(ValueError):
                    build(root, Path(d) / f'bank-{bad}', bad)
            existing = Path(d) / 'bank'
            existing.mkdir()
            with self.assertRaises(ValueError):
                build(root, existing)

    def test_wrong_profile_text_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = imported_fixture(Path(d) / 'imported')
            (root / 'p2-bulblax.txt').write_text(TEXT.replace('queen_health 5000', 'queen_health 4999'))
            with self.assertRaises(ValueError):
                self.run_build(root, Path(d) / 'bank')
            self.assertFalse((Path(d) / 'bank').exists())


if __name__ == '__main__':
    unittest.main()
