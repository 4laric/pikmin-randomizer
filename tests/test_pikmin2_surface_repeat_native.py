import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experimental.pikmin2_campaign import ledger_text
from scripts.test_pikmin2_surface_repeat_native import RepeatProcess,run_test,build_apps


class RepeatRuntimeDriverTests(unittest.TestCase):
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):run_test(SimpleNamespace(output=Path(d)))

    def test_timeout_bounded(self):
        for timeout in (0,301):
            with self.assertRaises(ValueError):RepeatProcess(Path('.'),timeout)

    def test_surface_config_comes_from_authoritative_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'session').mkdir();run=root/'run';run.mkdir()
            (root/'session/surface-ledger.json').write_text(json.dumps({'surface':{'position':[-205.5,80,1160]}}))
            (run/'manual-entrance.txt').write_text('repeat')
            (run/'p2-economy.txt').write_text(ledger_text({'treasure:a':100}))
            (run/'native.log').write_text('P2_REPEAT_RESTORE\nP2_REPEAT_F6_INJECTED\nP2_REPEAT_CONFIRM_INJECTED\n')
            process=RepeatProcess(root,30)
            with patch('scripts.test_pikmin2_surface_repeat_native.subprocess.run',return_value=SimpleNamespace(returncode=42)):
                process(['fixture'],cwd=run)
            self.assertEqual((run/'repeat-fixture.txt').read_text(),'surface 1 100 -205.5 80 1160\n')
            self.assertEqual(process.runs[0]['restored_pokos'],100)

    def test_missing_injected_input_marker_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'run';run.mkdir()
            (run/'p2-economy.txt').write_text(ledger_text({}))
            (run/'native.log').write_text('P2_REPEAT_RESTORE\n')
            with patch('scripts.test_pikmin2_surface_repeat_native.subprocess.run',return_value=SimpleNamespace(returncode=42)):
                with self.assertRaisesRegex(RuntimeError,'injected SDL'):
                    RepeatProcess(root,30)(['fixture'],cwd=run)

    def test_private_recipe_uses_current_objects_and_private_import_library(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cwd=root/'native';cwd.mkdir()
            (cwd/'build.ninja').write_text('build bin/nectar.exe: LINK CMakeFiles/pikmin_pc.dir/pc_port/pc_main.cpp.obj CMakeFiles/pikmin_pc.dir/pc_port/new_module.cpp.obj CMakeFiles/pikmin_pc.dir/pc_port/settings/pc_settings.cpp.obj | lib.a\n')
            recipe=root/'recipe.json';recipe.write_text(json.dumps(dict(cwd=str(cwd),
                compile=['g++','scripts/pikmin2_manual_entrance.cpp','-o','old/manual.obj'],
                link=['g++','CMakeFiles/pikmin_pc.dir/old.cpp.obj','old/manual.obj','-o','old/manual.exe','-Wl,--out-implib,libnectar.dll.a'])))
            target=root/'private'
            with patch('scripts.test_pikmin2_surface_repeat_native.subprocess.run'):
                build_apps(target,recipe,'test object base')
            commands=json.loads((target/'commands.json').read_text())
            for name in ('manual','fixture'):
                link=commands[name]['link']
                self.assertIn('CMakeFiles/pikmin_pc.dir/pc_port/new_module.cpp.obj',link)
                self.assertNotIn('CMakeFiles/pikmin_pc.dir/old.cpp.obj',link)
                self.assertIn('-Wl,--out-implib,'+str(target/f'{name}.dll.a'),link)
                self.assertIn(str(target/'settings.obj'),link)
                self.assertNotIn('CMakeFiles/pikmin_pc.dir/pc_port/settings/pc_settings.cpp.obj',link)
            self.assertIn('-fno-lto',commands['settings_compile'])
            self.assertIn('class ManualEntranceApp',(target/'manual-app.inc').read_text())


if __name__=='__main__':unittest.main()
