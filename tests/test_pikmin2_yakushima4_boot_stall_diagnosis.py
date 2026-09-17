"""Fail-closed tests for the yakushima4 boot-stall classifier (#671)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from experimental import pikmin2_yakushima4_boot_stall_diagnosis as diag

SILENT_LOG = (
    'P2_CAVE_GUARDED_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1\n'
    '[PC Port] OpenGL context: 3.3.0\n'
    '[PC Port] Texture filtering: anisotropy available (max 16x), mipmaps available\n'
    '[jaudio] NextOS DSP, SDL2 S16 stereo 32000 Hz\n'
)

ENTRY_LOG = SILENT_LOG + (
    'memStat: piki : 0.00 kbytes\n'
    'GameFlow: free : 207 files took 0.2 secs\n'
    'Invalid P2 cave entry: spawn count differs from checkpoint\n'
)

CRASH_LOG = (
    'P2_CAVE_GUARDED_WINDOW size=960x540 centered=1\n'
    'Thread 1 received signal SIGSEGV, Segmentation fault.\n'
    '0x00007ff604390c54 in Font::setTexture(Texture*, int, int) [clone .constprop.0] ()\n'
)

HEALTHY_LOG = SILENT_LOG + (
    'P2_CAVE_READY floor=1 survivors=20 health=1\n'
    'P2_CAVE_GENERATE_PASS rooms=8 spawns=10 links=36\n'
    'PASS CAVE_GUARDED_BOOT\n'
)

GOOD_ASSET = {'member': 'user/Mukki/mapunits/caveinfo/yakushima_4.txt',
              'offset': 770715532, 'size': 5977,
              'sha256': '4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8'}


class ClassifyTests(unittest.TestCase):
    def test_silent_stall_bracket(self):
        result = diag.classify_boot_log(SILENT_LOG)
        self.assertEqual(result['verdict'], 'silent-stall-post-audio')
        bracket = result['bracket']
        self.assertEqual(bracket['audio_tail_line'], 4)
        self.assertIsNone(bracket['first_dvd_read_after_audio'])
        self.assertIsNone(bracket['memstat_line'])
        self.assertIsNone(bracket['cave_ready_line'])
        self.assertEqual(result['failed_reads'], [])

    def test_dvd_burst_after_audio_is_not_silent(self):
        log = SILENT_LOG + 'DVDOpen("dataDir/SndData/Seqs/pikiseq.arc") -> OK, size = 219392\n'
        result = diag.classify_boot_log(log)
        self.assertEqual(result['verdict'], 'silent-stall-post-audio')
        self.assertEqual(result['bracket']['first_dvd_read_after_audio'], 5)

    def test_entry_refusal_detail(self):
        result = diag.classify_boot_log(ENTRY_LOG)
        self.assertEqual(result['verdict'], 'entry-refused')
        self.assertEqual(result['refusal']['reason'], 'spawn count differs from checkpoint')
        self.assertEqual(result['refusal']['line'], 7)

    def test_crash_signature(self):
        result = diag.classify_boot_log(CRASH_LOG)
        self.assertEqual(result['verdict'], 'crash-font-segfault')

    def test_progressed_boot(self):
        result = diag.classify_boot_log(HEALTHY_LOG)
        self.assertEqual(result['verdict'], 'progressed')
        self.assertTrue(result['ready'] and result['generate'] and result['passed'])

    def test_no_markers_and_empty(self):
        self.assertEqual(diag.classify_boot_log('some random text\n')['verdict'],
                         'no-boot-markers')
        self.assertEqual(diag.classify_boot_log('')['verdict'], 'no-boot-markers')
        with self.assertRaises(ValueError):
            diag.classify_boot_log(None)

    def test_failed_reads_extracted(self):
        log = (SILENT_LOG
               + 'DVDOpen("dataDir/x.arc") -> FAILED to open /assets/x.arc\n')
        hits = diag.failed_reads(diag._lines(log))
        self.assertEqual(len(hits), 1)
        self.assertIn('FAILED', hits[0][1])
        win_log = 'open overlay failed WinError 267\n'
        self.assertEqual(len(diag.failed_reads(diag._lines(win_log))), 1)

    def test_last_marker_line(self):
        lines = diag._lines('a\nP2_CAVE_READY x\nb\nP2_CAVE_READY y\n')
        self.assertEqual(diag.last_marker_line(lines, 'P2_CAVE_READY'), 4)
        self.assertIsNone(diag.last_marker_line(lines, 'missing'))

    def test_entry_refusal_absent(self):
        self.assertIsNone(diag.entry_refusal_detail(diag._lines(SILENT_LOG)))


class AssetRecordTests(unittest.TestCase):
    def test_good_record(self):
        self.assertTrue(diag.check_asset_record(dict(GOOD_ASSET)))

    def test_malformed_records_fail(self):
        bad = dict(GOOD_ASSET)
        for field in ('member', 'offset', 'size', 'sha256'):
            broken = dict(bad)
            del broken[field]
            with self.assertRaises(ValueError):
                diag.check_asset_record(broken)
        for sha in ('xyz', '0' * 63, '', None):
            with self.assertRaises(ValueError):
                diag.check_asset_record(dict(bad, sha256=sha))
        for field in ('offset', 'size'):
            with self.assertRaises(ValueError):
                diag.check_asset_record(dict(bad, **{field: -1}))
        with self.assertRaises(ValueError):
            diag.check_asset_record('not-a-mapping')

    def test_real_asset_inputs_pin_shape(self):
        data = json.loads(Path(
            'C:/Users/alari/pikmin-randomizer/output/workflow/asset-inputs.json'
        ).read_text(encoding='utf-8'))
        members = [m for m in data.get('verified_members', [])
                   if m.get('member', '').endswith('yakushima_4.txt')]
        self.assertEqual(len(members), 1)
        self.assertTrue(diag.check_asset_record(members[0]))
        self.assertEqual(members[0]['offset'], 770715532)
        self.assertEqual(members[0]['size'], 5977)


class CliTests(unittest.TestCase):
    def test_cli_classifies_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as handle:
            handle.write(SILENT_LOG)
            path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, '-m',
                 'experimental.pikmin2_yakushima4_boot_stall_diagnosis',
                 '--log', path],
                capture_output=True, text=True, cwd='.')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['verdict'],
                             'silent-stall-post-audio')
        finally:
            Path(path).unlink()

    def test_cli_missing_file(self):
        proc = subprocess.run(
            [sys.executable, '-m',
             'experimental.pikmin2_yakushima4_boot_stall_diagnosis',
             '--log', 'does-not-exist.log'],
            capture_output=True, text=True, cwd='.')
        self.assertNotEqual(proc.returncode, 0)


if __name__ == '__main__':
    unittest.main()
