"""Tests for experimental/pikmin2_flora_runtime.py and the native #171 policy.

The pure consistency and protocol checks always run. The native policy test is
compiled and executed with strict MinGW flags when a compiler and the
native-patches/flora header are available; otherwise it is skipped without
failing the suite.
"""
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from experimental import pikmin2_flora_behavior as fb
from experimental import pikmin2_flora_runtime as fr

ROOT = Path(__file__).resolve().parents[1]

SPECS = [dict(generator=240001, stage='full', pellet=5, colour='blue')]


class ProtocolTests(unittest.TestCase):
    def test_sidecar_round_trip(self):
        text = fr.pelplant_sidecar(SPECS).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], 'P2_FLORA_PELPLANT_1 1')
        self.assertEqual(lines[1], '240001 full 5 blue')

    def test_sidecar_random_colour(self):
        text = fr.pelplant_sidecar([dict(generator=1, stage='middle', pellet=20, colour='random')]).decode('ascii')
        self.assertEqual(text.splitlines()[1], '1 middle 20 random')

    def test_sidecar_rejections(self):
        def reject(specs):
            with self.assertRaises(ValueError):
                fr.pelplant_sidecar(specs)
        reject([])
        reject(SPECS + [dict(SPECS[0])])                                     # duplicate generator
        reject([dict(SPECS[0], generator=1 << 32)])                          # id overflow
        reject([dict(SPECS[0], stage='huge')])                               # unknown stage
        reject([dict(SPECS[0], pellet=7)])                                   # invalid size
        reject([dict(SPECS[0], colour='purple')])                            # unknown colour

    def test_validate_pass_and_fail(self):
        text = (
            'P2_FLORA_PELPLANT_READY generator=240001 stage=full pellet=5 colour=blue visual=P1_Palm_proxy\n'
            'P2_FLORA_FIXTURE_ATTACK_ASSIGNED count=5\n'
            'P2_FLORA_PELPLANT_FELL generator=240001 stage=full instant_fell_head=1 pellet=5 released_on_death=1 regrowth=0\n'
            'P2_FLORA_PELLET_RELEASED generator=240001 pellet=5 colour=0 capture_receptor=1\n'
            'P2_FLORA_PELLET_CAPTURED generator=240001 carriers=1 carrier=0x1\n'
            'P2_FLORA_FIXTURE_CAPTURED carriers=1 pellet=70723030\n'
            'P2_FLORA_FIXTURE_DELIVER_ENDPOINT injection=1 natural_carry=0\n'
            'P2_FLORA_ONION_RECEIPT generator=240001 pellet=5 pokos=0 seeds=5 granted=1 duplicate=0 ledger=onion seed=local\n'
            '[Pikipelago] P2_FLORA_DELIVER onion_receipt=1\n'
            'P2_FLORA_FIXTURE_DELIVERED receipts=1 duplicates=0\n'
            'PASS P2_FLORA_PELPLANT_RUNTIME release_capture_deliver\n'
        )
        good = fr.validate(text, 0)
        self.assertTrue(good['passed'], good['failed'])
        # A missing capture must fail closed.
        missing = text.replace('P2_FLORA_PELLET_CAPTURED generator=240001 carriers=1 carrier=0x1\n', '')
        bad = fr.validate(missing, 0)
        self.assertFalse(bad['passed'])
        self.assertIn('captured', bad['failed'])
        # A first-run duplicate (no grant) must fail the receipt gate.
        dup = text.replace('granted=1 duplicate=0', 'granted=0 duplicate=1')
        self.assertIn('onion_receipt', fr.validate(dup, 0)['failed'])

    def test_generator_uid_is_little_endian(self):
        # Generator::_70 is the little-endian view of record[8:12]; big-endian
        # stamping would silently never bind.
        little = bytearray(64)
        struct.pack_into('<I', little, 8, 240001)
        self.assertEqual(fr.generator_uid(bytes(little)), 240001)
        big = bytearray(64)
        struct.pack_into('>I', big, 8, 240001)
        self.assertNotEqual(fr.generator_uid(bytes(big)), 240001)

    def test_instrument_replaces_room_app(self):
        source = 'prefix\nclass RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\nint main(int, char**) { return 0; }\n'
        out = fr.instrument(source)
        self.assertIn('PASS P2_FLORA_PELPLANT_RUNTIME', out)
        self.assertIn('int main(', out)
        self.assertNotIn('class RoomApp : public PlugPikiApp {\n int idle() override { return 0; }', out)


class ConsistencyTests(unittest.TestCase):
    """Native policy constants must keep matching the #171 behavior model."""

    def test_reference_facts_used_by_the_actor(self):
        self.assertEqual(fb.FLORA['Pelplant'], 0)
        self.assertEqual(fb.PELPLANT_STATES['waitsmall'], 0)
        self.assertEqual(fb.PELPLANT_STATES['waitfull'], 2)
        self.assertEqual(fb.PELPLANT_STATES['dead'], 6)
        self.assertEqual(fb.PELPLANT_PROPER_DISC['fp01'], 90.0)
        self.assertEqual(fb.PELPLANT_PROPER_DISC['fp02'], 60.0)
        self.assertEqual(fb.PELPLANT_PROPER_DISC['fp03'], 1.5)
        self.assertEqual(tuple(fb.PELPLANT_PELLET_SIZES), (1, 5, 10, 20))
        self.assertEqual(tuple(fb.PELLET_COLOUR_CYCLE), ('blue', 'red', 'yellow'))
        self.assertFalse(fb.PELPLANT_HAS_REGROWTH_TIMER)
        self.assertFalse(fb.PELLET_FOLLOWS_ATTACKER_COLOUR)
        self.assertEqual(fb.PELPLANT_INSTANT_FELL_SUFFIX, '0')
        # Policy function spot-checks.
        self.assertTrue(fb.pellet_is_vulnerable('full'))
        self.assertFalse(fb.pellet_is_vulnerable('small'))
        self.assertFalse(fb.pellet_is_vulnerable('middle'))
        self.assertTrue(fb.pellet_instant_fell('s__0'))
        self.assertFalse(fb.pellet_instant_fell('head'))
        self.assertTrue(fb.pellet_released_on_death(captured=True, state='dead'))
        self.assertFalse(fb.pellet_released_on_death(captured=False, state='dead'))
        self.assertEqual(fb.pellet_growth('small', 90.0, growing=True), 'middle')
        self.assertEqual(fb.pellet_growth('small', 1000.0, growing=False), 'small')
        self.assertTrue(fb.pellet_size_uses_bgrow(10))
        self.assertFalse(fb.pellet_size_uses_bgrow(5))

    def test_native_policy_executable(self):
        candidates = [ROOT / 'native-patches' / 'flora']
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.append(Path(os.environ['P2_NATIVE_PC_PORT']))
        include = next((c for c in candidates if (c / 'pc_p2_flora_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            return  # reference-consistency checks above still guard the contract
        source = ROOT / 'tests' / 'pikmin2_flora_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-flora-policy-') as tmp:
            exe = Path(tmp) / 'flora_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
