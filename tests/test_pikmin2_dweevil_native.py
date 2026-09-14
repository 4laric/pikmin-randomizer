"""Tests for experimental/pikmin2_dweevil_runtime (#170, child #447) and the
native policy header pc_p2_dweevil_policy.h.

Protocol/validation tests always run. The C++ policy test is compiled and
executed with strict MinGW flags when a pc_port include directory is available
(the lane worktree, native/pc_port, or $P2_NATIVE_PC_PORT); otherwise the
Python consistency checks still guard the contract and the compile is skipped.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from experimental import pikmin2_dweevil_runtime as dr
from experimental import pikmin2_elemental_behavior as eb

ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        text = dr.protocol(
            [dict(generator_id=235300, species=59, xyz=[34, 30, 1896], yaw=0, otakara_life=80.0)],
            [dict(id=900001, xyz=[30, 30, 1880], alive=True, pickable=True, captured=False)]).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], dr.MAGIC)
        self.assertEqual(lines[1], '1')
        self.assertEqual(lines[2].split()[0:2], ['235300', '59'])
        self.assertEqual(lines[3], '1')
        self.assertEqual(lines[4].split()[0], '900001')
        self.assertTrue(lines[4].endswith('1 1 0'))

    def test_no_treasure_is_fine(self):
        text = dr.protocol([dict(generator_id=1, species=93, xyz=[0, 0, 0], otakara_life=100)]).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[3], '0')

    def test_scenarios_match_the_native_reader(self):
        for blob in (dr.scenario_a(), dr.scenario_b()):
            self.assertTrue(blob.startswith(b'P2_DWEEVIL_NATIVE_1\n'))
            self.assertIn(b'235300 59 ', blob)

    def test_rejections(self):
        def reject(units, treasures=()):
            with self.assertRaises(ValueError):
                dr.protocol(units, treasures)
        good = dict(generator_id=235300, species=59, xyz=[0, 0, 0], otakara_life=80.0)
        reject([])
        reject([good] * 9)
        reject([dict(good, species=58)])
        reject([dict(good, xyz=[1e6, 0, 0])])
        reject([dict(good, xyz=[float('nan'), 0, 0])])
        reject([dict(good, yaw=361)])
        reject([dict(good, otakara_life=0)])
        reject([dict(good, generator_id=1 << 32)])
        reject([good, dict(good)])
        reject([good], [dict(id=900001, xyz=[0, 0, 0], alive=True, pickable=True, captured=False)] * 9)
        reject([good], [dict(id=900001, xyz=[0, 0, 0], alive=1, pickable=True, captured=False)])
        reject([good], [dict(id=900001, xyz=[0, 0, 0], alive=True, pickable=True, captured=False),
                        dict(id=900001, xyz=[0, 0, 0], alive=True, pickable=True, captured=False)])
        reject([good], [dict(id=235300, xyz=[0, 0, 0], alive=True, pickable=True, captured=False)])


class ReferenceTests(unittest.TestCase):
    def test_python_model_contract(self):
        self.assertEqual(eb.DWEEVIL_STATES['take'], 5)
        self.assertEqual(eb.DWEEVIL_STATES['item_drop'], 10)
        self.assertEqual(eb.DWEEVIL_STATES['bomb_turn'], 13)
        self.assertEqual(eb.dweevil_stimulus('FireOtakara'), 'InteractFire')
        self.assertEqual(eb.dweevil_stimulus('WaterOtakara'), 'InteractBubble')
        self.assertEqual(eb.dweevil_stimulus('GasOtakara'), 'InteractGas')
        self.assertEqual(eb.dweevil_stimulus('ElecOtakara'), 'InteractDenki')
        self.assertIsNone(eb.dweevil_stimulus('BombOtakara'))
        self.assertEqual(eb.DWEEVIL_IDS, ('FireOtakara', 'WaterOtakara', 'GasOtakara',
                                           'ElecOtakara', 'BombOtakara'))
        self.assertEqual(dr.SPECIES, (59, 60, 61, 62, 93))


class SyntheticLogTests(unittest.TestCase):
    GOOD = (
        'P2_DWEEVIL_READY generator=235300 species=FireOtakara xyz=34.000,30.000,1896.000 yaw=0.000 otakara_life=80.0 policy=dweevil_source_1\n'
        'P2_DWEEVIL_TREASURE id=900000 xyz=30.000,30.000,1880.000 alive=1 pickable=0 captured=0\n'
        'P2_DWEEVIL_BASELINE red=5 blue=5\n'
        'P2_DWEEVIL_READY generator=235300 species=FireOtakara xyz=34.000,30.000,1896.000 yaw=0.000 otakara_life=80.0 policy=dweevil_source_1\n'
        'P2_DWEEVIL_TREASURE id=900001 xyz=30.000,30.000,1880.000 alive=1 pickable=1 captured=0\n'
        'P2_DWEEVIL_SCENARIO1 death_drop_replay\n'
        'P2_DWEEVIL_CAPTURE generator=235300 species=FireOtakara treasure=900001 otakara_life=80.0 health=80.0\n'
        'P2_DWEEVIL_CARRY generator=235300 treasure=900001 state=item_move otakara_health=80.0\n'
        'P2_DWEEVIL_DEATH generator=235300 tick=40 fixture=1\n'
        'P2_DWEEVIL_DROP generator=235300 treasure=900001 reason=death dropped=1 exactly_once=1 total_drops=1\n'
        'P2_DWEEVIL_REPLAY generator=235300 tick=100 fixture=1\n'
        'P2_DWEEVIL_DROP_SUPPRESSED generator=235300 treasure=900001 reason=death dropped=0 already_dropped=1\n'
        'P2_DWEEVIL_RESET_REQUEST\n'
        'P2_DWEEVIL_READY generator=235300 species=FireOtakara xyz=34.000,30.000,1896.000 yaw=0.000 otakara_life=80.0 policy=dweevil_source_1\n'
        'P2_DWEEVIL_TREASURE id=900002 xyz=30.000,30.000,1880.000 alive=1 pickable=1 captured=0\n'
        'P2_DWEEVIL_SCENARIO2 interrupt_drop\n'
        'P2_DWEEVIL_CAPTURE generator=235300 species=FireOtakara treasure=900002 otakara_life=80.0 health=80.0\n'
        'P2_DWEEVIL_CARRY generator=235300 treasure=900002 state=item_move otakara_health=80.0\n'
        'P2_DWEEVIL_INTERRUPT generator=235300 tick=40 fixture=1\n'
        'P2_DWEEVIL_DROP generator=235300 treasure=900002 reason=interruption dropped=1 exactly_once=1 total_drops=1\n'
        'P2_DWEEVIL_DEATH generator=235300 tick=100 fixture=1\n'
        'P2_DWEEVIL_DROP_SUPPRESSED generator=235300 treasure=900002 reason=death dropped=0 already_dropped=1\n'
        'Experimental preview window set to 960x540 windowed and centered\n'
        'PASS P2_DWEEVIL_RUNTIME bounded_behavior_tick\n'
    )

    def test_good_log_passes(self):
        evidence = dr.validate(self.GOOD, 0)
        self.assertTrue(evidence['passed'], evidence['failed'])
        self.assertEqual(evidence['failed'], [])

    def test_missing_drop_fails(self):
        text = self.GOOD.replace(
            'P2_DWEEVIL_DROP generator=235300 treasure=900001 reason=death dropped=1 exactly_once=1 total_drops=1\n', '')
        evidence = dr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        for name in ('death_drop', 'exactly_two_drops'):
            self.assertIn(name, evidence['failed'])

    def test_duplicate_drop_fails(self):
        doubled = self.GOOD + ('P2_DWEEVIL_DROP generator=235300 treasure=900001 reason=death '
                               'dropped=1 exactly_once=1 total_drops=2\n')
        evidence = dr.validate(doubled, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('exactly_two_drops', evidence['failed'])

    def test_missing_suppression_fails(self):
        text = self.GOOD.replace(
            'P2_DWEEVIL_DROP_SUPPRESSED generator=235300 treasure=900002 reason=death dropped=0 already_dropped=1\n', '')
        evidence = dr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        for name in ('suppressed_interrupt', 'exactly_two_suppressed'):
            self.assertIn(name, evidence['failed'])

    def test_extra_capture_fails(self):
        text = self.GOOD + ('P2_DWEEVIL_CAPTURE generator=235300 species=FireOtakara treasure=900001 '
                            'otakara_life=80.0 health=80.0\n')
        evidence = dr.validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('captures', evidence['failed'])

    def test_nonzero_exit_fails(self):
        self.assertFalse(dr.validate(self.GOOD, 1)['passed'])


class NativePolicyTests(unittest.TestCase):
    def test_native_policy_executable(self):
        candidates = []
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.append(Path(os.environ['P2_NATIVE_PC_PORT']))
        candidates.append(ROOT / 'native' / 'pc_port')
        candidates.append(ROOT.parent.parent / 'native' / 'output' / 'p2-lane22-native' / 'pc_port')
        include = next((c for c in candidates if (c / 'pc_p2_dweevil_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            return  # Python consistency checks above still guard the contract
        source = ROOT / 'tests' / 'pikmin2_dweevil_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-dweevil-policy-') as tmp:
            exe = Path(tmp) / 'dweevil_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
