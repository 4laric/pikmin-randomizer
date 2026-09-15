"""Tests for experimental/pikmin2_hiba_runtime (#170, child #447) and the native
fixed-hazard policy header pc_p2_hiba_policy.h.

Protocol/validation tests always run. The C++ policy test is compiled and
executed with strict MinGW flags when a pc_port include directory is available
(the lane worktree, native/pc_port, or $P2_NATIVE_PC_PORT); otherwise the
Python-model consistency checks still guard the contract.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from experimental import pikmin2_hiba_runtime as hr
from experimental import pikmin2_elemental_behavior as eb

ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        text = hr.protocol(hr.scenario_hazards()).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], hr.MAGIC)
        self.assertEqual(lines[1], '3')
        self.assertTrue(lines[2].startswith('20 20 '))
        self.assertTrue(lines[3].startswith('21 21 '))
        self.assertTrue(lines[4].startswith('22 22 '))
        self.assertTrue(lines[4].endswith('0'))

    def test_reference_profile_parses(self):
        hr.protocol([dict(generator_id=20, hazard_id=20, xyz=[0, 0, 0])])

    def test_rejections(self):
        def reject(hazards):
            with self.assertRaises(ValueError):
                hr.protocol(hazards)
        good = dict(generator_id=20, hazard_id=20, xyz=[0, 0, 0])
        reject([])
        reject([good] * 9)
        reject([dict(good, hazard_id=23)])
        reject([dict(good, xyz=[1e6, 0, 0])])
        reject([dict(good, xyz=[float('nan'), 0, 0])])
        reject([dict(good, yaw=361)])
        reject([dict(good, health=0)])
        reject([dict(good, wait_override=1001)])
        reject([dict(good, separation=1)])
        reject([dict(good, link=1)])
        reject([dict(good, generator_id=1 << 32)])
        reject([good, dict(good)])
        reject([dict(good, hazard_id=22, separation=-1)])
        reject([dict(good, hazard_id=21, link=4)])
        reject([dict(good, warning_override=1)])           # warning on Hiba


class ReferenceTests(unittest.TestCase):
    def test_python_model_contract(self):
        self.assertEqual(eb.HAZARD_STATES['Hiba'], {'dead': 0, 'wait': 1, 'attack': 2})
        self.assertEqual(eb.HAZARD_STATES['GasHiba'], {'dead': 0, 'wait': 1, 'attack': 2})
        self.assertEqual(eb.HAZARD_STATES['ElecHiba'],
                         {'dead': 0, 'wait': 1, 'sign': 2, 'attack': 3})
        self.assertEqual(eb.HAZARD_TIMING_DISC['Hiba']['wait'], 3.0)
        self.assertEqual(eb.HAZARD_TIMING_HEADER['Hiba']['wait'], 2.5)
        self.assertEqual(eb.HAZARD_TIMING_DISC['GasHiba']['attack_start'], 0.6)
        self.assertEqual(eb.HAZARD_TIMING_DISC['ElecHiba']['warning'], 1.5)
        self.assertEqual(eb.EMITTED_STIMULUS['Hiba'], 'InteractFire')
        self.assertEqual(eb.EMITTED_STIMULUS['GasHiba'], 'InteractGas')
        self.assertEqual(eb.EMITTED_STIMULUS['ElecHiba'], 'InteractDenki')
        self.assertEqual(eb.panic_for('InteractDenki'), 'DenkiDying')
        self.assertEqual(eb.FIXED_HAZARD_CLASSIFICATION['GasHiba']['linked_actor'], 'bridge_or_gate')
        self.assertEqual(eb.FIXED_HAZARD_CLASSIFICATION['ElecHiba']['linked_actor'],
                         'parent_child_wire_pair')
        self.assertTrue(eb.is_fixed_hazard('Hiba') and eb.is_fixed_hazard('ElecHiba'))
        self.assertFalse(eb.is_fixed_hazard('Tank'))
        # Receiver spot-checks the native policy mirrors.
        self.assertEqual(eb.receiver_accepts(stimulus='InteractFire', colour='Red'), 'reject')
        self.assertEqual(eb.receiver_accepts(stimulus='InteractFire', colour='Blue'), 'accept')
        self.assertEqual(eb.receiver_accepts(stimulus='InteractGas', colour='White'), 'reject')
        self.assertEqual(eb.receiver_accepts(stimulus='InteractDenki', colour='Yellow'), 'reject')
        self.assertEqual(eb.hiba_activate(health=10.0, wait_elapsed=3.0), 'attack')
        self.assertTrue(eb.hiba_emit(state='attack', health=10.0, active_elapsed=0.0))


class SyntheticLogTests(unittest.TestCase):
    GOOD = (
        'P2_HIBA_READY generator=20 hazard=Hiba xyz=34.000,30.000,1896.000 wait=0.40 active=2.50 separation=0.00 link=none policy=hiba_source_1\n'
        'P2_HIBA_READY generator=21 hazard=GasHiba xyz=34.000,30.000,1904.000 wait=0.00 active=3.00 separation=0.00 link=none policy=hiba_source_1\n'
        'P2_HIBA_READY generator=22 hazard=ElecHiba xyz=34.000,30.000,1888.000 wait=0.40 active=2.50 separation=40.00 link=none policy=hiba_source_1\n'
        'P2_HIBA_BASELINE red=5 blue=5\n'
        'P2_HIBA_SCENARIO hiba_gas_elec centroid=34.000,30.000,1896.000\n'
        'P2_HIBA_NODES generator=22 hazard=ElecHiba center=34.000 negative=14.000 positive=54.000\n'
        'P2_HIBA_ACTIVATE generator=20 hazard=Hiba from=wait to=attack\n'
        'P2_HIBA_EMIT generator=20 hazard=Hiba stimulus=InteractFire\n'
        'P2_HIBA_FIRE_PASS generator=20 hazard=Hiba species=1 immune=1 applied=0\n'
        'P2_HIBA_FIRE_HIT generator=20 hazard=Hiba species=0 state=7 applied=1 damage=1.0\n'
        'P2_HIBA_ACTIVATE generator=21 hazard=GasHiba from=wait to=attack\n'
        'P2_HIBA_EMIT generator=21 hazard=GasHiba stimulus=InteractGas\n'
        'P2_HIBA_GAS_PASS generator=21 hazard=GasHiba species=4 immune=1 applied=0\n'
        'P2_HIBA_GAS_HIT generator=21 hazard=GasHiba species=1 state=36 applied=1\n'
        'P2_HIBA_ACTIVATE generator=22 hazard=ElecHiba from=sign to=attack\n'
        'P2_HIBA_EMIT generator=22 hazard=ElecHiba stimulus=InteractDenki\n'
        'P2_HIBA_DENKI_PASS generator=22 hazard=ElecHiba species=2 immune=1 applied=0\n'
        'P2_HIBA_DENKI_HIT generator=22 hazard=ElecHiba species=1 state=35 applied=1\n'
        'P2_HIBA_GAS_LETHAL dead=1 species=2\n'
        'P2_HIBA_DENKI_LETHAL dead=1 species=1\n'
        'P2_HIBA_RECOLOUR white=1 yellow=1\n'
        'P2_HIBA_CLEANUP kill_all=1\n'
        'P2_HIBA_DEAD generator=20 hazard=Hiba\n'
        'P2_HIBA_DEAD generator=21 hazard=GasHiba\n'
        'P2_HIBA_DEAD generator=22 hazard=ElecHiba\n'
        'Experimental preview window set to 960x540 windowed and centered\n'
        'PASS P2_HIBA_RUNTIME gates_ready\n'
    )

    def test_good_log_passes(self):
        evidence = hr.validate(self.GOOD, 0)
        self.assertTrue(evidence['passed'], evidence['failed'])
        self.assertEqual(evidence['failed'], [])

    def test_missing_fire_hit_fails(self):
        text = self.GOOD.replace('P2_HIBA_FIRE_HIT generator=20 hazard=Hiba species=0 state=7 applied=1 damage=1.0\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('fire_hit', evidence['failed'])

    def test_missing_fire_pass_fails(self):
        text = self.GOOD.replace('P2_HIBA_FIRE_PASS generator=20 hazard=Hiba species=1 immune=1 applied=0\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('fire_pass', evidence['failed'])

    def test_missing_gas_hit_fails(self):
        text = self.GOOD.replace('P2_HIBA_GAS_HIT generator=21 hazard=GasHiba species=1 state=36 applied=1\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('gas_hit', evidence['failed'])

    def test_missing_gas_pass_fails(self):
        text = self.GOOD.replace('P2_HIBA_GAS_PASS generator=21 hazard=GasHiba species=4 immune=1 applied=0\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('gas_pass', evidence['failed'])

    def test_missing_denki_hit_fails(self):
        text = self.GOOD.replace('P2_HIBA_DENKI_HIT generator=22 hazard=ElecHiba species=1 state=35 applied=1\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('denki_hit', evidence['failed'])

    def test_missing_denki_pass_fails(self):
        text = self.GOOD.replace('P2_HIBA_DENKI_PASS generator=22 hazard=ElecHiba species=2 immune=1 applied=0\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('denki_pass', evidence['failed'])

    def test_gas_blocked_reintroduced_fails(self):
        text = self.GOOD.replace('P2_HIBA_GAS_HIT generator=21 hazard=GasHiba species=1 state=36 applied=1\n',
                                 'P2_HIBA_APPLY_BLOCKED generator=21 hazard=GasHiba stimulus=InteractGas '
                                 'colour=Blue immune=0 applied=0 reason=no_engine_interaction\n'
                                 'P2_HIBA_GAS_HIT generator=21 hazard=GasHiba species=1 state=36 applied=1\n')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_gas_blocked', evidence['failed'])
        self.assertIn('no_apply_blocked', evidence['failed'])

    def test_fire_death_without_gas_lethal_fails(self):
        text = self.GOOD.replace('P2_HIBA_GAS_LETHAL dead=1 species=2\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('gas_lethal', evidence['failed'])

    def test_bare_gas_lethal_fails(self):
        text = self.GOOD.replace('P2_HIBA_GAS_LETHAL dead=1 species=2\n', 'P2_HIBA_GAS_LETHAL dead=1\n')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('gas_lethal', evidence['failed'])

    def test_bare_denki_lethal_fails(self):
        text = self.GOOD.replace('P2_HIBA_DENKI_LETHAL dead=1 species=1\n', 'P2_HIBA_DENKI_LETHAL dead=1\n')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('denki_lethal', evidence['failed'])

    def test_missing_gas_hit_red_fails(self):
        text = self.GOOD.replace('P2_HIBA_GAS_HIT generator=21 hazard=GasHiba species=1 state=36 applied=1\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('gas_hit_red', evidence['failed'])

    def test_missing_elec_activation_fails(self):
        text = self.GOOD.replace('P2_HIBA_ACTIVATE generator=22 hazard=ElecHiba from=sign to=attack\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('activate_elec', evidence['failed'])

    def test_blocked_timeout_fails(self):
        text = self.GOOD.replace('PASS P2_HIBA_RUNTIME gates_ready\n',
                                 'P2_HIBA_BLOCKED gates reason=timeout hit=1 immune=1 activated=3 emitted=3\n')
        evidence = hr.validate(text, 1)
        self.assertFalse(evidence['passed'])
        for name in ('completion', 'no_timeout'):
            self.assertIn(name, evidence['failed'])

    def test_nonzero_exit_fails(self):
        self.assertFalse(hr.validate(self.GOOD, 1)['passed'])


class GasReceiverNativeTests(unittest.TestCase):
    GOOD = SyntheticLogTests.GOOD

    def test_missing_gas_lethal_fails(self):
        text = self.GOOD.replace('P2_HIBA_GAS_LETHAL dead=1 species=2\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('gas_lethal', evidence['failed'])

    def test_missing_denki_lethal_fails(self):
        text = self.GOOD.replace('P2_HIBA_DENKI_LETHAL dead=1 species=1\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('denki_lethal', evidence['failed'])

    def test_missing_recolour_fails(self):
        text = self.GOOD.replace('P2_HIBA_RECOLOUR white=1 yellow=1\n', '')
        evidence = hr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('recolour', evidence['failed'])


class NativePolicyTests(unittest.TestCase):
    def test_native_policy_executable(self):
        candidates = []
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.append(Path(os.environ['P2_NATIVE_PC_PORT']))
        candidates.append(ROOT / 'native' / 'pc_port')
        candidates.append(ROOT / 'engine' / 'pc_port')
        include = next((c for c in candidates if (c / 'pc_p2_hiba_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            self.skipTest('Hiba policy header/compiler unavailable in selected checkout')
        source = ROOT / 'tests' / 'pikmin2_hiba_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-hiba-policy-') as tmp:
            exe = Path(tmp) / 'hiba_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
