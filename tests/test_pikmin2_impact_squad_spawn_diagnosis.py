"""Fail-closed tests for the impact squad-spawn stall classifier (#698)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from experimental import pikmin2_impact_squad_spawn_diagnosis as diag

STALL_LOG = (
    '[PC Port] DVDOpen("dataDir/stages/chal0/1.gen") -> FAILED to open assets/x\n'
    '[PC Generator] default: initialised 80 recognised generators, spawned 95 creatures\n'
    'P2_CHALLENGE_PARK nx=309.663 ny=0.000 nz=1505.612\n'
    '[PC Port] FPS: 29.6, DeltaTime: 20.0480ms\n'
    '[PC Port] Textures: 511 live, 60 MB\n'
)

HEALTHY_LOG = STALL_LOG + (
    'P2_CHALLENGE_SQUAD pikis=20\n'
    'P2_CHALLENGE_BOOT level=0 slot=chal0\n'
    'PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive\n'
)

REAL_RUN = Path('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/planning-shards'
                '/p1-challenge/prepared/p1-challenge-impact-runtime-output/acceptance/runs'
                '/540c84b9a7ff463593ef98e7f9093627/native.log')


class ClassifyTests(unittest.TestCase):
    def test_stall_signature(self):
        result = diag.classify_run(STALL_LOG)
        self.assertEqual(result['verdict'], 'stall-post-park')
        self.assertEqual(result['park_line'], 3)
        self.assertEqual(len(result['failed_reads']), 1)
        self.assertEqual(len(result['spawn_evidence']), 1)
        self.assertEqual(result['captain_signals'], [])
        self.assertTrue(result['engine_alive_after_park'])

    def test_progressed_boot(self):
        result = diag.classify_run(HEALTHY_LOG)
        self.assertEqual(result['verdict'], 'progressed')
        self.assertEqual(result['park_line'], 3)
        self.assertEqual(result['squad_line'], 6)
        self.assertEqual(result['boot_line'], 7)
        self.assertEqual(result['pass_line'], 8)

    def test_captain_interruption_wins(self):
        log = STALL_LOG + 'P2_FIXTURE_CAPTAIN_DOWN tick=5 hp=0.000 outcome=BLOCKED\n'
        result = diag.classify_run(log)
        self.assertEqual(result['verdict'], 'captain-interrupted')
        self.assertEqual(len(result['signals']), 1)

    def test_empty_and_missing_markers(self):
        self.assertEqual(diag.classify_run('')['verdict'], 'empty-log')
        self.assertEqual(diag.classify_run('   \n')['verdict'], 'empty-log')
        self.assertEqual(diag.classify_run('boot noise\n')['verdict'], 'no-park-marker')
        with self.assertRaises(ValueError):
            diag.classify_run(None)

    def test_failed_reads_extracted(self):
        lines = diag._lines(STALL_LOG)
        hits = diag.failed_reads(lines)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], 1)
        self.assertIn('FAILED', hits[0][1])
        win_hits = diag.failed_reads(diag._lines('open overlay failed WinError 267\n'))
        self.assertEqual(len(win_hits), 1)

    def test_last_marker_line(self):
        lines = diag._lines('a\nP2_CHALLENGE_PARK x\nb\nP2_CHALLENGE_PARK y\n')
        self.assertEqual(diag.last_marker_line(lines, 'P2_CHALLENGE_PARK'), 4)
        self.assertIsNone(diag.last_marker_line(lines, 'missing'))

    def test_engine_heartbeat(self):
        self.assertTrue(diag.engine_alive_after(diag._lines(STALL_LOG), 3))
        self.assertFalse(diag.engine_alive_after(diag._lines('P2_CHALLENGE_PARK x\n'), 1))


class RealEvidenceTests(unittest.TestCase):
    def test_real_run_classifies_stall(self):
        text = REAL_RUN.read_text(encoding='utf-8', errors='replace')
        result = diag.classify_run(text)
        self.assertEqual(result['verdict'], 'stall-post-park')
        self.assertEqual(result['park_line'], 797)
        self.assertEqual([line for line, _ in result['failed_reads']], [404, 405])
        self.assertTrue(result['engine_alive_after_park'])


class DeterminismTests(unittest.TestCase):
    def test_identical_shape_unanimous(self):
        report = diag.compare_runs([STALL_LOG, STALL_LOG])
        self.assertTrue(report['identical_shape'])
        self.assertTrue(report['unanimous_verdict'])
        self.assertEqual(report['verdicts'], ['stall-post-park'])

    def test_mixed_verdicts_detected(self):
        report = diag.compare_runs([STALL_LOG, HEALTHY_LOG])
        self.assertFalse(report['unanimous_verdict'])
        self.assertEqual(report['runs'], 2)


class CliTests(unittest.TestCase):
    def test_cli_classifies_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as handle:
            handle.write(STALL_LOG)
            path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, '-m',
                 'experimental.pikmin2_impact_squad_spawn_diagnosis',
                 '--log', path],
                capture_output=True, text=True, cwd='.')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['verdict'], 'stall-post-park')
        finally:
            Path(path).unlink()

    def test_cli_missing_file(self):
        proc = subprocess.run(
            [sys.executable, '-m',
             'experimental.pikmin2_impact_squad_spawn_diagnosis',
             '--log', 'does-not-exist.log'],
            capture_output=True, text=True, cwd='.')
        self.assertNotEqual(proc.returncode, 0)


if __name__ == '__main__':
    unittest.main()
