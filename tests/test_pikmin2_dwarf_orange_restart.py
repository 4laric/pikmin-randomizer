"""Unit tests for the lane-13 Dwarf Orange process-restart gate-F driver (#120)."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import experimental.pikmin2_dwarf_orange_restart as restart

READY = ('P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy '
         'generator=211001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 '
         'max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s')
BANK = 'P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 texture_attach_calls=1 load_seconds=0.005'
BIRTH1 = ('P2_DWARF_ORANGE_ARENA_BIRTH id=211001 x=-150.000 y=30.000 z=1850.000 '
          'health=250.0 fallback=130.0 red=1')
BIRTH2 = ('P2_DWARF_ORANGE_ARENA_BIRTH id=211002 x=150.000 y=30.000 z=1550.000 '
          'health=130.0 fallback=130.0 red=0')


def good_log(bank=BANK):
    return '\n'.join([
        'Experimental preview window set to 960x540 windowed and centered',
        READY, bank, BIRTH1, BIRTH2,
        'P2_DWARF_ORANGE_DRAW corpse=1',
        'P2_DWARF_ORANGE_COMBAT tick=24 health=235.0000 state=11 target=1 corpses=0',
        'DONE P2_DWARF_ORANGE_COMBAT',
    ])


class MarkerTests(unittest.TestCase):
    def test_markers_partition_by_prefix_and_id(self):
        found = restart.markers(good_log())
        self.assertEqual(found['enemy_ready'], [READY])
        self.assertEqual(found['bank'], [BANK])
        self.assertEqual(set(found['births']), {211001, 211002})
        self.assertEqual(found['births'][211002], BIRTH2)

    def test_identical_logs_compare_equal(self):
        result = restart.compare(restart.markers(good_log()), restart.markers(good_log()))
        self.assertTrue(result['identical'])
        for key in ('enemy_ready', 'bank', 'birth_211001', 'birth_211002'):
            self.assertTrue(result[key]['identical'], key)

    def test_volatile_bank_timing_is_ignored(self):
        other = good_log(bank=BANK.replace('load_seconds=0.005', 'load_seconds=0.412'))
        result = restart.compare(restart.markers(good_log()), restart.markers(other))
        self.assertTrue(result['bank']['identical'])
        self.assertTrue(result['identical'])

    def test_changed_health_is_a_difference(self):
        other = good_log() + '\n' + BIRTH1.replace('health=250.0', 'health=200.0')
        result = restart.compare(restart.markers(good_log()), restart.markers(other))
        self.assertFalse(result['birth_211001']['identical'])
        self.assertFalse(result['identical'])

    def test_changed_xyz_is_a_difference(self):
        other = good_log().replace('z=1550.000', 'z=1500.000')
        result = restart.compare(restart.markers(good_log()), restart.markers(other))
        self.assertFalse(result['birth_211002']['identical'])
        self.assertFalse(result['identical'])

    def test_missing_birth_is_a_difference(self):
        other = '\n'.join(line for line in good_log().splitlines() if 'id=211002' not in line)
        result = restart.compare(restart.markers(good_log()), restart.markers(other))
        self.assertFalse(result['birth_211002']['identical'])
        self.assertFalse(result['identical'])


class ContentTests(unittest.TestCase):
    def test_content_checks_pass_for_the_slice(self):
        checks = restart.content_checks(restart.markers(good_log()))
        self.assertTrue(all(checks.values()), checks)

    def test_wrong_species_is_rejected(self):
        checks = restart.content_checks(restart.markers(good_log().replace('BlueKochappy', 'Red')))
        self.assertFalse(checks['enemy_identity'])
        self.assertTrue(checks['enemy_health'])

    def test_wrong_source_health_is_rejected(self):
        log = good_log().replace('source_id=44', 'source_id=45')
        self.assertFalse(restart.content_checks(restart.markers(log))['enemy_identity'])

    def test_wrong_bank_pose_count_is_rejected(self):
        checks = restart.content_checks(restart.markers(
            good_log(bank=BANK.replace('poses=64', 'poses=32'))))
        self.assertFalse(checks['bank_poses'])

    def test_control_birth_must_keep_source_health(self):
        log = good_log().replace('id=211002 x=150.000 y=30.000 z=1550.000 health=130.0',
                                 'id=211002 x=150.000 y=30.000 z=1550.000 health=250.0')
        self.assertFalse(restart.content_checks(restart.markers(log))['birth_control'])

    def test_evaluate_passes_then_fails_on_restart_drift(self):
        passed = restart.evaluate(good_log(), 0, good_log(), 0)
        self.assertTrue(passed['passed'])
        drifted = restart.evaluate(good_log(), 0, good_log().replace('health=250.0', 'health=200.0'), 0)
        self.assertFalse(drifted['passed'])
        self.assertFalse(drifted['identical'])

    def test_evaluate_rejects_nonzero_exit(self):
        self.assertFalse(restart.evaluate(good_log(), 1, good_log(), 0)['passed'])


class SaveStateTests(unittest.TestCase):
    def test_save_delta_reports_added_changed_removed(self):
        self.assertFalse(restart.save_delta({'a': '1'}, {'a': '1'})['any'])
        delta = restart.save_delta({'a': '1', 'b': '2'}, {'a': '3', 'c': '4'})
        self.assertEqual(delta['added'], ['c'])
        self.assertEqual(delta['removed'], ['b'])
        self.assertEqual(delta['changed'], ['a'])
        self.assertTrue(delta['any'])

    def test_snapshot_and_session_dirs_read_save_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'save' / 'bbft_sessions' / 's1' / 'card0').mkdir(parents=True)
            (root / 'save' / 'bbft_sessions' / 's1' / 'card0' / 'state.sav').write_bytes(b'x')
            self.assertEqual(restart.snapshot(root), {'save/bbft_sessions/s1/card0/state.sav':
                                                      hashlib.sha256(b'x').hexdigest()})
            self.assertEqual(restart.session_dirs(root), ['s1'])


class IsolationTests(unittest.TestCase):
    def test_copy_arena_leaves_the_source_intact(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            source.mkdir()
            (source / 'arena.json').write_text('{"actors": []}')
            dest = restart.copy_arena(source, Path(temp) / 'copy')
            self.assertTrue((dest / 'arena.json').is_file())
            self.assertTrue((source / 'arena.json').is_file())

    def test_copy_arena_refuses_overlapping_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            source.mkdir()
            with self.assertRaises(ValueError):
                restart.copy_arena(source, source)
            with self.assertRaises(ValueError):
                restart.copy_arena(source, source / 'nested')

    def test_serialized_lock_excludes_a_second_run(self):
        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / 'gl.lock'
            with restart.serialized(lock):
                with self.assertRaises(restart.SessionBusy):
                    with restart.serialized(lock):
                        pass
            self.assertFalse(lock.exists())

    def test_only_two_runs_are_permitted(self):
        self.assertEqual(restart.MAX_RUNS, 2)

    def test_runtime_path_is_prepended_once(self):
        with tempfile.TemporaryDirectory() as temp:
            before = restart.os.environ.get('PATH', '')
            try:
                restart.ensure_runtime_path(temp)
                restart.ensure_runtime_path(temp)
                parts = restart.os.environ['PATH'].split(restart.os.pathsep)
                self.assertEqual(parts.count(temp), 1)
                self.assertEqual(parts[0], temp)
            finally:
                restart.os.environ['PATH'] = before


if __name__ == '__main__':
    unittest.main()
