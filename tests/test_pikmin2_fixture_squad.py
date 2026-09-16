"""Every private fixture stage must carry a starting Pikmin squad (#374-#376).

A zero-Pikmin stage boots straight into the engine extinction flow
(``GAMEEND_PikminExtinction`` / ``DEMOID_Extinction``), which unattended test
fixtures never clear. ``preview_pikmin2_room.ensure_pikmin_squad`` injects a
20-red squad at overlay time when the stage has no ``ikip`` record.
"""
import struct
import unittest
from unittest.mock import patch

from scripts.preview_pikmin2_room import ensure_pikmin_squad

HEADER = b'1.0v' + struct.pack('>4f', -85.0, 0.0, 0.0, 45.0)
ASSETS = object()


def record(kind):
    return b'    0.0v' + bytes(72 - 8) + kind + bytes(40)


def blob_with(template_kind):
    entry = record(template_kind)
    return b'1.0v' + struct.pack('>4fI', -85.0, 0.0, 0.0, 45.0, 1) + entry


def stage_without_pikmin():
    entry = record(b'iket')
    return HEADER + struct.pack('>I', 1) + entry


def count(data):
    return struct.unpack_from('>I', data, 20)[0]


class EnsurePikminSquadTests(unittest.TestCase):
    def test_injects_squad_when_absent(self):
        with patch('scripts.preview_pikmin2_room.generator',
                   return_value=blob_with(b'ikip')):
            data = stage_without_pikmin()
            self.assertNotIn(b'ikip', data)
            out = ensure_pikmin_squad(ASSETS, data)
        self.assertIn(b'ikip', out)
        self.assertEqual(count(out), 21)
        self.assertEqual(out.count(b'    0.0v'), 21)
        self.assertIn(struct.pack('<I', 1), out)  # fresh injected generator ID

    def test_idempotent_when_squad_present(self):
        with patch('scripts.preview_pikmin2_room.generator',
                   return_value=blob_with(b'ikip')):
            once = ensure_pikmin_squad(ASSETS, stage_without_pikmin())
            twice = ensure_pikmin_squad(ASSETS, once)
        self.assertEqual(once, twice)

    def test_existing_pikmin_stage_unchanged(self):
        data = blob_with(b'ikip')
        self.assertEqual(ensure_pikmin_squad(ASSETS, data), data)

    def test_non_stage_bytes_unchanged(self):
        self.assertEqual(ensure_pikmin_squad(ASSETS, b'not a stage'), b'not a stage')

    def test_no_template_leaves_stage_unchanged(self):
        with patch('scripts.preview_pikmin2_room.generator', return_value=b''):
            data = stage_without_pikmin()
            self.assertEqual(ensure_pikmin_squad(ASSETS, data), data)


if __name__ == '__main__':
    unittest.main()
