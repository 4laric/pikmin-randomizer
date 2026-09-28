import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_convert import Writer, u32
from experimental.pikmin2_frog_visual_audit import chunks
from experimental.pikmin2_bulblax_assets import CLIPS, TEXT
from experimental.pikmin2_bulblax_bank import HEADER, parse_bank
from experimental import pikmin2_bulblax_material as bm


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tex_model(shapes):
    """Synthetic emitted pose: `shapes` entries of (tex, rgba, control).

    tex >= 0 builds a 152-byte record with one texture; tex == -1 builds an
    84-byte textureless record. Mirrors the converter writer layout
    (pikmin2_convert.py:263-280).
    """
    w = Writer()
    w.begin(16, 1)
    w.pad()
    w.put('3f', 1, 2, 3)
    w.end()
    textures = max((t for t, _, _ in shapes), default=-1) + 1
    w.begin(32, textures)
    w.pad()
    for _ in range(textures):
        w.data += bytes(32)
    w.end()
    w.begin(34, textures)
    w.pad()
    for i in range(textures):
        w.put('4Hf', i, 0, 0, 0, 0.)
    w.end()
    w.begin(48, len(shapes), len(shapes))
    w.pad()
    for _ in shapes:
        w.data += bytes(88)
        w.put('I', 1)
        w.data += bytes(32)
    for tex, rgba, control in shapes:
        r = len(w.data)
        length = 152 if tex >= 0 else 84
        w.data += bytes(length)
        struct.pack_into('>I', w.data, r, 257)
        struct.pack_into('>i', w.data, r + 4, tex)
        w.data[r + 8:r + 12] = bytes(rgba)
        w.data[r + 16:r + 20] = bytes(rgba)
        struct.pack_into('>I', w.data, r + 36, control)
        struct.pack_into('>I', w.data, r + 76, 1 if tex >= 0 else 0)
        if tex >= 0:
            struct.pack_into('>I', w.data, r + 84, 1)
            struct.pack_into('>i', w.data, r + 88, tex)
    w.end()
    w.begin(65535)
    w.end()
    return bytes(w.data)


def entries(shapes):
    return [dict(material=i, texture=t, replace_texture=t, rgba=list(c), control=k,
                 uv_source='TEX0' if t >= 0 else None, tev_scale=0,
                 texgen_retargeted=False)
            for i, (t, c, k) in enumerate(shapes)]


class RewriteTests(unittest.TestCase):
    def test_texture_retarget_and_lighting_fields_only(self):
        raw = tex_model([(0, [255] * 4, 0), (1, [255] * 4, 0)])
        materials = entries([(0, [255] * 4, 0x93), (2, [255] * 4, 0x93)])
        materials[0]['texture'] = 0
        materials[1]['replace_texture'] = 1
        materials[1]['texture'] = 2
        # texture table needs index 2
        raw = tex_model([(0, [255] * 4, 0), (1, [255] * 4, 0)])  # 2 textures only
        with self.assertRaises(ValueError):
            bm.rewrite(raw, materials)  # retarget beyond table refused
        materials[1]['texture'] = 1  # no-op target; adjust below instead
        after = bm.rewrite(raw, materials)
        a, b = chunks(raw), chunks(after)
        for tag in a:
            if tag != 48:
                self.assertEqual(a[tag], b[tag])
        self.assertEqual(len(a[48]), len(b[48]))
        start = 32 + 124 * 2
        self.assertEqual(u32(b[48], start + 36), 0x93)
        self.assertEqual(struct.unpack_from('>i', b[48], start + 4)[0], 0)
        # second record: control updated, texture untouched
        r2 = start + 152
        self.assertEqual(u32(b[48], r2 + 36), 0x93)
        self.assertEqual(struct.unpack_from('>i', b[48], r2 + 4)[0], 1)
        self.assertEqual(struct.unpack_from('>i', b[48], r2 + 88)[0], 1)

    def test_textureless_baby_style_record(self):
        raw = tex_model([(-1, [255, 247, 198, 255], 0x1800)])
        materials = entries([(-1, [255, 247, 198, 255], bm.LIT | bm.VERTEX_COLOR_FLAG)])
        after = bm.rewrite(raw, materials)
        b = chunks(after)[48]
        self.assertEqual(u32(b, 32 + 124 + 36), bm.LIT | bm.VERTEX_COLOR_FLAG)
        self.assertEqual(struct.unpack_from('>i', b, 32 + 124 + 4)[0], -1)
        self.assertEqual(b[32 + 124 + 8:32 + 124 + 12], bytes([255, 247, 198, 255]))

    def test_rgba_restored(self):
        raw = tex_model([(0, [255] * 4, 0)])
        materials = entries([(0, [204, 204, 204, 255], 0)])
        after = bm.rewrite(raw, materials)
        b = chunks(after)[48]
        self.assertEqual(b[32 + 124 + 8:32 + 124 + 12], bytes([204, 204, 204, 255]))
        self.assertEqual(b[32 + 124 + 16:32 + 124 + 20], bytes([204, 204, 204, 255]))

    def test_refusals(self):
        raw = tex_model([(0, [255] * 4, 0), (1, [255] * 4, 0)])
        good = entries([(0, [255] * 4, 0x93), (1, [255] * 4, 0x93)])
        with self.assertRaises(ValueError):
            bm.rewrite(raw, good[:1])  # count mismatch
        bad = entries([(0, [255] * 4, 0xffff), (1, [255] * 4, 0x93)])
        with self.assertRaises(ValueError):
            bm.rewrite(raw, bad)  # control outside bounded set
        bad = entries([(0, [255] * 4, 0x93), (1, [300, 0, 0, 255], 0x93)])
        with self.assertRaises(ValueError):
            bm.rewrite(raw, bad)  # invalid rgba
        bad = entries([(0, [255] * 4, 0x93), (1, [255] * 4, 0x93)])
        bad[1]['replace_texture'] = 0
        with self.assertRaises(ValueError):
            bm.rewrite(raw, bad)  # tampered/double application
        bad = entries([(0, [255] * 4, 0x93), (1, [255] * 4, 0x93)])
        bad[0]['texture'] = -1
        with self.assertRaises(ValueError):
            bm.rewrite(raw, bad)  # cannot drop texture from textured record
        with self.assertRaises(ValueError):
            bm.rewrite(b'not a mod', good)

    def test_unknown_source_model_rejected(self):
        with self.assertRaises(ValueError):
            bm.profile(b'not a source model', 'Queen', False)
        with self.assertRaises(ValueError):
            bm.profile(b'not a source model', 'Frog', False)


