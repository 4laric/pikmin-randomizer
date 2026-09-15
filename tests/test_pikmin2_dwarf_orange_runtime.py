"""Unit tests for the lane-13 Dwarf Orange Bulborb runtime driver (#120, #186)."""
import json
import tempfile
import unittest
from pathlib import Path

import experimental.pikmin2_dwarf_orange_runtime as rt


GOOD_LOG = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 '
    'x=-150.0 y=30.0 z=1850.0 health=250.0 max_health=250.0 behavior=P1 '
    'purple_stun=bluekochappy_5s',
    'P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 texture_attach_calls=1 load_seconds=0.012',
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211001 x=-150.000 y=30.000 z=1850.000 health=250.0 '
    'fallback=130.0 red=1',
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211002 x=150.000 y=30.000 z=1550.000 health=130.0 '
    'fallback=130.0 red=0',
    'P2_DWARF_ORANGE_DRAW corpse=0',
    'P2_DWARF_ORANGE_DRAW corpse=1',
    'P2_DWARF_ORANGE_COMBAT tick=24 health=235.0000 state=11 target=1 x=-150.0 y=24.0 '
    'z=1850.0 corpses=0',
    'P2_DWARF_ORANGE_COMBAT tick=62 health=0.0000 state=1 target=1 x=-150.0 y=0.0 '
    'z=1850.0 corpses=1',
    'DONE P2_DWARF_ORANGE_COMBAT',
])


def drop(fragment):
    return '\n'.join(line for line in GOOD_LOG.splitlines() if fragment not in line)


class DwarfOrangeRuntimeTests(unittest.TestCase):
    def test_instrument_targets_the_blue_variant(self):
        source = 'class RoomApp : public PlugPikiApp {\n};\nint main(\n'
        fragment = ('#include "pc_p2_kochappy.h"\n'
                    'class RoomApp : public PlugPikiApp {\n};\nint main(\n')
        out = rt.instrument(fragment)
        self.assertIn('pc_p2_dwarf_orange.h', out)
        self.assertIn('P2_DWARF_ORANGE', out)
        self.assertNotIn('pc_p2_kochappy', out)
        self.assertNotIn('186001', out)
        self.assertNotIn('186002', out)
        self.assertIn('==250', out)
        self.assertNotIn('==200', out)
        # The transform must not leave a Red-dwarf health/bank behind.
        self.assertIn('dwarf-orange-arena-positions.txt', out)

    def test_identity_and_health_checks_pass(self):
        result = rt.evidence(GOOD_LOG, 0)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))
        self.assertEqual(result['metrics']['first_damage_tick'], 24.0)
        self.assertEqual(result['metrics']['zero_health_tick'], 62.0)
        self.assertEqual(result['metrics']['corpse_tick'], 62.0)
        self.assertIn(235.0, result['metrics']['health_samples'])
        self.assertIn(0.0, result['metrics']['health_samples'])

    def test_wrong_species_is_rejected(self):
        result = rt.evidence(drop('source_id=44'), 0)
        self.assertFalse(result['checks']['identity_ready'])
        self.assertFalse(result['passed'])

    def test_missing_corpse_render_is_rejected(self):
        result = rt.evidence(drop('corpse=1'), 0)
        self.assertFalse(result['checks']['corpse_render'])
        self.assertFalse(result['passed'])

    def test_extinction_and_bad_exit_are_rejected(self):
        result = rt.evidence(GOOD_LOG + '\nExtinction\n', 1)
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])

    def test_positions_reads_expected_xyz(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            (stage / 'arena.json').write_text(json.dumps({'actors': [
                {'generator': 211001, 'expected_xyz': [-150.0, 30.0, 1850.0]},
                {'generator': 211002, 'expected_xyz': [150.0, 30.0, 1550.0]},
            ]}))
            rt.positions(stage)
            text = (stage / rt.POSITIONS_FILE).read_text()
            self.assertEqual(text, '211001 -150.0 30.0 1850.0\n211002 150.0 30.0 1550.0\n')

    def test_positions_rejects_wrong_roster(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            (stage / 'arena.json').write_text(json.dumps({'actors': [
                {'generator': 211001, 'expected_xyz': [-150.0, 30.0, 1850.0]},
            ]}))
            with self.assertRaises(ValueError):
                rt.positions(stage)


if __name__ == '__main__':
    unittest.main()
