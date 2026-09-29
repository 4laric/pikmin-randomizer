"""P1-native lighting and source material colour in the converter (#895).

Synthetic models extend the #186 normal-test builder with real MAT3 colour and
channel-control tables. Retail checks run only when the local P1 assets and
P2 source extraction are present.
"""
import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_change_texture import CHANGE_TEXTURES, replace_texture
from experimental.pikmin2_convert import (LEGACY_VERTEX_CONTROL, MAT_SRC_ALPHA0_VERTEX,
                                          MAT_SRC_COLOR0_VERTEX, P1_LIT_CONTROL, blocks,
                                          decode, lighting_control, source_lighting, u16,
                                          u32, write_model)
from experimental.pikmin2_material_audit import (audit_content, check_pose, mat3_channels, mod_materials,
                                                 mod_textures, shape_materials, source_table)
from tests.test_pikmin2_convert_normals import normal_model

P1_TEKIS = Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets/dataDir/tekis')
P2_SOURCE = Path(__file__).resolve().parents[1] / 'output/claude-orch/p2-884/content-35'
if not P2_SOURCE.is_dir():
    P2_SOURCE = Path('C:/Users/alari/pikmin-randomizer/output/claude-orch/p2-884/content-35')


def with_channels(model, lit=True, color_vertex=False, alpha_vertex=False,
                  rgba=(204, 180, 150, 255), channel_count=1):
    """Append MAT3 colour/channel tables to material 0 of a synthetic model."""
    b = blocks(model)
    m = bytearray(b['MAT3'])
    r = u32(m, 12)
    base = len(m)
    m += bytes([channel_count, 0, 0, 0])                       # +0 channel counts
    m += bytes(rgba)                                             # +4 material colours
    m += bytes([1 if lit else 0, 1 if color_vertex else 0, 1, 2, 1, 0, 255, 255])  # +8 COLOR0
    m += bytes([0, 1 if alpha_vertex else 0, 0, 2, 2, 0, 255, 255])                # +16 ALPHA0
    struct.pack_into('>I', m, 36, base)
    struct.pack_into('>I', m, 32, base + 4)
    struct.pack_into('>I', m, 40, base + 8)
    m[r + 2] = 0
    struct.pack_into('>HH', m, r + 8, 0, 0xFFFF)
    struct.pack_into('>4H', m, r + 12, 0, 1, 0xFFFF, 0xFFFF)
    struct.pack_into('>I', m, 4, len(m))
    b['MAT3'] = bytes(m)
    result = bytearray(model[:32] + b''.join(b.values()))
    struct.pack_into('>I', result, 8, len(result))
    return bytes(result)


def converted(model, **kwargs):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'pose.mod'
        report = write_model(decode(model, True, bake_rigid=True), out, 'synthetic.bmd', **kwargs)
        return out.read_bytes(), report


class SourceLightingTests(unittest.TestCase):
    def test_reads_channel_control_and_material_colour(self):
        model = with_channels(normal_model(), lit=True, color_vertex=True, alpha_vertex=True)
        m = blocks(model)['MAT3']
        info = source_lighting(m, u32(m, 12))
        self.assertEqual(info, dict(lit=True, color_vertex=True, alpha_vertex=True, rgba=(204, 180, 150, 255)))

    def test_zero_channel_count_and_disabled_channel_are_unlit(self):
        for kwargs in (dict(lit=False), dict(lit=True, channel_count=0)):
            model = with_channels(normal_model(), **kwargs)
            m = blocks(model)['MAT3']
            self.assertFalse(source_lighting(m, u32(m, 12))['lit'])

    def test_tableless_mat3_keeps_legacy_material(self):
        m = blocks(normal_model())['MAT3']
        self.assertIsNone(source_lighting(m, u32(m, 12)))
        raw, report = converted(normal_model())
        self.assertEqual(mod_materials(raw)[0]['control'], 0)
        self.assertEqual(mod_materials(raw)[0]['rgba'], [255] * 4)
        self.assertNotIn('lighting_controls', report)

    def test_out_of_range_channel_reference_rejected(self):
        model = with_channels(normal_model())
        m = bytearray(blocks(model)['MAT3'])
        struct.pack_into('>H', m, u32(m, 12) + 12, 999)
        with self.assertRaisesRegex(ValueError, 'channel reference'):
            source_lighting(bytes(m), u32(m, 12))

    def test_control_word_matrix(self):
        src = dict(lit=True, color_vertex=True, alpha_vertex=True, rgba=(255,) * 4)
        self.assertEqual(lighting_control(src, True), P1_LIT_CONTROL | LEGACY_VERTEX_CONTROL)
        self.assertEqual(lighting_control(src, False), P1_LIT_CONTROL)
        self.assertEqual(lighting_control(dict(src, lit=False), True), 0xd0 | LEGACY_VERTEX_CONTROL)
        self.assertEqual(lighting_control(dict(src, alpha_vertex=False), True),
                         P1_LIT_CONTROL | MAT_SRC_COLOR0_VERTEX)
        self.assertEqual(lighting_control(dict(src, color_vertex=False), True),
                         P1_LIT_CONTROL | MAT_SRC_ALPHA0_VERTEX)
        self.assertEqual(P1_LIT_CONTROL, 0xd1)


