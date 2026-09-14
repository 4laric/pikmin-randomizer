"""Unit tests for the lane-13 mixed Dwarf Orange + Snow Bulborb probe."""
import json
import tempfile
import unittest
from pathlib import Path

import experimental.pikmin2_mixed_bulborb_runtime as rt


TICK = ('[PC tick] last 120 ticks, budget 16.7 ms (ms, except the gl: rows marked as counts)\n'
        '           update           mean     0.08  p50     0.01  p95     0.01  p99     0.03  worst    10.66\n'
        '           tick             mean    12.09  p50     9.01  p95    19.79  p99    21.28  worst   119.31\n')

GOOD_LOG = '\n'.join([
    '[PC Port] Experimental preview window set to 960x540 windowed and centered',
    'P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=5001 behavior=P1',
    'P2_SNOW_POLICY generator=5001 health=150.0 max_health=150.0 previous=130.0 '
    'source=YellowKochappy_fp00',
    'P2_SNOW_BANK poses=60 mod_bytes=960000 texture_attach_calls=1 load_seconds=0.200 '
    'load_budget_seconds=5 budget_exceeded=0',
    'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 '
    'x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0 behavior=P1 '
    'purple_stun=bluekochappy_5s',
    'P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 texture_attach_calls=1 load_seconds=0.012',
    'P2_MIXED_ARENA_BIRTH id=211001 x=-150.000 y=30.000 z=1850.000 health=250.0 '
    'fallback=130.0 display=Dwarf Orange Bulborb',
    'P2_MIXED_ARENA_BIRTH id=211002 x=150.000 y=30.000 z=1550.000 health=130.0 '
    'fallback=130.0 display=-',
    'P2_MIXED_ARENA_BIRTH id=5001 x=-150.000 y=30.000 z=1700.000 health=150.0 '
    'fallback=130.0 display=Snow Bulborb',
    'P2_MIXED_ARENA_SPAWN teki=3 reds=20',
    'P2_MIXED_SNOW_DISPLAY name=Snow Bulborb generator=5001 source_marker=P2_ENEMY_READY '
    'species=YellowKochappy',
    'P2_MIXED_STIMULUS tick=1 target=dwarf',
    'P2_DWARF_ORANGE_DRAW corpse=0',
    'P2_SNOW_DRAW corpse=0',
    TICK,
    'PASS P2 mixed Dwarf Orange + Snow Bulborb observation',
])


def drop(fragment):
    return '\n'.join(line for line in GOOD_LOG.splitlines() if fragment not in line)


class MixedBulborbInstrumentTests(unittest.TestCase):
    def test_instrument_tolerates_three_teki(self):
        source = 'class RoomApp : public PlugPikiApp {\n};\nint main(\n'
        out = rt.instrument(source)
        self.assertIn('P2_MIXED_ARENA_SPAWN', out)
        self.assertIn('expected==3', out)
        self.assertIn('live==3', out)
        self.assertIn('"Snow Bulborb"', out)
        self.assertIn('pc_p2_enemy.h', out)
        # The hardcoded two-actor roster must not survive.
        self.assertNotIn('expected==2 && count==2', out)
        for identity in ('211001', '211002', '5001'):
            self.assertIn(identity, out)

    def test_instrument_refuses_double_patch(self):
        source = ('class RoomApp : public PlugPikiApp {\nP2_MIXED_ARENA_SPAWN\n};\n'
                  'int main(\n')
        with self.assertRaises(ValueError):
            rt.instrument(source)


