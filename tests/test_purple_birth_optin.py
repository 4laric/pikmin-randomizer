import argparse
import unittest

from scripts import purple_birth_ledger as ledger
from scripts import run_pikmin2_purple_sdl as driver


class OptInControls(unittest.TestCase):
    def test_invalid_optin_refused_before_input_or_launch(self):
        for optin, mode, profile in ((1, 'sdl_save_resume', 'ordinary-off'),
                                     (True, 'sdl_acquire', 'ordinary-off'),
                                     (True, 'sdl_save_resume', 'unknown')):
            with self.subTest(optin=optin, mode=mode), self.assertRaises(ValueError):
                driver.preflight(argparse.Namespace(birth_ledger=optin, mode=mode, profile=profile))

    def test_explicit_flag_default_and_prepare_only(self):
        flags = ['--' + key for key in ('root', 'assets', 'bank', 'motion', 'content', 'exe', 'session',
                  'root-pin', 'native-pin', 'overlay-sha256', 'platform-sha256', 'exe-sha256', 'native-source-sha256')]
        args = [value for flag in flags for value in (flag, 'placeholder')]
        args += ['--mode', 'sdl_save_resume', '--profile', 'ordinary-off', '--preflight-only']
        self.assertFalse(driver.parser().parse_args(args).birth_ledger)
        selected = driver.parser().parse_args(args + ['--birth-ledger'])
        self.assertTrue(selected.birth_ledger)
        self.assertTrue(selected.preflight_only)

    def test_fresh_day_stock_observer_refuses_wrong_or_incomplete_rows(self):
        stock = dict(rgb=[0, 0, 0, 21, 0, 0, 0, 0, 0], p2=[1, 0, 0, 0, 0, 0], day=5)
        rows = [f'P2_PURPLE_RESUME_STOCK kind={kind} color={color} maturity={m} count={counts[index*3+m]} read_only=1'
                for kind, counts, colors in (('rgb', stock['rgb'], range(3)), ('p2', stock['p2'], range(3, 5)))
                for index, color in enumerate(colors) for m in range(3)]
        end = 'P2_PURPLE_RESUME_STOCK_OBSERVED day=5 generations=1 checkpoint_resumed=1 field=0 heads=0 starting_population_validated=0 external_card_comparison_required=1 saved_bytes_injected=0'
        self.assertFalse(ledger.compare_stock_observation('\n'.join(rows + [end]), stock)['starting_population_validated'])
        for bad in (rows[:-1] + [end], rows + [rows[0], end], rows + [end.replace('day=5', 'day=3')],
                    rows + [end, rows[0]], rows + [end, 'P2_PURPLE_ORDINARY_RESUME_PASS']):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ledger.compare_stock_observation('\n'.join(bad), stock)


if __name__ == '__main__':
    unittest.main()
