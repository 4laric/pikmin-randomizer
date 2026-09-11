import copy
import unittest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch
from collections import Counter
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.spawn_data import ADULT_SLOTS, GENERATOR_SLOTS
from randomizer.enemy_slots import resolve_spawn_layout, verify_source_assets
from randomizer.catalog import BESTIARY_TARGETS, bestiary_sources


class EnemySlotTests(unittest.TestCase):
    def test_asset_mismatch_and_unmodeled_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            path = base / 'dataDir/stages/stage1/init.gen'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'audited fixture')
            with patch('randomizer.enemy_slots.SOURCE_FILES', {'stage1/init.gen': hashlib.sha256(path.read_bytes()).hexdigest()}):
                verify_source_assets(base)
                extra = path.with_name('1.gen'); extra.write_bytes(b'extra')
                with self.assertRaisesRegex(ValueError, 'unrecognized campaign generator'): verify_source_assets(base)
                extra.unlink()
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'does not match'): verify_source_assets(base)
                path.unlink()
                with self.assertRaisesRegex(ValueError, 'does not match'): verify_source_assets(base)

    def test_layout_counts_and_persistent_coverage(self):
        self.assertEqual(len({r[0] for r in GENERATOR_SLOTS}), 690)
        layouts = set()
        for seed in range(200):
            layout = resolve_spawn_layout(seed, 'Player1')
            self.assertEqual(layout, resolve_spawn_layout(seed, 'Player1'))
            actual = [r['actual'] for r in layout['assignments']]
            self.assertEqual(Counter(actual), {4: 9, 32: 6})
            layouts.add(tuple(actual))
            for stage in (1, 3):
                self.assertEqual({actual[i] for i, r in enumerate(ADULT_SLOTS) if r['stage'] == stage
                                  and r['first_day'] == 2 and 0 < r['respawn_days'] <= 5
                                  and (r['expires_after_day'] is None or r['expires_after_day'] >= 29)}, {4, 32})
        self.assertGreater(len(layouts), 100)

    def test_all_checks_and_start_matrix(self):
        for area in ('impact', 'forest', 'navel', 'spring', 'trial'):
            for color in ('red', 'yellow', 'blue'):
                m = generate('slots-' + area + color, per_spawn_enemies=True, enemy_shuffle=True,
                             starting_area=area, starting_color=color, starting_flarlic=1,
                             randomize_color_stats=True, progressive_color_stats=True, permanent_checks=True)
                self.assertEqual(m['enemy_mask'], 0)
                self.assertEqual(sum(map(len, spheres(solo_rewards(m), m))), len(m['locations']))
                for name in BESTIARY_TARGETS:
                    self.assertTrue(bestiary_sources(name, m), name)

    def test_tampering_and_legacy(self):
        m = generate('slots', per_spawn_enemies=True)
        for mutation in (lambda x: x['spawn_layout']['assignments'].reverse(),
                         lambda x: x['spawn_layout'].update(catalog_hash='bad'),
                         lambda x: x['enemy_layout']['sources'].pop(),
                         lambda x: x.update(enemy_mask=1)):
            changed = copy.deepcopy(m); mutation(changed)
            with self.assertRaises(ValueError): validate(changed)
        self.assertNotIn('spawn_layout', generate('legacy', enemy_shuffle=True))
        with self.assertRaises(ValueError): generate('old', legacy_checks=True, per_spawn_enemies=True)
