import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('purple_sdl_metadata', Path(__file__).parents[1] / 'scripts/run_pikmin2_purple_sdl.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

# Exact acceptance lines from actual Purple11. This is a parser regression
# control, not a replacement for the retained native/card gameplay evidence.
SAVE = '''P2_FIXTURE_WINDOW width=960 height=540 x=160 y=90
P2_PURPLE_SDL_START field=20 red=20 scripted_throw=0 direct_throw_api=0 actor_state_writes=0 starting_withdrawal_fixture=1
P2_VIOLET_WITNESS sequence=1 generator=1347768321 input=red
P2_VIOLET_CONVERT count=1
P2_PURPLE_SAVE_BUDGET_TRANSITION acquisition_seconds=48.038190 acquisition_limit=60 save_limit=60 whole_limit=120 verified_acquisition=1 monotonic=1
P2_PURPLE_SDL_ACQUISITION_PASS scripted_throw=0 direct_throw_api=0 actor_state_writes=0 native_throw_state_observed=1 SDL_pluck=1 field=20 red=19 purple=1 selection=4 strength=10
P2_PURPLE_PERSIST_BINDING uid=3640055869 source=2 registered=1
P2_PURPLE_PERSIST_CATALOG uid=3640055869 source=2 profile_enabled=1 live_registered=1 live_required=1 stage=1
P2_PURPLE_ORDINARY_SAVE_BEGIN day=2 expected_day=3 maturity=0 field=20 stock=0 direct_stock_helpers=0 clock_advanced=0 SDL_menu_input=1
[Pikmin Randomizer] CAMPAIGN_SAVED generation=1
P2_PURPLE_SAVE_BUDGET_FINISHED acquisition_seconds=48.038190 save_seconds=46.266670 whole_seconds=94.304860 acquisition_limit=60 save_limit=60 whole_limit=120 monotonic=1 movie_skip=0
P2_PURPLE_ORDINARY_SAVE_PASS day_before=2 day=3 maturity=0 stock=1 generations=1 direct_stock_helpers=0 clock_advanced=0 external_checkpoint_validation_required=1
'''
RESUME = '''P2_FIXTURE_WINDOW width=960 height=540
P2_PURPLE_PERSIST_CATALOG uid=3640055869 source=2 profile_enabled=1 live_registered=0 live_required=0 stage=0
P2_PURPLE_ORDINARY_RESUME_PASS day=3 maturity=0 stock=1 native_population=20 generations=1 checkpoint_resumed=1 direct_stock_helpers=0 withdrawal_ui_validated=0 saved_bytes_injected=0
'''


def result(timeout=120):
    return dict(passed=True, exit_code=0, timed_out=False, captain_down=False,
                timeout_seconds=timeout, elapsed_seconds=94.372 if timeout == 120 else 5,
                pid=940500, owned_process_group=940500)


class PurpleSaveMetadataTests(unittest.TestCase):
    def test_actual_save_acceptance_lines_with_readonly_metadata(self):
        data = driver.save_observations(result(), SAVE, True, [])
        self.assertEqual((data['day'], data['maturity']), (3, 0))

    def test_fresh_resume_accepts_absent_stage_catalog_metadata(self):
        self.assertEqual(driver.resume_observations(result(60), RESUME, True, [],
                         {'day': 3, 'maturity': 0})['stock'], '1')

    def test_all_legacy_and_unknown_routes_still_refused_in_both_phases(self):
        for marker in ('PERSIST_BEGIN', 'PERSIST_PROGRESS', 'PERSIST_SAVED', 'PERSIST_RESUME_PASS',
                       'PERSIST_NEW_ROUTE', 'PERSIST_BINDING_SCRIPTED', 'PERSIST_CATALOG_SCRIPTED',
                       'SCRIPTED_THROW', 'SCRIPTED_THROW_NEW'):
            for phase in ('save', 'resume'):
                with self.subTest(marker=marker, phase=phase), self.assertRaises(ValueError):
                    extra = '\nP2_PURPLE_' + marker + ' clock_advanced=1\n'
                    if phase == 'save': driver.save_observations(result(), SAVE + extra, True, [])
                    else: driver.resume_observations(result(60), RESUME + extra, True, [], {'day': 3, 'maturity': 0})

    def test_diagnostics_without_token_separator_are_not_whitelisted(self):
        for marker in ('PERSIST', 'PERSIST_BINDING', 'PERSIST_CATALOG', 'PERSIST_BINDING\tuid=1'):
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                driver.reject_legacy_routes('P2_PURPLE_' + marker)

    def test_readonly_metadata_cannot_substitute_for_native_commit(self):
        with self.assertRaises(ValueError):
            driver.save_observations(result(), SAVE.replace('[Pikmin Randomizer] CAMPAIGN_SAVED generation=1\n', ''), True, [])

    def test_readonly_metadata_cannot_waive_stock_or_clock_shortcut(self):
        for old, new in (('clock_advanced=0', 'clock_advanced=1'), ('direct_stock_helpers=0', 'direct_stock_helpers=1')):
            with self.subTest(old=old), self.assertRaises(ValueError):
                driver.save_observations(result(), SAVE.replace(old, new), True, [])

    def test_resume_still_refuses_reacquisition_and_new_commit(self):
        for extra in ('P2_PURPLE_SDL_ACQUISITION_PASS', 'P2_VIOLET_WITNESS', 'CAMPAIGN_SAVED'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                driver.resume_observations(result(60), RESUME + extra, True, [], {'day': 3, 'maturity': 0})


if __name__ == '__main__': unittest.main()