BANK_TEXT = (HEADER + '\n'
             'Queen 1\n'
             'wait1 2 30 0 29\n'
             'Baby 1\n'
             'move 2 12 0 11\n'
             'KingChappy 1\n'
             'move1 2 40 0 39\n')


def bank_fixture(root, tamper=False, reference='x'):
    bank = parse_bank(BANK_TEXT)
    for species, clips in bank.items():
        (root / species).mkdir(parents=True, exist_ok=True)
        for name, info in clips.items():
            for index in range(info['poses']):
                raw = tex_model([(0, [255] * 4, 0)])
                if tamper and species == 'Baby' and index == 1:
                    raw = tex_model([(0, [255] * 4, 0x1800)])
                (root / species / f'bulblax_{species}_{name}_{index:02}.mod').write_bytes(raw)
    report = {'schema': 1, 'bank': HEADER, 'reference_sha256': reference,
              'motions': {}, 'unsupported': {}, 'blocked': {},
              'file_sha256': {}, 'normal_policy': {}}
    for species, clips in bank.items():
        for name, info in clips.items():
            for index in range(info['poses']):
                p = root / species / f'bulblax_{species}_{name}_{index:02}.mod'
                report['file_sha256'][p.name] = sha(p.read_bytes())
    (root / 'bulblax-bank.json').write_text(json.dumps(report))
    (root / 'p2-bulblax-bank.txt').write_text(BANK_TEXT)
    return root


def import_fixture(root):
    report = {'schema': 1, 'policy': 'P2_BULBLAX_IMPORT_1', 'species': {}}
    for species in CLIPS:
        folder = root / species
        folder.mkdir(parents=True)
        model = f'synthetic:{species}'.encode()
        (folder / 'enemy.bmd').write_bytes(model)
        report['species'][species] = {'model_sha256': sha(model)}
    (root / 'p2-bulblax.txt').write_text(TEXT)
    (root / 'bulblax.json').write_text(json.dumps(report))
    return root


