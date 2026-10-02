"""Exercise the actual runner isolation function without importing game/staging modules."""
import ast
import math
import re
from pathlib import Path
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'scripts/run_elecbug_contact_runtime.py'


def actual_function(name):
    tree = ast.parse(RUNNER.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {'math': math, 're': re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(RUNNER), 'exec'), namespace)
    return namespace[name]


def actual_environment():
    return actual_function('private_environment')


class Isolation(unittest.TestCase):
    def test_only_inactive_guard_requests_second_captain(self):
        for mask in (None, 'active', 'inactive', 'null-state', 'missing-manager'):
            with self.subTest(mask=mask), tempfile.TemporaryDirectory() as tmp:
                env = actual_environment()({'PIKMIN_P2_SECOND_CAPTAIN': '1',
                        'pikmin_p2_second_captain': '1', 'PIKMIN_COOP': '1'},
                        Path(tmp), Path('/exe'), 'landing', guard_mask=mask)
                self.assertEqual(env.get('PIKMIN_P2_SECOND_CAPTAIN'), '1' if mask == 'inactive' else None)
                self.assertNotIn('pikmin_p2_second_captain', env)
                self.assertNotIn('PIKMIN_COOP', env)

    def test_unknown_guard_cannot_change_startup(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            actual_environment()({}, Path(tmp), Path('/exe'), 'landing', guard_mask='typo')

    def test_hostile_game_overrides_and_settings_cannot_escape(self):
        for platform in ('windows', 'linux'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                external = base / 'user-settings.ini'
                external.write_text('user settings must stay intact')
                run = base / platform
                run.mkdir()
                hostile = dict(PIKMIN_SETTINGS_PATH=str(external), PIKMIN_SETTINGS_TEST_EARLY_EXIT='1',
                               BBFT_CONFIG=str(external), NECTAR_LANGUAGE='hostile', P2_OTHER_TEST='1',
                               PIKMIN_NETPLAY_TEST_TELEPORT='1', NECTAR_SAVE_DIR=str(base),
                               SDL_VIDEO_WINDOW_POS='0,0', SDL_VIDEODRIVER='dummy',
                               APPDATA=str(base), LOCALAPPDATA=str(base), HOME=str(base),
                               XDG_CONFIG_HOME=str(base), XDG_DATA_HOME=str(base), XDG_STATE_HOME=str(base),
                               XDG_CACHE_HOME=str(base), USERPROFILE=str(base), HOMEDRIVE='C:', HOMEPATH='/user',
                               PATH='trusted loader search', DISPLAY=':93', XAUTHORITY='/runner/private-auth')
                before = dict(hostile)
                env = actual_environment()(hostile, run, Path('/exact/executable'), 'white-electric')
                self.assertEqual(hostile, before)
                for key in ('PIKMIN_SETTINGS_TEST_EARLY_EXIT','BBFT_CONFIG','NECTAR_LANGUAGE','P2_OTHER_TEST',
                            'PIKMIN_NETPLAY_TEST_TELEPORT','SDL_VIDEO_WINDOW_POS','SDL_VIDEODRIVER','HOMEDRIVE','HOMEPATH'):
                    self.assertNotIn(key, env)
                for key in ('APPDATA','LOCALAPPDATA','HOME','USERPROFILE','XDG_CONFIG_HOME',
                            'XDG_CACHE_HOME','XDG_DATA_HOME','XDG_STATE_HOME','NECTAR_SAVE_DIR'):
                    directory = Path(env[key])
                    self.assertTrue(directory.is_dir())
                    self.assertTrue(directory.is_relative_to(run))
                settings = Path(env['PIKMIN_SETTINGS_PATH'])
                self.assertTrue(settings.is_relative_to(run))
                settings.write_text('fixture settings')
                self.assertEqual(external.read_text(), 'user settings must stay intact')
                for key in ('PATH','DISPLAY','XAUTHORITY'):
                    self.assertEqual(env[key], hostile[key])
                self.assertEqual(env['P2_ELECBUG_MODE'], 'white-electric')
                self.assertEqual(env['PIKMIN_P2_ROOM_WINDOW'], '960x540')
                self.assertEqual(env['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'], '1')

    def test_case_insensitive_aliases_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            aliases = {key: 'external' for key in ('pIkMiN_SETTINGS_PATH','BbFt_Config','nEcTaR_LANGUAGE',
                       'sDl_VIDEODRIVER','p2_guard_mask','AppData','LocalAppData','Home','UserProfile','Xdg_Config_Home')}
            env = actual_environment()(aliases, Path(tmp), Path('/exe'), 'landing')
            for key in aliases:
                self.assertNotIn(key, env)
            self.assertEqual(env['P2_ELECBUG_MODE'], 'landing')

    def test_no_inherited_guard_injection_and_fixed_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = actual_environment()({'P2_ELECBUG_GUARD_MASK':'active','P2_ELECBUG_READY_ONLY':'1',
                       'PIKMIN_P2_ROOM_WINDOW':'off'}, Path(tmp), Path('/exe'), 'red-electric')
            self.assertNotIn('P2_ELECBUG_GUARD_MASK', env)
            self.assertNotIn('P2_ELECBUG_READY_ONLY', env)
            self.assertEqual(env['PIKMIN_P2_ROOM_WINDOW'], '960x540')


class InactiveGuardEvidence(unittest.TestCase):
    good = '\n'.join((
        'P2_ELECBUG_STARTUP second_captain=1 capacity=2 guard=inactive',
        'P2_ELECBUG_CAPTAIN_INITIALIZED slot=0 active=1 hp=100.000 frame=40',
        'P2_ELECBUG_CAPTAIN_INITIALIZED slot=1 active=0 hp=100.000 frame=40',
        'P2_ELECBUG_GUARD_OBSERVATION mask=inactive injected=1 slot=1 active=0 frame=40',
    ))

    def test_supported_startup_and_matching_initialized_slot(self):
        self.assertTrue(actual_function('inactive_guard_witness')(self.good))

    def test_rejects_missing_or_unrelated_initialization(self):
        lines = self.good.splitlines()
        cases = ['\n'.join(lines[:i] + lines[i+1:]) for i in range(len(lines))]
        cases += [self.good.replace('injected=1 slot=1', 'injected=1 slot=0'),
                  self.good.replace('active=0 frame=40', 'active=0 frame=41'),
                  self.good.replace('slot=0 active=1', 'slot=0 active=0'),
                  self.good.replace('slot=1 active=0 hp=', 'slot=1 active=1 hp='),
                  '\n'.join([lines[0], lines[1], lines[3], lines[2]]),
                  '\n'.join([lines[1], lines[0], lines[2], lines[3]]),
                  '\n'.join([lines[0], lines[1], lines[2], lines[2], lines[3]])]
        for text in cases:
            with self.subTest(text=text):
                self.assertFalse(actual_function('inactive_guard_witness')(text))

    def test_rejects_unhealthy_or_malformed_initial_health(self):
        for hp in ('0', '1', '-3', 'nan', 'inf', '1.2.3'):
            with self.subTest(hp=hp):
                self.assertFalse(actual_function('inactive_guard_witness')(self.good.replace('100.000', hp)))


if __name__ == '__main__':
    unittest.main()
