"""Campaign identity serialization and production C++ parser acceptance."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from randomizer.purple_campaign import combat_profile

class CombatBindingsTests(unittest.TestCase):
    def test_exact_species_deterministic_uid_order(self):
        rows = [dict(target='300', source_id=33, enum_name='FireChappy'),
                dict(target='200', source_id=2, enum_name='Chappy'),
                dict(target='100', source_id=1, enum_name='Kochappy')]
        expected = b'P2_PURPLE_DIRECT_2\nbindings 2\n100 1\n200 2\n'
        self.assertEqual(combat_profile({'p2_layout': {'bindings': rows}}), expected)
        self.assertEqual(combat_profile({'p2_layout': {'bindings': rows[::-1]}}), expected)
        self.assertEqual(combat_profile({'p2_layout': {'bindings': []}}), b'P2_PURPLE_DIRECT_2\nbindings 0\n')

    def test_reject_ambiguous_or_wrong_identity(self):
        good = dict(target='10', source_id=2, enum_name='Chappy')
        for change in [dict(target='010'), dict(target='0'), dict(target='4294967296'),
                       dict(target=10), dict(target='-1'), dict(source_id=True), dict(enum_name='FireChappy')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                combat_profile({'p2_layout': {'bindings': [dict(good, **change)]}})
        with self.assertRaises(ValueError):
            combat_profile({'p2_layout': {'bindings': [good, good]}})

    def test_production_binding_policy(self):
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', Path(__file__).resolve().parents[1] / 'native'))
        compiler = shutil.which('g++')
        source = native / 'tools/test_p2_purple_combat_bindings.cpp'
        if not compiler or not source.exists():
            self.skipTest('Set PIKMIN_NATIVE_SOURCE and provide g++')
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'bindings.exe'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(native/'pc_port'), str(source), '-o', str(exe)], check=True, capture_output=True)
            subprocess.run([str(exe)], check=True, capture_output=True)
