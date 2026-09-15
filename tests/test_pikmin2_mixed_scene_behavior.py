"""Unit tests for the P2 mixed-scene harness (#165/#166/#167).

Synthetic-log tests exercise ``validate`` with no native build or GL. The
``prepare`` smoke test stages the real cross-family run directory from local
assets/imports but never launches the executable, so it needs no GL slot.
"""
import json
import struct
import unittest
from pathlib import Path

from experimental.pikmin2_mixed_scene_behavior import (
    CONTROL_ACTOR, EXPECTED_BINDS, EXPECTED_SPECIES, FAMILIES, PROPOSED_BUDGETS,
    WINDOW, _assess, prepare, validate)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(r'C:\Users\alari\pikmin-local\game\assets')
IMPORTED = ROOT / 'output/p2-lane-verify'

_BANK2_BYTES = 1838080
_BANK3_BYTES = 3045536


def _binds():
    batch2 = [(2, a['generator'], f"ground|{a['species']}") for a in FAMILIES[0]['actors']]
    batch3 = [(3, a['generator'], f"{f['name']}|{a['species']}")
              for f in FAMILIES[1:] for a in f['actors']]
    return batch2 + batch3


def good_log():
    lines = ['[Pikipelago] P2_PREVIEW_HEAP previous=0 map_vertices=0 movie_range=0..0',
             'Experimental preview window set to 960x540 windowed and centered']
    for batch, generator, key in _binds():
        lines.append(f'P2_BATCH{batch}_BIND generator={generator} key={key} '
                     f'visual_only=0 native_fsm=implemented')
    for species in EXPECTED_SPECIES:
        lines.append(f'P2_ENEMY_READY species={species} native_family=Chappy generator=1 '
                     f'x=0.0 y=30.0 z=1850.0 health=10.0 max_health=10.0 behavior=native '
                     f'source_FSM=implemented')
    lines += [
        f'P2_BATCH2_BANK total_mod_bytes={_BANK2_BYTES} species=6',
        f'P2_BATCH3_BANK total_mod_bytes={_BANK3_BYTES} species=6',
        '[PERF] 60.0 fps 16.67 ms | 200 draws (150 source, 50 fast) 1000 verts '
        '4000 DL (1.50 MiB) 3.00 tex uploads/frame',
        '[PERF] 59.5 fps 16.81 ms | 210 draws (160 source, 50 fast) 1000 verts '
        '4000 DL (1.50 MiB) 3.00 tex uploads/frame',
        '[PC Port] Textures: 100 live, 12 MB (peak 15 MB), 50 made / 5 freed',
        '[PC tick] last 120 ticks, budget 16.67 ms',
        ' update          mean  1.00 p50  1.00 p95  2.00 p99  3.00 worst  4.00',
        ' tick            mean  1.00 p50  1.00 p95  2.00 p99  3.00 worst  4.00',
    ]
    return '\n'.join(lines)


