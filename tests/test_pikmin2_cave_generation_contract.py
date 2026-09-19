"""Unit tests for the read-only cave generation seam checker
(lane cave-generation-contract-review, issue #129).

Stdlib unittest only. Synthetic snippets exercise the probe; one live test
runs the probe against the real audited engine export in this worktree and
skips cleanly if the file is absent. Nothing here builds, runs, or admits.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    'cave_generation_contract',
    ROOT / 'experimental' / 'pikmin2_cave_generation_contract.py')
_CONTRACT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CONTRACT)

SEAM_PATH = ROOT / 'engine' / 'pc_port' / 'pc_p2_cave.cpp'

FULL_SNIPPET = (
    'void pc_p2_cave_setup() {\n'
    '  std::printf("P2_CAVE_RESTORE species=%d maturity=%d\\n", 1, 2);\n'
    '  std::printf("P2_CAVE_READY floor=%d survivors=%d\\n", 1, 3);\n'
    '  std::printf("P2_CAVE_TRANSFER floor=%d\\n", 1);\n'
    '  std::printf("P2_CAVE_ANCHOR kind=%s\\n", "hole");\n'
    '  std::printf("P2_CAVE_NAV seq=%u\\n", 7);\n'
    '  std::printf("P2_CAVE_VISUAL_READY kind=%s\\n", "hole");\n'
    '}\n'
    'void pc_p2_cave_tick() {}\n'
    'bool pc_p2_cave_checkpoint(bool confirm) { return true; }\n'
)


class ProbeTests(unittest.TestCase):
    def test_full_seam_reports_all_present(self):
        report = _CONTRACT.check_seam(FULL_SNIPPET)
        self.assertEqual(report['missing'], [])
        self.assertEqual(sorted(report['present']),
                         sorted(_CONTRACT.REQUIRED_MARKERS))

    def test_each_required_marker_stripped_flips(self):
        for marker in _CONTRACT.REQUIRED_MARKERS:
            stripped = '\n'.join(line for line in FULL_SNIPPET.splitlines()
                                 if marker not in line) + '\n'
            report = _CONTRACT.check_seam(stripped)
            self.assertIn(marker, report['missing'])
            self.assertNotIn(marker, report['present'])

    def test_malformed_input_fails_closed(self):
        for bad in (None, 42, '', b'P2_CAVE_READY'):
            with self.subTest(bad=repr(bad)[:20]):
                with self.assertRaises(ValueError):
                    _CONTRACT.check_seam(bad)
                with self.assertRaises(ValueError):
                    _CONTRACT.find_markers(bad)
                with self.assertRaises(ValueError):
                    _CONTRACT.entry_points(bad)

    def test_entry_points_follow_header_order(self):
        names = _CONTRACT.entry_points(FULL_SNIPPET)
        self.assertEqual(names, ['pc_p2_cave_setup', 'pc_p2_cave_tick',
                                 'pc_p2_cave_checkpoint'])
        self.assertEqual(names, sorted(names, key=_CONTRACT.ENTRY_POINTS.index))


class ContractShapeTests(unittest.TestCase):
    def test_gap_table_rows_complete(self):
        rows = _CONTRACT.gap_table()
        self.assertGreaterEqual(len(rows), 6)
        for row in rows:
            self.assertEqual(set(row), {'requirement', 'retail', 'port', 'work'})
            self.assertTrue(all(isinstance(v, str) and v.strip() for v in row.values()))
        self.assertTrue(any('P2_CAVE_TRANSFER' in r['port'] for r in rows))

    def test_review_draft_names_exact_files(self):
        draft = _CONTRACT.review_draft()
        for token in ('#186', 'pc_p2_cave.cpp:87', 'P2_CAVE_RESTORE',
                      'pc_p2_cave.h:4', 'pc_p2_cave_anchor.h:7',
                      'pc_p2_cave_entry_policy.h:4'):
            self.assertIn(token, draft)

    def test_live_audited_seam_surface(self):
        if not SEAM_PATH.is_file():
            self.skipTest('audited engine export absent from this worktree')
        report = _CONTRACT.check_seam(SEAM_PATH.read_text(encoding='utf-8'))
        self.assertEqual(report['missing'], [], report['missing'])
        names = _CONTRACT.entry_points(SEAM_PATH.read_text(encoding='utf-8'))
        for required in ('pc_p2_cave_setup', 'pc_p2_cave_tick',
                         'pc_p2_cave_checkpoint', 'pc_p2_cave_interact',
                         'pc_p2_cave_draw_transition'):
            self.assertIn(required, names)


if __name__ == '__main__':
    unittest.main()