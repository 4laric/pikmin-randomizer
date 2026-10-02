import importlib.util
from pathlib import Path
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('purple_sdl_budget', Path(__file__).parents[1] / 'scripts/run_pikmin2_purple_sdl.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def evidence(acquisition='59.000000', save='59.000000', whole='118.000000'):
    return ('P2_PURPLE_SAVE_BUDGET_TRANSITION acquisition_seconds=' + acquisition +
        ' acquisition_limit=60 save_limit=60 whole_limit=120 verified_acquisition=1 monotonic=1\n'
        'P2_PURPLE_SDL_ACQUISITION_PASS field=20\nP2_PURPLE_ORDINARY_SAVE_BEGIN day=2\n'
        'P2_PURPLE_SAVE_BUDGET_FINISHED acquisition_seconds=' + acquisition + ' save_seconds=' + save +
        ' whole_seconds=' + whole + ' acquisition_limit=60 save_limit=60 whole_limit=120 monotonic=1 movie_skip=0\n'
        'P2_PURPLE_ORDINARY_SAVE_PASS day=3\n')


class PurpleSaveBudgetTests(unittest.TestCase):
    def test_valid_late_acquisition_has_separate_save_budget(self):
        self.assertEqual(driver.save_budget_observations(evidence())['whole_seconds'], 118)

    def test_late_acquisition_not_waived_by_whole_limit(self):
        with self.assertRaises(ValueError): driver.save_budget_observations(evidence('60', '30', '90'))

    def test_post_acquisition_deadline(self):
        with self.assertRaises(ValueError): driver.save_budget_observations(evidence('40', '60', '100'))

    def test_missing_or_duplicate_transition(self):
        for log in (evidence().split('\n', 1)[1], evidence().split('\n')[0] + '\n' + evidence()):
            with self.assertRaises(ValueError): driver.save_budget_observations(log)

    def test_unverified_or_skip_or_wrong_limits(self):
        for old, new in [('verified_acquisition=1', 'verified_acquisition=0'), ('movie_skip=0', 'movie_skip=1'),
                         ('save_limit=60', 'save_limit=90'), ('monotonic=1', 'monotonic=0')]:
            with self.assertRaises(ValueError): driver.save_budget_observations(evidence().replace(old, new))

    def test_nonfinite_negative_or_unclosed_time(self):
        for args in [('nan','20','50'), ('30','inf','50'), ('30','-1','29'), ('30','20','49'), ('30','20','120')]:
            with self.assertRaises(ValueError): driver.save_budget_observations(evidence(*args))

    def test_acquisition_time_cannot_reset(self):
        log = evidence().replace('FINISHED acquisition_seconds=59.000000', 'FINISHED acquisition_seconds=58.000000')
        with self.assertRaises(ValueError): driver.save_budget_observations(log)

    def test_acquisition_marker_must_precede_save_start(self):
        lines=evidence().splitlines();lines[1],lines[2]=lines[2],lines[1]
        with self.assertRaises(ValueError): driver.save_budget_observations('\n'.join(lines))

    def test_fresh_resume_remains_original60(self):
        result={'passed':True,'exit_code':0,'timed_out':False,'pid':123,'owned_process_group':123,
                'timeout_seconds':120,'elapsed_seconds':70}
        with self.assertRaises(ValueError):
            driver.native_success(result, 'P2_FIXTURE_WINDOW width=960 height=540', True, [])
        driver.native_success(result, 'P2_FIXTURE_WINDOW width=960 height=540', True, [], timeout_seconds=120)

    def test_actual_dispatch_uses_120_save_and_60_resume(self):
        for mode, timeout in [('sdl_dayend', 120), ('natural_resume', 60)]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                directory=Path(tmp);(directory/'native.log').write_text('observed log')
                exe=directory/'exe';exe.write_bytes(b'test executable')
                run=SimpleNamespace(directory=directory, bootstrap=directory/'seed', handshaken=True,
                    poll=Mock(), write_state=Mock())
                a=SimpleNamespace(exe=exe, exe_sha256=driver.digest(exe), root=directory,
                    session=directory, development_launch=True)
                launch=Mock(return_value={'passed':True})
                with patch.object(driver,'inventory',return_value={}), \
                     patch.object(driver,'save_observations',return_value={'validated':True}), \
                     patch.object(driver,'resume_observations',return_value={'validated':True}):
                    result=driver.launch_save_phase(a, {'run_pikmin2_fixture':SimpleNamespace(launch=launch)},
                        run, {'assets':{},'immutable_files':{}}, mode)
                self.assertTrue(result['passed'], result)
                self.assertEqual(launch.call_args.args[4], timeout)
                self.assertEqual(result['timeout_seconds'], timeout)


if __name__ == '__main__': unittest.main()
