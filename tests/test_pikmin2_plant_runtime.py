"""Tests for experimental/pikmin2_plant_runtime.py and the native #448 policy.

Pure consistency and protocol checks always run. The native policy test is
compiled and executed with strict MinGW flags when a compiler and the
native-patches/plant header are available; otherwise it is skipped.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from experimental import pikmin2_flora_behavior as fb
from experimental import pikmin2_plant_runtime as pl

ROOT = Path(__file__).resolve().parents[1]

SPECS = [dict(generator=240021, species='Ooinu_l', lod_scale=1.5, floor_offset=0, sentinel=1),
         dict(generator=240022, species='Tanpopo', lod_scale=0.1, floor_offset=25, sentinel=0),
         dict(generator=240023, species='Clover', lod_scale=9.0, floor_offset=25, sentinel=1)]


class ProtocolTests(unittest.TestCase):
    def test_sidecar_round_trip(self):
        text = pl.plant_sidecar(SPECS).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], 'P2_PLANT_1 3')
        self.assertEqual(lines[1], '240021 Ooinu_l 1.5 0 1')
        self.assertEqual(lines[2], '240022 Tanpopo 0.1 25 0')
        self.assertEqual(lines[3], '240023 Clover 9.0 25 1')

    def test_sidecar_rejections(self):
        def reject(specs):
            with self.assertRaises(ValueError):
                pl.plant_sidecar(specs)
        reject([])
        reject(SPECS + [dict(SPECS[0])])                                # duplicate generator
        reject([dict(SPECS[0], generator=1 << 32)])                     # id overflow
        reject([dict(SPECS[0], sentinel=2)])                            # sentinel not 0/1

    def test_validate_pass_and_fail(self):
        text = (
            'P2_PLANT_LOD generator=240021 species=Ooinu_l territory=lifted_sphere private=cylinder home=cylinder '
            'floor_role=none floor_offset=0.000 scale=1.500 clamped=0 reconstructed=0 bound=1\n'
            'P2_PLANT_LOD generator=240022 species=Tanpopo territory=lifted_sphere private=cylinder home=cylinder '
            'floor_role=none floor_offset=0.000 scale=0.250 clamped=1 reconstructed=0 bound=1\n'
            'P2_PLANT_LOD generator=240023 species=Clover territory=lifted_sphere private=cylinder home=cylinder '
            'floor_role=floor_offset floor_offset=40.000 scale=4.000 clamped=0 reconstructed=1 bound=1\n'
            'P2_PLANT_SENTINEL_NONE generator=240022 species=Tanpopo sentinel=0\n'
            'P2_PLANT_SENTINEL_ARMED generator=240021 species=Ooinu_l per_touch=5 slot_reserved=1\n'
            'P2_PLANT_SENTINEL_BLOCKED generator=240021 species=Ooinu_l reason=no_qurione_seam spawn=blocked\n'
            'P2_PLANT_SENTINEL_SUPPRESSED generator=240023 species=Clover reason=no_reserved_slot\n'
            'PASS P2_PLANT_NATIVE lod_sentinel_slot_rule\n'
        )
        good = pl.validate(text, 0)
        self.assertTrue(good['passed'], good['failed'])
        missing = text.replace('P2_PLANT_SENTINEL_BLOCKED generator=240021 species=Ooinu_l reason=no_qurione_seam spawn=blocked\n', '')
        bad = pl.validate(missing, 0)
        self.assertFalse(bad['passed'])
        self.assertIn('sentinel_spawn', bad['failed'])

    def test_instrument_replaces_room_app(self):
        source = 'prefix\nclass RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\nint main(int, char**) { return 0; }\n'
        out = pl.instrument(source)
        self.assertIn('PASS P2_PLANT_NATIVE', out)
        self.assertIn('int main(', out)


class ConsistencyTests(unittest.TestCase):
    """Native policy constants must keep matching the #171 behavior model."""

    def test_reference_facts_used_by_the_actor(self):
        self.assertIn('Tanpopo', fb.PLANT_SPECIES)
        self.assertIn('Ooinu_l', fb.PLANT_SPECIES)
        self.assertIn('Magaret', fb.PLANT_SPECIES)
        self.assertEqual(tuple(fb.SPECTRALID_DECLARED), ('Tanpopo', 'Ooinu_l', 'Magaret'))
        self.assertEqual(fb.SPECTRALID_PER_TOUCH, 5)
        self.assertEqual(fb.PLANT_SWAY_MIN_SPEED, 1.0)
        self.assertEqual(fb.plant_lod('Tanpopo', 'territory'), 'lifted_sphere')
        self.assertEqual(fb.plant_lod('Tanpopo', 'private_radius'), 'cylinder')
        self.assertEqual(fb.plant_lod('Tanpopo', 'home_radius'), 'cylinder')
        self.assertIsNone(fb.plant_lod('Tanpopo', 'fp01'))
        self.assertEqual(fb.plant_lod('Clover', 'fp01'), 'floor_offset')
        clover = fb.plant_floor_offset('Clover')
        self.assertEqual(clover['general_fp01_disc'], 40.0)
        self.assertTrue(fb.plant_floor_offset.reconstructed)
        self.assertTrue(fb.spectralid_reserved('Tanpopo') and fb.spectralid_reserved('Ooinu_l') and fb.spectralid_reserved('Magaret'))
        self.assertFalse(fb.spectralid_reserved('Clover'))
        self.assertEqual(fb.spectralid_spawn(species='Tanpopo', has_sentinel=True, first_touch=True), 5)
        self.assertEqual(fb.spectralid_spawn(species='Tanpopo', has_sentinel=False, first_touch=True), 0)
        self.assertEqual(fb.spectralid_spawn(species='Tanpopo', has_sentinel=True, first_touch=False), 0)
        self.assertTrue(fb.plant_sways(mover='captain', speed=1.1, past_volume=True))
        self.assertFalse(fb.plant_sways(mover='captain', speed=1.0, past_volume=True))
        self.assertTrue(fb.plant_sways(mover='purple_quake', speed=0.0, past_volume=False))
        self.assertFalse(fb.plant_sways(mover='enemy', speed=10.0, past_volume=True))
        self.assertEqual(fb.plant_touch_sound('captain'), 'PSSE_PL_TOUCH_LEAF')
        self.assertIsNone(fb.plant_touch_sound('pikmin'))

    def test_native_policy_executable(self):
        candidates = [ROOT / 'native-patches' / 'plant']
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.append(Path(os.environ['P2_NATIVE_PC_PORT']))
        include = next((c for c in candidates if (c / 'pc_p2_plant_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            return
        source = ROOT / 'tests' / 'pikmin2_plant_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-plant-policy-') as tmp:
            exe = Path(tmp) / 'plant_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