class WriteModelTests(unittest.TestCase):
    def test_lit_source_emits_p1_word_and_source_colour(self):
        raw, report = converted(with_channels(normal_model(), lit=True))
        material = mod_materials(raw)[0]
        self.assertEqual(material['control'], 0xd1)
        self.assertEqual(material['rgba'], [204, 180, 150, 255])
        self.assertEqual([s['scale'] for s in material['stages']], [0])
        self.assertEqual(report['lighting_controls'], [0xd1])
        self.assertEqual(report['material_colors'], [[204, 180, 150, 255]])
        self.assertIn('0xd1', report['material_policy'])

    def test_unlit_source_stays_unlit(self):
        raw, _ = converted(with_channels(normal_model(), lit=False, rgba=(204, 204, 204, 255)))
        material = mod_materials(raw)[0]
        # Retail kabekuiA unlit word; EnableColor0 (bit 0) stays clear.
        self.assertEqual(material['control'], 0xd0)
        self.assertEqual(material['control'] & 1, 0)
        self.assertEqual(material['rgba'], [204, 204, 204, 255])

    def test_vertex_bits_need_display_list_colour(self):
        # The synthetic shape has no colour attribute, so vertex-source bits
        # are not set even though the source channel asks for them.
        raw, _ = converted(with_channels(normal_model(), color_vertex=True, alpha_vertex=True))
        self.assertEqual(mod_materials(raw)[0]['control'], 0xd1)

    def test_explicit_material_colors_win(self):
        raw, report = converted(with_channels(normal_model()), material_colors=[(10, 20, 30, 255)])
        self.assertEqual(mod_materials(raw)[0]['rgba'], [10, 20, 30, 255])
        self.assertEqual(report['material_colors'], [[10, 20, 30, 255]])

    def test_audit_accepts_conversion_and_flags_drift(self):
        model = with_channels(normal_model())
        raw, _ = converted(model)
        source, mapping = source_table(model), shape_materials(model)
        self.assertEqual(check_pose(raw, source, mapping), [])
        legacy, _ = converted(normal_model())
        problems = check_pose(legacy, source, mapping)
        self.assertTrue(any('control' in p for p in problems))
        self.assertTrue(any('rgba' in p for p in problems))

    def test_audit_content_tree(self):
        model = with_channels(normal_model())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'Species'
            root.mkdir()
            (root / 'enemy.bmd').write_bytes(model)
            write_model(decode(model, True, bake_rigid=True), root / 'p_00.mod', 'enemy.bmd')
            report = audit_content(tmp)
        self.assertEqual((report['poses'], report['mismatched_poses']), (1, 0))
        self.assertEqual(report['controls'], {'0xd1': 1})

    def test_audit_reads_mat3_independently_of_converter(self):
        # The audit's named-offset MAT3 reader must agree with the converter's
        # source_lighting on every channel combination (#895 review: the audit
        # no longer imports source_lighting).
        for kwargs in (dict(lit=True), dict(lit=False), dict(lit=True, channel_count=0),
                       dict(lit=True, color_vertex=True), dict(lit=True, alpha_vertex=True),
                       dict(lit=False, color_vertex=True, alpha_vertex=True, rgba=(200, 80, 0, 255))):
            m = blocks(with_channels(normal_model(), **kwargs))['MAT3']
            self.assertEqual(mat3_channels(m, 0), source_lighting(m, u32(m, 12)), kwargs)

    def test_audit_expects_retail_unlit_word(self):
        model = with_channels(normal_model(), lit=False)
        raw, _ = converted(model)
        self.assertEqual(check_pose(raw, source_table(model), shape_materials(model)), [])
        self.assertEqual(mod_materials(raw)[0]['control'], 0xd0)


