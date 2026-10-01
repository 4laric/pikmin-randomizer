"""Focused tests for the Chappy siblings pin audit (#810)."""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load():
    path = os.path.join(_HERE, '..', 'experimental',
                        'pikmin2_chappy_siblings_audit.py')
    spec = importlib.util.spec_from_file_location('siblings_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()


def _canonical():
    cur = os.path.abspath(os.path.join(_HERE, '..'))
    for _ in range(12):
        if os.path.isdir(os.path.join(cur, 'native')) and os.path.isdir(os.path.join(cur, 'output')):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


ROOT = _canonical()
RESEARCH = os.path.join(ROOT, 'native', 'pikmin2-research') if ROOT else None
NATIVE = os.path.join(ROOT, 'native') if ROOT else None


class ShapeTests(unittest.TestCase):
    def test_siblings(self):
        self.assertEqual(set(M.SIBLINGS), {45, 53})
        self.assertEqual(M.SIBLINGS[45]['key'], 'YellowKochappy')
        self.assertEqual(M.SIBLINGS[53]['key'], 'KingChappy')

    def test_first_slices(self):
        for key in ('YellowKochappy', 'KingChappy'):
            self.assertIn('callsite', M.FIRST_SLICES[key])
            self.assertIn('build_membership', M.FIRST_SLICES[key])
            self.assertTrue(M.FIRST_SLICES[key]['build_membership'])

    def test_destination_pins(self):
        self.assertRegex(M.DESTINATION_PINS['root'], r'^[0-9a-f]{40}$')
        self.assertRegex(M.DESTINATION_PINS['native'], r'^[0-9a-f]{40}$')


class MalformedTests(unittest.TestCase):
    def test_missing_research(self):
        with self.assertRaises(ValueError):
            M.verify_research(os.path.join(_HERE, 'no-such-research'))

    def test_missing_port(self):
        with self.assertRaises(ValueError):
            M.inventory_port(os.path.join(_HERE, 'no-such-native'))

    def test_missing_owner_tree(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                M._read(tmp, 'missing.cpp')


class LivePinTests(unittest.TestCase):
    def test_research_identity(self):
        if RESEARCH is None or not os.path.isdir(RESEARCH):
            self.skipTest('research checkout absent')
        found = M.verify_research(RESEARCH)
        self.assertEqual(found['enum_ids']['YellowKochappy'], 45)
        self.assertEqual(found['enum_ids']['KingChappy'], 53)
        self.assertIn('YellowKochappy', found['enemyinfo_rows'])
        self.assertIn('KingChappy', found['enemyinfo_rows'])

    def test_port_inventory(self):
        if NATIVE is None or not os.path.isdir(os.path.join(NATIVE, 'pc_port')):
            self.skipTest('native port absent')
        inv = M.inventory_port(NATIVE)
        self.assertTrue(inv['family_base_present'])
        self.assertFalse(inv['dedicated_yellow_module'])
        self.assertFalse(inv['dedicated_king_module'])

    def test_producer_verdicts(self):
        if NATIVE is None or not os.path.isdir(os.path.join(NATIVE, 'pc_port')):
            self.skipTest('native port absent')
        producers = M.resolve_producer(NATIVE)
        for key in ('YellowKochappy', 'KingChappy'):
            self.assertIsNone(producers[key]['producer'])
            self.assertIn('missing', producers[key]['blocker'])
            self.assertEqual(producers[key]['provider_shard'], 'actor-birth-projectiles')

    def test_registry_shape(self):
        if RESEARCH is None or NATIVE is None:
            self.skipTest('reference trees absent')
        if not (os.path.isdir(RESEARCH) and os.path.isdir(os.path.join(NATIVE, 'pc_port'))):
            self.skipTest('reference trees absent')
        packet = M.audit(RESEARCH, NATIVE)
        self.assertEqual(packet['schema'], M.SCHEMA)
        self.assertEqual(set(packet['producers']), {'YellowKochappy', 'KingChappy'})
        self.assertIn('first_slices', packet)
        self.assertIn('destination_pins', packet)


if __name__ == '__main__':
    unittest.main()
