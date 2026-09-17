"""Focused fail-closed tests for the rover reconciliation checker (#699)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental.pikmin2_rover_spawn_count_reconciliation import (
    parse_entry, parse_log, reconcile)


def entry_text(count=60, pairs=60):
    lines = ["P2_CAVE_ENTRY_1 %s 1 1.0 %d" % ("0" * 32, count)]
    lines += ["0 2"] * pairs
    return chr(10).join(lines) + chr(10)


def run10_log():
    return chr(10).join([
        '[PC Port] DVDOpen("dataDir/stages/chal0/default.gen") -> OK, size = 14665',
        '[PC Generator] default: initialised 80 recognised generators, spawned 93 creatures',
        'Invalid P2 cave entry: spawn count differs from checkpoint'])


def run11_log():
    return chr(10).join([
        'Experimental preview window set to 960x540 windowed and centered',
        '[PC Port] FPS: 30.0',
        '[Pikipelago] P2_ROOM_READY treasure=bolt carry=5 repairs=1'])


def healthy_log(count=60):
    lines = ['CHALLENGE_LAYOUT_READY id=rover',
             'P2_CAVE_READY floor=1 survivors=%d health=1' % count,
             'P2_CAVE_GENERATE_PASS rooms=1']
    lines += ['P2_CAVE_RESTORE species=0 maturity=2'] * count
    return chr(10).join(lines)


class ReconcileTests(unittest.TestCase):
    def test_run10_shape_is_staging_path(self):
        verdict = reconcile(entry_text(), run10_log(), staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "staging-path")
        self.assertEqual(verdict["entry"]["count"], 60)
        self.assertTrue(verdict["log"]["abort_spawn_mismatch"])
        self.assertEqual(verdict["log"]["opened_gen_sizes"], [14665])

    def test_run11_shape_is_entry_missing(self):
        verdict = reconcile(None, run11_log(), staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "entry-missing")
        self.assertTrue(verdict["log"]["room_ready"])
        self.assertEqual(verdict["log"]["restores"], 0)

    def test_healthy_run_is_consistent(self):
        verdict = reconcile(entry_text(), healthy_log(), staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "consistent")

    def test_same_gen_abort_is_count_or_timing(self):
        log = run10_log().replace("size = 14665", "size = 23913")
        verdict = reconcile(entry_text(), log, staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "count-or-timing")

    def test_malformed_entry_refused(self):
        verdict = reconcile("garbage" + chr(10), run10_log(), staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "refused:malformed-entry")

    def test_pair_count_mismatch_refused(self):
        verdict = reconcile(entry_text(count=60, pairs=59), run10_log(), staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "refused:malformed-entry")

    def test_captain_down_blocked(self):
        verdict = reconcile(entry_text(), run10_log() + "P2_FIXTURE_CAPTAIN_DOWN" + chr(10),
                            staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "blocked")

    def test_injected_refused(self):
        verdict = reconcile(entry_text(), run10_log() + "mHealth=0" + chr(10),
                            staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "refused:injected")

    def test_incomplete_boot_unobserved(self):
        verdict = reconcile(entry_text(), "[PC Port] FPS: 30.0" + chr(10), staged_gen_size=23913)
        self.assertEqual(verdict["verdict"], "incomplete")

    def test_parse_entry_fields(self):
        entry = parse_entry(entry_text())
        self.assertFalse(entry["malformed"])
        self.assertEqual((entry["count"], entry["pairs"]), (60, 60))

    def test_parse_log_counts(self):
        log = parse_log(healthy_log(count=60))
        self.assertEqual((log["restores"], log["fps"]), (60, 0))
        self.assertTrue(log["cave_ready"])


if __name__ == "__main__":
    unittest.main()