def _bti(width, height, fill):
    header = bytearray(32)
    header[0] = 14  # CMPR
    struct.pack_into('>HH', header, 2, width, height)
    struct.pack_into('>I', header, 28, 32)
    return bytes(header) + bytes([fill]) * (width * height // 2)


class ChangeTextureTests(unittest.TestCase):
    def test_bombotakara_swap_matches_dweevil_mgr_texture(self):
        # BombOtakara is not tinted natively (pc_p2_batch2.h), so its retail
        # swap is baked; the tinted four stay on the placeholder.
        from experimental.pikmin2_change_texture import RUNTIME_TINTED
        from experimental.pikmin2_dweevil_assets import CHANGE_TEXTURES as MGR_TEXTURES
        self.assertEqual(CHANGE_TEXTURES['BombOtakara'],
                         [(0, MGR_TEXTURES['BombOtakara'].lstrip('/'))])
        self.assertNotIn('BombOtakara', RUNTIME_TINTED)
        self.assertFalse(set(RUNTIME_TINTED) & set(CHANGE_TEXTURES))

    def model_with_textures(self, count):
        tex = bytearray(32 + 32 * count)
        tex[:4] = b'TEX1'
        struct.pack_into('>H', tex, 8, count)
        struct.pack_into('>I', tex, 12, 32)
        for i in range(count):
            at = 32 + 32 * i
            tex[at] = 3  # IA8 placeholder
            struct.pack_into('>HH', tex, at + 2, 8, 8)
            struct.pack_into('>I', tex, at + 28, 32 + 32 * count + 128 * i - at)
        tex += bytes(128 * count)
        struct.pack_into('>I', tex, 4, len(tex))
        data = bytearray(32)
        data[:8] = b'J3D2bmd3'
        struct.pack_into('>I', data, 12, 1)
        data += tex
        struct.pack_into('>I', data, 8, len(data))
        return bytes(data)

    def test_slot_swap_rewrites_header_and_data(self):
        model = self.model_with_textures(2)
        swapped = replace_texture(model, 1, _bti(16, 16, 0x5a))
        t = blocks(swapped)['TEX1']
        self.assertEqual(u16(t, 8), 2)
        first, second = 32, 64
        self.assertEqual((t[first], u16(t, first + 2)), (3, 8))
        self.assertEqual((t[second], u16(t, second + 2), u16(t, second + 4)), (14, 16, 16))
        start = second + u32(t, second + 28)
        self.assertEqual(t[start:start + 128], bytes([0x5a]) * 128)
        self.assertEqual(u32(swapped, 8), len(swapped))

    def test_missing_slot_and_bad_bti_rejected(self):
        model = self.model_with_textures(1)
        with self.assertRaisesRegex(ValueError, 'slot'):
            replace_texture(model, 1, _bti(8, 8, 0))
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            replace_texture(model, 0, _bti(8, 8, 0)[:40])

    def test_table_matches_decomp_managers(self):
        self.assertEqual([s for s, _ in CHANGE_TEXTURES['Chappy']], [0, 1])
        self.assertTrue(CHANGE_TEXTURES['Rkabuto'][0][1].endswith('babykabuto_red_s3tc.bti'))
        self.assertEqual(CHANGE_TEXTURES['Kabuto'], CHANGE_TEXTURES['Fkabuto'])


@unittest.skipUnless((P1_TEKIS / 'chappy/chappy.mod').is_file(), 'Requires local P1 assets')
class RetailP1Tests(unittest.TestCase):
    def test_retail_tekis_use_d1_d3(self):
        for name in ('chappy', 'tank', 'swallow', 'iwagon', 'beatle'):
            controls = {m['control'] for m in mod_materials((P1_TEKIS / name / f'{name}.mod').read_bytes())}
            self.assertTrue(controls <= {0xd1, 0xd3}, (name, controls))
        textures = mod_textures((P1_TEKIS / 'chappy/chappy.mod').read_bytes())
        self.assertTrue(all(t['mean_luma'] is not None for t in textures))


@unittest.skipUnless((P2_SOURCE / 'KingChappy/enemy.bmd').is_file(), 'Requires local P2 source extraction')
class RetailP2SourceTests(unittest.TestCase):
    def test_kingchappy_and_firechappy_source_policy(self):
        king = source_table((P2_SOURCE / 'KingChappy/enemy.bmd').read_bytes())
        self.assertTrue(king[0]['lit'])
        self.assertFalse(king[1]['lit'])
        self.assertEqual(king[1]['rgba'], [204, 204, 204, 255])
        fire = source_table((P2_SOURCE / 'FireChappy/enemy.bmd').read_bytes())
        self.assertEqual(fire[1]['rgba'], [200, 80, 0, 255])
        jigumo = source_table((P2_SOURCE / 'Jigumo/Jigumo/enemy.bmd').read_bytes())
        self.assertTrue(jigumo[0]['lit'] and jigumo[0]['color_vertex'])


if __name__ == '__main__':
    unittest.main()
