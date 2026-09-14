"""Tests for the BigTreasure lane conversion glue (#246).

Synthetic parse-level checks always run; the disc-dependent encode check
skips when the local import directory is absent (no assets are committed).
"""
import tempfile
import unittest
from pathlib import Path

from experimental import pikmin2_bigtreasure_assets as assets
from experimental import pikmin2_bigtreasure_motion as motion

IMPORT_DIR = Path('output/bigtreasure-import-01')


def registry_text(slot_events):
    """Build a synthetic 30-slot enemyanimmgr.txt in retail format."""
    lines = ['\t30 \t# number of animations']
    for name, events in zip(assets.ANIM_SLOTS, slot_events):
        lines.append('{')
        lines.append(f'\teditor/path/{name}.bca')
        lines.append(f'\t{name}.bca')
        lines.extend(f'\t{frame} {kind}' for frame, kind in events)
        lines.append('\t-1')
        lines.append('}')
    return '\n'.join(lines) + '\n'


def pellet_block(name, **overrides):
    fields = {'name': name, 'archive': f'{name}.szs', 'bmd': f'elements_{name}.bmd', 'radius': '35',
              'p_radius': '25', 'height': '50', 'inertiascaling': '350',
              'particletype': 'simple', 'numparticles': '8', 'particlesize': '1',
              'friction': '0.1', 'min': '30', 'max': '40', 'pikicountmax': '0',
              'pikicountmin': '0', 'dynamics': 'lod', 'money': '1000',
              'unique': 'yes', 'code': '0', 'dictionary': '197', 'depth': '0',
              'depth_max': '50', 'depth_a': '10', 'depth_b': '35', 'depth_c': '35',
              'depth_d': '35'}
    fields.update({key: str(value) for key, value in overrides.items()})
    rows = ''.join(f'\t{key}\t{value}\n' for key, value in fields.items())
    return '{\n' + rows + '\tend\n}\n'


class RegistryValidationTest(unittest.TestCase):
    def test_valid_registry_with_divergent_wait2_duplicate(self):
        events = {name: list(rows) for name, rows in assets.EXPECTED_EVENTS.items()}
        slot_events = [events[name] for name in assets.ANIM_SLOTS]
        slot_events[29] = []  # source-legitimate: second wait2 has no events
        from experimental.pikmin2_engine_parms import parse_anim_mgr
        rows = parse_anim_mgr(registry_text(slot_events))['clips']
        seen, slots = assets.validate_registry(rows)
        self.assertEqual(seen['wait2'], [[0, 0], [29, 1]])
        self.assertEqual(slots[29], [])
        self.assertEqual(seen['dead'][-1], [320, 100])

    def test_registry_rejects_wrong_slot_count_and_event_drift(self):
        from experimental.pikmin2_engine_parms import parse_anim_mgr
        events = {name: list(rows) for name, rows in assets.EXPECTED_EVENTS.items()}
        slot_events = [events[name] for name in assets.ANIM_SLOTS]
        slot_events[29] = []
        drifted = [list(rows) for rows in slot_events]
        drifted[0] = [[0, 0]]
        rows = parse_anim_mgr(registry_text(drifted))['clips']
        with self.assertRaises(ValueError):
            assets.validate_registry(rows)


class PelletConfigTest(unittest.TestCase):
    def config_text(self, **overrides):
        blocks = []
        specs = {'elec': {}, 'fire': {'dictionary': '198', 'height': '52'},
                 'gas': {'dictionary': '199', 'radius': '37', 'height': '20'},
                 'water': {'dictionary': '200', 'height': '51'},
                 'loozy': {'bmd': 'otakara_loozy.bmd', 'min': '1', 'max': '5', 'money': '10',
                           'dictionary': '201', 'radius': '12', 'height': '10'}}
        for name, spec in specs.items():
            spec.update(overrides.get(name, {}))
            blocks.append(pellet_block(name, **spec))
        return '\n'.join(blocks)

    def test_valid_configs(self):
        from experimental.pikmin2_engine_parms import parse_otakara_config
        configs = parse_otakara_config(self.config_text(), tuple(assets.PELLETS))
        result = assets.validate_pellet_config(configs)
        self.assertEqual(result['elec']['money'], 1000)
        self.assertEqual(result['loozy']['dictionary'], 201)
        self.assertEqual(result['loozy']['min'], 1)

    def test_config_drift_rejected(self):
        from experimental.pikmin2_engine_parms import parse_otakara_config
        configs = parse_otakara_config(self.config_text(elec={'money': '500'}),
                                       tuple(assets.PELLETS))
        with self.assertRaises(ValueError):
            assets.validate_pellet_config(configs)


class MotionTableTest(unittest.TestCase):
    def test_missing_directory_rejected(self):
        with self.assertRaises((ValueError, OSError)):
            motion.encode('nonexistent-bigtreasure-dir')

    @unittest.skipUnless((IMPORT_DIR / 'BigTreasure' / 'enemyanimmgr.txt').is_file(),
                         'local import directory absent')
    def test_encode_matches_vendored_reader_contract(self):
        data = motion.encode(IMPORT_DIR / 'BigTreasure', IMPORT_DIR / 'bigtreasure.json')
        text = data.decode('ascii')
        lines = text.splitlines()
        magic, _registry_sha, count = lines[0].split()
        self.assertEqual(magic, 'P2_RETAIL_EVENTS_1')
        self.assertEqual(int(count), 29)
        self.assertEqual(len([l for l in lines[1:] if l.endswith('.bca') or ' .bca ' in l]), 0)
        clip_lines = [l for l in lines[1:] if l.split()[0].endswith('.bca')]
        self.assertEqual(len(clip_lines), 29)
        dead = next(l for l in clip_lines if l.startswith('dead.bca'))
        self.assertEqual(int(dead.split()[4]), 11)  # authored events incl. (320, 100)
        self.assertIn('320 100', lines)
        # wait2 appears exactly once (first, loop-carrying registration).
        self.assertEqual(sum(1 for l in clip_lines if l.startswith('wait2.bca')), 1)


if __name__ == '__main__':
    unittest.main()