class AuditTests(unittest.TestCase):
    def test_mapping_table_and_consistency(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bank_fixture(root)
            result = bm.audit_bank(root)
            self.assertEqual(result['poses'], 6)
            self.assertEqual(result['mapping_table']['Queen']['wait1'],
                             [{'pose': 0, 'source_frame': 0}, {'pose': 1, 'source_frame': 29}])
            self.assertEqual(result['mapping_table']['Baby']['move'][1]['source_frame'], 11)
            self.assertEqual(result['mapping_table']['KingChappy']['move1'][1]['source_frame'], 39)
            for species in ('Queen', 'Baby', 'KingChappy'):
                self.assertEqual(result['species'][species]['deviating_poses'], [])
                self.assertEqual(result['species'][species]['pose_count'], 2)
            self.assertEqual(len(result['pose_materials']['Queen'][0]['materials']), 1)

    def test_material_deviation_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bank_fixture(root, tamper=True)
            result = bm.audit_bank(root)
            deviants = result['species']['Baby']['deviating_poses']
            self.assertEqual(len(deviants), 1)
            self.assertIn('bulblax_Baby_move_01.mod', deviants[0]['file'])
            self.assertEqual(result['species']['Queen']['deviating_poses'], [])

    def test_resource_deviation_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bank_fixture(root)
            # Change a texture byte in one Queen pose -> resource chunks differ.
            path = root / 'Queen' / 'bulblax_Queen_wait1_01.mod'
            raw = bytearray(path.read_bytes())
            raw[100] ^= 1
            path.write_bytes(bytes(raw))
            result = bm.audit_bank(root)
            self.assertEqual(len(result['species']['Queen']['deviating_poses']), 1)


class PrepareTests(unittest.TestCase):
    def fake_profile(self, model, species, has_vertex_colors):
        return entries([(0, [204, 204, 204, 255], 0x93)])

    def run_prepare(self, root, imported, bank, output):
        with patch.object(bm, 'profile', side_effect=self.fake_profile):
            return bm.prepare(imported, bank, output)

    def test_prepare_writes_new_files_and_preserves_bank(self):
        with tempfile.TemporaryDirectory() as d:
            imported = import_fixture(Path(d) / 'imported')
            bank = bank_fixture(Path(d) / 'bank',
                                reference=sha((Path(imported) / 'bulblax.json').read_bytes()))
            before = {p.name: sha(p.read_bytes()) for p in Path(bank).rglob('*.mod')}
            metadata = self.run_prepare(Path(d), imported, bank, Path(d) / 'profiled')
            self.assertEqual(metadata['policy'], bm.POLICY)
            # Original bank untouched.
            after = {p.name: sha(p.read_bytes()) for p in Path(bank).rglob('*.mod')}
            self.assertEqual(before, after)
            # Profiled poses carry new hashes and provenance.
            report = json.loads((Path(d) / 'profiled' / 'bulblax-bank.json').read_text())
            self.assertEqual(report['material_profile']['source_bank_sha256'],
                             sha((Path(bank) / 'bulblax-bank.json').read_bytes()))
            for name, digest in report['file_sha256'].items():
                self.assertNotEqual(digest, before[name])
            for species in CLIPS:
                self.assertIn(species, report['material_profile']['unsupported'])
            # Emitted material actually updated.
            raw = (Path(d) / 'profiled' / 'Queen' / 'bulblax_Queen_wait1_00.mod').read_bytes()
            b = chunks(raw)[48]
            self.assertEqual(u32(b, 32 + 124 + 36), 0x93)
            self.assertEqual(b[32 + 124 + 8:32 + 124 + 12], bytes([204, 204, 204, 255]))

    def test_double_run_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            imported = import_fixture(Path(d) / 'imported')
            bank = bank_fixture(Path(d) / 'bank',
                                reference=sha((Path(imported) / 'bulblax.json').read_bytes()))
            self.run_prepare(Path(d), imported, bank, Path(d) / 'p1')
            self.run_prepare(Path(d), imported, bank, Path(d) / 'p2')
            def tree(root):
                return {str(p.relative_to(root)): sha(p.read_bytes())
                        for p in sorted(Path(root).rglob('*')) if p.is_file()}
            self.assertEqual(tree(Path(d) / 'p1'), tree(Path(d) / 'p2'))

    def test_refusals_before_any_output(self):
        with tempfile.TemporaryDirectory() as d:
            imported = import_fixture(Path(d) / 'imported')
            bank = bank_fixture(Path(d) / 'bank',
                                reference=sha((Path(imported) / 'bulblax.json').read_bytes()))
            (Path(bank) / 'bulblax-bank.json').write_text('{"schema": 2}')
            with self.assertRaises(ValueError):
                self.run_prepare(Path(d), imported, bank, Path(d) / 'out')
            self.assertFalse((Path(d) / 'out').exists())
        with tempfile.TemporaryDirectory() as d:
            imported = import_fixture(Path(d) / 'imported')
            bank = bank_fixture(Path(d) / 'bank',
                                reference=sha((Path(imported) / 'bulblax.json').read_bytes()))
            (Path(imported) / 'Baby' / 'enemy.bmd').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                self.run_prepare(Path(d), imported, bank, Path(d) / 'out')
            self.assertFalse((Path(d) / 'out').exists())
        with tempfile.TemporaryDirectory() as d:
            imported = import_fixture(Path(d) / 'imported')
            bank = bank_fixture(Path(d) / 'bank',
                                reference=sha((Path(imported) / 'bulblax.json').read_bytes()))
            out = Path(d) / 'out'
            out.mkdir()
            with self.assertRaises(ValueError):
                self.run_prepare(Path(d), imported, bank, out)

    def test_tampered_bank_pose_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            imported = import_fixture(Path(d) / 'imported')
            bank = bank_fixture(Path(d) / 'bank',
                                reference=sha((Path(imported) / 'bulblax.json').read_bytes()))
            (Path(bank) / 'Queen' / 'bulblax_Queen_wait1_01.mod').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                self.run_prepare(Path(d), imported, bank, Path(d) / 'out')
            self.assertFalse((Path(d) / 'out').exists())


if __name__ == '__main__':
    unittest.main()
