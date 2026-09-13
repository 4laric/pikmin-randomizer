"""Synthetic BTK import and compiled production sampler/draw-scope contracts."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from experimental.pikmin2_material_srt import decode, bank_text, export
from experimental.verify_material_srt import verify


def fixture():
    # Generated values, not retail animation data. Independent X incoming/outgoing tangents.
    block = bytearray(320)
    block[:4] = b'TTK1'
    struct.pack_into('>I', block, 4, len(block))
    struct.pack_into('>BBh4H', block, 8, 2, 1, 10, 3, 10, 1, 1)
    struct.pack_into('>8I', block, 20, 96, 150, 152, 176, 180, 192, 232, 236)
    struct.pack_into('>3H', block, 96, 2, 0, 1)  # X scale: 2 asymmetric keys
    struct.pack_into('>3H', block, 114, 1, 1, 0)  # Y scale: constant
    struct.pack_into('>3H', block, 138, 1, 0, 0)  # Z rotation
    struct.pack_into('>HHHH', block, 152, 1, 0xffff, 0, 8)
    block[160:169] = b'material\0'
    struct.pack_into('>3f', block, 180, .5, .5, 0)
    struct.pack_into('>10f', block, 192, 0, 1, 7, .2, 10, 3, -.4, 0, 3, 0)
    struct.pack_into('>h', block, 232, 17)
    header = bytearray(32)
    header[:8] = b'J3D1btk1'
    struct.pack_into('>II', header, 8, 352, 1)
    return bytes(header + block)


class MaterialImportTests(unittest.TestCase):
    def test_curve_mapping_and_determinism(self):
        raw = fixture()
        r = decode(raw)
        self.assertEqual(r['source_sha256'], hashlib.sha256(raw).hexdigest())
        t = r['tracks'][0]
        self.assertEqual((t['material'], t['slot']), ('material', 0))
        self.assertEqual(t['curves'][0][0], [0, 1, 7, struct.unpack('>f', struct.pack('>f', .2))[0]])
        self.assertEqual(t['curves'][1], [[0, 1, 0, 0]])
        self.assertEqual(t['curves'][2], [[0, 17, 0, 0]])
        self.assertEqual(t['curves'][3:], [[[0, 0, 0, 0]], [[0, 0, 0, 0]]])
        self.assertEqual(bank_text(r), bank_text(decode(raw)))

    def test_shared_tangents(self):
        raw = bytearray(fixture())
        struct.pack_into('>3H', raw, 32+96, 2, 0, 0)
        struct.pack_into('>6f', raw, 32+192, 0, 1, .2, 10, 3, -.4)
        for key in decode(raw)['tracks'][0]['curves'][0]:
            self.assertEqual(key[2], key[3])

    def test_reject_corruption_and_unsupported(self):
        raw = fixture()
        for n in range(len(raw)):
            with self.subTest(truncation=n), self.assertRaises(ValueError):
                decode(raw[:n])
        # bad signature/size/count, section tag/length, playback, shift, counts,
        # offsets, post matrices, Maya, curve bounds, name, slot, center and NaN pool.
        mutations = [(0, b'X'), (8, struct.pack('>I', 999)), (12, struct.pack('>I', 2)),
                     (32, b'NOPE'), (36, struct.pack('>I', 95)), (40, b'\x01'),
                     (41, b'\x10'), (42, b'\0\0'), (44, b'\0\x02'),
                     (52, struct.pack('>I', 0)), (84, b'\0\x01'),
                     (92, struct.pack('>I', 1)), (124, struct.pack('>I', 1)),
                     (128, struct.pack('>3H', 4097, 0, 1)),
                     (128, struct.pack('>3H', 2, 9, 1)),
                     (128, struct.pack('>3H', 2, 0, 2)),
                     (192, b'!'), (208, b'\x0a'),
                     (212, struct.pack('>f', float('inf'))),
                     (224, struct.pack('>f', float('nan'))),
                     (240, struct.pack('>f', 0))]
        for offset, data in mutations:
            mutated = bytearray(raw); mutated[offset:offset+len(data)] = data
            with self.subTest(offset=offset, data=data), self.assertRaises(ValueError):
                decode(mutated)

    def test_export_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'test.btk'; source.write_bytes(fixture())
            export(source, root/'bank')
            before = (root/'bank/material-srt.txt').read_bytes()
            with self.assertRaises(ValueError): export(source, root/'bank')
            self.assertEqual(before, (root/'bank/material-srt.txt').read_bytes())


class MaterialNativeTests(unittest.TestCase):
    def test_production_sampler_and_scope(self):
        root = Path(__file__).resolve().parents[1]
        compiler = shutil.which('g++') or ('C:/msys64/mingw64/bin/g++.exe' if Path('C:/msys64/mingw64/bin/g++.exe').exists() else None)
        if not compiler: self.skipTest('C++ compiler unavailable')
        env = dict(os.environ, PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH', ''))
        with tempfile.TemporaryDirectory() as d:
            build = Path(d)
            (build/'bank.txt').write_text(bank_text(decode(fixture())), encoding='ascii')
            output = build/'test.exe'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-I', str(root/'engine/tools/material_srt_stubs'),
                            '-I', str(root/'engine/pc_port'),
                            str(root/'engine/tools/test_p2_material_srt.cpp'),
                            str(root/'engine/pc_port/pc_p2_material_scope.cpp'),
                            '-o', str(output)], check=True, capture_output=True, env=env, timeout=60)
            result = subprocess.run([str(output), str(build/'bank.txt')], check=True, capture_output=True,
                                    text=True, env=env, timeout=15)
            self.assertIn('PASS', result.stdout)
            binding = build/'binding.exe'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-I', str(root/'engine/tools/material_srt_stubs'), '-I', str(root/'engine/pc_port'),
                            str(root/'engine/tools/test_p2_material_binding.cpp'),
                            str(root/'engine/pc_port/pc_p2_material_binding.cpp'), '-o', str(binding)],
                           check=True, capture_output=True, env=env, timeout=60)
            bound = subprocess.run([str(binding), str(build/'bank.txt')], check=True, capture_output=True,
                                   text=True, env=env, timeout=15)
            self.assertIn('PASS transactional', bound.stdout)
            probe = build/'sample.exe'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-I', str(root/'engine/pc_port'), str(root/'engine/tools/sample_p2_material_srt.cpp'),
                            '-o', str(probe)], check=True, capture_output=True, env=env, timeout=60)
            samples = subprocess.run([str(probe), str(build/'bank.txt')], check=True, capture_output=True,
                                     text=True, env=env, timeout=15).stdout.splitlines()
            self.assertEqual(verify(decode(fixture()), samples)['samples'], 81)
            with self.assertRaises(ValueError): verify(decode(fixture()), samples[:-1])
            for corrupted in ('extra', 'bad', 'zero-count', 'bad-curve'):
                text = bank_text(decode(fixture()))
                if corrupted == 'extra': text += 'trailing garbage'
                elif corrupted == 'bad': text = text.replace('material 0', 'material 99')
                elif corrupted == 'zero-count': text = text.replace('\n2\n', '\n0\n', 1)
                else: text = text.replace('10 3 ', '0 3 ')
                (build/'bad.txt').write_text(text, encoding='ascii')
                result = subprocess.run([str(probe), str(build/'bad.txt')], capture_output=True, env=env, timeout=15)
                with self.subTest(bank=corrupted): self.assertNotEqual(result.returncode, 0)
