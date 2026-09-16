import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_fuefuki_teki_stage import (
    NAPKID_TYPE,
    POD_CARGO_PROFILE,
    SIDECAR_MAGIC,
    append_napkid,
)
from scripts.preview_pikmin2_room import records


def make_record(gen_id, name, tag=b'meti', teki_type=None):
    row = bytearray(120)
    row[0:8] = b'    0.0v'
    struct.pack_into('<I', row, 8, gen_id)
    row[16:48] = name.encode('ascii').ljust(32, b'\0')
    row[72:76] = tag
    if teki_type is not None:
        row[80] = teki_type
    return bytes(row)


def make_gen(path, dwarf=True):
    entries = [make_record(1, 'preview red onion'), make_record(2, 'preview ship')]
    if dwarf:
        entries.append(make_record(3, 'preview dwarf bulborb', b'iket', 3))
    blob = (b'1.0v' + struct.pack('>4f', 0, 0, 0, 0)
            + struct.pack('>I', len(entries)) + b''.join(entries))
    path.write_bytes(blob)
    return blob


class FuefukiTekistageTests(unittest.TestCase):
    def test_sidecar_and_pod_profile(self):
        self.assertEqual(SIDECAR_MAGIC, 'P2_FUEFUKI_TEKI_1')
        self.assertEqual(NAPKID_TYPE, 11)
        lines = POD_CARGO_PROFILE.splitlines()
        self.assertEqual(lines[0], 'P2_POD_1')
        self.assertEqual(lines[-1], 'Kochappy 2')
        # A cargo Pod is required; the emitter must never write cargo-free.
        self.assertNotIn('cargo-free', POD_CARGO_PROFILE)

    def test_append_napkid_replaces_dwarf_and_sets_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = Path(tmp) / 'default.gen'
            make_gen(gen)
            rebuilt = append_napkid(gen, 245001, (-110.0, 20.0, 0.0))
            entries = records(gen)
            self.assertEqual(len(entries), 3)
            self.assertEqual(rebuilt, gen.read_bytes())
            by_gen = {struct.unpack_from('<I', r, 8)[0]: r for r in entries}
            self.assertIn(245001, by_gen)
            self.assertNotIn(3, by_gen)
            napkid = by_gen[245001]
            self.assertEqual(napkid[72:76], b'iket')
            self.assertEqual(napkid[80], NAPKID_TYPE)
            self.assertEqual(napkid[16:16 + len(b'Fuefuki Napkid vehicle')],
                             b'Fuefuki Napkid vehicle')
            x, y, z = struct.unpack_from('>3f', napkid, 48)
            self.assertAlmostEqual(x, -110.0)
            self.assertAlmostEqual(y, 20.0)
            self.assertAlmostEqual(z, 0.0)

    def test_append_napkid_generator_collision_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = Path(tmp) / 'default.gen'
            make_gen(gen)
            with self.assertRaises(ValueError):
                append_napkid(gen, 3, (0.0, 0.0, 0.0))


if __name__ == '__main__':
    unittest.main()
