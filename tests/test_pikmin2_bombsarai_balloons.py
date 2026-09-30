"""Dirigibug balloons (#1027): verbatim two-stage TEV overrides and billboard staging.

The retail check runs only when a local BombSarai extraction is present
(``output/smooth-evidence/dirigi/content`` or ``output/p2-content-dense``).
"""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_bombsarai_assets import BALLOON_STAGES
from experimental.pikmin2_bombsarai_stage import BILLBOARD_HEADER, BombSaraiStageError, billboard_text
from experimental.pikmin2_convert import decode, u32, write_model
from tests.p2_convert_model_helpers import TRIANGLE, UVS, build_model

ROOT = Path(__file__).resolve().parents[1]


def material_chunk(data):
    at = 0
    while u32(data, at) != 48:
        at += 8 + u32(data, at + 4)
    return at


def override(regs):
    return {0: dict(regs=regs, konst=bytes(range(16)),
                    stages=[dict(order=s['order'], color=s['color'], alpha=s['alpha'], kcolor=2, kalpha=28)
                            for s in BALLOON_STAGES])}


class TevOverride(unittest.TestCase):
    def decoded(self):
        b, a, shapes, _ = decode(build_model(TRIANGLE, [(0., 0., 1.)] * 3, UVS), True, bake_rigid=True)
        return b, a, shapes, [0]  # pretend the shape samples texture 0

    def test_two_source_stages_written_verbatim(self):
        regs = [[40, 10, 10, 220], [255, 100, 100, 255], [128, 0, 0, 255]]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'x.mod'
            write_model(self.decoded(), out, 'synthetic.bmd', tev_overrides=override(regs))
            data = out.read_bytes()
        at = material_chunk(data)
        tev = (at + 16 + 31) // 32 * 32  # chunk header + counts, padded
        self.assertEqual([list(struct.unpack_from('>4h', data, tev + 24 * k)) for k in range(3)], regs)
        self.assertEqual(data[tev + 72:tev + 88], bytes(range(16)))
        self.assertEqual(u32(data, tev + 88), 2)
        first = tev + 92
        self.assertEqual(list(data[first:first + 6]), [0, 0, 0, 4, 2, 28])
        self.assertEqual(list(data[first + 8:first + 17]), BALLOON_STAGES[0]['color'])
        self.assertEqual(list(data[first + 20:first + 29]), BALLOON_STAGES[0]['alpha'])
        second = first + 32
        self.assertEqual(list(data[second + 8:second + 17]), BALLOON_STAGES[1]['color'])

    def test_untextured_override_is_refused(self):
        b, a, shapes, _ = self.decoded()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_model((b, a, shapes, [-1]), Path(tmp) / 'x.mod', 'synthetic.bmd',
                            tev_overrides=override([[0, 0, 0, 0]] * 3))

    def test_no_override_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Path(tmp) / 'a.mod', Path(tmp) / 'b.mod'
            write_model(self.decoded(), one, 'synthetic.bmd')
            write_model(self.decoded(), two, 'synthetic.bmd', tev_overrides={})
            self.assertEqual(one.read_bytes(), two.read_bytes())


class BillboardText(unittest.TestCase):
    def test_rows(self):
        text = billboard_text([[218, 22, 217, 22], [240, 22, 239, 22]]).decode('ascii')
        self.assertEqual(text, f'{BILLBOARD_HEADER} 2\n218 22 217 22\n240 22 239 22\n')

    def test_none_without_billboards(self):
        self.assertIsNone(billboard_text([]))

    def test_bad_rows(self):
        for row in ([1, 0, 1, 1], [1, 2, 3], [-1, 2, 3, 4], [1.0, 2, 3, 4]):
            with self.assertRaises(BombSaraiStageError):
                billboard_text([row])


class RetailBalloons(unittest.TestCase):
    def test_extracted_balloons_carry_source_colours(self):
        for base in (ROOT / 'output' / 'smooth-evidence' / 'dirigi' / 'content',
                     ROOT.parent / 'smooth-evidence' / 'dirigi' / 'content'):
            record = base / 'BombSarai' / 'BombSarai' / 'bombsarai_BombSarai_wait1_00.json'
            if record.is_file():
                break
        else:
            self.skipTest('no local #1027 BombSarai extraction')
        report = json.loads(record.read_text(encoding='utf-8'))
        self.assertEqual(report['balloon_tev_shapes'], [1, 2, 3, 4, 5])
        self.assertEqual(len(report['billboard_vertex_ranges']), 5)
        self.assertTrue(all(r[1] == 22 for r in report['billboard_vertex_ranges']))


if __name__ == '__main__':
    unittest.main()
