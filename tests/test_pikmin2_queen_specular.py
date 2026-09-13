import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_convert import Writer, u16, u32
from experimental.pikmin2_frog_visual_audit import chunks
from experimental.pikmin2_queen_specular import BTK, POLICY, remap_uv, source_contract
from experimental.pikmin2_queen_specular_stage import stage


def fixture(colored=False):
    arrays = {13: [(0., 0.), (1., 1.)], 14: [(.25, .75), (.5, .125)]}
    shapes = [[[{13: 0, 14: 1}, {13: 1, 14: 0}, {13: 0, 14: 0}]] for _ in range(2)]
    writer = Writer()
    for tag in (16, 17):
        writer.begin(tag, 1); writer.pad(); writer.put('3f', 1., 2., 3.); writer.end()
    writer.begin(24, 2); writer.pad()
    for uv in arrays[13]: writer.put('2f', *uv)
    writer.end(); writer.begin(80, 2); writer.pad()
    for tris in shapes:
        dl = bytearray(struct.pack('>BH', 0x90, 3))
        for vertex in tris[0]:
            dl.extend(struct.pack('>BHH', 0, 0, 0))
            if colored: dl.extend(struct.pack('>H', 0))
            dl.extend(struct.pack('>H', vertex[13]))
        dl.extend(bytes(-len(dl) % 32))
        writer.put('4Ih4I', 0, 13 if colored else 9, 1, 1, 0, 1, 0, 1, len(dl))
        writer.pad(); writer.data.extend(dl)
    writer.end(); writer.begin(65535); writer.end()
    return bytes(writer.data), arrays, shapes


class UVTests(unittest.TestCase):
    def test_body_only_uv1_and_geometry_preserved(self):
        for colored in (False, True):
            with self.subTest(colored=colored):
                raw, arrays, shapes = fixture(colored)
                before = chunks(raw); after = chunks(remap_uv(raw, arrays, shapes))
                for tag in (16, 17, 65535): self.assertEqual(before[tag], after[tag])
                self.assertEqual(u32(after[24], 8), 4)
                self.assertEqual(after[24][32:48], before[24][32:48])
                self.assertEqual(after[24][48:64], b''.join(struct.pack('>2f', *v) for v in arrays[14]))
                # Two 96-byte records; index is the last u16 of each vertex.
                stride = 9 if colored else 7
                for shape, indices in enumerate(((0, 1, 0), (3, 2, 2))):
                    start = 96 + shape * 96 + 3
                    self.assertEqual([u16(after[80], start + i * stride + stride - 2) for i in range(3)], list(indices))

    def test_refuses_mismatched_uvs_and_double_apply(self):
        raw, arrays, shapes = fixture()
        changed = copy.deepcopy(arrays); changed[13][0] = (.5, .5)
        with self.assertRaisesRegex(ValueError, 'UV0 differs'): remap_uv(raw, changed, shapes)
        with self.assertRaisesRegex(ValueError, 'count mismatch'): remap_uv(remap_uv(raw, arrays, shapes), arrays, shapes)
        shapes[1][0][0][14] = 20
        with self.assertRaisesRegex(ValueError, 'UV1 index'): remap_uv(raw, arrays, shapes)

    def test_refuses_mesh_and_primitive_mismatch(self):
        raw, arrays, shapes = fixture()
        for offset, value in ((36, 0), (64, 0)):
            changed = chunks(raw); mesh = bytearray(changed[80]); mesh[offset] = value
            # flags is a big-endian u32; primitive begins at 96.
            if offset == 36: struct.pack_into('>I', mesh, 36, 0)
            else: mesh[96] = 0
            changed[80] = bytes(mesh)
            with self.assertRaises(ValueError): remap_uv(b''.join(changed.values()), arrays, shapes)

    def test_source_hash_preflight(self):
        with self.assertRaisesRegex(ValueError, 'audited'): source_contract(b'wrong model', b'wrong animation')


class StageTests(unittest.TestCase):
    def test_existing_output_refusal_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'run'; output.mkdir(); (output / 'save').write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'fresh'): stage(Path(temp)/'absent', Path(temp)/'absent', output, [0, 0, 0])
            self.assertEqual((output / 'save').read_bytes(), b'keep')

    def test_tampered_animation_refused_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            bank = Path(temp); output = bank / 'new'
            (bank / 'bulblax-bank.json').write_text(json.dumps({'queen_specular': dict(
                policy=POLICY, source_btk=BTK, animation_sha256=hashlib.sha256(b'original').hexdigest())}))
            (bank / 'p2-queen-specular.txt').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'Animation hash'): stage(bank, bank, output, [0, 0, 0])
            self.assertFalse(output.exists())

    def test_tampered_model_refused_before_overlay(self):
        with tempfile.TemporaryDirectory() as temp:
            bank = Path(temp); output = bank / 'new'; model = bank / 'test.mod'; model.write_bytes(b'changed')
            (bank / 'bulblax-bank.json').write_text(json.dumps({'queen_specular': dict(
                policy=POLICY, source_btk=BTK, animation_sha256=hashlib.sha256(b'animation').hexdigest()),
                'file_sha256': {model.name: hashlib.sha256(b'original').hexdigest()}}))
            (bank / 'p2-queen-specular.txt').write_bytes(b'animation'); (bank / 'p2-bulblax-bank.txt').write_text('bank')
            with patch('experimental.pikmin2_queen_specular_stage.parse_bank', return_value={}), \
                 patch('experimental.pikmin2_queen_specular_stage.validate_files', return_value=([model], 7)), \
                 self.assertRaisesRegex(ValueError, 'Model hash'):
                stage(bank, bank, output, [0, 0, 0])
            self.assertFalse(output.exists())
