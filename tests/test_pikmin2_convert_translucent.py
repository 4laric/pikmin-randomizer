"""Alpha-blended P2 materials use P1's translucent path (#960).

Synthetic model: material 0 is category 4 (alpha blend) with the Jellyfloat
alpha combiner (A0 + RASA*TEXA) and a non-zero A0 register. The retail check
runs only when the local Kurage source extraction is present.
"""
import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_convert import (DEFAULT_ALPHA_STAGE, SHAPE_ALLOW_CACHING, blocks, decode,
                                          u32, write_model)
from tests.test_pikmin2_convert_normals import normal_model

# Constant source alpha from register A0. (The Jellyfloat A0 + RASA*TEXA needs a texture;
# the synthetic model has none, so TEXA inputs are covered by the fallback test.)
KURAGE_ALPHA = [7, 7, 7, 1, 0, 0, 0, 1, 0]


def blended_model(alpha=KURAGE_ALPHA, category=4, mode=1, depth_write=1, a0=100):
    """Extend the synthetic model's MAT3 with pixel-state and TEV tables."""
    model = normal_model()
    b = blocks(model)
    m = bytearray(b['MAT3'])
    r = u32(m, 12)
    while len(m) % 4:
        m += b'\0'
    tables = {}

    def add(offset, data):
        tables[offset] = len(m)
        m.extend(data)
        while len(m) % 4:
            m.append(0)
    add(112, bytes([mode, 4, 5, 3]))                       # blend: SRCALPHA / INVSRCALPHA
    add(116, bytes([1, 3, depth_write, 255]))              # z test, LEQUAL, write
    add(108, bytes([7, 0, 1, 7, 0, 255, 255, 255]))        # alpha compare: always
    add(88, bytes([1, 0, 0, 0]))                            # one TEV stage
    add(92, bytes([255, 15, 8, 10, 15, 0, 0, 0, 1, 0]) + bytes(alpha) + bytes([1, 0, 255]))
    add(76, bytes([0, 0, 4, 255]))                          # order: texcoord 0, texmap 0, COLOR0A0
    add(80, struct.pack('>4h', 195, 220, 90, a0) + b'\0' * 16)
    for offset, at in tables.items():
        struct.pack_into('>I', m, offset, at)
    m[r] = category
    m[r + 4] = 0
    m[r + 6] = 0
    struct.pack_into('>H', m, r + 0x148, 0)
    struct.pack_into('>H', m, r + 0x146, 0)
    for k in range(3):
        struct.pack_into('>H', m, r + 220 + 2 * k, 0)
    struct.pack_into('>H', m, r + 0xe4, 0)
    struct.pack_into('>H', m, r + 0xbc, 0)
    struct.pack_into('>I', m, 4, len(m))
    b['MAT3'] = bytes(m)
    result = bytearray(model[:32] + b''.join(b.values()))
    struct.pack_into('>I', result, 8, len(result))
    return bytes(result)


def convert(model):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'pose.mod'
        report = write_model(decode(model, True, bake_rigid=True), out, 'synthetic.bmd')
        return out.read_bytes(), report


def mod_chunk(mod, tag):
    at = 0
    while at + 8 <= len(mod):
        kind, size = struct.unpack_from('>II', mod, at)
        if kind == tag:
            return at, size
        at += 8 + size
    raise AssertionError(tag)


class TranslucentMaterialTests(unittest.TestCase):
    def test_blended_material_keeps_source_alpha_stage_and_register(self):
        mod, report = convert(blended_model())
        self.assertEqual(report['alpha_stages'], [KURAGE_ALPHA])
        start, _ = mod_chunk(mod, 48)
        pos = (start + 16 + 31) // 32 * 32
        self.assertEqual(list(mod[pos + 112:pos + 121]), KURAGE_ALPHA)
        self.assertEqual(struct.unpack_from('>4h', mod, pos), (195, 220, 90, 100))

    def test_blended_shape_defers_to_sorted_flush_without_depth_write(self):
        mod, report = convert(blended_model())
        start, _ = mod_chunk(mod, 0)
        self.assertEqual(struct.unpack_from('>I', mod, start + 0x24)[0], SHAPE_ALLOW_CACHING)
        pos = (mod_chunk(mod, 48)[0] + 16 + 31) // 32 * 32
        self.assertEqual(report['translucent_path']['blended_shapes'], [0])
        self.assertEqual(report['translucent_path']['shape_flags'], SHAPE_ALLOW_CACHING)

    def test_default_combiner_keeps_exporter_stage(self):
        mod, report = convert(blended_model(alpha=DEFAULT_ALPHA_STAGE))
        self.assertNotIn('alpha_stages', report)
        self.assertIn('translucent_path', report)

    def test_opaque_material_is_unchanged(self):
        mod, report = convert(blended_model(category=1, mode=0, depth_write=1))
        self.assertNotIn('translucent_path', report)
        self.assertNotIn('alpha_stages', report)
        start, _ = mod_chunk(mod, 0)
        self.assertEqual(mod[start + 0x24:start + 0x28], b'\0\0\0\0')

    def test_texture_alpha_input_without_a_texture_falls_back(self):
        _, report = convert(blended_model(alpha=[7, 5, 4, 1, 0, 0, 0, 1, 0]))
        self.assertNotIn('alpha_stages', report)

    def test_unsupported_alpha_input_falls_back(self):
        _, report = convert(blended_model(alpha=[0, 5, 4, 7, 0, 0, 0, 1, 0]))  # APREV input
        self.assertNotIn('alpha_stages', report)


if __name__ == '__main__':
    unittest.main()
