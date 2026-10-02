"""Exercise the actual runner isolation function without importing game/staging modules."""
import ast
from pathlib import Path
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'scripts/run_elecbug_contact_runtime.py'


def actual_environment():
    tree = ast.parse(RUNNER.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'private_environment')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(RUNNER), 'exec'), namespace)
    return namespace['private_environment']


class Isolation(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