class MixedBulborbEvidenceTests(unittest.TestCase):
    def test_all_gates_pass(self):
        result = rt.evidence(GOOD_LOG, 0)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))
        self.assertEqual(result['tick']['mean_tick_ms'], 12.09)
        self.assertEqual(result['tick']['last_tick_p95_ms'], 19.79)
        self.assertEqual(len(result['rows']), 3)

    def test_missing_snow_draw_rejected(self):
        result = rt.evidence(drop('P2_SNOW_DRAW'), 0)
        self.assertFalse(result['checks']['snow_draw'])
        self.assertFalse(result['passed'])

    def test_missing_dwarf_draw_rejected(self):
        result = rt.evidence(drop('P2_DWARF_ORANGE_DRAW'), 0)
        self.assertFalse(result['checks']['dwarf_draw'])
        self.assertFalse(result['passed'])

    def test_wrong_dwarf_identity_rejected(self):
        self.assertFalse(rt.evidence(drop('source_id=44'), 0)['passed'])
        self.assertFalse(rt.evidence(drop('species=BlueKochappy'), 0)['passed'])

    def test_snow_requires_policy_and_bank(self):
        self.assertFalse(rt.evidence(drop('P2_SNOW_POLICY'), 0)['checks']['snow_policy'])
        self.assertFalse(rt.evidence(drop('P2_SNOW_BANK'), 0)['checks']['snow_bank'])
        self.assertFalse(rt.evidence(drop('P2_MIXED_SNOW_DISPLAY'), 0)['checks']['snow_display'])

    def test_non_three_roster_rejected(self):
        result = rt.evidence(GOOD_LOG.replace('teki=3 reds=20', 'teki=2 reds=20'), 0)
        self.assertFalse(result['checks']['spawn_three'])
        self.assertFalse(result['passed'])

    def test_extinction_and_bad_exit_rejected(self):
        self.assertFalse(rt.evidence(GOOD_LOG + '\nExtinction\n', 0)['checks']['no_extinction'])
        self.assertFalse(rt.evidence(GOOD_LOG, 1)['passed'])

    def test_missing_tick_is_unmeasured(self):
        stripped = '\n'.join(line for line in GOOD_LOG.splitlines()
                             if not line.startswith('[PC tick]') and 'tick  ' not in line)
        result = rt.evidence(stripped, 0)
        self.assertIsNone(result['tick']['mean_tick_ms'])
        self.assertFalse(result['checks']['tick_measured'])


class MixedBulborbTickTests(unittest.TestCase):
    def test_no_windows(self):
        stats = rt.tick_stats('nothing here\n')
        self.assertEqual(stats['windows'], 0)
        self.assertIsNone(stats['mean_tick_ms'])

    def test_mean_across_windows(self):
        log = TICK + TICK.replace('12.09', '20.00').replace('19.79', '30.00')
        stats = rt.tick_stats(log)
        self.assertEqual(stats['windows'], 2)
        self.assertAlmostEqual(stats['mean_tick_ms'], (12.09 + 20.00) / 2)
        self.assertEqual(stats['last_tick_ms'], 20.00)


class MixedBulborbArenaTests(unittest.TestCase):
    def test_snow_row_is_a_distinct_chappy(self):
        import struct
        template = bytearray(b'\0' * 96)
        template[72:76] = b'iket'
        template[80] = 3
        row = rt.snow_row(bytes(template), 5001, 'Snow Bulborb', (-150.0, 30.0, 1700.0))
        self.assertEqual(struct.unpack_from('<I', row, 8)[0], 5001)
        self.assertEqual(row[16:48].rstrip(b'\0'), b'Snow Bulborb')
        self.assertEqual(struct.unpack_from('>3f', row, 48), (-150.0, 30.0, 1700.0))
        self.assertEqual(row[72:76], b'iket')

    def test_snow_row_rejects_non_chappy_template(self):
        template = bytearray(b'\0' * 96)
        template[72:76] = b'ikip'
        template[80] = 0
        with self.assertRaises(ValueError):
            rt.snow_row(bytes(template), 5001, 'Snow Bulborb', (0.0, 0.0, 0.0))

    def test_positions_writes_three_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            (stage / rt.MANIFEST).write_text(json.dumps({'actors': [
                {'generator': 211001, 'expected_xyz': [-150.0, 30.0, 1850.0]},
                {'generator': 211002, 'expected_xyz': [150.0, 30.0, 1550.0]},
                {'generator': 5001, 'expected_xyz': [-150.0, 30.0, 1700.0]},
            ]}))
            rt.positions(stage)
            self.assertEqual((stage / rt.POSITIONS_FILE).read_text(),
                             '211001 -150.0 30.0 1850.0\n'
                             '211002 150.0 30.0 1550.0\n'
                             '5001 -150.0 30.0 1700.0\n')

    def test_positions_rejects_wrong_roster(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            (stage / rt.MANIFEST).write_text(json.dumps({'actors': [
                {'generator': 211001, 'expected_xyz': [-150.0, 30.0, 1850.0]},
            ]}))
            with self.assertRaises(ValueError):
                rt.positions(stage)


if __name__ == '__main__':
    unittest.main()