class MixedSceneValidateTests(unittest.TestCase):
    def test_expected_bind_contract(self):
        self.assertEqual(len(EXPECTED_BINDS), 12)
        self.assertEqual(len(set(EXPECTED_BINDS)), 12)
        self.assertEqual(len(EXPECTED_SPECIES), 12)
        self.assertEqual(EXPECTED_BINDS[0], 'ground|Armor')
        self.assertIn('flying|Mar', EXPECTED_BINDS)
        self.assertIn('aquatic|UmiMushi', EXPECTED_BINDS)
        self.assertEqual(CONTROL_ACTOR['species'], 'P1 Chappy')

    def test_actor_tables_match_source_arena_modules(self):
        ground, flying, aquatic = FAMILIES
        self.assertEqual([a['species'] for a in ground['actors']],
                         ['Armor', 'ElecBug', 'Imomushi', 'TamagoMushi', 'Sokkuri', 'Hana'])
        self.assertEqual([a['species'] for a in flying['actors']],
                         ['Mar', 'Hanachirashi'])
        self.assertEqual([a['species'] for a in aquatic['actors']],
                         ['Catfish', 'Tadpole', 'Jigumo', 'UmiMushi'])
        self.assertEqual([a['native_teki_type'] for a in ground['actors']],
                         [3, 3, 3, 3, 3, 3])
        self.assertEqual([a['native_teki_type'] for a in flying['actors']], [16, 16])
        self.assertEqual([a['native_teki_type'] for a in aquatic['actors']], [30, 25, 3, 3])

    def test_validate_passes_on_synthetic_mixed_log(self):
        result = validate(good_log())
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(all(result['checks'].values()))
        self.assertEqual(result['missing_binds'], [])
        self.assertEqual(result['unexpected_binds'], [])
        self.assertEqual(result['batch2_bank']['total_mod_bytes'], _BANK2_BYTES)
        self.assertEqual(result['batch3_bank']['total_mod_bytes'], _BANK3_BYTES)
        self.assertEqual(result['total_pose_bank_bytes'], _BANK2_BYTES + _BANK3_BYTES)
        self.assertIsNotNone(result['frame_time'])
        self.assertGreater(result['frame_time']['mean_frame_ms'], 0)
        self.assertIsNotNone(result['texture_memory'])
        self.assertTrue(result['budget_assessment']['total_pose_bank_bytes']['within'])

    def test_missing_family_bind_fails(self):
        stale = good_log().replace(
            'P2_BATCH2_BIND generator=346006 key=ground|Hana visual_only=0 '
            'native_fsm=implemented\n', '')
        result = validate(stale)
        self.assertFalse(result['passed'])
        self.assertEqual(result['missing_binds'], ['ground|Hana'])

    def test_missing_batch3_bank_fails(self):
        stale = good_log().replace(
            f'P2_BATCH3_BANK total_mod_bytes={_BANK3_BYTES} species=6\n', '')
        result = validate(stale)
        self.assertFalse(result['checks']['bank'])
        self.assertFalse(result['passed'])
        self.assertIsNone(result['batch3_bank'])

    def test_validate_flags_extinction(self):
        result = validate(good_log() + '\nGAMEEND_PikminExtinction')
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')

    def test_budget_assessment_flags_over_budget(self):
        over = _assess(100 * 1024 * 1024,
                       {'mean_frame_ms': 100.0, 'slowest_window_mean_ms': 120.0},
                       {'maximum_reported_mib': 256})
        self.assertFalse(over['total_pose_bank_bytes']['within'])
        self.assertFalse(over['mean_frame_ms']['within'])
        self.assertFalse(over['tracked_texture_peak_mib']['within'])
        self.assertEqual(over['status'], PROPOSED_BUDGETS['status'])


def _prereqs_present():
    if not ASSETS.is_dir():
        return False
    for family, manifest in (('ground', 'ground_inverts.json'),
                             ('flying', 'flying.json'),
                             ('aquatic', 'aquatic.json')):
        if not (IMPORTED / family / manifest).is_file():
            return False
    return True


@unittest.skipUnless(_prereqs_present(), 'local P2 assets/imports unavailable')
class MixedScenePrepareSmokeTests(unittest.TestCase):
    def test_prepare_stages_all_three_families_without_gl(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare(ASSETS, IMPORTED, Path(tmp))
            scene = json.loads((run / 'mixed-scene.json').read_text())
            self.assertEqual(scene['actor_count'], 13)
            self.assertEqual(scene['species_count'], 12)
            self.assertEqual(scene['window'], WINDOW)
            self.assertEqual(set(scene['families']), {'ground', 'flying', 'aquatic'})
            for name, family in scene['families'].items():
                self.assertEqual(family['receipt_visuals'], 'installed')
                self.assertTrue(family['pose_files'] > 0)
            self.assertEqual(scene['families']['ground']['pose_bytes'], 1838080)
            self.assertEqual(scene['families']['ground']['native_setup'], 'pc_p2_batch2_setup')
            self.assertEqual(scene['families']['flying']['native_setup'], 'pc_p2_batch3_setup')
            self.assertEqual(set(scene['install_verified']), {'ground', 'flying', 'aquatic'})
            # The Sokkuri appear1 pose is the only misindexed name in the staged bank.
            self.assertEqual(len(scene['pose_name_normalization']['ground']), 1)
            for bank in ('p2-ground-bank.txt', 'p2-flying-bank.txt', 'p2-aquatic-bank.txt'):
                self.assertTrue((run / bank).is_file())
            gen = (run / 'assets/dataDir/stages/chal0/default.gen').read_bytes()
            self.assertGreater(struct.unpack_from('>I', gen, 20)[0], 13)


if __name__ == '__main__':
    unittest.main()
