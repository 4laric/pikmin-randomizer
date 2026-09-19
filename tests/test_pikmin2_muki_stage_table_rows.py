"""Focused tests for the pinned MUKI stage rows (#748). Hermetic except the
disc-gated live cross-check, which skips cleanly without the retail ISO."""
import importlib.util
import os
import unittest

_ISO = r'C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso'


def _load():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'experimental', 'pikmin2_muki_stage_table_rows.py')
    spec = importlib.util.spec_from_file_location('muki_rows', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()


class PinShapeTests(unittest.TestCase):
    def test_both_rows_present(self):
        self.assertEqual(set(M.PINNED), {'ch_MUKI_houdai', 'ch_MUKI_redblue'})

    def test_populations(self):
        self.assertEqual(M.PINNED['ch_MUKI_houdai']['population'], 50)
        self.assertEqual(M.PINNED['ch_MUKI_redblue']['population'], 50)
        self.assertEqual(M.population(M.PINNED['ch_MUKI_houdai']['roster']), 50)
        self.assertEqual(M.population(M.PINNED['ch_MUKI_redblue']['roster']), 50)

    def test_ui_and_floors(self):
        self.assertEqual(M.PINNED['ch_MUKI_houdai']['ui_index'], 8)
        self.assertEqual(M.PINNED['ch_MUKI_redblue']['ui_index'], 18)
        self.assertEqual(M.PINNED['ch_MUKI_houdai']['floors'], 2)
        self.assertEqual(M.PINNED['ch_MUKI_redblue']['floors'], 2)
        self.assertEqual(M.PINNED['ch_MUKI_houdai']['floor_seconds'], [100.0, 150.0])
        self.assertEqual(M.PINNED['ch_MUKI_redblue']['floor_seconds'], [200.0, 200.0])
        self.assertEqual(M.PINNED['ch_MUKI_houdai']['bitter_sprays'], 1)
        self.assertEqual(M.PINNED['ch_MUKI_redblue']['spicy_sprays'], 1)

    def test_lookup(self):
        self.assertEqual(M.lookup_ui(8), 'ch_MUKI_houdai')
        self.assertEqual(M.lookup_ui(18), 'ch_MUKI_redblue')
        self.assertIsNone(M.lookup_ui(29))
        self.assertIsNone(M.lookup_ui(-1))

    def test_markers(self):
        self.assertIn('P2_MUKI_STAGE_RESOLVED', M.MARKERS)
        self.assertIn('P2_MUKI_STAGE_TABLE_DONE', M.MARKERS)


class VerifyTests(unittest.TestCase):
    def _decoded(self, cave_id):
        row = dict(M.PINNED[cave_id])
        row['roster'] = [list(r) for r in row['roster']]
        return row

    def test_verify_pass(self):
        self.assertTrue(M.verify_row('ch_MUKI_houdai', self._decoded('ch_MUKI_houdai')))
        self.assertTrue(M.verify_row('ch_MUKI_redblue', self._decoded('ch_MUKI_redblue')))

    def test_verify_unknown_stage(self):
        with self.assertRaises(M.PinMismatch):
            M.verify_row('ch_MUKI_nope', {})

    def test_verify_divergences_fail_closed(self):
        for key, bad in (('ui_index', 9), ('floors', 1),
                         ('floor_seconds', [100.0, 100.0]),
                         ('bitter_sprays', 2), ('spicy_sprays', 0),
                         ('treasure_count_field', 1)):
            row = self._decoded('ch_MUKI_houdai')
            row[key] = bad
            with self.assertRaises(M.PinMismatch, msg=key):
                M.verify_row('ch_MUKI_houdai', row)
        row = self._decoded('ch_MUKI_redblue')
        row['roster'] = [[0, 0, 24], [0, 0, 25]] + [[0, 0, 0]] * 5
        with self.assertRaises(M.PinMismatch):
            M.verify_row('ch_MUKI_redblue', row)

    def test_verify_malformed(self):
        with self.assertRaises(M.PinMismatch):
            M.verify_row('ch_MUKI_houdai', None)
        with self.assertRaises(M.PinMismatch):
            M.verify_row('ch_MUKI_houdai', {'ui_index': 8})
        with self.assertRaises(M.PinMismatch):
            M.population([[1] * 3] * 6)
        with self.assertRaises(M.PinMismatch):
            M.population('nope')


class LiveDecodeTests(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(_ISO), 'retail ISO absent')
    def test_live_decode_matches_pins(self):
        # Decode through the shared #136 framework contract parser (read-only).
        import importlib.util as iu
        p = (r'C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards'
             r'\challenge-2\prepared\shard-challenge-2-contract-consumer-root\experimental'
             r'\pikmin2_challenge_framework_contract.py')
        spec = iu.spec_from_file_location('contract_live', p)
        contract = iu.module_from_spec(spec)
        spec.loader.exec_module(contract)
        raw = contract.read_stage_table(_ISO)[0]
        stages = contract.parse_stage_table(raw.decode('shift_jis'))
        by_id = {s.get('cave_id'): s for s in stages}
        for cave_id in ('ch_MUKI_houdai', 'ch_MUKI_redblue'):
            live = dict(by_id[cave_id])
            live['roster'] = [list(r) for r in live['roster']]
            self.assertTrue(M.verify_row(cave_id, live), cave_id)


if __name__ == '__main__':
    unittest.main()