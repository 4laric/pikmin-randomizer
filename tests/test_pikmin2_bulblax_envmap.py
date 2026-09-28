import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_convert import Writer, write_model
from experimental.pikmin2_frog_visual_audit import chunks
from experimental import pikmin2_bulblax_envmap as em

# SHA-256 of the unmodified single-stage converter output for
# ``converter_sample()`` below. Frozen to prove the additive envmap interface
# does not change any default converter output.
FROZEN_DEFAULT_SHA256 = '4abad52016f21b3dc3e44bf785fd78a61fe5344441a760122e183d160f850725'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tex_block(count=3):
    """Minimal valid TEX1 block: `count` 8x8 I4 textures."""
    data = bytearray(16 + 64 * count)
    struct.pack_into('>H', data, 8, count)
    struct.pack_into('>I', data, 12, 16)
    for i in range(count):
        r = 16 + 32 * i
        data[r] = 0
        struct.pack_into('>H', data, r + 2, 8)
        struct.pack_into('>H', data, r + 4, 8)
        data[r + 8] = 0
        struct.pack_into('>I', data, r + 28, 32 * count)
        data[r + 32 * count:r + 32 * count + 32] = bytes([0x11]) * 32
    return bytes(data)


def decoded():
    b = {'_render_states': [(257, 1, 0, 0, 0), (257, 1, 0, 0, 0)],
         '_draw_order': [0, 1], 'TEX1': tex_block()}
    a = {9: [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
         10: [(0.0, 0.0, 1.0)] * 3,
         13: [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]}
    tri = [[{9: 0, 10: 0, 13: 0}, {9: 1, 10: 1, 13: 1}, {9: 2, 10: 2, 13: 2}]]
    return b, a, [tri, tri], [0, 2]


def converter_sample():
    """Real `pikmin2_convert.write_model` output: shape 1 base texture 2."""
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / 'sample.mod'
        write_model(decoded(), out, 'sample.bmd')
        return out.read_bytes()


def tex_model(shapes):
    """Synthetic generated material chunk in the audited writer layout.

    `shapes` entries are (texture, rgba, control); texture -1 builds an 84-byte
    textureless record. Mirrors pikmin2_convert.py:263-280.
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


class DefaultOutputTests(unittest.TestCase):
    def test_converter_default_is_byte_identical(self):
        data = converter_sample()
        self.assertEqual(sha(data), FROZEN_DEFAULT_SHA256)
        self.assertEqual(len(data), 1696)

    def test_default_sample_is_single_stage(self):
        data = converter_sample()
        self.assertEqual([info['stage_count'] for info in em.tev_infos(data)], [1, 1])
        records = em.material_records(data)
        self.assertEqual([r['texgen_count'] for r in records], [1, 1])
        self.assertEqual([len(r['texture_data']) for r in records], [1, 1])
        self.assertEqual(records[1]['texture'], 2)

    def test_apply_none_is_a_noop(self):
        data = converter_sample()
        self.assertEqual(em.apply(data), data)
        self.assertEqual(em.apply(data, None), data)


class OptInStageTests(unittest.TestCase):
    def test_adds_exactly_one_expected_stage(self):
        data = converter_sample()
        result = em.apply_queen_body(data)
        before, after = chunks(data), chunks(result)
        # Only the material chunk may change.
        for tag in before:
            if tag != 48:
                self.assertEqual(before[tag], after[tag], f'chunk {tag} changed')
        self.assertIn(48, after)

        tev = em.tev_infos(result)
        self.assertEqual(tev[0]['stage_count'], 1)
        self.assertEqual(tev[1]['stage_count'], 2)
        stage = tev[1]['stages'][1]
        self.assertEqual(stage['tex_coord_id'], 1)
        self.assertEqual(stage['tex_map_id'], 1)
        self.assertEqual(stage['channel_id'], 5)
        self.assertEqual(stage['color_combiner'], [15, 10, 8, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        self.assertEqual(stage['alpha_combiner'], [4, 7, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        records = em.material_records(result)
        self.assertEqual(records[0], em.material_records(data)[0])
        self.assertEqual(records[1]['texgen_count'], 2)
        self.assertEqual(records[1]['texgens'], [[0, 1, 4, 10], [1, 1, 1, 30]])
        self.assertEqual(len(records[1]['texture_data']), 2)
        envmap = records[1]['texture_data'][1]
        self.assertEqual(envmap['source_attr'], 1)
        self.assertEqual(envmap['marker'], em.ENVMAP_MARKER)
        self.assertEqual(envmap['tev_flag'], em.TEV_FLAG)
        self.assertEqual(envmap['animation_factor'], 0)
        self.assertEqual(envmap['total_frame'], 0)
        self.assertEqual((envmap['scale_x'], envmap['scale_y']), (1.0, 1.0))
        self.assertEqual(envmap['rotation'], 0.0)

    def test_chunk_growth_is_bounded(self):
        data = converter_sample()
        result = em.apply_queen_body(data)
        # +32 stage +4 texgen +64 texture data, rounded up to the chunk pad.
        self.assertEqual(len(chunks(result)[48]) - len(chunks(data)[48]), 96)

    def test_deterministic(self):
        data = converter_sample()
        self.assertEqual(em.apply_queen_body(data), em.apply_queen_body(data))

    def test_synthetic_sample(self):
        raw = tex_model([(0, [255] * 4, 0), (2, [255] * 4, 0)])
        result = em.apply_queen_body(raw)
        self.assertEqual([i['stage_count'] for i in em.tev_infos(result)], [1, 2])
        self.assertEqual(em.material_records(result)[1]['texgens'],
                         [[0, 0, 0, 0], [1, 1, 1, 30]])


class QueenSpecTests(unittest.TestCase):
    def test_spec_matches_documented_source_stage(self):
        self.assertEqual(em.QUEEN_BODY['shape'], 1)
        self.assertEqual(em.QUEEN_BODY['texture'], 1)
        self.assertEqual(em.QUEEN_BODY['channel_id'], 5)
        self.assertEqual(em.QUEEN_BODY['color_combiner'][:4], (15, 10, 8, 0))
        self.assertEqual(em.QUEEN_BODY['alpha_combiner'][:4], (4, 7, 6, 0))
        self.assertEqual(em.QUEEN_BODY['texgen'], (1, 1, 30))
        self.assertEqual(em.QUEEN_BODY['marker'], 0xE6)
        self.assertEqual(list(em.QUEEN_BODY['srt']), [1.0, 1.0, 0.0, 0.0, 0.0, 0.0])

    def test_channel_and_marker_constants(self):
        self.assertEqual(em.ENVMAP_MARKER, 0xE6)
        self.assertEqual(em.TEV_FLAG, 2)
        self.assertEqual(em.POLICY, 'P2_BULBLAX_ENVMAP_1')


class RefusalTests(unittest.TestCase):
    def setUp(self):
        self.raw = converter_sample()

    def spec(self, **overrides):
        spec = dict(em.QUEEN_BODY)
        spec.update(overrides)
        return spec

    def test_shape_out_of_range(self):
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, self.spec(shape=9))

    def test_texture_out_of_range(self):
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, self.spec(texture=99))

    def test_double_application_refused(self):
        once = em.apply_queen_body(self.raw)
        with self.assertRaises(ValueError):
            em.add_stage(once, em.QUEEN_BODY)

    def test_textureless_target_refused(self):
        raw = tex_model([(0, [255] * 4, 0), (-1, [255] * 4, 0)])
        with self.assertRaises(ValueError):
            em.add_stage(raw, self.spec(shape=1))

    def test_bad_combiner_length_refused(self):
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, self.spec(color_combiner=(1, 2, 3)))
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, self.spec(alpha_combiner=[0] * 13))

    def test_missing_fields_refused(self):
        spec = self.spec()
        del spec['texgen']
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, spec)

    def test_invalid_srt_refused(self):
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, self.spec(srt=(1.0, 1.0)))
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, self.spec(srt=(1.0, float('nan'), 0.0, 0.0, 0.0, 0.0)))

    def test_invalid_byte_refused(self):
        with self.assertRaises(ValueError):
            em.add_stage(self.raw, self.spec(channel_id=256))

    def test_not_a_mod_refused(self):
        with self.assertRaises(ValueError):
            em.add_stage(b'not a mod', em.QUEEN_BODY)


class PrepareTests(unittest.TestCase):
    def make_profiled_bank(self, root):
        (root / 'Queen').mkdir(parents=True)
        (root / 'Baby').mkdir(parents=True)
        (root / 'Queen' / 'bulblax_Queen_born_00.mod').write_bytes(converter_sample())
        (root / 'Queen' / 'bulblax_Queen_born_01.mod').write_bytes(converter_sample())
        (root / 'Baby' / 'bulblax_Baby_move_00.mod').write_bytes(b'baby-pose')
        report = {'schema': 1, 'bank': 'P2_BULBLAX_BANK_1',
                  'file_sha256': {}, 'material_profile': {'policy': em.MATERIAL_POLICY, 'applied': True}}
        (root / 'bulblax-bank.json').write_text(json.dumps(report))
        (root / 'p2-bulblax-bank.txt').write_text('P2_BULBLAX_BANK_1\n')
        return root

    def test_prepare_writes_new_bank_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as d:
            bank = self.make_profiled_bank(Path(d) / 'bank')
            before = {p.name: sha(p.read_bytes()) for p in bank.rglob('*.mod')}
            info = em.prepare(bank, Path(d) / 'out')
            self.assertEqual(info['policy'], em.POLICY)
            self.assertEqual(info['queen_poses'], 2)
            after = {p.name: sha(p.read_bytes()) for p in bank.rglob('*.mod')}
            self.assertEqual(before, after)
            # Baby pose copied unchanged, Queen poses rewritten.
            self.assertEqual((Path(d) / 'out' / 'Baby' / 'bulblax_Baby_move_00.mod').read_bytes(),
                             b'baby-pose')
            queen = (Path(d) / 'out' / 'Queen' / 'bulblax_Queen_born_00.mod').read_bytes()
            self.assertEqual([i['stage_count'] for i in em.tev_infos(queen)], [1, 2])

    def test_prepare_requires_material_profile(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'bulblax-bank.json').write_text('{"schema": 1}')
            with self.assertRaises(ValueError):
                em.prepare(Path(d), Path(d) / 'out')


if __name__ == '__main__':
    unittest.main()
