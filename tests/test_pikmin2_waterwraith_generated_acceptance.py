"""Tests for the Waterwraith99 generated-acceptance consumer boundary (#572)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from experimental import pikmin2_waterwraith_generated_acceptance as ga

SLOT = '568677317'

# Contract-logic sample in the reviewed placement99 grammar (#575): accepted
# slot, placement generator, numeric register tie. No engine build can
# complete this triple yet (register logs no generator field); this
# exercises matcher logic only, never runtime evidence.
TRIPLE_LOG = (
    ':100 P2_SEED_RESOLVE source_id=99 target=568677317 original_type=15 x=10.0 z=20.0\n'
    ':101 P2_GENERATED_PLACEMENT source_id=99 target=568677317 generator=568677317 bound=1\n'
    ':102 P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98 generator=568677317\n'
)

# Exact historical fixed-encounter marker (l63 encounter-run-2 stdout.log:892):
# birth with no resolve/placement markers anywhere in its log.
FIXED_EXCERPT = 'P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98\n'

# Full fixed-encounter gate set (birth+profile+visual+chase leg) for the
# default fixture mode contract.
FIXED_FULL_EXCERPT = (
    'P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98\n'
    'P2_WATERWRAITH_REGISTER_PROFILE placement=1.0,2.0,3.0 yaw=0.5 species=2\n'
    'P2_WATERWRAITH_VISUAL_READY species=2\n'
    'P2_WATERWRAITH_STEER mode=chase motion=walk travel=2.5 escape=2\n'
)

FIXTURE_SRC = Path('C:/Users/alari/pikmin-randomizer/output/autofill-native-572'
                   '/tools/p2_muse_waterwraith_fixture.cpp')
GXX = shutil.which('g++')


def build_fixture(directory):
    directory = Path(directory)
    exe = directory / 'ww_fixture.exe'
    proc = subprocess.run(
        [GXX, '-std=c++17', '-Wall', '-Wextra', '-Werror',
         str(FIXTURE_SRC), '-o', str(exe)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError('fixture compile failed:\n' + proc.stderr[-2000:])
    return exe


def run_fixture(exe, log_text, *args):
    log = Path(exe).parent / 'sample.log'
    log.write_text(log_text, encoding='utf-8')
    proc = subprocess.run([str(exe), str(log), *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout


def generated_flag(output):
    match = re.search(r'generated_ok=([01])', output)
    return match.group(1) == '1' if match else None


class GeneratedAcceptanceTests(unittest.TestCase):
    def test_accepted_slot_is_reviewed(self):
        self.assertEqual(ga.ACCEPTED_SLOT, SLOT)

    def test_triple_correlation_passes(self):
        verdict, detail = ga.validate_generated_birth(TRIPLE_LOG)
        self.assertEqual(verdict, 'PASS')
        self.assertIn(SLOT, detail)
        self.assertIn('helper=98', detail)
        self.assertTrue(ga.is_generated_identity(TRIPLE_LOG))

    def test_register_generator_mismatch_fails(self):
        log = TRIPLE_LOG.replace('id=99 helper=98 generator=568677317',
                                 'id=99 helper=98 generator=777001')
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('disagreement', detail)

    def test_untied_register_birth_never_passes(self):
        log = (':100 P2_SEED_RESOLVE source_id=99 target=568677317 original_type=15 x=1.0 z=2.0\n'
               ':101 P2_GENERATED_PLACEMENT source_id=99 target=568677317 generator=568677317 bound=1\n'
               ':102 P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98\n')
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('not numeric', detail)
        self.assertFalse(ga.is_generated_identity(log))

    def test_slot_not_accepted_fails(self):
        log = TRIPLE_LOG.replace('568677317', '424242')
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('slot-not-accepted', detail)
        self.assertFalse(ga.is_generated_identity(log))

    def test_missing_placement_is_blocked_live_state(self):
        log = (':100 P2_SEED_RESOLVE source_id=99 target=568677317 original_type=15 x=1.0 z=2.0\n'
               ':102 P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98\n')
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('placement99', detail)
        self.assertFalse(ga.is_generated_identity(log))

    def test_fixed_encounter_birth_is_not_generated(self):
        self.assertTrue(ga.fixed_birth_present(FIXED_EXCERPT))
        verdict, detail = ga.validate_generated_birth(FIXED_EXCERPT)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('fixed-encounter', detail)
        self.assertFalse(ga.is_generated_identity(FIXED_EXCERPT))

    def test_missing_resolve_fails(self):
        log = ('P2_GENERATED_PLACEMENT source_id=99 target=568677317 generator=568677317 bound=1\n'
               'P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98 generator=568677317\n')
        verdict, _ = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')

    def test_missing_birth_fails(self):
        log = ('P2_SEED_RESOLVE source_id=99 target=568677317 original_type=15 x=1.0 z=2.0\n'
               'P2_GENERATED_PLACEMENT source_id=99 target=568677317 generator=568677317 bound=1\n')
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('register', detail)

    def test_bound_zero_refusal_fails(self):
        log = ('P2_SEED_RESOLVE source_id=99 target=568677317 original_type=15 x=1.0 z=2.0\n'
               'P2_GENERATED_PLACEMENT source_id=99 target=568677317 generator=568677317 bound=0 reason=slot-rejected\n')
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('bound=0', detail)

    def test_target_disagreement_fails(self):
        log = TRIPLE_LOG.replace('target=568677317 generator=568677317', 'target=111111 generator=111111')
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('disagreement', detail)

    def test_wrong_identity_rejected(self):
        self.assertFalse(ga.fixed_birth_present(
            'P2_WATERWRAITH_BIRTH phase=fall attached=1 id=98 helper=0\n'))
        verdict, _ = ga.validate_generated_birth(
            TRIPLE_LOG.replace('id=99 helper=98', 'id=98 helper=0'))
        self.assertEqual(verdict, 'FAIL')

    def test_injected_taint_fails(self):
        log = TRIPLE_LOG + 'P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98 generator=568677317 injected=1\n'
        verdict, detail = ga.validate_generated_birth(log)
        self.assertEqual(verdict, 'FAIL')
        self.assertIn('taint', detail.lower())
        self.assertFalse(ga.is_generated_identity(log))

    def test_empty_log_fails(self):
        verdict, _ = ga.validate_generated_birth('')
        self.assertEqual(verdict, 'FAIL')
        self.assertFalse(ga.is_generated_identity(''))
        self.assertFalse(ga.fixed_birth_present(''))


class CaptainSafetyScanTests(unittest.TestCase):
    def test_clean_log_has_no_hits(self):
        self.assertEqual(ga.captain_safety_scan(TRIPLE_LOG), [])
        self.assertEqual(ga.captain_safety_scan(FIXED_FULL_EXCERPT), [])
        self.assertEqual(ga.captain_safety_scan(''), [])

    def test_death_markers_flagged(self):
        log = (TRIPLE_LOG
               + ':900 P2_FIXTURE_CAPTAIN_DOWN orima=1 navi=0 hp=0.0\n')
        hits = ga.captain_safety_scan(log)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], 4)
        self.assertIn('CAPTAIN_DOWN', hits[0][1])

    def test_extinction_flagged(self):
        hits = ga.captain_safety_scan('squad status: extinction imminent\n')
        self.assertEqual(len(hits), 1)

    def test_benign_substrings_not_flagged(self):
        self.assertEqual(ga.captain_safety_scan(
            'DVDOpen headcount=20 readout ready\n'), [])


@unittest.skipUnless(GXX and FIXTURE_SRC.is_file(), 'needs g++ and the native fixture source')
class FixtureGeneratedModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        cls.exe = build_fixture(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_default_mode_contract_preserved(self):
        code, out = run_fixture(self.exe, FIXED_EXCERPT)
        self.assertEqual(code, 1)
        self.assertIn('gate1_ok=0', out)
        code, out = run_fixture(self.exe, FIXED_FULL_EXCERPT)
        self.assertEqual(code, 0, out)
        self.assertIn('gate1_ok=1', out)
        self.assertIn('gate2_ok=1', out)

    def test_generated_mode_passes_triple(self):
        code, out = run_fixture(self.exe, FIXED_FULL_EXCERPT + TRIPLE_LOG, '--generated')
        self.assertEqual(code, 0, out)
        self.assertIn('generated_ok=1', out)

    def test_generated_mode_blocks_fixed_only(self):
        code, out = run_fixture(self.exe, FIXED_FULL_EXCERPT, '--generated')
        self.assertEqual(code, 1, out)
        self.assertIn('generated_ok=0', out)

    def test_generated_mode_blocks_untied_register(self):
        log = FIXED_FULL_EXCERPT + (
            'P2_SEED_RESOLVE source_id=99 target=568677317 original_type=15 x=1.0 z=2.0\n'
            'P2_GENERATED_PLACEMENT source_id=99 target=568677317 generator=568677317 bound=1\n'
            'P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98\n')
        code, out = run_fixture(self.exe, log, '--generated')
        self.assertEqual(code, 1, out)
        self.assertIn('generated_ok=0', out)

    def test_generated_mode_blocks_wrong_slot(self):
        log = TRIPLE_LOG.replace('568677317', '424242')
        code, out = run_fixture(self.exe, log, '--generated')
        self.assertEqual(code, 1, out)
        self.assertIn('generated_ok=0', out)

    def test_observers_agree(self):
        for log, expected in ((TRIPLE_LOG, True), (FIXED_EXCERPT, False),
                              (FIXED_FULL_EXCERPT, False)):
            _, out = run_fixture(self.exe, log, '--generated')
            self.assertEqual(ga.is_generated_identity(log), expected)
            self.assertEqual(generated_flag(out), expected)


if __name__ == '__main__':
    unittest.main()
