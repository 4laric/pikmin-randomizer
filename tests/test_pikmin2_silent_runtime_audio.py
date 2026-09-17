"""Synthetic silent-audio policy/checker tests; never launches audio or game code."""
import unittest

from experimental.pikmin2_silent_runtime_audio import (
    BACKGROUND_MARKER,
    SILENT_AUDIO_DRIVER,
    SILENT_POLICY_VERSION,
    PolicyRejected,
    classify_run_log,
    describe,
    silent_run_environ,
    validate_silent_environ,
)


def launch_log(extra='exit code 0'):
    return 'launch env SDL_AUDIODRIVER=dummy\nnative fixture running\n' + extra + '\n'


class EnvironTests(unittest.TestCase):
    def test_enforces_dummy_driver_without_mutating_base(self):
        base = {'PATH': 'x', 'SDL_AUDIODRIVER': 'wasapi'}
        env = silent_run_environ(base)
        self.assertEqual(env['SDL_AUDIODRIVER'], 'dummy')
        self.assertEqual(base['SDL_AUDIODRIVER'], 'wasapi')
        self.assertEqual(silent_run_environ()['SDL_AUDIODRIVER'], 'dummy')

    def test_malformed_base_fails_closed(self):
        for bad in ('SDL_AUDIODRIVER=dummy', ['SDL_AUDIODRIVER'], {'SDL_AUDIODRIVER': 1}, 42, b'x'):
            with self.subTest(base=repr(bad)), self.assertRaises(PolicyRejected):
                silent_run_environ(bad)

    def test_validate_accepts_exact_dummy_only(self):
        env = validate_silent_environ({'SDL_AUDIODRIVER': 'dummy', BACKGROUND_MARKER: '1'})
        self.assertEqual(env['SDL_AUDIODRIVER'], 'dummy')
        for bad in ({}, {'SDL_AUDIODRIVER': ''}, {'SDL_AUDIODRIVER': 'DUMMY'},
                    {'SDL_AUDIODRIVER': 'wasapi'}, 'dummy', None, {'SDL_AUDIODRIVER': None}):
            with self.subTest(env=repr(bad)), self.assertRaises(PolicyRejected):
                validate_silent_environ(bad)


class CheckerTests(unittest.TestCase):
    def test_silent_verified_needs_ack_end_and_clean(self):
        self.assertEqual(classify_run_log(launch_log()), 'silent-verified')

    def test_device_open_wins_over_silence_markers(self):
        for marker in ('WASAPI device opened', 'DirectSound init', 'SDL_OpenAudio failed',
                       'opened audio device 0', 'audio device open', 'dial tone audible',
                       'DIAL-TONE', 'continuous tone during run'):
            with self.subTest(marker=marker):
                self.assertEqual(classify_run_log(launch_log() + marker + '\n'), 'audio-device-open')

    def test_missing_ack_end_or_evidence_is_unknown(self):
        self.assertEqual(classify_run_log('native fixture running\nexit code 0\n'), 'unknown')
        self.assertEqual(classify_run_log('launch env SDL_AUDIODRIVER=dummy\nnative running\n'), 'unknown')
        self.assertEqual(classify_run_log('unrelated output\n'), 'unknown')

    def test_malformed_log_fails_closed(self):
        for bad in ('', '   ', None, 42, b'log', ['log']):
            with self.subTest(log=repr(bad)), self.assertRaises(PolicyRejected):
                classify_run_log(bad)

    def test_never_claims_fault_fixed(self):
        verdict = classify_run_log(launch_log())
        self.assertEqual(verdict, 'silent-verified')
        self.assertIn('NOT fixed', describe()['fault_note'])


class DescribeTests(unittest.TestCase):
    def test_policy_summary_shape(self):
        info = describe()
        self.assertEqual(info['policy_version'], SILENT_POLICY_VERSION)
        self.assertEqual(info['silent_audio_driver'], SILENT_AUDIO_DRIVER)
        self.assertEqual(info['background_marker'], BACKGROUND_MARKER)
        self.assertEqual(tuple(info['verdicts']), ('silent-verified', 'audio-device-open', 'unknown'))


if __name__ == '__main__':
    unittest.main()
