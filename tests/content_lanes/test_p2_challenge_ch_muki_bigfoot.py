"""Focused P0 tests for the ch_MUKI_bigfoot import contract; no disc, no runtime.

The adapter module has a hyphenated filename, so it is loaded by path
instead of a package import (same convention as sibling content lanes).
"""
import importlib.util
import sys
import unittest
from pathlib import Path

WORKTREE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKTREE))
ADAPTER = WORKTREE / "experimental" / "content_lanes" / "p2-challenge-ch_muki_bigfoot.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("bigfoot_adapter", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lane = load_adapter()


GOOD_STAGE = """\
{ { c000 } 4 1 { _eof } } 1
{ { f000 } 4 0 { f001 } 4 0 { _eof } }
{ 1 1 10 0 }
{ 1 2 5 }
{ 0 }
{ 0 }
"""


class ContractTests(unittest.TestCase):
    def test_pinned_identity(self):
        self.assertEqual(lane.CAVE_ID, 'ch_MUKI_bigfoot')
        self.assertEqual(lane.SOURCE_PATH, 'user/Mukki/mapunits/caveinfo/ch_MUKI_bigfoot.txt')
        self.assertEqual(lane.SOURCE_SHA256, '9d3efaf030587a94366bf2db7ed26aecfd93f37b806708061bd218440a2a782f')
        self.assertEqual((lane.FLOORS, lane.FLOOR_SECONDS, lane.UI_INDEX), (1, [200.0], 7))
        self.assertEqual((lane.SPICY_SPRAYS, lane.BITTER_SPRAYS), (2, 0))

    def test_missing_source_reports_exact_prerequisite(self):
        prereq = lane.missing_prerequisite()
        self.assertEqual(prereq['disc_path'], lane.SOURCE_PATH)
        self.assertEqual(prereq['expected_sha256'], lane.SOURCE_SHA256)
        with self.assertRaises(lane.MissingSource) as caught:
            lane.load_source('output/definitely-not-a-disc.txt')
        message = str(caught.exception)
        self.assertIn(lane.SOURCE_PATH, message)
        self.assertIn(lane.SOURCE_SHA256, message)

    def test_source_bytes_empty_and_mismatch_rejected(self):
        with self.assertRaises(lane.MalformedStage):
            lane.validate_source_bytes(b'')
        with self.assertRaisesRegex(lane.MalformedStage, 'Source hash differs'):
            lane.validate_source_bytes(b'invented stage bytes')

    def test_decode_minimal_stage_preserves_coverage_without_placements(self):
        record = lane.decode_stage(GOOD_STAGE)
        self.assertEqual(record['cave_id'], 'ch_MUKI_bigfoot')
        self.assertEqual(record['source_sha256'], lane.SOURCE_SHA256)
        self.assertEqual(len(record['floors']), 1)
        floor = record['floors'][0]
        self.assertEqual(floor['number'], 1)
        self.assertEqual(floor['enemy_definitions'], [dict(id='1', packed_weight=10, placement_type=0)])
        self.assertEqual(floor['treasure_definitions'], [dict(id='2', packed_weight=5)])
        blob = repr(record)
        for banned in ('position', 'coordinate', 'spawned', 'actor_count'):
            self.assertNotIn(banned, blob)

    def test_malformed_stages_rejected(self):
        for bad in ('', GOOD_STAGE.replace('{ _eof }', '', 1),
                    GOOD_STAGE.replace('} 1\n', '} 2\n', 1),
                    GOOD_STAGE.replace('{ f000 } 4 0', '{ f000 } 4 3'),
                    GOOD_STAGE.replace('{ 0 }\n{ 0 }', '{ 1 2 }\n{ 0 }'),
                    GOOD_STAGE.replace('{ 1 1 10 0 }', '{ 1 1 }')):
            with self.assertRaises(lane.MalformedStage, msg=repr(bad[:40])):
                lane.decode_stage(bad)

    def test_roster_totals_preserved(self):
        totals = lane.roster_totals()
        self.assertEqual(totals['rows'], [0, 25, 0, 0, 25, 0, 0])
        self.assertEqual(totals['total'], 50)
        with self.assertRaises(lane.MalformedStage):
            lane.roster_totals([[25, 0]])
        with self.assertRaises(lane.MalformedStage):
            lane.roster_totals([[0, 0, -1]] + [[0, 0, 0]] * 6)

    def test_resource_closure_names_blockers(self):
        closure = lane.resource_closure()
        self.assertEqual(closure['floors'], 1)
        self.assertEqual(closure['floor_seconds'], [200.0])
        self.assertEqual(closure['starting_roster_total'], 50)
        joined = ' '.join(closure['unsupported'])
        for token in ('#136', '#137', '#129', 'disc source unavailable'):
            self.assertIn(token, joined)

    def test_stage_contract_packet(self):
        contract = lane.stage_contract()
        self.assertEqual(contract['schema'], 1)
        self.assertEqual(contract['issue'], 539)
        self.assertEqual(contract['runtime_dependencies'], [136, 137, 129, 130, 131])
        self.assertTrue(all('playability' in limit or 'placements' in limit or 'undecodable' in limit
                            for limit in contract['limitations']))


if __name__ == '__main__':
    unittest.main()
