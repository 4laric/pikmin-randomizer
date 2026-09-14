"""Tests for experimental/pikmin2_bombotakara_runtime (#170, child #447) and the
native payload policy header pc_p2_bombotakara_policy.h.

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

from experimental import pikmin2_bombotakara_runtime as br
from experimental import pikmin2_elemental_behavior as eb

ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        text = br.protocol(br.scenario_units()).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], br.MAGIC)
        self.assertEqual(lines[1], '2')
        self.assertTrue(lines[2].startswith('30 '))
        self.assertTrue(lines[3].startswith('31 '))

    def test_injection_text(self):
        text = br.injection_text().decode('ascii').splitlines()
        self.assertEqual(len(text), 4)
        self.assertTrue(text[0].startswith('P2_BOMBOTAKARA_INJECT_1 75 30 contact'))
        self.assertTrue(text[1].startswith('P2_BOMBOTAKARA_INJECT_1 90 31 death'))
        self.assertTrue(text[2].startswith('P2_BOMBOTAKARA_INJECT_1 105 30 contact'))
        self.assertTrue(text[3].startswith('P2_BOMBOTAKARA_INJECT_1 120 31 death'))

    def test_rejections(self):
        def reject(units):
            with self.assertRaises(ValueError):
                br.protocol(units)
        good = dict(generator_id=30, payload_id=40, xyz=[0, 0, 0], bomb_xyz=[1, 0, 1])
        reject([])
        reject([good] * 5)
        reject([dict(good, generator_id=1 << 32)])
        reject([dict(good, payload_id=1 << 32)])
        reject([dict(good, xyz=[1e6, 0, 0])])
        reject([dict(good, xyz=[float('nan'), 0, 0])])
        reject([dict(good, bomb_xyz=[0, 0, float('inf')])])
        reject([dict(good, yaw=361)])
        reject([dict(good, health=0)])
        reject([good, dict(good)])
        reject([good, dict(good, payload_id=41, generator_id=40)])


class ReferenceTests(unittest.TestCase):
    def test_python_model_contract(self):
        self.assertEqual(eb.ENEMY_IDS['BombOtakara'], 93)
        self.assertEqual(eb.BOMB_FORCE_DELAY_SECONDS, 1.5)
        self.assertTrue(eb.BOMB_OTAKARA_CONSUMES_SHARED_BLAST)
        self.assertEqual(eb.DWEEVIL_STATES['bomb_wait'], 11)
        self.assertEqual(eb.DWEEVIL_STATES['bomb_move'], 12)
        self.assertEqual(eb.DWEEVIL_STATES['bomb_turn'], 13)
        self.assertEqual(eb.BOMB_CARRY_STATES, ('bomb_wait', 'bomb_move', 'bomb_turn'))
        base = dict(payload_present=True, bittered=False, earthquake=False)
        self.assertEqual(eb.bomb_otakara_payload(**base), 'chase_payload')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, chase_elapsed=1.4)), 'chase_payload')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, chase_elapsed=1.5)), 'force_bomb')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, bittered=True)), 'damage_payload')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, earthquake=True)), 'force_bomb')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, payload_present=False)), 'kill_carrier')


class SyntheticLogTests(unittest.TestCase):
    GOOD = (
        'P2_BOMBOTAKARA_READY generator=30 xyz=34.000,30.000,1896.000 health=150.0 payload=40 bomb_xyz=44.000,30.000,1906.000 state=bomb_wait policy=bombotakara_source_1\n'
        'P2_BOMBOTAKARA_READY generator=31 xyz=40.000,30.000,1902.000 health=150.0 payload=41 bomb_xyz=50.000,30.000,1912.000 state=bomb_wait policy=bombotakara_source_1\n'
        'P2_BOMBOTAKARA_CARRY generator=30 payload=40 state=bomb_wait joint=otakara\n'
        'P2_BOMBOTAKARA_CARRY generator=31 payload=41 state=bomb_wait joint=otakara\n'
        'P2_BOMBOTAKARA_ARM generator=30 payload=40 arm_seconds=1.50 source=stimulateBomb\n'
        'P2_BOMBOTAKARA_ARM generator=31 payload=41 arm_seconds=1.50 source=stimulateBomb\n'
        'P2_BOMBOTAKARA_DETONATE generator=30 payload=40 trigger=contact detonated=1 exactly_once=1 total_detonations=1\n'
        'P2_BOMBOTAKARA_BLAST_BLOCKED generator=30 payload=40 reason=no_shared_blast\n'
        'P2_BOMBOTAKARA_DETONATE generator=31 payload=41 trigger=death detonated=1 exactly_once=1 total_detonations=1\n'
        'P2_BOMBOTAKARA_BLAST_BLOCKED generator=31 payload=41 reason=no_shared_blast\n'
        'P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=30 payload=40 trigger=contact detonated=0 already_detonated=1\n'
        'P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=31 payload=41 trigger=death detonated=0 already_detonated=1\n'
        'P2_BOMBOTAKARA_BASELINE red=5 blue=5\n'
        'P2_BOMBOTAKARA_SCENARIO carry_arm_detonate centroid=37.000,30.000,1899.000\n'
        'P2_BOMBOTAKARA_CLEANUP kill_all=1\n'
        'P2_BOMBOTAKARA_DEAD generator=30\n'
        'Experimental preview window set to 960x540 windowed and centered\n'
        'PASS P2_BOMBOTAKARA_RUNTIME gates_ready\n'
    )

    def test_good_log_passes(self):
        evidence = br.validate(self.GOOD, 0)
        self.assertTrue(evidence['passed'], evidence['failed'])
        self.assertEqual(evidence['failed'], [])

    def test_missing_detonate_fails(self):
        text = self.GOOD.replace(
            'P2_BOMBOTAKARA_DETONATE generator=30 payload=40 trigger=contact detonated=1 exactly_once=1 total_detonations=1\n', '')
        evidence = br.validate(text, 0)
        self.assertFalse(evidence['passed'])
        for name in ('detonate_contact', 'exactly_two_detonations'):
            self.assertIn(name, evidence['failed'])

    def test_duplicate_detonation_fails(self):
        doubled = self.GOOD + ('P2_BOMBOTAKARA_DETONATE generator=30 payload=40 trigger=contact '
                               'detonated=1 exactly_once=1 total_detonations=2\n')
        evidence = br.validate(doubled, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('exactly_two_detonations', evidence['failed'])

    def test_missing_suppression_fails(self):
        text = self.GOOD.replace(
            'P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=31 payload=41 trigger=death detonated=0 already_detonated=1\n', '')
        evidence = br.validate(text, 0)
        self.assertFalse(evidence['passed'])
        for name in ('suppressed_death', 'exactly_two_suppressed'):
            self.assertIn(name, evidence['failed'])

    def test_missing_blast_blocked_fails(self):
        text = self.GOOD.replace('P2_BOMBOTAKARA_BLAST_BLOCKED generator=31 payload=41 reason=no_shared_blast\n', '')
        evidence = br.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('blast_blocked', evidence['failed'])

    def test_blocked_timeout_fails(self):
        text = self.GOOD.replace('PASS P2_BOMBOTAKARA_RUNTIME gates_ready\n',
                                 'P2_BOMBOTAKARA_BLOCKED gates reason=timeout carry=2 armed=2 detonated=1 suppressed=0 blast=1\n')
        evidence = br.validate(text, 1)
        self.assertFalse(evidence['passed'])
        for name in ('completion', 'no_timeout'):
            self.assertIn(name, evidence['failed'])

    def test_nonzero_exit_fails(self):
        self.assertFalse(br.validate(self.GOOD, 1)['passed'])


class NativePolicyTests(unittest.TestCase):
    def test_native_policy_executable(self):
        candidates = []
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.append(Path(os.environ['P2_NATIVE_PC_PORT']))
        candidates.append(ROOT / 'native' / 'pc_port')
        candidates.append(ROOT.parent.parent / 'native' / 'output' / 'p2-lane22-native' / 'pc_port')
        include = next((c for c in candidates if (c / 'pc_p2_bombotakara_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            return  # Python consistency checks above still guard the contract
        source = ROOT / 'tests' / 'pikmin2_bombotakara_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-bombotakara-policy-') as tmp:
            exe = Path(tmp) / 'bombotakara_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
